from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    is_analytic_account_required = fields.Boolean(string='Keep Analytic Mandatory')
    allow_for_zakath = fields.Boolean(string='Allow for Zakath')
