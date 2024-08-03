# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HRMainTimesheet(models.Model):
    _name = 'hr.main.timesheet'
    _description = 'HR Main Timesheet'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    state = fields.Selection([('draft', 'Draft'),
                              ('ts_gen', 'Approved'),
                              ('payslip', 'Payslips Generated'),
                              ('cancel', 'Rejected')],
                             copy=False, tracking=True, default='draft')
    name = fields.Char(required=True, copy=False, tracking=True, default='/')
    date_start = fields.Date('Date From', required=True, readonly=True, states={'draft': [('readonly', False)]},
                             tracking=True)
    date_end = fields.Date('Date To', required=True, readonly=True, states={'draft': [('readonly', False)]},
                           tracking=True)
    timesheet_ids = fields.One2many('hr.timesheet.import', 'main_timesheet_id', 'Employee Time sheets',
                                    copy=False, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department',
                                    states={'draft': [('readonly', False)]}, tracking=True)
    journal_id = fields.Many2one('account.journal', 'Salary Journal')
    missed_timesheets = fields.One2many('hr.timesheet.import', 'main_timesheet_id', 'Missed Timesheets', copy=False)
    payslip_id = fields.Many2one('hr.payslip.run', 'Payslip Batch', tracking=True, copy=False)
    omani_staff = fields.Boolean(string="Timesheet For Omani Staff",
                                 help="Select if you are uploading timesheets for labours.", tracking=True,
                                 copy=False)
    omani_labor = fields.Boolean(string="Timesheet For Omani Labor",
                                 help="Select if you are uploading timesheets for Omani Labor.",
                                 tracking=True,
                                 copy=False)
    expat_staff = fields.Boolean(string="Timesheet For Expat Staff",
                                 help="Select if you are uploading timesheets for Expat Staff.",
                                 tracking=True,
                                 copy=False)
    expat_labor = fields.Boolean(string="Timesheet For Expat Labor",
                                 help="Select if you are uploading timesheets for Expat Labor.",
                                 tracking=True,
                                 copy=False)
    work_location_id = fields.Many2one('hr.work.location', string='Work Location', required=False,
                                       domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                       readonly=True, states={"draft": [("readonly", False)]})
    employee_ids = fields.Many2many(comodel_name='hr.employee',
                                    tracking=True)  # special case used to submit ts for selected ones
    d_employee_ids = fields.Many2many('hr.employee', 'emp_timesheet_rel', 'time_id', 'emp_id',
                                      tracking=True)  # special case used to remove ts for selected ones
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.onchange('work_location_id')
    def get_work_location_employees(self):
        for rec in self:
            if rec.work_location_id:
                employee_ids = self.env['hr.employee'].search([('work_location_id', '=', rec.work_location_id.id)])
                rec.update({'employee_ids': [(6, 0, employee_ids.ids)]})
            else:
                rec.update({'employee_ids': [(5,)]})

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'hr.main.timesheet') or '/'
        result = super(HRMainTimesheet, self).create(vals)
        return result

    def _filter_category(self):
        self.update({'timesheet_ids': []})
        self.update({'missed_timesheets': []})
        domain = []
        if self.date_start and self.date_end and self.work_location_id:
            domain += [
                ('sheet_date', '>=', self.date_start),
                ('sheet_date', '<=', self.date_end),
                ('work_location_id', '=', self.work_location_id.id),
                ('main_timesheet_id', '=', False)]

            value = []
            if domain:
                timesheets = self.env['hr.timesheet.import'].search(domain)
                if timesheets:
                    value = [(6, 0, timesheets.ids)]
                self.timesheet_ids = [(5, _, _)]
                self.update({'timesheet_ids': value})

    def generate_timesheet(self):
        """Generate the timesheet for the conditions applied
        Case 1 Timesheet for Labours
            1.1 For Whole Department for the period
            1.2 For selected Employees from the list
            1.3 Not Generate for selected employees from the list
        Case 2 Timesheet for admin support
            There will be no department checking, check for admin support flag on the emp master
        Case 3 Timesheet for admin Engineers"""
        self._filter_category()

    def send_back(self):
        """

        :return:
        """
        for record in self:
            if record.state == 'ts_gen':
                record.state = 'draft'

    def ts_gen(self):
        l_type = self.env['hr.leave.type'].search([('is_unpaid', '=', True)], limit=1)
        for i in self.timesheet_ids:
            i.write({'state': 'open'})
            t_lines = i.timesheet_lines.filtered(
                lambda x: x.work_description in ('a', 'A'))
            # for line in t_lines:
            #     leave_check = self.env['hr.leave'].search(
            #         [('employee_id', '=', i.employee_id.id), ('request_date_from', '=', line.act_date),
            #          ('request_date_to', '=', line.act_date)])
            #     if not leave_check:
            #         leave = self.env['hr.leave'].create({
            #             'name': 'Unpaid Leaves - Timesheet',
            #             'employee_id': i.employee_id.id,
            #             'holiday_status_id': l_type.id,
            #             'request_date_from': line.act_date,
            #             'date_from': line.act_date,
            #             'request_date_to': line.act_date,
            #             'date_to': line.act_date,
            #             'number_of_days': 1,
            #         })
            #         leave.action_approvee()
        self.state = 'ts_gen'

    def cancel(self):
        """
        :return:
        """
        for record in self:
            record.write({'state': 'cancel'})

    def unlink_payslips(self):
        """
        Delete The payslip with the related timesheet. Before unlink make sure the related JE is unposted and removed.
        :return:
        """
        for record in self:
            if record.state == 'cancel':
                record.payslip_id.slip_ids and record.payslip_id.slip_ids.action_payslip_cancel()  # Just to make sure. JE is removed
                slips = [rec.number for rec in record.payslip_id.slip_ids]
                record.payslip_id.slip_ids and record.payslip_id.slip_ids.unlink()

                record.payslip_id.slip_ids and record.message_post(
                    body="Payslips Deleted.\n Reference %s" % slips,
                    subtype_xmlid="mail.mt_comment",
                    message_type="notification")

    def unlink(self):
        for record in self:
            if record.state == 'ts_gen':
                raise UserError(
                    _('You cannot delete the employee timesheet in the approved state.')
                )
        return super(HRMainTimesheet, self).unlink()
