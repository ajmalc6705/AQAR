# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class Respartner(models.Model):
    _inherit = 'res.partner'

    is_property_agent = fields.Boolean(string='Property Agent',
                                       help='Is the partner is Property Agent')
