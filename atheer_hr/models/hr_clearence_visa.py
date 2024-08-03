# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrClearanceRequest(models.Model):
    _name = 'hr.clearance.request'
    _description = 'HR Clearance Request'
    _inherit = ['mail.thread']
    _order = 'id DESC'

    @api.depends('clearance_lines')
    def get_balance(self):
        for record in self:
            total_issue = 0
            total_used = 0
            total_granded = 0
            for i in record.clearance_lines:
                total_issue += i.total
                total_used += i.used
                total_granded += i.total_issued
            record.total = total_granded
            record.used = total_used
            record.total_issued = total_issue
            record.balance = total_issue - total_used

    name = fields.Char(string='Reference', required=True, default='/')
    date_issue = fields.Date(string='Request Date', required=True, default=fields.date.today())
    clearance_lines = fields.One2many(comodel_name='hr.clearance.details', inverse_name='hr_clearance_request',
                                      string='Clearance Lines', copy=False)
    clearance_lines2 = fields.One2many(comodel_name='hr.clearance.details', inverse_name='hr_clearance_request',
                                       string='Clearance Lines', copy=False)
    total = fields.Integer(string='Total Request', compute='get_balance')
    used = fields.Integer(string='Total Used', compute='get_balance')
    balance = fields.Integer(string='Balance', compute='get_balance')
    total_issued = fields.Integer(string='No of Granted Workers', compute='get_balance')
    state = fields.Selection([('draft', 'Draft'),
                              ('hr', 'HR Head'),
                              ('pr', 'PR Section'),
                              ('done', 'Done')], string='Status', copy=False, default='draft',
                             tracking=True)

    def sent_forward(self):
        """
        this will forward the record to next level
        if sequence is not generated we will generate the same at draft level. otherwise just send to HR Head
        """
        for record in self:
            if record.state == 'draft':
                if record.name == '/':
                    record.write({'name': self.env['ir.sequence'].get('CLR') or '/'})
                if not record.clearance_lines:
                    raise UserError('Please add clearance details!')
                record.write({'state': 'hr'})
            elif record.state == 'hr':
                record.write({'state': 'pr'})
            elif record.state == 'pr':
                record.write({'state': 'done'})


