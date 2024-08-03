# -*- coding: utf-8 -*-
import io
from datetime import timedelta, datetime
from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

from odoo import models, fields

import json
from odoo.tools import date_utils


class LevySummaryReport(models.TransientModel):
    _name = 'levy.summary.report'
    _description = 'Levy Summary Report'

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    def action_create_report(self):
        """ action create report"""
        data = {
            'ids': self.ids,
            'model': self._name,
            'start_date': self.start_date,
            'end_date': self.end_date,
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'levy.summary.report',
                     'options': json.dumps(data, default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Levy Summary Report',
                     },
            'report_type': 'community_xlsx'
        }

    def get_lines(self, data):
        self._cr.execute("""
                       select  a.name,a.start_date,a.end_date,c.total_sinking_fund,c.total_admin_fund,c.total_fund from property_community as c 
                        inner join aqar_contract as a on c.community_contract_id = a.id 
                        where a.start_date >= '%s' AND a.end_date <= '%s' """
                         % (data.get('start_date'), data.get('end_date')))
        value = self._cr.dictfetchall()
        return value

    def get_sublevy_data(self,data):
        self._cr.execute("""
                               select b.sub_levy_name,l.levy_name,b.total_gross_amount,b.period_start,b.period_end,s.sub_levy_name,a.name,m.credit from community_budget as b
                                inner join levy_master as l on b.levy_id = l.id
                                inner join sub_levy_line as s on b.levy_id = s.levy_id
                                inner join account_account as a on s.sub_levy_account_id = a.id
                                inner join account_move_line as m on a.id = m.account_id
                                 """
                         )
        value = self._cr.dictfetchall()
        sum_credits = defaultdict(lambda: defaultdict(float))
        date = datetime.strptime(data.get('end_date'), "%Y-%m-%d")
        year = date.year
        last_day_year = date.replace(day=31, month=12)
        last_days = []
        for i in range(1, 4):
            last_days.append((last_day_year - timedelta(days=365 * i)).year)

        for item in value:
            levy_name = item['levy_name']
            sub_levy_name = item['sub_levy_name']
            period_start = item['period_start']
            period_end = item['period_end']
            credit = item['credit']
            total_gross_amount = item['total_gross_amount']
            for year_to_filter in last_days:
                if period_start.year == year_to_filter and period_end.year == year_to_filter:
                    sum_credits[levy_name]['sub_levy_name'] = sub_levy_name
                    sum_credits[levy_name]['total_gross_amount'] += total_gross_amount
                    if period_start.year != year:
                        sum_credits[levy_name]['total_credit'] += credit
                    else:
                        sum_credits[levy_name]['total_credit'] += 0
        return sum_credits

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        lines = self.get_lines(data)
        sub_levy_data = self.get_sublevy_data(data)
        sheet = workbook.add_worksheet('Budget Summary')
        sheet_1 = workbook.add_worksheet('Levies Summary')
        format0 = workbook.add_format({'font_size': 20, 'align': 'center', 'bold': True})
        format1 = workbook.add_format({'font_size': 14, 'align': 'vcenter', 'bold': True})
        format11 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
        format21 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
        format3 = workbook.add_format({'bottom': True, 'top': True, 'font_size': 12})
        format4 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True})
        font_size_8 = workbook.add_format({'font_size': 8, 'align': 'center'})
        font_size_8_l = workbook.add_format({'font_size': 8, 'align': 'left'})
        font_size_8_r = workbook.add_format({'font_size': 8, 'align': 'right'})
        txt = workbook.add_format({'font_size': 10, 'border': 1})
        txt_no_border = workbook.add_format({'font_size': 10, })
        red_mark = workbook.add_format({'font_size': 8, 'bg_color': 'blue'})
        justify = workbook.add_format({'font_size': 12})
        format3.set_align('center')
        justify.set_align('justify')
        format1.set_align('center')
        red_mark.set_align('center')
        sheet.merge_range('A1:G1', 'Levy Summary Report', format1)
        sheet.merge_range('A2:G2', '', red_mark)
        sheet.write('A3', 'Contract Name', format11)
        sheet.write('B3', 'From', format11)
        sheet.write('C3', 'To', format11)
        sheet.write('D3', 'LEVIES - ADMIN FUND', format11)
        sheet.write('E3', 'LEVIES - SINKING FUND', format11)
        sheet.write('F3', 'Total', format11)
        sheet_1.write('B2', 'Community', format11)
        sheet_1.write('C2', 'Management', format11)
        sheet_1.write('B3', 'Period', format1)
        sheet_1.write('C3', str(data.get('start_date')), txt_no_border)
        sheet_1.write('D3', str(data.get('end_date')), txt_no_border)
        sheet_1.write('B3', 'SI No', format11)
        sheet_1.write('C3', 'Sub Levy', format11)
        date = datetime.strptime(data.get('end_date'), "%Y-%m-%d")
        year = date.year
        sheet_1.write('D3', 'Budget %s' % (year), format11)
        last_day_year = date.replace(day=31, month=12)
        last_days = []
        for i in range(1, 4):
            last_days.append(last_day_year - timedelta(days=365 * i))
        row_1 = 2
        col_1 = 2
        for l in last_days:
            date = l.date().replace(day=31, month=12)
            if date.year != year:
                col_1 += 2
                sheet_1.write(row_1, col_1, 'Actual Exps %s' % (date), format11)
                sheet_1.write(row_1, col_1 + 1, 'Budget %s' % (date), format11)
        row_1 = 3
        col_1 = 0
        for levy_name, details in sub_levy_data.items():
            col_1 += 2
            sheet_1.write(row_1, col_1, levy_name, format11)
            print("detaoilss",details)
            row_1 += 1
            sheet_1.write(row_1, col_1, details['sub_levy_name'], txt)
            sheet_1.write(row_1, col_1 + 1, details['total_gross_amount'], txt)
            sheet_1.write(row_1, col_1 + 2, details['credit'], txt)
            row_1 += 1
            col_1 = 0
        sheet.set_column(1, 1, 15)
        sheet.set_column(0, 0, 20)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        sheet.set_column(4, 4, 20)
        sheet.set_column(5, 5, 20)
        sheet.set_column(6, 6, 20)
        sheet_1.set_column(1, 1, 10)
        sheet_1.set_column(0, 0, 10)
        sheet_1.set_column(2, 2, 15)
        sheet_1.set_column(3, 3, 15)
        sheet_1.set_column(4, 4, 20)
        sheet_1.set_column(5, 5, 20)
        sheet_1.set_column(6, 6, 20)
        row = 2
        col = 0
        for brand in lines:
            row += 1
            start_date = str(brand.get('start_date'))
            end_date = str(brand.get('end_date'))
            sheet.write(row, col, brand.get('name'), txt)
            sheet.write(row, col + 1, start_date, txt)
            sheet.write(row, col + 2, end_date, txt)
            sheet.write(row, col + 3, brand.get('total_admin_fund'), txt)
            sheet.write(row, col + 4, brand.get('total_sinking_fund'), txt)
            sheet.write(row, col + 5, brand.get('total_fund'), txt)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
