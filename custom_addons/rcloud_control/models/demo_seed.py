# -*- coding: utf-8 -*-
import random

from odoo import api, fields, models, _

DEMO_PREFIX = 'Demo '

TENANT_SPECS = (
    # name, subdomain, state, plan name
    ('Seaside Grand Hotel', 'seasidegrand', 'active', 'Resort'),
    ('Riverine Boutique Stay', 'riverine', 'active', 'Boutique'),
    ('Golden Dunes Resort', 'goldendunes', 'active', 'Resort'),
    ('Lakeview Eco Lodge', 'lakeview', 'active', 'Boutique'),
    ('Palm Court Hotel', 'palmcourt', 'active', 'Starter'),
    ('Coral Bay Retreat', 'coralbay', 'trial', 'Boutique'),
    ('Highland Inn', 'highland-inn', 'trial', 'Starter'),
    ('Misty Valley Resort', 'mistyvalley', 'past_due', 'Resort'),
    ('Azure Sky Hotel', 'azuresky', 'suspended', 'Boutique'),
    ('Old Town Heritage Lodge', 'oldtown', 'terminated', 'Starter'),
    ('Blue Lagoon Resort', 'bluelagoon', 'provisioning', 'Resort'),
    ('Sunset Cliff Resort', 'sunsetcliff', 'active', 'Enterprise'),
)
REGIONS = ('ap-southeast-1', 'ap-south-1', 'eu-west-1', 'us-east-1')


