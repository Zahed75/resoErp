# -*- coding: utf-8 -*-
{
    'name': 'Resort Cloud Control Plane',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'SaaS control plane: plans, tenants, provisioning pipeline, usage, impersonation audit',
    'description': """
Control plane for the Resort Cloud SaaS product (operator-side).

* rcloud.plan — sellable tiers with property/room/user limits.
* rcloud.tenant — one record per customer database, from provisioning to
  termination, with plan-limit enforcement.
* rcloud.provision.job — idempotent, per-step transactional provisioning
  pipeline (validate, copy template, filestore, seed, neutralize,
  register, verify, notify) with automatic rollback on failure.
* rcloud.tenant.usage — daily counters; rcloud.impersonation.log —
  immutable support-access audit trail.
    """,
    'author': 'Syscomatic LLC / ProspireNext',
    'license': 'LGPL-3',
    'depends': ['rcloud_base', 'sale_subscription'],
    'data': [
        'security/ir.model.access.csv',
        'views/rcloud_control_views.xml',
        'views/demo_seed.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
