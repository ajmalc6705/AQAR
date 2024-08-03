# -*- coding: utf-8 -*-
from random import randint

from odoo import models, fields, api


class CRMLead(models.Model):
    _inherit = 'crm.lead'

    enquiry_date = fields.Date(string='Date of Enquiry', help="Enquiry Date", tracking=True)
    offer_valid_date = fields.Date(string='Offer Valid Until', tracking=True)
    building_id = fields.Many2one('property.building', string='Building')
    unit_id = fields.Many2one('property.property', string='Unit', tracking=True)
    unit_ids = fields.Many2many('property.property', compute='_compute_unit_ids')
    unit_type_id = fields.Many2one('property.type', string='Property Type')
    terms_conditions_id = fields.Many2one('terms.conditions', string='Terms & Conditions')
    property_tag_ids = fields.Many2many('property.tags', string='Interested for')
    sub_types = fields.Many2one('sub.type', string='Sub Type')
    rent_offer_sent = fields.Boolean(string='Rent offer Sent', default=False)
    sale_offer_sent = fields.Boolean(string='Sale offer Sent', default=False)
    sales_price = fields.Float(string='Sale Price', )
    notes = fields.Html(string='Terms & Conditions', readonly=False)
    offer_send_date = fields.Date(string='Offer Send Date')
    seq_no = fields.Char(string='NO', readonly=True, copy=False, )
    sale_offer_notes = fields.Html(string='Sale Offer Notes')
    rent_offer_notes = fields.Html(string='Rent Offer Notes')

    # Vat
    vat_taxes_ids = fields.Many2many('account.tax', string='Vat', domain=[('type_tax_use', '=', 'sale')])

    def name_get(self):
        res = []
        for each in self:
            name = each.name
            if each.seq_no:
                res.append((each.id, str(name) + ' [' + each.seq_no + ']'))
            else:
                res.append((each.id, name))
        return res

    @api.model
    def create(self, vals):
        if vals.get('seq_no', '/') == '/':
            vals['seq_no'] = self.env['ir.sequence'].next_by_code('crm.sequence') or '/'
        return super(CRMLead, self).create(vals)

    @api.depends('building_id')
    def _compute_unit_ids(self):
        self.unit_ids = False
        for rec in self:
            unit = self.env['property.property'].search(
                [('parent_building', '=', rec.building_id.id), ('state', '=', 'open')])
            rec.unit_ids = unit.mapped('id')

    @api.onchange('terms_conditions_id')
    def _onchange_terms_conditions(self):
        self.notes = self.terms_conditions_id.description

    @api.onchange('building_id')
    def _onchange_building_sale_notes(self):
        """ get notes for sale offer in crm"""
        self.sale_offer_notes = self.env['ir.config_parameter'].sudo().get_param('aqar_crm.sale_offer_notes')
        self.rent_offer_notes = self.env['ir.config_parameter'].sudo().get_param('aqar_crm.rent_offer_notes')

    def action_send_rent_offer(self):
        """ send mail for rent offer"""
        mail_template = self.env.ref('aqar_crm.rent_offer_letter')
        lang = self.env.context.get('lang')

        ctx = {
            'default_model': 'crm.lead',
            'default_res_id': self.id,
            'default_use_template': bool(mail_template),
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'rent_offer_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def action_send_sale_offer(self):
        """ send mail for sale offer"""
        mail_template = self.env.ref('aqar_crm.sale_offer_letter')
        lang = self.env.context.get('lang')
        ctx = {
            'default_model': 'crm.lead',
            'default_res_id': self.id,
            'default_use_template': bool(mail_template),
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'sale_offer_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }


class PropertyTags(models.Model):
    _name = 'property.tags'
    _rec_name = 'name'
    _description = 'Property Tags'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string='Property Tags', help='Tags of the Property')
    color = fields.Integer('Color', default=_get_default_color)


class SubType(models.Model):
    _name = 'sub.type'
    _rec_name = 'name'
    _description = 'Sub Types'

    name = fields.Char(string='Sub Types', )


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    rent_offer_sent = fields.Boolean(string='Rent Offer Sent')
    sale_offer_sent = fields.Boolean(string='Sale Offer Sent')

    def action_send_mail(self):
        res = super(MailComposer, self).action_send_mail()
        if self.model == 'crm.lead':
            today = fields.date.today()
            crm = self.env['crm.lead'].browse(self.res_id)
            if self.env.context.get('sale_offer_sent'):
                crm.update({
                    'sale_offer_sent': True,
                    'offer_send_date': today
                })
            elif self.env.context.get('rent_offer_sent'):
                crm.update({
                    'rent_offer_sent': True,
                })
        return res
