from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrLeaveStatistics(models.Model):
    _name = 'hr.leave.salary.balance'
    _inherit = ['mail.thread']
    _rec_name = 'employee_id'
    _description = 'Leave Salary Balance'

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, tracking=True)
    date_from = fields.Date(string="From Date", tracking=True)
    date_to = fields.Date(string="To Date", tracking=True)
    days = fields.Float(string="Days")

    @api.constrains('employee_id')
    def constrain_employee_ido(self):
        leave_salary_balance_rec = self.search_count([('employee_id', '=', self.employee_id.id)])
        if leave_salary_balance_rec > 1:
            raise UserError(_('Leave Salary Balance has been already created for the employee %s.') % (self.employee_id.display_ename))