class RcloudTenant(models.Model):
    """One-click demo data seed (menu: Control Plane → Generate Demo
    Data). Covers every control-plane model — plans, tenants,
    subscriptions, usage snapshots, provision jobs and impersonation
    logs. Idempotent: bails out when demo records already exist."""

    _inherit = 'rcloud.tenant'

    # ------------------------------------------------------------ entry
    @api.model
    def _load_demo_data(self):
        if self.search([('name', '=like', DEMO_PREFIX + '%')], limit=1):
            return self._demo_notification(
                _('Demo data was already generated — nothing was created.'),
                'warning')
        rng = random.Random(20260920)
        today = fields.Date.today()
        counts = {}
        company = self.env.company

        # ------------------------------------------------------------- plans
        Plan = self.env['rcloud.plan'].sudo()
        plan_specs = (
            ('Starter', 4990.0, 'monthly', 1, 20, 5),
            ('Boutique', 14900.0, 'monthly', 2, 60, 15),
            ('Resort', 39900.0, 'monthly', 5, 150, 40),
            ('Enterprise', 89900.0, 'yearly', 15, 500, 100),
        )
        plans = {}
        for name, price, period, props, rooms, users in plan_specs:
            plan = Plan.search([('name', '=', name)], limit=1)
            if not plan:
                plan = Plan.create({
                    'name': name,
                    'monthly_price': price,
                    'billing_period': period,
                    'max_properties': props,
                    'max_rooms': rooms,
                    'max_users': users,
                    'included_modules':
                        'rcloud_pms, rcloud_ownership, rcloud_portal_api',
                })
            plans[name] = plan
        counts['rcloud.plan'] = len(plans)

        # ----------------------------------------------------------- tenants
        Tenant = self.env['rcloud.tenant'].sudo()
        tenants = []
        for name, subdomain, state, plan_name in TENANT_SPECS:
            plan = plans[plan_name]
            tenants.append(Tenant.create({
                'name': DEMO_PREFIX + name,
                'subdomain': subdomain,
                'db_name': 'rcloud_%s' % subdomain.replace('-', ''),
                'state': state,
                'plan_id': plan.id,
                'property_count': rng.randint(1, plan.max_properties),
                'room_count': max(1, int(plan.max_rooms * rng.uniform(
                    0.3, 0.9))),
                'user_count': max(1, int(plan.max_users * rng.uniform(
                    0.3, 0.9))),
                'trial_ends': fields.Date.add(
                    today, days=rng.randint(-10, 14))
                if state in ('trial', 'provisioning') else False,
                'odoo_version': '19.0',
                'region': rng.choice(REGIONS),
                'company_id': company.id,
            }))
        counts['rcloud.tenant'] = len(tenants)

        # ----------------------------------------------------- subscriptions
        Subscription = self.env['rcloud.tenant.subscription'].sudo()
        sub_states = {
            'active': 'active', 'trial': 'active', 'past_due': 'paused',
            'suspended': 'paused', 'terminated': 'cancelled',
            'provisioning': 'active',
        }
        subs = []
        for tenant, spec in zip(tenants, TENANT_SPECS):
            _name, _sub, state, plan_name = spec
            start = fields.Date.subtract(
                today, days=rng.randint(5, 340))
            subs.append(Subscription.create({
                'tenant_id': tenant.id,
                'plan_id': plans[plan_name].id,
                'date_start': start,
                'next_invoice_date': fields.Date.add(
                    start, months=rng.randint(1, 6)),
                'state': sub_states[state],
            }))
            # A couple of long-running tenants show a superseded plan.
            if state == 'active' and rng.random() < 0.4:
                older = [p for p in plan_specs if p[1] < plans[plan_name]
                         .monthly_price]
                if older:
                    subs.append(Subscription.create({
                        'tenant_id': tenant.id,
                        'plan_id': plans[rng.choice(older)[0]].id,
                        'date_start': fields.Date.subtract(
                            today, days=rng.randint(300, 700)),
                        'next_invoice_date': fields.Date.subtract(
                            today, days=rng.randint(200, 280)),
                        'state': 'cancelled',
                    }))
        counts['rcloud.tenant.subscription'] = len(subs)

        # ------------------------------------------------------ usage stats
        Usage = self.env['rcloud.tenant.usage'].sudo()
        usage_rows = []
        for tenant in tenants:
            if tenant.state in ('terminated', 'provisioning'):
                continue
            base_rooms = tenant.room_count
            base_users = tenant.user_count
            for days_ago in range(2, 10):
                usage_rows.append({
                    'tenant_id': tenant.id,
                    'date': fields.Date.subtract(today, days=days_ago),
                    'rooms': base_rooms,
                    'users': max(1, base_users + rng.randint(-2, 2)),
                    'reservations': rng.randint(0, base_rooms),
                    'storage_mb': rng.randint(200, 4000),
                })
        Usage.create(usage_rows)
        counts['rcloud.tenant.usage'] = len(usage_rows)

        # ----------------------------------------------------- provision jobs
        Job = self.env['rcloud.provision.job'].sudo()
        Step = self.env['rcloud.provision.step'].sudo()
        by_state = {}
        for tenant in tenants:
            by_state.setdefault(tenant.state, []).append(tenant)
        jobs = []
        steps = []

        def add_job(tenant, state, step_states):
            job = Job.create({
                'tenant_id': tenant.id,
                'state': state,
                'step': step_states[-1][0] if step_states else False,
                'log': '[%s] Demo provisioning run (%s).' % (
                    fields.Datetime.now(), tenant.subdomain),
            })
            jobs.append(job)
            for step_name, step_state in step_states:
                steps.append({
                    'job_id': job.id,
                    'name': step_name,
                    'state': step_state,
                    'log': 'Step %s.' % step_state,
                })
            return job

        step_names = [s[0] for s in Job.STEPS]
        for tenant in by_state.get('trial', []):
            add_job(tenant, 'done', [
                (n, 'done') for n in step_names])
        for tenant in by_state.get('active', [])[:2]:
            add_job(tenant, 'done', [
                (n, 'done') for n in step_names])
        for tenant in by_state.get('terminated', []):
            add_job(tenant, 'done', [
                (n, 'done') for n in step_names])
        for tenant in by_state.get('provisioning', []):
            add_job(tenant, 'pending', [])
        for tenant in by_state.get('past_due', [])[:1]:
            add_job(tenant, 'failed', (
                [('validate_subdomain', 'done'),
                 ('copy_template', 'failed')] +
                [(n, 'pending') for n in step_names[2:]]
            ))
        Step.create(steps)
        counts['rcloud.provision.job'] = len(jobs)
        counts['rcloud.provision.step'] = len(steps)

        # ------------------------------------------------- impersonation log
        Log = self.env['rcloud.impersonation.log'].sudo()
        admin = self.env.ref('base.user_admin')
        impersonated = tenants[:6]
        logs = []
        for i, tenant in enumerate(impersonated):
            started = fields.Datetime.subtract(
                fields.Datetime.now(), days=3 * i + 1, hours=rng.randint(
                    0, 8))
            vals = {
                'admin_user_id': admin.id,
                'tenant_id': tenant.id,
                'started_on': started,
                'note': 'Demo support session for %s.' % tenant.name,
            }
            if i % 3 != 2:  # most sessions are closed
                vals['ended_on'] = fields.Datetime.add(
                    started, minutes=rng.randint(5, 90))
            logs.append(vals)
        Log.create(logs)
        counts['rcloud.impersonation.log'] = len(logs)

        message = _('Created: %s.') % ', '.join(
            '%d %s' % (n, model) for model, n in counts.items())
        return self._demo_notification(message)

    # --------------------------------------------------------- notification
    def _demo_notification(self, message, notif_type='success'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Control plane demo data'),
                'message': message,
                'type': notif_type,
                'sticky': False,
            },
        }
