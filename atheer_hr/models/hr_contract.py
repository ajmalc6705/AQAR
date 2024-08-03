# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class HrContract(models.Model):
    _name = 'hr.contract'
    _description = "Hr Contract"
    _inherit = ['hr.contract', 'mail.thread']

    name = fields.Char('Contract Reference', compute='_compute_reference', store=True, readonly=True, required=False)
    probation_days = fields.Char(string="Probation Period")
    first_contract_date = fields.Date(string="First Contract Date ", related='employee_id.joining_date')
    worked_days = fields.Float()
    total_days = fields.Float()
    basic_salary = fields.Float()
    loan_amount = fields.Float(string="Loan Amount", copy=False)
    loan_addition_amount = fields.Float(string="Loan Addition Amount", copy=False)
    loan_deduction_amount = fields.Float(string="Loan Deduction Amount", copy=False)
    bonus_amount = fields.Float(string="Bonus Amount", copy=False)
    ot_amount = fields.Float(string="OT Amount", copy=False)

    def _create(self, vals_list):
        res = super(HrContract, self)._create(vals_list)
        if res.employee_id:
            res.name = 'Contract for ' + str(res.employee_id.name)
        else:
            res.name = 'Contract for ' + str(res.employee_id.name)
        return res

    @api.depends('employee_id')
    def _compute_reference(self):
        for rec in self:
            if rec.employee_id:
                rec.name = 'Contract for ' + str(rec.employee_id.name)
            if not rec.employee_id:
                rec.name = 'Contract'

    def basic_inc(self):
        if self.employee_id.is_omani == 'omani':
            type = self.env['salary.package.type'].search([('name', '=', 'Basic')])
            self.salary_increment.create(
                {'ttype': type and type.id, 'hr_contract': self.id, 'employee_id': self.employee_id.id,
                 'inc_date': fields.date.today(),
                 'basic': self.wage, 'amount_inc': self.wage * .03, 'new_basic': self.wage + (self.wage * .03)})
        else:
            raise UserError('Applicable Only to Oman Citizens')

    @api.depends('wage', 'hra', 'ta', 'other_allowance', 'food_allowance')
    def total_salary(self):
        for rec in self:
            rec.total_salary = rec.wage + rec.hra + rec.ta + rec.other_allowance + rec.food_allowance

    hra = fields.Float(string='HRA', digits=(16, 3))
    ta = fields.Float(string='TA', digits=(16, 3))
    other_allowance = fields.Float(string='Other Allowance', digits=(16, 3))
    food_allowance = fields.Float(string='Food Allowance', digits=(16, 3))
    total_salary = fields.Float(string='Total Salary', help="Sum of Basic, HRA, TA and Other Allowance",
                                compute=total_salary, store=True, digits=(16, 3))
    hours_per_day = fields.Float('Working Hours Per Day')
    calc_hours = fields.Float('Salary Hour Rate Calculation Hours', digits=(16, 3))
    dummy = fields.Float(string='Dummy', copy=False, default=0)
    active_contract = fields.Boolean('Active ', help='Set this as the active contract for given employee', default=True)
    salary_increment = fields.One2many('hr.salary.increment', 'hr_contract', 'Salary Increment Details')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    trial_date_start = fields.Date(string='Probation Start Date', copy=False)
    trial_date_end = fields.Date(string='Probation End Date', copy=False)
    salary_package_ids = fields.One2many('salary.packages', 'contract_id')
    salary_structure_id = fields.Many2one('hr.payroll.structure')
    increment = fields.Boolean(default=False)
    gross_salary = fields.Float(string="Gross Salary", compute='_compute_gross_salary')
    wage = fields.Monetary('Wage', tracking=True, help="Employee's monthly gross wage.",
                           compute='_compute_gross_salary')

    @api.depends('salary_package_ids')
    def _compute_gross_salary(self):
        for rec in self:
            result = 0
            wage = 0
            for line in rec.salary_package_ids:
                result += line.amount_per_month
                if line.component.name == 'Basic':
                    wage += line.amount_per_month
            rec.gross_salary = result
            rec.wage = wage

    # @api.model
    # def create(self, vals):
    #     vals['dummy'] = 1
    #     res = super(HrContract, self).create(vals)
    #     if res.active_contract:
    #         other_contracts = self.env['hr.contract'].search(
    #             [('employee_id', '=', vals['employee_id']), ('active_contract', '=', True)])
    #         for i in other_contracts:
    #             if i.id != res.id:
    #                 i.write({'active_contract': False})
    #         res.employee_id.write({'active_contract_id': res.id})
    #     return res

    @api.model
    def update_state(self):
        return True

    @api.model
    def create_probation_record(self):
        contracts = self.sudo().env['hr.contract'].search([])
        for contract in contracts:
            if contract.trial_date_start and contract.trial_date_end:
                if self.sudo().env['hr.probation.eval'].search([('employee_id', '=', contract.employee_id.id)]):
                    continue
                self.sudo().env['hr.probation.eval'].create({'employee_id': contract.employee_id.id,
                                                             'date_from': contract.trial_date_start,
                                                             'date_to': contract.trial_date_end,
                                                             'state': 'confirm'})


