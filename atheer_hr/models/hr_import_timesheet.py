# -*- coding: utf-8 -*-
from datetime import timedelta, date
from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class HROvertime(models.Model):
    _name = "hr.overtime"
    _description = 'HR Overtime'

    name = fields.Char(string="Name", required=True)
    type = fields.Char(string="Code", required=True)
    rate = fields.Float(string='Rate', required=True)


class HRTimesheetImport(models.Model):
    """
    Master For Storing Timesheet which is uploaded through xls
    """
    _name = 'hr.timesheet.import'
    _description = 'HR Import Timesheet'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    work_location_id = fields.Many2one('hr.work.location', string='Work Location', required=True,
                                       domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    sheet_date = fields.Date(string='Date', tracking=True, required=True)
    timesheet_lines = fields.One2many(comodel_name='hr.timesheet.import.lines', inverse_name='import_id',
                                      string='Timesheet Lines', tracking=True)
    timesheet_id = fields.Many2one(comodel_name='account.analytic.line', string='Timesheet')
    main_timesheet_id = fields.Many2one(comodel_name='hr.main.timesheet', string='Timesheet Ref')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)
    actual_ot_hours = fields.Float(string='Actual OT Hours', compute='_compute_actual_ot_hours')
    state = fields.Selection([('draft', 'Draft'),
                              ('open', 'Approved'),
                              ('cancel', 'Rejected')], copy=False, tracking=True, default='draft')
    normal_ot = fields.Integer(compute='_compute_ots', store=True)
    weekend_ot = fields.Integer(compute='_compute_ots', store=True)
    ph_ot = fields.Integer(compute='_compute_ots', store=True)
    normal_ot_hours = fields.Integer(compute='_compute_ots', store=True)
    weekend_ot_hours = fields.Integer(compute='_compute_ots', store=True)
    ph_ot_hours = fields.Integer(compute='_compute_ots', store=True)
    no_ot = fields.Integer()
    no_of_days = fields.Integer()
    cost_center = fields.Many2one('account.analytic.account', string='Project')
    attendance_type = fields.Selection([('partial_day', 'Partial Day'),
                                        ('pr_present', 'PR- Present'),
                                        ('absent', 'A – Absent'),
                                        ('hd_holiday', 'HD- Holiday'),
                                        ('sick_leave', 'SL- Sick Leave'),
                                        ('annual_leave', 'AL- Annual Leave'),
                                        ('emergency_leave', 'EL- Emergency Leave')])

    def name_get(self):
        """
        Display Name Formating for the related model.
        :return: [(id, {employee_name} On {Timesheet} From {date_from} To {to})]
        """
        res = []
        for record in self:
            name = '{work_location} Timesheet On {sheet_date}'. \
                format(work_location=record.work_location_id.name,
                       timesheet='Timesheet',
                       sheet_date=record.sheet_date)
            res.append((record.id, name))
        return res

    @api.model
    def create(self, vals):
        """

        :param vals:
        :return:
        """
        res = super(HRTimesheetImport, self).create(vals)
        already_load = self.env['hr.timesheet.import'].search(
            [('work_location_id', '=', res.work_location_id.id),
             ('sheet_date', '=', res.sheet_date), ('id', '!=', res.id)])
        if already_load:
            raise UserError(
                "Time sheet already loaded for location %s on %s" % (
                    already_load.work_location_id.name, already_load.sheet_date))
        counter = 0
        for line in res.timesheet_lines:
            if line:
                _logger.info("Total No of Import Lines")
                _logger.info(len(res.timesheet_lines))
                _logger.info("Current Count/ No of Lines processed")
                _logger.info(counter)
                _logger.info("***********************************")
                counter += 1

                values = {
                    'date': line.act_date,
                    'name': [line.work_description.upper() if line.work_description else False],
                    'project_id': self.env['project.project'].search(
                        [('analytic_account_id', '=', line.cost_center.id)],
                        limit=1).id,
                    'account_id': line.cost_center.id,
                    'import_timesheet_id': res.id,
                    'unit_amount': line.hours,
                    'user_id': line.employee_id.user_id.id,
                    'emp_id': line.employee_id.id,
                    'employee_id': line.employee_id.id,
                }
                self.env['account.analytic.line'].create(values)
        return res

    def unlink(self):
        """
        Delete the imported timesheet and the same time deleting master.
        :return:
        """
        for record in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if record.timesheet_id:
                    record.timesheet_id.state = 'draft'
                    record.timesheet_id.unlink()
            return super(HRTimesheetImport, self).unlink()

    @api.depends('timesheet_lines.employee_id', 'timesheet_lines.ot_id')
    def _compute_ots(self):
        """
        Compute Total Actual OT Hours [no computation with OT Rate]
        :return:
        """
        normal = weekend = ph = 0
        normal_ot_hours = weekend_ot_hours = ph_ot_hours = 0
        for record in self.timesheet_lines:
            if record.ot_id == 'normal':
                normal += 1
                normal_ot_hours += record.hours
            elif record.ot_id == 'ph':
                ph += 1
                ph_ot_hours += record.hours
            elif record.ot_id == 'holiday':
                weekend += 1
                weekend_ot_hours += record.hours

        self.normal_ot = normal
        self.weekend_ot = weekend
        self.ph_ot = ph
        self.normal_ot_hours = normal_ot_hours
        self.weekend_ot_hours = weekend_ot_hours
        self.ph_ot_hours = ph_ot_hours

    @api.depends('timesheet_lines.hours')
    def _compute_actual_ot_hours(self):
        """
        Compute Total Actual OT Hours [no computation with OT Rate]
        :return:
        """
        for record in self:
            record.actual_ot_hours = sum(line.hours for line in record.timesheet_lines)

    @api.onchange('work_location_id', 'sheet_date', 'cost_center', 'attendance_type')
    def onchange_dates(self):
        for rec in self:
            rec.update({'timesheet_lines': [(5,)]})
            if rec.sheet_date and rec.cost_center and rec.attendance_type:
                sheet_week_day = rec.sheet_date.weekday()
                employee_ids = self.env['hr.employee'].search([('work_location_id', '=', rec.work_location_id.id)])
                timesheet_lines_list = []
                for emp in employee_ids:
                    time_schedule = emp.resource_calendar_id
                    if time_schedule.two_weeks_calendar:
                        week_type = self.env['resource.calendar.attendance'].get_week_type(rec.sheet_date)
                        schedule_attendance = self.env['resource.calendar.attendance'].search([
                            ('calendar_id', '=', time_schedule.id),
                            ('display_type', '=', False),
                            ('dayofweek', '=', sheet_week_day),
                            ('week_type', '=', week_type),
                        ], limit=1)
                    else:
                        schedule_attendance = self.env['resource.calendar.attendance'].search([
                            ('calendar_id', '=', time_schedule.id),
                            ('display_type', '=', False),
                            ('dayofweek', '=', sheet_week_day),
                        ], limit=1)
                    holidays = self.env['resource.calendar.leaves'].search(
                        [('calendar_id', '=', time_schedule.id), ('resource_id', '=', False),
                         ('date_from', '>=', rec.sheet_date),
                         ('date_to', '<=', rec.sheet_date)])
                    if holidays:
                        vals = {
                            'employee_id': emp.id,
                            'act_date': rec.sheet_date,
                            'attendance_type': 'hd_holiday',
                            'hours': 0,
                            'ot_id': 'ph',
                            'cost_center': rec.cost_center.id,
                            'work_description': 'System generated'
                        }
                        timesheet_lines_list.append((0, 0, vals))
                    else:
                        emp_leave = self.env['hr.leave'].search([('date_from', '<=', rec.sheet_date),
                                                                 ('date_to', '>=', rec.sheet_date),
                                                                 ('state', '=', 'validate'),
                                                                 ('employee_id', '=', emp.id)], limit=1)
                        if schedule_attendance and schedule_attendance.is_weekend:
                            vals = {
                                'employee_id': emp.id,
                                'act_date': rec.sheet_date,
                                'attendance_type': 'hd_holiday',
                                'hours': 0,
                                'ot_id': 'weekend',
                                'cost_center': rec.cost_center.id,
                                'work_description': 'System generated'
                            }
                            timesheet_lines_list.append((0, 0, vals))
                        elif emp_leave:
                            vals = {
                                'employee_id': emp.id,
                                'act_date': rec.sheet_date,
                                'attendance_type': 'absent',
                                'hours': 0,
                                'ot_id': 'normal',
                                'cost_center': rec.cost_center.id,
                                'work_description': 'System generated'
                            }
                            timesheet_lines_list.append((0, 0, vals))
                        else:
                            vals = {
                                'employee_id': emp.id,
                                'act_date': rec.sheet_date,
                                'attendance_type': rec.attendance_type,
                                'hours': 0,
                                'cost_center': rec.cost_center.id,
                                'ot_id': 'normal',
                            }
                            timesheet_lines_list.append((0, 0, vals))
                rec.update({'timesheet_lines': timesheet_lines_list})


