# -*- coding: utf-8 -*-
{
    'name': 'Resort Cloud Base',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'Multi-property foundation: property model, analytic plumbing, mixins',
    'description': """
Foundation for the Resort Cloud SaaS product.

* rcloud.property — the property/branch dimension every operational and
  financial record carries.
* Property analytic account auto-provisioning (analytic plan "Property").
* rcloud.property.mixin — drop-in property dimension + company consistency
  for any model.
* Hotel staff / manager role groups.
    """,
    'author': 'Syscomatic LLC / ProspireNext',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'account'],
    'data': [
        'security/rcloud_security.xml',
        'security/ir.model.access.csv',
        'data/rcloud_data.xml',
        'views/rcloud_base_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
