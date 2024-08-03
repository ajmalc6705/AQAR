from odoo import api, fields, models, _


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    cheque_bearer_name = fields.Char('Bearer Name', tracking=True)
