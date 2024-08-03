# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ResGroups(models.Model):
    _inherit = "res.groups"

    notify_users_ids = fields.Many2many('res.users', 'res_groups_notify_users_rel', 'group_id', 'user_id',
                                        string="Notify Users")
