from odoo import _, api, fields, models

from odoo.exceptions import ValidationError


class ProductPrd(models.Model):
    _inherit = 'product.product'

    @api.constrains('default_code')
    def _check_internal_ref(self):
        if self.default_code:
            product_ids = self.env['product.product'].search([
                ('default_code', '=', self.default_code), ('id', '!=', self.id)
            ])
            if product_ids:
                raise ValidationError(_("The internal reference '%s' already exists", self.default_code))


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _check_company_auto = True

    @api.model
    def create(self, vals):
        if not vals.get('default_code'):
            if vals.get('categ_id'):
                category = self.env['product.category'].browse(vals.get('categ_id'))
                if not category:
                    raise ValidationError(_("Please Select Product Category"))
                if category.ir_sequence_id:
                    vals['default_code'] = category.ir_sequence_id.next_by_id()
                else:
                    raise ValidationError(_("Please Configure Sequence under the Product Category"))
        program = super(ProductTemplate, self).create(vals)
        return program

    @api.constrains('default_code')
    def _check_internal_ref(self):
        if self.default_code:
            product_ids = self.env['product.template'].search([
                ('default_code', '=', self.default_code), ('id', '!=', self.id)
            ])
            if product_ids:
                raise ValidationError(_("The internal reference '%s' already exists", self.default_code))


class ProductCategoryIrSequence(models.Model):
    _inherit = 'product.category'

    ir_sequence_id = fields.Many2one('ir.sequence')
