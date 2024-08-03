# -*- coding: utf-8 -*-

import datetime as DT
from odoo import models, api, fields, tools
from odoo.tools.translate import _


class AccountMove(models.Model):
    _inherit = "res.partner"

    is_auditor = fields.Boolean()