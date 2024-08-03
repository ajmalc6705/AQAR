# -*- coding: utf-8 -*-

from odoo import models,fields

class InvestmentType(models.Model):
    _name ='investment.type'
    _description = 'Investment Type'

    name = fields.Char(string='Name', help='Type of the Investment')
