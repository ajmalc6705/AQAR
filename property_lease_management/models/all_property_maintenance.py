# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo import SUPERUSER_ID


class AllMaintenance(models.Model):
    _name = 'all.property.maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = _('All Property Maintenance')
    _order = 'date desc'

    # @api.model
    # def _get_name(self):
    #     if 'default_utility' in self._context.keys():
    #         return "Utility Charges"
    #     else:
    #         return "Maintenance"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
            self_comp = self.with_company(company_id)
            if vals.get('name', 'New') == 'New':
                vals['name'] = self_comp.env['ir.sequence'].next_by_code('all.property.maintenance') or '/'
        return super().create(vals_list)

    name = fields.Char(string='Job Number')

    property_maintenance_type = fields.Selection([('all_flats', 'All Flats'), ('flat', 'Flat')], 'Type',
                                                 default="all_flats",)

    state = fields.Selection([('draft', _('Draft')),
                              ('pending_approval', _('Pending Approval')),
                              ('approved', _('Approved')),
                              ('start_the_work', _('Start the Work')),
                              ('done', _('Work Completed')),
                              ('cancel', _('Cancelled'))], string='State', default="draft")
    property_id = fields.Many2one(comodel_name='property.property', string='Unit No.',
                                  ondelete='cascade', states={'draft': [('readonly', False)]})
    all_property_id = fields.Many2many(comodel_name='property.property', string='Unit No.',
                                       ondelete='cascade', states={'draft': [('readonly', False)]})
    employee_ids = fields.Many2many(comodel_name='hr.employee', string='Assigned Employees',
                                    states={'draft': [('readonly', False)]})
    date = fields.Date(string='Date', states={'draft': [('readonly', False)]}, default=fields.Date.today)
    due_date = fields.Datetime(string='Due Date', states={'draft': [('readonly', False)]})
    done_date = fields.Datetime(string='Date Completed', states={'draft': [('readonly', False)]})
    description = fields.Text(string='Description')
    cost = fields.Float(string='Expense', digits='Property')
    maintenance_type = fields.Selection([('routine', _('Routine maintenance')), ('adhoc', _('Adhoc maintenance'))],
                                        string='Maintainance Type', copy=False)
    asset_id = fields.Many2one(comodel_name='assets.accessrz', string='Assets ')
    asset_type_id = fields.Many2one(comodel_name='assets.accessrz.type', string='Asset Type')
    tenant_id = fields.Many2one(comodel_name='res.partner', string='Tenants', related="property_id.rent_id.partner_id")
    # all_tenant_id = fields.Many2one(comodel_name='res.partner', string='Tenants', related="property_id.rent_id.partner_id")
    company_id = fields.Many2one(comodel_name='res.company', string='Company', change_default=True,
                                 default=lambda self: self.env.company,
                                 readonly=True, states={'draft': [('readonly', False)]})
    building = fields.Many2one(comodel_name='property.building', string='Building', required=True)
    priority = fields.Selection([('high', 'Major'), ('low', 'Minor')],
                                string='Priority', default='high')
    attachment_id = fields.Binary(string='Attachment')
    flat_count = fields.Integer(compute='compute_flat_count')
    bill_attachment_id = fields.Binary(string='Attachment', help='Attachments', copy=False,
                                       attachment=True)
    file_name = fields.Char('File Name')
    create_true = fields.Boolean(default=False)
    remarks = fields.Char(string="Remarks")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('all.property.maintenance')
        res = super(AllMaintenance, self).create(vals)
        res.create_true = True
        return res

    def write(self, vals):
        res = super(AllMaintenance, self).write(vals)
        for record in self:
            print("iuhjihioknj", record.flat_count, record.create_true)
            record_id = record.id
            if record.asset_type_id:
                flat_maintenance_ids = self.env['property.maintenance'].search(
                    [('property_maintenance_ids', '=', record_id)]).ids
                if flat_maintenance_ids:
                    self.env.cr.execute("UPDATE property_maintenance SET property_maintenance_ids=NULL WHERE id IN %s",
                                        [tuple(flat_maintenance_ids)])
                    self.env.cr.execute("DELETE FROM property_maintenance WHERE id IN %s",
                                        [tuple(flat_maintenance_ids)])
                if record.all_property_id and record.asset_type_id:
                    asset_ids = self.env['assets.accessrz'].search(
                        [('asset_categ', '=', record.asset_type_id.id), ('building_id', '=', record.building.id),
                         ('property_id', 'in', record.all_property_id.ids)])
                    if not asset_ids:
                        raise ValidationError('There are no asset associated with the selected building and flat. ')
                    for rec in asset_ids:
                        name = self.env['ir.sequence'].next_by_code('property.maintenance') or _('Maintenance')
                        maintenance = "INSERT INTO property_maintenance (building,name,property_maintenance_ids,property_id,asset_id,cost,date,maintenance_type,state,description) " \
                                      "VALUES(" + str(record.building.id) + ",'" + str(name) + "'," + str(
                            record.id) + "," + str(
                            rec.property_id.id) + "," + str(rec.id) + ",'" + str(record.cost) + "','" + str(
                            record.date) + "','" \
                                      + str(record.maintenance_type) + "','" + str('draft') + "','" + str(
                            record.remarks) + "')"
                        self._cr.execute(maintenance)

                if record.property_id and record.asset_type_id:
                    asset_ids = self.env['assets.accessrz'].search(
                        [('asset_categ', '=', record.asset_type_id.id), ('building_id', '=', record.building.id),
                         ('property_id', '=', record.property_id.id)])
                    if not asset_ids:
                        raise ValidationError(
                            'There are no asset associated with the selected building and flat. ')
                    for rec in asset_ids:
                        name = self.env['ir.sequence'].next_by_code('property.maintenance') or _('Maintenance')
                        maintenance = "INSERT INTO property_maintenance (building,name,property_maintenance_ids,property_id,asset_id,cost,date,maintenance_type,state,description) " \
                                      "VALUES(" + str(record.building.id) + ",'" + str(name) + "'," + str(
                            record.id) + "," + str(
                            rec.property_id.id) + "," + str(rec.id) + ",'" + str(record.cost) + "','" + str(
                            record.date) + "','" \
                                      + str(record.maintenance_type) + "','" + str('draft') + "','" + str(
                            record.remarks) + "')"
                        self._cr.execute(maintenance)

        return res

    @api.onchange('property_maintenance_type', 'building')
    def onchange_property_maintenance_type(self):
        for rec in self:
            rec.all_property_id = [((5, 0, 0))]
            if rec.property_maintenance_type == 'all_flats' and rec.building:
                rec.all_property_id = [((5, 0, 0))]
                flat_ids = self.env['property.property'].search(
                    [('parent_building', '=', rec.building.id), ('state', '=', 'open')]).ids
                rec.all_property_id = [((6, 0, flat_ids))]

    def compute_flat_count(self):
        for record in self:
            flat_maintenance_ids = self.env['property.maintenance'].search_count(
                [('property_maintenance_ids', '=', record.id)])
            record.flat_count = flat_maintenance_ids

    @api.onchange('maintenance_type', 'date', 'cost', 'description')
    def onchange_details(self):
        for rec in self:
            flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', rec.id)])
            for each in flat_maintenance_ids:
                each.maintenance_type = rec.maintenance_type
                each.date = rec.date
                each.cost = rec.cost
                each.description = rec.remarks

    def action_pending_for_approval(self):
        for rec in self:
            flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', rec.id)])
            for each in flat_maintenance_ids:
                each.new_send_for_approval()
            rec.state = 'pending_approval'

    def action_approve(self):
        for rec in self:
            flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', rec.id)])
            for each in flat_maintenance_ids:
                each.new_approve()
            rec.state = 'approved'

    def action_start_work(self):
        for rec in self:
            flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', rec.id)])
            for each in flat_maintenance_ids:
                each.start_the_work()
            rec.state = 'start_the_work'

    def action_done(self):
        for rec in self:
            flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', rec.id)])
            for each in flat_maintenance_ids:
                each.done_date = rec.done_date
                each.mark_completed()
            rec.state = 'done'

    # def action_pending_for_approval2(self):
    #     for rec in self:
    #         flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', rec.id)])
    #         for each in flat_maintenance_ids:
    #             each.action_pending_for_approval2()
    #         rec.state = 'pending_approval2'

    def action_complete_payment(self):
        for rec in self:
            flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', rec.id)])
            for each in flat_maintenance_ids:
                each.action_complete_payment()

            # notification_obj = self.env['atheer.notification']
            # template_id = self.env.ref('notify_atheer.record_waiting_for_response').id
            # model_id = self.env['ir.model'].sudo().search([('model', '=', 'all.property.maintenance')]).id
            # notification_obj._send_instant_notify(
            #     title="Property Maintenance",
            #     message='Waiting for approval for ' + ' ' + str(
            #         rec.name),
            #     notification_type='both', template_id=template_id,
            #     template_object=rec.id, template_model_id=model_id,
            #     action=self.env.ref(
            #         'property_lease_management.action_all_property_maintenance').id,
            #     domain=[['id', '=', rec.id]],
            #     user_type="groups", recipient_ids=[
            #         self.env.ref('property_lease_management.group_property_accountant').id])

            rec.state = 'accountant'

    def action_paid(self):
        for rec in self:
            flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', rec.id)])
            for each in flat_maintenance_ids:
                each.action_paid()
            rec.state = 'paid'

    def action_cancel(self):
        for rec in self:
            flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', rec.id)])
            for each in flat_maintenance_ids:
                each.button_cancel()
            rec.state = 'cancel'

    def action_view_maintenance_ids(self):
        flat_maintenance_ids = self.env['property.maintenance'].search([('property_maintenance_ids', '=', self.id)]).ids

        return {
            'type': 'ir.actions.act_window',
            'name': ('Maintenance'),
            'view_mode': 'tree,form',
            'res_model': 'property.maintenance',
            'target': 'current',
            'context': {'create': False},
            'domain': [('id', 'in', flat_maintenance_ids)],
        }

    def action_send_mail_to_tenants(self):
        body = self.env['assets.accessrz'].maintenance_req_mail_body
        email_to = []
        asset_ids = self.env['assets.accessrz'].search(
            [('asset_categ', '=', self.asset_type_id.id), ('building_id', '=', self.building.id),
             ('property_id', '=', self.property_id.id)]).ids
        for assets_id in asset_ids:
            asset = self.env['assets.accessrz'].search([('id', '=', assets_id)])
            print("dfgsdgsdg", assets_id, asset.property_id.rent_id)
            if asset.property_id.rent_id.partner_id:
                email_to.append(asset.property_id.rent_id.partner_id.id)
                print("dfgsdgsdgemail_to", email_to)
        print("23444444444444", email_to)
        return {
            'name': _("Send MAIL"),
            'view_mode': 'form',
            'view_id': self.env.ref('property_lease_management.send_mail_maintenance_request_view_form').id,
            'view_type': 'form',
            'tag': 'reload',
            'res_model': 'send.mail.maintenance.request',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'stay_open': True,
            'domain': '[]',
            'context': {
                'default_subject': str('Send Mail'),
                'default_assets_ids': asset_ids,
                'default_recipient_ids': [(6, 0, email_to)] if email_to else None,
                'default_message': body
            }
        }

    def unlink(self):
        for record in self:
            if record.state == 'draft':
                flat_maintenance_ids = self.env['property.maintenance'].search(
                    [('property_maintenance_ids', '=', record.id)])
                for each in flat_maintenance_ids:
                    each.property_maintenance_ids = False
                    each.unlink()
            if record.state != 'draft':
                raise UserError('At this gggstate, it is not possible to delete this record. ')
            return super(AllMaintenance, self).unlink()


# maintenance wizard for sending mail
class SendMaintenanceRequest(models.TransientModel):
    _name = 'send.mail.maintenance.request'
    _description = _('Send Mail maintenance request')

    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    subject = fields.Char(string="Subject", required=True)
    message = fields.Html("Message")
    assets_ids = fields.Many2many('assets.accessrz', string='Assets', store=True)
    recipient_ids = fields.Many2many('res.partner', string="Recipients")

    def send_mail(self):
        """ function to send the email notification """
        email_to = []
        for assets_id in self.assets_ids:
            email_to.append(str(assets_id.property_id.rent_id.partner_id.email), )
        main_content = {
            'subject': self.subject,
            'author_id': SUPERUSER_ID,
            'body_html': self.message,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).sudo().send()
