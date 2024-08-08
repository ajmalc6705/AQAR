# -*- coding: utf-8 -*-

from odoo import fields, models, api, _, tools
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta
import datetime as DT
from odoo import SUPERUSER_ID
from odoo.osv import expression


class Property(models.Model):
    _name = 'property.property'
    _inherit = ['image.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = _('Property Details')

    @api.model
    def _default_company(self):
        return self.env.user.company_id.id

    def _has_image(self):
        image = False
        for rec in self:
            if rec.image_1920:
                image = dict((rec.id, bool(rec.image_1920)))
        return image

    @api.depends('parent_building')
    def onchange_bld(self):
        for rec in self:
            if rec.parent_building:
                rec.partner_id = rec.parent_building.partner_id

    @api.onchange('rent_monthly')
    def onchange_rent(self):
        self.rent_price = self.rent_monthly * 12

    @api.onchange('rent_sqm', 'area')
    def onchange_area(self):
        self.rent_monthly = self.rent_sqm * self.area
        self.rent_price = self.rent_monthly * 12

    @api.depends('bed_rooms')
    def flat_bhk(self):
        for rec in self:
            rec.bhk = str(rec.bed_rooms) + "BHK"

    @api.depends('state')
    def _check_color(self):
        """
        this method is used to chenge color index base on fee status
        :return: index of color for kanban view
        """
        for record in self:
            color = 0
            if record.state == 'open':
                color = 1
            elif record.state == 'rented':
                color = 2
            elif record.state == 'sold':
                color = 3
            # elif record.cleaning_state == 'closed':
            #     color = 4
            else:
                color = 5
            record.color = color

    active = fields.Boolean(default=True)
    id_temp = fields.Integer(string='ID Temp')
    name = fields.Char(string='Unit No.', required=True)
    parent_id = fields.Many2one(comodel_name='property.property', string='Parent Property')
    property_type_id = fields.Many2one(comodel_name='property.type', string='Property Type', required=True)
    property_group = fields.Char(string='Property Group')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Landlord')
    bhk = fields.Char(string='Type', compute='flat_bhk')
    bld_number = fields.Char(string='Building No.', related="parent_building.bld_no")
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    zip = fields.Char(string='Zip', size=24, change_default=True)
    city = fields.Char(string='City')
    state_id = fields.Many2one(comodel_name='res.country.state', string='State', ondelete='restrict')
    country_id = fields.Many2one(comodel_name='res.country', string='Country', ondelete='restrict')
    phone = fields.Char(string='Phone')
    fax = fields.Char(string='Fax')
    mobile = fields.Char(string='Mobile')
    electricity_no = fields.Char(string='Electricity Account No.')
    for_rent = fields.Boolean(string='For Rent', default=True)
    for_sale = fields.Boolean(string='For Sale')
    owned = fields.Boolean(string='Owned')
    for_parking = fields.Boolean(string='For Parking')
    contract_type = fields.Selection([('investment', _('Investment')), ('management', _('Management'))],
                                     string='Contract Type', default='investment')
    bed_rooms = fields.Integer(string='Bed Rooms')
    kitchen = fields.Integer(string='Kitchen')
    hall = fields.Integer(string='Hall')
    bathroom = fields.Integer(string='Bathroom')
    balcony = fields.Integer(string='Balcony')
    parking = fields.Integer(string='Parking')
    doors = fields.Integer(string='Doors')
    ac_type = fields.Char(string='A/C Type')
    area = fields.Float(string='Area(sqm)', digits='Product Price')
    sea_view = fields.Boolean(string='Sea View')
    gym = fields.Boolean(string='Gym')
    maid = fields.Boolean(string='Maids Room')
    health_club = fields.Boolean(string='Health Club')
    rent_sqm = fields.Float(string='Rent (sqm)', digits='Product Price')
    rent_monthly = fields.Float(string='Rent Price (Monthly)', digits='Product Price')
    rent_price = fields.Float(string='Rent Price (Annual)', digits='Product Price')
    sale_price = fields.Float(string='Sale Price', digits='Product Price')
    room_ids = fields.One2many(comodel_name='property.room', inverse_name='property_id', string='Room Lines')
    cost_center_id = fields.Many2one(comodel_name='account.analytic.account', string='Cost Center',
                                     related='parent_building.bu_cc', store=True)
    attachment_ids = fields.Many2many(comodel_name='ir.attachment', relation='property_attachments_rel',
                                      column1='property_id', column2='attachment_id',
                                      string='Attachments')
    has_image = fields.Boolean(default=_has_image)
    rent_id = fields.Many2one('property.rent', string='Rent Agreement')
    tenant_id = fields.Many2one('res.partner', string='Tenant', related='rent_id.partner_id')
    doc_ids = fields.Many2many('atheer.documents',
                               string='Documents')
    electricity_meter_no = fields.Char(string='Electricity Meter No.')
    # 'electricity_account_no': fields.float(_('Electricity Account No.')),
    water_meter_no = fields.Char(string='Water Meter No.')
    water_account_no = fields.Char(string='Water Account No.')

    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=_default_company)
    state = fields.Selection([('open', _('Available')),
                              ('rented', _('Rented')),
                              ('reserve', _('Reserve')),
                              ('take_over', _('Available/Takeover')),
                              ('sold', _('Sold')),
                              ('close', _('Closed')), ], string='Status', default='open', readonly=True, copy=False,
                             help=_("Gives the status of the property"))
    # alsabla extra fields
    accessrz_ids = fields.One2many(comodel_name='assets.accessrz', inverse_name='property_id',
                                   string='Assets and Accessories')
    parent_building = fields.Many2one(comodel_name='property.building', string='Building', required=True)
    color = fields.Integer(string='Color Index', compute="_check_color", store=True)
    in_active_bol = fields.Boolean("Inactive")
    complaint_count = fields.Integer('Complaints', compute="compute_complaint_count")
    maintenance_count = fields.Integer('Maintenance', compute="compute_maintenance_count")

    mulkiya_no = fields.Char(string='Mulkiya No')
    muncipality_no = fields.Char(string='Muncipality No')
    open_from = fields.Date(string='Open From')
    # floor_no = fields.Char(string='Floor No')  # They need a master to select the floor
    floor_id = fields.Many2one('unit.floor', string='Floor No')
    rentable_area = fields.Float(string='Rentable Area(sqm)', digits='Product Price')
    indoor_area = fields.Float(string='Indoor Area(sqm)', digits='Product Price')
    outdoor_area = fields.Float(string='Outdoor Area(sqm)', digits='Product Price')
    mulkiya_area = fields.Float(string='Mulkiya Area(sqm)', digits='Product Price')
    park_buy = fields.Boolean(string='Parkings Can Buy')
    owner_name = fields.Many2one('res.partner', string='Owner Name', domain=[('landlord', '=', True)])
    owner_agreement = fields.Char(string='Owner Agreement')
    ownership_type = fields.Selection([('own', 'Own'), ('third_party', 'Third Party')], string='Ownership Type')
    unit_views_id = fields.Many2many('property.unit.view', string='Unit View')
    furnished_type_id = fields.Many2one('furnished.type', string='Furnished Type')
    electricity_account_ids = fields.One2many('electricity.account.line', 'property_id', string='Electricity Accounts')
    water_account_ids = fields.One2many('water.account.line', 'property_id', string='Water Accounts')
    rent_ids = fields.One2many('property.rent', 'property_id', string='Unit History', compute='_compute_rent_ids')
    history_count = fields.Integer(string='History Count', compute='_compute_rent_count')
    room_details_count = fields.One2many('room.details', 'property_id', string='Room Equipments Count')
    unit_seq = fields.Char(string='Unit No', help='sequence of the unit', copy=False, index=True, )

    def name_get(self):
        res = []
        for each in self:
            name = each.name
            if each.unit_seq:
                res.append((each.id, str(name) + ' [' + each.unit_seq + ']'))
            else:
                res.append((each.id, name))
        return res

    def send_unit_mail(self):
        """ bulk mail based on units to Tenants"""
        for rec in self:
            lang = self.env.context.get('lang')
            mail_template = self.env.ref('property_lease_management.unit_email_template', raise_if_not_found=False)
            if mail_template and mail_template.lang:
                lang = mail_template._render_lang(self.ids)[self.id]
            ctx = {
                'default_model': 'property.property',
                'default_res_id': rec.id,
                'default_use_template': bool(mail_template),
                'default_template_id': mail_template.id if mail_template else None,
                'default_composition_mode': 'comment',
                'mark_so_as_sent': True,
                'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
                'proforma': self.env.context.get('proforma', False),
                'force_email': True,
            }
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(False, 'form')],
                'view_id': False,
                'target': 'new',
                'context': ctx,
            }

    def action_unit_history(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rent',
            'view_mode': 'tree,form',
            'res_model': 'property.rent',
            'domain': [('property_id', '=', self.id)],
        }

    @api.depends('rent_id')
    def _compute_rent_count(self):
        self.history_count = False
        for rec in self:
            property_rent = self.env['property.rent'].search_count([('property_id', '=', self.id)])
            rec.history_count = property_rent

    @api.depends('rent_id')
    def _compute_rent_ids(self):
        self.rent_ids = False
        for rec in self:
            property_rent = self.env['property.rent'].search([('property_id', '=', self.id)])
            rec.rent_ids = property_rent.mapped('id')

    def compute_maintenance_count(self):
        """ find maintenance count  """
        for rec in self:
            rec.maintenance_count = self.env['property.maintenance'].search_count([('property_id', '=', rec.id)])

    def return_property_maintenance(self):
        """ load the maintenance details """
        for rec in self:
            action = self.env.ref('property_lease_management.action_property_maintenance').read()[0]
            action['domain'] = [('property_id', '=', rec.id)]
            return action

    def compute_complaint_count(self):
        """ find complaints count  """
        for rec in self:
            rec.complaint_count = self.env['customer.complaints'].search_count([('property', '=', rec.id)])

    def return_property_complaints(self):
        """ load the complaint details """
        for rec in self:
            action = self.env.ref('property_lease_management.action_customer_issue_form').read()[0]
            action['domain'] = [('property', '=', rec.id)]
            return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('parent_id', False):
                vals['state'] = self.env['property.property'].browse(vals['parent_id']).state
            vals['unit_seq'] = self.env['ir.sequence'].next_by_code('unit.sequence')
        return super(Property, self).create(vals_list)

    # @api.model
    # def create(self, vals):
    #     # rent_rec = self.env['property.rent'].search([('id', '=', vals['agreement_no'])])
    #     # if vals['complain_initiated_by'] == 'tenant':
    #     #     vals.update({'tenant_id': rent_rec.partner_id.id})
    #     return super(Property, self).create(vals)

    def write(self, vals):
        if vals.get('parent_id', False):
            vals['state'] = self.env['property.property'].browse(vals['parent_id']).state
        return super(Property, self).write(vals)

    def onchange_property_type(self, type_id):
        res = {}
        if type_id:
            ptype = self.env['property.type'].browse(type_id)
            res = {'value': {'property_group': ptype.property_group}}
        return res

    @api.onchange('property_type_id')
    def onchange_property_type_id(self):
        if self.property_type_id:
            self.property_group = self.property_type_id.property_group

    def onchange_state(self, state_id):
        if state_id:
            state = self.env['res.country.state'].browse(state_id)
            return {'value': {'country_id': state.country_id.id}}
        return {}

    def onchange_parent_id(self, parent_id):
        res = {}
        if parent_id:
            p = self.browse(parent_id)
            res.update({
                'street': p.street,
                'street2': p.street2,
                'zip': p.zip,
                'city': p.city,
                'state_id': p.state_id.id,
                'country_id': p.country_id.id,
                'partner_id': p.partner_id.id,
                'cost_center_id': p.cost_center_id.id,
                'property_type_id': p.property_type_id.id,
            })
        return {'value': res}

    def button_print_opportunity(self):
        # view_ref = self.env['ir.model.data'].get_object_reference('property_lease_management',
        #                                                           'view_property_opportunity_report_wiz')
        # view_ref = self.env['ir.model.data']._xmlid_to_res_id('property_lease_management.view_property_opportunity_report_wiz')
        view_ref = self.env.ref('property_lease_management.view_property_opportunity_report_wiz')
        # print(view_ref)
        # view_id = view_ref and view_ref[1] or False,
        view_id = view_ref and view_ref.id or False,
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cost Of Opportunity'),
            'res_model': 'property.opportunity.report.wiz',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id,
            # 'view_id': view_id,
            'nodestroy': True,
        }


