# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    portfolio_purchase_id = fields.Many2one('portfolio.purchase', string='Purchase')
    portfolio_sale_id = fields.Many2one('portfolio.sale', string='Sale')
    portfolio_dividend_id = fields.Many2one('portfolio.dividend', string='Dividend')

    def button_draft(self):
        result = super(AccountMove, self).button_draft()
        if self.portfolio_dividend_id and self.portfolio_dividend_id. state == 'done':
            raise ValidationError('Unable to cancel this Entry. Please cancel the corresponding Dividend entry first')
        elif self.portfolio_sale_id and self.portfolio_sale_id. state == 'done':
            raise ValidationError('Unable to cancel this Entry. Please cancel the corresponding Sale entry first')
        elif self.portfolio_purchase_id and self.portfolio_purchase_id. state == 'done':
            raise ValidationError('Unable to cancel this Entry. Please cancel the corresponding Purchase entry first')
        return result
