# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MasterVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    vehicle_group = fields.Selection([('personal', 'Personal'), ('company', 'Company'), ], string='Vehicle Group',
                                     tracking=True)

    accessories = fields.Many2many('vehicle.accessory', string='Accessories', tracking=True)
    number_plate = fields.Many2one('master.number.plate', string='Number Plate', tracking=True,
                                   context={'active_test': True})
    owner = fields.Many2one('res.partner', string='Owner', tracking=True)

    rhs_front = fields.Many2one('master.vehicle.tyres', string='RHS Front', context={'active_test': True})
    lhs_front = fields.Many2one('master.vehicle.tyres', string='LHS Front', context={'active_test': True})
    rhs_rear = fields.Many2one('master.vehicle.tyres', string='RHS Rear', context={'active_test': True})
    lhs_rear = fields.Many2one('master.vehicle.tyres', string='LHS Rear', context={'active_test': True})
    rhs_rear_out = fields.Many2one('master.vehicle.tyres', string='RHS Rear  OUT', context={'active_test': True})
    lhs_rear_out = fields.Many2one('master.vehicle.tyres', string='LHS Rear OUT', context={'active_test': True})
    spare_tyre = fields.Many2one('master.vehicle.tyres', string='Spare Tyre', context={'active_test': True})
    battery_details = fields.Many2one('master.battery', string='Battery Details', context={'active_test': True})
    # fuel_card = fields.Many2one('master.fuel.card',string='Fuel Card')
    insurance_details = fields.Many2one('master.insurance', string='Insurance Details', tracking=True,
                                        context={'active_test': True})
    mulkia_rop_number = fields.Char(string='Mulkia ROP Number', tracking=True)
    mulkia_expiry_date = fields.Date(string='Mulkia Expiry Date', tracking=True)
    service_warranty_expiry_date = fields.Date(string='Service Warranty Expiry Date', tracking=True)
    ext_warranty_expiry_date = fields.Date(string='Ext Warranty Expiry Date', tracking=True)
    document_ids = fields.Many2many('atheer.documents', 'rel_document_vehicle_id', 'doc_id', 'vehicle_id',
                                    string='Documents', copy=False)

    name_seq = fields.Char(string="Ref", readonly=True, copy=False, required=True, default=lambda self: _('New'))
    image_vehicle = fields.Image("Vehicle Image", tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name_seq', 'New') == 'New':
                vals['name_seq'] = self.env['ir.sequence'].next_by_code('fleet.vehicle') or 'New'
        return super(MasterVehicle, self).create(vals_list)

    @api.onchange('number_plate')
    def compute_number_plate(self):
        self.license_plate = self.number_plate.number_plate

    def get_fuel_cards(self):
        """ to get the fuel card informations """
        domain = "[('vehicle_id', '=', " + str(self.id) + ")]"
        return {'name': _("Fuel Cards"),
                'view_mode': 'tree,form',
                'view_type': 'tree',
                'res_model': 'master.fuel.card',
                'type': 'ir.actions.act_window',
                'domain': domain,
                'context': {'default_vehicle_id': self.id, }
                }

    def get_fleet_insurance(self):
        """ to get the fuel card informations """
        domain = "[('vehicle_id', '=', " + str(self.id) + ")]"
        return {'name': _("Fuel Cards"),
                'view_mode': 'tree',
                'view_type': 'tree',
                'res_model': 'master.insurance',
                'type': 'ir.actions.act_window',
                'domain': domain,
                'context': {'default_vehicle_id': self.id, }
                }


class VehicleDocuments(models.Model):
    _inherit = 'atheer.documents'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Fleet Vehicle')


class VehicleAccessory(models.Model):
    _name = 'vehicle.accessory'
    _description = 'Accessory'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    price = fields.Float(string='Price')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Accessory name must be unique.'),
    ]
