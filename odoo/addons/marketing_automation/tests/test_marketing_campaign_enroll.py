from contextlib import nullcontext
from datetime import datetime

from odoo.addons.marketing_automation.tests.common import MarketingAutomationCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged, users
from odoo.tools import mute_logger


class MarketingCampaignEnrollCommon(MarketingAutomationCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.campaign.write({
            'state': 'running',
        })
        cls.activity_begin_mail = cls._create_activity_mail(
            cls.campaign,
            user=cls.user_marketing_automation,
            act_values={
                'trigger_type': 'begin',
                'interval_number': 0, 'interval_type': 'hours',
            },
        )

        # Juanuary 02 to ease cross-months / cross-year checks // 2029 as 2028 is a leap year
        cls.date_reference = datetime(2029, 1, 2, 10, 15, 30)


@tagged("marketing_automation", "ma_enroll")
class TestMarketingCampaignDomain(MarketingCampaignEnrollCommon):
    """ Test domain-based enroll mode for campaigns. It enrolls participants
    based on an input filtering domain. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # add some more contacts for batch check
        cls.test_contacts += cls.env['mailing.contact'].create([
            {
                'country_id': cls.test_countries[idx % len(cls.test_countries)].id,
                'email': f'ma.test.contact.add.{idx}@example.com',
                'name': f'MATest_{idx + 10}',
            }
            for idx in range(30)
        ])

    def test_assert_initial_values(self):
        """ Just ensure inherited / created test data validity """
        self.assertEqual(len(self.test_contacts), 40)
        self.assertEqual(len(set(self.test_contacts.mapped('name'))), 40, 'Name is unique on all contacts')
        self.assertEqual(len(set(self.test_contacts.mapped('country_id'))), 4, 'Country is not unique')

    @users('user_marketing_automation')
    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_domain_enroll_unique_field(self):
        test_contacts = self.test_contacts.with_user(self.env.user)
        # make email of first 10 repeated on 20+ and 30+ (aka: 2 duplicates / record for 10 first)
        # and void one value, to check support of Falsy values
        # for country, see in common.py: rotate on 1 Falsy + 4 countries
        for idx in range(10):
            test_contacts[20 + idx].write({'email': test_contacts[idx].email})
            test_contacts[30 + idx].write({'email': test_contacts[idx].email})
        (test_contacts[0] + test_contacts[20] + test_contacts[30]).write({'email': False})

        email_field = self.env['ir.model.fields']._get('mailing.contact', 'email')
        country_field = self.env['ir.model.fields']._get('mailing.contact', 'country_id')

        campaign = self.campaign.with_user(self.env.user)
        # note sorting of contact is name asc, id desc -> should be respected when searching for new participants
        for unique_field, should_raise, out_of_unique_vals, exp_records in [
            # char field: void value is kept
            (email_field, False, {'email': 'unique@example.com'}, test_contacts[:20]),
            # m2o field: void value is rejected (FIXME probably)
            (country_field, False, {'country_id': self.env.ref('base.ca').id}, test_contacts[1:5]),
        ]:
            with self.subTest(fname=unique_field.name, ftype=unique_field.ttype):
                campaign.participant_ids.unlink()
                self.assertEqual(campaign.running_participant_count, 0)
                raiseIfInvalidField = self.assertRaises(ValidationError) if should_raise else nullcontext()
                with raiseIfInvalidField:
                    campaign.write({
                        'unique_field_id': unique_field.id,
                    })

                with self.mock_datetime_and_now(self.date_reference):
                    self._launch_campaign(campaign)
                self.assertEqual(campaign.running_participant_count, len(exp_records))
                self.assertEqual(sorted(campaign.participant_ids.mapped('res_id')), sorted(exp_records.ids))

                if should_raise:
                    continue

                # made unique again -> should be added in campaign
                test_contacts[-1].write(out_of_unique_vals)
                campaign.sync_participants()
                new_exp_records = exp_records + test_contacts[-1]
                self.assertEqual(campaign.running_participant_count, len(new_exp_records))
                self.assertEqual(sorted(campaign.participant_ids.mapped('res_id')), sorted(new_exp_records.ids))
