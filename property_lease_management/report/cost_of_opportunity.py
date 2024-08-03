# -*- coding: utf-8 -*-
#
# Al Sabla Digital Solutions <http://www.alsablasolutions.com>, Copyright (C) 2015 - Today.
#    
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from openerp.report import report_sxw
from openerp import api, models
from datetime import timedelta, datetime
from utils import find_amount, get_next_day, get_previous_day


class OpportunityParser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(OpportunityParser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_data': self._get_data,
        })
        self.context = context

    def _get_data(self, property_id, amount, data):
        res = []
        total_lost = 0
        total_income = 0
        cr = self.cr
        sql = '''select r.from_date as f_dt , r.to_date as t_dt, r.rent_total as amnt, p.name  from property_rent as r
                 left join property_property as p on (r.property_id = p.id)
                 where property_id = %s and (r.from_date between %s and %s or r.to_date between %s and %s)
                 order by 1 '''
        from_date = data['form']['date_from']
        to_date = data['form']['date_to']

        fro_date = datetime.strptime(from_date, '%Y-%m-%d') - timedelta(days=1)  # to get exact from date
        #  from find_amount function
        t_date = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)  # to get exact to date
        #  from find_amount function
        fro_date = fro_date.date()
        t_date = t_date.date()
        cr.execute(sql, tuple((property_id, from_date, to_date, from_date, to_date)))
        records = cr.dictfetchall()

        if not records:
            res.append({'to_dt': to_date, 'fro_dt': from_date, 'amount': amount, 'status': 'Empty'})
            total_lost = amount
        else:
            r1 = records[0]

            # To find empty days between from date and first record
            r = find_amount(str(fro_date), get_previous_day(r1['f_dt']), amount, from_date, to_date)
            if r:
                res.append({'to_dt': r['t_dt'], 'fro_dt': r['f_dt'], 'amount': r['amnt'], 'status': 'Empty'})
                total_lost += r['amnt']

            for i in range(len(records) - 1):
                r1 = records[i]
                r2 = records[i + 1]

                # To find amount of record
                r = find_amount(r1['f_dt'], r1['t_dt'], amount, from_date, to_date)
                if r:
                    res.append({'to_dt': r['t_dt'], 'fro_dt': r['f_dt'], 'amount': r['amnt'], 'status': 'Rented'})
                    total_income += r['amnt']

                # To find empty days between two records
                r = find_amount(get_next_day(r1['t_dt']), get_previous_day(r2['f_dt']), amount, from_date, to_date)
                if r:
                    res.append({'to_dt': r['t_dt'], 'fro_dt': r['f_dt'], 'amount': r['amnt'], 'status': 'Empty'})
                    total_lost += r['amnt']

            r_l = records[-1]  # last record

            # To find amount of last record
            r = find_amount(r_l['f_dt'], r_l['t_dt'], amount, from_date, to_date)
            if r:
                res.append({'to_dt': r['t_dt'], 'fro_dt': r['f_dt'], 'amount': r['amnt'], 'status': 'Rented'})
                total_income += r['amnt']

            # To find empty days between to date and last record
            r = find_amount(get_next_day(r_l['t_dt']), str(t_date), amount, from_date, to_date)
            if r:
                res.append({'to_dt': r['t_dt'], 'fro_dt': r['f_dt'], 'amount': r['amnt'], 'status': 'Empty'})
                total_lost += r['amnt']

        return {'period': res, 'total_lost': total_lost, 'total_income': total_income}


class OpportunityReport(models.AbstractModel):
    _name = 'report.property_lease_management.report_income_and_lost_opportunity'
    _inherit = 'report.abstract_report'
    _template = 'property_lease_management.report_income_and_lost_opportunity'
    _wrapped_report_class = OpportunityParser

    # def render_html(self, cr, uid, ids, data=None, context=None):
    #     report_obj = self.pool['report']
    #     property_obj = self.pool['property.property']
    #
    #     # If the key 'landscape' is present in data['form'], passing it into the context
    #     if data and data.get('form', {}).get('landscape'):
    #         context['landscape'] = True
    #
    #     rec_ids = [data['form']['property_id'][0]]
    #     objects = property_obj.browse(cr, uid, rec_ids)
    #     context['active_model'] = 'property.property'
    #     context['active_ids'] = rec_ids
    #
    #     wrapped_report = self._wrapped_report_class(cr, uid, '',  context=context)
    #     wrapped_report.set_context(objects, data, context['active_ids'])
    #
    #     docargs = wrapped_report.localcontext
    #     docargs['docs'] = docargs.get('objects')
    #     docargs['doc_ids'] = rec_ids
    #     docargs['doc_model'] = 'property.property'
    #
    #     return report_obj.render(cr, uid, [], self._template, docargs, context=context)
