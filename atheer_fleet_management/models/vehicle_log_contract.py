# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FleetLogContratInherit(models.Model):
    _inherit = 'fleet.vehicle.log.contract'

    name_seq_ref = fields.Char(string="Ref", readonly=True, copy=False, required=True, default=lambda self: _('New'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name_seq_ref', 'New') == 'New':
                vals['name_seq_ref'] = self.env['ir.sequence'].next_by_code('fleet.vehicle.log.contract') or 'New'
        return super(FleetLogContratInherit, self).create(vals_list)
