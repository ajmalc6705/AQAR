
from odoo import models, fields,api, _
from odoo.exceptions import ValidationError



class ResCompany(models.Model):
    _inherit = 'res.company'

    internal_users = fields.Many2one('res.users', string='Internal Users')

