# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class AccountAnalyticApplicability(models.Model):
    _inherit = 'account.analytic.applicability'
    _description = "Analytic Plan's Applicabilities"

    business_domain = fields.Selection(selection_add=[('petty_cash', 'Petty Cash Expenses'),
                                                      ('stock_picking', 'Stock Picking')],
                                       ondelete={'petty_cash': 'cascade', 'stock_picking': 'cascade', },
                                       )
