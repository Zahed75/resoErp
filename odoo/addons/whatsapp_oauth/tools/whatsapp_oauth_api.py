import json
import logging
import typing

from odoo.addons.whatsapp.tools.whatsapp_api import WhatsAppApi
from odoo.addons.whatsapp.tools.whatsapp_exception import WhatsAppError

_logger = logging.getLogger(__name__)

DEFAULT_PROXY_ENDPOINT = "https://whatsapp.api.odoo.com/api/whatsapp/1"


class AccountState(typing.TypedDict):
    is_phone_registered: bool  # the number is registered on the Cloud API and can message
    is_webhook_subscribed: bool  # Meta still forwards this account's events to our proxy


class OnboardedPhoneNumber(typing.TypedDict):
    display_phone_number: str  # the number as displayed to users
    id: str  # identifier of the phone number resource, kept as ``phone_uid``
    status: str  # connection status, ``CONNECTED`` once the number is registered
    verified_name: str  # business name associated with the number


def get_proxy_endpoint(env):
    """Return the WhatsApp proxy endpoint, overridable to test against another server."""
    return env['ir.config_parameter'].sudo().get_param('whatsapp_oauth.endpoint', DEFAULT_PROXY_ENDPOINT)


def get_proxy_error_message(env, error_code):
    """Return the message matching an error code returned by the proxy.

    The proxy does not know the language of the user, so it answers with a short
    code that the database turns into a translated message.
    """
    subscription_message = env._("The Enterprise subscription could not be validated.")
    return {
        'configuration_error': env._("WhatsApp authorization is temporarily unavailable."),
        'dbuuid_not_exist': subscription_message,
        'error_subscription': subscription_message,
        'invalid_request': env._("The WhatsApp proxy rejected the request."),
        'not_active_db': subscription_message,
        'not_enterprise': subscription_message,
        'not_prod_env': subscription_message,
        'subscription_error': subscription_message,
        'whatsapp_invalid_response': env._("WhatsApp returned an unexpected response, please try again later."),
        'whatsapp_unreachable': env._("WhatsApp could not be reached, please try again later."),
    }.get(error_code) or env._("The WhatsApp proxy returned an unknown error: %s", error_code)


