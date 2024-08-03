# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MasterVehicleTyres(models.Model):
    _name = 'master.vehicle.tyres'
    _description = 'Master Vehicle Tyres'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", readonly=True, copy=False, required=True, default=lambda self: _('New'))
    tyre_size = fields.Char(string='Tyre Size', tracking=True)
    brand = fields.Many2one('master.brand', string='Brand', tracking=True)
    purchase_date = fields.Date(string='Purchase Date', tracking=True)
    warranty_upto = fields.Date(string='Warranty Upto', tracking=True)
    year_of_manufacture = fields.Char(string='Year of Manufacture', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", tracking=True)
    active = fields.Boolean('Active', default=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('master.vehicle.tyres') or 'New'
        return super(MasterVehicleTyres, self).create(vals_list)


class MasterBrand(models.Model):
    _name = 'master.brand'
    _description = 'Master Brand'

    name = fields.Char(string="Name")


class FleetTyre(models.Model):
    _inherit = 'fleet.vehicle'

    tyre_count = fields.Integer(compute="_compute_tyres_count_all", string='Tyre Count')

    def _compute_tyres_count_all(self):
        for rec in self:
            tyre_ids = self.env['master.vehicle.tyres'].search([('vehicle_id', '=', rec.id)])
            rec.tyre_count = len(tyre_ids)

    def open_vehicle_tyre_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicle Tyres Details',
            'view_mode': 'tree,form',
            'res_model': 'master.vehicle.tyres',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id}
        }
