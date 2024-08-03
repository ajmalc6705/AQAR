# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class settlementDone(models.TransientModel):
    _name = 'settlement.done'
    _description = 'Settlement Done'

    legal_action_id = fields.Many2one('dispute.legal.action', 'Legal Action', required=True)
    remarks = fields.Text('Remarks')

    def send_mail(self):
        self.legal_action_id.state = 'settlement_done'
        self.legal_action_id.settlement_remarks = self.remarks


class DisputeLegalAction(models.Model):
    _name = 'dispute.legal.action'
    _rec_name = 'sequence'
    _check_company_auto = True
    _description = 'Legal Action'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Char(string='Sequence', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Tenant', required=True, related="rent_id.partner_id")
    rent_id = fields.Many2one(comodel_name='property.rent', string='Rent', tracking=True, check_company=True)
    building_id = fields.Many2one('property.building', 'Building', store=True, related="rent_id.building",
                                  readonly=False)
    building_area_id = fields.Many2one('building.area', 'Building Area', related="building_id.building_area",
                                       readonly=False)
    property_id = fields.Many2one(comodel_name='property.property', string='Unit', store=True,
                                  related="rent_id.property_id", readonly=False)
    unit_ids = fields.Many2many('property.property', string="Unit Ids", compute='_compute_unit_ids')
    lease_from_date = fields.Date(string='Lease Start', related="rent_id.from_date")
    lease_to_date = fields.Date(string='Lease End', related="rent_id.to_date")
    period = fields.Integer(string='Rental Period', related="rent_id.period")
    installment_schedule = fields.Selection(related="rent_id.installment_schedule", string='Installment Schedule',
                                            tracking=True)
    response_date = fields.Date('Tenant Response Date', tracking=True)
    hearing_date = fields.Date('Court Hearing Date', tracking=True)
    verdict_date = fields.Date('Court Verdict Date', tracking=True)
    agreed_rent_amount = fields.Float(string='Agreed Rent Amount', related='rent_id.agreed_rent_amount')
    bounced_cheque_ids = fields.One2many('property.bounced.cheque', 'dispute_legal_id', 'Bounced Cheques')
    doc_ids = fields.Many2many('atheer.documents',
                               string='Documents')
    state = fields.Selection([('draft', 'Draft'),
                              ('waiting', 'Pending Approval'),
                              ('approved', 'Approved'),
                              ('settlement_done', 'Settlement Done'),
                              ('refused', 'Rejected')], tracking=True, default='draft')
    settlement_remarks = fields.Text('Settlement Remarks')
    send_back_flag = fields.Boolean(default=False)
    notes = fields.Text("Description")
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)

    @api.depends('building_id')
    def _compute_unit_ids(self):
        """ dynamic domain for unit"""
        self.unit_ids = False
        for rec in self:
            unit = self.env['property.property'].search(
                [('parent_building', '=', rec.building_id.id)])
            rec.unit_ids = unit.mapped('id')

    def open_tasks(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tasks',
            'view_mode': 'tree,form',
            'res_model': 'project.task',
            'domain': [('legal_action_id', '=', self.id)],
            'context': {
                'default_project_id': self.env.ref('property_lease_management.legal_action_id').id,
                'default_legal_action_id': self.id,
            }
        }

    @api.model
    def create(self, vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('legal.action') or _('Legal Action')
        return super(DisputeLegalAction, self).create(vals)

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(DisputeLegalAction, self).unlink()

    def settlement_done(self):
        return {
            'name': _("Settlement Done"),
            'view_mode': 'form',
            # 'view_id': self.env.ref('amlak_property_management.send_email_document_view_form').id,
            'view_type': 'form',
            'tag': 'reload',
            'res_model': 'settlement.done',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'stay_open': True,
            'domain': '[]',
            'context': {
                'default_legal_action_id': self.id,
            }
        }

    def send_to_property_head(self):
        """ send to property head """
        for rec in self:
            rec.write({'state': 'waiting'})
            # rec.notification = True
            # rec.requested_date = fields.date.today()

    def send_to_senior(self):
        """ sending to senior property head """
        for rec in self:
            rec.write({'state': 'approved'})

    def button_action_send_back(self):
        for rec in self:
            state_map = {
                'approved': 'waiting',
                'waiting': 'draft',
            }
            new_state = state_map.get(rec.state)
            if new_state:
                rec.state = new_state

    def button_action_cancel(self):
        for rec in self:
            rec.write({'state': 'waiting'})


class ProjectTask(models.Model):
    _inherit = 'project.task'

    legal_action_id = fields.Many2one('dispute.legal.action')
