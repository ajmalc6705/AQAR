# -*- coding: utf-8 -*-

from odoo import models,fields,api,_

class SecurityDepositWizard(models.TransientModel):
    _name = 'security.deposit.wizard'
    _inherit = ['analytic.mixin']
    _description = "Security Deposit Wizard"

    rent_id = fields.Many2one('property.rent',string='Rent')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Tenant', required=True, readonly=True,)
    invoice_date = fields.Date('Accounting Date', default=fields.Date.today)
    reference = fields.Char(string='Reference')
    debit_account = fields.Many2one('account.account',string='Debit Account')
    credit_account = fields.Many2one('account.account',string='Credit Account')
    journal_id = fields.Many2one('account.journal',string='Journal')
    security_deposit = fields.Float(string='Security Deposit Amount', digits="Product Price")
    analytic_distribution = fields.Json("Analytic Distribution", store=True, )

    def create_entry(self):
        self.rent_id.created_security_entry = True
        # date = fields.date.today()
        debit_vals = {
            'name': self.reference,
            'account_id': self.debit_account.id,
            'partner_id': self.partner_id.id,
            'journal_id': self.journal_id.id,
            'date': self.invoice_date,
            'debit': self.security_deposit > 0.0 and self.security_deposit or 0.0,
            'credit': self.security_deposit < 0.0 and -self.security_deposit or 0.0,
            'analytic_distribution': self.analytic_distribution
        }
        credit_vals = {
            'name': self.reference,
            'account_id': self.credit_account.id,
            'partner_id': self.partner_id.id,
            'journal_id': self.journal_id.id,
            'date': self.invoice_date,
            'debit': self.security_deposit < 0.0 and -self.security_deposit or 0.0,
            'credit': self.security_deposit > 0.0 and self.security_deposit or 0.0,
            'analytic_distribution': self.analytic_distribution

        }
        vals = {
            'narration': self.reference,
            'move_type': 'entry',
            'ref': self.reference,
            'security_deposit_rent_id': self.rent_id.id,
            'journal_id': self.journal_id.id,
            'date': self.invoice_date,
            'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
        }
        move = self.env['account.move'].create(vals)
        move.action_post()
        self.rent_id.security_move_id = move.id
