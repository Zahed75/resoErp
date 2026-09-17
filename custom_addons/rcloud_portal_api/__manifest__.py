# -*- coding: utf-8 -*-
{
    'name': 'Resort Cloud Portal API',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'Public JSON API for the guest booking website',
    'description': """
Documented REST layer consumed by the Angular booking site (spec Part 16/18):

    GET  /rcloud/api/v1/properties
    POST /rcloud/api/v1/availability
    POST /rcloud/api/v1/bookings

The frontend never touches the ORM directly — all access flows through
these controllers into the availability engine and reservation lifecycle.
    """,
    'author': 'Syscomatic LLC / ProspireNext',
    'license': 'LGPL-3',
    'depends': ['rcloud_pms'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
