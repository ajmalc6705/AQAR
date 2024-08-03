from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('atheer_product_cw_access.product_creation_access'):
            raise UserError(_("You don't have access to create product."))
        result = super(ProductProduct, self).create(vals)
        return result

    @api.model
    def write(self, vals):
        if not self.env.user.has_group('atheer_product_cw_access.product_creation_access'):
            raise UserError(_("You don't have access to write product."))
        result = super(ProductProduct, self).write(vals)
        return result