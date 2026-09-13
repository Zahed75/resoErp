# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Belgian Registered Cash Register (Transition from V1 to V2)',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Helps the transition between the Blackbox V1 and V2 for the Belgian Registered Cash Register.',
    'depends': ['pos_blackbox_be', 'l10n_be_pos_blackbox'],
    'post_init_hook': 'migrate_data_from_v1_to_v2',
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}
