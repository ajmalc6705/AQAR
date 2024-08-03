# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import UserError


class WizardChequeUpdate(models.TransientModel):
    _name = 'wizard.cheque.number.update'
    _description = "Wizard Cheque Update"

    cheque_number = fields.Char(string='Cheque Number')
    reason = fields.Text(string='Reason', copy=False)

    def post(self):
        """
        Update Cheque Number and feed the current number in cancelled cheque details.
        :return:
        """
        voucher_id = self.env['account.voucher'].browse(self.env.context.get('active_id'))
        if voucher_id.cheque_no and (voucher_id.cheque_no.strip() == self.cheque_number.strip()):
            raise UserError("Cheque Number Should Be Unique !")
        voucher_id.cancelled_cheques = [(0, 0, {'cheque_number': voucher_id.cheque_no and voucher_id.cheque_no.strip(),
                                                'remarks': self.reason})]
        voucher_id.cheque_no = self.cheque_number and self.cheque_number.strip()
