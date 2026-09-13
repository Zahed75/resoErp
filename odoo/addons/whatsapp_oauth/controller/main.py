import logging

from odoo.addons.whatsapp.controller.main import Webhook

_logger = logging.getLogger(__name__)


class WhatsAppOAuthWebhook(Webhook):
    """Handle webhook requests for OAuth-onboarded WhatsApp accounts."""

    def _check_signature(self, business_account):
        if not business_account:
            _logger.warning("Received a webhook for an unknown WhatsApp Business Account.")
            return False
        if business_account.is_oauth_onboarded:
            # The proxy re-signs the event with the secret shared at registration,
            # Meta's own signature uses the app secret, which only the proxy holds.
            return self._check_request_signature(business_account, 'IAP-Signature-256', 'shared_webhook_secret')
        return super()._check_signature(business_account)
