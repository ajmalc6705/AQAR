# -*- coding: utf-8 -*-

import datetime
from odoo import fields, models, api, _
from odoo.exceptions import UserError


# class PropertyVoucher(models.Model):
#     _inherit = 'account.voucher'
#     _name = 'property.voucher'
#     _description = _('Property Voucher Details')
#
#     @api.depends('cost_center_id', 'amount')
#     def _compute_total_amount(self):
#         for voucher in self:
#             if voucher.cost_center_id:
#                 voucher.total_amount = self.amount
#             else:
#                 for i in voucher.line_ids:
#                     voucher.total_amount += i.amount
#
#     contract_id = fields.Many2one(comodel_name='property.contract', string='Contract Number',
#                                   readonly=True, copy=True,
#                                   states={'draft': [('readonly', False)]})
#     agreement_id = fields.Many2one(comodel_name='property.rent', string='Rent Agreement Number',
#                                    readonly=True, copy=True,
#                                    states={'draft': [('readonly', False)]})
#     sale_agreement_id = fields.Many2one(comodel_name='property.sale', string='Sale Agreement Number',
#                                         readonly=True, copy=True,
#                                         states={'draft': [('readonly', False)]})
#     cost_center_id = fields.Many2one(comodel_name='account.analytic.account', string='Cost Center Name',
#                                      readonly=True, copy=True,
#                                      states={'draft': [('readonly', False)]})
#     property_id = fields.Many2one(comodel_name='property.property', string='Flat/Villa',
#                                   readonly=True, copy=True)
#     expense_category_id = fields.Many2one(comodel_name='property.maintenance.type', string='Expense Category',
#                                           readonly=True, copy=True,
#                                           states={'draft': [('readonly', False)]})
#     income_category_id = fields.Many2one(comodel_name='property.income.type', string='Income Category',
#                                          readonly=True, copy=True,
#                                          states={'draft': [('readonly', False)]})
#     account_type = fields.Char(string='Account Type', readonly=True, copy=True,
#                                states={'draft': [('readonly', False)]})
#     cash_or_cheque = fields.Selection([('cash', _('Cash')), ('cheque', _('Cheque')), ('transfer', _('Transfer'))],
#                                       string='Cash/Cheque', readonly=True, copy=True,
#                                       states={'draft': [('readonly', False)]})
#     bank_name = fields.Char(string='Bank Name', readonly=True, copy=True,
#                             states={'draft': [('readonly', False)]})
#     # 'cheque_number_contra = fields.Char(_('Cheque No (IF)'), readonly=True, copy=True,
#     #                              states={'draft': [('readonly', False)]}),
#     # alsabla changes
#     cheque_number = fields.Many2one(comodel_name='property.rent.installment.collection', string='Cheque No (IF)',
#                                     readonly=True, copy=True, states={'draft': [('readonly', False)]},
#                                     domain="[('rent_id', '=', agreement_id),('state', '=', 'draft')]")
#     # end
#     installment_type = fields.Selection([('installment', _('Installment')),
#                                          ('fee', _('Fee')),
#                                          ('deposit', _('Deposit')),
#                                          ('advance', _('Advance'))], string='Installment Type', required=False,
#                                         readonly=True, states={'draft': [('readonly', False)]}),
#     line_ids = fields.One2many(comodel_name='property.voucher.line', inverse_name='voucher_id', string='Voucher Lines',
#                                readonly=True, copy=True,
#                                states={'draft': [('readonly', False)]}),
#     total_amount = fields.Float(string='Total Amount', digits='Property', compute='_compute_total_amount')
#
#     # alsabla customisation
#     @api.onchange('cheque_number')
#     def onchange_cheque_number(self):
#         if self.cash_or_cheque:
#             self.amount = self.cheque_number.amount
#
#     # end
#
#     def cancel_voucher(self, cr, uid, ids, context=None):
#         installment_obj = self.pool.get('property.contract.installment')
#         current_rec = self.browse(cr, uid, ids)
#         if current_rec.contract_id:
#             move_id = current_rec.move_id.id
#             installment_id = installment_obj.search(cr, uid, [('move_id', '=', move_id)])
#             installment_obj.unlink(cr, uid, installment_id)
#
#         res = super(PropertyVoucher, self).cancel_voucher(cr, uid, ids, context)
#         return res
#
#     @api.onchange('contract_id', 'agreement_id', 'sale_agreement_id')
#     def _onchange_contract_id(self):
#         if self.agreement_id:
#             self.partner_id = self.agreement_id.partner_id.id
#             self.property_id = self.agreement_id.property_id.id
#             self.cost_center_id = self.agreement_id.property_id.cost_center_id.id
#         elif self.contract_id:
#             self.partner_id = self.contract_id.partner_id.id
#             self.property_id = self.contract_id.property_id.id
#             self.cost_center_id = self.contract_id.property_id.cost_center_id.id
#         elif self.sale_agreement_id:
#             self.partner_id = self.sale_agreement_id.buyer_id.id
#             self.property_id = self.sale_agreement_id.property_id.id
#             self.cost_center_id = self.sale_agreement_id.property_id.cost_center_id.id
#
#     def proforma_voucher(self):
#         self.check_cost_center_budget()
#
#         period_obj = self.env['account.period']
#         move_line_obj = self.env['account.move.line']
#         seq_obj = self.env['ir.sequence']
#         property_id = self.property_id.id or self.contract_id.property_id.id or self.agreement_id.property_id.id or \
#                       self.sale_agreement_id.property_id.id
#         period_ids = period_obj.find(dt=self.date)
#         # period_ids = self.invoice_id and self.invoice_id.period_id and self.invoice_id.period_id.ids
#         from_date = datetime.datetime.strptime(self.date, '%Y-%m-%d')
#         invoice = self.env['account.invoice'].search(
#             [('rent_id', '=', self.agreement_id.id), ('rental_period_id', '=', self.rent_period_id.id)])
#         if self.journal_id.sequence_id:
#             if not self.journal_id.sequence_id.active:
#                 raise UserError(_('Configuration Error !\nPlease activate the sequence of selected journal !'))
#             name = seq_obj.next_by_id(self.journal_id.sequence_id.id)
#         else:
#             raise UserError(_('Please define a sequence on the journal.'))
#
#         move_data = {
#             'name': name,
#             'journal_id': self.journal_id.id,
#             'date': from_date,
#             'narration': self.name,
#             'ref': self.contract_id.name or self.agreement_id.name or self.sale_agreement_id.name or name,
#             'property_id': property_id,
#             'period_id': period_ids[0].id,
#             'contract_id': self.contract_id.id,
#             'agreement_id': self.agreement_id.id,
#             'sale_agreement_id': self.sale_agreement_id.id,
#         }
#         move = self.env['account.move'].create(move_data)
#         if self.type == 'payment':
#             if self.cost_center_id:
#                 move_line1 = self.create_move_line(move, period_ids, from_date)
#                 move_line1['credit'] = self.amount
#                 # move_line1['invoice'] = invoice.id
#                 move_line1['account_id'] = self.journal_id.default_credit_account_id.id
#                 move_line1['name'] = self.name or '/'
#                 line1 = move_line_obj.create(move_line1)
#                 move_line2 = self.create_move_line(move, period_ids, from_date)
#                 move_line2['debit'] = self.amount
#                 move_line2['invoice'] = invoice.id
#                 line2 = move_line_obj.create(move_line2)
#                 move.post()
#                 self.write({'number': move.name,
#                             'move_id': move.id,
#                             'move_ids': [(4, line1.id), (4, line2.id)],
#                             'state': 'posted'})
#                 if self.contract_id.id:
#                     self.create_installment()
#                     self.create_payment_lines(line2.id)
#                     invoice.payment_ids = [(4, line2)]
#             elif self.line_ids:
#
#                 self.write({'number': move.name,
#                             'move_id': move.id,
#                             'state': 'posted'})
#                 for i in self.line_ids:
#                     move_line1 = self.create_move_line(move, period_ids, i.cheque_date)
#                     move_line1['credit'] = i.amount
#                     # move_line1['invoice'] = invoice.id
#                     move_line1['account_id'] = self.journal_id.default_credit_account_id.id
#                     move_line1['name'] = i.description or '/'
#                     move_line1['cost_center_id'] = i.cost_center_id.id
#                     move_line1['expense_category_id'] = i.expense_category_id.id
#                     line1 = move_line_obj.create(move_line1)
#                     move_line2 = self.create_move_line(move, period_ids, i.cheque_date)
#                     move_line2['debit'] = i.amount
#                     move_line2['invoice'] = invoice.id
#                     move_line2['account_id'] = i.account_id.id
#                     move_line2['cost_center_id'] = i.cost_center_id.id
#                     move_line2['expense_category_id'] = i.expense_category_id.id
#                     line2 = move_line_obj.create(move_line2)
#                     amount = self.amount + i.amount
#                     self.write({'move_ids': [(4, line1.id), (4, line2.id)], 'amount': amount})
#                 move.post()
#
#         else:
#             if self.cost_center_id:
#                 move_line1 = self.create_move_line(move, period_ids, from_date)
#                 move_line1['credit'] = self.amount
#                 move_line1['name'] = self.name or '/'
#                 move_line1['invoice'] = invoice.id
#                 line1 = move_line_obj.create(move_line1)
#                 move_line2 = self.create_move_line(move, period_ids, from_date)
#                 move_line2['debit'] = self.amount
#                 move_line2['invoice'] = invoice.id
#                 move_line2['account_id'] = self.journal_id.default_debit_account_id.id
#                 line2 = move_line_obj.create(move_line2)
#
#                 self.write({'number': move.name,
#                             'move_id': move.id,
#                             'move_ids': [(4, line1.id), (4, line2.id)],
#                             'state': 'posted'})
#                 if self.agreement_id.id or self.sale_agreement_id.id:
#                     self.create_installment()
#                     self.create_payment_lines(line2.id)
#                     # self.env['account.invoice'].browse(invoice.id).payment_ids = [(4, line2)]
#                     mov_line_1 = self.env['account.move.line'].search(
#                         [('move_id', '=', invoice.move_id.id), ('debit', '=', invoice.amount_total)])
#                     # move_data['debit'] = self.amount
#                     # move_data['account_id'] = self.journal_id.default_debit_account_id.id
#                     # move_data['partner_id'] = self.partner_id.id
#                     # line1['debit'] = self.amount
#                     line_pool = self.env['account.move.line'].search([('id', 'in', (mov_line_1.id, line1.id))])
#                     line_pool.reconcile_partial([[mov_line_1.id, line1.id]])
#                     move.post()
#                     # invoice.payment_ids = [(4, line2)]
#             elif self.line_ids:
#                 self.write({'number': move.name,
#                             'move_id': move.id,
#                             'state': 'posted'})
#                 for i in self.line_ids:
#                     move_line1 = self.create_move_line(move, period_ids, i.cheque_date)
#                     move_line1['credit'] = i.amount
#                     move_line1['name'] = i.description or '/'
#                     move_line1['invoice'] = invoice.id
#                     move_line1['account_id'] = i.account_id.id
#                     move_line1['cost_center_id'] = i.cost_center_id.id
#                     move_line1['income_category_id'] = i.income_category_id.id
#                     line1 = move_line_obj.create(move_line1)
#                     move_line2 = self.create_move_line(move, period_ids, i.cheque_date)
#                     move_line2['debit'] = i.amount
#                     move_line2['invoice'] = invoice.id
#                     move_line2['account_id'] = self.journal_id.default_debit_account_id.id
#                     move_line2['cost_center_id'] = i.cost_center_id.id
#                     move_line2['income_category_id'] = i.income_category_id.id
#                     line2 = move_line_obj.create(move_line2)
#                     amount = self.amount + i.amount
#                     self.write({'move_ids': [(4, line1.id), (4, line2.id)], 'amount': amount})
#                 move.post()
#         return True
#
#     def button_proforma_voucher(self, ):
#         # if not self.rent_period_id:
#         #     raise Warning('Set period(s) for payment')
#         if self.amount or self.line_ids:
#             self.proforma_voucher()
#         else:
#             raise UserError(_('You can not validate a voucher without Amount or Voucher Lines!'))
#
#     def create_installment(self, ):
#         installment_data = {
#             'sequence': self.get_sequence(),
#             'partner_id': self.partner_id.id,
#             'amount': self.amount,
#             'date': self.date,
#             'cash_or_cheque': self.cash_or_cheque,
#             'bank_name': self.bank_name,
#             # customisation in alsabla
#             'cheque_number': self.cheque_number,
#             # end
#             'move_id': self.move_id.id,
#             'receipt_number': 0,
#             'state': 'open',
#             'installment_type': self.installment_type or 'installment',
#
#         }
#         if self.contract_id.id:
#             installment_data['contract_id'] = self.contract_id.id
#             self.env['property.contract.installment'].create(installment_data)
#         elif self.agreement_id.id:
#             installment_data['rent_id'] = self.agreement_id.id
#             # alsabla customisation for relating payment to cheque collected
#             installment_data['cheque_number'] = installment_data['cheque_number'].cheque_number
#             if self.agreement_id.collection_ids:
#                 if self.cash_or_cheque == 'cheque':
#                     collection_id = self.agreement_id.collection_ids.search([('id', '=', self.cheque_number.id)])
#                     collection_id.state = 'paid'
#             # end
#
#             self.env['property.rent.installment'].create(installment_data)
#         else:
#             installment_data['sale_id'] = self.sale_agreement_id.id
#             self.env['property.sale.installment'].create(installment_data)
#
#     def get_sequence(self):
#         if self.contract_id.id:
#             no = len(self.env['property.contract'].browse(self.contract_id.id).installment_ids)
#         elif self.agreement_id.id:
#             no = len(self.env['property.rent'].browse(self.agreement_id.id).installment_ids)
#         else:
#             no = len(self.env['property.sale'].browse(self.sale_agreement_id.id).installment_ids)
#         return no + 1
#
#     def create_payment_lines(self, line_id):
#         if self.contract_id.id:
#             self.env['property.contract'].browse(self.contract_id.id).payment_ids = [(4, line_id)]
#         elif self.agreement_id.id:
#             self.env['property.rent'].browse(self.agreement_id.id).payment_ids = [(4, line_id)]
#         else:
#             self.env['property.sale'].browse(self.sale_agreement_id.id).payment_ids = [(4, line_id)]
#
#     def create_move_line(self, move, period_ids, from_date):
#         move_line = {
#             'name': '/',
#             'debit': 0.0,
#             'credit': 0.0,
#             'account_id': self.account_id.id,
#             'move_id': move.id,
#             'journal_id': self.journal_id.id,
#             'period_id': period_ids[0].id,
#             'partner_id': self.partner_id.id,
#             'date': from_date,
#         }
#         return move_line
#
#     def check_cost_center_budget(self):
#         if self.type == 'payment':
#             if self.cost_center_id and self.account_id.user_type.code == 'expense':
#                 query = """SELECT COALESCE(sum(ml.debit), 0)
#                 FROM account_move_line ml
#                 LEFT JOIN account_account a on(ml.account_id=a.id)
#                 LEFT JOIN account_account_type t on(t.id=a.user_type)
#                 WHERE ml.cost_center_id = %s AND t.code = 'expense'
#                 """
#                 self._cr.execute(query, (self.cost_center_id.id,))
#                 total = self._cr.fetchone()[0]
#                 if self.amount + total > self.cost_center_id.current_year_budget:
#                     raise UserError(_('You have exceeded the current year budget for the selected cost center!'))
#         return True
#
#
# class AccountVoucherMaster(models.Model):
#     _inherit = 'account.voucher'
#
#     def onchange_date(self, cr, uid, ids, date, currency_id, payment_rate_currency_id, amount, company_id,
#                       context=None):
#         """
#         @param date: latest value from user input for field date
#         @param args: other arguments
#         @param context: context arguments, like lang, time zone
#         @return: Returns a dict which contains new values, and context
#         """
#         if context is None:
#             context = {}
#         res = {'value': {}}
#         # set the period of the voucher
#         period_pool = self.pool.get('account.period')
#         currency_obj = self.pool.get('res.currency')
#         ctx = context.copy()
#         ctx.update({'company_id': company_id, 'account_period_prefer_normal': True})
#         voucher_currency_id = currency_id or self.pool.get('res.company').browse(cr, uid, company_id,
#                                                                                  context=ctx).currency_id.id
#         pids = period_pool.find(cr, uid, date, context=ctx)
#         if pids:
#             res['value'].update({'period_id': pids[0]})
#         if payment_rate_currency_id:
#             ctx.update({'date': date})
#             payment_rate = 1.0
#             if payment_rate_currency_id != currency_id:
#                 tmp = currency_obj.browse(cr, uid, payment_rate_currency_id, context=ctx).rate
#                 payment_rate = tmp / currency_obj.browse(cr, uid, voucher_currency_id, context=ctx).rate
#             vals = self.onchange_payment_rate_currency(cr, uid, ids, voucher_currency_id, payment_rate,
#                                                        payment_rate_currency_id, date, amount, company_id,
#                                                        context=context)
#             vals['value'].update({'payment_rate': payment_rate})
#             for key in vals.keys():
#                 res[key].update(vals[key])
#         return res
#
#     def onchange_journal(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id,
#                          context=None):
#         if context is None:
#             context = {}
#         if not journal_id:
#             return False
#         journal_pool = self.pool.get('account.journal')
#         journal = journal_pool.browse(cr, uid, journal_id, context=context)
#         if ttype in ('sale', 'receipt'):
#             account_id = journal.default_debit_account_id
#         elif ttype in ('purchase', 'payment'):
#             account_id = journal.default_credit_account_id
#         else:
#             account_id = journal.default_credit_account_id or journal.default_debit_account_id
#         tax_id = False
#         if account_id and account_id.tax_ids:
#             tax_id = account_id.tax_ids[0].id
#
#         vals = {'value': {}}
#         if ttype in ('sale', 'purchase'):
#             vals = self.onchange_price(cr, uid, ids, line_ids, tax_id, partner_id, context)
#             vals['value'].update({'tax_id': tax_id, 'amount': amount})
#         currency_id = False
#         if journal.currency:
#             currency_id = journal.currency.id
#         else:
#             currency_id = journal.company_id.currency_id.id
#         if not context.get('period_id', False):
#             period_ids = self.pool['account.period'].find(cr, uid, dt=date,
#                                                           context=dict(context, company_id=company_id))
#         else:
#             period_ids = [context.get('period_id')]
#         vals['value'].update({
#             'currency_id': currency_id,
#             'payment_rate_currency_id': currency_id,
#             'period_id': period_ids and period_ids[0] or False
#         })
#         # in case we want to register the payment directly from an invoice, it's confusing to allow to switch the journal
#         # without seeing that the amount is expressed in the journal currency, and not in the invoice currency. So to avoid
#         # this common mistake, we simply reset the amount to 0 if the currency is not the invoice currency.
#         if context.get('payment_expected_currency') and currency_id != context.get('payment_expected_currency'):
#             vals['value']['amount'] = 0
#             amount = 0
#         if partner_id:
#             res = self.onchange_partner_id(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date,
#                                            context)
#             for key in res.keys():
#                 vals[key].update(res[key])
#         return vals
#
#
# class PropertyVoucherLine(models.Model):
#     _name = 'property.voucher.line'
#
#     voucher_id = fields.Many2one(comodel_name='property.voucher', string='Voucher',
#                                  required=1, ondelete='cascade')
#     account_id = fields.Many2one(comodel_name='account.account', string='Account', required=True)
#     cost_center_id = fields.Many2one(comodel_name='account.analytic.account', string='Cost Center',
#                                      required=True)
#     cheque_date = fields.Date(string='Cheque Date', default=fields.Date.today)
#     description = fields.Char(string='Description')
#     cheque_number = fields.Char(string='Cheque No (IF)')
#     amount = fields.Float(string='Amount', digits='Property')
#     expense_category_id = fields.Many2one(comodel_name='property.maintenance.type', string='Expense Category')
#     income_category_id = fields.Many2one(comodel_name='property.income.type', string='Income Category')
#     company_id = fields.Many2one(comodel_name='res.company', related='voucher_id.company_id',
#                                  string='Company', store=True, readonly=True)

