# -*- coding: utf-8 -*-
from odoo import fields, models, api,_
from odoo.exceptions import UserError, ValidationError


class HRAttendanceAmendment(models.Model):
    _name = "hr.attendance.amendment"
    _description = 'HR Attendance Amendment'
    _rec_name = 'sequence'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    sequence = fields.Char(required=True, copy=False, string="Sequence", tracking=True, default='/')
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirm')], string="State",
                             copy=False, tracking=True, default='draft')
    date_from = fields.Date('Date From', required=True, tracking=True, readonly=True,
                            states={'draft': [('readonly', False)]})
    date_to = fields.Date('Date To', required=True, tracking=True, readonly=True,
                          states={'draft': [('readonly', False)]})
    attendance_type = fields.Selection([('partial_day', 'Partial Day'),
                                        ('pr_present', 'PR- Present'),
                                        ('hd_holiday', 'HD- Holiday'),
                                        ('absent', 'A – Absent'),
                                        ('sick_leave', 'SL- Sick Leave'),
                                        ('annual_leave', 'AL- Annual Leave'),
                                        ('emergency_leave', 'EL- Emergency Leave')], string="Attendance Type",
                                       store=True, tracking=True)
    employee_amendment_ids = fields.One2many('hr.attendance', 'attendance_amendment_id')

    @api.model
    def create(self, vals):
        """creates sequence for the model"""
        if vals.get('sequence', '/') == '/':
            vals['sequence'] = self.env['ir.sequence'].next_by_code(
                'hr.attendance.amendment') or '/'
        result = super(HRAttendanceAmendment, self).create(vals)
        return result

    @api.onchange('date_from', 'date_to', 'attendance_type')
    def onchange_employee_ids(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.attendance_type:
                rec.employee_amendment_ids = False
                attendance_ids = self.env['hr.attendance'].search(
                    [('attendance_type', '=', rec.attendance_type), ('amendment_true', '=', False)]).filtered(
                    lambda x: rec.date_from <= x.date <= rec.date_to)
                if attendance_ids:
                    for ids in attendance_ids:
                        rec.employee_amendment_ids = [(4, ids.id)]
                else:
                    rec.employee_amendment_ids = False
            elif rec.date_from and rec.date_to and not rec.attendance_type:
                rec.employee_amendment_ids = False
                attendance_ids = self.env['hr.attendance'].search(
                    [('amendment_true', '=', False)]).filtered(
                    lambda x: rec.date_from <= x.date <= rec.date_to)
                if attendance_ids:
                    for ids in attendance_ids:
                        rec.employee_amendment_ids = [(4, ids.id)]
                else:
                    rec.employee_amendment_ids = False

    def action_set_to_draft(self):
        """changes the state to draft"""
        for rec in self:
            rec.write({'state': 'draft'})
            for ids in rec.employee_amendment_ids:
                attendances = self.env['hr.attendance'].search(
                    [('check_in', '=', ids.check_in), ('employee_id', '=', ids.employee_id.id)])
                for lines in attendances:
                    if lines:
                        lines.amendment_true = False
        return True

    def action_confirm(self):
        """changes the state to confirm"""
        for rec in self:
            rec.write({'state': 'confirm'})
            if not rec.employee_amendment_ids:
                raise ValidationError('There are no attendance records during this period.')
            for ids in rec.employee_amendment_ids:
                attendances = self.env['hr.attendance'].search(
                    [('check_in', '=', ids.check_in), ('employee_id', '=', ids.employee_id.id),
                     ('amendment_true', '=', False)])
                for lines in attendances:
                    if lines:
                        lines.amendment_true = True
                        lines.attendance_type = ids.amendment_attendance_type
                    else:
                        lines.amendment_true = False

        return True

    def unlink(self):
        for record in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if record.state != 'draft':
                    raise UserError(
                        _("You Cannot delete an attendance amendment %s in the current state", record.sequence))
        return super(HRAttendanceAmendment, self).unlink()
