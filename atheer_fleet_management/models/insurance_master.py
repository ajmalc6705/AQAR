# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MasterInsurance(models.Model):
    _name = 'master.insurance'
    _description = 'Master Insurance'
    _rec_name = 'policy_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", readonly=True, copy=False, required=True, default=lambda self: _('New'))
    policy_number = fields.Char(string='Policy Number', required=True)
    type_of_insurance = fields.Many2one('insurance.types', string='Type of Insurance', tracking=True)
    insurance_company = fields.Many2one('res.partner', string='Insurance Company', tracking=True)
    issue_date = fields.Date(string='Issue Date', tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    insurance_value = fields.Float(string='Insurance Value', tracking=True, digits=(12, 3))
    document_ids = fields.Many2many('atheer.documents', 'rel_document_insurance_id', 'doc_id', 'insurance_id',
                                    string='Documents', copy=False)
    vehicle_id = fields.Many2one("fleet.vehicle", string='Vehicle', tracking=True, context={'active_test': True})
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean('Active', default=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('master.insurance') or 'New'
        return super(MasterInsurance, self).create(vals_list)


class VehicleDocuments(models.Model):
    _inherit = 'atheer.documents'
    _description = 'Documents'

    insurance_id = fields.Many2one('master.insurance', string='Fleet Insurance')


class InsuranceTypes(models.Model):
    _name = 'insurance.types'
    _description = 'Insurance Types'

    name = fields.Char('Name')
