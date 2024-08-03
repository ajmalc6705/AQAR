# -*- coding: utf-8 -*-

from odoo import models,fields

class CustomerComplaints(models.Model):
    _inherit = 'customer.complaints'


    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket',string='Helpdesk Ticket')
    from_helpdesk = fields.Boolean(string='From Helpdesk',default=False)