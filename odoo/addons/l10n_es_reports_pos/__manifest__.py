# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Spain - Accounting Reports Libro IVA PoS',
    'countries': ['es'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Point of Sale support for the Spanish VAT record books (Libros Registro de IVA).
    """,
    'depends': [
        'l10n_es_reports',
        'point_of_sale',
    ],
    'installable': True,
    'auto_install': True,
    'website': 'https://www.odoo.com/app/accounting',
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}
