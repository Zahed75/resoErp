import logging
import time

from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.addons.base.models.ir_cron import MIN_FAILURE_COUNT_BEFORE_DEACTIVATION
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.marketing_automation.models.marketing_activity import MarketingActivity
from odoo.addons.marketing_automation.models.marketing_participant import MarketingParticipant
from odoo.addons.marketing_automation.models.marketing_trace import MarketingTrace
from odoo.addons.test_mail.tests.test_performance import BaseMailPerformance
from odoo.addons.test_marketing_automation.tests.common import TestMACommon
from odoo.tests.common import warmup
from odoo.tests import tagged, users
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)


@tagged('mail_performance', 'marketing_automation', 'post_install', '-at_install')
class MAPerformanceCommon(BaseMailPerformance, TestMACommon, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.date_reference = fields.Datetime.from_string("2024-07-15 10:30:00")

    @contextmanager
    def trace_duration(self, label):
        """ Context manager to measure wall-clock time """
        start = time.perf_counter()
        yield
        spent = time.perf_counter() - start
        _logger.info("[Performance] %s: %.4f seconds", label, spent)

    @contextmanager
    def mockMACalls(self, error_dict=None):
        error_dict = error_dict or {}
        original_act_execute_on_traces = MarketingActivity.execute_on_traces
        original_part_create = MarketingParticipant.create
        original_part_search = MarketingParticipant.search
        original_part_write = MarketingParticipant.write
        original_trace_create = MarketingTrace.create
        original_trace_search = MarketingTrace.search
        original_trace_write = MarketingTrace.write

        # error generation tweaks
        # 1. fail at participant creation (e.g. )
        fail_part_create_ctr = error_dict.get('fail_part_create_ctr')
        fail_act_exec_traces_ctr = error_dict.get('fail_act_exec_traces_ctr')

        creation_counter = 0
        exec_traces_counter = 0

        def _failing_part_create(*args, **kwargs):
            nonlocal fail_part_create_ctr
            nonlocal creation_counter
            nonlocal original_part_create

            model, vals_list = args
            creation_counter += len(vals_list)
            if fail_part_create_ctr and creation_counter >= fail_part_create_ctr:
                raise MemoryError('Raising MemoryError')
            return original_part_create(model, vals_list, **kwargs)

        def _failing_act_exec_traces(*args):
            nonlocal fail_act_exec_traces_ctr
            nonlocal exec_traces_counter
            nonlocal original_part_create

            model, traces = args
            exec_traces_counter += 1
            # make time move forward, notably because crons check time spend in jobs
            # and may loop indefinitively
            self.frozen_datetime_mock.tick(delta=timedelta(minutes=1))

            if fail_act_exec_traces_ctr and exec_traces_counter >= fail_act_exec_traces_ctr:
                raise MemoryError('Raising MemoryError')
            return original_act_execute_on_traces(model, traces)

        with patch.object(MarketingActivity, 'execute_on_traces',
                          autospec=True, side_effect=_failing_act_exec_traces) as mock_act_execute_on_traces, \
             patch.object(MarketingParticipant, 'create',
                          autospec=True, side_effect=_failing_part_create) as mock_part_create, \
             patch.object(MarketingParticipant, 'search',
                          autospec=True, side_effect=original_part_search) as mock_part_search, \
             patch.object(MarketingParticipant, 'write',
                          autospec=True, side_effect=original_part_write) as mock_part_write, \
             patch.object(MarketingTrace, 'create',
                          autospec=True, side_effect=original_trace_create) as mock_trace_create, \
             patch.object(MarketingTrace, 'search',
                          autospec=True, side_effect=original_trace_search) as mock_trace_search, \
             patch.object(MarketingTrace, 'write',
                          autospec=True, side_effect=original_trace_write) as mock_trace_write:
            self._mock_act_execute_on_traces = mock_act_execute_on_traces
            self._mock_part_create = mock_part_create
            self._mock_part_search = mock_part_search
            self._mock_part_write = mock_part_write
            self._mock_trace_create = mock_trace_create
            self._mock_trace_search = mock_trace_search
            self._mock_trace_write = mock_trace_write
            yield

    @classmethod
    def _create_test_campaign(cls, campaign_domain=None):
        # --------------------------------------------------
        # CAMPAIGN, based on marketing.test.performance
        #
        # ACT1           MAIL: begin, +1 hour
        #   ACT1_1       -> opened -> send an SMS after 1h with a promotional link
        #   ACT1_2       -> not_opened within 1 day-> update description through server action
        # ACT2           SMS: begin, +2 hour
        #   ACT2_1       -> clicked -> send an SMS after 1h with a promotional link
        #   ACT2_2       -> not_clicked within 1 day-> update description through server action
        # ACT3           WA: begin, +3 hour
        #   ACT3_1       -> replied -> send an SMS after 1h with a promotional link
        #   ACT3_2       -> not_replied within 1 day-> update description through server action
        # ACT4           SA: begin, +4 hour
        # --------------------------------------------------
        campaign_domain = campaign_domain or [("name", "!=", "Invalid")]
        test_campaign = cls.env['marketing.campaign'].with_user(cls.user_marketing_automation).create({
            "domain": campaign_domain,
            "model_id": cls.env['ir.model']._get_id("marketing.test.performance"),
            "name": "Test Campaign",
        })
        # ACT1: send a mailing
        act1_begin_mailing = cls._create_activity_mail(
            test_campaign,
            mailing_values={
                "email_from": cls.user_marketing_automation.email_formatted,
                "keep_archives": True,
            },
            act_values={
                "interval_number": 1,
                "interval_type": "hours",
                "trigger_type": "begin",
            },
        )
        # ACT1_1: send an SMS 1 hour after 'open' event
        _act1_1_sms = cls._create_activity_mail(
            test_campaign,
            mailing_values={
                "body_plaintext": "SMS for {{ object.name }}: please confirm on https://test.example.com/confirm_mail",
                "mailing_type": "sms",
                "sms_allow_unsubscribe": True,
            },
            act_values={
                "interval_number": 1,
                "interval_type": "hours",
                "parent_id": act1_begin_mailing.id,
                "trigger_type": "mail_open",
            },
        )
        # ACT_1_2: update description if not opened after 1 day
        # created by admin, should probably not give rights to marketing
        _act1_2_sa = cls._create_activity_sa(
            test_campaign,
            "records.write({'selection_field': 'key1'})",
            act_values={
                "activity_domain": [("email_from", "!=", False)],
                "interval_number": 1,
                "interval_type": "days",
                "parent_id": act1_begin_mailing.id,
                "trigger_type": "mail_not_open",
            },
        )

        # ACT2: send a SMS mailing
        act2_begin_sms = cls._create_activity_mail(
            test_campaign,
            mailing_values={
                "body_plaintext": "SMS for {{ object.name }}: mega promo on https://test.example.com/promo",
                "mailing_type": "sms",
                "keep_archives": True,
            },
            act_values={
                "interval_number": 2,
                "interval_type": "hours",
                "trigger_type": "begin",
            },
        )
        # ACT2_1: send an SMS 1 hour after a 'click' event
        _act2_1_sms = cls._create_activity_mail(
            test_campaign,
            mailing_values={
                "body_plaintext": "SMS for {{ object.name }}: please confirm on https://test.example.com/confirm_sms",
                "mailing_type": "sms",
                "sms_allow_unsubscribe": True,
            },
            act_values={
                "interval_number": 1,
                "interval_type": "hours",
                "parent_id": act2_begin_sms.id,
                "trigger_type": "sms_click",
            },
        )
        # ACT2_2: update description if not opened after 1 day
        _act2_2_sa = cls._create_activity_sa(
            test_campaign,
            "records.write({'selection_field': 'key2'})",
            act_values={
                "activity_domain": [("phone", "!=", False)],
                "interval_number": 1,
                "interval_type": "days",
                "parent_id": act2_begin_sms.id,
                "trigger_type": "sms_not_click",
            },
        )

        # ACT2: send a whatsapp
        act3_begin_wa = cls._create_activity_wa(
            test_campaign,
            template_values={
                'name': f'TestTemplate for {test_campaign.id}',
            },
            act_values={
                "interval_number": 3,
                "interval_type": "hours",
                "trigger_type": "begin",
            },
        )
        # ACT3_1: send an SMS 1 hour after a 'replied' event
        _act3_1_sms = cls._create_activity_mail(
            test_campaign,
            mailing_values={
                "body_plaintext": "SMS for {{ object.name }}: please confirm on https://test.example.com/confirm_wa",
                "mailing_type": "sms",
                "sms_allow_unsubscribe": True,
            },
            act_values={
                "interval_number": 1,
                "interval_type": "hours",
                "parent_id": act3_begin_wa.id,
                "trigger_type": "whatsapp_replied",
            },
        )
        # ACT3_2: update description if not replied after 1 day
        _act3_2_sa = cls._create_activity_sa(
            test_campaign,
            "records.write({'selection_field': 'key3'})",
            act_values={
                "activity_domain": [("phone", "!=", False)],
                "interval_number": 1,
                "interval_type": "days",
                "parent_id": act3_begin_wa.id,
                "trigger_type": "whatsapp_not_replied",
            },
        )

        # ACT4: run a SA
        _act4 = cls._create_activity_sa(
            test_campaign,
            "records.write({'selection_field': 'key1'})",
            act_values={
                "interval_number": 4,
                "interval_type": "hours",
                "trigger_type": "begin",
            },
        )

        return test_campaign

    @classmethod
    def _create_perf_test_records(cls, count=200, include_void=True, include_dupe=False):
        # --------------------------------------------------
        # TEST RECORDS, using marketing.test.performance
        #
        # 200 times (or 'count')
        # - 3 records with partners
        # - 1 records wo partner, but email/mobile
        # - 1 record wo partner/email/mobile
        # AKA 1000 records
        # --------------------------------------------------
        return cls._create_marketauto_records(
            model="marketing.test.performance",
            count=count,
            include_void=include_void,
            include_dupe=include_dupe,
        )


@tagged('mail_performance', 'ma_cron', 'post_install', '-at_install')
class TestMACron(MAPerformanceCommon):
    """ Cron behavior for marketing campaigns

    Quick timing info
    Vers -- cnt -- aver
    19.0  10000    37  / 50 (unique)
    19.0   1000    1.7 / 1.9 (unique)
    19.0    100    0.15
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # test records
        cls.total_size = 100
        cls.test_records = cls._create_perf_test_records(count=int(cls.total_size / 5), include_void=False, include_dupe=True)
        cls.dupe_size = cls.total_size / 5

        # test campaign, same for all tests
        with cls.mock_datetime_and_now(cls, cls.date_reference):
            cls.campaign = cls._create_test_campaign(
                campaign_domain=[("name", "!=", "Invalid"), ("selection_field", "!=", "key3")],
            )
            cls.campaign.write({'state': 'running'})
        cls.begin_activities = cls.campaign.marketing_activity_ids.filtered(lambda a: a.trigger_type == 'begin')

    def test_assert_initial_values(self):
        """ Common initial tests for this class """
        self.assertEqual(len(self.test_records), self.total_size)
        self._assert_cron_progress(self.cron_ma_sync_participants, 0)
        self._assert_cron_progress(self.cron_ma_execute_activities, 0)
        self.assertEqual(len(self.begin_activities), 4)

        # crons are clean
        self._assert_cron_state(self.cron_ma_sync_participants)
        self._assert_cron_state(self.cron_ma_execute_activities)

    def test_cron_execute_activities(self):
        """ Test 'ir_cron_campaign_execute_activities' cron """
        cron = self.cron_ma_execute_activities
        campaign = self.campaign

        with self.mock_datetime_and_now(self.date_reference):
            campaign.sync_participants()
        self.assertEqual(len(campaign.participant_ids), self.total_size)
        self.assertActivityScheduled(self.begin_activities, self.test_records)

        with self.trace_duration('Cron Complete'), \
             self.mock_datetime_and_now(self.date_reference + timedelta(hours=4)), \
             self.mock_mail_gateway(), self.mockSMSGateway(), \
             self.mockWhatsappGateway(), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_sync_participants') as captured_triggers_sync, \
             self.capture_triggers('marketing_automation.ir_cron_campaign_execute_activities') as captured_triggers_execute:
            cron.method_direct_trigger()

        # progression check
        self.assertActivityProcessed(self.begin_activities, self.test_records)
        # cron usage
        self._assert_cron_state(
            cron, failure_count=0, first_failure_date=False,
            lastcall=self.date_reference + timedelta(hours=4),
        )
        self.assertEqual(cron.nextcall, self.date_reference + timedelta(hours=5), 'Rescheduled for later, not asap (to check for time)')
        self._assert_cron_progress(cron, 1, remaining=0)
        # triggers: for children traces (_generate_children_traces); those are
        # scheduled one day after the 'begin' trace, see setup
        self.assertEqual(len(captured_triggers_execute.records), 3,
                         "Cron triggers for child activities, added in '_generate_children_traces'")
        self.assertEqual(captured_triggers_execute.records.cron_id, cron)
        self.assertEqual(
            sorted(captured_triggers_execute.records.mapped('call_at')),
            [self.date_reference + timedelta(days=1, hours=1), self.date_reference + timedelta(days=1, hours=2), self.date_reference + timedelta(days=1, hours=3)],
        )
        # sync untouched
        self.assertEqual(len(captured_triggers_sync.records), 0,
                         'Run did not schedule anything (nor commit progress)')

    def test_cron_execute_activities_fail(self):
        """ Test 'ir_cron_campaign_execute_activities' cron managing failures """
        cron = self.cron_ma_execute_activities
        campaign = self.campaign

        with self.mock_datetime_and_now(self.date_reference):
            campaign.sync_participants()
        self.assertEqual(len(campaign.participant_ids), self.total_size)
        self.assertActivityScheduled(self.begin_activities, self.test_records)

        # fail when calling execute_on_traces, simulating a MemoryError
        with self.mockMACalls({'fail_act_exec_traces_ctr': 2}), \
             mute_logger('odoo.addons.base.models.ir_cron'),\
             self.mock_datetime_and_now(self.date_reference + timedelta(hours=4)), \
             self.mock_mail_gateway(), self.mockSMSGateway(), \
             self.mockWhatsappGateway(), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_sync_participants') as captured_triggers_sync, \
             self.capture_triggers('marketing_automation.ir_cron_campaign_execute_activities') as captured_triggers_execute:
            cron.method_direct_trigger()

        # progression check
        self.assertActivityScheduled(self.begin_activities, self.test_records)  # 'Due to fail, traces has not been processed'
        # cron usage
        self._assert_cron_state(
            cron, failure_count=1,
            first_failure_date=self.date_reference + timedelta(hours=4),
            lastcall=self.date_reference + timedelta(hours=4),
        )
        self.assertEqual(cron.nextcall, self.date_reference + timedelta(hours=5), 'Rescheduled for later, not asap (to check for time)')
        self._assert_cron_progress(cron, 1, remaining=0)
        self.assertEqual(len(captured_triggers_sync.records), 0,
                         'Run did not schedule anything (nor commit progress)')
        # sync untouched
        self.assertEqual(len(captured_triggers_execute.records), 0,
                         'Run did not schedule anything (nor commit progress)')

    def test_cron_execute_activities_fail_mixed(self):
        """ Test 'ir_cron_campaign_execute_activities' cron managing failures
        on working and failing campaigns, aka check iterative support """
        cron = self.cron_ma_execute_activities
        campaign = self.campaign
        begin_activities = self.begin_activities
        campaign_2 = campaign.copy({'state': 'running'})
        begin_activities_2 = campaign_2.marketing_activity_ids.filtered(lambda a: a.trigger_type == 'begin')

        with self.mock_datetime_and_now(self.date_reference):
            (campaign + campaign_2).sync_participants()
        self.assertEqual(len(campaign.participant_ids), self.total_size)
        self.assertEqual(len(campaign_2.participant_ids), self.total_size)
        self.assertActivityScheduled(begin_activities, self.test_records)
        self.assertActivityScheduled(begin_activities_2, self.test_records)

        # fail when calling execute_on_traces, simulating a MemoryError during
        # 'campaign' 2d activity (aka 6th activity)
        with self.mockMACalls({'fail_act_exec_traces_ctr': 6}), \
             mute_logger('odoo.addons.base.models.ir_cron'),\
             self.mock_datetime_and_now(self.date_reference + timedelta(hours=4)), \
             self.mock_mail_gateway(), self.mockSMSGateway(), \
             self.mockWhatsappGateway(), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_sync_participants') as captured_triggers_sync, \
             self.capture_triggers('marketing_automation.ir_cron_campaign_execute_activities') as captured_triggers_execute:
            cron.method_direct_trigger()

        # progression check
        self.assertActivityScheduled(self.begin_activities, self.test_records)  # 'Due to fail, traces has not been processed'
        self.assertActivityScheduled(begin_activities_2, self.test_records)  # 'Due to fail, traces has not been processed'
        # cron usage
        self._assert_cron_state(
            cron, failure_count=1,
            first_failure_date=self.date_reference + timedelta(hours=4),
            lastcall=self.date_reference + timedelta(hours=4),
        )
        self.assertEqual(cron.nextcall, self.date_reference + timedelta(hours=5), 'Rescheduled for later, not asap (to check for time)')
        self._assert_cron_progress(cron, 1, remaining=0)
        self.assertEqual(len(captured_triggers_sync.records), 0,
                         'Run did not schedule anything (nor commit progress)')
        # sync untouched
        self.assertEqual(len(captured_triggers_execute.records), 0,
                         'Run did not schedule anything (nor commit progress)')

    def test_cron_synchronize_participants(self):
        """ Test 'ir_cron_campaign_sync_participants' cron """
        cron = self.cron_ma_sync_participants
        campaign = self.campaign

        with self.trace_duration('Cron Complete'), \
             self.mock_datetime_and_now(self.date_reference), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_sync_participants') as captured_triggers:
            cron.method_direct_trigger()

        # progression check
        self.assertEqual(
            len(campaign.participant_ids), self.total_size,
            'Synchronized everything, as process is not iterative')
        # cron usage: no failure detecter
        self._assert_cron_state(cron, failure_count=0, first_failure_date=False, lastcall=self.date_reference)
        self.assertEqual(cron.nextcall, self.cron_last_call + timedelta(hours=12), 'Rescheduled for later, not asap')
        self._assert_cron_progress(cron, 1, remaining=0)
        self.assertEqual(len(captured_triggers.records), 0,
                         'Run did not schedule anything (nor commit progress)')

    def test_cron_synchronize_participants_fail(self):
        """ Test 'ir_cron_campaign_sync_participants' cron managing failures """
        cron = self.cron_ma_sync_participants
        campaign = self.campaign

        with self.mockMACalls({'fail_part_create_ctr': 75}), \
             mute_logger('odoo.addons.base.models.ir_cron'),\
             self.mock_datetime_and_now(self.date_reference), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_sync_participants') as captured_triggers:
            cron.method_direct_trigger()

        # progression check
        self.assertEqual(
            len(campaign.participant_ids), 0,
            'Failed, everything is rollbacked (which could be improved)')
        # cron usage: failure detected once
        self._assert_cron_state(cron, active=True, failure_count=1, first_failure_date=self.date_reference, lastcall=self.date_reference)
        self.assertEqual(cron.nextcall, self.cron_last_call + timedelta(hours=12), 'Rescheduled for later, not asap')
        self._assert_cron_progress(cron, 1, remaining=0)
        self.assertEqual(len(captured_triggers.records), 0,
                         'Run did not schedule anything (nor commit progress)')

        # some more fails (see MIN_FAILURE_COUNT_BEFORE_DEACTIVATION) under limited
        # timeframe (see MIN_DELTA_BEFORE_DEACTIVATION) should deactivate it (such sad)
        for idx in range(MIN_FAILURE_COUNT_BEFORE_DEACTIVATION - 1):
            with self.mockMACalls({'fail_part_create_ctr': 75}), \
                 mute_logger('odoo.addons.base.models.ir_cron'),\
                 self.mock_datetime_and_now(self.date_reference + timedelta(days=(7 + idx))):
                cron.method_direct_trigger()
        # cron deactivated
        self.assertFalse(cron.active, 'Should be deactivated after successive fails')

    def test_cron_synchronize_participants_fail_mixed(self):
        """ Test 'ir_cron_campaign_sync_participants' cron managing failures
        on working and failing campaigns, aka check iterative support """
        cron = self.cron_ma_sync_participants
        campaign = self.campaign
        campaign_2 = campaign.copy({'state': 'running'})

        with self.mockMACalls({'fail_part_create_ctr': 175}), \
             mute_logger('odoo.addons.base.models.ir_cron'),\
             self.mock_datetime_and_now(self.date_reference), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_sync_participants') as captured_triggers:
            cron.method_direct_trigger()

        # progression check
        self.assertEqual(
            len(campaign.participant_ids), 0,
            'Failed, everything is rollbacked (which could be improved)')
        self.assertEqual(
            len(campaign_2.participant_ids), 0,
            'Failed, everything is rollbacked (which could be improved)')
        # cron usage
        self._assert_cron_state(
            cron, failure_count=1,
            first_failure_date=self.date_reference,
            lastcall=self.date_reference,
        )
        self.assertEqual(cron.nextcall, self.date_reference + timedelta(hours=1), 'Rescheduled for later, not asap (to check for time)')
        self._assert_cron_progress(cron, 1, remaining=0)
        self.assertEqual(len(captured_triggers.records), 0,
                         'Run did not schedule anything (nor commit progress)')

    def test_cron_synchronize_participants_unique(self):
        """ Test 'ir_cron_campaign_sync_participants' cron, dealing with field
        unicity. """
        cron = self.cron_ma_sync_participants
        campaign = self.campaign

        with self.mock_datetime_and_now(self.date_reference):
            campaign.write({'unique_field_id': self.env['ir.model.fields']._get(self.test_records._name, 'email_from').id})

        with self.trace_duration('Cron Complete Unique Check'), \
             self.mock_datetime_and_now(self.date_reference), \
             self.capture_triggers('marketing_automation.ir_cron_campaign_sync_participants') as captured_triggers:
            cron.method_direct_trigger()

        # progression check
        self.assertEqual(
            len(campaign.participant_ids), self.total_size - self.dupe_size,
            'Synchronized everything, as process is not iterative, minus duplicates')
        # cron usage
        self._assert_cron_state(cron, active=True, failure_count=0, first_failure_date=False, lastcall=self.date_reference)
        self.assertEqual(cron.nextcall, self.cron_last_call + timedelta(hours=12), 'Rescheduled for later, not asap')
        self._assert_cron_progress(cron, 1, remaining=0)
        self.assertEqual(len(captured_triggers.records), 0,
                         'Run did not schedule anything (nor commit progress)')

    def test_cron_synchronize_participants_unique_quick(self):
        """ Quick testing of unique feature support, easing early fault detection
        in queries / algorithm """
        cron = self.cron_ma_sync_participants
        campaign = self.campaign
        campaign_2 = campaign.copy({'state': 'running'})
        test_records = self.env['marketing.test.performance'].create([
            {'email_from': 'from.1@zboing.example.com'},
            {'email_from': 'from.2@zboing.example.com'},  # already participating
            {'email_from': 'from.3@zboing.example.com'},
            {'email_from': 'from.1@zboing.example.com'},  # duplicate inside new to consider
            {'email_from': 'from.2@zboing.example.com'},  # duplicate of already participating
        ])
        _existing = self.env['marketing.participant'].create({'campaign_id': campaign.id, 'res_id': test_records[1].id})
        _existing2 = self.env['marketing.participant'].create({'campaign_id': campaign_2.id, 'res_id': test_records[1].id})

        with self.mock_datetime_and_now(self.date_reference):
            (campaign + campaign_2).write({
                'domain': [('email_from', 'ilike', 'zboing.example.com')],
                'unique_field_id': self.env['ir.model.fields']._get(self.test_records._name, 'email_from').id,
            })
            with self.capture_triggers('marketing_automation.ir_cron_campaign_sync_participants') as captured_triggers:
                cron.method_direct_trigger()

        for c in campaign + campaign_2:
            self.assertEqual(len(c.participant_ids), 3)
            self.assertEqual(
                sorted(test_records.browse(c.participant_ids.mapped('res_id')).mapped('email_from')),
                [f'from.{idx}@zboing.example.com' for idx in range(1, 4)]
            )
        self._assert_cron_state(cron, active=True, failure_count=0, first_failure_date=False, lastcall=self.date_reference)
        self.assertEqual(cron.nextcall, self.cron_last_call + timedelta(hours=12), 'Rescheduled for later, not asap')
        self._assert_cron_progress(cron, 1, remaining=0)
        self.assertEqual(len(captured_triggers.records), 0,
                         'Run did not schedule anything (nor commit progress)')


@tagged('mail_performance', 'post_install', '-at_install')
class TestMAPerformance(MAPerformanceCommon):
    """ Simpler tests that do not require an heavy campaign in data """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_records = cls._create_perf_test_records()

    def setUp(self):
        super().setUp()
        with self.mock_datetime_and_now(self.date_reference):
            self.test_campaign = self._create_test_campaign()
        self._launch_campaign(self.test_campaign, date_reference=self.date_reference)

    def test_assert_initial_values(self):
        """ Check initial values for tests """
        self.assertEqual(len(self.test_records), 1000)

        self.assertFalse(self.test_campaign.require_sync)
        self.assertEqual(self.test_campaign.last_sync_date, self.date_reference)
        self.assertEqual(
            len(self.test_campaign.marketing_activity_ids.trace_ids),
            len(self.test_records) * 4,
            "Should have generated one trace / begin activity / campaign record",
        )
        self.assertEqual(
            len(self.test_campaign.participant_ids),
            len(self.test_records),
            "Should have generated one participant / campaign record",
        )

    @warmup
    def test_campaign_sync_participants_launch(self):
        """ Test 'sync_participants' at campaign beginning. It is called by a
        cron regularly, or manually on campaign form view to start the campaign
        directly. It creates participants and their starting trace. """
        with self.mock_datetime_and_now(self.date_reference):
            campaign = self._create_test_campaign()
        self.assertEqual(len(self.test_records), 1000)

        # local: 1099
        # runbot: 1099, taking 100 more to avoid runbot issues in stable
        with self.assertQueryCount(1099 + 100), \
             self.mock_datetime_and_now(self.date_reference), \
             self.mockMACalls():
            campaign.sync_participants()

        # sanity check
        self.assertEqual(len(campaign.participant_ids), len(self.test_records))
        # performance check
        self.assertEqual(
            self._mock_part_create.call_count, 10,
            'Sync participants: created by batches of 100')
        self.assertEqual(self._mock_part_search.call_count, 0)
        self.assertEqual(self._mock_part_write.call_count, 1000,
                         'Sync participants: participants updated one by one,could be improved probably')
        self.assertEqual(self._mock_trace_create.call_count, 1000,
            'Sync participants: trace created one by one, could be improved')
        self.assertEqual(self._mock_trace_search.call_count, 0)
        self.assertEqual(self._mock_trace_write.call_count, 0)

    @mute_logger(
        'odoo.addons.mass_mailing_sms.models.mailing_mailing',
        'odoo.addons.mass_mailing.models.mailing',
    )
    @warmup
    def test_execute_activities_then_sync_participants(self):
        """ Test 'execute_activities' on all activity types. Then test
        'sync_participants' on a running campaign, aka updating participants
        based on DB state. """
        campaign = self.test_campaign

        # local: 16864
        # runbot: 16869, taking 100 more to avoid runbot issues in stable
        # hours+4 -> is going to trigger all 4 begin activities
        with self.assertQueryCount(16869 + 100), \
             self.mock_datetime_and_now(self.date_reference + timedelta(hours=4)), \
             self.mock_mail_gateway(), self.mock_mail_app(), self.mockSMSGateway(), \
             self.mockWhatsappGateway(), self.patchWhatsappCronTrigger(), \
             self.mockMACalls():
            campaign.execute_activities()

        # produced side records check
        self.assertEqual(
            len(self._new_mails), len(self.test_records) - 200,
            "Should have sent one email / campaign record, minus canceled ones "
            "(no valid email -> no email created), aka 1000 - 200",
        )
        self.assertEqual(
            len(self._new_sms), len(self.test_records) - 200,
            "Should have sent one SMS / campaign record, minus canceled ones "
            "(no valid number -> no sms created), aka 1000 - 200",
        )
        self.assertEqual(
            len(self._new_wa_msg), len(self.test_records),
            "Should have sent one WA / campaign record, aka 1000",
        )
        self.assertEqual(
            len(campaign.marketing_activity_ids.trace_ids),
            len(self.test_records) * 10,
            "Should have: 4 begin activity + 6 sub activities / record, aka 10 * 1000",
        )
        # performance check
        self.assertEqual(self._mock_act_execute_on_traces.call_count, 8,
                         '4 activities * 2 batch / activity')
        self.assertEqual(self._mock_part_create.call_count, 0)
        self.assertEqual(self._mock_part_search.call_count, 0)
        self.assertEqual(self._mock_part_write.call_count, 8,
                         'Where do those come from anyway ?')
        self.assertEqual(self._mock_trace_create.call_count, 6000,
                         'Child trace creation: still done sequentially')
        self.assertEqual(self._mock_trace_search.call_count, 30,
                         'Yay 2*15. Probably because of batches inside batches. To check.')
        self.assertEqual(self._mock_trace_write.call_count, 1014,
                         'Where do those come from anyway ?')
        # side records performance check
        self.assertEqual(self.mail_mail_create_mocked.call_count, 20,
                         'Done by batch size inside activity execution batch (2 * 10)')
        self.assertEqual(self._mock_mail_message_create.call_count, 1022,
                         'Sequential creation spotted notably in whatsapp')
        self.assertEqual(self._mock_sms_create.call_count, 2,
                         'Done by activity execution batch (500 currently)')
        self.assertEqual(self._mock_wa_msg_create.call_count, 2,
                         'Done by activity execution batch (500 currently)')
        self.assertEqual(self._mock_wa_msg_write.call_count, 2000,
                         'Sequential update of whatsapp message (during creation and send)')

        # now create 10*5 records, unlink other 50 records, observe performance
        self.test_records_new = self._create_perf_test_records(count=10)
        self.assertEqual(len(self.test_records_new), 50)
        self.test_records[:50].unlink()

        # local: 74
        # runbot: 75, taking 10 more to avoid runbot issues in stable
        with self.assertQueryCount(75 + 10), \
             self.mock_datetime_and_now(self.date_reference + timedelta(hours=24)), \
             self.mockMACalls():
            campaign.sync_participants()

        # sanity check
        self.assertEqual(
            len(campaign.participant_ids), 1050,
            'Removed records still have their participant, set as unlinked'
        )
        # performance check
        self.assertEqual(self._mock_part_create.call_count, 1)
        self.assertEqual(self._mock_part_search.call_count, 1)
        self.assertEqual(self._mock_part_write.call_count, 51)
        self.assertEqual(self._mock_trace_create.call_count, 50,
                         'Created sequentially')
        self.assertEqual(self._mock_trace_search.call_count, 1)
        self.assertEqual(self._mock_trace_write.call_count, 1)

    @users("user_marketing_automation")
    @warmup
    def test_update_participants(self):
        """ 'action_update_participants' can be called manually when the
        workflow has been modified on an ongoing marketing campaign. """
        campaign = self.test_campaign.with_env(self.env)

        # update activities, should update scheduled dates
        activity_mail = campaign.marketing_activity_ids.filtered(
            lambda a: a.trigger_type == "begin" and a.activity_type == "email"
        )
        self.assertTrue(activity_mail)
        activity_mail.write({
            "interval_number": 2,
        })

        # create new activities that are about to trigger the "require sync" flag !
        new_activity_begin = self._create_activity_mail(
            campaign,
            user=self.env.user,
            act_values={
                "interval_number": 1,
                "interval_type": "days",
                "name": "New begin MAIL activity",
                "trigger_type": "begin",
            },
        )
        _new_activity_sub = self._create_activity_sa(
            campaign,
            "records.write({'selection_field': 'key3'})",
            act_values={
                "activity_domain": [("email_from", "!=", False)],
                "interval_number": 1,
                "interval_type": "days",
                "parent_id": new_activity_begin.id,
                "trigger_type": "mail_not_open",
            },
        )

        # local: 1055
        # runbot: 1055, taking 100 more to avoid runbot issues in stable
        with self.assertQueryCount(1055 + 100), \
             self.mockMACalls(), \
             self.mock_datetime_and_now(self.date_reference + timedelta(hours=2)):
            campaign.action_update_participants()

        self.assertEqual(self._mock_part_create.call_count, 0)
        self.assertEqual(self._mock_part_search.call_count, 5)
        self.assertEqual(self._mock_part_write.call_count, 7)
        self.assertEqual(self._mock_trace_create.call_count, 1000,
                         'New traces for new begin activity created sequentially')
        self.assertEqual(self._mock_trace_search.call_count, 13)
        self.assertEqual(self._mock_trace_write.call_count, 1000,
                         'Looks like sequential update')
