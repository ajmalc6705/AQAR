# -*- coding:utf-8 -*-

import pytz
import calendar
import logging
import time
from lxml import etree
import json
from datetime import datetime, date, timedelta
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError
from odoo.tools.translate import _
from odoo.tools import float_compare, date_utils, float_is_zero
from odoo.tools.misc import format_date
from odoo.addons.resource.models.resource import datetime_to_string, string_to_datetime, Intervals
from odoo.addons.hr_payroll.models.browsable_object import BrowsableObject, InputLine, WorkedDays, Payslips, ResultRules
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class HRContract(models.Model):
    _inherit = 'hr.contract'

    def _get_contract_work_entries_values(self, date_start, date_stop):
        contract_vals = []
        bypassing_work_entry_type_codes = self._get_bypassing_work_entry_type_codes()
        for contract in self:
            employee = contract.employee_id
            calendar = contract.resource_calendar_id
            resource = employee.resource_id
            tz = pytz.timezone(calendar.tz)
            start_dt = pytz.utc.localize(date_start) if not date_start.tzinfo else date_start
            end_dt = pytz.utc.localize(date_stop) if not date_stop.tzinfo else date_stop

            attendances = calendar._attendance_all_intervals_batch(
                start_dt, end_dt, resources=resource, tz=tz
            )[resource.id]

            # Other calendars: In case the employee has declared time off in another calendar
            # Example: Take a time off, then a credit time.
            # YTI TODO: This mimics the behavior of _leave_intervals_batch, while waiting to be cleaned
            # in master.
            resources_list = [self.env['resource.resource'], resource]
            resource_ids = [False, resource.id]
            leave_domain = [
                ('time_type', '=', 'leave'),
                # ('calendar_id', '=', self.id), --> Get all the time offs
                ('resource_id', 'in', resource_ids),
                ('date_from', '<=', datetime_to_string(end_dt)),
                ('date_to', '>=', datetime_to_string(start_dt)),
                ('company_id', '=', self.env.company.id),
            ]
            result = defaultdict(lambda: [])
            tz_dates = {}
            for leave in self.env['resource.calendar.leaves'].search(leave_domain):
                for resource in resources_list:
                    if leave.resource_id.id not in [False, resource.id]:
                        continue
                    tz = tz if tz else pytz.timezone((resource or contract).tz)
                    if (tz, start_dt) in tz_dates:
                        start = tz_dates[(tz, start_dt)]
                    else:
                        start = start_dt.astimezone(tz)
                        tz_dates[(tz, start_dt)] = start
                    if (tz, end_dt) in tz_dates:
                        end = tz_dates[(tz, end_dt)]
                    else:
                        end = end_dt.astimezone(tz)
                        tz_dates[(tz, end_dt)] = end
                    dt0 = string_to_datetime(leave.date_from).astimezone(tz)
                    dt1 = string_to_datetime(leave.date_to).astimezone(tz)
                    result[resource.id].append((max(start, dt0), min(end, dt1), leave))
            mapped_leaves = {r.id: Intervals(result[r.id]) for r in resources_list}
            leaves = mapped_leaves[resource.id]

            real_attendances = attendances - leaves
            real_leaves = attendances - real_attendances

            # A leave period can be linked to several resource.calendar.leave
            split_leaves = []
            for leave_interval in leaves:
                if leave_interval[2] and len(leave_interval[2]) > 1:
                    split_leaves += [(leave_interval[0], leave_interval[1], l) for l in leave_interval[2]]
                else:
                    split_leaves += [(leave_interval[0], leave_interval[1], leave_interval[2])]
            leaves = split_leaves

            # Attendances
            default_work_entry_type = contract._get_default_work_entry_type()
            for interval in real_attendances:
                work_entry_type_id = interval[2].mapped('work_entry_type_id')[:1] or default_work_entry_type
                # All benefits generated here are using datetimes converted from the employee's timezone
                contract_vals += [{
                    'name': "%s: %s" % (work_entry_type_id.name, employee.name),
                    'date_start': interval[0].astimezone(pytz.utc).replace(tzinfo=None),
                    'date_stop': interval[1].astimezone(pytz.utc).replace(tzinfo=None),
                    'work_entry_type_id': work_entry_type_id.id,
                    'employee_id': employee.id,
                    'contract_id': contract.id,
                    'company_id': contract.company_id.id,
                    'state': 'draft',
                }]

            for interval in real_leaves:
                # Could happen when a leave is configured on the interface on a day for which the
                # employee is not supposed to work, i.e. no attendance_ids on the calendar.
                # In that case, do try to generate an empty work entry, as this would raise a
                # sql constraint error
                if interval[0] == interval[1]:  # if start == stop
                    continue
                leave_entry_type = contract._get_interval_leave_work_entry_type(interval, leaves,
                                                                                bypassing_work_entry_type_codes)
                interval_start = interval[0].astimezone(pytz.utc).replace(tzinfo=None)
                interval_stop = interval[1].astimezone(pytz.utc).replace(tzinfo=None)
                contract_vals += [dict([
                                           ('name', "%s%s" % (
                                               leave_entry_type.name + ": " if leave_entry_type else "",
                                               employee.name)),
                                           ('date_start', interval_start),
                                           ('date_stop', interval_stop),
                                           ('work_entry_type_id', leave_entry_type.id),
                                           ('employee_id', employee.id),
                                           ('company_id', contract.company_id.id),
                                           ('state', 'draft'),
                                           ('contract_id', contract.id),
                                       ] + contract._get_more_vals_leave_interval(interval, leaves))]
        return contract_vals

    # def _get_work_hours(self, date_from, date_to, domain=None):
    #     """
    #     Returns the amount (expressed in hours) of work
    #     for a contract between two dates.
    #     If called on multiple contracts, sum work amounts of each contract.
    #     :param date_from: The start date
    #     :param date_to: The end date
    #     :returns: a dictionary {work_entry_id: hours_1, work_entry_2: hours_2}
    #     """
    #     generated_date_max = min(fields.Date.to_date(date_to), date_utils.end_of(fields.Date.today(), 'month'))
    #     self._generate_work_entries(date_from, generated_date_max)
    #     date_from = datetime.combine(date_from, datetime.min.time())
    #     date_to = datetime.combine(date_to, datetime.max.time())
    #     work_data = []
    #     work_entries = self.env['hr.work.entry'].read_group(
    #         self._get_work_hours_domain(date_from, date_to, domain=domain, inside=True),
    #         ['hours:sum(duration)'],
    #         ['work_entry_type_id', 'date_start:month'], lazy=False
    #     )
    #     import calendar
    #     for data in work_entries:
    #         year = data['date_start:month'].split(" ")
    #         datetime_object = datetime.strptime(year[0], "%B")
    #         month_number = datetime_object.month
    #         res = {
    #             'month': data['date_start:month'],
    #             'hours': data['hours'],
    #             'max_days': calendar.monthrange(int(year[1]), int(month_number))[1],
    #             'work_entry_id': data['work_entry_type_id'][0]
    #         }
    #         work_data.append(res)
    #     # Second, find work entry that exceeds interval and compute right duration.
    #     work_entries = self.env['hr.work.entry'].search(
    #         self._get_work_hours_domain(date_from, date_to, domain=domain, inside=False))
    #     for work_entry in work_entries:
    #         date_start = max(date_from, work_entry.date_start)
    #         date_stop = min(date_to, work_entry.date_stop)
    #         if work_entry.work_entry_type_id.is_leave:
    #             contract = work_entry.contract_id
    #             calendar = contract.resource_calendar_id
    #             employee = contract.employee_id
    #             contract_data = employee._get_work_days_data_batch(
    #                 date_start, date_stop, compute_leaves=False, calendar=calendar
    #             )[employee.id]
    #
    #             work_data[work_entry.work_entry_type_id.id] += contract_data.get('hours', 0)
    #         else:
    #             dt = date_stop - date_start
    #             work_data[work_entry.work_entry_type_id.id] += dt.days * 24 + dt.seconds / 3600  # Number of hours
    #     return work_data


