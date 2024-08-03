# -*- coding: utf-8 -*-

from odoo import api, models, fields, _


class ChequeCancelled(models.Model):
    _name = 'account.cheque.cancelled'
    _description = 'Cancelled Cheques'
    _order = 'create_date desc'

    cheque_number = fields.Char(string='Cheque Number')
    voucher_id = fields.Many2one(comodel_name='account.payment')
    move_id = fields.Many2one(comodel_name='account.move')
    bearer = fields.Char(string='Bearer', related='voucher_id.bearer', store=True)
    amount = fields.Monetary(string='Amount', related='voucher_id.amount', store=True)
    currency_id = fields.Many2one('res.currency', related='voucher_id.currency_id')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    remarks = fields.Text(string='Remarks')

    def write(self, vals):
        """
        :param vals:
        :return:
        """
        for record in self:
            remarks = record.remarks
            if "remarks" in vals:
                self.voucher_id.message_post(
                    body="Cancelled Cheque Remarks Updated\n %s to %s" % (remarks or '', vals.get('remarks')),
                    subtype_xmlid="mail.mt_comment",
                    message_type="comment")
        return super(ChequeCancelled, self).write(vals)


class TransferPurpose(models.Model):
    _name = 'transfer.purpose'
    _description = 'Transfer Purpose'

    name = fields.Text(string='Transfer Purpose', required=True, copy=False)
    code = fields.Char(string='Code', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string='Company',
                                 default=lambda self: self.env.company)
