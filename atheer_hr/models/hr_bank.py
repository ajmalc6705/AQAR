# -*- coding: utf-8 -*-
from odoo import fields, models


class ResBank(models.Model):
    _inherit = "res.bank"

    branch = fields.Char(string="Bank Branch")
