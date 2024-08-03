# -*- coding: utf-8 -*-

from odoo import models, fields


class InvestmentSector(models.Model):
    _name = 'investment.sector'
    _description = 'Investment Sector'

    name = fields.Char(string='Name', help='Name of the Sector')

class InvestmentSubsector(models.Model):
    _name = 'investment.subsector'
    _description = 'Investment Subsector'

    name = fields.Char(string='Name', help='Name of the Sector')
