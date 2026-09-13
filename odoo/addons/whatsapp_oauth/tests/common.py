import hashlib
import hmac

from contextlib import contextmanager
from unittest.mock import patch

from odoo.addons.whatsapp.tests.common import WhatsAppCommon
from odoo.addons.whatsapp.tools.whatsapp_api import DEFAULT_ENDPOINT, WhatsAppApi

PROXY_ENDPOINT = 'https://whatsapp.odoo.test/api/whatsapp/1'


class WhatsAppOAuthCommon(WhatsAppCommon):
    """ Bootstrap an account onboarded through Embedded Signup. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('whatsapp_oauth.endpoint', PROXY_ENDPOINT)
        cls.whatsapp_account_oauth = cls.env['whatsapp.account'].with_user(cls.user_wa_admin).create({
            'account_uid': 'waba_oauth_123',
            'app_uid': 'app_oauth_123',
            'is_oauth_onboarded': True,
            'is_phone_registered': True,
            'is_webhook_subscribed': True,
            'name': 'odoo oauth account',
            'notify_user_ids': cls.user_wa_admin.ids,
            'phone_uid': '111222333444',
            'proxy_webhook_url': f'{PROXY_ENDPOINT}/webhook/oauth_hook',
            'shared_webhook_secret': 'shared_secret_oauth',
            'token': 'oauth_access_token',
        })

    @contextmanager
    def mockWhatsappOAuthGateway(
        self,
        *,
        is_phone_registered=True,
        is_webhook_subscribed=True,
        access_token='new_access_token',
        phone_numbers=None,
        granular_scopes=None,
        proxy_webhook_data=None,
        register_phone_error=None,
    ):
        """Mock the WhatsApp gateway using OAuth-domain response values.

        The HTTP boundary remains mocked, so API response handling is still
        exercised.  Callers only provide the data relevant to their scenario,
        not endpoint paths or HTTP response envelopes.
        """
        def get_response(call_url):
            # The host is part of what the tests check, a Graph call must not reach the proxy.
            on_proxy = call_url.startswith(PROXY_ENDPOINT)
            on_graph = call_url.startswith(DEFAULT_ENDPOINT)
            if on_proxy and call_url.endswith('/get_access_token'):
                return {'content': {'access_token': access_token} if access_token else {}}
            if on_proxy and call_url.endswith('/debug_token'):
                return {'content': {'data': {'granular_scopes': granular_scopes or []}}}
            if on_proxy and call_url.endswith('/register_account'):
                return {'content': proxy_webhook_data or {
                    'shared_webhook_secret': 'new_shared_secret',
                    'webhook_url': f'{PROXY_ENDPOINT}/webhook/new_hook',
                }}
            if on_proxy and call_url.endswith('/unregister_account'):
                return {'content': {'success': True}}
            if on_graph and call_url.endswith('/phone_numbers'):
                return {'content': {'data': phone_numbers or []}}
            if on_graph and call_url.endswith('/register'):
                if register_phone_error:
                    return {'content': {
                        'error': {'code': 133005, 'message': register_phone_error},
                    }}
                return {'content': {'success': True}}
            if on_graph and call_url.endswith('/subscribed_apps'):
                return {'content': {'success': True}}
            if on_graph and call_url.endswith(f'/{self.whatsapp_account_oauth.phone_uid}'):
                return {'content': {
                    'status': 'CONNECTED' if is_phone_registered else 'PENDING',
                    'webhook_configuration': {
                        'whatsapp_business_account': self.whatsapp_account_oauth.proxy_webhook_url
                        if is_webhook_subscribed else 'https://another-provider.example.com/hook',
                    },
                }}
            self.fail(f'Unexpected WhatsApp API request: {call_url}')

        with (
            self.mockWhatsappGateway(),
            patch.object(WhatsAppApi, '_test_connection'),
            self.mockWhatsappHTTPResponse(get_response),
        ):
            yield

    def _get_proxy_signature(self, account, payload):
        return hmac.new(
            account.shared_webhook_secret.encode(),
            msg=payload.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()
