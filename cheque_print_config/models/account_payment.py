# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    bearer = fields.Char(string='Check Bearer', tracking=True)
    cheque_state = fields.Selection(selection=[
        ('not_print', 'Not Printed'),
        ('printed', 'Cheque Printed'),
        ('re_print', 'Reprint Request'),
        ('cheque_reprint', 'Reprint Cheque'),
        ('reprint', 'Cheque Reprinted')],
        string="Cheque Status", copy=False, tracking=True, default='not_print')

    @api.onchange('partner_id')
    def set_bearer(self):
        if not self.bearer and self.partner_id:
            self.bearer = self.partner_id.name

    def print_check_v(self):
        for record in self:
            record.write({
                'cheque_state': 'printed' if record.cheque_state == 'not_print' else 'reprint'
            })
            if record.journal_id.type == 'bank':
                return self.env.ref(
                    'cheque_print_config.action_check_print_std'
                ).report_action(self)
            else:
                return self.env.ref(
                    'cheque_print_config.action_check_print_default'
                ).report_action(self)

    def request_reprint_check(self):
        for record in self:
            record.write({'cheque_state': 're_print'})

    def reprint_check(self):
        for record in self:
            record.write({'cheque_state': 'cheque_reprint'})

    def update_cheque_no(self):
        """
        Update Cheque Number and feed the current number in cancelled cheque details.
        :return:
        """
        return {
            'name': _("Update Cheque Number"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'wizard.cheque.number.update',
            'type': 'ir.actions.act_window',
            'nodestroy': False,
            'target': 'new',
            'domain': '[]',
        }

    def cheque_clear_pdc(self):
        for record in self:
            print("-")

    def send_to_head(self):
        """ Overrides the state to Open to Head Acc"""
        super(AccountPayment, self).send_to_head()
        for record in self:
            if (record.transaction_type == 'pdc' and
                    record.effective_date <= record.date):
                raise UserError(" PDC Date must be greater than payment date")

    def do_format_amount(self):
        line1 = ""
        line2 = ""
        amount = self.check_amount_in_words + " Only"
        line_width = self.journal_id.amt_line1_width
        if len(amount) > line_width:
            line1 = amount[:line_width]
            line2 = amount[line_width:]
            # avoid breaking of words
            first_line = len(line1)
            while True:
                if line1[-1] == " " or line2[0] == " " or first_line <= 1:
                    break
                line2 = line1[-1] + line2
                line1 = line1[:-1]
                first_line -= 1
        else:
            line1 = amount
        return {
            'line1': line1,
            'line2': line2,
        }
