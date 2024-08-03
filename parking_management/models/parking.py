# -*- coding: utf-8 -*-

from odoo import models,fields,api,_
from odoo.exceptions import  UserError
import re


class Parking(models.Model):
    _name = 'parking.parking'
    _description = 'Parking'
    _rec_name = 'parking_no'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", help="Name of the parking", required=1)
    building_id = fields.Many2one('property.building', string='Building', required=1)
    unit_id = fields.Many2one('property.property', string='Unit')
    unit_ids = fields.Many2many('property.property', string="Unit Ids", compute='_compute_unit_ids')

    floor_no = fields.Char(string='Floor No', required=1)
    is_sale = fields.Boolean(string='Sale', copy=False)
    is_rent = fields.Boolean(string='Rent',copy=False)
    notes = fields.Html(string='Notes')
    parking_no = fields.Char(string='Serial Number', copy=False,
                             readonly=True,
                             index=True, default=lambda self: _('New'))
    park_no = fields.Char(string='Parking Number', required=1)
    sales_price = fields.Float(string='Sale Price', default=5000, digits='Product Price', )
    parking_reservation_id = fields.Many2one('parking.reservation', string='Parking Reservation')
    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('rent', 'Rented'),
    ], string='Status', readonly=True, index=True, copy=False, default='available', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('parking_no', 'New') == 'New':
                if vals['building_id']:
                    building = self.env['property.building'].browse(vals['building_id'])
                    if building.sequence_id:
                        vals['parking_no'] = building.sequence_id.prefix + str(building.sequence_id.number_next_actual)
                        # vals['parking_no'] = building.sequence_id.prefix + '/' + vals['floor_no'] + '/' + vals[
                        #     'park_no'] + '/' + str(building.sequence_id.number_next_actual)
                        building.sequence_id.number_next_actual += 1
                    else:
                        raise UserError(_('Select the Building Sequence'))
        res = super(Parking, self).create(vals_list)
        return res

    @api.depends('building_id')
    def _compute_unit_ids(self):
        """ dynamic domain for unit"""
        self.unit_ids = False
        for rec in self:
            unit = self.env['property.property'].search(
                [('parent_building', '=', rec.building_id.id), ('state', '=', 'open'), ('for_sale', '=', True)])
            rec.unit_ids = unit.mapped('id')

    def action_done(self):
        """ change the state done state """
        self.write({'state': 'reserved'})

    def action_sold(self):
        """ change the state Sold state """
        self.write({'state': 'sold'})

    def action_rent(self):
        """ change the state Rented state """
        self.write({'state': 'rent'})

    def action_reset_draft(self):
        """ Reset the record to draft state"""
        self.write({'state': 'available'})


class PropertyRent(models.Model):
    _inherit = 'property.rent'

    parking_line_ids = fields.Many2many('parking.parking', string='Parking Slot')
    parking_reservation_ids = fields.Many2many('parking.reservation', string='Parking Reservation')

    def compute_installments(self):
        res = super(PropertyRent, self).compute_installments()
        for rec in self.parking_line_ids:
            parking_reservation = self.env['parking.reservation'].create({
                'building_id': self.building.id,
                'unit_ids': self.property_id.ids,
                'partner_id': self.partner_id.id,
                'parking_slot_ids': rec.ids,
                'state': 'reserved',
                'type_of_parking': 'is_rent',
            })
            self.write({'parking_reservation_ids': [(4, parking_reservation.id)]})
            rec.state = 'reserved'
        return res

    @api.onchange('building')
    def _onchange_parking_building(self):
        for rec in self:
            park_domain = [('building_id', '=', rec.building.id), ('state', '=', 'available')]
            parking_ids = rec.env['parking.parking'].search(park_domain)
            if parking_ids:
                return {'domain': {'parking_line_ids': [('id', 'in', parking_ids.ids)]}}
