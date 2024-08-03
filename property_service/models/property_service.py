# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PropertyService(models.Model):
    _name = 'property.service'
    _description = 'Property Service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "service_seq"

    name = fields.Char(string="Name", help="name of the service")
    service_seq = fields.Char(string='Sequence', copy=False,
                              readonly=True, help="Sequence for Service Sequence",
                              index=True, default=lambda self: _('New'))
    crm_id = fields.Many2one('crm.lead', string='CRM')
    partner_id = fields.Many2one('res.partner', string='Partner')
    contract_id = fields.Many2one('aqar.contract', string='Contract')
    start_date = fields.Date(string="Contract Start Date", related='contract_id.start_date')
    end_date = fields.Date(string="Contract End Date", related='contract_id.end_date')
    contract_categ_id = fields.Many2one('aqar.contract.category', string='Contract Category',
                                        related='contract_id.contract_categ_id')
    contract_type = fields.Selection([
        ('issues', 'Issues'),
        ('receipt', 'Receipt')], string='Contract Type', related='contract_id.contract_type')
    building_id = fields.Many2one('property.building', string='Building')
    unit_id = fields.Many2one('property.property', string='Unit')
    unit_ids = fields.Many2many('property.property', string="Unit Ids", compute='_compute_unit_ids')
    contract_service_type = fields.Selection([('A/C_maintenance', 'A/C Maintenance'), ('pest_control', 'Pest Control'),
                                              ('lease_agency_service', 'Lease Agency Service'),
                                              ('sale_agency', 'Sale Agency Service'),
                                              ('exit_inspection', 'Exit Inspection'),
                                              ('others', 'Others')], string='Contract Service Type', copy=False)
    service = fields.Char(string='Service', copy=False)
    monthly_rent = fields.Float(string='Monthly Rent', copy=False)
    periods_in_months = fields.Integer(string="Periods In Months", copy=False)
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    total_amount = fields.Float(string='Deal Amount', copy=False)
    sale_agency_amount = fields.Float(string='Sale Amount', copy=False)
    commission_percent = fields.Float(string='Commission %', copy=False)
    commission_amount = fields.Float(string='Commission Amount', copy=False)
    # stage_id = fields.Many2one('service.stage', string='Stage',
    #                            default=lambda self: self.env.ref('property_service.quotation_stage'))
    state = fields.Selection([('draft', 'Quotation'), ('running', 'Running'), ('done', 'Completed'),
                              ('cancel', 'Canceled')], default='draft', tracking=True, copy=False)
    service_line_ids = fields.One2many('property.service.line', 'service_id', string='Order Line', copy=False)
    amount_total = fields.Monetary(string='Amount Total', store=True, help='Total Amount to be paid',
                                   compute='_compute_total', tracking=True, digits=(12, 3))
    amount_untaxed = fields.Monetary(string="Amount Untaxed", store=True, compute='_compute_total', tracking=True,
                                     digits=(12, 3), copy=False)
    sale_id = fields.Many2one('sale.order', string="Sale Order", copy=False)
    purchase_id = fields.Many2one('purchase.order', string="Purchase Order", copy=False)
    is_create_sale = fields.Boolean(string='Sale', default=False, copy=False)
    is_create_purchase = fields.Boolean(string='Purchase', default=False, copy=False)
    company_id = fields.Many2one('res.company', string="Company", help='company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)
    document_ids = fields.Many2many('atheer.documents', 'rel_document_property_service', 'document_id',
                                    'property_service_id', string='Documents', copy=False)

    @api.depends('service_line_ids.sub_total', 'service_line_ids.price_reduce')
    def _compute_total(self):
        """Compute the total amounts of the SO."""
        for order in self:
            order_lines = order.service_line_ids.filtered(lambda x: x.service_id)
            order.amount_total = sum(order_lines.mapped('price_reduce'))
            order.amount_untaxed = sum(order_lines.mapped('sub_total'))

    @api.onchange('contract_service_type', 'commission_amount')
    def _onchange_contract_service_type(self):
        """ onchange the contract service Type """
        if self.contract_service_type:
            product = False
            if self.contract_service_type == 'A/C_maintenance':
                product = self.env.ref('property_service.A/C_maintenance_product')
            elif self.contract_service_type == 'pest_control':
                product = self.env.ref('property_service.pest_control_product')
            elif self.contract_service_type == 'lease_agency_service':
                product = self.env.ref('property_service.lease_agency_product')
            elif self.contract_service_type == 'sale_agency':
                product = self.env.ref('property_service.sale_agency_product')
            elif self.contract_service_type == 'exit_inspection':
                product = self.env.ref('property_service.exit_inspection_product')
            elif self.contract_service_type == 'others':
                product = self.env.ref('property_service.others_product')
            service_lines = self.env['property.service.line'].create({
                'product_id': product.id,
                'name': product.name,
                'qty': 1,
                'price_unit': self.commission_amount
            })
            self.update({'service_line_ids': [(6, 0, [penalty_line.id for penalty_line in service_lines])]})

    @api.onchange('crm_id', )
    def onchange_crm_id(self):
        for rec in self:
            if rec.crm_id:
                rec.partner_id = rec.crm_id.partner_id
                rec.building_id = rec.crm_id.building_id
                rec.unit_id = rec.crm_id.unit_id

    @api.onchange('monthly_rent', 'periods_in_months', 'commission_percent', 'sale_agency_amount')
    def onchange_total(self):
        if self.contract_service_type == "sale_agency":
            self.total_amount = self.sale_agency_amount
        else:
            self.total_amount = self.monthly_rent * self.periods_in_months
        self.commission_amount = self.total_amount * (self.commission_percent / 100)

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('service_seq', 'New') == 'New':
                vals['service_seq'] = self.env['ir.sequence'].next_by_code(
                    'service.sequence') or 'New'
        return super(PropertyService, self).create(vals_list)

    @api.depends('building_id')
    def _compute_unit_ids(self):
        """ dynamic domain for unit"""
        self.unit_ids = False
        for rec in self:
            unit = self.env['property.property'].search(
                [('parent_building', '=', rec.building_id.id), ('for_service', '=', True)])
            rec.unit_ids = unit.mapped('id')

    def action_create_sale(self):
        """ create sale order from property service"""
        sale = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [(0, 0, {
                'name': val.name,
                'product_id': val.product_id.id,
                'product_uom_qty': val.qty,
                'price_unit': val.price_unit,
                'discount': val.discount,
                'tax_id': [(6, 0, val.tax_ids.ids)],
                'price_subtotal': val.sub_total,
            }) for val in self.service_line_ids],
            'amount_total': self.amount_total,
            'amount_untaxed': self.amount_untaxed,
            'property_service_id': self.id
        })
        self.sale_id = sale.id
        self.is_create_sale = True

    def action_create_purchase(self):
        """ create Purchase order from property service"""
        purchase = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [(0, 0, {
                'name': val.name,
                'product_id': val.product_id.id,
                'product_uom_qty': val.qty,
                # 'price_unit': val.price_unit,
                # 'taxes_id': [(6, 0, val.tax_ids.ids)],
                # 'price_subtotal': val.sub_total,
            }) for val in self.service_line_ids],
            # 'amount_total': self.amount_total,
            # 'amount_untaxed': self.amount_untaxed,
            'property_service_id': self.id
        })
        self.purchase_id = purchase.id
        self.is_create_purchase = True

    def action_sale(self):
        """ show the sale"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': self.sale_id.id,
        }

    def action_purchase(self):
        """ show the Purchase"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': self.purchase_id.id,
        }

    def button_action_running(self):
        """ Change State  Draft into Running"""
        for rec in self:
            rec.write({'state': 'running'})

    def button_action_done(self):
        """ Change State  Draft into Running"""
        for rec in self:
            rec.write({'state': 'done'})

    def button_action_cancel(self):
        """ Change State  Draft into Running"""
        for rec in self:
            if rec.sale_id.state != 'draft':
                raise ValidationError(_("You cannot cancel a Sale Order  '%s' not in Draft state", rec.service_seq))
            else:
                rec.sale_id.write({'cancel_reason': "Due to Cancel the '%s' Services "}, rec.service_seq)
                rec.sale_id.action_cancel()
            rec.write({'state': 'cancel'})