# asset and asseccories tab

class PropertyType(models.Model):
    _name = 'property.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = _('Property Type')

    PROPERTY_GROUPS = [
        ('residence', _('Residential')),
        ('shop', _('Commercial')),
        ('camp', _('Accommodation')),
        ('land', _('Plot'))
    ]

    id_temp = fields.Integer(string='ID Temp')
    name = fields.Char(string='Name', required=True)
    property_group = fields.Selection(PROPERTY_GROUPS, string='Property Group', required=True)
    is_for_parking = fields.Boolean(string='Is For Parking', default=False, tracking=True)

    def unlink(self):
        res = self.env['property.property'].search([('property_type_id', 'in', self.ids)])
        if res:
            raise UserError(_("You can't delete this type.it is referred in some property"))


class Room(models.Model):
    _name = 'property.room'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = _('Room Details')

    id_temp = fields.Integer(string='ID Temp')
    name = fields.Char(string='Name', required=True)
    type_id = fields.Many2one(comodel_name='property.room.type', string='Room Type', required=True)
    room_length = fields.Float(string='Length (m)', digits='Product Price')
    room_width = fields.Float(string='Width (m)', digits='Product Price')
    room_height = fields.Float(string='Height (m)', digits='Product Price')
    property_id = fields.Many2one(comodel_name='property.property', string='Unit',
                                  required=True, ondelete='cascade')
    asset_type_ids = fields.Many2many('assets.accessrz.type', 'asset_room_rel', 'room_id', 'asset_type_id',
                                      string='Assets')


