# -*- coding: utf-8 -*-
{
    'name': 'Resort Cloud UI',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'Design tokens, PMS dashboard, app drawer, dark mode',
    'description': """
OWL-based PMS experience layer for Resort Cloud (spec Part 2 & 6):

* Material-inspired design tokens (light + dark) in _tokens.scss
* PMS Dashboard client action: KPIs with deltas vs prior period,
  today's movements with one-click check-in/out, room status grid,
  30-day trend, revenue-by-source, housekeeping progress
* rcloud.pms.daily.stat materialized stats + nightly cron
* Hamburger app drawer (systray) with search, grouped by category
* Property switcher respected by every widget
    """,
    'author': 'Syscomatic LLC / ProspireNext',
    'license': 'LGPL-3',
    'depends': ['rcloud_pms', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/rcloud_ui_data.xml',
        'views/rcloud_ui_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'rcloud_ui/static/src/scss/_tokens.scss',
            'rcloud_ui/static/src/scss/dashboard.scss',
            'rcloud_ui/static/src/scss/drawer.scss',
            'rcloud_ui/static/src/js/dashboard.js',
            'rcloud_ui/static/src/js/drawer.js',
            'rcloud_ui/static/src/xml/dashboard.xml',
            'rcloud_ui/static/src/xml/drawer.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
