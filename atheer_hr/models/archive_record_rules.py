# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrLeaveInherit(models.Model):
    _inherit = 'hr.leave'

    @api.model
    def archive_time_off_rules(self):
        """
        Deleting existing record rules of leave for the access rights of users
        """
        if self.env.ref('hr_holidays.hr_leave_rule_responsible_update', raise_if_not_found=False):
            self.env.ref('hr_holidays.hr_leave_rule_responsible_update').active = False

        if self.env.ref('hr_holidays.hr_leave_rule_responsible_read', raise_if_not_found=False):
            self.env.ref('hr_holidays.hr_leave_rule_responsible_read').active =False

        if self.env.ref('hr_holidays.hr_leave_rule_user_read', raise_if_not_found=False):
            self.env.ref('hr_holidays.hr_leave_rule_user_read').active = False

        if self.env.ref('hr_holidays.hr_leave_rule_officer_update', raise_if_not_found=False):
            self.env.ref('hr_holidays.hr_leave_rule_officer_update').active = False

        if self.env.ref('hr_holidays.hr_leave_rule_employee_update', raise_if_not_found=False):
            self.env.ref('hr_holidays.hr_leave_rule_employee_update').active = False

        if self.env.ref('hr_holidays.hr_leave_rule_employee', raise_if_not_found=False):
            self.env.ref('hr_holidays.hr_leave_rule_employee').active = False
