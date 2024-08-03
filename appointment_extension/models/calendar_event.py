# -*- coding: utf-8 -*-

from odoo import models,fields,api,_

class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    enable_meeting_link = fields.Boolean(string="Enable Meeting Link",default=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('visit', 'Visited'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    ref_no = fields.Char(string='Ref No', copy=False,
                         readonly=False,
                         index=True, default=lambda self: _('New'))
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'calendar.event')],
                                     string='Attachments')

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('ref_no', 'New') == 'New':
                vals['ref_no'] = self.env['ir.sequence'].next_by_code(
                    'appointment.sequence') or 'New'
        return super(CalendarEvent, self).create(vals_list)

    def action_visited(self):
        """this action set the functionality to visited"""
        self.write({'state': 'visit'})

    def action_reset_draft(self):
        """ Reset the record to draft state"""
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_done(self):
        self.write({'state': 'confirm'})