# class AccountVoucherLines(models.Model):
#     _inherit = 'account.voucher.line'
#
#     analytic_account_id = fields.Many2one('account.analytic.account', string='Cost Center', copy=False)


# class AccountVoucher(models.Model):
#     _inherit = 'account.voucher'
#
#     inv_id = fields.Many2one(comodel_name='account.invoice')
#
#     def cancel_voucher(self):
#         """
#         Cancelling Voucher will add Cheque number in Cancelled Cheques.
#         :return:
#         """
#         res = super(AccountVoucher, self).cancel_voucher()
#         obj_collection = self.env['property.rent.installment'].search([('voucher_id', '=', self.id)])
#         obj_collection.unlink()
#         obj_collection_ids = self.env['property.rent.installment.collection'].search([('invoice_id', '=', self.inv_id.id)])
#         for col in obj_collection_ids:
#             col.write({'state': 'draft'})
#         return res
#
#     def deselect(self):
#         """
#         Button to reset the auto matched entries.
#         :return:
#         """
#         if self._context.get('type', False) == 'payment':
#             for record in self.line_dr_ids.filtered(lambda rec: rec.amount > 0):
#                 record.amount = 0
#                 record.reconcile = False
#         if self._context.get('type', False) == 'receipt':
#             for record in self.line_cr_ids.filtered(lambda rec: rec.amount > 0):
#                 record.amount = 0
#                 record.reconcile = False
#         if self._context.get("default_rent_id", False):
#             return {
#                 'context': self.env.context,
#                 'view_type': 'form',
#                 'view_mode': 'form',
#                 'res_model': 'account.voucher',
#                 'res_id': self.id,
#                 'view_id': self.env.ref('account_voucher.view_vendor_receipt_dialog_form').id,
#                 'type': 'ir.actions.act_window',
#                 'target': 'new',
#             }
#         else:
#             return True
#
#     def save_draft(self):
#         """
#         Draft Accpount Receipt, Later to be a confirmed voucher after reconciliation
#         :return:
#         """
#         context = self.env.context
#         if 'default_rent_id' in context:
#             moves = self.line_cr_ids.filtered(lambda rec: rec.amount > 0)
#             if moves:
#                 installment = self.env['property.rent.installment.collection'].search([
#                     ('invoice_id', 'in',
#                      [inv.move_line_id.invoice.id for inv in moves])])
#                 installment.write({'state': 'draft'})
#                 invoices = self.line_cr_ids.filtered(lambda rec: rec.amount > 0).mapped(
#                     'move_line_id.invoice')
#                 for inv in invoices:
#                     installment = self.env['property.rent.installment.collection'].search(
#                         [('invoice_id', '=', inv.id)])
#                     if installment:
#                         total = 0
#                         for mov in self.line_cr_ids:
#                             if mov.move_line_id.invoice == inv:
#                                 total = mov.amount
#                         vals = {
#                             'sequence': len(
#                                 installment.rent_id.installment_ids) + 1 if installment.rent_id.installment_ids else 1,
#                             'partner_id': installment.invoice_id.partner_id.id,
#                             'amount': total,
#                             'date': self.date,
#                             'cash_or_cheque': 'cheque' if installment.cash_cheque == 'check' else installment.cash_cheque,
#                             'cheque_number': self.cheque_no,
#                             'installment_type': 'installment',
#                             'move_id': self.move_id.id,
#                             'voucher_id': self.id,
#                             'invoice_id': inv.id,
#                             'rent_id': installment.rent_id.id,
#                         }
#                         self.env['property.rent.installment'].create(vals)
#                     else:
#                         raise Warning(_('Error!'),
#                                       _('Link Invoice Before Posting.'))
#             return {'type': 'ir.actions.act_window_close'}
#
#     def button_proforma_voucher(self):
#         """
#         Payment Processing, Post the JE, Inv To Paid, Installments To Paid, Link Payments with RentAgreement
#         :return:
#         """
#         context = self.env.context
#         if 'default_rent_id' in context:
#             res = self.action_move_line_create()
#             if res:
#                 invoices = self.line_cr_ids.filtered(lambda rec: rec.amount > 0).mapped(
#                     'move_line_id.invoice')
#                 for inv in invoices:
#                     installments = self.env['property.rent.installment.collection'].search(
#                         [('invoice_id', '=', inv.id)])
#                 for installment in installments:
#                     installment.rent_id.payment_ids = [(4, rec.id) for rec in installment.invoice_id.payment_ids]
#                     if installment.invoice_id.state == 'paid':
#                         installment.state = 'paid'
#                         installment.period_ids.state = 'done'
#                 return {'type': 'ir.actions.act_window_close'}
#         else:
#             super(AccountVoucher, self).button_proforma_voucher()
#
#     def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
#         """
#         Returns a dict that contains new values and context
#
#         @param partner_id: latest value from user input for field partner_id
#         @param args: other arguments
#         @param context: context arguments, like lang, time zone
#
#         @return: Returns a dict which contains new values, and context
#         """
#         def _remove_noise_in_o2m():
#             """if the line is partially reconciled, then we must pay attention to display it only once and
#                 in the good o2m.
#                 This function returns True if the line is considered as noise and should not be displayed
#             """
#             if line.reconcile_partial_id:
#                 if currency_id == line.currency_id.id:
#                     if line.amount_residual_currency <= 0:
#                         return True
#                 else:
#                     if line.amount_residual <= 0:
#                         return True
#             return False
#
#         if context is None:
#             context = {}
#         context_multi_currency = context.copy()
#
#         currency_pool = self.pool.get('res.currency')
#         move_line_pool = self.pool.get('account.move.line')
#         partner_pool = self.pool.get('res.partner')
#         journal_pool = self.pool.get('account.journal')
#         line_pool = self.pool.get('account.voucher.line')
#
#         # set default values
#         default = {
#             'value': {'line_dr_ids': [], 'line_cr_ids': [], 'pre_line': False},
#         }
#
#         # drop existing lines
#         line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', ids[0])])
#         for line in line_pool.browse(cr, uid, line_ids, context=context):
#             if line.type == 'cr':
#                 default['value']['line_cr_ids'].append((2, line.id))
#             else:
#                 default['value']['line_dr_ids'].append((2, line.id))
#
#         if not partner_id or not journal_id:
#             return default
#
#         journal = journal_pool.browse(cr, uid, journal_id, context=context)
#         partner = partner_pool.browse(cr, uid, partner_id, context=context)
#         currency_id = currency_id or journal.company_id.currency_id.id
#
#         total_credit = 0.0
#         total_debit = 0.0
#         account_type = None
#         if context.get('account_id'):
#             account_type = self.pool['account.account'].browse(cr, uid, context['account_id'], context=context).type
#         if ttype == 'payment':
#             if not account_type:
#                 account_type = 'payable'
#             total_debit = price or 0.0
#         else:
#             total_credit = price or 0.0
#             if not account_type:
#                 account_type = 'receivable'
#
#         if not context.get('move_line_ids', False):
#             ids = move_line_pool.search(cr, uid, [('state','=','valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id)], context=context)
#         else:
#             ids = context['move_line_ids']
#         invoice_id = context.get('invoice_id', False)
#         company_currency = journal.company_id.currency_id.id
#         move_lines_found = []
#         # once invoice payment is in initial level of approval, then that invoice should not come in on next payment
#         # so we took all the move lines from voucher lines with full reconcile flag is set and remove them from the list
#         query = "SELECT vl.move_line_id FROM account_voucher_line vl " \
#                 "INNER JOIN account_move_line aml ON aml.id=vl.move_line_id " \
#                 "INNER JOIN account_voucher av ON av.id=vl.voucher_id  " \
#                 "INNER JOIN account_account aa ON aa.id=aml.account_id " \
#                 "WHERE vl.reconcile=True AND " \
#                 "aml.partner_id='" + str(partner_id) + "' " \
#                                                        "AND av.state IN ('with_head', 'senior_acc', 'finance_mng') " \
#                                                        "AND aa.type = '" + str(account_type) + "'"
#         # params = (partner_id,)
#         cr.execute(query)
#         move_lines = cr.dictfetchall()
#         for l in move_lines:
#             if l['move_line_id'] in ids:
#                 ids.remove(l['move_line_id'])
#
#         #order the lines by most old first
#         ids.reverse()
#         account_move_lines = move_line_pool.browse(cr, uid, ids, context=context)
#         # this is added to auto select the invoice payment, only for rent payment
#         if context.get('default_rent_id', False):
#             invoice_id = context.get('default_invoice_id', False)
#         #compute the total debit/credit and look for a matching open amount or invoice
#         for line in account_move_lines:
#             if _remove_noise_in_o2m():
#                 continue
#
#             if invoice_id:
#                 if line.invoice.id == invoice_id:
#                     #if the invoice linked to the voucher line is equal to the invoice_id in context
#                     #then we assign the amount on that line, whatever the other voucher lines
#                     move_lines_found.append(line.id)
#             elif currency_id == company_currency:
#                 #otherwise treatments is the same but with other field names
#                 if line.amount_residual == price:
#                     #if the amount residual is equal the amount voucher, we assign it to that voucher
#                     #line, whatever the other voucher lines
#                     move_lines_found.append(line.id)
#                     break
#                 #otherwise we will split the voucher amount on each line (by most old first)
#                 total_credit += line.credit or 0.0
#                 total_debit += line.debit or 0.0
#             elif currency_id == line.currency_id.id:
#                 if line.amount_residual_currency == price:
#                     move_lines_found.append(line.id)
#                     break
#                 total_credit += line.credit and line.amount_currency or 0.0
#                 total_debit += line.debit and line.amount_currency or 0.0
#
#         remaining_amount = price
#         #voucher line creation
#         for line in account_move_lines:
#
#             if _remove_noise_in_o2m():
#                 continue
#
#             if line.currency_id and currency_id == line.currency_id.id:
#                 amount_original = abs(line.amount_currency)
#                 amount_unreconciled = abs(line.amount_residual_currency)
#             else:
#                 #always use the amount booked in the company currency as the basis of the conversion into the voucher currency
#                 amount_original = currency_pool.compute(cr, uid, company_currency, currency_id, line.credit or line.debit or 0.0, context=context_multi_currency)
#                 amount_unreconciled = currency_pool.compute(cr, uid, company_currency, currency_id, abs(line.amount_residual), context=context_multi_currency)
#             line_currency_id = line.currency_id and line.currency_id.id or company_currency
#             rs = {
#                 'name': line.move_id.name,
#                 'type': line.credit and 'dr' or 'cr',
#                 'move_line_id': line.id,
#                 'analytic_account_id': line.invoice.account_analytic_id.id if line.invoice and line.invoice.account_analytic_id else False,
#                 'account_id': line.account_id.id,
#                 'amount_original': amount_original,
#                 'amount': (line.id in move_lines_found) and min(abs(remaining_amount), amount_unreconciled) or 0.0,
#                 'date_original': line.date,
#                 'date_due': line.date_maturity,
#                 'amount_unreconciled': amount_unreconciled,
#                 'currency_id': line_currency_id,
#             }
#             remaining_amount -= rs['amount']
#             #in case a corresponding move_line hasn't been found, we now try to assign the voucher amount
#             #on existing invoices: we split voucher amount by most old first, but only for lines in the same currency
#             if not move_lines_found:
#                 if currency_id == line_currency_id:
#                     if line.credit:
#                         amount = min(amount_unreconciled, abs(total_debit))
#                         rs['amount'] = amount
#                         total_debit -= amount
#                     else:
#                         amount = min(amount_unreconciled, abs(total_credit))
#                         rs['amount'] = amount
#                         total_credit -= amount
#
#             if rs['amount_unreconciled'] == rs['amount']:
#                 rs['reconcile'] = True
#
#             if rs['type'] == 'cr':
#                 default['value']['line_cr_ids'].append(rs)
#             else:
#                 default['value']['line_dr_ids'].append(rs)
#
#             if len(default['value']['line_cr_ids']) > 0:
#                 default['value']['pre_line'] = 1
#             elif len(default['value']['line_dr_ids']) > 0:
#                 default['value']['pre_line'] = 1
#             default['value']['writeoff_amount'] = self._compute_writeoff_amount(cr, uid, default['value']['line_dr_ids'], default['value']['line_cr_ids'], price, ttype)
#         return default
#
#     @api.model
#     def create(self, values):
#         result = super(AccountVoucher, self).create(values)
#         context = self.env.context
#         if 'default_rent_id' in context:
#             moves = result.line_cr_ids.filtered(lambda rec: rec.amount > 0)
#             if moves:
#                 invoices = result.line_cr_ids.filtered(lambda rec: rec.amount > 0).mapped(
#                     'move_line_id.invoice')
#                 for inv in invoices:
#                     installment = self.env['property.rent.installment.collection'].search(
#                         [('invoice_id', '=', inv.id)])
#                     if not installment:
#                         raise Warning(_('Error!'),
#                                       _('Link Installment with Invoice Before Posting.'))
#         return result
#
#     def write(self, vals):
#         result = super(AccountVoucher, self).write(vals)
#         context = self.env.context
#         if 'default_rent_id' in context:
#             moves = self.line_cr_ids.filtered(lambda rec: rec.amount > 0)
#             if moves:
#                 invoices = self.line_cr_ids.filtered(lambda rec: rec.amount > 0).mapped(
#                     'move_line_id.invoice')
#                 for inv in invoices:
#                     installment = self.env['property.rent.installment.collection'].search(
#                         [('invoice_id', '=', inv.id)])
#                     if not installment:
#                         raise Warning(_('Error!'),
#                                       _('Link Installment with Invoice Before Posting.'))
#         return result


