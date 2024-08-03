# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from lxml import etree
import json


class ClientInformation(models.Model):
    _name = 'client.information'
    _rec_name = 'sequence'
    _description = 'Client Information'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'resource.mixin']

    sequence = fields.Char(string='Sequence', readonly=True)
    date = fields.Date("Date", index=True,
                       copy=False, default=fields.Date.context_today)

    building = fields.Many2one(comodel_name='property.building', string='Building', required=True)
    property_id = fields.Many2one(comodel_name='property.property',
                                  string='Unit', ondelete='cascade', domain="[('parent_building','=',building),('state', '=', 'open')]",
                                  required=True)
    name = fields.Char('Name', required=True)
    marital = fields.Selection([('single', 'Single'),
                                ('married', 'Married')],
                               'Marital Status')
    tenancy_agreement = fields.Char('Tenancy Period', required=True)
    nationality = fields.Many2one(comodel_name='res.country', string='Nationality')
    monthly_rental = fields.Char('Monthly Rental', required=True)
    resident_card = fields.Char('Resident Card No', required=True)
    # driving_license = fields.Char('Driving License No')
    passport = fields.Char('Passport No')
    passport_expiry_date = fields.Date(string='Expiry Date')
    email = fields.Char('Email', required=True)
    mobile = fields.Char(string='Mobile No', required=True)
    mobile_alternate = fields.Char(string='Alternate No')
    office_no = fields.Char(string='Office No')
    # fax_no = fields.Char(string='Fax No')
    company = fields.Char(string='Company ')
    position = fields.Char(string='Position')
    company_address = fields.Text(string='Company Address', help="Company Address & PO Box No")
    sales_remarks = fields.Text('Sales Remarks')
    sales_head_remarks = fields.Text('Sales Head Remarks')
    property_division_remarks = fields.Text('Property Division Remarks')
    doc_ids = fields.Many2many('atheer.documents',
                               string='Documents')
    sales_coordinator = fields.Many2one('res.users', 'Sales Co Coordinator')
    approved_by = fields.Many2one('res.users', 'Approved By')
    approved_date = fields.Date(string='Approved Date')
    referred_by = fields.Many2one('res.partner', 'Referred By')
    partner_id = fields.Many2one('res.partner', 'Partner')
    referrals = fields.One2many('referral.information', 'client_info', string="Referrals")
    state = fields.Selection([('draft', 'Draft'),
                              ('waiting', 'Sales Head'),
                              ('approved', 'Property Division'),
                              ('refused', 'Refused')], tracking=True, default='draft')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)
    send_back_flag = fields.Boolean(default=False)
    payment_status = fields.Char(string='Payment Status')
    cr_number = fields.Char(string='CR Number')
    commercial_activities = fields.Char(string='Commercial Activities')

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(ClientInformation, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                             submenu=False)
        form_view_id = self.env.ref('property_lease_management.view_client_information_form').id
        if res.get('view_id', False) == form_view_id and res.get('type', False) == 'form':
            doc = etree.XML(res['arch'])
            if doc:
                if not self.env.user.has_group('property_lease_management.group_property_sales_user'):
                    node = doc.xpath("//field[@name='sales_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('property_lease_management.group_property_sales_admin'):
                    node = doc.xpath("//field[@name='sales_head_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group(
                        'property_lease_management.group_property_user') or not self.env.user.has_group(
                    'property_lease_management.group_property_head'):
                    node = doc.xpath("//field[@name='property_division_remarks']")[0]
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
                raise ValidationError('At this state, it is not possible to delete this record. ')
            return super(ClientInformation, self).unlink()

    @api.model
    def create(self, vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('client.information') or _('ClientInformation')
        return super(ClientInformation, self).create(vals)

    def request_for_approval(self):
        """ move from draft to waiting """
        for rec in self:
            rec.state = 'waiting'
            rec.send_back_flag = False
            # notification_obj = self.env['atheer.notification']
            # notification_obj._send_instant_notify(title="Pending Client Approval",
            #                                       message='Waiting for approval of ' + ' ' + str(
            #                                           rec.name),
            #                                       action=self.env.ref(
            #                                           'property_lease_management.action_client_information').id,
            #                                       domain=[['id', '=', rec.id]],
            #                                       user_type="groups",
            #                                       recipient_ids=[self.env.ref(
            #                                           'property_lease_management.group_property_sales_admin').id])

    def send_back(self):
        """ move to refused stage """
        for rec in self:
            rec.state = 'draft'
            rec.send_back_flag = True

    def move_to_refuse(self):
        """ move to refused stage """
        for rec in self:
            rec.state = 'refused'
            rec.send_back_flag = False

    def client_approve(self):
        """ approve the client information """
        for rec in self:
            rec.state = 'approved'
            rec.send_back_flag = False
            rec.approved_by = self.env.user.id
            rec.approved_date = fields.date.today()
            details = {
                'name': rec.name,
                'phone': rec.mobile_alternate,
                'mobile': rec.mobile,
                'email': rec.email,
                'country_id': rec.nationality.id,
                'is_company': True,
                'tenant': True,
                'id_passport': rec.passport,
            }
            rec.partner_id = self.env['res.partner'].sudo().create(details)
            # notification_obj = self.env['atheer.notification']
            # notification_obj._send_instant_notify(title="Completed Client Approval",
            #                                       message='Completed approval of ' + str(rec.name),
            #                                       action=self.env.ref(
            #                                           'property_lease_management.action_client_information').id,
            #                                       domain=[['id', '=', rec.id]],
            #                                       user_type="groups",
            #                                       recipient_ids=[self.env.ref(
            #                                           'property_lease_management.group_property_user').id])

    def muncipality_informations_link(self):
        return {
            "type": "ir.actions.act_url",
            "url": 'https://isupport.mm.gov.om/OA_HTML/xxmmNewRCFormOnlineAll.jsp',
            "target": "new"
        }

    def rent_agreement(self):
        for rec in self:
            return {
                'name': _("Rent Agreement"),
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'property.rent',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'current',
                'domain': '[]',
                'context': {
                    'default_building': rec.building.id,
                    'default_property_id': rec.property_id.id,
                    'default_partner_id': rec.partner_id.id,
                }
            }


# class ReferralInformation(models.Model):
#     _name = 'referral.information'
#     _description = 'Referral Information'
#
#     name = fields.Char('Name', required=True)
#     contact_no = fields.Char('Contact No', required=True)
#     client_info = fields.Many2one('client.information', 'Client Information')
