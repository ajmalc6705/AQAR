# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ParkingReservation(models.Model):
    _name = 'parking.reservation'
    _description = 'Parking Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'parking_reservation_no'

    building_id = fields.Many2one('property.building', string='Building')
    partner_id = fields.Many2one('res.partner', string='Customer')
    type_of_parking = fields.Selection([
        ('is_sale', 'Sale'),
        ('is_rent', 'Rent'),
    ], string='Type of Parking', default='is_sale')
    notes = fields.Html(string='Notes')
    parking_reservation_no = fields.Char(string='Parking Reservation Number', copy=False,
                                         readonly=True, index=True, default=lambda self: _('New'))
    sales_price = fields.Float(string='Total Amount', store=True, compute='_compute_sales_price',
                               digits='Product Price', )
    amount_untaxed = fields.Monetary(string="Amount Untaxed", compute='_compute_total', store=True,
                                     help="Sum of sales price and parking price", digits='Product Price', )
    amount_total = fields.Monetary(string='Amount Total', help='Total Amount to be paid', compute='_compute_total',
                                   digits='Product Price', store=True)
    tax_ids = fields.Many2many('account.tax', string='Taxes',
                               domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'sale')]")
    state = fields.Selection([
        ('draft', 'Available'),
        ('reserved', 'Reserved'),
        ('confirm', 'Confirm'),
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    parking_slot_ids = fields.Many2many('parking.parking', 'parking_reservation_id', string='Parking Reservation', )
    unit_ids = fields.Many2many('property.property', string='Unit')
    parking_ids = fields.Many2many('parking.parking', compute='_compute_parking_slots')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)
    company_id = fields.Many2one('res.company', string="Company", help='company',
                                 default=lambda self: self.env.company)
    property_rent_id = fields.Many2one('property.rent', string='Rent Agreement')
    lease_start_date = fields.Date(string='Lease Start Date', related='property_rent_id.from_date')
    lease_end_date = fields.Date(string='Lease End Date', related='property_rent_id.to_date')

    @api.depends('amount_untaxed', 'sales_price', 'tax_ids')
    def _compute_total(self):
        """Compute the total amounts of the SO."""
        self.amount_total = 0
        tax_amount = 0
        for rec in self:
            rec.amount_untaxed = rec.sales_price
            for tax in rec.tax_ids:
                cal_amount = (tax.amount / 100 * rec.amount_untaxed)
                tax_amount += cal_amount
            rec.amount_total = rec.amount_untaxed + tax_amount

    @api.onchange('building_id')
    def _onchange_building(self):
        domain = []
        if self.type_of_parking == 'is_sale':
            units = self.env['property.property'].search(
                [('parent_building', '=', self.building_id.id), ('state', '=', 'open'), ('for_sale', '=', True)])
            return {'domain': {'unit_ids': [('id', 'in', units.ids)]}}
        elif self.type_of_parking == 'is_rent':
            units = self.env['property.property'].search(
                [('parent_building', '=', self.building_id.id), ('state', '=', 'open'), ('for_rent', '=', True)])
            return {'domain': {'unit_ids': [('id', 'in', units.ids)]}}
        return domain

    @api.depends('parking_slot_ids.sales_price')
    def _compute_sales_price(self):
        self.sales_price = 0
        price = 0
        for rec in self:
            price = sum(rec.parking_slot_ids.mapped('sales_price'))
            rec.sales_price = price

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('parking_reservation_no', 'New') == 'New':
                vals['parking_reservation_no'] = self.env['ir.sequence'].next_by_code(
                    'parking.reservation.sequence') or 'New'
        res = super(ParkingReservation, self).create(vals_list)
        return res

    @api.depends('building_id', 'type_of_parking')
    def _compute_parking_slots(self):
        """ compute the parking slots """
        self.parking_ids = False
        for rec in self:
            park_domain = [('building_id', '=', rec.building_id.id), ('state', '=', 'available')]
            if rec.type_of_parking == 'is_sale':
                park_domain += [('is_sale', '=', True)]
            if rec.type_of_parking == 'is_rent':
                park_domain += [('is_rent', '=', True)]
            parking_slot = self.env['parking.parking'].search(park_domain)
            rec.parking_ids = parking_slot.mapped('id')

    def action_done(self):
        """ change the state done state """
        self.write({'state': 'confirm'})
        for rec in self.parking_slot_ids:
            if rec.state == 'reserved':
                rec.state = 'sold'

    def action_reserve(self):
        """ change the state Sold state """
        self.write({'state': 'reserved'})
        for rec in self.parking_slot_ids:
            if rec.state == 'available':
                rec.state = 'reserved'

    def action_reset_draft(self):
        """ Reset the record to draft state"""
        self.write({'state': 'draft'})
        for rec in self.parking_slot_ids:
            rec.state = 'available'
