# -*- coding: utf-8 -*-
{
    'name': 'Resort Cloud PMS',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'Rooms, rate plans, reservations, availability engine, folio',
    'description': """
Core PMS for the Resort Cloud SaaS product.

* Multi-property room inventory with a structural overbooking guard:
  availability buckets per property/room-type/date protected by a
  database CHECK constraint and row-level locking.
* Strict reservation state machine (draft -> hold -> confirmed ->
  checked_in -> checked_out -> invoiced, cancelled/no_show) with
  chatter-logged, permissioned transitions.
* Rate calendar with per-night pricing, min-stay and closed-to-arrival.
* Folio and folio lines (accounting bridge lives in rcloud_pms_account).
    """,
    'author': 'Syscomatic LLC / ProspireNext',
    'license': 'LGPL-3',
    'depends': ['rcloud_base', 'mail', 'product'],
    'data': [
        'security/rcloud_pms_security.xml',
        'security/ir.model.access.csv',
        'data/rcloud_pms_data.xml',
        'data/rcloud_ops_data.xml',
        'views/rcloud_pms_views.xml',
        'views/rcloud_pms_menus.xml',
        'views/rcloud_ops_views.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