class RoomType(models.Model):
    _name = 'property.room.type'
    _description = _('Room Type')

    id_temp = fields.Integer(string='ID Temp')
    name = fields.Char(string='Name', required=True)


class CreateMaintenanceRequest(models.TransientModel):
    _name = 'create.maintenance.request'
    _description = _('Create maintenance request')

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

    def create_maintenance_request(self):
        """ creating maintenance request from assets """
        if not self.to_date or not self.from_date:
            raise UserError("Please fill the Maintenance Due Date")
        for rec in self.assets_ids:
            maintenance = self.env['property.maintenance'].sudo().search([('asset_id', '=', rec.id),
                                                                          ('done_date', '=', self.to_date)])
            if not maintenance:
                maintenance_vals = {'property_id': rec.property_id.id,
                                    'asset_id': rec.id,
                                    'building': rec.building_id.id,
                                    'done_date': self.to_date,
                                    'due_date': self.from_date,
                                    'maintenance_type': 'routine',
                                    }
                self.env['property.maintenance'].sudo().create(maintenance_vals)
            # else:
            #     raise UserError("A maintenance request is already available for this asset on the same due date")


# Assets and accessories
class Assets(models.Model):
    _name = 'assets.accessrz'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = _('Asset &amp;amp; Accessories')

    id_temp = fields.Integer(string='ID Temp')
    name = fields.Char(string='Name', readonly=True)
    desc = fields.Text(string='Description')
    asset_categ = fields.Many2one(comodel_name='assets.accessrz.type', string=_('Asset Type'))
    room_id = fields.Many2one('property.room', 'Room')
    warrnty_date = fields.Date(string='Warranty Date')
    property_id = fields.Many2one(comodel_name='property.property', string='Unit')
    doc_ids = fields.Many2many('atheer.documents',
                               string='Documents')
    warrnty_date_from = fields.Date(string='From Date')
    warrnty_date_to = fields.Date(string='To Date')
    expiry_date = fields.Date(string='Maintenance Due Date')
    maintenance_count = fields.Integer('Maintenance Request', compute="compute_maintenance_count")
    building_id = fields.Many2one('property.building', 'Building', store=True, related="property_id.parent_building")
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    invoice_date = fields.Date(string='Invoice Date')
    brand = fields.Char(string='Brand')
    invoice_ref_no = fields.Char(string='Invoice Ref No')
    model = fields.Char(string='Model')
    helpdesk_no = fields.Char(string='Helpdesk No ')

    @api.onchange('property_id', 'asset_categ')
    def find_description(self):
        """ finding the value of description"""
        for rec in self:
            if rec.property_id and rec.asset_categ:
                rec.desc = rec.property_id.name + " / " + rec.asset_categ.name

    def maintenance_req_mail_body(self):
        body = """ 
                            <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
                            <tr><td align="center"><table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;"> 
                            <tr>
                                                <td align="center" style="min-width: 590px;">
                                                    <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                                                        <tr><td valign="middle">
                                                            <span style="font-size: 10px;">Hello</span><br/>
                                                            <span style="font-size: 20px; font-weight: bold;">

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
                                                                <p style="font-weight:bold;">Dear ,</p>
                                                                <p> </p><br/><br/><br/>
                                                                <p> </p>
                                                                <p> </p>

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
                    """.format(tenant_id=self.env.user.partner_id, )
        return body

    def create_maintenance_request(self):
        body = """ 
                    <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;">
                    <tr><td align="center"><table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;"> 
                    <tr>
                                        <td align="center" style="min-width: 590px;">
                                            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                                                <tr><td valign="middle">
                                                    <span style="font-size: 10px;">Hello</span><br/>
                                                    <span style="font-size: 20px; font-weight: bold;">
                                                        
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
                                                        <p style="font-weight:bold;">Dear ,</p>
                                                        <p> </p><br/><br/><br/>
                                                        <p> </p>
                                                        <p> </p>
                                                        
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
            """.format(tenant_id=self.env.user.partner_id, )
        self.maintenance_req_mail_body()
        email_to = []
        for assets_id in self.ids:
            asset = self.env['assets.accessrz'].search([('id', '=', assets_id)])
            if asset.property_id.rent_id.partner_id:
                email_to.append(asset.property_id.rent_id.partner_id.id)
        return {
            'name': _("Create Maintenance Request"),
            'view_mode': 'form',
            'view_id': self.env.ref('property_lease_management.create_maintenance_request_view_form').id,
            'view_type': 'form',
            'tag': 'reload',
            'res_model': 'create.maintenance.request',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'stay_open': True,
            'domain': '[]',
            'context': {
                'default_subject': str('Maintenance Request'),
                'default_assets_ids': self.ids,
                'default_recipient_ids': [(6, 0, email_to)] if email_to else None,
                'default_message': body
            }
        }

    def compute_maintenance_count(self):
        """ find maintenance request count """
        for rec in self:
            maintenance = self.env['property.maintenance'].sudo().search_count([('asset_id', '=', rec.id)])
            rec.maintenance_count = maintenance

    def return_asset_maintenance(self):
        """ load the maintenance requests of the asset """
        action = self.env["ir.actions.act_window"]._for_xml_id('property_lease_management.action_property_maintenance')
        # form_view = self.env.ref('material_requisition.view_mr_form')
        # action['views'] = [(form_view.id, 'form')]
        maintenance = self.env['property.maintenance'].sudo().search([('asset_id', '=', self.id)])
        if maintenance:
            action['domain'] = [('id', 'in', maintenance.ids)]
            return action

    def create_periodic_maintenance(self):
        """ creating maintenance request from assets """
        for rec in self:
            if not rec.expiry_date:
                raise UserError("Please fill the Maintenance Due Date")
            maintenance = self.env['property.maintenance'].sudo().search([('asset_id', '=', rec.id),
                                                                          ('done_date', '=', rec.expiry_date)])
            if not maintenance:
                maintenance_vals = {'property_id': rec.property_id.id,
                                    'asset_id': rec.id,
                                    'building': rec.property_id.parent_building.id,
                                    'done_date': rec.expiry_date,
                                    'due_date': rec.expiry_date,
                                    'maintenance_type': 'routine',
                                    }
                self.env['property.maintenance'].sudo().create(maintenance_vals)
            else:
                raise UserError("A maintenance request is already available for this asset on the same due date")

    @api.onchange('property_id')
    def onchange_property_id_room_id(self):
        """ to set the domain for room as per the selected property"""
        for rec in self:
            room_ids = self.env['property.room'].search([('property_id', '=', rec.property_id.id)])
            return {'domain': {'room_id': [('id', 'in', room_ids.ids)]}}

    # notify expiring policy:cron job calling
    def notify_asset_expiry(self):
        """ notification for asset """
        print("print notification")
        # days_before_maintenance = self.env['notification.duration'].search([('maintenance_notification', '=', True)])
        # days_before_expiry = self.env['notification.duration'].search([('warranty_notification', '=', True)])
        # date_today = date.today()
        # # asset maintenance due date notification
        # maintenance_list = []
        # for maintenance_date in days_before_maintenance:
        #     if maintenance_date.period == 'days':
        #         maintenance_before_date = date_today + relativedelta(days=maintenance_date.duration)
        #     if maintenance_date.period == 'months':
        #         maintenance_before_date = date_today + relativedelta(months=maintenance_date.duration)
        #     asset_maintenance = self.env['assets.accessrz'].search([('expiry_date', '=', maintenance_before_date)])
        #     for maintenance in asset_maintenance:
        #         maintenance_list.append(maintenance.id)
        # message = "Maintenance due date of few assets are going to expire"
        # if len(maintenance_list):
        #     self.env['atheer.notification']._send_instant_notify(title="Asset Maintenance Due Date Notification",
        #                                                          message=message,
        #                                                          action=self.env.ref(
        #                                                              'amlak_property_management.action_acces_asset').id,
        #                                                          domain=[['id', 'in', maintenance_list]],
        #                                                          user_type="groups",
        #                                                          recipient_ids=[self.env.ref('base.group_system').id])
        # # asset warrenty expiry date notification
        # warranty_list = []
        # for warranty_date in days_before_expiry:
        #     if warranty_date.period == 'days':
        #         expiry_before_date = date_today + relativedelta(days=warranty_date.duration)
        #     if warranty_date.period == 'months':
        #         expiry_before_date = date_today + relativedelta(months=warranty_date.duration)
        #     asset_warranty = self.env['assets.accessrz'].search([('warrnty_date_to', '=', expiry_before_date)])
        #     for warranty in asset_warranty:
        #         warranty_list.append(warranty.id)
        # message = "Warranty of few Assets are going to expire"
        # if len(warranty_list):
        #     self.env['atheer.notification']._send_instant_notify(title="Asset Warranty Due Date Notification",
        #                                                          message=message,
        #                                                          action=self.env.ref(
        #                                                              'amlak_property_management.action_acces_asset').id,
        #                                                          domain=[['id', 'in', warranty_list]],
        #                                                          user_type="groups",
        #                                                          recipient_ids=[self.env.ref('base.group_system').id])

    # @api.model
    # @api.onchange('asset')
    # def onchange_asset(self):
    #     self.asset_categ = self.asset.type

    @api.model_create_multi
    def create(self, vals_list):
        asset_type_rec = self.env['assets.accessrz.type']
        for vals in vals_list:
            code = asset_type_rec.browse(vals['asset_categ']).code
            vals['name'] = 'ASSET/' + str(code) + '/' + str(self.env['ir.sequence'].next_by_code('assets.accessrz'))
        new_ids = super(Assets, self).create(vals_list)
        return new_ids

    def name_get(self):
        res = []
        for each in self:
            name = each.name
            if each.desc:
                res.append((each.id, name + '[' + str(each.desc) + ']'))
            else:
                res.append((each.id, each.name))
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = list(args or [])
        if not (name == '' and operator == 'ilike'):
            args += ['|', (self._rec_name, operator, name), ('desc', operator, name)]
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    # @api.model
    # def name_search(self, name='', args=None, operator='ilike', limit=100):
    #     ids = self._name_search(name, args, operator, limit=limit)
    #     print("ieeeeeeds",ids)
    #     print("7868",self.browse(ids).sudo().name_get())
    #     return self.browse(ids).sudo().name_get()


