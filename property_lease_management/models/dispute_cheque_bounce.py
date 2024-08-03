# -*- coding: utf-8 -*-

import calendar
from odoo import SUPERUSER_ID
from odoo import fields, models, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

from lxml import etree
import json


class DisputeChequeBounce(models.Model):
    _name = 'dispute.cheque.bounce'
    _rec_name = 'sequence'
    _description = 'Dispute Management'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Char(string='Sequence', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Tenant', required=True, domain=[('tenant', '=', True)])
    rent_id = fields.Many2one(comodel_name='property.rent', string='Rent', required=True, tracking=True,
                              check_company=True )
    building_id = fields.Many2one('property.building', 'Building', store=True, related="rent_id.building")
    building_area_id = fields.Many2one('building.area', 'Building Area', related="building_id.building_area")
    property_id = fields.Many2one(comodel_name='property.property', string='Unit', store=True,
                                  related="rent_id.property_id")
    lease_from_date = fields.Date(string='Lease Start', related="rent_id.from_date")
    lease_to_date = fields.Date(string='Lease End', related="rent_id.to_date")
    period = fields.Integer(string='Rental Period', related="rent_id.period")
    installment_schedule = fields.Selection(related="rent_id.installment_schedule", string='Installment Schedule',
                                            tracking=True)
    account_remarks = fields.Text('Accounts Remarks')
    property_remarks = fields.Text('Property Remarks')
    created_date = fields.Date('Created Date')
    requested_date = fields.Date('Requested Date')
    response_date = fields.Date('Tenant Response Date')
    approved_date = fields.Date('Approved Date')
    notification = fields.Boolean('Email notification', default=False)
    year_month_days = fields.Char('Duration', related="rent_id.year_month_days")
    security_deposit = fields.Float(string='Security Deposit', related='rent_id.security_deposit')
    agreed_rent_amount = fields.Float(string='Agreed Rent Amount', related='rent_id.agreed_rent_amount')
    bounced_cheque_ids = fields.One2many('property.bounced.cheque', 'dispute_id', 'Bounced Cheques')
    notification_ids = fields.One2many('property.notification', 'dispute_id', 'Notifications')
    state = fields.Selection([('draft', 'Accounts'),
                              ('waiting', 'Property Division'),
                              ('approved', 'Approved'),
                              ('resolved', 'Resolved'),
                              ('refused', 'Refused')], tracking=True, default='draft')
    send_back_flag = fields.Boolean(default=False)
    notification_1 = fields.Html("Notification 1")
    notification_2 = fields.Html("Notification 2")
    notification_3 = fields.Html("Notification 3")
    notes = fields.Text("Description")
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company, )

    @api.onchange('rent_id')
    def onchange_rent_agreement(self):
        for rec in self:
            print('@#$%^&*******************')
            if rec.rent_id:
                print('*()************ASDFGH')
                self.partner_id = rec.rent_id.partner_id

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(DisputeChequeBounce, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                               submenu=False)
        form_view_id = self.env.ref('property_lease_management.view_client_information_form').id
        if res.get('view_id', False) == form_view_id and res.get('type', False) == 'form':
            doc = etree.XML(res['arch'])
            if doc:
                if not self.env.user.has_group(
                        'property_lease_management.group_property_user') or not self.env.user.has_group(
                    'property_lease_management.group_property_head'):
                    node = doc.xpath("//field[@name='property_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('property_lease_management.group_property_accountant'):
                    node = doc.xpath("//field[@name='account_remarks']")[0]
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
            return super(DisputeChequeBounce, self).unlink()

    @api.onchange('partner_id')
    def _get_rent_info(self):
        """ setting domain for rent """
        domain = []
        for rec in self:
            if not rec.notification_1:
                body = """ 
                                            <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
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
                                                                                
                                                                                <p> </p>
                                                                                <p>In reference to our lease agreement No.{lease}, we would like to remind you that as to this date we
                                                                                    have not received the rental payments for the months of {month} amounting to <strong> {amount_in_word} 
                                                                                    (RO {amount}) </strong>.</p><p></p>
                                                                                <p>Please settle the amount within seven (7) days from the date of this letter.</p><p></p>
                                                                                <p>We highly value your tenancy and hope to gain your cooperation in paying your monthly rent on due 
                                                                                date. Should you have any questions feel free to contact me at 24499537</p><p></p>
                                                                                <p>Thank you for your prompt attention to this matter.</p>

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
                                    """
                rec.notification_1 = body
            if not rec.notification_2:
                body_2 = """ 
                                    <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
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
                                                                                
                                                   <p> </p>
                                                   <p>Further to my letter {previous_date}, regarding your unpaid rent of <strong>
                                                   {amount_in_word} (RO {amount})</strong>, the amount remain outstanding. </p>
                                                   <p></p>
                                                   <p>As this amount is now seriously overdue, please pay within <strong> seven(7) days</strong>
                                                   from the receipt of this letter.</p><p></p>
                                                   <p>We highly value your tenancy and hope to gain your cooperation in paying your rent on due
                                                    date. Should you have any questions, feel free to contact me at 24499537.</p><p></p>
                                                    <p>Thank you.</p>

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
                                    """
                rec.notification_2 = body_2
            if not rec.notification_3:
                body_3 = """ <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
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
                                                                                
                                                                                <p> </p>
                                                                                <p>We are writing concerning the amount of RO {amount} which was due to be paid
                                                                                    on {month} and, despite numerous requests for payment, remains outstanding and
                                                                                    twice a time your cheque is bounce from bank as well.</p><p></p>

                                                                                <p>If this account is not resolved by the specified date we reserve the right
                                                                                    to commence legal proceedings to recover the debt without further notice to 
                                                                                    you, and you may be responsible for any associated legal fees or collection 
                                                                                    costs. </p><p></p>
                                                                                <p>If you wish to prevent this, please contact the undersigned as a matter of 
                                                                                urgency and settle your account before the above date.</p><p></p>
                                                                                <p>Regards</p>

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
                                    """
                rec.notification_3 = body_3
            # if rec.partner_id:
            #     rents = self.env['property.rent'].search([('partner_id', '=', rec.partner_id.id)])
            #     return {'domain': {'rent_id': [('id', 'in', rents.ids)]}}
            # else:
            #     domain = []
        return domain

    @api.model
    def create(self, vals):
        vals['created_date'] = fields.date.today()
        vals['sequence'] = self.env['ir.sequence'].next_by_code('dispute.management') or _('Dispute Management')
        body = """ 
                            <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
                            <tr><td align="center"><table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;"> 
                            <tr>
                                                <td align="center" style="min-width: 590px;">
                                                    <table border="0" cellpadding="0" cellspacing="0" width="590"
                                                     style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
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
                                                            
                                                                <p> </p>
                                                                <p>In reference to our lease agreement No.{lease}, we would like to remind you that as to this date we
                                                                    have not received the rental payments for the months of {month} amounting to <strong> {amount_in_word} 
                                                                    (RO {amount}) </strong>.</p><p></p>
                                                                <p>Please settle the amount within seven (7) days from the date of this letter.</p><p></p>
                                                                <p>We highly value your tenancy and hope to gain your cooperation in paying your monthly rent on due 
                                                                date. Should you have any questions feel free to contact me at 24499537</p><p></p>
                                                                <p>Thank you for your prompt attention to this matter.</p>

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
                    """
        vals['notification_1'] = body
        body_2 = """ 
                    <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
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
                                                               
                                   <p> </p>
                                   <p>Further to my letter {previous_date}, regarding your unpaid rent of <strong>
                                   {amount_in_word} (RO {amount})</strong>, the amount remain outstanding. </p>
                                   <p></p>
                                   <p>As this amount is now seriously overdue, please pay within <strong> seven(7) days</strong>
                                   from the receipt of this letter.</p><p></p>
                                   <p>We highly value your tenancy and hope to gain your cooperation in paying your rent on due
                                    date. Should you have any questions, feel free to contact me at 24499537.</p><p></p>
                                    <p>Thank you.</p>

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
                    """
        vals['notification_2'] = body_2
        body_3 = """ <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
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
                                                                
                                                                <p> </p>
                                                                <p>We are writing concerning the amount of RO {amount} which was due to be paid
                                                                    on {month} and, despite numerous requests for payment, remains outstanding and
                                                                    twice a time your cheque is bounce from bank as well.</p><p></p>

                                                                <p>If this account is not resolved by the specified date we reserve the right
                                                                    to commence legal proceedings to recover the debt without further notice to 
                                                                    you, and you may be responsible for any associated legal fees or collection 
                                                                    costs. </p><p></p>
                                                                <p>If you wish to prevent this, please contact the undersigned as a matter of 
                                                                urgency and settle your account before the above date.</p><p></p>
                                                                <p>Regards</p>

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
                    """
        vals['notification_3'] = body_3
        return super(DisputeChequeBounce, self).create(vals)

    # @api.onchange('rent_id', 'partner_id')
    def get_bounced_cheques(self):
        """ get the bounced check details """
        for rec in self:
            rec.bounced_cheque_ids = [(5, 0, 0)]
            if rec.partner_id and rec.rent_id:
                cheques = self.env['property.bounced.cheque'].sudo().search([('rent_id', '=', rec.rent_id.id),
                                                                             ('paid', '=', False)])
                for cheque in cheques:
                    cheque.dispute_id = rec.id

    def send_to_property_head(self):
        """ send to property head """
        for rec in self:
            rec.send_back_flag = False
            rec.state = 'waiting'
            rec.notification = True
            rec.requested_date = fields.date.today()
            # notification_obj = self.env['atheer.notification']
            # if not rec.notification_1:
            #     body = """
            #                                 <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
            #                                 <tr><td align="center"><table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
            #                                 <tr>
            #                                                     <td align="center" style="min-width: 590px;">
            #                                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
            #                                                             <tr><td valign="middle">
            #                                                                 <span style="font-size: 10px;">Hello</span><br/>
            #                                                                 <span style="font-size: 20px; font-weight: bold;">
            #                                                                     {tenant}
            #                                                                 </span>
            #                                                             </td><td valign="middle" align="right">
            #                                                                 <img src="/logo.png?company={tenant_id.company_id.id}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" alt="{tenant_id.company_id.name}"/>
            #                                                             </td></tr>
            #                                                             <tr><td colspan="2" style="text-align:center;">
            #                                                               <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
            #                                                             </td></tr>
            #                                                         </table>
            #                                                     </td>
            #                                                 </tr>
            #                                                 <tr>
            #                                                     <td align="center" style="min-width: 590px;">
            #                                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
            #                                                             <tr><td valign="top" style="font-size: 13px;">
            #                                                                 <div>
            #                                                                     <p> </p>
            #                                                                     <p>In reference to our lease agreement No.{lease}, we would like to remind you that as to this date we
            #                                                                         have not received the rental payments for the months of {month} amounting to <strong> {amount_in_word}
            #                                                                         (RO {amount}) </strong>.</p><p></p>
            #                                                                     <p>Please settle the amount within seven (7) days from the date of this letter.</p><p></p>
            #                                                                     <p>We highly value your tenancy and hope to gain your cooperation in paying your monthly rent on due
            #                                                                     date. Should you have any questions feel free to contact me at 24499537</p><p></p>
            #                                                                     <p>Thank you for your prompt attention to this matter.</p>
            #
            #                                                                 </div>
            #                                                             </td></tr>
            #                                                             <tr><td style="text-align:center;">
            #                                                               <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
            #                                                             </td></tr>
            #                                                         </table>
            #                                                     </td>
            #                                                 </tr>
            #                                                 <tr>
            #                                                     <td align="center" style="min-width: 590px;">
            #                                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
            #                                                             <tr><td valign="middle" align="left">
            #                                                                 {tenant_id.company_id.name}
            #                                                             </td></tr>
            #
            #                                                         </table>
            #                                                     </td>
            #                                                 </tr>
            #                         """
            #     rec.notification_1 = body
            # if not rec.notification_2:
            #     body_2 = """
            #                         <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
            #                                 <tr><td align="center"><table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
            #                                 <tr>
            #                                                     <td align="center" style="min-width: 590px;">
            #                                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
            #                                                             <tr><td valign="middle">
            #                                                                 <span style="font-size: 10px;">Hello</span><br/>
            #                                                                 <span style="font-size: 20px; font-weight: bold;">
            #                                                                     {tenant}
            #                                                                 </span>
            #                                                             </td><td valign="middle" align="right">
            #                                                                 <img src="/logo.png?company={tenant_id.company_id.id}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" alt="{tenant_id.company_id.name}"/>
            #                                                             </td></tr>
            #                                                             <tr><td colspan="2" style="text-align:center;">
            #                                                               <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
            #                                                             </td></tr>
            #                                                         </table>
            #                                                     </td>
            #                                                 </tr>
            #                                                 <tr>
            #                                                     <td align="center" style="min-width: 590px;">
            #                                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
            #                                                             <tr><td valign="top" style="font-size: 13px;">
            #                                                                 <div>
            #
            #                                        <p> </p>
            #                                        <p>Further to my letter {previous_date}, regarding your unpaid rent of <strong>
            #                                        {amount_in_word} (RO {amount})</strong>, the amount remain outstanding. </p>
            #                                        <p></p>
            #                                        <p>As this amount is now seriously overdue, please pay within <strong> seven(7) days</strong>
            #                                        from the receipt of this letter.</p><p></p>
            #                                        <p>We highly value your tenancy and hope to gain your cooperation in paying your rent on due
            #                                         date. Should you have any questions, feel free to contact me at 24499537.</p><p></p>
            #                                         <p>Thank you.</p>
            #
            #                                                                 </div>
            #                                                             </td></tr>
            #                                                             <tr><td style="text-align:center;">
            #                                                               <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
            #                                                             </td></tr>
            #                                                         </table>
            #                                                     </td>
            #                                                 </tr>
            #                                                 <tr>
            #                                                     <td align="center" style="min-width: 590px;">
            #                                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
            #                                                             <tr><td valign="middle" align="left">
            #                                                                 {tenant_id.company_id.name}
            #                                                             </td></tr>
            #
            #                                                         </table>
            #                                                     </td>
            #                                                 </tr>
            #                         """
            #     rec.notification_2 = body_2
            # if not rec.notification_3:
            #     body_3 = """ <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
            #                                 <tr><td align="center"><table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
            #                                 <tr>
            #                                                     <td align="center" style="min-width: 590px;">
            #                                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
            #                                                             <tr><td valign="middle">
            #                                                                 <span style="font-size: 10px;">Hello</span><br/>
            #                                                                 <span style="font-size: 20px; font-weight: bold;">
            #                                                                     {tenant}
            #                                                                 </span>
            #                                                             </td><td valign="middle" align="right">
            #                                                                 <img src="/logo.png?company={tenant_id.company_id.id}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" alt="{tenant_id.company_id.name}"/>
            #                                                             </td></tr>
            #                                                             <tr><td colspan="2" style="text-align:center;">
            #                                                               <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
            #                                                             </td></tr>
            #                                                         </table>
            #                                                     </td>
            #                                                 </tr>
            #                                                 <tr>
            #                                                     <td align="center" style="min-width: 590px;">
            #                                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
            #                                                             <tr><td valign="top" style="font-size: 13px;">
            #                                                                 <div>
            #
            #                                                                     <p> </p>
            #                                                                     <p>We are writing concerning the amount of RO {amount} which was due to be paid
            #                                                                         on {month} and, despite numerous requests for payment, remains outstanding and
            #                                                                         twice a time your cheque is bounce from bank as well.</p><p></p>
            #
            #                                                                     <p>If this account is not resolved by the specified date we reserve the right
            #                                                                         to commence legal proceedings to recover the debt without further notice to
            #                                                                         you, and you may be responsible for any associated legal fees or collection
            #                                                                         costs. </p><p></p>
            #                                                                     <p>If you wish to prevent this, please contact the undersigned as a matter of
            #                                                                     urgency and settle your account before the above date.</p><p></p>
            #                                                                     <p>Regards</p>
            #
            #                                                                 </div>
            #                                                             </td></tr>
            #                                                             <tr><td style="text-align:center;">
            #                                                               <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
            #                                                             </td></tr>
            #                                                         </table>
            #                                                     </td>
            #                                                 </tr>
            #                                                 <tr>
            #                                                     <td align="center" style="min-width: 590px;">
            #                                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
            #                                                             <tr><td valign="middle" align="left">
            #                                                                 {tenant_id.company_id.name}
            #                                                             </td></tr>
            #
            #                                                         </table>
            #                                                     </td>
            #                                                 </tr>
            #                         """
            #     rec.notification_3 = body_3
            # notification_obj._send_instant_notify(title="Dispute Management",
            #                                       message='Pending approval for Dispute Action of ' + str(
            #                                           rec.partner_id.name),
            #                                       action=self.env.ref(
            #                                           'property_lease_management.action_dispute_cheque_bounce').id,
            #                                       domain=[['id', '=', rec.id]],
            #                                       user_type="groups",
            #                                       recipient_ids=[self.env.ref(
            #                                           'property_lease_management.group_property_head').id])
            # notification_obj._send_instant_notify(title="Dispute Management",
            #                                       message='Pending approval for Dispute Action of ' + str(
            #                                           rec.partner_id.name),
            #                                       action=self.env.ref(
            #                                           'property_lease_management.action_dispute_cheque_bounce').id,
            #                                       domain=[['id', '=', rec.id]],
            #                                       user_type="groups",
            #                                       recipient_ids=[self.env.ref(
            #                                           'property_lease_management.group_property_user').id])

    def stop_notification(self):
        """ stop email notification """
        for rec in self:
            rec.notification = False

    def approve(self):
        """ approving the dispute  """
        for rec in self:
            rec.state = 'approved'
            rec.send_back_flag = False
            rec.approved_date = fields.Date.today()
            dispute_legal_id = self.env['dispute.legal.action'].sudo().create({'partner_id': rec.partner_id.id,
                                                                               'response_date': rec.response_date,
                                                                               'rent_id': rec.rent_id.id})
            # notification_obj = self.env['atheer.notification']
            # notification_obj._send_instant_notify(title="Dispute Management",
            #                                       message='A legal action is created against ' + str(
            #                                           rec.partner_id.name),
            #                                       action=self.env.ref(
            #                                           'property_lease_management.action_dispute_legal_action').id,
            #                                       domain=[['id', '=', dispute_legal_id.id]],
            #                                       user_type="groups",
            #                                       recipient_ids=[self.env.ref(
            #                                           'property_lease_management.group_property_accountant').id])
            for cheque in rec.bounced_cheque_ids:
                cheque.dispute_legal_id = dispute_legal_id

    def reject(self):
        """ rejecting the dispute  """
        for rec in self:
            rec.state = 'refused'
            rec.send_back_flag = False

    def send_back(self):
        """ send back the dispute  """
        for rec in self:
            rec.state = 'draft'
            rec.send_back_flag = True

    def resolved(self):
        """ Resolved the dispute  """
        for rec in self:
            rec.state = 'resolved'

    def dispute_notification(self):
        """ auto function to generate email notification regarding dispute managemlease_to_dateent """
        today = fields.date.today()
        third_date = today + relativedelta(days=21)
        second_date = today + relativedelta(days=14)
        first_date = today + relativedelta(days=7)
        print(today, first_date, second_date, third_date)
        first_dispute_ids = self.env['dispute.cheque.bounce'].search([('requested_date', '=', first_date),
                                                                      ('notification', '=', True)])
        second_dispute_ids = self.env['dispute.cheque.bounce'].search([('requested_date', '=', second_date),
                                                                       ('notification', '=', True)])
        third_dispute_ids = self.env['dispute.cheque.bounce'].search([('requested_date', '=', third_date),
                                                                      ('notification', '=', True)])
        # CODE FOR FIRST NOTIFICATION 7TH DAY
        for dispute in first_dispute_ids:
            cheques = dispute.bounced_cheque_ids.search([('paid', '=', False)], order='date desc')
            length = len(cheques)
            total = sum(cheques.mapped('amount'))
            month = str(calendar.month_name[cheques[length - 1].date.month]) + " to " + str(
                calendar.month_name[cheques[0].date.month])
            amount_in_word = self.env.user.company_id.currency_id.amount_to_text(total)
            body = str(dispute.notification_1).format(lease=dispute.rent_id.name,
                                                      tenant=dispute.rent_id.partner_id.name, month=month, amount=total,
                                                      amount_in_word=amount_in_word,
                                                      tenant_id=dispute.rent_id.partner_id)
            subject = "1st Overdue Rent Notice"
            dispute.update({'notification_ids': [(0, 0, {'rent_id': dispute.rent_id.id,
                                                         'building_id': dispute.building_id.id,
                                                         'property_id': dispute.property_id.id,
                                                         'partner_id': dispute.partner_id.id,
                                                         'notification_date': today,
                                                         'dispute_id': dispute.id,
                                                         'description': '1st notification',
                                                         'notification_type': 'dispute'})]})
            main_content = {
                'subject': subject,
                'author_id': SUPERUSER_ID,
                'body_html': body,
                'email_to': dispute.partner_id.email,
            }
            self.env['mail.mail'].sudo().create(main_content).sudo().send()
        # CODE FOR SECOND NOTIFICATION 14TH DAY
        for dispute in second_dispute_ids:
            cheques = dispute.bounced_cheque_ids.search([('paid', '=', False)], order='date desc')
            length = len(cheques)
            total = sum(cheques.mapped('amount'))
            month = str(calendar.month_name[cheques[length - 1].date.month]) + " to " + str(
                calendar.month_name[cheques[0].date.month])
            amount_in_word = self.env.user.company_id.currency_id.amount_to_text(total)
            previous_date = dispute.notification_ids.search([('description', '=', '1st notification'),
                                                             ('notification_type', '=', 'dispute')], limit=1).date
            body = str(dispute.notification_2).format(lease=dispute.rent_id.name,
                                                      tenant=dispute.rent_id.partner_id.name,
                                                      tenant_id=dispute.rent_id.partner_id,
                                                      month=month, amount=total,
                                                      amount_in_word=amount_in_word, previous_date=previous_date)
            # body = """<div style="padding:0px;font-size: 16px;width:600px;background:#FFFFFF repeat top /100%;color:#777777">
            #                <p style="font-weight:bold;">Dear {tenant},</p>
            #                <p> </p>
            #                <p>Further to my letter {previous_date}, regarding your unpaid rent of <strong>
            #                {amount_in_word} (RO {amount})</strong>, the amount remain outstanding. </p>
            #                <p></p>
            #                <p>As this amount is now seriously overdue, please pay within <strong> seven(7) days</strong>
            #                from the receipt of this letter.</p><p></p>
            #                <p>We highly value your tenancy and hope to gain your cooperation in paying your rent on due
            #                 date. Should you have any questions, feel free to contact me at 24499537.</p><p></p>
            #                 <p>Thank you.</p>
            #         """.format(lease=self.rent_id.name, tenant=self.rent_id.partner_id.name, month=month, amount=total,
            #                    amount_in_word=amount_in_word, previous_date=previous_date)
            dispute.update({'notification_ids': [(0, 0, {'rent_id': dispute.rent_id.id,
                                                         'building_id': dispute.building_id.id,
                                                         'property_id': dispute.property_id.id,
                                                         'partner_id': dispute.partner_id.id,
                                                         'notification_date': today,
                                                         'dispute_id': dispute.id,
                                                         'description': '1st notification',
                                                         'notification_type': 'dispute'})]})
            subject = "2nd Overdue Rent Notice"
            main_content = {
                'subject': subject,
                'author_id': SUPERUSER_ID,
                'body_html': body,
                'email_to': dispute.partner_id.email,
            }
            self.env['mail.mail'].sudo().create(main_content).sudo().send()
        # CODE FOR THIRD NOTIFICATION 21ST DAY
        for dispute in third_dispute_ids:
            cheques = dispute.bounced_cheque_ids.search([('paid', '=', False)], order='date desc')
            length = len(cheques)
            total = sum(cheques.mapped('amount'))
            month = str(calendar.month_name[cheques[length - 1].date.month]) + " to " + str(
                calendar.month_name[cheques[0].date.month])
            amount_in_word = self.env.user.company_id.currency_id.amount_to_text(total)
            body = str(dispute.notification_3).format(lease=dispute.rent_id.name,
                                                      tenant=dispute.rent_id.partner_id.name,
                                                      tenant_id=dispute.rent_id.partner_id,
                                                      month=month, amount=total,
                                                      amount_in_word=amount_in_word, previous_date=previous_date)
            # body = """<div style="padding:0px;font-size: 16px;width:600px;background:#FFFFFF repeat top /100%;color:#777777">
            #                            <p style="font-weight:bold;">Dear {tenant},</p>
            #                            <p> </p>
            #                            <p>We are writing concerning the amount of RO {amount} which was due to be paid
            #                             on {month} and, despite numerous requests for payment, remains outstanding and
            #                              twice a time your cheque is bounce from bank as well.</p><p></p>

            #                            <p>If this account is not resolved by the specified date we reserve the right
            #                             to commence legal proceedings to recover the debt without further notice to
            #                             you, and you may be responsible for any associated legal fees or collection
            #                             costs. </p><p></p>
            #                            <p>If you wish to prevent this, please contact the undersigned as a matter of
            #                            urgency and settle your account before the above date.</p><p></p>
            #                            <p>Regards</p>
            #                     """.format(lease=self.rent_id.name, tenant=self.rent_id.partner_id.name, month=month,
            #                                amount=total,
            #                                amount_in_word=amount_in_word)
            dispute.update({'notification_ids': [(0, 0, {'rent_id': dispute.rent_id.id,
                                                         'building_id': dispute.building_id.id,
                                                         'property_id': dispute.property_id.id,
                                                         'partner_id': dispute.partner_id.id,
                                                         'notification_date': today,
                                                         'dispute_id': dispute.id,
                                                         'description': '1st notification',
                                                         'notification_type': 'dispute'})]})
            subject = "FINAL NOTICE - OUTSTANDING ACCOUNT"
            main_content = {
                'subject': subject,
                'author_id': SUPERUSER_ID,
                'body_html': body,
                'email_to': dispute.partner_id.email,
            }
            self.env['mail.mail'].sudo().create(main_content).sudo().send()

    # def dispute_notification(self):
    #     """ auto function to generate email notification regarding dispute managemlease_to_dateent """
    #     today = fields.date.today()
    #     third_date = today + relativedelta(days=21)
    #     second_date = today + relativedelta(days=14)
    #     first_date = today + relativedelta(days=7)
    #     print(today, first_date, second_date, third_date)
    #     first_dispute_ids = self.env['dispute.cheque.bounce'].search([])
    #     # first_dispute_ids = self.env['dispute.cheque.bounce'].search([('requested_date', '=', first_date),
    #     #                                                               ('notification', '=', True)])
    #     second_dispute_ids = self.env['dispute.cheque.bounce'].search([('requested_date', '=', second_date),
    #                                                                    ('notification', '=', True)])
    #     third_dispute_ids = self.env['dispute.cheque.bounce'].search([('requested_date', '=', third_date),
    #                                                                   ('notification', '=', True)])
    #     # CODE FOR FIRST NOTIFICATION 7TH DAY
    #     print(first_dispute_ids, second_dispute_ids, third_dispute_ids)
    #     for dispute in first_dispute_ids:
    #         cheques = dispute.bounced_cheque_ids.search([('paid', '=', False)], order='date desc')
    #         length = len(cheques)
    #         total = sum(cheques.mapped('amount'))
    #         print(calendar.month_name, "total",length)
    #         # month = str(calendar.month_name[cheques[length - 1].date.month]) + " to " + str(
    #         #     calendar.month_name[cheques[0].date.month])
    #         month = "April"
    #         print(month, "month")
    #         amount_in_word = self.env.user.company_id.currency_id.amount_to_text(total)
    #         body = """
    #                 <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
    #                 <tr><td align="center"><table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
    #                 <tr>
    #                     <td align="center" style="min-width: 590px;">
    #                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
    #                             <tr><td valign="middle">
    #                                 <span style="font-size: 10px;">Hello</span><br/>
    #                                 <span style="font-size: 20px; font-weight: bold;">
    #                                     {tenant}
    #                                 </span>
    #                             </td><td valign="middle" align="right">
    #                                 <img src="/logo.png?company={tenant_id.company_id.id}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" alt="{tenant_id.company_id.name}"/>
    #                             </td></tr>
    #                             <tr><td colspan="2" style="text-align:center;">
    #                               <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
    #                             </td></tr>
    #                         </table>
    #                     </td>
    #                 </tr>
    #                 <tr>
    #                     <td align="center" style="min-width: 590px;">
    #                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
    #                             <tr><td valign="top" style="font-size: 13px;">
    #                                 <div>
    #                                     <p style="font-weight:bold;">Dear {tenant},</p>
    #                                     <p> </p>
    #                                     <p>In reference to our lease agreement No.{lease}, we would like to remind you that as to this date we
    #                                         have not received the rental payments for the months of {month} amounting to <strong> {amount_in_word}
    #                                         (RO {amount}) </strong>.</p><p></p>
    #                                     <p>Please settle the amount within seven (7) days from the date of this letter.</p><p></p>
    #                                     <p>We highly value your tenancy and hope to gain your cooperation in paying your monthly rent on due
    #                                     date. Should you have any questions feel free to contact me at 24499537</p><p></p>
    #                                     <p>Thank you for your prompt attention to this matter.</p>
    #
    #                                 </div>
    #                             </td></tr>
    #                             <tr><td style="text-align:center;">
    #                               <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
    #                             </td></tr>
    #                         </table>
    #                     </td>
    #                 </tr>
    #                 <tr>
    #                     <td align="center" style="min-width: 590px;">
    #                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
    #                             <tr><td valign="middle" align="left">
    #                                 {tenant_id.company_id.name}
    #                             </td></tr>
    #
    #                         </table>
    #                     </td>
    #                 </tr>
    #         """
    #         print("ffffffffffffffffffffffffff")
    #         data = str(dispute.notification_1).format(lease=dispute.rent_id.name, tenant=dispute.rent_id.partner_id.name, month=month,
    #                                           amount=total,
    #                                           amount_in_word=amount_in_word, tenant_id=dispute.rent_id.partner_id)
    #         print(data,"no dataaaaaaaaaaaaaaaaaa",dispute.notification_1)
    #         subject = "1st Overdue Rent Notice"
    #         dispute.update({'notification_ids': [(0, 0, {'rent_id': dispute.rent_id.id,
    #                                                      'building_id': dispute.building_id.id,
    #                                                      'property_id': dispute.property_id.id,
    #                                                      'partner_id': dispute.partner_id.id,
    #                                                      'notification_date': today,
    #                                                      'dispute_id': dispute.id,
    #                                                      'description': '1st notification',
    #                                                      'notification_type': 'dispute'})]})
    #         main_content = {
    #             'subject': subject,
    #             'author_id': SUPERUSER_ID,
    #             'body_html': body,
    #             'email_to': self.partner_id.email,
    #         }
    #         self.env['mail.mail'].sudo().create(main_content).sudo().send()
    #     # CODE FOR SECOND NOTIFICATION 14TH DAY
    #     for dispute in second_dispute_ids:
    #         cheques = dispute.bounced_cheque_ids.search([('paid', '=', False)], order='date desc')
    #         length = len(cheques)
    #         total = sum(cheques.mapped('amount'))
    #         month = str(calendar.month_name[cheques[length - 1].date.month]) + " to " + str(
    #             calendar.month_name[cheques[0].date.month])
    #         amount_in_word = self.env.user.company_id.currency_id.amount_to_text(total)
    #         previous_date = dispute.notification_ids.search([('description', '=', '1st notification'),
    #                                                          ('notification_type', '=', 'dispute')], limit=1).date
    #         body = """
    #         <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
    #                 <tr><td align="center"><table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
    #                 <tr>
    #                                     <td align="center" style="min-width: 590px;">
    #                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
    #                                             <tr><td valign="middle">
    #                                                 <span style="font-size: 10px;">Hello</span><br/>
    #                                                 <span style="font-size: 20px; font-weight: bold;">
    #                                                     {tenant}
    #                                                 </span>
    #                                             </td><td valign="middle" align="right">
    #                                                 <img src="/logo.png?company={tenant_id.company_id.id}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" alt="{tenant_id.company_id.name}"/>
    #                                             </td></tr>
    #                                             <tr><td colspan="2" style="text-align:center;">
    #                                               <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
    #                                             </td></tr>
    #                                         </table>
    #                                     </td>
    #                                 </tr>
    #                                 <tr>
    #                                     <td align="center" style="min-width: 590px;">
    #                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
    #                                             <tr><td valign="top" style="font-size: 13px;">
    #                                                 <div>
    #                                                     <p style="font-weight:bold;">Dear {tenant},</p>
    #                        <p> </p>
    #                        <p>Further to my letter {previous_date}, regarding your unpaid rent of <strong>
    #                        {amount_in_word} (RO {amount})</strong>, the amount remain outstanding. </p>
    #                        <p></p>
    #                        <p>As this amount is now seriously overdue, please pay within <strong> seven(7) days</strong>
    #                        from the receipt of this letter.</p><p></p>
    #                        <p>We highly value your tenancy and hope to gain your cooperation in paying your rent on due
    #                         date. Should you have any questions, feel free to contact me at 24499537.</p><p></p>
    #                         <p>Thank you.</p>
    #
    #                                                 </div>
    #                                             </td></tr>
    #                                             <tr><td style="text-align:center;">
    #                                               <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
    #                                             </td></tr>
    #                                         </table>
    #                                     </td>
    #                                 </tr>
    #                                 <tr>
    #                                     <td align="center" style="min-width: 590px;">
    #                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
    #                                             <tr><td valign="middle" align="left">
    #                                                 {tenant_id.company_id.name}
    #                                             </td></tr>
    #
    #                                         </table>
    #                                     </td>
    #                                 </tr>
    #         """.format(lease=self.rent_id.name, tenant=self.rent_id.partner_id.name, tenant_id=self.rent_id.partner_id,
    #                    month=month, amount=total,
    #                    amount_in_word=amount_in_word, previous_date=previous_date)
    #         # body = """<div style="padding:0px;font-size: 16px;width:600px;background:#FFFFFF repeat top /100%;color:#777777">
    #         #                <p style="font-weight:bold;">Dear {tenant},</p>
    #         #                <p> </p>
    #         #                <p>Further to my letter {previous_date}, regarding your unpaid rent of <strong>
    #         #                {amount_in_word} (RO {amount})</strong>, the amount remain outstanding. </p>
    #         #                <p></p>
    #         #                <p>As this amount is now seriously overdue, please pay within <strong> seven(7) days</strong>
    #         #                from the receipt of this letter.</p><p></p>
    #         #                <p>We highly value your tenancy and hope to gain your cooperation in paying your rent on due
    #         #                 date. Should you have any questions, feel free to contact me at 24499537.</p><p></p>
    #         #                 <p>Thank you.</p>
    #         #         """.format(lease=self.rent_id.name, tenant=self.rent_id.partner_id.name, month=month, amount=total,
    #         #                    amount_in_word=amount_in_word, previous_date=previous_date)
    #         dispute.update({'notification_ids': [(0, 0, {'rent_id': dispute.rent_id.id,
    #                                                      'building_id': dispute.building.id,
    #                                                      'property_id': dispute.property_id.id,
    #                                                      'partner_id': dispute.partner_id.id,
    #                                                      'notification_date': today,
    #                                                      'dispute': dispute.id,
    #                                                      'description': '1st notification',
    #                                                      'notification_type': 'dispute'})]})
    #         subject = "2nd Overdue Rent Notice"
    #         main_content = {
    #             'subject': subject,
    #             'author_id': SUPERUSER_ID,
    #             'body_html': body,
    #             'email_to': self.partner_id.email,
    #         }
    #         self.env['mail.mail'].sudo().create(main_content).sudo().send()
    #     # CODE FOR THIRD NOTIFICATION 21ST DAY
    #     for dispute in third_dispute_ids:
    #         cheques = dispute.bounced_cheque_ids.search([('paid', '=', False)], order='date desc')
    #         length = len(cheques)
    #         total = sum(cheques.mapped('amount'))
    #         month = str(calendar.month_name[cheques[length - 1].date.month]) + " to " + str(
    #             calendar.month_name[cheques[0].date.month])
    #         amount_in_word = self.env.user.company_id.currency_id.amount_to_text(total)
    #         body = """ <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
    #                 <tr><td align="center"><table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
    #                 <tr>
    #                                     <td align="center" style="min-width: 590px;">
    #                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
    #                                             <tr><td valign="middle">
    #                                                 <span style="font-size: 10px;">Hello</span><br/>
    #                                                 <span style="font-size: 20px; font-weight: bold;">
    #                                                     {tenant}
    #                                                 </span>
    #                                             </td><td valign="middle" align="right">
    #                                                 <img src="/logo.png?company={tenant_id.company_id.id}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" alt="{tenant_id.company_id.name}"/>
    #                                             </td></tr>
    #                                             <tr><td colspan="2" style="text-align:center;">
    #                                               <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
    #                                             </td></tr>
    #                                         </table>
    #                                     </td>
    #                                 </tr>
    #                                 <tr>
    #                                     <td align="center" style="min-width: 590px;">
    #                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
    #                                             <tr><td valign="top" style="font-size: 13px;">
    #                                                 <div>
    #                                                     <p style="font-weight:bold;">Dear {tenant},</p>
    #                                                     <p> </p>
    #                                                     <p>We are writing concerning the amount of RO {amount} which was due to be paid
    #                                                         on {month} and, despite numerous requests for payment, remains outstanding and
    #                                                         twice a time your cheque is bounce from bank as well.</p><p></p>
    #
    #                                                     <p>If this account is not resolved by the specified date we reserve the right
    #                                                         to commence legal proceedings to recover the debt without further notice to
    #                                                         you, and you may be responsible for any associated legal fees or collection
    #                                                         costs. </p><p></p>
    #                                                     <p>If you wish to prevent this, please contact the undersigned as a matter of
    #                                                     urgency and settle your account before the above date.</p><p></p>
    #                                                     <p>Regards</p>
    #
    #                                                 </div>
    #                                             </td></tr>
    #                                             <tr><td style="text-align:center;">
    #                                               <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
    #                                             </td></tr>
    #                                         </table>
    #                                     </td>
    #                                 </tr>
    #                                 <tr>
    #                                     <td align="center" style="min-width: 590px;">
    #                                         <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
    #                                             <tr><td valign="middle" align="left">
    #                                                 {tenant_id.company_id.name}
    #                                             </td></tr>
    #
    #                                         </table>
    #                                     </td>
    #                                 </tr>
    #         """.format(lease=self.rent_id.name, tenant=self.rent_id.partner_id.name, tenant_id=self.rent_id.partner_id,
    #                    month=month, amount=total,
    #                    amount_in_word=amount_in_word, previous_date=previous_date)
    #         # body = """<div style="padding:0px;font-size: 16px;width:600px;background:#FFFFFF repeat top /100%;color:#777777">
    #         #                            <p style="font-weight:bold;">Dear {tenant},</p>
    #         #                            <p> </p>
    #         #                            <p>We are writing concerning the amount of RO {amount} which was due to be paid
    #         #                             on {month} and, despite numerous requests for payment, remains outstanding and
    #         #                              twice a time your cheque is bounce from bank as well.</p><p></p>
    #
    #         #                            <p>If this account is not resolved by the specified date we reserve the right
    #         #                             to commence legal proceedings to recover the debt without further notice to
    #         #                             you, and you may be responsible for any associated legal fees or collection
    #         #                             costs. </p><p></p>
    #         #                            <p>If you wish to prevent this, please contact the undersigned as a matter of
    #         #                            urgency and settle your account before the above date.</p><p></p>
    #         #                            <p>Regards</p>
    #         #                     """.format(lease=self.rent_id.name, tenant=self.rent_id.partner_id.name, month=month,
    #         #                                amount=total,
    #         #                                amount_in_word=amount_in_word)
    #         dispute.update({'notification_ids': [(0, 0, {'rent_id': dispute.rent_id.id,
    #                                                      'building_id': dispute.building.id,
    #                                                      'property_id': dispute.property_id.id,
    #                                                      'partner_id': dispute.partner_id.id,
    #                                                      'notification_date': today,
    #                                                      'dispute': dispute.id,
    #                                                      'description': '1st notification',
    #                                                      'notification_type': 'dispute'})]})
    #         subject = "FINAL NOTICE - OUTSTANDING ACCOUNT"
    #         main_content = {
    #             'subject': subject,
    #             'author_id': SUPERUSER_ID,
    #             'body_html': body,
    #             'email_to': self.partner_id.email,
    #         }
    #         self.env['mail.mail'].sudo().create(main_content).sudo().send()
