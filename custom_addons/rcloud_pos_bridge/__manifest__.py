# -*- coding: utf-8 -*-
{
    'name': 'Resort Cloud POS Bridge',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'Post POS charges (restaurant/bar/spa/retail) to the guest folio',
    'description': """
POS room-charge bridge (spec Part 4.2): a POS sale charged to a room
becomes rcloud.folio.line records (source pos) on the guest folio and is
settled with the folio at checkout. One guest record, one folio.
    """,
    'author': 'Syscomatic LLC / ProspireNext',
    'license': 'LGPL-3',
    'depends': ['rcloud_pms_account', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_bridge_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
