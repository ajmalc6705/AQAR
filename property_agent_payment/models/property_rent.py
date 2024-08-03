# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError


class PropertyRent(models.Model):
    _inherit = 'property.rent'

    is_agent_payment = fields.Boolean(string='Is Agent Payment', copy=False)
    total_amount = fields.Float(string='Total Amount', help="amounts calculated as per sales or lease or service")
    commission_percent = fields.Float(string='Commission %')
    commission_amount = fields.Float(string='Commission Amount', help="Commission percentage of total amount")
    agent_payment_count = fields.Integer(string='Payment Count', compute='_compute_agent_payment')
    agent_rent_created = fields.Boolean(compute='compute_agent_rent_created', compute_sudo=True, store=True)
    agent_payment_ids = fields.One2many('agent.payment', 'property_lease_id')

    @api.depends('agent_payment_ids')
    def compute_agent_rent_created(self):
        for rec in self:
            agent_rent_created = False
            if rec.agent_payment_ids:
                agent_rent_created = True
            rec.agent_rent_created = agent_rent_created

    def _compute_agent_payment(self):
        """ count of agent payments"""
        self.agent_payment_count = False
        for rec in self:
            agent_payments = self.env['agent.payment'].search_count([('property_lease_id', '=', self.id)])
            rec.agent_payment_count = agent_payments

    @api.onchange('total_amount', 'commission_percent')
    def onchange_total(self):
        self.commission_amount = self.total_amount * self.commission_percent

    def action_show_agent_payment(self):
        """ action to show bill"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agent Payment',
            'view_mode': 'tree,form',
            'res_model': 'agent.payment',
            'domain': [('property_lease_id', '=', self.id)],
        }

    def action_create_agent_payment(self):
        """ create agent payment"""
        for rec in self:
            if rec.rent_total <= 0:
                raise ValidationError(_('Thw Total amount should be greater than Zero.!'))
            agent_payment = self.env['agent.payment'].create({
                'partner_id': rec.partner_id.id,
                'building_id': rec.building.id,
                'unit_id': rec.property_id.id,
                'agent_service_type': 'property_lease',
                'total_amount': rec.rent_total,
                # 'commission_percent': self.commission_percent,
                # 'commission_amount': self.commission_amount,
                'property_lease_id': self.id,
            })
        self.is_agent_payment = True
