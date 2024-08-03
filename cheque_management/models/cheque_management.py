# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _


class ChequeManagement(models.Model):
    _name = 'cheque.management'
    _description = "Cheque"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, readonly=True, default=lambda self: _('New'))
    partner_id = fields.Many2one(comodel_name='res.partner', string="Vendor")
    state = fields.Selection([('draft', 'Draft'), ('print', 'Print Cheque'), ('pending_signature', 'Pending Signature'),
                              ('signed', 'Signed'), ('submitted_to_client', 'Submitted to Client'),
                              ('cancel', 'Cancelled'), ], 'Status', readonly=True, required=True, copy=False,
                             tracking=True, default="draft")
    print_state = fields.Selection([('new', 'Check Print Available'), ('printed', 'Printed'), ], 'Status',
                                   readonly=True, required=True, copy=False, tracking=True, default="new")
    bearer = fields.Char(string='Check Bearer', tracking=True)
    cheque_no = fields.Char('Cheque No.', required=True, tracking=True, copy=False)
    effective_date = fields.Date(required=True, string='Cheque Date')
    payment_type = fields.Selection([
        ('vendor', 'Vendor Payment'),
        ('other', 'Other Payment'),
    ], string='Payment Type', default='vendor', required=True, tracking=True)

    amount = fields.Float(string='Amount', digits=(12, 3), tracking=True)
    date = fields.Date(string='Date', default=datetime.today())
    memo = fields.Char(string='Memo')
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 domain="[('id', 'in', available_journal_ids)]", )
    payment_id = fields.Many2one('account.payment', 'Payment')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', compute='_compute_currency_id',
                                  store=True, readonly=False, precompute=True,
                                  help="The payment's currency.")

    company_id = fields.Many2one(comodel_name='res.company', string='Company', compute='_compute_company_id',
                                 store=True, readonly=False, precompute=True, index=True,
                                 )
    check_amount_in_words = fields.Char(
        string="Amount in Words",
        store=True,
        compute='_compute_check_amount_in_words',
    )
    available_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        compute='_compute_available_journal_ids'
    )
    debit_account_id = fields.Many2one(comodel_name='account.account', string='Debit Account')
    move_id = fields.Many2one(comodel_name='account.move', string="Journal Entry", readonly=True)
    include_payee = fields.Boolean(string="Include payee")
    bill_ids = fields.Many2many('account.move', 'rel_move_id_cheque_id', 'move_id', 'cheque_id', string='Unpaid Bills')

    @api.constrains('partner_id')
    def _compute_unpaid_bills(self):
        for record in self:
            if record.partner_id:
                unpaid_bills = self.env['account.move'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('payment_state', 'in', ('not_paid', 'partial')),
                    ('state', '=', 'posted'),
                    ('move_type', '=', 'in_invoice')
                ])
                # print(unpaid_bills, 'Unpaid_bissla')
                record.bill_ids = unpaid_bills
            else:
                record.bill_ids = self.env['account.move']

    @api.onchange('partner_id')
    def set_bearer(self):
        if self.partner_id:
            self.bearer = self.partner_id.cheque_bearer_name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                if vals.get('effective_date'):
                    vals['name'] = self.env['ir.sequence'].with_context(
                        ir_sequence_date=vals['effective_date']).next_by_code('cheque.management') or _('New')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('cheque.management') or _('New')
        return super().create(vals_list)

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for pay in self:
            pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id

    @api.depends('journal_id')
    def _compute_company_id(self):
        for move in self:
            company_id = move.journal_id.company_id or self.env.company
            if company_id != move.company_id:
                move.company_id = company_id

    @api.depends('company_id')
    def _compute_available_journal_ids(self):
        """
        Get all journals having at least one payment method for inbound/outbound depending on the payment_type.
        """
        journals = self.env['account.journal'].search([
            ('company_id', 'in', self.company_id.ids), ('type', '=', 'bank')
        ])
        self.available_journal_ids = journals.filtered(
            lambda j: j.company_id == self.company_id and j.outbound_payment_method_line_ids.ids != [])

    @api.depends('currency_id', 'amount')
    def _compute_check_amount_in_words(self):
        for pay in self:
            if pay.currency_id:
                pay.check_amount_in_words = pay.currency_id.amount_to_text(pay.amount)
            else:
                pay.check_amount_in_words = False

    def approve(self):
        self.state = 'pending_signature'

    def sign(self):
        for rec in self:
            if rec.payment_id:
                rec.payment_id.action_post()
            elif rec.move_id:
                rec.move_id.action_post()
        self.state = 'signed'

    def confirm(self):
        for rec in self:
            if rec.payment_type == 'vendor':
                self.payment_id = self.env['account.payment'].create({
                    # 'name': self.name,
                    'partner_id': rec.partner_id.id,
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'transaction_type': 'manual',
                    # 'effective_date': rec.effective_date,
                    'cheque_no': rec.cheque_no,
                    'bearer': rec.bearer,
                    'journal_id': rec.journal_id.id,
                    'date': rec.effective_date,
                    'ref': rec.memo,
                    'amount': rec.amount,
                    'include_payee': rec.include_payee
                })
            elif rec.payment_type == 'other':
                # Get the company related to the journal
                company_id = rec.journal_id.company_id
                # Fetch the Outstanding Payments Account from company settings
                outstanding_payments_account_id = company_id.account_journal_payment_credit_account_id.id

                journal_rec = self.env['account.move'].create({
                    'move_type': 'entry',
                    'ref': 'OtherPayment' + '-' + rec.name,
                    'date': rec.effective_date,
                    'journal_id': rec.journal_id.id,
                    'cheque_no': rec.cheque_no,
                    'line_ids': [
                        (0, 0, {
                            'name': 'OtherPayment' + '-' + rec.name + '-' + rec.cheque_no + '-' + rec.memo,
                            'debit': rec.amount,
                            'credit': 0,
                            'account_id': rec.debit_account_id.id,
                        }),
                        (0, 0, {
                            'name': 'OtherPayment' + '-' + rec.name + '-' + rec.cheque_no + '-' + rec.memo,
                            'debit': 0,
                            'credit': rec.amount,
                            # 'account_id': rec.journal_id.default_account_id.id,
                            # 'account_id': rec.journal_id.outbound_payment_method_line_ids and rec.journal_id.outbound_payment_method_line_ids[0].payment_account_id.id or rec.journal_id.default_account_id.id,
                            'account_id': rec.journal_id.outbound_payment_method_line_ids and
                                          rec.journal_id.outbound_payment_method_line_ids[
                                              0].payment_account_id.id or outstanding_payments_account_id,
                        }),
                    ],
                })
                if journal_rec:
                    rec.move_id = journal_rec.id
            rec.state = 'print'

    def submit_to_client(self):
        for rec in self:
            rec.state = 'submitted_to_client'

    def print_check(self):
        self.print_state = 'printed'
        return self.payment_id.print_check_v()

    def button_payment(self):
        self.ensure_one()
        return {
            'name': _("Payment"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': self.payment_id.id,
        }

    def cancel(self):
        for rec in self:
            # rec.state = 'cancel'
            if rec.move_id:
                rec.move_id.button_draft()
                rec.move_id.button_cancel()
        view = self.env.ref('petty_cash_management.cancel_reason_form_view')
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Cancel Reason',
            'res_model': 'cancel.reason',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [[view.id, 'form']],
            'target': 'new',
            'binding_model_id': self._context.get('active_model'),
        }
        return action

    def reset_to_draft(self):
        self.state = 'draft'


