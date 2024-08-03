# -*- coding: utf-8 -*-

import base64
from io import BytesIO
from odoo import models
import datetime as DT


class MonthlyBillExcel(models.AbstractModel):
    _name = 'report.property_lease_management.monthly_bill_excel'
    _inherit = 'report.report_xlsx.abstract'
    _description = "MonthlyBillExcel"

    def generate_xlsx_report(self, workbook, data, monthly_bill):
        """ generating Monthly Bill Excel"""
        company_id = self.env.user.company_id
        sheet = workbook.add_worksheet('Monthly Bill')

        format1 = workbook.add_format({'font_size': 14, 'right': True, 'left': True, 'top': True,
                                       'align': 'center', 'bold': True, 'valign': 'vcenter'})
        format11 = workbook.add_format({'font_size': 12, 'right': True, 'left': True, 'top': True,
                                        'align': 'right', 'bold': True, 'valign': 'vcenter'})
        format2 = workbook.add_format({'font_size': 12, 'align': 'left', 'right': True, 'top': True, 'bold': True,
                                       'text_wrap': True, 'bottom': True, 'bg_color': '#41689c', 'valign': 'vcenter'})
        format3 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})
        format33 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'right': True, 'left': True,
                                        'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})
        format33_float = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': False, 'right': True,
                                              'left': True, 'bottom': True, 'top': True, 'valign': 'vcenter',
                                              'text_wrap': True, 'num_format': '#,##0.000'})
        sheet.set_column(0, 0, 10)
        sheet.set_column(1, 1, 10)
        sheet.set_column(2, 2, 10)
        sheet.set_column(3, 3, 10)
        sheet.set_column(4, 4, 13)
        sheet.set_column(5, 5, 11)
        sheet.set_column(6, 6, 10)
        sheet.set_column(7, 7, 9)
        sheet.set_column(8, 8, 9)
        sheet.set_column(9, 9, 9)
        sheet.set_row(1, 20)
        sheet.set_row(2, 20)
        sheet.set_row(3, 20)
        sheet.set_row(4, 20)
        sheet.set_row(5, 40)

        if monthly_bill.is_electricity:
            if monthly_bill.bill_type.name == 'Electricity':
                sheet.merge_range('A1:I2', "Monthly Electricity Bill", format1)
                sheet.write(5, 1, 'Electricity Account', format2)
                sheet.write(5, 4, 'Consumption KWH', format2)
                sheet.write(5, 5, 'Consuming readings', format2)
                sheet.write(5, 6, 'Unit Rate', format2)
            elif monthly_bill.bill_type.name == 'Water':
                sheet.merge_range('A1:I2', "Monthly Water Bill", format1)
                sheet.write(5, 1, 'Water Account', format2)
                sheet.write(5, 4, 'Consuming readings', format2)
                sheet.write(5, 5, 'Unit Rate', format2)
                sheet.write(5, 6, 'Unit Rate (Sewage)', format2)
                sheet.write(5, 9, 'Note', format2)
            sheet.write(3, 0, 'From Date:', format11)
            sheet.write(3, 1, DT.datetime.strptime(str(monthly_bill.from_date), '%Y-%m-%d').strftime('%d-%m-%Y'), format3)
            sheet.write(4, 0, 'To Date:', format11)
            sheet.write(4, 1, DT.datetime.strptime(str(monthly_bill.to_date), '%Y-%m-%d').strftime('%d-%m-%Y'), format3)

            sheet.write(5, 0, 'Project', format2)
            # if monthly_bill.bill_type.name == 'Electricity':
            #     sheet.write(5, 1, 'Electricity Account', format2)
            #     sheet.write(5, 4, 'Consumption KWH', format2)
            #     sheet.write(5, 5, 'Consuming readings', format2)
            #     sheet.write(5, 6, 'Unit Rate', format2)
            # else:
            #     sheet.write(5, 1, 'Water Account', format2)
            #     sheet.write(5, 4, 'Consuming readings', format2)
            #     sheet.write(5, 5, 'Unit Rate', format2)
            #     sheet.write(5, 6, 'Unit Rate (Sewage)', format2)
            #     sheet.write(5, 9, 'Note', format2)
            sheet.write(5, 7, 'VAT Amount', format2)
            sheet.write(5, 2, 'Previous Reading', format2)
            sheet.write(5, 3, 'Current Reading', format2)
            sheet.write(5, 7, 'VAT Amount', format2)
            sheet.write(5, 8, 'Total Amount', format2)
            sheet.freeze_panes(6, 0)
            row = 6
            for line in monthly_bill.monthly_bill_ids:
                sheet.set_row(row, 20)
                sheet.write(row, 0, line.building_id.name, format3)
                if monthly_bill.bill_type.name == 'Electricity':
                    sheet.write(row, 1, line.electricity_account, format33)
                    sheet.write(row, 2, line.previous_reading, format33_float)
                    sheet.write(row, 3, line.current_reading, format33_float)
                    sheet.write(row, 4, line.kwh, format33_float)
                    sheet.write(row, 5, line.consumed_reading, format33_float)
                    sheet.write(row, 6, line.unit_rate, format33_float)
                    sheet.write(row, 7, line.tax_amount, format33_float)
                    sheet.write(row, 8, line.total_amount, format33_float)
                elif monthly_bill.bill_type.name == 'Water':
                    sheet.write(row, 1, line.electricity_account, format33)
                    sheet.write(row, 2, line.previous_reading, format33_float)
                    sheet.write(row, 3, line.current_reading, format33_float)
                    sheet.write(row, 4, line.consumed_reading, format33_float)
                    sheet.write(row, 5, line.unit_rate, format33_float)
                    sheet.write(row, 6, line.sewage_rate, format33_float)
                    sheet.write(row, 7, line.tax_amount, format33_float)
                    sheet.write(row, 8, line.total_amount, format33_float)
                    # sheet.write(row, 9, line.remarks, format3)
                row += 1
            sheet.merge_range(row, 0, row, 7, "Grant Total:", format11)
            sheet.write(row, 8, monthly_bill.total_total_amount, format11)
        else:
            sheet.merge_range('A1:I2', 'Monthly '+monthly_bill.bill_type.name +' Bill', format1)
            sheet.write(3, 0, 'From Date:', format11)
            sheet.write(3, 1, DT.datetime.strptime(str(monthly_bill.from_date), '%Y-%m-%d').strftime('%d-%m-%Y'), format3)
            sheet.write(4, 0, 'To Date:', format11)
            sheet.write(4, 1, DT.datetime.strptime(str(monthly_bill.to_date), '%Y-%m-%d').strftime('%d-%m-%Y'), format3)
            # sheet.write(5, 0, 'Project', format2)
            sheet.merge_range(5, 0, 5, 2, 'Project', format2)
            # sheet.write(5, 1, 'Total Amount', format2)
            sheet.merge_range(5, 3, 5, 5, 'Total Amount', format2)
            sheet.freeze_panes(6, 0)
            row = 6
            for line in monthly_bill.monthly_bill_ids:
                # sheet.write(row, 0, line.building_id.name, format3)
                sheet.merge_range(row, 0, row, 2, line.building_id.name, format3)
                # sheet.write(row, 1, line.total_amount, format33_float)
                sheet.merge_range(row, 3, row, 5, line.total_amount,format33_float)
                row += 1
            # sheet.merge_range(row, 0, row, 7, "Grant Total:", format11)
            sheet.merge_range(row, 0, row, 2, "Grant Total:", format11)
            # sheet.write(row, 8, monthly_bill.total_total_amount, format11)
            sheet.merge_range(row, 3, row, 5, monthly_bill.total_total_amount, format11)
            
