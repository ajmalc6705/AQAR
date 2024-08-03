# -*- coding: utf-8 -*-

from __future__ import print_function
from odoo import fields, models, api, _
from datetime import date
from odoo.exceptions import UserError, ValidationError
from lxml import etree
import json


class HrResignation(models.Model):
    _name = "hr.resignation"
    _description = 'HR Resignation'
    _inherit = ['mail.thread']

    def _default_employee(self):
        if self.env.user.has_group('atheer_hr.group_hr_employee_staff'):
            return self.env.user.employee_id

    def _default_type(self):
        if self.env.user.has_group('atheer_hr.group_hr_employee_staff') or self.env.user.has_group(
                'atheer_hr.group_hr_site_engineer'):
            resignation_type = 'normal_resignation'
            return resignation_type

    def get_employee_domain(self):
        if self.env.user.has_group('atheer_hr.group_hr_site_engineer') and not self.env.user.has_group(
                'atheer_hr.group_hr_manager') and not self.env.user.has_group(
            'atheer_hr.group_hr_ceo') and not self.env.user.has_group(
            'atheer_hr.group_hr_accounts') and not self.env.user.has_group(
            'atheer_hr.group_hr_employee_staff') and not self.env.user.has_group(
            'atheer_hr.group_hr_line_manager'):
            employee_ids = self.env['hr.employee'].search(
                ['|', ('employee_category', 'in', ['expat_labor', 'omani_labor']),
                 ('user_id', '=', self.env.user.id)]).ids
            result = [('id', 'in', employee_ids)]
        else:
            result = []
        return result

    def dynamic_selection_type(self):
        if self.env.user.has_group('atheer_hr.group_hr_manager') and not self.env.user.has_group(
                'atheer_hr.group_hr_ceo') and not self.env.user.has_group(
            'atheer_hr.group_hr_accounts') and not self.env.user.has_group(
            'atheer_hr.group_hr_site_engineer') and not self.env.user.has_group(
            'atheer_hr.group_hr_line_manager'):
            select = [('normal_resignation', 'Resignation'), ('termination', 'Termination'),
                      ('absconding', 'Absconding'), ('exit_process', 'Cancel- 180 days completion')]
        else:
            select = [('normal_resignation', 'Resignation'), ('termination', 'Termination'),
                      ('absconding', 'Absconding'), ('exit_process', 'Cancel- 180 days completion')]
        return select

    name = fields.Char(string='No.', copy=False, required=True, default='/')
    employee_id = fields.Many2one('hr.employee', string='Employee', domain=get_employee_domain,
                                  default=_default_employee, required=True)
    designation = fields.Many2one(related='employee_id.job_id', string="Designation")
    employee_category = fields.Selection(related='employee_id.employee_category')
    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id',
                                    store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('line_manager', 'Line Manager'),
        ('hr', 'HR Manager'),
        ('ceo', 'CEO'),
        ('finance', 'Finance'),
        ('approved', 'Approved'),
        ('reject', 'Refused')
    ], string='Status', default='draft', tracking=True, copy=False)
    joining_date = fields.Date(string="Joining Date", related='employee_id.joining_date')
    resign_date = fields.Date(string="Resign Date", required=True)
    type = fields.Selection(selection=[('normal_resignation', 'Resignation'), ('termination', 'Termination'),
                                       ('absconding', 'Absconding'), ('exit_process', 'Cancel- 180 days completion'),
                                       ('death', 'Death')],
                            required=True, default=_default_type,
                            string="Resignation Type")
    evaluation = fields.Many2one('performance.evaluation', string="Evaluation")
    location = fields.Char(string="Location")
    need_final_settlement = fields.Boolean(string='Need Final Settlement',default=False)
    final_settlement = fields.Boolean(string='Create Final Settlement',default=False)

    lm_remark = fields.Char(string="Line Manager Remark")
    hr_remark = fields.Char(string="HR Remark")
    ceo_remark = fields.Char(string="CEO Remark")
    acc_remark = fields.Char(string="Finance Remark")
    employee_remark = fields.Char(string="Employee Remark")
    reason_for_resignation = fields.Char(string='Reason for Resignation')
    provision_for_notice = fields.Date(string='Provision for Notice Period')

    travel_date = fields.Date(string="Travel Date", required=True)
    confirmed_travel_date = fields.Date(string="Confirmed Travel Date", required=True)
    rejected_by = fields.Many2one('res.users')
    rejected_date = fields.Date(string="Rejected Date")

    # access flags
    labor_flag = fields.Boolean(default=False)
    send_back_flag = fields.Boolean(default=False)
    left_emp_flag = fields.Boolean(default=False)
    left_se_flag = fields.Boolean(default=False)
    left_hr_flag = fields.Boolean(default=False)
    left_lm_flag = fields.Boolean(default=False)

    lm_user_id = fields.Many2one('res.users', compute='compute_user_id', store=True, tracking=True,
                                 help='Line manager of the employee')
    # for labor type: other 3 types except resignation
    left_pm_flag = fields.Boolean(default=False)
    # # for labor type: other 2 types except resignation
    pm_user_id = fields.Many2one('res.users', compute='compute_user_id', store=True, tracking=True,
                                 help='Project Manager of the employee')

    def create_final_settlement(self):
        final_settlement = self.env['final.settlement'].create({
            'employee_id': self.employee_id.id,
            'resignation_reference': self.id
        })
        self.final_settlement = True

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.resignation') or '/'
        return super(HrResignation, self).create(vals)

    @api.constrains('travel_date', 'confirmed_travel_date')
    def check_travel_dates(self):
        for rec in self:
            if rec.travel_date < rec.resign_date:
                raise ValidationError(_("Travel date should be greater than or equal to the resign date"))
            if rec.confirmed_travel_date < rec.resign_date:
                raise ValidationError(_("Confirmed travel date should be greater than or equal to the resign date"))

    @api.depends('employee_id')
    def compute_user_id(self):
        for record in self:
            if record.employee_id.parent_id:
                record.lm_user_id = record.employee_id.parent_id.user_id.id
            else:
                record.lm_user_id = False

            if record.employee_id.user_id.has_group('atheer_hr.group_hr_project_manager'):
                record.pm_user_id = record.employee_id.user_id.id

    @api.onchange('travel_date')
    def onchange_travel_date(self):
        for rec in self:
            if rec.travel_date:
                rec.confirmed_travel_date = rec.travel_date

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(HrResignation, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                         submenu=False)
        form_view_id = self.env.ref('atheer_hr.view_hr_resignation_form_view').id

        if res.get('view_id', False) == form_view_id and res.get('type', False) == 'form':
            doc = etree.XML(res['arch'])
            if len(doc):
                if not self.env.user.has_group('atheer_hr.group_hr_line_manager'):
                    node = doc.xpath("//field[@name='lm_remark']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('atheer_hr.group_hr_manager'):
                    node = doc.xpath("//field[@name='hr_remark']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('atheer_hr.group_hr_ceo'):
                    node = doc.xpath("//field[@name='ceo_remark']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('atheer_hr.group_hr_accounts'):
                    node = doc.xpath("//field[@name='acc_remark']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                return res
        return res

    def send_to_line_manager(self):
        for rec in self:
            rec.left_hr_flag = True
            rec.send_back_flag = False
            rec.state = 'line_manager'

    def send_to_hr(self):
        for rec in self:
            rec.left_emp_flag = True
            rec.send_back_flag = False
            rec.state = 'hr'

    def send_to_ceo(self):
        for rec in self:
            rec.send_back_flag = False
            rec.state = 'ceo'

    def send_to_finance(self):
        for rec in self:
            rec.send_back_flag = False
            rec.state = 'finance'

    def approve(self):
        approver = str(self.env.user.name)
        for rec in self:
            rec.state = 'approved'
            self.employee_id.applicable_date = rec.resign_date
            self.employee_id.travel_date = rec.confirmed_travel_date
            self.cron_resignation()
            self.env['air.ticket.management'].create({
                'employee_id': rec.employee_id.id,
                'designation': rec.employee_id.job_id.id,
                'department_id': rec.employee_id.department_id.id,
                'ticket_type': 'resignation',
                'travel_date': rec.confirmed_travel_date,
                'state': 'draft',
                'resignation_check': True,
                'resignation': rec.id,
            })

    def cron_resignation(self):
        """Cron job for change the employee state from active to resign"""
        today = date.today()
        resign_obj = self.env['hr.resignation'].search([('state', '=', 'approved')])
        for rec in resign_obj:
            if rec.resign_date:
                if rec.resign_date <= today:
                    rec.employee_id.employee_status = 'resigned'
                    rec.employee_id.contract_id.write({'state': 'cancel'})
                    rec.employee_id.toggle_active()

    def send_back(self):
        """
         send backs to previous state
        """
        for rec in self:
            if rec.state == 'finance':
                rec.send_back_flag = True
                rec.write({'state': 'ceo'})
            elif rec.state == 'ceo':
                rec.send_back_flag = True
                rec.write({'state': 'hr'})
            elif rec.state == 'hr':
                rec.send_back_flag = True
                rec.write({'state': 'line_manager'})
            elif rec.state == 'line_manager':
                rec.send_back_flag = True
                rec.write({'state': 'draft'})

    def action_reject(self):
        for rec in self:
            rec.write({'state': 'reject', 'rejected_by': self.env.user.id, 'rejected_date': date.today()})

    def copy_data(self, default=None):
        raise UserError(_('Resignation cannot be duplicated.'))

    def unlink(self):
        for record in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if record.state not in ['draft']:
                    raise UserError(
                        _('You cannot delete the resignation %s in the current state.', record.name)
                    )
            return super(HrResignation, self).unlink()
