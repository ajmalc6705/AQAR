# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class MulkiyaStages(models.Model):
    _name = 'mulkiya.stages'
    _description = 'Mulkiya Stages'

    name = fields.Char(string='Stage')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_journal_id = fields.Many2one('account.journal', string='Default Journal',domain=[('type', '=', 'sale')],
                                 config_parameter='property_sale.sale_journal_id')