class ServiceOrderLine(models.Model):
    _name = 'property.service.line'
    _rec_name = 'product_id'
    _description = 'Property service line'

    product_id = fields.Many2one('product.product', string='Product')
    qty = fields.Float(string="Quantity", default='1.00', digits='Discount')
    name = fields.Char(string="Description", )
    price_unit = fields.Monetary(string="Unit Price", readonly=False, digits='Discount')
    sub_total = fields.Monetary(string="SubTotal", store=True, compute='_compute_amount_total', digits=(16, 4))
    tax_ids = fields.Many2many('account.tax', string="Taxes", readonly=False)
    discount = fields.Float(string="Discount (%)", digits='Discount', )
    price_reduce = fields.Monetary(string='Price Reduce', compute='_compute_price_reduce')
    service_id = fields.Many2one('property.service', string="Service")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)
    company_id = fields.Many2one('res.company', string="Company", help='company',
                                 default=lambda self: self.env.company)
    is_create_sale = fields.Boolean(string='Sale', related="service_id.is_create_sale")

    @api.onchange('product_id')
    def _onchange_product(self):
        self.name = self.product_id.name
        if self.product_id.default_code:
            self.name = '[' + self.product_id.default_code + ']' + self.product_id.name

    @api.depends('product_id', 'price_unit', 'qty', 'discount')
    def _compute_amount_total(self):
        self.sub_total = False
        for rec in self:
            price_total = rec.qty * rec.price_unit
            if rec.discount:

                rec.sub_total = price_total * (1 - (rec.discount / 100))
            else:
                rec.sub_total = price_total

    @api.onchange('product_id', 'qty')
    def onchange_price(self):
        self.price_unit = False
        if self.product_id.default_code:
            self.name = '[' + self.product_id.default_code + ']' + self.product_id.name
        else:
            self.name = self.product_id.name
        for line in self:
            price = line.product_id.lst_price
            line.price_unit = price

    @api.onchange('product_id', )
    def onchange_tax(self):
        self.tax_ids = False
        for line in self:
            line.tax_ids = line.product_id.taxes_id

    @api.depends('price_unit', 'discount', 'tax_ids')
    def _compute_price_reduce(self):
        self.price_reduce = False
        for line in self:
            tax_amount = 0
            for tax in line.tax_ids:
                tax_amount += (tax.amount / 100) * line.sub_total
            line.price_reduce = line.sub_total + tax_amount


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    property_service_id = fields.Many2one('property.service', string='Service')


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    property_service_id = fields.Many2one('property.service', string='Service')


class PropertyProperty(models.Model):
    _inherit = 'property.property'

    for_service = fields.Boolean(string=' For Service', default=False)
