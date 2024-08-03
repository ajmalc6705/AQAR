# -*- coding: utf-8 -*-

from odoo import models,fields,api,_
from odoo.addons import decimal_precision as dp

class PortfolioSales(models.Model):
    _name = 'portfolio.sale'
    _description = 'Transactions Sale'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'doc_id'

    company_id = fields.Many2one('res.company', required=True,help="Investment Company",
                                 default=lambda self: self.env.company)
    doc_id = fields.Char(string='Doc ID', copy=False,
                         readonly=True,help="Sequence No for Share sales",
                         index=True, default=lambda self: _('New'),tracking=True)
    date = fields.Date(string='Date of Sale', default=fields.Date.today())
    currency_id = fields.Many2one('res.currency', string='Currency', help='Currency of Transaction',
                                  default=lambda self: self.env.company.currency_id)

    investment_id = fields.Many2one('portfolio.investment', string='Investment', required=True,
                                    domain=[('state', '=', 'done')],
                                    help="Investment /Portfolio")
    investment_company = fields.Many2one('res.partner', string='Investment Company', store=True,
                                         help='Name of the Investment Company',
                                         related="investment_id.investment_company")
    investor_id = fields.Many2one('res.partner', string='Investor', help='Person/Company who is investing',
                                  related="investment_id.investor_id", store=True)

    investment_type_id = fields.Many2one('investment.type', string='Investment Type',required=True,tracking=True)
    investment_broker_id = fields.Many2one('res.partner', string='Investment Broker',required=True,tracking=True,
                                            domain=[('is_investment_broker', '=', True)])
    invested_value = fields.Float(string="Invested Value", help="Sum of all Purchases - sum of all Sales",
                                  compute='_compute_market_values', digits='Product Price', )
    cost_per_share = fields.Float(string='Cost per share', digits='Product Price', help="Invested Value / Shares in Hand")
    commission = fields.Float(string='Commission',help="Commission Value")
    commission_percentage = fields.Float(string='Commission %',help="Commission / (No of Shares * Cost per Share)")
    sales_qty = fields.Float(string='Sales QTY',help="Share in Sales")
    share_in_hand = fields.Float(string='Shares in Hand', digits='Product Price',
                                 compute='_compute_share_in_hand',
                                help="Total number of shares that owned")
    total_amount = fields.Float(string='Total Amount',digits='Product Price',help="(No of Shares * Cost per Share) + Commission" )
    target_date = fields.Date(string='Target Date', default=fields.Date.today(),help="Date of the Target")
    account_id = fields.Many2one('account.account', string='Account', required=1,help="Account for the bill in Purchase")
    journal_id = fields.Many2one('account.journal', string='Journal', required=1,domain=[('type','=','sale')])
    tax_ids = fields.Many2many('account.tax', string="Taxes", help="Taxes Applied in Entry",
                               domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'sale')]")
    move_id = fields.Many2one('account.move', string='Move Entry')
    holding_share_percent = fields.Float(string="% Holding Shares", store=True,
                                         compute="_compute_holding",
                                         help="shares in hand / Public Issue in Number of Shares * 100")
    current_market_rate = fields.Float(string='Current Market Rate', store=True, digits='Product Price',
                                             compute="_compute_market_rate",help="Current Market rate based on updation date")
    sale_rate_per_share = fields.Float("Sale Rate", digits='Product Price',
                                           help="Rate of share per unit on purchase")
    analytic_distribution = fields.Json(
        "Analytic Distribution", store=True,
    )
    analytic_precision = fields.Integer(
        store=True,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    notes = fields.Html(string="Description")

    @api.depends('investment_id')
    def _compute_share_in_hand(self):
        self.share_in_hand = False
        for rec in self:
            share_in_hand = self.env['share.quant'].search([('investment_id', '=', rec.investment_id.id)])
            rec.share_in_hand = share_in_hand.qty

    @api.depends('investment_id')
    def _compute_market_rate(self):
        self.current_market_rate = False
        for rec in self:
            current_rate = self.env['market.updation'].search([('investment_id', '=', rec.investment_company.id)],
                                                              order="updation_date desc", limit=1)
            rec.current_market_rate = current_rate.rate

    @api.depends('company_id', 'investment_id')
    def _compute_market_values(self):
        self.invested_value = False
        for rec in self:
            purchase_vals = sales_vals = 0
            investment_vals_purchase = self.env['portfolio.purchase'].search(
                [('investment_id', '=', rec.investment_id.id), ('state', '=', 'done')])
            investment_vals_sales = self.env['portfolio.sale'].search(
                [('investment_id', '=', rec.investment_id.id), ('state', '=', 'done')])
            for purchase in investment_vals_purchase:
                purchase_vals += purchase.total_amount
            for sales in investment_vals_sales:
                sales_vals = + sales.total_amount
            investment_vals = purchase_vals - sales_vals
            rec.invested_value = investment_vals

    @api.onchange('share_in_hand', 'commission', 'invested_value', 'sale_rate_per_share')
    def _onchange_share(self):
        self.commission_percentage = False
        for rec in self:
            if rec.share_in_hand:
                rec.cost_per_share = rec.invested_value / rec.share_in_hand
            rec.total_amount = (rec.sales_qty * rec.sale_rate_per_share) + rec.commission
            if rec.sales_qty and rec.sale_rate_per_share:
                rec.commission_percentage = rec.commission / (rec.sales_qty * rec.sale_rate_per_share)

    @api.depends('company_id', 'investment_id', 'share_in_hand')
    def _compute_holding(self):
        """ computing % of holding """
        print("KKKKKKKKKKKKK")
        for rec in self:
            if rec.investment_id.public_issue:
                rec.holding_share_percent = rec.share_in_hand / (rec.investment_id.public_issue * 100)
            else:
                rec.holding_share_percent = 0
            print("sale, % holding", rec.holding_share_percent)

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('doc_id', 'New') == 'New':
                vals['doc_id'] = self.env['ir.sequence'].next_by_code(
                    'portfolio.sale.sequence') or 'New'
        return super(PortfolioSales, self).create(vals_list)

    def action_done(self):
        """ change the state done state """
        share_investment = self.env['share.quant']
        share_exists = share_investment.search([('investment_id', '=', self.investment_id.id)])
        if share_exists:
            share_exists.qty = share_exists.qty - self.sales_qty
        else:
            investment_share = share_investment.create({
                'investment_id': self.investment_id.id,
                'qty': -self.sales_qty,

            })
        self.action_invoice()
        self.write({'state': 'done'})

    def action_invoice(self):
        move = self.env['account.move'].create({
            'partner_id': self.investment_broker_id.id,
            'move_type': 'out_invoice',
            'invoice_date': self.date,
            'journal_id': self.journal_id.id,
            'portfolio_sale_id': self.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': val.doc_id,
                    'quantity': 1,
                    'price_unit': val.total_amount,
                    'account_id': val.account_id.id,
                    'analytic_distribution': val.analytic_distribution,
                    'tax_ids': [(6, 0, val.tax_ids.ids)]
                }) for val in self
            ]

        })
        move.action_post()
        self.move_id = move.id

    def action_reset_draft(self):
        """ Reset the record to draft state"""
        if self.state == 'done':
            share_investment = self.env['share.quant']
            share_exists = share_investment.search([('investment_id', '=', self.investment_id.id)])
            if share_exists:
                share_exists.qty = share_exists.qty + self.sales_qty
        self.write({'state': 'draft'})
        self.move_id.button_draft()

    def action_cancel(self):
        self.write({'state': 'cancel'})
        self.move_id.button_cancel()

    def get_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Invoices',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
        }