class HRTimesheetImportLines(models.Model):
    """
    The Import Lines From Uploaded XLS stored here
    """
    _name = 'hr.timesheet.import.lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'HR Timesheet Import Lines'

    import_id = fields.Many2one('hr.timesheet.import', ondelete='cascade')
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee',
                                  domain=['|', ('active', '=', True), ('active', '=', False)], tracking=True)
    act_date = fields.Date('Date', required=True)
    work_description = fields.Char(string='Remarks', required=False)
    cost_center = fields.Many2one('account.analytic.account', string='Project', required=True)
    attendance_type = fields.Selection([('partial_day', 'Partial Day'),
                                        ('pr_present', 'PR- Present'),
                                        ('absent', 'A – Absent'),
                                        ('hd_holiday', 'HD- Holiday'),
                                        ('sick_leave', 'SL- Sick Leave'),
                                        ('annual_leave', 'AL- Annual Leave'),
                                        ('emergency_leave', 'EL- Emergency Leave')])
    ot_id = fields.Selection([('normal', 'Normal OT'),
                              ('weekend', 'Weekend OT'),
                              ('ph', 'Public Holiday OT')],
                             default='normal')

    hours = fields.Float('OT Hours')
    company_id = fields.Many2one('res.company', 'Company', related='import_id.company_id')

    @api.constrains('act_date', 'employee_id')
    def check_timesheet_line(self):
        """
        To restrict the entering of timesheets not on date and duplicate employee lines
        :return:
        """
        for record in self:
            if record.act_date and record.import_id.sheet_date:
                if record.act_date != record.import_id.sheet_date:
                    raise UserError("Date Mismatch. You can only import timesheet on %s "
                                    % record.import_id.sheet_date)
                timesheet_lines = record.import_id.timesheet_lines.mapped('employee_id.id')
                contains_duplicates = any(timesheet_lines.count(emp) > 1 for emp in timesheet_lines)
                if contains_duplicates:
                    raise UserError("Duplicate employee timesheet line is not allowed")


