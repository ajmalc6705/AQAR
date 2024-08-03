# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

PAYMENT_STATE_SELECTION = [
    ('not_paid', 'Not Paid'),
    ('in_payment', 'In Payment'),
    ('paid', 'Paid'),
    ('partial', 'Partially Paid'),
    ('reversed', 'Reversed'),
    ('invoicing_legacy', 'Invoicing App Legacy'),
]


class AgentPayment(models.Model):
    _name = 'agent.payment'
    _description = 'Agent Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "agent_payment_seq"

    agent_payment_seq = fields.Char(string='Sequence', copy=False,
                                    readonly=True, help="Sequence for Agent Payment Sequence",
                                    index=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Partner')
    building_id = fields.Many2one('property.building', string='Building')
    unit_id = fields.Many2one('property.property', string='Unit')
    unit_ids = fields.Many2many('property.property', string="Unit Ids", compute='_compute_unit_ids')
    total_amount = fields.Float(string='Total Amount', help="amounts calculated as per sales or lease or service")
    commission_percent = fields.Float(string='Commission %')
    commission_amount = fields.Float(string='Commission Amount', help="Commission percentage of total amount")
    agent_service_type = fields.Selection([('property_sale', 'Property Sales'), ('property_lease', 'Property Lease'),
                                           ('property_service', 'Property Service'),
                                           ('property_parking', 'Property Parking'),
                                           ('property_community', 'Property Community'), ],
                                          string='Deal Type')
    property_sale_id = fields.Many2one('property.sale', string='Property Sale')
    property_service_id = fields.Many2one('property.service', string='Property Service')
    property_lease_id = fields.Many2one('property.rent', string='Property Rent')
    property_parking_id = fields.Many2one('parking.reservation', string='Property Parking')
    source = fields.Char(string='Source', compute='_compute_source', store=True)
    agent_payment_ids = fields.One2many('agent.payment.line', 'payment_id', string='Agent Details')
    invoiced_ribbon = fields.Boolean(string='Invoiced', default=False, compute='_compute_invoiced')
    is_create_bill = fields.Boolean(string='Bill', default=False, compute='_compute_create_bill')
    partial_invoiced_ribbon = fields.Boolean(string='Partial Invoiced', default=False, compute='_compute_invoiced')
    fully_invoiced_ribbon = fields.Boolean(string='Fully Invoiced', default=False, compute='_compute_invoiced')
    state = fields.Selection(
        [('draft', 'draft'), ('checked', 'Checked'), ('verified', 'Verified'), ('confirm', 'Approved'),
         ('cancel', 'Canceled'), ], string='Status',
        readonly=True, index=True, copy=False, default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    payment_state = fields.Selection(related="agent_payment_ids.payment_state", string="Payment Status",
                                     store=True, readonly=True, compute_sudo=True, copy=False, tracking=True,
                                     )

    # compute='_compute_payment_state'

    @api.depends('agent_payment_ids.is_invoiced', 'property_service_id')
    def _compute_create_bill(self):
        """ compute create bill"""
        self.is_create_bill = False
        for rec in self.agent_payment_ids:
            if not rec.move_id:
                self.is_create_bill = False
            else:
                self.is_create_bill = True

    @api.depends('agent_service_type', 'property_sale_id', 'property_service_id', 'property_lease_id',
                 'property_parking_id')
    def _compute_source(self):
        """ compute the source """
        self.source = False
        for rec in self:
            if rec.agent_service_type == 'property_sale':
                rec.source = rec.property_sale_id.sale_seq
            elif rec.agent_service_type == 'property_lease':
                rec.source = rec.property_lease_id.name
            elif rec.agent_service_type == 'property_service':
                rec.source = rec.property_service_id.service_seq
            elif rec.agent_service_type == 'property_parking':
                rec.source = rec.property_parking_id.parking_reservation_no

    @api.depends('agent_payment_ids')
    def _compute_invoiced(self):
        """ compute the ribbon value"""
        self.invoiced_ribbon = False
        self.partial_invoiced_ribbon = False
        self.fully_invoiced_ribbon = False
        is_invoiced = 0
        for rec in self.agent_payment_ids:
            if rec.is_invoiced:
                is_invoiced += 1
        if is_invoiced == 0:
            self.invoiced_ribbon = True
        elif is_invoiced < len(self.agent_payment_ids):
            self.partial_invoiced_ribbon = True
        elif is_invoiced >= len(self.agent_payment_ids):
            self.fully_invoiced_ribbon = True

    @api.onchange('agent_service_type', 'property_sale_id', 'property_service_id', 'property_lease_id',
                  'property_parking_id')
    def onchange_service_type(self):
        # For Property  Sale
        if self.agent_service_type == 'property_sale':
            # self.total_amount = self.property_sale_id.total_amount
            self.partner_id = self.property_sale_id.partner_id
            self.building_id = self.property_sale_id.building_id.id
            self.unit_id = self.property_sale_id.unit_id.id
            self.total_amount = self.property_sale_id.amount_untaxed
            self.commission_percent = self.property_sale_id.commission_percent * 100
        # For Property Rent Agreement/ Lease
        elif self.agent_service_type == 'property_lease':
            self.partner_id = self.property_lease_id.partner_id
            self.total_amount = self.property_lease_id.rent_total
            self.building_id = self.property_lease_id.building.id
            self.unit_id = self.property_lease_id.property_id.id
        # For Property Service
        elif self.agent_service_type == 'property_service':
            self.partner_id = self.property_service_id.partner_id
            self.building_id = self.property_service_id.building_id.id
            self.unit_id = self.property_service_id.unit_id.id
            self.total_amount = self.property_service_id.amount_untaxed
            self.commission_percent = self.property_service_id.commission_percent
        # For Property Parking
        elif self.agent_service_type == 'property_parking':
            self.partner_id = self.property_parking_id.partner_id
            self.building_id = self.property_parking_id.building_id.id
            self.total_amount = self.property_parking_id.amount_untaxed

    @api.onchange('total_amount', 'commission_percent')
    def onchange_total(self):
        self.commission_amount = self.total_amount * self.commission_percent / 100
        # if self.agent_service_type == 'property_sale':
        #     self.commission_amount = self.total_amount * self.commission_percent/100
        #
        # if self.agent_service_type == 'property_lease':
        #     self.commission_amount = self.total_amount * self.commission_percent/100
        #
        # if self.agent_service_type == 'property_service':
        #     self.commission_amount = self.total_amount * self.commission_percent/100

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('agent_payment_seq', 'New') == 'New':
                vals['agent_payment_seq'] = self.env['ir.sequence'].next_by_code(
                    'agent.payment.sequence') or 'New'
        return super(AgentPayment, self).create(vals_list)

    @api.depends('building_id')
    def _compute_unit_ids(self):
        """ dynamic domain for unit"""
        self.unit_ids = False
        for rec in self:
            unit = self.env['property.property'].search([('parent_building', '=', rec.building_id.id)])
            rec.unit_ids = unit.mapped('id')

    def action_button_send_to_authorizer(self):
        """ change the state Expire state """
        self.write({'state': 'checked'})

    def action_button_verify(self):
        """ change the state Expire state """
        # # Retrieve model id for 'purchase.order'
        for rec in self:
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'agent.payment')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            rec.write({'state': 'verified'})

    def action_confirm(self):
        """ change the state running state """
        confirmed_payments = 0
        if self.agent_service_type == 'property_sale':
            confirmed_payments = self.env['agent.payment'].search(
                [('property_sale_id', '=', self.property_sale_id.id), ('state', '=', 'confirm')])

        elif self.agent_service_type == 'property_lease':
            confirmed_payments = self.env['agent.payment'].search(
                [('property_lease_id', '=', self.property_lease_id.id), ('state', '=', 'confirm')])

        elif self.agent_service_type == 'property_service':
            confirmed_payments = self.env['agent.payment'].search(
                [('property_service_id', '=', self.property_service_id.id), ('state', '=', 'confirm')])

        elif self.agent_service_type == 'property_parking':
            confirmed_payments = self.env['agent.payment'].search(
                [('property_parking_id', '=', self.property_parking_id.id), ('state', '=', 'confirm')])

        if len(confirmed_payments) > 0:
            raise UserError(_('Already a Confirmed Agent Payment is existing for this Property'))

        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'agent.payment')]).id
        # Remove Old Activities related to the current record
        self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id),
        ]).unlink()

        self.write({'state': 'confirm'})

    def button_action_send_back(self):
        state_map = {
            'confirm': 'verified',
            'verified': 'checked',
            'checked': 'draft',
        }
        for rec in self:
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'agent.payment')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()

            new_state = state_map.get(rec.state)
            if new_state:
                rec.state = new_state

    def action_cancel(self):
        """ change the state Expire state """
        if not self.agent_payment_ids:
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'agent.payment')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', self.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()

            self.write({'state': 'cancel'})
        else:
            for rec in self.agent_payment_ids:
                if not rec.move_id:
                    res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'agent.payment')]).id
                    # Remove Old Activities related to the current record
                    self.env['mail.activity'].search([
                        ('res_id', '=', self.id),
                        ('res_model_id', '=', res_model_id),
                    ]).unlink()

                    self.write({'state': 'cancel'})
                else:
                    raise UserError(_("Unable to Cancel Agent Payment '%s' as some Bill have already Created.",
                                      self.agent_payment_seq))

    def action_reset_draft(self):
        """ change the state Draft state """
        if not self.agent_payment_ids:
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'agent.payment')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', self.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()

            self.write({'state': 'draft'})
        else:
            for rec in self.agent_payment_ids:
                if rec.move_id.state == 'draft':
                    res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'agent.payment')]).id
                    # Remove Old Activities related to the current record
                    self.env['mail.activity'].search([
                        ('res_id', '=', self.id),
                        ('res_model_id', '=', res_model_id),
                    ]).unlink()

                    self.write({'state': 'draft'})
                else:
                    raise UserError(_("Unable to Set to Draft Agent Payment '%s' as some Bill have already posted.",
                                      self.agent_payment_seq))

    def action_create_bill(self):
        """ Create bills aganist each agent"""
        for rec in self.agent_payment_ids:
            # Modified Name
            name = rec.payment_id.agent_payment_seq + ' : ' + rec.agent_id.name

            if not rec.is_invoiced:
                move = self.env['account.move'].create({
                    'partner_id': rec.agent_id.id,
                    'move_type': 'in_invoice',
                    # 'ref': rec.payment_id.agent_payment_seq,
                    'invoice_date': fields.Date.today(),
                    'agent_payment_id': self.id,
                    'invoice_line_ids': [
                        (0, 0, {
                            'name': name,
                            'price_unit': val.amount_untaxed,
                            # 'price_unit': val.amount,
                            'quantity': 1,
                            'account_id': rec.account_id.id,
                            'tax_ids': [(6, 0, val.tax_ids.ids)]

                        }) for val in rec
                    ]
                })
                rec.is_invoiced = True
                rec.move_id = move.id

    def action_bill(self):
        """ action to show bill"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bill',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('agent_payment_id', '=', self.id)],
        }


class AgentPaymentLine(models.Model):
    _name = 'agent.payment.line'
    _inherit = ['mail.thread']
    _rec_name = 'agent_id'
    _description = 'Agent Payment'

    agent_id = fields.Many2one('res.partner', domain=[('is_property_agent', '=', True)], string='Agent')
    account_id = fields.Many2one('account.account', string='Account')
    tax_ids = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use', '=', 'purchase')])
    amount = fields.Float(string='Total Amount')
    percentage = fields.Float(string='Percent')
    amount_untaxed = fields.Float(string='Amount Untaxed')
    move_id = fields.Many2one('account.move', string='Move')
    payment_state = fields.Selection(related="move_id.payment_state", string="Payment Status",
                                     store=True, readonly=True, compute_sudo=True,
                                     copy=False, tracking=True,
                                     )
    invoice_state = fields.Selection(related="move_id.state", string='Status', readonly=True, copy=False, tracking=True,
                                     compute_sudo=True, store=True,
                                     )
    payment_id = fields.Many2one('agent.payment', string='Payment')
    is_invoiced = fields.Boolean(string='Is Invoiced', default=False)
    company_id = fields.Many2one('res.company', string='Company', related='payment_id.company_id', compute_sudo=True)

    @api.onchange('percentage')
    def _onchange_percentage(self):
        self.amount_untaxed = (self.percentage / 100) * self.payment_id.commission_amount

    @api.onchange('tax_ids', 'amount_untaxed', 'percentage')
    def calculate_amount(self):
        tax_percentage = 0
        for tax in self.tax_ids:
            tax_percentage = tax.amount
        amount_taxed = self.amount_untaxed * tax_percentage / 100
        self.amount = self.amount_untaxed + amount_taxed


class AccountMove(models.Model):
    _inherit = 'account.move'

    agent_payment_id = fields.Many2one('agent.payment', string='Agent Payment')