# class AccountInvoice(models.Model):
#     _inherit = 'account.invoice'
#
#     def write(self, vals):
#         """
#         :param vals:
#         :return:
#         """
#         res = super(AccountInvoice, self).write(vals)
#         for record in self:
#             if record.state == 'paid':
#                 installment = self.env['property.rent.installment.collection'].search(
#                     [('rent_id', '=', record.rent_id.id), ('period_ids', '=', record.rental_period_id.id)])
#                 if installment:
#                     installment.state = 'paid'
#                     record.rental_period_id.state = 'done'
#         return res
#
#     def invoice_pay_customer(self):
#         if not self.id: return []
#         view_id = self.env.ref('itis_cybro_estate.view_property_receipt_dialog_form').id
#
#         inv = self
#         return {
#             'name': _("Pay Invoice"),
#             'view_mode': 'form',
#             'view_id': view_id,
#             'view_type': 'form',
#             'res_model': 'account.voucher',
#             'type': 'ir.actions.act_window',
#             'nodestroy': True,
#             'target': 'new',
#             'domain': '[]',
#             'context': {
#                 'payment_expected_currency': inv.currency_id.id,
#                 'default_partner_id': self.env['res.partner']._find_accounting_partner(inv.partner_id).id,
#                 'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
#                 'default_reference': inv.name,
#                 'close_after_process': True,
#                 'invoice_type': inv.type,
#                 'invoice_id': inv.id,
#                 'default_type': inv.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
#                 'type': inv.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment'
#             }
#         }
#


