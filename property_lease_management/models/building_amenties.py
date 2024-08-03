# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class BuildingAmenities(models.Model):
    _name = 'building.amenities'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Building Amenities'
    _rec_name = 'amenities_no'

    amenities_no = fields.Char(string='Amenities No', help='sequence of the Amenities', copy=False,
                               readonly=True,
                               index=True, )
    building_id = fields.Many2one('property.building', string='Building')
    ameniti_type_id = fields.Many2one('amenities.type', string='Ameniti Type')
    notes = fields.Html(string='Description')
    inspection_line_ids = fields.One2many('inspection.line', 'amenities_id', string='Inspection')

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            vals['amenities_no'] = self.env['ir.sequence'].next_by_code(
                'amenities.sequence')
        return super(BuildingAmenities, self).create(vals_list)


class AmenitiesType(models.Model):
    _name = 'amenities.type'
    _description = "Amenities Type"

    name = fields.Char(string='Name')


class InspectionLine(models.Model):
    _name = 'inspection.line'
    _description = 'Inspection Line'

    amenities_id = fields.Many2one('building.amenities', string='Amenities')
    date = fields.Date(string='Date')
    user_id = fields.Many2one('res.users', string='User')
    building_id = fields.Many2one('property.building', string='Building', related='amenities_id.building_id')
