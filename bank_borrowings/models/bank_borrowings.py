# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.fields import Command


class BankBorrowings(models.Model):
    _name = 'bank.borrowings'
    _description = 'Bank Borrowings'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'journal_id'

    journal_id = fields.Many2one('account.journal', string='Bank Journal', domain=[('type', '=', 'bank')])
    loan_ref = fields.Char(string='Ref')
    type_id = fields.Many2one('borrowing.type', string='Type')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)
    from_date = fields.Date(string='From')
    maturity_date = fields.Date(string='Maturity Date')
    renewal_date = fields.Date(string='Renewal Date')
    days = fields.Integer(string='Days')
    interest_rate = fields.Float(string='Interest Rate')
    amount = fields.Float(string='Amount', tracking=True)
    balance_to_utilize = fields.Float(string='Balance to Utilize')
    account_id = fields.Many2one('res.partner.bank', string='Bank Name')
    bill_journal_id = fields.Many2one('account.journal', string=' Journal', domain=[('type', '=', 'purchase')])
    bank_ledger_account_id = fields.Many2one('account.account', string='Bank Ledger Account')
    bank_interest_account_id = fields.Many2one('account.account', string='Bank Interest Account')
    account_receivable_id = fields.Many2one('account.account', string='Account Payable',
                                            domain="[('account_type','=','liability_payable')]")
    account_balance = fields.Float(string='Account Balance')
    remarks = fields.Html(string='Remarks')
    bank_partner_id = fields.Many2one('res.partner', string='Bank Partner')
    installment_ids = fields.One2many('bank.installments', 'borrowing_bank_id', string='Installments')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('cancel', 'Cancel'),
    ], string='Status', copy=False, default="draft", index=True, tracking=True)

    @api.onchange('journal_id')
    def _onchange_journal(self):
        self.account_id = self.journal_id.bank_account_id.id
        self.account_balance = self.journal_id.current_statement_balance

    @api.onchange('amount', 'account_balance')
    def _onchange_amount(self):
        self.balance_to_utilize = self.account_balance + self.amount

    def action_approve(self):
        self.write({'state': 'confirm'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class BorrowingType(models.Model):
    _name = 'borrowing.type'
    _description = 'Borrowing Type'
    _rec_name = 'seq'

    name = fields.Char(string='Name')
    seq = fields.Char(string='Sequence', copy=False,
                      readonly=True,
                      index=True, default=lambda self: _('New'))

    def name_get(self):
        res = []
        for each in self:
            name = each.name
            if each.seq:
                res.append((each.id, name + ' [' + str(each.seq) + ']'))
            else:
                res.append((each.id, name))
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('seq', 'New') == 'New':
                vals['seq'] = self.env['ir.sequence'].next_by_code(
                    'bank.borrowing.type.sequence') or 'New'
        res = super(BorrowingType, self).create(vals_list)
        return res


class BankInstallments(models.Model):
    _name = 'bank.installments'
    _description = 'Bank Installments'

    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    days = fields.Integer(string='Days')
    due_date = fields.Date(string='Due Date')
    loan_amount = fields.Float(string='Loan Amount', digits='Product Price')
    interest_amount = fields.Float(string='Intrest Amount', digits='Product Price')
    total_amount = fields.Float(string='Total Amount', digits='Product Price')
    interest_percent = fields.Integer(string='Interest Percent')
    principle_repayment = fields.Integer(string='Principle Repayment', digits='Product Price')
    borrowing_bank_id = fields.Many2one('bank.borrowings', string='Bank Borrowings')
    is_create_move = fields.Boolean(string='Is move')
    move_id = fields.Many2one('account.move', string='Bill', readonly=True)

    @api.onchange('principle_repayment', 'interest_percent', 'days')
    def _onchange_loan(self):
        """ change the loan """
        if self.days > 0:
            interest_percent = self.interest_percent / 100
            self.interest_amount = ((self.loan_amount * interest_percent) / (365)) * self.days
        self.total_amount = self.principle_repayment + self.interest_amount

    def create_bill(self):
        """ create bill from each installment line"""
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.borrowing_bank_id.bank_partner_id.id,
            'invoice_date': self.from_date,
            'invoice_date_due': self.due_date,
            'journal_id': self.borrowing_bank_id.bill_journal_id.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Bank Ledger Account',
                    'display_type': 'product',
                    'price_unit': self.principle_repayment,
                    'quantity': 1,
                    'account_id': self.borrowing_bank_id.bank_ledger_account_id.id,
                    'tax_ids': [],

                }),
                Command.create({
                    'name': 'Bank Interest Account',
                    'display_type': 'product',
                    'price_unit': self.interest_amount,
                    'quantity': 1,
                    'account_id': self.borrowing_bank_id.bank_interest_account_id.id,
                    'tax_ids': [],
                })
            ]

        })
        for l in bill.line_ids:
            payable_line = l.filtered(lambda line: line.debit == 0)
            payable_line.account_id = self.borrowing_bank_id.account_receivable_id.id
        bill.action_post()
        self.is_create_move = True
        self.move_id = bill.id

    @api.onchange('from_date', 'to_date')
    def _onchange_dates(self):
        if self.from_date and self.to_date:
            self.days = (self.to_date - self.from_date).days + 1
