# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import fields, models, api, _
from odoo.tools import float_compare
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class HrLeaveReturn(models.Model):
    _name = "hr.leave.return"
    _description = 'Leave Return'
    _inherit = ['mail.thread']
    _order = 'id DESC'

    name = fields.Char("Form No.", copy=False, default='/')
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', copy=False,
                                  tracking=True)
    mode = fields.Selection([('late', 'LATE'), ('early', 'EARLY'), ('on_time', 'On-Time')], string='Mode Of Return',
                            copy=False,
                            tracking=True)
    return_date = fields.Date(string='Return Date', tracking=True, )
    designation = fields.Many2one('hr.job', string='Designation', readonly=True, related='employee_id.job_id',
                                  tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True,
                                    related='employee_id.department_id')
    remarks = fields.Text(string='Remarks', copy=False, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'),
                              ('approved', 'Approved'), ], default='draft', copy=False, tracking=True)
    leave_returned = fields.Boolean(default=False)
    leave_details = fields.One2many('hr.leave', 'leave_return_id')
    comp_leave = fields.Many2one('hr.leave.type', string="Compensation Leave",
                                 domain=['|', ('requires_allocation', '=', 'no'), ('has_valid_allocation', '=', True)])
    rejoining_date = fields.Datetime(string='Rejoining Date', required=True, tracking=True, )
    excess_leave = fields.Float(string="Excess Leave")

    @api.constrains('excess_leave', 'comp_leave')
    def _check_holidays(self):
        for rec in self:
            if not rec.employee_id or not rec.comp_leave or rec.comp_leave.requires_allocation == 'no' or rec.mode != 'late':
                continue
            mapped_days = rec.comp_leave.get_employees_days([rec.employee_id.id], rec.rejoining_date)
            leave_days = mapped_days[rec.employee_id.id][rec.comp_leave.id]
            if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 or float_compare(
                    leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
                raise ValidationError(_('The number of remaining leave is not sufficient for this leave type.'))

    @api.onchange('employee_id')
    def onchange_leaves(self):
        for rec in self:
            rec.leave_details = [(5, 0, 0)]
            if rec.employee_id:
                leave_ids = self.env['hr.leave'].search(
                    [('leave_returned', '=', False), ('leave_return', '=', False),
                     ('employee_id', '=', rec.employee_id.id),
                     ('holiday_status_id.is_sick', '=', False), ('state', '=', 'validate'),
                     ], order="request_date_to desc", limit=1)
                if leave_ids:
                    last_request_date = leave_ids.request_date_to
                    rec.return_date = last_request_date + relativedelta(days=1)
                    rec.leave_details = [(4, leave_ids.id)]
                if not leave_ids:
                    rec.leave_details = [(5, 0, 0)]
                    raise ValidationError(
                        _('You dont have leaves for %s') % (rec.employee_id.name))

    @api.onchange('rejoining_date', 'return_date')
    @api.depends('rejoining_date', 'return_date')
    def onchange_excess_leave(self):
        for rec in self:
            all_leaves = [line.date_from for line in rec.leave_details]
            if all_leaves:
                start_date = all_leaves[0]
                if start_date and rec.rejoining_date:
                    if rec.rejoining_date.date() < start_date.date():
                        raise ValidationError(
                            _('Rejoining date you have selected is earlier than the leave start date.'))
                    elif rec.rejoining_date.date() == start_date.date():
                        raise ValidationError(
                            _('Rejoining date you have selected is equal to the leave start date.'))
            if rec.return_date and rec.rejoining_date:
                if rec.return_date == rec.rejoining_date.date():
                    rec.mode = 'on_time'
                    rec.excess_leave = 0
                elif rec.rejoining_date.date() > rec.return_date:
                    rec.mode = 'late'
                    rec.excess_leave = (rec.rejoining_date.date() - rec.return_date).days
                elif rec.rejoining_date.date() < rec.return_date:
                    rec.mode = 'early'
                    rec.excess_leave = (rec.return_date - rec.rejoining_date.date()).days

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.leave.return') or '/'
        return super(HrLeaveReturn, self).create(vals)

    def approve(self):
        """
        :return-mode ('late', 'LATE'), ('early', 'EARLY')
    
        Case 1 Early Return:
            : leave Record which is selected according to the employee travel return date.
            - if the leave selected date is greater than the return date, then it gets reused. Later can consider for payroll
            - if the leave selected period contains the return date: ie, return date in between leave period
                1. refuse the selected leave in the same multiple leave record [for tracking the updates on leave]
                2. New Leave record with updated date according to the leave return date.
                    example 1: leave from 02/06/2019  to 07/06/2019  and return date 05/06/2019
                        1. current leave record will get refuse
                        2. Updated new leave record with leave from 02/06/2019 to 04/06/2019
                    example 2: leave from 02/06/2019  to 07/06/2019  and return date 02/06/2019 or less than 02/06/2019
                        1. current leave record will get refuse
                3. 3. Update Message Logs
        Case 2 Late Return:
            : leave Record which is selected according to the employee travel return date.
                - if the leave selected period not in the return date: ie, return date greater than leave period
                    1. Create an Unpaid Leave from last date of leave selected up to return date
                        example 1: leave from 02/06/2019  to 07/06/2019  and return date 10/06/2019
                        1. current leave record will get remains there
                        2. Create new leave record with leave from 08/06/2019 to 09/06/2019
                    2. Link created leave with the leave application
                    3. Update Message Logs
        :return:
        """
        for record in self:
            selected_leave = record.leave_details.sorted(key=lambda x: x.date_to)
            if selected_leave and record.rejoining_date:
                return_date = record.return_date
                if record.mode == 'on_time':
                    for ids in record.leave_details:
                        ids.write({'leave_return_id': record.id,
                                   'leave_return': True,
                                   'leave_returned': True,
                                   })
                    record.state = 'approved'

                elif record.mode == 'early':
                    for each in selected_leave:
                        if each.request_date_from > record.rejoining_date.date():
                            last = list(selected_leave).index(each)
                            each.action_refuse()
                            leave_name = each.display_name
                            each.message_post(
                                body="Leave Return Note %s Approved For %s." % (record.name, leave_name),
                                subtype_xmlid="mail.mt_comment",
                                message_type="comment")
                            record.message_post(body="Leave Application %s Refused." % leave_name,
                                                subtype_xmlid="mail.mt_comment",
                                                message_type="comment")
                        if each.request_date_to >= record.rejoining_date.date() > each.request_date_from:
                            each.action_refuse()
                            leave_name = each.holiday_status_id.display_name
                            each.message_post(
                                body="Leave Return Note %s Refused Leave %s." % (record.name, leave_name),
                                subtype_xmlid="mail.mt_comment",
                                message_type="comment")
                            record.message_post(body="Leave Application %s Refused." % leave_name,
                                                subtype_xmlid="mail.mt_comment",
                                                message_type="comment")

                            date_to = record.rejoining_date - timedelta(days=1)
                            # Duplicate Leave And Update the new date according to the return date
                            dur = (date_to + timedelta(hours=8)).date() - each.request_date_from + relativedelta(days=1)
                            vals = {
                                'employee_id': each.employee_id.id,
                                'request_date_from': each.request_date_from,
                                'request_date_to': date_to + timedelta(hours=8),
                                'date_from': each.request_date_from,
                                'date_to': date_to + timedelta(hours=8),
                                'holiday_status_id': each.holiday_status_id.id,
                                'rejoining_date': record.rejoining_date,
                                # 'number_of_days': dur.days,
                                'name': 'Early Leave Return' + ' ' + record.name,
                                'leave_return_id': record.id,
                                'leave_return': True,
                                'leave_returned': True,
                                'direct_req': True,
                            }
                            leave_copy = self.env['hr.leave'].create(vals)
                            leave_copy.onchange_no_of_days_eligible()
                            leave_copy._compute_number_of_days()
                            leave_copy.request_to_annual_line_manager()
                            leave_copy.request_to_annual_hr()
                            leave_copy.request_to_line_manager()
                            leave_copy.request_to_project_manager()
                            leave_copy.request_to_hr()
                            leave_copy.request_to_ceo()
                            leave_copy.action_confirm()
                            leave_copy.action_validate()
                            leave_copy.state = 'validate'
                            leave_copy.leave_return = True
                            leave_copy.message_post(
                                body="Leave Return Note %s Approved For %s." % (record.name, leave_copy.display_name),
                                subtype_xmlid="mail.mt_comment",
                                message_type="comment")
                            leave_copy.message_post(
                                body="Leave Application Updated According to the travel return date %s." % return_date,
                                subtype_xmlid="mail.mt_comment",
                                message_type="comment")
                            record.state = 'approved'
                        each.write({'leave_return_id': record.id,
                                    'leave_return': True,
                                    'leave_returned': True,
                                    })
                elif record.mode == 'late':
                    end_date = record.return_date
                    date_from = end_date
                    date_to = (record.rejoining_date + timedelta(days=-1)).date()
                    dur = date_to - date_from + relativedelta(days=1)
                    confirmed_date = datetime.combine(date_to, datetime.max.time())
                    dt = confirmed_date - timedelta(hours=6, minutes=50)
                    vals = {
                        'employee_id': record.employee_id.id,
                        'request_date_from': date_from,
                        'request_date_to': dt,
                        'date_from': date_from,
                        'date_to': dt,
                        'holiday_status_id': record.comp_leave.id,
                        # 'number_of_days': dur.days,
                        'name': 'Late Leave Return' + ' ' + record.name,
                        'rejoining_date': record.rejoining_date,
                        'leave_return_id': record.id,
                        'leave_return': True,
                        'annual_leave': False,
                        'leave_returned': True,
                        'direct_req': True,
                    }
                    leave_copy = self.env['hr.leave'].create(vals)
                    leave_copy._checking_dates()
                    leave_copy._compute_number_of_days()
                    leave_copy.action_confirm()
                    leave_copy.action_validate()
                    leave_copy.state = 'validate'

                    leave_copy.message_post(
                        body="Leave Return Note %s Approved For %s." % (record.name, leave_copy.display_name),
                        subtype_xmlid="mail.mt_comment",
                        message_type="comment")
                    leave_copy.message_post(
                        body="Leave Application Created According to the travel return date %s." % return_date,
                        subtype_xmlid="mail.mt_comment",
                        message_type="comment")
                    for ids in record.leave_details:
                        ids.write({'leave_return_id': record.id,
                                   'leave_return': True,
                                   'leave_returned': True,
                                   })
                    record.state = 'approved'

    @api.onchange('employee_id')
    def onchange_employee(self):
        for rec in self:
            if not rec.employee_id:
                rec.leave_details = False

    def unlink(self):
        for rec in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if rec.state not in ['draft']:
                    raise UserError(_("You can't delete leave return %s in the current state.", rec.name))
            return super(HrLeaveReturn, self).unlink()
