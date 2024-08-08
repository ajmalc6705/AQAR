# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PropertyCommunity(models.Model):
    _name = 'property.community'
    _description = 'Community Management'
    _rec_name = 'community_seq'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    community_seq = fields.Char(string='Sequence', copy=False,
                                readonly=True, help="Sequence for Community",
                                index=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Partner')
    building_id = fields.Many2one('property.building', string='Building', )
    contract_ids = fields.Many2many('aqar.contract', string='Contract', compute='_compute_contract')
    doc_date = fields.Date(string='Doc Date', copy=False)
    prospect_name = fields.Char(string='Prospect Name')
    tentative_period = fields.Integer(string='Tentative Period')
    expected_units = fields.Integer(string='Expected Units')
    total_area = fields.Float(string='Total Area')
    enquiry_no = fields.Char(string='Enquiry No', copy=False)
    enq_record_from = fields.Date(string='Enquiry Date', copy=False)
    valid_upto = fields.Date(string='Valid Upto')
    prepared_by_id = fields.Many2one('res.users', string='Prepared By', default=lambda self: self.env.user)

    state = fields.Selection([('draft', 'Draft'), ('enquiry', 'Enquiry & Estimation'), ('confirm', 'Confirmed'),
                              ('budget', 'Budgeting'), ('verify', 'Verify Budget'), ('ceo', 'CEO'),
                              ('approved', 'Approved'), ('invoice', 'Invoice'), ('cancel', 'Reject')],
                             default='draft', string="State", copy=False, tracking=True)

    unit_ids = fields.Many2many('property.property', string='Unit')
    budget_summary_line_ids = fields.One2many('budget.summary.line', 'community_id', string='Budget Summary Line')
    unit_domain_ids = fields.Many2many('property.property', 'community_id', string='Unit', compute='_compute_units', )
    is_confirmed = fields.Boolean(string='Is Confirm', default=False)
    is_budgeting = fields.Boolean(string='Is Budgeting', default=False)
    levy_id = fields.Many2many('levy.master', string='Levy', copy=False)
    notes = fields.Html(string='Description')
    documents_ids = fields.Many2many('atheer.documents', string='Documents', copy=False)
    terms_conditions = fields.Html(string='Terms & Conditions')
    community_contract_id = fields.Many2one('aqar.contract', string='Community Contract')
    contract_start_date = fields.Date(string='Contract Start Date', related='community_contract_id.start_date')
    contract_end_date = fields.Date(string='Contract End Date', related='community_contract_id.end_date')
    contract_days = fields.Integer(string='Days')
    budget_count = fields.Integer(string='Budget', compute='_compute_budget')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    payment_structure = fields.Selection([('weekly', 'Weekly'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly'),
                                          ('half_year', 'Half Yearly'), ('yearly', 'Yearly')],
                                         string="Payment Structure", copy=False, tracking=True)
    community_status = fields.Selection([('draft', 'New'), ('on_going', 'Running'), ('done', 'Completed')],
                                        compute='_compute_community_status', store=True
                                        )

    is_approved = fields.Boolean(string='Is Approved Budget', default=False, copy=False)
    is_invoiced = fields.Boolean(string='Is Invoiced', default=False, copy=False)
    is_budget_summary = fields.Boolean(string='Is Budget Summary', default=False, copy=False)
    move_ids = fields.Many2many('account.move', string='Move', copy=False)
    total_admin_fund = fields.Float(string='Total Admin Fund', copy=False)
    total_sinking_fund = fields.Float(string='Total Sinking Fund', copy=False)
    total_fund = fields.Float(string='Total Fund', copy=False)
    previous_community_ids = fields.Many2many('property.community', 'rel_previous_community_id', 'community_id',
                                              'previous_community_id', string='Previous Year Community')
    total_budget_amount = fields.Monetary(compute='_budget_total', string="Total Budget Amount", )
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
                                  string="Currency")
    prev_total_budget = fields.Float(compute='_compute_budget_total', string="Total Budget", )

    @api.depends('state')
    def _compute_community_status(self):
        for rec in self:
            if rec.state == 'draft':
                rec.write({'community_status': 'draft'})
            else:
                rec.write({'community_status': 'on_going'})

    def action_view_previous_budgets(self):
        # Collect all community IDs
        community_ids = self.previous_community_ids.ids
        # Search for budgets that match these community IDs
        budgets = self.env['community.budget'].search([('community_id', 'in', community_ids)])

        return {
            'type': 'ir.actions.act_window',
            'name': 'Previous Year Budgets',
            'view_mode': 'tree,form',
            'res_model': 'community.budget',
            'domain': [('id', 'in', budgets.ids)],
            # 'context': {'community_id': community_ids},
        }

    def _get_company_currency(self):
        for partner in self:
            if partner.company_id:
                partner.currency_id = partner.sudo().company_id.currency_id
            else:
                partner.currency_id = self.env.company.currency_id

    def _compute_budget_total(self):
        for rec in self:
            rec.prev_total_budget = 0
            community_ids = self.previous_community_ids.ids
            budget_obj =  self.env['community.budget'].search_count([('community_id', 'in', community_ids)])
            # print(budget_obj, '**********')
            rec.prev_total_budget = budget_obj


    def _budget_total(self):
        for rec in self:
            rec.total_budget_amount = 0
            budget_obj = self.env['community.budget'].search([('community_id', '=', rec.id)])
            for line in budget_obj:
                rec.total_budget_amount += line.total_gross_amount

    def action_add_summary(self):
        """ add units to summary """
        budgets_not_confirmed = self.env['community.budget'].search_count(
            [('community_id', '=', self.id), ('is_confirmed', '=', False)])
        if budgets_not_confirmed > 0:
            raise UserError(_('Confirm all budgets under this community'))
        summary_lines = []
        for rec in self.unit_ids:
            budget_summary_line = self.env['budget.summary.line'].create({
                'unit_id': rec.id,
                'community_id': self.id
            })
            summary_lines.append(budget_summary_line)
        self.update({'budget_summary_line_ids': [(6, 0, [budget_lines.id for budget_lines in summary_lines])]})
        for rec in self.budget_summary_line_ids:
            list = []
            for levy in self.levy_id:
                levy_values = self.env['budget.unit.line'].search(
                    [('unit_id', '=', rec.unit_id.id), ('levy_id', '=', levy.id)])
                admin = sum(
                    levy_values.filtered(lambda budget: budget.budget_id.community_id == self).mapped('net_amount'))
                vals = {
                    'levy': levy.sequence,
                    'levy_val': admin,
                },
                list.append(vals)
            min_dict = min(list, key=lambda x: x[0]['levy'])
            max_dict = max(list, key=lambda x: x[0]['levy'])
            rec.admin_fund = min_dict[0]['levy_val']
            rec.sinking_fund = max_dict[0]['levy_val']

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        # default['stage_id'] = self.env.ref('property_community.enq_stage').id
        default['levy_id'] = False
        default['is_approved'] = False
        default['is_invoiced'] = False
        default['is_budget_summary'] = False
        default['is_confirmed'] = False
        default['is_budgeting'] = False
        return super(PropertyCommunity, self).copy(default)

    @api.depends('community_contract_id')
    def _compute_contract(self):
        self.contract_ids = False
        for rec in self:
            contracts = self.community_contract_id.child_ids
            rec.contract_ids = contracts.mapped('id')

    @api.onchange('community_contract_id')
    def onchange_contract(self):
        if self.contract_end_date and self.contract_start_date:
            self.contract_days = (self.contract_end_date - self.contract_start_date).days + 1
        return {'domain': {'contract_ids': [('building_id', 'in', self.building_id.ids)]}}

    @api.depends('levy_id')
    def _compute_budget(self):
        self.budget_count = False
        for rec in self:
            budgets = self.env['community.budget'].search_count([('community_id', '=', rec.id)])
            rec.budget_count = budgets

    @api.depends('building_id')
    def _compute_units(self):
        self.unit_domain_ids = False
        for rec in self:
            unit_ids = self.env['property.property'].search(
                [('parent_building', '=', self.building_id.id), ('is_community', '=', True)])
            if unit_ids:
                rec.unit_ids = unit_ids
                rec.unit_domain_ids = [(6, 0, unit_ids.ids)]
            else:
                rec.unit_domain_ids = [(5, 0, 0)]
                rec.unit_ids = [(5, 0, 0)]
            # rec.unit_domain_ids = unit_ids.mapped('id')

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('community_seq', 'New') == 'New':
                vals['community_seq'] = self.env['ir.sequence'].next_by_code(
                    'community.sequence') or 'New'
            if len(vals.get('unit_ids')) == 0:
                raise ValidationError(_('Add the Units for this Building'))
        return super(PropertyCommunity, self).create(vals_list)

    def button_action_reject(self):
        for rec in self:
            rec.write({'state': 'cancel'})

    def button_action_set_to_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})
            rec.is_approved = False
            rec.is_invoiced = False
            rec.is_budget_summary = False
            rec.is_confirmed = False
            rec.is_budgeting = False

    def action_send_authorizer(self):
        """ get action confirm"""
        for rec in self:
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'property.community')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            rec.write({'state': 'enquiry'})

    def action_confirm(self):
        """ get action confirm"""
        for rec in self:
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'property.community')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            rec.write({'state': 'confirm'})
            rec.is_confirmed = True

    def action_budget(self):
        """ get action budgeting"""
        for rec in self.levy_id:
            for levy in rec.sub_levy_ids:
                budget = self.env['community.budget'].create({
                    'doc_date': self.doc_date,
                    'partner_id': self.partner_id.id,
                    'building_id': self.building_id.id,
                    'levy_id': levy.levy_id.id,
                    'community_id': self.id,
                    'sub_levy_name': levy.sub_levy_name,
                    'sub_levy_id': levy.id,
                    'sub_levy_account_id': levy.sub_levy_account_id.id,
                    'period_start': self.community_contract_id.start_date,
                    'period_end': self.community_contract_id.end_date,
                    'budget_lines': [
                        (0, 0, {
                            'unit_id': val.id,
                            'from_date': self.contract_start_date,
                            'to_date': self.contract_end_date,

                        }) for val in self.unit_ids
                    ]
                })

        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'property.community')]).id
        # Remove Old Activities related to the current record
        self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id),
        ]).unlink()
        self.write({'state': 'budget'})
        #
        self.is_budgeting = True
        return {
            'type': 'ir.actions.act_window',
            'name': 'Community Budget',
            'view_mode': 'tree,form',
            'res_model': 'community.budget',
            'domain': [('community_id', '=', self.id)],
        }

    def action_show_budget(self):
        """ show the budget"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Community Budget',
            'view_mode': 'tree,form',
            'res_model': 'community.budget',
            'domain': [('community_id', '=', self.id)],
        }

    def button_action_send_cm(self):
        for rec in self:
            budgets_not_confirmed = self.env['community.budget'].search_count(
                [('community_id', '=', self.id), ('is_confirmed', '=', False)])
            if budgets_not_confirmed > 0:
                raise UserError(_('Confirm all budgets under this community'))
            if not rec.budget_summary_line_ids:
                raise UserError(_('Budget Summary Line is empty Please Click Get Budget Summary Button'))
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'property.community')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', self.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()

            rec.write({'state': 'verify'})

    def action_verify_budget(self):
        for rec in self:
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'property.community')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', self.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()

            rec.write({'state': 'ceo'})

    def action_approve_budget(self):
        """ action for approve budget"""
        budgets_not_confirmed = self.env['community.budget'].search_count(
            [('community_id', '=', self.id), ('is_confirmed', '=', False)])
        if budgets_not_confirmed > 0:
            raise UserError(_('Confirm all budgets under this community'))
        self.write({'state': 'approved'})
        self.is_approved = True

    def button_action_send_back(self):
        for rec in self:
            state_map = {
                'ceo': 'verify',
                'verify': 'budget',
                'budget': 'confirm',
                'confirm': 'enquiry',
                'enquiry': 'draft',
            }

            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'property.community')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()

            new_state = state_map.get(rec.state)
            if new_state:
                rec.state = new_state

    def action_show_invoices(self):
        """ show the budget Invoice"""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id('account.action_move_out_invoice_type')
        ctx = dict(self.env.context)
        ctx.update({'create': False, 'default_move_type': 'out_invoice'})
        views = self.env.ref('account.view_invoice_tree')
        action['context'] = ctx
        action.update({
            'domain': [('id', 'in', self.move_ids.ids)],
            'views': [(views.id, 'tree'), (False, 'form'), (False, 'kanban')]

        })
        return action

    def action_community_invoice(self):
        journal_id = False
        action = self.env.ref('property_community.action_community_invoice').read()[0]
        journal = self.env['ir.config_parameter'].sudo().get_param('property_community.community_journal_id')
        if journal:
            journal_id = self.env['account.journal'].browse(int(journal)).id
        if action:
            units = self.unit_ids.ids
            action['context'] = {
                'default_unit_ids': units,
                'default_journal_id': journal_id,
                'default_company_id': self.company_id.id
            }
        return action


class BudgetSummaryLine(models.Model):
    _name = 'budget.summary.line'
    _rec_name = 'community_id'
    _description = 'Budget Summary line'

    community_id = fields.Many2one('property.community', string='Community')
    building_id = fields.Many2one('property.building', string='Building', related='community_id.building_id')
    unit_id = fields.Many2one('property.property', string='Unit')
    municipality_no = fields.Char(related="unit_id.muncipality_no", string='Municipality No')
    admin_fund = fields.Float(string='Admin Fund', digits='Product Price')
    sinking_fund = fields.Float(string='Sinking Fund', digits='Product Price')
    invoiced_fund = fields.Float(string='Invoiced Fund', digits='Product Price')
    total_fund = fields.Float(string='Total Fund', compute='_compute_fund', digits='Product Price')
    outstanding_fund = fields.Float(string='Outstanding Fund', compute='_compute_fund')
    unit_admin_fund = fields.Float(string='Unit Admin Fund')
    unit_sinking_fund = fields.Float(string='Unit Sinking Fund')
    move_ids = fields.Many2many('account.move', 'rel_move_id_summary_line_id', 'move_id', 'summary_id', string='Move',
                                related="community_id.move_ids", copy=False
                                )

    @api.depends('unit_id', 'community_id', 'invoiced_fund')
    def _compute_fund(self):
        self.total_fund = False
        self.outstanding_fund = False
        self.invoiced_fund = False
        self.unit_admin_fund = False
        self.unit_sinking_fund = False
        admin_fund = 0
        for rec in self:
            rec.total_fund = rec.admin_fund + rec.sinking_fund
            rec.outstanding_fund = sum(
                rec.community_id.move_ids.filtered(lambda budget: budget.property_id == rec.unit_id).mapped(
                    'amount_residual'))
            rec.invoiced_fund = sum(
                rec.community_id.move_ids.filtered(lambda budget: budget.property_id == rec.unit_id).mapped(
                    "amount_total"))
            days = self.community_id.contract_days
            if days != 0:
                rec.unit_admin_fund = rec.admin_fund / days
                rec.unit_sinking_fund = rec.sinking_fund / days
        self.community_id.total_admin_fund = sum(self.mapped('admin_fund'))
        self.community_id.total_sinking_fund = sum(self.mapped('sinking_fund'))
        self.community_id.total_fund = sum(self.mapped('total_fund'))

    def action_view_invoices(self):
        """ show the budget"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Budget Summary Invoices',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('community_id', '=', self.community_id.id), ('property_id', '=', self.unit_id.id)],
        }


class PropertyProperty(models.Model):
    _inherit = 'property.property'

    community_id = fields.Many2one('property.community', string='Community')
    is_community = fields.Boolean(string='For Community', default=False)
    community_landlord_id = fields.Many2one('res.partner', string='Community Owner')


class AccountAccountInheritCommunity(models.Model):
    _inherit = 'account.account'

    is_admin_fund = fields.Boolean(string='Is for Admin Fund', default=False)
    is_sinking_fund = fields.Boolean(string='Is for Sinking Fund', default=False)


class AccountMoveInheritCommunity(models.Model):
    _inherit = 'account.move'

    community_id = fields.Many2one('property.community', string='Community ID')
    community_start_date = fields.Date(string='Community Start Date')
    community_end_date = fields.Date(string='Community End Date')


class AccountMoveLineInheritCommunity(models.Model):
    _inherit = 'account.move.line'

    community_id = fields.Many2one('property.community', string='Community ID')
    community_start_date = fields.Date(string='Community Start Date')
    community_end_date = fields.Date(string='Community End Date')
