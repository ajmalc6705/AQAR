# -*- coding: utf-8 -*-

from odoo import models, fields,_
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    building_id = fields.Many2one('property.building',string='Building',help='Building of that property')
    property_id = fields.Many2one('property.property',string='Flat/Villa',help='Unit of the Property')
    complaint_id = fields.Many2one('customer.complaints',string='Customer Complaints')
    is_complaint_created = fields.Boolean(string='Is Complaint',default=False)


    def action_create_complaints(self):
        """ Action for create complaints """
        if not self.building_id:
            raise UserError(_('Enter the Building Details'))
        if not self.property_id:
            raise UserError(_('Enter the Flat/Villa Details'))
        complaint = self.env['customer.complaints'].sudo().create({
            'building':self.building_id.id,
            'property':self.property_id.id,
            'tenant_ph':self.partner_phone,
            'tenant_id':self.partner_id.id,
            'helpdesk_ticket_id':self.id,
            'from_helpdesk':True,
            'procurement_flag':True,
        })
        self.complaint_id = complaint.id
        self.is_complaint_created = True

    def action_view_complaints(self):
        """ view the complaints"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tenant Complaints',
            'view_mode': 'form',
            'res_model': 'customer.complaints',
            'res_id': self.complaint_id.id,
        }
