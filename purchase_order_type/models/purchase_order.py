# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    purchase_type = fields.Selection([('purchase', 'Purchase'),
                                      ('work', 'Work')], string="Purchase Type", default="purchase")

    state = fields.Selection(selection_add=[('po_authorizer', 'COORDINATOR'), ('po_manager', 'MANAGER'),
                                            ('gm', 'GM'), ('ceo', 'CEO')])

    purchase_revision = fields.Integer(string='Purchase Revision', default=0)
    signature = fields.Binary(string="Signature", copy=False)
    user_signature = fields.Binary('Signature', copy=False, attachment=True, tracking=True)
    order_is_signed = fields.Boolean(default=False, string="Order is signed",
                                     help="Used to identify Signature is added")
    is_sign_initials = fields.Boolean(default=False, string="Initial Sign",
                                      help="Used to identify Initial Signature is added")
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    type_id = fields.Many2one('purchase.requisition.type', string='Agreement Type')
    is_vehicle_requisition = fields.Boolean('Is related to Vehicle', default=False)

    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        res = super(PurchaseOrderInherit, self)._onchange_requisition_id()
        if self.requisition_id:
            self.type_id = self.requisition_id.type_id.id
            self.vehicle_id = self.requisition_id.vehicle_id.id
        return res

    @api.onchange('type_id')
    def onchange_type_id(self):
        for rec in self:
            if rec.type_id:
                rec.is_vehicle_requisition = rec.type_id.is_vehicle_requisition

    def button_draft(self):
        self.purchase_revision = self.purchase_revision + 1
        res = super(PurchaseOrderInherit, self).button_draft()
        return res

    def button_confirm(self):
        for order in self:
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.order')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', order.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()

            if order.state not in ['draft', 'sent', 'gm', 'ceo']:
                continue
            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True

    def button_send_authorizer(self):
        """."""
        for rec in self:
            rec.write({'state': 'po_authorizer'})

    def button_send_to_manager(self):
        """."""
        for rec in self:
            # Retrieve model id for 'purchase.order'
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.order')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            rec.write({'state': 'po_manager'})

    def button_send_to_gm(self):
        """."""
        for rec in self:
            # Retrieve model id for 'purchase.order'
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.order')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            rec.write({'state': 'gm'})

    def button_send_to_ceo(self):
        """."""
        for order in self:
            # Retrieve model id for 'purchase.order'
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.order')], limit=1).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', order.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()

            config_obj = self.env['ir.config_parameter'].sudo()
            config_obj_approval = config_obj.get_param('purchase.po_order_limit')
            if config_obj_approval:
                po_limit = config_obj.get_param('purchase.po_limit_amount') or 5000
                # To convert amount_total into company currency
                total_amount = self.env.company.currency_id._convert(
                    float(order.amount_total), order.currency_id, order.company_id,
                    order.date_order or fields.Date.today())
                if total_amount <= float(po_limit):
                    order.button_confirm()
                else:
                    order.write({'state': 'ceo'})

    def action_send_back(self):
        for rec in self:
            state_map = {
                'ceo': 'gm',
                'gm': 'po_manager',
                'po_manager': 'po_authorizer',
                'po_authorizer': 'draft',
            }
            for rec in self:
                res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.order')]).id
                # Remove Old Activities related to the current record
                self.env['mail.activity'].search([
                    ('res_id', '=', rec.id),
                    ('res_model_id', '=', res_model_id),
                ]).unlink()
                new_state = state_map.get(rec.state)
                if new_state:
                    rec.state = new_state

    def button_get_digital_signature(self):
        """Get User Digital Signature and assign it to the Purchase order."""
        for rec in self:
            user = self.env.user
            if user.sign_signature:
                rec.user_signature = user.sign_signature
                rec.order_is_signed = True
            else:
                raise UserError(_("User's digital signature is not available. Please Add Signature under user"))


    def button_get_sign_initials(self):
        """Get User Digital Signature and assign it to the Purchase order."""
        for rec in self:
            user = self.env.user
            if user.sign_initials:
                rec.user_signature = user.sign_initials
                rec.is_sign_initials = True
            else:
                raise UserError(
                    _("The Initial signature is not available. Please Add your Initial Signature "))

    def button_approve(self):
        for rec in self:
            res = super().button_approve()
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.order')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            return res


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    po_order_limit = fields.Boolean("Purchase Order Approval Amount Limit", config_parameter='purchase.po_order_limit')
    po_limit_amount = fields.Float('Limit Amount', config_parameter='purchase.po_limit_amount', default=5000.000,
                                   digits='Product Price', )
