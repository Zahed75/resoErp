# -*- coding: utf-8 -*-
{
    'name': 'Resort Cloud PMS Accounting',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'Folio invoicing, deposits, guest folio PDF and tax invoice',
    'description': """
Accounting bridge for the Resort Cloud PMS.

* Post ONE customer invoice per folio (idempotent), one line per folio
  charge, stamped with the property analytic account.
* Record customer deposit payments against the folio invoice.
* Guest Folio Statement and Tax Invoice QWeb PDF reports.
    """,
    'author': 'Syscomatic LLC / ProspireNext',
    'license': 'LGPL-3',
    'depends': ['rcloud_pms', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'report/folio_reports.xml',
        'views/rcloud_pms_account_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
