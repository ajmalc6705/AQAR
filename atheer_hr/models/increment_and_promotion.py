# -*- coding: utf-8 -*-
from lxml import etree
import json
from datetime import date
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class IncrementPromotion(models.Model):
    _name = "increment.and.promotion"
    _description = 'Increment & Promotion'
    _inherit = ['mail.thread']
    _rec_name = 'reference'

    def compute_payslip_generated(self):
        for rec in self:
            if rec.state == 'approved':
                payslip = self.env['hr.payslip'].search(
                    [('employee_id', '=', rec.employee_id.id), ('date_from', '<=', rec.effective_date),
                     ('date_to', '>=', rec.effective_date), ('state', '!=', 'cancel')])
                if payslip:
                    rec.payslip_generated = True
                else:
                    rec.payslip_generated = False
            else:
                rec.payslip_generated = False

    @api.model
    def default_get(self, fields_list):
        res = super(IncrementPromotion, self).default_get(fields_list)
        given_date = date.today()
        first_day_of_month = given_date.replace(day=1)
        self.effective_date = first_day_of_month
        res.update({'effective_date': first_day_of_month})
        return res

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', required=True,
                                  readonly=False,
                                  states={'approved': [('readonly', True)]},
                                  tracking=True)
    designation = fields.Many2one('hr.job', string='Designation', related='employee_id.job_id',
                                  tracking=True, copy=False)

    department_id = fields.Many2one('hr.department', string='Department',
                                    related='employee_id.department_id',
                                    tracking=True, copy=False)
    type = fields.Selection(
        [('salary_increment', 'Salary increment'), ('promotion', 'Promotion'),
         ('salary_increment_plus_promotion', 'Salary increment + Promotion'),
         ('demotion', 'Demotion'), ('demotion_plus_salary_revision', 'Demotion + Salary Revision'),
         ('airticket_addition', 'Airticket Addition'), ('airticket_deduction', 'Airticket Deduction')], required=True,
        readonly=False, states={'approved': [('readonly', True)]}, default='salary_increment',
        string="Type")
    contract_updated = fields.Boolean(string="Contract Updated", default=False)
    payslip_generated = fields.Boolean(default=False, compute='compute_payslip_generated')
    effective_date = fields.Date(string="Effective Date", copy=False)
    promoted_designation = fields.Many2one('hr.job', readonly=False,
                                           tracking=True, copy=False)
    job_description = fields.Text(string="Job Description", store=True, copy=False)
    state = fields.Selection([
        ('hr', 'HR Manager'),
        ('ceo', 'CEO'),
        ('approved', 'Approved'),
        ('reject', 'Refused'),
    ], default='hr', copy=False, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, copy=False)
    salary_package_ids = fields.One2many('current.salary.packages', 'increment_id', readonly=True,
                                         store=True)
    new_salary_details = fields.One2many('salary.packages', 'new_increment_id', readonly=False, store=True,
                                         states={'approved': [('readonly', True)]}, )
    current_gross_salary = fields.Float(string="Current Gross Salary", copy=False)
    gross_salary = fields.Float(string="New Gross Salary", copy=False)
    approval_person = fields.Many2one('res.users', string="Approved By", readonly=True, copy=False)
    hr_remarks = fields.Char(string="HR Remarks", readonly=False, copy=False)
    ceo_remarks = fields.Char(string="CEO Remarks", readonly=False, copy=False)
    today_date = fields.Date(string="Approval Date", readonly=True, store=True, copy=False)
    reference = fields.Char(string="Reference", tracking=True, copy=False, readonly=True)
    date_today = fields.Date(default=fields.Date.today())
    rejected_by = fields.Many2one('res.users', string="Refused By", copy=False)
    rejected_date = fields.Date(string="Refused Date", copy=False)
    # access flags
    send_back_flag = fields.Boolean(default=False, copy=False)
    left_hr_flag = fields.Boolean(default=False, copy=False)
    left_ch_flag = fields.Boolean(default=False, copy=False)

    airticket_qty = fields.Integer(string='Airticket Qty')
    start_date  = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    current_date = fields.Date(string='Current Date', default=fields.Date.today())
    last_payroll_processing_date = fields.Date(string='Last Payroll Processing Date', compute='_compute_date')
    salary_arrears = fields.Float(string='Salary Arrears',compute='_compute_salary_arrears')

    @api.depends('employee_id','gross_salary')
    def _compute_salary_arrears(self):
        self.salary_arrears = False
        for rec in self:
            salary_diff = rec.gross_salary - rec.current_gross_salary
            each_day_amount = salary_diff/30
            if rec.last_payroll_processing_date and rec.last_payroll_processing_date > rec.effective_date:
                no_of_days = (rec.last_payroll_processing_date - rec.effective_date).days
                rec.salary_arrears = no_of_days * each_day_amount


    @api.depends('employee_id')
    def _compute_date(self):
        self.last_payroll_processing_date = False
        for rec in self:
            payslip = self.env['hr.payslip'].search([('employee_id', '=', rec.employee_id.id), ('state', '=', 'paid')],
                                                    order='create_date DESC', limit=1)
            rec.last_payroll_processing_date = payslip.date_to

    def send_to_ceo(self):
        for rec in self:
            if rec.state == 'hr':
                rec.state = 'ceo'
            else:
                raise UserError(_('The records that in HR state can only approve'))

    def approve_hr(self):
        for rec in self:
            if rec.state == 'ceo':
                rec.state = 'approved'
            else:
                raise UserError(_('The records that in CEO state can only approve'))

    @api.model
    def create(self, vals):
        vals['reference'] = self.env['ir.sequence'].next_by_code('increment.and.promotion') or 'New'
        result = super(IncrementPromotion, self).create(vals)
        return result

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(IncrementPromotion, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                              submenu=False)
        form_view_id = self.env.ref('atheer_hr.view_increment_and_promotion_form').id

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

                if not self.env.user.has_group('atheer_hr.group_hr_ceo'):
                    node = doc.xpath("//field[@name='ceo_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                return res
        return res

    @api.onchange('employee_id')
    def onchange_employee(self):
        rules = []
        values = []
        for rec in self:
            rec.job_description = rec.designation.description
            if rec.employee_id.emp_salary_package_ids:
                rec.salary_package_ids = [(5, _)]
                rec.new_salary_details = [(5, _)]
                for record in rec.employee_id.contract_id.salary_package_ids:
                    vals = {
                        'component': record.component.id,
                        'amount_per_month': record.amount_per_month,
                    }
                    values.append((0, 0, vals))
                rec.salary_package_ids = values
                rec.new_salary_details = values
                rec.current_gross_salary = sum(rec.employee_id.contract_id.salary_package_ids.mapped('amount_per_month'))
            else:
                rec.salary_package_ids = False

    @api.onchange('new_salary_details')
    def compute_gross_salary(self):
        result = 0
        for rec in self.new_salary_details:
            result += rec.amount_per_month
        self.gross_salary = result

    def sent_to_ceo(self):
        for rec in self:
            rec.left_ch_flag = True
            rec.send_back_flag = False
            rec.write({'state': 'ceo'})

    def approve(self):
        today = date.today()
        for rec in self:
            rec.send_back_flag = False
            rec.write({'state': 'approved', 'approval_person': self.env.user.id, 'today_date': date.today()})
            if rec.effective_date:
                if rec.effective_date <= today:
                    if rec.type in ['promotion', 'salary_increment_plus_promotion', 'demotion',
                                    'demotion_plus_salary_revision']:
                        if rec.promoted_designation:
                            rec.employee_id.job_id = rec.promoted_designation.id
                    rules = []
                    if rec.type in ['salary_increment', 'salary_increment_plus_promotion', 'demotion',
                                    'demotion_plus_salary_revision']:
                        # self.cron_update_employee_info()
                        contract_id = rec.employee_id.contract_id
                        for sal_line in rec.new_salary_details:
                            if sal_line.component.name == 'Basic' and sal_line.amount_per_month > 0:
                                contract_id.write({'increment': True})
                            new_rule = (0, 0, {
                                'component': sal_line.component.id,
                                'employee_id': rec.employee_id.id,
                                'amount_per_month': sal_line.amount_per_month,
                            })
                            rules.append(new_rule)
                        contract_id.salary_package_ids = [(5, _, _)]
                        contract_id.salary_package_ids = rules

    def action_reject(self):
        for rec in self:
            rec.write({'state': 'reject', 'rejected_by': self.env.user.id, 'rejected_date': date.today()})

    def cron_update_employee_info(self):
        pass
    #     given_date = date.today()
    #     employees = self.env['hr.employee'].search([])
    #     rules = []
    #     for emp in employees:
    #         contracts = self.env['hr.contract'].search([('employee_id', '=', emp.id)], order="date_start asc")
    #         increments_prom_obj = self.env['increment.and.promotion'].search(
    #             [('employee_id', '=', emp.id), ('state', '=', 'approved'), ('contract_updated', '=', False)],
    #             order="effective_date asc")
    #         increments = increments_prom_obj.filtered(
    #             lambda x: x.type in ['salary_increment', 'salary_increment_plus_promotion',
    #                                  'demotion_plus_salary_revision'] and x.effective_date <= given_date)
    #         contract_list = []
    #         increment_list = []
    #         if contracts:
    #             for contract in contracts:
    #                 if not contract.increment:
    #                     data = {'date_from': contract.date_start,
    #                             'wage': contract.wage,
    #                             'gross': contract.gross_salary,
    #                             'type': 'Contract',
    #                             'emp_history_ids': emp.id,
    #                             }
    #                     contract_list.append(data)
    #         contract_id = emp.contract_id
    #         if increments:
    #             # contract_id.update({'salary_package_ids': [(5, _)]})
    #             for sal_line in increments.new_salary_details:
    #                 if sal_line.component.name == 'Basic' and sal_line.amount_per_month > 0:
    #                     contract_id.write({'increment': True})
    #                 new_rule = (0, 0, {
    #                     'component': sal_line.component.id,
    #                     'employee_id': emp.id,
    #                     'amount_per_month': sal_line.amount_per_month,
    #                 })
    #                 rules.append(new_rule)
    #
    #             contract_id.salary_package_ids = [(5, _, _)]
    #             contract_id.salary_package_ids = rules
    #         # designation update
    #         increments_designation = increments_prom_obj.filtered(
    #             lambda x: x.type in ['promotion', 'salary_increment_plus_promotion',
    #                                  'demotion', 'demotion_plus_salary_revision'] and x.effective_date <= given_date)
    #
    #         for each in increments_designation:
    #             emp.write({'job_id': each.promoted_designation.id})
    #             emp.contract_id.update({'job_id': each.promoted_designation.id})

    def send_back(self):
        """
        send backs to previous state
        """
        for rec in self:
            if rec.state == 'ceo':
                rec.send_back_flag = True
                rec.state = 'hr'

    def unlink(self):
        for record in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if record.state != 'hr':
                    raise UserError(
                        _('You cannot delete the increment and promotion %s in the current state.', record.reference)
                    )
            return super(IncrementPromotion, self).unlink()


class CurrentSalaryPackage(models.Model):
    _name = 'current.salary.packages'
    _description = 'Current Salary Packages'

    sl_no = fields.Integer(string="Sl No")
    component = fields.Many2one('salary.package.type', string="Component")
    amount_per_month = fields.Float(string="Amount Per Month (In OMR)", digits=(12, 3))
    contract_id = fields.Many2one('hr.contract')
    employee_id = fields.Many2one('hr.employee')
    increment_id = fields.Many2one('increment.and.promotion')
