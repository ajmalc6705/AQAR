# -*- coding: utf-8 -*-


from odoo import models,fields,_
from odoo.exceptions import UserError

class CRMLead(models.Model):
    _inherit = 'crm.lead'

    is_create_rent = fields.Boolean(string='Create Rent',default=False)
    rent_id = fields.Many2one('property.rent',string='Rent')
    journal_id = fields.Many2one('account.journal', string="Journal")
    installment_schedule = fields.Selection([('monthly', _('Monthly')),
                                             ('one_bill', _('One Bill')),
                                             ('quaterly', _('Quarterly')),
                                             ('six_month', _('6 - Month')),
                                             ('yearly', _('Yearly')),
                                             ('one_bill', _('One Bill(Fully Tenure)'))], string='Installment Schedule',
                                            tracking=True)
    rental_period = fields.Integer(string='Rental Period')
    security_deposit = fields.Float(string='Security Deposit')
    rent_start_date = fields.Date(string='Rental Start Date')


    def action_property_rent(self):
        """ create rent agreemnt"""
        self.partner_id.tenant = 1
        if not self.building_id:
            raise UserError(_('Add the Building '))
        if not self.unit_id:
            raise UserError(_('Add the Unit for the Building '))
        if not self.journal_id:
            raise UserError(_('Add the appropriate journal and partner accounts for rent  '))
        rent_agreement = self.env['property.rent'].create({
            'building':self.building_id.id,
            'partner_id':self.partner_id.id,
            'property_id':self.unit_id.id,
            'journal_id': self.journal_id.id,
            'account_id':self.partner_id.property_account_receivable_id.id,
            'installment_schedule': self.installment_schedule,
            'rental_period': self.rental_period,
            'security_deposit': self.security_deposit,
            'from_date':fields.Date.today(),
            'to_date':False,
            'state':'draft',
            'is_from_crm':True,
        })
        self.is_create_rent = True
        self.rent_id = rent_agreement.id


    def action_view_rent(self):
        """ show the property rent"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rent Agreement',
            'view_mode': 'form',
            'res_model': 'property.rent',
            'res_id': self.rent_id.id,
        }