class HRPayslip(models.Model):
    _name = 'hr.payslip'
    _description = "Payslip"
    _inherit = ['hr.payslip', 'mail.thread']

    employee_category = fields.Selection(related='employee_id.employee_category')

    emp_ot_lines = fields.Many2many('hr.attendance.overtime', string='OT Lines', compute='get_attendance_ot_lines')
    emp_timesheet = fields.One2many('payslip.timesheet.line', 'payslip_id', 'Employee Timesheets')
    monthly_hours = fields.Float(string='Actual Hours', compute='days_in_month', store=True, digits=(16, 3))
    total_timesheet = fields.Float(string='Total Hours Worked', digits=(16, 3))

    ot_eligibility = fields.Boolean(string="OT Eligibility")
    ph_ot_eligibility = fields.Boolean(string="Public Holiday OT Eligibility")
    ot_hours = fields.Float(string='OT Hours', compute='payslip_days', store=True, digits=(16, 3))
    normal_ot = fields.Float(string='Normal OT Amount', compute='compute_overtime', digits=(16, 3))
    weekend_ot = fields.Float(string='Weekend OT Amount', compute='compute_overtime', digits=(16, 3))
    ph_ot = fields.Float(string='Public Holiday OT Amount', compute='compute_overtime', store=True, digits=(16, 3))
    total_ot_amount = fields.Float(string='Total OT Amount', compute='compute_overtime', store=True, digits=(16, 3))
    ot_salary = fields.Float(string='OT Salary', compute='_ot_salary', store=True, digits=(16, 3), )
    total_worked_days = fields.Float(string='Total no. of days worked', compute='payslip_days', store=True,
                                     digits=(16, 2))
    worked_days_salary = fields.Float(string='Salary for worked days', compute='_payable_days', store=True,
                                      digits=(16, 3))
    annual_leaves = fields.Float(string='Annual Leaves(days)', compute='leave_days', store=True, digits=(12, 2))
    other_leaves = fields.Float(string='Other Leaves(days)', compute='leave_days', store=True, digits=(12, 2))
    no_of_leaves = fields.Float(string='No. of leaves(days)', compute='leave_days', store=True, digits=(12, 2))
    payable_leaves = fields.Float(string='Payable Leaves', compute='_payable_days', store=True, digits=(12, 2))
    leave_unpaid_amount = fields.Monetary(string='Sick Leaves Deductions Amount', compute='get_leave_unpaid_amount',
                                          store=True, readonly=False)
    unpaid_leave_deductions = fields.Monetary(string='Unpaid Leave Deductions', compute='get_unpaid_leave_amount',
                                              store=True, readonly=False)

    payable_days = fields.Float(string='Payable Days', compute='_payable_days', store=True, digits=(12, 2))
    hours_lost = fields.Float(string='Hours Lost', compute='payslip_days', store=True, digits=(16, 3))
    payslip_day = fields.Float('Total Days in the Starting Month', compute='days_in_month', store=True, digits=(16, 3))
    std_salary = fields.Float('Standard Salary', compute='total_salary', store=True, digits=(16, 3), )
    computed_salary = fields.Float('Net Salary', compute='total_salary', store=True, digits=(16, 3), )
    additions = fields.Float('Additions', compute='_compute_additions', store=True, digits=(16, 3), )
    deductions = fields.Float('Deductions', compute='_compute_deductions', store=True, digits=(16, 3))
    is_final = fields.Boolean(string='Is Final Settlement ?')
    acc_gratuity = fields.Float(string='Accumulated Gratuity', readonly=True,
                                help='This field is automatically calculated from the Final Settlement Form')
    is_leave = fields.Boolean(string='Is Leave Settlement ?')
    leaves = fields.Float('Payable Leaves(On Final Settlement)', readonly=True)
    state = fields.Selection(selection_add=[
        ('draft', 'HR Admin'),
        ('with_hr', 'HR MANAGER'),
        ('accounts', 'Finance Controller'),
        ('with_ceo', 'CEO'),
        ('hold', 'HOLD'),
        ('done',),
        ('cancel', 'REJECTED'),
    ])
    input_line_ids = fields.One2many('hr.payslip.input', 'payslip_id', 'Payslip Inputs', required=False, readonly=False,
                                     tracking=True)
    process_salary = fields.Boolean(string='WPS Generated', readonly=True)
    date_pay = fields.Date(string='Payment Date', readonly=True)
    is_leave_cash = fields.Boolean(string='Is Leave Encashment ?')
    annual_leaves_cash = fields.Float(string='Annual Leaves to Encash(days)', readonly=True, digits=(16, 3))
    bonus_details = fields.One2many('annual.bonus', 'bonus_id')
    bonus_check = fields.Boolean(default=False)
    payroll_hold = fields.Boolean(default=False)
    today_date = fields.Date(default=fields.Date.today())
    loan_amount = fields.Float(string="Loan Amount", compute='compute_loan_amount', copy=False)
    loan_addition_amount = fields.Float(string="Loan Addition Amount", copy=False)
    loan_deduction_amount = fields.Float(string="Loan Deduction Amount", copy=False)
    bonus_amount = fields.Float(string="Bonus Amount", copy=False)
    advance_salary_amount = fields.Float(string="Advance Salary Amount", compute='compute_advance_salary')
    salary_period = fields.Char(compute="compute_salary_period", copy=False)
    no_of_months = fields.Float()
    rejected_by = fields.Many2one('res.users', string="Refused By")
    rejected_date = fields.Date(string="Refused Date")
    accounts_remarks = fields.Char(string="Accounts Remarks", readonly=False)
    hr_remarks = fields.Char(string="HR Remarks", readonly=False)
    ceo_remarks = fields.Char(string="CEO Remarks", readonly=False)
    # access flags
    send_back_flag = fields.Boolean(default=False)
    left_acc_flag = fields.Boolean(default=False)
    left_ch_flag = fields.Boolean(default=False)
    left_hr_flag = fields.Boolean(default=False)
    payslip_batch = fields.Boolean(default=False)
    display_worked_days = fields.Boolean(default=False)

    @api.depends('date_from', 'date_to', 'employee_id', 'contract_id', 'struct_id',
                 'worked_days_line_ids.amount_unpaid')
    def get_leave_unpaid_amount(self):
        for rec in self:
            leave_lines = rec.worked_days_line_ids.filtered(lambda x: x.is_leave and x.pay_perc != '100' and x.is_paid)
            rec.leave_unpaid_amount = sum(leave_lines.mapped('amount_unpaid')) if leave_lines else 0

    @api.depends('date_from', 'date_to', 'employee_id', 'contract_id', 'struct_id',
                 'worked_days_line_ids.amount_unpaid')
    def get_unpaid_leave_amount(self):
        for rec in self:
            leave_lines = rec.worked_days_line_ids.filtered(lambda x: x.is_leave and not x.is_paid)
            rec.unpaid_leave_deductions = sum(leave_lines.mapped('amount')) if leave_lines else 0

    @api.model
    def create(self, vals):
        vals['number'] = self.env['ir.sequence'].next_by_code('hr.payslip') or 'New'
        result = super(HRPayslip, self).create(vals)
        result.display_worked_days = True
        return result

    def write(self, vals):
        vals['display_worked_days'] = True
        res = super(HRPayslip, self).write(vals)
        # self.display_worked_days =True
        return res

    @api.constrains('employee_id', 'date_from', 'date_to')
    def check_employee_payslip(self):
        for rec in self:
            payslip_ids = self.env['hr.payslip'].search([('date_to', '>', rec.date_from),
                                                         ('date_from', '<=', rec.date_to),
                                                         ('employee_id', '=', rec.employee_id.id),
                                                         ('state', 'not in', ['draft', 'cancel'])])
            if payslip_ids:
                raise ValidationError(_("Payslip has been already created for %s for the requested period") % (
                    str(rec.employee_id.name)))

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee_loan(self):
        for rec in self:
            res = rec.find_loan_addition_amount(rec.date_from, rec.date_to, rec.employee_id)
            if res:
                rec.loan_addition_amount = res.get('sum_loan_addition', False)
                rec.loan_deduction_amount = res.get('sum_loan_deduction', False)

    def find_loan_addition_amount(self, date_from, date_to, employee_id):
        if employee_id:
            loan_addition_obj = self.env['hr.loan.types'].search(
                [('employee_id', '=', employee_id.id), ('type', '=', 'addition'), ('state', '=', 'approved'),
                 ('effective_date', '>=', date_from),
                 ('effective_date', '<=', date_to)])
            loan_deduction_obj = self.env['hr.loan.types'].search(
                [('employee_id', '=', employee_id.id), ('type', '=', 'deduction'), ('state', '=', 'approved'),
                 ('effective_date', '>=', date_from),
                 ('effective_date', '<=', date_to)])
            sum_loan_addition = sum(loan_addition_obj.mapped('amount'))
            sum_loan_deduction = sum(loan_deduction_obj.mapped('amount'))
            return {'sum_loan_addition': sum_loan_addition, 'sum_loan_deduction': sum_loan_deduction}
        else:
            return False

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(HRPayslip, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                     submenu=False)
        form_view_id = self.env.ref('hr_payroll.view_hr_payslip_form').id
        if res.get('view_id', False) == form_view_id and res.get('type', False) == 'form':
            doc = etree.XML(res['arch'])
            if len(doc):
                if not self.env.user.has_group('atheer_hr.group_hr_accounts'):
                    node = doc.xpath("//field[@name='accounts_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
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

    @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        for rec in self:
            if (not rec.employee_id) or (not rec.date_from) or (not rec.date_to):
                return
            if rec.date_from and rec.date_to:
                d1 = rec.date_from
                d2 = rec.date_to
                rec.no_of_months = ((d2.year - d1.year) * 12 + (d2.month - d1.month)) + 1
            rec.ot_eligibility = rec.employee_id.ot_eligibility
            rec.ph_ot_eligibility = rec.employee_id.ph_ot_eligibility

    def compute_salary_period(self):
        period = ''
        for rec in self:
            if rec.date_from and rec.date_to:
                if rec.date_from.month == rec.date_to.month:
                    period = ' ' + rec.date_from.strftime("%B") + ' ' + str(rec.date_from.year)
                else:
                    period = ' ' + str(rec.date_from.strftime("%B")) + ' ' + str(rec.date_from.year) + ' and ' + str(
                        rec.date_to.strftime("%B")) + ' ' + str(rec.date_from.year)
        self.salary_period = period

    def compute_loan_amount(self):
        amt = 0.0
        for rec in self.installments:
            if rec.paid_check:
                amt += rec.amount
        self.loan_amount = amt

    def compute_advance_salary(self):
        amt = 0.0
        for rec in self.advance_installments:
            if rec.paid_check:
                amt += rec.amount
        self.advance_salary_amount = amt

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee_contract(self):
        for rec in self:
            if rec.employee_id and rec.contract_id:
                bonus = rec.find_bonus_amount(rec.employee_id, rec.date_from, rec.date_to)
                if bonus:
                    rec.bonus_check = bonus.get('bonus_check', False)
                    rec.bonus_details = bonus.get('bonus_details', False)
                    rec.bonus_amount = bonus.get('bonus_amount', False)
                else:
                    rec.bonus_check = False
                    rec.bonus_details = False
                    rec.bonus_amount = 0
                hold_ids = self.env['hr.payroll.hold'].search(
                    [('employee_id', '=', rec.employee_id.id), ('date_from', '<=', rec.date_from),
                     ('date_to', '<=', rec.date_to), ('state', '=', 'on_hold')])
                if hold_ids:
                    rec.payroll_hold = True
                else:
                    rec.payroll_hold = False

    def find_bonus_amount(self, employee_id, date_from, date_to):
        if employee_id and employee_id.contract_id:
            bonus = self.env['annual.bonus'].search(
                [('employee_id', '=', employee_id.id), ('effective_date', '>=', date_from),
                 ('effective_date', '<=', date_to), ('state', '=', 'approved')])
            if bonus:
                bonus_check = True
                bonus_details = [(6, 0, bonus.ids)]
                bonus_amount = sum(bonus.mapped('bonus_amount'))
                return {'bonus_details': bonus_details, 'bonus_check': bonus_check, 'bonus_amount': bonus_amount}
            else:
                return False

    @api.depends('worked_days_line_ids', 'input_line_ids')
    def _compute_line_ids(self):
        if not self.env.context.get("payslip_no_recompute"):
            return
        for payslip in self.filtered(
                lambda p: p.line_ids and p.state in ['draft', 'verify', 'with_account_dep']):
            payslip.line_ids = [(5, 0, 0)] + [(0, 0, line_vals) for line_vals in payslip._get_payslip_lines()]

    def compute_sheet(self):
        payslips = self.filtered(lambda slip: slip.state in ('draft', 'verify', 'with_hr'))
        if len(payslips) == 1:
            self._onchange_employee()

        # delete old payslip lines
        payslips.line_ids.unlink()
        for payslip in payslips:
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            lines = [(0, 0, line) for line in payslip._get_payslip_lines()]
            # removing the zero values from result
            final_lines = []
            for rec in lines:
                if rec[2].get('amount', False) != 0.0:
                    final_lines.append(rec)
            payslip.write({'line_ids': final_lines, 'number': number, 'compute_date': fields.Date.today()})
        return True

    @api.depends('employee_id', 'date_from', 'date_to')
    def get_attendance_ot_lines(self):
        for rec in self:
            if rec.employee_id and rec.date_from and rec.date_to:
                overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', rec.employee_id.id),
                                                                      ('date', '>=', rec.date_from),
                                                                      ('date', '<=', rec.date_to)])
                rec.emp_ot_lines = overtime
            else:
                rec.emp_ot_lines = False

    @api.onchange('employee_id', 'date_from', 'date_to')
    def _get_timesheet_lines(self):
        """fetch the list of timesheet lines of the employees"""
        for record in self:
            record.update({'emp_timesheet': [(5,)]})
            if record.employee_id and record.date_from and record.date_to:
                query = """SELECT count(il.id) as days_worked, sum(il.hours) as hours, to_char(il.act_date, 'MM') as month,
                    il.cost_center as bu_cc, il.ot_id as ot_id
                    FROM hr_timesheet_import_lines il WHERE
                    il.employee_id =""" + str(record.employee_id.id) + """
                    AND il.act_date>='""" + str(record.date_from) + """' AND il.act_date<='""" + str(record.date_to) + """'
                    GROUP BY
                    to_char(il.act_date, 'MM'), il.cost_center,il.ot_id
                """
                self._cr.execute(query)
                time_disc = self._cr.dictfetchall()
                sheet_lines = []
                for time_line in time_disc:
                    sheet_lines.append((0, 0, time_line))
                if time_disc:
                    record.update({'emp_timesheet': sheet_lines})
                else:
                    record.update({'emp_timesheet': [(5, )]})

    def _action_create_account_move(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')

        # Add payslip without run
        payslips_to_post = self.filtered(lambda slip: not slip.payslip_run_id)

        # Adding pay slips from a batch and deleting pay slips with a batch that is not ready for validation.
        payslip_runs = (self - payslips_to_post).mapped('payslip_run_id')
        for run in payslip_runs:
            if run._are_payslips_ready():
                payslips_to_post |= run.slip_ids

        # A payslip need to have a done state and not an accounting move.
        payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.move_id)

        # Check that a journal exists on all the structures
        if any(not payslip.journal_id for payslip in payslips_to_post):
            raise ValidationError(_('One of the contract for these payslips has no structure type.'))
        if any(not structure.journal_id for structure in payslips_to_post.mapped('struct_id')):
            raise ValidationError(_('One of the payroll structures has no account journal defined on it.'))

        # Map all payslips by structure journal and pay slips month.
        # {'journal_id': {'month': [slip_ids]}}
        slip_mapped_data = {
            slip.struct_id.journal_id.id: {fields.Date().end_of(slip.date_to, 'month'): self.env['hr.payslip']} for slip
            in payslips_to_post}
        for slip in payslips_to_post:
            slip_mapped_data[slip.struct_id.journal_id.id][fields.Date().end_of(slip.date_to, 'month')] |= slip

        for journal_id in slip_mapped_data:  # For each journal_id.
            for slip_date in slip_mapped_data[journal_id]:  # For each month.
                line_ids = []
                debit_sum = 0.0
                credit_sum = 0.0
                date = slip_date
                move_dict = {
                    'narration': '',
                    'ref': date.strftime('%B %Y'),
                    'journal_id': journal_id,
                    'date': date,
                }

                for slip in slip_mapped_data[journal_id][slip_date]:
                    move_dict['narration'] += slip.number or '' + ' - ' + slip.employee_id.name or ''
                    move_dict['narration'] += '\n'
                    for line in slip.line_ids.filtered(lambda line: line.category_id):
                        amount = -line.total if slip.credit_note else line.total
                        if line.code == 'NET':  # Check if the line is the 'Net Salary'.
                            for tmp_line in slip.line_ids.filtered(lambda line: line.category_id):
                                if tmp_line.salary_rule_id.not_computed_in_net:  # Check if the rule must be computed in the 'Net Salary' or not.
                                    if amount > 0:
                                        amount -= abs(tmp_line.total)
                                    elif amount < 0:
                                        amount += abs(tmp_line.total)
                        if float_is_zero(amount, precision_digits=precision):
                            continue

                        debit_account_id = line.salary_rule_id.account_debit.id
                        credit_account_id = line.salary_rule_id.account_credit.id
                        if slip.employee_id.is_omani == 'omani':
                            if debit_account_id:  # If the rule has a debit account.
                                debit = amount if amount > 0.0 else 0.0
                                credit = -amount if amount < 0.0 else 0.0

                                debit_line = self._get_existing_lines(
                                    line_ids, line, debit_account_id, debit, credit)

                                if not debit_line:
                                    debit_line = self._prepare_line_values(line, debit_account_id, date, debit, credit)
                                    line_ids.append(debit_line)
                                else:
                                    debit_line['debit'] += debit
                                    debit_line['credit'] += credit

                            if credit_account_id:  # If the rule has a credit account.
                                debit = -amount if amount < 0.0 else 0.0
                                credit = amount if amount > 0.0 else 0.0
                                credit_line = self._get_existing_lines(
                                    line_ids, line, credit_account_id, debit, credit)

                                if not credit_line:
                                    credit_line = self._prepare_line_values(line, credit_account_id, date, debit,
                                                                            credit)
                                    line_ids.append(credit_line)
                                else:
                                    credit_line['debit'] += debit
                                    credit_line['credit'] += credit
                        elif slip.employee_id.is_omani == 'expat':
                            # For normal employees especially labours
                            self._cr.execute(
                                "SELECT SUM(days_worked) from payslip_timesheet_line WHERE payslip_id={0}".format(
                                    slip.id))
                            total_worked_days = self._cr.fetchone()
                            total_worked_days = total_worked_days and total_worked_days[0]
                            if not total_worked_days:
                                continue
                            amount_for_one_day = amount / total_worked_days  # For getting and post cc wise JE, Here Amount for 1 day is calculated
                            for timesheet_line in slip.emp_timesheet:
                                try:
                                    post_amt = amount_for_one_day * timesheet_line.days_worked  # 1.256 * 31/30/28/29 if full present or worked days
                                except ZeroDivisionError as e:
                                    raise UserError("Compute Payslip Again. Timesheet Values are Changed.")
                                post_bucc = timesheet_line.bu_cc.id or 'NULL'
                                if debit_account_id:  # If the rule has a debit account.
                                    debit = post_amt if post_amt > 0.0 else 0.0
                                    credit = -post_amt if post_amt < 0.0 else 0.0

                                    debit_line = self._get_existing_lines(
                                        line_ids, line, debit_account_id, debit, credit)

                                    if not debit_line:
                                        debit_line = self._prepare_line_values_cc(line, debit_account_id, date, debit,
                                                                                  credit, post_bucc)
                                        line_ids.append(debit_line)
                                    else:
                                        debit_line['debit'] += debit
                                        debit_line['credit'] += credit

                                if credit_account_id:  # If the rule has a credit account.
                                    debit = -post_amt if post_amt < 0.0 else 0.0
                                    credit = post_amt if post_amt > 0.0 else 0.0
                                    credit_line = self._get_existing_lines(
                                        line_ids, line, credit_account_id, debit, credit)

                                    if not credit_line:
                                        credit_line = self._prepare_line_values_cc(line, credit_account_id, date, debit,
                                                                                   credit, post_bucc)
                                        line_ids.append(credit_line)
                                    else:
                                        credit_line['debit'] += debit
                                        credit_line['credit'] += credit

                for line_id in line_ids:  # Get the debit and credit sum.
                    debit_sum += line_id['debit']
                    credit_sum += line_id['credit']

                # The code below is called if there is an error in the balance between credit and debit sum.
                if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                    acc_id = slip.journal_id.default_account_id.id
                    if not acc_id:
                        raise UserError(
                            _('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                                slip.journal_id.name))
                    existing_adjustment_line = (
                        line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                    )
                    adjust_credit = next(existing_adjustment_line, False)

                    if not adjust_credit:
                        adjust_credit = {
                            'name': _('Adjustment Entry'),
                            'partner_id': False,
                            'account_id': acc_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': 0.0,
                            'credit': debit_sum - credit_sum,
                        }
                        line_ids.append(adjust_credit)
                    else:
                        adjust_credit['credit'] = debit_sum - credit_sum

                elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                    acc_id = slip.journal_id.default_account_id.id
                    if not acc_id:
                        raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                            slip.journal_id.name))
                    existing_adjustment_line = (
                        line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                    )
                    adjust_debit = next(existing_adjustment_line, False)

                    if not adjust_debit:
                        adjust_debit = {
                            'name': _('Adjustment Entry'),
                            'partner_id': False,
                            'account_id': acc_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': credit_sum - debit_sum,
                            'credit': 0.0,
                        }
                        line_ids.append(adjust_debit)
                    else:
                        adjust_debit['debit'] = credit_sum - debit_sum

                # Add accounting lines in the move
                move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
                move = self.env['account.move'].create(move_dict)
                move and move.mapped('line_ids') and move.action_post()
                for slip in slip_mapped_data[journal_id][slip_date]:
                    slip.write({'move_id': move.id, 'date': date})
        return True

    def _prepare_line_values_cc(self, line, account_id, date, debit, credit, post_bucc):
        return {
            'name': line.name,
            'partner_id': line.partner_id.id,
            'account_id': account_id,
            'journal_id': line.slip_id.struct_id.journal_id.id,
            'date': date,
            'debit': debit,
            'credit': credit,
            'analytic_account_id': post_bucc,
        }

    @api.depends('worked_days_line_ids', 'emp_timesheet', 'emp_ot_lines', 'employee_id', 'contract_id', 'date_from',
                 'date_to')
    def compute_overtime(self):
        normal_ot = 0
        weekend_ot = 0
        ph_ot = 0
        total_ot_amount = 0
        for records in self:
            result = records.find_ot_amount()
            if result:
                normal_ot = result['normal_ot']
                weekend_ot = result['weekend_ot']
                ph_ot = result['ph_ot']
                total_ot_amount = result['total_ot_amount']
            records.normal_ot = normal_ot
            records.weekend_ot = weekend_ot
            records.ph_ot = ph_ot
            records.total_ot_amount = total_ot_amount

    def find_ot_amount(self):
        normal_ot_factor = 1.25
        weekend_ot_factor = 1.5
        ph_ot_factor = 1.5
        wage = self.contract_id.wage
        normal_ot = weekend_ot = ph_ot = 0
        month_days = calendar.monthrange(self.date_to.year, self.date_to.month)[1]
        hrs_per_day = self.employee_id.resource_calendar_id.hours_per_day
        if self.employee_category in ('omani_labor', 'expat_labor'):
            normal_ot_hrs = sum(self.emp_timesheet.filtered(lambda x: x.ot_id == 'normal').mapped('hours'))
            weekend_ot_hrs = sum(self.emp_timesheet.filtered(lambda x: x.ot_id == 'weekend').mapped('hours'))
            ph_ot_hrs = sum(self.emp_timesheet.filtered(lambda x: x.ot_id == 'ph').mapped('hours'))
        else:
            normal_ot_hrs = sum(self.emp_ot_lines.filtered(lambda x: x.ot_day_type == 'normal').mapped('duration'))
            weekend_ot_hrs = sum(self.emp_ot_lines.filtered(lambda x: x.ot_day_type == 'weekend').mapped('duration'))
            ph_ot_hrs = sum(self.emp_ot_lines.filtered(lambda x: x.ot_day_type == 'ph').mapped('duration'))
        if self.ot_eligibility:
            normal_ot = (wage / month_days / hrs_per_day) * normal_ot_factor * normal_ot_hrs
            weekend_ot = (wage / month_days / hrs_per_day) * weekend_ot_factor * weekend_ot_hrs
        elif self.ph_ot_eligibility:
            ph_ot = (wage / month_days / hrs_per_day) * ph_ot_factor * ph_ot_hrs
        total_ot_amount = normal_ot + weekend_ot + ph_ot
        return {'normal_ot': normal_ot, 'weekend_ot': weekend_ot, 'ph_ot': ph_ot, 'total_ot_amount': total_ot_amount}

    @api.depends('worked_days_line_ids', 'emp_timesheet', 'total_timesheet', 'ot_hours')
    def payslip_days(self):
        for record in self:
            total = 0
            ot_hours = 0
            if record.employee_id:
                for i in record.worked_days_line_ids:
                    if i.work_entry_type_id.code == 'WORK100':
                        total += i.number_of_days
                if record.employee_category in ('omani_labor', 'expat_labor'):
                    ot_hours = sum(ts.hours for ts in record.emp_timesheet)
                else:
                    ot_hours = sum(ot.duration for ot in record.emp_ot_lines)

            record.total_worked_days = total
            record.ot_hours = ot_hours

    @api.depends('worked_days_line_ids', 'employee_id')
    def leave_days(self):
        for record in self:
            total_days = 0
            annual_leaves = 0
            other_leaves = 0
            for i in record.worked_days_line_ids:
                i._effective_days()
                if i.line_type == 'leave':
                    if i.annual_leave:
                        annual_leaves += i.number_of_days
                    elif not i.annual_leave:
                        other_leaves += i.number_of_days
                    total_days += i.number_of_days
            record.no_of_leaves = total_days
            record.annual_leaves = annual_leaves
            record.other_leaves = other_leaves

    @api.depends('line_ids')
    def total_salary(self):
        for record in self:
            record.std_salary = record.contract_id.total_salary
            computed_ot_line = record.line_ids.filtered(lambda rec: rec.code == 'NET')
            record.computed_salary = 0
            for line in computed_ot_line:
                record.computed_salary = record.computed_salary + line.total

    @api.depends('line_ids', 'total_worked_days', 'payslip_day', 'computed_salary')
    def _payable_days(self):
        for record in self:
            total_days = 0
            leaves_payable = 0
            for i in record.worked_days_line_ids:
                entry_type = self.env['hr.work.entry.type'].search([('leave_type_ids.is_unpaid', '=', True)], limit=1)
                total_days += i.effective_days
                if i.line_type == 'leave' and i.work_entry_type_id.id != entry_type.id:
                    leaves_payable += i.effective_days
            record.payable_leaves = leaves_payable  # While comparing with focus report the value -1 is total basic result
            record.payable_days = record.total_worked_days + record.payable_leaves
            computed_ot_line = record.line_ids.filtered(
                lambda rec: rec.category_id.code == 'GROSS' and rec.code == 'BASIC')
            record.worked_days_salary = 0
            for line in computed_ot_line:
                record.worked_days_salary = record.worked_days_salary + line.total

    @api.depends('line_ids')
    def _ot_salary(self):
        for record in self:
            computed_ot_line = record.line_ids.filtered(lambda rec: rec.category_id.code == 'OT')
            record.ot_salary = 0
            for line in computed_ot_line:
                record.ot_salary = record.ot_salary + line.total

    @api.depends('date_from', 'date_to')
    def days_in_month(self):
        for record in self:
            date_format = "%Y-%m-%d"
            if record.date_to and record.date_from:
                m = datetime.strptime(str(record.date_from), date_format)
                last_date = calendar.monthrange(m.year, m.month)[1]
                d = datetime.strptime(str(record.date_to), date_format) - datetime.strptime(str(record.date_from),
                                                                                            date_format)
                record.monthly_hours = d.days * record.contract_id.hours_per_day if record.contract_id else 0
                record.payslip_day = last_date

    @api.depends('line_ids')
    def _compute_additions(self):
        for record in self:
            total = 0.0
            record.additions = total

    @api.depends('line_ids')
    def _compute_deductions(self):
        for record in self:
            total = 0.0
            record.deductions = total

    def send_to_hr(self):
        """
                sending single payslip to HR
        """
        for record in self:
            record.left_acc_flag = True
            record.send_back_flag = False
            record.state = 'with_hr'
            responsible_users = self.sudo().env.ref('atheer_hr.group_hr_manager').users
            note = _('%(emp_name)s %(doc_name)s is approved by HR Manager',
                     emp_name=record.employee_id.name, doc_name=record.number, doc_status=record.state)
            summary = _('%(doc_name)s %(doc_status)s', doc_name=record.number, doc_status=record.state)
            if responsible_users:
                for responsible_user in responsible_users:
                    record.activity_schedule('atheer_hr.mail_act_payslip_to_hr_manager', note=note,
                                          user_id=responsible_user.id, date_deadline=record.date_to, summary=summary)
            if record.payslip_run_id and record.payslip_run_id.slip_ids.filtered(
                    lambda x: x.state not in ('draft')):
                record.payslip_run_id.state = 'with_hr'

    def send_to_accounts(self):
        """

        ('accounts', 'Finance'),
        """
        for record in self:
            record.left_acc_flag = True
            record.send_back_flag = False
            record.state = 'accounts'
            responsible_users = self.sudo().env.ref('atheer_hr.group_hr_manager').users
            note = _('%(emp_name)s %(doc_name)s is sent to  Accounts',
                     emp_name=record.employee_id.name, doc_name=record.number, doc_status=record.state)
            summary = _('%(doc_name)s %(doc_status)s', doc_name=record.number, doc_status=record.state)
            if responsible_users:
                for responsible_user in responsible_users:
                    record.activity_schedule('atheer_hr.mail_act_payslip_to_accounts', note=note,
                                          user_id=responsible_user.id, date_deadline=record.date_to, summary=summary)
            if record.payslip_run_id and record.payslip_run_id.slip_ids.filtered(
                    lambda x: x.state not in ('with_hr')):
                record.payslip_run_id.state = 'accounts'

    def send_to_ceo(self):
        """
           sending single payslip to CEO
        """
        for record in self:
            record.left_hr_flag = True
            record.send_back_flag = False
            record.state = 'with_ceo'
            responsible_users = self.sudo().env.ref('atheer_hr.group_hr_ceo').users
            note = _('%(emp_name)s %(doc_name)s is sent to CEO',
                     emp_name=record.employee_id.name, doc_name=record.number, doc_status=record.state)
            summary = _('%(doc_name)s %(doc_status)s', doc_name=record.number, doc_status=record.state)
            if responsible_users:
                for responsible_user in responsible_users:
                    record.activity_schedule('atheer_hr.mail_act_payslip_to_accounts', note=note,
                                          user_id=responsible_user.id, date_deadline=record.date_to, summary=summary)
            if record.payslip_run_id and record.payslip_run_id.slip_ids.filtered(
                    lambda x: x.state not in ('draft', 'with_hr')):
                record.payslip_run_id.state = 'with_ceo'

    def set_as_done(self):
        for record in self:
            if record.payslip_run_id and record.payslip_run_id.slip_ids.filtered(
                    lambda x: x.state not in ('draft', 'with_hr', 'with_ceo')):
                record.payslip_run_id.state = 'close'

    def send_back(self):
        for record in self:
            if record.state == 'with_hr':
                record.state = 'draft'
                record.send_back_flag = True
            elif record.state == 'with_ceo':
                record.state = 'accounts'
                record.send_back_flag = True
            elif record.state == 'accounts':
                record.state = 'with_hr'
                record.send_back_flag = True

    def draft(self):
        for record in self:
            record.state = 'draft'

    def action_payslip_done(self):
        for payslip in self:
            hold_ids = self.env['hr.payroll.hold'].search(
                [('employee_id', '=', payslip.employee_id.id), ('date_from', '<=', payslip.date_from),
                 ('date_to', '<=', payslip.date_to), ('state', '=', 'on_hold')])
            if hold_ids:
                payslip.state = 'hold'

            if not payslip.employee_id.bank_id or not payslip.employee_id.bank_account:
                self.env['salary.hold'].create({
                    'employee_id': payslip.employee_id.id,
                    'date_from': payslip.date_from,
                    'date_to': payslip.date_to,
                    'std_salary': payslip.std_salary,
                    'computed_salary': payslip.computed_salary,
                    'additions': payslip.additions,
                    'deductions': payslip.deductions,
                    'payslip_id': payslip.id,
                    'batch_id': payslip.payslip_run_id.id,
                })
            if not hold_ids:
                if any(slip.state == 'cancel' for slip in self):
                    raise ValidationError(_("You can't validate a cancelled payslip."))
                self.write({'state': 'done'})
                self.mapped('payslip_run_id').action_close()
                self._action_create_account_move()
                return super(HRPayslip, self).action_payslip_done()

    create_direct_flag = fields.Boolean(default=False)

    def action_payslip_cancel(self):
        for rec in self:
            group_ids = self.env.ref('atheer_hr.group_hr_accounts').ids

            rec.write({'state': 'cancel', 'rejected_by': self.env.user.id, 'rejected_date': date.today()})
            rec.mapped('payslip_run_id').action_close()

    # FOR FINAL SETTLEMENT SALARY CALCULATION ATHEER Co.
    def find_get_new_worked_days_lines(self, date_from, date_to, contract_id):
        struct_id = contract_id.salary_structure_id
        if struct_id.use_worked_day_lines:
            # computation of the salary worked days
            worked_days_line_values = self.find_get_worked_day_lines(date_from, date_to, contract_id)
            worked_days_lines = []
            for r in worked_days_line_values:
                worked_days_lines.append(r)
            return worked_days_lines

    def _get_worked_day_lines_values(self, domain=None):
        self.ensure_one()
        res = []
        hours_per_day = self._get_worked_day_lines_hours_per_day()
        date_from = datetime.combine(self.date_from, datetime.min.time())
        date_to = datetime.combine(self.date_to, datetime.max.time())
        work_hours = self.contract_id._get_work_hours(date_from, date_to, domain=domain)
        work_hours_ordered = sorted(work_hours.items(), key=lambda x: x[1])
        biggest_work = work_hours_ordered[-1][0] if work_hours_ordered else 0
        add_days_rounding = 0
        for work_entry_type_id, hours in work_hours_ordered:
            work_entry_type = self.env['hr.work.entry.type'].browse(work_entry_type_id)
            days = round(hours / hours_per_day, 5) if hours_per_day else 0
            if work_entry_type_id == biggest_work:
                days += add_days_rounding
            day_rounded = self._round_days(work_entry_type, days)
            add_days_rounding += (days - day_rounded)
            if work_entry_type and work_entry_type.code.startswith('LEAVE'):
                line_type = 'leave'
            else:
                line_type = 'normal'
            attendance_line = {
                'sequence': work_entry_type.sequence,
                'work_entry_type_id': work_entry_type_id,
                'number_of_days': day_rounded,
                'number_of_hours': hours,
                'is_leave': work_entry_type.is_leave,
                'pay_perc': work_entry_type.pay_perc,
                'line_type': line_type,
            }
            res.append(attendance_line)
        return res

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """override and change out of office no of days"""
        res = []
        # fill only if the contract as a working schedule linked
        self.ensure_one()
        contract = self.contract_id
        if contract.resource_calendar_id:
            res = self._get_worked_day_lines_values(domain=domain)
            if not check_out_of_contract:
                return res

            # If the contract doesn't cover the whole month, create
            # worked_days lines to adapt the wage accordingly
            out_days, out_hours = 0, 0
            reference_calendar = self._get_out_of_contract_calendar()
            if self.date_from < contract.date_start:
                start = fields.Datetime.to_datetime(self.date_from)
                stop = fields.Datetime.to_datetime(contract.date_start) + relativedelta(days=-1, hour=23, minute=59)
                # function change from get_work_duration_data to get_all_work_duration_data
                out_time = reference_calendar.get_all_work_duration_data(start, stop, domain=['|', (
                    'work_entry_type_id', '=', False), ('work_entry_type_id.is_leave', '=', False)])
                out_days += out_time['days']
                out_hours += out_time['hours']
            if contract.date_end and contract.date_end < self.date_to:
                start = fields.Datetime.to_datetime(contract.date_end) + relativedelta(days=1)
                stop = fields.Datetime.to_datetime(self.date_to) + relativedelta(hour=23, minute=59)
                # function change from get_work_duration_data to get_all_work_duration_data
                out_time = reference_calendar.get_all_work_duration_data(start, stop, domain=['|', (
                    'work_entry_type_id', '=', False), ('work_entry_type_id.is_leave', '=', False)])
                out_days += out_time['days']
                out_hours += out_time['hours']

            if out_days or out_hours:
                work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_out_of_contract')
                res.append({
                    'sequence': work_entry_type.sequence,
                    'work_entry_type_id': work_entry_type.id,
                    'number_of_days': out_days,
                    'number_of_hours': out_hours,
                })
        return res

    def find_get_payslip_lines(self, find_res, employee_id):
        # self.ensure_one()
        contract_id = employee_id.contract_id
        salary_struct_id = contract_id.salary_structure_id
        localdict = self.env.context.get('force_payslip_localdict', None)
        if localdict is None:
            localdict = self.find_get_localdict(find_res, employee_id)
        if 'rules' in localdict:
            rules_dict = localdict['rules'].dict
            result_rules_dict = localdict['result_rules'].dict

            blacklisted_rule_ids = self.env.context.get('prevent_payslip_computation_line_ids', [])

            result = {}

            for rule in sorted(salary_struct_id.rule_ids, key=lambda x: x.sequence):
                if rule.id in blacklisted_rule_ids:
                    continue
                localdict.update({
                    'result': None,
                    'result_qty': 1.0,
                    'result_rate': 100})
                if rule._satisfy_condition(localdict):
                    amount, qty, rate = rule.find_compute_rule(localdict)
                    # check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    # set/overwrite the amount computed for this rule in the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    result_rules_dict[rule.code] = {'total': tot_rule, 'amount': amount, 'quantity': qty}
                    rules_dict[rule.code] = rule
                    # sum the amount for its salary category
                    localdict = rule.category_id._sum_salary_rule_category(localdict, tot_rule - previous_amount)
                    # Retrieve the line name in the employee's lang
                    employee_lang = employee_id.sudo().address_home_id.lang
                    # This actually has an impact, don't remove this line
                    context = {'lang': employee_lang}
                    if rule.code in ['BASIC', 'GROSS', 'NET']:  # Generated by default_get (no xmlid)
                        if rule.code == 'BASIC':
                            rule_name = _('Basic Salary')
                        elif rule.code == "GROSS":
                            rule_name = _('Gross')
                        if rule.code == 'NET':
                            rule_name = _('Net Salary')
                    else:
                        rule_name = rule.with_context(lang=employee_lang).name
                    # create/overwrite the rule in the temporary results

                    result[rule.code] = {
                        'sequence': rule.sequence,
                        'code': rule.code,
                        'name': rule_name,
                        'note': rule.note,
                        'salary_rule_id': rule.id,
                        'contract_id': localdict['contract'].id,
                        'employee_id': localdict['employee'].id,
                        'amount': amount,
                        'quantity': qty,
                        'rate': rate,
                        # 'slip_id': self.id,
                    }
            return result.values()

    def find_get_localdict(self, find_res, employee_id):
        contract_id = employee_id.contract_id
        localdict = {}
        if find_res:
            worked_days_dict = {line['sequence']: line for line in find_res if line['sequence']}
            employee = employee_id
            contract = contract_id
            localdict = {
                **self._get_base_local_dict(),
                **{
                    'categories': BrowsableObject(employee.id, {}, self.env),
                    'rules': BrowsableObject(employee.id, {}, self.env),
                    'payslip': Payslips(employee.id, self, self.env),
                    'worked_days': WorkedDays(employee.id, worked_days_dict, self.env),
                    # 'inputs': InputLine(employee.id, inputs_dict, self.env),
                    'employee': employee,
                    'contract': contract,
                    'result_rules': ResultRules(employee.id, {}, self.env)
                }
            }
        return localdict

    def find_get_timesheet_lines(self, employee_id, date_from, date_to):
        """fetch the list of timesheet lines of the employees"""
        query = """SELECT count(il.id) as days_worked, sum(il.hours) as hours, to_char(il.act_date, 'MM') as month,
            il.cost_center as bu_cc, il.ot_id as ot_id
            FROM hr_timesheet_import_lines il WHERE
            il.employee_id =""" + str(employee_id.id) + """
            AND il.act_date>='""" + str(date_from) + """' AND il.act_date<='""" + str(date_to) + """'
            GROUP BY
            to_char(il.act_date, 'MM'), il.cost_center,il.ot_id
        """
        self._cr.execute(query)
        worked_time_lines = []
        time_disc = self._cr.dictfetchall()
        for time_line in time_disc:
            worked_time_lines.append(time_line)
        return worked_time_lines


