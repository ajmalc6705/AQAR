# -*- coding: utf-8 -*-

from odoo import models,fields,api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    community_journal_id = fields.Many2one('account.journal',string='Default Journal',config_parameter='property_community.community_journal_id')

