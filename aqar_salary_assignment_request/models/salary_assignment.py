# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SalaryAssignment(models.Model):
    _name = 'hr.salary.assignment'
    _description = 'Salary Assignment'
    _rec_name = 'ref'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    ref = fields.Char(string='Number', copy=False,
                      readonly=True,
                      index=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee')
    bank_id = fields.Many2one(comodel_name='res.bank', string='Bank', groups="hr.group_hr_user", )
    bank_name = fields.Char('Bank Name', copy=False, groups="hr.group_hr_user", )
    bank_account = fields.Char('Bank Account', copy=False, groups="hr.group_hr_user")
    new_bank_id = fields.Many2one(comodel_name='res.bank', string='New Bank', groups="hr.group_hr_user")
    new_bank_name = fields.Char('Bank Name', copy=False, groups="hr.group_hr_user")
    new_bank_account = fields.Char('Bank Account', copy=False, groups="hr.group_hr_user")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('cancel', 'Cancel')], string='Status',
                             default='draft')
    notes = fields.Html(string='Remarks')
    bank_issued = fields.Boolean(string='Bank Issued')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachment')

    @api.onchange('employee_id')
    def _onchange_employee(self):
        self.bank_id = self.employee_id.bank_id.id
        self.bank_account = self.employee_id.bank_account

    def action_cancel(self):
        """ function which triggers in cancel button"""
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        """ function that triggers when reset to draft button"""
        self.write({'state': 'draft'})

    def action_approve(self):
        """ function that triggers """
        if self.bank_issued:
            if not self.attachment_ids:
                raise UserError(_('NOC Document is mandatory '))
        self.employee_id.bank_id = self.new_bank_id.id
        self.employee_id.bank_name = self.new_bank_name
        self.employee_id.bank_account = self.new_bank_account
        self.bank_issued = True
        self.employee_id.salary_assignment_issued = True
        self.write({'state': 'confirm'})

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code(
                    'salary.assign.sequence') or 'New'
        res = super(SalaryAssignment, self).create(vals_list)
        return res


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    salary_assignment_issued = fields.Boolean(string='Salary Assignment Issued')


class HrEmployeePublicSalaryAssignmentInherit(models.Model):
    _inherit = 'hr.employee.public'

    salary_assignment_issued = fields.Boolean(string='Salary Assignment Issued')
