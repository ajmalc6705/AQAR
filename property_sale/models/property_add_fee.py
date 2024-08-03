# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertyAddFee(models.Model):
    _name = 'property.add.fee'
    _description = "Property Add Fee"

    product_id = fields.Many2one('product.product', string='Product')
    sale_id = fields.Many2one('property.sale', string="Sale")
    qty = fields.Float(string='Qty', default=1.000, digits="Product Price", )
    name = fields.Char(string="Description", related='product_id.default_code')
    price_unit = fields.Monetary(string="Unit Price", digits="Product Price", )
    sub_total = fields.Monetary(string="SubTotal", compute='_compute_amount_total', digits="Product Price", )
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)
    company_id = fields.Many2one('res.company', string="Company", help='company',
                                 default=lambda self: self.env.company)
    move_id = fields.Many2one('account.move', string='Move')
    is_create_move = fields.Boolean(string='Create Move', default=False)

    @api.onchange('product_id', 'qty')
    def onchange_price(self):
        self.price_unit = False
        for line in self:
            price = line.product_id.lst_price
            line.price_unit = price

    @api.depends('product_id', 'price_unit', 'qty', )
    def _compute_amount_total(self):
        self.sub_total = 0
        for rec in self:
            price_total = rec.qty * rec.price_unit
            rec.sub_total = price_total

    def create_invoice(self):
        """ create Invoices"""
        today = fields.Date.today()
        move = self.env['account.move'].create({
            'partner_id': self.sale_id.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': today,
            'sale_payment_id': self.sale_id.id,

            'invoice_line_ids': [
                (0, 0, {
                    'property_sale_id': val.sale_id.id,
                    'property_add_free_id': val.id,
                    'product_id': val.product_id.id,
                    'name': val.name,
                    'quantity': val.qty,
                    'price_unit': val.price_unit,
                    'account_id': val.sale_id.account_id.id,
                }) for val in self
            ]

        })
        move.action_post()
        self.move_id = move.id
        self.is_create_move = True


class Parking(models.Model):
    _inherit = 'parking.reservation'

    property_sale_id = fields.Many2one('property.sale', string='Property Sale')



class AccountMoveLineInheritPropertySale(models.Model):
    _inherit = 'account.move.line'

    property_sale_id = fields.Many2one('property.sale', string='Property Sale')
    property_add_free_id = fields.Many2one('property.add.fee', string='Property Sale')
