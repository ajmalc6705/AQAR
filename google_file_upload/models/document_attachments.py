# -*- coding: utf-8 -*-
# Part of Laxicon Solution. See LICENSE file for full copyright and
# licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import requests


class DocumentAttachments(models.Model):

    _name = 'document.attachments'
    _description = 'Attachments'

    name = fields.Char()
    file = fields.Binary('File')
    file_name = fields.Char('Filename')
    file_url = fields.Char('File URL')
    file_id = fields.Char('File ID')

    def create_folder_on_drive(self, folder_name, model_obj=None):
        url = 'https://www.googleapis.com/drive/v3/files'
        access_token = self.env.user.company_id.gdrive_access_token
        headers = {
            'Authorization': 'Bearer {}'.format(access_token),
            'Content-Type': 'application/json'
        }
        # params = self.env['ir.config_parameter']
        folder_id = self.env['multi.folder.drive'].search([('model_id.model', '=', model_obj)], limit=1).folder_id
        parent_id = folder_id
        if not parent_id:
            parent_id = self.env.user.company_id.drive_folder_id
        metadata = {
            'name': folder_name,
            'parents': [parent_id],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        response = requests.post(url, headers=headers, data=json.dumps(metadata))
        if response.status_code == 200:
            des = response.text.encode("utf-8")
            d = json.loads(des)
            return d.get('id')

    def download_document(self):
        return {'url': self.file_url,
                'type': 'ir.actions.act_url',
                'target': 'new'}

    def upload_document(self):
        if self.file_url and self.file:
            self.env['google.file.upload'].delete_from_google_drive(self.file_id)
        active_model = self._context.get('rec_model') or self._context.get('params')['model']
        active_id = self._context.get('rec_id')
        folder = self.env.user.company_id.folder_type
        parent_id = self.env.user.company_id.drive_folder_id
        if folder == 'single_folder':
            parent_id = parent_id
        if folder == 'multi_folder':
            m_folder_id = self.env['multi.folder.drive'].search([('model_id.model', '=', active_model)], limit=1)
            parent_id = m_folder_id.folder_id if m_folder_id.folder_id else parent_id
        if folder == 'record_wise_folder':
            rec_id = self.env[active_model].browse(active_id)
            folder = self.env['ir.model.fields'].search([('model_id.model', '=', active_model), ('name', '=', 'folder_id')])
            if not folder:
                raise ValidationError(_("Development Error\nPlease define folder_id field in %s" % active_model))
            if rec_id and rec_id.folder_id:
                parent_id = rec_id.folder_id
            else:
                parent_id = self.create_folder_on_drive(
                    rec_id.name or rec_id.id, active_model)
                rec_id.folder_id = parent_id
        if parent_id:
            file_url = self.env['google.file.upload'].upload_to_google_drive(self.file_name, self.file, parent_id)
            if file_url:
                self.file = False
                self.file_url = file_url.get('url')
                self.file_id = file_url.get('file_id')

    def unlink(self):
        for rec in self:
            if rec.file_id:
                self.env['google.file.upload'].delete_from_google_drive(rec.file_id)
        return super(DocumentAttachments, self).unlink()
