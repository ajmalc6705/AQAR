# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class EmailMarketingInherit(models.Model):
    _inherit = 'mailing.mailing'

    user_ids = fields.Many2many('res.users', string='Users')


class MailingListInherit(models.Model):
    _inherit = 'mailing.list'

    user_ids = fields.Many2many('res.users', string='Users')


class MailingContactInherit(models.Model):
    _inherit = 'mailing.contact'

    user_ids = fields.Many2many('res.users', string='Users', store=True, precompute=True, tracking=True,
                                compute='_get_allowed_users_list', default=False, readonly=False)

    @api.depends('subscription_list_ids.list_id.user_ids')
    def _get_allowed_users_list(self):
        for rec in self:
            users_list = []
            for subscription in rec.subscription_list_ids:
                if subscription.list_id:
                    users_list += subscription.list_id.user_ids.ids
            rec.user_ids = [(6, 0, users_list)]
