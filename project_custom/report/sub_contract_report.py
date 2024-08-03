# -*- coding: utf-8 -*-

import base64
from io import BytesIO
from odoo import models


def get_partner_address(partner):
    address = "{name}\nP.O Box : {zip}, P.C. : 111, {country}\nTel. : {phone}, Email : {email}".format(
        name=partner.display_name,
        zip=partner.zip,
        phone=partner.phone,
        country=partner.country_id.name,
        email=partner.email
    )
    return address


class LncSubContractReport(models.AbstractModel):
    _name = "report.project_custom.report_project_sub_contract_xls.xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "LNC Sub Contract Report"

    def generate_xlsx_report(self, workbook, data, objs):
        company_id = self.env.user.company_id
        sheet = workbook.add_worksheet('Manpower Status Report')

        format1 = workbook.add_format({'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True,
                                       'align': 'center', 'bold': True, 'bg_color': '#bfbfbf', 'valign': 'vcenter'})
        format2 = workbook.add_format({'font_size': 14, 'align': 'center', 'right': True,
                                       'bottom': True, 'top': True, 'bold': True, 'valign': 'vcenter'})
        format3 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter'})
        format4 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True})
        format5 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'bg_color': '#bfbfbf'})
        format6 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True})

        binaryData = company_id.logo
        img_data = base64.b64decode(binaryData)
        im = BytesIO(img_data)
        sheet.insert_image(0, 0, 'logo.png', {'image_data': im, 'x_offset': 0, 'y_offset': 0,
                                              'x_scale': 0.75, 'y_scale': 0.5})
        # Header
        sheet.merge_range(0, 1, 0, 8, get_partner_address(company_id.partner_id), format2)
        sheet.merge_range(2, 0, 2, 8, 'SUB CONTRACT REPORT', format1)
        sheet.set_column(0, 4, 15)
        sheet.set_column(5, 5, 25)
        sheet.set_column(6, 6, 15)
        sheet.set_column(7, 8, 20)
        sheet.set_row(0, 50)
        sheet.set_row(2, 25)

        row = 4
        col = 0
        sheet.write(row, col, 'Date', format4)
        sheet.write(row, col + 1, data["form"]["date"], format3)
        sheet.write(row, col + 7, 'Report Type', format4)
        sheet.write(row, col + 8, data["report_type"], format3)
        sheet.write(row + 1, col, 'Project', format4)
        if data["form"]["project_id"]:
            sheet.write(row + 1, col + 1, data["form"]["project_id"][1], format3)
        else:
            sheet.write(row + 1, col + 1, 'All', format3)
        row += 3
        sheet.write(row, col, 'Sub Contract', format5)
        sheet.write(row, col + 1, 'From Date', format5)
        sheet.write(row, col + 2, 'To Date', format5)
        sheet.write(row, col + 3, 'Type', format5)
        sheet.write(row, col + 4, 'Value', format5)
        sheet.write(row, col + 5, 'Supply/Service Schedule', format5)
        sheet.write(row, col + 6, 'Service Date', format5)
        sheet.write(row, col + 7, 'Remark', format5)
        sheet.write(row, col + 8, 'Service Status', format5)

        row += 1
        for project in data['project_list']:
            if not data['form']['project_id']:
                sheet.merge_range(row, col, row, col + 8, project['name'], format6)
                row += 1
            for contract in project['contracts']:
                sheet.merge_range(row, col, row + len(contract['contract_lines']) - 1, col, contract['name'], format3)
                sheet.merge_range(row, col + 1, row + len(contract['contract_lines']) - 1, col + 1,
                                  contract['date_from'], format3)
                sheet.merge_range(row, col + 2, row + len(contract['contract_lines']) - 1, col + 2, contract['date_to'],
                                  format3)
                sheet.merge_range(row, col + 3, row + len(contract['contract_lines']) - 1, col + 3,
                                  contract['contract_type'], format3)
                sheet.merge_range(row, col + 4, row + len(contract['contract_lines']) - 1, col + 4, contract['value'],
                                  format3)
                sheet.merge_range(row, col + 5, row + len(contract['contract_lines']) - 1, col + 5,
                                  contract['invoice_schedule'], format3)
                for line in contract['contract_lines']:
                    sheet.write(row, col + 6, line['service_date'], format3)
                    sheet.write(row, col + 7, line['remark'], format3)
                    sheet.write(row, col + 8, line['service_status'], format3)
                    row += 1
