# *-* Coding :UTF-8 *-*

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TenantRequestInheritCommunity(models.Model):
    _inherit = "tenant.request"

    property_community_id = fields.Many2one('property.community')
    is_community = fields.Boolean('Is Community', default=False,
                                  helpe="To Identify the community record in Tenant request")

    @api.onchange('property_community_id')
    def onchange_property_community_id(self):
        for rec in self:
            if rec.property_community_id:
                rec.building_id = rec.property_community_id.building_id.id
