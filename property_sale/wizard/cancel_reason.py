# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CancelSaleReason(models.Model):
    _name = 'cancel.sale.reason'
    _description = 'Cancel Sale Reason'

    reason = fields.Char(string='Reason',required=True)
    property_sale_id = fields.Many2one('property.sale',string='Sale')
    date = fields.Date(string="Date",required=True)
    amount = fields.Float(string="Amount",required=True)


    def action_cancel_apply(self):
        """ functionality of cancel reason"""
        self.property_sale_id.write({'state': 'cancel'})
        self.property_sale_id.reservation_id.state = 'sale_offer'
        self.property_sale_id.unit_id.state = 'open'
        for rec in self.property_sale_id.parking_line_ids:
            rec.state = 'available'
