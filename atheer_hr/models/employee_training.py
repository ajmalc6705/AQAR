from odoo import models, fields, api
from datetime import date, timedelta, datetime
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError


class EmployeeTraining(models.Model):
    _name = 'employee.training.form'
    _description = "Employee Training Request Form"
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(string='No', required=True, default='/')
    emp_code = fields.Char(string="Emp Code",store=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('approve', 'Approved'),
                              ('cancel', 'Cancelled'),
                              ('reject', 'Refused'),
                              ], default='draft', copy=False, tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", tracking=True)
    emp_course = fields.Many2one('employee.course.master', string="Program", tracking=True)
    program_date = fields.Date(string="Start Date", tracking=True)
    end_date = fields.Date(string="End Date", tracking=True)
    location = fields.Char(string="Location", tracking=True)
    description = fields.Text(string="Description", tracking=True)
    emp_signature = fields.Binary('Signature', help='Signature received through the portal.', copy=False,
                                  attachment=True, tracking=True)
    emp_signed_on = fields.Datetime('Signed On', help='Date of the signature.', copy=False)
    manager_signature = fields.Binary('Signature', help='Signature received through the portal.', copy=False,
                                      attachment=True, max_width=1024, max_height=1024, tracking=True)
    manager_signed_on = fields.Datetime('Signed On', help='Date of the signature.', copy=False)
    hr_signature = fields.Binary('Signature', help='Signature received through the portal.', copy=False,
                                 attachment=True, max_width=1024, max_height=1024, tracking=True)
    hr_signed_on = fields.Datetime('Signed On', help='Date of the signature.', copy=False)
    top_signature = fields.Binary('Signature', help='Signature received through the portal.', copy=False,
                                  attachment=True, max_width=1024, max_height=1024, tracking=True)
    top_signed_on = fields.Datetime('Signed On', help='Date of the signature.', copy=False, tracking=True)
    eligible1 = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string='Employee Eligible ', copy=False, index=True, tracking=True)
    eligible2 = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string='Employee Eligible ', copy=False, index=True, tracking=True)
    description1 = fields.Text(string="Description", tracking=True)
    cost = fields.Float(string="Approximate cost", tracking=True)
    description2 = fields.Text(string="Description", tracking=True)
    approved = fields.Char(string="Approved", tracking=True)
    disapproved = fields.Char(string="Disapproved", tracking=True)
    description3 = fields.Text(string="Description", tracking=True)
    # New fields

    trainer_id = fields.Many2one('res.partner',string='Trainer')
    training_type = fields.Selection([('internal','Internal'),('external','External')],string='Training Type')
    training_institute = fields.Char(string='Training Institute')
    feedback = fields.Html(string='Feedback')


    def approve(self):
        for rec in self:
            rec.write({'state': 'approve'})

    def cancel(self):
        for rec in self:
            rec.write({'state': 'cancel'})
    
    def action_refuse(self):
        for rec in self:
            rec.write({'state': 'reject'})

    def action_reset(self):
        for rec in self:
            rec.write({'state': 'draft'})
    

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_id:
                rec.emp_code = rec.employee_id.emp_id

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise UserError(_("You cannot delete employee training request form which is not in draft state."))
        return super(EmployeeTraining, self).unlink()

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('employee.training') or '/'
        return super(EmployeeTraining, self).create(vals)


class EmployeeCourse(models.Model):
    _name = 'employee.course.master'
    _description = "Employee Course Master Form"
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(string="Name")
