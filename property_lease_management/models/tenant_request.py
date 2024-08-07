# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import SUPERUSER_ID

from lxml import etree
import json


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    tenant_request_id = fields.Many2one(comodel_name='tenant.request', string='Tenant Request')


class SendEmailDocument(models.TransientModel):
    _name = 'send.email.document'
    _description = 'Send Email Document'

    partner_id = fields.Many2one('res.partner', string="Send To", required="1")
    subject = fields.Char(string="Subject", required=True)
    message = fields.Html("Message")
    attachment_ids = fields.Many2many('ir.attachment', 'tenant_request_id', string='Attachments')

    def send_mail(self):
        """ function to send the email notification """
        main_content = {
            'subject': self.subject,
            'author_id': SUPERUSER_ID,
            'body_html': self.message,
            'email_to': self.partner_id.email,
            'attachment_ids': self.attachment_ids
        }
        self.env['mail.mail'].sudo().create(main_content).sudo().send()


class TenantRequest(models.Model):
    _name = 'tenant.request'
    _rec_name = 'sequence'
    _description = 'Tenant Requests'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Char(string='Sequence', readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string='Tenant', required=True,
                                 tracking=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    rent_id = fields.Many2one(comodel_name='property.rent', string='Rent Agreement')
    new_rent_id = fields.Many2one(comodel_name='property.rent', string='New Rent Agreement',
                                  compute="compute_new_rent_id")
    building_id = fields.Many2one('property.building', 'Building',  store=True)
    property_id = fields.Many2one(comodel_name='property.property', string='Unit', store=True,
                                  related="rent_id.property_id", tracking=True)
    request_type = fields.Selection([('Cheque holding', 'Cheque holding'),
                                     ('Rent Reduction', 'Rent Reduction'),
                                     ('Renewal Request', 'Renewal Request'),
                                     ('Vacate Request', 'Vacate Request'),
                                     ('waiver_of_rent', 'Waiver of Rent'),
                                     ('other', 'Other')], string="Request Type")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    no_of_month = fields.Integer('Number of Months', required=True, default=1)
    check_ids = fields.One2many('tenant.check', 'tenant_request_id', 'Cheque Details')
    tenant_esignature_ids = fields.One2many('tenant.signature.template', 'tenant_request_id', 'E-Signature Details')
    current_rent = fields.Float('Current Rent', store=True, digits='Property')
    proposed_rent = fields.Float('Rent Proposed by Tenant', digits='Property')
    approved_rent = fields.Float('Rent Proposed by Sales Head', digits='Property')
    effective_date = fields.Date(string="Effective Date")
    vacate_date = fields.Date(string="Vacate Date")
    state = fields.Selection([('draft', 'Draft'),
                              ('Property Head', 'Property Head'),
                              ('Accountant', 'Accountant'),
                              ('approved', 'Approved'),
                              ('refused', 'Refused')],
                             default='draft', string='State', copy=False, tracking=True)
    state_renewal = fields.Selection([('draft', 'Draft'),
                                      ('Property Head', 'Property Head'),
                                      ('approved', 'Approved'),
                                      ('refused', 'Refused')],
                                     default='draft', string='State ', copy=False, tracking=True)
    tenant_reason = fields.Text('Tenant Reason')
    sales_remarks = fields.Text('Executive Remarks')
    sales_head_remarks = fields.Text('Property Head Remarks')
    accountant_remarks = fields.Text('Property Accountant Remarks')
    p_head_approved_by = fields.Many2one('res.users', 'Property Head')
    p_head_approved_date = fields.Date(string='Property Head Approved Date')
    commercial_approved_date = fields.Date(string='Commercial')
    sanad_approved_date = fields.Date(string='Sanad')
    sanad_tenant_date = fields.Date(string='Sanad by Tenant')
    lease_from_date = fields.Date(string='Lease Start', default=fields.Date.today, readonly=True,
                                  states={'draft': [('readonly', False)]}, tracking=True)
    lease_to_date = fields.Date(string='Lease End', readonly=True,
                                compute='_compute_to_date', tracking=True, store=True)
    period = fields.Integer(string='Rental Period', tracking=True)
    installment_schedule = fields.Selection([('monthly', _('Monthly')),
                                             ('one_bill', _('One Bill')),
                                             ('quaterly', _('Quarterly')),
                                             ('six_month', _('6 - Month')),
                                             ('yearly', _('Yearly')),
                                             ('one_bill', _('One Bill(Fully Tenure)'))], string='Installment Schedule',
                                            tracking=True)
    year_month_days = fields.Char('Duration', compute="_compute_year_month_days")
    approve_button = fields.Boolean('approve visibility', default=False, compute="compute_button_visibility")
    accountant_button = fields.Boolean('accountant visibility', default=False, compute="compute_button_visibility")
    doc_type = fields.Many2one(comodel_name='document.type', string='Document Type')
    # attachment_details = fields.One2many(comodel_name='tenant.request.documents',
    #                                      inverse_name='tenant_request_id',
    #                                      string='Documents')
    doc_ids = fields.Many2many(comodel_name='atheer.documents', relation='tenant_request_atheer_doc_rel',
                               column1='tenant_request_id', column2='atheer_documents_id',
                               string='Documents')
    # doc_ids = fields.Many2many('atheer.documents',
    #                            string='Documents')
    renew_button_visibility = fields.Boolean('Renewal Visibility', default=False, compute="compute_renew_visibility")
    installment_ids = fields.Many2many('property.rent.installment.collection', string='Installments', store=True)
    send_back_flag = fields.Boolean(default=False)
    accountant_flag = fields.Boolean(default=False)
    rent_amount_total = fields.Float('Total Amount', digits="Product Price")
    # is_property_rent = fields.Boolean('Is For rent', default=False)

    @api.onchange('rent_id')
    def onchange_rent_id(self):
        for rec in self:
            if rec.rent_id:
                rec.building_id = rec.rent_id.building
                rec.lease_from_date = rec.rent_id.from_date
                rec.lease_to_date = rec.rent_id.to_date
                rec.installment_schedule = rec.rent_id.installment_schedule
                rec.period = rec.rent_id.period
                rec.rent_amount_total = rec.rent_id.rent_total

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(TenantRequest, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                         submenu=False)
        form_view_id = self.env.ref('property_lease_management.view_client_information_form').id
        if res.get('view_id', False) == form_view_id and res.get('type', False) == 'form':
            doc = etree.XML(res['arch'])
            if doc:
                if not self.env.user.has_group('property_lease_management.group_property_user'):
                    node = doc.xpath("//field[@name='sales_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('property_lease_management.group_property_head'):
                    node = doc.xpath("//field[@name='sales_head_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('property_lease_management.group_property_accountant'):
                    node = doc.xpath("//field[@name='accountant_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                return res
        return res

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(TenantRequest, self).unlink()

    def compute_renew_visibility(self):
        """ visibility for new button """
        for rec in self:
            if rec.request_type == 'Renewal Request' and rec.state_renewal == 'approved':
                rec.renew_button_visibility = True
                new_rent_id = self.env['property.rent'].search([('tenant_request_renewal_id', '=', rec.id)], limit=1)
                if new_rent_id:
                    rec.renew_button_visibility = False
                    rec.new_rent_id = new_rent_id.id
            else:
                rec.renew_button_visibility = False

    def compute_new_rent_id(self):
        """ finding the new rent details """
        for rec in self:
            new_rent_id = self.env['property.rent'].search([('tenant_request_renewal_id', '=', rec.id)], limit=1)
            rec.new_rent_id = new_rent_id.id

    def onchange_doc_type(self):
        """ getting the document data while changing the doc type"""
        for rec in self:
            if rec.doc_type:
                # print(rec.doc_type)
                # data = self.env['atheer.documents'].search(['|', '|', ('partner_id', '=', rec.partner_id.id),
                #                                                 ('property_id', '=', rec.property_id.id),
                #                                                 ('building_id', '=', rec.building_id.id)])
                data = self.env['atheer.documents'].search([])
                # print(data, 'HLOOOOOOOO')
                if data:
                    attachments = data.filtered(lambda x: x.doc_type == rec.doc_type)
                    list_data = []
                    for att in attachments:
                        if not rec.attachment_details.filtered(lambda x: x.document_id.id == att.id):
                            list_data.append((0, 0, {'doc_type': att.doc_type.id,
                                                     'doc_no': att.doc_no,
                                                     'doc_dec': att.doc_dec,
                                                     'document_id': att.id,
                                                     'attachment_ids': att.attachment_ids,
                                                     'tenant_request_id': rec.id}))
                        rec.update({'attachment_details': list_data})
                    else:
                        raise ValidationError(_(
                            'The Document type "%s" have no documents please choose another document type/create new Document under the document type ') % rec.doc_type.name)
            else:
                raise ValidationError('Please Select Document Type')

    def compute_button_visibility(self):
        """ check button visibilities """
        for rec in self:
            if rec.state == 'Property Head':
                if rec.request_type == 'Renewal Request':
                    rec.approve_button = True
                    rec.accountant_button = False
                else:
                    rec.approve_button = False
                    rec.accountant_button = True
            else:
                rec.approve_button = False
                rec.accountant_button = False

    @api.depends('period', 'lease_from_date')
    def _compute_to_date(self):
        for record in self:
            if record.period and record.lease_from_date:
                lease_to_date = record.lease_from_date + relativedelta(months=+record.period)
                record.lease_to_date = lease_to_date - timedelta(1)
            else:
                record.lease_to_date = False

    def print_renewal_sanad(self):
        """ print the sanad report"""
        data = {
            'doc_ids': self.ids,
            'form': self.read()[0],
            'doc_model': 'tenant.request',
            'docs': self.id,
        }
        return self.env.ref('property_lease_management.renewal_sanad_report_tag').report_action(self)

    def print_renewal_commercial(self):
        """ print the commercial report """
        data = {
            'doc_ids': self.ids,
            'form': self.read()[0],
            'doc_model': 'tenant.request',
            'docs': self.id,
        }
        return self.env.ref('property_lease_management.renewal_commercial_report_tag').report_action(self)

    def send_email_document(self):
        for rec in self:
            # create ir.attachment based on the binery field in the attachment_detail
            attachment_ids = []
            for attachment_detail in rec.attachment_details:
                attachment_id = self.env['ir.attachment'].create({
                    'name': ("%s" % attachment_detail.doc_no),
                    'datas': attachment_detail.attachment_ids,
                    'res_model': 'tenant.request',
                    'res_id': 0,
                    'type': 'binary',
                    'tenant_request_id': self.id
                })
                attachment_ids.append(attachment_id.id)
        body = """<table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
                    <tr><td align="center"><table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;"> 
                    <tr>
                                        <td align="center" style="min-width: 590px;">
                                            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                                                <tr><td valign="middle">
                                                    <span style="font-size: 10px;">Hello</span><br/>
                                                    <span style="font-size: 20px; font-weight: bold;">
                                                        {tenant}
                                                    </span>
                                                </td><td valign="middle" align="right">
                                                    <img src="/logo.png?company={tenant_id.company_id.id}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" alt="{tenant_id.company_id.name}"/>
                                                </td></tr>
                                                <tr><td colspan="2" style="text-align:center;">
                                                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                                                </td></tr>
                                            </table>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center" style="min-width: 590px;">
                                            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                                                <tr><td valign="top" style="font-size: 13px;">
                                                    <div>
                                                        Dear {tenant},<br/><br/>
                                                        <br/>
                                                         <p> We are thankful to you for your consistent business relations with our company and would
                                                            appreciate it if you would look into the above matter as soon as possible. Thank you for 
                                                            your cooperation. We look forward to serve you for many years to come. </p>
                                                        <p>Should you have any questions, feel free to contact me at 79434432 from 8am to 4pm or 
                                                            e-mail me at raiya.amlak@gmail.com</p>
                                                            <p style="font-weight:bold;">Sincerely, Raiya Al-shaaili</p> 
                                                            <p style="font-weight:bold;">Assistant Property Manager In charger </p>

                                                        If you do not expect this, you can safely ignore this email.<br/><br/>
                                                        Thanks,

                                                    </div>
                                                </td></tr>
                                                <tr><td style="text-align:center;">
                                                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                                                </td></tr>
                                            </table>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center" style="min-width: 590px;">
                                            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
                                                <tr><td valign="middle" align="left">
                                                    {tenant_id.company_id.name}
                                                </td></tr>

                                            </table>
                                        </td>
                                    </tr>

        """.format(lease=self.display_name, tenant=self.partner_id.name, tenant_id=self.partner_id,
                   property=self.property_id.name, date=self.to_date)
        return {
            'name': _("Send Email Document"),
            'view_mode': 'form',
            'view_id': self.env.ref('property_lease_management.send_email_document_view_form').id,
            'view_type': 'form',
            'tag': 'reload',
            'res_model': 'send.email.document',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'stay_open': True,
            'domain': '[]',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_subject': str(self.rent_id.name) + '-' + str(self.partner_id.name),
                'default_attachment_ids': attachment_ids,
                'default_message': body
            }
        }

    def renew_contract(self):
        """ renewing the contract """
        # dummy, view_id = self.env['ir.model.data'].get_object_reference('property_lease_management',
        #                                                                 'view_rent_form')
        view_ref = self.env.ref('property_lease_management.view_rent_form')
        view_id = view_ref and view_ref.id or False,

        rent_obj = self.rent_id
        end_date = self.lease_to_date
        # next_day = end_date + relativedelta(days=1)
        # next_day = datetime.strftime(next_day, "%Y-%m-%d")
        next_day = self.lease_from_date
        return {
            'name': _("Rent Agreement"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'tag': 'reload',
            'res_model': 'property.rent',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            # 'target': 'new',
            'stay_open': True,
            'domain': '[]',
            'context': {
                'default_building': rent_obj.building.id,
                'default_residing_tenant': rent_obj.residing_tenant,
                'default_residing_since': rent_obj.residing_since,
                'default_security_deposit': rent_obj.security_deposit,
                'default_partner_id': rent_obj.partner_id.id,
                'default_property_id': rent_obj.property_id.id,
                'default_account_id': rent_obj.account_id.id,
                'default_journal_id': rent_obj.journal_id.id,
                'default_agreed_rent_amount': rent_obj.agreed_rent_amount,
                'default_revenue_account': rent_obj.revenue_account.id,
                'default_currency_id': rent_obj.currency_id.id,
                'default_company_id': rent_obj.company_id.id,
                'default_reference_id': rent_obj.id,
                'default_installment_schedule': self.installment_schedule,
                'default_period': self.period,
                'default_from_date': next_day,
                'default_to_date': self.lease_from_date,
                'default_state': 'draft',
                'default_tenant_request_renewal_id': self.id
            }
        }

    @api.onchange('lease_from_date', 'lease_to_date')
    def _compute_year_month_days(self):
        """ compute the duration """
        for rec in self:
            # print(rec, '_compute_year_month_days')
            if rec.lease_from_date and rec.lease_to_date and rec.request_type == 'Renewal Request':
                lease_to_date = rec.lease_to_date + timedelta(days=1)
                diff = relativedelta(lease_to_date, rec.lease_from_date)
                years = diff.years
                months = diff.months
                days = diff.days
                rec.year_month_days = "{} years {} months {} days".format(years, months, days)

            elif rec.lease_from_date and rec.lease_to_date and rec.request_type == 'Vacate Request':
                lease_to_date = rec.lease_to_date + timedelta(days=1)
                diff = relativedelta(lease_to_date, rec.lease_from_date)
                years = diff.years
                months = diff.months
                days = diff.days
                rec.year_month_days = "{} years {} months {} days".format(years, months, days)

            else:
                rec.year_month_days = " "

    @api.model
    def create(self, vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('tenant.request') or _('TenantRequest')
        return super(TenantRequest, self).create(vals)

    @api.constrains('no_of_month')
    def constrains_no_of_month(self):
        for rec in self:
            if rec.no_of_month > 3:
                raise ValidationError("The number of months cannot be greater than 3 months.")

    @api.onchange('request_type')
    def onchange_request_type(self):
        """ find the current rent """
        for rec in self:
            # clearing the other fields
            rec.lease_from_date = ""
            rec.period = 0
            rec.installment_schedule = False
            rec.rent_amount_total = False
            # rec.year_month_days = ""
            rec.from_date = ""
            rec.to_date = ""
            rec.effective_date = ""
            rec.vacate_date = ""
            rec.no_of_month = 1
            rec.proposed_rent = 0.0
            rec.approved_rent = 0.0
            rec.check_ids = [(5, 0, 0)]
            if rec.request_type == 'Vacate Request':
                rec.lease_from_date = rec.rent_id.from_date
                rec.lease_to_date = rec.rent_id.to_date
                rec.installment_schedule = rec.rent_id.installment_schedule
                rec.period = rec.rent_id.period
                rec.rent_amount_total = rec.rent_id.rent_total

            if rec.request_type == 'Rent Reduction':
                rec.current_rent = rec.rent_id.agreed_rent_amount
            if rec.request_type == 'Renewal Request':
                next_day = rec.rent_id.to_date + relativedelta(days=1)
                rec.lease_from_date = datetime.strftime(next_day, "%Y-%m-%d")

    def move_to_sales_head(self):
        """ move from draft to Property Head """
        for rec in self:
            if rec.request_type == 'Cheque holding':
                property_installment_ids = self.env['property.rent.installment.collection'].search_count(
                    [('rent_id', '=', rec.rent_id.id), ('state', '!=', 'paid'), ('date', '<', rec.from_date)])
                if property_installment_ids > 3:
                    rec.state = 'Property Head'
                    rec.state_renewal = 'Property Head'
                    rec.send_back_flag = False
                    # notification_obj = self.env['atheer.notification']
                    # notification_obj._send_instant_notify(title="Tenant Request",
                    #                                       message='Pending approval for ' + str(rec.request_type),
                    #                                       action=self.env.ref(
                    #                                           'property_lease_management.action_tenant_request').id,
                    #                                       domain=[['id', '=', rec.id]],
                    #                                       user_type="groups",
                    #                                       recipient_ids=[self.env.ref(
                    #                                           'property_lease_management.group_property_head').id])
                else:
                    rec.state = 'Accountant'
                    rec.send_back_flag = False
                    # notification_obj = self.env['atheer.notification']
                    # notification_obj._send_instant_notify(title="Tenant Request",
                    #                                       message='Pending approval for ' + str(rec.request_type),
                    #                                       action=self.env.ref(
                    #                                           'property_lease_management.action_tenant_request').id,
                    #                                       domain=[['id', '=', rec.id]],
                    #                                       user_type="groups",
                    #                                       recipient_ids=[self.env.ref(
                    #                                           'property_lease_management.group_property_accountant').id])
            else:
                rec.state = 'Property Head'
                rec.state_renewal = 'Property Head'
                rec.send_back_flag = False
                # notification_obj = self.env['atheer.notification']
                # notification_obj._send_instant_notify(title="Tenant Request",
                #                                       message='Pending approval for ' + str(rec.request_type),
                #                                       action=self.env.ref(
                #                                           'property_lease_management.action_tenant_request').id,
                #                                       domain=[['id', '=', rec.id]],
                #                                       user_type="groups",
                #                                       recipient_ids=[self.env.ref(
                #                                           'property_lease_management.group_property_head').id])

    def sales_head_approve(self):
        """ move from Property Head to Accountant """
        for rec in self:
            print(rec.approved_rent, 'rec.approved_rent')
            if rec.approved_rent <= 0:
                raise ValidationError('Rent Proposed Amount Should be Greater than  zero')
            rec.write({'state': 'Accountant'})
            rec.send_back_flag = False
            rec.accountant_flag = True
            # notification_obj = self.env['atheer.notification']
            # notification_obj._send_instant_notify(title="Tenant Request",
            #                                       message='Pending approval for ' + str(rec.request_type),
            #                                       action=self.env.ref(
            #                                           'property_lease_management.action_tenant_request').id,
            #                                       domain=[['id', '=', rec.id]],
            #                                       user_type="groups",
            #                                       recipient_ids=[self.env.ref(
            #                                           'property_lease_management.group_property_accountant').id])

    def renewal_approve(self):
        """ move from Property Head to Approved """
        for rec in self:
            rec.state = 'approved'
            rec.state_renewal = 'approved'
            rec.p_head_approved_by = self.env.user.id
            rec.p_head_approved_date = fields.date.today()
            rec.accountant_approve()
            rec.send_back_flag = False

    def accountant_approve(self):
        """ move from Accountant to Approved """
        for rec in self:
            if rec.request_type == 'Rent Reduction':
                if not rec.effective_date:
                    raise ValidationError('You must fill the effective date')
                if not rec.approved_rent:
                    raise ValidationError('Approved rent cannot be zero')
                rec.rent_id.agreed_rent_amount = rec.approved_rent
                self.env['tenant.rent.history'].sudo().create({'from_date': rec.effective_date,
                                                               'to_date': rec.rent_id.to_date,
                                                               'rent_id': rec.rent_id.id,
                                                               'current_rent': rec.current_rent,
                                                               'proposed_rent': rec.proposed_rent,
                                                               'approved_rent': rec.approved_rent,
                                                               'tenant_request_id': rec.id})
                invoices = rec.rent_id.invoice_ids.filtered(lambda x: (x.invoice_date >= rec.effective_date))
                for invoice in invoices:
                    for line in invoice.invoice_line_ids:
                        line.with_context(check_move_validity=False).write({'price_unit': rec.approved_rent})
                    invoice.with_context(check_move_validity=False)._compute_tax_totals()
                for collection in rec.rent_id.collection_ids.filtered(lambda x: (x.date >= rec.effective_date)):
                    collection.amount = rec.approved_rent
                    collection.residual = collection.invoice_id.amount_residual
                    collection.amount_total = collection.invoice_id.amount_total
            # sending the mail template to signature
            if rec.request_type == 'Vacate Request Agreement':
                subject = "Vacate Agreement"
            elif rec.request_type == 'Rent Reduction':
                subject = "Rent Reduction Agreement"
            elif rec.request_type == 'Cheque holding':
                subject = "Cheque Holding Agreement"
            elif rec.request_type == 'Renewal Request':
                subject = "Rent Agreement Renewal Request"
            else:
                subject = " "
            # giving the default role as 1 as per odoo code
            # role = self.env['sign.item.role'].sudo().search([('name', '=', 'Tenant Request Role')])
            # if not role:
            #     role = self.env['sign.item.role'].sudo().create({'name': 'Tenant Request Role'})
            for template in rec.tenant_esignature_ids:
                for partner in template.partner_ids:
                    message = "Kindly sign the document"
                    sign_obj = self.env['sign.send.request'].sudo().create(
                        {'signer_ids': [(0, 0, {'partner_id': partner.id, 'role_id': 1})],
                         'template_id': template.signature_template.id,
                         'subject': subject,
                         'message': message,
                         'signers_count': 1,
                         'filename': template.signature_template.name})
                    res = sign_obj.create_request()
                    request = self.env['sign.request'].browse(res['id'])
            if rec.request_type == 'waiver_of_rent':
                for installment in rec.installment_ids:
                    installment.state = 'waived'
                    installment.invoice_id.button_cancel()
            rec.state = 'approved'
            rec.send_back_flag = False

    def send_back(self):
        """ move to Property Head stage """
        for rec in self:
            # state_map = {
            #     'accountant': 'property_hed',
            #     'property_hed': 'draft',
            #     # 'waiting': 'draft',
            # }
            # new_state = state_map.get(rec.state)
            # if new_state:
            #     rec.state = new_state

            if rec.request_type == 'waiver_of_rent':
                for installment in rec.installment_ids:
                    installment.state = 'draft0'
                    installment.invoice_id.button_draft()
            rec.state = 'Property Head'
            rec.state_renewal = 'Property Head'
            rec.send_back_flag = True

    def send_back_renewal(self):
        """ move from Property Head stage to draft"""
        for rec in self:
            rec.state = 'draft'
            rec.state_renewal = 'draft'
            rec.send_back_flag = True

    def move_to_refuse(self):
        """ move to refused stage """
        for rec in self:
            rec.state = 'refused'
            rec.state_renewal = 'refused'
            rec.send_back_flag = False


class TenantCheck(models.Model):
    _name = 'tenant.check'
    _description = 'Tenant Cheque'

    check_no = fields.Char('Cheque no')
    check_bearer = fields.Char('Cheque Bearer')
    check_date = fields.Date('Cheque Date')
    attachment_ids = fields.Binary(string='Attachments')
    tenant_request_id = fields.Many2one('tenant.request')


# Not Using instead of this class we are using atheer documents
# class TenantRequestDocuments(models.Model):
#     _name = 'tenant.request.documents'
#     _description = 'Tenant Requested Documents'
#     _rec_name = 'tenant_request_id'
#
#     doc_type = fields.Many2one(comodel_name='document.type', string='Document Type')
#     doc_no = fields.Char(string='Document NO.')
#     doc_dec = fields.Text(string='Description')
#     file_name = fields.Char(string='File Name')
#     attachment_ids = fields.Binary(string='Attachments')
#     tenant_request_id = fields.Many2one('tenant.request')
#     document_id = fields.Many2one('atheer.documents')


class TenantRentHistory(models.Model):
    _name = 'tenant.rent.history'
    _description = 'Tenant Rent History'
    _rec_name = 'rent_id'

    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    rent_id = fields.Many2one('property.rent', string='Rent Agreement')
    building = fields.Many2one(comodel_name='property.building', string="Building", related="rent_id.building",
                               store=True)
    property_id = fields.Many2one(comodel_name='property.property', string="Unit", related="rent_id.property_id",
                                  store=True)
    tenant_id = fields.Many2one(comodel_name='res.partner', string="Tenant", related="rent_id.partner_id", store=True)
    current_rent = fields.Float('Previous Rent', digits='Property')
    proposed_rent = fields.Float('Rent Proposed by Tenant', digits='Property')
    approved_rent = fields.Float('Rent Proposed by Sales Head', digits='Property')
    tenant_request_id = fields.Many2one('tenant.request', 'Tenant Requests')


class TenantSignatureTemplate(models.Model):
    _name = 'tenant.signature.template'
    _description = 'Tenant Signature Template'

    tenant_request_id = fields.Many2one('tenant.request', 'Tenant Requests')
    signature_template = fields.Many2one(comodel_name='sign.template', string='Signature Template')
    partner_ids = fields.Many2many('res.partner', 'signature_id', column2='partner_id',
                                   string='Send to')
