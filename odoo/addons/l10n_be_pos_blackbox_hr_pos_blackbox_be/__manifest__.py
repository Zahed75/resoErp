# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Belgian Registered Cash Register (Transition from V1 to V2) HR',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'depends': ['l10n_be_pos_blackbox_pos_blackbox_be', 'pos_hr'],
    'post_init_hook': 'migrate_data_from_v1_to_v2_employee',
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}
