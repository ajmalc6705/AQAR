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


class LncProjectReceivableReport(models.AbstractModel):
    _name = "report.project_custom.report_project_receivable_xls.xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "LNC Project Receivable Report"

    def generate_xlsx_report(self, workbook, data, objs):
        company_id = self.env.user.company_id
        sheet = workbook.add_worksheet('Receivable Report')

        format1 = workbook.add_format({'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True,
                                       'align': 'center', 'bold': True, 'bg_color': '#bfbfbf', 'valign': 'vcenter'})
        format2 = workbook.add_format({'font_size': 14, 'align': 'center', 'right': True,
                                       'bottom': True, 'top': True, 'bold': True, 'valign': 'vcenter'})
        format3 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})
        format4 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True})
        format5 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'bg_color': '#bfbfbf'})
        format6 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter'})
        format7 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter'})
        format8 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter'})

        binaryData = company_id.logo
        img_data = base64.b64decode(binaryData)
        im = BytesIO(img_data)
        sheet.insert_image(0, 0, 'logo.png', {'image_data': im, 'x_offset': 0, 'y_offset': 0,
                                              'x_scale': 0.75, 'y_scale': 0.5})
        # Header
        if len(data['form']['project_ids']) != 1:
            col_len = 8
        else:
            col_len = 7
        sheet.merge_range(0, 1, 0, col_len, get_partner_address(company_id.partner_id), format2)
        sheet.merge_range(2, 0, 2, col_len, 'RECEIVABLE REPORT', format1)
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, col_len - 3, 20)
        sheet.set_column(col_len - 2, col_len, 17)
        sheet.set_row(0, 50)
        sheet.set_row(2, 25)
        sheet.set_row(4, 25)

        row = 4
        col = 0
        sheet.write(row, col, 'Project', format4)
        if data["form"]["project_ids"]:
            sheet.merge_range(row, col + 1, row, col + 3, data['project_ids'], format3)
        else:
            sheet.merge_range(row, col + 1, row, col + 3, 'All', format3)
        if data["form"]["inv_date"]:
            sheet.write(row, col_len - 1, 'Invoice Date', format4)
            sheet.write(row, col_len, data["form"]["inv_date"], format3)
        row += 2
        if len(data['form']['project_ids']) != 1:
            sheet.write(row, col, 'Project', format5)
            col += 1
        sheet.write(row, col, 'Customer', format5)
        sheet.write(row, col + 1, 'Invoice Date', format5)
        sheet.write(row, col + 2, 'Number', format5)
        sheet.write(row, col + 3, 'Due Date', format5)
        sheet.write(row, col + 4, 'Source Document', format5)
        sheet.write(row, col + 5, 'Total', format5)
        sheet.write(row, col + 6, 'Balance', format5)
        sheet.write(row, col + 7, 'Total Receivable', format5)

        row += 1
        for project in data['project_list']:
            col = 0
            if len(data['form']['project_ids']) != 1:
                if project['total_count'] > 1:
                    sheet.merge_range(row, col, row + project['total_count'] - 1, col, project['name'], format6)
                else:
                    sheet.write(row, col, project['name'], format6)
                col += 1
            for receivable in project['receivables']:
                if len(receivable['lines']) > 1:
                    sheet.merge_range(row, col, row + len(receivable['lines']) - 1, col, receivable['name'], format3)
                    sheet.merge_range(row, col + 7, row + len(receivable['lines']) - 1, col + 7, receivable['total'],
                                      format8)
                else:
                    sheet.write(row, col, receivable['name'], format3)
                    sheet.write(row, col + 7, receivable['total'], format8)
                for line in receivable['lines']:
                    sheet.write(row, col + 1, line['invoice_date'], format3)
                    sheet.write(row, col + 2, line['number'], format3)
                    sheet.write(row, col + 3, line['due_date'], format3)
                    sheet.write(row, col + 4, line['source'], format3)
                    sheet.write(row, col + 5, line['total'], format7)
                    sheet.write(row, col + 6, line['balance'], format7)
                    row += 1
