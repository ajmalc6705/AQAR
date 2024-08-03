# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class POSignaturePasswordTransient(models.TransientModel):
    _name = "signature.password.check.wizard"
    _description = 'Signature password Checking'

    sign_password = fields.Char(string='Signature Password', required=True, help="Enter Signature password")

    def validate_password_and_write_signature(self):
        user = self.env.user
        if self.sign_password == user.sign_password:  # This is a simplistic check, you might want to enhance it
            active_id = self._context.get('active_id')
            purchase_order = self.env['purchase.order'].browse(active_id)
            if user.sign_signature:
                purchase_order.write({
                    'user_signature': user.sign_signature,
                    'order_is_signed': True,
                })
            else:
                raise UserError(_("User's digital signature is not available. Please Add Signature under user"))

        else:
            raise ValidationError("Wrong password! Please try again.")

    def validate_initial_sign_password_and_write_signature(self):
        user = self.env.user
        if self.sign_password == user.sign_password:  # This is a simplistic check, you might want to enhance it
            active_id = self._context.get('active_id')
            purchase_order = self.env['purchase.order'].browse(active_id)
            if user.sign_initials:
                purchase_order.write({
                    'user_signature': user.sign_initials,
                    'is_sign_initials': True,
                })
            else:
                raise UserError(
                    _("The Initial signature is not available. Please Add your Initial Signature "))

        else:
            raise ValidationError("Wrong password! Please try again.")
