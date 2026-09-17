# -*- coding: utf-8 -*-
{
    'name': 'Resort Cloud WhatsApp',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'WhatsApp templates, provider abstraction, chatbot rules, consent, webhooks',
    'description': """
Guest messaging over WhatsApp for the Resort Cloud SaaS product.

* rcloud.whatsapp.template — qweb-lite templates with {{placeholder}}
  rendering per record.
* rcloud.whatsapp.message — full in/out log on the partner chatter.
* Provider abstraction: rcloud.whatsapp.provider interface with a default
  log-only implementation, swappable per database through the
  rcloud.whatsapp.provider config parameter.
* Keyword chatbot rules with opt-out (STOP) handling and guest consent
  tracking on res.partner.
* Public webhook endpoints (/rcloud/whatsapp/webhook, /rcloud/whatsapp/status).
    """,
    'author': 'Syscomatic LLC / ProspireNext',
    'license': 'LGPL-3',
    'depends': ['rcloud_base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/rcloud_whatsapp_data.xml',
        'views/rcloud_whatsapp_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
