# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class DocumentManagement(models.Model):
    _name = 'atheer.documents'
    _description = 'Documents'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'doc_no'

    doc_no = fields.Char(string='Doc Number', copy=False,
                         readonly=True,
                         index=True, default=lambda self: _('New'))
    name = fields.Char(string='Document Name', help='Name of the Document', required=True, tracking=True)
    doc_type = fields.Many2one('document.type', string='Document Type', tracking=True, required=True)
    user_ids = fields.Many2many('res.users', string='User')
    issue_date = fields.Date(string="Issue Date", default=fields.Date.today(), tracking=True)
    expiry_date = fields.Date(string='Expiry Date', copy=False,
                              help="Date of expiry", tracking=True)
    active = fields.Boolean('Active', default=True, tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', tracking=True,
                                      string="Attachment",
                                      help='You can attach the copy of your document',
                                      copy=False)
    doc_dec = fields.Html(string="Description")
    file_name = fields.Char(string="Filename")
    doc_link = fields.Char('Document Link', help="Youtube or Google Document URL")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    issued_authority = fields.Char("Issued Authority")

    @api.onchange('doc_type')
    def onchange_doc_type(self):
        for rec in self:
            if rec.doc_type.user_ids:
                rec.user_ids = rec.doc_type.user_ids.ids

    def name_get(self):
        res = []
        for each in self:
            name = each.name
            if name:
                res.append((each.id, each.doc_no + ' [' + str(name) + ']'))
            else:
                res.append((each.id, each.doc_no))
        return res

    def unlink(self):
        res = super().unlink()
        if not self.env.user.has_group('atheer_documents.group_doc_admin'):
            raise UserError(_('Doc Admin have the access to delete the Document'))
        return res

    # @api.constrains('issue_date', 'expiry_date')
    # def check_expiry_date(self):
    #     """ To check Expiry date is not after issued date"""
    #     for rec in self:
    #         if rec.expiry_date and rec.issue_date:
    #             if rec.expiry_date < rec.issue_date:
    #                 raise UserError(_(
    #                     "Please select a Valid Expiry Date for document. issue date:%s and Expiry date:%s",
    #                     rec.issue_date, rec.expiry_date
    #                 ))

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('doc_no', 'New') == 'New':
                vals['doc_no'] = self.env['ir.sequence'].next_by_code(
                    'document.sequence') or 'New'
        res = super(DocumentManagement, self).create(vals_list)
        return res

    def notification_reminder(self):
        """ automatic notification reminder based on doc type"""
        doc = self.search([])
        days = []
        exp_date = 0
        for rec in doc:
            mail_sent = 0
            if rec.expiry_date:
                for expire_days in rec.doc_type.doc_expiry_before_days:
                    if mail_sent == 0:
                        if expire_days.period == 'days':
                            days = expire_days.duration
                        elif expire_days.period == 'months':
                            days = expire_days.duration * 30
                        exp_date = rec.expiry_date - timedelta(days=days)
                        if fields.Date.today() == rec.expiry_date or fields.Date.today() == exp_date:
                            if rec.doc_type.email_notification:
                                mail_template = self.env.ref('atheer_documents.doc_letter_email')
                                if mail_template:
                                    for user in rec.doc_type.user_ids:
                                        template_rec = mail_template
                                        template_rec.write({'email_to': user.id})
                                        template_rec.send_mail(rec.id, force_send=True)
                                    mail_sent = 1
                            if rec.doc_type.odoo_notification:
                                for user in rec.doc_type.user_ids:
                                    self.env['mail.activity'].create({
                                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                        'summary': 'Document Expiry',
                                        'date_deadline': rec.expiry_date,
                                        'user_id': user.id,
                                        'res_model_id': self.env['ir.model']._get_id('atheer.documents'),
                                        'res_id': rec.id,
                                    })
                                mail_sent = 1
