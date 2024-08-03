# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AqarContractCategory(models.Model):
    _name = 'aqar.contract.category'
    _description = 'Aqar Contract Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Name', help="Name of the contract Category")
    user_ids = fields.One2many('res.users','contract_id', string='Users',help='Users who have access')
    user_notification_ids = fields.Many2many('res.users', string='Users',help="Users can send notification")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 help="Company")
    email_notification = fields.Boolean(string='Email Notification', default=False)
    odoo_notification = fields.Boolean(string='Odoo Notification', default=False)
    doc_expiry_before_days = fields.Many2many('expiry.contract.duration', string='Before')
    active = fields.Boolean('Active', default=True, tracking=True)


class ResUsers(models.Model):
    _inherit = 'res.users'

    contract_id = fields.Many2one('aqar.contract.category',string='Contract')

