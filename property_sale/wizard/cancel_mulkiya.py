# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CancelMulkiya(models.TransientModel):
    _name = 'cancel.mulkiya'
    _description = 'Cancel Mulkiya'

    reason = fields.Char(string='Reason',required=True)
    mulkiya_id = fields.Many2one('property.mulkiya.transfer',string='Mulkiya Transfer')



    def action_cancel_apply(self):
        """ functionality of cancel reason"""
        self.mulkiya_id.stage_id = self.env.ref('property_sale.canceled_stage')
        self.mulkiya_id.sale_id.write({'state': 'cancel'})
        self.mulkiya_id.sale_id.reservation_id.state = 'sale_offer'
        self.mulkiya_id.unit_id.state = 'open'
        for rec in self.mulkiya_id.parking_line_ids:
            rec.state = 'available'
