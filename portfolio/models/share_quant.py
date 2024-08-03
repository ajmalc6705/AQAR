# -*- coding: utf-8 -*-

from odoo import models,fields

class ShareQuant(models.Model):
    _name = 'share.quant'
    _description='Shared Quantity'

    investment_id = fields.Many2one('portfolio.investment', string='Investment')
    qty = fields.Float(string='Quantity')