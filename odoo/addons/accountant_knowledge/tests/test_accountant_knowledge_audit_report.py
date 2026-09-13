from datetime import timedelta
from freezegun import freeze_time
from lxml import etree

from odoo import Command
from odoo.tests.common import users

from odoo.addons.accountant_knowledge.controller.main import is_html_element_empty
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


class TestAccountantKnowledgeAuditReport(TransactionCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invoice_user = mail_new_test_user(
            cls.env,
            login='invoice_user',
            groups='account.group_account_invoice',
            notification_type='inbox',
        )
        cls.user_admin = cls.env.ref('base.user_admin')
        cls.account_report = cls.env['account.report'].create({
            'name': 'Account Report',
        })
        cls.category = cls.env['knowledge.article.template.category'].create({
            'name': 'Accounting'
        })

        cls.audit_report_template = cls.env['knowledge.article'].create({
            'is_template': True,
            'is_audit_report_template': True,
            'template_name': 'Annual Report Root Template',
            'template_category_id': cls.category.id,
        })

        cls.audit_report_child_template = cls.env['knowledge.article'].create({
            'is_template': True,
            'is_audit_report_template': True,
            'template_name': 'Annual Report Child Template',
            'parent_id': cls.audit_report_template.id,
            'template_category_id': cls.category.id,
        })

        cls.audit_report = cls.env['audit.report'].with_user(cls.user_admin).create({
            'knowledge_template_article_id': cls.audit_report_template.id,
            'title': 'My Annual Report',
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
            'responsible_user_ids': [
                Command.link(cls.user_admin.id),
            ],
        })

    def test_automatically_invite_responsible_users_on_root_article(self):
        """ Check that the responsible users are automatically invited to the
            article linked to the audit report. """

        audit_report = self.env['audit.report'].create({
            'title': 'My Annual Report',
            'responsible_user_ids': [
                Command.link(self.user_demo.id)
            ],
        })

        article = audit_report.knowledge_article_id
        self.assertEqual(len(article.article_member_ids), 2)
        self.assertEqual(article.article_member_ids[0].partner_id, self.env.user.partner_id)
        self.assertEqual(article.article_member_ids[0].permission, 'write')
        self.assertEqual(article.article_member_ids[1].partner_id, self.user_demo.partner_id)
        self.assertEqual(article.article_member_ids[1].permission, 'write')

    @users('invoice_user')
    def test_invoice_user_can_apply_regular_knowledge_template(self):
        """Applying a regular Knowledge template should not require access to accountant-only models."""
        self.assertFalse(self.env['audit.report'].has_access('read'))
        article = self.env['knowledge.article'].create({'name': 'Test Article'})
        # The created article has an empty audit_report_id cached. Clear it to
        # reproduce the uncached access done when loading a template from the UI.
        article.invalidate_recordset(['audit_report_id'])

        body = article.apply_template(
            self.env.ref('knowledge.knowledge_article_template_meeting_minutes').id,
            skip_body_update=True,
        )
        self.assertTrue(body)

    def test_is_html_element_empty(self):
        """ Check that the `is_html_element_empty` method correctly identifies
            empty HTML elements, ignoring all empty tags and whitespace
            characters."""
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div></div>
        ''')))
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div>   </div>
        ''')))
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div><div></div></div>
        ''')))
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div><div> </div></div>
        ''')))
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div><div> </div> </div>
        ''')))
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div> <div> </div> </div>
        ''')))
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div><p><br/></p></div>
        ''')))
        # NBSP character (\u00A0):
        self.assertTrue(is_html_element_empty(etree.fromstring('''
            <div><p>&#160;<br/></p></div>
        ''')))

        self.assertFalse(is_html_element_empty(etree.fromstring('''
            <div>Hello</div>
        ''')))
        self.assertFalse(is_html_element_empty(etree.fromstring('''
            <div><p>Hello<br/></p></div>
        ''')))

    def test_gc_trashed_articles_for_audit_report(self):
        """
        Check that trashed knowledge articles and their linked audit reports
        are deleted by the garbage collector.
        """
        parent_article = self.audit_report.knowledge_article_id
        child_article = parent_article.child_ids[0]
        other_child_article = self.env['knowledge.article'].create({
            'name': 'Other Child Article',
            'parent_id': parent_article.id,
        })
        parent_article.action_send_to_trash()
        other_child_article.action_unarchive()
        trash_limit_days = 30
        self.env['ir.config_parameter'].sudo().set_param(
            'knowledge.knowledge_article_trash_limit_days',
            trash_limit_days,
        )
        article_deletion_date = parent_article.write_date + timedelta(
            days=trash_limit_days,
            seconds=30,
        )

        with freeze_time(article_deletion_date):
            self.env['knowledge.article']._gc_trashed_articles()
        self.assertFalse(parent_article.exists(),
            "Trashed knowledge article linked to annual report should be deleted after _gc_trashed_articles.")
        self.assertFalse(child_article.exists(),
            "Trashed child article linked to parent article should be deleted after _gc_trashed_articles.")
        self.assertTrue(other_child_article.exists(),
            "Restored child article linked to parent article should not be deleted after _gc_trashed_articles.")
        self.assertFalse(parent_article.audit_report_id.exists(),
            "audit report should be deleted after _gc_trashed_articles.")
