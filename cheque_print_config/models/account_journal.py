# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from datetime import date



class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # cheque date
    date_top = fields.Float(string="Cheque Top Margin", default=1.24)
    date_left = fields.Float(string="Cheque Left Margin", default=20.75)

    # bearer
    bearer_top = fields.Float(string="Bearer Top Margin", default=2.8)
    bearer_left = fields.Float(string="BearerTop Left Margin", default=0.95)
    # payee
    payee_top = fields.Float(string="Payee Top Margin", default=1.90)
    payee_left = fields.Float(string="Payee Left Margin", default=12.00)

    # amount in words
    amt_line1_top = fields.Float(string="Amount Words Top Margin", default=3.7)
    amt_line1_left = fields.Float(string="Amount Words Left Margin", default=0.2)
    amt_line1_width = fields.Integer(string="Width(no. of letters allowed)",
                                     default=44)
    amt_line2_top = fields.Float(string="Top Margin", default=4.7)
    amt_line2_left = fields.Float(string="Left Margin", default=0.2)

    # amount
    amt_top = fields.Float(string="Amount Top Margin", default=5.7)
    amt_left = fields.Float(string=" Amount Left Margin", default=21)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Cheque payment (payment, receipt)
    bearer = fields.Char(string='Check Bearer', tracking=True)
    cancelled_cheques = fields.One2many(comodel_name='account.cheque.cancelled',
                                        inverse_name='voucher_id',
                                        string='Cancelled Cheques',
                                        tracking=True, copy=False)
    cheque_no = fields.Char('Cheque No.', tracking=True, copy=False)
    transaction_type = fields.Selection([('manual', 'Manual'),
                                         ('pdc', 'PDC')
                                         ], string='Transaction Method', default='manual')
    pdc_state = fields.Selection([('pending', 'Post Dated'),
                                  ('cleared', 'Cleared'),
                                  ('bounced', 'Bounced')], string='PDC Status', copy=False)
    pdc_move_id = fields.Many2one(comodel_name='account.move', string='PDC Entry', copy=False)
    effective_date = fields.Date(string='Payment Date', copy=False,default=date.today())
    purpose_id = fields.Many2one(comodel_name='transfer.purpose', string='Transfer Purpose')
    purpose_transfer = fields.Char(string='Purpose of Transfer')
    cheque_state = fields.Selection([
        ('not_print', 'Not Printed'),
        ('printed', 'Cheque Printed'),
        ('re_print', 'Reprint Request'),
        ('cheque_reprint', 'Reprint Cheque'),
        ('reprint', 'Cheque Reprinted')],
        string="Cheque Status", copy=False, tracking=True, default='not_print')

    _sql_constraints = [
        ('cheque_no_uniq', 'CHECK(1=1)', 'This cheque no has been used before !')
    ]

    def send_to_head(self):
        """ Overrides the state to Open to Head Acc"""
        super(AccountMove, self).send_to_head()
        for record in self:
            if (record.transaction_type == 'pdc' and
                    record.effective_date <= record.date):
                raise UserError(" PDC Date must be greater than payment date")

    def action_cancel(self):
        if (self.cheque_no and self.move_type == 'in_receipt' and
                self.cheque_state in ('printed', 're_print')):
            self.cancelled_cheques = [(
                0, 0,
                {'cheque_number': self.cheque_no and self.cheque_no.strip()})]
            self.cheque_no = ""
        return super(AccountMove, self).action_cancel()

    @api.onchange('partner_id')
    def set_bearer(self):
        if not self.bearer and self.partner_id:
            self.bearer = self.partner_id.name
