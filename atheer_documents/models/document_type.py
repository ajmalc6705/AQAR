# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class DocumentType(models.Model):
    _name = 'document.type'
    _inherit = ['mail.thread']
    _description = 'Document Type'

    name = fields.Char(string="Name", help="Name", tracking=True)
    user_ids = fields.Many2many('res.users', string='Users', tracking=True,
                                help="Users who needs the expiry notifications")
    email_notification = fields.Boolean(string='Email Notification', default=False, tracking=True,
                                        help="Enable this if the user needs to receive email notification")
    odoo_notification = fields.Boolean(string='Odoo Notification', default=False, tracking=True,
                                       help="Enable this if the user needs to receive Odoo notification")
    doc_expiry_before_days = fields.Many2many('expiry.duration', string='Before', tracking=True,
                                              help="Configure how much days or months before that you need the notification")
