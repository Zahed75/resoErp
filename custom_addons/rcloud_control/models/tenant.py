# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

SUBDOMAIN_RE = re.compile(r'^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$')
RESERVED_SUBDOMAINS = {
    'www', 'admin', 'api', 'app', 'mail', 'static', 'web', 'billing',
    'status', 'support', 'blog', 'docs',
}


class RcloudTenant(models.Model):
    """One customer database on the platform."""

    _name = 'rcloud.tenant'
    _description = 'Tenant'
    _order = 'id desc'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    subdomain = fields.Char(required=True, index=True)
    db_name = fields.Char(required=True, index=True)
    state = fields.Selection([
        ('provisioning', 'Provisioning'),
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], default='provisioning', required=True, tracking=True)
    plan_id = fields.Many2one('rcloud.plan', required=True, ondelete='restrict')
    property_count = fields.Integer(default=0)
    room_count = fields.Integer(default=0)
    user_count = fields.Integer(default=0)
    trial_ends = fields.Date()
    odoo_version = fields.Char(default='19.0')
    region = fields.Char(default='ap-southeast-1')
    company_id = fields.Many2one('res.company', string='Billing Company')
    subscription_ids = fields.One2many(
        'rcloud.tenant.subscription', 'tenant_id', string='Subscriptions')
    usage_ids = fields.One2many(
        'rcloud.tenant.usage', 'tenant_id', string='Usage History')
    job_ids = fields.One2many(
        'rcloud.provision.job', 'tenant_id', string='Provision Jobs')

    _subdomain_uniq = models.Constraint(
        'unique(subdomain)', 'The subdomain must be unique.')
    _dbname_uniq = models.Constraint(
        'unique(db_name)', 'The database name must be unique.')

    @api.constrains('subdomain')
    def _check_subdomain(self):
        for tenant in self:
            if not SUBDOMAIN_RE.match(tenant.subdomain or ''):
                raise ValidationError(_(
                    'Subdomain "%s" is invalid. Use 3-32 characters: '
                    'lowercase letters, digits and hyphens, starting and '
                    'ending with a letter or digit.') % tenant.subdomain)
            if tenant.subdomain in RESERVED_SUBDOMAINS:
                raise ValidationError(_(
                    'Subdomain "%s" is reserved.') % tenant.subdomain)

    def check_limits(self):
        """Raise when the tenant's current usage exceeds its plan."""
        for tenant in self:
            plan = tenant.plan_id
            checks = (
                ('properties', tenant.property_count, plan.max_properties),
                ('rooms', tenant.room_count, plan.max_rooms),
                ('users', tenant.user_count, plan.max_users),
            )
            for label, used, maximum in checks:
                if maximum and used > maximum:
                    raise ValidationError(_(
                        'Plan "%(plan)s" allows at most %(max)d %(label)s; '
                        'this tenant uses %(used)d. Upgrade the plan.') % {
                        'plan': plan.name, 'max': maximum,
                        'label': label, 'used': used,
                    })
        return True

    # ---------------------------------------------------------- operations
    def action_provision(self):
        self.ensure_one()
        job = self.env['rcloud.provision.job'].create({
            'tenant_id': self.id,
        })
        job.action_run()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rcloud.provision.job',
            'res_id': job.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_suspend(self):
        for tenant in self:
            if tenant.state not in ('trial', 'active', 'past_due'):
                raise ValidationError(_(
                    'Only trial, active or past-due tenants can be '
                    'suspended.'))
            tenant.state = 'suspended'

    def action_resume(self):
        for tenant in self:
            if tenant.state != 'suspended':
                raise ValidationError(_('Only suspended tenants can resume.'))
            tenant.state = 'past_due' if tenant.subscription_ids.filtered(
                lambda s: s.state == 'paused') else 'active'

    def action_extend_trial(self, days=14):
        for tenant in self:
            if tenant.state != 'trial':
                raise ValidationError(_('Only trial tenants can be extended.'))
            base = tenant.trial_ends or fields.Date.today()
            tenant.trial_ends = fields.Date.add(base, days=days)

    def action_change_plan(self, plan_id):
        """Swap plan and immediately enforce the new limits."""
        for tenant in self:
            tenant.plan_id = plan_id
            tenant.check_limits()

    def action_impersonate(self):
        """Support access: audit-log the impersonation, then open the
        tenant form. Actual login-as is performed by the platform
        operator tooling outside Odoo."""
        self.ensure_one()
        self.env['rcloud.impersonation.log'].create({
            'admin_user_id': self.env.user.id,
            'tenant_id': self.id,
            'started_on': fields.Datetime.now(),
            'note': 'Impersonation session opened from the control plane.',
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rcloud.tenant',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
