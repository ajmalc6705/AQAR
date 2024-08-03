# -*- coding: utf-8 -*-

from odoo import models, fields


class MarketUpdation(models.Model):
    _name = 'market.updation'
    _description = 'Market Updation'
    _rec_name = 'rate'

    rate = fields.Float(string="Current Rate", digits='Product Price', help="Rate of share on this date")
    updation_date = fields.Datetime(string="Date", default=fields.Datetime.now())
    investment_id = fields.Many2one('res.partner', string='Investment Company',
                                    domain=[('is_investment_company', '=', True)])
