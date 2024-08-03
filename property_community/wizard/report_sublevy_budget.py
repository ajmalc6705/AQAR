# -*- coding: utf-8 -*-

import io
from datetime import timedelta, datetime
from collections import defaultdict

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

from odoo import models, fields

import json
from odoo.tools import date_utils


class ReportSublevyBudget(models.TransientModel):
    _name = 'report.sublevy.budget'
    _description = 'Report Sub levy Budget'

    budget_id = fields.Many2one('community.budget', string='Budget')

    def action_create_report(self):
        docids = self.env['report.sublevy.budget'].search([]).ids
        budget_ids = self._get_report_data()
        data = {
            'doc_ids': docids,
            'ids': budget_ids,
            'budget': self.budget_id.budget_seq
        }
        return self.env.ref('property_community.action_budget_report').report_action(self, data)

    def _get_report_data(self):
        budget = self.budget_id.id
        self._cr.execute("""select b.budget_seq,q.name,b.sub_levy_name,b.total_gross_amount,b.type,b.budget_amount,b.total_area,m.credit from community_budget as b
                            inner join property_community as c on b.community_id = c.id 
                            inner join aqar_contract as q on c.community_contract_id = q.id
                            inner join levy_master as l on b.levy_id = l.id
                            inner join sub_levy_line as s on b.levy_id = s.levy_id
                            inner join account_account as a on s.sub_levy_account_id = a.id
                            inner join account_move_line as m on a.id = m.account_id
                            where b.id = '%s'
                                         """ % (budget))
        value = self._cr.dictfetchall()
        model = self.env.context.get('active_model')
        data = {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': value,
            'today': fields.Date.today(),
            'company': self.env.company,

        }
        return data
