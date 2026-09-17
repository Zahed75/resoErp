# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class RcloudUiController(http.Controller):

    @http.route('/dashboard', type='http', auth='user', website=False)
    def dashboard_redirect(self, **kw):
        """Product home: /dashboard opens the PMS dashboard directly."""
        action = request.env.ref('rcloud_ui.action_rcloud_dashboard', False)
        if not action:
            return request.redirect('/odoo')
        return request.redirect(f'/odoo/action-{action.id}')