class AccountMoveCheque(models.Model):
    _inherit = 'account.move'

    cheque_id = fields.Many2one('cheque.management')


class PaymentSignature(models.Model):
    _inherit = 'account.payment'

    signature = fields.Image(string='Signature')
    received_by = fields.Char(string='Received by')
    attachment = fields.Binary('Attachment',
                               help=' You can attach the ID proof of the receiver or the copy of cheque. This will be visible in the payment receipt')
    include_payee = fields.Boolean(string="Include payee?")

    def _get_responsible_for_approval(self):

        group = self.env.ref('cheque_management.group_receive_pdc_notifications').users
        return group.ids

    def activity_update(self):
        for rec in self:
            responsible_users = rec.sudo()._get_responsible_for_approval()
            note = _(
                'PDC Cheque Date created by %(user)s on %(create_date)s,',
                user=rec.create_uid.name,
                create_date=rec.date,
            )
            if responsible_users:
                for responsible_user in responsible_users:
                    rec.activity_schedule(
                        'cheque_management.mail_activity_pdc_receiving_notification',
                        note=note,
                        user_id=responsible_user,
                        date_deadline=rec.date)

    def action_post(self):
        res = super(PaymentSignature, self).action_post()
        for rec in self:
            if rec.transaction_type == 'pdc':
                rec.activity_update()
        return res
