import ast
import calendar
from odoo import models, fields, api, _
from datetime import date, timedelta, datetime
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class EmployeeUtilityType(models.Model):
    _name = 'employee.utility.type'
    _description = "Employee Utility"
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)


class EmployeeUtility(models.Model):
    _name = 'employee.utility'
    _description = "Employee Utility"
    _rec_name = 'utility_type'

    employee_id = fields.Many2one('hr.employee')
    utility_type = fields.Many2one('employee.utility.type', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id.id)

    date = fields.Date(string="Date", required=True)
    file_name = fields.Char('File Name')
    account_no = fields.Char('Account no')
    attachment = fields.Binary(string="Bill Attachment ", required=True)
    amount = fields.Monetary(string="Amount", required=True, store=True)


class DocMaster(models.Model):
    _name = 'doc.master'
    _description = "Doc Master"
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)
    comments = fields.Text(string="Comments")


class EmpDocuments(models.Model):
    _name = 'hr.employee.docs'
    _description = "Employee Documents"
    _rec_name = 'name'

    employee = fields.Many2one('hr.employee')
    name = fields.Many2one('doc.master', string="Document Name", required=True)
    doc_type = fields.Selection([('self', 'Self'), ('relative', 'Relative')], string="Document Type",
                                default='self', required=True)
    relation_id = fields.Many2one("hr.employee.relative.relation", string="Relation")
    doc_id = fields.Char(string="Document No./Id", required=True)
    exp_date = fields.Date(string="Expiry Date", required=True)
    comments = fields.Text(string="Comments")
    file_name = fields.Char('File Name')
    attachment = fields.Binary(string="Attachment", required=True)
    type = fields.Selection([('passport', 'Passport'), ('civil_id', 'Civil id')], required=False, string="Type")
    # notification checking field
    doc_notify = fields.Boolean(string="Active Doc Notification", default=False)

    @api.onchange('doc_type')
    def onchange_doc_type(self):
        for rec in self:
            if rec.doc_type == 'self':
                rec.relation_id = False

    # @api.onchange('type')
    # def onchange_type(self):
    #     for rec in self:
    #         doc_passport_name = self.env['doc.master'].search([('name', '=', 'Passport')])
    #         doc_civil_name = self.env['doc.master'].search([('name', '=', 'Civil Id')])
    #         if not doc_passport_name:
    #             self.env['doc.master'].create({'name': 'Passport'})
    #         if not doc_civil_name:
    #             self.env['doc.master'].create({'name': 'Civil Id'})
    #         if rec.type == 'passport':
    #             rec.name = doc_passport_name
    #             rec.doc_id = rec.employee.passport_no
    #             rec.exp_date = rec.employee.passport_expiry_date
    #         elif rec.type == 'civil_id':
    #             rec.name = doc_civil_name
    #             rec.doc_id = rec.employee.civil_card_no
    #             rec.exp_date = rec.employee.civil_card_expire_date


class HrJobInherit(models.Model):
    _inherit = 'hr.job'

    occupation_code = fields.Char(string="Occupation Code", readonly=False, store=True)
    special_display_name = fields.Boolean()

    @api.model
    def create(self, vals_list):
        res = super(HrJobInherit, self).create(vals_list)
        for rec in res:
            occupation_code = self.env['occupation.code'].search([('job_id', '=', rec.id)])
            if rec.occupation_code:
                if occupation_code:
                    occupation_code.write({'name': rec.occupation_code})
                if not occupation_code:
                    self.env['occupation.code'].create({'name': rec.occupation_code, 'job_id': rec.id})
        return res

    def write(self, vals_list):
        for rec in self:
            occupation_code = self.env['occupation.code'].search([('job_id', '=', rec.id)])
            if vals_list.get('occupation_code', False):
                if occupation_code:
                    occupation_code.write({'name': vals_list['occupation_code']})
                if not occupation_code:
                    self.env['occupation.code'].create({'name': vals_list['occupation_code'], 'job_id': rec.id})
        return super(HrJobInherit, self).write(vals_list)


