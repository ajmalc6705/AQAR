from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
import warnings


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # inherit the create draft entry button and add advance_installments section
    def action_payslip_done(self):
        for slip in self:
            if slip.advance_amount:
                for i in slip.advance_installments:
                    if i.paid_check:
                        i.installment_id.write({'paid': True, 'notes': i.notes})
        return super(HrPayslip, self).action_payslip_done()

    # inherit the mark as paid method and write updation in hr.loan model
    def action_payslip_paid(self):
        res = super(HrPayslip, self).action_payslip_paid()
        for slip in self:
            if slip.loan_amount:
                for i in slip.installments:
                    if i.paid_check and not i.is_refund:
                        loans = self.env['hr.loan'].search(
                            [('employee_id', '=', self.employee_id.id), ('state', '=', 'approved')])
                        i.installment_id.write({'paid': True,
                                                'paid_amount': i.proposed_amount,
                                                'notes': i.notes})
                        installments = self.env['hr.loan.installments'].search([('loan_id', 'in', loans.ids),
                                                                                ('paid', '=', False)],
                                                                               order='date_pay ASC', limit=1)
                        installments.amount = installments.amount + (i.amount - i.proposed_amount)
        return res

    # compute the loan ammount on the base of employe date from and date to
    # add instalment lines to payslip
    @api.constrains('employee_id', 'date_from', 'date_to')
    def compute_loan(self):
        """
        """
        if self.employee_id:
            loans = self.env['hr.loan'].search([('employee_id', '=', self.employee_id.id), ('state', '=', 'approved')])

            installments = self.env['hr.loan.installments'].search([('loan_id', 'in', loans.ids),
                                                                    ('date_pay', '<=', self.date_to),
                                                                    ('paid', '=', False)], order='date_pay ASC')
            if installments:
                lines = []
                for index, line in enumerate(installments):
                    if not line.paid:
                        values = {
                            'loan_id': line.loan_id.name,
                            'installment_id': line.id,
                            'date_pay': line.date_pay,
                            'amount': line.amount,
                            'notes': line.notes,
                        }
                        lines.append((0, 0, values))
                self.installments = [(5, _, _)]
                self.installments = lines

    @api.constrains('employee_id', 'date_from', 'date_to')
    def compute_advance(self):
        """

        :return:
        """
        if self.employee_id:
            loans = self.env['hr.salary.advance'].search([('employee_id', '=', self.employee_id.id),
                                                          ('state', '=', 'approved')])
            installments = self.env['hr.salary.installments'].search([('advance_id', 'in', loans.ids),
                                                                      ('date_pay', '<=', self.date_to),
                                                                      ('paid', '=', False)],
                                                                     order='date_pay ASC')
            if installments:

                lines = []
                for index, line in enumerate(installments):
                    if not line.paid:
                        values = {
                            'advance_id': line.advance_id.name,
                            'installment_id': line.id,
                            'date_pay': line.date_pay,
                            'amount': line.amount,
                            'notes': line.notes,
                        }
                        lines.append((0, 0, values))
                        self.advance_installments = [(5, _, _)]
                        if (self._context.get('params', False) and self._context.get('params', False).get('id',
                                                                                                          False)) or self:
                            p_id = self.id if self.id else self._context.get('params', False) and self._context.get(
                                'params', False).get('id', False)
                            print(p_id)
                            if p_id:
                                u_query = "INSERT INTO hr_payslip_sal_installments (payslip_id,advance_id,installment_id,date_pay,amount,notes,paid_check,create_date,create_uid) " \
                                          "VALUES('" + str(p_id) + "', " \
                                                                   "'" + str(line.advance_id.name) + "'," \
                                                                                                     "'" + str(
                                    line.id) + "'," \
                                               "'" + str(line.date_pay) + "'," \
                                                                          "'" + str(line.amount) + "'," \
                                                                                                   "'" + str(
                                    line.notes) + "'," \
                                                  "'" + str(True) + "'," \
                                                                    "(now() at time zone 'UTC') ," \
                                                                    "'" + str(
                                    self.env.user.id) + "')"
                                self._cr.execute(u_query)
                        else:
                            self.advance_installments = lines

    # add loan ammount based on installment lines addeed to the pay lisp
    @api.depends('installments')
    def add_loan(self):
        total = 0.0
        for i in self.installments:
            total += i.proposed_amount if i.paid_check else 0
        self.loan_amount = total

    # method fro cross check the instalment lines are paid or not
    def check_installments_line_ids(self):
        self.ensure_one()
        for i in self.installments:
            if i.is_refund != True and i.installment_id.paid:
                i.unlink()

    # check final instalment or not if final dedction in loan ammount cant be done
    def check_loan_amount(self):
        self.ensure_one()
        for i in self.installments:
            if i.is_refund != True:
                if i.proposed_amount < i.amount:
                    loans = self.env['hr.loan'].search(
                        [('employee_id', '=', self.employee_id.id), ('state', '=', 'approved')])

                    if self.env['hr.loan.installments'].search_count(
                            [('loan_id', 'in', loans.ids), ('paid', '=', False)]) > 1:
                        pass
                    else:
                        i.proposed_amount = i.amount
                        raise UserError(
                            "Because this is your final instalment, you are unable to reduce the instalment amount.")
                        # raise Warning(_("Because this is your final instalment, you are unable to reduce the instalment amount.")

    # onchange of installments lines check the loan amount to be dedcted from the payslip            
    @api.onchange('installments')
    def _onchange_installments(self):
        for rec in self:
            rec.check_loan_amount()

    @api.depends('advance_installments')
    def add_advance(self):
        total = 0.0
        for i in self.advance_installments:
            total += i.amount if i.paid_check else 0
        self.advance_amount = total

    # inherit the compute sheet method and cross check the installment lines are padi or not
    def compute_sheet(self):
        self.check_installments_line_ids()
        return super().compute_sheet()

    # inherit the action_payslip_done method and cross check the installment lines are padi or not
    def action_payslip_done(self):
        self.check_installments_line_ids()
        return super(HrPayslip, self).action_payslip_done()

    # while refund the payslip we ne update is_refund boolen in the instalment line
    # and also if the value is update in hr.loan we need to revert it
    def refund_sheet(self):
        res = super(HrPayslip, self).refund_sheet()
        payslip_id = self.env['hr.payslip'].search([('id', 'in', res['domain'][0][2])])
        for i in payslip_id.installments:
            i.is_refund = True
            i.installment_id.paid = False
            i.installment_id.proposed_amount = 0
        return res

    installments = fields.One2many('hr.payslip.installments', 'payslip_id', string='Loan Installments', readonly=False,
                                   compute='compute_loan', store=True, copy=True)
    loan_amount = fields.Float('Loan Amount', compute='add_loan', store=True, digits=(16, 3))
    advance_installments = fields.One2many('hr.payslip.sal.installments', 'payslip_id',
                                           string='Advance Salary Installments', compute='compute_advance', store=True)
    advance_amount = fields.Float('Advance Amount', compute='add_advance', store=True, digits=(16, 3))
