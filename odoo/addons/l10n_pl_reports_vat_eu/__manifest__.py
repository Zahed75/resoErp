{
    'name': 'Poland - VAT-UE Report',
    'version': '1.0',
    'author': 'Odoo S.A.',
    'description': """
Polish EC Sales and Purchase List with VAT-UE XML export
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_pl_reports'],
    'data': [
        'data/account_report_vat_eu.xml',
        'data/vat_eu_export_template.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