class SalaryIncrement(models.Model):
    _name = 'hr.salary.increment'
    _description = "Salary Increment"

    @api.onchange('ttype')
    def onchange_type(self):
        if self.ttype:
            amount = self.hr_contract.salary_package_ids.filtered(lambda rec: rec.component == self.ttype).mapped('amount_per_month')
            if amount:
                self.basic = amount and amount[0]
            else:
                raise UserError("Selected Package is not enabled for this contract.")

    @api.onchange('amount_inc')
    def total_amount(self):
        basic = self.basic
        amount_inc = self.amount_inc
        self.new_basic = basic + amount_inc

    def write(self, vals):
        """
        :param vals:
        :return:
        """
        raise UserError('Updation Not Allowed. Instead Create new line.')

    @api.model
    def create(self, vals):
        """
        :param vals:
        :return:
        """
        record = super(SalaryIncrement, self).create(vals)
        basic = record.basic
        amount_inc = record.amount_inc
        active_contract = record.hr_contract
        if active_contract and "amount_inc" in vals:
            package_id = active_contract.salary_package_ids.filtered(lambda rec: rec.component == record.ttype)
            if package_id:
                package_id.amount_per_month = basic + amount_inc
            else:
                pass
        return record

    hr_contract = fields.Many2one('hr.contract')
    employee_id = fields.Many2one('hr.employee', 'Employee ID/Name')
    type = fields.Selection(
        [('basic', 'Basic'), ('hra', 'HRA'), ('ta', 'TA'), ('food', 'Food Allowance'), ('other', 'Other Allowance')],
        string="Type")
    ttype = fields.Many2one(comodel_name='salary.package.type', string='Type')
    inc_date = fields.Date('Date')
    basic = fields.Float('Amount', digits=(16, 3))
    amount_inc = fields.Float('Increment Amount', digits=(16, 3))
    new_basic = fields.Float('Final Amount', digits=(16, 3))


class SalaryPackage(models.Model):
    _name = 'salary.packages'
    _description = 'Salary Packages'

    sl_no = fields.Integer(string="Sl No")
    component = fields.Many2one('salary.package.type', string="Component")
    amount_per_month = fields.Float(string="Amount Per Month (In OMR)", digits=(12, 3))
    contract_id = fields.Many2one('hr.contract')
    employee_id = fields.Many2one('hr.employee')
    increment_id = fields.Many2one('increment.and.promotion')
    new_increment_id = fields.Many2one('increment.and.promotion')
    final_settlement_id = fields.Many2one('final.settlement')


class SalaryPackageType(models.Model):
    _name = 'salary.package.type'
    _description = 'Salary Package Type'

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")


class SalaryStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    contract = fields.Many2one('hr.contract')
    employee_id = fields.Many2one('hr.employee')
    is_regular_pay = fields.Boolean(default=False)