# Asset type
class AssetsType(models.Model):
    _name = 'assets.accessrz.type'
    _description = _('Asset &amp; Accessories Type')

    id_temp = fields.Integer(string='ID Temp')
    name = fields.Char(string='Name', required=True)
    parent_id = fields.Many2one(comodel_name='assets.accessrz.type', string='Parent Asset')
    code = fields.Char(string='Code')

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].next_by_code('assets.accessrz.type')
        res = super(AssetsType, self).create(vals)
        if res.parent_id.name:
            name = str(res.parent_id.name) + '/' + str(res.name)
        else:
            name = res.name
        res.update({'name': name})
        return res


# building model
class Building(models.Model):
    _name = 'property.building'
    _description = _('Buildings')
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def onchange_state(self, state_id):
        if state_id:
            state = self.env['res.country.state'].browse(state_id)
            return {'value': {'country_id': state.country_id.id}}
        return {}

    id_temp = fields.Integer(string='ID Temp')
    name = fields.Char(string='Name', required=True)
    parent_building = fields.Many2one(comodel_name='property.building', string='Parent Building')
    ref = fields.Char(readonly=True, string='Ref')
    building_seq = fields.Char(string='Building No', help='sequence of the building', copy=False,
                               readonly=True,
                               index=True, )
    doc_ids = fields.Many2many('atheer.documents',
                               string='Documents')
    property_ids = fields.One2many(comodel_name='property.property', inverse_name='parent_building',
                                   string='Property', domain=[('for_parking', '=', False)])
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    zip = fields.Char(string='Zip', size=24, change_default=True)
    city = fields.Char(string='City')
    state_id = fields.Many2one(comodel_name='res.country.state', string='State', ondelete='restrict')
    country_id = fields.Many2one(comodel_name='res.country', string='Country', ondelete='restrict')
    plot_no = fields.Char(string='Plot No.')
    way_no = fields.Char(string='Way No.')
    bld_no = fields.Char(string='Building No.')
    partner_id = fields.Many2many(comodel_name='res.partner', string='Landlord')
    bu_cc = fields.Many2one(comodel_name='account.analytic.account', string='Cost Center')
    type = fields.Selection([('own', 'Own Building'), ('out', '3rd Party')],
                            string='Type', required=True, default='own')
    purpose_of_contract = fields.Selection([('commercial', 'Commercial'),
                                            ('industrial', 'Industrial'),
                                            ('investment', 'Investment (For Re-Rent Purpose)'),
                                            ('residential', 'Residential')], 'Purpose of Contract')
    residential_usage_type = fields.Selection([('manpower_family', 'Manpower Family'),
                                               ('manpower_single', 'Manpower Single'),
                                               ('family', 'Family'),
                                               ('single', 'Single'),
                                               ('student_male', 'Student (Male)'),
                                               ('student_female', 'Student (Female)')], 'Residential Usage Type')
    land_usage_purpose = fields.Selection(related="plot_id.land_usage_purpose", string='Purpose of Land Usage', )
    krookie_number = fields.Char('Krookie Number', related="plot_id.krooki_number")
    block_number = fields.Char('Block Number')
    block_number_mulkia = fields.Char('Block Number (as Mulkia certificate)')
    rent_full_building = fields.Boolean('Rent Full Building')
    sub_contract = fields.Boolean('Sub Contract')
    electricity_account = fields.Char('Building Electricity Account')
    water_account = fields.Char('Building Water Account')
    building_area = fields.Many2one('building.area', 'Area')
    active = fields.Boolean(string='Active', default=True)
    complaint_count = fields.Integer('Complaints', compute="compute_complaint_count")
    maintenance_count = fields.Integer('Maintenance', compute="compute_maintenance_count")
    specifications = fields.Html(string='Specifications')

    plot_id = fields.Many2one('property.plot', string='Plot No')
    commencement_date = fields.Date(string='Commencement Date')
    completion_date = fields.Date(string='Completion Date')
    builtup_area = fields.Integer(string='Builtup Area(SQM)', help='sqm')
    reservation_docs = fields.Html(string='Reservation Docs')
    bank_account_line_ids = fields.One2many('bank.account.line', 'building_id', string='Bank Account Line')
    building_amenties_ids = fields.One2many('building.amenities', 'building_id', string='Building Amenities')

    def name_get(self):
        res = []
        for each in self:
            name = each.name
            if each.building_seq:
                res.append((each.id, str(name) + ' [' + each.building_seq + ']'))
            else:
                res.append((each.id, name))
        return res

    def compute_maintenance_count(self):
        """ find maintenance count  """
        for rec in self:
            rec.maintenance_count = self.env['property.maintenance'].search_count([('building', '=', rec.id)])

    def return_building_maintenance(self):
        """ load the maintenance details """
        for rec in self:
            action = self.env.ref('property_lease_management.action_property_maintenance').read()[0]
            action['domain'] = [('building', '=', rec.id)]
            return action

    def compute_complaint_count(self):
        """ find complaints count  """
        for rec in self:
            rec.complaint_count = self.env['customer.complaints'].search_count([('building', '=', rec.id)])

    def return_building_complaints(self):
        """ load the complaint details """
        for rec in self:
            action = self.env.ref('property_lease_management.action_customer_issue_form').read()[0]
            action['domain'] = [('building', '=', rec.id)]
            return action

    # 'commission': fields.one2many('property.building.commission', 'building_id', _('Commission')),

    # def name_get(self):
    #     res = []
    #     for each in self:
    #         res.append((each.id, each.ref))
    #     return res

    @api.onchange('purpose_of_contract')
    def onchange_purpose_of_contract(self):
        for rec in self:
            rec.residential_usage_type = None

    @api.model
    def create(self, vals):
        if vals.get('parent_building'):
            ref = str(self.browse(vals['parent_building']).name) + '/' + str(vals['name'])
        else:
            ref = vals['name']
        vals['ref'] = ref
        vals['building_seq'] = self.env['ir.sequence'].next_by_code(
            'building.sequence')
        return super(Building, self).create(vals)

    def write(self, vals):
        if 'name' in vals:
            ref = vals['name']
            vals['ref'] = ref
        return super(Building, self).write(vals)


