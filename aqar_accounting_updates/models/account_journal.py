from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    zakath = fields.Boolean(string='Zakath', help="Activate Zakath and to view the Zakath Amount")
    zakath_amount = fields.Float(string='Zakath Amount',
                                 help="(Current Assets - Current Liabilities) * 2.575 / 100",
                                 compute="_compute_zakath_amount")

    def _compute_zakath_amount(self):
        """ to calculate the zakath amount"""
        for rec in self:
            rec.zakath_amount = 0
            if rec.zakath:
                current_assets = self.env['account.account'].search(
                    [('account_type', '=', 'asset_current'), ('allow_for_zakath', '=', True)])
                total_assets = sum(current_assets.mapped('current_balance'))
                current_liabilities = self.env['account.account'].search(
                    [('account_type', '=', 'liability_current'), ('allow_for_zakath', '=', True)])
                total_liability = sum(current_liabilities.mapped('current_balance'))
                contibution = total_assets - total_liability
                rec.zakath_amount = contibution * 2.575 / 100
