# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError


class PettyCashExpenseType(models.Model):
    _name = 'petty.cash.expense.type'
    _description = "Petty Cash Expense Type"

    name = fields.Char('Name')
    user_ids = fields.Many2many('res.users', 'rel_user_expense_type', 'user_id', 'expense_type_id')

    @api.constrains('name')
    def _check_duplicate_name(self):
        for rec in self:
            if rec.name:
                similar_name_records = self.search([('name', '=', rec.name), ('id', '!=', rec.id)], limit=1)
                if similar_name_records:
                    raise UserError(
                        _("The Expense Type name %s is already exist ,Please choose another one", rec.name, ))
