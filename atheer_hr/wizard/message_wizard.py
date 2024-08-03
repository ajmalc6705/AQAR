# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class MessageWizard(models.TransientModel):
    _name = 'message.wizard'
    _description = "Message Wizard"

    message = fields.Text('Message', required=True)

    def action_ok(self):
        """ close wizard"""
        return {'type': 'ir.actions.act_window_close'}
