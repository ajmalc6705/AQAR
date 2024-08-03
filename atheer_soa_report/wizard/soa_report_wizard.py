# -*- coding: utf-8 -*-

from datetime import datetime
import datetime as DT
from odoo import models, api, fields, tools
from odoo.tools.translate import _


class TaxReport(models.TransientModel):
    _name = "soa.report.wiz"
    _description = _("Customer Statement of Account Report")

    balance_as_of_date = fields.Date(_('Balance as of Date'), default=fields.Date.today(), required=True)
    date = fields.Date(_('Report Date'), required=True, default=fields.Date.today(), readonly=1)
    company_id = fields.Many2one("res.company", string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    partner_id = fields.Many2one("res.partner", string='Partner', required=True)
    include_all = fields.Boolean('Include All Transactions')

    def button_print_report(self):
        datas = {}
        if self.partner_id:
            datas['partner_id'] = self.partner_id.id
        if self.date:
            datas['date'] = self.date
        if self.company_id:
            datas['company_id'] = self.company_id.id
        if self.balance_as_of_date:
            datas['balance_as_of_date'] = self.balance_as_of_date
        datas['include_all'] = self.include_all
        return self.env.ref('atheer_soa_report.action_customer_soa_report_pdf').report_action(None, data=datas)


class StatementAccountReport(models.AbstractModel):
    _name = "report.atheer_soa_report.statement_document"

    @api.model
    def _get_report_values(self, docids, data=None):
        if data.get('partner_id'):
            partner_id = data.get('partner_id')
        else:
            partner_id = docids[0]
        partner_id = self.env['res.partner'].browse(partner_id)
        data['partner_id'] = partner_id
        if data.get('balance_as_of_date'):
            balance_as_of_date = data.get('balance_as_of_date')
            data['balance_as_of_date'] = datetime.strptime(balance_as_of_date, "%Y-%m-%d").strftime("%d-%m-%Y")

        else:
            balance_as_of_date = fields.Date.today()
            data['balance_as_of_date'] = balance_as_of_date.strftime("%d-%m-%Y")

        if data.get('date'):
            date = data.get('date')
            data['date'] = datetime.strptime(date, "%Y-%m-%d").strftime("%d%m%Y")
        else:
            date = fields.Date.today()
            data['date'] = date.strftime("%d%m%Y")
        if data.get('company_id'):
            company_id = data.get('company_id')
        else:
            company_id = self.env.user.company_id.id
        data['company_id'] = self.env['res.company'].browse(company_id)

        options = {
            'date': {'date_to': balance_as_of_date},
            'partner': True, 
            'partner_ids': [partner_id.id],
            'filter_account_type': 'receivable' if partner_id.customer_rank > 0 else 'payable',
            'partner_id': str(partner_id.id),
        }
        query = ("""
                SELECT
                    {move_line_fields},
                    move.date AS voucher_date,
                    move.ref AS move_ref,
                    
                    move.invoice_date AS bill_date,
                    move.invoice_payment_term_id AS payment_terms_id,
                    account_move_line.amount_currency as amount_currency,
                    account_move_line.amount_residual AS amount_in_omr,
                
                    account_move_line.partner_id AS partner_id,
                    partner.name AS partner_name,                
                    COALESCE(trust_property.value_text, 'normal') AS partner_trust,
                    COALESCE(account_move_line.currency_id, journal.currency_id) AS report_currency_id,
                    account_move_line.payment_id AS payment_id,
                    COALESCE(account_move_line.date_maturity, account_move_line.date) AS report_date,
                    account_move_line.expected_pay_date AS expected_pay_date,
                    move.move_type AS move_type,
                    move.name AS move_name,                
                    account.code || ' ' || account.name AS account_name,
                    account.code AS account_code,""" + ','.join([("""
                    CASE WHEN (COALESCE(account_move_line.date_maturity, account_move_line.date) <= %(date)s)
                    THEN %(sign)s * ROUND((
                        account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0)
                    ) * currency_table.rate, currency_table.precision)
                    ELSE 0 END AS period{i}""").format(i=i) for i in range(6)]) + """
                FROM account_move_line
                JOIN account_move move ON account_move_line.move_id = move.id
                JOIN account_journal journal ON journal.id = account_move_line.journal_id
                JOIN account_account account ON account.id = account_move_line.account_id
                LEFT JOIN res_partner partner ON partner.id = account_move_line.partner_id
                LEFT JOIN ir_property trust_property ON (
                    trust_property.res_id = 'res.partner,'|| account_move_line.partner_id
                    AND trust_property.name = 'trust'
                    AND trust_property.company_id = account_move_line.company_id
                )
                JOIN {currency_table} ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN LATERAL (
                    SELECT part.amount, part.debit_move_id
                    FROM account_partial_reconcile part
                    WHERE part.max_date <= %(date)s
                ) part_debit ON part_debit.debit_move_id = account_move_line.id
                LEFT JOIN LATERAL (
                    SELECT part.amount, part.credit_move_id
                    FROM account_partial_reconcile part
                    WHERE part.max_date <= %(date)s
                ) part_credit ON part_credit.credit_move_id = account_move_line.id
                WHERE account.internal_type IN ('payable','receivable')
                AND account.exclude_from_aged_reports IS NOT TRUE
                AND account_move_line.partner_id = %(partner_id)s
                AND move.state = 'posted'
                AND account_move_line.date <= %(date)s
                GROUP BY account_move_line.id, partner.id, trust_property.id, journal.id, move.id, account.id,
                         currency_table.rate, currency_table.precision
                HAVING ROUND(account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0), currency_table.precision) != 0
                """
        ).format(
            move_line_fields=self.env['account.aged.partner']._get_move_line_fields('account_move_line'),
            currency_table=self.env['res.currency']._get_query_currency_table(options),
        )
        params = {
            'account_type': options['filter_account_type'],
            'sign': 1,
            'date': options['date']['date_to'],
            'partner_id': options['partner_id'],
        }
        self.env.cr.execute(query, params)
        query_fetch_values = self.env.cr.fetchall()

        # move_line_ids = self.env['account.move.line'].search([
        #     ('account_internal_type', 'in', ['payable', 'receivable']),
        #     ('move_id.state', '=', 'posted'),
        #     ('partner_id', '=', partner_id.id),
        #     ('company_id', '=', company_id),
        #     ('date', '<=', balance_as_of_date)
        # ])
        # move_line_ids = sorted(move_line_ids, key=lambda d: d.move_id.invoice_date or d.date):

        total_balance = 0
        total_credit = 0
        total_debit = 0
        move_details_lst = []
        data['currency'] = "OMR"
        cr_list = []
        for line_id in query_fetch_values:
            line = self.env['account.move.line'].browse(line_id[0])
            due_days = ''
            if line.move_id.invoice_date:
                d1 = line.move_id.invoice_date
                d2 = datetime.strptime(balance_as_of_date, "%Y-%m-%d").date()
                due_days = abs((d2 - d1).days)
            # else:
            #     d1 = line.date
            #     d2 = datetime.strptime(balance_as_of_date, "%Y-%m-%d").date()
            #     due_days = abs((d2 - d1).days)

            invoice_property = ''
            if line.move_id.move_type == 'out_invoice':
                invoice_property = 'Invoice'
                move_name = line.move_id.name
                # if line.move_id.invoice_property == 'sale_invoice':
                #     invoice_property = 'Sales Invoice'
                #     move_name = line.move_id.name
                # elif line.move_id.invoice_property == 'service_invoice':
                #     invoice_property = 'Service Invoice'
                #     move_name = line.move_id.ref
                # balance = line.move_id.amount_residual_signed
                # currency_amount = str(line.move_id.amount_residual) + " " + line.move_id.currency_id.name
            elif line.move_id.move_type == 'in_invoice':
                invoice_property = 'Bill'
                move_name = line.move_id.ref or line.move_id.name
                # balance = line.move_id.amount_residual_signed

                # currency_amount = str(line.move_id.amount_residual_currency) + " " + line.move_id.currency_id.name
            else:
                invoice_property = 'Payment'
                move_name = line.move_id.name +" : "+ (line.move_id.ref or '')
            balance = line_id[31] if line_id[31] != 0 else line_id[13]

            currency_amount = str(line_id[18]) + " " + line.currency_id.name
                # rec_line_ids = line._reconciled_lines()
                # rec_line_ids.remove(line.id)
                # reconciled_entries = self.env['account.move.line'].search([('id', 'in', rec_line_ids)])
                # balance = line.balance
                # if reconciled_entries:
                #     balance = line.amount_residual

                    # if line.credit > 0:
                    #     balance = min(sum(reconciled_entries.mapped('debit'))-line.credit, 0)
                    # elif line.debit > 0:
                    #     balance = line.amount_residual
                # currency_amount = str(line.amount_currency)+" "+line.currency_id.name
            if line.move_id.invoice_date:
                invoice_date = line.move_id.invoice_date.strftime("%d-%m-%Y")
            else:
                invoice_date = line.move_id.date.strftime("%d-%m-%Y")
            total_balance += balance
            total_debit += line.debit
            total_credit += line.credit

            dict_vals = {
                'transfer_type': invoice_property,
                'name': move_name,
                'invoice_date': invoice_date,
                # 'sale_order': line.move_id.sale_order_id.name,
                'ref': line.move_id.ref,
                'amount_currency': currency_amount,
                # 'amount_currency': str(line.amount_residual_currency)+" "+line.currency_id.name,
                # 'amount_currency': str(line.move_id.amount_residual)+" "+line.move_id.currency_id.name,
                'debit': line.debit,
                'credit': line.credit,
                'balance': round(total_balance, 3),
                # 'balance': line.balance,
                'invoice_date_due': line.move_id.invoice_date_due or '',
                'age': due_days,
                'move_id': line,
            }
            move_details_lst.append(dict_vals)
            if line.currency_id not in cr_list:
                cr_list.append(line.currency_id)

        # cr_list = []
        # for cr in currency_ids:
        #     if cr not in cr_list:
        #         cr_list.append(cr)
        # for cr_item in cr_list:
        #     currency_move_ids = move_line_ids.filtered(lambda l: l.currency_id.id == cr_item.id)
        #     data[cr_item.name] = round(sum(currency_move_ids.mapped('amount_residual_currency')), 3)

        for cr_item in cr_list:
            currency_move_lines = filter(lambda l: l[7] == cr_item.id, query_fetch_values)
            currency_total = round(sum(list(map(lambda x: x[18], currency_move_lines))), 3)
            data[cr_item.name] = currency_total

        data['currency_ids'] = cr_list
        data['currency'] = ','.join(map(lambda cr: cr.name, cr_list))
        data["total_credit"] = round(total_credit, 3)
        data["total_debit"] = round(total_debit, 3)
        data["total_balance"] = round(total_balance, 3)
        # move_details_lst = sorted(move_details_lst, key=lambda d: d['invoice_date'], reverse=True)
        return {
            'doc_ids': docids,
            'doc_model': 'soa.report.wiz',
            'docs': move_details_lst,
            'data': data,
        }
