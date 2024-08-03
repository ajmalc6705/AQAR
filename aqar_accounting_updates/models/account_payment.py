
from odoo import models, fields,api, _
from odoo.exceptions import ValidationError
# from werkzeug.wrappers import json


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    amount_dues = fields.Monetary(string='Amount Dues', compute='_compute_amount_dues',
                                  currency_field='company_currency_id',
                                  help="Current due of the customer", readonly=True)
    balance = fields.Float(string='Balance', compute="_compute_balance", help="Balance of the Journal")
    approval_status_1 = fields.Boolean(default=False, string="Approval Status One",
                                     help="Used to identify First approval status")
    approval_status_2 = fields.Boolean(default=False, string="Approval Status Two",
                                       help="Used to identify second approval status")

    def action_draft(self):
        self.approval_status_1 = False
        self.approval_status_2 = False
        return super(AccountPayment, self).action_draft()

    def update_approve_status_one(self):
        for rec in self:
            rec.approval_status_1 = True

    def update_approve_status_two(self):
        for rec in self:
            rec.approval_status_2 = True

    @api.onchange('partner_id', 'journal_id')
    def _compute_balance(self):
        """ compute the balance of the account related to the journal """
        for rec in self:
            rec.balance = 0
            if rec.journal_id.default_account_id:
                rec.balance = rec.journal_id.default_account_id.current_balance

    @api.depends('partner_id')
    def _compute_amount_dues(self):
        """ function to compute the balance of the partner"""
        for rec in self:
            rec.amount_dues = 0
            today = fields.Date.context_today(rec)
            for partner in rec.partner_id:
                total_overdue = 0
                total_due = 0
                for aml in partner.unreconciled_aml_ids:
                    is_overdue = today > aml.date_maturity if aml.date_maturity else today > aml.date
                    if aml.company_id == self.env.company and not aml.blocked:
                        total_due += aml.amount_residual
                        if is_overdue:
                            total_overdue += aml.amount_residual
                rec.amount_dues = total_due