# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class Maintenance(models.Model):
    _name = 'property.maintenance'
    _description = _('Flat Maintenance Details')
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    @api.model
    def _get_default(self):
        if 'default_utility' in self._context.keys():
            # for each in self:
            return 'utility'
        else:
            # for each in self:
            return 'draft'

    @api.model
    def _get_name(self):
        if 'default_utility' in self._context.keys():
            return "Utility Charges"
        else:
            return "Maintenance"

    def button_approve(self):
        self.state = 'progress'

    name = fields.Char(string='Job Number', readonly=True, default=_get_name)
    utility_type = fields.Many2one(comodel_name='utility.type', string='Type')
    supervisor = fields.Many2one(comodel_name='res.users', string='Supervisor', readonly=True,
                                 states={'draft': [('readonly', False)]})
    property_id = fields.Many2one(comodel_name='property.property', string='Unit No.', required=True,
                                  ondelete='cascade', states={'draft': [('readonly', False)]})
    employee_ids = fields.Many2many(comodel_name='hr.employee', string='Assigned Employees',
                                    states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', _('Draft')),
                              ('send_for_approval', _('Send for Approval of PH')),
                              ('approved', _('approved')),
                              ('start_the_work', _('Start the Work')),
                              ('done', _('Work Completed')),
                              ('cancel', _('Cancelled'))], string='State', default="draft")
    date = fields.Date(string='Date', states={'draft': [('readonly', False)]}, default=fields.Date.today)
    due_date = fields.Datetime(string='Due Date', states={'draft': [('readonly', False)]})
    done_date = fields.Datetime(string='Date Completed', states={'draft': [('readonly', False)]})
    description = fields.Text(string='Repair Performed')
    cost = fields.Float(string='Expense', digits='Property')
    maintenance_type = fields.Selection([('routine', _('Routine maintenance')), ('adhoc', _('Adhoc maintenance'))],
                                        string='Maintainance Type', copy=False)
    next_date = fields.Date(string='Next Maintainance Date')
    complaint_id = fields.Many2one(comodel_name='customer.complaints', string='Customer Complaints')
    asset_id = fields.Many2one(comodel_name='assets.accessrz', string='Assets ')
    asset_type_id = fields.Many2one(comodel_name='assets.accessrz.type', string='Assets',
                                    related="asset_id.asset_categ", store=True)
    tenant_id = fields.Many2one(comodel_name='res.partner', string='Tenants', related="property_id.rent_id.partner_id")
    utility = fields.Boolean(string='Utility Charge')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', change_default=True,
                                 default=lambda self: self.env.company,
                                 readonly=True, states={'draft': [('readonly', False)]})
    from_date = fields.Date(string='From Date', default=fields.Date.context_today)
    to_date = fields.Date(string='to Date', default=fields.Date.context_today)
    building = fields.Many2one(comodel_name='property.building', string='Building', required=True)
    doc_ids = fields.Many2many('atheer.documents',
                               string='Documents')
    priority = fields.Selection([('high', 'Major'), ('low', 'Minor')],
                                string='Priority', default='high')
    attachment_id = fields.Binary(string='Attachment')
    property_maintenance_ids = fields.Many2one('all.property.maintenance')

    def new_send_for_approval(self):
        self.write({'state': 'send_for_approval'})

    def new_approve(self):
        self.write({'state': 'approved'})

    def start_the_work(self):
        self.write({'state': 'start_the_work'})

    def mark_completed(self):
        self.write({'state': 'done'})

    def unlink(self):
        for record in self:
            print("345345345",record.state,record.property_maintenance_ids)
            if record.property_maintenance_ids:
                raise UserError('You are not able to delete the record as it is being created by property maintenance. ')
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(Maintenance, self).unlink()

    # alsabla customisation
    @api.onchange('complaint_id')
    def onchange_complaint_id(self):
        print("9ygbhjcvbsfdb")
        if self.complaint_id:
            self.property_id = self.complaint_id.property
            # self.asset_id = self.complaint_id.asset
            # self.employee_id = self.complaint_id.assigned_emp
            # self.description = self.complaint_id.comp_detail
            self.supervisor = self.complaint_id.job_by_suprvsr
            self.due_date = self.complaint_id.exp_date
            self.done_date = self.complaint_id.exp_date
            self.tenant_id = self.complaint_id.tenant_id
            self.building = self.complaint_id.building
            # self.tenant_id = self.complaint_id.tenant_id

    # @api.constrains('employee_ids')
    def notify_employee_ids(self):
        """ give notification for the employees """
        for rec in self:
            print(rec)
            print(rec.employee_ids.ids)
            # self.env['atheer.notification']._send_instant_notify(title="Maintenance Request Notification",
            #                                                      message="You got assigned to a new maintenance request",
            #                                                      action=self.env.ref(
            #                                                          'property_lease_management.action_property_maintenance').id,
            #                                                      user_type="groups",
            #                                                      domain=[['id', '=', rec.id]],
            #                                                      recipient_ids=rec.employee_ids.ids)

    def to_approve(self):
        res_id = self.complaint_id.id
        # self.complaint_id.state = 'waiting'
        view_id = self.env['ir.model.data'].sudo().get_object_reference('property_lease_management',
                                                                        'view_customer_complaint_form')
        self.state = 'done'
        self.complaint_id.cost = self.cost
        # self.complaint_id.compl_emp = self.employee_id
        self.complaint_id.approv_suprvsr = self.supervisor
        self.complaint_id.compld_date = self.done_date
        self.complaint_id.parts_replaced = self.description
        if self.next_date:
            self.asset_id.expiry_date = self.next_date
        if res_id:
            return {
                'name': _("Customer Complaint"),
                'view_mode': 'form',
                'view_id': view_id[1],
                'res_id': res_id,
                'view_type': 'form',
                'res_model': 'customer.complaints',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                'context': {
                    'default_cost': self.cost,
                    # 'default_state': 'done',
                }
            }

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('property.maintenance') or _('Maintenance')
        return super(Maintenance, self).create(vals)

    # def create_sequence(self):
    #     self.name = self.env['ir.sequence'].next_by_code('property.maintenance')
    #     print("r32egregr", self.name)

    def button_confirm(self):
        self.write({'state': 'waiting_approval'})

    def button_done(self):
        self.state = 'done'
        return

    def button_cancel(self):
        self.write({'state': 'cancel'})

    # added for property maintenance


    # def action_pending_for_approval2(self):
    #     for rec in self:
            # flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', rec.id)])
            # for each in flat_maintenance_ids:
            #     each.mark_completed()
            # rec.state = 'pending_approval2'
    #

    # def action_complete_payment(self):
    #     for rec in self:
            # flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', rec.id)])
            # for each in flat_maintenance_ids:
            #     each.mark_completed()
            # rec.state = 'accountant'


    # def action_paid(self):
    #     for rec in self:
            # flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', rec.id)])
            # for each in flat_maintenance_ids:
            #     each.mark_completed()
            # rec.state = 'paid'


class MaintenanceType(models.Model):
    _name = 'property.maintenance.type'
    _description = _('Flat Maintenance Type')

    name = fields.Char(string='Name', required=True)


class UtilityType(models.Model):
    _name = 'utility.type'
    _description = _('Utility Type')

    name = fields.Char(string='Name', required=True)


class IncomeType(models.Model):
    _name = 'property.income.type'
    _description = _('Property Income Type')

    name = fields.Char(string='Name', required=True)

    # customer complaints
#
# class Customer_complaint(osv.Model):
#     _name = 'customer.complaints'
#
#
#     _columns = {
#         'partner_id':fields.Many2one('res.partner',_('Customer')),
#         'dec = fields.Text(_('Complaint'), required=True),
#     }