class HrClearance(models.Model):
    _name = 'hr.clearance'
    _description = 'HR Clearance'
    _inherit = ['mail.thread']
    _order = 'id DESC'

    @api.depends('clearance_lines')
    def get_balance(self):
        for rec in self:
            total_issue = 0
            total_used = 0
            total_issued = 0
            for line in rec.clearance_lines:
                total_issue += line.total
                total_used += line.visa_total
                total_issued += line.total_issued
            rec.total = total_issue
            rec.used = total_used
            rec.total_issued = total_issued
            rec.balance = total_issue - total_used

    name = fields.Char(string='Clearance No.', required=True)
    date_issue = fields.Date(string='Issued Date', required=True)
    date_expiry = fields.Date(string='Expiry Date', required=True)
    clearance_lines = fields.One2many(comodel_name='hr.clearance.details', inverse_name='hr_clearance',
                                      string='Clearance Lines')
    total = fields.Integer(string='Total Issued', compute='get_balance')
    total_issued = fields.Integer(string='No of Granted Workers', compute='get_balance')
    used = fields.Integer(string='Visa Applied', compute='get_balance')
    balance = fields.Integer(string='Balance', compute='get_balance')
    work_permit_duration = fields.Char(string='Work Permit Duration', copy=False)
    labour_office = fields.Char(string='Labour Office')
    employees_count = fields.Float(string='Employees Count', compute='_compute_employee_count')
    visa_applications = fields.Float(string='Visa Application', compute='_compute_employee_count')

    def _compute_employee_count(self):
        """get the count of the employees whose salary is not processed"""
        for record in self:
            record.employees_count = len(self.env['hr.employee'].search([('clearance', '=', record.id)]))
            record.visa_applications = len(self.env['hr.visa.request'].search([('clearance_id', '=', record.id)]))

    def action_employee_list(self):
        """ This opens the xml view specified in xml_id for the employees """
        if self.employees_count:
            e_ids = [emp.id for emp in self.env['hr.employee'].search([('clearance', '=', self.id)])]
            tree_id = self.env.ref('hr.view_employee_tree').id
            return {
                'type': 'ir.actions.act_window',
                'name': _('Employee'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.employee',
                'domain': str([('id', 'in', tuple(e_ids))]),
                'views': [(tree_id, 'tree')],
            }

        return False

    def action_visa_request(self):
        """ This opens the xml view specified in xml_id for the employees """
        tree_id = self.env.ref('atheer_hr.view_hr_visa_tree').id
        form_id = self.env.ref('atheer_hr.view_hr_visa_form').id
        if self.visa_applications:
            e_ids = [emp.id for emp in self.env['hr.visa.request'].search([('clearance_id', '=', self.id)])]
            return {
                'type': 'ir.actions.act_window',
                'name': _('Visa Details'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.visa.request',
                'domain': str([('id', 'in', tuple(e_ids))]),
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'context': {
                    'default_clearance_id': self.id,
                }
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Visa Details'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.visa.request',
            'domain': str([('id', 'in', ())]),
            'views': [(tree_id, 'tree'), (form_id, 'form')],
            'context': {
                'default_clearance_id': self.id,
            }
        }


class HrClearanceDetails(models.Model):
    _name = 'hr.clearance.details'
    _description = 'HR Clearance Details'
    _inherit = ['mail.thread']

    def name_get(self):
        res = []
        for each in self:
            res.append((each.id, str(each.hr_clearance.name) + '-' + each.job_id))
        return res

    @api.depends('employees')
    def get_used(self):
        for record in self:
            total = 0
            for i in record.employees:
                total += 1
            record.used = total

    @api.depends('total', 'used', 'employees')
    def get_balance(self):
        for record in self:
            total = 0
            for i in record.employees:
                total += 1
            record.balance = record.total - total

    hr_clearance = fields.Many2one(comodel_name='hr.clearance', string='Clearance No.')
    hr_clearance_request = fields.Many2one(comodel_name='hr.clearance.request', string='Clearance Request',
                                           ondelete='cascade')
    date_issue = fields.Date(string='Issued Date', related='hr_clearance.date_issue')
    date_expiry = fields.Date(string='Expiry Date', related='hr_clearance.date_expiry')
    job_code = fields.Char(string='Occupation Code', required=True)
    job_id = fields.Char(string='Occupation Name')
    division = fields.Many2one(comodel_name='hr.department', string='Division')
    total = fields.Integer(string='No of Granted Workers')
    total_issued = fields.Integer(string='Total Request', copy=False)
    visa_total = fields.Integer(string='Total Visa', copy=False)
    visa_progress = fields.Integer(string='Visa Under Progress', copy=False)
    used = fields.Integer(string='Total Used', compute='get_used')
    balance = fields.Integer(string='Balance', compute='get_balance')
    gender = fields.Selection([('m', 'Male'),
                               ('f', 'Female'),
                               ('t', 'Transgender')], string='Gender', copy=False, default='m')
    employees = fields.One2many(comodel_name='hr.employee', inverse_name='clearance', string='Employee Details',
                                copy=False)
    state = fields.Selection([('draft', 'Draft'),
                              ('hr', 'HR Head'),
                              ('pr', 'PR Section'),
                              ('done', 'Done')], string='Status', copy=False)

    def create_visa_request(self):
        """

        :return:
        """
        view_id = self.env.ref('atheer_hr.view_hr_visa_form').id

        if self.visa_total >= self.total:
            raise UserError('You cannot request more visa!')

        return {
            'name': _("Visa Request"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'views': [(view_id, 'form')],
            'res_model': 'hr.visa.request',
            'res_id': False,
            'type': 'ir.actions.act_window',
            'nodestroy': False,
            'target': 'new',
            'domain': '[]',
            'context': {
                'default_clearance_id': self.hr_clearance.id,
                'default_clearance_details_id': self.id,
                'default_job_code': self.job_code,
                'default_job_id': self.job_id,
                'default_division': self.division.id,
            }
        }


class HrVisaRequest(models.Model):
    _name = 'hr.visa.request'
    _description = 'HR Visa Request'
    _inherit = ['mail.thread']
    _order = 'id DESC'

    def get_balance(self):
        total_issue = 0
        total_used = 0
        total_granded = 0
        # for i in self.clearance_lines:
        #     total_issue += i.total
        #     total_used += i.used
        #     total_granded += i.total_issued
        self.total = total_issue
        self.used = total_used
        self.total_issued = total_granded
        self.balance = total_issue - total_used

    name = fields.Char(string='Reference', required=True, default='/')
    date_issue = fields.Date(string='Request Date', required=True, default=fields.date.today())
    job_code = fields.Char(string='Occupation Code', required=True)
    job_id = fields.Char(string='Occupation Name')
    division = fields.Many2one(comodel_name='hr.department', string='Division')
    passport_no = fields.Char(string='Passport No', copy=False, required=True)
    p_expiry = fields.Date(string='Passport Expiry', copy=False, required=True)
    p_issue_date = fields.Date(string='Passport Issue Date', copy=False, required=True)
    nationality = fields.Many2one(comodel_name='res.country', string='Nationality')
    dob = fields.Date(string='Date of Birth')
    p_name = fields.Char(string='Name', copy=False, required=True)
    clearance_request_id = fields.Many2one(comodel_name='hr.clearance.request', string='Clearance', copy=False)
    clearance_id = fields.Many2one(comodel_name='hr.clearance', string='Clearance', copy=False, required=True)
    clearance_details_id = fields.Many2one(comodel_name='hr.clearance.details', string='Clearance Details', copy=False)
    # manpower_id = fields.Many2one(comodel_name='hr.manpower', string='Manpower Request', copy=False)
    total = fields.Integer(string='Total Request', compute='get_balance', store=True)
    used = fields.Integer(string='Total Used', compute='get_balance', store=True)
    balance = fields.Integer(string='Balance', compute='get_balance', store=True)
    total_issued = fields.Integer(string='No of Granted Workers', compute='get_balance', store=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('hr', 'HR Head'),
                              ('pr', 'PR Section'),
                              ('done', 'Done')], string='Status', copy=False, default='draft',
                             tracking=True)
    job_ids = fields.Many2one(comodel_name='hr.job', string='Job Title', copy=False)
    visa_number = fields.Char(string='Visa Number')
    visa_issue_dt = fields.Date(string='Visa Issue Date')

    @api.onchange('p_expiry')
    @api.constrains('p_expiry')
    def onchange_p_expiry(self):
        """Expiry date must be greater than Issue date"""

        for record in self:
            if record.p_expiry and record.p_issue_date:
                if record.p_expiry <= record.p_issue_date:
                    raise UserError('Expiry date of the passport must be greater than Issue date')

    def sent_forward(self):
        """
        this will forward the record to next level
        if sequence is not generated we will generate the same at draft level. otherwise just send forward
        """
        for record in self:
            if record.state == 'draft':
                if record.name == '/':
                    record.write({'name': self.env['ir.sequence'].get('VR') or '/'})
                if record.clearance_details_id and record.clearance_details_id.visa_total > record.clearance_details_id.total:
                    raise UserError('You cannot request more visa!')
                else:
                    record.clearance_details_id.visa_total = record.clearance_details_id.visa_total + 1
                record.write({'state': 'hr'})
            elif record.state == 'hr':
                record.write({'state': 'pr'})
            elif record.state == 'pr':
                record.write({'state': 'done'})

    def sent_backward(self):
        for record in self:
            if record.state == 'hr':
                for rec in record.clearance_id.clearance_lines:
                    if record.clearance_details_id.id == rec.id:
                        rec.visa_total = rec.visa_total - 1
                    self.write({'state': 'draft'})
            elif record.state == 'pr':
                if not record.visa_number or not record.visa_issue_dt:
                    raise UserError('Please add Visa Number or Visa issued Date')
                record.write({'state': 'hr'})

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise Warning('You can only delete draft request')
        return super(HrVisaRequest, self).unlink()


class HrVisaCancelRequest(models.Model):
    _name = 'hr.visa.cancel.request'
    _description = 'HR Visa Cancellation Request'
    _inherit = ['mail.thread']
    _order = 'id DESC'

    name = fields.Char(string='Reference', required=True, default='/', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee Name')
    family_member = fields.Integer(default=0)
    # rc_number = fields.Char('RC Number', related='employee_id.otherid', readonly=True, required=True)
    nationality = fields.Many2one(comodel_name='res.country', related='employee_id.country_id', string='Nationality',
                                  required=True)
    passport_no = fields.Char(string='Passport No', related='employee_id.passport_no', copy=False, readonly=True,
                              required=True)
    p_issue_date = fields.Date(string='Passport Issue Date', copy=False, related='employee_id.passport_issued_date')
    p_expiry = fields.Date(string='Passport Expiry', related='employee_id.passport_expiry_date', copy=False,
                           required=True)
    visa_expiry = fields.Date(string='Visa Expiry', related='employee_id.visa_expire', copy=False)
    job_id = fields.Many2one(comodel_name="hr.job", string='Job Title', related='employee_id.job_id', readonly=True,
                             )
    department_id = fields.Many2one(comodel_name='hr.department', string='Department',
                                    related='employee_id.department_id', readonly=True)
    date_joining = fields.Date(string='Date Of Joining', related='employee_id.joining_date', readonly=True,
                               required=True)
    request_date = fields.Date(string='Date of Request Raised', required=True, default=fields.date.today())
    cancellation_reason = fields.Selection([('end_of_service', 'End Of Service'),
                                            ('more_than_6_month', 'More Than 6 Months'),
                                            ('termination', 'Termination'),
                                            ('death', 'Death'),
                                            ('absconding', 'Absconding')], string='Reason For Cancellation', copy=False)
    departure_date = fields.Datetime(string='Date & Time Of Departure', required=True)
    submitted_document = fields.Many2many('document.submit', string='Document Submitted ', copy=True)
    job_assigned = fields.Many2one('hr.employee', string='Job Assigned To')
    job_finish_date = fields.Date(string='Job Finished Date')
    state = fields.Selection([('draft', 'Draft'),
                              ('hr', 'Hr Section'),
                              ('pr', 'PR Section'),
                              ('done', 'Done')], string='Status', copy=False, default='draft',
                             tracking=True)
    # cancel_attachment = fields.Boolean(string="Cancellation Attached ?")
    cancel_attachment = fields.Binary(string="Cancellation Attachment")
    last_working_date = fields.Date(string='Last Working Date')
    date_of_travel = fields.Datetime(string='Date Of Travel')

    def sent_forward(self):
        """
        this will forward the record to next level
        if sequence is not generated we will generate the same at draft level. otherwise just send forward
        """
        for record in self:
            if record.state == 'draft':
                if record.name == '/':
                    record.write({'name': self.env['ir.sequence'].get('VCR') or '/'})
                record.write({'state': 'hr'})
            elif record.state == 'hr':
                record.write({'state': 'pr'})
            elif record.state == 'pr':
                record.write({'state': 'done'})

    def sent_backward(self):
        """
        this will forward the record to next level
        if sequence is not generated we will generate the same at draft level. otherwise just send forward
        """
        for record in self:
            if record.state == 'hr':
                record.write({'state': 'draft'})
            elif record.state == 'pr':
                record.write({'state': 'hr'})

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise Warning('You can only delete draft request')
        return super(HrVisaCancelRequest, self).unlink()


class DocumentSubmit(models.Model):
    _name = 'document.submit'
    _description = 'Document Submitted'
    _order = 'id DESC'

    name = fields.Char(string='Document Type name')


class HrVisaRenewRequest(models.Model):
    _name = 'hr.visa.renew.request'
    _description = 'HR Visa Renewal Request'
    _inherit = ['mail.thread']
    _order = 'id DESC'

    name = fields.Char(string='Reference', required=True, default='/')
    employee_id = fields.Many2one('hr.employee', string='Employee Name')
    duty_joining_date = fields.Date(string='Duty Joining Date')
    department_id = fields.Many2one(comodel_name='hr.department', string='Department')
    trade = fields.Many2one(comodel_name="hr.job", string='Job Title')
    dob = fields.Date(string='Date of Birth')
    passport_no = fields.Char(string='Passport No', copy=False, )
    p_expiry = fields.Date(string='Passport Expiry', copy=False, required=True)
    labor_card_no = fields.Char(string='Labor Card No')
    visa_expiry = fields.Date(string='Visa Expiry', copy=False, required=True)
    nationality = fields.Many2one(comodel_name='res.country', string='Nationality',
                                  required=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('hr', 'HR Head'),
                              ('pr', 'PR Section'),
                              ('done', 'Done')], string='Status', copy=False, default='draft',
                             tracking=True)
    job_code = fields.Char(string='Occupation Code', required=True)
    job_id = fields.Char(string='Occupation Name')

    @api.onchange('employee_id')
    def onchange_employee(self):
        for record in self:
            if record.employee_id:
                if record.employee_id.department_id:
                    record.department_id = record.employee_id.department_id
                if record.employee_id.passport_id:
                    record.passport_no = record.employee_id.passport_id
                if record.employee_id.visa_expire:
                    record.visa_expiry = record.employee_id.visa_expire
                if record.employee_id.passport_expiry_date:
                    record.p_expiry = record.employee_id.passport_expiry_date
                if record.employee_id.country_id:
                    record.nationality = record.employee_id.country_id
                if record.employee_id.job_id:
                    record.trade = record.employee_id.job_id

    def sent_forward(self):
        """
        this will forward the record to next level
        if sequence is not generated we will generate the same at draft level. otherwise just send forward
        """
        for record in self:
            if record.state == 'draft':
                if record.name == '/':
                    record.write({'name': self.env['ir.sequence'].get('VRR') or '/'})
                record.write({'state': 'hr'})
            elif record.state == 'hr':
                record.write({'state': 'pr'})
            elif record.state == 'pr':
                record.write({'state': 'done'})

    def sent_backward(self):
        """
        this will forward the record to next level
        if sequence is not generated we will generate the same at draft level. otherwise just send forward
        """
        for record in self:
            if record.state == 'hr':
                record.write({'state': 'draft'})
            elif record.state == 'pr':
                record.write({'state': 'hr'})

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise Warning('You can only delete draft request')
        return super(HrVisaRenewRequest, self).unlink()


class ClearanceUsage(models.Model):
    _name = 'clearance.usage'
    _description = 'Clearance Usage'


class VisaClearance(models.Model):
    _name = 'visa.clearance'
    _description = 'Visa Clearance'
