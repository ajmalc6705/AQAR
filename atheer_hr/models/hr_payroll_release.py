# -*- coding: utf-8 -*-

from __future__ import print_function
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date,datetime
from lxml import etree
import json
from dateutil.relativedelta import relativedelta
import calendar

class HrPayrollRelease(models.Model):
    _name = "hr.payroll.release"
    _description = 'HR Payroll Release'
    _inherit = ['mail.thread']

    name = fields.Char(string='No', required=True, default='/', copy=False)
    payroll_hold_id = fields.Many2one('hr.payroll.hold', domain=[('state', '=', 'on_hold')], required=True,
                                      string="Payroll Hold")
    employee_id = fields.Many2one('hr.employee', string='Employee')
    designation = fields.Many2one(comodel_name='hr.job', string="Designation")
    department = fields.Many2one(comodel_name='hr.department', string="Department")
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(comodel_name='res.currency', related='company_id.currency_id')
    date_from = fields.Date(string="Date From", required=True, readonly=False)
    date_to = fields.Date(string="Date To", required=True, readonly=False)
    effective_date = fields.Date(string="Effective Date", required=True, readonly=False,
                                 states={'released': [('readonly', True)]})
    state = fields.Selection([
        ('hr', 'HR Manager'),
        ('accounts', 'Accounts'),
        ('released', 'Released'),
        ('refuse', 'Refused'),
    ], 'Status', default='hr',
        tracking=True, copy=False)
    reason = fields.Char(string="Reason", readonly=False, states={'released': [('readonly', True)]})
    hr_remarks = fields.Char(string="HR Remarks", readonly=False)

    account_remarks = fields.Char(string="Account  Remarks", readonly=False)
    approval_person = fields.Many2one('res.users', string="Released By", readonly=True)
    today_date = fields.Date(string="Approval Date", readonly=True, store=True)
    rejected_by = fields.Many2one('res.users', string="Refused By")
    rejected_date = fields.Date(string="Refused Date")
    payslip_batch_id = fields.Many2one(comodel_name='hr.payslip.run', string='Payslip Batch')

    # access flags
    send_back_flag = fields.Boolean(default=False)
    left_hr_flag = fields.Boolean(default=False)
    left_ch_flag = fields.Boolean(default=False)
    addition_created = fields.Boolean(default=False)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.payroll.release') or '/'
        return super(HrPayrollRelease, self).create(vals)

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(HrPayrollRelease, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                            submenu=False)
        form_view_id = self.env.ref('atheer_hr.view_hr_payroll_hold_form').id
        if res.get('view_id', False) == form_view_id and res.get('type', False) == 'form':
            doc = etree.XML(res['arch'])
            if len(doc):
                if not self.env.user.has_group('atheer_hr.group_hr_manager'):
                    node = doc.xpath("//field[@name='hr_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('atheer_hr.group_hr_accounts'):
                    node = doc.xpath("//field[@name='account_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)

                return res
        return res

    @api.onchange('payroll_hold_id')
    def onchange_payroll_hold(self):
        for rec in self:
            if rec.payroll_hold_id:
                rec.employee_id = rec.payroll_hold_id.employee_id
                rec.designation = rec.payroll_hold_id.designation
                rec.department = rec.payroll_hold_id.department
                rec.date_from = rec.payroll_hold_id.date_from
                rec.date_to = rec.payroll_hold_id.date_to

    def send_to_accounts(self):
        for rec in self:
            rec.left_hr_flag = True
            rec.send_back_flag = False
            rec.payroll_hold_id.update({'payroll_release_id': self.id})
            rec.state = 'accounts'

    def send_back(self):
        """
               send backs to previous state
        """
        for rec in self:
            if rec.state == 'accounts':
                rec.state = 'hr'
                rec.send_back_flag = True

    def action_reject(self):
        for rec in self:
            rec.write({'state': 'refuse', 'rejected_by': self.env.user.id, 'rejected_date': date.today()})

    def release(self):
        if self.effective_date <= date.today():
            for rec in self:
                rec.send_back_flag = False
                rec.write({'state': 'released', 'approval_person': self.env.user.id, 'today_date': date.today()})
                rec.payroll_hold_id.cron_release()
        else:
            message_id = self.env['message.wizard'].create(
                {'message': _("Payroll will be released on the effective date")})
            return {
                'name': _('Information'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'message.wizard',
                'res_id': message_id.id,
                'target': 'new'
            }

    def current_salary(self):
        current_month_salary = 0
        for rec in self:
            date_from = datetime.today().replace(day=1).date()
            given_date = date.today()
            current_month = given_date.month
            current_year = given_date.year
            out_of_contract_salary = 0
            worked_days_salary = 0
            if rec.employee_id and rec.effective_date:
                out_of_contract_days = self.env['final.settlement'].out_of_contract(rec.employee_id,date_from,rec.effective_date)
                worked_days = self.env['hr.work.entry'].search_count(
                    [('employee_id', '=', rec.employee_id.id), ('work_entry_type_id', '!=', 'Unpaid'),
                     ('work_entry_type_id', '!=', False),
                     ('date_start', '>=', date_from), ('date_stop', '<=', rec.effective_date)])
                num_days = calendar.monthrange(current_year, current_month)[1]  # num_days = 28
                if worked_days:
                    total_worked_days = worked_days / 2
                    per_day_amount = total_worked_days / (num_days)
                    per_day_amount = round(per_day_amount, 5)
                    worked_days_salary = rec.employee_id.contract_id.wage * per_day_amount
                if out_of_contract_days:
                    out_of_contract_salary = rec.employee_id.contract_id.wage * out_of_contract_days.get('out_days',
                                                                                                         False)
                current_month_salary = worked_days_salary + out_of_contract_salary

                current_month_salary = round(current_month_salary, 5)
        return current_month_salary

    def create_addition(self):
        self.addition_created = True
        current_month_salary = self.current_salary()
        vals = {
            'employee_id': self.employee_id.id,
            'designation': self.designation.id,
            'department': self.department.id,
            'type': 'addition',
            'amount': current_month_salary,
            'effective_date': self.effective_date + relativedelta(days=1),
            'notes': 'Created from payroll release',
        }
        addition_id = self.env['hr.loan.types'].create(vals)
        if addition_id:
            message_id = self.env['message.wizard'].create(
                {'message': _("An Addition record has been created")})
            return {
                'name': _('Information'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'message.wizard',
                'res_id': message_id.id,
                'target': 'new'
            }

    def action_view_payroll_hold(self):
        return {
            'type': 'ir.actions.act_window',
            'name': ('Payroll Hold'),
            'view_mode': 'tree,form',
            'res_model': 'hr.payroll.hold',
            'target': 'current',
            'context': {'create': False},
            'domain': [('id', '=', self.payroll_hold_id.id)],
        }

    def unlink(self):
        for rec in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if rec.state not in ['hr']:
                    raise UserError(
                        _('You cannot delete the payroll release %s in the current state.', rec.name)
                    )
            return super(HrPayrollRelease, self).unlink()
