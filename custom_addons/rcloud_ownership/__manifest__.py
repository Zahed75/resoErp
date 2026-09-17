# -*- coding: utf-8 -*-
{
    'name': 'Resort Cloud Ownership',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'Fractional ownership: share classes, holdings, transfers, distributions',
    'description': """
Ownership / shared-equity layer for the Resort Cloud product.

* rcloud.owner — owner master data with KYC, banking and portal user link.
* rcloud.share.class — per-property share classes with distribution rules
  (gross room revenue, NOI, room subset, guaranteed-or-share) and
  entitlement percentages (management fee, reserve, withholding).
* rcloud.share.holding — append-only acquisition records; weighted unit
  positions replayed from holdings plus completed transfers.
* rcloud.share.transfer — 5-state transfer workflow with availability
  validation at completion.
* rcloud.distribution.run — period distribution engine: basis pulled from
  posted accounting analytic lines, per-class deductions, cent-exact
  rounding, journal entry posting and outbound payments.
* Owner portal (/my/ownership) with holdings, distributions, statements
  and a self-service report builder (PDF + CSV).
    """,
    'author': 'Syscomatic LLC / ProspireNext',
    'license': 'LGPL-3',
    'depends': ['rcloud_base', 'rcloud_pms', 'account', 'portal'],
    'data': [
        'security/rcloud_ownership_security.xml',
        'security/ir.model.access.csv',
        'data/rcloud_ownership_data.xml',
        'views/ownership_views.xml',
        'views/owner_report_templates.xml',
        'views/portal_templates.xml',
        'views/ownership_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
