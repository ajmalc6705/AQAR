# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockMoveInherit(models.Model):
    _inherit = 'stock.move'

    return_reason = fields.Text('Return Reason')

class StockMoveLineInherit(models.Model):
    _inherit = 'stock.move.line'


    qty_available = fields.Integer(string='Qty Available', compute='compute_qty_available')


    def compute_qty_available(self):
        for rec in self:
            rec.qty_available = rec.product_id.with_context({'location': rec.location_id.id}).qty_available

class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'


    return_reason = fields.Text('Return Reason',placeholder="Return Reason")

    def _create_returns(self):
        result = super(ReturnPicking, self)._create_returns()

        if result:
            new_picking_id, picking_type_id = result
            new_picking = self.env['stock.picking'].browse(new_picking_id)

            if self.return_reason:
                new_picking.write({
                    'return_reason': self.return_reason
                })
                msg = "<strong>Return Reason: </strong>" + self.return_reason
                new_picking.message_post(body=msg)
            else:
                raise UserError(_("Please Enter the reason "))

        return result


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'


    return_reason = fields.Text('Return Reason')


class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'


    def action_apply_inventory(self):
        if not self.env.user.has_group('aqar_inventory_adjustment.group_allow_inventory_adjust'):
            raise UserError(_("Permission Needed to do this operation"))

        result = super(StockQuantInherit, self).action_apply_inventory()
        return result

