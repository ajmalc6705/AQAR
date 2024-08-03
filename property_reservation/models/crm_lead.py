# -*- coding: utf-8 -*-

from odoo import models,fields,api,_

class CRMLead(models.Model):
    _inherit = 'crm.lead'


    is_create_reservation = fields.Boolean(string='Reservation',default=False)
    reservation_id = fields.Many2one('property.reservation',string='Reservation')


    def action_property_reservation(self):
        """ action for create property reservation"""
        reservation = self.env['property.reservation'].create({
            'lead_id':self.id,
            'partner_id': self.partner_id.id,
            'building_id':self.building_id.id,
            'unit_id':self.unit_id.id,
            'unit_type_id':self.unit_type_id.id,
            'sales_price':self.sales_price,
            'terms_conditions_id':self.terms_conditions_id.id,
            'notes':self.terms_conditions_id.description,
            'enquiry_date':self.enquiry_date,
            'offer_valid_date': self.offer_valid_date,
            'unit_sales_price':self.unit_id.sale_price,
            'specifications': self.building_id.specifications,
            'doc_ids':self.unit_id.doc_ids.ids,
        })
        self.is_create_reservation = True
        self.reservation_id = reservation.id

    def action_view_reservation(self):
        """ shows the created reservation"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Property Reservation',
            'view_mode': 'form',
            'res_model': 'property.reservation',
            'res_id': self.reservation_id.id,
        }


class ResConfigsettings(models.TransientModel):
    _inherit = 'res.config.settings'

    report_template = fields.Char(string='Reservation Report Template',
                                  config_parameter='property_reservation.report_template')
    journal_id = fields.Many2one('account.journal', string='Default Journal', domain=[('type', '=', 'sale')],
                                 config_parameter='property_reservation.journal_id')
