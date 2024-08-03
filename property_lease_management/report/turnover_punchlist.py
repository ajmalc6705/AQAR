# -*- coding: utf-8 -*-

import base64
from io import BytesIO
from odoo import models
import datetime as DT
import time


class TurnOverXlsx(models.AbstractModel):
    _name = 'report.property_lease_management.turn_over_punch_list_excel'
    _inherit = 'report.report_xlsx.abstract'
    _description = "TurnOverXlsx"

    def generate_xlsx_report(self, workbook, data, checklist):
        """ generating Turn Over PunchList """
        company_id = self.env.user.company_id
        sheet = workbook.add_worksheet('TurnOver PunchList')

        format1 = workbook.add_format({'font_size': 14, 'right': True, 'left': True, 'top': True,
                                       'align': 'center', 'bold': True, 'valign': 'vcenter'})
        format2 = workbook.add_format({'font_size': 14, 'align': 'center', 'right': True, 'bg_color': '#41689c',
                                       'bottom': True, 'top': True, 'bold': True, 'valign': 'vcenter'})
        format21 = workbook.add_format({'font_size': 12, 'align': 'center', 'right': True,
                                        'bottom': True, 'top': True, 'bold': True, 'valign': 'vcenter'})
        format21_bg = workbook.add_format({'font_size': 12, 'align': 'center', 'bg_color': '#41689c', 'right': True,
                                           'bottom': True, 'top': True, 'bold': True, 'valign': 'vcenter'})
        format22 = workbook.add_format({'font_size': 12, 'align': 'left', 'right': True,
                                        'bottom': True, 'top': True, 'bold': True, 'valign': 'vcenter'})
        format22_bg = workbook.add_format({'font_size': 12, 'align': 'left', 'right': True, 'bg_color': '#41689c',
                                           'bottom': True, 'top': True, 'bold': True, 'valign': 'vcenter'})
        format3 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})
        format33 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                        'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})
        format333 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True, 'right': True, 'left': True,
                                         'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})
        format4 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})

        if company_id.report_image1:
            binaryData = company_id.report_image1
            img_data = base64.b64decode(binaryData)
            im = BytesIO(img_data)
            sheet.insert_image(0, 0, 'logo.png', {'image_data': im, 'x_offset': 0, 'y_offset': 0,
                                                  'x_scale': 1.3, 'y_scale': 1})

        # Header
        # Insert Image [company logo]
        def get_partner_address(partner):
            address = "P.O Box : {zip}, P.C. : 111, {country}\nTel. : {phone}, Email : {email}".format(
                name=partner.display_name,
                zip=partner.zip,
                phone=partner.phone,
                country=partner.country_id.name,
                email=partner.email
            )
            return address

        col_len = 5
        sheet.set_column(0, 0, 8)
        sheet.set_column(1, 1, 25)
        sheet.set_column(2, 2, 10)
        sheet.set_column(3, 3, 10)
        sheet.set_column(4, 4, 12)
        sheet.set_column(5, 5, 40)
        sheet.merge_range('A1:F2', company_id.partner_id.display_name, format1)
        sheet.merge_range('A3:F3', "P.O Box : " + company_id.partner_id.zip + ", P.C. : 111,", format21)
        sheet.merge_range('A4:F4', company_id.country_id.name, format21)
        sheet.merge_range('A5:F5', checklist.building.name, format21)
        sheet.merge_range('A6:F6', "Inspection Check List For Vacating the Flat", format21_bg)
        sheet.write(6, 0, 'Flat No.:', format22)
        sheet.merge_range('B7:C7', checklist.property_id.name, format22)
        sheet.merge_range('D7:E7', "Inspection Date:", format22)
        if checklist.inspection_date:
            sheet.write(6, 5, DT.datetime.strptime(str(checklist.inspection_date), '%Y-%m-%d').strftime('%d-%m-%Y'),
                        format22)
        else:
            sheet.write(6, 5, " ", format22)
        sheet.write(7, 0, 'Tenant:', format22)
        sheet.merge_range('B8:C8', checklist.partner_id.name, format22)
        if checklist.checked:
            sheet.merge_range('D8:F8', "Checked", format22)
        else:
            sheet.merge_range('D8:F8', "Not Checked", format22)
        # sheet.set_row(7, 20)
        sheet.set_row(5, 20)
        sheet.set_row(6, 20)
        sheet.set_row(7, 20)
        sheet.set_row(8, 20)

        sheet.write(8, 0, 'Sr. No.', format2)
        sheet.write(8, 1, 'Description', format2)
        sheet.write(8, 2, 'Quantity', format2)
        sheet.write(8, 3, 'Working', format2)
        sheet.write(8, 4, 'Not Working', format22_bg)
        sheet.write(8, 5, 'Remarks', format2)

        sheet.freeze_panes(9, 0)

        row = 9
        for line in checklist.take_over_checklist:
            sheet.set_row(row, 20)
            if line.session_head:
                sheet.write(row, 0, line.sl_no, format333)
                sheet.write(row, 1, line.description, format33)
            else:
                sheet.write(row, 0, None, format3)
                sheet.write(row, 1, line.description, format3)
            if line.quantity:
                sheet.write(row, 2, line.quantity, format4)
            else:
                sheet.write(row, 2, None, format3)
            if line.yes_working:
                sheet.write(row, 3, " * ", format333)
            else:
                sheet.write(row, 3, None, format3)
            if line.not_working:
                sheet.write(row, 4, " * ", format333)
            else:
                sheet.write(row, 4, None, format3)
            if line.remarks:
                sheet.write(row, 5, line.remarks, format3)
            else:
                sheet.write(row, 5, None, format3)
            row += 1
