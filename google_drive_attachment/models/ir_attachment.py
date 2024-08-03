# -*- coding: utf-8 -*-
# Part of Laxicon Solution. See LICENSE file for full copyright and
# licensing details.

from odoo import models, fields, api
import json
import requests


class IrAttachment(models.Model):

    _inherit = 'ir.attachment'

    file_id = fields.Char()
    folder_id = fields.Char()

    def create_folder_on_google_drive(self, folder_name, model_obj=None):
        self.env.user.company_id.check_token_expirey()
        url = 'https://www.googleapis.com/drive/v3/files'
        access_token = self.env.user.company_id.gdrive_access_token
        headers = {
            'Authorization': 'Bearer {}'.format(access_token),
            'Content-Type': 'application/json'
        }
        folder_id = self.env['multi.folder.drive'].search(
            [('model_id.model', '=', model_obj)], limit=1).folder_id
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

    @api.model
    def create(self, vals):
        res = super(IrAttachment, self).create(vals)
        if self.env.user.has_group('base.group_system') or self.env.user.has_group('base.group_erp_manager'):
            model_ids = self.env.user.company_id.model_ids.ids
            active_model = res.res_model
            m_id = self.env['ir.model'].search([('model', '=', active_model)])
            m_id = m_id and m_id.id or False
            company_id = res.company_id
            if model_ids and m_id in model_ids:
                models = self.env['ir.model'].search([('model', '=', active_model)])
                record_id = self.env[active_model].search([('id', '=', res.res_id)])
                if 'company_id' in record_id._fields and record_id._fields['company_id']:
                    company_id = record_id.company_id
                active_id = res.res_id
                folder = company_id.folder_type
                parent_id = company_id.drive_folder_id
                if folder == 'single_folder':
                    parent_id = parent_id
                if folder == 'multi_folder':
                    m_folder_id = self.env['multi.folder.drive'].search(
                        [('model_id.model', '=', active_model), ('company_id', '=', company_id.id)], limit=1)
                    parent_id = m_folder_id.folder_id and m_folder_id.folder_id or parent_id
                if folder == 'record_wise_folder':
                    rec_id = self.env[active_model].browse(active_id)
                    attachment = self.env['ir.attachment'].search(
                        [('res_model', '=', active_model), ('res_id', '=', active_id), ('folder_id', '!=', False)])
                    if not attachment:
                        parent_id = self.create_folder_on_google_drive(
                            rec_id.name or res.res_name, active_model)
                        res.folder_id = parent_id
                    else:
                        parent_id = attachment.folder_id
                if parent_id:
                    file_url = self.env['google.file.upload'].upload_to_google_drive(res.name, res.datas, parent_id, company_id)
                    if file_url:
                        res.datas = False
                        res.store_fname = ''
                        res.db_datas = False
                        res.type = 'url'
                        res.url = file_url.get('url')
                        res.file_id = file_url.get('file_id')
        return res


    def upload_on_drive(self):
        active_model = self.res_model
        company_id = self.company_id
        record_id = self.env[active_model].search([('id', '=', self.res_id)], limit=1)
        if 'company_id' in record_id._fields and record_id._fields['company_id']:
            company_id = record_id.company_id
        active_id = self.res_id
        folder = company_id.folder_type
        parent_id = company_id.drive_folder_id
        if folder == 'single_folder':
            parent_id = parent_id
        if folder == 'multi_folder':
            m_folder_id = self.env['multi.folder.drive'].search([('model_id.model', '=', active_model), ('company_id', '=', company_id.id)], limit=1)
            parent_id = m_folder_id.folder_id and m_folder_id.folder_id or parent_id
        if folder == 'record_wise_folder':
            rec_id = self.env[active_model].browse(active_id)
            attachment = self.env['ir.attachment'].search([('res_model', '=', active_model), ('res_id', '=', active_id), ('folder_id', '!=', False)])
            if not attachment:
                parent_id = self.create_folder_on_google_drive(rec_id.name or self.res_name, active_model)
                self.folder_id = parent_id
            else:
                parent_id = attachment.folder_id
        if parent_id:
            file_url = self.env['google.file.upload'].upload_to_google_drive(self.name, self.datas, parent_id, company_id)
            if file_url:
                self.datas = False
                self.store_fname = ''
                self.db_datas = False
                self.type = 'url'
                self.url = file_url.get('url')
                self.file_id = file_url.get('file_id')

    def cron_upload_on_gdrive(self, limit):
        company_ids = self.env['res.company'].sudo().search([])
        model_list = []
        for comapny in company_ids:
            comapny.generate_gdrive_refresh_token()
            model_ids = comapny.model_ids
            for model in model_ids:
                model_list.append(model.model)
        attachment_ids = self.sudo().search([('type', '=', 'binary'), ('res_model', 'in', list(set(model_list)))], limit=limit)
        for att in attachment_ids:
            att.upload_on_drive()


    def unlink(self):
        for rec in self:
            active_model = rec.res_model
            company_id = rec.company_id
            record_id = self.env[active_model].search([('id', '=', rec.res_id)])
            if 'company_id' in record_id._fields and record_id._fields['company_id']:
                company_id = record_id.company_id
            if rec.file_id:
                self.env['google.file.upload'].delete_from_google_drive(rec.file_id, rec.company_id)
        return super(IrAttachment, self).unlink()
