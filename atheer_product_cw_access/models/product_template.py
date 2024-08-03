from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def create(self, vals):
        if self.env.user.has_group('atheer_product_cw_access.product_creation_restriction'):
            raise UserError(_("You don't have access to create product."))
        result = super(ProductTemplate, self).create(vals)
        return result

    def write(self, vals):
        if self.env.user.has_group('atheer_product_cw_access.product_creation_restriction'):
            raise UserError(_("You don't have access to write product."))
        result = super(ProductTemplate, self).write(vals)
        return result