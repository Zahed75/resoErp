{
    'name': 'CODA - Extension Number',
    'summary': 'Small module to handle extension number for CODA',
    'description': 'Module to import and handle the extension number for CODA.',
    'version': '1.0',
    'author': 'Odoo S.A.',
    'website': 'https://www.odoo.com/app/accounting',
    'category': 'Accounting/Localizations',
    'depends': ['l10n_be_coda'],
    'auto_install': True,
    'installable': True,
    'license': 'LGPL-3',
    'data': [
        'views/account_journal_views.xml',
    ],
}
