# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    delivery_date = fields.Date("Delivery Date")
