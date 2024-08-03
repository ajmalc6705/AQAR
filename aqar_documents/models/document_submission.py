# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DocumentSubmission(models.Model):
    _name = 'document.submission'
    _description = 'Document Submission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'ref'

    ref = fields.Char(string='Doc Number', copy=False,
                      readonly=True,
                      index=True, default=lambda self: _('New'))
    name = fields.Char(string='Document Name', help='Name of the Document', required=True, tracking=True)
    doc_type = fields.Many2one('document.type', string='Document Type', required=True, tracking=True)
    user_ids = fields.Many2many('res.users', string='User')
    issue_date = fields.Date(string="Issue Date", default=fields.Date.today(), tracking=True)
    expiry_date = fields.Date(string='Expiry Date', copy=False,
                              help="Date of expiry", tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    active = fields.Boolean('Active', default=True, tracking=True)
    return_date = fields.Date(string='Return Date', tracking=True)
    received_date = fields.Date(string='Received Date', tracking=True, help='Date for Received Document From Employee')
    attachment_ids = fields.Many2many('ir.attachment',
                                      string="Attachment", tracking=True,
                                      help='You can attach the copy of your document',
                                      copy=False)
    doc_dec = fields.Html(string="Description", tracking=True)
    file_name = fields.Char(string="Filename", tracking=True)
    doc_link = fields.Char('Document Link', help="Youtube or Google Document URL", tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('doc_with_company', 'Doc With Company'),
                              ('return_back', 'Return Back'), ('cancel', 'Cancel')], string='Status',
                             default='draft', tracking=True)
    issued_authority = fields.Char("Issued Authority", tracking=True)

    @api.onchange('doc_type')
    def onchange_doc_type(self):
        for rec in self:
            if rec.doc_type.user_ids:
                rec.user_ids = rec.doc_type.user_ids.ids

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code(
                    'document.submission.sequence') or 'New'
        res = super(DocumentSubmission, self).create(vals_list)
        return res

    @api.constrains('issue_date', 'expiry_date')
    def check_expiry_date(self):
        """ To check Expiry date is not after issued date"""
        if self.expiry_date and self.issue_date:
            if self.expiry_date < self.issue_date:
                raise UserError(_(
                    "Please select a Valid Expiry Date."
                ))

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_approve(self):
        for rec in self:
            if not rec.employee_id:
                raise UserError(_(
                    "Please select the Employee."
                ))
            if not rec.received_date:
                raise UserError(_(
                    "Please enter the Received Date."
                ))
            rec.write({'state': 'doc_with_company'})

    def action_return_company(self):
        for rec in self:
            if not rec.employee_id:
                raise UserError(_(
                    "Please select the Employee."
                ))
            if not rec.received_date:
                raise UserError(_(
                    "Please enter the Received Date."
                ))
            self.return_date = False
            rec.write({'state': 'doc_with_company'})

    def action_return_back(self):
        if not self.return_date:
            raise UserError(_('Add the Return Date'))
        self.received_date = False
        self.write({'state': 'return_back'})
