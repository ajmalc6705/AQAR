# -*- coding: utf-8 -*-

from odoo import models,fields

class InvestmentMarket(models.Model):
    _name = 'investment.market'
    _description = 'Investment Market'

    name = fields.Char(string='Name', help='Name of the Market')