# -*- coding: utf-8 -*-
{
    'name': 'Resort Cloud KYC',
    'version': '19.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'Guest KYC records, verification workflow, GDPR tooling, check-in guard',
    'description': """
Know-your-customer compliance for the Resort Cloud SaaS product.

* rcloud.kyc.record — passport / NID / driving licence / visa records with
  attachments, a strict verification state machine and a database-level
  guarantee of a single open record per partner and document type.
* Number masking: lists only ever show a masked document number; the raw
  value is restricted to KYC officers and hotel managers.
* Check-in guard: properties flagged kyc_required refuse check-in until a
  verified KYC record exists for the guest.
* GDPR export / erasure actions on res.partner.
    """,
    'author': 'Syscomatic LLC / ProspireNext',
    'license': 'LGPL-3',
    'depends': ['rcloud_base', 'rcloud_pms', 'mail', 'documents'],
    'data': [
        'security/rcloud_kyc_security.xml',
        'security/ir.model.access.csv',
        'data/rcloud_kyc_documents.xml',
        'views/rcloud_kyc_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
