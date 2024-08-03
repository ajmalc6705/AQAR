# -*- coding: utf-8 -*-

import math
from lxml import etree
import json
import logging
from collections import namedtuple, defaultdict
from datetime import datetime, timedelta, time, date
from odoo.addons.resource.models.resource import float_to_time
from pytz import timezone, UTC
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period, week_type')


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    leave_balance = fields.Float(string="Leave Balance", readonly=True)

    paid_leaves = fields.Float(string="Paid Leaves", store=True, readonly=True)
    reference = fields.Char(string="Reference", tracking=True, readonly=True)
    bool_check = fields.Boolean(default=False)

    # request_date_from = fields.Date('Request Start Date', store=True)
    # request_date_to = fields.Date('Request End Date', store=True)
    date = fields.Date(string='Date', readonly=True, default=fields.Date.today)

    # Employee details
    designation = fields.Many2one('hr.job', string='Designation', related='employee_id.job_id')
    joining_date = fields.Date(string="Date Of Joining", related='employee_id.joining_date')
    employee_category = fields.Selection(related='employee_id.employee_category')

    given_leave_types = fields.Selection(
        [('emergency_leave', 'Emergency'), ('contractual', 'Contractual'), ('other', 'Other')],
        string="Reason For Leave:")
    emergency_leave = fields.Boolean(string="Emergency:", readonly=True,
                                     states={'draft': [('readonly', False)], 'validate1': [('readonly', False)],
                                             'employee': [('readonly', False)],
                                             'site_engineer': [('readonly', False)]}, tracking=True)
    contractual = fields.Boolean(string="Contractual:", readonly=True,
                                 states={'draft': [('readonly', False)], 'validate1': [('readonly', False)],
                                         'employee': [('readonly', False)],
                                         'site_engineer': [('readonly', False)]}, tracking=True)
    other = fields.Boolean(string="Other:", readonly=True,
                           states={'draft': [('readonly', False)], 'validate1': [('readonly', False)],
                                   'employee': [('readonly', False)],
                                   'site_engineer': [('readonly', False)]}, tracking=True)
    is_annual = fields.Boolean(default=False, compute='compute_annual')
    other_reason = fields.Char(string='Give Reason if other:',
                               states={'draft': [('readonly', False)], 'validate1': [('readonly', False)]},
                               tracking=True)
    emp_signature = fields.Binary(string='Employee Signature', readonly=False,
                                  help='Signature received from Employee.', copy=False,
                                  attachment=True)
    lm_signature = fields.Binary(string='Line Manager Signature', readonly=False,
                                 help='Signature received from Line Manager.', copy=False,
                                 attachment=True)
    hr_signature = fields.Binary(string='HR Signature', readonly=False,
                                 help='Signature received from HR.', copy=False,
                                 attachment=True)

    approved_days = fields.Integer(string="Approved Days", readonly=True,
                                   states={'draft': [('readonly', False)], 'validate1': [('readonly', False)],
                                           'employee': [('readonly', False)],
                                           'site_engineer': [('readonly', False)]}, tracking=True)
    # site_incharge_remark = fields.Char(string='Site Incharge’s Remarks',
    #                                    states={'draft': [('readonly', False)], 'validate1': [('readonly', False)],
    #                                            'site_engineer': [('readonly', False)]},
    #                                    tracking=True)
    site_incharge_signature = fields.Binary(help='Signature', readonly=False, copy=False,
                                            attachment=True)
    leave_salary = fields.Selection(
        [('paid', 'Yes'), ('not_paid', 'No')],
        string="Leave Salary Paid:")
    guarantors_required = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string="Guarantors Required:")
    leave_salary_paid = fields.Boolean(string="leave_salary_paid", readonly=True,
                                       states={'draft': [('readonly', False)], 'validate1': [('readonly', False)],
                                               'employee': [('readonly', False)],
                                               'site_engineer': [('readonly', False)]}, tracking=True)
    leave_salary_not_paid = fields.Boolean(string="leave_salary_not_paid", readonly=True,
                                           states={'draft': [('readonly', False)], 'validate1': [('readonly', False)],
                                                   'employee': [('readonly', False)],
                                                   'site_engineer': [('readonly', False)]}, tracking=True)
    guarantors_not_required = fields.Boolean(string="guarantors_not_required", readonly=True,
                                             states={'draft': [('readonly', False)], 'validate1': [('readonly', False)],
                                                     'employee': [('readonly', False)],
                                                     'site_engineer': [('readonly', False)]}, tracking=True)
    hr_remark = fields.Text(string="HR Remarks", tracking=True)
    remark_by_hod = fields.Text(string="Remarks by H.O.D", tracking=True)
    line_manager_remark = fields.Text(string="Line Manager Remarks", tracking=True)
    # ceo_remark = fields.Text(string="CEO Remarks", tracking=True)
    hod = fields.Text(string="H.O.D Remarks", tracking=True)
    director = fields.Text(string="Director", tracking=True)
    rejoining_date = fields.Date(string="Rejoining Date", readonly=True, store=True)

    state = fields.Selection(
        [('draft', 'Employee'), ('draft2', 'Site Engineer'), ('confirm', 'Line Manager'), ('refuse', 'Refused'),
         ('validate1', 'HR Manager'), ('ceo', 'CEO'), ('approved', 'Approved'), ('validate', 'Leave Confirmed'),
         ('cancel', 'Cancelled')], compute=False, default='draft',
        string="Status", store=True, tracking=True, copy=False, readonly=False)

    leave_return = fields.Boolean(default=False)
    leave_extended = fields.Boolean(default=False)
    leave_returned = fields.Boolean(default=False)
    is_eligible_for_annual_leave = fields.Boolean(string="Eligible for Annual Leave",
                                                  related="employee_id.is_eligible_for_annual_leave")
    leave_extension = fields.Boolean(default=False)

    unpaid_leaves = fields.Float(string="Unpaid Leaves", store=True, readonly=True)
    annual_leave = fields.Boolean(default=False)
    leave_return_id = fields.Many2one('hr.leave.return', string="Leave Return Id")
    current_year = fields.Char(string="Current Year")
    is_sick = fields.Boolean(default=False)
    is_unpaid = fields.Boolean(related='holiday_status_id.is_unpaid')
    annual_leave_confirmed = fields.Boolean(default=False)
    direct_req = fields.Boolean(default=False)
    leave_type_request_unit = fields.Selection(string='Hour from ', related='holiday_status_id.request_unit',
                                               readonly=True)
    payslip_created = fields.Boolean(default=False)
    attendance_true = fields.Boolean(default=False)
    leave_salary_true = fields.Boolean(default=False)
    extension_description = fields.Char(string="Extension Description", readonly=True, store=True)
    confirm_description = fields.Char(string="Confirmation Description", readonly=True, store=True)
    rejected_by = fields.Many2one('res.users', string="Refused BY")
    rejected_date = fields.Date(string="Refused Date")
    # access flags
    send_back_flag = fields.Boolean(default=False, copy=False)
    left_emp_flag = fields.Boolean(default=False, copy=False)
    left_se_flag = fields.Boolean(default=False, copy=False)
    left_lm_flag = fields.Boolean(default=False, copy=False)
    left_pm_flag = fields.Boolean(default=False, copy=False)
    left_hr_flag = fields.Boolean(default=False, copy=False)
    left_annual_hr_flag = fields.Boolean(default=False, copy=False)
    left_ch_flag = fields.Boolean(default=False, copy=False)
    acc_user_id = fields.Many2one('res.users', compute='compute_user_id', store=True, tracking=True)
    lm_user_id = fields.Many2one('res.users', compute='compute_user_id', store=True, tracking=True)
    pm_user_id = fields.Many2one('res.users', compute='compute_user_id', store=True, tracking=True)
    created_user_id = fields.Many2one('res.users', string='Created By', required=False,
                                      default=lambda self: self.env.user)
    created_emp_id = fields.Many2one('hr.employee', related='created_user_id.employee_id', string="Created Employee")
    created_user_department = fields.Many2one(comodel_name='hr.department', string="Department",
                                              related='created_emp_id.department_id')
    created_user_designation = fields.Many2one(comodel_name='hr.job', string="Designation",
                                               related='created_emp_id.job_id')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.depends('holiday_type')
    def _compute_from_holiday_type(self):
        if not self.env.user.employee_id:
            raise UserError(_("Employee is not linked with the user !"))
        return super(HrLeave, self)._compute_from_holiday_type()

    def _get_number_of_days(self, date_from, date_to, employee_id):
        result = super(HrLeave, self)._get_number_of_days(date_from, date_to, employee_id)
        if employee_id:
            if self.holiday_status_id.leave_days_type == 'calendar_days':
                result = {'days': 0, 'hours': 0}
                diff = date_to - date_from
                result['days'] = diff.days + 1
            return result

    # @api.constrains('holiday_status_id', 'number_of_days')
    # def _check_allocation_duration(self):
    #     for rec in self:
    #         if rec.holiday_status_id.requires_allocation == 'yes' \
    #                 and rec.number_of_days > rec.holiday_allocation_id.number_of_days \
    #                 and not rec.holiday_status_id.annual_leave:
    #             raise ValidationError(_("You have several allocations for those type and period.\n"
    #                                     "Please split your request to fit in their number of days."))

    @api.constrains('state', 'number_of_days', 'holiday_status_id')
    def _check_holidays(self):
        for holiday in self:
            if holiday.holiday_type != 'employee' or not holiday.employee_id or not holiday.holiday_status_id or holiday.holiday_status_id.requires_allocation == 'no':
                continue
            mapped_days = holiday.holiday_status_id.get_employees_days([holiday.employee_id.id],
                                                                       holiday.date_from.date())
            leave_days = mapped_days[holiday.employee_id.id][holiday.holiday_status_id.id]
            if not holiday.holiday_status_id.annual_leave and float_compare(leave_days['remaining_leaves'], 0,
                                                                            precision_digits=2) == -1 or float_compare(
                    leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
                raise ValidationError(_('The number of remaining time off is not sufficient for this time off type.\n'
                                        'Please also check the time off waiting for validation.') + '\n- %s' % holiday.display_name)
            if holiday.employee_id and holiday.holiday_status_id.annual_leave and holiday.number_of_days:
                joining_date = holiday.employee_id.joining_date
                check = True
                holiday.annual_leave_check(holiday.request_date_from, joining_date, holiday.request_date_to, check)

    @api.onchange('holiday_status_id', 'employee_id')
    def onchange_holiday_type(self):
        for rec in self:
            if rec.holiday_status_id:
                rec.leave_balance = rec.holiday_status_id.remaining_leaves
                if rec.holiday_status_id.annual_leave:
                    rec.annual_leave = True
                else:
                    rec.annual_leave = False
                if rec.holiday_status_id.is_sick:
                    rec.is_sick = True
                else:
                    rec.is_sick = False

    @api.depends('employee_id')
    def compute_user_id(self):
        for record in self:
            if record.employee_id.parent_id:
                record.lm_user_id = record.employee_id.parent_id.user_id.id
            elif record.employee_id.user_id.has_group('atheer_hr.group_hr_line_manager'):
                record.lm_user_id = record.employee_id.user_id.id
            else:
                record.lm_user_id = False

            if record.employee_id.user_id.has_group('atheer_hr.group_hr_accounts'):
                record.acc_user_id = record.employee_id.user_id.id
            else:
                record.acc_user_id = False

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        if self.env.is_superuser():
            return

    # @api.model
    # def create(self, vals_list):
    #     print(vals_list,"#########################################################")
    #     vals_list['reference'] = self.env['ir.sequence'].next_by_code('hr.leave') or 'New'
    #     if vals_list.get('request_date_from') and vals_list.get('request_date_to') and \
    #             not vals_list.get('date_from') and not vals_list.get('date_to') and vals_list.get('employee_id'):
    #         vals_list = self.update_datetime_from_date(vals_list)
    #     print(vals_list,"&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
    #     res = super(HrLeave, self).create(vals_list)
    #     res.current_year = res.request_date_from.year
    #     leaves = self.env['hr.leave'].search(
    #         [('employee_id', '=', vals_list['employee_id']), ('holiday_status_id.is_sick', '=', False),
    #          ('state', '=', 'validate')])
    #     conditional_leaves = leaves.filtered(lambda
    #                                              x: x.holiday_status_id.annual_leave == True or x.holiday_status_id.is_unpaid == True or x.holiday_status_id.is_emergency_leave == True)
    #     if leaves:
    #         if 'direct_req' in vals_list:
    #             direct_req = vals_list['direct_req']
    #         else:
    #             direct_req = self.direct_req
    #             for rec in conditional_leaves:
    #                 if not direct_req:
    #                     if not rec.leave_returned:
    #                         raise ValidationError(_(
    #                             "You cannot create a new leave request as you don't have leave return for the previous leaves"))
    #     return res

    # def update_datetime_from_date(self, vals):
    #     request_date_from = fields.Date.from_string(vals.get('request_date_from'))
    #     request_date_to = fields.Date.from_string(vals.get('request_date_to'))
    #     employee_id = self.env['hr.employee'].browse(vals.get('employee_id'))
    #     tz = employee_id.tz
    #
    #     resource_calendar_id = employee_id.resource_calendar_id or self.env.company.resource_calendar_id
    #     domain = [('calendar_id', '=', resource_calendar_id.id), ('display_type', '=', False)]
    #     attendances = self.env['resource.calendar.attendance'].read_group(domain, ['ids:array_agg(id)',
    #                                                                                'hour_from:min(hour_from)',
    #                                                                                'hour_to:max(hour_to)', 'week_type',
    #                                                                                'dayofweek', 'day_period'],
    #                                                                       ['week_type', 'dayofweek', 'day_period'],
    #                                                                       lazy=False)
    #
    #     # Must be sorted by dayofweek ASC and day_period DESC
    #     attendances = sorted([DummyAttendance(group['hour_from'], group['hour_to'], group['dayofweek'],
    #                                           group['day_period'], group['week_type']) for group in attendances],
    #                          key=lambda att: (att.dayofweek, att.day_period != 'morning'))
    #
    #     default_value = DummyAttendance(0, 0, 0, 'morning', False)
    #
    #     if resource_calendar_id.two_weeks_calendar:
    #         # find week type of start_date
    #         start_week_type = int(math.floor((request_date_from.toordinal() - 1) / 7) % 2)
    #         attendance_actual_week = [att for att in attendances if
    #                                   att.week_type is False or int(att.week_type) == start_week_type]
    #         attendance_actual_next_week = [att for att in attendances if
    #                                        att.week_type is False or int(att.week_type) != start_week_type]
    #         # First, add days of actual week coming after date_from
    #         attendance_filtred = [att for att in attendance_actual_week if
    #                               int(att.dayofweek) >= request_date_from.weekday()]
    #         # Second, add days of the other type of week
    #         attendance_filtred += list(attendance_actual_next_week)
    #         # Third, add days of actual week (to consider days that we have remove first because they coming before date_from)
    #         attendance_filtred += list(attendance_actual_week)
    #
    #         end_week_type = int(math.floor((request_date_to.toordinal() - 1) / 7) % 2)
    #         attendance_actual_week = [att for att in attendances if
    #                                   att.week_type is False or int(att.week_type) == end_week_type]
    #         attendance_actual_next_week = [att for att in attendances if
    #                                        att.week_type is False or int(att.week_type) != end_week_type]
    #         attendance_filtred_reversed = list(
    #             reversed([att for att in attendance_actual_week if int(att.dayofweek) <= request_date_to.weekday()]))
    #         attendance_filtred_reversed += list(reversed(attendance_actual_next_week))
    #         attendance_filtred_reversed += list(reversed(attendance_actual_week))
    #
    #         # find first attendance coming after first_day
    #         attendance_from = attendance_filtred[0]
    #         # find last attendance coming before last_day
    #         attendance_to = attendance_filtred_reversed[0]
    #     else:
    #         # find first attendance coming after first_day
    #         attendance_from = next((att for att in attendances if int(att.dayofweek) >= request_date_from.weekday()),
    #                                attendances[0] if attendances else default_value)
    #         # find last attendance coming before last_day
    #         attendance_to = next(
    #             (att for att in reversed(attendances) if int(att.dayofweek) <= request_date_to.weekday()),
    #             attendances[-1] if attendances else default_value)
    #
    #     compensated_request_date_from = request_date_from
    #     compensated_request_date_to = request_date_to
    #     hour_from = float_to_time(attendance_from.hour_from)
    #     hour_to = float_to_time(attendance_to.hour_to)
    #
    #     vals['date_from'] = timezone(tz).localize(
    #         datetime.combine(compensated_request_date_from, hour_from)).astimezone(UTC).replace(tzinfo=None)
    #     vals['date_to'] = timezone(tz).localize(datetime.combine(compensated_request_date_to, hour_to)).astimezone(
    #         UTC).replace(tzinfo=None)
    #     return vals

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(HrLeave, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                   submenu=False)
        annual_leave = self._context.get('default_annual_leave', False)
        if annual_leave:
            form_view_id = self.env.ref('hr_holidays.hr_leave_view_form').id
        else:
            form_view_id = self.env.ref('atheer_hr.hr_leave_request_form_view_inherit').id

        if res.get('view_id', False) == form_view_id and res.get('type', False) == 'form':
            doc = etree.XML(res['arch'])
            if len(doc):
                if self.env.user.has_group('atheer_hr.group_hr_employee_staff') and not self.env.user.has_group(
                        'atheer_hr.group_hr_manager') and not self.env.user.has_group(
                    'atheer_hr.group_hr_ceo') and not self.env.user.has_group(
                    'atheer_hr.group_hr_accounts') and not self.env.user.has_group(
                    'atheer_hr.group_hr_site_engineer') and not self.env.user.has_group(
                    'atheer_hr.group_hr_line_manager'):
                    node = doc.xpath("//field[@name='employee_id']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                # if self.env.user.has_group('atheer_hr.group_hr_site_engineer'):
                #     node = doc.xpath("//field[@name='project']")[0]
                #     node.set("required", "1")
                #     modifiers = json.loads(node.get("modifiers"))
                #     modifiers['required'] = True
                #     node.set("modifiers", json.dumps(modifiers))
                #     res['arch'] = etree.tostring(doc)
                # if not self.env.user.has_group('atheer_hr.group_hr_site_engineer'):
                #     node = doc.xpath("//field[@name='site_incharge_remark']")[0]
                #     node.set("readonly", "1")
                #     modifiers = json.loads(node.get("modifiers"))
                #     modifiers['readonly'] = True
                #     node.set("modifiers", json.dumps(modifiers))
                #     res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('atheer_hr.group_hr_manager'):
                    node = doc.xpath("//field[@name='hr_remark']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('atheer_hr.group_hr_line_manager'):
                    node = doc.xpath("//field[@name='line_manager_remark']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                # if not self.env.user.has_group('atheer_hr.group_hr_project_manager'):
                #     node = doc.xpath("//field[@name='project_manager_remark']")[0]
                #     node.set("readonly", "1")
                #     modifiers = json.loads(node.get("modifiers"))
                #     modifiers['readonly'] = True
                #     node.set("modifiers", json.dumps(modifiers))
                #     res['arch'] = etree.tostring(doc)
                # if not self.env.user.has_group('atheer_hr.group_hr_ceo'):
                #     node = doc.xpath("//field[@name='ceo_remark']")[0]
                #     node.set("readonly", "1")
                #     modifiers = json.loads(node.get("modifiers"))
                #     modifiers['readonly'] = True
                #     node.set("modifiers", json.dumps(modifiers))
                #     res['arch'] = etree.tostring(doc)
                return res
        return res

    def name_get(self):
        """
        Updating name_get to add the leave ref
        """
        res = super(HrLeave, self).name_get()
        leave_obj = self.env['hr.leave']
        result = []
        for leave in res:
            if isinstance(leave[0], int):
                leave_ref = leave_obj.search([('id', '=', leave[0])]).reference
                new_ref = str(leave_ref) + '-' + leave[1]
                result.append((leave[0], new_ref))
        if result:
            return result
        return res

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date_state(self):
        """Override the orginal function in order to remove state validate1 :[to remove this warning i have removed
        the validate1 state condition from this warning (This modification is not allowed in the current state.)] """
        if self.env.context.get('leave_skip_state_check'):
            return
        for holiday in self:
            if holiday.state in ['cancel', 'refuse', 'validate']:
                raise ValidationError(_("This modification is not allowed in the current state."))

    @api.constrains('date_from', 'date_to', 'employee_id', 'holiday_status_id', 'employee_id')
    def _check_date(self):
        if self.env.context.get('leave_skip_date_check', False):
            return
        for holiday in self.filtered('employee_id'):
            domain = [
                ('date_from', '<', holiday.date_to),
                ('date_to', '>', holiday.date_from),
                ('employee_id', '=', holiday.employee_id.id),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse']),
            ]
            nholidays = self.search_count(domain)
            if nholidays:
                raise ValidationError(
                    _('You can not set 2 time off that overlaps on the same day for the same employee.'))
        if self.env.context.get('leave_skip_date_check', False):
            return

    @api.constrains('date_from', 'date_to', 'employee_id', 'holiday_status_id', 'employee_id')
    def _checking_dates(self):
        requesting_date_from_year = ''
        requesting_date_to_year = ''
        for rec in self:
            joining_date = rec.employee_id.joining_date
            if not joining_date:
                raise ValidationError(_(
                    "There is no joining date for the employee."))
            if rec.request_date_from:
                requesting_date_from_year = rec.request_date_from.year
            if rec.request_date_to:
                requesting_date_to_year = rec.request_date_to.year
            if rec.request_date_from < rec.employee_id.joining_date:
                raise ValidationError(_(
                    "You are not eligible for the requested duration."))
            leaves = self.env['hr.leave'].search(
                [('employee_id', '=', rec.employee_id.id), ('holiday_status_id.annual_leave', '=', False),
                 ('holiday_status_id', '=', rec.holiday_status_id.id)])

            if requesting_date_from_year and requesting_date_to_year \
                    and rec.holiday_status_id.restart_date == 'annual' \
                    and rec.holiday_status_id.eligible_days_type == 'fixed':
                if requesting_date_from_year == requesting_date_to_year:
                    this_year = requesting_date_to_year
                    leave_sum = self._year_leave_check(this_year, leaves)
                    balance = rec.holiday_status_id.eligible_days - leave_sum
                    requested_days = rec.number_of_days
                    if int(requested_days) > balance:
                        raise ValidationError(_(
                            "There is no enough %s type for the requested duration") % (rec.holiday_status_id.name))

                if requesting_date_from_year != requesting_date_to_year:
                    from_year_sum_og = self._year_leave_check(requesting_date_from_year, leaves)
                    to_year_sum_og = self._year_leave_check(requesting_date_to_year, leaves)
                    from_year_sum = self._year_leave_check(requesting_date_from_year, rec)
                    to_year_sum = self._year_leave_check(requesting_date_to_year, rec)
                    balance_from_year = rec.holiday_status_id.eligible_days - from_year_sum_og
                    balance_to_year = rec.holiday_status_id.eligible_days - to_year_sum_og
                    if to_year_sum > rec.holiday_status_id.eligible_days:
                        raise ValidationError(_(
                            "There is no enough %s leaves for the requested duration.Please check your eligible leaves") % (
                                                  rec.holiday_status_id.name))
                    if from_year_sum > rec.holiday_status_id.eligible_days:
                        raise ValidationError(_(
                            "There is no enough %s leaves for the requested duration.Please check your eligible leaves") % (
                                                  rec.holiday_status_id.name))
                    if from_year_sum > balance_from_year:
                        raise ValidationError(_(
                            "There is no enough %s type for the requested duration") % rec.holiday_status_id.name)
                    if to_year_sum > balance_to_year:
                        raise ValidationError(_(
                            "There is no enough %s type for the requested duration") % rec.holiday_status_id.name)
            # contract year
            if requesting_date_from_year and requesting_date_to_year and rec.employee_id.joining_date and \
                    not rec.holiday_status_id.annual_leave and rec.holiday_status_id.restart_date == 'contract' \
                    and rec.holiday_status_id.eligible_days_type == 'fixed':
                # other_leaves = self.env['hr.leave.allocation'].search(
                #     [('employee_id', '=', rec.employee_id.id), ('holiday_status_id.annual_leave', '=', False),
                #      ('holiday_status_id', '=', rec.holiday_status_id.id), ('date_from', '<=', rec.request_date_from),
                #      ('date_to', '>=', rec.request_date_to)], limit=1)
                other_leaves = self.env['hr.leave.allocation'].search(
                    [('employee_id', '=', rec.employee_id.id), ('holiday_status_id.annual_leave', '=', False),
                     ('holiday_status_id', '=', rec.holiday_status_id.id)], limit=1)
                if rec.request_date_from > rec.employee_id.joining_date:
                    if other_leaves:
                        remaining = other_leaves.number_of_days
                        if rec.number_of_days > remaining:
                            raise ValidationError(_(
                                "There is no enough %s type for the requested duration") % rec.holiday_status_id.name)

                    # elif requesting_date_from_year == requesting_date_to_year:
                    #     this_year = requesting_date_to_year
                    #     leave_sum = self._year_leave_check(this_year, leaves)
                    #     balance = rec.holiday_status_id.eligible_days - leave_sum
                    #     if rec.number_of_days > balance:
                    #         raise ValidationError(_(
                    #             "There is no enough %s type for the requested duration") % rec.holiday_status_id.name)
                    # elif requesting_date_from_year != requesting_date_to_year:
                    #     from_year_sum_og = self._year_leave_check(requesting_date_from_year, leaves)
                    #     to_year_sum_og = self._year_leave_check(requesting_date_to_year, leaves)
                    #     balance_from_year = rec.holiday_status_id.eligible_days - from_year_sum_og
                    #     balance_to_year = rec.holiday_status_id.eligible_days - to_year_sum_og
                    #     balance_total = balance_from_year + balance_to_year
                    #     if rec.number_of_days > balance_total:
                    #         raise ValidationError(_(
                    #             "There is no enough %s type for the requested duration") % rec.holiday_status_id.name)

    @api.onchange('employee_id', 'holiday_status_id', 'number_of_days',
                  'request_date_from', 'request_date_to')
    def onchange_no_of_days_eligible(self):
        """CHECKED LEAVES REQUESTS STARTING AND ENDING IN SAME YEAR"""
        for rec in self:
            if rec.request_date_from and rec.request_date_to:
                rec.rejoining_date = rec.request_date_to + timedelta(1)
            else:
                rec.rejoining_date = False
            # CHECKING FOR ANNUAL LEAVES
            if self.holiday_status_id.annual_leave:
                if rec.request_date_from and rec.request_date_to and rec.holiday_status_id.annual_leave and rec.employee_id.is_eligible_for_annual_leave:
                    joining_date = rec.employee_id.joining_date
                    if joining_date:
                        if rec.employee_id.is_eligible_for_annual_leave:
                            check = False
                            self.annual_leave_check(rec.request_date_from, joining_date, rec.request_date_to, check)

    def annual_leave_check(self, request_date_from, joining_date, request_date_to, check):
        joining_date = self.employee_id.joining_date
        if not joining_date:
            raise ValidationError(_(
                "There is no joining date for the employee."))
        if request_date_from < joining_date:
            raise ValidationError("You are not eligible for annual leave")
        annual_leave_calc_rate = self.env['ir.config_parameter'].sudo().get_param('atheer_hr.annual_leave_calc_rate')
        annual_leave_type = self.env['ir.config_parameter'].sudo().get_param('atheer_hr.annual_leave_type')
        annual_leave_alloc = self.env['hr.leave.allocation'].search([('employee_id', '=', self.employee_id.id),
                                                                     (
                                                                     'holiday_status_id', '=', int(annual_leave_type))],
                                                                    limit=1)
        if annual_leave_alloc:
            if self.employee_id.annual_leave_last_reco:
                last_reco = request_date_to - fields.Date.from_string(self.employee_id.annual_leave_last_reco)
            else:
                last_reco = request_date_to - fields.Date.from_string(self.employee_id.joining_date)

            annual_leaves = self.env['hr.leave'].search([('holiday_status_id', '=', annual_leave_type),
                                                         ('employee_id', '=', self.id),
                                                         ('state', '=', 'validate')])
            total_annual_leaves = 0.0
            for i in annual_leaves:
                total_annual_leaves += i.number_of_days
            no_of_days_eligible = self.employee_id.open_blnc + (
                    float(last_reco.days) * float(annual_leave_calc_rate)) - total_annual_leaves

            # CHECKING TOTAL ANNUAL LEAVES
            if float(no_of_days_eligible) == 0 and check:
                raise ValidationError(_("%s have 0 eligible days" % self.employee_id.name))
            if self.number_of_days > float(no_of_days_eligible) and check:
                raise ValidationError(_("%s cannot take leaves more than the eligible leaves" % self.employee_id.name))

    def _year_leave_check(self, this_year, leaves):
        leave_sum = 0
        today = fields.Date.context_today(self.env.user)
        for lv in leaves:
            if lv.date_from.year == lv.date_to.year == this_year:
                start_date = lv.date_from
                end_date = lv.date_to
            elif lv.date_from.year != this_year and lv.date_to.year == this_year:
                year_start = today.replace(day=1, month=1)
                start_date = year_start
                end_date = lv.date_to
            elif lv.date_from.year == this_year and lv.date_to.year != this_year:
                year_end = today.replace(day=31, month=12)
                start_date = lv.date_from
                end_date = year_end
            else:
                start_date = end_date = False
            if start_date and end_date:
                if lv.holiday_status_id.leave_days_type == 'calendar_days':
                    diff = end_date - start_date
                    year_leave = diff.days + 1
                else:
                    year_leave = lv._get_number_of_days(start_date, end_date, lv.employee_id.id)['days']
            else:
                year_leave = 0
            leave_sum += year_leave

        # same_year = list(filter(None, [
        #     leave if leave.date_from.year == leave.date_to.year == this_year else False for
        #     leave in leaves]))
        # to_year = list(filter(None, [
        #     leave if leave.date_from.year != this_year and leave.date_to.year == this_year else False
        #     for leave in leaves]))
        # from_year = list(filter(None, [
        #     leave if leave.date_from.year == this_year and leave.date_to.year != this_year else False
        #     for leave in leaves]))
        # if same_year:
        #     for leave in same_year:
        #         if self.request_unit_half:
        #             leave_sum += 0.5
        #         else:
        #             leave_sum += leave.number_of_days
        # if to_year:
        #     days = 0
        #     for res in to_year:
        #         days += self._check_dates(res, this_year)
        #         leave_sum += days
        #
        # if from_year:
        #     days = 0
        #     for res in from_year:
        #         days += self._check_dates(res, this_year)
        #         leave_sum += days
        return leave_sum

    # def _check_dates(self, record, year):
    #     days_count = 0
    #     start_date = record.date_from
    #     end_date = record.date_to
    #     delta_days = end_date - start_date
    #     for i in range(delta_days.days + 1):
    #         day = start_date + timedelta(days=i)
    #         if day.year == year:
    #             days_count += 1
    #     return days_count

    def action_confirm(self):
        if self.state == 'draft':
            self.write({'state': 'confirm'})
        holidays = self.filtered(lambda leave: leave.validation_type == 'no_validation')
        if holidays:
            # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
            holidays.sudo().action_validate()
        self.activity_update()
        return True

    @api.constrains('request_date_from', 'request_date_to')
    def check_attendance(self):
        for rec in self:
            difference = ((rec.request_date_to - rec.request_date_from).days) + 1
            for each in range(difference):
                att_date = rec.request_date_from + relativedelta(days=each)
                attendance_rec = self.env['hr.attendance'].search(
                    [('employee_id', '=', self.employee_id.id),
                     ('date', '=', att_date), ('attendance_type', 'not in', ['partial_day', 'absent'])])
                if attendance_rec:
                    raise ValidationError(
                        _('You cannot create leave for %s the date %s.As attendance is already created for the date %s')
                        % (rec.employee_id.display_ename, att_date, att_date))

    def action_validate(self):
        current_employee = self.env.user.employee_id
        leaves = self._get_leaves_on_public_holiday()
        if leaves:
            raise ValidationError(_('The following employees are not supposed to work during that period:\n %s') % ','.join(leaves.mapped('employee_id.name')))

        self.check_attendance()
        # if any(holiday.state not in ['confirm', 'validate1'] and holiday.validation_type != 'no_validation' for holiday in self):
        #     raise UserError(_('Time off request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})

        leaves_second_approver = self.env['hr.leave']
        leaves_first_approver = self.env['hr.leave']

        for leave in self:
            if leave.validation_type == 'both':
                leaves_second_approver += leave
            else:
                leaves_first_approver += leave

            if leave.holiday_type != 'employee' or\
                (leave.holiday_type == 'employee' and len(leave.employee_ids) > 1):
                if leave.holiday_type == 'employee':
                    employees = leave.employee_ids
                elif leave.holiday_type == 'category':
                    employees = leave.category_id.employee_ids
                elif leave.holiday_type == 'company':
                    employees = self.env['hr.employee'].search([('company_id', '=', leave.mode_company_id.id)])
                else:
                    employees = leave.department_id.member_ids

                conflicting_leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True
                ).search([
                    ('date_from', '<=', leave.date_to),
                    ('date_to', '>', leave.date_from),
                    ('state', 'not in', ['cancel', 'refuse']),
                    ('holiday_type', '=', 'employee'),
                    ('employee_id', 'in', employees.ids)])

                if conflicting_leaves:
                    # YTI: More complex use cases could be managed in master
                    if leave.leave_type_request_unit != 'day' or any(l.leave_type_request_unit == 'hour' for l in conflicting_leaves):
                        raise ValidationError(_('You can not have 2 time off that overlaps on the same day.'))

                    # keep track of conflicting leaves states before refusal
                    target_states = {l.id: l.state for l in conflicting_leaves}
                    conflicting_leaves.action_refuse()
                    split_leaves_vals = []
                    for conflicting_leave in conflicting_leaves:
                        if conflicting_leave.leave_type_request_unit == 'half_day' and conflicting_leave.request_unit_half:
                            continue

                        # Leaves in days
                        if conflicting_leave.date_from < leave.date_from:
                            before_leave_vals = conflicting_leave.copy_data({
                                'date_from': conflicting_leave.date_from.date(),
                                'date_to': leave.date_from.date() + timedelta(days=-1),
                                'state': target_states[conflicting_leave.id],
                            })[0]
                            before_leave = self.env['hr.leave'].new(before_leave_vals)
                            before_leave._compute_date_from_to()

                            # Could happen for part-time contract, that time off is not necessary
                            # anymore.
                            # Imagine you work on monday-wednesday-friday only.
                            # You take a time off on friday.
                            # We create a company time off on friday.
                            # By looking at the last attendance before the company time off
                            # start date to compute the date_to, you would have a date_from > date_to.
                            # Just don't create the leave at that time. That's the reason why we use
                            # new instead of create. As the leave is not actually created yet, the sql
                            # constraint didn't check date_from < date_to yet.
                            if before_leave.date_from < before_leave.date_to:
                                split_leaves_vals.append(before_leave._convert_to_write(before_leave._cache))
                        if conflicting_leave.date_to > leave.date_to:
                            after_leave_vals = conflicting_leave.copy_data({
                                'date_from': leave.date_to.date() + timedelta(days=1),
                                'date_to': conflicting_leave.date_to.date(),
                                'state': target_states[conflicting_leave.id],
                            })[0]
                            after_leave = self.env['hr.leave'].new(after_leave_vals)
                            after_leave._compute_date_from_to()
                            # Could happen for part-time contract, that time off is not necessary
                            # anymore.
                            if after_leave.date_from < after_leave.date_to:
                                split_leaves_vals.append(after_leave._convert_to_write(after_leave._cache))

                    split_leaves = self.env['hr.leave'].with_context(
                        tracking_disable=True,
                        mail_activity_automation_skip=True,
                        leave_fast_create=True,
                        leave_skip_state_check=True
                    ).create(split_leaves_vals)

                    split_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()

                values = leave._prepare_employees_holiday_values(employees)
                leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True,
                    no_calendar_sync=True,
                    leave_skip_state_check=True,
                ).create(values)

                leaves._validate_leave_request()

                # FOR ANNUAL LEAVE
                if leave.holiday_status_id.annual_leave:
                    self.env['air.ticket.management'].create({
                        'employee_id': leave.employee_id.id,
                        'designation': leave.employee_id.job_id.id,
                        'department_id': leave.employee_id.department_id.id,
                        'location': leave.destination,
                        'ticket_type': 'annual_leave',
                        'travel_date': leave.leave_request_date_from,
                        'state': 'draft',
                        'leave_check': True,
                        'annual_leave': leave.id,
                    })

        leaves_second_approver.write({'second_approver_id': current_employee.id})
        leaves_first_approver.write({'first_approver_id': current_employee.id})

        employee_requests = self.filtered(lambda hol: hol.holiday_type == 'employee')
        employee_requests._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            employee_requests.filtered(lambda holiday: holiday.validation_type != 'no_validation').activity_update()
        return True

    def action_draft(self):
        for rec in self:
            if rec.state == 'refuse':
                rec.state = 'draft'

    def action_send_back(self):
        for rec in self:
            if rec.state == 'validate1':
                rec.send_back_flag = True
                rec.write({'state': 'confirm'})
            elif rec.state == 'confirm':
                rec.send_back_flag = True
                rec.write({'state': 'draft'})

    def request_to_line_manager(self):
        for rec in self:
            rec.left_emp_flag = True
            rec.send_back_flag = False
            if rec.state == 'draft' and not rec.direct_req:
                rec.state = 'confirm'

    def request_to_annual_line_manager(self):
        for rec in self:
            if rec.state == 'draft' and not rec.direct_req:
                rec.left_emp_flag = True
                rec.send_back_flag = False
                rec.state = 'confirm'

    def request_to_annual_project_manager(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'confirm'

    def action_approved(self):
        approver = str(self.env.user.name)
        for rec in self:
            rec.state = 'approved'
            rec.action_validate()

    def request_to_hr(self):
        for rec in self:
            if rec.state == 'confirm':
                rec.state = 'validate1'
                rec.left_lm_flag = True
                rec.send_back_flag = False

    def request_to_annual_hr(self):
        for rec in self:
            if rec.state == 'confirm':
                rec.left_lm_flag = True
                rec.send_back_flag = False
                rec.state = 'validate1'

    def request_to_ceo(self):
        for rec in self:
            if rec.state == 'validate1':
                rec.send_back_flag = False
                rec.state = 'ceo'

    def action_reject(self):
        for rec in self:
            refuser = str(self.env.user.name)
            # staff case
            rec.state = 'refuse'
            rec.rejected_by = rec.env.user.id
            rec.rejected_date = date.today()

    def action_refuse(self):
        current_employee = self.env.user.employee_id

        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write(
            {'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write(
            {'state': 'refuse', 'second_approver_id': current_employee.id})
        # Delete the meeting
        self.mapped('meeting_id').write({'active': False})
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()
        for rec in self:
            if rec.state == 'refuse':
                rec.rejected_by = rec.env.user.id
                rec.rejected_date = date.today()

        # Post a second message, more verbose than the tracking message
        for holiday in self:
            if holiday.employee_id.user_id:
                holiday.message_post(
                    body=_('Your %(leave_type)s planned on %(date)s has been refused',
                           leave_type=holiday.holiday_status_id.display_name, date=holiday.date_from),
                    partner_ids=holiday.employee_id.user_id.partner_id.ids)
        self._remove_resource_leave()
        self.activity_update()
        return True

    def action_leave_return(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Leave Return',
            'view_mode': 'tree,form',
            'res_model': 'hr.leave.return',
            'target': 'current',
            'context': {'create': False},
            'domain': [('id', '=', self.leave_return_id.id)],
        }

    def compute_annual(self):
        for rec in self:
            if rec.holiday_status_id.annual_leave:
                rec.is_annual = True
            else:
                rec.is_annual = False

    false_value = fields.Boolean(default=False)

    def copy_data(self, default=None):
        if default and 'date_from' in default and 'date_to' in default:
            default['request_date_from'] = default.get('date_from')
            default['request_date_to'] = default.get('date_to')
            return super().copy_data(default)
        raise UserError(_('Leave request cannot be duplicated.'))

    def unlink(self):
        if not self.env.ref('base.user_admin').id or not self.env.ref(
                'base.user_root').id or not self.env.user.has_group('base.group_system'):
            if self.state not in ['draft', 'cancel', 'confirm', 'validate1']:
                raise UserError(
                    _('You cannot delete the leave request %s in the current state.', self.reference)
                )
        return super(HrLeave, self).unlink()


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    def allocate_leaves(self, employee=False):
        """
        Function which do the allocation for employees.
        Jan 1 is set for cron, [think about next year], While creating employees or changing their
         religion or gender the function invokes
        :param employee:
        :return:
        """

        if (date.today().month == 1 and date.today().day == 1) or employee:  # whether jan 1
            fmt = '%Y-%m-%d %H:%M:%S'
            currYear = date.today().year
            nextYear = date.today().year + 1
            current_create_date = datetime.strptime(str(currYear) + '-01-01 00:00:00', fmt)
            next_year_date = datetime.strptime(str(nextYear) + '-01-01 00:00:00', fmt)
            employees = self.env['hr.employee'].sudo().search([('active', '=', True)]) if not employee else employee
            holiday_ids = self.env['hr.leave.type'].sudo().search([('leave_reset', '!=', 'accumulate'),
                                                                   ('annual_leave', '=', False),
                                                                   ('active', '=', True),
                                                                   ('requires_allocation', '!=', 'no'),
                                                                   ('restart_date', '=', 'annual')])
            if employee:
                # To give annual leave while creation of employee
                annual_leave_ids = self.env['hr.leave.type'].sudo().search([
                    ('annual_leave', '=', True), ('active', '=', True)])
                holiday_ids += annual_leave_ids
                # To give contract leaves while creating the employee
                contract_leaves = self.env['hr.leave.type'].sudo().search([('leave_reset', '!=', 'accumulate'),
                                                                           ('annual_leave', '=', False),
                                                                           ('active', '=', True),
                                                                           ('requires_allocation', '!=', 'no'),
                                                                           ('restart_date', '=', 'contract')])
                holiday_ids += contract_leaves
            for emp in employees:
                if (emp.contract_id and emp.contract_id.active_contract) or employee:
                    # if emp.joining_date and emp.joining_date <= fields.Date.today():
                    #     _logger.info("Skip...................................End of Service")
                    #     continue
                    for holiday in holiday_ids:
                        _logger.info(
                            "Emp Name: %s holiday: %s, gender: %s, religion: %s, holiday muslim %s, holiday women %s" % (
                                emp.name, holiday.name,
                                emp.gender, emp.religion, holiday.is_muslim, holiday.is_women))
                        if holiday.is_muslim and emp.religion != 'muslim':
                            _logger.info("Skip...................................Skip")
                            continue
                        if holiday.is_women and emp.gender != 'female':
                            _logger.info("Skip...................................Skip")
                            continue
                        if holiday.is_omani and emp.is_omani != 'omani':
                            continue
                        holiday_prev = self.env['hr.leave.allocation'].sudo().search([('employee_id', '=', emp.id),
                                                                                      ('state', 'in',
                                                                                       ['confirm', 'validate1',
                                                                                        'validate']),
                                                                                      ('holiday_status_id', 'in',
                                                                                       [holiday.id]),
                                                                                      ('create_date', '>=',
                                                                                       str(current_create_date)),
                                                                                      ('create_date', '<',
                                                                                       str(next_year_date))])
                        _logger.info("previous Holidays %s" % holiday_prev)
                        _logger.info("Holidays %s, eligible: %s" % (holiday.name, holiday.eligible_days))

                        if holiday.annual_leave:
                            # If annual leave then we are assigning 0, but the cron for annual leave set the exact one
                            eligible_days = 0
                        else:
                            eligible_days = holiday.eligible_days
                        if holiday.restart_date == 'contract':
                            if emp.joining_date:
                                start_date = emp.joining_date
                            else:
                                start_date = fields.Date.today()
                        elif holiday.restart_date == 'annual':
                            year_start = fields.Date.today().replace(day=1, month=1)
                            if emp.joining_date and emp.joining_date > year_start :
                                start_date = emp.joining_date
                            else:
                                start_date = year_start
                        else:
                            start_date = fields.Date.today()
                        if not len(holiday_prev) and eligible_days > 0:
                            query = " INSERT INTO hr_leave_allocation (private_name,state,number_of_days,allocation_type,\
                                 holiday_type, employee_id, holiday_status_id, date_from, create_date, create_uid, active) VALUES (\
                                 '{name}','{state}',{eligible_days}, '{allocation_type}', '{h_type}', {emp_id}, {h_status_id}, '{date_from}', '{c_d}', {c_u}, {active})\
                            ".format(name="Annual Leave Allocation", state=str("validate"), eligible_days=eligible_days,
                                     allocation_type="regular", h_type="employee", emp_id=emp.id,
                                     h_status_id=holiday.id, h_status_id_1=holiday.id, date_from=start_date,
                                     c_d=str(datetime.today()), c_u=1, active=True)
                            self._cr.execute(
                                query)  # using query to save time and avoid serialization error due to concurrent updates

    @api.model
    def allocate_leaves_annually(self):
        """
        Cron function will do the automatic allocation of leaves expect the annual type.
        Allocation takes place the day of 1 of starting month of every year
        :return: hr.leave.allocation(ids)
        """
        _logger.info("Annual Leave Allocation Cron Init")
        self.allocate_leaves()
        _logger.info("Annual Leave Allocation Cron Done.")

    ph_id = fields.Many2one('public.holidays')
    ph_line = fields.Many2one('resource.calendar.leaves')


class AccrualPlanLevel(models.Model):
    _inherit = "hr.leave.accrual.level"

    added_value = fields.Float(
        "Rate", required=True, digits=(16, 9),
        help="The number of hours/days that will be incremented in the specified Time Off Type for every period")


class HrLeaveSettlement(models.Model):
    _name = 'hr.leave.settlement'
    _description = 'Hr Leave Settlement'
