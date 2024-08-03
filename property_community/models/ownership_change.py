# -*- coding: utf-8 -*-

from odoo import models,fields,api

class OwnershipChange(models.Model):
    _name = 'ownership.change'
    _description='Ownership Change'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'unit_id'

    building_id = fields.Many2one('property.building',string='Building')
    unit_id = fields.Many2one('property.property', string='Unit')
    unit_ids = fields.Many2many('property.property', string="Unit Ids", compute='_compute_unit_ids')
    date = fields.Date(string='Date', default=fields.Date.today, copy=False)
    owner_id = fields.Many2one('res.partner',string='Community Owner')
    new_owner_id = fields.Many2one('res.partner',string='New Community Owner')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('cancel', 'Canceled'),
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string="Company", help='company',
                                 default=lambda self: self.env.company)


    def action_reset_draft(self):
        """reset the state to draft"""
        self.state = 'draft'

    def action_confirm(self):
        self.unit_id.community_landlord_id = self.new_owner_id.id
        self.state = 'confirm'

    @api.onchange('unit_id')
    def _onchange_unit(self):
        self.owner_id = self.unit_id.community_landlord_id.id

    @api.depends('building_id')
    def _compute_unit_ids(self):
        """ dynamic domain for unit"""
        self.unit_ids = False
        for rec in self:
            unit = self.env['property.property'].search(
                [('parent_building', '=', rec.building_id.id)])
            rec.unit_ids = unit.mapped('id')