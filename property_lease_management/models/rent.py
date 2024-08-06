# -*- coding: utf-8 -*-

import calendar

import dateutil.utils
from odoo import SUPERUSER_ID
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError


class PropertyRent(models.Model):
    _name = 'property.rent'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _description = _('Rent Details')

    @api.model
    def _default_company(self):
        return self.env.user.company_id.id

    @api.model
    def _default_currency(self):
        return self.env.user.company_id.currency_id.id

    @api.model_create_multi
    def create(self, vals_list):
        # Check if all records have 'property_id'
        for vals in vals_list:
            # print(vals, '18**********')
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            if 'property_id' not in vals:
                raise ValidationError("'property_id' is required to create a property rent record.")

            if not self.env['property.rent'].search(
                    [('property_id', '=', vals['property_id']), ('from_date', '>=', vals['from_date']),
                     ('to_date', '<=', vals['to_date']), ('state', 'in', ('open', 'notice'))]):
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(
                    vals['from_date'])) if 'from_date' in vals else None
                vals['name'] = self.env['ir.sequence'].next_by_code('property.rent', sequence_date=seq_date) or _("New")
                # print(vals['name'])
                # OLD FORMATE
                # vals['name'] = self.env['ir.sequence'].with_context(ir_sequence_date=vals['from_date']).next_by_code(
                #     'property.rent')
                res = super(PropertyRent, self).create(vals)
                if res.reference_id:
                    res.reference_id.write({'state': 'renewed'})
                    res.reference_id.property_id.write({'state': 'open'})
                return res
            else:
                return super(PropertyRent, self).create(vals)

    id_temp = fields.Integer(string='ID Temp')
    name = fields.Char(string='Rent ID', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today, readonly=True,
                       states={'draft': [('readonly', False)]}, tracking=True)
    year = fields.Integer(string='Year', default=lambda self: fields.Date.today().year)
    from_date = fields.Date(string='Lease Start', required=True, default=fields.Date.today, readonly=True,
                            states={'draft': [('readonly', False)]}, tracking=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string='Tenant', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]}, tracking=True)
    property_id = fields.Many2one(comodel_name='property.property', string='Unit', required=True, readonly=True,
                                  states={'draft': [('readonly', False)]}, tracking=True)
    area = fields.Float(string='Area(sqm)', digits='Product Price')
    std_rent_sqm = fields.Float(string='Standard Rent(sqm)', digits='Product Price')
    property_group = fields.Char(string='Property Group', related='property_id.property_group')
    purpose = fields.Char(string='Purpose of Rent', tracking=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string=_('Journal'),
                                 required=True, states={'draft': [('readonly', False)]},
                                 compute='_compute_journal', store=True,
                                 tracking=True)
    account_id = fields.Many2one(comodel_name='account.account', string='Account', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 help=_("The lessee account used for this agreement."),
                                 tracking=True)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', default=_default_currency,
                                  required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  tracking=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company,
                                 change_default=True, required=True, readonly=True,
                                 states={'draft': [('readonly', False)]}, tracking=True)
    move_ids = fields.Many2many(comodel_name='account.move', relation='property_rent_move_rel',
                                column1='rent_id', column2='move_id', string=_('Journal Entry'),
                                readonly=True, index=True, ondelete='restrict', copy=False,
                                help=_("Link to the automatically generated Journal Items."),
                                tracking=True)
    payment_ids = fields.Many2many(comodel_name='account.move.line', relation='property_rent_move_line_rel',
                                   column1='rent_id', column2='move_line_id', string='Journal Entry Lines',
                                   readonly=True, index=True, ondelete='restrict', copy=False,
                                   tracking=True)
    reference_id = fields.Many2one(comodel_name='property.rent', string='Reference',
                                   readonly=True, states={'draft': [('readonly', False)]},
                                   tracking=True)
    auto_entry_ids = fields.One2many(comodel_name='property.rent.auto.entry', inverse_name='contract_id',
                                     string='Auto Journal Entry', tracking=True)
    annual_rent = fields.Float(string='Standard Annual Rent', digits='Product Price', store=True,
                               readonly=True, compute='_compute_amount', tracking=True)
    rent_price = fields.Float(string='Standard Monthly Amount', digits='Product Price', store=True,
                              compute='_compute_amount', tracking=True)
    rent_total = fields.Float(string='Total Amount', digits='Product Price', store=True,
                              readonly=True, compute='_compute_amount', tracking=True)
    deposit_total = fields.Float(string='Total Deposit', digits='Product Price',
                                 compute='_compute_total_amount', tracking=True, store=True)
    installment_total = fields.Float(string='Total Installment', digits='Product Price',
                                     compute='_compute_total_amount', tracking=True, store=True)
    fee_total = fields.Float(string='Total Fee', digits='Product Price',
                             compute='_compute_total_amount', tracking=True, store=True)
    collection_ids = fields.One2many(comodel_name='property.rent.installment.collection', inverse_name='rent_id',
                                     string='Collections', tracking=True)

    # bounced cheque relation
    lease_acquired = fields.Date(string='Lease Acquired', tracking=True)
    collection_ids_bounce = fields.One2many(comodel_name='property.rent.installment.collection.bounced',
                                            inverse_name='rent_id', string='Collections Bounced',
                                            tracking=True)
    security_deposit = fields.Float(string='Security Deposit', digits='Product Price', tracking=True)
    open_dated_cheque = fields.Boolean('Open Dated Cheque')
    deposit_collected = fields.Float(string='Deposit Collected', compute="_compute_total_deposit",
                                     digits='Product Price', tracking=True)
    cheq_deposit = fields.Float(string='Cheque Deposits', compute="_compute_cheque_total",
                                digits='Product Price', tracking=True)
    # end

    installment_ids = fields.One2many(comodel_name='property.rent.installment', inverse_name='rent_id',
                                      string='Installment Receipt', tracking=True)
    installment_type = fields.Selection([('installment', _('Installment')), ('fee', _('Fee')),
                                         ('deposit', _('Deposit'))], string='Installment Type', default='installment',
                                        readonly=True, states={'open': [('readonly', False)]},
                                        tracking=True)
    residing_tenant = fields.Char(string='Residing Tenant', tracking=True)
    residing_since = fields.Date(string='Residing Since', states={'draft': [('readonly', False)]},
                                 tracking=True)
    tenant_years = fields.Char(string='Tenancy Period (Years)', compute='_residing_since', store=True, readonly=True,
                               tracking=True)
    property_type = fields.Char(string='Type', tracking=True)
    resend = fields.Boolean(string='Return', default=False)

    building = fields.Many2one(comodel_name='property.building', string='Building',
                               required=True, tracking=True)
    doc_ids = fields.Many2many('atheer.documents',
                               string='Documents')
    installment_schedule = fields.Selection([('monthly', _('Monthly')),
                                             ('one_bill', _('One Bill')),
                                             ('quaterly', _('Quarterly')),
                                             ('six_month', _('Half Yearly')),
                                             ('yearly', _('Yearly')),
                                             ('one_bill', _('One Bill(Fully Tenure)'))], string='Installment Schedule',
                                            tracking=True)
    to_date = fields.Date(string='Lease End', readonly=False,
                          compute='_compute_todate', tracking=True, store=True)
    invoice_ids = fields.One2many(comodel_name='account.move', inverse_name='rent_id',
                                  domain=[('move_type', '=', 'out_invoice')],
                                  string='Invoices',
                                  tracking=True)
    period = fields.Integer(string='Rental Period', tracking=True)
    muncipality_agreemnt_no = fields.Char(related="property_id.muncipality_no", string='Municipality Agreement No.',
                                          tracking=True,
                                          )
    period_line_ids = fields.One2many(comodel_name='rent.period.lines', inverse_name='rent_ids',
                                      string='Rent Period ids', tracking=True)
    agreed_rent_amount = fields.Float(string='Agreed Rent Amount', digits='Product Price',
                                      tracking=True)
    rent_sqm = fields.Float(string='Agreed Rent(sqm)', digits='Product Price',
                            tracking=True)
    revenue_account = fields.Many2one(comodel_name='account.account', string='Revenue Account',
                                      tracking=True)
    remarks = fields.Text(string='Remarks', tracking=True)

    state = fields.Selection([('draft', _('Draft')),
                              ('cancel', _('Cancelled')),
                              ('hand_over', _('Property Handover')), ('open', _('Occupied')),
                              ('notice', _('To Notice')), ('take_over', _('Property Takeover')),
                              ('legal_case', _('Legal Case')), ('to_renew', _('Needs Renewal')),
                              ('renewed', _('Renewed')), ('close', _('Closed / Vacant'))],
                             string='Status', readonly=True, copy=False, default='draft',
                             help=_("Gives the status of the rent"), tracking=True)
    key_received = fields.Boolean(string='Key Received/Takeover completed')
    handover_check_id = fields.Many2one(comodel_name='property.checklist')
    cancellation_form = fields.Many2one(comodel_name='agreement.cancellation')
    legal_case = fields.Boolean(string='Legal Case', default=False)
    attestation = fields.Boolean(string='Attestation', default=False)
    active = fields.Boolean(related='building.active', string='Active')
    prev_state = fields.Char(string='Prev State')
    l_start_date = fields.Date(string='Start Date')
    e_start_date = fields.Date(string='End Date')

    agreement_type = fields.Selection([('residential', 'Residential'), ('commercial', 'Commercial')],
                                      string='Agreement Type', copy=False, tracking=True)
    tax_id = fields.Many2one('account.tax', string='Tax', domain=[('type_tax_use', '=', 'sale')], check_company=True,
                             tracking=True)
    vat_percentage = fields.Char(string='Tax Percentage')
    invoice_created = fields.Boolean(string='Invoice Created', default=False)
    name_temp = fields.Char(string='Name temp')
    owner = fields.Char(string='Owner', readonly=True)
    customer_vat = fields.Char(string='Owner VATIN', readonly=True)
    property_handed_back = fields.Boolean(string='Property Handed Back', default=False)
    attach_agreement = fields.Binary(string="Upload Attested Agreement")
    file_name = fields.Char('File Name')
    notes = fields.Html('Notes')
    year_month_days = fields.Char('Duration', compute="compute_year_month_days")
    rent_history_ids = fields.One2many('tenant.rent.history', 'rent_id', 'Tenant Rent History')
    building_area_id = fields.Many2one('building.area', 'Building Area', related="building.building_area")
    confirmed_handover = fields.Boolean('Handover', compute="compute_confirmed_handover")
    confirmed_takeover = fields.Boolean('Takeover', compute="compute_confirmed_handover")
    acknowledgment_date = fields.Date(string="Acknowledgment Date")
    notification_ids = fields.One2many('property.notification', 'rent_id')
    tenant_request_renewal_id = fields.Many2one('tenant.request', 'Tenant Request')
    bounced_count = fields.Integer('Bounced Count', compute="compute_bounce_count")
    legal_case_count = fields.Integer('Legal case Count', compute="compute_bounce_count")
    vacating_info_count = fields.Integer('Vacating info Count', compute="compute_bounce_count", store=True)

    invoice_count = fields.Integer('Invoiced Count', compute="compute_bounce_count")
    agreement_count = fields.Integer('Agreement Count', compute="compute_agreement_count")

    # New fields
    grace_period = fields.Integer(string='Grace Period(in months)')
    service_charges = fields.Float(string='Service & Marketing Charges', digits="Product Price")
    business_categ_id = fields.Many2one('business.category', string='Business Category')
    is_from_crm = fields.Boolean(string='Is From CRM', default=False)
    created_security_entry = fields.Boolean(string='Created Entry', default=False)
    security_move_id = fields.Many2one('account.move', string='Security Entry', )

    def action_view_crm(self):
        """ show the property lead"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lead',
            'view_mode': 'tree,form',
            'res_model': 'crm.lead',
            'domain': [('rent_id', '=', self.id)]
        }

    def open_deferred_revenue(self):
        """ open revenue """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Deferred Revenue',
            'view_mode': 'tree,form',
            'res_model': 'account.asset',
            'domain': [('asset_type', '=', 'sale'), ('property_rent_id', '=', self.id)],
            'views': [
                (self.env.ref('account_asset.view_account_asset_model_sale_tree').id, 'tree'),
                (self.env.ref('account_asset.view_account_asset_revenue_form').id, 'form')
            ],
            'context': {
                'asset_type': 'sale',
                'default_asset_type': 'sale',
                'default_acquisition_date': self.from_date,
                'default_original_value': self.rent_total,
                'default_property_rent_id': self.id,
            }
        }

    # Security deposit entry

    def create_security_deposit_entry(self):
        if self.security_deposit <= 0:
            raise ValidationError(_("The Security Deposit Amount Must be Greater Than Zero ."))

        wizard = self.env['security.deposit.wizard'].create({
            'rent_id': self.id,
            'reference': "Security Deposit of %s" % self.name,
            'partner_id': self.partner_id.id,
            'security_deposit': self.security_deposit
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Security Deposit Entry',
            'view_mode': 'form',
            'res_model': 'security.deposit.wizard',
            'res_id': wizard.id,
            'target': 'new',

        }

    def action_cancel(self):
        ''' action for cancel button'''
        self.property_id.state = 'open'
        self.state = 'cancel'

    def name_get(self):
        res = []
        for each in self:
            state = ''
            name = each.name
            if each.reference_id:
                res.append((each.id, name + ' (' + each.reference_id.name + ')'))
            if each.state:
                if each.state == 'renewed':
                    state = 'Renewed'
                    res.append((each.id, name + ' (' + state + ')'))
                else:
                    res.append((each.id, name))
            else:
                res.append((each.id, name))
        return res

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(PropertyRent, self).unlink()

    def action_set_to_draft(self):
        """cancel and delete the invoices and installments from one2many and change the rent agreement state to draft"""
        for rec in self:
            checklist_obj = self.env['property.checklist']
            check_list_id = checklist_obj.search([('rent_id', '=', self.id), ('state', '=', 'confirm')], limit=1)
            check_list_id.state = 'draft'
            if rec.collection_ids:
                for each in rec.collection_ids:
                    each.state = 'draft0'
            if rec.invoice_ids:
                for each in rec.invoice_ids:
                    each.button_draft()
                    each.button_cancel()
            rec.state = 'draft'
        for each in self:
            each.collection_ids = [(5, 0, 0)]
            each.invoice_ids = [(5, 0, 0)]

    def compute_agreement_count(self):
        for rec in self:
            agreement_count = self.env['property.rent'].search_count([('reference_id', '=', rec.id)])
            rec.agreement_count = agreement_count

    def action_view_new_rent_agreement(self):
        return {
            'type': 'ir.actions.act_window',
            'name': ('Rent Agreement'),
            'view_mode': 'tree,form',
            'res_model': 'property.rent',
            'target': 'current',
            'context': {'create': False},
            'domain': [('reference_id', '=', self.id)],
        }

    def compute_bounce_count(self):
        """ find the number of check bounced in this rent agreement """
        for rec in self:
            bounced_cheques = self.env['property.bounced.cheque'].sudo().search_count([('rent_id', '=', rec.id)])
            rec.bounced_count = bounced_cheques

            """ To find the number of legal case in this rent agreement """
            legal_case_count = self.env['dispute.legal.action'].sudo().search_count([('rent_id', '=', rec.id)])
            rec.legal_case_count = legal_case_count

            """ To find the number of Invoices in this rent agreement """
            # invoice_count = self.env['account.move'].sudo().search_count([('rent_id', '=', rec.id)])
            invoice_count = self.env['account.move'].sudo().search_count([('id', 'in', self.invoice_ids.ids)])
            rec.invoice_count = invoice_count

            """ To find the number of Tenant Deposit Release in this rent agreement """
            vacating_info_count = self.env['tenant.deposit.release'].sudo().search_count([('rent_id', '=', rec.id)])
            rec.vacating_info_count = vacating_info_count

    def get_bounced_cheques(self):
        """ get details of bounced cheques """
        for rec in self:
            bounced_cheques = self.env['property.bounced.cheque'].sudo().search([('rent_id', '=', rec.id)])
            action = self.env["ir.actions.act_window"]._for_xml_id(
                'property_lease_management.action_property_bounced_cheque')
            form_view = self.env.ref('property_lease_management.view_property_bounced_cheque_form')
            action['domain'] = [('id', 'in', bounced_cheques.ids)]

            return action

    def mail_rent_expiry(self):
        """ send mail to tenant when rent expiry """
        self.ensure_one()
        template = self.env.ref('property_lease_management.email_template_rent_expiry')
        ctx = {
            "default_model": "property.rent",
            "default_res_id": self.ids[0],
            "default_use_template": bool(template.id),
            "default_template_id": template.id,
            "default_composition_mode": "comment",
            # "custom_layout": "mail.mail_notification_paynow",
            "force_email": True,
        }
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(False, "form")],
            "view_id": False,
            "target": "new",
            "context": ctx,
        }

    def check_rent_expiry(self):
        """ auto function to generate email notification regarding rent expiry """
        today = fields.date.today()
        one_month_before = today + relativedelta(months=1)
        first_date = today + relativedelta(days=21)
        second_date = today + relativedelta(days=14)
        third_date = today + relativedelta(days=7)
        # print(today, one_month_before, first_date, second_date, third_date)
        month_rent_ids = self.env['property.rent'].search([('to_date', '=', one_month_before)])
        first_rent_ids = self.env['property.rent'].search([('to_date', '=', first_date)])
        second_rent_ids = self.env['property.rent'].search([('to_date', '=', second_date)])
        third_rent_ids = self.env['property.rent'].search([('to_date', '=', third_date)])
        # print(first_rent_ids, second_rent_ids, third_rent_ids)
        for rent_id in month_rent_ids:
            rent_id.button_notice()
        for rent_id in first_rent_ids:
            rent_id.update({'notification_ids': [(0, 0, {'rent_id': rent_id.id,
                                                         'building_id': rent_id.building.id,
                                                         'property_id': rent_id.property_id.id,
                                                         'partner_id': rent_id.partner_id.id,
                                                         'notification_date': today,
                                                         'description': '1st notification',
                                                         'notification_type': 'rent_expiry'})]})
            rent_id.send_notification_mail()
        for rent_id in second_rent_ids:
            rent_id.update({'notification_ids': [(0, 0, {'rent_id': rent_id.id,
                                                         'building_id': rent_id.building.id,
                                                         'property_id': rent_id.property_id.id,
                                                         'partner_id': rent_id.partner_id.id,
                                                         'notification_date': today,
                                                         'description': '2nd notification',
                                                         'notification_type': 'rent_expiry'})]})
            rent_id.send_notification_mail()
        for rent_id in third_rent_ids:
            rent_id.update({'notification_ids': [(0, 0, {'rent_id': rent_id.id,
                                                         'building_id': rent_id.building.id,
                                                         'property_id': rent_id.property_id.id,
                                                         'partner_id': rent_id.partner_id.id,
                                                         'notification_date': today,
                                                         'description': '3rd notification',
                                                         'notification_type': 'rent_expiry'})]})
            rent_id.send_notification_mail()

    def send_notification_mail(self):
        """ function to send the email notification """
        body = """ <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
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
                                                        <p style="font-weight:bold;">Dear {tenant},</p>
                                                        <p> </p>
                                                        <p>In reference to our lease agreement No.{lease},  we would like to remind you that
                                                        the lease date of the property <strong>{property}</strong> that you leased is going to
                                                        expire on <strong>{date}</strong>.
                                                        <p> We are thankful to you for your consistent business relations with our company and would
                                                            appreciate it if you would look into the above matter as soon as possible. Thank you for
                                                            your cooperation. We look forward to serve you for many years to come. </p>
                                                        <p>Should you have any questions, feel free to contact me at 79434432 from 8am to 4pm or
                                                            e-mail me at raiya.amlak@gmail.com</p>
                                                            <p style="font-weight:bold;">Sincerely, Raiya Al-shaaili</p>
                                                            <p style="font-weight:bold;">Assistant Property Manager In charger </p>

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

        """.format(lease=self.name, tenant=self.partner_id.name, tenant_id=self.partner_id,
                   property=self.property_id.name, date=self.to_date)
        # body = """<div style="padding:0px;font-size: 16px;width:600px;background:#FFFFFF repeat top /100%;color:#777777">
        #        <p style="font-weight:bold;">Dear {tenant},</p>
        #        <p> </p>
        #        <p>In reference to our lease agreement No.{lease},  we would like to remind you that
        #        the lease date of the property <strong>{property}</strong> that you leased is going to
        #        expire on <strong>{date}</strong>.
        #        <p> We are thankful to you for your consistent business relations with our company and would
        #         appreciate it if you would look into the above matter as soon as possible. Thank you for
        #         your cooperation. We look forward to serve you for many years to come. </p>
        #        <p>Should you have any questions, feel free to contact me at 79434432 from 8am to 4pm or
        #         e-mail me at raiya.amlak@gmail.com</p>
        #         <p style="font-weight:bold;">Sincerely, Raiya Al-shaaili</p>
        #         <p style="font-weight:bold;">Assistant Property Manager In charger </p>
        # """.format(lease=self.name, tenant=self.partner_id.name,
        #            property=self.property_id.name, date=self.to_date)
        main_content = {
            'subject': _('Property Rent Period Expiry Notification'),
            'author_id': SUPERUSER_ID,
            'body_html': body,
            'email_to': self.partner_id.email,
        }
        self.env['mail.mail'].sudo().create(main_content).sudo().send()

    def compute_confirmed_handover(self):
        """ find confirmed handover and takeover checklists """
        for rec in self:
            checklist_obj = self.env['property.checklist']
            if checklist_obj.search([('rent_id', '=', rec.id), ('state', '=', 'confirm')], limit=1):
                rec.confirmed_handover = True
            else:
                rec.confirmed_handover = False
            take_over_checklist_obj = self.env['property.checklist.takeover']
            if take_over_checklist_obj.search([('rent_id', '=', rec.id), ('state', '=', 'confirm')], limit=1):
                rec.confirmed_takeover = True
            else:
                rec.confirmed_takeover = False

    def find_confirmed_handover(self):
        """ load handover checklists """
        for rec in self:
            checklist_obj = self.env['property.checklist']
            check_list_id = checklist_obj.search([('rent_id', '=', rec.id), ('state', '=', 'confirm')], limit=1)
            action = self.env["ir.actions.act_window"]._for_xml_id('property_lease_management.action_checklist')
            form_view = self.env.ref('property_lease_management.view_checklist_form')
            action['views'] = [(form_view.id, 'form')]
            action['res_id'] = check_list_id and check_list_id.id
            return action

    def find_confirmed_takeover(self):
        """ load takeover checklist """
        for rec in self:
            checklist_obj = self.env['property.checklist.takeover']
            check_list_id = checklist_obj.search([('rent_id', '=', rec.id), ('state', '=', 'confirm')], limit=1)
            action = self.env["ir.actions.act_window"]._for_xml_id(
                'property_lease_management.action_takeover_checklist')
            form_view = self.env.ref('property_lease_management.view_takeover_checklist_form')
            action['views'] = [(form_view.id, 'form')]
            action['res_id'] = check_list_id and check_list_id.id
            return action

    @api.onchange('to_date', 'from_date')
    def compute_year_month_days(self):
        """ compute the duration """
        for rec in self:
            if rec.from_date and rec.to_date:
                to_date = rec.to_date + timedelta(days=1)
                diff = relativedelta(to_date, rec.from_date)
                years = diff.years
                months = diff.months
                days = diff.days
                rec.year_month_days = "{} years {} months {} days".format(years, months, days)
            else:
                rec.year_month_days = " "

    @api.onchange('tax_id')
    def onchange_tax(self):
        if self.tax_id:
            self.vat_percentage = str(self.tax_id.amount) + '%'

    @api.onchange('property_id')
    def _onchange_property(self):
        for record in self:
            record.property_id.state = 'reserve'

    @api.onchange('building', 'property_handed_back')
    def onchange_building(self):
        for record in self:
            if record.property_handed_back:
                record.property_id.state = 'open'
            owner_name = ''
            customer_vat = ''
            for partner_id in self.building.partner_id:
                owner_name += str(partner_id.name) + ','
                if partner_id.vat:
                    customer_vat += str(partner_id.vat) + ','
            record.owner = owner_name
            record.customer_vat = customer_vat
            # record.customer_vat = self.building.partner_id.vat
        return {
            'domain': {'property_id': [('in_active_bol', '=', False), ('state', '=', 'open'), ('for_rent', '=', True),
                                       ('parent_building', '=', self.building.id)]}}

    def print_rent_payment_policy(self):
        """ function to print the Rent payment policy"""
        return self.env.ref('property_lease_management.rent_payment_policy_report_tag').report_action(self)

    def print_repair_policy(self):
        """ function to print the Rent Repair policy"""
        return self.env.ref('property_lease_management.rent_repair_report_tag').report_action(self)

    def print_report_turn_over(self):
        """ function to print the Rent Turn Over Report form """
        return self.env.ref('property_lease_management.key_turnover_report_tag').report_action(self)

    def resend_notice(self):
        if self.state == 'notice':
            self.state = 'open'

    def button_takeover(self):
        self.property_id.state = 'take_over'
        self.write({'state': 'take_over'})

    def button_takeover_checklist(self):
        asset_values = []
        asset_values_sql = []

        checklist_obj = self.env['property.checklist.takeover']
        check_list_id = checklist_obj.search([('rent_id', '=', self.id), ('state', '=', 'confirm')], limit=1)
        if not check_list_id:
            # deleting existing checklists
            draft_check_list = checklist_obj.search([('rent_id', '=', self.id), ('state', '=', 'draft')])
            if draft_check_list:
                for draft in draft_check_list:
                    draft.unlink()
            # finding the asset values using query
            query = """select at.name, count(aa.id) as qty, prt.name as room_type from assets_accessrz aa
            inner join assets_accessrz_type at on at.id=aa.asset_categ
            inner join property_room pr on pr.id=aa.room_id
            inner join property_room_type prt on prt.id=pr.type_id
            inner join property_property pp on pp.id=pr.property_id where pp.id={id} group by at.name,prt.name;
              """.format(id=self.property_id.id)
            self._cr.execute(query)
            data = self._cr.dictfetchall()
            from collections import defaultdict
            current_vals = sorted(data, key=lambda k: k['room_type'])
            t_vals = defaultdict(list)
            for c_val in current_vals:
                t_vals[c_val['room_type']].append(c_val)
            # preparing the asset values from the above query data
            alpha = 65
            for ii in t_vals:
                asset_values_sql.append((0, 0, {'session_head': True,
                                                'sl_no': chr(alpha),
                                                'description': ii}))
                alpha = alpha + 1
                sl_no = 1
                for t_val in t_vals[ii]:
                    asset_values_sql.append((0, 0, {'session_head': False,
                                                    'description': str(sl_no) + "." + t_val['name'],
                                                    'quantity': t_val['qty']}))
                    sl_no = sl_no + 1

            handover_checklist_obj = self.env['property.checklist']
            handover_check_list_id = handover_checklist_obj.search(
                [('rent_id', '=', self.id), ('state', '=', 'confirm')], limit=1)
            values = {
                'partner_id': self.partner_id.id,
                'building': self.building.id,
                'property_id': self.property_id.id,
                'electricity_account_ids': self.property_id.electricity_account_ids.ids,
                'water_account_ids': self.property_id.water_account_ids.ids,
                'rent_id': self.id,
                'water_acc_no': self.property_id.water_account_no,
                'water_meter_no': self.property_id.water_meter_no,
                'elec_acc_no': self.property_id.electricity_no,
                'elec_meter_no': self.property_id.electricity_meter_no,
                'take_over_checklist': asset_values_sql,
                'hand_over_checklist': [(6, 0, handover_check_list_id.hand_over_checklist.ids)]
            }
            check_list_id = checklist_obj.create(values)
        action = self.env["ir.actions.act_window"]._for_xml_id('property_lease_management.action_takeover_checklist')
        form_view = self.env.ref('property_lease_management.view_takeover_checklist_form')
        action['views'] = [(form_view.id, 'form')]
        action['res_id'] = check_list_id and check_list_id.id
        return action

    def button_renew(self):
        view_ref = self.env.ref('property_lease_management.view_rent_form')
        view_id = view_ref.id if view_ref else False
        rent_obj = self
        end_date = self.to_date
        next_day = end_date + relativedelta(days=1)
        next_day = datetime.strftime(next_day, "%Y-%m-%d")

        return {
            'name': _("Rent Agreement"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'tag': 'reload',
            'res_model': 'property.rent',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'stay_open': True,
            'domain': '[]',
            'context': {
                'default_reference_id': rent_obj.id,
                'default_building': rent_obj.building.id,
                'default_residing_tenant': rent_obj.residing_tenant,
                'default_residing_since': rent_obj.residing_since,
                'default_security_deposit': rent_obj.security_deposit,
                'default_partner_id': rent_obj.partner_id.id,
                'default_property_id': rent_obj.property_id.id,
                'default_account_id': rent_obj.account_id.id,
                'default_journal_id': rent_obj.journal_id.id,
                'default_agreed_rent_amount': rent_obj.agreed_rent_amount,
                'default_installment_schedule': rent_obj.installment_schedule,
                'default_revenue_account': rent_obj.revenue_account.id,
                'default_currency_id': rent_obj.currency_id.id,
                'default_company_id': rent_obj.company_id.id,
                'default_from_date': next_day,
                'default_period': rent_obj.period,
                'default_agreement_type': rent_obj.agreement_type,
                'default_tax_id': rent_obj.tax_id.id,
                'default_state': 'draft',
            }
        }

    def button_confirm_agreement(self):
        checklist_obj = self.env['property.checklist']
        check_list_id = checklist_obj.search([('rent_id', '=', self.id), ('state', '=', 'confirm')], limit=1)
        if not check_list_id:
            raise UserError('You need to confirm the HandOver checklist before Confirming the Agreement.')
        if not self.env['property.rent'].search(
                [('id', 'not in', [self.id]), ('property_id', '=', self.property_id.id),
                 ('from_date', '>=', self.from_date),
                 ('to_date', '<=', self.to_date), ('state', 'in', ('open', 'notice'))]):
            # if not self.invoice_ids or self.installment_ids:
            #     raise UserError("Compute Installments/Invoices")
            # self.write({'state': 'confirm'})
            if self.reference_id:
                self.handover_check_id = self.reference_id.handover_check_id.id
                self.update({'state': 'open'})
            if not self.property_id.for_parking:
                self.property_id.state = 'rented'
            self.property_id.rent_id = self.id
            self.button_confirm()
            self.write({'rent_history_ids': [(0, 0, {'from_date': self.from_date,
                                                     'to_date': self.to_date,
                                                     'rent_id': self.id,
                                                     'approved_rent': self.agreed_rent_amount})]})
        else:
            if not self.property_id.for_parking:
                raise UserError('Rent Agreement already exist for this property.')
            # raise UserError('Rent Agreement already exist for this property.')

    def button_handover(self):
        if not len(self.collection_ids.ids):
            raise UserError('There is no installments. Kindly click on the COMPUTE INSTALLMENTS')

        if not self.env['property.rent'].search(
                [('property_id', '=', self.property_id.id), ('from_date', '>=', self.from_date),
                 ('to_date', '<=', self.to_date), ('state', 'in', ('open', 'notice'))]):
            self.write({'state': 'hand_over'})
        else:
            raise UserError('Rent Agreement already exist for this property.')

    def button_handover_checklist(self):

        asset_values_sql = []
        asset_values = []
        checklist_obj = self.env['property.checklist']
        check_list_id = checklist_obj.search([('rent_id', '=', self.id), ('state', '=', 'confirm')], limit=1)
        # print("check_list_id", check_list_id)
        if not check_list_id:
            rent_agreement = self

            draft_check_list = checklist_obj.search([('rent_id', '=', self.id), ('state', '=', 'draft')])
            if draft_check_list:
                # checklist_obj.unlink(draft_check_list.ids)
                for draft in draft_check_list:
                    draft.unlink()
            # finding the asset values using query
            query = """select at.name, count(aa.id) as qty, prt.name as room_type from assets_accessrz aa
            inner join assets_accessrz_type at on at.id=aa.asset_categ
            inner join property_room pr on pr.id=aa.room_id
            inner join property_room_type prt on prt.id=pr.type_id
            inner join property_property pp on pp.id=pr.property_id where pp.id={id} group by at.name,prt.name;
              """.format(id=self.property_id.id)
            self._cr.execute(query)
            data = self._cr.dictfetchall()
            from collections import defaultdict
            current_vals = sorted(data, key=lambda k: k['room_type'])
            t_vals = defaultdict(list)
            for c_val in current_vals:
                t_vals[c_val['room_type']].append(c_val)
            # preparing the asset values from the above query data
            alpha = 65
            for ii in t_vals:
                asset_values_sql.append((0, 0, {'session_head': True,
                                                'sl_no': chr(alpha),
                                                'description': ii}))
                alpha = alpha + 1
                sl_no = 1
                for t_val in t_vals[ii]:
                    asset_values_sql.append((0, 0, {'session_head': False,
                                                    'description': str(sl_no) + "." + t_val['name'],
                                                    'quantity': t_val['qty']}))
                    sl_no = sl_no + 1
            values = {
                'partner_id': rent_agreement.partner_id.id,
                'building': rent_agreement.building.id,
                'property_id': rent_agreement.property_id.id,
                'electricity_account_ids': rent_agreement.property_id.electricity_account_ids.ids,
                'water_account_ids': rent_agreement.property_id.water_account_ids.ids,
                'rent_id': rent_agreement.id,
                'company': True if rent_agreement.partner_id.is_company else False,
                'hand_over_checklist': asset_values_sql,
                'state': 'draft'
            }
            check_list_id = checklist_obj.create(values)
        action = self.env["ir.actions.act_window"]._for_xml_id('property_lease_management.action_checklist')
        form_view = self.env.ref('property_lease_management.view_checklist_form')
        action['views'] = [(form_view.id, 'form')]
        action['res_id'] = check_list_id and check_list_id.id
        self.handover_check_id = check_list_id.id
        # action['target'] = 'new'
        return action

    @api.depends('residing_since')
    def _residing_since(self):
        if type(self.residing_since) != bool:
            start_date = datetime.strptime(str(self.residing_since), "%Y-%m-%d").date()
            date_today = datetime.strptime(str(fields.date.today()), "%Y-%m-%d").date()
            years = relativedelta(date_today, start_date).years
            months = relativedelta(date_today, start_date).months
            y = ""
            m = ""
            if years > 0:
                if years == 1:
                    y = str(years) + "year"
                else:
                    y = str(years) + "years"
            if months > 0:
                if months == 1:
                    m = str(months) + "month"
                else:
                    m = str(months) + "months"
            self.tenant_years = y + ',' + '' + m
        else:
            self.tenant_years = ''

    @api.depends('property_id', 'agreed_rent_amount')
    def _compute_amount(self):
        if self.property_id:
            if self.property_id.bed_rooms:
                self.property_type = str(self.property_id.bed_rooms) + "BHK"
            else:
                self.property_type = self.property_id.property_type_id.name
            price = self.property_id.rent_price
            monthly_rent = price / 12
            self.annual_rent = price
            self.rent_price = monthly_rent
            if self.agreed_rent_amount:
                if self.period:
                    self.rent_total = self.agreed_rent_amount * self.period
        else:
            self.annual_rent = 0
            self.rent_price = 0
            self.rent_total = 0

    @api.onchange('property_id')
    def onchange_flat(self):
        if self.property_id:
            price = self.property_id.rent_price
            monthly_rent = price / 12
            self.agreed_rent_amount = monthly_rent

    @api.depends('period', 'from_date')
    def _compute_todate(self):
        for record in self:
            if record.period and record.from_date:
                to_date = record.from_date + relativedelta(months=+record.period)
                record.to_date = to_date - timedelta(1)
            else:
                record.to_date = False

    def open_invoices(self):
        ''' Redirect the user to the invoice(s) for this rent agreement.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id('account.action_move_out_invoice_type')
        ctx = dict(self.env.context)
        ctx.update({'create': False, 'default_move_type': 'out_invoice'})
        views = self.env.ref('property_lease_management.view_invoice_tree_property')
        action['context'] = ctx
        action.update({
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'views': [(views.id, 'tree'), (False, 'form'), (False, 'kanban')]
        })
        return action

    def open_payments(self):
        ''' Redirect the user to the invoice(s) for this rent agreement.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Payments"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'default_partner_id': self.partner_id.id,
                        'default_rent_id': self.id}
        }
        payments = self.env['account.payment'].search([
            ('partner_id', '=', self.partner_id.id),
            ('payment_type', '=', 'inbound'),
            ('rent_id', '=', self.id)])

        payments |= self.env['account.payment'].search([('reconciled_invoice_ids', 'in', self.invoice_ids.ids),
                                                        ('partner_id', '=', self.partner_id.id),
                                                        ('payment_type', '=', 'inbound'),
                                                        ('rent_id', '=', self.id)])

        # TODO Can add cheque number same payments by partner id, add accordingly

        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            # changed the tree view to the default payment tree view to avoid error
            view = self.env.ref('account.view_account_payment_tree')
            action.update({
                # 'view_mode': 'list,form',
                'views': [(view.id, 'tree'), (False, 'form')],
                'domain': [('id', 'in', payments.ids)],
            })
        return action

    def compute_installments(self):
        """
        Lets Compute Installments and invoices.
        """
        self.ensure_one()
        # if self.state not in ('draft', 'with_section','open'):
        #     raise UserError("Installment can be computed only before the rent agreement approval")
        if self.property_id.for_parking:
            if not self.parking_line_ids:
                """Validation error while parking slot have no value if the Unit is For parking"""
                raise UserError("Please Select Parking Slot")
        if not (self.period and self.from_date) or not self.agreed_rent_amount or not self.to_date:
            raise UserError(
                "Required Fields Missing. \n (Rental Period/ Lease Start Date/ Lease End Date/ Agreed Rent Amount)")
        if not any(self.invoice_ids.filtered(lambda invoice: invoice.state in (
                'posted', 'cancel'))) or not any(
            self.collection_ids.filtered(lambda installment: installment.state in ('draft0'))):
            # Compute Installments
            self.generate_installment_lines()
            # Compute Invoices
            self.generate_invoices()
            self.invoice_created = False
        else:
            raise UserError("Not allowed to recompute installment/Rental Invoices if any of journal posted.")

    def update_description(self):
        for invoice in (self.invoice_ids.filtered(lambda invoice: invoice.state in (
                'posted'))):
            for inv in invoice.invoice_line_ids:
                inv.name = 'Rent For Unit No: ' + str(self.property_id.name) + ' At ' + \
                           str(self.building.name) + ' ' + 'Rental Period' + ' ' + str(
                    invoice.rental_period_id.from_date) + ' ' + 'to' + ' ' + str(invoice.rental_period_id.to_date)

    # @api.onchange('installment_schedule', 'period', 'from_date', 'agreed_rent_amount')
    def generate_installment_lines(self):
        """
        Here The Installments are appending
        :return:
        """

        # if self.invoice_ids:
        #     raise Warning('Not Allowed')
        # function to generate period entries
        def get_lines_for_eachperiod(rent_rec, start_date, end_date, period, period_len, anual_rent_amt):
            entries = []
            try:
                for i in range(0, int(period)):
                    if self.installment_schedule == 'one_bill':
                        l_period = self.to_date
                        vals = {
                            'name': 'Period' + str(i + 1),
                            'sl_no': i + 1,
                            'from_date': start_date,
                            'to_date': l_period,
                            'state': 'draft',
                        }
                        entries.append((0, 0, vals))
                    else:
                        end_date = start_date + relativedelta(months=+period_len)
                        l_period = end_date - timedelta(1)
                        if start_date >= lease_acquired:
                            vals = {
                                'name': 'Period' + str(i + 1),
                                'sl_no': i + 1,
                                'from_date': start_date,
                                'to_date': l_period,
                                'state': 'draft',
                            }
                            entries.append((0, 0, vals))
                        start_date = end_date
                return entries
            except TypeError:
                raise UserError("Period Must be Adjusted For Correct Installment Calculation.")

        # function to get lines for installments
        def get_lines_for_installments(rent_rec, start_date, end_date, period, period_len, anual_rent_amt):
            i_entries = []
            period_amt = float(rent_rec.rent_total / period) * period_len
            for index, period_line in enumerate(self.period_line_ids):
                end_date = start_date + relativedelta(months=+period_len)
                l_period = end_date - timedelta(1)
                if start_date >= lease_acquired:
                    i_vals = {
                        'date': start_date,
                        'amount': period_amt,
                        'cash_cheque': 'check',
                        'state': 'draft0',
                        'building': rent_rec.building.id,
                        'property_id': rent_rec.property_id.id,
                        'tenant_id': rent_rec.partner_id.id,
                        'agreemnt_no': rent_rec.name,
                        'from_date': rent_rec.from_date,
                        'to_date': l_period,
                        'period_ids': period_line.id
                    }
                    i_entries.append((0, 0, i_vals))
                start_date = end_date
            return i_entries

        if not self.lease_acquired:
            self.lease_acquired = self.from_date
        lease_acquired = self.lease_acquired

        # # Check The Lease Acquired Date
        # if self.lease_acquired and self.lease_acquired > self.from_date:
        #     start_date = self.lease_acquired
        # else:
        #     start_date = self.from_date

        if self.period and self.from_date:
            period_len = 1
            period = self.period
            if self.installment_schedule == 'quaterly':
                period = int(period // 3)
                period_len = 3
            if self.installment_schedule == 'six_month':
                period = int(period // 6)
                period_len = 6
            if self.installment_schedule == 'yearly':
                period = int(period // 12)
                period_len = 12
            if self.installment_schedule == 'one_bill':
                to_date = self.to_date
            else:
                to_date = self.from_date + relativedelta(months=+self.period)
            start_date_with_accquired = self.lease_acquired or self.start_date
            # check if updated rent total or standard rent total
            if self.agreed_rent_amount:
                monthly_amt = self.agreed_rent_amount
                self.rent_total = monthly_amt * self.period
            else:
                monthly_amt = self.rent_price
                self.rent_total = monthly_amt * self.period

            # get the lines for rental period monthly
            entries = get_lines_for_eachperiod(self, self.from_date, to_date, period, period_len, self.annual_rent)
            self.period_line_ids.unlink()
            if entries:
                self.period_line_ids = entries

            if self.installment_schedule == 'monthly':
                i_entries = get_lines_for_installments(self, start_date_with_accquired, to_date, self.period, 1,
                                                       self.annual_rent)

            elif self.installment_schedule == 'quaterly':
                to_date = self.from_date + relativedelta(months=+(period * 3))
                i_entries = get_lines_for_installments(self, start_date_with_accquired, to_date, self.period, 3,
                                                       self.annual_rent)

            elif self.installment_schedule == 'six_month':
                to_date = self.from_date + relativedelta(months=+(period * 6))
                i_entries = get_lines_for_installments(self, start_date_with_accquired, to_date, self.period, 6,
                                                       self.annual_rent)

            elif self.installment_schedule == 'yearly':
                to_date = self.from_date + relativedelta(months=+(period * 12))
                i_entries = get_lines_for_installments(self, start_date_with_accquired, to_date, self.period, 12,
                                                       self.annual_rent)
            elif self.installment_schedule == 'one_bill':
                if self.to_date:
                    to_date = self.to_date
                    i_entries = get_lines_for_installments(self, start_date_with_accquired, to_date, self.period,
                                                           int(self.period),
                                                           self.annual_rent)
            else:
                i_entries = False
            self.collection_ids.unlink()
            if i_entries:
                self.collection_ids = i_entries
        else:
            self.collection_ids.unlink()
            self.period_line_ids.unlink()
            self.rent_total = 0

    def generate_invoices(self):
        for rec in self:
            if not rec.revenue_account:
                raise UserError(_('Revenue Account Required.'))
            if not self.agreement_type:
                raise UserError(_('Please Configure Agreement type.'))
            if not self.tax_id:
                if self.agreement_type:
                    if self.agreement_type == 'commercial':
                        raise UserError(_('Please Configure Tax.'))
            if not any(rec.invoice_ids.filtered(lambda invoice: invoice.state in (
                    'posted', 'cancel'))) or not any(
                rec.collection_ids.filtered(lambda installment: installment.state in ('draft0'))):
                rec.partner_id.property_account_receivable_id = rec.account_id.id
                rec.invoice_ids.unlink()  # unlink
                inv_list = []
                for index, line in enumerate(rec.collection_ids):
                    total_len = len(rec.collection_ids)
                    # invoice_date_due = line.date.replace(day=calendar.monthrange(line.date.year, line.date.month)[1])
                    end_date = line.date + relativedelta(months=index + 1)
                    l_period = end_date - timedelta(1)

                    inv_vals = {
                        'ref': rec.name + ' Rent Installment Entry (%s/%s)' % (index + 1, total_len),
                        'partner_id': rec.partner_id.id,
                        'invoice_date': line.date,
                        'invoice_date_due': line.date,
                        'invoice_origin': rec._origin.name,
                        'invoice_payment_term_id': rec.partner_id.property_payment_term_id and rec.partner_id.property_payment_term_id.id,
                        'journal_id': rec.journal_id.id,
                        'invoice_line_ids': [(0, 0, {
                            'name': 'Rent For Unit No: ' + str(self.property_id.name) + ' At ' +
                                    str(self.building.name) + '(%s/%s)' % (
                                        index + 1, total_len) + '  with  M No:  %s </b>' % (
                                        str(self.muncipality_agreemnt_no)) + ' Period : %s To :%s ' % (
                                        line.date, l_period),
                            'account_id': rec.revenue_account.id,
                            # 'analytic_account_id': rec.building.bu_cc.id,
                            'price_unit': line.amount,
                            'price_subtotal': line.amount,
                            'price_total': line.amount,
                            'tax_ids': [[6, False, [rec.tax_id.id]]] if line.date >= datetime.strptime('2021-05-01',
                                                                                                       '%Y-%m-%d').date() and rec.tax_id else [
                                [6, False, []]]
                        }), ],
                        'amount_total': line.amount,
                        'name': '/',
                        'asset_value_change': False,
                        # 'auto_post': True,
                        'move_type': 'out_invoice',
                        'property_id': rec.property_id.id,
                        'rent_id': rec._origin.id,
                        'rental_period_id': line.period_ids.id,
                        'rental_installment_id': line.id
                    }
                    # if line.date >= datetime.strptime('2021-05-01', '%Y-%m-%d').date():
                    #     inv_vals['invoice_line_ids'][0][2]['tax_ids'] = [[6, False, [rec.tax_id.id]]]
                    inv_list.append((0, 0, inv_vals))
                if inv_list:
                    rec.write({
                        'invoice_ids': inv_list
                    })
                    refs = ["<a href=# data-oe-model=account.move data-oe-id=%s>%s</a>" % tuple(name_get) for name_get
                            in rec.name_get()]
                    message = _("This Rent Installment Invoice has been created from: %s") % ','.join(refs)
                    for inv in rec.invoice_ids:
                        today_date = date.today()
                        if inv.invoice_date > today_date:
                            inv.message_post(body=message)
                            inv.write({'state': 'draft'})  # To create Draft Entries

                        else:
                            """ Previous Month Invoice State Change TO Post State"""
                            inv.message_post(body=message)
                            inv.action_post()  # post entries

                    for installment in rec.collection_ids:
                        invoice = self.env['account.move'].search(
                            [('rental_installment_id', '=', installment.id),
                             ('state', '!=', 'cancel')])
                        installment.invoice_id = invoice and invoice.id

            else:
                raise UserError("Not allowed to recompute installment/Rental Invoices if any of journal posted.")

    @api.depends('collection_ids')
    def _compute_cheque_total(self):
        if self.collection_ids:
            self.cheq_deposit = sum([collection.amount for collection in self.collection_ids if
                                     collection.state == 'paid'])
        else:
            self.cheq_deposit = 0

    @api.depends('installment_ids')
    def _compute_total_deposit(self):
        if self.installment_ids:
            self.deposit_collected = sum([installment.amount for installment in self.installment_ids])
        else:
            self.deposit_collected = 0

    @api.depends('installment_ids')
    def _compute_total_amount(self):
        for rec in self:
            if rec.installment_ids:
                rec.deposit_total = sum([installment.amount for installment in rec.installment_ids if
                                         installment.installment_type == 'deposit'])
                rec.installment_total = sum([installment.amount for installment in rec.installment_ids if
                                             installment.installment_type == 'installment'])
                rec.fee_total = sum([installment.amount for installment in rec.installment_ids if
                                     installment.installment_type == 'fee'])
            else:
                rec.deposit_total = 0
                rec.installment_total = 0
                rec.fee_total = 0

    @api.constrains('rent_sqm')
    @api.onchange('rent_sqm')
    def _onchange_rent_sqm(self):
        """Agreed amount is calculated """
        if self.rent_sqm:
            self.agreed_rent_amount = self.rent_sqm * self.area

    def write(self, vals):
        """
        :param vals:
        :return:
        """
        res = super(PropertyRent, self).write(vals)
        if vals.get('lease_acquired'):
            lease_acquired = fields.Date.from_string(self.lease_acquired)
            from_date = fields.Date.from_string(self.from_date)
            if lease_acquired > from_date:
                installments = self.collection_ids.filtered(
                    lambda rec: rec.state not in ['draft', 'paid', 'cancel'] and fields.Date.from_string(
                        rec.date) < lease_acquired)
                installments.write({'state': 'lease_acquired_issue'})
                # if not self.invoice_ids:  # if no invoice, then create and track before update
                #     self.create_invoice()
                # invoice_ids = self.invoice_ids.filtered(
                #     lambda rec: rec.state not in ['cancel', 'paid'] and fields.Date.from_string(
                #         rec.date_invoice) < lease_acquired)
                # invoice_ids.with_context(rent=True).action_cancel()
        # for record in self:
        #     if "legal_case" in vals:
        #         if record.legal_case and record.state in ['to_renew', 'open']:
        #             record.prev_state = record.state
        #             record.state = 'legal_case'
        #         if not record.legal_case and record.state == 'legal_case':
        #             if record.prev_state == 'open':
        #                 date_today = datetime.strptime(str(fields.date.today()), "%Y-%m-%d").date()
        #                 if fields.Datetime.from_string(record.to_date).date() < date_today:
        #                     record.state = 'to_renew'
        #                     record.prev_state = ''
        #                 else:
        #                     record.state = 'open'
        #                     record.prev_state = ''
        #             else:
        #                 record.state = 'to_renew'
        return res

    def button_action_create_legal_case(self):
        for rec in self:
            case_id = self.env['dispute.legal.action'].create({
                'partner_id': rec.partner_id.id,
                'rent_id': rec.id,

            })
            rec.legal_case = True
            return {
                'name': _("Legal Action"),
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'dispute.legal.action',
                'res_id': case_id.id,
                'type': 'ir.actions.act_window',
                'target': 'current',
                # 'domain': '[]',
                # 'context': {
                #     'default_partner_id': rec.partner_id.id,
                #     'default_rent_id': rec.id,
                # }
            }

    def action_view_legal_case(self):
        """ action to show bill"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Legal Case ',
            'view_mode': 'tree,form',
            'res_model': 'dispute.legal.action',
            'domain': [('rent_id', '=', self.id)],
        }

    # Commented By Ajmal jul 8
    def button_action_create_vacating_information(self):
        for rec in self:
            release_id = self.env['tenant.deposit.release'].create({
                'partner_id': rec.partner_id.id,
                'rent_id': rec.id,
                'security_deposit': rec.security_deposit,

            })
            rec.legal_case = True
            return {
                'name': _("Vacating Information"),
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'tenant.deposit.release',
                'res_id': release_id.id,
                'type': 'ir.actions.act_window',
                'target': 'current',
            }


    def action_view_vacating_information(self):
        """ action to show bill"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vacating Information ',
            'view_mode': 'tree,form',
            'res_model': 'tenant.deposit.release',
            'domain': [('rent_id', '=', self.id)],
        }

    def copy(self, default=None):
        """
        Restrict
        @param default:
        @return:
        """
        raise UserError("Restricted!")

    def unlink(self):
        for rent_id in self.ids:
            rent_record = self.browse(rent_id)
            if self.search([('reference_id', '=', rent_id)]):
                raise UserError(_('You cannot delete an rent agreement which is referred in another agreement .'))
            elif rent_record.move_ids:
                raise UserError(_('You cannot delete an agreement which posted some entries to a Journal.'
                                  '\nFirst you should cancel that entries'))
            elif rent_record.payment_ids:
                raise UserError(_('You cannot delete an agreement which contains some payments.'
                                  '\nFirst you should delete the Payment Records'))
            elif rent_record.state in ('open', 'to_renew'):
                raise UserError(_('You cannot delete an agreement which is not in close.'))
            return super(PropertyRent, self).unlink()

    @api.onchange('legal_case')
    def onchange_legal_case(self):
        for record in self:
            if record.legal_case and record.state in ['to_renew', 'open']:
                record.prev_state = record.state
                record.state = 'legal_case'
            if not record.legal_case and record.state == 'legal_case':
                if record.prev_state == 'open':
                    date_today = datetime.strptime(str(fields.date.today()), "%Y-%m-%d").date()
                    if fields.Datetime.from_string(record.to_date).date() < date_today:
                        record.state = 'to_renew'
                        record.prev_state = ''
                    else:
                        record.state = 'open'
                        record.prev_state = ''
                else:
                    record.state = 'to_renew'

    @api.onchange('partner_id')
    def _onchange_partner(self):
        account_id = False
        if self.partner_id:
            account_id = self.partner_id.property_account_receivable_id.id
        self.account_id = account_id

    @api.onchange('property_id')
    def _onchange_property(self):
        if self.property_id:
            self.std_rent_sqm = self.property_id.rent_sqm
            self.area = self.property_id.area

    @api.onchange('date')
    def _onchange_date(self):
        if self.date:
            self.year = self.date.year

    def button_notice(self):
        self.state = 'notice'

    def button_confirm(self):
        if not self.property_id.for_parking:
            self.property_id.sudo().write({'state': 'rented'})
            for p in self.env['property.property'].search([('parent_id', '=', self.property_id.id)]):
                p.sudo().write({'state': 'rented'})

        self.write({'state': 'open'})
        return True

    def button_cancel(self):
        cancel_id = self.env['agreement.cancellation'].search([('rent_id', '=', self.id)])
        take_over_checklist_obj = self.env['property.checklist.takeover']
        check_list_id = take_over_checklist_obj.search([('rent_id', '=', self.id), ('state', '=', 'confirm')], limit=1)
        vacation_info_obj = self.env['tenant.deposit.release']
        vacation_info_id = vacation_info_obj.search([('rent_id', '=', self.id), ('state', '=', 'approved')], limit=1)
        if not check_list_id:
            raise UserError('There is no Confirmed TakeOver Checklist.')

        if not vacation_info_id:
            raise UserError('There is no Confirmed Vacating Information Please Confirm Vacating Information.')
        if not vacation_info_id.move_id:
            raise UserError('There is no Invoice is Generated Against Vacating Information.')
        if vacation_info_id.move_id and vacation_info_id.move_id.payment_state != 'paid':
            raise UserError('Invoice is Generated Against Vacating Information is Not Paid.')
            
        if not cancel_id:
            if self.key_received:
                values = {
                    'rent_id': self.id,
                    'partner_id': self.partner_id.id,
                    'building': self.building.id,
                    'property_id': self.property_id.id,
                }
                cancel_id = self.env['agreement.cancellation'].create(values)
                self.cancellation_form = cancel_id
            else:
                raise UserError('Keys not received !!!')
        action = self.env["ir.actions.act_window"]._for_xml_id('property_lease_management.action_agreement_cancel')
        form_view = self.env.ref('property_lease_management.view_cancellation_form')
        action['views'] = [(form_view.id, 'form')]
        action['res_id'] = cancel_id and cancel_id.id
        return action

    def make_installment(self, ):
        """ commended the code to remove the property voucher"""
        account_id = False
        # if self.installment_type == 'fee':
        #     dummy, view_id = self.env['ir.model.data'].get_object_reference('amlak_property_management',
        #                                                                     'view_property_payment_dialog_form')
        #     name = _("Payment Voucher")
        # else:
        #     dummy, view_id = self.env['ir.model.data'].get_object_reference('amlak_property_management',
        #                                                                     'view_property_receipt_dialog_form')
        #     name = _("Receipt Voucher")
        #     account_id = self.account_id.id
        # if self.property_id.contract_type == 'management':
        #     account_id = self.property_id.partner_id.property_account_receivable_id.id
        #
        # context_dict = {
        #     'default_partner_id': self.partner_id.id,
        #     'default_agreement_id': self.id,
        #     'default_type': 'receipt',
        #     'default_installment_type': self.installment_type,
        #
        # }
        # if account_id:
        #     context_dict['default_account_id'] = account_id
        # return {
        #     'name': name,
        #     'view_mode': 'form',
        #     'view_id': view_id,
        #     'view_type': 'form',
        #     'res_model': 'property.voucher',
        #     'type': 'ir.actions.act_window',
        #     'nodestroy': True,
        #     'target': 'new',
        #     'domain': '[]',
        #     'context': context_dict
        # }

    def button_copy_agreement(self):
        new_id = self.copy()
        # view_id = self.env['ir.model.data'].get_object_reference('property_lease_management', 'view_rent_form')[1]
        view_ref = self.env.ref('property_lease_management.view_rent_form')[1]
        view_id = view_ref and view_ref.id or False,
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rent Agreement'),
            'res_model': 'property.rent',
            'res_id': new_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }

    @api.model
    def check_renew(self):
        date_today = datetime.strptime(str(fields.date.today()), "%Y-%m-%d").date()
        rent_agreements = self.env['property.rent'].search([('state', '=', 'open'), ('to_date', '<', date_today)])
        for i in rent_agreements:
            i.state = 'to_renew'

    # def send_to_section(self):
    #     if self.resend:
    #         self.resend = False
    #     self.state = 'with_section'


class RentInstallment(models.Model):
    _name = 'property.rent.installment'
    _description = _('Installment Collection Details')
    _order = "date"

    id_temp = fields.Integer(string='ID Temp')
    sequence = fields.Char(string='Sr. No', readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer')
    amount = fields.Float(string='Installment Amount', digits='Product Price', readonly=True,
                          states={'draft': [('readonly', False)]})
    date = fields.Date(string='Date', readonly=True, states={'draft': [('readonly', False)]})
    cash_or_cheque = fields.Selection([('cash', _('Cash')), ('cheque', _('Cheque')), ('transfer', _('Transfer'))],
                                      string='Cash/Cheque')
    bank_name = fields.Char(string='Bank Name', readonly=True, states={'draft': [('readonly', False)]})
    cheque_number = fields.Char(string='Cheque No (IF)', readonly=True, states={'draft': [('readonly', False)]})
    installment_type = fields.Selection([('installment', _('Installment')), ('fee', _('Fee')),
                                         ('deposit', _('Deposit'))], string=_('Installment Type'), required=True,
                                        readonly=True, states={'draft': [('readonly', False)]})
    move_id = fields.Many2one(comodel_name='account.move', string='Journal Entry',
                              readonly=True, index=True, ondelete='cascade', copy=False,
                              help=_("Link to the automatically generated Journal Items."))
    receipt_number = fields.Char(string='Receipt Number', default=0,
                                 readonly=True, states={'draft': [('readonly', False)]})
    rent_id = fields.Many2one(comodel_name='property.rent', string='Rent Reference', required=True, ondelete='cascade')
    state = fields.Selection([('draft', _('Draft')), ('open', _('Open'))], string='Status', default='draft',
                             readonly=True, copy=False, help=_("Gives the status of the rent installment"))
    building = fields.Many2one(comodel_name='property.building', string='Building', related='rent_id.building',
                               store=True)
    flat = fields.Many2one(comodel_name='property.property', string='Flat', related='rent_id.property_id', store=True)
    company_id = fields.Many2one(string='Company', store=True, readonly=True,
                                 related='rent_id.company_id',
                                 )

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(RentInstallment, self).unlink()

    @api.model
    def create(self, vals):
        if not vals.get('receipt_number', False):
            vals['receipt_number'] = self.env['ir.sequence'].next_by_code('property.rent.installment')
        return super(RentInstallment, self).create(vals)

    def print_receipt(self):
        """This function prints installment receipt"""
        assert len(self) == 1, 'This option should only be used for a single id at a time'
        return self.env.ref('property_lease_management.action_report_rent_installment_receipt').report_action(self)


class RentInstallmentCollection(models.Model):
    _name = 'property.rent.installment.collection'
    _description = _('Rent Installment Details')
    _rec_name = 'period_ids'

    id_temp = fields.Integer(string='ID Temp')
    sequence = fields.Integer(string='Sr. No')
    amount = fields.Float(string='Installment Amount', digits='Product Price')
    date = fields.Date(string='Collection Date')
    cheque_number = fields.Char(string='Cheque No (IF)')
    rent_id = fields.Many2one(comodel_name='property.rent', string='Rent', ondelete='cascade', required=True)
    company_id = fields.Many2one(string='Company', store=True, readonly=True,
                                 related='rent_id.journal_id.company_id',
                                 )
    currency_id = fields.Many2one(string='Company Currency', readonly=True,
                                  related='company_id.currency_id')
    amount_total = fields.Monetary(related='invoice_id.amount_total')
    residual = fields.Monetary(related='invoice_id.amount_residual')
    building = fields.Many2one(comodel_name='property.building', string="Building")
    property_id = fields.Many2one(comodel_name='property.property', string="Unit")
    tenant_id = fields.Many2one(comodel_name='res.partner', string="Tenant")
    from_date = fields.Date(string="From")
    to_date = fields.Date(string="To")
    agreemnt_no = fields.Char(string="Agreement No.")
    rent_dummy = fields.Many2one(comodel_name='property.rent', string="Rent ref")
    period_ids = fields.Many2one(comodel_name='rent.period.lines', string='Rental Period')
    invoice_id = fields.Many2one(comodel_name='account.move', string='Invoice', compute='get_invoice', store=True)
    invoice_state = fields.Selection(related='invoice_id.state', string='Invoice Status')
    cash_cheque = fields.Selection([('cash', _('Cash')), ('check', _('Cheque')), ('transfer', _('Transfer'))],
                                   string='Cash/Cheque')
    remarks = fields.Char('Remarks')
    state = fields.Selection(
        [('draft0', _('Waiting Collection')), ('draft', _('Cash / Cheque Deposited')), ('paid', _('Collected')),
         ('cancel', _('Bounced')), ('lease_acquired_issue', 'Installment Before Lease Acquired'),
         ('waived', _('Waived')), ],
        string='Status', default="draft0", readonly=True)

    def unlink(self):
        for record in self:
            if record.state not in ['draft0', 'draft']:
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(RentInstallmentCollection, self).unlink()

    def change_state(self):
        vals = {
            'sequence': self.sequence,
            'amount': self.amount,
            'date': self.date,
            'cash_cheque': self.cash_cheque,
            'cheque_number': self.cheque_number,
            'rent_id': self.rent_id.id,
            'state': 'cancel',
            'collected_id': self.id,
        }
        bounced_vals = {
            'sequence': self.sequence,
            'amount': self.amount,
            'date': self.date,
            'cheque_number': self.cheque_number,
            'rent_id': self.rent_id.id,
            'collected_id': self.id,
            'remarks': self.remarks
        }
        self.state = 'cancel'
        bounce = self.env['property.bounced.cheque'].sudo().create(bounced_vals)
        self.rent_id.collection_ids_bounce = [(0, 0, vals)]
        self.rent_id.update({'notification_ids': [(0, 0, {'rent_id': self.rent_id.id,
                                                          'building_id': self.rent_id.building.id,
                                                          'property_id': self.rent_id.property_id.id,
                                                          'partner_id': self.rent_id.partner_id.id,
                                                          'notification_date': fields.date.today(),
                                                          'description': 'Cheque Bounced',
                                                          'notification_type': 'check_bounce'})]})
        body = """<div style="padding:0px;font-size: 16px;width:600px;background:#FFFFFF repeat top /100%;color:#777777">
                       <p style="font-weight:bold;">Dear {tenant},</p>
                       <p> </p>
                       <p>This is to inform you that the payment you made to our company Aqar Real Estate has been
                        returned to us by the bank on grounds of “insufficient funds”. The check
                        #<strong>{cheque}</strong> was not accepted by the bank as your account does not have
                        sufficient balance.<p/>
                       <p> We understand that this is a mere case of over sightedness. To clear this issue, we would
                       request you to pay us the due amount within the coming days, by the {due_date} at the latest.</p>
                       <p/><p>We are thankful to you for your consistent business relations with our company and would
                       appreciate it if you would look into the above matter as soon as possible. Thank you for your
                        cooperation. We look forward to serve you for many years to come.</p><p/>
                       <p>Should you have any questions, feel free to contact me at 79434432 from 8am to 4pm or
                        e-mail me at raiya.amlak@gmail.com</p>
                        <p style="font-weight:bold;">Sincerely, Raiya Al-shaaili</p>
                        <p style="font-weight:bold;">Assistant Property Manager In charger </p>
                """.format(cheque=self.cheque_number, tenant=self.rent_id.partner_id.name, due_date=self.date)
        #
        # main_content = {
        #     'subject': _('NOTICE FOR THE RETURN CHEQUE'),
        #     'author_id': SUPERUSER_ID,
        #     'body_html': body,
        #     'email_to': self.rent_id.partner_id.email,
        #     'state': 'outgoing'
        # }

        return {
            'name': _("NOTICE FOR THE CHEQUE BOUNCE"),
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
                'default_partner_id': self.rent_id.partner_id.id,
                'default_subject': "NOTICE FOR THE CHEQUE BOUNCE",
                'default_message': body,
            }
        }
        # mail = self.env['mail.mail'].sudo().create(main_content)
        # mail.sudo().send(raise_exception=False)
        # return True

    def action_invoice_post(self):
        """
        :return:
        """
        for rec in self:
            if rec.invoice_id:
                rec.invoice_id.action_post()

    @api.depends('period_ids')
    def get_invoice(self):
        for record in self:
            if record.state == 'lease_acquired_issue':
                raise UserError(
                    'You are not allowed to link the invoice, The installment is generated before the lease is acquired.')
            if record.period_ids:
                invoice = self.env['account.move'].search(
                    [('rental_period_id', '=', record.period_ids.id),
                     ('state', '!=', 'cancel')])
            else:
                invoice = self.env['account.move'].search(
                    [('rental_installment_id', '=', record._origin.id),
                     ('state', '!=', 'cancel')])
            # commended the code for check bounced
            # if invoice:
            #     record.invoice_id = invoice.id

    @api.model
    def create(self, vals):
        vals.update({'rent_dummy': vals['rent_id']})
        return super(RentInstallmentCollection, self).create(vals)

    def change_state_paid(self):
        """manually make the collection as paid if the invoice is paid and the state is not changed"""
        if self.invoice_id:
            if not self.cheque_number:
                raise UserError("Enter the cheque number!")

            # self.write({'state': 'paid'})
            # self.period_ids.write({'state': 'done'})
            voucher_ids = self.env['account.payment'].search([('rental_installment_id', '=', self.id),
                                                              ('state', 'not in', ['cancel'])])

            voucher_ids |= self.env['account.payment'].search([('rent_id', '=', self.rent_id.id),
                                                               ('cheque_no', '=', self.cheque_number),
                                                               ('state', 'not in', ['cancel']), ])
            if not voucher_ids:
                raise UserError(
                    "Vouchers Already Reconciled / Please check and make sure related payment with correct cheque number is linked with agreement.")
            for payment in voucher_ids:
                if not payment.cheque_no:
                    payment.write({'cheque_no': self.cheque_number})
                if payment.state != 'posted' and payment.state != 'cancel':
                    if payment.name or payment.name == '/':
                        payment.get_sequence_number()
                    payment.action_post()
                domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                payment_lines = payment.line_ids.filtered_domain(domain)
                # if payment.curr_move_line:
                #     for account in payment_lines.account_id:
                #         (payment_lines + payment.curr_move_line.mapped('line_ids')) \
                #             .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]) \
                #             .reconcile()
                # elif payment.selection_move_line:
                # slection_move_line field is also created from thabat_accounting
                # if payment.selection_move_line:
                #     for account in payment_lines.account_id:
                # commended the below code to avoid the error of allocated_amount
                # (payment_lines + payment.selection_move_line.filtered(
                #     lambda rec: rec.allocated_amount > 0).mapped(
                #     'line_ids')) \
                #     .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]) \
                #     .reconcile(selection=True)
                # else:
                for account in payment_lines.account_id:
                    if self.invoice_id.mapped('line_ids') \
                            .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', True)]):
                        raise UserError("Invoice Already Reconciled.")
                    (payment_lines + self.invoice_id.mapped('line_ids')) \
                        .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]) \
                        .reconcile()
                    if self.invoice_id.payment_state == 'paid':
                        self.state = 'paid'

        else:
            raise UserError('Please Link Invoices')

    def change_state_deposited(self):
        if self.cash_cheque == 'check' and not self.cheque_number:
            raise UserError('Allocate Cheque Number in installment lines before depositing')
        if not self.period_ids:
            raise UserError('Allocate period in installment lines before depositing')
        if not self.invoice_id:
            raise UserError('Link Invoice in installment lines Before Posting')

        voucher_ids = self.env['account.payment'].search([('rental_installment_id', '=', self.id),
                                                          ('state', 'not in', ['cancel', 'posted'])])
        voucher_ids = self.env['account.payment'].search([('rent_id', '=', self.rent_id.id),
                                                          ('state', 'not in', ['cancel', 'posted'])])
        # self.state = 'draft'

    # TODO Installment link invo
    def make_installmentt(self):
        """
        :return:
        """
        view_id = self.env.ref('account_voucher.view_vendor_receipt_dialog_form')

        if self.invoice_id and self.invoice_id.period_id:
            period_id = self.invoice_id.period_id.id
        else:
            period_id = False

        voucher_id = self.env['account.pay'].search([('inv_id', '=', self.invoice_id.id),
                                                     ('state', 'not in', ['posted', 'cancel'])])
        for record in voucher_id:
            line_cr_ids = record.line_cr_ids.filtered(lambda rec: rec.amount > 0)
            if line_cr_ids:
                voucher_id = False
            else:
                voucher_id = record

        journal = self.env['account.journal'].search(
            [('code', '=', 'OAB P')])
        return {
            'name': _("Pay Invoice"),
            'view_mode': 'form',
            'view_id': view_id.id,
            'view_type': 'form',
            'views': [(view_id.id, 'form')],
            'res_model': 'account.payment',
            'res_id': voucher_id.id if voucher_id else False,
            'type': 'ir.actions.act_window',
            'nodestroy': False,
            'target': 'new',
            'domain': '[]',
            'context': {
                # 'default_account_id': self.rent_id.account_id.id,
                # 'default_building': self.rent_id.building.id,
                # 'default_property_id': self.rent_id.property_id.id,
                # 'default_agreement_id': self.rent_id.id,
                # 'default_cost_center_id': self.rent_id.building.bu_cc.id,
                'default_name': self.invoice_id.number,
                'default_invoice_id': self.invoice_id.id,
                'default_inv_id': self.invoice_id.id,
                'default_rent_id': self.rent_id.id,
                'default_cheque_no': self.cheque_number,
                'cheque_no': self.cheque_number,
                'default_payment_expected_currency': self.invoice_id.currency_id.id,
                'payment_expected_currency': self.invoice_id.currency_id.id,
                'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(
                    self.invoice_id.partner_id).id,
                'default_amount': self.invoice_id.residual,
                'default_reference': self.rent_id.name,
                'default_close_after_process': True,
                'default_invoice_type': self.invoice_id.type,
                'default_journal_id': journal and journal[0].id if self.rent_id.building.type == 'out' else '',
                'default_type': self.invoice_id.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
                'type': self.invoice_id.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
                'period_id': period_id,
                'close_after_process': True,
                'default_cash_or_cheque': 'cheque' if self.cash_cheque == 'check' else self.cash_cheque,
                'cash_cheque': 'cheque' if self.cash_cheque == 'check' else self.cash_cheque,
            }
        }

    def post_entries(self):
        """
        :return:
        """
        voucher_ids = self.env['account.payment'].search([('rental_installment_id', '=', self.id),
                                                          ('state', 'not in', ['cancel'])])
        voucher_ids |= self.env['account.payment'].search([('rent_id', '=', self.rent_id.id),
                                                           ('cheque_no', '=', self.cheque_number),
                                                           ('state', 'not in', ['cancel', 'posted'])])
        voucher_ids |= self.env['account.payment'].search(
            [('cheque_no', '=', self.cheque_number), ('partner_id', '=', self.rent_id.partner_id.id),
             ('state', 'not in', ['cancel', 'posted'])])
        journal = self.env['account.journal'].search(
            [('code', '=', 'OAB P')])
        if voucher_ids and self.state == 'draft0':
            self.state = 'draft'
            return

        rental_period_id = self.rent_id.period_line_ids and self.rent_id.period_line_ids.filtered(
            lambda p: p.from_date <= self.date and self.date <= p.to_date) or False
        if rental_period_id:
            rental_period_id.write({'state': 'done'})
        # elif voucher_ids:
        #     raise UserError(
        #         "Already Cash / Cheque Registered %s - Cheque Numbers %s \n Please post entries if already check/cash registered." % (
        #             voucher_ids.mapped(
        #                 'name'), voucher_ids.mapped(
        #                 'cheque_no')))

        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.invoice_id.id,
                'active_id': self.invoice_id.id,
                'default_cheque_no': self.cheque_number,
                'default_journal_id': journal and journal.id,
                'rent_collection': True,
                'rent_collection_id': self.id,
                'rent_period_id': self.period_ids.id,
                'default_rental_installment_id': self.id,
                'default_rent_id': self.rent_id and self.rent_id.id or False,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }


