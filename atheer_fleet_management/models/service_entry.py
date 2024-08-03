# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ServiceEntry(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    name = fields.Char(string="Name", readonly=True, copy=False, required=True, default=lambda self: _('New'))
    service_type = fields.Selection([
        ('preventive', 'Preventive'),
        ('minor', 'Minor'),
        ('semi_major', 'Semi Major'),
        ('major', 'Major')
    ], string='Type of Service', tracking=True)

    rhs_front = fields.Many2one('master.vehicle.tyres', string='RHS Front', tracking=True)
    lhs_front = fields.Many2one('master.vehicle.tyres', string='LHS Front', tracking=True)
    rhs_rear = fields.Many2one('master.vehicle.tyres', string='RHS Rear', tracking=True)
    lhs_rear = fields.Many2one('master.vehicle.tyres', string='LHS Rear', tracking=True)
    rhs_rear_out = fields.Many2one('master.vehicle.tyres', string='RHS Rear  OUT', tracking=True)
    lhs_rear_out = fields.Many2one('master.vehicle.tyres', string='LHS Rear OUT', tracking=True)
    spare_tyre = fields.Many2one('master.vehicle.tyres', string='Spare Tyre', tracking=True)
    parts_list = fields.One2many('service.entry.parts', 'service_entry_id', string='Parts List', tracking=True)
    battery_details = fields.Many2one('master.battery', string='Battery Details', tracking=True)
    next_service_date = fields.Date(string='Next Service Date', tracking=True)
    next_odometer = fields.Float(string='Next Odometer Value', tracking=True)

    @api.onchange('parts_list')
    def compute_amount(self):
        """ computing the total amount """
        for rec in self:
            rec.amount = sum(rec.parts_list.mapped('rate'))

    @api.onchange('vehicle_id')
    def compute_rhs_front(self):
        self.battery_details = self.vehicle_id.battery_details
        self.rhs_front = self.vehicle_id.rhs_front
        self.lhs_front = self.vehicle_id.lhs_front
        self.rhs_rear = self.vehicle_id.rhs_rear
        self.lhs_rear = self.vehicle_id.lhs_rear
        self.spare_tyre = self.vehicle_id.spare_tyre

    def confirm(self):
        self.state = 'running'

    def done(self):
        self.vehicle_id.battery_details = self.battery_details
        self.vehicle_id.lhs_rear = self.lhs_rear
        self.vehicle_id.rhs_rear = self.rhs_rear
        self.vehicle_id.lhs_front = self.lhs_front
        self.vehicle_id.rhs_front = self.rhs_front
        self.vehicle_id.spare_tyre = self.spare_tyre
        self.state = 'done'

    def cancel(self):
        self.state = 'cancelled'

    def reset(self):
        self.state = 'draft'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.vehicle.log.services') or 'New'
        return super(ServiceEntry, self).create(vals_list)


class ServiceEntryParts(models.Model):
    _name = 'service.entry.parts'
    _description = 'Service Entry Parts'

    service_entry_id = fields.Many2one('fleet.vehicle.log.services', string='Service Entry')
    product_id = fields.Many2one('product.product', string='Item Code', required=True)
    qty = fields.Float(string='Quantity', digits=(12, 3))
    rate = fields.Float(string='Rate', onchange="onchange_rate", digits=(12, 3))
    remark = fields.Text(string='Remarks')