class WhatsAppOAuthApi(WhatsAppApi):
    """WhatsApp API for the OAuth flow."""

    def _fetch_account_state(self) -> AccountState:
        """Return the registration and webhook state of the account on Meta.

        The number can be deregistered and the callback URI can be overridden by
        another provider without Meta notifying us, so both are read again.

        API Documentation:
        https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/override
        """
        response = self._api_requests(
            'GET',
            f'/{self.wa_account_id.phone_uid}',
            auth_type='bearer',
            params={'fields': 'status,webhook_configuration'},
        )
        response_json = response.json()
        webhook_configuration = response_json.get('webhook_configuration', {})
        return {
            'is_phone_registered': response_json.get('status') == 'CONNECTED',
            'is_webhook_subscribed': webhook_configuration.get('whatsapp_business_account') == self.wa_account_id.proxy_webhook_url,
        }

    def _prepare_error_response(self, response):
        """Turn a proxy error code into a message, Graph errors keep the base handling.

        Meta answers with a dict, ``{'error': {'message': ...}}``, while the proxy
        and the IAP subscription check answer with a plain code,
        ``{'error': 'not_enterprise'}``.
        """
        error = response.get('error')
        if isinstance(error, str):
            _logger.warning("WhatsApp proxy returned the error %s", error)
            return (get_proxy_error_message(self.wa_account_id.env, error), -1)
        return super()._prepare_error_response(response)

    def _fetch_and_store_access_token(self, authorization_code):
        """Exchange the authorization code for an access token, and use it for the next calls."""
        data = {'authorization_code': authorization_code, 'db_uuid': self._get_db_uuid()}
        response = self._api_requests(
            'POST',
            f'{get_proxy_endpoint(self.wa_account_id.env)}/get_access_token',
            data=data,
            endpoint_include=True,
        )
        access_token = response.json().get('access_token')
        if not access_token:
            raise WhatsAppError(self.wa_account_id.env._("The WhatsApp proxy did not return an access token."))
        self.token = access_token
        return self.token

    def _fetch_onboarded_phone_number_data(self, waba_id) -> OnboardedPhoneNumber:
        """Return the phone number that was most recently onboarded for the WABA.

        The Phone Numbers API returns phone numbers sorted by
        ``last_onboarded_time`` in descending order by default, so the first
        entry corresponds to the phone number that was just onboarded.

        API Documentation:
        https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/phone-numbers#get-all-phone-numbers
        """
        phone_number_fields = [
            'display_phone_number',
            'id',
            'status',
            'verified_name',
        ]
        response = self._api_requests(
            'GET',
            f'/{waba_id}/phone_numbers',
            auth_type='bearer',
            params={'fields': ','.join(phone_number_fields)},
        )
        phone_numbers = response.json().get('data', [])
        if not phone_numbers:
            raise WhatsAppError(self.wa_account_id.env._("The onboarded WhatsApp Business Account does not have any Cloud API phone numbers."))
        return phone_numbers[0]

    def _fetch_onboarded_waba_id(self):
        """Return the most recently onboarded WhatsApp Business Account ID.

        The Debug Token API returns every WABA that granted the application the
        ``whatsapp_business_management`` permission. Meta returns these WABA IDs
        in onboarding order, with the most recently onboarded account first, so
        the first ID is selected.

        API Documentation:
        https://developers.facebook.com/documentation/business-messaging/whatsapp/solution-providers/manage-accounts#get-shared-waba-id-with-access-token
        """
        data = {'db_uuid': self._get_db_uuid(), 'input_token': self.token}
        response = self._api_requests(
            'POST',
            f'{get_proxy_endpoint(self.wa_account_id.env)}/debug_token',
            data=data,
            endpoint_include=True,
        )
        response_json = response.json()
        for granular_scope in response_json.get('data', {}).get('granular_scopes', []):
            if granular_scope.get('scope') == 'whatsapp_business_management':
                target_ids = granular_scope.get('target_ids', [])
                if target_ids:
                    return target_ids[0]
        raise WhatsAppError(self.wa_account_id.env._("No WhatsApp Business Account was found for the access token."))

    def _get_db_uuid(self):
        """Return the UUID identifying this database on the proxy."""
        return self.wa_account_id.env['ir.config_parameter'].sudo().get_param('database.uuid')

    def _register_phone(self, pin):
        """Register the onboarded phone number to enable messaging.

        Until the phone number is registered, it cannot send or receive WhatsApp
        messages through the Cloud API.

        API Documentation:
        https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/registration
        """
        _logger.info("Register phone for account %s [%s]", self.wa_account_id.name, self.wa_account_id.id)
        data = {'messaging_product': 'whatsapp', 'pin': pin}
        response = self._api_requests(
            'POST',
            f'/{self.wa_account_id.phone_uid}/register',
            auth_type='bearer',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(data),
        )
        response_json = response.json()
        if response_json.get('success'):
            return True
        raise WhatsAppError(*self._prepare_error_response(response_json))

    def _register_proxy_webhook(self):
        """Register the database webhook on the proxy and return its configuration.

        The database supplies its webhook verification token for the proxy to store.
        The proxy generates a dedicated webhook URL. Both are used to subscribe the
        proxy endpoint to the WhatsApp Business Account. Once subscribed, the proxy
        validates Meta webhook signatures and forwards webhook events to the database.
        The subscription is performed by the database because it holds the business
        access token required by the Graph API.
        """
        _logger.info("Register database webhook on proxy for account %s [%s]", self.wa_account_id.name, self.wa_account_id.id)
        data = {
            'account_uid': self.wa_account_id.account_uid,
            'db_uuid': self._get_db_uuid(),
            'db_webhook_url': self.wa_account_id.callback_url,
            'webhook_verify_token': self.wa_account_id.webhook_verify_token,
        }
        response = self._api_requests(
            'POST',
            f'{get_proxy_endpoint(self.wa_account_id.env)}/register_account',
            data=data,
            endpoint_include=True,
        )
        return response.json()

    def _subscribe_webhook(self):
        """Subscribe the proxy webhook as the WhatsApp Business Account webhook.

        API Documentation:
        https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/override
        """
        _logger.info("Subscribe app to WhatsApp Business Account for account %s [%s]", self.wa_account_id.name, self.wa_account_id.id)
        data = {
            'override_callback_uri': self.wa_account_id.proxy_webhook_url,
            'verify_token': self.wa_account_id.webhook_verify_token,
        }
        response = self._api_requests(
            'POST',
            f'/{self.wa_account_id.account_uid}/subscribed_apps',
            auth_type='bearer',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(data),
        )
        response_json = response.json()
        if response_json.get('success'):
            return True
        raise WhatsAppError(*self._prepare_error_response(response_json))

    def _unregister_proxy_webhook(self):
        """Unregister the database webhook on the proxy"""
        _logger.info("Unregister database webhook on proxy for account %s [%s]", self.wa_account_id.name, self.wa_account_id.id)
        data = {
            'account_uid': self.wa_account_id.account_uid,
            'db_uuid': self._get_db_uuid(),
        }
        response = self._api_requests(
            'POST',
            f'{get_proxy_endpoint(self.wa_account_id.env)}/unregister_account',
            data=data,
            endpoint_include=True,
        )
        if not response.json().get('success'):
            raise WhatsAppError(self.wa_account_id.env._("The WhatsApp proxy did not unregister the webhook."))
        return True

    def _unsubscribe_webhook(self):
        """Unsubscribe the proxy webhook from the WhatsApp Business Account.

        API Documentation:
        https://developers.facebook.com/documentation/business-messaging/whatsapp/reference/whatsapp-business-account/subscribed-apps-api
        """
        _logger.info("Unsubscribe app from WhatsApp Business Account for account %s [%s]", self.wa_account_id.name, self.wa_account_id.id)
        response = self._api_requests(
            'DELETE',
            f'/{self.wa_account_id.account_uid}/subscribed_apps',
            auth_type='bearer',
        )
        response_json = response.json()
        if response_json.get('success'):
            return True
        raise WhatsAppError(*self._prepare_error_response(response_json))