# property installments bounced
class RentInstallmentCollectionBounced(models.Model):
    _name = 'property.rent.installment.collection.bounced'
    _inherit = 'property.rent.installment.collection'
    _description = "Rent Installment Collection Bounced Details"

    state = fields.Selection(selection_add=[('draft', _('Waiting collection'))], default='cancel',
                             ondelete={"draft": "cascade"})
    collected_id = fields.Many2one(comodel_name='property.rent.installment.collection', string='Collection Relation')

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(RentInstallmentCollectionBounced, self).unlink()

    # reverse bouced cheque
    def change_waiting(self):
        if self.collected_id:
            self.collected_id.write({"state": 'draft'})
        self.write({"state": 'draft'})
        self.collected_id = False
        self.unlink()
        return True


class ContractAutoJournalEntry(models.Model):
    _name = 'property.rent.auto.entry'
    _description = _('Auto Journal Entry Of Rent')

    sequence = fields.Integer(string='Sr. No', readonly=True)
    date = fields.Date(string='Collection Date', readonly=True)
    amount = fields.Float(string='Installment Amount', digits='Product Price', readonly=True)
    contract_id = fields.Many2one(comodel_name='property.rent', string='Contract', ondelete='cascade', required=True)
    state = fields.Selection([('pending', _('Pending')), ('sent', _('Sent')), ('cancel', _('cancelled'))],
                             string='Status', default='pending', readonly=True)
    sent = fields.Boolean(string='Sent')
    jurnal_id = fields.Many2one(comodel_name='account.move')

    def post(self):
        period_obj = self.env['account.period']
        move_line_obj = self.env['account.move.line']
        seq_obj = self.env['ir.sequence']
        cr = self.env.cr
        uid = self.env.uid
        period_ids = period_obj.find(dt=self.date)
        from_date = datetime.strptime(self.date, '%Y-%m-%d')

        # calculate due date
        total_days = calendar.monthrange(from_date.year, from_date.month)[1]
        last_date = '%s-%s-%s' % (from_date.year, from_date.month, total_days)
        to_date = datetime.strptime(last_date, '%Y-%m-%d')

        # get account id
        config = self.env['ir.config_parameter'].sudo()
        if self.contract_id.property_id.contract_type == 'investment':
            income_account_id = config.get_param('property.rent_income_account_id') or False
        else:
            income_account_id = config.get_param('property.own_rent_income_account_id') or False
        if not income_account_id:
            income_account_id = self.contract_id.journal_id.default_credit_account_id.id
        if not income_account_id:
            action = self.env.ref('property_lease_management.action_property_settings')
            msg = _('Cannot find an income account for this contract, You should configure it.'
                    ' \nPlease go to Property Configuration or set default credit account in journal.')
            raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

        if self.contract_id.journal_id.sequence_id:
            if not self.contract_id.journal_id.sequence_id.active:
                raise UserError(_('Configuration Error ! \nPlease activate the sequence of selected journal !'))
            name = seq_obj.next_by_id(self.contract_id.journal_id.sequence_id.id)
        else:
            raise UserError(_('Please define a sequence on the journal.'))
        narration = 'Rent Of ' + str(datetime.strptime(self.date, '%Y-%m-%d').strftime('%B %Y'))

        move_data = {
            'name': name,
            'journal_id': self.contract_id.journal_id.id,
            'date': from_date,
            'ref': self.contract_id.name,
            'period_id': period_ids[0].id,
            'narration': narration
        }
        move = self.env['account.move'].create(move_data)

        move_line1 = {
            'name': '/',
            'debit': self.amount,
            'credit': 0.0,
            'account_id': self.contract_id.account_id.id,
            'move_id': move.id,
            'journal_id': self.contract_id.journal_id.id,
            'period_id': period_ids[0].id,
            'partner_id': self.contract_id.partner_id.id,
            'date': from_date,
            'date_maturity': to_date
        }
        move_line_obj.create(move_line1)

        move_line2 = {
            'name': self.contract_id.name or '/',
            'debit': 0.0,
            'credit': self.amount,
            'account_id': income_account_id,
            'move_id': move.id,
            'journal_id': self.contract_id.journal_id.id,
            'period_id': period_ids[0].id,
            'partner_id': self.contract_id.partner_id.id,
            'date': from_date,
            'date_maturity': to_date
        }
        move_line_obj.create(move_line2)
        move.post()

        self.contract_id.write({'move_ids': [(4, move.id)]})
        self.write({'state': 'sent'})
        self.jurnal_id = move
        return True

    def cancel_button(self):
        ju = self.jurnal_id.id
        account_obj = self.env['account.move'].browse(ju)
        account_obj.button_cancel()
        self.state = 'pending'


