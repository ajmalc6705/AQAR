# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class AccountMPayment(models.Model):
    _inherit = 'account.payment'

    def action_cancel(self):
        ''' draft -> cancelled '''
        for rec in self:
            if rec.rent_id and rec.cheque_no:
                installments_toupdate = self.env['property.rent.installment.collection']. \
                    search(
                    [('rent_id', '=', rec.rent_id.id), ('state', 'in', ['paid', 'draft']),
                     ('cheque_number', '=', rec.cheque_no)])
                installments_toupdate |= self.env['property.rent.installment.collection']. \
                    search(
                    [('state', 'in', ['paid', 'draft']), ('cheque_number', '=', rec.cheque_no)])
                # Revert In state of installments in case of cancel payments manually
                installments_toupdate.write({'state': 'draft0'})
                message = _("This Rent Receipt for Installment has been Updated from: %s") % (rec.name)
                rec.rent_id.message_post(body=message)
            message = _("This Rent Receipt for Installment has been updated from: %s") % (rec.name)
            rec.message_post(body=message)
        self.move_id.button_cancel()

    def action_draft(self):
        ''' posted -> draft '''
        for rec in self:
            if rec.rent_id and rec.cheque_no:
                installments_toupdate = self.env['property.rent.installment.collection']. \
                    search(
                    [('rent_id', '=', rec.rent_id.id), ('state', 'in', ['paid', 'draft']),
                     ('cheque_number', '=', rec.cheque_no)])
                installments_toupdate |= self.env['property.rent.installment.collection']. \
                    search(
                    [('state', 'in', ['paid', 'draft']), ('cheque_number', '=', rec.cheque_no)])
                # Revert In state of installments in case of cancel payments manually
                installments_toupdate.write({'state': 'draft0'})
                message = _("This Rent Receipt for Installment has been Updated from: %s") % (rec.name)
                rec.rent_id.message_post(body=message)
            message = _("This Rent Receipt for Installment has been updated from: %s") % (rec.name)
            rec.message_post(body=message)
        self.move_id.button_draft()

    def write(self, vals):
        """

        @param vals:
        @return:
        """
        result = super(AccountMPayment, self).write(vals)
        if vals.get('rent_id'):
            for rec in self:
                if rec.rent_id and rec.cheque_no:
                    installments_toupdate = self.env['property.rent.installment.collection']. \
                        search(
                        [('rent_id', '=', rec.rent_id.id), ('state', '=', 'draft0'),
                         ('cheque_number', '=', rec.cheque_no)])
                    installments_toupdate |= self.env['property.rent.installment.collection']. \
                        search(
                        [('state', '=', 'draft0'), ('cheque_number', '=', rec.cheque_no)])
                    installments_toupdate.write({'state': 'draft'})
                message = _("This Rent Receipt for Installment has been Updated from: %s") % (rec.name)
                rec.rent_id.message_post(body=message)
                message = _("This Rent Receipt for Installment has been updated from: %s") % (rec.name)
                rec.message_post(body=message)
        return result

    @api.model_create_multi
    def create(self, vals):
        """

        @param vals:
        @return:
        """
        result = super().create(vals)
        for rec in result:
            if rec.rent_id and rec.cheque_no:
                installments_toupdate = self.env['property.rent.installment.collection']. \
                    search(
                    [('rent_id', '=', rec.rent_id.id), ('state', '=', 'draft0'), ('cheque_number', '=', rec.cheque_no)])
                installments_toupdate |= self.env['property.rent.installment.collection']. \
                    search(
                    [('rent_id.partner_id', '=', rec.partner_id.id), ('state', '=', 'draft0'),
                     ('cheque_number', '=', rec.cheque_no)])
                installments_toupdate.write({'state': 'draft'})
                message = _("This Rent Receipt for Installment has been Created from: %s") % (rec.name)
                rec.rent_id.message_post(body=message)
            message = _("This Rent Receipt for Installment has been created from: %s") % (rec.name)
            rec.message_post(body=message)
        return result


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Move entry fields
    # contract_id = fields.Many2one(comodel_name='property.contract', string='Contract Number')
    # agreement_id = fields.Many2one(comodel_name='property.rent', string='Rent Agreement Number')
    # sale_agreement_id = fields.Many2one(comodel_name='property.sale', string='Sale Agreement Number')
    property_id = fields.Many2one(comodel_name='property.property', string='Unit')
    building_id = fields.Many2one(comodel_name='property.building', string='Building')

    # Invoice details
    rent_id = fields.Many2one(comodel_name='property.rent', string='Rent')
    rental_period_id = fields.Many2one(comodel_name='rent.period.lines', string='Rental Periods')
    rental_installment_id = fields.Many2one(comodel_name='property.rent.installment.collection', string='Rental Period')

    # @api.depends(
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.balance',
    #     'line_ids.currency_id',
    #     'line_ids.amount_currency',
    #     'line_ids.amount_residual',
    #     'line_ids.amount_residual_currency',
    #     'line_ids.payment_id.state',
    #     'line_ids.full_reconcile_id',
    #     'state')
    # def _compute_amount(self):
    #     for move in self:
    #         total_untaxed, total_untaxed_currency = 0.0, 0.0
    #         total_tax, total_tax_currency = 0.0, 0.0
    #         total_residual, total_residual_currency = 0.0, 0.0
    #         total, total_currency = 0.0, 0.0
    #
    #         for line in move.line_ids:
    #             if move.is_invoice(True):
    #                 # === Invoices ===
    #                 if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
    #                     # Tax amount.
    #                     total_tax += line.balance
    #                     total_tax_currency += line.amount_currency
    #                     total += line.balance
    #                     total_currency += line.amount_currency
    #                 elif line.display_type in ('product', 'rounding'):
    #                     # Untaxed amount.
    #                     total_untaxed += line.balance
    #                     total_untaxed_currency += line.amount_currency
    #                     total += line.balance
    #                     total_currency += line.amount_currency
    #                 elif line.display_type == 'payment_term':
    #                     # Residual amount.
    #                     total_residual += line.amount_residual
    #                     total_residual_currency += line.amount_residual_currency
    #             else:
    #                 # === Miscellaneous journal entry ===
    #                 if line.debit:
    #                     total += line.balance
    #                     total_currency += line.amount_currency
    #
    #         sign = move.direction_sign
    #         move.amount_untaxed = sign * total_untaxed_currency
    #         move.amount_tax = sign * total_tax_currency
    #         move.amount_total = sign * total_currency
    #         move.amount_residual = -sign * total_residual_currency
    #         move.amount_untaxed_signed = -total_untaxed
    #         move.amount_tax_signed = -total_tax
    #         move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
    #         move.amount_residual_signed = total_residual
    #         move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(
    #                 sign * move.amount_total)

    def action_register_payment_rent(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
                'rent_agreement': True
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    cost_center_id = fields.Many2one(comodel_name='account.analytic.account', string='Cost Center Name')
    expense_category_id = fields.Many2one(comodel_name='property.maintenance.type', string='Expense Category')
    income_category_id = fields.Many2one(comodel_name='property.income.type', string='Income Category')
    property_id = fields.Many2one(comodel_name='property.property', string='Unit')
    building_id = fields.Many2one(comodel_name='property.building', string='Building')


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    rent_id = fields.Many2one(comodel_name='property.rent', string='Rent')
    rental_period_id = fields.Many2one(comodel_name='rent.period.lines', string='Rental Periods')
    rental_installment_id = fields.Many2one(comodel_name='property.rent.installment.collection', string='Rental Period')

    @api.depends('line_ids')
    def _compute_from_lines(self):
        ''' Load initial values from the account.moves passed through the context. '''
        for wizard in self:
            batches = wizard._get_batches()
            if len(batches) == 1:
                # == Single batch to be mounted on the view ==
                batch_result = batches[0]
                wizard.update(wizard._get_wizard_values_from_batch(batch_result))

                wizard.can_edit_wizard = True
                wizard.can_group_payments = len(batch_result['lines']) != 1
            else:
                # == Multiple batches: The wizard is not editable  ==
                wizard.update({
                    'company_id': batches[0]['lines'][0].company_id.id,
                    'partner_id': False,
                    'partner_type': False,
                    'payment_type': False,
                    'source_currency_id': False,
                    'source_amount': False,
                    'source_amount_currency': False,
                })

                wizard.can_edit_wizard = False
                wizard.can_group_payments = any(len(batch_result['lines']) != 1 for batch_result in batches)
            # if self._context.get('rent_agreement'):
            #     wizard.hide_payment_method = True

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard(batch_result)
        if self._context.get('active_model') == 'account.move' and self._context.get('active_id') \
                and self.env['account.move'].browse(self._context.get('active_id')) and \
                self.env['account.move'].browse(self._context.get('active_id')).rent_id:
            invoice = self.env['account.move'].browse(self._context.get('active_id'))
            if invoice.state != 'posted' and 'line_ids' in payment_vals:
                payment_vals['line_ids'] = []
            if "rent_collection_id" in self._context and self._context.get('rent_collection_id'):
                if not invoice.rental_installment_id:
                    invoice.rental_installment_id = self._context.get('rent_collection_id')
                if not invoice.rental_period_id:
                    invoice.rental_period_id = self._context.get('rent_period_id')
            payment_vals.update({
                'rent_id': invoice.rent_id and invoice.rent_id.id,
                'rental_installment_id': invoice.rental_installment_id and invoice.rental_installment_id.id
            })
            if invoice.rental_installment_id:
                invoice.rental_installment_id.state = 'draft'
        else:
            pass
        return payment_vals

    @api.model
    def _get_line_batch_key(self, line):
        ''' Turn the line passed as parameter to a dictionary defining on which way the lines
        will be grouped together.
        :return: A python dictionary.
        '''
        batch_keys = super(AccountPaymentRegister, self)._get_line_batch_key(line)
        batch_keys.update({
            'rent_id': line.move_id.rent_id and line.move_id.rent_id.id,
            'rental_installment_id': line.move_id.rental_installment_id and line.move_id.rental_installment_id.id
        })
        return batch_keys

    @api.model
    def _get_wizard_values_from_batch(self, batch_result):
        ''' Extract values from the batch passed as parameter (see '_get_batches')
        to be mounted in the wizard view.
        :param batch_result:    A batch returned by '_get_batches'.
        :return:                A dictionary containing valid fields
        '''
        result = super(AccountPaymentRegister, self)._get_wizard_values_from_batch(batch_result)
        print("hhh", batch_result)
        # if batch_result['key_values']:
        #     key_values = batch_result['key_values']

        if "rental_installment_id" in batch_result and "rent_id" in batch_result:
            result.update({
                'rent_id': batch_result['rent_id'] if 'rent_id' in batch_result else False,
                'rental_installment_id': batch_result[
                    'rental_installment_id'] if 'rental_installment_id' in batch_result else False,
            })

        return result

    def _create_payments_for_rent(self):
        self.ensure_one()
        batches = self._get_batches()
        edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)

        to_reconcile = []
        if edit_mode:
            batch_result = batches[0]
            payment_vals = self._create_payment_vals_from_wizard(batch_result)
            # payment_vals['curr_move_line'] = [(6, 0, self.curr_move_line.ids)]
            payment_vals['bearer'] = self.bearer
            payment_vals['cheque_no'] = self.cheque_no
            # payment_vals['effective_date'] = self.effective_date
            # payment_vals['transaction_type'] = self.transaction_type
            payment_vals_list = [payment_vals]
            to_reconcile.append(batches[0]['lines'])
        else:
            # Don't group payments: Create one batch per move.
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        new_batches.append({
                            **batch_result,
                            'lines': line,
                        })
                batches = new_batches

        payment_vals_list = []
        for batch_result in batches:
            payment_vals_list.append(self._create_payment_vals_from_batch(batch_result))
            to_reconcile.append(batch_result['lines'])

        payments = self.env['account.payment'].create(payment_vals_list)

        if edit_mode:
            for payment, lines in zip(payments, to_reconcile):
                # Batches are made using the same currency so making 'lines.currency_id' is ok.
                if payment.currency_id != lines.currency_id:
                    liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
                    source_balance = abs(sum(lines.mapped('amount_residual')))
                    payment_rate = liquidity_lines[0].amount_currency / liquidity_lines[0].balance
                    source_balance_converted = abs(source_balance) * payment_rate

                    payment_balance = abs(sum(counterpart_lines.mapped('balance')))
                    payment_amount_currency = abs(sum(counterpart_lines.mapped('amount_currency')))
                    if not payment.currency_id.is_zero(source_balance_converted - payment_amount_currency):
                        continue

                    delta_balance = source_balance - payment_balance

                    # Balance are already the same.
                    if self.company_currency_id.is_zero(delta_balance):
                        continue

                    # Fix the balance but make sure to peek the liquidity and counterpart lines first.
                    debit_lines = (liquidity_lines + counterpart_lines).filtered('debit')
                    credit_lines = (liquidity_lines + counterpart_lines).filtered('credit')

                    payment.move_id.write({'line_ids': [
                        (1, debit_lines[0].id, {'debit': debit_lines[0].debit + delta_balance}),
                        (1, credit_lines[0].id, {'credit': credit_lines[0].credit + delta_balance}),
                    ]})
        return payments


def action_create_payments(self):
    if "rent_collection" in self._context and self._context.get('rent_collection'):
        payments = self._create_payments_for_rent()

        # update collection state
        if "rent_collection" in self._context and self._context.get('rent_collection'):
            payments.write({'rental_installment_id': self._context.get('rent_collection_id'),
                            'rental_period_id': self._context.get('rent_period_id')})
            payments.rental_installment_id.change_state_deposited()
    else:
        payments = self._create_payments()

    if self._context.get('dont_redirect_to_payments') or self._context.get('rent_collection'):
        return True

    action = {
        'name': _('Payments'),
        'type': 'ir.actions.act_window',
        'res_model': 'account.payment',
        'context': {'create': False},
    }
    if len(payments) == 1:
        action.update({
            'view_mode': 'form',
            'res_id': payments.id,
        })
    else:
        action.update({
            'view_mode': 'tree,form',
            'domain': [('id', 'in', payments.ids)],
        })
    return action