# Commission
# class PropertyBuildingCommission(osv.Model):
#     _name = "property.building.commission"
#
#     # @api.one
#     # @api.onchange('date_from', 'date_to')
#     def onchange_date(self, cr, uid, ):
#         print self, self.date_from
#         if self.date_from and self.date_to:
#             res = self.env['property.building.commission'].search([('building_id', '=', self._context['building_id']), ('date_from', '<=', self.date_from), ('date_to', '>=', self.date_to)])
#             if len(res) > 0:
#                 warning = {'title': _('Warning !'), 'message': _('Period overlapping.')}
#                 return {'value': {'date_from': False, 'date_to': False, 'commission_percentage':10.0}, 'warning': warning}
#             if self.date_from >= self.date_to:
#                 print 'yeaaa'
#                 warning = {'title': _('Warning !'), 'message': _('Date From must be less than Date To')}
#                 return {'value': {}, 'warning': warning}
#
#     _columns = {
#         'date_from': fields.date('From'),
#         'date_to': fields.date('To'),
#         'commission_percentage': fields.float('Commission Percentage'),
#         'building_id': fields.many2one('Building ID'),
#     }
#
#     _sql_constraints = [('percentage_check', 'CHECK(commission_percentage <= 100)', 'Commission percentage must be less than or equal to 100.')]


