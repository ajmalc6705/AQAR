# -*- coding: utf-8 -*-

import base64
from io import BytesIO
from odoo import models
import datetime as DT
from datetime import *
from dateutil.relativedelta import relativedelta


class PropertyForcastingReport(models.AbstractModel):
    _name = 'report.property_lease_management.property_forcasting_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Property Forcasting Report"

    def generate_xlsx_report(self, workbook, data, wizard):
        """ generating Property Forcasting Report """
        if wizard.building_select == 'all':
            building_data = self.env['property.building'].search([])
        else:
            building_data = wizard.building_ids

        format1 = workbook.add_format({'font_size': 14, 'right': True, 'left': True, 'top': True,
                                       'align': 'center', 'bold': True, 'valign': 'vcenter'})
        format11 = workbook.add_format({'font_size': 12, 'right': True, 'left': True, 'top': True, 'bottom': True,
                                        'align': 'center', 'bold': False, 'valign': 'vcenter'})
        format2 = workbook.add_format({'font_size': 10, 'align': 'center', 'right': True, 'top': True, 'bold': True,
                                       'text_wrap': True, 'bottom': True, 'bg_color': '#f5b8b8', 'valign': 'vcenter'})
        format3 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})
        format3_red = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True, 'right': True,
                                           'left': True, 'bottom': True, 'top': True, 'valign': 'vcenter',
                                           'text_wrap': True, 'bg_color': '#f20707'})
        format_vacant = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': False, 'right': True,
                                             'left': True, 'bottom': True, 'top': True, 'valign': 'vcenter',
                                             'text_wrap': True, 'bg_color': '#939694'})
        format33 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': False, 'right': True, 'left': True,
                                        'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})
        for building in building_data:
            sheet = workbook.add_worksheet(building.name)
            sheet.set_column(0, 0, 5)
            sheet.set_column(1, 1, 10)
            sheet.set_column(2, 2, 10)
            sheet.set_column(3, 3, 25)
            sheet.set_column(4, 4, 10)
            sheet.set_column(5, 5, 10)
            sheet.set_column(6, 6, 10)
            sheet.set_column(7, 7, 10)
            sheet.set_column(8, 8, 10)
            sheet.set_column(9, 9, 10)
            sheet.merge_range('A1:C1', "Aqar Real Estate", format1)
            sheet.merge_range('A2:C2', building.name, format1)
            address = ""
            address = address + (building.bld_no + ',') if building.bld_no else " "
            address = address + (building.way_no + ',') if building.way_no else " "
            address = address + (building.plot_no + ',') if building.plot_no else " "
            address = address + building.building_area.name if building.building_area.name else " "
            sheet.merge_range('A2:C2', address, format11)
            row = 5
            sl_no = 1
            sheet.set_row(row, 25)
            sheet.merge_range('A5:A6', 'SL NO.', format2)
            sheet.merge_range('B5:B6', 'Unit No', format2)
            sheet.merge_range('C5:C6', 'Type', format2)
            sheet.merge_range('D5:D6', "TENANT'S NAME", format2)
            sheet.merge_range('E5:G5', 'RENTAL', format2)
            sheet.merge_range('H5:I5', 'TENANCY PERIOD', format2)
            sheet.write(row, 4, 'Expected Rent', format2)
            sheet.write(row, 5, 'Actual Rent', format2)
            sheet.write(row, 6, 'Terms', format2)
            sheet.write(row, 7, 'From', format2)
            sheet.write(row, 8, 'To', format2)
            col = 9
            total_expected_rent = 0
            total_actual_rent = 0
            start_date = datetime.strptime(str(wizard.date_from), "%Y-%m-%d").date()
            end_date = datetime.strptime(str(wizard.date_to), "%Y-%m-%d")
            # setting header row for months
            date1 = datetime.strptime(str(wizard.date_from), "%Y-%m-%d").date()
            date1 = date1.replace(day=1)
            date2 = datetime.strptime(str(wizard.date_to), "%Y-%m-%d").date()
            if date2.month != 12:
                date2_month = date2.month + 1
                date2_year = date2.year
            else:
                date2_month = 1
                date2_year = date2.year + 1
            date2 = date2.replace(day=1, month=date2_month, year=date2_year)
            while date1 < date2:
                month = date1.month
                year = date1.year
                month_data = str(month) + "/" + str(year)
                sheet.write(row, col, month_data, format2)
                next_month = month + 1 if month != 12 else 1
                next_year = year + 1 if next_month == 1 else year
                date1 = date1.replace(month=next_month, year=next_year)
                col += 1

            row += 1
            monthly_total = {}
            for flat in building.property_ids:
                red = 0
                sheet.write(row, 0, sl_no, format3)
                sheet.write(row, 1, flat.name, format3)
                sheet.write(row, 2, flat.property_type_id.name, format3)
                sheet.write(row, 4, flat.rent_id.property_id.rent_monthly, format3)
                total_expected_rent += flat.rent_id.property_id.rent_monthly
                sheet.write(row, 5, flat.rent_id.agreed_rent_amount, format3)
                total_actual_rent += flat.rent_id.agreed_rent_amount
                sheet.write(row, 6, flat.rent_id.installment_schedule, format3)

                if flat.state == 'open':
                    sheet.write(row, 3, "Vacant", format_vacant)
                    sheet.write(row, 7, " ", format3)
                    sheet.write(row, 8, " ", format3)
                else:
                    sheet.write(row, 7,
                                DT.datetime.strptime(str(flat.rent_id.from_date), '%Y-%m-%d').strftime('%d-%m-%Y'),
                                format3)
                    sheet.write(row, 8,
                                DT.datetime.strptime(str(flat.rent_id.to_date), '%Y-%m-%d').strftime('%d-%m-%Y'),
                                format3)
                    if flat.rent_id.to_date < start_date:
                        sheet.write(row, 3, "Vacant", format_vacant)
                    else:
                        sheet.write(row, 3, flat.rent_id.partner_id.name, format3)

                col = 9
                date1 = datetime.strptime(str(wizard.date_from), "%Y-%m-%d").date()
                date2 = datetime.strptime(str(wizard.date_to), "%Y-%m-%d").date()
                date1 = date1.replace(day=1)
                if date2.month != 12:
                    date2_month = date2.month + 1
                    date2_year = date2.year
                else:
                    date2_month = 1
                    date2_year = date2.year + 1
                date2 = date2.replace(day=1, month=date2_month, year=date2_year)
                while date1 < date2:
                    if flat.state == 'open':
                        sheet.write(row, col, "V", format3)
                    else:
                        if flat.rent_id.to_date < start_date:
                            sheet.write(row, col, "V", format3)
                        else:
                            if flat.rent_id.to_date < date1:
                                sheet.write(row, col, "E", format3)
                            else:
                                if date1.month != 12:
                                    search_to_date = date1.replace(day=1, month=date1.month + 1)
                                else:
                                    search_to_date = date1.replace(day=1, month=1, year=date1.year + 1)
                                paid = 0
                                if flat.rent_id.installment_schedule == 'monthly':
                                    collection_amount = sum(
                                        flat.rent_id.collection_ids.filtered(
                                            lambda x: date1 <= x.date < search_to_date and x.state != 'draft0').mapped(
                                            'amount'))
                                elif flat.rent_id.installment_schedule == 'quaterly':
                                    period = int(flat.rent_id.period // 3)
                                    period_len = 3
                                    first_date = flat.rent_id.from_date
                                    for i in range(period):
                                        next_date = first_date + relativedelta(months=period_len)
                                        search_first_date = first_date.replace(day=1)
                                        search_next_date = next_date.replace(day=1)
                                        if search_first_date <= date1 < search_next_date:
                                            collection_amount = sum(
                                                flat.rent_id.collection_ids.filtered(lambda
                                                                                         x: first_date <= x.date < next_date and x.state != 'draft0').mapped(
                                                    'amount'))
                                            break
                                        first_date = next_date
                                        next_date = first_date + relativedelta(months=+period_len)
                                elif flat.rent_id.installment_schedule == 'six_month':
                                    period = int(flat.rent_id.period // 6)
                                    period_len = 6
                                    first_date = flat.rent_id.from_date
                                    for i in range(period):
                                        next_date = first_date + relativedelta(months=period_len)
                                        search_first_date = first_date.replace(day=1)
                                        search_next_date = next_date.replace(day=1)
                                        if search_first_date <= date1 < search_next_date:
                                            collection_amount = sum(
                                                flat.rent_id.collection_ids.filtered(lambda
                                                                                         x: first_date <= x.date < next_date and x.state != 'draft0').mapped(
                                                    'amount'))
                                            break
                                        first_date = next_date
                                        next_date = first_date + relativedelta(months=+period_len)
                                elif flat.rent_id.installment_schedule == 'yearly':
                                    period = int(flat.rent_id.period // 12)
                                    period_len = 12
                                    first_date = flat.rent_id.from_date
                                    for i in range(period):
                                        next_date = first_date + relativedelta(months=period_len)
                                        search_first_date = first_date.replace(day=1)
                                        search_next_date = next_date.replace(day=1)
                                        if search_first_date <= date1 < search_next_date:
                                            collection_amount = sum(
                                                flat.rent_id.collection_ids.filtered(lambda
                                                                                         x: first_date <= x.date < next_date and x.state != 'draft0').mapped(
                                                    'amount'))
                                            break
                                        first_date = next_date
                                        next_date = first_date + relativedelta(months=+period_len)
                                else:
                                    collection_amount = sum(
                                        flat.rent_id.collection_ids.filtered(lambda
                                                                                 x: flat.rent_id.from_date <= x.date < flat.rent_id.to_date and x.state != 'draft0').mapped(
                                            'amount'))
                                if flat.rent_id.from_date > date1 and flat.rent_id.from_date > search_to_date:
                                    sheet.write(row, col, "E", format3)
                                elif collection_amount >= flat.rent_id.agreed_rent_amount:
                                    paid = 1
                                    sheet.write(row, col, flat.rent_id.agreed_rent_amount, format3)
                                else:
                                    red = 1
                                    sheet.write(row, col, "D", format3)
                                # if sum(flat.rent_id.collection_ids.filtered(
                                #         lambda x: date1 <= x.date < search_to_date).mapped('residual')):
                                #     red = 1
                                if paid:
                                    if col in monthly_total.keys():
                                        monthly_total[col] = monthly_total[col] + flat.rent_id.agreed_rent_amount
                                    else:
                                        monthly_total[col] = flat.rent_id.agreed_rent_amount
                                else:
                                    if col in monthly_total.keys():
                                        monthly_total[col] = monthly_total[col] + 0
                                    else:
                                        monthly_total[col] = 0
                    month = date1.month
                    year = date1.year
                    next_month = month + 1 if month != 12 else 1
                    next_year = year + 1 if next_month == 1 else year
                    date1 = date1.replace(month=next_month, year=next_year)
                    col += 1
                if red:
                    sheet.write(row, 3, flat.rent_id.partner_id.name, format3_red)
                row += 1
                sl_no += 1
            sheet.write(row, 3, "Total", format1)
            sheet.write(row, 4, total_expected_rent, format1)
            sheet.write(row, 5, total_actual_rent, format1)
            sheet.write(row, 8, "Total", format1)
            column = 9
            for length in monthly_total:
                sheet.write(row, column, monthly_total[length], format1)
                column += 1
