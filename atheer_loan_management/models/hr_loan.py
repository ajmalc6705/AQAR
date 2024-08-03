# -*- coding: utf-8 -*-

from __future__ import print_function
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


def int_to_en(num):
    d = {0: 'zero', 1: 'One', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five',
         6: 'Six', 7: 'Seven', 8: 'Eight', 9: 'Nine', 10: 'Ten',
         11: 'Eleven', 12: 'Twelve', 13: 'Thirteen', 14: 'Fourteen',
         15: 'Fifteen', 16: 'Sixteen', 17: 'Seventeen', 18: 'Eighteen',
         19: 'Nineteen', 20: 'Twenty',
         30: 'Thirty', 40: 'Forty', 50: 'Fifty', 60: 'Sixty',
         70: 'Seventy', 80: 'Eighty', 90: 'Ninety'}
    k = 1000
    m = k * 1000
    b = m * 1000
    t = b * 1000

    assert (0 <= num)

    if (num < 20):
        return d[num]

    if (num < 100):
        if num % 10 == 0:
            return d[num]
        else:
            return d[num // 10 * 10] + '-' + d[num % 10]

    if (num < k):
        if num % 100 == 0:
            return d[num // 100] + ' Hundred'
        else:
            return d[num // 100] + ' Hundred and ' + int_to_en(num % 100)

    if (num < m):
        if num % k == 0:
            return int_to_en(num // k) + ' Thousand'
        else:
            return int_to_en(num // k) + ' Thousand, ' + int_to_en(num % k)

    if (num < b):
        if (num % m) == 0:
            return int_to_en(num // m) + ' Million'
        else:
            return int_to_en(num // m) + ' Million, ' + int_to_en(num % m)

    if (num < t):
        if (num % b) == 0:
            return int_to_en(num // b) + ' Billion'
        else:
            return int_to_en(num // b) + ' Billion, ' + int_to_en(num % b)

    if (num % t == 0):
        return int_to_en(num // t) + ' Trillion'
    else:
        return int_to_en(num // t) + ' Trillion, ' + int_to_en(num % t)

    raise UserError('num is too large: %s' % str(num))


def amount_to_text(number, currency):
    amount_left = ''
    amount_right = ''
    if number:
        number = '%.3f' % number
        units_name = currency
        lists = str(number).split('.')
        if lists[0]:
            val1 = int(lists[0])
            val2 = int(lists[1])
            start_word = int_to_en(val1)
            end_word = int_to_en(val2)
        cents_number = int(lists[1])
        cents_name = (cents_number > 1) and 'Baisa'
        amount_left = ' '.join(filter(None, [start_word, units_name]))
        amount_right = ' '.join(filter(None, [end_word, cents_name]))
    return {'left': amount_left, 'right': amount_right}


class HrLoan(models.Model):
    _name = "hr.loan"
    _description = 'HR Loan'
    _inherit = ['mail.thread']
    _order = 'name desc'

    name = fields.Char(string='Loan No.', required=True, default='/')
    employee_id = fields.Many2one('hr.employee', string='Employee ID', required=True)
    emp_id = fields.Char(string='Employee ', related='employee_id.name')
    date_request = fields.Date('Loan Applied On')
    date_approved = fields.Date('Loan Approved On', readonly=True)
    department = fields.Many2one('hr.department', string="Department", related='employee_id.department_id', store=True)
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id', store=True)
    date_of_joining = fields.Date(string='Date Of Joining', store=True)
    gratuity = fields.Float(string='Gratuity', store=True, digits=(16, 3))
    no_of_month = fields.Integer('Number Of Installments', required=True, default=1)
    start_date_pay = fields.Date('Start Date Of Payment', required=True)
    amount = fields.Float(string='Loan Amount', digits=(16, 3), required=True)
    employee_acc = fields.Many2one('account.account', string='Employee Account')
    treasury_acc = fields.Many2one('account.account', string='Treasury Account')
    journal = fields.Many2one('account.journal', string='Journal')
    journal_entry = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    installments = fields.One2many('hr.loan.installments', 'loan_id', string='Installments')
    amount_total = fields.Float('Total Loan Amount', digits=(16, 3), compute='total_amount')
    amount_paid = fields.Float('Total Paid Amount', digits=(16, 3), compute='total_amount')
    amount_balance = fields.Float('Balance Amount', digits=(16, 3), compute='total_amount')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    state = fields.Selection([('draft', 'Draft'),
                              ('approved', 'Approved'),
                              ('cancel', 'Refused'),
                              ('done', 'Paid')],
                             'Status', default='draft',
                             tracking=True, copy=False)
    notes = fields.Text(string='Remarks', tracking=True)
    account_analytic_id = fields.Many2one('account.analytic.account',
                                          string='Analytic Account')
    analytic_precision = fields.Integer(
        store=True,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    )
    analytic_distribution = fields.Json(
        "Analytic Distribution", store=True,
    )
    amount_in_text = fields.Char('Amount in Text', compute='total_amount')
    payslip_ids = fields.Many2many(comodel_name='hr.payslip', compute="get_payslips")
    last_installment_date = fields.Date(string='Last Installment Deducted', tracking=True, copy=False,
                                        compute='get_last_deducted_date')
    is_omani = fields.Selection([('omani', 'Omani'), ('expat', 'Expat')])
    type = fields.Selection([('loan', 'Loan'),
                             ('advance', 'Advance'),
                             ('deduction', 'Deduction'),
                             ('allowance', 'Allowance'),
                             ('fine', 'Fine')], string='Type')
    last_loan = fields.Boolean(string='Last Loan Date', copy=False, readonly=True)
    date_recovered = fields.Date(string='Loan completed', copy=False)
    installment_type = fields.Selection([('amt', 'Amount'), ('period', 'Period')],
                                        default='period', string='Installment Method')
    installment_amount = fields.Float(string='Installment Amount', copy=False, digits=(16, 3))
    check_deserve_emp = fields.Boolean("Deserve Emp")

    _sql_constraints = [('sequence_name', 'unique(name)', 'Sequence Number Duplicated.')]

    @api.onchange('installments')
    def set_paid(self):
        for record in self:
            if record.installments:
                paid = True
                for i in record.installments:
                    if not i.paid:
                        paid = False
                if paid:
                    record.write({'state': 'done', 'date_recovered': fields.Date.today()})

    @api.onchange('start_date_pay')
    def onchange_start_date_loan(self):
        for record in self:
            if record.start_date_pay:
                payslip = self.env['hr.payslip'].search(
                    [('employee_id', '=', record.employee_id.id), ('date_from', '<=', record.start_date_pay),
                     ('date_to', '>=', record.start_date_pay)], limit=1)
                if payslip:
                    raise UserError('Already Generated Payslip for the Starting Date')

    def sent(self):
        for record in self:
            if record.state == 'p_accountant':
                record.state = 'to_approve'

    def approve(self):
        move_pool = self.env['account.move']
        timenow = time.strftime('%Y-%m-%d')
        for record in self:
            move = {
                'narration': record.employee_id.name,
                'date': timenow,
                'ref': record.name,
                'journal_id': record.journal.id,
                'move_type': 'entry',
                'partner_id': record.employee_id.user_partner_id.id,
                'analytic_distribution': record.analytic_distribution,
            }
            line_ids = []
            debit_line = (0, 0, {
                'name': record.employee_id.name,
                'date': timenow,
                'partner_id': record.employee_id.user_partner_id.id,
                'account_id': record.employee_acc.id,
                'journal_id': record.journal.id,
                'debit': record.amount > 0.0 and record.amount or 0.0,
                'credit': record.amount < 0.0 and -record.amount or 0.0,
                'analytic_distribution': record.analytic_distribution,
            })
            line_ids.append(debit_line)

            credit_line = (0, 0, {
                'name': record.employee_id.name,
                'date': timenow,
                'partner_id': record.employee_id.user_partner_id.id,
                'account_id': record.treasury_acc.id,
                'journal_id': record.journal.id,
                'debit': record.amount < 0.0 and -record.amount or 0.0,
                'credit': record.amount > 0.0 and record.amount or 0.0,
                'analytic_distribution': record.analytic_distribution,
            })
            line_ids.append(credit_line)
            move_id = move_pool.create(move)
            move_id.update({'line_ids': line_ids})
            move_id.action_post()
            record.write({'journal_entry': move_id.id, 'state': 'approved', 'date_approved': fields.Date.today()})

    def refuse(self):
        for record in self:
            if record.installments.filtered(lambda x: x.paid == True):
                raise UserError('Already deducted from the salary, You cannot cancel the advance')

            record.write({'state': 'cancel'})

    @api.constrains('start_date_pay')
    def check_date(self):
        for record in self:
            if record.start_date_pay.day in [29, 30, 31]:
                raise ValidationError("Days In 29,30,31 are not allowed for installments")

    def generate_loan_installment(self):
        """
        Update Installments relative to the start date, amount and no of installments.
        :return: [(0, 0, {values})]
        """

        loan_ids = self.env['hr.loan'].search([('employee_id', '=', self.employee_id.id), ('id', '!=', self.id)],
                                              order='id ASC', limit=1)
        date_180 = datetime.today() - timedelta(days=180)
        date = []
        if loan_ids:
            for loan in loan_ids.mapped('installments'):
                date.append(loan.date_pay)
            if date and date[-1] >= date_180.date():
                self.check_deserve_emp = True
            else:
                self.check_deserve_emp = False
        for record in self:
            record.installments = [(5, _, _)]
            if record.start_date_pay and record.amount and record.no_of_month and record.installment_type == 'period':
                lines = []
                amount = record.amount / record.no_of_month
                date = record.start_date_pay
                if date.day in [29, 30, 31]:
                    record.start_date_pay = False
                    record.installments = []
                    raise UserError("Days In 29,30,31 are not allowed for installments")

                for i in range(record.no_of_month):
                    date_pay = date + relativedelta(months=i)
                    values = {
                        'date_pay': date_pay,
                        'amount': amount,
                    }
                    lines.append((0, 0, values))
                record.installments = lines
                if (round(amount, 3) * record.no_of_month) > record.amount:
                    extra_amount = (round(amount, 3) * record.no_of_month) - record.amount
                    if extra_amount:
                        record.installments[-1].amount = record.installments[-1].amount - extra_amount
                        record.installments[
                            -1].notes = "Extra Adjustment amount -%s to adjust decimal precision" % round(
                            extra_amount, 3)
                elif (round(amount, 3) * record.no_of_month) < record.amount:
                    extra_amount = record.amount - (round(amount, 3) * record.no_of_month)
                    if extra_amount:
                        record.installments[-1].amount = record.installments[-1].amount + extra_amount
                        record.installments[
                            -1].notes = "Extra Adjustment amount +%s to adjust decimal precision" % round(
                            extra_amount, 3)
            elif record.start_date_pay and record.amount and record.no_of_month and record.installment_type == 'amt':
                date = record.start_date_pay
                if date.day in [29, 30, 31]:
                    record.start_date_pay = False
                    record.installments = []
                    raise UserError("Days In 29,30,31 are not allowed for installments")
                no_of_month = int(str(record.amount / record.no_of_month).split('.')[0])
                remaining = record.amount - (no_of_month * record.no_of_month)
                lines = [(0, 0, {'date_pay': date + relativedelta(months=i),
                                 'amount': record.no_of_month}) for i in range(no_of_month)]
                if remaining > 0:
                    lines.append((0, 0, {
                        'date_pay': date + relativedelta(months=no_of_month),
                        'amount': remaining,
                    }))
                record.installments = lines

    # TODO split loan
    def split_loan(self):
        """
        Split Loan after approval. Non Paid installments should be split according
         to the new monthly payment amount and date.
        :return: Wizard to recalculate the installments and amount
        """
        for record in self:
            if not record.state == 'approved':
                continue
            dues = record.installments.filtered(lambda rec: not rec.paid).sorted(
                lambda a: fields.Date.from_string(a['date_pay']),
                reverse=False)
            if not dues:
                continue
            context = {
                'default_no_of_month': len(dues),
                'default_amount': record.amount_balance,
                'default_start_date_pay': dues[0].date_pay,
                'default_amount_due': record.amount_balance,
                'default_no_of_month_due': len(dues),
            }
            wizard = {
                'name': 'Split Loan Installments',
                'type': 'ir.actions.act_window',
                'model': 'ir.actions.act_window',
                'res_model': 'wizard.loan.split',
                'view_mode': 'form',
                'target': 'new',
                'context': context,
            }
            return wizard

    @api.depends('amount', 'installments')
    def total_amount(self):
        for record in self:
            record.amount_total = record.amount
            total = 0
            for i in record.installments:
                if i.paid:
                    total += i.paid_amount
            record.amount_paid = total
            record.amount_balance = record.amount_total - record.amount_paid
            if record.amount:
                amount_in_word = amount_to_text(number=record.amount, currency='Rial Omani')
                amt_l = amount_in_word['left']
                amt_r = amount_in_word['right']
                amount_formated_l = amt_l
                amount_formated_r = amt_r
                if (record.amount <= 999) and (int(record.amount) % 100 == 0):
                    amount_formated_l = amt_l.replace('Hundred and', 'Hundred')
                total = '%.3f' % record.amount
                floating_point = str(total).split('.')[1]
                if int(floating_point) and (int(floating_point) <= 999) and (int(floating_point) % 100 == 0):
                    amount_formated_r = amt_r.replace('and Baisa', 'Baisa')
                if amount_formated_r == 'zero':
                    record.amount_in_text = amount_formated_l
                else:
                    record.amount_in_text = amount_formated_l + ' and ' + amount_formated_r
            else:
                record.amount_in_text = 'Zero'

    def get_payslips(self):
        """

        :return: payslip ids where the loan amount processed.
        """
        for record in self:
            payslips = self.env['hr.payslip'].search([('installments', '!=', False),
                                                      ('employee_id', '=', record.employee_id.id),
                                                      ('installments.installment_id.loan_id', '=', record.id)])
            if payslips:
                record.payslip_ids = payslips.ids
            else:
                record.payslip_ids = None

    def get_last_deducted_date(self):
        """
        Grab loan installment last deducted payslip end period.
        :return:
        """
        for record in self:
            if record.payslip_ids:
                last_deducted_slip = record.payslip_ids.filtered(
                    lambda payslip: payslip.state in ['done', 'with_finance_manager']).sorted(
                    key=lambda slip: slip.date_to, reverse=True)
                record.last_installment_date = last_deducted_slip and last_deducted_slip[0].date_to
            else:
                record.last_installment_date = None

    # def pay_loan(self):
    #     """
    #
    #     :return:
    #     """
    #     self.ensure_one()
    #     record = self
    #     if not record.journal_entry:
    #         record.approve()  # create journal entry if not created
    #     if not record.voucher_id:
    #         # Create Voucher 'Other Payments' with the related journal entries
    #         vals = {
    #             'account_id': record.employee_acc.id,
    #             'journal_id': record.journal.id,
    #             'reference': record.name,
    #             'line_dr_ids': [(0, 0, {
    #                 'account_id': record.employee_acc.id,
    #                 'description': 'Payment For Loan %s' % record.name,
    #                 'amount': record.amount,
    #             })],
    #             'move_id': record.journal_entry.id,
    #             'type': 'purchase',
    #         }
    #         record.voucher_id = self.env['account.voucher'].create(vals)
    #     else:  # if voucher exists then show them
    #         pass
    #     form = self.env.ref('sabla_accounting.view_sabla_other_payments')
    #     tree = self.env.ref('account_voucher.view_voucher_tree')
    #     search = self.env.ref('account_voucher.view_voucher_filter_vendor')
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Loan Payment',
    #         'view_type': 'form',
    #         'view_mode': 'form,tree',
    #         'context': {'default_type': 'purchase', 'type': 'purchase'},
    #         'views': [(form.id, 'form'), (tree.id, 'tree'), (search.id, 'search')],
    #         'domain': [('journal_id.type', 'in', ['purchase', 'purchase_refund', 'general']), ('type', '=', 'purchase')],
    #         'res_model': 'account.voucher',
    #         'res_id': record.voucher_id.id,
    #         'nodestroy': True,
    #     }

    # @api.multi
    # def sent_to_pa(self):
    #     """
    #
    #     :return:
    #     """
    #     for record in self:
    #         if record.state == 'draft':
    #             record.state = 'pa_admin'

    def sent_to_section(self):
        """

        :return:
        """
        for record in self:
            record.generate_loan_installment()
            if record.state == 'draft':
                record.state = 'with_section_head'

    def sent_to_hr_m(self):
        """

        :return:
        """
        for record in self:
            if record.state == 'with_section_head':
                record.state = 'hr_manager'

    def sent_to_ceo(self):
        """
        Here new wrk is introduced, if the requested amount is less than 25 OMR then it will not go through
        CEO/Dy.CEO.
        :return:
        """
        for record in self:
            if record.state == 'hr_manager':
                if record.amount < 25:
                    record.write({'state': 'p_accountant'})
                    record.message_post(
                        body="The Advance Salary Less than 25 OMR will not go through CEO/Dy.CEO.",
                        subtype_xmlid="mail.mt_comment",
                        message_type="comment")
                else:
                    record.state = 'ceo'

    def sent_to_pa_accountant(self):
        """

        :return:
        """
        for record in self:
            if record.state in ['ceo']:
                record.state = 'p_accountant'

    def send_back(self):
        """

        :return:
        """
        for record in self:
            if record.state == 'with_section_head':
                record.state = 'draft'
            elif record.state == 'hr_manager':
                record.state = 'with_section_head'
            elif record.state == 'ceo':
                record.state = 'hr_manager'
            elif record.state == 'p_accountant':
                record.state = 'hr_manager'
            elif record.state == 'to_approve':
                record.state = 'p_accountant'

    @api.model
    def create(self, vals):
        vals['date_request'] = fields.date.today()
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.loan.sequence') or '/'
        return super(HrLoan, self).create(vals)


class HrLoanInstallments(models.Model):
    _name = 'hr.loan.installments'
    _description = 'Loan Installments'

    loan_id = fields.Many2one('hr.loan', ondelete='cascade')
    payslip_id = fields.Many2one('hr.payslip')
    date_pay = fields.Date('Payment Date', required=True, readonly=True)
    amount = fields.Float('Amount', required=True, readonly=False, digits=(16, 3))
    paid_amount = fields.Float('Paid Amount', digits=(16, 3))
    paid = fields.Boolean('Paid')
    proposed_amount = fields.Float(string='Proposed Amount', digits=(16, 3))
    notes = fields.Text('Notes')
    pay = fields.Boolean('Add To Payslip')
    company_id = fields.Many2one('res.company', 'Company', related='loan_id.company_id')
    state = fields.Selection(related='loan_id.state')
    employee_id = fields.Many2one(related='loan_id.employee_id', string='Employee')

    @api.onchange("paid")
    def _onchange_paid(self):
        loan = self.env['hr.loan'].browse(self._origin.loan_id.id)
        current_user = self.env.user.name
        if self.paid:
            loan.message_post(
                body="Loan is Mark it as paid by %s for the Installment date %s " % (current_user, self.date_pay),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
        else:
            loan.message_post(
                body="Loan is Mark it as Unpaid by %s for the Installment date %s " % (current_user, self.date_pay),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")

#     Mark as Paid Button
    def mark_as_paid_loan(self):
        wizard = self.env['loan.payment.wizard'].create({'loan_id': self.loan_id.id,
                        'amount': self.amount,'loan_installment_id':self.id})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Loan Payment',
            'view_mode': 'form',
            'res_model': 'loan.payment.wizard',
            'res_id': wizard.id,
            'target': 'new',

        }


class HrSalaryAdvance(models.Model):
    _name = 'hr.salary.advance'
    _description = 'HR Advance Salary'
    _inherit = ['mail.thread']

    name = fields.Char(string='Application No', required=True, default='/')
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee ID', required=True)
    emp_id = fields.Char(string='Employee', related='employee_id.name')
    date_request = fields.Date(string='Applied On', readonly=True)
    date_approved = fields.Date(string='Approved On', readonly=True)
    department = fields.Many2one(comodel_name='hr.department', string="Department", related='employee_id.department_id',
                                 store=True)
    job_id = fields.Many2one(comodel_name='hr.job', string='Job Position', related='employee_id.job_id', store=True)
    no_of_month = fields.Integer(string='Number Of Installments', required=True, default=1)
    start_date_pay = fields.Date(string='Start Date Of Payment', required=True)
    amount = fields.Float(string='Amount', required=True, digits=(16, 3))
    employee_acc = fields.Many2one(comodel_name='account.account', string='Employee Account')
    treasury_acc = fields.Many2one(comodel_name='account.account', string='Treasury Account')
    journal = fields.Many2one(comodel_name='account.journal', string='Journal')
    journal_entry = fields.Many2one(comodel_name='account.move', string='Journal Entry', readonly=True)
    installments = fields.One2many('hr.salary.installments', 'advance_id', string='Installments',
                                   tracking=True)
    amount_total = fields.Float('Total Amount', compute='total_amount', digits=(16, 3))
    amount_paid = fields.Float('Paid Amount', compute='total_amount', digits=(16, 3))
    amount_balance = fields.Float('Balance Amount', compute='total_amount', digits=(16, 3))
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    state = fields.Selection([('draft', 'Draft'),
                              ('pa_admin', 'PA Administrator'),
                              ('with_section_head', 'Section Head'),
                              ('hr_manager', 'HR Manager'),
                              ('ceo', 'Dy CEO / CEO'),
                              ('p_accountant', 'Payroll Accountant'),
                              ('to_approve', 'Senior Accountant / Finance Manager'),
                              ('approved', 'Approved'),
                              ('cancel', 'Refused'),
                              ('done', 'Paid')],
                             'Status', default='draft',
                             tracking=True, copy=False)
    ticket_reference = fields.Char("Ticket reference")
    ticket_reference_id = fields.Integer("Ticket reference id")
    remark = fields.Text("Ticket Remarks")
    check_previous_adc = fields.Boolean("Check Previous Advance")

    _sql_constraints = [('sequence_advance_name', 'unique(name)', 'Sequence Number Duplicated.')]

    @api.depends('amount', 'installments')
    def total_amount(self):
        self.amount_total = self.amount
        total = 0
        for i in self.installments:
            if i.paid:
                total += i.amount
        self.amount_paid = total
        self.amount_balance = self.amount_total - self.amount_paid

    @api.onchange('start_date_pay')
    def onchange_start_date_loan(self):
        for record in self:
            if record.start_date_pay:
                payslip = self.env['hr.payslip'].search(
                    [('employee_id', '=', record.employee_id.id), ('date_from', '<=', record.start_date_pay),
                     ('date_to', '>=', record.start_date_pay)], limit=1)
                if payslip:
                    raise UserError('Already Generated Payslip for the Starting Date')

    def sent_to_section(self):
        """

        :return:
        """
        for record in self:
            if record.ticket_reference_id:
                record.generate_installment()
            # if not record.installments:
            #     record.installment_calc()
            if record.state == 'draft':
                record.state = 'with_section_head'

    def sent_to_hr_m(self):
        """

        :return:
        """
        for record in self:
            if record.state == 'with_section_head':
                record.state = 'hr_manager'

    def sent_to_ceo(self):
        """
        Here new wrk is introduced, if the requested amount is less than 25OMR then it will not go through
        CEO/Dy.CEO. This is common now, PCR test(CoVID-19)
        :return:
        """
        for record in self:
            if record.state == 'hr_manager':
                if record.amount <= 25:
                    record.write({'state': 'p_accountant'})
                    record.message_post(
                        body="The Advance Salary Less than 25OMR will not go through CEO/Dy.CEO.",
                        subtype_xmlid='mail.mt_comment',
                        message_type="comment")

                else:
                    record.state = 'ceo'

    def sent_to_pa_accountant(self):
        """

        :return:
        """
        for record in self:
            if record.state in ['ceo']:
                record.state = 'p_accountant'

    def send_back(self):
        """

        :return:
        """
        for record in self:
            if record.state == 'with_section_head':
                record.state = 'draft'
            elif record.state == 'hr_manager':
                record.state = 'with_section_head'
            elif record.state == 'ceo':
                record.state = 'hr_manager'
            elif record.state == 'p_accountant':
                record.state = 'hr_manager'
            elif record.state == 'to_approve':
                record.state = 'p_accountant'

    def sent(self):
        if self.state == 'p_accountant':
            self.state = 'to_approve'

    def approve(self):
        move_pool = self.env['account.move']
        timenow = time.strftime('%Y-%m-%d')
        for record in self:
            move = {
                'narration': record.employee_id.name,
                'date': timenow,
                'ref': record.name,
                'journal_id': record.journal.id,
                'move_type': 'entry',
                'partner_id': record.employee_id.user_partner_id.id,
                'analytic_distribution': record.analytic_distribution,
            }
            line_ids = []
            debit_line = (0, 0, {
                'name': record.employee_id.name,
                'date': timenow,
                'partner_id': record.employee_id.user_partner_id.id,
                'account_id': record.employee_acc.id,
                'journal_id': record.journal.id,
                'debit': record.amount > 0.0 and record.amount or 0.0,
                'credit': record.amount < 0.0 and -record.amount or 0.0,
                'analytic_distribution': record.analytic_distribution,
            })
            line_ids.append(debit_line)
            # debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

            credit_line = (0, 0, {
                'name': record.employee_id.name,
                'date': timenow,
                'partner_id': record.employee_id.user_partner_id.id,
                'account_id': record.treasury_acc.id,
                'journal_id': record.journal.id,
                'debit': record.amount < 0.0 and -record.amount or 0.0,
                'credit': record.amount > 0.0 and record.amount or 0.0,
                'analytic_account_id': False,
            })
            line_ids.append(credit_line)
            move_id = move_pool.create(move)
            move_id.update({'line_ids': line_ids})
            move_id.post()
            record.write({'journal_entry': move_id.id, 'state': 'approved', 'date_approved': fields.Date.today()})

    def refuse(self):
        for record in self:
            if record.installments.filtered(lambda x: x.paid == True):
                raise UserError('Already deducted from the salary, You cannot cancel the advance')

            record.write({'state': 'cancel'})

    def cancel(self):
        """Once the advance salary is approved still the payroll accountant can cancel the application"""
        moves = self.env['account.move']
        for record in self:
            if record.amount_paid:
                raise UserError('The Amount deducted from the salary, You cannot cancel.')
            if record.journal_entry:
                moves += record.journal_entry
            # First, set the advance as cancelled and detach the move ids
            self.write({'state': 'cancel', 'journal_entry': False})
            if moves:
                # second, invalidate the move(s)
                moves.button_cancel()
                # delete the move this advance was pointing to
                # Note that the corresponding move_lines and move_reconciles
                # will be automatically deleted too
                moves.unlink()

    def generate_installment(self):
        advance_ids = self.env['hr.salary.advance'].search(
            [('employee_id', '=', self.employee_id.id), ('id', '!=', self.id)], order='id ASC',
            limit=1)
        date = []
        paid = False
        if advance_ids:
            for advance in advance_ids.mapped('installments'):
                date.append(advance.date_pay)
                paid = advance.paid
            if date and not paid:
                self.check_previous_adc = True
            else:
                self.check_previous_adc = False
        for record in self:
            record.installments = [(5, _, _)]
            if record.start_date_pay and record.amount and record.no_of_month:
                lines = []
                amount = record.amount / record.no_of_month
                date = record.start_date_pay
                if date.day in [29, 30, 31]:
                    record.start_date_pay = False
                    record.installments = []
                    raise Warning("Days In 29,30,31 are not allowed for installments")

                for i in range(record.no_of_month):
                    date_pay = record.start_date_pay + timedelta(i * 365 / 12)
                    values = {
                        'date_pay': date_pay,
                        'amount': amount,
                    }
                    lines.append((0, 0, values))
                record.installments = [(5, _, _)]
                record.installments = lines
                if (round(amount, 3) * record.no_of_month) > record.amount:
                    extra_amount = (round(amount, 3) * record.no_of_month) - record.amount
                    if extra_amount:
                        record.installments[-1].amount = record.installments[-1].amount - extra_amount
                        record.installments[
                            -1].notes = "Extra Adjustment amount -%s to adjust decimal precision" % round(
                            extra_amount, 3)
                elif (round(amount, 3) * record.no_of_month) < record.amount:
                    extra_amount = record.amount - (round(amount, 3) * record.no_of_month)
                    if extra_amount:
                        record.installments[-1].amount = record.installments[-1].amount + extra_amount
                        record.installments[
                            -1].notes = "Extra Adjustment amount +%s to adjust decimal precision" % round(
                            extra_amount, 3)

    @api.model
    def create(self, vals):
        vals['date_request'] = fields.date.today()
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.salary.advance') or '/'
        return super(HrSalaryAdvance, self).create(vals)


class HrSalaryInstallments(models.Model):
    _name = 'hr.salary.installments'
    _description = 'Salary Installments'

    advance_id = fields.Many2one(comodel_name='hr.salary.advance', ondelete='cascade', string='Advance')
    payslip_id = fields.Many2one(comodel_name='hr.payslip', string='Payslip')
    date_pay = fields.Date(string='Payment Date', readonly=True)
    amount = fields.Float(string='Amount', readonly=True, digits=(16, 3))
    proposed_amount = fields.Float(string='Proposed Amount', digits=(16, 3))
    paid = fields.Boolean(string='Paid')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', related='advance_id.company_id')
    pay = fields.Boolean(string='Add To Payslip')

    @api.onchange("paid")
    def _onchange_paid(self):
        advance_salary = self.env['hr.salary.advance'].browse(self._origin.advance_id.id)
        current_user = self.env.user.name
        if self.paid:
            advance_salary.message_post(
                body="Advance salary is Mark it as paid by %s for the Installment date %s " % (
                    current_user, self.date_pay),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
        else:
            advance_salary.message_post(
                body="Advance Salary is Mark it as Unpaid by %s for the Installment date %s " % (
                    current_user, self.date_pay),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")


class HRPayslipInstallments(models.Model):
    """Loan Lines In Payslip"""
    _name = 'hr.payslip.installments'
    _description = 'Payslip Installment'

    payslip_id = fields.Many2one('hr.payslip')
    loan_id = fields.Char('Loan')
    installment_id = fields.Many2one('hr.loan.installments')
    date_pay = fields.Date('Payment Date', required=True, readonly=True)
    amount = fields.Float('Amount', required=True, readonly=True, digits=(16, 3))
    proposed_amount = fields.Float(string='Proposed Amount', readonly=False, digits=(16, 3))
    paid_check = fields.Boolean('Paid', default=True)
    notes = fields.Text('Notes')
    company_id = fields.Many2one('res.company', 'Company', related='payslip_id.company_id')
    payslip_state = fields.Selection(related='payslip_id.state')
    is_refund = fields.Boolean('Is Refund')

    @api.model
    def create(self, vals):
        vals['proposed_amount'] = vals['amount']
        return super(HRPayslipInstallments, self).create(vals)

    def compute_loan(self):
        if not self.paid_check:
            self.paid_check = True
            self.payslip_id.message_post(
                body="Loan is Mark it as paid by %s for the Installment date %s " % (
                    self.env.user.name, self.date_pay),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
        elif self.paid_check:
            self.paid_check = False
            self.payslip_id.message_post(
                body="Loan is Mark it as Unpaid by %s for the Installment date %s " % (
                    self.env.user.name, self.date_pay),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
        self.payslip_id.add_loan()

    @api.onchange('proposed_amount')
    def _onchange_proposed_amount(self):
        for rec in self:
            if rec.amount < rec.proposed_amount:
                rec.proposed_amount = rec.amount
                raise UserError("Proposed Amount is Grater Than Installment Amount!")


class HRPayslipSalInstallments(models.Model):
    _name = 'hr.payslip.sal.installments'
    _description = 'Payslip Salary installment'

    payslip_id = fields.Many2one('hr.payslip')
    advance_id = fields.Char('Form No.')
    installment_id = fields.Many2one('hr.salary.installments')
    date_pay = fields.Date('Payment Date', required=True, readonly=True)
    amount = fields.Float('Amount', required=True, readonly=True, digits=(16, 3))
    paid_check = fields.Boolean('Paid')
    notes = fields.Text('Notes')
    payslip_state = fields.Selection(related='payslip_id.state')
    company_id = fields.Many2one('res.company', 'Company', related='payslip_id.company_id')

    def compute_advance(self):
        if not self.paid_check:
            self.paid_check = True
            self.payslip_id.message_post(
                body="Advance salary is Mark it as paid by %s for the Installment date %s " % (
                    self.env.user.name, self.date_pay),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
        elif self.paid_check:
            self.paid_check = False
            self.payslip_id.message_post(
                body="Advance salary is Mark it as Unpaid by %s for the Installment date %s " % (
                    self.env.user.name, self.date_pay),
                subtype_xmlid="mail.mt_comment",
                message_type="comment")
        self.payslip_id.add_advance()