class BuildingArea(models.Model):
    _name = 'building.area'
    _description = 'Areas of Building'

    name = fields.Char('Name', required=True)


class ElectricityAccountLine(models.Model):
    _name = 'electricity.account.line'
    _description = 'Electricity Account Line'
    _rec_name = 'account_no'

    property_id = fields.Many2one('property.property', string='Property')
    name = fields.Char(string='Description')
    account_no = fields.Char(string='Account No')
    meter_no = fields.Char(string='Meter No')
    meter_reading = fields.Float(string='Meter Reading', digits="Product Price")
    takeover_checklist_id = fields.Many2one('property.checklist.takeover', string='Takeover')
    handover_checklist_id = fields.Many2one('property.checklist', string='Handover')


class WaterAccountLine(models.Model):
    _name = 'water.account.line'
    _description = 'Water Account Line'
    _rec_name = 'account_no'

    property_id = fields.Many2one('property.property', string='Property')
    name = fields.Char(string='Description')
    account_no = fields.Char(string='Account No')
    meter_no = fields.Char(string='Meter No')
    meter_reading = fields.Float(string='Meter Reading', digits="Product Price")
    takeover_checklist_id = fields.Many2one('property.checklist.takeover', string='Takeover')
    handover_checklist_id = fields.Many2one('property.checklist', string='Handover')


