# -*- coding: utf-8 -*-

from odoo import models,fields,api,_

class Parking(models.Model):
    _inherit = 'parking.parking'

    reservation_id = fields.Many2one('property.reservation',string='Reservation')