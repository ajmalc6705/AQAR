from datetime import datetime, timedelta, date
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from pytz import timezone, UTC


class PublicHolidays(models.Model):
    _name = 'public.holidays'
    _inherit = ['mail.thread']
    _rec_name = 'year'
    _description = 'Public Holidays'

    name = fields.Char()
    year = fields.Char(string="Year", copy=False)
    resource_calendar_id = fields.One2many('resource.calendar.leaves', 'public_holiday_id',
                                           domain=[('approved', '=', False)])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved')], string='State', default='draft', tracking=True)

    @api.constrains('year')
    def check_year_validation(self):
        public_holiday_rec = self.search_count([('year', '=', self.year)])
        if public_holiday_rec > 1:
            raise UserError(_('You have already created for the year %s .') % (
                self.year))
        for rec in self.resource_calendar_id:
            if str(rec.date_from.year) != str(self.year) or str(rec.date_to.year) != str(self.year):
                raise ValidationError(
                    _('You cannot add holiday dates which does not belongs to the given year'))

    def action_approve(self):
        resource_calendar_obj = self.env['resource.calendar'].search([])
        holidays = []
        if self.resource_calendar_id:
            for rec in self.resource_calendar_id:
                vals = {
                    'public_holiday_id': self.id,
                    'date_from': rec.date_from,
                    'date_to': rec.date_to,
                    'name': rec.name,
                    'work_entry_type_id': rec.work_entry_type_id.id,
                    'approved': True
                }
                holidays.append((0, 0, vals))
        for each in resource_calendar_obj:
            each.global_leave_ids = holidays
        if self.resource_calendar_id:
            self.state = 'approved'
        else:
            raise ValidationError(
                _('You cannot move to next stage as there are no public holidays records')
            )

    def set_to_draft(self):
        for rec in self:
            rec.state = 'draft'
            resource_calendar_obj = self.env['resource.calendar.leaves'].search(
                [('public_holiday_id', '=', rec.id), ('approved', '=', True)])
            for each in resource_calendar_obj:
                each.unlink()

    def unlink(self):
        for record in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if record.state != 'draft':
                    raise UserError(
                        _('You cannot delete the public holidays %s in the current state.', record.year)
                    )
            return super(PublicHolidays, self).unlink()

    # Cron for create compensation leave for overlapping weekend and public holiday
    def update_compensation_leave(self):
        current_year = datetime.now().year
        first_day = date(current_year, 1, 1)
        last_day = date(current_year, 12, 31)
        comp_activity = self.env.ref("hr_work_entry_contract.work_entry_type_compensatory")
        holiday_type = self.env['hr.leave.type'].search([('work_entry_type_id', '=', comp_activity.id)], limit=1)
        ph_id = self.search([('year', '=', current_year), ('state', '=', 'approved')], limit=1)
        ph_leave_ids = ph_id.resource_calendar_id
        for emp in self.env['hr.employee'].sudo().search([]):
            print(emp.name)
            emp_calendar_id = emp.resource_calendar_id
            for leave in ph_leave_ids:
                print(leave.name)
                leave_allocation = self.env['hr.leave.allocation'].search([('employee_id', '=', emp.id),
                                                                           ('ph_line', '=', leave.id)])
                if not leave_allocation:
                    comp_leave_count = 0
                    date_to = leave.date_to.replace(tzinfo=UTC).astimezone(timezone(emp.tz)).date()
                    date_from = leave.date_from.replace(tzinfo=UTC).astimezone(timezone(emp.tz)).date()
                    delta = date_to - date_from
                    leave_days = [date_from + timedelta(days=i) for i in range(delta.days + 1)]
                    for leave_day in leave_days:
                        print(leave_day)
                        leave_weekday = leave_day.weekday()
                        print(leave_weekday, type(leave_weekday))
                        schedule_line = emp_calendar_id.attendance_ids.filtered(
                            lambda x: x.dayofweek == str(leave_weekday) and not x.is_weekend)
                        if not schedule_line:
                            comp_leave_count += 1
                    if comp_leave_count > 0 and holiday_type:
                        self.env['hr.leave.allocation'].create({
                            'employee_id': emp.id,
                            'employee_ids': [(6, 0, [emp.id])],
                            'date_from': first_day,
                            'date_to': last_day,
                            'ph_line': leave.id,
                            'ph_id': ph_id.id,
                            'number_of_days': comp_leave_count,
                            'holiday_status_id': holiday_type.id
                        })


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    def _default_work_entry_type_id(self):
        return self.env.ref('hr_work_entry_contract.work_entry_type_leave', raise_if_not_found=False)

    public_holiday_id = fields.Many2one(comodel_name='public.holidays', copy=False, ondelete='cascade')
    work_entry_type_id = fields.Many2one(comodel_name='hr.work.entry.type', string='Work Entry Type',
                                         default=_default_work_entry_type_id)
    approved = fields.Boolean(default=False)
