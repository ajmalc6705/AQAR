# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResUsersInherit(models.Model):
    _inherit = "res.users"

    customer_type_ids = fields.Many2many('customer.type', 'user_customer_type_rel', 'user_id', 'customer_type_id', string='Customer Types')
