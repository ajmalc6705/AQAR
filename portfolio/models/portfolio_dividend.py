# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp


class PortfolioDividend(models.Model):
    _name = 'portfolio.dividend'
    _description = 'Transaction Dividend'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'doc_id'

    company_id = fields.Many2one('res.company', required=True, help="Investment Company",
                                 default=lambda self: self.env.company)
    doc_id = fields.Char(string='Doc ID', copy=False,
                         readonly=False, help="Sequence No for Share Dividend",
                         index=True, default=lambda self: _('New'))
    date = fields.Date(string='Date', default=fields.Date.today())

    market_id = fields.Many2one('market.updation', string='Market Value', compute="_compute_market_rate",
                                help="Current Market rate based on updation date")
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
    investment_type_id = fields.Many2one('investment.type', string='Investment Type', required=True,
                                         help="Type of the Investment")
    investment_broker_id = fields.Many2one('res.partner', string='Investment Broker',
                                           domain=[('is_investment_broker', '=', True)], required=True)
    account_id = fields.Many2one('account.account', string='Debit Account', required=1)
    credit_account_id = fields.Many2one('account.account', string='Credit Account', required=1)
    journal_id = fields.Many2one('account.journal', string='Journal', required=1, domain=[('type', '=', 'general')])
    share_in_hand = fields.Float(string='Share In Hand', help="Total number of shares that owned",
                                 compute='_compute_share_in_hand', digits='Product Price', )
    total_dividend = fields.Float("Dividend Received", digits='Product Price')
    dividend_cut_off_date = fields.Date(string='Dividend Cut off Date')
    available_stocks = fields.Integer(string='Available Stocks', help='Stock as on dividend Cut off date',
                                      compute='_compute_available_stocks')
    face_value = fields.Integer(string='Face Value')
    dividend_percent = fields.Integer(string='Dividend %')
    amount = fields.Float(string='Amount')
    label = fields.Char("Label ")
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
    move_id = fields.Many2one('account.move', string='Move Entry')

    @api.depends('investment_id','dividend_cut_off_date')
    def _compute_available_stocks(self):
        """ compute the available stocks based on cut off date"""
        investment_purchases = sum(self.env['portfolio.purchase'].search(
            [('investment_id', '=', self.investment_id.id), ('date', '<=', self.dividend_cut_off_date),
             ('state', '=', 'done')]).mapped('no_of_shares'))
        investment_sales = sum(self.env['portfolio.sale'].search(
            [('investment_id', '=', self.investment_id.id), ('date', '<=', self.dividend_cut_off_date),
             ('state', '=', 'done')]).mapped(
            'sales_qty'))
        investment_shares_addition = sum(self.env['investment.adjustment'].search(
            [('investment_id', '=', self.investment_id.id), ('date', '<=', self.dividend_cut_off_date),
             ('state', '=', 'done'),('adjustment_type','=','addition')]).mapped(
            'extra_share'))
        investment_shares_deduction = sum(self.env['investment.adjustment'].search(
            [('investment_id', '=', self.investment_id.id), ('date', '<=', self.dividend_cut_off_date),
             ('state', '=', 'done'), ('adjustment_type', '=','deduction')]).mapped(
            'extra_share'))
        self.available_stocks = investment_purchases - investment_sales + (investment_shares_addition + -(investment_shares_deduction))

    @api.onchange('available_stocks', 'face_value', 'dividend_percent')
    def _onchange_available(self):
        self.amount = self.available_stocks * self.face_value * (self.dividend_percent / 100)

    @api.depends('investment_id')
    def _compute_market_rate(self):
        self.market_id = False
        for rec in self:
            current_rate = self.env['market.updation'].search([('investment_id', '=', rec.investment_id.id)],
                                                              order="updation_date desc", limit=1)
            rec.market_id = current_rate.id

    @api.depends('investment_id')
    def _compute_share_in_hand(self):
        self.share_in_hand = False
        for rec in self:
            share_in_hand = self.env['share.quant'].search([('investment_id', '=', rec.investment_id.id)])
            rec.share_in_hand = share_in_hand.qty

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('doc_id', 'New') == 'New':
                vals['doc_id'] = self.env['ir.sequence'].next_by_code(
                    'portfolio.dividend.sequence') or 'New'
        return super(PortfolioDividend, self).create(vals_list)

    def action_done(self):
        """ change the state done state """
        self.action_entry()
        self.write({'state': 'done'})

    def action_entry(self):
        """ create entry when transaction is done"""
        debit_vals = {
            'name': self.doc_id + self.label,
            'account_id': self.account_id.id,
            'journal_id': self.journal_id.id,
            'date': self.date,
            'currency_id': self.currency_id.id,
            'analytic_distribution': self.analytic_distribution,
            'debit': self.total_dividend,
            'credit': 0,
        }
        credit_vals = {
            'name': self.doc_id + self.label,
            'account_id': self.credit_account_id.id,
            'journal_id': self.journal_id.id,
            'date': self.date,
            'currency_id': self.currency_id.id,
            'analytic_distribution': self.analytic_distribution,
            'debit': 0,
            'credit': self.total_dividend,

        }
        vals = {
            'ref': self.doc_id + self.label,
            'narration': self.doc_id + self.label,
            'move_type': 'entry',
            'portfolio_dividend_id': self.id,
            'journal_id': self.journal_id.id,
            'date': self.date,
            'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
        }
        move = self.env['account.move'].create(vals)
        move.action_post()
        self.move_id = move.id

    def action_reset_draft(self):
        """ Reset the record to draft state"""
        self.write({'state': 'draft'})
        self.move_id.button_draft()

    def action_cancel(self):
        self.write({'state': 'cancel'})
        self.move_id.button_cancel()

    def get_entry(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dividend Entry',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
        }
