# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_investment_broker = fields.Boolean(string='Investment Broker',
                                          help='Is the partner is Investment Broker/Manager')
    is_investor = fields.Boolean(string='Investor', help='Is the partner is Investor')
    is_investment_company = fields.Boolean(string='Investment Company',
                                           help='Is the partner is Company that get listed in the share market')
