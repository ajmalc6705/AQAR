from odoo import models, fields, api, _
from datetime import datetime


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_petty_cash_journal = fields.Boolean(string='Is Petty cash Journal')
