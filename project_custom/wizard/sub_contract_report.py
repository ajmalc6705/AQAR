# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError


class SubContractReport(models.TransientModel):
    _name = "sub.contract.report"
    _description = "Sub Contract Report"

    @api.onchange('date')
    def get_project_domain(self):
        domain = []
        res = dict()
        if self.date:
            domain += [('start_date', '<=', self.date), ('date_end', '>=', self.date)]
        res['domain'] = {'project_id': domain}
        return res

    date = fields.Date(string=_('Date'), required=True)
    project_id = fields.Many2one('project.project', string=_('Project'), domain=get_project_domain)
    report_type = fields.Selection([('all', 'All'), ('due', 'Due Services')],
                                   string='Report Type', required=True, default='all')

    def get_report_values(self):
        data = {}
        data["form"] = self.read()[0]
        sub_contract_line_obj = self.env['sub.contract.line']
        if self.report_type == 'due':
            sub_contract_line_rec = sub_contract_line_obj.search([('state', '=', 'confirmed')]).filtered(
                lambda x: x.service_date < self.date and not x.is_completed)
        else:
            sub_contract_line_rec = sub_contract_line_obj.search([('state', '=', 'confirmed')])
        if self.project_id:
            project_rec = self.project_id
        else:
            project_rec = sub_contract_line_rec.mapped('project_id')
        if not sub_contract_line_rec:
            raise UserError(_('There is no supply/service lines.'))
        project_list = []
        for project in project_rec:
            lines = sub_contract_line_rec.filtered(lambda x: x.project_id == project)
            sub_contract_list = []
            sub_contracts = lines.mapped(lambda x: x.sub_contract_id)
            for contract in sub_contracts:
                contract_lines = []
                for line in lines.filtered(lambda x: x.sub_contract_id == contract):
                    if line.service_date < self.date and not line.is_completed:
                        service_status = 'Due'
                    elif line.is_completed:
                        service_status = 'Completed'
                    else:
                        service_status = 'Pending'
                    contract_lines.append({
                        'service_date': line.service_date,
                        'remark': line.remark or '',
                        'service_status': service_status
                    })
                sub_contract_list.append({
                    'name': contract.name,
                    'date_from': contract.date_from,
                    'date_to': contract.date_to,
                    'contract_type': dict(contract._fields['contract_type'].selection).get(
                        contract.contract_type) or '',
                    'invoice_schedule': dict(contract._fields['invoice_schedule'].selection).get(
                        contract.invoice_schedule) or '',
                    'value': contract.contract_value or 0,
                    'contract_lines': contract_lines
                })
            project_list.append({
                'name': project.name,
                'contracts': sub_contract_list
            })
        data.update({'project_list': project_list})
        data.update({'report_type': dict(self._fields['report_type'].selection).get(self.report_type)})
        return data

    def print_xls(self):
        data = self.get_report_values()
        return self.env.ref('project_custom.action_report_sub_contract_xls').report_action(
            self, data=data, config=False)
