# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SplitWizardLoan(models.TransientModel):
    _name = 'wizard.loan.split'
    _description = "Split Wizard Loan"

    no_of_month = fields.Integer('Number Of Installments', required=True)
    start_date_pay = fields.Date('Start Date Of Payment', required=True)
    amount = fields.Float(string='Loan Amount', digits='Loan', required=True)
    no_of_month_due = fields.Integer('Number Of Installments Due', readonly=1)
    amount_due = fields.Float(string='Loan Amount Due', digits='Loan', readonly=True)

    def confirm(self):
        """
        Update and recalculate loan Installments from the data inputs from wizard.
        :return:
        """
        if self.start_date_pay and self.amount and self.no_of_month:
            if self.amount < self.amount_due:
                raise UserError("Amount mismatch with Amount Due")
            lines = []
            amount = self.amount / self.no_of_month
            date = self.start_date_pay
            loan_id = self.env['hr.loan'].browse(self._context.get('active_id'))
            dues = loan_id.installments.filtered(lambda rec: not rec.paid).sorted(
                lambda a: a['date_pay'], reverse=False)
            if date.day in [29, 30, 31]:
                raise UserError("Days In 29,30,31 are not allowed for installments")

            for month in range(self.no_of_month):
                date_pay = date + relativedelta(months=month)
                values = {
                    'date_pay': date_pay,
                    'amount': amount,
                }
                lines.append((0, 0, values))
            dues_to_remove = [(2, due.id, _) for due in dues]
            lines += dues_to_remove
            loan_id.write({'installments': lines})
