# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CancelReason(models.Model):
    _name = 'cancel.reason.reservation'
    _description = 'Cancel Reason'

    reason = fields.Char(string='Reason')
    reservation_id = fields.Many2one('property.reservation',string='Reservation')


    def action_cancel_apply(self):
        """ functionality of cancel reason"""
        self.reservation_id.write({'state': 'cancel'})
        self.reservation_id.unit_id.state = 'open'
        for rec in self.reservation_id.parking_line_ids:
            rec.state = 'available'
