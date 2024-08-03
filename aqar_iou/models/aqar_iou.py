# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AqarIoU(models.Model):
    _name = 'aqar.iou'
    _description = 'IoU '
    _rec_name = 'ref'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    ref = fields.Char(string='Doc Number', copy=False,
                      readonly=True,
                      index=True, default=lambda self: _('New'))
    required = fields.Selection([('from_employee', 'From Employee'), ('to_employee', 'To Employee')], string='Required')
    notes = fields.Html(string="Description")
    doc_date = fields.Date(string="Doc Date", default=fields.Date.today())
    amount = fields.Monetary(string='Amount')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                               ('cancel', 'Cancel')], string='Status',
                             default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code(
                    'iou.sequence') or 'New'
        res = super(AqarIoU, self).create(vals_list)
        return res

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_approve(self):
        self.write({'state': 'confirm'})
