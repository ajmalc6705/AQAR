# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError



class CancelLCReason(models.TransientModel):
    _name = 'cancel.lc.reason'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Cancel Reason Wizard"

    name = fields.Char('Reason', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        reasons = super(CancelLCReason, self).create(vals_list)
        for vals in vals_list:
            if self.env.context.get('active_id'):
                model_id = self.env[self.env.context["active_model"]].browse(self.env.context.get('active_id'))
                if model_id.id:
                    msg = "<strong>Canceled Reason: </strong>" + vals['name']
                    model_id.message_post(body=msg)
        return reasons

    def action_cancel(self):
        if self.env.context.get('active_id'):
            model_id = self.env[self.env.context["active_model"]].browse(self.env.context.get('active_id'))
            if self.env.context["active_model"] == 'lc.letter':
                payment = self.env['account.payment'].search([('lc_id','=',model_id.name)])
                move = self.env['account.move'].search([('lc_letter','=',model_id.id)])
                if payment:
                    payment.action_draft()
                    payment.action_cancel()

                if move:
                    move.button_draft()
                    move.button_cancel()
                model_id.state = 'cancel'