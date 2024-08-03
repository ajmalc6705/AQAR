# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TypeOfFuel(models.Model):
    _name = 'fleet.vehicle.type.of.fuel'
    _description = 'Type of Fuel'

    name = fields.Char(string="Name", required=True)


class MasterFuelCard(models.Model):
    _name = 'master.fuel.card'
    _description = 'Master Fuel Card'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", readonly=True, copy=False, required=True, default=lambda self: _('New'))
    card_number = fields.Char(string='Card Number', required=True, tracking=True)
    petrol_limit_per_month = fields.Float(string='Petrol Limit per Month', tracking=True, digits=(12, 3))
    type_of_fuel_id = fields.Many2one("fleet.vehicle.type.of.fuel", string='Type of Fuel', tracking=True)
    vehicle_id = fields.Many2one("fleet.vehicle", string='Vehicle', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean('Active', default=True, tracking=True)

    # @api.onchange('vehicle_id')
    # def compute_vehicle_id(self):
    #     for rec in self:
    #         rec.vehicle_id.fuel_card = rec.id
    #
    # @api.constrains('vehicle_id')
    # def compute_vehicle_id(self):
    #     for rec in self:
    #         rec.vehicle_id.fuel_card = rec.id
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        domain = ['|', ('name', operator, name), ('card_number', operator, name)]
        records = self.search(domain + args, limit=limit)
        return records.name_get()

    def name_get(self):
        res = []
        for each in self:
            name = each.name
            if each.card_number:
                res.append((each.id, str(each.card_number) + ' [' + name + ']'))
            else:
                res.append((each.id, name))
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('master.fuel.card') or 'New'
        return super(MasterFuelCard, self).create(vals_list)
