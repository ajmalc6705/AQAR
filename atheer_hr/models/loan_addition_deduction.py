# -*- coding: utf-8 -*-

from __future__ import print_function
from datetime import date
from odoo import fields, models, api,_
from odoo.exceptions import UserError


class HrLoanTypes(models.Model):
    _name = "hr.loan.types"
    _description = 'HR Loan Types'
    _inherit = ['mail.thread']

    @api.model
    def default_get(self, fields_list):
        res = super(HrLoanTypes, self).default_get(fields_list)
        given_date = date.today()
        first_day_of_month = given_date.replace(day=1)
        self.effective_date = first_day_of_month
        res.update({'effective_date': first_day_of_month})
        return res

    name = fields.Char(string='No.', copy=False, required=True, default='/')
    employee_id = fields.Many2one('hr.employee', string='Employee ID', required=True)
    designation = fields.Many2one(string="Designation", related='employee_id.job_id')
    department = fields.Many2one(string="Department", related='employee_id.department_id', store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    amount = fields.Float(string="Amount", required=True)
    state = fields.Selection([
        ('draft', 'HR/ACCOUNTS'),
        ('approved', 'Approved')],
        'Status', default='draft',
        tracking=True, copy=False)
    type = fields.Selection([
        ('addition', 'Addition'),
        ('deduction', 'Deduction'),
    ], required=True, string="Type")
    reason_type = fields.Many2one('reason.types', domain="[('type', '=', type)]")
    effective_date = fields.Date(string="Payroll Effective Date", copy=False)
    # access flags
    left_hr_flag = fields.Boolean(default=False)

    remarks = fields.Char()
    notes = fields.Char()
    analytic_precision = fields.Integer(
        store=True,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    )
    analytic_distribution = fields.Json(
        "Analytic Distribution", store=True,
    )
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    debit_account_id = fields.Many2one('account.account', string='Debit Account', required=True)
    credit_account_id = fields.Many2one('account.account', string='Credit Account', required=True)
    accounting_date = fields.Datetime(string='Accounting Date', required=True)

    def approve(self):
        for record in self:
            move = {
                'narration': record.employee_id.name,
                'date': record.accounting_date,
                'ref': record.name + '-' + record.employee_id.name + ' -' + record.remarks if record.remarks else '',
                'journal_id': record.journal_id.id,
                'move_type': 'entry',
                'partner_id': record.employee_id.user_partner_id.id,
                'analytic_distribution': record.analytic_distribution,
            }
            line_ids = []
            debit_line = (0, 0, {
                'name':  record.employee_id.name + '-' + record.reason_type.name + ' -' + record.remarks,
                'date': record.accounting_date,
                'partner_id': record.employee_id.user_partner_id.id,
                'account_id': record.debit_account_id.id,
                'journal_id': record.journal_id.id,
                'debit': record.amount > 0.0 and record.amount or 0.0,
                'credit': record.amount < 0.0 and -record.amount or 0.0,
                'analytic_distribution': record.analytic_distribution,
            })
            line_ids.append(debit_line)

            credit_line = (0, 0, {
                'name': record.employee_id.name + '-' + record.reason_type.name + ' -' + record.remarks,
                'date': record.accounting_date,
                'partner_id': record.employee_id.user_partner_id.id,
                'account_id': record.credit_account_id.id,
                'journal_id': record.journal_id.id,
                'debit': record.amount < 0.0 and -record.amount or 0.0,
                'credit': record.amount > 0.0 and record.amount or 0.0,
                'analytic_distribution': record.analytic_distribution,
            })
            line_ids.append(credit_line)
            move_id = self.env['account.move'].create(move)
            move_id.update({'line_ids': line_ids})
            move_id.action_post()
            record.write({'move_id': move_id.id, 'state': 'approved'})

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.loan.types') or '/'
        return super(HrLoanTypes, self).create(vals)

    def unlink(self):
        for record in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if record.state != 'draft':
                    raise UserError(
                        _('You cannot delete the loan additon and deduction %s in the current state.', record.name)
                    )
            return super(HrLoanTypes, self).unlink()


class HrReasonType(models.Model):
    _name = "reason.types"
    _description = 'Reason Types'

    name = fields.Char()
    type = fields.Selection([
        ('addition', 'Addition'),
        ('deduction', 'Deduction'),
    ], 'Type', required=True, copy=False)
