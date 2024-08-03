# -*- coding: utf-8 -*-

import base64
from io import BytesIO
from odoo import models, _
from odoo.exceptions import UserError, MissingError


def get_partner_address(partner):
    address = "{name}\nP.O Box : {zip}, P.C. : 111, {country}\nTel. : {phone}, Email : {email}".format(
        name=partner.display_name,
        zip=partner.zip,
        phone=partner.phone,
        country=partner.country_id.name,
        email=partner.email
    )
    return address


class LncTenderReport(models.AbstractModel):
    _name = "report.project_custom.report_project_tender_xls.xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "LNC Tender Report"

    def generate_xlsx_report(self, workbook, data, objs):
        company_id = self.env.user.company_id
        # if not objs.mapped('competitor_ids'):
        #     return {'warning': _('No Competitor details! \n Competitor details are not available for selected tender.')}
        format1 = workbook.add_format({'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True,
                                       'align': 'center', 'bold': True, 'bg_color': '#bfbfbf', 'valign': 'vcenter'})
        format2 = workbook.add_format({'font_size': 14, 'align': 'center', 'right': True,
                                       'bottom': True, 'top': True, 'bold': True, 'valign': 'vcenter'})
        format3 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True})
        format4 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True})
        format5 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter'})

        binaryData = company_id.logo
        img_data = base64.b64decode(binaryData)
        im = BytesIO(img_data)
        for tender in objs:
            if tender.type_contract == 'lump_sum':
                contract_type = 'Lump Sum'
            elif tender.type_contract == 'unit_rate':
                contract_type = 'Unit Rate'
            elif tender.type_contract == 'manpower_rate':
                contract_type = 'Manpower Rate'
            elif tender.type_contract == '55':
                contract_type = 'Clause 55'
            elif tender.type_contract == '56':
                contract_type = 'Clause 56'
            else:
                contract_type = ''
            sheet = workbook.add_worksheet(tender.tender_no)
            sheet.set_row(0, 50)
            sheet.set_row(2, 25)
            sheet.set_row(14, 35)
            sheet.set_column(0, 3, 30)
            sheet.insert_image(0, 0, 'logo.png', {'image_data': im, 'x_offset': 0, 'y_offset': 0,
                                                  'x_scale': 0.75, 'y_scale': 0.5})
            sheet.merge_range(0, 1, 0, 3, get_partner_address(company_id.partner_id), format2)
            sheet.merge_range(2, 0, 2, 3, 'TENDER REPORT', format1)

            sheet.write('A5', 'Tender No', format5)
            sheet.write('B5', tender.tender_no or '', format3)
            sheet.write('C5', 'Tender Reference', format5)
            sheet.write('D5', tender.tender_ref or '', format3)
            sheet.write('A6', 'Tender Title', format5)
            sheet.write('B6', tender.tender_title or '', format3)
            sheet.write('C6', 'Priority', format5)
            sheet.write('D6', dict(tender._fields['priority'].selection).get(tender.priority) or '', format3)
            sheet.write('A7', 'Type', format5)
            sheet.write('B7', tender.project_tender_type.name)
            sheet.write('C7', 'Contract Type', format5)
            sheet.write('D7', contract_type or '', format3)
            sheet.write('A8', 'Location', format5)
            sheet.write('B8', tender.location or '', format3)
            sheet.write('C8', 'Client', format5)
            sheet.write('D8', tender.client or '', format3)
            sheet.write('A9', 'Tender Sub type', format5)
            sheet.write('B9', tender.sub_type.name or '', format3)
            sheet.write('C9', 'Extended Days', format5)
            sheet.write('D9', tender.extended_days or '', format3)

            sheet.merge_range('A10:D10', 'Estimation Details', format4)
            sheet.write('A11', 'Manpower Required', format5)
            sheet.write('B11', tender.manpower or '', format3)
            sheet.write('C11', 'Project Duration', format5)
            sheet.write('D11', tender.project_duration or '', format3)
            sheet.write('A12', 'Mobilisation Duration', format5)
            sheet.write('B12', tender.mobilization_duration or '', format3)
            sheet.write('C12', 'Project Cost', format5)
            sheet.write('D12', tender.project_cost or '', format3)

            sheet.write('A13', 'Project Buffer Amount', format5)
            sheet.write('B13', tender.project_buffer_amount or '', format3)
            sheet.write('C13', 'Profit %', format5)
            sheet.write('D13', tender.profit_perc or '', format3)

            sheet.write('A14', 'Project Total', format5)
            sheet.write('B14', tender.project_total or '', format3)
            sheet.write('C14', 'Minimum Monthly Claim', format5)
            sheet.write('D14', tender.minimum_monthly_claim or '', format3)

            sheet.write('A15', 'Description', format5)
            sheet.merge_range('B15:D15', tender.description or '', format3)

            sheet.merge_range('A16:D16', 'Competitor Details', format4)
            sheet.merge_range('A17:B17', 'Company Name', format5)
            sheet.write('C17', 'Value', format5)
            sheet.write('D17', 'Position', format5)
            row = 18
            col = 0
            for competitor in tender.competitor_ids:
                sheet.merge_range(row, col, row, col + 1, competitor.company_name, format3)
                sheet.write(row, col + 2, competitor.value or '', format3)
                sheet.write(row, col + 3, competitor.position or '', format3)
                row += 1
