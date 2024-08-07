# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class CommunityBudget(models.Model):
    _name = 'community.budget'
    _description = 'Budget Community'
    _rec_name = 'budget_seq'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    budget_seq = fields.Char(string='Sequence', copy=False,
                             readonly=True, help="Sequence for Budget",
                             index=True, default=lambda self: _('New'))
    doc_date = fields.Date(string='Doc date')
    partner_id = fields.Many2one('res.partner', string='Partner')
    building_id = fields.Many2one('property.building', string='Building')
    levy_id = fields.Many2one('levy.master', string='Levy')
    community_id = fields.Many2one('property.community', string='Community')
    total_area = fields.Float(string='Total Builtup Area', compute='_compute_area', store=True, digits='Product Price')
    sub_levy_name = fields.Char(string='Sub Levy Name')
    sub_levy_account_id = fields.Many2one('account.account', string='Sub Levy A/C')
    sub_levy_id = fields.Many2one('sub.levy.line', string='Sub Levy Name')
    period_start = fields.Date(string='Contract Period')
    period_end = fields.Date(string='Contract Period')
    actual_units = fields.Integer(string='Actual Units', compute='_compute_unit_count', readonly=False)
    excluded_units = fields.Integer(string='Excluded Units', compute='_compute_exclude_units')
    budget_units = fields.Integer(string='Budget Units', compute='_compute_unit_count')
    stage_id = fields.Many2one('budget.stages', string='Stage',
                               default=lambda self: self.env.ref('property_community.draft_stage'))
    budget_lines = fields.One2many('budget.unit.line', 'budget_id', string='Budget Line')
    total_amount = fields.Float(string='Total Amount', compute='_compute_amount', digits='Product Price')
    budget_amount = fields.Float(string='Budget Amount', digits='Product Price')
    type = fields.Selection([('equal', 'Split Equally'), ('split_per_area', 'Split As Per Area')], string='Type')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    total_net_amount = fields.Float(string='Total Net Amount', compute='_compute_total', digits='Product Price')
    total_disc_amount = fields.Float(string='Total Disc Amount', compute='_compute_total', digits='Product Price')
    total_gross_amount = fields.Float(string='Total Gross Amount', compute='_compute_total', digits='Product Price',
                                      store=True)
    is_confirmed = fields.Boolean(string='Confirmed', default=False)
    total_expenses = fields.Float(string='Total expense', digits='Product Price', compute='_compute_total_expenses',
                                  compute_sudo=True, store=True, copy=False)

    #

    def action_confirm(self):
        for rec in self:
            if not rec.type:
                raise ValidationError(_('The Type is missing Please Select the Type'))
            if not rec.budget_amount > 0:
                raise ValidationError(_('The Budget Amount Should Be Greater Than Zero !'))
            if not rec.total_gross_amount > 0:
                raise ValidationError(_('The Total Gross Amount Should Be Greater Than Zero !'))
            rec.stage_id = self.env.ref('property_community.confirm_budget_stage').id
            rec.is_confirmed = True

    @api.depends('budget_lines.rate_unit', 'budget_lines.net_amount', 'budget_lines.disc_amount')
    def _compute_total(self):
        self.total_net_amount = self.total_disc_amount = self.total_gross_amount = 0
        for rec in self:
            rec.total_gross_amount = sum(rec.budget_lines.mapped('rate_unit'))
            rec.total_disc_amount = sum(rec.budget_lines.mapped('disc_amount'))
            rec.total_net_amount = sum(rec.budget_lines.mapped('net_amount'))

    @api.depends('period_start', 'period_end', 'sub_levy_account_id')
    def _compute_total_expenses(self):
        for rec in self:
            rec.total_expenses = 0
            if rec.period_start and rec.period_end and rec.sub_levy_account_id:
                account_lines = self.env['account.move.line'].search([('account_id', '=', rec.sub_levy_account_id.id),
                                                                      ('date', '>=', rec.period_start),
                                                                      ('date', '<=', rec.period_end),
                                                                      ('parent_state', '=', 'posted'),
                                                                      ])
                rec.total_expenses = sum(line.debit for line in account_lines) - sum(
                    line.credit for line in account_lines)

    def action_view_account_move_line_select(self):
        """ show the budget"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Items',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'domain': [('account_id', '=', self.sub_levy_account_id.id),
                       ('date', '>=', self.period_start),
                       ('date', '<=', self.period_end),
                       ('parent_state', '=', 'posted'), ],
        }

    @api.onchange('period_start', 'period_end')
    def change_date(self):
        for rec in self.budget_lines:
            rec.from_date = self.period_start
            rec.to_date = self.period_end

    @api.depends('budget_lines.net_amount')
    def _compute_amount(self):
        self.total_amount = 0
        for rec in self:
            rec.total_amount = sum(rec.budget_lines.mapped('net_amount'))

    def _compute_unit_count(self):
        for rec in self:
            rec.budget_units = len(self.budget_lines.filtered(lambda budget: budget.exclude_compute == False))
            units = self.env['property.property'].search_count(
                [('parent_building', '=', rec.building_id.id), ('for_parking', '!=', True)])
            rec.actual_units = units

    def _compute_exclude_units(self):
        self.excluded_units = self.actual_units - self.budget_units

    @api.depends('budget_lines.unit_area')
    def _compute_area(self):
        self.total_area = False
        for rec in self:
            # rec.total_area = sum(rec.budget_lines.mapped('unit_area'))
            rec.total_area = sum(line.unit_area for line in rec.budget_lines if not line.unit_id.for_parking)

    def action_compute(self):
        """ compute the rate/area"""
        unit_rate = 0
        if not self.type:
            raise ValidationError(_('Please select the Type'))
        if self.type == 'equal':
            if self.budget_units != 0:
                unit_rate = self.budget_amount / self.budget_units
            for rec in self.budget_lines.filtered(lambda budget: budget.exclude_compute == False):
                rec.rate_unit = unit_rate
        elif self.type == 'split_per_area':
            if self.total_area != 0:
                unit_rate = self.budget_amount / self.total_area
            for rec in self.budget_lines.filtered(lambda budget: budget.exclude_compute == False):
                rec.rate_unit = unit_rate * rec.unit_area

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('budget_seq', 'New') == 'New':
                vals['budget_seq'] = self.env['ir.sequence'].next_by_code(
                    'budget.sequence') or 'New'
        return super(CommunityBudget, self).create(vals_list)

    def get_not_added_units(self):
        # Get all units in the community
        for rec in self:
            community_units = rec.community_id.unit_ids
            # Get units already added in budget_lines
            line_units = rec.budget_lines.mapped('unit_id')
            # Find units not yet added
            not_added_units = community_units - line_units
            return not_added_units


class BudgetUnitLine(models.Model):
    _name = 'budget.unit.line'
    _rec_name = 'unit_id'
    _description = 'Budget unit line'

    unit_id = fields.Many2one('property.property', string='Unit')
    unit_ids = fields.Many2many('property.property', string='Unit', compute='compute_unit')
    landlord_id = fields.Many2one('res.partner', string='Owner', related='unit_id.community_landlord_id',
                                  domain=[('is_community_owner', '=', True)])
    budget_id = fields.Many2one('community.budget', string='Budget')
    levy_id = fields.Many2one('levy.master', string='Levy', related='budget_id.levy_id')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    unit_area = fields.Float(string='Total Area (sqm)', related='unit_id.mulkiya_area')
    rate_unit = fields.Float(string='Rate/Unit')
    due_date = fields.Date(string='Due Date')
    net_amount = fields.Float(string='Net Amount', compute='_compute_net_amount', readonly=False,
                              digits='Product Price')
    disc_amount = fields.Float(string='Disc Amount', digits='Product Price')
    exclude_compute = fields.Boolean(string='Exclude', default=False)

    @api.depends('disc_amount', 'rate_unit')
    def _compute_net_amount(self):
        self.net_amount = False
        for rec in self.filtered(lambda budget: budget.exclude_compute == False):
            rec.net_amount = rec.rate_unit - rec.disc_amount

    @api.depends('budget_id.community_id.unit_ids')
    def compute_unit(self):
        self.unit_ids = False
        for rec in self:
            community = rec.budget_id.community_id
            rec.unit_ids = community.unit_ids.ids

    @api.onchange('unit_id')
    def onchange_unit_id(self):
        for rec in self:
            if rec.budget_id:
                line_unit = rec.budget_id.get_not_added_units()
                if rec.unit_ids.ids not in line_unit.ids:
                    return {'domain': {'unit_id': [('id', '=', line_unit.ids)]}}
                else:
                    return {'domain': {'unit_id': [('id', 'in', [rec.unit_id.id])]}}


class BudgetStages(models.Model):
    _name = 'budget.stages'
    _rec_name = 'name'
    _description = 'Budget stages'

    name = fields.Char(string='Stage')
