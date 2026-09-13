{
    'name': 'Germany - Elster Tax Submission',
    'author': 'Odoo S.A.',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Submit UStVA (VAT advance returns) to ELSTER',
    'description': """
Electronic submission of German UStVA to the
Finanzamt via the ELSTER system.""",
    'depends': ['l10n_de_reports'],
    'data': [
        'views/report_export_template.xml',
    ],
    'demo': ['demo/company.xml'],
    'license': 'OEEL-1',
}
