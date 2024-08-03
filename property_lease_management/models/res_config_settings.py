# -*- coding: utf-8 -*-

from ast import literal_eval
from odoo import fields, models, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    journal = fields.Many2one('account.journal', string='Default Journal', domain=[('type', '=', 'sale')],
                                 config_parameter='property_lease_management.journal')

    @api.model
    def maintenance_notification(self):
        print("print notification")
        # return self.env['notification.duration'].search([('maintenance_notification', '=', True)])

    @api.model
    def warranty_notification(self):
        print("print notification")
        # return self.env['notification.duration'].search([('warranty_notification', '=', True)])

    @api.model
    def doc_expiry_notification(self):
        print("print notification")
        # return self.env['notification.duration'].search([('doc_expiry_notification', '=', True)])

    # maintenance_months_before = fields.Many2many('notification.duration', 'notification_duration_maintenance_rel',
    #                                              'maintenance_days',
    #                                              default=maintenance_notification)
    # warranty_months_before = fields.Many2many('notification.duration', 'notification_duration_warranty_rel',
    #                                           'warranty_days', default=warranty_notification)
    # doc_expiry_before_days = fields.Many2many('notification.duration', 'notification_duration_asset_doc_rel',
    #                                           'document_days', default=doc_expiry_notification)

    # @api.model
    # def get_values(self):
    #     res = super(ResConfigSettings, self).get_values()
    #     params = self.env['ir.config_parameter'].sudo()
    #     maintenance_notification_ids = literal_eval(params.get_param('notification.maintenance_months_before')) \
    #         if params.get_param('notification.maintenance_months_before') else []
    #     warranty_notification_ids = literal_eval(params.get_param('notification.warranty_months_before')) \
    #         if params.get_param('notification.warranty_months_before') else []
    #     doc_expiry_notification_ids = literal_eval(params.get_param('notification.doc_expiry_before_days')) \
    #         if params.get_param('notification.doc_expiry_before_days') else []
    #     res.update(
    #         maintenance_months_before=[(6, 0, maintenance_notification_ids)],
    #         warranty_months_before=[(6, 0, warranty_notification_ids)],
    #         doc_expiry_before_days=[(6, 0, doc_expiry_notification_ids)],
    #     )
    #     return res
    #
    # def set_values(self):
    #     super(ResConfigSettings, self).set_values()
    #     self.env['ir.config_parameter'].sudo().set_param('notification.maintenance_months_before',
    #                                                      self.maintenance_months_before.ids)
    #     self.env['ir.config_parameter'].sudo().set_param('notification.warranty_months_before',
    #                                                      self.warranty_months_before.ids)
    #     self.env['ir.config_parameter'].sudo().set_param('notification.doc_expiry_before_days',
    #                                                      self.doc_expiry_before_days.ids)
    #     obj = self.env['notification.duration'].search([])
    #     maintenance = []
    #     for rec in self.maintenance_months_before:
    #         maintenance.append(rec.id)
    #     for records in obj:
    #         if records.id in maintenance:
    #             records.maintenance_notification = True
    #         else:
    #             records.maintenance_notification = False
    #
    #     warranty = []
    #     for record in self.warranty_months_before:
    #         warranty.append(record.id)
    #     for records in obj:
    #         if records.id in warranty:
    #             records.warranty_notification = True
    #         else:
    #             records.warranty_notification = False
    #
    #     asset_doc = []
    #     for record in self.doc_expiry_before_days:
    #         asset_doc.append(record.id)
    #     for records in obj:
    #         if records.id in asset_doc:
    #             records.doc_expiry_notification = True
    #         else:
    #             records.doc_expiry_notification = False

    # def execute(self):
    #     obj = self.env['notification.duration'].search([])
    #     maintenance = []
    #     for rec in self.maintenance_months_before:
    #         maintenance.append(rec.id)
    #     for records in obj:
    #         if records.id in maintenance:
    #             records.maintenance_notification = True
    #         else:
    #             records.maintenance_notification = False
    #
    #     warranty = []
    #     for record in self.warranty_months_before:
    #         warranty.append(record.id)
    #     for records in obj:
    #         if records.id in warranty:
    #             records.warranty_notification = True
    #         else:
    #             records.warranty_notification = False
    #
    #     asset_doc = []
    #     for record in self.doc_expiry_before_days:
    #         asset_doc.append(record.id)
    #     for records in obj:
    #         if records.id in asset_doc:
    #             records.doc_expiry_notification = True
    #         else:
    #             records.doc_expiry_notification = False
