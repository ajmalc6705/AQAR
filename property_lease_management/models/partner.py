# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class Partner(models.Model):
    _inherit = 'res.partner'

    arabic_name = fields.Char(string="Name", translate=True)

    def return_tenant_complaint(self):
        """ This opens the xml view specified in xml_id for the current Insurance """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window']._for_xml_id('property_lease_management.' + xml_id)
            res['domain'] = [('tenant_id', '=', self.id)]
            res['context'] = {}
            return res
        return False

    def _get_mrf_amount(self):
        count = self.env['customer.complaints'].search_count([('tenant_id', '=', self.id)])
        if count:
            self.mrf_count = count
        else:
            self.mrf_count = 0

    partner_ident_no = fields.Char(string='Tenants Ref No.', default='/')
    rent_agreement = fields.One2many(comodel_name='property.rent', inverse_name='partner_id',
                                     string='Rent Agreements')
    is_government = fields.Boolean(string='Government Sector')
    company_reg_no = fields.Char(string='Company Registration No.')
    id_card_no = fields.Char(string='ID Card No.')
    id_passport = fields.Char(string='Passport No.')
    landlord = fields.Boolean(string='Landlord', default=False, help=_("Check this box if this contact is a landlord."))
    is_community_owner = fields.Boolean(string='Community Owner', default=False,
                                        help=_("Check this box if this contact is a Community Owner."))
    tenant = fields.Boolean(string='Tenant', default=False, help=_("Check this box if this contact is a tenant."))
    nationality = fields.Char(string='Nationality')
    attachment_ids = fields.Many2many(comodel_name='ir.attachment', relation='partner_attachments_rel',
                                      column1='partner_id', column2='attachment_id', string='Attachments')
    mrf_count = fields.Integer(compute='_get_mrf_amount')
    landlord_account_type = fields.Selection([('AG', 'AG - Agreement'),
                                              ('CR', 'CR - Commercial'),
                                              ('CV', 'CV - Person'),
                                              ('EM', 'EM - Embassy'),
                                              ('FC', 'FC - Foreign Company'),
                                              ('GV', 'GV - Government'),
                                              ('HT', 'HT - Heritage'),
                                              ('PR', 'PR - Profession')], 'Landlord Account Type')
    landlord_relation = fields.Selection([('investor', 'Investor'),
                                          ('beneficiary', 'Beneficiary')], 'Landlord Relation')
    landlord_account_number = fields.Char('Landlord Account Number')
    tenant_account_type = fields.Selection([('AG', 'AG - Agreement'),
                                            ('CR', 'CR - Commercial'),
                                            ('CV', 'CV - Person'),
                                            ('EM', 'EM - Embassy'),
                                            ('FC', 'FC - Foreign Company'),
                                            ('GV', 'GV - Government'),
                                            ('HT', 'HT - Heritage'),
                                            ('PR', 'PR - Profession')], 'Tenant Account Type')
    tenant_account_number = fields.Char('Tenant Account Number')
    po_box = fields.Char('PO Box')
    # doc_no = fields.Char(string='Document NO.')
    # doc_dec = fields.Text(string='Description')
    maintenance_count = fields.Integer('Maintenance', compute="compute_maintenance_count")

    def compute_maintenance_count(self):
        """ find maintenance count  """
        for rec in self:
            rec.maintenance_count = self.env['property.maintenance'].search_count([('property_id', '=', rec.id)])

    def return_property_maintenance(self):
        """ load the maintenance details """
        for rec in self:
            action = self.env.ref('property_lease_management.action_property_maintenance').read()[0]
            action['domain'] = [('tenant_id', '=', rec.id)]
            return action

    @api.onchange('tenant_account_type')
    def onchange_tenant_account_type(self):
        """ clear the tenant account number """
        for rec in self:
            rec.tenant_account_number = ""

    @api.onchange('landlord_account_type')
    def onchange_tenant_account_type(self):
        """ clear the landlord account number """
        for rec in self:
            rec.landlord_account_number = ""

    @api.model
    def create(self, vals):
        if vals.get('partner_ident_no', '/') == '/' and vals.get('tenant') == True:
            vals['partner_ident_no'] = self.env['ir.sequence'].next_by_code('res.partner') or '/'
        if 'parent_id' in vals:
            parent = self.env['res.partner'].browse(vals['parent_id'])
            if parent.tenant:
                vals['tenant'] = True
            if parent.landlord:
                vals['landlord'] = True
        return super(Partner, self).create(vals)

    # def button_update(self):
    #     records = self.env['res.partner'].search([])
    #     no = 000
    #     if records:
    #         for record in records:
    #             if record.tenant:
    #                 no += 1
    #                 record.partner_ident_no = '00' + str(no)
