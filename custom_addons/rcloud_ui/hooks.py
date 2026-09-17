# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """Every internal user lands on the PMS dashboard after login (spec
    2.4) — unless they already chose a personal home action."""
    action = env.ref('rcloud_ui.action_rcloud_dashboard')
    users = env['res.users'].with_context(active_test=False).search([
        ('share', '=', False),
        ('action_id', '=', False),
    ])
    users.write({'action_id': action.id})
