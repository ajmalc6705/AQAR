# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertyService(models.Model):
    _inherit = 'parking.reservation'

    is_agent_payment = fields.Boolean(string='Is Agent Payment', copy=False)
    agent_payment_count = fields.Integer(string='Payment Count', compute='_compute_agent_payment')
    parking_agent_payment_created = fields.Boolean(compute='compute_agent_payment_created', compute_sudo=True, store=True)
    agent_payment_ids = fields.One2many('agent.payment', 'property_parking_id')

    @api.depends('agent_payment_ids')
    def compute_agent_payment_created(self):
        for rec in self:
            parking_agent_payment_created = False
            if rec.agent_payment_ids:
                parking_agent_payment_created = True
            rec.parking_agent_payment_created = parking_agent_payment_created

    def _compute_agent_payment(self):
        """ count of agent payments"""
        self.agent_payment_count = False
        for rec in self:
            agent_payments = self.env['agent.payment'].search_count([('property_parking_id', '=', self.id)])
            rec.agent_payment_count = agent_payments

    def action_show_agent_payment(self):
        """ action to show bill"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agent Payment',
            'view_mode': 'tree,form',
            'res_model': 'agent.payment',
            'domain': [('property_parking_id', '=', self.id)],
        }

    def action_button_create_agent_payment(self):
        """ create agent payment"""
        agent_payment = self.env['agent.payment'].create({
            'partner_id': self.partner_id.id,
            'building_id': self.building_id.id,
            'agent_service_type': 'property_parking',
            'total_amount': self.amount_untaxed,
            'property_parking_id': self.id,
        })
        self.is_agent_payment = True
