{
    'name': 'WhatsApp OAuth',
    'category': 'Productivity/WhatsApp',
    'summary': 'WhatsApp Embedded Signup',
    'description': 'Adds Embedded Signup support for WhatsApp accounts.',
    'depends': ['whatsapp'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/ir_cron_data.xml',
        'wizard/whatsapp_register_phone_views.xml',
        'views/whatsapp_account_views.xml',
        'views/whatsapp_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'whatsapp_oauth/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'auto_install': True,
    'license': 'OEEL-1',
}
