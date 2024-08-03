# -*- coding: utf-8 -*-

from odoo import models,fields

class InvestmentExchange(models.Model):
    _name = 'investment.exchange'
    _description = 'Investment Exchange'

    name = fields.Char(string='Name', help='Name of the Sector')