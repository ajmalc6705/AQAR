# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResaleWizard(models.TransientModel):
    _name = 'resale.wizard'
    _description = 'Resale Wizard'

    sale_date = fields.Date(string="Sale Date")
    partner_id = fields.Many2one('res.partner', string='Customer')
    amount_total = fields.Monetary(string='Sale Amount', help='Total Amount to be paid', )
    new_sale_date = fields.Date(string='New Sale Date')
    new_partner_id = fields.Many2one('res.partner', string='New Customer')
    new_sale_value = fields.Monetary(string='New Sale Amount', help='Total Amount to be paid', )
    sale_id = fields.Many2one('property.sale', string='Sale')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)
    company_id = fields.Many2one('res.company', string="Company", help='company',
                                 default=lambda self: self.env.company)

    def create_resale(self):
        """action to create resale"""
        resale = self.env['property.resale'].create({
            'sale_id': self.sale_id.id,
            'sale_date': self.sale_date,
            'partner_id': self.partner_id.id,
            'amount_total': self.amount_total,
            'new_sale_date': self.new_sale_date,
            'new_partner_id': self.new_partner_id.id,
            'new_sale_value': self.new_sale_value,
        })
        self.sale_id.sale_date = self.new_sale_date
        self.sale_id.partner_id = self.new_partner_id.id
        self.sale_id.amount_total = self.new_sale_value