class RentPeriodEntry(models.Model):
    _name = 'rent.period.lines'
    _description = "Rent Period Entries"

    id_temp = fields.Integer(string='ID Temp')
    name = fields.Char(string='Name')
    sl_no = fields.Char(string='No.')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    # 'amount': fields.float('Amount'),
    state = fields.Selection([('draft', _('Pending')), ('done', _('Collected'))],
                             string='Status', readonly=1)
    rent_ids = fields.Many2one(comodel_name='property.rent', string='Rent Ids')

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(RentPeriodEntry, self).unlink()


class PropertyNotification(models.Model):
    _name = 'property.notification'
    _rec_name = 'rent_id'
    _description = 'Property Notification'

    rent_id = fields.Many2one(comodel_name='property.rent', string='Rent Agreement')
    building_id = fields.Many2one('property.building', 'Building', related="rent_id.building", store=True)
    property_id = fields.Many2one(comodel_name='property.property', string='Unit', store=True,
                                  related="rent_id.property_id")
    partner_id = fields.Many2one(comodel_name='res.partner', string='Tenant', related="rent_id.partner_id")
    notification_date = fields.Date(string="Notified Date")
    description = fields.Text('Description')
    notification_type = fields.Selection([('rent_expiry', 'Rent Expiry'),
                                          ('dispute', 'Dispute Management'),
                                          ('check_bounce', 'Cheque Bounce')],
                                         'Notification Type')
    dispute_id = fields.Many2one('dispute.cheque.bounce')


