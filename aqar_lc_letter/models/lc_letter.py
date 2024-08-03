# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class LCLetter(models.Model):
    _name = "lc.letter"
    _description = 'Letter of credit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Doc Reference", readonly=True,copy=False, required=True, default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.company)
    lc_type = fields.Many2one('lc.type', string="LC Type")
    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('lc_open', "LC OPEN"),
            ('assign_po', "Assign PO"),
            ('acceptance', "LC Acceptance"),
            ('payment', "LC Payment"),
            ('ltr', "LTR"),
            ('ltr_payment', "LTR Payment"),
            ('cancel', "Cancel"),
        ],
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='draft')
    lc_ref = fields.Char(string='LC Reference')
    supplier = fields.Many2one('res.partner', string="Supplier")
    date = fields.Date("Date")
    lc_ref_date = fields.Date("LC Ref Date")
    # supplier_address = fields.related('employer.master', required=True)
    # supplier_bank_name = fields.related('employer.master', required=True)
    iban_code = fields.Char(string='IBAN Code')
    swift_Code = fields.Char(string='Swift Code')
    advising_bank_code = fields.Char(string='Advising Bank Code')
    advising_bank_number = fields.Char(string='Advising Bank A/C Number')
    currency_id = fields.Many2one('res.currency', string='Currency',related='company_id.currency_id', tracking=True, )
    lc_value = fields.Integer(string="LC Value", copy=False)
    lc_increment = fields.Integer(string="LC Increment %", copy=False)
    lc_max_val = fields.Integer(string="LC Max Val", compute="compute_max_val")
    lc_payment_terms = fields.Html(string='Payment Terms')
    shipment_last_date = fields.Date("Shipment Last Date", copy=False)
    shipment_by = fields.Char(string='Shipment By')
    shipment_from = fields.Char(string='Shipment From')
    shipment_to = fields.Char(string='Shipment To')
    lc_exp_date = fields.Date("LC expiry Date")
    new_ltr_ref_date = fields.Date("New LTR Ref Date")
    valid_place = fields.Char(string='Valid Place')
    partial_shipment = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')], default="yes", string='Partial Shipment')
    transshipment = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')], default="yes", string='Transshipment')
    completed = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')], default="yes", string='Completed')
    multi_modal_shipment = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')], default="yes", string='Multi Modal Shipment')
    lc_description = fields.Text('LC Description', copy=False)
    trade_terms = fields.Html('Trade Terms')
    bank_name = fields.Char(string='Bank Name')
    pending_lc_value = fields.Integer(string="Pending LC Value",
                                      compute="compute_pending_lc_value")
    total_assign_value = fields.Monetary(string="Total Assign Value", currency_field='currency_id', compute="compute_total_assign_value")
    # exchange_rate = fields.Integer(string='Exchange Rate')
    acceptance_value = fields.Integer(string='Acceptance Value')
    new_ltr_val = fields.Integer(string='New LTR Value')
    acceptance_value_omr = fields.Integer(string='Acceptance Value OMR')
    due_date = fields.Date(string='Due Date')
    acceptance_date = fields.Date(string='Acceptance Date', copy=False)
    new_ltr_due_date = fields.Date(string='New LTR Due Date', copy=False)
    lading_bill_no = fields.Integer(string='Lading Bill No')
    new_ltr_ref_no = fields.Integer(string='New LTR Ref No')
    lading_bill_date = fields.Datetime(string='Bill Of Lading Date', copy=False)
    lc_lines = fields.One2many('lc.letter.line', 'lc_id', string='Lines')
    payment_id = fields.Many2one('account.payment', 'Payment')
    move_id = fields.Many2one('account.move', 'Account Move')

    # currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', compute_sudo=True, store=True, readonly=True, help='Ratio between the purchase order currency and the company currency')

    # @api.depends('currency_id', 'company_id', 'company_id.currency_id')
    # def _compute_currency_rate(self):
    #     for order in self:
    #         order.currency_rate = self.env['res.currency']._get_conversion_rate(order.company_id.currency_id, order.currency_id, order.company_id,)
    #

    @api.ondelete(at_uninstall=False)
    def _unlink_if_cancelled(self):
        for lc in self:
            if not lc.state == 'cancel':
                raise UserError(_('In order to delete a LC, you must cancel it first.'))

    @api.depends('lc_lines.assigning_value')
    def compute_total_assign_value(self):
        for lc in self:
            total_assign_value = sum(lc.lc_lines.mapped('assigning_value'))
            lc.total_assign_value = total_assign_value

    @api.depends("lc_value", "lc_increment")
    def compute_max_val(self):
        self.lc_max_val = self.lc_value + (self.lc_increment / 100) * self.lc_value
        return True

    @api.depends("lc_max_val", "total_assign_value")
    def compute_pending_lc_value(self):
        self.pending_lc_value = self.lc_value - self.total_assign_value
        return True

    def open_lc(self):
        self.state = 'lc_open'
        return True

    def create_ltr(self):
        self.ensure_one()
        if self.move_id and self.move_id.state != 'cancel':
            raise UserError(_("Already Journal is created for this LC."))

        line_ids = []
        payment = self.env['account.payment'].search([('lc_id','=',self.name),('state','!=','cancel')])
        new_move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.env['account.journal'].search([('name', '=', 'Miscellaneous Operations')]).id,
            'lc_letter': self.id,
            'date': fields.Date.today(),
            'line_ids': [(0, 0, {
                            'debit': self.total_assign_value,
                            'credit': 0,
                            'partner_id': self.supplier.id,
                            'name': payment.name + '/-' + self.lc_ref,
                            'account_id': payment.journal_id.default_account_id.id,
                        }),
                        (0, 0, {
                            'debit': 0,
                            'credit': self.total_assign_value,
                            'partner_id': self.supplier.id,
                            'name': payment.name + '/-' + self.lc_ref,
                            'account_id': payment.journal_id.outbound_payment_method_line_ids[0].payment_account_id.id,
                        }),]
        })
        self.move_id = new_move
        action = {
            'name': _("Journal Entries"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        action.update({
            'view_mode': 'list,form',
            'domain': [('id', '=', new_move.id)],
        })
        return action


    def cancel(self):
        view = self.env.ref('aqar_lc_letter.cancel_lc_reason_form_view')
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Cancel Reason',
            'res_model': 'cancel.lc.reason',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [[view.id, 'form']],
            'target': 'new',
        }
        return action

    def done(self):
        move = self.env['account.move'].search([('lc_letter','=',self.name),('state','!=','cancel')])
        if move.state == 'posted':
            self.state = 'ltr_payment'
            return True
        else:
            raise UserError(_("Please Create/Post LTR Payment Before Proceding Done."))


    def reset_to_draft(self):
        self.state = 'draft'
        return True

    def po_assign(self):
        self.state = 'assign_po'
        return True

    def send_to_ltr(self):
        payment = self.env['account.payment'].search([('lc_id','=',self.name),('state','!=','cancel')])
        if payment.state != 'posted':
            raise UserError(_("The Payment For this LC Not Recorded."))
        self.state = 'ltr'
        return True

    def button_payment(self):
        if self.env['account.payment'].search([('lc_id','in',self.name),('state','!=','cancel')]):
            raise UserError(_("Already Payment is created for this LC."))

        self.ensure_one()
        return {
            'name': _("Payment"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'default_lc_id': self.id,
                        'default_payment_type': 'outbound',
                        'default_partner_id': self.supplier.id,
                        'default_memo': self.lc_ref,
                        'default_partner_type': 'supplier',
                        'default_amount': self.total_assign_value,
                        'default_currency_id': self.currency_id.id,
                        'default_date': fields.Date.today()},
            'view_mode': 'form',
            'res_id': self.payment_id.id,
        }

    def accept_lc(self):
        self.state = 'acceptance'
        return True

    def lc_payment(self):
        self.state = 'payment'
        return self.payment_id

    def button_view_payment(self):
        self.ensure_one()
        action = {
            'name': _("Payment"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        action.update({
            'view_mode': 'list,form',
            'domain': [('lc_id', 'in', self.name)],
        })
        return action

    def button_view_move(self):
        self.ensure_one()
        action = {
            'name': _("Journal Entries"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        action.update({
            'view_mode': 'list,form',
            'domain': [('id', '=', self.move_id.id)],
        })
        return action


    def lc_ltr(self):
        self.state = 'ltr'
        return True

    def lc_ltr(self):
        self.state = 'ltr_payment'
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'lc.letter') or 'New'
        return super(LCLetter, self).create(vals_list)


class LCLetterLine(models.Model):
    _name = "lc.letter.line"
    _description = 'Letter of credit line'

    lc_id = fields.Many2one('lc.letter', string='Product Wizard')
    purchase_id = fields.Many2one('purchase.order',
                                  states={'draft': [('readonly', False)]},
                                  string='Purchase Order',
                                  domain="[('mode_of_payment', '=', 'lc')]",
                                  help="Auto-complete from a past purchase order.")
    date_order = fields.Datetime(related='purchase_id.date_order', string='Order Date', readonly=True)
    currency_id = fields.Many2one('res.currency', related='purchase_id.currency_id')
    po_order_val = fields.Monetary(string='Purchase Order Value', currency_field='currency_id',
                                   related='purchase_id.amount_total', store=True, readonly=True)
    assigning_value = fields.Integer(string='Assigning Value')
    remarks = fields.Text('Remarks')
    lc_pending_order_value = fields.Integer(string="Pending LC Value", compute="compute_lc_pending_order_value")

    @api.depends("assigning_value", "po_order_val")
    def compute_lc_pending_order_value(self):
        self.lc_pending_order_value = self.assigning_value - self.po_order_val
        return True


class LCType(models.Model):
    _name = 'lc.type'
    _description = "LC Type"

    name = fields.Char(string='LC Type')


class DashBoard(models.Model):
    _inherit = 'account.move'

    lc_letter = fields.Many2one('lc.letter',string='LC Letter')