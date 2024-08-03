# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta


class DocumentAttachment(models.Model):
    _inherit = 'atheer.documents'

    asset_id = fields.Many2one(comodel_name='assets.accessrz')
    complaint_id = fields.Many2one(comodel_name='customer.complaints')
    property_id = fields.Many2one(comodel_name='property.property')
    building_id = fields.Many2one(comodel_name='property.building', string="Building")
    maintainz_id = fields.Many2one(comodel_name='property.maintenance')
    rent_id = fields.Many2one(comodel_name='property.rent')
    tenant_attachment_id = fields.Many2one(comodel_name='tenant.request')
    legal_action_id = fields.Many2one(comodel_name='dispute.legal.action')
    # sale_id = fields.Many2one(comodel_name='property.sale')
    # client_id = fields.Many2one('client.information')
    room_id = fields.Many2one('property.room', 'Room', related="asset_id.room_id")
    room_property_id = fields.Many2one(comodel_name='property.property', related="room_id.property_id")
    room_building_id = fields.Many2one(comodel_name='property.building',
                                       string="Buildings",
                                       related="room_property_id.parent_building")

    # notify expiring policy:cron job calling
    def notify_document_expiry(self):
        """ notification for asset """
        print("print notification")
    #     doc_expiry_before_days = self.env['notification.duration'].search([('doc_expiry_notification', '=', True)])
    #     date_today = date.today()
    #     # document expiry date notification
    #     for expiry_date in doc_expiry_before_days:
    #         if expiry_date.period == 'days':
    #             before_expiry_date = date_today + relativedelta(days=expiry_date.duration)
    #         if expiry_date.period == 'months':
    #             before_expiry_date = date_today + relativedelta(months=expiry_date.duration)
    #         document_expiry = self.env['atheer.documents'].search([('expiry_date', '=', before_expiry_date)])
    #         for document_exp in document_expiry:
    #             message = "Document with document no. " + document_exp.doc_no + " will expire on " + str(
    #                 document_exp.expiry_date)
    #             self.env['atheer.notification']._send_instant_notify(title="Document Expiry",
    #                                                                  message=message,
    #                                                                  action=self.env.ref(
    #                                                                      'amlak_property_management.action_document_attachment_notification').id,
    #                                                                  user_type="groups",
    #                                                                  domain=[['id', '=', document_exp.id]],
    #                                                                  recipient_ids=[
    #                                                                      self.env.ref('base.group_system').id])

    @api.model
    def create(self, vals):
        res = super(DocumentAttachment, self).create(vals)
        attachment_obj = self.env['ir.attachment']
        if res.rent_id:
            attachment_obj.create({
                'name': res.doc_no,
                'type': 'binary',
                'datas': res.attachment_ids,
                'res_model': 'property.rent',
                'res_id': res.rent_id.id,
                'doc_attachment_id': res.id
            })
        elif res.complaint_id:
            attachment_obj.create({
                'name': res.doc_no,
                'type': 'binary',
                'datas': res.attachment_ids,
                'res_model': 'customer.complaints',
                'res_id': res.complaint_id.id,
                'doc_attachment_id': res.id
            })
        elif res.building_id:
            attachment_obj.create({
                'name': res.doc_no,
                'type': 'binary',
                'datas': res.attachment_ids,
                'res_model': 'property.building',
                'res_id': res.building_id.id,
                'doc_attachment_id': res.id
            })
        elif res.property_id:
            attachment_obj.create({
                'name': res.doc_no,
                'type': 'binary',
                'datas': res.attachment_ids,
                'res_model': 'property.property',
                'res_id': res.property_id.id,
                # 'doc_attachment_id': res.id
            })
        elif res.asset_id:
            attachment_obj.create({
                'name': res.doc_no,
                'type': 'binary',
                'datas': res.attachment_ids,
                'res_model': 'assets.accessrz',
                'res_id': res.asset_id.id,
                'doc_attachment_id': res.id
            })
        return res

    def unlink(self):
        for rec in self:
            if rec.rent_id:
                if rec.rent_id.state != 'draft':
                    raise UserError(_("You cant delete documents of rent agreement which is not in draft state"))
        return super(DocumentAttachment, self).unlink()
