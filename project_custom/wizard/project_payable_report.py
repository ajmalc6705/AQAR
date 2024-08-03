# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError


class ProjectPayableReport(models.TransientModel):
    _name = "project.payable.report"
    _description = "Project Payable Report"

    inv_date = fields.Date(string=_('Date'))
    project_ids = fields.Many2many('project.project', string=_('Project'))

    def get_report_values(self):
        data = {}
        data["form"] = self.read()[0]
        invoice_obj = self.env['account.move']
        if self.inv_date:
            invoice_rec = invoice_obj.search([('move_type', '=', 'in_invoice'),
                                              ('state', '=', 'open'),
                                              ('date_invoice', '=', self.inv_date)])
        else:
            invoice_rec = invoice_obj.search([('move_type', '=', 'in_invoice'), ('state', '=', 'open')])
        if self.project_ids:
            project_rec = self.project_ids
        else:
            project_rec = self.env['project.project'].search([('state', '=', 'open')])
        project_list = []
        for project in project_rec:
            project_payables = invoice_rec.filtered(lambda x: x.account_analytic_id == project.analytic_account_id)
            if not project_payables:
                continue
            payable_lines = []
            suppliers = project_payables.mapped('partner_id')
            for supplier in suppliers:
                supplier_lines = []
                suppliers_payables = project_payables.filtered(lambda x: x.partner_id == supplier)
                for payable in suppliers_payables:
                    supplier_lines.append({
                        'customer': payable.partner_id.name,
                        'invoice_date': payable.date_invoice,
                        'number': payable.number,
                        'due_date': payable.date_due,
                        'source': payable.origin or '',
                        'balance': payable.residual,
                        'total': payable.amount_total,
                    })
                payable_lines.append({
                    'name': supplier.name,
                    'lines': supplier_lines,
                    'count': len(supplier_lines),
                    'total': sum([line['balance'] for line in supplier_lines])
                })
            project_list.append({
                'name': project.name,
                'payables': payable_lines,
                'total_count': sum([line['count'] for line in payable_lines])
            })
        data.update({'project_list': project_list})
        data.update({'project_ids': ', '.join(self.project_ids.mapped('name'))})
        return data

    def print_xls(self):
        data = self.get_report_values()
        return self.env.ref('project_custom.action_report_project_payable_xls').report_action(
            self, data=data, config=False)
