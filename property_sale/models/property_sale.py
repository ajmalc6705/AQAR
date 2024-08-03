# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertySale(models.Model):
    _name = 'property.sale'
    _description = 'Property Sale'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'sale_seq'

    reservation_date = fields.Date(string='Reservation Date', default=fields.Date.today())
    sale_seq = fields.Char(string='Doc ID', copy=False,
                           readonly=True, help="Sequence for Sale",
                           index=True, default=lambda self: _('New'))
    sale_date = fields.Date(string="Sale Date")
    partner_id = fields.Many2one('res.partner', string='Customer')
    building_id = fields.Many2one('property.building', string='Building')
    unit_id = fields.Many2one('property.property', string='Unit')
    unit_ids = fields.Many2many('property.property', string="Unit Ids", compute='_compute_unit_ids')
    unit_type_id = fields.Many2one('property.type', string='Property Type', copy=False)
    sales_price = fields.Float(string='Sale Price', digits="Product Price", copy=False)
    parking_price = fields.Float(string='Parking Price', compute='_compute_parking_price', store=True,
                                 digits="Product Price")
    amount_untaxed = fields.Monetary(string="Amount Untaxed", )
    amount_total = fields.Monetary(string='Amount Total', help='Total Amount to be paid', )
    tax_ids = fields.Many2many('account.tax', string='Taxes', check_company=True,
                               domain="[('type_tax_use', '=', 'sale')]")
    unit_sales_price = fields.Float(string='Unit Sale Price', related='unit_id.sale_price')
    lead_id = fields.Many2one('crm.lead', string='Lead')
    reservation_id = fields.Many2one('property.reservation', string='Reservation')
    notes = fields.Html(string='Terms & Conditions')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)
    company_id = fields.Many2one('res.company', string="Company", help='company',
                                 default=lambda self: self.env.company)
    terms_conditions_id = fields.Many2one('terms.conditions', string='Terms & Conditions')
    parking_line_ids = fields.Many2many('parking.parking', string='Parking Slot')
    # parking_ids = fields.Many2many('parking.parking', compute='_compute_parking_slots')
    enquiry_date = fields.Date(string='Date of Enquiry', help="Enquiry Date")
    offer_valid_date = fields.Date(string='Offer Valid Until')
    payment_plan_ids = fields.One2many('payment.plan', 'sale_id', string='Payment Plans')
    installation_amount = fields.Monetary(string="Installment(s) Amount", compute='_compute_installation_total')
    remaining_amount = fields.Monetary(string="Remaining Amount", compute='_compute_installation_total')
    payment_term_id = fields.Many2one('payment.term', string='Payment Term')
    payment_terms = fields.Html(string='Payment Terms')
    specifications = fields.Html(string='Specifications')
    state = fields.Selection([
        ('reserve', 'Reserved'),
        ('sold', 'Sold'),
        ('cancel', 'Canceled'),
    ], string='Status', readonly=True, index=True, copy=False, default='reserve', tracking=True)
    doc_ids = fields.Many2many('atheer.documents',
                               string='Documents')
    witness_signature = fields.Char(string="Witness Sign")
    dev_signature = fields.Char(string="Developer Sign")
    partner_sign = fields.Char(string="Customer Sign")
    date_of_spa = fields.Date(string='Date of SPA', help="Date of issued SPA Document")
    area_spa = fields.Char(string="SPA Area")
    attachment_ids = fields.Many2many('ir.attachment',
                                      string="SPA Documents",
                                      help='You can attach the copy of your SPA document',
                                      copy=False)
    journal_id = fields.Many2one('account.journal', domain=[('type', '=', 'sale')], copy=False
                                 )
    account_id = fields.Many2one('account.account', string='Revenue Account',
                                 help="Account for the bill in Sale")
    move_id = fields.Many2one('account.move', string='Move')
    mulkiya_mortgage = fields.Boolean(string='Mulkiya Mortgage', default=False, compute='_compute_mulkiya')
    additional_fee_ids = fields.One2many('property.add.fee', 'sale_id', string='Additional Fees')
    mulkiya_transfer_id = fields.Many2one('property.mulkiya.transfer', string='Mulkiya Transfer')
    create_mulkiya = fields.Boolean(string='Create Mulkiya', default=False)
    mortage_bank = fields.Char(string='Mortage Bank')
    # Account Receivable
    account_receivable_id = fields.Many2one('account.account', string='Account Receivable',
                                            domain=[('account_type', '=', 'asset_receivable')], readonly=False,
                                            related='building_id.account_receivable_id')
    invoiced_amount = fields.Float(string='Invoiced Amount', compute='_compute_invoiced_amount')
    balance_amount = fields.Float(string='Balance Amount', compute='_compute_invoiced_amount', digits="Product Price",)
    resale_ids = fields.One2many('property.resale', 'sale_id', string='Resale History')
    resale_count = fields.Integer(string='Resale Count', compute='_compute_resale_count')

    def _compute_resale_count(self):
        resale_count = self.env['property.resale'].search_count([('sale_id', '=', self.id)])
        self.resale_count = resale_count

    def action_resale(self):
        """open the wizard of action resale"""
        action = self.env.ref('property_sale.action_resale_wizard').read()[0]
        company_id = self.company_id.id
        if action:
            action['context'] = {
                'default_company_id': company_id,
                'default_sale_date': self.sale_date,
                'default_amount_total': self.amount_total,
                'default_partner_id': self.partner_id.id,
                'default_sale_id': self.id}
        return action

    # @api.depends('company_id')
    # def _compute_journal(self):
    #     journal = self.env['ir.config_parameter'].sudo().get_param('property_sale.sale_journal_id')
    #     if journal:
    #         journal_id = self.env['account.journal'].browse(int(journal))
    #         self.journal_id = journal_id.id
    #     else:
    #         self.journal_id = False

    @api.depends('payment_plan_ids')
    def _compute_invoiced_amount(self):
        self.invoiced_amount = False
        self.balance_amount = False
        for rec in self:
            invoice_amount = sum(
                self.env['account.move'].search([('sale_payment_id', '=', rec.id)]).mapped('amount_total'))
            balance_amount = sum(
                self.env['account.move'].search([('sale_payment_id', '=', rec.id)]).mapped('amount_residual'))
            rec.invoiced_amount = invoice_amount
            rec.balance_amount = balance_amount

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('sale_seq', 'New') == 'New':
                vals['sale_seq'] = self.env['ir.sequence'].next_by_code(
                    'sale.sequence') or 'New'
        return super(PropertySale, self).create(vals_list)

    @api.depends('payment_plan_ids.amount_total')
    def _compute_installation_total(self):
        self.installation_amount = False
        self.remaining_amount = False
        for rec in self:
            rec.installation_amount = sum(rec.payment_plan_ids.mapped('amount_total'))
            rec.remaining_amount = rec.amount_total - rec.installation_amount

    @api.onchange('amount_untaxed', 'parking_price', 'sales_price', 'tax_ids')
    def onchange_total(self):
        """Compute the total amounts of the SO."""
        self.amount_total = 0
        tax_amount = 0
        for rec in self:
            rec.amount_untaxed = rec.parking_price + rec.sales_price
            for tax in rec.tax_ids:
                tax_amount += tax.amount
            rec.amount_total = rec.amount_untaxed + tax_amount

    @api.depends('parking_line_ids.sales_price')
    def _compute_parking_price(self):
        self.parking_price = 0
        price = 0
        for rec in self:
            price = sum(rec.parking_line_ids.mapped('sales_price'))
            rec.parking_price = price

    # @api.depends('building_id', )
    # def _compute_parking_slots(self):
    #     """ compute the parking slots """
    #     self.parking_ids = False
    #     for rec in self:
    #         park_domain = [('building_id', '=', rec.building_id.id), ('state', '=', 'available'),
    #                        ('is_sale', '=', True)]
    #         parking_slot = self.env['parking.parking'].search(park_domain)
    #         rec.parking_ids = parking_slot.mapped('id')

    @api.onchange('terms_conditions_id')
    def _onchange_terms_conditions(self):
        self.notes = self.terms_conditions_id.description

    @api.onchange('payment_term_id')
    def _onchange_payment_terms(self):
        self.payment_terms = self.payment_term_id.description

    @api.onchange('building_id')
    def _onchange_specifications(self):
        self.specifications = self.building_id.specifications

    @api.onchange('unit_id')
    def _onchange_doc(self):
        self.doc_ids = self.unit_id.doc_ids.ids

    @api.depends('building_id')
    def _compute_unit_ids(self):
        """ dynamic domain for unit"""
        self.unit_ids = False
        for rec in self:
            unit = self.env['property.property'].search(
                [('parent_building', '=', rec.building_id.id), ('state', '=', 'open'), ('for_sale', '=', True)])
            rec.unit_ids = unit.mapped('id')

    def action_reservation(self):
        """action for sale"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'view_mode': 'form',
            'res_model': 'property.reservation',
            'res_id': self.reservation_id.id,
        }

    def action_sold(self):
        """ change the state Sold state """
        self.write({'state': 'sold'})
        self.unit_id.state = 'sold'
        for rec in self.parking_line_ids:
            rec.state = 'sold'

    def action_reset_draft(self):
        """ Reset the record to draft state"""
        self.write({'state': 'reserve'})
        self.unit_id.state = 'open'
        for rec in self.parking_line_ids:
            rec.state = 'available'

    @api.depends('doc_ids')
    def _compute_mulkiya(self):
        self.mulkiya_mortgage = False
        for rec in self:
            for doc in rec.doc_ids:
                if doc.doc_type.name == 'Mulkiya Mortgage':
                    rec.mulkiya_mortgage = True

    def action_create_transfer(self):
        untaxed = self.sales_price + sum(self.parking_line_ids.mapped('sales_price'))
        transfer = self.env['property.mulkiya.transfer'].create({
            'mulkiya_mortgage': self.mulkiya_mortgage,
            'sale_id': self.id,
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
            'parking_line_ids': self.parking_line_ids.ids,
            'untaxed_amount': untaxed,
            'mortage_bank': self.mortage_bank,
        })
        self.mulkiya_transfer_id = transfer.id
        self.create_mulkiya = True

    def action_mulkiya(self):
        """ shows the Property Mulkiya"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Property Mulkiya',
            'view_mode': 'form',
            'res_model': 'property.mulkiya.transfer',
            'res_id': self.mulkiya_transfer_id.id,
        }

    def action_create_invoice(self):
        """ shows the invoice"""
        move_ids = self.payment_plan_ids.mapped('move_id')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', move_ids.ids)]
        }

    def action_view_invoice_tree(self):
        """ show the Invoices """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Summary Invoices',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('sale_payment_id', '=', self.id)],
        }

    


class PropertyBuilding(models.Model):
    _inherit = 'property.building'

    account_receivable_id = fields.Many2one('account.account', string='Account Receivable',
                                            domain=[('account_type', '=', 'asset_receivable')], )
