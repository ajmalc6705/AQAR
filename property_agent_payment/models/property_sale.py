# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertySale(models.Model):
    _inherit = 'property.sale'

    is_agent_payment = fields.Boolean(string='Is Agent Payment', copy=False)
    total_amount = fields.Float(string='Total Amount', help="amounts calculated as per sales or lease or service", digits=(12,3))
    commission_percent = fields.Float(string='Commission %', )
    commission_amount = fields.Float(string='Commission Amount', help="Commission percentage of total amount",digits=(12,3))
    agent_payment_count = fields.Integer(string='Payment Count', compute='_compute_agent_payment', digits=(12,3))
    agent_sale_created = fields.Boolean(compute='compute_agent_sale_created', compute_sudo=True, store=True)
    agent_payment_ids = fields.One2many('agent.payment', 'property_sale_id')

    @api.depends('agent_payment_ids')
    def compute_agent_sale_created(self):
        for rec in self:
            agent_sale_created = False
            if rec.agent_payment_ids:
                agent_sale_created = True
            rec.agent_sale_created = agent_sale_created

    def _compute_agent_payment(self):
        """ count of agent payments"""
        self.agent_payment_count = False
        for rec in self:
            agent_payments = self.env['agent.payment'].search_count([('property_sale_id', '=', self.id)])
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
            'domain': [('property_sale_id', '=', self.id)],
        }


    def action_create_agent_payment(self):
        """ create agent payment"""
        agent_payment = self.env['agent.payment'].create({
            'partner_id':self.partner_id.id,
            'building_id':self.building_id.id,
            'unit_id': self.unit_id.id,
            'agent_service_type':'property_sale',
            'total_amount':self.total_amount,
            'commission_percent': self.commission_percent,
            'commission_amount': self.commission_amount,
            'property_sale_id':self.id,
        })
        self.is_agent_payment = True