# -*- coding: utf-8 -*-

from odoo import models,fields,api,_

class PaymentPlan(models.Model):
    _name = 'payment.plan'
    _rec_name = 'reservation_id'
    _description = 'payment plan'

    amount_untaxed = fields.Monetary(string="Amount Untaxed",)
    amount_taxed = fields.Monetary(string="Amount Taxed",)
    amount_total = fields.Monetary(string="Amount Total",compute='_compute_total')
    due_date = fields.Date(string="Due Date")
    reservation_id = fields.Many2one('property.reservation', string='Reservation')
    percent = fields.Float(string='Percentage', help="percentage", digits="Product Price")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)
    company_id = fields.Many2one('res.company', string="Company", help='company',
                                 default=lambda self: self.env.company)

    @api.onchange('percent',)
    def find_untaxed_amount(self):
        for rec in self:
            if rec.reservation_id:
                rec.amount_untaxed = rec.reservation_id.amount_untaxed * rec.percent / 100

    @api.onchange('percent', 'amount_untaxed')
    def find_tax_amount(self):
        for rec in self:
            tax_percentage = 0
            if rec.reservation_id:
                for tax in rec.reservation_id.tax_ids:
                    tax_percentage = tax.amount
                rec.amount_taxed = rec.amount_untaxed * tax_percentage / 100

    @api.depends('amount_taxed','amount_untaxed')
    def _compute_total(self):
        self.amount_total = False
        for rec in self:
            rec.amount_total = rec.amount_untaxed + rec.amount_taxed
