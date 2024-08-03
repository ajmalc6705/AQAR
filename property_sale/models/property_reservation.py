# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    property_sale_id = fields.Many2one('property.sale', string="Property Sale")
    is_create_sale = fields.Boolean(string='Is Create Sale', default=False)

    def create_property_sale(self):
        """ Function for create property sale"""
        sale = self.env['property.sale'].create({
            'reservation_id': self.id,
            'lead_id': self.lead_id.id,
            'partner_id': self.partner_id.id,
            'building_id': self.building_id.id,
            'unit_id': self.unit_id.id,
            'unit_type_id': self.unit_type_id.id,
            'sales_price': self.sales_price,
            'terms_conditions_id': self.terms_conditions_id.id,
            'notes': self.terms_conditions_id.description,
            'enquiry_date': self.enquiry_date,
            'offer_valid_date': self.offer_valid_date,
            'unit_sales_price': self.unit_id.sale_price,
            'specifications': self.building_id.specifications,
            'doc_ids': self.unit_id.doc_ids.ids,
            'payment_term_id': self.payment_term_id.id,
            'payment_terms': self.payment_terms,
            'payment_plan_ids': self.payment_plan_ids.ids,
            'parking_line_ids': self.parking_line_ids.ids,
            'account_receivable_id': self.building_id.account_receivable_id.id,
        })
        for rec in self.parking_reservation_ids:
            rec.state = 'confirm'
            rec.property_sale_id = sale.id
        self.property_sale_id = sale.id
        self.is_create_sale = True

    def action_sale(self):
        """ shows the Property Sale"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Property Sale',
            'view_mode': 'form',
            'res_model': 'property.sale',
            'res_id': self.property_sale_id.id,
        }


class PaymentPlan(models.Model):
    _inherit = 'payment.plan'

    sale_id = fields.Many2one('property.sale', string='Sale')
    is_create_move = fields.Boolean(string='Create Move', default=False)
    move_id = fields.Many2one('account.move', string='Move')
    parking_reservation_id = fields.Many2one('parking.reservation', string='Parking Reservation')

    @api.onchange('percent', )
    def find_untaxed_amount_sale(self):
        for rec in self:
            if rec.sale_id:
                rec.amount_untaxed = rec.sale_id.amount_untaxed * rec.percent / 100
            elif rec.parking_reservation_id:
                rec.amount_untaxed = rec.parking_reservation_id.amount_untaxed * rec.percent / 100

    @api.onchange('percent', 'amount_untaxed')
    def find_tax_amount_sale(self):
        for rec in self:
            tax_percentage = 0
            if rec.sale_id:
                for tax in rec.sale_id.tax_ids:
                    tax_percentage = tax.amount
                rec.amount_taxed = rec.amount_untaxed * tax_percentage / 100
            elif rec.parking_reservation_id:
                for tax in rec.parking_reservation_id.tax_ids:
                    tax_percentage = tax.amount
                rec.amount_taxed = rec.amount_untaxed * tax_percentage / 100

    def create_invoice(self):
        today = fields.Date.today()
        if self.sale_id:
            self.sale_id.partner_id.property_account_receivable_id = self.sale_id.account_receivable_id.id
            tax_ids = []
            for tax in self.sale_id.tax_ids:
                tax_ids.append(tax.id)
            move = self.env['account.move'].create({
                'partner_id': self.sale_id.partner_id.id,
                'move_type': 'out_invoice',
                'invoice_date': today,
                'sale_payment_id': self.sale_id.id,
                'building_id': self.sale_id.building_id.id,
                'property_id': self.sale_id.unit_id.id,
                'journal_id': self.sale_id.journal_id.id,
                'invoice_line_ids': [
                    (0, 0, {
                        'quantity': 1,
                        'price_unit': val.amount_total,
                        'account_id': val.sale_id.account_id.id,
                        'building_id': val.sale_id.building_id.id,
                        'property_id': val.sale_id.unit_id.id,
                        'tax_ids': tax_ids,
                    }) for val in self
                ]

            })
        elif self.parking_reservation_id:
            self.parking_reservation_id.partner_id.property_account_receivable_id = self.parking_reservation_id.account_receivable_id.id
            tax_ids = []
            for tax in self.parking_reservation_id.tax_ids:
                tax_ids.append(tax.id)
            move = self.env['account.move'].create({
                'partner_id': self.parking_reservation_id.partner_id.id,
                'move_type': 'out_invoice',
                'invoice_date': today,
                'building_id': self.parking_reservation_id.building_id.id,
                'journal_id': self.parking_reservation_id.journal_id.id,
                'invoice_line_ids': [
                    (0, 0, {
                        'quantity': 1,
                        'price_unit': val.amount_total,
                        'account_id': val.parking_reservation_id.account_id.id,
                        'building_id': val.parking_reservation_id.building_id.id,
                        'tax_ids':tax_ids,
                    }) for val in self
                ]

            })
        move.action_post()
        self.move_id = move.id
        self.is_create_move = True


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_payment_id = fields.Many2one('property.sale', string='Sale Payment')


class ParkingReservation(models.Model):
    _inherit = 'parking.reservation'

    payment_plan_ids = fields.One2many('payment.plan', 'parking_reservation_id', string='Payment Plans')
    journal_id = fields.Many2one('account.journal', domain=[('type', '=', 'sale')],
                                 readonly=False)
    account_id = fields.Many2one('account.account', string='Income Account',
                                 help="Account for the bill in Sale")
    account_receivable_id = fields.Many2one('account.account', string='Account Receivable',
                                            domain=[('account_type', '=', 'asset_receivable')], readonly=False,
                                            related='building_id.account_receivable_id')
