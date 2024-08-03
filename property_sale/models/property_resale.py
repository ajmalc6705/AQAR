# -*- coding: utf-8 -*-

from odoo import models,fields,api

class PropertyResale(models.Model):
    _name = 'property.resale'
    _description = 'Property Resale'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'sale_id'

    sale_date = fields.Date(string="Sale Date")
    partner_id = fields.Many2one('res.partner', string='Customer')
    amount_total = fields.Monetary(string='Sale Amount', help='Total Amount to be paid',)
    new_sale_date = fields.Date(string='New Sale Date')
    new_partner_id = fields.Many2one('res.partner', string='New Customer')
    new_sale_value = fields.Monetary(string='New Sale Amount', help='Total Amount to be paid',)
    sale_id = fields.Many2one('property.sale',string='Sale')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)
    company_id = fields.Many2one('res.company', string="Company", help='company',
                                 default=lambda self: self.env.company)