class PropertyBouncedCheque(models.Model):
    _name = 'property.bounced.cheque'
    _description = 'Bounced Cheques'
    _rec_name = 'cheque_number'

    sequence = fields.Integer(string='Sr. No')
    amount = fields.Float(string='Installment Amount', digits='Product Price')
    date = fields.Date(string='Collection Date')
    cheque_number = fields.Char(string='Cheque No (IF)')
    rent_id = fields.Many2one(comodel_name='property.rent', string='Rent', ondelete='cascade', required=True)
    company_id = fields.Many2one(string='Company', store=True, readonly=True,
                                 related='rent_id.journal_id.company_id',
                                 )
    building = fields.Many2one(comodel_name='property.building', string="Building", related="rent_id.building",
                               store=True)
    property_id = fields.Many2one(comodel_name='property.property', string="Unit", related="rent_id.property_id",
                                  store=True)
    tenant_id = fields.Many2one(comodel_name='res.partner', string="Tenant", related="rent_id.partner_id", store=True)
    collected_id = fields.Many2one(comodel_name='property.rent.installment.collection', string='Collection Relation')
    period_ids = fields.Many2one(comodel_name='rent.period.lines', string='Rental Period',
                                 related="collected_id.period_ids")
    invoice_id = fields.Many2one(comodel_name='account.move', string='Invoice', related="collected_id.invoice_id")
    paid = fields.Boolean('Installment Paid', compute="compute_installment_paid")
    dispute_id = fields.Many2one('dispute.cheque.bounce', 'Dispute')
    dispute_legal_id = fields.Many2one('dispute.legal.action', 'Legal Action')
    remarks = fields.Char('Remarks')

    def compute_installment_paid(self):
        """ find paid or not  """
        for rec in self:
            if rec.collected_id.state == 'paid':
                rec.paid = True
            else:
                rec.paid = False


class BusinessCategory(models.Model):
    _name = 'business.category'
    _description = 'Business Category'
    name = fields.Char(string='Name')


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    property_rent_id = fields.Many2one('property.rent', string='Rent')


class AccountMove(models.Model):
    _inherit = 'account.move'

    security_deposit_rent_id = fields.Many2one('property.rent', string='Rent')

# ********************************************************************************************

# @api.depends('building')
# def _compute_journal(self):
#     # journal = self.env['ir.config_parameter'].sudo().get_param('property_lease_management.journal')
#     # if journal:
#     #     self.journal_id = self.env['account.journal'].browse(int(journal)).id
#     # else:
#     #     self.journal_id = False

# def post_entries(self):
# return {
#     'name': _("Pay Installments"),
#     'view_mode': 'form',
#     # 'view_id': SE,
#     'view_type': 'form',
#     'res_model': 'wizard.property.payment',
#     'type': 'ir.actions.act_window',
#     'nodestroy': False,
#     'target': 'new',
#     'domain': '[]',
#     'context': {'default_voucher_ids': voucher_ids.ids
#                 }
# }
