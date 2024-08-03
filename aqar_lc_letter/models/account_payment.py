# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api, _


class PaymentLC(models.Model):
    _inherit = 'account.payment'

    lc_id = fields.Many2one('lc.letter', 'LC ID')