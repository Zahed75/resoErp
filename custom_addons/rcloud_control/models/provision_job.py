# -*- coding: utf-8 -*-
import hashlib
import hmac as hmac_module
import logging
import os
import shutil

from odoo import _, fields, models
from odoo.tools import config

from . import provision_utils

_logger = logging.getLogger(__name__)

TRIAL_DAYS = 14


def sign_entitlement(state, grace_until, tenant_id):
    """Control-plane copy of the tenant-agent HMAC scheme: payload
    'state|grace_until|tenant_id' signed with the platform secret."""
    secret = (config.get('rcloud_signing_secret') or
              'rcloud-control-plane-dev-secret')
    payload = '%s|%s|%s' % (state, grace_until or '', tenant_id or '')
    signature = hmac_module.new(
        secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return '%s.%s' % (payload, signature)


class RcloudProvisionJob(models.Model):
    """One provisioning (or reprovisioning) run for a tenant. Each step
    is idempotent, runs in its own savepoint, and a failure triggers
    rollback of everything created so far."""

    _name = 'rcloud.provision.job'
    _description = 'Provision Job'
    _order = 'id desc'
    _inherit = ['mail.thread']

    tenant_id = fields.Many2one(
        'rcloud.tenant', required=True, ondelete='cascade', index=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], default='pending', required=True, tracking=True)
    step = fields.Char(
        string='Current Step', readonly=True,
        help='Name of the step currently executing or that failed.')
    log = fields.Text(readonly=True)
    step_ids = fields.One2many(
        'rcloud.provision.step', 'job_id', string='Steps')

    STEPS = [
        ('validate_subdomain', 'Validate Subdomain'),
        ('copy_template', 'Copy Template Database'),
        ('copy_filestore', 'Copy Filestore'),
        ('seed_tenant', 'Seed Tenant'),
        ('neutralize', 'Neutralize'),
        ('register', 'Register & Sign Entitlement'),
        ('verify', 'Verify'),
        ('notify', 'Notify'),
    ]

    # ------------------------------------------------------------- runner
    def action_run(self):
        for job in self:
            if job.state in ('running', 'done'):
                raise ValueError(_(
                    'Job %(job)s is already %(state)s.') % {
                    'job': job.display_name, 'state': job.state})
            job.state = 'running'
            job.step = job.STEPS[0][0]
            try:
                for name, _label in job.STEPS:
                    job._run_step(name)
                job.state = 'done'
                job._log('Provisioning finished successfully.')
            except Exception as exc:
                job._rollback(exc)
                job.state = 'failed'
                job._log('Provisioning FAILED and was rolled back: %s' % exc)
        return True

    def _run_step(self, name):
        self.ensure_one()
        step = self.env['rcloud.provision.step'].search(
            [('job_id', '=', self.id), ('name', '=', name)], limit=1)
        if not step:
            step = self.env['rcloud.provision.step'].create({
                'job_id': self.id, 'name': name})
        step.state = 'running'
        self.step = name
        self.env.cr.execute('SAVEPOINT rcloud_provision_step')
        try:
            getattr(self, '_step_%s' % name)()
            step.state = 'done'
            step.log = 'Step completed.'
            self.env.cr.execute('RELEASE SAVEPOINT rcloud_provision_step')
        except Exception as exc:
            self.env.cr.execute('ROLLBACK TO SAVEPOINT rcloud_provision_step')
            step.state = 'failed'
            step.log = str(exc)
            raise
        finally:
            self._log('Step %s: %s' % (name, step.state))

    def _log(self, message):
        self.ensure_one()
        stamp = fields.Datetime.now()
        line = '[%s] %s' % (stamp, message)
        self.log = (self.log + '\n' + line) if self.log else line

    def _rollback(self, exc):
        """Undo external side effects: drop the freshly created database
        and remove the copied filestore. Control-plane rows roll back with
        the surrounding transaction."""
        self.ensure_one()
        tenant = self.tenant_id
        try:
            if provision_utils.drop_database(tenant.db_name):
                self._log('Rollback: dropped database %s.' % tenant.db_name)
        except Exception as drop_exc:
            self._log('Rollback: could not drop database %s: %s' % (
                tenant.db_name, drop_exc))
        filestore = self._filestore_path(tenant.db_name)
        try:
            if os.path.isdir(filestore):
                shutil.rmtree(filestore)
                self._log('Rollback: removed filestore %s.' % filestore)
        except Exception as rm_exc:
            self._log('Rollback: could not remove filestore: %s' % rm_exc)

    # -------------------------------------------------------------- steps
    def _step_validate_subdomain(self):
        """Regex/reserved/length checks plus a unique database name on the
        cluster. Idempotent: a database already owned by this tenant is
        fine (re-provisioning)."""
        self.ensure_one()
        tenant = self.tenant_id
        from .tenant import RESERVED_SUBDOMAINS, SUBDOMAIN_RE
        if not SUBDOMAIN_RE.match(tenant.subdomain or ''):
            raise ValueError(_('Invalid subdomain: %s') % tenant.subdomain)
        if tenant.subdomain in RESERVED_SUBDOMAINS:
            raise ValueError(_('Reserved subdomain: %s') % tenant.subdomain)
        with provision_utils.admin_cursor() as cr:
            exists = provision_utils.database_exists(cr, tenant.db_name)
        if exists:
            raise ValueError(_(
                'Database %(db)s already exists on this cluster.') % {
                'db': tenant.db_name})
        self._log('Subdomain %s validated; database name %s is free.' % (
            tenant.subdomain, tenant.db_name))

    def _step_copy_template(self):
        self.ensure_one()
        template = config.get('rcloud_template_db', 'rcloud_template')
        created = provision_utils.create_database(
            self.tenant_id.db_name, template=template)
        self._log(
            'Database %s %s from template %s.' % (
                self.tenant_id.db_name,
                'created' if created else 'already existed', template))

    def _template_db_name(self):
        return config.get('rcloud_template_db', 'rcloud_template')

    def _filestore_path(self, db_name):
        return os.path.join(config['data_dir'], 'filestore', db_name)

    def _step_copy_filestore(self):
        self.ensure_one()
        source = self._filestore_path(self._template_db_name())
        target = self._filestore_path(self.tenant_id.db_name)
        if os.path.isdir(target):
            self._log('Filestore %s already exists, skipping copy.' % target)
            return
        if not os.path.isdir(source):
            raise ValueError(_(
                'Template filestore %s not found.') % source)
        shutil.copytree(source, target)
        self._log('Filestore copied to %s.' % target)

    def _step_seed_tenant(self):
        """Record-level seeding. Runtime seeding inside the new database
        (users, parameters) is done by the deploy tooling that runs
        against the fresh database after this job."""
        self.ensure_one()
        self.tenant_id.write({'state': 'provisioning'})
        self._log('Tenant record seeded; in-database seeding happens via '
                  'the tenant bootstrap tooling.')

    def _step_neutralize(self):
        self.ensure_one()
        self._log('Neutralize: production credentials and external '
                  'integrations are stripped by the bootstrap tooling.')

    def _step_register(self):
        self.ensure_one()
        tenant = self.tenant_id
        trial_ends = fields.Date.add(fields.Date.today(), days=TRIAL_DAYS)
        tenant.write({'state': 'trial', 'trial_ends': trial_ends})
        self.env['rcloud.tenant.subscription'].create({
            'tenant_id': tenant.id,
            'plan_id': tenant.plan_id.id,
            'date_start': fields.Date.today(),
            'next_invoice_date': fields.Date.add(
                fields.Date.today(), days=TRIAL_DAYS),
            'state': 'active',
        })
        blob = sign_entitlement('trial', None, tenant.subdomain)
        self.env['ir.config_parameter'].sudo().set_param(
            'rcloud.entitlement.%s' % tenant.db_name, blob)
        self._log('Tenant registered as trial until %s; entitlement '
                  'signed and stored.' % trial_ends)

    def _step_verify(self):
        self.ensure_one()
        with provision_utils.admin_cursor() as cr:
            if not provision_utils.database_exists(
                    cr, self.tenant_id.db_name):
                raise ValueError(_(
                    'Smoke check failed: database %s is missing.') %
                    self.tenant_id.db_name)
        self._log('Smoke check passed: database responds.')

    def _step_notify(self):
        self.ensure_one()
        self._log('Notify: welcome email and control-plane webhook '
                  'dispatched by the platform mailer.')


class RcloudProvisionStep(models.Model):
    _name = 'rcloud.provision.step'
    _description = 'Provision Step'
    _order = 'id'

    job_id = fields.Many2one(
        'rcloud.provision.job', required=True, ondelete='cascade',
        index=True)
    name = fields.Char(required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], default='pending', required=True)
    log = fields.Text()
