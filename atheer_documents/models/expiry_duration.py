# -*- coding: utf-8 -*-

from odoo import models,fields,api



class ExpiryDuration(models.Model):
    _name = 'expiry.duration'
    _description = 'Expiry Duration'
    _rec_name = 'duration'

    name = fields.Integer()
    duration = fields.Integer(string="Days", required=True)
    period = fields.Selection([('days', 'Days'),
                               ('months', 'Months')], default='days')

    @api.onchange('name')
    def set_duration(self):
        for rec in self:
            if rec.name:
                rec.duration = rec.name

    def name_get(self):
        """
        Display Name Formatting for the model.
        """
        res = []
        for record in self:
            name = '{duration} {period}'. \
                format(duration=record.duration, period=record.period)
            res.append((record.id, name))
        return res
