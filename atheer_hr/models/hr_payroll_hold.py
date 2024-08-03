# -*- coding: utf-8 -*-

from __future__ import print_function
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date
from lxml import etree
import json


class HrPayrollHold(models.Model):
    _name = "hr.payroll.hold"
    _description = 'HR Payroll Hold'
    _inherit = ['mail.thread']

    name = fields.Char(string='No', required=True, default='/', copy=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=False,
                                  states={'approved': [('readonly', True)]})
    designation = fields.Many2one(related='employee_id.job_id')
    department = fields.Many2one('hr.department', string="Department", related='employee_id.department_id', store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    date_from = fields.Date(string="Date From", required=True, readonly=False,
                            states={'approved': [('readonly', True)]})
    date_to = fields.Date(string="Date To", required=True, readonly=False,
                          states={'approved': [('readonly', True)]})
    state = fields.Selection([
        ('hr', 'HR Manager'),
        ('accounts', 'Accounts'),
        ('on_hold', 'On Hold'),
        ('approved', 'Released'),
        ('refuse', 'Refused'),
    ], 'Status', default='hr',
        tracking=True, copy=False)
    reason = fields.Char(string="Reason", readonly=False,
                         states={'approved': [('readonly', True)]})
    hr_remarks = fields.Char(string="HR Remarks", readonly=False)

    account_remarks = fields.Char(string="Account  Remarks", readonly=False)
    approval_person = fields.Many2one('res.users', string="Approved By", readonly=True)
    today_date = fields.Date(string="Approval Date", readonly=True, store=True)
    rejected_by = fields.Many2one('res.users', string="Refused By")
    rejected_date = fields.Date(string="Refused Date")
    payslip_batch_id = fields.Many2one(comodel_name='hr.payslip.run', string='Payslip Batch')

    # access flags
    send_back_flag = fields.Boolean(default=False)
    left_hr_flag = fields.Boolean(default=False)
    left_ch_flag = fields.Boolean(default=False)

    payroll_release_id = fields.Many2one('hr.payroll.release')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.payroll.hold') or '/'
        return super(HrPayrollHold, self).create(vals)

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(HrPayrollHold, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
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

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        for rec in self:
            if rec.employee_id and rec.date_from and rec.date_to:
                payslip_id = self.env['hr.payslip'].search(
                    [('employee_id', '=', rec.employee_id.id), ('date_from', '<=', rec.date_from),
                     ('date_to', '>=', rec.date_to), ('state', '=', 'done')])
                if payslip_id:
                    raise ValidationError(_("Payslip has been already created for %s for the requested period") % (
                        str(rec.employee_id.name)))

    def send_to_accounts(self):
        for rec in self:
            rec.left_ch_flag = True
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

    def hold(self):
        for rec in self:
            rec.state = 'on_hold'

    def cron_release(self):
        payroll_hold_obj = self.env['hr.payroll.hold'].search([])
        for rec in payroll_hold_obj:
            if rec.payroll_release_id:
                if rec.payroll_release_id.effective_date <= date.today():
                    rec.send_back_flag = False
                    payslip_id = self.env['hr.payslip'].search(
                        [('employee_id', '=', rec.employee_id.id), ('date_from', '<=', rec.date_from),
                         ('date_to', '>=', rec.date_to), ('state', '=', 'hold')])
                    for record in payslip_id:
                        record.action_payslip_done()
                    rec.state = 'approved'
                    rec.payroll_release_id.state = 'released'

    def action_view_payroll_release(self):
        return {
            'type': 'ir.actions.act_window',
            'name': ('Payroll Release'),
            'view_mode': 'tree,form',
            'res_model': 'hr.payroll.release',
            'target': 'current',
            'context': {'create': False},
            'domain': [('id', '=', self.payroll_release_id.id)],
        }

    def unlink(self):
        for rec in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if rec.state not in ['hr']:
                    raise UserError(
                        _('You cannot delete the payroll hold %s in the current state.', rec.name)
                    )
            return super(HrPayrollHold, self).unlink()
