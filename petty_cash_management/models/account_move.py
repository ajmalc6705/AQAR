from odoo import models, fields, api, _
from datetime import datetime


class AccountMovePettyCashInherit(models.Model):
    _inherit = 'account.move'

    petty_cash_id = fields.Many2one(comodel_name='petty.cash.expense', string='Petty Cash Expense', readonly=True)

    # @api.onchange('state')
    # def onchange_state(self):
    #     if self.state == 'paid':
    #         # Perform custom actions here, such as sending an email notification or updating a custom field
    #         vendor_name = self.partner_id.name
    #         print(f"Vendor bill paid for {vendor_name}")

    def write(self, vals):
        res = super(AccountMovePettyCashInherit, self).write(vals)
        for record in self:
            if record.petty_cash_id and record.payment_state == 'paid':
                record.petty_cash_id.state = 'approved'
        return res
