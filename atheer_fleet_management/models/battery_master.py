# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MasterBattery(models.Model):
    _name = 'master.battery'
    _description = 'Master Battery'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", readonly=True, copy=False, required=True, default=lambda self: _('New'))
    purchased_date = fields.Date(string='Purchased Date', tracking=True)
    model_number = fields.Char(string='Model Number', tracking=True)
    brand_name = fields.Char(string='Brand', tracking=True)
    warranty_expiry_date = fields.Date(string='Warranty Expiry Date', tracking=True)
    document_ids = fields.One2many('atheer.documents', inverse_name="battery_id", string='Documents', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", tracking=True)
    active = fields.Boolean('Active', default=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('master.battery') or 'New'
        return super(MasterBattery, self).create(vals_list)


class VehicleDocuments(models.Model):
    _inherit = 'atheer.documents'

    battery_id = fields.Many2one('master.battery', string='Fleet Battery')


class FleetBatteryDetails(models.Model):
    _inherit = 'fleet.vehicle'

    battery_count = fields.Integer(compute="_compute_battery_count_all", string='Battery Count')

    def _compute_battery_count_all(self):
        for each in self:
            battery_ids = self.env['master.battery'].search([('vehicle_id', '=', each.id)])
            each.battery_count = len(battery_ids)

    def open_vehicle_battery_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicle Battery Details',
            'view_mode': 'tree,form',
            'res_model': 'master.battery',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id}
        }
