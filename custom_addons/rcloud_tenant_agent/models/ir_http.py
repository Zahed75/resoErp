# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from werkzeug.wrappers import Response

from odoo import models
from odoo.http import abort, request

_logger = logging.getLogger(__name__)

# Paths that stay reachable while the tenant is suspended: the billing
# page itself, login/session endpoints and static assets.
ALLOWED_PATHS = (
    '/rcloud/billing',
    '/web/login',
    '/web/session',
    '/web/reset_password',
    '/web/assets',
    '/web/static',
    '/web/content',
    '/web/image',
    '/web/binary',
    '/rcloud/whatsapp',
)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _rcloud_blocked(cls, path, user, env=None):
        """True when the request must be replaced by the pause page.

        Suspended tenants keep working until the grace period expires;
        afterwards every non-exempt route answers 402. System
        administrators are never locked out. This helper is deliberately
        side-effect free so tests can call it directly.
        """
        if env is None:
            env = request.env
        Entitlement = env['rcloud_tenant_agent.entitlement'].sudo()
        state, grace_until = Entitlement.current_state()
        if state != 'suspended':
            return False
        if grace_until:
            grace = cls._rcloud_parse_dt(grace_until)
            if grace and grace > datetime.now():
                return False
        if user and user.has_group('base.group_system'):
            return False
        path = path or '/'
        if path == '/':
            return False
        return not any(
            path == allowed or path.startswith(allowed + '/')
            for allowed in ALLOWED_PATHS)

    @classmethod
    def _rcloud_parse_dt(cls, value):
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d'):
            try:
                return datetime.strptime(value, fmt)
            except (ValueError, TypeError):
                continue
        return None

    @classmethod
    def _rcloud_pause_response(cls):
        html = """
<!DOCTYPE html>
<html><head><title>Subscription Paused</title>
<style>
 body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background:
   linear-gradient(135deg, #0f2027, #203a43, #2c5364); color: #fff;
   display: flex; align-items: center; justify-content: center;
   min-height: 100vh; margin: 0; }}
 .card {{ background: rgba(255,255,255,.08); border: 1px solid
   rgba(255,255,255,.2); border-radius: 12px; padding: 40px 48px;
   max-width: 520px; text-align: center; }}
 h1 {{ margin-top: 0; }}
 a.btn {{ display: inline-block; margin-top: 16px; padding: 10px 24px;
   background: #f0a500; color: #203a43; border-radius: 6px;
   text-decoration: none; font-weight: 600; }}
</style></head><body>
 <div class="card">
  <h1>Subscription Paused</h1>
  <p>Your Resort Cloud workspace is temporarily suspended, most likely
     because a payment is overdue.</p>
  <p>No data has been lost. Reach out to your account manager or update
     your billing to resume service immediately.</p>
  <a class="btn" href="/rcloud/billing">View Billing Status</a>
 </div>
</body></html>"""
        return Response(html, status=402)

    @classmethod
    def _pre_dispatch(cls, rule, args):
        super()._pre_dispatch(rule, args)
        path = request.httprequest.path
        if cls._rcloud_blocked(path, request.env.user, env=request.env):
            _logger.info('rcloud: tenant suspended, blocking %s', path)
            abort(cls._rcloud_pause_response())
