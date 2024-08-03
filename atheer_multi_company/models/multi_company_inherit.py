# *-* coding: UTF-8 *-*

from odoo import fields, models, api, _


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company.id)


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    company_id = fields.Many2one('res.company', 'Company', index=1, default=lambda self: self.env.company.id)


# class ResPartnerInherit(models.Model):
#     _inherit = 'res.partner'
#
#     company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company.id)
