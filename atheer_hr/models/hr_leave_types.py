# -*- coding: utf-8 -*-


from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    leave_days_type = fields.Selection([('working_days', 'Working Days'),
                                        ('calendar_days', 'Calendar Days'),
                                        ], default='working_days',
                                       string="Leave Days", )
    start_date = fields.Selection([
        ('trail', 'Probation'),
        ('contract', 'Contract')], 'Start Date')
    restart_date = fields.Selection([
        ('contract', 'Contract'),
        ('daily', 'Daily'),
        ('annual', 'Annually')], 'Reset Type')
    leave_reset = fields.Selection([
        ('eligible', 'Eligibility'),
        ('accumulate', 'Accumulate')], 'Leave Reset')
    default_for = fields.Selection([
        ('all', 'Default All'),
        ('omani', 'Default Omani'),
        ('expat', 'Default Expat')], 'Set Default', default='all')
    is_muslim = fields.Boolean("Muslim")
    is_women = fields.Boolean("Women")
    is_omani = fields.Boolean("Omani")
    is_death_leave = fields.Boolean('Death Leave')

    eligible_days = fields.Float('Eligible Days')
    annual_leave = fields.Boolean(string="Annual Leave")
    unpaid_leave = fields.Boolean(string="IS Unpaid Leave")
    is_sick = fields.Boolean(string="Sick Leave")
    is_unpaid = fields.Boolean(string="Unpaid Leave")
    is_emergency_leave = fields.Boolean(string="Emergency Leave")
    eligible_days_type = fields.Selection(selection=[('fixed', 'Fixed'),
                                                     ('carry_forward', 'Carry Forward'),
                                                     ('no_limit', 'No Limit')], required=True,
                                          string="Eligible Days Type",
                                          default='no_limit')
    allocation_type = fields.Selection([
        ('no', 'No Limit'),
        ('fixed_allocation', 'Allow Employees Requests'),
        ('fixed', 'Set by Time Off Officer')],
        default='no', string='Mode',
        help='\tNo Limit: no allocation by default, users can freely request time off; '
             '\tAllow Employees Requests: allocated by HR and users can request time off and allocations;'
             '\tSet by Time Off Officer: allocated by HR and cannot be bypassed; users can request time off;')
    request_unit = fields.Selection(string="Hour from", selection='_get_valid_hours', default='day')
    default_type = fields.Boolean(default=False)
    responsible_id = fields.Many2one('res.users', 'Responsible', required=False, default=lambda self: self.env.user.id,
                                     domain=lambda self: [
                                         ('groups_id', 'in', self.env.ref('hr_holidays.group_hr_holidays_user').id)],
                                     help="This user will be responsible for approving this type of time off. "
                                          "This is only used when validation is 'By Time Off Officer' or 'By Employee's Manager and Time Off Officer'")

    @api.model
    def _get_valid_hours(self):
        selection = [('day', 'Day'), ('half_day', 'Half Day'), ('hour', 'Hours')]
        return selection

    @api.onchange('is_sick', 'is_unpaid', 'is_emergency_leave', 'annual_leave')
    def onchange_leave_types(self):
        for rec in self:
            if rec.is_sick:
                rec.is_unpaid = False
                rec.is_emergency_leave = False
                rec.annual_leave = False
            elif rec.is_unpaid:
                rec.is_sick = False
                rec.is_emergency_leave = False
                rec.annual_leave = False
            elif rec.is_emergency_leave:
                rec.is_sick = False
                rec.is_unpaid = False
                rec.annual_leave = False
            elif rec.annual_leave:
                rec.is_sick = False
                rec.is_unpaid = False
                rec.is_emergency_leave = False

    @api.onchange('annual_leave', 'restart_date', 'is_sick', 'annual_leave')
    def onchange_days_type(self):
        for rec in self:
            if rec.annual_leave:
                rec.is_sick = False
                rec.eligible_days_type = 'carry_forward'
                rec.restart_date = 'contract'
                rec.eligible_days = 30
            if rec.is_sick:
                rec.annual_leave = False
            if rec.is_unpaid:
                rec.is_sick = False
                rec.annual_leave = False
                rec.eligible_days_type = 'no_limit'

    @api.constrains('request_unit', 'eligible_days_type')
    def check_hour_type(self):
        for rec in self:
            if rec.annual_leave:
                if rec.request_unit == 'half_day':
                    raise ValidationError(" You cannot select hour from as half day for annual leaves ")
            if not rec.annual_leave:
                if rec.eligible_days_type == 'carry_forward':
                    raise ValidationError(" You cannot select Eligible days type as Carry Forward for annual leaves ")
            if rec.request_unit == 'hour':
                raise ValidationError(" You cannot select Hour from as hour for leave types")
