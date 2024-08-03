from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    partner_mobile_unique = fields.Boolean(string="partner moblie unique")
    partner_email_unique = fields.Boolean(string="partner email unique")
    partner_additional_email_unique = fields.Boolean(string="partner Additional email unique")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    contact_unique = fields.Boolean("Contact Unique", default=True)
    partner_mobile_unique = fields.Boolean("Enable Unique Mobile Number", related='company_id.partner_mobile_unique', readonly=False, default=True)
    partner_email_unique = fields.Boolean(string="Enable Unique Email", readonly=False, related="company_id.partner_email_unique")
    partner_additional_email_unique = fields.Boolean(string="Enable Unique Email 2", readonly=False, related="company_id.partner_additional_email_unique")
