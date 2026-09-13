# -*- coding: utf-8 -*-
{
    'name': 'Reso Ownership',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'Fractional Ownership & Investor Management',
    'description': """
Reso Ownership
==================
Fractional Ownership & Investor Management foundation for the Reso
Resort Management System.

Models: owner shareholding registry, approval-based share transfers, and
the owner income distribution engine (runs + lines).

Multi-property and multi-company aware. Accounting integration and the
owner portal are added in a later step.
    """,
    'author': 'Syscomatic / ProspireNext',
    'website': 'https://prospirenext.com',
    'license': 'LGPL-3',
    'depends': ['reso_pms'],
    'data': [
        'security/ownership_security.xml',
        'security/ir.model.access.csv',
        'data/ownership_sequence_data.xml',
        'views/owner_registry_views.xml',
        'views/share_transfer_views.xml',
        'views/distribution_run_views.xml',
        'views/ownership_menus.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
}
