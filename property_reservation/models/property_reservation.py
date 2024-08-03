# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertyReservation(models.Model):
    _name = 'property.reservation'
    _description = 'Property Reservation'
    _rec_name = 'reservation_seq'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    reservation_date = fields.Date(string='Reservation Date', default=fields.Date.today())
    reservation_seq = fields.Char(string='Doc ID', copy=False,
                                  readonly=True, help="Sequence for Reservation",
                                  index=True, default=lambda self: _('New'))
    sale_date = fields.Date(string="Sale Date")
    partner_id = fields.Many2one('res.partner', string='Customer')
    building_id = fields.Many2one('property.building', string='Building')
    unit_id = fields.Many2one('property.property', string='Unit')
    unit_ids = fields.Many2many('property.property', string="Unit Ids", compute='_compute_unit_ids')
    unit_type_id = fields.Many2one('property.type', string='Property Type', related="unit_id.property_type_id")
    sales_price = fields.Float(string='Sale Price', digits='Product Price', )
    parking_price = fields.Float(string='Parking Price', compute='_compute_parking_price', digits='Product Price', )
    amount_untaxed = fields.Monetary(string="Amount Untaxed", compute='_compute_total',
                                     help="Sum of sales price and parking price", digits='Product Price', )
    amount_total = fields.Monetary(string='Amount Total', help='Total Amount to be paid', compute='_compute_total',
                                   digits='Product Price', )
    tax_amount = fields.Monetary(string=' Tax Amount', help='tax Amount to be paid', compute='_compute_total',
                                 digits='Product Price', )
    tax_ids = fields.Many2many('account.tax', string='Taxes',
                               domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'sale')]")
    unit_sales_price = fields.Float(string='Unit Sale Price', related='unit_id.sale_price', digits='Product Price', )
    lead_id = fields.Many2one('crm.lead', string='Lead')
    notes = fields.Html(string='Terms & Conditions')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, required=True)
    company_id = fields.Many2one('res.company', string="Company", help='company',
                                 default=lambda self: self.env.company)
    terms_conditions_id = fields.Many2one('terms.conditions', string='Terms & Conditions')
    parking_line_ids = fields.Many2many('parking.parking', 'reservation_id', string='Parking Slot')
    parking_ids = fields.Many2many('parking.parking', compute='_compute_parking_slots')
    enquiry_date = fields.Date(string='Date of Enquiry', help="Enquiry Date")
    offer_valid_date = fields.Date(string='Offer Valid Until')
    payment_plan_ids = fields.One2many('payment.plan', 'reservation_id', string='Payment Plans')
    installation_amount = fields.Monetary(string="Installment Amount", compute='_compute_installation_total',
                                          digits='Product Price', )
    remaining_amount = fields.Monetary(string="Remaining Amount", compute='_compute_installation_total',
                                       digits='Product Price', )
    payment_term_id = fields.Many2one('payment.term', string='Payment Term')
    payment_terms = fields.Html(string='Payment Terms')
    specifications = fields.Html(string='Specifications')
    report_template = fields.Html(string='Report template')
    state = fields.Selection([
        ('sale_offer', 'Sales Offer'),
        ('reserve', 'Reserved'),
        ('cancel', 'Canceled'),
    ], string='Status', readonly=True, index=True, copy=False, default='sale_offer', tracking=True)
    doc_ids = fields.Many2many('atheer.documents',
                               string='Documents')
    witness_signature = fields.Binary(string="Witness Sign", copy=False,
                                      attachment=True, tracking=True)
    dev_signature = fields.Binary(string="Developer Sign", copy=False,
                                  attachment=True, tracking=True)
    partner_sign = fields.Binary(string="Customer Sign", copy=False,
                                 attachment=True, tracking=True)
    parking_reservation_ids = fields.Many2many('parking.reservation',string='Parking Reservation')

    def offer_valid_notification(self):
        """offer valid notification"""
        today = fields.Date.today()
        doc = self.search([('offer_valid_date', '>=', today)])
        for rec in doc:
            rec.unit_id.state = 'available'

    # Property Sale

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('reservation_seq', 'New') == 'New':
                vals['reservation_seq'] = self.env['ir.sequence'].next_by_code(
                    'reservation.sequence') or 'New'
        return super(PropertyReservation, self).create(vals_list)

    @api.depends('payment_plan_ids.amount_total')
    def _compute_installation_total(self):
        self.installation_amount = False
        self.remaining_amount = False
        for rec in self:
            rec.installation_amount = sum(rec.payment_plan_ids.mapped('amount_total'))
            rec.remaining_amount = rec.amount_total - rec.installation_amount

    @api.depends('amount_untaxed', 'parking_price', 'sales_price', 'tax_ids')
    def _compute_total(self):
        """Compute the total amounts of the SO."""
        self.amount_total = 0
        tax_amount = 0
        for rec in self:
            rec.amount_untaxed = rec.parking_price + rec.sales_price
            for tax in rec.tax_ids:
                cal_amount = (tax.amount / 100 * rec.amount_untaxed)
                tax_amount += cal_amount
            rec.amount_total = rec.amount_untaxed + tax_amount
            rec.tax_amount = tax_amount

    @api.depends('parking_line_ids.sales_price')
    def _compute_parking_price(self):
        self.parking_price = 0
        price = 0
        for rec in self:
            price = sum(rec.parking_line_ids.mapped('sales_price'))
            rec.parking_price = price

    @api.depends('building_id', )
    def _compute_parking_slots(self):
        """ compute the parking slots """
        self.parking_ids = False
        for rec in self:
            park_domain = [('building_id', '=', rec.building_id.id), ('state', '=', 'available'),
                           ('is_sale', '=', True)]
            parking_slot = self.env['parking.parking'].search(park_domain)
            rec.parking_ids = parking_slot.mapped('id')

    @api.onchange('terms_conditions_id')
    def _onchange_terms_conditions(self):
        self.notes = self.terms_conditions_id.description

    @api.onchange('payment_term_id')
    def _onchange_payment_terms(self):
        self.payment_terms = self.payment_term_id.description

    @api.onchange('building_id')
    def _onchange_specifications(self):
        self.specifications = self.building_id.specifications
        self.report_template = self.env['ir.config_parameter'].sudo().get_param('property_reservation.report_template')

    @api.onchange('unit_id')
    def _onchange_doc(self):
        self.doc_ids = self.unit_id.doc_ids.ids

    @api.depends('building_id')
    def _compute_unit_ids(self):
        """ dynamic domain for unit"""
        self.unit_ids = False
        for rec in self:
            unit = self.env['property.property'].search([('parent_building', '=', rec.building_id.id)])
            rec.unit_ids = unit.mapped('id')

    def action_lead(self):
        """ shows the lead"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lead',
            'view_mode': 'form',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
        }

    def action_reserve(self):
        """ change the state Sold state """
        self.write({'state': 'reserve'})
        self.unit_id.state = 'reserve'
        for rec in self.parking_line_ids:
            parking_reservation = self.env['parking.reservation'].create({
                'building_id': self.building_id.id,
                'unit_ids': self.unit_id.ids,
                'partner_id': self.partner_id.id,
                'parking_slot_ids': rec.ids,
                'state': 'reserved'
            })
            self.write({'parking_reservation_ids': [(4, parking_reservation.id)]})
            rec.state = 'reserved'

    def action_reset_draft(self):
        """ Reset the record to draft state"""
        self.write({'state': 'sale_offer'})
        self.unit_id.state = 'open'
        for rec in self.parking_line_ids:
            rec.state = 'available'
