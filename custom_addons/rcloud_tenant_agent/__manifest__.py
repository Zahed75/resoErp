# -*- coding: utf-8 -*-
{
    'name': 'Resort Cloud Tenant Agent',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'Per-tenant entitlement enforcement, control-plane phone-home, billing gate',
    'description': """
Tenant-side enforcement agent for the Resort Cloud SaaS product.

* Signed entitlement blob (HMAC-SHA256 over the tenant database uuid)
  cached in ir.config_parameter; the tenant NEVER self-unlocks.
* Cron phone-home to the control plane every 6 hours; unreachable means
  keep the cached state.
* ir.http gate: when the tenant is suspended past its grace period every
  non-public route answers a branded "Subscription Paused" page except
  login, assets and /rcloud/billing.
* Branded billing page with a retry-entitlement-check action.
    """,
    'author': 'Syscomatic LLC / ProspireNext',
    'license': 'LGPL-3',
    'depends': ['rcloud_base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/rcloud_billing_templates.xml',
        'data/rcloud_tenant_agent_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
