# -*- coding: utf-8 -*-

from odoo import models,fields,api,_
from odoo.addons import decimal_precision as dp

class InvestmentAdjustments(models.Model):
    _name = 'investment.adjustment'
    _description = 'Investment Adjustments'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'doc_id'

    investment_id = fields.Many2one('portfolio.investment',string='Investment')
    doc_id = fields.Char(string='Doc ID', copy=False,
                         readonly=False,
                         index=True, default=lambda self: _('New'))
    date = fields.Date(string='Date of Entry', default=fields.Date.today())
    cut_off_date = fields.Date(string='Cut Off Date')
    shares_available = fields.Float(string='Shares Available',digits='Product Price',help='Shares available at cut off date')
    extra_share = fields.Float(string='Extra  Shares', digits='Product Price', )
    total_share = fields.Float(string='Total  Shares', digits='Product Price', )
    share_in_hand = fields.Float(string='Share In Hand', help="Total number of shares that owned",
                                 compute='_compute_share_in_hand', digits='Product Price', )
    adjustment_type = fields.Selection([('addition','Addition'),('deduction','Deduction'),],string='Type')
    method_id = fields.Many2one('adjustment.method',string='Adjustment Method')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    notes = fields.Html(string="Description")

    @api.onchange('share_in_hand','extra_share')
    def _onchange_total_share(self):
        self.total_share = self.share_in_hand + self.extra_share

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('doc_id', 'New') == 'New':
                vals['doc_id'] = self.env['ir.sequence'].next_by_code(
                    'adjustment.sequence') or 'New'
        return super(InvestmentAdjustments, self).create(vals_list)

    def action_done(self):
        """ change the state done state """
        share_investment  = self.env['share.quant']
        share_exists = share_investment.search([('investment_id','=',self.investment_id.id)])
        if self.adjustment_type == 'addition':
            if share_exists:
                share_exists.qty = share_exists.qty + self.extra_share
            else:
                investment_share = share_investment.create({
                    'investment_id': self.investment_id.id,
                    'qty': self.extra_share,

                })
        elif self.adjustment_type == 'deduction':
            if share_exists:
                share_exists.qty = share_exists.qty - self.extra_share
            else:
                investment_share = share_investment.create({
                    'investment_id': self.investment_id.id,
                    'qty': -(self.extra_share),

                })
        self.write({'state': 'done'})

    def action_reset_draft(self):
        """ Reset the record to draft state"""
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})


    @api.depends('investment_id')
    def _compute_share_in_hand(self):
        self.share_in_hand = False
        for rec in self:
            share_in_hand = self.env['share.quant'].search([('investment_id', '=', rec.investment_id.id)])
            rec.share_in_hand = share_in_hand.qty


class AdjustmentMethod(models.Model):
    _name = 'adjustment.method'
    _rec_name = 'name'
    _description = 'Adjustment Method'

    name = fields.Char(string='Method')