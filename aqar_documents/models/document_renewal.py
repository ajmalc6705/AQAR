# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DocumentRenewal(models.Model):
    _name = "document.renewal"
    _description = 'Document Renewal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'ref'

    ref = fields.Char(string='Doc Number', copy=False,
                      readonly=True,
                      index=True, default=lambda self: _('New'))
    document_id = fields.Many2one('atheer.documents', string='Document',tracking=True)
    user_ids = fields.Many2many('res.users', string='User')
    document_type = fields.Many2one('document.type', string='Document Type',required=True,tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('cancel', 'Cancel')], string='Status',
                             default='draft',tracking=True)
    issue_date = fields.Date(string="Issue Date", default=fields.Date.today(),tracking=True)
    expiry_date = fields.Date(string='Expiry Date', copy=False,
                              help="Date of expiry",tracking=True)
    old_issue_date = fields.Date(string="Old Issue Date", tracking=True,
                                 help="Issue Date before renewal")
    old_expiry_date = fields.Date(string='Old Expiry Date', copy=False,
                              help="Expiry Date before renewal", tracking=True)
    active = fields.Boolean('Active', default=True, tracking=True)
    attachment_ids = fields.Many2many('ir.attachment',
                                      string="Attachment",
                                      help='You can attach the copy of your document',
                                      copy=False,tracking=True)
    doc_dec = fields.Html(string="Description", tracking=True)
    file_name = fields.Char(string="Filename",tracking=True)
    doc_link = fields.Char('Document Link', help="Youtube or Google Document URL", tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    issued_authority = fields.Char("Issued Authority", tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code(
                    'document.renewal.sequence') or 'New'
        res = super(DocumentRenewal, self).create(vals_list)
        return res

    @api.onchange('document_id')
    def _onchange_document_id(self):
        for rec in self:
            if rec.document_id:
                rec.old_issue_date = rec.document_id.issue_date
                rec.old_expiry_date = rec.document_id.expiry_date
                rec.user_ids = rec.document_id.user_ids.ids

    @api.onchange('document_type')
    def _onchange_doc_type(self):
        documents = self.env['atheer.documents'].search([('doc_type','=',self.document_type.id)])
        return {'domain': {'document_id': [('id', 'in', documents.ids)]}}

    @api.constrains('issue_date', 'expiry_date')
    def check_expiry_date(self):
        """ To check Expiry date is not after issued date"""
        for rec in self:
            if rec.expiry_date and rec.issue_date:
                if rec.expiry_date <= rec.issue_date:
                    raise UserError(_(
                        "The new Expiry date should be greater than New Issue Date."
                    ))

    @api.constrains('issue_date', 'old_issue_date')
    def check_new_old_issue_date(self):
        """ To check Expiry date is not after issued date"""
        for rec in self:
            if rec.old_issue_date and rec.issue_date:
                if rec.issue_date <= rec.old_issue_date:
                    raise UserError(_(
                        "The new Issue date should be greater than Old Issue Date."
                    ))

    @api.constrains('expiry_date', 'old_expiry_date')
    def check_new_old_expiry_date(self):
        """ To check Expiry date is not after issued date"""
        for rec in self:
            if rec.expiry_date and rec.old_expiry_date:
                if rec.expiry_date <= rec.old_expiry_date:
                    raise UserError(_(
                        "The new Expiry date should be greater than Old Expiry Date."
                    ))

    def action_update_document(self):
        """ update the document based on new details"""
        if self.document_id:
            print("iss",self.issue_date)
            self.document_id.update({
                'issue_date':self.issue_date,
                'expiry_date':self.expiry_date,
                'doc_dec':self.doc_dec,
                'doc_link':self.doc_link,
                'file_name':self.file_name,
                'issued_authority':self.issued_authority,
                'attachment_ids':self.attachment_ids,
            })
            self.state = 'confirm'
        else:
            raise UserError(_('Upload a Document'))

    def action_cancel(self):
        self.write({'state':'cancel'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def mass_confirm(self):
        """ server action to move records to confirm"""
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'confirm'
