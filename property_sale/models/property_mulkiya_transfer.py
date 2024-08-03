# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertyMulkiyaTransfer(models.Model):
    _name = 'property.mulkiya.transfer'
    _description = 'Mulkiya Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'mulkiya_seq'

    partner_id = fields.Many2one('res.partner', string='Customer')
    mulkiya_seq = fields.Char(string='Mulkiya Seq', copy=False,
                                  readonly=True, help="Sequence for Mulkiya Transfer", index=True, default=lambda self: _('New'))
    building_id = fields.Many2one('property.building', string='Building')
    unit_id = fields.Many2one('property.property', string='Unit')
    unit_ids = fields.Many2many('property.property', string="Unit Ids", compute='_compute_unit_ids')
    unit_type_id = fields.Many2one('property.type', string='Property Type')
    sales_price = fields.Float(string='Sale Price', )
    sale_id = fields.Many2one('property.sale',string='Property Sale')
    enquiry_date = fields.Date(string='Date of Enquiry', help="Enquiry Date")
    offer_valid_date = fields.Date(string='Offer Valid Until')
    mulkiya_transfer_date = fields.Date(string='Mulkiya Transfer Date',default=fields.Date.today())
    mulkiya_mortgage = fields.Boolean(string='Mulkiya Mortgage',default=False)
    doc_ids = fields.Many2many('atheer.documents',
                               string='Documents')
    notes = fields.Html(string='Terms & Conditions')
    unit_sales_price = fields.Float(string='Unit Sale Price', related='unit_id.sale_price')
    payment_term_id = fields.Many2one('payment.term', string='Payment Term')
    payment_terms = fields.Html(string='Payment Terms')
    specifications = fields.Html(string='Specifications')
    parking_price = fields.Float(string='Parking Price', compute='_compute_parking_price')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)
    company_id = fields.Many2one('res.company', string="Company", help='company',
                                 default=lambda self: self.env.company)
    terms_conditions_id = fields.Many2one('terms.conditions', string='Terms & Conditions')
    stage_id = fields.Many2one('mulkiya.stages',string='Stages',default=lambda self: self.env.ref('property_sale.new_stage'))
    parking_line_ids = fields.Many2many('parking.parking', string='Parking Slot')
    untaxed_amount = fields.Float(string='Untaxed Amount',compute='_compute_untaxed_amount')
    mortage_bank = fields.Char(string='Mortage Bank')
    inform_bank = fields.Char(string='Informed to Bank')
    balance_amount = fields.Float(string='Balance Amount', related='sale_id.balance_amount')

    @api.depends('parking_price','sales_price')
    def _compute_untaxed_amount(self):
        """ compute the untaxed amount"""
        self.untaxed_amount = False
        for rec in self:
            rec.untaxed_amount = rec.parking_price + rec.sales_price

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('mulkiya_seq', 'New') == 'New':
                vals['mulkiya_seq'] = self.env['ir.sequence'].next_by_code(
                    'mulkiya.sequence') or 'New'
        return super(PropertyMulkiyaTransfer, self).create(vals_list)

    @api.onchange('payment_term_id')
    def _onchange_payment_terms(self):
        self.payment_terms = self.payment_term_id.description

    @api.onchange('unit_id')
    def _onchange_doc(self):
        self.doc_ids = self.unit_id.doc_ids.ids

    @api.onchange('building_id')
    def _onchange_specifications(self):
        self.specifications = self.building_id.specifications

    @api.depends('building_id')
    def _compute_unit_ids(self):
        """ dynamic domain for unit"""
        self.unit_ids = False
        for rec in self:
            unit = self.env['property.property'].search([('parent_building', '=', rec.building_id.id)])
            rec.unit_ids = unit.mapped('id')

    @api.depends('parking_line_ids.sales_price')
    def _compute_parking_price(self):
        self.parking_price = 0
        price = 0
        for rec in self:
            price = sum(rec.parking_line_ids.mapped('sales_price'))
            rec.parking_price = price



    def action_sale(self):
        """ shows the Property Sale"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Property Sale',
            'view_mode': 'form',
            'res_model': 'property.sale',
            'res_id': self.sale_id.id,
        }


