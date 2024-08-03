# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OverTimePayment(models.Model):
    _name = 'overtime.payment'
    _description = 'Overtime Payment'
    _rec_name = 'ref'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    ref = fields.Char(string='Reference')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    employee_overtime_line_ids = fields.One2many('employee.ot', 'ot_payment_id', string='Employee Overtime')
    state = fields.Selection([('draft','Draft'),('approve','Approved')],default='draft',string="State")
    total_bank_amount = fields.Float(string='Total Bank Amount')
    total_cash_amount = fields.Float(string='Total Cash Amount')
    account_debit_id = fields.Many2one('account.account', string='Debit Account')
    account_credit_id = fields.Many2one('account.account', string='Credit Account')
    journal_id = fields.Many2one('account.journal', string='Journal')
    move_id = fields.Many2one('account.move',string='Accounting Entry')
    create_move = fields.Boolean(string='Move',default=False)



    def action_create_entry(self):
        """ creation of entry """
        line_ids = []
        for rec in self.employee_overtime_line_ids:
            debit_values =  (0, 0, {
                'name': rec.emp_id.name,
                'account_id': self.account_debit_id.id,
                'journal_id': self.journal_id.id,
                'date': self.start_date,
                'analytic_distribution': rec.analytic_distribution,
                'debit': rec.amount,
                'credit': 0,
            })
            line_ids.append(debit_values)
            credit_values =  (0, 0, {
                'name': rec.emp_id.name,
                'account_id': self.account_credit_id.id,
                'journal_id': self.journal_id.id,
                'date': self.start_date,
                'debit': 0,
                'credit': rec.amount,

            })
            line_ids.append(credit_values)
        vals = {
            'ref': self.ref,
            'narration': self.ref,
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': self.start_date,
            'line_ids': line_ids
        }
        move = self.env['account.move'].create(vals)
        move.action_post()
        self.move_id = move.id
        self.create_move = True


    def action_approve(self):
        self.state = 'approve'


    @api.onchange('start_date', 'end_date')
    def _onchange_date(self):
        """ get ot lines based on start date and end"""
        if self.start_date and self.end_date:
            ot_requests = self.env['hr.overtime.request'].search(
                [('type', '=', 'cash')]).filtered(lambda rec: rec.date_from.date() >= self.start_date and rec.date_to.date() < self.end_date and rec.category == 'contract_employee')
            employee_ot_lines = self._get_ot_lines(self.start_date, self.end_date,ot_requests)
            self.update({'employee_overtime_line_ids': [(6, 0, [ot.id for ot in employee_ot_lines])]})
            self.total_bank_amount = sum(self.employee_overtime_line_ids.filtered(lambda rec: rec.payment_type == 'bank').mapped('amount'))
            self.total_cash_amount = sum(self.employee_overtime_line_ids.filtered(lambda rec: rec.payment_type == 'cash').mapped('amount'))

    def _get_ot_lines(self, start_date, end_date,ot_requests):
        ot_lines = []
        ot_dict = defaultdict(lambda: {'hours': 0, 'amount': 0.0})
        for ot in ot_requests:
            hours = ot.days_no_tmp
            amount = ot.cash_hrs_amount
            ot_dict[ot.employee_id.id]['hours'] += hours
            ot_dict[ot.employee_id.id]['amount'] += amount
        for key, value in ot_dict.items():
            employee = self.env['hr.employee'].browse(key)
            ot_line = self.env['employee.ot'].create({
                'emp_id': employee.id,
                'payment_type':'bank',
                'amount': value['amount'],
                'hours': value['hours']
            }
            )
            ot_lines.append(ot_line)
        return ot_lines


class EmployeeOT(models.Model):
    _name = 'employee.ot'
    _description = 'Employee OT'

    ot_payment_id = fields.Many2one('overtime.payment', string='OT Payment')
    emp_id = fields.Many2one('hr.employee', string='Employee ID')
    payment_type = fields.Selection([('bank', 'Bank'), ('cash', 'Cash')], string='Payment Type', default='bank')
    bank_ac_no = fields.Char(string='Bank A/C No', related='bank_name.acc_number')
    bank_name = fields.Many2one('res.partner.bank', string='Account Bank Name')
    amount = fields.Float(string='Amount')
    hours = fields.Float(string='Hours')
    account_analytic_id = fields.Many2one('account.analytic.account',
                                          string='Analytic Account')
    analytic_precision = fields.Integer(
        store=True,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    )
    analytic_distribution = fields.Json(
        "Analytic Distribution", store=True,
    )




