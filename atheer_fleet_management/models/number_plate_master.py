# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class MasterNumberPlate(models.Model):
    _name = 'master.number.plate'
    _description = "Master Number Plate"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", readonly=True, copy=False, required=True, default=lambda self: _('New'))
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", tracking=True)
    number_plate = fields.Char(string='Number Plate', tracking=True)
    owner = fields.Many2one('res.partner', string='Owner', required=True, tracking=True)
    location = fields.Selection([('rop', 'ROP (Royal Oman Police)'),
                                 ('vehicle', 'Vehicle')],
                                string='Location', tracking=True)
    vendor_id = fields.Many2one('res.partner', string='Purchased From', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    purchase_date = fields.Date(string='Purchase Date', tracking=True)
    purchase_value = fields.Float(string='Purchase Value', tracking=True, digits=(12, 3))

    customer_id = fields.Many2one('res.partner', string='Sold To', tracking=True)
    sold_value = fields.Float(string='Sold Value', tracking=True, digits=(12, 3))
    sold_date = fields.Date(string='Sold  Date', tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    document_ids = fields.Many2many('atheer.documents', 'rel_document_number_plate_id', 'doc_id', 'number_plate_id',
                                    string='Documents', copy=False)
    active = fields.Boolean('Active', default=True, tracking=True)
    sold = fields.Boolean('sold', default=False, tracking=True)

    def button_action_sold(self):
        for rec in self:
            if not rec.customer_id:
                raise ValidationError(_('Please Enter Sold To field.'))
            if not rec.sold_date:
                raise ValidationError(_('Please Enter Sold Date field.'))
            if rec.sold_value <= 0:
                raise ValidationError(_('The Sold Value should be greater than zero'))
            rec.sold = True
            rec.active = False

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        domain = ['|', ('name', operator, name), ('number_plate', operator, name)]
        records = self.search(domain + args, limit=limit)
        return records.name_get()

    def name_get(self):
        res = []
        for each in self:
            name = each.name
            if each.number_plate:
                res.append((each.id, str(each.number_plate) + ' [' + name + ']'))
            else:
                res.append((each.id, name))
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('master.number.plate') or 'New'
        return super(MasterNumberPlate, self).create(vals_list)


class VehicleDocuments(models.Model):
    _inherit = 'atheer.documents'

    number_plate_id = fields.Many2one('master.number.plate', string='Number Plate')


class FleetNumberPlate(models.Model):
    _inherit = 'fleet.vehicle'

    no_plate_count = fields.Integer(compute="_compute_no_plate_count_all", string='No Plate Count')

    def _compute_no_plate_count_all(self):
        for rec in self:
            no_plate_ids = self.env['master.number.plate'].search([('vehicle_id', '=', rec.id)])
            rec.no_plate_count = len(no_plate_ids)

    def open_vehicle_no_plate_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicle Number Plate Details',
            'view_mode': 'tree,form',
            'res_model': 'master.number.plate',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id}
        }
