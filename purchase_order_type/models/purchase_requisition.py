# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

PURCHASE_REQUISITION_STATES = [('draft', 'Draft'), ('authorizer', 'Authorizer'), ('ongoing', 'Checked'),
                               ('verified', 'Verified'),
                               ('confirm', 'Confirmed'), ('in_progress', 'Approved'), ('open', 'Bid Selection'),
                               ('done', 'Closed'), ('cancel', 'Cancelled')
                               ]


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"
    #
    # ordering_date = fields.Date(string="Ordering Date", tracking=True, default=fields.Date.today())
    project_id = fields.Many2one('project.project', string='Project', domain=[('is_assignment', '=', False)])
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    requested_by = fields.Many2one('requested.by', string="Requested By")
    state = fields.Selection(PURCHASE_REQUISITION_STATES, string='Status', tracking=True, required=True,
                             copy=False, default='draft')
    state_blanket_order = fields.Selection(PURCHASE_REQUISITION_STATES, compute='_set_state')

    is_vehicle_requisition = fields.Boolean('Is related to Vehicle', default=False)

    @api.onchange('type_id')
    def onchange_type_id(self):
        for rec in self:
            if rec.type_id:
                rec.is_vehicle_requisition = rec.type_id.is_vehicle_requisition

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order') or 'New'
        return super(PurchaseRequisition, self).create(vals)

    #
    def action_draft(self):
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.requisition')]).id
        # Remove Old Activities related to the current record
        self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id),
        ]).unlink()
        return super(PurchaseRequisition, self).action_draft()

    def update_approve_status_one(self):
        for rec in self:
            """SEND TO AUTHORIZER"""
            rec.write({'state': 'authorizer'})
            # rec.write({'state': 'ongoing'})

    def button_action_send_ongoing(self):
        for rec in self:
            """SEND TO AUTHORIZER"""
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.requisition')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', self.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            # rec.write({'state': 'authorizer'})
            rec.write({'state': 'ongoing'})

    def update_approve_status_two(self):
        for rec in self:
            """state From Checked to VERIFY state"""
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.requisition')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()

            rec.write({'state': 'verified'})

    def update_approve_status_three(self):
        for rec in self:
            """state From VERIFY to confirm state"""
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.requisition')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()

            rec.write({'state': 'confirm'})
            # rec.approval_status_3 = True

    def action_button_send_back(self):
        for rec in self:
            state_map = {
                'in_progress': 'confirm',
                'confirm': 'verified',
                'verified': 'ongoing',
                'ongoing': 'authorizer',
                'authorizer': 'draft',
            }
            for rec in self:
                res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.requisition')]).id
                # Remove Old Activities related to the current record
                self.env['mail.activity'].search([
                    ('res_id', '=', rec.id),
                    ('res_model_id', '=', res_model_id),
                ]).unlink()

                new_state = state_map.get(rec.state)
                if new_state:
                    rec.state = new_state

    def action_in_progress(self):
        for rec in self:
            res = super().action_in_progress()
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'purchase.requisition')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            return res


#
class RequestedBy(models.Model):
    _name = "requested.by"
    _description = "Requested By"
    _rec_name = 'name'

    name = fields.Char('Name')


class PurchaseRequisitionType(models.Model):
    _inherit = "purchase.requisition.type"

    is_vehicle_requisition = fields.Boolean('Is related to Vehicle', default=False)