class PayslipTimesheetLine(models.Model):
    _name = 'payslip.timesheet.line'
    _description = 'Payslip Timesheet Line'

    payslip_id = fields.Many2one(comodel_name='hr.payslip', string='Payslip', required=True, ondelete='cascade')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    days = fields.Float(string='No. of Days in Month', default=0.0)
    days_worked = fields.Float(string='No. of Days Worked')
    bu_cc = fields.Many2one(comodel_name='account.analytic.account', string='CC Code')
    ot_id = fields.Selection([('normal', 'Normal OT'),
                              ('weekend', 'Weekend OT'),
                              ('ph', 'Public Holiday OT')],
                             default='normal')
    hours = fields.Float(string='Total Hours')
    month = fields.Integer(string="Month")
    company_id = fields.Many2one(comodel_name='res.company', string='Company', related='payslip_id.company_id')


class HRPayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _description = "Payslip Batch"
    _inherit = ['hr.payslip.run', 'portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # access flags
    send_back_flag = fields.Boolean(default=False)
    left_acc_flag = fields.Boolean(default=False)
    left_ch_flag = fields.Boolean(default=False)
    left_hr_flag = fields.Boolean(default=False)

    salary_period = fields.Char(compute="compute_salary_period", copy=False)

    def compute_salary_period(self):
        period = ''
        for rec in self:
            if rec.date_start and rec.date_end:
                if rec.date_start.month == rec.date_end.month:
                    period = ' ' + rec.date_start.strftime("%B") + ' ' + str(rec.date_start.year)
                else:
                    period = ' ' + str(rec.date_start.strftime("%B")) + ' ' + str(rec.date_start.year) + ' and ' + str(
                        rec.date_end.strftime("%B")) + ' ' + str(rec.date_end.year)
        self.salary_period = period

    @api.model
    def cron_confirm_payslip(self):
        """
        Cron To Confirm Payslip
        :return:
        """
        for record in self.env['hr.payslip.run'].search(
                [('confirm_cron', '=', True), ('state', '=', 'with_ceo')]):
            record.confirm_payslip_run()
            record.confirm_cron = False

    def confirm_payslip_run_to_queue(self):
        """
        :return:
        """
        for record in self:
            record.confirm_cron = True
            record.confirm_payslip_run()

    def confirm_payslip_run(self):
        start = time.time()
        _logger.warning("******************************************************************************")
        _logger.warning("Payslip Confirmation and Account Entry Generation Started")

        for record in self:
            for payslip in record.slip_ids:
                hold_ids = self.env['hr.payroll.hold'].search(
                    [('employee_id', '=', payslip.employee_id.id), ('date_from', '<=', payslip.date_from),
                     ('date_to', '<=', payslip.date_to), ('state', '=', 'on_hold')])
                if hold_ids:
                    payslip.state = 'hold'
                # payslip.process_sheet()
                if not hold_ids:
                    payslip.payslip_batch = True
                    payslip.action_payslip_done()
                    self._cr.execute("UPDATE hr_payslip_run SET state = 'close' WHERE id = {0}".format(record.id))
                    record.invalidate_cache()
                    end = time.time()
                    _logger.warning("Payslip Confirmation and Account Entry Generation Done")
                    _logger.warning("Total Time %s" % (end - start))

    def send_to_hr(self):
        """
               sending payslip batch to HR
        """
        import time
        start = time.time()
        p_ids = []
        e_ids = []
        for record in self:
            if not record.slip_ids:
                raise UserError("Add Some Pay Slips")
            else:
                for each in record.slip_ids:
                    payslip_ids = self.env['hr.payslip'].search([('date_to', '>', self.date_start),
                                                                 ('date_from', '<=', self.date_end),
                                                                 ('employee_id', '=', each.employee_id.id),
                                                                 ('state', 'not in', ['draft', 'cancel'])], limit=1)
                    if payslip_ids:
                        record.slip_ids = [(3, each.id)]
                        p_ids.append(payslip_ids.employee_id.id)
                    else:
                        e_ids.append(payslip_ids.employee_id)
                if not e_ids:
                    raise ValidationError(
                        _("Payslip has been already created for the employee for the particular period."))

                if len(record.slip_ids) > 1:
                    self._cr.execute("UPDATE hr_payslip SET state = 'with_hr' WHERE id in {0}".format(
                        tuple((record.slip_ids.ids))))
                elif len(record.slip_ids) == 1:
                    self._cr.execute("UPDATE hr_payslip SET state = 'with_hr' WHERE id = {0}".format(
                        record.slip_ids.ids[0]))
                for each in record.slip_ids:
                    each.compute_sheet()
                    each.left_acc_flag = True
                    each.send_back_flag = False
                record.left_acc_flag = True
                record.send_back_flag = False
                record.state = 'with_hr'
                responsible_users = self.sudo().env.ref('atheer_hr.group_hr_manager').users
                note = _('%(doc_name)s is approved by HR Manager',doc_name=record.name, doc_status=record.state)
                summary = _('%(doc_name)s %(doc_status)s', doc_name=record.name, doc_status=record.state)
                if responsible_users:
                    for responsible_user in responsible_users:
                        record.activity_schedule('atheer_hr.mail_act_payslip_run_notifications', note=note,
                                            user_id=responsible_user.id, date_deadline=record.date_end, summary=summary)
                record.invalidate_cache()

            end = time.time()
            if p_ids:
                self.employee_list = [(6, 0, p_ids)]
                message_id = self.env['message.wizard'].create(
                    {'message': _(
                        "Some employees have overlapping pay slip : Proceeding will delete the overlapping employees "
                        "from this list and payslip will be created for the remaining employees !!")})
                return {
                    'name': _('Alert'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'message.wizard',
                    'res_id': message_id.id,
                    'target': 'new'
                }

            _logger.warning("Payslip Computation End")
            _logger.warning("Total Time Taken %s" % (end - start))
            _logger.warning("******************************************************************************")

    def send_to_accounts(self):
        """

        ('accounts', 'Finance'),
        """
        for record in self:
            if len(record.slip_ids) > 1:
                self._cr.execute("UPDATE hr_payslip SET state = 'accounts' WHERE id in {0}".format(
                    tuple((record.slip_ids.ids))))
            elif len(record.slip_ids) == 1:
                self._cr.execute("UPDATE hr_payslip SET state = 'accounts' WHERE id = {0}".format(
                    record.slip_ids.ids[0]))
            for each in record.slip_ids:
                each.left_hr_flag = True
                each.send_back_flag = False
            record.state = 'accounts'
            responsible_users = self.sudo().env.ref('atheer_hr.group_hr_manager').users
            note = _('%(doc_name)s is send to accounts',doc_name=record.name, doc_status=record.state)
            summary = _('%(doc_name)s %(doc_status)s', doc_name=record.name, doc_status=record.state)
            if responsible_users:
                for responsible_user in responsible_users:
                    record.activity_schedule('atheer_hr.mail_act_payslip_run_notifications', note=note,
                                        user_id=responsible_user.id, date_deadline=record.date_end, summary=summary)

    def send_to_ceo(self):
        """
              sending payslip batch to CEO
        """
        for record in self:
            if len(record.slip_ids) > 1:
                self._cr.execute("UPDATE hr_payslip SET state = 'with_ceo' WHERE id in {0}".format(
                    tuple((record.slip_ids.ids))))
            elif len(record.slip_ids) == 1:
                self._cr.execute("UPDATE hr_payslip SET state = 'with_ceo' WHERE id = {0}".format(
                    record.slip_ids.ids[0]))
            for each in record.slip_ids:
                each.left_hr_flag = True
                each.send_back_flag = False
            record.state = 'with_ceo'
            responsible_users = self.sudo().env.ref('atheer_hr.group_hr_manager').users
            note = _('%(doc_name)s is sent to CEO',doc_name=record.name, doc_status=record.state)
            summary = _('%(doc_name)s %(doc_status)s', doc_name=record.name, doc_status=record.state)
            if responsible_users:
                for responsible_user in responsible_users:
                    record.activity_schedule('atheer_hr.mail_act_payslip_run_notifications', note=note,
                                        user_id=responsible_user.id, date_deadline=record.date_end, summary=summary)

    def send_back(self):
        for record in self:
            if record.state == 'with_hr':
                if len(record.slip_ids) > 1:
                    self._cr.execute("UPDATE hr_payslip SET state = 'draft' WHERE id in {0}".format(
                        tuple((record.slip_ids.ids))))
                elif len(record.slip_ids) == 1:
                    self._cr.execute("UPDATE hr_payslip SET state = 'draft' WHERE id = {0}".format(
                        record.slip_ids.ids[0]))
                record.state = 'draft'
                record.send_back_flag = True

            elif record.state == 'with_ceo':
                if len(record.slip_ids) > 1:
                    self._cr.execute("UPDATE hr_payslip SET state = 'accounts' WHERE id in {0}".format(
                        tuple((record.slip_ids.ids))))
                elif len(record.slip_ids) == 1:
                    self._cr.execute("UPDATE hr_payslip SET state = 'accounts' WHERE id = {0}".format(
                        record.slip_ids.ids[0]))
                # record.slip_ids.write({'state': 'with_hr'})
                record.state = 'accounts'
                record.send_back_flag = True
                record.confirm_cron = False
            elif record.state == 'accounts':
                if len(record.slip_ids) > 1:
                    self._cr.execute("UPDATE hr_payslip SET state = 'with_hr' WHERE id in {0}".format(
                        tuple((record.slip_ids.ids))))
                elif len(record.slip_ids) == 1:
                    self._cr.execute("UPDATE hr_payslip SET state = 'with_hr' WHERE id = {0}".format(
                        record.slip_ids.ids[0]))
                # record.slip_ids.write({'state': 'with_hr'})
                record.state = 'with_hr'
                record.send_back_flag = True
                record.confirm_cron = False

    def cancel(self):
        """
        Cancel related payslip batch, related JE for payslip and delete payslips.
        :return:
        """
        for record in self:
            for each in record.slip_ids:
                each.create_direct_flag = True
            record.slip_ids and record.slip_ids.action_payslip_cancel()
            record.slip_ids and record.message_post(
                body="Timesheet, Related Payslip Batch and Payslips Rejected.\n Reference %s" % [rec.number for rec in
                                                                                                 record.slip_ids],
                subtype_xmlid="mail.mt_comment",
                message_type="notification")
            record.state = 'cancel'

    def unlink_payslips(self):
        """
        Delete The payslip with the related timesheet. Before unlink make sure the related JE is unposted and removed.
        :return:
        """
        for record in self:
            if record.state == 'cancel':
                record.slip_ids and record.slip_ids.action_payslip_cancel()  # Just to make sure. JE is removed
                slips = [rec.number for rec in record.slip_ids]
                record.slip_ids and record.slip_ids.unlink()
                record.state = 'cancel'
                record.message_post(
                    body="Payslips Removed.\n Reference %s" % slips,
                    subtype_xmlid="mail.mt_comment",
                    message_type="notification")

    state = fields.Selection(selection_add=[
        ('draft', 'HR Admin'),
        ('with_hr', 'HR MANAGER'),
        ('accounts', 'Finance Controller'),
        ('with_ceo', 'CEO'),
        ('close', 'PAYSLIPS CONFIRMED'),
        ('cancel', 'REJECTED'),
    ])

    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', 'Payslips', required=False, readonly=True,
                               states={'draft': [('readonly', False)], 'done': [('readonly', False)],
                                       'with_hr': [('readonly', False)]}, tracking=True)
    user_id = fields.Many2one('res.users', readonly=True)
    confirm_cron = fields.Boolean(string="In Queue For Confirming Payslips")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    create_cron = fields.Boolean(string="In Queue For Creating Payslips")
    withhold_salary_emp = fields.One2many(comodel_name='hr.payroll.hold', inverse_name='payslip_batch_id',
                                          string='Salary Hold', copy=False)
    payroll_hold = fields.Boolean(default=False, copy=False)
    payslip_created = fields.Boolean(default=False, copy=False)
    employee_list = fields.Many2many('hr.employee', string='Employee')
    count_salary_hold = fields.Float(string='Salary Withhold')
    process_salary = fields.Boolean(string='SIF Generated', readonly=True)
    date_pay = fields.Date(string='SIF Generated Date', readonly=True)
    sif_name = fields.Char(string='SIF', copy=False, readonly=True)
    total_amount = fields.Float(string='Total Amount', digits=(16, 3), compute='get_total_amount')
    journal_id = fields.Many2one('account.journal', 'Salary Journal')
    total_wage = fields.Float(compute='_compute_withhold_salary', digits=(16, 3), string='Grand Total of Wages')
    total_basic = fields.Float(compute='_compute_withhold_salary', digits=(16, 3), string='Grand Total of Basic')
    zero_wage = fields.Boolean(compute='_compute_withhold_salary')
    emp_list = fields.Char(compute='_compute_withhold_salary')

    _defaults = {
        'user_id': lambda self, cr, uid, ctx=None: uid
    }

    def _valid_field_parameter(self, field, name):
        return name == 'ondelete' or super()._valid_field_parameter(field, name)

    @api.depends('slip_ids')
    def get_total_amount(self):
        """:return payslip total amount"""
        for rec in self:
            rec.total_amount = sum(slip.computed_salary for slip in rec.slip_ids) if rec.slip_ids else 0

    def _compute_withhold_salary(self):
        """get the count of the employees whose salary is not processed"""
        for record in self:
            employee_ids = [emp.employee_id.id for emp in self.slip_ids if emp.payroll_hold]
            if employee_ids:
                record.payroll_hold = True
            list = [str(slip.employee_id) for slip in
                    record.slip_ids.filtered(lambda x: x.computed_salary <= 0)]
            if list:
                self.zero_wage = True
            else:
                self.zero_wage = False
            self.emp_list = list
        wage = 0
        basic = 0
        for rec in self.slip_ids:
            wage = wage + rec.net_wage
            basic = basic + rec.basic_wage
        self.total_wage = wage
        self.total_basic = basic

    def action_employee_list(self):
        """ This opens the xml view specified in xml_id for the employees """
        e_ids = [emp.employee_id.id for emp in self.slip_ids if emp.payroll_hold]
        p_ids = []
        for rec in e_ids:
            payslip_id = self.env['hr.payslip'].search([('date_to', '>', self.date_start),
                                                        ('date_from', '<=', self.date_end),
                                                        ('employee_id', '=', rec),
                                                        ('state', 'not in', ['draft', 'cancel'])], limit=1)
            p_ids.append(payslip_id.id)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payslip'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.payslip',
            'domain': str([('id', 'in', tuple(p_ids))]),
            "views": [[False, "tree"], [False, "form"]],
            'context': {
                'create': False, 'edit': False,
            }
        }

    def action_open_payslips(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [['id', 'in', self.slip_ids.ids]],
            "name": "Payslips",
            'context': {
                'create': False, 'edit': False,
            }
        }

    overlapping_count = fields.Integer(compute='_compute_overlapping_count')
    payroll_hold_count = fields.Integer(compute='_compute_payroll_hold_count')

    def _compute_payroll_hold_count(self):
        e_ids = [emp.employee_id.id for emp in self.slip_ids if emp.payroll_hold]
        p_ids = []
        for rec in e_ids:
            payslip_id = self.env['hr.payslip'].search([('date_to', '>', self.date_start),
                                                        ('date_from', '<=', self.date_end),
                                                        ('employee_id', '=', rec),
                                                        ('payroll_hold', '=', True),
                                                        ('state', 'not in', ['draft', 'cancel'])], limit=1)
            if payslip_id.id:
                p_ids.append(payslip_id.id)
        self.payroll_hold_count = len(p_ids)

    def _compute_overlapping_count(self):
        p_ids = []
        for rec in self.employee_list:
            payslip_id = self.env['hr.payslip'].search([('date_to', '>', self.date_start),
                                                        ('date_from', '<=', self.date_end),
                                                        ('employee_id', '=', rec.id),
                                                        ('state', 'not in', ['draft', 'cancel'])], limit=1)
            p_ids.append(payslip_id.id)
        self.overlapping_count = len(p_ids)

    def action_payslip_employee_list(self):
        """ This opens the xml view specified in xml_id for the employees """
        p_ids = []
        for rec in self.employee_list:
            payslip_id = self.env['hr.payslip'].search([('date_to', '>', self.date_start),
                                                        ('date_from', '<=', self.date_end),
                                                        ('employee_id', '=', rec.id),
                                                        ('state', 'not in', ['draft', 'cancel'])], limit=1)
            p_ids.append(payslip_id.id)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payslip'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.payslip',
            'domain': str([('id', 'in', tuple(p_ids))]),
            "views": [[False, "tree"], [False, "form"]],
            'context': {
                'create': False, 'edit': False,
            }
        }


class HRPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def compute_sheet(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            today = fields.date.today()
            first_day = today + relativedelta(day=1)
            last_day = today + relativedelta(day=31)
            if from_date == first_day and end_date == last_day:
                batch_name = from_date.strftime('%B %Y')
            else:
                batch_name = _('From %s to %s', format_date(self.env, from_date), format_date(self.env, end_date))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': batch_name,
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        employees = self.with_context(active_test=False).employee_ids
        if not employees:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        # Prevent a payslip_run from having multiple payslips for the same employee
        employees -= payslip_run.slip_ids.employee_id
        success_result = {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }
        if not employees:
            return success_result

        payslips = self.env['hr.payslip']
        Payslip = self.env['hr.payslip']

        contracts = employees._get_contracts(
            payslip_run.date_start, payslip_run.date_end, states=['open', 'close']
        ).filtered(lambda c: c.active)
        date_start = fields.Datetime.to_datetime(payslip_run.date_start)
        date_stop = datetime.combine(fields.Datetime.to_datetime(payslip_run.date_end), datetime.max.time())
        contracts._generate_work_entries(date_start, date_stop)
        work_entries = self.env['hr.work.entry'].search([
            ('date_start', '<=', payslip_run.date_end),
            ('date_stop', '>=', payslip_run.date_start),
            ('employee_id', 'in', employees.ids),
        ])
        self._check_undefined_slots(work_entries, payslip_run)

        if (self.structure_id.type_id.default_struct_id == self.structure_id):
            work_entries = work_entries.filtered(lambda work_entry: work_entry.state != 'validated')
            if work_entries._check_if_error():
                work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])

                for work_entry in work_entries.filtered(lambda w: w.state == 'conflict'):
                    work_entries_by_contract[work_entry.contract_id] |= work_entry

                for contract, work_entries in work_entries_by_contract.items():
                    conflicts = work_entries._to_intervals()
                    time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in conflicts._items]])
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Some work entries could not be validated.'),
                        'message': _('Time intervals to look for:%s', time_intervals_str),
                        'sticky': False,
                    }
                }

        default_values = Payslip.default_get(Payslip.fields_get())
        payslips_vals = []
        for contract in self._filter_contracts(contracts):
            values = dict(default_values, **{
                'name': _('New Payslip'),
                'employee_id': contract.employee_id.id,
                # 'credit_note': payslip_run.credit_note,
                'payslip_run_id': payslip_run.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
                'contract_id': contract.id,
                'struct_id': self.structure_id.id or contract.structure_type_id.default_struct_id.id,
            })
            payslips_vals.append(values)
        payslips = Payslip.with_context(tracking_disable=True).create(payslips_vals)

        payroll_hold_ids = [emp.employee_id.id for emp in payslips if emp.payroll_hold]
        if payroll_hold_ids:
            payslip_run.payroll_hold = True
        payslips._compute_name()
        payslips._onchange_employee()
        payslips.compute_sheet()
        payslip_run.state = 'draft'
        return success_result


class HRPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    amount = fields.Monetary(string='Amount', digits=(16, 6), compute='_compute_amount', store=True)
    amount_orig = fields.Monetary(string='Amount (Without Deduction)', digits=(16, 6),
                                  compute='_compute_amount', store=True)
    amount_unpaid = fields.Monetary(string='Unpaid Amount', digits=(16, 6), compute='_compute_amount', store=True)
    pay_perc = fields.Selection([('100', '100 %'), ('75', '75 %'), ('50', '50 %'), ('25', '25 %'), ('0', '0 %')],
                                string="Paid %", default='100')
    is_leave = fields.Boolean(string="Is Leave")

    # updated for Atheer co. in order to update line type in worked days for computing leaves
    @api.model
    def create(self, vals_list):
        res = super(HRPayslipWorkedDays, self).create(vals_list)
        p = res.payslip_id._get_worked_day_lines_values(domain=[])
        for record in p:
            if record.get('work_entry_type_id') == res['work_entry_type_id'].id:
                res.update({'line_type': record.get('line_type')})

        return res

    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):
        for worked_days in self.filtered(lambda wd: not wd.payslip_id.edited):
            if not worked_days.contract_id or worked_days.code == 'OUT':
                worked_days.amount = 0
                worked_days.amount_orig = 0
                worked_days.amount_unpaid = 0
                continue
            if worked_days.payslip_id.wage_type == "hourly":
                worked_days_amount = worked_days.payslip_id.contract_id.hourly_wage * worked_days.number_of_hours
                paid_amount = (
                                          int(worked_days.pay_perc) * worked_days_amount) / 100 if worked_days.is_paid else worked_days_amount
            else:
                worked_days_amount = worked_days.payslip_id.contract_id.contract_wage * worked_days.number_of_hours / (
                        worked_days.payslip_id.sum_worked_hours or 1)
                paid_amount = (
                                          int(worked_days.pay_perc) * worked_days_amount) / 100 if worked_days.is_paid else worked_days_amount
            worked_days.amount = paid_amount
            worked_days.amount_orig = worked_days_amount
            # TODO Ashwini, Make sure the computaion needs worked_days_amount - paid_amount calculation, nothing in hours
            # worked_days.amount_unpaid = worked_days_amount - paid_amount
            worked_days.amount_unpaid = paid_amount

    @api.depends('work_entry_type_id')
    def _effective_days(self):
        for record in self:
            is_annual_leave = False
            record.effective_days = 0.0
            if record.work_entry_type_id.is_leave:
                leave = self.env['hr.leave.type'].search([
                    ('work_entry_type_id', '=', record.work_entry_type_id.id)], limit=1)
                if leave.annual_leave:
                    is_annual_leave = True
                record.effective_days = record.number_of_days
            else:
                leave = self.env['hr.leave.type'].search([
                    ('work_entry_type_id', '=', record.work_entry_type_id.id)], limit=1)
                if not leave.is_unpaid:
                    record.effective_days = record.number_of_days
            record.annual_leave = is_annual_leave

    name = fields.Char(related='', string='Description', readonly=True)
    line_type = fields.Selection([('normal', 'Normal'), ('leave', 'Leave')], 'Line Type')
    bu_cc = fields.Many2one('account.analytic.account', 'Business Unit')
    ot_id = fields.Selection([('normal', 'Normal OT'),
                              ('weekend', 'Weekend OT'),
                              ('ph', 'Public Holiday OT')],
                             default='normal')
    effective_days = fields.Float(string='Effective Days', compute='_effective_days')
    annual_leave = fields.Boolean('Annual Leave', compute='_effective_days')
    month = fields.Integer(string="Month Reference")
    max_days = fields.Integer(string="Month Max Days")
    company_id = fields.Many2one('res.company', 'Company', related='payslip_id.company_id')

    def _valid_field_parameter(self, field, name):
        return name == 'digits' or super()._valid_field_parameter(field, name)


