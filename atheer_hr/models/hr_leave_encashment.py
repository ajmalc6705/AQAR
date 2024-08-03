# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from num2words import num2words

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from odoo.tools.float_utils import float_round
from num2words import num2words
import calendar

_logger = logging.getLogger(__name__)


class HRLeaveEncashment(models.Model):
    _name = 'hr.leave.encashment'
    _description = 'Leave Encashment'
    _inherit = ['mail.thread']
    _order = 'id DESC'

    def update_payslip(self):
        if self.payslip_id:
            # self.payslip_id.compute_sheet()
            self.paylip_lines()

    @api.constrains('elg_leaves')
    @api.onchange('elg_leaves')
    def _update_annual_leave_days(self):
        """Update the annual leave days to payslip"""
        for record in self:
            remain_le = 0
            if record.employee_id:
                annual_leave_type = self.env['ir.config_parameter'].sudo().get_param('atheer_hr.annual_leave_type')
                annual_leave_alloc = self.env['hr.leave.allocation'].search([('employee_id', '=', record.employee_id.id),
                                                                             ('holiday_status_id', '=',
                                                                              int(annual_leave_type))],
                                                                            limit=1)
                avail_annual_leaves = annual_leave_alloc.eligible_days if annual_leave_alloc else 0
                if record.elg_leaves > avail_annual_leaves:
                    raise ValidationError(_('You cannot give more than eligible annual leave.'))
            if record.payslip_id:
                record.payslip_id.annual_leaves_cash = record.elg_leaves
                # record.payslip_id.compute_sheet()

    @api.depends('pay_lines')
    def total_salary(self):
        if self.pay_lines:
            total = 0.0
            for i in self.pay_lines.filtered(lambda x: x.code == 'NET'):
                total += i.total
            self.amount_total = total

    @api.depends('amount_total')
    def _amount_in_words(self):
        for record in self:
            if record.amount_total:
                currency = record.vendor_id.property_purchase_currency_id or self.env.company.currency_id
                amount_in_word = currency.amount_to_text(number=record.amount_total, currency='Riyal Omani')
                amt_l = amount_in_word['left'].replace('Hundred ', 'Hundred and ').replace('and Zero', '')
                amt_r = amount_in_word['right'].replace('Hundred ', 'Hundred and ').replace('and Zero', '')
                amount_formated_l = amt_l
                amount_formated_r = amt_r
                if (record.amount_total <= 999) and (int(record.amount_total) % 100 == 0):
                    amount_formated_l = amt_l.replace('Hundred and', 'Hundred')
                total = '%.3f' % record.amount_total
                floating_point = str(total).split('.')[1]
                if int(floating_point) and (int(floating_point) <= 999) and (int(floating_point) % 100 == 0):
                    amount_formated_r = amt_r.replace('and Baisa', 'Baisa')
                if amount_formated_r == 'Zero':
                    record.amount_in_text = amount_formated_l
                else:
                    record.amount_in_text = amount_formated_l + ' and ' + amount_formated_r

    def used_leaves(self):
        for record in self:
            if record.employee_id and not record.used_leave:
                annual_leave_type = self.env['ir.config_parameter'].sudo().get_param('atheer_hr.annual_leave_type')
                annual_leave_alloc = self.env['hr.leave.allocation'].search(
                    [('employee_id', '=', record.employee_id.id),
                     ('holiday_status_id', '=',
                      int(annual_leave_type))],
                    limit=1)
                avail_annual_leaves = annual_leave_alloc.eligible_days if annual_leave_alloc else 0
                record.used_leave = avail_annual_leaves

    @api.depends('elg_leaves', 'used_leave')
    def _leaves_remain(self):
        for record in self:
            record.leave_remaining = record.used_leave - record.elg_leaves

    name = fields.Char(string='Form No.', required=True, default='/')
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', required=True)
    date = fields.Date(string='Date Requested', copy=False, readonly=True)
    elg_leaves = fields.Float(string='Annual Leaves to Cash')
    payslip_id = fields.Many2one(comodel_name='hr.payslip', string='Payslip')
    pay_lines = fields.One2many('hr.leave.encashment.payslip', 'is_leave', string='Payslip Line')
    used_leave = fields.Float(string='Eligible Annual leave')
    leave_remaining = fields.Float(string='Remaining Annual Leaves', compute='_leaves_remain')
    amount_total = fields.Float(string='Net Payable', compute='total_salary', store=True, digits=(16, 3))
    amount_in_text = fields.Char(string='Amount in Text', compute='_amount_in_words')
    company_id = fields.Many2one(comodel_name='res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    state = fields.Selection([('draft', 'Draft'),
                              ('pa_admin', 'PA Administrator'),
                              ('p_accountant', 'Payroll Accountant'),
                              ('to_approve', 'Senior Accontant / Finanace Manager'),
                              ('approved', 'Approved'),
                              ('refuse', 'Refused'),
                              ('cancel', 'Cancel')],
                             'Status', default='draft', tracking=True, copy=False)

    def generate_leave_encash(self):
        """todo"""
        self.paylip_lines()

    def paylip_lines(self):
        if self.employee_id and self.payslip_id:
            self.used_leaves()
            lines = []
            for line in self.payslip_id.line_ids:
                values = {
                    'name': line.name,
                    'code': line.category_id.code,
                    # 'category_id': line.category_id.id,
                    # 'sequence': line.sequence,
                    'quantity': line.quantity,
                    'rate': line.rate,
                    # 'type': line.salary_rule_id.type,
                    'amount': line.amount,
                    'total': line.total
                }
                lines.append((0, 0, values))
            self.pay_lines = [(5, _, _)]
            self.pay_lines = lines
        else:
            self.pay_lines = [(5, _, _)]

    def sent_to_pa(self):
        """
        :return:
        """
        for record in self:
            if record.payslip_id:
                record.payslip_id.compute_sheet()
            if record.state == 'draft':
                record.write({'state': 'pa_admin', 'date': fields.date.today()})

    def sent_to_pa_accountant(self):
        """
        :return:
        """
        for record in self:
            if record.state in ['pa_admin']:
                if record.payslip_id:
                    # record.payslip_id.compute_sheet()
                    record.payslip_id.state = 'with_accounts_dept'
                record.paylip_lines()
                record.state = 'p_accountant'

    def sent(self):
        for record in self:
            record.state = 'to_approve'
            if record.payslip_id:
                record.payslip_id.state = 'with_finance_manager'

    def cancel(self):
        self.payslip_id.action_payslip_cancel()
        self.state = 'cancel'

    # def set_to_draft(self):
    #     self.payslip_id.state = 'draft'
    #     self.state = 'draft'

    def send_back(self):
        """
        :return:
        """
        for record in self:
            if record.state == 'pa_admin':
                record.state = 'draft'
            elif record.state == 'p_accountant':
                record.state = 'pa_admin'
                if record.payslip_id:
                    record.payslip_id.state = 'with_section'
            elif record.state == 'to_approve':
                record.state = 'p_accountant'
                if record.payslip_id:
                    record.payslip_id.state = 'with_accounts_dept'

    def approve(self):
        """

        :return:
        """
        for record in self:
            if record.payslip_id:
                record.payslip_id.action_payslip_done()
            record.state = 'approved'

    @api.model
    def create(self, values):
        if values.get('name', '/') == '/':
            values['name'] = self.env['ir.sequence'].next_by_code('hr_leave_settlement') or '/'
        return super(HRLeaveEncashment, self).create(values)

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('You can only delete draft record.'))
        return super(HRLeaveEncashment, self).unlink()


class HRLeaveEncashmentPayslip(models.Model):
    _name = "hr.leave.encashment.payslip"
    _description = 'Leave Encashment Payslip'

    is_leave = fields.Many2one(comodel_name='hr.leave.encashment')
    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    rate = fields.Float(string='Rate (%)')
    amount = fields.Float(string='Amount', digits=(16, 3))
    quantity = fields.Float(string='Quantity')
    type = fields.Selection(
        [('add', 'Additions'),
         ('remove', 'Deductions'),
         ('ls', 'Leave Salary'),
         ('grty', 'Gratuity'),
         ('l_cash', 'Leave Encashment')], string='Rule Type')
    total = fields.Float(string='Total', digits=(16, 3))
    company_id = fields.Many2one(comodel_name='res.company', string='Company', related='is_leave.company_id')