class HrJobOccupationCode(models.Model):
    _name = 'occupation.code'
    _description = "Occupation Code"
    _rec_name = 'name'

    name = fields.Char(string="Name")
    job_id = fields.Many2one('hr.job')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    work_permit_name = fields.Char('Work Permit No')

    @api.model
    def _get_sequence(self):
        company_id = self.env.company.id
        sequence = self.env['ir.sequence'].next_by_code('hr.employee.code')
        if sequence:
            seq_obj = self.env['ir.sequence'].search(
                [('code', '=', 'hr.employee.code'), ('company_id', '=', company_id)])
            value = seq_obj.number_next_actual - 1
            seq_obj.sudo().update({'number_next_actual': value})
            return sequence
        else:
            return False

    @api.model
    def _get_visa_clearance_domain(self):
        """Only showing the records with balance for clearance"""
        return [('id', 'in', self.env['hr.clearance.details'].search([('balance', '!=', 0)]).ids)]

    # Rename fields
    parent_id = fields.Many2one('hr.employee', string='Manager/Supervisor')
    work_phone = fields.Char(string='Contact No')

    emp_id = fields.Char(string="Employee ID", default=lambda self: self._get_sequence())
    display_ename = fields.Char(string="Full Name", compute='_compute_display_ename', store=True)
    emp_check = fields.Boolean(default=True)
    reporting_department = fields.Many2one('hr.department', string="Reporting Department", groups="hr.group_hr_user")
    age = fields.Char(string="Age", readonly="True")
    passport_no = fields.Char(string="Passport", groups="hr.group_hr_user")
    passport_place_of_issue = fields.Char(string="Passport Place Of Issue", groups="hr.group_hr_user")
    civil_card_no = fields.Char(string="Civil Card No", groups="hr.group_hr_user")
    civil_card_designation = fields.Char(string="Civil Card Designation", groups="hr.group_hr_user")
    visa_no = fields.Char(string="Visa No", groups="hr.group_hr_user")
    visa_duration = fields.Selection(
        [('renewable', '2 years renewable'), ('non_renewable', '2 years non renewable'), ('nine_month', '9 month ')],
        string="Visa Duration", groups="hr.group_hr_user")
    is_omani = fields.Selection([('omani', 'Omani'), ('expat', 'Expat')], default='expat')
    pasi_no = fields.Char(string="PASI No", groups="hr.group_hr_user")

    visa_company_id = fields.Many2one('res.company', string='Visa Company', default=lambda self: self.env.company,
                                      copy=False)
    mess_facility = fields.Selection([('no', 'No'), ('yes', 'Yes')], default='no',
                                     help='To Identify this employee have Mess facility', )
    blood_group_id = fields.Many2one('emp.blood.groups', string='Blood Group')
    address_home_country_id = fields.Many2one('res.partner', 'Address in Home Country',
                                              help='Enter here the private address of the employee, not the one linked to your company.',
                                              groups="hr.group_hr_user", tracking=True,
                                              domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    # active_contract_id = fields.Many2one('hr.contract', string='Active Contract', readonly=True)

    employee_docs = fields.One2many('hr.employee.docs', 'employee', "Documents")
    employee_utility_ids = fields.One2many('employee.utility', 'employee_id', "Utility")
    joining_date = fields.Date(string="Joining Date", tracking=True)
    site_joining_date = fields.Date(string="Site Joining Date", tracking=True)

    passport_issued_date = fields.Date(string="Passport Issued Date", tracking=True, groups="hr.group_hr_user")
    passport_accepted_date = fields.Date(string="Passport Accepted Date", tracking=True, groups="hr.group_hr_user")
    civil_card_expire_date = fields.Date(string="Civil Card Expire Date", tracking=True, groups="hr.group_hr_user")
    visa_start_date = fields.Date(string="Visa Start Date", tracking=True, groups="hr.group_hr_user")
    passport_expiry_date = fields.Date(string="Passport Expiry Date", tracking=True, groups="hr.group_hr_user")

    ot_eligibility = fields.Boolean(string="OT Eligibility", tracking=True, )
    ph_ot_eligibility = fields.Boolean(string="Public Holiday OT Eligibility", tracking=True, )

    bank_id = fields.Many2one(comodel_name='res.bank', string='Bank', groups="hr.group_hr_user",
                              related='bank_account_id.bank_id')
    bank_name = fields.Char('Bank Name', copy=False, groups="hr.group_hr_user")
    bank_branch = fields.Char('Bank Branch', copy=False, store=True,
                              groups="hr.group_hr_user")
    acc_holder_name = fields.Char('Account Name', copy=False, groups="hr.group_hr_user",
                                  related='bank_account_id.acc_holder_name')
    # bank_account = fields.Char('Bank Account', copy=False, groups="hr.group_hr_user")

    employee_category = fields.Selection([
        ('omani_staff', 'Omani Staff'),
        ('omani_labor', 'Omani Labor'),
        ('expat_staff', 'Expat Staff'),
        ('expat_labor', 'Expat Labor'),
        ('domestic_servant', 'Domestic Servant'),
    ], string='Employee Category', copy=False, index=True)
    employee_status = fields.Selection([
        ('active', 'Active'),
        ('resigned', 'Resigned'),
    ], string='Employee Status', copy=False, default="active", index=True, tracking=True)
    is_eligible_for_annual_leave = fields.Boolean(string="Eligible for Annual Leave", default=True)
    eligible_annual_leaves = fields.Float(string="Eligible Annual Leaves", compute='compute_eligible_annual_leaves')
    total_annual_leaves = fields.Float(string="Total Annual Leaves", compute='compute_eligible_annual_leaves')
    open_blnc = fields.Float('Opening Balance(Annual Leave)', copy=False)  # Imported Data
    annual_leave_last_reco = fields.Date('Annual Leave Last Reconciliation', copy=False)  # Imported Data

    leave_history_ids = fields.One2many('hr.leave', 'employee_id', string="Allocated Leave",
                                        domain=[('state', '=', 'validate')])
    emp_salary_package_ids = fields.One2many('salary.packages', 'employee_id',
                                             domain="[('contract_id.state', '=', 'open')]")
    gross_salary = fields.Float(compute='compute_gross_salary')
    wages = fields.Monetary(related='contract_id.wage')
    joining_salary = fields.Float(compute='compute_joining_salary')
    visa_cost = fields.Float(string="Visa Cost", groups="hr.group_hr_user")
    clearance = fields.Many2one('hr.clearance.details', 'Clearance Detail', domain=_get_visa_clearance_domain,
                                groups="hr.group_hr_user")

    applicable_date = fields.Date(string="Resignation Date", readonly=True)
    travel_date = fields.Date(string="Travel Date", readonly=True, groups="hr.group_hr_user")
    first_contract_date = fields.Date(string="First Contract Date", groups="hr.group_hr_user")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    gratuity_amount = fields.Float(string="Gratuity Amount", compute='compute_gratuity_amount')
    unpaid_leaves = fields.Float(string='Total Unpaid Leaves', compute='compute_unpaid_leaves')

    religion = fields.Selection([('muslim', 'Muslim'), ('chris', 'Christian'), ('hindu', 'Hindu'),
                                 ('other', 'Others')], copy=False)
    traning_analysis_ids = fields.One2many('training.analysis', 'employee_id', string="Training Need Analysis")

    # notification checking fields
    visa_notify = fields.Boolean(string="Active Visa Notification", default=False)
    passport_notify = fields.Boolean(string="Active Passport Notification", default=False)
    civil_notify = fields.Boolean(string="Active Civil Card Notification", default=False)
    contract_notify = fields.Boolean(string="Active Contract Notification", default=False)

    annual_leave_notify = fields.Boolean(string="Annual Leave Notification", default=False)
    airticket_line_ids = fields.One2many('air.ticket.line', 'employee_id')
    airticket_count = fields.Integer(string="Air Ticket", compute="compute_airtickets")
    air_sector_id = fields.Many2one('air.sector', string='Air Sector')
    provision_grade_id = fields.Many2one('provision.grade', string='Provision Grade')

    # new fields
    employee_name_arabic = fields.Char(string='Name', help='Employee Name in Arabic')
    employee_job_arabic = fields.Char(string='Job Title (Arabic)', help='Employee Job position in Arabic')

    # Gratiuity Fields
    is_eligible_for_gratiuity = fields.Boolean(string='Eligible for Gratiuity', default=False,
                                               compute='_compute_gratiuity_eligible')
    last_gratiuity_encashed_date = fields.Date(string='Last Gratiuity Encashment Date',
                                               compute='_compute_last_enchashment_date')
    current_gratiuity_amount = fields.Monetary(string='Current Gratiuity Amount',
                                               compute='_compute_current_gratiuity_amount')

    @api.depends('employee_category')
    def _compute_current_gratiuity_amount(self):
        self.current_gratiuity_amount = False
        for rec in self:
            if rec.is_eligible_for_gratiuity:
                date_from = rec.joining_date
                if rec.last_gratiuity_encashed_date:
                    date_from = rec.last_gratiuity_encashed_date
                date_to = fields.Date.today()
                if date_from and date_to:
                    no_of_days = (date_to - date_from).days
                    year_days = 366 if calendar.isleap(fields.date.today().year) else 365
                    if no_of_days:
                        daily_rate = (rec.contract_id.wage * 12) / year_days
                        unpaid_leave_share = 0.0
                        total_unpaid_leaves = 0.0
                        holiday_type = self.env['hr.leave.type'].search([('is_unpaid', '=', True)], limit=1)
                        unpaid_leaves = self.env['hr.leave'].search([('holiday_status_id', '=', holiday_type.id),
                                                                     ('employee_id', '=', rec.id),
                                                                     ('date_from', '<=', date_to),
                                                                     ('date_to', '>=', date_from),
                                                                     ('state', '=', 'validate')])
                        for i in unpaid_leaves:
                            total_unpaid_leaves += i.number_of_days
                        total_working_days = no_of_days - total_unpaid_leaves
                        rec.current_gratiuity_amount = daily_rate * total_working_days

    @api.depends('employee_category')
    def _compute_last_enchashment_date(self):
        """ last gratiuity encashed date"""
        self.last_gratiuity_encashed_date = False
        for rec in self:
            gratiuity_date = self.env['hr.gratuity'].search([('employee_id', '=', rec.id), ('state', '=', 'approved')],
                                                            order='date DESC', limit=1)
            rec.last_gratiuity_encashed_date = gratiuity_date.date

    @api.depends('employee_category')
    def _compute_gratiuity_eligible(self):
        """ check employee is eligible for gratiuity"""
        self.is_eligible_for_gratiuity = False
        for rec in self:
            if rec.employee_category and rec.employee_category != 'domestic_servant':
                rec.is_eligible_for_gratiuity = True

    def compute_airtickets(self):
        for rec in self:
            airtickets = self.env['air.ticket.management'].search([('employee_id', '=', self.id)])
            rec.airticket_count = len(airtickets)

    def action_view_airtickets(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("atheer_hr.action_air_ticket")
        action['domain'] = [('employee_id', '=', self.id)]
        action['context'] = dict(self._context, create=False)
        return action

    @api.onchange('bank_account_id')
    def set_bank_branch(self):
        for rec in self:
            if rec.bank_account_id:
                rec.bank_branch = rec.bank_account_id.branch_name

    @api.onchange('ot_eligibility')
    def set_ot_eligibility(self):
        for rec in self:
            if rec.ot_eligibility:
                rec.ph_ot_eligibility = False

    @api.onchange('ph_ot_eligibility')
    def set_ph_ot_eligibility(self):
        for rec in self:
            if rec.ph_ot_eligibility:
                rec.ot_eligibility = False

    @api.depends('joining_date', 'emp_id', 'employee_category')
    def compute_eligible_annual_leaves(self):
        values = self
        for rec in values:
            result = rec.annual_leaves_count(emp_obj=rec)
            if result:
                rec.total_annual_leaves = result['total_annual_leaves']
                rec.eligible_annual_leaves = result['eligible_annual_leaves']
            else:
                rec.total_annual_leaves = 0
                rec.eligible_annual_leaves = 0

    @api.depends('joining_date')
    def compute_eligible_for_annual_leave(self):
        values = self
        self.annual_leave_eligibility(values)

    def cron_eligible_for_annual_leaves(self):
        employees = self.env['hr.employee'].search([])
        values = employees
        self.annual_leave_eligibility(values)

    def cron_eligible_annual_leaves(self):
        employees = self.env['hr.employee'].search([])
        values = employees
        for rec in values:
            result = rec.annual_leaves_count(emp_obj=rec)
            if result:
                rec.total_annual_leaves = result['total_annual_leaves']
                rec.eligible_annual_leaves = result['eligible_annual_leaves']
            else:
                rec.total_annual_leaves = 0
                rec.eligible_annual_leaves = 0

    @api.onchange('clearance')
    def onchange_clearance(self):
        if self.clearance:
            if self.clearance.balance > 0:
                self.clearance.used += 1
            else:
                warning = {
                    'title': 'Warning!',
                    'message': 'No Clearance Left'
                }
                return {'warning': warning, 'value': {'clearance': False}}

    def compute_unpaid_leaves(self):
        """Total Unpaid Leaves of the employee"""
        for record in self:
            total_unpaid_leaves = 0.0
            holiday_type = self.env['hr.leave.type'].search([('is_unpaid', '=', True)], limit=1)
            unpaid_leaves = self.env['hr.leave'].search([('holiday_status_id', '=', holiday_type.id),
                                                         ('employee_id', '=', record.id),
                                                         ('state', '=', 'validate')])
            for i in unpaid_leaves:
                total_unpaid_leaves += i.number_of_days
            record.unpaid_leaves = total_unpaid_leaves

    @api.depends('joining_date', 'applicable_date', 'contract_id')
    def compute_gratuity_amount(self):
        no_of_days = 0
        if self.joining_date and self.contract_id:
            if not self.applicable_date:
                current_date = fields.date.today()
                no_of_days = (current_date - self.joining_date)
            else:
                no_of_days = (self.applicable_date - self.joining_date)
            year_days = 366 if calendar.isleap(fields.date.today().year) else 365

            if no_of_days.days > 365:
                daily_rate = self.contract_id.wage / year_days
                unpaid_leave_share = 0.0
                if no_of_days.days <= 1095:
                    gratuity = (daily_rate / 2) * (no_of_days.days + 1)
                    if self.unpaid_leaves > 0:
                        unpaid_leave_share = (daily_rate / 2) * self.unpaid_leaves
                    self.gratuity_amount = gratuity - unpaid_leave_share
                else:
                    f_date = self.joining_date + timedelta(1095)
                    f_total_unpaid_leaves = 0.0
                    s_total_unpaid_leaves = 0.0
                    holidy_type = self.env['hr.leave.type'].search([('is_unpaid', '=', True)], limit=1)
                    f_unpaid_leaves = self.env['hr.leave'].search([('holiday_status_id', '=', holidy_type.id),
                                                                   ('employee_id', '=', self.id),
                                                                   ('state', '=', 'validate'),
                                                                   ('date_from', '<=', f_date),
                                                                   ('date_to', '>=', f_date)])
                    for i in f_unpaid_leaves:
                        f_total_unpaid_leaves += i.number_of_days
                    s_unpaid_leaves = self.env['hr.leave'].search([('holiday_status_id', '=', holidy_type.id),
                                                                   ('employee_id', '=', self.id),
                                                                   ('state', '=', 'validate'),
                                                                   ('date_from', '>=', f_date),
                                                                   ('date_to', '>=', f_date)])
                    for i in s_unpaid_leaves:
                        s_total_unpaid_leaves += i.number_of_days
                    f_unpaid_leave = f_total_unpaid_leaves
                    s_unpaid_leave = s_total_unpaid_leaves
                    gratuity = ((daily_rate / 2) * 1095) + (daily_rate * ((no_of_days.days + 1) - 1095))
                    f_gratuity = (daily_rate / 2) * f_unpaid_leave
                    s_gratuity = daily_rate * s_unpaid_leave
                    self.gratuity_amount = gratuity - f_gratuity - s_gratuity
            else:
                self.gratuity_amount = 0.0
        else:
            self.gratuity_amount = 0.0

    @api.depends('name', 'emp_id')
    def _compute_display_ename(self):
        for emp in self:
            result = ''
            if emp.name and emp.emp_id:
                result = str(emp.emp_id) + '-' + str(emp.name)
            emp.display_ename = result

    @api.onchange('visa_expire')
    def onchange_passport_expiry(self):
        for rec in self:
            if not rec.civil_card_expire_date:
                rec.civil_card_expire_date = rec.visa_expire

    @api.onchange('civil_card_expire_date')
    def onchange_civil_card_expire_date(self):
        for rec in self:
            if not rec.visa_expire:
                rec.visa_expire = rec.civil_card_expire_date

    @api.onchange('employee_category')
    def compute_joining_salary(self):
        for rec in self:
            if rec.contract_id:
                rec.joining_salary = rec.contract_id.gross_salary
            else:
                rec.joining_salary = 0

    def compute_gross_salary(self):
        result = 0
        for rec in self.emp_salary_package_ids:
            result += rec.amount_per_month
        self.gross_salary = result

    def _check_dates(self, record, year):
        days_count = 0
        start_date = record.request_date_from
        end_date = record.request_date_to
        delta_days = end_date - start_date
        for i in range(delta_days.days + 1):
            day = start_date + timedelta(days=i)
            if day.year == year:
                days_count += 1
        return days_count

    def gratuity_days(self, emp_obj, last_date, joining_date):
        difference_in_year = last_date.year - joining_date.year + 1
        gratuity_days1 = 0
        gratuity_days2 = 0
        gratuity_amount1 = 0
        gratuity_amount2 = 0
        basic_pay = emp_obj.contract_id.wage
        first_three_year_date = joining_date + relativedelta(years=3)
        first_three_year_days = (first_three_year_date - joining_date).days
        total_days = (last_date - joining_date + relativedelta(days=1)).days
        unpaid_leave = self.onchange_no_unpaid_from_joining(emp_obj)
        total_days_after_unpaid = total_days - unpaid_leave['no_of_up_taken_from_joining']
        # calculation in 3 years
        if difference_in_year > 3:
            gratuity_days1 = (first_three_year_days * 15) / 365
            gratuity_amount1 = (basic_pay * first_three_year_days) / 730
        if difference_in_year <= 3:
            total_days_after_unpaid_in_three_year = total_days - unpaid_leave['no_of_up_taken_from_joining']
            gratuity_days1 = (total_days_after_unpaid_in_three_year * 15) / 365
            gratuity_amount1 = (basic_pay * total_days_after_unpaid_in_three_year) / 730
        # calculation after 3 years
        if difference_in_year > 3:
            remaining_year_days = (total_days_after_unpaid - first_three_year_days)
            gratuity_days2 = (remaining_year_days * 30) / 365
            gratuity_amount2 = (basic_pay * remaining_year_days) / 365

        eligible_gratuity_days = gratuity_days1 + gratuity_days2
        gratuity_amount = gratuity_amount1 + gratuity_amount2
        return {'eligible_gratuity_days': eligible_gratuity_days, 'gratuity_amount': gratuity_amount}

    def onchange_no_unpaid_from_joining(self, emp_ob):
        no_of_up_taken_from_joining = 0
        all_unpaid_leaves = self.env['hr.leave'].search(
            [('employee_id', '=', emp_ob.id),
             ('holiday_status_id.is_unpaid', '=', True),
             ('state', '=', 'validate')])
        unpaid = 0
        if all_unpaid_leaves:
            no_of_up_taken_from_joining = sum(all_unpaid_leaves.mapped('number_of_days'))
        no_of_up_taken_from_joining = no_of_up_taken_from_joining + unpaid
        return {'no_of_up_taken_from_joining': no_of_up_taken_from_joining}

    def annual_leaves_count(self, emp_obj, to_date=date.today()):
        if not emp_obj.joining_date:
            return {'total_annual_leaves': 0, 'eligible_annual_leaves': 0}
        annual_leave_calc_rate = self.env['ir.config_parameter'].sudo().get_param('atheer_hr.annual_leave_calc_rate')
        annual_leave_type = self.env['ir.config_parameter'].sudo().get_param('atheer_hr.annual_leave_type')
        if emp_obj.annual_leave_last_reco:
            last_reco = to_date - fields.Date.from_string(emp_obj.annual_leave_last_reco)
        else:
            last_reco = to_date - fields.Date.from_string(emp_obj.joining_date)
        annual_leaves = self.env['hr.leave'].search([('holiday_status_id', '=', int(annual_leave_type)),
                                                     ('employee_id', '=', emp_obj.id),
                                                     ('state', '=', 'validate')])
        total_taken_leaves = 0.0
        for i in annual_leaves:
            total_taken_leaves += i.number_of_days
        total_annual_leaves = emp_obj.open_blnc + (float(last_reco.days) * float(annual_leave_calc_rate))
        eligible_annual_leaves = total_annual_leaves - total_taken_leaves
        return {'total_annual_leaves': total_annual_leaves, 'eligible_annual_leaves': eligible_annual_leaves}

    # @api.onchange('annual_leave_last_reco', 'open_blnc')
    def annual_leave_update(self):
        if not self.joining_date:
            return
        annual_leave_calc_rate = self.env['ir.config_parameter'].sudo().get_param('atheer_hr.annual_leave_calc_rate')
        annual_leave_type = self.env['ir.config_parameter'].sudo().get_param('atheer_hr.annual_leave_type')
        current_date = fields.Date.today()
        if self.annual_leave_last_reco:
            last_reco = current_date - fields.Date.from_string(self.annual_leave_last_reco)
        else:
            last_reco = current_date - fields.Date.from_string(self.joining_date)
        annual_leaves = self.env['hr.leave'].search([('holiday_status_id', '=', int(annual_leave_type)),
                                                     ('employee_id', '=', self.id),
                                                     ('state', '=', 'validate')])
        total_annual_leaves = 0.0
        for i in annual_leaves:
            total_annual_leaves += i.number_of_days
        allocated_days = self.open_blnc + (float(last_reco.days) * float(annual_leave_calc_rate)) - total_annual_leaves
        if allocated_days > 0:
            annual_leave_alloc = self.env['hr.leave.allocation'].search([('employee_id', '=', self.id),
                                                                         ('holiday_status_id', '=',
                                                                          int(annual_leave_type))],
                                                                        limit=1)
            if not annual_leave_alloc:
                query = " INSERT INTO hr_leave_allocation (private_name,state,number_of_days,allocation_type,\
                     holiday_type, employee_id, holiday_status_id, date_from, create_date, create_uid, active) VALUES (\
                     '{name}','{state}',{eligible_days}, '{allocation_type}', '{h_type}', {emp_id}, {h_status_id}, '{date_from}', '{c_d}', {c_u}, {active})\
                ".format(name="Annual Leave Allocation", state=str("validate"),
                         eligible_days=allocated_days,
                         allocation_type="regular", h_type="employee", emp_id=self.id,
                         h_status_id=annual_leave_type, h_status_id_1=annual_leave_type,
                         date_from=self.joining_date,
                         c_d=str(datetime.today()), c_u=1, active=True)
                self._cr.execute(query)
            else:
                annual_leave_alloc.number_of_days = allocated_days

    @api.model
    def annual_leave_cron(self):
        for record in self.search([]):
            record.annual_leave_update()

    def notify_employee_annual_leave(self):
        """Notify employee annual leave balance exceeds 60"""
        employee_ids = self.env['hr.employee'].search([('annual_leave_notify', '!=', True)])
        for emp in employee_ids:
            if emp.eligible_annual_leaves > 60:
                responsible_users = self.sudo().env.ref('atheer_hr.group_hr_manager').users
                note = _('%(emp_name)s annual leave balance exceeds 60 days !',
                         emp_name=emp.name)
                summary = _('Excessive annual leave')
                if responsible_users:
                    for responsible_user in responsible_users:
                        emp.activity_schedule('mail.mail_activity_data_warning', note=note,
                                              user_id=responsible_user.id, summary=summary,
                                              excess_annual_leave=True)
                    emp.update({'annual_leave_notify': True})

    def notify_employee_doc_expiry(self):
        """notify expiring employee documents (visa, civil card, contract) :cron job calling"""

        def get_notification_checking_dates(notification_ids):
            if notification_ids:
                notify_dates = []
                for notification in notification_ids:
                    if notification.period == 'days':
                        future_date = date_today + relativedelta(days=notification.duration)
                    else:
                        future_date = date_today + relativedelta(months=notification.duration)
                    notify_dates.append(future_date)
                if notify_dates:
                    notify_dates = list(set(notify_dates))
                return notify_dates
            else:
                return []

        employee_ids = self.env['hr.employee'].search([])
        date_today = date.today()
        with_user = self.env['ir.config_parameter'].sudo()
        notify_obj = self.env['notification.duration']
        visa_notify_dates = []
        passport_notify_dates = []
        civil_notify_dates = []
        contract_notify_dates = []
        doc_notify_dates = []
        visa_notification = with_user.get_param('atheer_hr.visa_notification')
        passport_notification = with_user.get_param('atheer_hr.passport_notification')
        civil_notification = with_user.get_param('atheer_hr.civil_notification')
        contract_notification = with_user.get_param('atheer_hr.contract_notification')
        doc_notification = with_user.get_param('atheer_hr.doc_notification')
        visa_notification_ids = notify_obj.browse(ast.literal_eval(visa_notification)) \
            if visa_notification else False
        passport_notification_ids = notify_obj.browse(ast.literal_eval(passport_notification)) \
            if passport_notification else False
        civil_notification_ids = notify_obj.browse(ast.literal_eval(civil_notification)) \
            if civil_notification else False
        contract_notification_ids = notify_obj.browse(ast.literal_eval(contract_notification)) \
            if contract_notification else False
        doc_notification_ids = notify_obj.browse(ast.literal_eval(doc_notification)) \
            if doc_notification else False
        if visa_notification_ids:
            visa_notify_dates = get_notification_checking_dates(visa_notification_ids)
        if passport_notification_ids:
            passport_notify_dates = get_notification_checking_dates(passport_notification_ids)
        if civil_notification_ids:
            civil_notify_dates = get_notification_checking_dates(civil_notification_ids)
        if contract_notification_ids:
            contract_notify_dates = get_notification_checking_dates(contract_notification_ids)
        if doc_notification_ids:
            doc_notify_dates = get_notification_checking_dates(doc_notification_ids)
        for emp in employee_ids:
            visa_expiry = emp.visa_expire
            passport_expiry = emp.passport_expiry_date
            civil_card_expiry = emp.civil_card_expire_date
            contract_expiry = emp.contract_id.date_end if emp.contract_id else False
            if visa_notify_dates and visa_expiry and not emp.visa_notify:
                for notify_date in visa_notify_dates:
                    if visa_expiry <= date_today:
                        emp.schedule_notification_activity(notify_doc='visa', status='expired',
                                                           expiry_date=visa_expiry)
                        break
                    elif notify_date >= visa_expiry:
                        emp.schedule_notification_activity(notify_doc='visa', status='to_expire',
                                                           expiry_date=visa_expiry)
                        break
            if passport_notify_dates and passport_expiry and not emp.passport_notify:
                for notify_date in passport_notify_dates:
                    if passport_expiry <= date_today:
                        emp.schedule_notification_activity(notify_doc='passport', status='expired',
                                                           expiry_date=passport_expiry)
                        break
                    elif notify_date >= passport_expiry:
                        emp.schedule_notification_activity(notify_doc='passport', status='to_expire',
                                                           expiry_date=passport_expiry)
                        break
            if civil_notify_dates and civil_card_expiry and not emp.civil_notify:
                for notify_date in civil_notify_dates:
                    if civil_card_expiry <= date_today:
                        emp.schedule_notification_activity(notify_doc='civil', status='expired',
                                                           expiry_date=civil_card_expiry)
                        break
                    elif notify_date >= civil_card_expiry:
                        emp.schedule_notification_activity(notify_doc='civil', status='to_expire',
                                                           expiry_date=civil_card_expiry)
                        break
            if contract_notify_dates and contract_expiry and not emp.contract_notify:
                for notify_date in contract_notify_dates:
                    if contract_expiry <= date_today:
                        emp.schedule_notification_activity(notify_doc='contract', status='expired',
                                                           expiry_date=contract_expiry)
                        break
                    elif notify_date >= contract_expiry:
                        emp.schedule_notification_activity(notify_doc='contract', status='to_expire',
                                                           expiry_date=contract_expiry)
                        break
            # Documents Expiry checking
            if doc_notify_dates:
                for emp_doc in emp.employee_docs:
                    print(emp_doc.name, emp_doc.exp_date, emp_doc.doc_notify)
                    if emp_doc.exp_date and not emp_doc.doc_notify:
                        if emp_doc.exp_date <= date_today:
                            emp.schedule_notification_activity(notify_doc='doc', status='expired',
                                                               expiry_date=emp_doc.exp_date, doc_id=emp_doc)
                        else:
                            for notify_date in doc_notify_dates:
                                if notify_date >= emp_doc.exp_date:
                                    emp.schedule_notification_activity(notify_doc='doc', status='to_expire',
                                                                       expiry_date=emp_doc.exp_date, doc_id=emp_doc)
                                    break

    def schedule_notification_activity(self, notify_doc, status, expiry_date, doc_id=False):
        for rec in self:
            if notify_doc == 'visa':
                doc_name = 'Visa'
            elif notify_doc == 'passport':
                doc_name = 'Passport'
            elif notify_doc == 'civil':
                doc_name = 'Civil Id'
            elif notify_doc == 'contract':
                doc_name = 'Contract'
            else:
                doc_name = 'Document'
            if status == 'to_expire':
                doc_status = 'will expire'
            else:
                doc_status = 'is expired'
            if doc_id:
                doc_desc = '%s (%s)' % (doc_id.name.name, doc_id.doc_id)
            else:
                doc_desc = ''
            responsible_users = self.sudo().env.ref('atheer_hr.group_hr_manager').users
            note = _('%(emp_name)s %(doc_name)s %(doc_desc)s %(doc_status)s on %(expiry_date)s',
                     emp_name=rec.name, doc_name=doc_name, doc_desc=doc_desc,
                     doc_status=doc_status, expiry_date=expiry_date)
            summary = _('%(doc_name)s %(doc_status)s', doc_name=doc_name, doc_status=doc_status)
            if responsible_users:
                for responsible_user in responsible_users:
                    rec.activity_schedule('atheer_hr.mail_act_employee_doc_expiry', note=note,
                                          user_id=responsible_user.id, date_deadline=expiry_date, summary=summary,
                                          emp_doc_type=notify_doc, doc_id=doc_id.id if doc_id else False)
                if doc_id:
                    doc_id.update({notify_doc + '_notify': True})
                else:
                    rec.update({notify_doc + '_notify': True})

    @api.onchange('birthday')
    def _onchange_dob(self):
        """set Age based on DOB"""
        for res in self:
            if res.birthday:
                today = date.today()
                res.age = today.year - res.birthday.year - (
                        (today.month, today.day) < (res.birthday.month, res.birthday.day))

    def name_get(self):
        res = []
        for each in self:
            if each.emp_id:
                res.append((each.id, str(each.emp_id) + '-' + str(each.name)))
            else:
                res.append((each.id, str(each.name)))
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('emp_id', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    @api.model
    def create(self, vals):
        """
        Adding new user to line manager group when creating the employee
        """
        # if not vals.get('employee_id', False):
        company_id = vals.get('company_id')
        company = self.env['res.company'].browse(company_id)
        print(company_id)
        sequence = self.env['ir.sequence'].next_by_code('hr.employee.code')
        if not sequence:
            raise ValidationError(
                _('The employee code sequence not set under the {company} company, Please contact Administrator.').format(
                    company=company.name))

        vals['emp_id'] = sequence.lstrip('0')
        if vals.get('name', False) and vals.get('employee', False):
            vals['employee'] = vals['emp_id'] + '-' + vals['name']
        res = super(HrEmployee, self).create(vals)
        # Leave allocation
        if (res.gender is not False) or (res.religion is not False):
            self.env['hr.leave.allocation'].allocate_leaves(employee=res)
        # Annual leave allocation
        res.annual_leave_update()
        return res


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    emp_id = fields.Char(string="Employee ID", related='employee_id.name', compute_sudo=True)
    display_ename = fields.Char(string="Full Name")
    emp_check = fields.Boolean(default=True)
    age = fields.Char(string="Age", readonly="True")
    is_omani = fields.Selection([('omani', 'Omani'), ('expat', 'Expat')], default='expat')
    pasi_no = fields.Char(string="PASI No", groups="hr.group_hr_user")
    joining_date = fields.Date(string="Joining Date")
    site_joining_date = fields.Date(string="Site Joining Date")
    employee_category = fields.Selection([
        ('omani_staff', 'Omani Staff'),
        ('omani_labor', 'Omani Labor'),
        ('expat_staff', 'Expat Staff'),
        ('expat_labor', 'Expat Labor'),
        ('domestic_servant', 'Domestic Servant'),
    ], string='Employee Category', copy=False, index=True)
    employee_status = fields.Selection([
        ('active', 'Active'),
        ('resigned', 'Resigned'),
    ], string='Employee Status', copy=False, default="active", index=True)
    applicable_date = fields.Date(string="Resignation Date", readonly=True)
    religion = fields.Selection([('muslim', 'Muslim'), ('chris', 'Christian'), ('hindu', 'Hindu'),
                                 ('other', 'Others')], copy=False)

    is_eligible_for_annual_leave = fields.Boolean(string="Eligible for Annual Leave", default=True)
    open_blnc = fields.Float('Opening Balance(Annual Leave)', copy=False)  # Imported Data
    annual_leave_last_reco = fields.Date('Annual Leave Last Reconciliation', copy=False)  # Imported Data

    ot_eligibility = fields.Boolean(string="OT Eligibility")
    ph_ot_eligibility = fields.Boolean(string="Public Holiday OT Eligibility")

    # notification checking fields
    visa_notify = fields.Boolean(string="Active Visa Notification", default=False)
    passport_notify = fields.Boolean(string="Active Passport Notification", default=False)
    civil_notify = fields.Boolean(string="Active Civil Card Notification", default=False)
    contract_notify = fields.Boolean(string="Active Contract Notification", default=False)

    annual_leave_notify = fields.Boolean(string="Annual Leave Notification", default=False)
    visa_company_id = fields.Many2one('res.company', string='Visa Company', related='employee_id.visa_company_id',
                                      compute_sudo=True, copy=False)
    mess_facility = fields.Selection([('no', 'No'), ('yes', 'Yes')], default='no',
                                     related='employee_id.mess_facility',
                                     compute_sudo=True, help='To Identify this employee have Mess facility', )
    blood_group_id = fields.Many2one('emp.blood.groups', string='Blood Group', related='employee_id.blood_group_id',
                                     compute_sudo=True, )
    air_sector_id = fields.Many2one('air.sector', string='Air Sector', related='employee_id.air_sector_id',
                                    compute_sudo=True, )
    provision_grade_id = fields.Many2one('provision.grade', string='Provision Grade',
                                         related='employee_id.provision_grade_id', compute_sudo=True, )
    employee_name_arabic = fields.Char(string='Name', help='Employee Name in Arabic',
                                       related='employee_id.employee_name_arabic', compute_sudo=True, )
    employee_job_arabic = fields.Char(string='Job Title (Arabic)', help='Employee Job position in Arabic',
                                      related='employee_id.employee_job_arabic', compute_sudo=True, )


class AirTicketLine(models.Model):
    _name = 'air.ticket.line'
    _description = "Air Ticket Line"
    _rec_name = 'relative_id'

    employee_id = fields.Many2one('hr.employee')
    relative_id = fields.Many2one('hr.employee.relative', domain="[('employee_id', '=', employee_id)]", string="Name")
    relation_id = fields.Many2one("hr.employee.relative.relation", related="relative_id.relation_id")
    start_date = fields.Date(string="Eligibility Start Date", related='employee_id.joining_date')
    end_date = fields.Date(string="Eligibility End Date")
    ticket_qty = fields.Integer(string="Ticket Qty")
    amount_per_ticket = fields.Integer(string='Maximum Amount Per Ticket')
    no_of_ticket = fields.Integer(string='No of Tickets Taken', compute='_compute_tickets')

    @api.depends('employee_id')
    def _compute_tickets(self):
        self.no_of_ticket = False
        for rec in self:
            rec.no_of_ticket = self.env['air.ticket.management'].search_count(
                [('employee_id', '=', rec.employee_id.id), ('state', '=', 'approved')])


class TrainingAnalysis(models.Model):
    _name = 'training.analysis'
    _description = "Training Analysis"

    course_title = fields.Many2one('employee.course.master', string="Course Title")
    date_taken = fields.Date(string="Date Taken")
    date_expiry = fields.Date(string="Expiry Date")
    employee_id = fields.Many2one('hr.employee', string="Employee")


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    current_leave_state = fields.Selection(
        selection=[('draft', 'Employee'), ('draft2', 'Site Engineer'), ('confirm', 'Line Manager'),
                   ('refuse', 'Refused'), ('validate1', 'HR Manager'), ('ceo', 'CEO'), ('approved', 'Approved'),
                   ('validate', 'Leave Confirmed'), ('cancel', 'Cancelled')],
        compute='_compute_leave_status', string="Current Time Off Status")


class HolidaysSummaryEmployee(models.AbstractModel):
    _inherit = 'report.hr_holidays.report_holidayssummary'

    def _get_leaves_summary(self, start_date, empid, holiday_type):
        res = []
        count = 0
        start_date = fields.Date.from_string(start_date)
        end_date = start_date + relativedelta(days=59)
        for index in range(0, 60):
            current = start_date + timedelta(index)
            res.append({'day': current.day, 'color': ''})
            if self._date_is_day_off(current):
                res[index]['color'] = '#ababab'
        # count and get leave summary details.
        holiday_type = ['approved', 'validate'] if holiday_type == 'both' else [
            'approved'] if holiday_type == 'Approved' else ['validate']

        holidays = self.env['hr.leave'].search([
            ('employee_id', '=', empid), ('state', 'in', holiday_type),
            ('date_from', '<=', str(end_date)),
            ('date_to', '>=', str(start_date))
        ])
        for holiday in holidays:
            # Convert date to user timezone, otherwise the report will not be consistent with the
            # value displayed in the interface.
            date_from = fields.Datetime.from_string(holiday.date_from)
            date_from = fields.Datetime.context_timestamp(holiday, date_from).date()
            date_to = fields.Datetime.from_string(holiday.date_to)
            date_to = fields.Datetime.context_timestamp(holiday, date_to).date()
            for index in range(0, ((date_to - date_from).days + 1)):
                if date_from >= start_date and date_from <= end_date:
                    res[(date_from - start_date).days]['color'] = holiday.holiday_status_id.color_name
                date_from += timedelta(1)
            count += holiday.number_of_days
        employee = self.env['hr.employee'].browse(empid)
        return {'emp': employee.name, 'display': res, 'sum': count}


# Overtime
class HrAttendanceOvertime(models.Model):
    _inherit = 'hr.attendance.overtime'

    @api.depends('employee_id', 'date')
    def get_ot_day_type(self):
        for rec in self:
            ot_day_type = 'normal'
            if rec.employee_id and rec.date:
                sheet_week_day = rec.date.weekday()
                time_schedule = rec.employee_id.resource_calendar_id
                if time_schedule.two_weeks_calendar:
                    week_type = self.env['resource.calendar.attendance'].get_week_type(rec.date)
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
                     ('date_from', '>=', rec.date),
                     ('date_to', '<=', rec.date)])
                if holidays:
                    ot_day_type = 'ph'
                else:
                    if schedule_attendance and schedule_attendance.is_weekend:
                        ot_day_type = 'weekend'
                    else:
                        ot_day_type = 'normal'
            rec.ot_day_type = ot_day_type

    ot_day_type = fields.Selection([('normal', 'Normal OT'),
                                    ('weekend', 'Weekend OT'),
                                    ('ph', 'Public Holiday OT')],
                                   default='normal', compute=get_ot_day_type)


# Air Sector

class AirSector(models.Model):
    _name = 'air.sector'
    _description = 'Air Sector'
    _rec_name = 'air_sector_seq'

    air_sector_seq = fields.Char(string='Sequence', copy=False,
                                 readonly=True, help="Sequence for Air Sector",
                                 index=True, default=lambda self: _('New'))
    name = fields.Char(string='Air Sector')
    from_destination = fields.Char(string='From ')
    to_destination = fields.Char(string='To ')
    full_fare = fields.Char(string='Full Fare')
    employee_id = fields.Many2one('hr.employee', string='Employee')

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('air_sector_seq', 'New') == 'New':
                vals['air_sector_seq'] = self.env['ir.sequence'].next_by_code(
                    'airsector.sequence') or 'New'
        return super(AirSector, self).create(vals_list)


class ProvisionGrade(models.Model):
    _name = 'provision.grade'
    _description = 'Provision Grade'
    _rec_name = 'grade_seq'

    grade_seq = fields.Char(string='Sequence', copy=False,
                            readonly=True, help="Sequence for Provision Grade",
                            index=True, default=lambda self: _('New'))
    name = fields.Char(string='Provision Grade')

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('grade_seq', 'New') == 'New':
                vals['grade_seq'] = self.env['ir.sequence'].next_by_code(
                    'provision.grade.sequence') or 'New'
        return super(ProvisionGrade, self).create(vals_list)


class EmployeeChecklist(models.Model):
    _name = 'employee.checklist'
    _description = 'Employee Checklist'

    checklist_seq = fields.Char(string='Sequence', copy=False,
                                readonly=True, help="Sequence for Checklist",
                                index=True, default=lambda self: _('New'))
    name = fields.Char(string='Checklist')

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('checklist_seq', 'New') == 'New':
                vals['checklist_seq'] = self.env['ir.sequence'].next_by_code(
                    'checklist.sequence') or 'New'
        return super(EmployeeChecklist, self).create(vals_list)
