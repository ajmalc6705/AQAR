# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.fields import Command
from datetime import date
from odoo.exceptions import AccessError, UserError, ValidationError


class CommunityInvoice(models.TransientModel):
    _name = 'community.invoice'
    _description = 'Community Invoice'
    # _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _inherit = ['analytic.mixin']

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    invoice_date = fields.Date(string='Invoice Date', default=date.today())
    invoice_date_due = fields.Date(string='Due Date', default=date.today())
    unit_ids = fields.Many2many('property.property', string='Units', readonly=False,
                                )
    journal_id = fields.Many2one('account.journal', string='Journal')
    account_receivable_id = fields.Many2one('account.account', string='Account Receivable',
                                            domain=[('account_type', '=', 'asset_receivable')])
    income_account_id = fields.Many2one('account.account', string='Admin Account')
    sinking_account_id = fields.Many2one('account.account', string='Sinking Account')
    community_id = fields.Many2one('property.community', string='Community')
    tax_ids = fields.Many2many('account.tax', string='Taxes', ondelete='restrict')
    unit_community_invoice_line_ids = fields.Many2many('unit.community.invoice.line',
                                                       string='Unit Community Invoice Line')
    analytic_distribution = fields.Json("Analytic Distribution", store=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', )

    @api.onchange('start_date')
    def onchange_unit(self):
        return {'domain': {'unit_ids': [('id', 'in', self.community_id.unit_ids.ids)]}}

    @api.onchange('unit_ids')
    def onchange_start_date(self):
        for rec in self.unit_ids:
            community_line = self.community_id.budget_summary_line_ids.filtered(lambda p: p.unit_id.id == rec.id)
            admin_cost = community_line.unit_admin_fund
            sink_cost = community_line.unit_sinking_fund
            if self.start_date and self.end_date:
                invoice_days = (self.end_date - self.start_date).days
                admin_price = admin_cost * invoice_days
                sink_price = sink_cost * invoice_days
                if self.unit_community_invoice_line_ids.filtered(lambda p: p.property_id.id != rec.id):
                    unit_community_line = self.env['unit.community.invoice.line'].create({
                        'property_id': rec.id,
                        'unit_admin_amount': admin_price,
                        'unit_sink_amount': sink_price
                    })
                    self.write({'unit_community_invoice_line_ids': [(4, unit_community_line.id)]})

    def check_restrict_duplicate_invoice_creation(self, unit):

        # invoice_obj = self.env['account.move'].search([('property_id', '=', unit.id),
        #                                                ('community_id', '=', self.community_id.id),
        #                                                ('state', '!=', 'cancel'),
        #                                                '|', '&', ('community_start_date', '>=', self.start_date),
        #                                                ('community_start_date', '<=', self.end_date),
        #                                                '&', ('community_end_date', '>=', self.start_date),
        #                                                ('community_end_date', '<=', self.end_date),
        #                                                ])
        invoice_obj = self.env['account.move'].search([('property_id', '=', unit.id),
                                                       ('community_id', '=', self.community_id.id),
                                                       ('state', '!=', 'cancel'),
                                                       ('community_start_date', '>=', self.start_date),
                                                       ('community_start_date', '<=', self.end_date),
                                                       ('community_end_date', '>=', self.start_date),
                                                       ('community_end_date', '<=', self.end_date),
                                                       ])

        if invoice_obj:
            raise ValidationError(_("The Invoice All redy Created Against The Unit %s  under the %s ") % (
                unit.name, self.community_id.community_seq))

    def create_invoice(self):
        """action to create invoice"""
        contract_month = relativedelta(self.community_id.contract_end_date, self.community_id.contract_start_date)

        for unit in self.unit_ids:
            self.check_restrict_duplicate_invoice_creation(unit)

            community_line = self.community_id.budget_summary_line_ids.filtered(lambda p: p.unit_id.id == unit.id)
            admin_cost = community_line.unit_admin_fund
            sink_cost = community_line.unit_sinking_fund
            invoice_days = (self.end_date - self.start_date).days + 1
            admin_price = admin_cost * invoice_days
            sink_price = sink_cost * invoice_days
            invoice_section_line = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'community_id': self.community_id.id,
                'partner_id': unit.community_landlord_id.id,
                'journal_id': self.journal_id.id,
                'property_id': unit.id,
                'building_id': self.community_id.building_id.id,
                'invoice_date': self.invoice_date,
                'invoice_date_due': self.invoice_date_due,
                'community_start_date': self.start_date,
                'community_end_date': self.end_date,
                'company_id': self.company_id.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Period as on %s to %s' % (self.start_date, self.end_date),
                        'display_type': 'line_section',
                    }),
                    Command.create({
                        'name': 'Admin Fund',
                        'display_type': 'product',
                        'price_unit': admin_price,
                        'analytic_distribution': self.analytic_distribution,
                        'quantity': 1,
                        'account_id': self.income_account_id.id,
                        'tax_ids': [(6, 0, self.tax_ids.ids)],
                        'property_id': unit.id,
                        'community_id': self.community_id.id,
                        'building_id': self.community_id.building_id.id,
                        'community_start_date': self.start_date,
                        'community_end_date': self.end_date,
                    }),
                    Command.create({
                        'name': 'Sinking Fund',
                        'display_type': 'product',
                        'analytic_distribution': self.analytic_distribution,
                        'price_unit': sink_price,
                        'quantity': 1,
                        'account_id': self.sinking_account_id.id,
                        'tax_ids': [(6, 0, self.tax_ids.ids)],
                        'community_id': self.community_id.id,
                        'property_id': unit.id,
                        'building_id': self.community_id.building_id.id,
                        'community_start_date': self.start_date,
                        'community_end_date': self.end_date,
                    })
                ],
            })
            for l in invoice_section_line.line_ids:
                payable_line = l.filtered(lambda line: line.debit != 0)
                payable_line.account_id = self.account_receivable_id.id
            self.community_id.write({'move_ids': [(4, invoice_section_line.id)]})
        self.community_id.is_invoiced = True
        self.community_id.write({'state': 'invoice'})

    class UnitCommunityInvoice(models.Model):
        _name = 'unit.community.invoice.line'
        _description = 'Unit Community Invoice Line'

        property_id = fields.Many2one('property.property', string='Unit Name')
        unit_admin_amount = fields.Float(string='Unit Admin Amount')
        unit_sink_amount = fields.Float(string='Unit Cost Amount')