# class PropertyVoucher(models.Model):
#     _inherit = 'property.voucher'
#
#     building = fields.Many2one(comodel_name='property.building', string='Building')
#     cheque_number_contra = fields.Char(string='Cheque No (IF)', readonly=True, copy=True,
#                                        states={'draft': [('readonly', False)]})
#     rent_period_id = fields.Many2one(comodel_name='rent.period.lines', string='Rental Period')

#     def create_installment(self, ):
#         res = super(PropertyVoucher, self).create_installment()
#         if self.rent_period_id:
#             for each_period in self.rent_period_id:
#                 each_period.state = 'done'
#             self.cheque_number.period_ids = self.rent_period_id
#         return res
#
#     @api.onchange('contract_id', 'agreement_id', 'sale_agreement_id')
#     def _onchange_contract_id(self):
#         if self.agreement_id:
#             self.building = self.agreement_id.building
#         elif self.contract_id:
#             self.building = self.contract_id.building
#         elif self.sale_agreement_id:
#             self.building = self.sale_agreement_id.building
#         res = super(PropertyVoucher, self)._onchange_contract_id()
#         return res
#
#     @api.onchange('cheque_number')
#     def onchange_cheque_number(self):
#         if self.cash_or_cheque:
#             self.amount = self.cheque_number.amount
#             self.rent_period_ids = self.cheque_number.period_ids