class HRTimesheetMissed(models.Model):
    _name = 'hr.timesheets.missed'
    _description = 'Missed Timesheet'

    @api.depends('employee_id')
    def get_name(self):
        self.employee_name = self.employee_id.name

    @api.depends('employee_id')
    def get_code(self):
        self.code = self.employee_id.emp_id

    main_timesheet_id = fields.Many2one('hr.main.timesheet')
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee Id')
    code = fields.Char(compute='get_code', string='Employee ID')
    employee_name = fields.Char('Employee', compute="get_name")
    company_id = fields.Many2one('res.company', 'Company', related='main_timesheet_id.company_id')
    reason = fields.Text('Reason')


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    emp_id = fields.Many2one(comodel_name='hr.employee', string='Employee Name')
    import_timesheet_id = fields.Many2one(comodel_name='hr.timesheet.import', string='Import Timesheet',
                                          ondelete='cascade')
    job_id = fields.Many2one(comodel_name='hr.job', string='Trade', readonly=True)
    week_day = fields.Selection([('sun', 'Sunday'),
                                 ('mon', 'Monday'),
                                 ('tue', 'Tuesday'),
                                 ('wed', 'Wednesday'),
                                 ('thu', 'Thursday'),
                                 ('fri', 'Friday'),
                                 ('sat', 'Saturday'),
                                 ], string='Weekdays', readonly=True)

    def compute_day(self):
        """computing the weekdays based on the date"""
        for record in self:
            w_day = datetime.strptime(str(record.date), '%Y-%m-%d').strftime('%A')
            if w_day == 'Sunday':
                self._cr.execute("UPDATE account_analytic_line SET week_day = 'sun' WHERE id = {0}".format(record.id))
            elif w_day == 'Monday':
                self._cr.execute("UPDATE account_analytic_line SET week_day = 'mon' WHERE id = {0}".format(record.id))
            elif w_day == 'Tuesday':
                self._cr.execute("UPDATE account_analytic_line SET week_day = 'tue' WHERE id = {0}".format(record.id))
            elif w_day == 'Wednesday':
                self._cr.execute("UPDATE account_analytic_line SET week_day = 'wed' WHERE id = {0}".format(record.id))
            elif w_day == 'Thursday':
                self._cr.execute("UPDATE account_analytic_line SET week_day = 'thu' WHERE id = {0}".format(record.id))
            elif w_day == 'Friday':
                self._cr.execute("UPDATE account_analytic_line SET week_day = 'fri' WHERE id = {0}".format(record.id))
            else:
                self._cr.execute("UPDATE account_analytic_line SET week_day = 'sat' WHERE id = {0}".format(record.id))

    @api.model
    def create(self, vals):
        resource = super(AccountAnalyticLine, self).create(vals)
        resource.compute_day()
        if resource.emp_id and resource.emp_id.job_id:
            resource.job_id = resource.emp_id.job_id.id
        return resource
