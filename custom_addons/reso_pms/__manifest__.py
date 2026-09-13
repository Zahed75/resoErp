# -*- coding: utf-8 -*-
{
    'name': 'Reso PMS',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'Property Management System - data model foundation',
    'description': """
Reso Resort Management System - PMS Foundation
==================================================
Data-model foundation for a reusable, multi-property resort/hotel ERP.

Models: properties, room types, rooms, rate plans with seasonal pricing,
and bookings.
    """,
    'author': 'Syscomatic / ProspireNext',
    'website': 'https://prospirenext.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'product', 'account', 'crm', 'hr', 'web'],
    'data': [
        'security/reso_security.xml',
        'security/ir.model.access.csv',
        'data/reso_sequence_data.xml',
        'data/mail_server_data.xml',
        'views/reso_property_views.xml',
        'views/reso_room_views.xml',
        'views/reso_rate_plan_views.xml',
        'views/reso_booking_views.xml',
        'views/reso_maintenance_views.xml',
        'views/reso_whatsapp_views.xml',
        'views/reso_crm_lead_views.xml',
        'views/reso_document_views.xml',
        'views/reso_operations_views.xml',
        'views/reso_dashboard_action.xml',
        'views/reso_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'reso_pms/static/src/scss/reso_dashboard.scss',
            'reso_pms/static/src/js/reso_dashboard.js',
            'reso_pms/static/src/xml/reso_dashboard.xml',
            'reso_pms/static/src/js/reso_reports.js',
            'reso_pms/static/src/xml/reso_reports.xml',
        ],
    },
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
}
