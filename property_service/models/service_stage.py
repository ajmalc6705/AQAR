# -*- coding: utf-8 -*-

from odoo import models,fields,api,_

class PropertyServiceStage(models.Model):
    _name = 'service.stage'
    _description = 'Service Stage'

    name = fields.Char(string='Stage')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    journal_id = fields.Many2one('account.journal', string='Default Journal',domain=[('type', '=', 'sale')],
                                 config_parameter='property_service.journal_id')