# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderInheritReason(models.Model):
    _inherit = 'sale.order'

    outside_salesperson = fields.Many2one('res.partner', 'Outside Salesperson')
    ceo_note = fields.Text('Ceo Remarks')
    ceo_remark = fields.Boolean('Ceo Remarks', default=False, compute='_compute_remarks')
    salesman_note = fields.Text('Salesman Remarks')
    salesman_remark = fields.Boolean('Salesman Remarks', default=False, compute='_compute_remarks')
    manager_note = fields.Text('Manager Remarks')
    manager_remark = fields.Boolean('Manager Remarks', default=False, compute='_compute_remarks')
    cancel_reason = fields.Text('Cancel Reason')
    sale_revision = fields.Integer(string='Sale Revision', default=0)

    state = fields.Selection(
        selection_add=[
            ('ceo_approve', 'CEO Approval'),
        ], )
    user_signature = fields.Binary('Signature', copy=False, tracking=True)
    order_is_signed = fields.Boolean(default=False, string="Order is signed",
                                     help="Used to identify Signature is added")

    def button_get_digital_siganature(self):
        """Get User Digital Signature and assign it to the Sale order."""
        for rec in self:
            user = self.env.user
            if user.sign_signature:
                rec.user_signature = user.sign_signature
                rec.order_is_signed = True
            else:
                raise UserError(_("User's digital signature is not available. Please Add Signature under user"))

    def _compute_remarks(self):
        for order in self:
            order.ceo_remark = self.env.user.has_group('aqar_sale.group_sale_order_approve_group')
            order.salesman_remark = self.env.user.has_group('sales_team.group_sale_salesman')
            order.manager_remark = self.env.user.has_group('sales_team.group_sale_manager')

    def action_cancel(self):
        if not self.cancel_reason:
            raise UserError('You have to add a cancel reason.')
        else:
            msg = "<strong>Canceled Reason: </strong>" + self.cancel_reason
            self.message_post(body=msg)
        res = super(SaleOrderInheritReason, self).action_cancel()
        return res

    def action_draft(self):
        self.sale_revision = self.sale_revision + 1
        res = super(SaleOrderInheritReason, self).action_draft()
        return res

    def action_confirm(self):
        if self.company_id.so_price_limit < self.amount_total:
            self.state = 'ceo_approve'
            return False
        super(SaleOrderInheritReason, self).action_confirm()

    def action_approve(self):
        super(SaleOrderInheritReason, self).action_confirm()
        return True


#
# class SaleOrderLineInherit(models.Model):
#     _inherit = 'sale.order.line'


# @api.depends('product_id', 'state', 'qty_invoiced', 'qty_delivered')
# def _compute_product_updatable(self):
#     for line in self:
#         if line.state in ['done', 'cancel','sale']:
#             line.product_updatable = False
#             print("jh,kgkjvj",line.product_updatable);
#         else:
#             line.product_updatable = True
#
# @api.depends('product_id', 'state', 'qty_invoiced', 'qty_delivered')
# def _compute_product_updatable(self):
#     # super()._compute_product_updatable()
#     for data in self:
#         if data.order_id.state in ['done', 'cancel', 'sale']:
#             data.product_updatable = False
#             print("jh,kgkjvj", data.product_updatable);
#         else:
#             data.product_updatable = True

class Company(models.Model):
    _inherit = 'res.company'

    so_price_limit = fields.Float(
        string="Sale Price limit",
        help="Maximum Sale Price without approval of CEO")


class ResDiscountSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    so_order_approval = fields.Boolean("Sale limit Approval", default=True)

    so_price_limit = fields.Float(
        string="Sale price limit",
        related='company_id.so_price_limit', readonly=False)
