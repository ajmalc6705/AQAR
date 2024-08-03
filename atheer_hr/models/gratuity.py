# -*- coding: utf-8 -*-

import calendar
from datetime import timedelta
from odoo import fields, models, api


class HrGratuity(models.Model):
    _name = "hr.gratuity"
    _rec_name = "name"
    _description = 'HR Gratuity'
    _inherit = ['mail.thread']

    name = fields.Char(string='No', required=True, default='/')
    employee_category = fields.Selection([
        ('expat_staff', 'Expat Staff'),
        ('expat_labor', 'Expat Labor'),
    ], string='Employee Category', copy=False, index=True)
    employee_id = fields.Many2one('hr.employee', string='Employee ID', required=True)
    designation = fields.Many2one(related='employee_id.job_id')
    department = fields.Many2one('hr.department', string="Department", related='employee_id.department_id', store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)

    state = fields.Selection([
        ('hr', 'HR Manager'),
        ('approved', 'Approved'),
    ], 'Status', default='hr',
        tracking=True, copy=False)
    reason = fields.Char(string="Reason")
    struct_id = fields.Many2one('hr.payroll.structure', string="Salary Structure", related='contract_id.salary_structure_id')
    contract_id = fields.Many2one('hr.contract', related='employee_id.contract_id', string='Current Contract', required=True)
    date = fields.Date(default=fields.Date.today())
    gratuity_days = fields.Float(string="Gratuity Days", compute='compute_gratuity_amount')
    gratuity_amount = fields.Float(string="Gratuity Amount", compute='compute_gratuity_amount')
    basic_salary = fields.Monetary(string="Joining Salary", related='employee_id.contract_id.wage')
    joining_date = fields.Date(string="Joining Date", related='employee_id.joining_date')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.loan.adjustments') or '/'
        return super(HrGratuity, self).create(vals)

    def approve(self):
        for rec in self:
            rec.state = 'approved'

    @api.depends('employee_id', 'date_from', 'date_to')
    def compute_gratuity_amount(self):
        for rec in self:
            if rec.employee_id and rec.date_from and rec.date_to:
                no_of_days = (rec.date_to - rec.date_from).days
                year_days = 366 if calendar.isleap(fields.date.today().year) else 365
                if no_of_days:
                    daily_rate = (rec.contract_id.wage * 12) / year_days
                    unpaid_leave_share = 0.0
                    total_unpaid_leaves = 0.0
                    holiday_type = self.env['hr.leave.type'].search([('is_unpaid', '=', True)], limit=1)
                    unpaid_leaves = self.env['hr.leave'].search([('holiday_status_id', '=', holiday_type.id),
                                                                 ('employee_id', '=', rec.id),
                                                                 ('date_from', '<=', rec.date_to),
                                                                 ('date_to', '>=', rec.date_from),
                                                                 ('state', '=', 'validate')])
                    for i in unpaid_leaves:
                        total_unpaid_leaves += i.number_of_days
                    total_working_days = no_of_days - total_unpaid_leaves
                    rec.gratuity_amount = daily_rate * total_working_days
                    rec.gratuity_days = total_working_days
            else:
                rec.gratuity_amount = 0.0
                rec.gratuity_days = 0
