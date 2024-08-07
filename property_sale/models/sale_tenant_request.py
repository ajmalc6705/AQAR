# *-* Coding :UTF-8 *-*

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TenantRequestInheritCommunity(models.Model):
    _inherit = "tenant.request"

    property_sale_id = fields.Many2one('property.sale')
    is_property_sale = fields.Boolean('Is Community', default=False,
                                  helpe="To Identify the community record in Tenant request")

    @api.onchange('property_sale_id')
    def onchange_property_community_id(self):
        for rec in self:
            if rec.property_sale_id:
                rec.building_id = rec.property_sale_id.building_id.id
