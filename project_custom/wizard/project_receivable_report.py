# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError


class ProjectReceivableReport(models.TransientModel):
    _name = "project.receivable.report"
    _description = "Project Receivable Report"

    inv_date = fields.Date(string=_('Date'))
    project_ids = fields.Many2many('project.project', string=_('Project'))

    def get_report_values(self):
        data = {}
        data["form"] = self.read()[0]
        invoice_obj = self.env['account.move']
        if self.inv_date:
            invoice_rec = invoice_obj.search([('move_type', '=', 'out_invoice'),
                                              ('state', '=', 'open'),
                                              ('date_invoice', '=', self.inv_date)])
        else:
            invoice_rec = invoice_obj.search([('move_type', '=', 'out_invoice'), ('state', '=', 'open')])
        if self.project_ids:
            project_rec = self.project_ids
        else:
            project_rec = self.env['project.project'].search([('state', '=', 'open')])
        project_list = []
        for project in project_rec:
            project_receivables = invoice_rec.filtered(lambda x: x.account_analytic_id == project.analytic_account_id)
            if not project_receivables:
                continue
            receivable_lines = []
            customers = project_receivables.mapped('partner_id')
            for customer in customers:
                customer_lines = []
                customer_receivables = project_receivables.filtered(lambda x: x.partner_id == customer)
                for receivable in customer_receivables:
                    customer_lines.append({
                        'customer': receivable.partner_id.name,
                        'invoice_date': receivable.date_invoice,
                        'number': receivable.number,
                        'due_date': receivable.date_due,
                        'source': receivable.origin or '',
                        'balance': receivable.residual,
                        'total': receivable.amount_total,
                    })
                receivable_lines.append({
                    'name': customer.name,
                    'lines': customer_lines,
                    'count': len(customer_lines),
                    'total': sum([line['balance'] for line in customer_lines])
                })
            project_list.append({
                'name': project.name,
                'receivables': receivable_lines,
                'total_count': sum([line['count'] for line in receivable_lines])
            })
        data.update({'project_list': project_list})
        data.update({'project_ids': ', '.join(self.project_ids.mapped('name'))})
        return data

    def print_xls(self):
        data = self.get_report_values()
        return self.env.ref('project_custom.action_report_project_receivable_xls').report_action(
            self, data=data, config=False)
