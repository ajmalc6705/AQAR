# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'


    def action_apply_inventory(self):
        if not self.env.user.has_group('aqar_inventory_adjustment.group_allow_inventory_adjust'):
            raise UserError(_("Permission Needed to do this operation"))

        result = super(StockQuantInherit, self).action_apply_inventory()
        return result

