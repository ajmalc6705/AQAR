# -*- coding: utf-8 -*-
from __future__ import print_function
from odoo import fields, models, api,_
from odoo.exceptions import UserError


class AirTicket(models.Model):
    _name = "air.ticket.management"
    _description = 'Air Ticket'
    _inherit = ['mail.thread']
    _order = "name desc"

    name = fields.Char(string='NO', readonly=True, copy=False, required=True, default='/')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    designation = fields.Many2one('hr.job', string="Designation", related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id',
                                    store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    ticket_type = fields.Selection([
        ('annual_leave', 'Annual Leave'),
        ('return_from_leave', 'Return From Leave'),
        ('resignation', 'Resignation'),
    ], 'Ticket Type', required=True,
        tracking=True)
    travel_date = fields.Date(string="Travel Date")
    location = fields.Char(string="Location")
    price = fields.Float(string="Ticket Fare")
    eligible_amount = fields.Float(string="Eligible Amount")
    deduction_amount = fields.Float(string="Deduction Amount")
    attachment = fields.Binary(string='Attachment', help='Attachments', copy=False,
                               attachment=True)
    file_name = fields.Char('File Name')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('reject', 'Refused'),
    ], 'Status', default='draft',
        tracking=True, copy=False)
    annual_leave = fields.Many2one('hr.leave')
    resignation = fields.Many2one('hr.resignation')
    leave_check = fields.Boolean(default=False)
    resignation_check = fields.Boolean(default=False)
    rejected_by = fields.Many2one('res.users')
    rejected_date = fields.Date(string="Rejected Date")

    @api.onchange('eligible_amount','deduction_amount')
    def ticket_fare(self):
        self.price = self.eligible_amount + self.deduction_amount


    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('air.ticket.management') or '/'
        return super(AirTicket, self).create(vals)

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'

    def action_reject(self):
        for rec in self:
            rec.state = 'reject'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_open_leave(self):
        return {
            'type': 'ir.actions.act_window',
            'name': ('Annual Leave'),
            'view_mode': 'tree,form',
            'res_model': 'hr.leave',
            'target': 'current',
            'context': {'create': False},
            'domain': [('id', '=', self.annual_leave.id)],
        }

    def action_open_resignation(self):
        return {
            'type': 'ir.actions.act_window',
            'name': ('Resignation'),
            'view_mode': 'tree,form',
            'res_model': 'hr.resignation',
            'target': 'current',
            'context': {'create': False},
            'domain': [('id', '=', self.resignation.id)],
        }

    def unlink(self):
        for record in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if record.state != 'draft':
                    raise UserError(
                        _('You cannot delete the air ticket %s in the current state.', record.name)
                    )
            return super(AirTicket, self).unlink()

