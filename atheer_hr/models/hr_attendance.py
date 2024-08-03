# -*- coding: utf-8 -*-

import pytz
from operator import itemgetter
from collections import defaultdict
from datetime import timedelta
from odoo import fields, exceptions, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime
from odoo.osv.expression import AND, OR


class HRAttendance(models.Model):
    _inherit = "hr.attendance"

    attendance_type = fields.Selection([('partial_day', 'Partial Day'),
                                        ('pr_present', 'PR- Present'),
                                        ('absent', 'A – Absent'),
                                        ('hd_holiday', 'HD- Holiday'),
                                        ('sick_leave', 'SL- Sick Leave'),
                                        ('annual_leave', 'AL- Annual Leave'),
                                        ('emergency_leave', 'EL- Emergency Leave')])
    amendment_true = fields.Boolean(default=False)
    date = fields.Date(string='Date', default=fields.Date.today, copy=False)
    leaves = fields.Many2one('hr.leave')
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, required=False)
    print_date = fields.Date(default=fields.Date.context_today)
    attendance_amendment_id = fields.Many2one('hr.attendance.amendment')
    designation = fields.Many2one(related='employee_id.job_id')
    amendment_attendance_type = fields.Selection([('partial_day', 'Partial Day'),
                                                  ('pr_present', 'PR- Present'),
                                                  ('hd_holiday', 'HD- Holiday'),
                                                  ('absent', 'A – Absent'),
                                                  ('sick_leave', 'SL- Sick Leave'),
                                                  ('annual_leave', 'AL- Annual Leave'),
                                                  ('emergency_leave', 'EL- Emergency Leave')],
                                                 string="Amendment Type", store=True)
    check_out_true = fields.Boolean(default=False)

    is_early = fields.Boolean(compute="compute_attendance_status", store=True)
    is_late = fields.Boolean(compute="compute_attendance_status", store=True)
    late_time = fields.Float(string="Late Time")
    early_time = fields.Float(string="Early Time")
    time_diff = fields.Float(string="Time Difference")

    @api.onchange('date', 'check_in', 'check_out')
    def onchange_date(self):
        for rec in self:
            if rec.check_out:
                rec.check_out_true = True
            else:
                rec.check_out_true = False

    @api.constrains('date', 'check_in', 'check_out')
    def checking_dates(self):
        for rec in self:
            if rec.check_in:
                if rec.check_in.date() != rec.date:
                    raise ValidationError('Check in date should be same as date.')

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same employee.
            For the same employee we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous employee records
        """
        for attendance in self:
            if attendance.attendance_type == 'partial_day' and attendance.attendance_type == 'pr_present':
                # we take the latest attendance before our check_in time and check it doesn't overlap with ours
                last_attendance_before_check_in = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_in', '<=', attendance.check_in),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if last_attendance_before_check_in and last_attendance_before_check_in.check_out and last_attendance_before_check_in.check_out > attendance.check_in:
                    raise exceptions.ValidationError(_(
                        "Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
                                                         'empl_name': attendance.employee_id.name,
                                                         'datetime': format_datetime(self.env, attendance.check_in,
                                                                                     dt_format=False),
                                                     })

                if not attendance.check_out:
                    # if our attendance is "open" (no check_out), we verify there is no other "open" attendance
                    no_check_out_attendances = self.env['hr.attendance'].search([
                        ('employee_id', '=', attendance.employee_id.id),
                        ('check_out', '=', False),
                        ('id', '!=', attendance.id),
                    ], order='check_in desc', limit=1)
                    if no_check_out_attendances:
                        raise exceptions.ValidationError(_(
                            "Cannot create new attendance record for %(empl_name)s, the employee hasn't checked out since %(datetime)s") % {
                                                             'empl_name': attendance.employee_id.name,
                                                             'datetime': format_datetime(self.env,
                                                                                         no_check_out_attendances.check_in,
                                                                                         dt_format=False),
                                                         })
                else:
                    # we verify that the latest attendance with check_in time before our check_out time
                    # is the same as the one before our check_in time computed before, otherwise it overlaps
                    last_attendance_before_check_out = self.env['hr.attendance'].search([
                        ('employee_id', '=', attendance.employee_id.id),
                        ('check_in', '<', attendance.check_out),
                        ('id', '!=', attendance.id),
                    ], order='check_in desc', limit=1)
                    if last_attendance_before_check_out and last_attendance_before_check_in != last_attendance_before_check_out:
                        raise exceptions.ValidationError(_(
                            "Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s") % {
                                                             'empl_name': attendance.employee_id.name,
                                                             'datetime': format_datetime(self.env,
                                                                                         last_attendance_before_check_out.check_in,
                                                                                         dt_format=False),
                                                         })

    @api.model
    def create(self, vals_list):
        res = super(HRAttendance, self).create(vals_list)

        return res

    def action_view_amendment(self):
        for rec in self:
            attendances_ids = self.env['hr.attendance.amendment'].search(
                [('employee_amendment_ids.check_in', '=', rec.check_in)])
            if attendances_ids:
                self.amendment_true = True
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.attendance.amendment',
                'views': [[False, 'form']],
                'res_id': attendances_ids.id,
            }

    @api.depends('employee_id', 'check_in', 'check_out', )
    def compute_attendance_status(self):
        for rec in self:
            if rec.employee_id and rec.check_in:
                employee_attendance_dates = rec._get_attendances_dates()
                for emp, attendance_dates in employee_attendance_dates.items():
                    attendance_domain = []
                    for attendance_date in attendance_dates:
                        attendance_domain = OR([attendance_domain, [
                            ('check_in', '>=', attendance_date[0]),
                            ('check_in', '<', attendance_date[0] + timedelta(hours=24)),
                        ]])
                    attendance_domain = AND([[('employee_id', '=', emp.id)], attendance_domain])

                    attendances_per_day = defaultdict(lambda: self.env['hr.attendance'])
                    all_attendances = self.env['hr.attendance'].search(attendance_domain)
                    for attendance in all_attendances:
                        check_in_day_start = attendance._get_day_start_and_day(attendance.employee_id, attendance.check_in)
                        attendances_per_day[check_in_day_start[1]] += attendance

                    start = pytz.utc.localize(min(attendance_dates, key=itemgetter(0))[0])
                    stop = pytz.utc.localize(max(attendance_dates, key=itemgetter(0))[0] + timedelta(hours=24))

                    # Retrieve expected attendance intervals
                    expected_attendances = emp.resource_calendar_id._attendance_intervals_batch(
                        start, stop, emp.resource_id
                    )[emp.resource_id.id]
                    # Subtract Global Leaves
                    expected_attendances -= emp.resource_calendar_id._leave_intervals_batch(start, stop, None)[False]

                    working_times = defaultdict(lambda: [])
                    for expected_attendance in expected_attendances:
                        working_times[expected_attendance[0].date()].append(expected_attendance[:2])
                    for day_data in attendance_dates:
                        attendance_date = day_data[1]
                        attendances = attendances_per_day.get(attendance_date, self.browse())
                        unfinished_shifts = attendances.filtered(lambda a: not a.check_out)
                        if not unfinished_shifts and attendances:
                            if working_times[attendance_date]:
                                planned_start_dt, planned_end_dt = False, False
                                planned_work_duration = 0
                                for calendar_attendance in working_times[attendance_date]:
                                    planned_start_dt = min(planned_start_dt,
                                                           calendar_attendance[0]) if planned_start_dt else \
                                    calendar_attendance[0]
                                    planned_end_dt = max(planned_end_dt, calendar_attendance[1]) if planned_end_dt else \
                                    calendar_attendance[1]
                                    planned_work_duration += (calendar_attendance[1] - calendar_attendance[
                                        0]).total_seconds() / 3600.0

                                is_late = is_early = False
                                late_time = early_time = 0.0
                                for attendance in attendances:
                                    local_check_in = pytz.utc.localize(attendance.check_in)
                                    # There is an overtime at the start of the day
                                    if local_check_in > planned_start_dt:
                                        is_late = True
                                        late_time = local_check_in - planned_start_dt
                                    if attendance.check_out:
                                        local_check_out = pytz.utc.localize(attendance.check_out)
                                        if local_check_out < planned_end_dt:
                                            is_early = True
                                            early_time = planned_end_dt - local_check_out
                                    attendance.is_late = is_late
                                    attendance.is_early = is_early
                                    attendance.late_time = late_time.total_seconds() / 3600.0 if late_time else 0.0
                                    attendance.early_time = early_time.total_seconds() / 3600.0 if early_time else 0.0
            else:
                rec.is_late = False
                rec.is_early = False
                rec.late_time = 0.0
                rec.early_time = 0.0


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_grace_minutes = fields.Float(string='Grace Minutes', default=50.0)

    def set_values(self):
        """employee setting field values"""
        res = super(ResConfigSettingsInherit, self).set_values()
        self.env['ir.config_parameter'].set_param('hr_attendance.attendance_grace_minutes', self.attendance_grace_minutes)
        return res

    def get_values(self):
        """employee limit getting field values"""
        res = super(ResConfigSettingsInherit, self).get_values()
        value = self.env['ir.config_parameter'].sudo().get_param('hr_attendance.attendance_grace_minutes')
        res.update(
            attendance_grace_minutes=float(value)
        )
        return res
