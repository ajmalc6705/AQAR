# -*- coding: utf-8 -*-

import math
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class ProjectSubContract(models.Model):
    _name = 'project.sub.contract'
    _inherit = ['mail.thread']
    _description = 'Sub Contract'

    @api.onchange('date_from', 'date_to', 'invoice_schedule')
    def generate_contract_lines(self):
        for rec in self:
            for line in rec.line_ids:
                rec.update({
                    'line_ids': [(3, line.id)]
                })
            if rec.date_from and rec.date_to and rec.invoice_schedule:
                from_date = fields.Date.from_string(rec.date_from)
                to_date = fields.Date.from_string(rec.date_to)
                no_of_months = relativedelta(to_date, from_date).months + 1
                if rec.invoice_schedule == '1_time':
                    service_dates = [from_date]
                elif rec.invoice_schedule == 'monthly':
                    service_dates = [d for d in [from_date + relativedelta(months=i)
                                                 for i in range(no_of_months)]]
                elif rec.invoice_schedule == 'quarterly':
                    no_of_quarter = int(math.ceil(no_of_months / 3.0))
                    service_dates = [d for d in [from_date + relativedelta(months=i * 3)
                                                 for i in range(no_of_quarter)]]
                elif rec.invoice_schedule == 'half_yearly':
                    no_of_half_year = int(math.ceil(no_of_months / 6.0))
                    service_dates = [d for d in [from_date + relativedelta(months=i * 6)
                                                 for i in range(no_of_half_year)]]
                elif rec.invoice_schedule == 'yearly':
                    no_of_years = int(math.ceil(no_of_months / 12.0))
                    service_dates = [d for d in [from_date + relativedelta(years=i)
                                                 for i in range(no_of_years)]]
                else:
                    service_dates = [from_date]
                rec.update({
                    'line_ids': [(0, 0, {
                        'service_date': service
                    }) for service in service_dates]
                })

    name = fields.Char(string="Ref:", copy=False, default=lambda self: '/', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Sub Contractor', required=True,
                                 readonly=True, states={'draft': [('readonly', False)]})
    project_id = fields.Many2one('project.project', string='Project',
                                 required=True, readonly=True, states={'draft': [('readonly', False)]})
    date_from = fields.Date(string='From Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    date_to = fields.Date(string='To Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    invoice_schedule = fields.Selection([('monthly', 'Monthly'), ('quarterly', 'Quarterly'),
                                         ('half_yearly', 'Half Yearly'), ('yearly', 'Yearly'),
                                         ('1_time', '1 time')], string='Supply/Service Schedule',
                                        required=True, default='monthly', readonly=True,
                                        states={'draft': [('readonly', False)]})
    line_ids = fields.One2many('sub.contract.line', 'sub_contract_id', string='Contract Lines')
    contract_type = fields.Selection([('service', 'Service'), ('supply', 'Supply')],
                                     string='Sub Contract Type', readonly=True, states={'draft': [('readonly', False)]})
    contract_value = fields.Float(string='Sub Contract Value', required=True,
                                  readonly=True, states={'draft': [('readonly', False)]})
    reference = fields.Char(string='Reference', readonly=True, states={'draft': [('readonly', False)]})
    contact = fields.Char(string='Contact', readonly=True, states={'draft': [('readonly', False)]})
    phone = fields.Char(string='Phone', readonly=True, states={'draft': [('readonly', False)]})
    payment_terms = fields.Char(string='Payment Terms', readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Text(string='Description', readonly=True, states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], string='State', default='draft')

    @api.model
    def create(self, vals):
        if 'name' not in vals or vals['name'] == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('project.sub.contract') or '/'
        res = super(ProjectSubContract, self).create(vals)
        return res

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    @api.constrains('date_from', 'date_to')
    def check_date(self):
        for rec in self:
            if rec.date_to < rec.date_from:
                raise UserError(_('Please select end date greater than start date.'))


class SubContractLine(models.Model):
    _name = 'sub.contract.line'
    _description = 'Sub Contract Line'

    sub_contract_id = fields.Many2one('project.sub.contract', string='Sub Contract')
    project_id = fields.Many2one('project.project', string='Project', related='sub_contract_id.project_id')
    service_date = fields.Date(string='Date', required=True)
    is_completed = fields.Boolean(string='Completed')
    remark = fields.Char(string='Remark')
    service_doc = fields.Binary(string='Document')
    state = fields.Selection(string='State', related='sub_contract_id.state')


class ProjectContractHistory(models.Model):
    _name = 'project.contract.history'
    _description = 'Project Contract History'

    contract_id = fields.Many2one('project.project', string='Contract')
    start_date = fields.Date(string='Start Date', required=True)
    expiration_date = fields.Date(string='Expiration Date', required=True)
    history_type = fields.Selection([('beginning', 'Beginning'),
                                     ('extended', 'Extended'),
                                     ('termination', 'Termination')],
                                    string='Type')
