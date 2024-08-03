# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp


class InvestmentPortfolio(models.Model):
    _name = 'portfolio.investment'
    _description = 'Investment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'portfolio_name'

    portfolio_name = fields.Char("Portfolio Name")
    investment_company = fields.Many2one('res.partner', string='Investment Company',
                                         help='Name of the Investment Company',
                                         domain=[('is_investment_company', '=', True)], required=True)
    invest_company_code = fields.Char(string='Investment Company Code', help='Code of the Investment company')
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    country_id = fields.Many2one('res.country', string='Country', help='Country Name', required=True,
                                 default=lambda self: self.env.company.country_id)
    currency_id = fields.Many2one('res.currency', string='Currency', help='Currency used in the investment',
                                  default=lambda self: self.env.company.currency_id)
    investor_id = fields.Many2one('res.partner', string='Investor', help='Person/Company who is investing',
                                  domain=[('is_investor', '=', True)])
    sector_id = fields.Many2one('investment.sector', string='Sector', help='Sector Value', required=True)
    sub_sector_id = fields.Many2one('investment.subsector', string='Subsector', required=True)
    face_value = fields.Float(string='Face value', digits='Product Price',
                              help='Initial Value of a unit share at the time of listing')
    share_in_hand = fields.Float(string='Share In Hand', help="Total number of shares that owned",
                                 compute='_compute_share_in_hand', digits='Product Price')
    market_fare_value = fields.Float(string='Market Fare Value', help="Current Market Rate * Shares In Hand",
                                     compute='_compute_market_values', digits='Product Price', store=True)

    market_id = fields.Many2one('investment.market', string='Market', help="Market of the Investment")
    exchange_id = fields.Many2one('investment.exchange', string='Exchange', help="Exchange of the Investment ")
    invested_value = fields.Float(string="Invested Value", help="Sum of all Purchases - sum of all Sales",
                                  compute='_compute_market_values', digits='Product Price', )
    cost_per_share = fields.Float(string="Cost Per Share", help="Invested Value / Shares in Hand",
                                  compute='_compute_market_values', digits='Product Price', store=True)
    current_market_rate = fields.Float(string='Current Market Rate', store=True, digits='Product Price',
                                       help="Current Market rate based on updation date",
                                       compute="_compute_market_rate", readonly=1)
    paid_up_capital = fields.Float(string='Paid Up Capital', help="Paid up Capital in Amount", digits='Product Price')
    portfolio_type = fields.Selection([('portfolio_account', 'Portfolio Account'),
                                       ('assosciate_company', 'Assosciate Company'),
                                       ('subsidary_company', 'Subsidary Company')], string='Type')
    public_issue = fields.Float(string='Public Issue',
                                help="Public Issue in Number of Shares(capital/face value)",
                                digits='Product Price')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    notes = fields.Html(string="Description")
    target_date = fields.Date("Target Date", help="Target date")
    target_rate = fields.Float("Target Rate", help="Target rate", digits='Product Price')
    holding_share_percent = fields.Float(string="% Holding Shares", store=True,
                                         compute='_compute_market_values', digits='Product Price',
                                         help="shares in hand / Public Issue in Number of Shares * 100")
    purchase_count = fields.Integer(string='Purchase', compute='_compute_purchase')
    sale_count = fields.Integer(string='Sale', compute='_compute_sale')
    dividend_count = fields.Integer(string='Dividend', compute='_compute_dividend')

    def _compute_purchase(self):
        purchases = self.env['portfolio.purchase'].search_count(
            [('investment_id', '=', self.id), ('state', '=', 'done')])
        self.purchase_count = purchases

    def get_purchases(self):
        purchases = self.env['portfolio.purchase'].search([('investment_id', '=', self.id), ('state', '=', 'done')])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase',
            'view_mode': 'tree,form',
            'res_model': 'portfolio.purchase',
            'domain': [('id', 'in', purchases.ids)]
        }

    def _compute_sale(self):
        sales = self.env['portfolio.sale'].search_count(
            [('investment_id', '=', self.id), ('state', '=', 'done')])
        self.sale_count = sales

    def get_sales(self):
        sales = self.env['portfolio.sale'].search([('investment_id', '=', self.id), ('state', '=', 'done')])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales',
            'view_mode': 'tree,form',
            'res_model': 'portfolio.sale',
            'domain': [('id', 'in', sales.ids)]
        }

    def _compute_dividend(self):
        dividend = self.env['portfolio.dividend'].search_count(
            [('investment_id', '=', self.id), ('state', '=', 'done')])
        self.dividend_count = dividend

    def get_dividends(self):
        dividend = self.env['portfolio.dividend'].search([('investment_id', '=', self.id), ('state', '=', 'done')])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dividend',
            'view_mode': 'tree,form',
            'res_model': 'portfolio.dividend',
            'domain': [('id', 'in', dividend.ids)]
        }

    @api.onchange('paid_up_capital', 'face_value')
    def _onchange_capital(self):
        """ calculation of public issue in the change of capital"""
        self.public_issue = False
        if self.face_value != 0:
            self.public_issue = self.paid_up_capital / self.face_value

    @api.depends('company_id')
    def _compute_share_in_hand(self):
        """ computation of share in hand qty """
        print("PPPPPPPPP")
        for rec in self:
            share_in_hand = self.env['share.quant'].search([('investment_id', '=', rec.id)])
            print("XXXXXXXXX", share_in_hand)
            rec.share_in_hand = share_in_hand.qty

    @api.depends('share_in_hand', 'current_market_rate', 'investment_company')
    def _compute_market_values(self):
        self.market_fare_value = False
        self.invested_value = False
        self.cost_per_share = False
        self.holding_share_percent = False
        print("QQQQQQQ")
        for rec in self:
            purchase_vals = sales_vals = 0
            rec.market_fare_value = rec.share_in_hand * rec.current_market_rate
            investment_vals_purchase = self.env['portfolio.purchase'].search(
                [('investment_id', '=', rec.id), ('state', '=', 'done')])
            investment_vals_sales = self.env['portfolio.sale'].search(
                [('investment_id', '=', rec.id), ('state', '=', 'done')])
            for purchase in investment_vals_purchase:
                purchase_vals += purchase.total_amount
            for sales in investment_vals_sales:
                sales_vals = + sales.total_amount
            investment_vals = purchase_vals - sales_vals
            rec.invested_value = investment_vals
            print(rec.invested_value, rec.share_in_hand)
            if rec.share_in_hand:
                rec.cost_per_share = rec.invested_value / rec.share_in_hand
            print(rec.share_in_hand, rec.public_issue)
            if rec.public_issue:
                holding = rec.share_in_hand / (rec.public_issue * 100)
                print("hold", holding)
                # rec.holding_share_percent = holding
                rec.write({'holding_share_percent': holding})
            print(rec.holding_share_percent)

    @api.depends('investment_company')
    def _compute_market_rate(self):
        self.current_market_rate = False
        for rec in self:
            current_rate = self.env['market.updation'].search([('investment_id', '=', rec.investment_company.id)],
                                                              order="updation_date desc", limit=1)
            rec.current_market_rate = current_rate.rate

    def action_done(self):
        """ change the state done state """
        self.write({'state': 'done'})

    def action_reset_draft(self):
        """ Reset the record to draft state"""
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})