class BankAccountLine(models.Model):
    _name = 'bank.account.line'
    _description = 'Bank Account Line'

    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')
    acc_number = fields.Char(string='Account Number', related="bank_account_id.acc_number")
    swift_code = fields.Char(string='Swift Code', related="bank_account_id.bank_id.bic")
    branch_name = fields.Char(string='Branch Name', related="bank_account_id.branch_name")
    building_id = fields.Many2one('property.building', string='Building')
    type = fields.Selection([('sale', 'Sale'), ('lease', 'Lease'), ('service', 'Service'), ('community', 'Community')],
                            string='Type')


class RoomDetails(models.Model):
    _name = 'room.details'
    _description = 'Room Details'

    property_id = fields.Many2one('property.property', string='Unit')
    room_type_id = fields.Many2one('property.room.type', string='Room Type')
    type_count = fields.Integer(string='Type Count', compute='_compute_type_count')

    @api.depends('room_type_id')
    def _compute_type_count(self):
        self.type_count = False
        for rec in self:
            room_property = self.env['property.room'].search_count(
                [('property_id', '=', rec.property_id.id), ('type_id', '=', rec.room_type_id.id)])
            rec.type_count = room_property


class UnitFLoor(models.Model):
    _name = 'unit.floor'
    _description = 'Floors'

    name = fields.Char('Floor No')


class ResPartnerBankBranch(models.Model):
    _inherit = 'res.partner.bank'

    branch_name = fields.Char(string='Branch Name', )
