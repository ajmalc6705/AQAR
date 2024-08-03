# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    mode_of_payment = fields.Selection([('cash', 'Cash'),
                                        ('cheque_transfer', 'Cheque'),
                                        ('transfer', 'Transfer'),
                                        ('lc', 'LC')], string='Mode of Payment', default='transfer')

    def button_confirm(self):
        """ super the button confirm po"""
        res = super(PurchaseOrderInherit, self).button_confirm()
        today = fields.Date.today()
        if self.mode_of_payment == 'lc':
            lc = self.env['lc.letter'].create({
                'supplier': self.partner_id.id,
                'lc_ref_date': self.date_order,
                'lc_ref': self.name,
                'date': today
            })
            users_obj = self.env['res.users']
            users = []
            for user in users_obj.search([('company_id', '=', lc.company_id.id)]):
                if user.has_group("aqar_lc_letter.group_lc_admin"):
                    users.append(user)
            for notify_user in users:
                activity = self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('aqar_lc_letter.mail_activity_lc').id,
                    'note': "LC",
                    'user_id': notify_user.id,
                    'res_id': lc.id,
                    'res_model_id': self.env['ir.model']._get_id('lc.letter'),
                    'date_deadline': fields.date.today(),
                    'summary': "A Lc of {lc} is created for this {ref} on {date}".format(
                        lc=lc.name, ref=self.name, date=today),
                })
        return res
