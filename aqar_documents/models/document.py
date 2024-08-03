# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class DocumentManagement(models.Model):
    _inherit = 'atheer.documents'

    renew = fields.Boolean('Renewed',  default=False, compute='_compute_renewal')

    def renew_document(self):
        """ renew the document from document page """
        context = {'default_document_type': self.doc_type.id,
                   'default_document_id': self.id,
                   'default_old_issue_date': self.issue_date,
                   'default_old_expiry_date': self.expiry_date,
                   }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Document Renewal'),
            'view_mode': 'form',
            'res_model': 'document.renewal',
            'context': context,
        }
    def _compute_renewal(self):
        """ find the renewals """
        for rec in self:
            renews = self.env['document.renewal'].search([('document_id', '=', rec.id)])
            if renews:
                rec.renew = True
            else:
                rec.renew = False

    def get_renewals(self):
        """ get the renewals """
        renews = self.env['document.renewal'].search([('document_id', '=', self.id)])
        print("rrr",renews)
        domain = ['id', 'in', renews.ids]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Document Renewal'),
            'view_mode': 'tree,form',
            'res_model': 'document.renewal',
            'domain': [('document_id', '=', self.id)],
        }
