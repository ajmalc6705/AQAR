# -*- coding: utf-8 -*-
from __future__ import print_function
import calendar
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from num2words import num2words
from datetime import date, datetime, timedelta
from calendar import monthrange
from lxml import etree
import json


class FinalSettlement(models.Model):
    _name = "final.settlement"
    _description = 'Final Settlement'
    _inherit = ['mail.thread']

    name = fields.Char(string='Final Settlement No', copy=False, readonly=True, required=True, default='/')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    resignation_reference = fields.Many2one('hr.resignation',
                                            domain=[('state', '=', 'approved'), ('need_final_settlement', '=', True)],
                                            string="Resignation Reference",
                                            help="Resignation reference for final settlement")
    designation = fields.Many2one(related='employee_id.job_id')
    department = fields.Many2one('hr.department', string="Department", related='employee_id.department_id', store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    state = fields.Selection([
        ('hr', 'HR Manager'),
        ('accounts', 'Accounts'),
        ('approved', 'Approved'),
        ('reject', 'Refused'),
    ], 'Status', default='hr',
        tracking=True, copy=False)
    hr_remarks = fields.Char(string="HR Remarks")
    account_remarks = fields.Char(string="Accounts Remarks")
    leave_settlement = fields.Selection([('yes', 'YES'), ('no', 'NO')])
    document_date = fields.Date(string="Document Date", readonly=True, store=True, default=fields.Date.today())
    final_settlement_date = fields.Date(string="Final Settlement as on")
    last_rejoin_date_from_al = fields.Date(string="Last Rejoin Date from AL", readonly=True,
                                           help="Date of rejoining of last leave taken")
    no_of_up_after_rejoin_from_al = fields.Float(string="No of UP After rejoin from AL", readonly=True,
                                                 help="Total unpaid leaves taken from date of final settlement")
    no_of_up_taken_from_joining = fields.Float(string="No of UP taken from the Joining", readonly=True,
                                               help="Total unpaid leaves taken from date of joining")
    passport_no = fields.Char(string="Passport", related='employee_id.passport_no')
    passport_expiry_date = fields.Date(string="Passport Expiry", related='employee_id.passport_expiry_date')
    civil_card_no = fields.Char(string="Civil Card No", related='employee_id.civil_card_no')
    civil_card_expire_date = fields.Date(string="Civil Card Expiry", related='employee_id.civil_card_expire_date')
    joining_date = fields.Date(string="Joining Date", related='employee_id.joining_date')
    date_of_travelling = fields.Date(string="Date Of Travelling")
    flight_name = fields.Char(string="Flight Name")
    flight_departure_time = fields.Datetime(string="Flight Departure Time")
    ticket_fare = fields.Float(string="Ticket Fare")
    last_date_of_duty = fields.Date(string="Last Date Of Duty")
    total_days_completed_from_joining = fields.Float(string="Total Days completed from Joining", store=True,
                                                     readonly=True,
                                                     help="Total number of days from date of joining to date of final settlement")
    eligible_leave_days = fields.Float(string="Eligible Leave Days",
                                       help="Leave Salary Balance + Eligible Annual Leaves")
    eligible_gratuity_days = fields.Float(string="Eligible Gratuity Days", store=True, readonly=True,
                                          help="Gratuity days calculated from date of joining to date of final settlement")
    leave_salary = fields.Float(string="Leave Salary", store=True, readonly=True)
    gratuity_amount = fields.Float(string="Gratuity Amount", store=True, readonly=True,
                                   help="Gratuity amount calculated from date of joining to date of final settlement")
    previous_month_salary = fields.Float(string="Previous Month Salary", store=True, readonly=True)
    current_month_salary = fields.Float(string="Current Month Salary", digits=(16, 6), store=True, readonly=True)
    total_ot_amount = fields.Float(string="Total OT amount", compute='compute_overtime', readonly=True)
    loan_deduction = fields.Float(string="Loan Deduction", store=True, readonly=True,
                                  help="Sum of loan installment amount")
    other_additions = fields.Float(string="Other Additions")
    medical_deduction = fields.Float(string="Medical Deduction")
    air_ticket_deduction = fields.Float(string="Air Ticket Deduction")
    other_deduction = fields.Float(string="Other Deduction")
    visa_deduction = fields.Float(string="Visa deduction", store=True, readonly=True,
                                  help="Visa Cost * (Visa Expire Date - Final Settlement Date).days + 1 / 730")
    visa_waive_off = fields.Float(string="Visa Waiveoff")
    air_ticket_waive_off = fields.Float(string="Air ticket Waiveoff")
    total_allowances = fields.Float(string="Total Allowances", readonly=True, store=True,
                                    help="Leave Salary + Gratuity Amount + Current Month Salary + Total OT Amount + Other Additions")
    total_deductions = fields.Float(string="Total Deductions", readonly=True, store=True,
                                    help="Loan Deduction + Medical Deduction + Air Ticket Deduction + Other Deduction + Visa Deduction - Visa Waive Off + Air Ticket Waive Off")
    net_payable = fields.Float(string="Net Payable R.O", readonly=True, store=True,
                               help="Total Allowances - Total Deductions")
    prepared_by = fields.Many2one('res.users', string="Prepared By", store=True,
                                  default=lambda self: self.env.user.id,
                                  readonly=True)
    checked_by = fields.Many2one('res.users', string="Checked By")
    approved_by = fields.Many2one('res.users', string="Approved By", store=True,
                                  readonly=True)
    salary_package_ids = fields.One2many('salary.packages', 'final_settlement_id', readonly=True,
                                         store=True)
    gross_salary = fields.Float(help="Employee Gross Salary")
    emp_timesheet = fields.One2many('settlement.timesheet.line', 'settlement_id', 'Employee Timesheets')
    rejected_by = fields.Many2one('res.users', string="Refused By")
    rejected_date = fields.Date(string="Refused Date")
    leave_salary_taken = fields.Boolean(string="Leave Salary ")
    gratuity_amount_taken = fields.Boolean(string="Gratuity Amount ")
    total_net_payable = fields.Float(string="Net Payable R.O ", readonly=True, store=True,
                                     help="Total Allowances - Total Deductions")
    loan_ids = fields.Many2many('hr.loan', compute="compute_loans")
    checklist_line_ids = fields.One2many('employee.checklist.line', 'settlement_id', string='Employee Checklist')

    # access flags
    send_back_flag = fields.Boolean(default=False)
    left_hr_flag = fields.Boolean(default=False)
    left_ch_flag = fields.Boolean(default=False)



    @api.depends('employee_id')
    @api.onchange('employee_id')
    def compute_loans(self):
        for rec in self:
            rec.loan_ids = self.env['hr.loan'].search([('employee_id', '=', rec.employee_id.id)]).ids

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('final.settlement') or '/'
        return super(FinalSettlement, self).create(vals)

    @api.onchange('employee_id', 'final_settlement_date')
    def onchange_eligible_leave_days(self):
        start_date = ''
        date_to = ''
        total_days = 0
        unpaid_leave = 0
        unpaid = 0
        unpaid_leaves = 0
        eligible_leave_days = 0
        leave_salary = 0
        if self.employee_id and self.final_settlement_date:
            leave_type = self.env['hr.leave.type'].search([('is_unpaid', '=', True)])
            leave_salary_obj = self.env['hr.leave.salary.balance'].search([('employee_id', '=', self.employee_id.id)],
                                                                          limit=1)
            if leave_salary_obj:
                eligible_leave_days = leave_salary_obj.days + self.employee_id.eligible_annual_leaves
                start_date = leave_salary_obj[-1].date_to
            elif not leave_salary_obj:
                start_date = self.employee_id.joining_date
                eligible_leave_days = self.employee_id.eligible_annual_leaves
            end_date = self.final_settlement_date
            self.eligible_leave_days = eligible_leave_days
            # start_date =datetime.strptime(start_date, '%d/%m/%y %H:%M:%S')
            if start_date and end_date:
                total_days = (end_date - start_date).days
            # unpaid leave
            if leave_salary_obj:
                unpaid = self.no_of_up_taken_from_joining
            unpaid_leave = unpaid
            # if total_days != 0 and self.employee_id.contract_id:
            #     leave_salary = leave_settlement_obj.calculate_leave_days(self.employee_id, total_days, unpaid_leave,
            #                                                              self.employee_id.contract_id.wage)
            #     if 'leave_salary' in leave_salary:
            #         leave_salary = leave_salary['leave_salary']
            self.leave_salary = leave_salary

    @api.onchange('resignation_reference')
    def onchange_resignation_reference(self):
        for rec in self:
            if rec.resignation_reference:
                rec.employee_id = rec.resignation_reference.employee_id.id
                if rec.employee_id:
                    rec.designation = rec.employee_id.job_id.id if rec.employee_id.job_id else False
                    rec.passport_no = rec.employee_id.passport_no if rec.employee_id.passport_no else False
                    rec.passport_expiry_date = rec.employee_id.passport_expiry_date if rec.employee_id.passport_expiry_date else False
                    rec.civil_card_no = rec.employee_id.civil_card_no if rec.employee_id.civil_card_no else False
                    rec.civil_card_expire_date = rec.employee_id.civil_card_expire_date if rec.employee_id.civil_card_expire_date else False
                    rec.joining_date = rec.employee_id.joining_date if rec.employee_id.joining_date else False
                    rec.date_of_travelling = rec.resignation_reference.confirmed_travel_date if rec.resignation_reference.confirmed_travel_date else False

    @api.onchange('employee_id', 'leave_salary', 'gratuity_amount', 'current_month_salary', 'total_ot_amount',
                  'other_additions')
    def onchange_allowances(self):
        for rec in self:
            rec.total_allowances = rec.leave_salary + rec.gratuity_amount + rec.current_month_salary + rec.total_ot_amount + rec.other_additions

    @api.onchange('employee_id', 'loan_deduction', 'medical_deduction', 'air_ticket_deduction', 'other_deduction',
                  'visa_deduction',
                  'visa_waive_off', 'air_ticket_waive_off')
    def onchange_deductions(self):
        for rec in self:
            rec.total_deductions = rec.loan_deduction + rec.medical_deduction + rec.air_ticket_deduction + rec.other_deduction + rec.visa_deduction - rec.visa_waive_off + rec.air_ticket_waive_off

    @api.onchange('employee_id', 'final_settlement_date', 'final_settlement_date')
    def onchange_a_current_salary(self):
        payslip_obj = self.env['hr.payslip']
        for rec in self:
            if rec.employee_id:
                resignation_obj = self.env['hr.resignation'].search(
                    [('employee_id', '=', rec.employee_id.id), ('state', '=', 'approved')])
                if resignation_obj:
                    rec.resignation_reference = resignation_obj.id
                else:
                    rec.resignation_reference = False
            # current month
            date_from = datetime.today().replace(day=1).date()
            worked_days = 0
            total_days = 0
            net_salary = 0
            loan_amt = 0
            previous_loan_amt = 0
            previous_month_days = 0
            previous_net_salary = 0
            # previous month
            previous_month = datetime.now().month - 1
            previous_year = datetime.today().year
            this_first = date.today().replace(day=1)
            prev_last = this_first - timedelta(days=1)
            prev_first = prev_last.replace(day=1)
            if previous_month == 0:
                previous_month = previous_month.year
                previous_year = datetime.today().year - 1
            if previous_year and previous_month:
                previous_month_days = monthrange(previous_year, previous_month)[1]
            if rec.employee_id and rec.final_settlement_date and rec.employee_id.contract_id:
                # current month
                find_res = payslip_obj.find_get_new_worked_days_lines(date_from, rec.final_settlement_date,
                                                                      self.employee_id.contract_id)
                if find_res:
                    worked_days = sum([rec['number_of_days'] for rec in find_res if rec['sequence'] != 'LEAVE90'])
                    total_days = rec.days_in_month(date_from)
                    bonus_amount = payslip_obj.find_bonus_amount(rec.employee_id,
                                                                 date_from, rec.final_settlement_date)
                    loan_addition = payslip_obj.find_loan_addition_amount(date_from, rec.final_settlement_date,
                                                                          rec.employee_id)
                    rec.employee_id.contract_id.worked_days = worked_days
                    rec.employee_id.contract_id.total_days = total_days
                    timesheet_val = payslip_obj.find_get_timesheet_lines(rec.employee_id, date_from,
                                                                         rec.final_settlement_date)
                    # timesheet = payslip_obj.find_ot_amount(date_from, rec.final_settlement_date,
                    #                                        rec.employee_id.contract_id, timesheet_val)
                    # if timesheet:
                    #     rec.employee_id.contract_id.ot_amount = timesheet.get('total_ot_amount', False)
                    if bonus_amount:
                        rec.employee_id.contract_id.bonus_amount = bonus_amount.get('bonus_amount', False)
                    if loan_addition:
                        rec.employee_id.contract_id.loan_addition_amount = loan_addition.get('sum_loan_addition', False)
                        rec.employee_id.contract_id.loan_deduction_amount = loan_addition.get('sum_loan_deduction',
                                                                                              False)
                    # loan amount
                    loan_amount = payslip_obj.find_loan_installment(rec.employee_id, rec.final_settlement_date)
                    if loan_amount:
                        for t in loan_amount['vals']:
                            loan_amt += t['amount']
                        rec.employee_id.contract_id.loan_amount = loan_amt
                    rec.employee_id.contract_id.basic_salary = rec.employee_id.contract_id.wage * worked_days / (
                            total_days or 1)
                payslip_lines = payslip_obj.find_get_payslip_lines(find_res, rec.employee_id)

                if payslip_lines:
                    net_salary = [net['amount'] for net in payslip_lines if net['code'] == 'NET']
                    if net_salary:
                        net_salary = net_salary[0]
                # previous month
                previous_find_res = payslip_obj.find_get_new_worked_days_lines(prev_first, prev_last,
                                                                               self.employee_id.contract_id)
                rec.employee_id.contract_id.worked_days = 0
                rec.employee_id.contract_id.total_days = 0
                rec.employee_id.contract_id.bonus_amount = 0
                rec.employee_id.contract_id.loan_addition_amount = 0
                rec.employee_id.contract_id.loan_deduction_amount = 0
                rec.employee_id.contract_id.basic_salary = 0
                rec.employee_id.contract_id.loan_amount = 0
                rec.employee_id.contract_id.ot_amount = 0
                if previous_find_res:
                    previous_worked_days = sum(
                        [rec['number_of_days'] for rec in previous_find_res if rec['sequence'] != 'LEAVE90'])
                    previous_total_days = rec.days_in_month(prev_first)

                    rec.employee_id.contract_id.worked_days = previous_worked_days
                    rec.employee_id.contract_id.total_days = previous_total_days
                    previous_bonus_amount = payslip_obj.find_bonus_amount(rec.employee_id,
                                                                          prev_first, prev_last)
                    previous_loan_addition = payslip_obj.find_loan_addition_amount(prev_first, prev_last,
                                                                                   rec.employee_id)
                    timesheet_val = payslip_obj.find_get_timesheet_lines(rec.employee_id, prev_first,
                                                                         prev_last)
                    # timesheet = payslip_obj.find_ot_amount(prev_first, prev_last,
                    #                                        rec.employee_id.contract_id, timesheet_val)
                    # if timesheet:
                    #     rec.employee_id.contract_id.ot_amount = timesheet.get('total_ot_amount', False)
                    if previous_bonus_amount:
                        rec.employee_id.contract_id.bonus_amount = previous_bonus_amount.get('bonus_amount', False)
                    if previous_loan_addition:
                        rec.employee_id.contract_id.loan_addition_amount = previous_loan_addition.get(
                            'sum_loan_addition', False)
                        rec.employee_id.contract_id.loan_deduction_amount = previous_loan_addition.get(
                            'sum_loan_deduction',
                            False)
                        # loan amount
                    previous_loan_amount = payslip_obj.find_loan_installment(rec.employee_id, prev_last)
                    if previous_loan_amount:
                        for t in previous_loan_amount['vals']:
                            previous_loan_amt += t['amount']
                        rec.employee_id.contract_id.loan_amount = previous_loan_amt
                    rec.employee_id.contract_id.basic_salary = rec.employee_id.contract_id.wage * previous_total_days / (
                            previous_total_days or 1)
                previous_payslip_lines = payslip_obj.find_get_payslip_lines(previous_find_res, rec.employee_id)
                if previous_payslip_lines:
                    previous_net_salary = [net['amount'] for net in previous_payslip_lines if net['code'] == 'NET']
                    if previous_net_salary:
                        previous_net_salary = previous_net_salary[0]
                self.current_month_salary = round(net_salary, 5)
                self.previous_month_salary = round(previous_net_salary, 5)

    def days_in_month(self, date_from):
        for record in self:
            date_format = "%Y-%m-%d"
            if date_from and record.final_settlement_date:
                m = datetime.strptime(str(date_from), date_format)
                last_date = calendar.monthrange(m.year, m.month)[1]
                return last_date

    def _valid_field_parameter(self, field, name):
        return name == 'digits' or super()._valid_field_parameter(field, name)

    @api.onchange('leave_salary_taken', 'gratuity_amount_taken')
    @api.depends('leave_salary_taken', 'gratuity_amount_taken')
    def onchange_total_net_payable(self):
        for rec in self:
            if rec.leave_salary_taken:
                rec.total_net_payable = rec.total_allowances - rec.total_deductions - rec.leave_salary
            elif rec.gratuity_amount_taken:
                rec.total_net_payable = rec.total_allowances - rec.total_deductions - rec.gratuity_amount_taken
            else:
                rec.total_net_payable = rec.total_allowances - rec.total_deductions

    @api.onchange('total_allowances', 'total_deductions')
    @api.depends('total_allowances', 'total_deductions')
    def onchange_total(self):
        for rec in self:
            rec.net_payable = rec.total_allowances - rec.total_deductions

    @api.depends('employee_id', 'emp_timesheet')
    def compute_overtime(self):
        payslip_obj = self.env['hr.payslip']
        total = 0
        for records in self:
            date_from = datetime.today().replace(day=1).date()
            if records.final_settlement_date and records.employee_id:
                timesheet_val = payslip_obj.find_get_timesheet_lines(records.employee_id, date_from,
                                                                     records.final_settlement_date)
                # todo : fix ot calculation
                # timesheet = payslip_obj.find_ot_amount(date_from, records.final_settlement_date,
                #                                        records.employee_id.contract_id, timesheet_val)
                # if timesheet:
                #     total = timesheet.get('total_ot_amount', False)

            records.total_ot_amount = total

    @api.onchange('employee_id', 'final_settlement_date', 'last_date_of_duty')
    def onchange_visa_deduction_days(self):
        for rec in self:
            if rec.final_settlement_date and rec.employee_id.visa_expire:
                difference_days = (rec.employee_id.visa_expire - rec.final_settlement_date).days + 1
                if difference_days > 31:
                    rec.visa_deduction = rec.employee_id.visa_cost * difference_days / 730
                else:
                    rec.visa_deduction = 0

    @api.onchange('employee_id', 'final_settlement_date', 'last_date_of_duty')
    def onchange_employee_days(self):
        """
        gratuity calculation:((Basic pay /730)*1095)
        """
        for rec in self:
            if rec.employee_id and rec.final_settlement_date and rec.joining_date:
                result = rec.employee_id.gratuity_days(rec.employee_id, rec.final_settlement_date, rec.joining_date)
                rec.eligible_gratuity_days = result['eligible_gratuity_days']
                rec.gratuity_amount = result['gratuity_amount']

    @api.onchange('employee_id', 'final_settlement_date', 'last_date_of_duty')
    def onchange_employee(self):
        values = []
        for rec in self:
            if rec.final_settlement_date:
                rec.last_date_of_duty = rec.final_settlement_date
            if rec.employee_id:
                if rec.employee_id.contract_id.wage:
                    rec.leave_salary = (rec.employee_id.contract_id.wage / 30) * rec.eligible_leave_days
                else:
                    rec.leave_salary = 0
                loan_amt = 0
                resignation = self.env['hr.resignation'].search(
                    [('employee_id', '=', rec.employee_id.id), ('state', '=', 'approved')], limit=1)
                if resignation:
                    rec.resignation_reference = resignation.id
                else:
                    rec.resignation_reference = False
                loans = self.env['hr.loan'].search(
                    [('employee_id', '=', rec.employee_id.id), ('state', '=', 'approved')])
                if loans:
                    for loan in loans:
                        for each in loan.installments:
                            if not each.paid:
                                loan_amt += each.amount
                            rec.loan_deduction = loan_amt
                else:
                    rec.loan_deduction = 0
                if rec.final_settlement_date and rec.employee_id.joining_date:
                    total_days_completed_from_joining = (
                            rec.final_settlement_date - rec.employee_id.joining_date + relativedelta(days=1)).days
                    rec.total_days_completed_from_joining = total_days_completed_from_joining - rec.no_of_up_taken_from_joining
                else:
                    rec.total_days_completed_from_joining = 0
                leaves = self.env['hr.leave'].search(
                    [('employee_id', '=', rec.employee_id.id),
                     ('request_date_to', '<=', rec.final_settlement_date),
                     ('holiday_status_id.annual_leave', '=', True), ('annual_leave_confirmed', '=', True),
                     ('state', '=', 'validate')], order="request_date_to asc")
                all_unpaid_leaves = rec.employee_id.onchange_no_unpaid_from_joining(rec.employee_id)
                if all_unpaid_leaves:
                    rec.no_of_up_taken_from_joining = all_unpaid_leaves['no_of_up_taken_from_joining']

                unpaid_leaves = self.env['hr.leave'].search(
                    [('employee_id', '=', rec.employee_id.id),
                     ('request_date_from', '>=', rec.final_settlement_date),
                     ('holiday_status_id.is_unpaid', '=', True),
                     ('state', '=', 'validate')])
                if unpaid_leaves:
                    rec.no_of_up_after_rejoin_from_al = sum(unpaid_leaves.mapped('number_of_days'))
                if leaves:
                    if leaves[-1].leave_returned:
                        rec.last_rejoin_date_from_al = leaves[-1].rejoining_date
                    if not leaves[-1].leave_returned:
                        raise ValidationError(_("%s has no leave return for the last leave taken.") % (
                            rec.employee_id.name))
                if rec.employee_id.contract_id and rec.employee_id.contract_id.salary_package_ids:
                    if not rec.salary_package_ids:
                        for record in rec.employee_id.contract_id.salary_package_ids:
                            vals = (0, 0, {
                                'component': record.component.id,
                                'amount_per_month': record.amount_per_month,
                            })
                            values.append(vals)
                        self.write({'salary_package_ids': values})
                        rec.gross_salary = rec.employee_id.gross_salary
                else:
                    rec.salary_package_ids = False
                    rec.gross_salary = False
                # if rec.final_settlement_date:
                    # previous_month = rec.final_settlement_date - relativedelta(months=1)
                    # payslip = self.env['hr.payslip'].search(
                    #     [('employee_id', '=', rec.employee_id.id), ('state', '=', 'done'),
                    #      ('date_from', '<=', previous_month), ('date_to', '>=', previous_month)], order="date_to asc")
                # all_payslip = self.env['hr.payslip'].search(
                #     [('employee_id', '=', rec.employee_id.id), ('state', '=', 'done')])
                # if all_payslip:
                    # self._get_timesheet_lines(all_payslip, rec)

    # def _get_timesheet_lines(self, all_payslip, rec):
    #     """fetch the list of timesheet lines of the employees"""
    #     query = """SELECT count(il.id) as days_worked, sum(il.hours) as hours, to_char(il.act_date, 'MM') as month,
    #                    il.cost_center as bu_cc, il.ot_id as ot_id
    #                    FROM hr_timesheet_import_lines il inner join hr_timesheet_import ti on il.import_id=ti.id WHERE
    #                    ti.employee_id =""" + str(rec.employee_id.id) + """
    #                    AND act_date>'""" + str(all_payslip[-1].date_to) + """'
    #                    GROUP BY
    #                    to_char(act_date, 'MM'), cost_center,ot_id
    #                """
    #     self._cr.execute(query)
    #     worked_time_lines = self.emp_timesheet.browse([])
    #     time_disc = self._cr.dictfetchall()
    #     for time_line in time_disc:
    #         time_line['settlement_id'] = rec.id
    #         worked_time_lines |= worked_time_lines.new(time_line)
    #     if time_disc:
    #         return worked_time_lines
    #     else:
    #         return [(5, False, False)]

    @api.depends('net_payable', 'total_net_payable')
    def _compute_amount_in_word(self):
        first = 'Rial Omani '
        mid = ' Bzs '
        last = ' only'
        for rec in self:
            total_net_payable = round(rec.total_net_payable, 3)
            if total_net_payable.is_integer():
                total = first + str(num2words(total_net_payable)) + last
            else:
                convert_net_payable = str(total_net_payable)
                res = convert_net_payable.split(".")
                total = first + str(num2words(int(res[0]))) + mid + str(num2words(int(res[1]))) + last
            rec.total = total

    total = fields.Char(string="Amount In Words:", compute='_compute_amount_in_word')

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(FinalSettlement, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                           submenu=False)
        form_view_id = self.env.ref('atheer_hr.view_final_settlement_form').id
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
                if not self.env.user.has_group('atheer_hr.group_hr_accounts'):
                    node = doc.xpath("//field[@name='account_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                return res
        return res

    def send_to_accounts(self):
        for rec in self:
            rec.send_back_flag = False
            rec.left_ch_flag = True
            rec.state = 'accounts'

    def send_back(self):
        """
         send backs to previous state
        """
        for rec in self:
            if rec.state == 'accounts':
                rec.send_back_flag = True
                rec.write({'state': 'hr'})

    def action_reject(self):
        for rec in self:
            rec.write({'state': 'reject', 'rejected_by': self.env.user.id, 'rejected_date': date.today()})

    def approve(self):
        for rec in self:
            rec.send_back_flag = False
            rec.state = 'approved'
            rec.approved_by = self.env.user.id

    def unlink(self):
        for record in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if record.state != 'hr':
                    raise UserError(
                        _('You cannot delete the Final Settlement %s in the current state.', record.name)
                    )
            return super(FinalSettlement, self).unlink()


class PayslipTimesheetLine(models.Model):
    _name = 'settlement.timesheet.line'
    _description = 'Settlement Timesheet Line'

    settlement_id = fields.Many2one(comodel_name='final.settlement', string='Payslip', required=True,
                                    ondelete='cascade')
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
    company_id = fields.Many2one(comodel_name='res.company', string='Company', related='settlement_id.company_id')


class EmployeeChecklistLine(models.Model):
    _name = 'employee.checklist.line'
    _rec_name = 'checklist_id'
    _description = 'Checklist line'

    settlement_id = fields.Many2one('final.settlement', string='Settlement')
    checklist_id = fields.Many2one('employee.checklist', string='Checklist')
    answers = fields.Selection([('yes', 'YES'), ('no', 'NO')], string='Answer')
