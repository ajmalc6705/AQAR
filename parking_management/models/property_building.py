# -*- coding: utf-8 -*-

from odoo import models, fields


class PropertyBuilding(models.Model):
    _inherit = 'property.building'

    parking_line_ids = fields.One2many('parking.parking','building_id',string='Parking')
    sequence_id = fields.Many2one('ir.sequence',string='Building Sequence')
