# -*- coding: utf-8 -*-

from odoo import models, fields, api,_


class BankGuarantee(models.Model):
    _name = 'bank.guarantee'
    _description = 'Bank Guarantee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'seq'

    name = fields.Char(string='Name', help='name of the guarantee')
    transaction = fields.Char(string='Transaction', help='name of the guarantee')
    seq = fields.Char(string='Sequence No', copy=False,
                      readonly=True,
                      index=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Partner')
    ref = fields.Char(string='Guarantee Id')
    bgno = fields.Char(string='Bgno')
    bank_id = fields.Many2one('res.bank', string='Bank Name')
    branch_name = fields.Char(string='Branch Name')
    cheque_no = fields.Char('Cheque No.', tracking=True, copy=False)
    cheque_date = fields.Date(string='Cheque Date', tracking=True)
    cheque_bank = fields.Char(string='Cheque Bank')
    expiry_date = fields.Date(string='Expiry Date')
    issue_date = fields.Date(string='Issue Date')
    return_date = fields.Date(string='Return Date')
    doc_date = fields.Date(string='Doc Date')
    return_value = fields.Float(string='Return Value',tracking=True)
    return_bool = fields.Boolean(string='Return')
    remarks = fields.Html(string='Remarks')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('return', 'Return'),
        ('cancel', 'Cancel'),
    ], string='Status', copy=False, default="draft", index=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('seq', 'New') == 'New':
                vals['seq'] = self.env['ir.sequence'].next_by_code(
                    'bank.guarantee.sequence') or 'New'
        res = super(BankGuarantee, self).create(vals_list)
        return res

    def action_approve(self):
        self.write({'state': 'confirm'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_return(self):
        self.write({'state': 'return'})
        self.return_bool = True
