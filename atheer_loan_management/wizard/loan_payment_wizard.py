# -*- coding: utf-8 -*-

from odoo import models, fields


class LoanPaymentWizard(models.Model):
    _name = 'loan.payment.wizard'
    _description = 'Loan Payment Wizard'

    loan_id = fields.Many2one('hr.loan', string='Loan')
    loan_installment_id = fields.Many2one('hr.loan.installments', string='Installments')
    amount = fields.Float('Amount', required=True, readonly=False, digits=(16, 3))
    debit_account = fields.Many2one('account.account', string='Debit Account')
    credit_account = fields.Many2one('account.account', string='Credit Account')
    journal_id = fields.Many2one('account.journal', string='Journal')

    def create_entry(self):
        self.loan_installment_id.paid = True
        date = fields.date.today()
        ref = 'Loan' + '-' + self.loan_id.employee_id.name
        debit_vals = {
            'account_id': self.debit_account.id,
            'journal_id': self.journal_id.id,
            'date': date,
            'debit': self.amount > 0.0 and self.amount or 0.0,
            'credit': self.amount < 0.0 and -self.amount or 0.0,
        }
        credit_vals = {
            'account_id': self.credit_account.id,
            'journal_id': self.journal_id.id,
            'date': date,
            'debit': self.amount < 0.0 and -self.amount or 0.0,
            'credit': self.amount > 0.0 and self.amount or 0.0,

        }
        vals = {
            'move_type': 'entry',
            'ref': ref,
            'journal_id': self.journal_id.id,
            'date': date,
            'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
        }
        move = self.env['account.move'].create(vals)
        move.action_post()
        self.loan_installment_id.paid_amount = self.amount
