from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    extension_number = fields.Char(
        help="Required if you have multiple accounts sharing the same IBAN and same currency. It specifies the journal used for processing the corresponding coda file"
    )
