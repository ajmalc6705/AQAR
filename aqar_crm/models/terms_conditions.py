# -*- coding: utf-8 -*-

from odoo import models, fields


class TermsConditions(models.Model):
    _name = 'terms.conditions'
    _description = 'Terms and Conditions'
    _rec_name = 'name'

    description = fields.Html(string='Description')
    name = fields.Char(string='Terms & Conditions')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_offer_notes = fields.Char(string='Sale Offer Notes', config_parameter='aqar_crm.sale_offer_notes')
    rent_offer_notes = fields.Char(string='Rent Offer Notes', config_parameter='aqar_crm.rent_offer_notes')