class AdditionDeduction(models.Model):
    _name = 'hr.payslip.extra'
    _description = "Payslip Extra"

    def button_confirm(self):
        if self.line_ids:
            self.state = 'confirm'

    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    line_ids = fields.One2many('hr.payslip.extra.lines', 'hr_payslip_extra', 'Lines')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'DRAFT'), ('confirm', 'CONFIRMED')], default='draft')

    def _valid_field_parameter(self, field, name):
        # I can't even
        return name == 'ondelete' or super()._valid_field_parameter(field, name)


class AdditionDeductionLines(models.Model):
    _name = 'hr.payslip.extra.lines'
    _description = "Payslip Extra Lines"

    hr_payslip_extra = fields.Many2one('hr.payslip.extra')
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    salary_rule = fields.Many2one('hr.salary.rule', 'Salary Rule', required=True)
    amount = fields.Float('Amount', required=True)
    company_id = fields.Many2one('res.company', 'Company', related='hr_payslip_extra.company_id')


class SalaryHold(models.Model):
    _name = 'salary.hold'
    _description = 'Salary Hold'
    _order = 'id desc'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', copy=False, required=True,
                                  readonly=True)
    payslip_id = fields.Many2one(comodel_name='hr.payslip', string='Payslip', copy=False, readonly=True)
    std_salary = fields.Float(string='Standard Salary', digits=(16, 3), readonly=True)
    computed_salary = fields.Float(string='Net Salary', digits=(16, 3), readonly=True)
    additions = fields.Float(string='Additions', digits=(16, 3), readonly=True)
    deductions = fields.Float(string='Deductions', digits=(16, 3), readonly=True)
    process_salary = fields.Boolean(string='Salary Withdrawn', readonly=True)
    date_from = fields.Date(string='From Date', readonly=True)
    date_to = fields.Date(string='To Date', readonly=True)
    date_pay = fields.Date(string='Payment Date', readonly=True)
    batch_id = fields.Many2one(comodel_name='hr.payslip.run', string='Payslip Batch', readonly=True)
    file_name = fields.Char(string='File Name', copy=False, readonly=True)


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    online_account = fields.Boolean(string='Online Bank')


class HRSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    type = fields.Selection(
        [('add', 'Additions'), ('remove', 'Deductions'), ('ls', 'Leave Salary'), ('grty', 'Gratuity')], 'Rule Type',
        required=True, default='add')
    basic = fields.Boolean(string="Basic")
    bonus = fields.Boolean(string="Bonus")
    net_salary = fields.Boolean(string="Net Salary")
    loan = fields.Boolean(string="Loan")
    addition = fields.Boolean(string="Addition")
    deletion = fields.Boolean(string="Deletion")
    overtime = fields.Boolean(string="Overtime")
    amount_fix = fields.Float(string='Fixed Amount', digits=(16, 3))
    is_regular_pay = fields.Boolean(related='struct_id.is_regular_pay')

    def find_compute_rule(self, localdict):
        """
               :param localdict: dictionary containing the current computation environment
               :return: returns a tuple (amount, qty, rate)
               :rtype: (float, float, float)
               """
        # self.ensure_one()
        if self.fs_amount_select == 'fix':
            try:
                return self.fs_amount_fix or 0.0, float(safe_eval(self.fs_quantity, localdict)), 100.0
            except Exception as e:
                raise UserError(
                    _('Wrong quantity defined for salary rule %s (%s).\nError: %s') % (self.name, self.code, e))
        if self.fs_amount_select == 'percentage':
            try:
                return (float(safe_eval(self.fs_amount_percentage_base, localdict)),
                        float(safe_eval(self.fs_quantity, localdict)),
                        self.fs_amount_percentage or 0.0)
            except Exception as e:
                raise UserError(_('Wrong percentage base or quantity defined for salary rule %s (%s).\nError: %s') % (
                    self.name, self.code, e))
        else:  # python code
            try:
                safe_eval(self.fs_amount_python_compute or 0.0, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), localdict.get('result_qty', 1.0), localdict.get('result_rate', 100.0)
            except Exception as e:
                raise UserError(
                    _('Wrong python code defined for salary rule %s (%s).\nError: %s') % (self.name, self.code, e))

    # for final_settlement
    fs_amount_select = fields.Selection(string='Amount Type ', index=True, related='amount_select')
    fs_amount_fix = fields.Float(string='Fixed Amount ', related='amount_fix', store=True, digits='Payroll')
    fs_amount_percentage = fields.Float(string='Percentage (%) ', store=True, related='amount_percentage',
                                        digits='Payroll Rate')
    fs_amount_python_compute = fields.Text(string='Python Code ', store=True)
    fs_amount_percentage_base = fields.Char(string='Percentage based on ', store=True, related='amount_percentage_base',
                                            help='result will be affected to a variable')
    fs_quantity = fields.Char(string="Quantity ", store=True)


class HrPayslipLineInherit(models.Model):
    _inherit = 'hr.payslip.line'
    _description = 'Payslip Line'

    rate = fields.Float(string='Rate (%)', digits=(16, 3), default=100.0)
    amount = fields.Float(digits=(12, 6), default=1.000)
    quantity = fields.Float(digits=(12, 12), default=1.000)
    total = fields.Float(compute='_compute_total', digits=(12, 6), string='Total', store=True)


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    pay_perc = fields.Selection([('100', '100 %'), ('75', '75 %'), ('50', '50 %'), ('25', '25 %'), ('0', '0 %')],
                                string="Payment %", default='100', required=True)
