from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError, RedirectWarning, UserError


class PettyCashExpense(models.Model):
    _name = 'petty.cash.expense'
    _description = "Petty Cash Expense"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin', 'analytic.mixin']

    name = fields.Char(string='Number', required=True, readonly=True, default=lambda self: _('New'))
    invoice_number = fields.Char(string='Invoice Number')
    user_id = fields.Many2one(comodel_name='res.users', string="User", default=lambda self: self.env.user,
                              readonly=True)
    paid_to = fields.Char('Paid To', copy=False, tracking=True)
    expense = fields.Char(string='Label', readonly=True)
    date = fields.Date(string='Accounting Date', default=lambda self: fields.Date.today(), readonly=True)
    bill_date = fields.Date(string='Bill Date')
    # bill_ref = fields.Char(string='Bill Ref', copy=False,)# compute='compute_bill'
    bill_state = fields.Selection([('new', 'Check Bill State'), ('billed', 'Billed'), ], 'Status', readonly=True,
                                  copy=False, tracking=True, default="new", )
    # bill_id = fields.Many2one('account.move', string="Bill Ref", readonly=True)
    amount = fields.Float(string='Amount', readonly=True, digits=(12, 3), tracking=True)
    debit_id = fields.Many2one(comodel_name='account.account', string='Debit Account')
    credit_id = fields.Many2one(comodel_name='account.account', related='user_id.employee_id.petty_cash',
                                string='Credit Account')
    tax_ids = fields.Many2many(comodel_name='account.tax', string="Taxes", store=True, readonly=False, )
    group_officer = fields.Boolean('Officer Group', compute='_compute_group_officer')
    officer_remarks = fields.Char('Officer Remarks ', help='Officer can remarks about the expence')
    journal_entry_id = fields.Many2one(comodel_name='account.move', string='Journal Entry', readonly=True)
    in_hand_petty_cash = fields.Float(string='In Hand Petty Cash', compute='_calculate_in_hand_petty_cash',
                                      readonly=True, digits=(12, 3), tracking=True)

    pending_amount = fields.Char(string='Pending Approval', readonly=True)

    file_name = fields.Char('File Name')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', readonly=True)
    expense_type_id = fields.Many2one(comodel_name='petty.cash.expense.type', string='Expense Type', readonly=True,
                                      tracking=True)
    user_ids = fields.Many2many('res.users', 'rel_expense_id_user_id', 'petty_cash_expense_id', 'user_id',
                                string='Users', tracking=True)
    cheque_number = fields.Char(string='Cheque Number')
    cheque_date = fields.Date(string="Cheque Date")
    state = fields.Selection([('draft', 'Draft'), ('waiting', 'Checked'), ('verified', 'Verified'),
                              ('approved', 'Approved'), ('posted', 'Posted'), ('reject', 'Rejected'),
                              ('cancel', 'Cancelled'), ], 'Status', readonly=True, required=True,
                             copy=False, tracking=True, default="draft")
    analytic_distribution = fields.Json("Analytic Distribution", store=True, )

    analytic_precision = fields.Integer(
        store=True,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    )
    currency_id = fields.Many2one(comodel_name='res.currency', compute='_get_company_currency',
                                  string='Currency', precompute=True,store=True,
                                  help="The payment's currency.")
    check_amount_in_words = fields.Char(string="Amount in Words", store=True,
                                        compute='_compute_check_amount_in_words', )

    invoice_amount = fields.Float(string="Invoice Amount", digits=(12, 3), tracking=True)

    def _get_company_currency(self):
        for partner in self:
            if partner.company_id:
                partner.currency_id = partner.sudo().company_id.currency_id
            else:
                self.id = self.env.company.currency_id
                partner.currency_id = self.id

    @api.onchange('expense_type_id')
    def _onchange_expense_type_id(self):
        for rec in self:
            if rec.expense_type_id.user_ids:
                rec.user_ids = rec.expense_type_id.user_ids.ids

    @api.onchange('user_id')
    def _calculate_pending(self):
        petty_cash_expense_id = self.env['petty.cash.expense'].search(
            [('user_id', '=', self.user_id.id)])
        self.pending_amount = sum(petty_cash_expense_id.mapped('amount'))

    @api.onchange("credit_id")
    def _compute_journal_id(self):
        if self.credit_id:
            self.journal_id = self.env['account.journal'].search([('default_account_id', '=', self.credit_id.id)])

    # @api.onchange("analytic_distribution")
    # def _compute_analytic(self):
    #     if self.analytic_distribution:
    #         self.account_analytic = list(map(int, self.analytic_distribution.keys()))
    #     else:
    #         self.account_analytic = None

    # account_analytic = fields.Many2many('account.analytic.account', store="True",
    #                                     string='Analytic Account')

    def _compute_group_officer(self):
        self.group_officer = self.env.user.has_group('petty_cash_management.group_officer')

    # @api.depends('journal_id')
    # def _compute_currency_id(self):
    #     for pay in self:
    #         pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id

    @api.depends('currency_id', 'amount')
    def _compute_check_amount_in_words(self):
        for pay in self:
            if pay.currency_id:
                pay.check_amount_in_words = pay.currency_id.amount_to_text(pay.amount)
            else:
                pay.check_amount_in_words = False

    # def compute_bill(self):
    #     for rec in self:
    #         bill_id = self.env['account.move'].search([('petty_cash_id', '=', rec.id)])
    #         if bill_id:
    #             rec.bill_ref = bill_id.name
    #             rec.bill_id = bill_id.id
    #             rec.bill_state = 'billed'
    #             rec.invoice_amount = bill_id.amount_total
    #         else:
    #             rec.bill_ref = rec.bill_id = False
    #             rec.bill_state = 'new'
    #             rec.invoice_amount = 0

    @api.onchange('user_id')
    def _calculate_in_hand_petty_cash(self):
        petty_cash_amount = 0
        add_petty_cash_amount = 0
        for recrd in self:
            employee_id = recrd.user_id.employee_id
            if employee_id:
                if employee_id.petty_cash:
                    # petty_cash_expense_id = self.env['petty.cash.expense'].search(
                    #     [('user_id', '=', recrd.user_id.id), ('state', '=', 'approved')])
                    # add_petty_cash_id = self.env['add.petty.cash'].search(
                    #     [('user_id', '=', recrd.user_id.id), ('status', '=', 'confirm')])
                    # petty_cash_amount = sum(petty_cash_expense_id.mapped('amount'))
                    # add_petty_cash_amount = sum(add_petty_cash_id.mapped('amount'))
                    # recrd.in_hand_petty_cash = add_petty_cash_amount - petty_cash_amount
                    recrd.in_hand_petty_cash = recrd.user_id.employee_id.petty_cash.current_balance
                else:
                    raise ValidationError(
                        _("Please configure petty cash under the employee '%s', contact Administrator",
                          employee_id.name))
            else:
                raise ValidationError(
                    _("The User '%s' Have no employee please assign user under the employee , Contact Administrator",
                      recrd.user_id.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.expense') or _('New')
        return super().create(vals_list)

    def action_button_send_back(self):
        state_map = {
            'approved': 'verified',
            'verified': 'waiting',
            'waiting': 'draft',
        }
        for rec in self:
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'petty.cash.expense')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            new_state = state_map.get(rec.state)
            if new_state:
                rec.state = new_state

    def action_send_to_authorizer(self):
        for rec in self:
            if not rec.message_main_attachment_id:
                raise ValidationError(_("Please add the required attachments to proceed."))
            rec.write({'state': 'waiting'})

    def action_button_verify(self):
        for rec in self:
            if not rec.message_main_attachment_id:
                raise ValidationError(_("Please add the required attachments to proceed."))
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'petty.cash.expense')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            rec.write({'state': 'verified'})

    def action_button_approve(self):
        for rec in self:
            if not rec.message_main_attachment_id:
                raise ValidationError(_("Please add the required attachments to proceed."))
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'petty.cash.expense')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            rec.write({'state': 'approved'})

    def approve_officer(self):
        if not self.message_main_attachment_id:
            raise ValidationError(_("Please add the required attachments to proceed."))
        if self.invoice_amount and self.invoice_amount != self.amount:
            raise UserError(_("The Invoice Amount is not equal to Expense Amount"))

        if not self.journal_id and self.debit_id:
            raise UserError(_("Journal/Debit account is required"))

        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'petty.cash.expense')]).id
        # Remove Old Activities related to the current record
        self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id),
        ]).unlink()

        if not self.journal_entry_id:
            journal = self.create_journal_entry()
        self.write({'state': 'posted'})

    def approve_finance(self):
        if not self.message_main_attachment_id:
            raise ValidationError(_("Please add the required attachments to proceed."))
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'petty.cash.expense')]).id
        # Remove Old Activities related to the current record
        self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id),
        ]).unlink()
        self.write({'state': 'posted'})
        journal = self.create_journal_entry()

    def create_journal_entry(self):
        if not self.debit_id:
            raise UserError(_("Debit Account is required"))
        name = 'Petty Cash Expense' + '-' + str(self.user_id.name) + '-' + self.name
        if self.invoice_number:
            name += ' - Inv no - ' + self.invoice_number
        if self.expense:
            name += ' - ' + self.expense
        journal_rec = self.env['account.move'].create({
            'move_type': 'entry',
            'ref': 'Petty Cash Expense' + '-' + str(self.user_id.name) + '-' + self.name,
            'date': self.date,
            'journal_id': self.journal_id.id,
            'line_ids': [
                (0, 0, {
                    'name': name,
                    'debit': self.amount,
                    'credit': 0,
                    'account_id': self.debit_id.id,
                    'analytic_distribution': self.analytic_distribution,
                    'tax_ids': self.tax_ids.ids if self.amount > 0 else False,
                }),
                (0, 0, {
                    'name': 'PettyExpenseExpense' + '-' + str(self.user_id.name) + '-' + self.name,
                    'debit': 0,
                    'credit': self.amount,
                    'account_id': self.credit_id.id,
                    'tax_ids': self.tax_ids.ids if self.amount < 0 else False,
                }),
            ],
        })
        journal_rec.action_post()
        self.journal_entry_id = journal_rec.id

    def send_for_finance_approval(self):
        self.state = 'pending_finance_approval'

    def reject(self):
        view = self.env.ref('petty_cash_management.reject_reason_form_view')
        action = {
            'type': 'ir.actions.act_window',
            'name': 'View Reason',
            'res_model': 'reject.reason',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [[view.id, 'form']],
            'target': 'new',
        }
        return action

    def reset_to_draft(self):
        self.state = 'draft'

    def cancel(self):
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'petty.cash.expense')]).id
        # Remove Old Activities related to the current record
        self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id),
        ]).unlink()
        self.state = 'cancel'
        self.journal_entry_id.button_cancel()

    def create_bill(self):
        return {
            'name': _("Vendor Bill"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'domain': '[]',
            'context': {
                'default_move_type': "in_invoice",
                'default_analytic_distribution': self.analytic_distribution,
                'default_petty_cash_id': self.id,
                'default_ref': self.invoice_number,
                'default_invoice_date': self.bill_date,
                'default_date': self.date,
            }}

        # self.write({'bill_ref': moves.name})
        # record.bill_state = 'billed'


class RejectReason(models.TransientModel):
    _name = 'reject.reason'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Reject Reason Wizard"

    name = fields.Char('Reason', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        reasons = super(RejectReason, self).create(vals_list)
        for vals in vals_list:
            if self.env.context.get('active_id') and self.env.context.get('active_model') == 'petty.cash.expense':
                petty_id = self.env['petty.cash.expense'].browse(self.env.context.get('active_id'))
                if petty_id.id:
                    msg = "<strong>Rejected Reason: </strong>" + vals['name']
                    petty_id.message_post(body=msg)
        return reasons

    def action_reject(self):
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'petty.cash.expense':
            petty_id = self.env['petty.cash.expense'].browse(self.env.context.get('active_id'))
            if petty_id:
                petty_id.state = 'reject'


class CancelReason(models.TransientModel):
    _name = 'cancel.reason'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Cancel Reason Wizard"

    name = fields.Char('Reason', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        reasons = super(CancelReason, self).create(vals_list)
        for vals in vals_list:
            if self.env.context.get('active_id'):
                model_id = self.env[self.env.context["active_model"]].browse(self.env.context.get('active_id'))
                if model_id.id:
                    msg = "<strong>Canceled Reason: </strong>" + vals['name']
                    model_id.message_post(body=msg)
        return reasons

    def action_cancel(self):
        if self.env.context.get('active_id'):
            model_id = self.env[self.env.context["active_model"]].browse(self.env.context.get('active_id'))
            if self.env.context["active_model"] == 'add.petty.cash':
                if model_id.journal_id:
                    model_id.journal_id.button_draft()
                    model_id.journal_id.button_cancel()
                model_id.status = 'cancel'
            else:
                model_id.state = 'cancel'
                model_id.payment_id.action_cancel()
                # self.journal_id.button_cancel()


class AddPettyCash(models.Model):
    _name = 'add.petty.cash'
    _description = "Add Petty Cash"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']

    name = fields.Char(string='Number', required=True, readonly=True, default=lambda self: _('New'))
    user_id = fields.Many2one(comodel_name='res.users', string="User", default=lambda self: self.env.user,
                              tracking=True)
    amount = fields.Float(string="Amount", required=True, readonly=True, digits=(12, 3), tracking=True)
    date = fields.Date(string='Accounting Date', default=lambda self: fields.Date.today())
    cheque_date = fields.Date(string="Cheque Date", tracking=True)
    journal = fields.Many2one('account.journal', string='Journal', required=True, tracking=True,
                              default=lambda self: self.env['account.journal'].search(
                                  [('name', '=', 'Miscellaneous Operations')]))
    status = fields.Selection([('draft', 'Draft'), ('waiting', 'Checked'), ('verified', 'Verified'),
                               ('confirm', 'Approved'), ('cancel', 'Cancelled'), ], 'Status', readonly=True,
                              required=True, copy=False, tracking=True, default="draft")
    memo = fields.Char(string='Label')
    cheque_number = fields.Char(string='Cheque Number')
    debit = fields.Many2one('account.account', store=True, string='Debit Account',
                            related='user_id.employee_id.petty_cash', precompute=True)
    credit = fields.Many2one('account.account', string='Credit Account')
    journal_id = fields.Many2one(comodel_name='account.move', string='Journal Entry')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', compute='_get_company_currency',
                                  readonly=True, precompute=True, store=True, help="The payment's currency.")
    # compute = '_compute_currency_id',
    in_hand_petty_cash = fields.Float(string='In Hand Petty Cash', compute='_calculate_in_hand_petty_cash',
                                      digits=(12, 3), tracking=True)
    check_amount_in_words = fields.Char(string="Amount in Words", store=True,
                                        compute='_compute_check_amount_in_words', )
    analytic_distribution = fields.Json("Analytic Distribution", store=True, tracking=True)

    # analytic_precision = fields.Integer(
    #     store=True,
    #     default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    # )access_res_currency_account_manager,res.currency account manager,base.model_res_currency,group_account_manager,1,1,1,1

    def _get_company_currency(self):
        for partner in self:
            if partner.company_id:
                partner.currency_id = partner.sudo().company_id.currency_id
            else:
                self.id = self.env.company.currency_id
                partner.currency_id = self.id

    @api.onchange('user_id')
    def _calculate_in_hand_petty_cash(self):
        petty_cash_amount = 0
        add_petty_cash_amount = 0

        for rec in self:
            employee_id = rec.user_id.employee_id
            if employee_id:
                if employee_id.petty_cash:
                    # petty_cash_expense_id = self.env['petty.cash.expense'].search(
                    #     [('user_id', '=', recrd.user_id.id), ('state', '=', 'approved')])
                    # add_petty_cash_id = self.env['add.petty.cash'].search(
                    #     [('user_id', '=', recrd.user_id.id), ('status', '=', 'confirm')])
                    # petty_cash_amount = sum(petty_cash_expense_id.mapped('amount'))
                    # add_petty_cash_amount = sum(add_petty_cash_id.mapped('amount'))
                    # recrd.in_hand_petty_cash = add_petty_cash_amount - petty_cash_amount
                    rec.in_hand_petty_cash = employee_id.petty_cash.current_balance
                else:
                    raise ValidationError(
                        _("Please configure petty cash under the employee '%s', contact Administrator",
                          employee_id.name))
            else:
                raise ValidationError(
                    _("The User '%s' Have no employee please assign user under the employee, contact Administrator",
                      rec.user_id.name))

    @api.onchange('status')
    def _cancel_journal(self):
        if self.status == 'cancel':
            self.journal_id.button_cancel()

    # @api.depends('journal')
    # def _compute_currency_id(self):
    #     for pay in self:
    #         pay.currency_id = pay.journal.currency_id or pay.journal.company_id.currency_id

    @api.depends('currency_id', 'amount')
    def _compute_check_amount_in_words(self):
        for pay in self:
            if pay.currency_id:
                pay.check_amount_in_words = pay.currency_id.amount_to_text(pay.amount)
            else:
                pay.check_amount_in_words = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('add.petty.cash') or _('New')
        return super().create(vals_list)

    def action_button_send_back(self):
        state_map = {
            'verified': 'waiting',
            'waiting': 'draft',
        }
        for rec in self:
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'add.petty.cash')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            new_state = state_map.get(rec.status)
            if new_state:
                rec.status = new_state

    def action_send_authorizer(self):
        if self.amount <= 0:
            raise ValidationError(_("The Amount should be Greater than Zero !"))
        # if self.message_attachment_count == 0:
        #     raise ValidationError(_("Please upload attachments for Authorizer approval."))
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'add.petty.cash')]).id
        # Remove Old Activities related to the current record
        self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id),
        ]).unlink()
        self.write({'status': 'waiting'})

    def action_button_verify(self):
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'add.petty.cash')]).id
        # Remove Old Activities related to the current record
        self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id),
        ]).unlink()
        self.write({'status': 'verified'})

    def confirm(self):
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'add.petty.cash')]).id
        # Remove Old Activities related to the current record
        self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id),
        ]).unlink()
        self.write({'status': 'confirm'})
        self._create_journal_entry()
        self.journal_id.action_post()

    def _create_journal_entry(self):
        name = 'AddPettyCash' + '-' + str(self.user_id.name) + '-' + self.name
        if self.memo:
            name = name + '- Memo' + '-' + self.memo
        if self.cheque_number:
            name = name + '- Cheque' + '-' + self.cheque_number
        journal_entry_rec = self.env['account.move'].create({
            'move_type': 'entry',
            'ref': 'AddPettyCash' + '-' + str(self.user_id.name) + '-' + self.name,
            'date': self.date,
            'journal_id': self.journal.id,
            'cheque_no': self.cheque_number,
            'line_ids': [
                (0, 0, {
                    'name': name,
                    'debit': self.amount,
                    'analytic_distribution': self.analytic_distribution,
                    'credit': 0,
                    'account_id': self.debit.id,
                }),
                (0, 0, {
                    'name': name,
                    'debit': 0,
                    'credit': self.amount,
                    'account_id': self.credit.id,
                }),
            ],
        })
        self.journal_id = journal_entry_rec.id

    def reset_to_draft(self):
        self.status = 'draft'

    def cancel(self):
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'add.petty.cash')]).id
        # Remove Old Activities related to the current record
        self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id),
        ]).unlink()
        view = self.env.ref('petty_cash_management.cancel_reason_form_view')
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Cancel Reason',
            'res_model': 'cancel.reason',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [[view.id, 'form']],
            'target': 'new',
        }
        return action


class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    petty_cash = fields.Many2one('account.account', string='Petty cash')


class HrEmployeePettyCashInherit(models.Model):
    _inherit = 'hr.employee.public'

    petty_cash = fields.Many2one('account.account', string='Petty cash')


class IrAttachmentInherit(models.Model):
    _inherit = 'ir.attachment'

    def unlink(self):
        for attachment in self:
            # Check if the attachment is related to the Add Petty Cash model
            if attachment.res_model == 'petty.cash.expense':
                attachments = self.search([
                    ('res_model', '=', attachment.res_model),
                    ('res_id', '=', attachment.res_id),
                    ('id', '!=', attachment.id)
                ])
                # Check if have no attachment
                if not attachments:
                    raise UserError(
                        _('You cannot delete the last attachment. Please upload a new one before deleting this.'))
        return super(IrAttachmentInherit, self).unlink()
