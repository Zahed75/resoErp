import logging

from odoo import _, api, fields, models
from odoo.addons.whatsapp.tools.whatsapp_exception import WhatsAppError
from odoo.addons.whatsapp_oauth.tools.whatsapp_oauth_api import WhatsAppOAuthApi
from odoo.exceptions import RedirectWarning, ValidationError

_logger = logging.getLogger(__name__)


class WhatsappAccount(models.Model):
    _inherit = 'whatsapp.account'

    app_secret = fields.Char(required=False)
    token = fields.Char(required=False)

    is_oauth_onboarded = fields.Boolean(string="OAuth Onboarded", readonly=True, copy=False)
    is_phone_registered = fields.Boolean(string="Phone Registered", readonly=True, copy=False)
    is_webhook_subscribed = fields.Boolean(string="Webhook Subscribed", readonly=True, copy=False)
    show_disconnect = fields.Boolean(compute='_compute_show_disconnect')
    state = fields.Selection([
        ('connected', 'Connected'),
        ('disconnected', 'Not Connected'),
    ], compute='_compute_state', store=True, tracking=7)

    proxy_webhook_url = fields.Char(string="Proxy Webhook URL", readonly=True, copy=False, groups='whatsapp.group_whatsapp_admin')
    shared_webhook_secret = fields.Char(string="Shared Webhook Secret", readonly=True, copy=False,
                                        groups='whatsapp.group_whatsapp_admin',
                                        help="The secret used to validate incoming webhook calls from the proxy.")

    _check_app_credentials = models.Constraint(
        """CHECK(
            COALESCE(is_oauth_onboarded, false)
            OR (COALESCE(app_secret, '') != '' AND COALESCE(token, '') != '')
        )""",
        "App Secret and Access Token are required unless the account was onboarded through OAuth.",
    )

    @api.depends('is_webhook_subscribed', 'token')
    def _compute_show_disconnect(self):
        # Use a computed boolean instead of `token` directly because `token` is
        # restricted to WhatsApp admins and cannot be referenced by the view.
        for account in self:
            account.show_disconnect = bool(account.token or account.is_webhook_subscribed)

    @api.depends('is_oauth_onboarded', 'is_phone_registered', 'is_webhook_subscribed')
    def _compute_state(self):
        for account in self:
            if not account.is_oauth_onboarded:
                account.state = False
            elif account.is_phone_registered and account.is_webhook_subscribed:
                account.state = 'connected'
            else:
                account.state = 'disconnected'

    @api.model
    def _cron_refresh_onboarded_account_state(self):
        """Refresh the onboarded accounts against Meta.

        Nothing warns us when a phone number is deregistered or when another
        provider takes the webhook over, so without this the account keeps
        showing as connected until someone tests the connection.
        """
        for account in self.search([('is_oauth_onboarded', '=', True)]):
            was_connected = account.state == 'connected'
            try:
                account._refresh_account_state()
            except (RedirectWarning, WhatsAppError) as error:
                _logger.warning(
                    "Unable to refresh the state of the WhatsApp account %s [%s]: %s",
                    account.name, account.id, error,
                )
                continue
            if was_connected and account.state != 'connected':
                account._notify_connection_lost()

    def _refresh_account_state(self):
        """Store the registration and webhook state currently set on Meta."""
        self.ensure_one()
        self.write(WhatsAppOAuthApi(self)._fetch_account_state())

    def _get_connection_failure_reason(self):
        """Return why the account cannot exchange messages, empty when it can."""
        self.ensure_one()
        if not self.is_phone_registered and not self.is_webhook_subscribed:
            return _("The phone number is not registered and the webhook is not pointing to Odoo, so this account can neither send nor receive messages.")
        if not self.is_phone_registered:
            return _("The phone number is not registered, so this account can neither send nor receive messages.")
        if not self.is_webhook_subscribed:
            return _("Sending still works, but the webhook is not pointing to Odoo, so incoming messages will not reach this database.")
        return ''

    def _notify_connection_lost(self):
        """Warn the users in charge of the account that it stopped working.

        The state is only refreshed once a week, so nothing else tells them
        before a customer complains that nobody answered.
        """
        self.ensure_one()
        self.message_post(
            body=self._get_connection_failure_reason(),
            message_type='notification',
            partner_ids=self.notify_user_ids.partner_id.ids,
            subtype_xmlid='mail.mt_note',
        )

    def button_disconnect(self):
        """Disconnect the WhatsApp account.

        A failed unsubscribe on Meta leaves the account untouched rather than
        half disconnected. A failed proxy cleanup is only logged, that
        registration is dead anyway once Meta stops sending.
        """
        self.ensure_one()
        wa_api = WhatsAppOAuthApi(self)
        try:
            wa_api._unsubscribe_webhook()
        except WhatsAppError as error:
            raise ValidationError(str(error)) from error
        try:
            wa_api._unregister_proxy_webhook()
        except WhatsAppError as error:
            _logger.warning(
                "Unable to unregister the webhook of the WhatsApp account %s [%s] on the proxy: %s",
                self.name, self.id, error,
            )

        self.write({
            'active': False,
            'is_webhook_subscribed': False,
            'proxy_webhook_url': False,
            'shared_webhook_secret': False,
            'token': False,
        })

    def _configure_webhook(self):
        """Register and subscribe the webhook for this WhatsApp account."""
        self.ensure_one()
        wa_api = WhatsAppOAuthApi(self)

        if not all((
            self.proxy_webhook_url,
            self.shared_webhook_secret,
        )):
            proxy_webhook_data = wa_api._register_proxy_webhook()
            self.write({
                'proxy_webhook_url': proxy_webhook_data['webhook_url'],
                'shared_webhook_secret': proxy_webhook_data['shared_webhook_secret'],
            })

        wa_api._subscribe_webhook()
        self.is_webhook_subscribed = True

    def button_subscribe_webhook(self):
        """Manually subscribe to webhook, in case it failed during onboarding."""
        self.ensure_one()
        try:
            self._configure_webhook()
        except WhatsAppError as error:
            raise ValidationError(str(error)) from error
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("Successfully subscribed to webhook!"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def button_test_connection(self):
        """Refresh the onboarding flags before running the connection test.

        The phone number can be deregistered and the webhook subscription can be
        taken over without Meta notifying us, so the flags are re-read from Meta
        instead of keeping what was stored during the onboarding.
        """
        self.ensure_one()
        if self.is_oauth_onboarded:
            try:
                self._refresh_account_state()
            except WhatsAppError as error:
                raise ValidationError(str(error)) from error
        result = super().button_test_connection()
        # The base test only validates the credentials, it reports success even
        # when the phone is unregistered or the webhook was taken over.
        if self.is_oauth_onboarded and self.state != 'connected':
            result['params'].update({
                'type': 'warning',
                'message': self._get_connection_failure_reason(),
            })
        return result

    def action_open_registration_wizard(self):
        return {
            'name': _("Register Phone Number"),
            'view_mode': 'form',
            'res_model': 'whatsapp.register.phone',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_wa_account_id': self.id},
        }
