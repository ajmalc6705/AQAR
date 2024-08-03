# -*- coding: utf-8 -*-

import base64
import datetime as DT
from io import BytesIO
from odoo import models, api


def get_partner_address(partner):
    address = "{name}\nP.O Box : {zip}, P.C. : 111, {country}\nTel. : {phone}, Email : {email}".format(
        name=partner.display_name,
        zip=partner.zip,
        phone=partner.phone,
        country=partner.country_id.name,
        email=partner.email
    )
    return address


class LncManpowerStatusReport(models.AbstractModel):
    _name = "report.project_custom.report_manpower_status_xls.xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "LNC Manpower Transfer Report"

    def generate_xlsx_report(self, workbook, data, objs):
        company_id = self.env.user.company_id
        sheet = workbook.add_worksheet('Manpower Status Report')

        format1 = workbook.add_format({'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True,
                                       'align': 'center', 'bold': True, 'bg_color': '#bfbfbf', 'valign': 'vcenter'})
        format2 = workbook.add_format({'font_size': 14, 'align': 'center', 'right': True,
                                       'bottom': True, 'top': True, 'bold': True, 'valign': 'vcenter'})
        format3 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True})
        format4 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True})
        format5 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True})
        format6 = workbook.add_format({'font_size': 12, 'align': 'right', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True})
        format7 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'bg_color': '#bfbfbf'})
        format8 = workbook.add_format({'font_size': 12, 'align': 'right', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'bg_color': '#bfbfbf'})

        format9 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'font_color': 'red'})
        format10 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                        'bottom': True, 'top': True, 'font_color': 'red'})
        format11 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                        'bottom': True, 'top': True, 'bg_color': '#bfbfbf', 'font_color': 'red'})

        format12 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'right': True, 'left': True,
                                        'bottom': True, 'top': True, 'font_color': 'green'})
        format13 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                        'bottom': True, 'top': True, 'font_color': 'green'})
        format14 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                        'bottom': True, 'top': True, 'bg_color': '#bfbfbf', 'font_color': 'green'})

        binaryData = company_id.logo
        img_data = base64.b64decode(binaryData)
        im = BytesIO(img_data)
        sheet.insert_image(0, 0, 'logo.png', {'image_data': im, 'x_offset': 0, 'y_offset': 0,
                                              'x_scale': 0.75, 'y_scale': 0.5})
        if data["form"]["project_id"] and data["form"]["location_id"]:
            col_len = 6
        else:
            col_len = 7
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, col_len - 2, 25)
        sheet.set_column(col_len - 1, col_len - 1, 30)
        sheet.set_row(0, 50)
        sheet.set_row(2, 25)
        # Header
        sheet.merge_range(0, 1, 0, col_len - 1, get_partner_address(company_id.partner_id), format2)
        sheet.merge_range(2, 0, 2, col_len - 1, 'MANPOWER STATUS REPORT', format1)

        row = 5
        col = 0
        sheet.write(row, col, 'Date', format5)
        sheet.write(row, col + 1, data["form"]["date"], format5)
        sheet.write(row + 1, col, 'Project', format5)
        sheet.write(row + 1, col + 1, data["form"]["project_id"][1] if data["form"]["project_id"] else 'ALL', format5)
        sheet.write(row + 1, col_len - 2, 'Location', format5)
        sheet.write(row + 1, col_len - 1, data["form"]["location_id"][1] if data["form"]["location_id"] else 'ALL',
                    format5)
        row += 3
        if not data['form']['location_id']:
            sheet.write(row, col, 'Location', format7)
            col += 1
        sheet.write(row, col, 'Manpower Required', format8)
        sheet.write(row, col + 1, 'Manpower Allocated', format8)
        sheet.write(row, col + 2, 'Employees on Leave', format8)
        sheet.write(row, col + 3, 'Manpower Available', format8)
        sheet.write(row, col + 4, 'Employees On Notice', format8)
        sheet.write(row, col + 5, 'Manpower Status', format7)
        row += 1
        col = 0
        for project in data['project_list']:
            if not data['form']['project_id']:
                sheet.merge_range(row, col, row, col_len - 1, project['name'], format5)
                row += 1
            for location in project['location_list']:
                col = 0
                if not data['form']['location_id']:
                    sheet.write(row, col, location['name'], format3)
                    col += 1
                sheet.write(row, col, location['manpower'], format4)
                sheet.write(row, col + 1, location['current_manpower'], format4)
                sheet.write(row, col + 2, location['emp_on_leave'], format4)
                sheet.write(row, col + 3, location['manpower_available'], format4)
                sheet.write(row, col + 4, location['emp_on_notice'], format4)
                if location['manpower_status_type'] == 'shortage':
                    sheet.write(row, col + 5, location['manpower_status_str'], format9)
                elif location['manpower_status_type'] == 'excess':
                    sheet.write(row, col + 5, location['manpower_status_str'], format12)
                else:
                    sheet.write(row, col + 5, location['manpower_status_str'], format3)
                row += 1
            if not data['form']['project_id']:
                col = 0
                sheet.write(row, col, 'Total', format5)
                sheet.write(row, col + 1, project['manpower'], format6)
                sheet.write(row, col + 2, project['current_manpower'], format6)
                sheet.write(row, col + 3, project['emp_on_leave'], format6)
                sheet.write(row, col + 4, project['manpower_available'], format6)
                sheet.write(row, col + 5, project['emp_on_notice'], format6)
                if project['manpower_status_type'] == 'shortage':
                    sheet.write(row, col + 6, project['manpower_status_str'], format10)
                elif project['manpower_status_type'] == 'excess':
                    sheet.write(row, col + 6, project['manpower_status_str'], format13)
                else:
                    sheet.write(row, col + 6, project['manpower_status_str'], format5)
                row += 1
        if not data['form']['location_id']:
            col = 0
            sheet.write(row, col, 'Grand Total', format7)
            sheet.write(row, col + 1, data['total']['manpower'], format8)
            sheet.write(row, col + 2, data['total']['current_manpower'], format8)
            sheet.write(row, col + 3, data['total']['emp_on_leave'], format8)
            sheet.write(row, col + 4, data['total']['manpower_available'], format8)
            sheet.write(row, col + 5, data['total']['emp_on_notice'], format8)
            if data['total']['manpower_status_type'] == 'shortage':
                sheet.write(row, col + 6, data['total']['manpower_status_str'], format11)
            elif data['total']['manpower_status_type'] == 'excess':
                sheet.write(row, col + 6, data['total']['manpower_status_str'], format14)
            else:
                sheet.write(row, col + 6, data['total']['manpower_status_str'], format7)
            row += 1


class ReportManpowerStatus(models.AbstractModel):
    _name = "report.project_custom.report_manpower_status"
    _description = 'Manpower Status Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'data': data,
        }


class ManpowerStatusReportExcel(models.AbstractModel):
    _name = 'report.project_custom.manpower_status_report.xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Manpower Status Report Excel'

    def generate_xlsx_report(self, workbook, datas, projects):
        company_id = self.env.user.company_id
        worksheet = workbook.add_worksheet('Manpower Status Report')

        # Create a format to use in the merged range.
        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10,
            'indent': 15
            # 'x_offset': 15,

        })
        merge_format_head = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10,
            # 'x_offset': 15,

        })
        cell_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'valign': 'bottom',
            'font_size': 10,
        })
        cell__data_format_color = workbook.add_format({
            'bold': 0,
            'border': 1,
            'align': 'left',
            'valign': 'bottom',
            'font_size': 10,
            'bg_color': '#42f4ad'
        })
        cell__data_format = workbook.add_format({
            'bold': 0,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
        })
        cell__data_format_bold = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
        })
        cell__data_format_footer_bold_left = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
        })
        cell__data_format_details = workbook.add_format({
            'bold': 0,
            'border': 1,
            'align': 'left',
            'valign': 'top',
            'font_size': 10,
            # 'underline': True
        })
        datetime_format = workbook.add_format({
            'num_format': 'dd-mm-yyyy hh:mm:ss',
            'bold': 0,
            'border': 1,
            'align': 'left',
            'valign': 'bottom',
            'font_size': 10,
        })
        date_format = workbook.add_format({
            'num_format': 'dd-mm-yyyy',
            'bold': 0,
            'border': 1,
            'align': 'left',
            'valign': 'bottom',
            'font_size': 10,
        })
        cell__data_format_header_bold = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10,
        })

        # Insert Image [company logo]
        # worksheet.insert_image('B2', 'python.png')
        def get_partner_address(partner):
            address = "{name}\nP.O Box : {zip}, P.C. : 111, {country}\nTel. : {phone}, Email : {email}".format(
                name=partner.display_name,
                zip=partner.zip,
                phone=partner.phone,
                country=partner.country_id.name,
                email=partner.email
            )
            return address

        def format_date(date):
            if date:
                date = "{from_date}". \
                    format(from_date=DT.datetime.strptime(date, '%Y-%m-%d').strftime('%d-%m-%Y'))
                return date
            else:
                return ''

        binaryData = company_id.logo
        data = base64.b64decode(binaryData)
        im = BytesIO(data)
        worksheet.insert_image(0, 0, 'logo.png', {'image_data': im, 'x_offset': 0, 'y_offset': 0,
                                                  'x_scale': 0.75, 'y_scale': 0.5,
                                                  })

        # Column Headers
        worksheet.set_column(0, 0, 32)
        # column Headers End

        #  1,2 th row height
        worksheet.set_row(0, 17)
        worksheet.set_row(1, 17)
        worksheet.set_row(2, 17)
        worksheet.set_row(4, 25)
        # Merge Header
        col = 25
        worksheet.merge_range(3, 0, 3, col, 'MANPOWER STATUS AS ON %s' % format_date(str(DT.datetime.today().date())),
                              merge_format)
        worksheet.merge_range(0, 0, 2, col - 3, get_partner_address(company_id.partner_id), merge_format)
        worksheet.write(0, col - 2, 'Doc. No.', cell_format)
        worksheet.write(0, col - 1, '', cell__data_format)
        worksheet.write(1, col - 2, 'Rev. No.', cell_format)
        worksheet.write(1, col - 1, '', cell__data_format)
        worksheet.write(2, col - 2, 'Page', cell_format)
        worksheet.write(2, col - 1, '', cell__data_format)
        worksheet.merge_range(1, col, 2, col, 'Eff. Date:\n18-05-15', cell__data_format_header_bold)

        # col width
        worksheet.set_column(0, 0, 4)
        worksheet.set_column(1, 1, 25)
        worksheet.set_column(2, 14, 4)
        worksheet.set_column(15, 15, 8)
        worksheet.set_column(16, 16, 4)
        worksheet.set_column(17, 17, 8)
        worksheet.set_column(18, 23, 4)

        # data
        row = 4
        col = 0
        # worksheet.write(row, col, 'Sr.\nNo.', cell_format)
        worksheet.merge_range(row, col, row + 2, col, 'Sr.\nNo.', merge_format_head)
        worksheet.merge_range(row, col + 1, row + 2, col + 1, 'Project No. / Details', merge_format_head)
        worksheet.write(row, col + 2, '', cell__data_format)
        worksheet.merge_range(row, col + 3, row, col + 16, 'Workers', merge_format_head)
        worksheet.merge_range(row + 1, col + 2, row + 2, col + 2, 'S', merge_format_head)
        worksheet.merge_range(row + 1, col + 3, row + 2, col + 3, 'FM', merge_format_head)
        worksheet.merge_range(row + 1, col + 4, row + 2, col + 4, 'CH', merge_format_head)
        worksheet.merge_range(row + 1, col + 5, row + 2, col + 5, 'SC', merge_format_head)
        worksheet.merge_range(row + 1, col + 6, row + 2, col + 6, 'FC', merge_format_head)
        worksheet.merge_range(row + 1, col + 7, row + 2, col + 7, 'SF', merge_format_head)
        worksheet.merge_range(row + 1, col + 8, row + 2, col + 8, 'M', merge_format_head)
        worksheet.merge_range(row + 1, col + 9, row + 2, col + 9, 'TM', merge_format_head)
        worksheet.merge_range(row + 1, col + 10, row + 2, col + 10, 'P/PO', merge_format_head)
        worksheet.merge_range(row + 1, col + 11, row + 2, col + 11, 'H', merge_format_head)
        worksheet.merge_range(row + 1, col + 12, row + 2, col + 12, 'SK', merge_format_head)
        worksheet.merge_range(row + 1, col + 13, row + 2, col + 13, 'CB', merge_format_head)
        worksheet.merge_range(row + 1, col + 14, row + 2, col + 14, 'OB', merge_format_head)
        worksheet.merge_range(row + 1, col + 15, row + 2, col + 15, 'JCB/RC\nC/Oprtr', merge_format_head)
        worksheet.merge_range(row + 1, col + 16, row + 2, col + 16, 'D', merge_format_head)
        worksheet.merge_range(row, col + 17, row + 2, col + 17, 'Sub\nTotal\n(A)', merge_format_head)
        worksheet.merge_range(row, col + 18, row, col + 23, 'MEP', merge_format_head)
        worksheet.merge_range(row + 1, col + 18, row + 2, col + 18, 'S', merge_format_head)
        worksheet.merge_range(row + 1, col + 19, row + 2, col + 19, 'E', merge_format_head)
        worksheet.merge_range(row + 1, col + 20, row + 2, col + 20, 'PL', merge_format_head)
        worksheet.merge_range(row + 1, col + 21, row + 2, col + 21, 'A/C\nTech', merge_format_head)
        worksheet.merge_range(row + 1, col + 22, row + 2, col + 22, 'H\nTech', merge_format_head)
        worksheet.merge_range(row + 1, col + 23, row + 2, col + 23, 'ST.\nCblg', merge_format_head)
        worksheet.merge_range(row, col + 24, row + 2, col + 24, 'Sub Total\n(B)', merge_format_head)
        worksheet.merge_range(row, col + 25, row + 2, col + 25, 'Total', merge_format_head)

        row = 7
        col = 0
        count = 1

        if datas.get('project_id', 0):
            domain = [('id', 'in', datas.get('project_id'))]
        # elif projects:
        #     domain = [('id', 'in', projects.ids)]
        else:
            domain = []
        projects = self.env['project.project'].sudo().search(domain)
        len_s = 0
        len_fm = 0
        len_ch = 0
        len_sc = 0
        len_fc = 0
        len_sf = 0
        len_m = 0
        len_tm = 0
        len_p = 0
        len_h = 0
        len_sk = 0
        len_cb = 0
        len_ob = 0
        len_j = 0
        len_d = 0
        len_ms = 0
        len_me = 0
        len_mpl = 0
        len_ac = 0
        len_ht = 0
        len_st = 0
        sub_taa = 0
        sub_tbb = 0
        total = 0

        for record in projects:
            worksheet.write(row, col, count)
            worksheet.write(row, col + 1, record.name)
            # Workers
            worksheet.write(row, col + 2, len(record.w_supervisor.ids) if record.w_supervisor.ids else 0,
                            cell__data_format)
            worksheet.write(row, col + 3, len(record.w_fm.ids) if record.w_fm.ids else 0, cell__data_format)
            worksheet.write(row, col + 4, len(record.w_ch.ids) if record.w_ch.ids else 0, cell__data_format)
            worksheet.write(row, col + 5, len(record.w_sh.ids) if record.w_sh.ids else 0, cell__data_format)
            worksheet.write(row, col + 6, len(record.w_fc.ids) if record.w_fc.ids else 0, cell__data_format)
            worksheet.write(row, col + 7, len(record.w_sf.ids) if record.w_sf.ids else 0, cell__data_format)
            worksheet.write(row, col + 8, len(record.w_mason.ids) if record.w_mason.ids else 0, cell__data_format)
            worksheet.write(row, col + 9, len(record.w_tm.ids) if record.w_tm.ids else 0, cell__data_format)
            worksheet.write(row, col + 10, len(record.w_ppo.ids) if record.w_ppo.ids else 0, cell__data_format)
            worksheet.write(row, col + 11, len(record.w_helper.ids) if record.w_helper.ids else 0, cell__data_format)
            worksheet.write(row, col + 12, len(record.w_sk.ids) if record.w_sk.ids else 0, cell__data_format)
            worksheet.write(row, col + 13, len(record.w_cb.ids) if record.w_cb.ids else 0, cell__data_format)
            worksheet.write(row, col + 14, len(record.w_ob.ids) if record.w_ob.ids else 0, cell__data_format)
            worksheet.write(row, col + 15, len(record.w_jcb_rcc_optr.ids) if record.w_jcb_rcc_optr.ids else 0,
                            cell__data_format)
            worksheet.write(row, col + 16, len(record.w_driver.ids) if record.w_driver.ids else 0, cell__data_format)

            len_s += len(record.w_supervisor.ids)
            len_fm += len(record.w_fm.ids)
            len_ch += len(record.w_ch.ids)
            len_sc += len(record.w_sh.ids)
            len_fc += len(record.w_fc.ids)
            len_sf += len(record.w_sf.ids)
            len_m += len(record.w_mason.ids)
            len_tm += len(record.w_tm.ids)
            len_p += len(record.w_ppo.ids)
            len_h += len(record.w_helper.ids)
            len_sk += len(record.w_sk.ids)
            len_cb += len(record.w_cb.ids)
            len_ob += len(record.w_ob.ids)
            len_j += len(record.w_jcb_rcc_optr.ids)
            len_d += len(record.w_driver.ids)
            sub_ta = len(record.w_supervisor.ids) + len(record.w_fm.ids) + len(record.w_ch.ids) + len(record.w_sh.ids) + \
                     len(record.w_fc.ids) + len(record.w_sf.ids) + len(record.w_mason.ids) + len(record.w_tm.ids) + len(
                record.w_ppo.ids) + \
                     len(record.w_helper.ids) + len(record.w_sk.ids) + len(record.w_cb.ids) + len(record.w_ob.ids) + \
                     len(record.w_jcb_rcc_optr.ids) + len(record.w_driver.ids)
            sub_taa += sub_ta

            worksheet.write(row, col + 17, sub_ta, cell__data_format_bold)
            # MEP
            worksheet.write(row, col + 18, len(record.m_supervisor.ids) if record.m_supervisor.ids else 0,
                            cell__data_format)
            worksheet.write(row, col + 19, len(record.w_elec.ids) if record.w_elec.ids else 0, cell__data_format)
            worksheet.write(row, col + 20, len(record.w_pl.ids) if record.w_pl.ids else 0, cell__data_format)
            worksheet.write(row, col + 21, len(record.m_ac_tech.ids) if record.m_ac_tech.ids else 0, cell__data_format)
            worksheet.write(row, col + 22, len(record.m_helper.ids) if record.m_helper.ids else 0, cell__data_format)
            worksheet.write(row, col + 23, len(record.m_cable.ids) if record.m_cable.ids else 0, cell__data_format)

            len_ms += len(record.m_supervisor.ids)
            len_me += len(record.w_elec.ids)
            len_mpl += len(record.w_pl.ids)
            len_ac += len(record.m_ac_tech.ids)
            len_ht += len(record.m_helper.ids)
            len_st += len(record.m_cable.ids)
            sub_tb = len(record.m_supervisor.ids) + len(record.w_elec.ids) + len(record.w_pl.ids) + len(
                record.m_ac_tech.ids) + \
                     len(record.m_helper.ids) + len(record.m_cable.ids)
            sub_tbb += sub_tb
            worksheet.write(row, col + 24, sub_tb, cell__data_format_bold)
            sub_total = sub_tb + sub_ta
            total += sub_total
            worksheet.write(row, col + 25, sub_total, cell__data_format_bold)
            count += 1
            row += 1
        # Sub Totals, Total
        worksheet.write(row, col + 1, "Total", cell_format)
        worksheet.write(row, col + 2, len_s, cell_format)
        worksheet.write(row, col + 3, len_fm, cell_format)
        worksheet.write(row, col + 4, len_ch, cell_format)
        worksheet.write(row, col + 5, len_sc, cell_format)
        worksheet.write(row, col + 6, len_fc, cell_format)
        worksheet.write(row, col + 7, len_sf, cell_format)
        worksheet.write(row, col + 8, len_m, cell_format)
        worksheet.write(row, col + 9, len_tm, cell_format)
        worksheet.write(row, col + 10, len_p, cell_format)
        worksheet.write(row, col + 11, len_h, cell_format)
        worksheet.write(row, col + 12, len_sk, cell_format)
        worksheet.write(row, col + 13, len_cb, cell_format)
        worksheet.write(row, col + 14, len_ob, cell_format)
        worksheet.write(row, col + 15, len_j, cell_format)
        worksheet.write(row, col + 16, len_d, cell_format)
        worksheet.write(row, col + 17, sub_taa, cell_format)
        worksheet.write(row, col + 18, len_ms, cell_format)
        worksheet.write(row, col + 19, len_me, cell_format)
        worksheet.write(row, col + 20, len_mpl, cell_format)
        worksheet.write(row, col + 21, len_ac, cell_format)
        worksheet.write(row, col + 22, len_ht, cell_format)
        worksheet.write(row, col + 23, len_st, cell_format)
        worksheet.write(row, col + 24, sub_tbb, cell_format)
        worksheet.write(row, col + 25, total, cell_format)

        # Acronym
        worksheet.merge_range(row + 2, col, row + 2, col + 1, ' Acronym', merge_format_head)
        worksheet.write(row + 3, col, "S", cell__data_format_color)
        worksheet.write(row + 3, col + 1, "Supervisor", cell__data_format)
        worksheet.write(row + 4, col, "FM", cell__data_format_color)
        worksheet.write(row + 4, col + 1, "Foreman", cell__data_format)
        worksheet.write(row + 5, col, "CH", cell__data_format_color)
        worksheet.write(row + 5, col + 1, "Chargehand", cell__data_format)
        worksheet.write(row + 6, col, "SC", cell__data_format_color)
        worksheet.write(row + 6, col + 1, "Shuttering Carpenter", cell__data_format)
        worksheet.write(row + 7, col, "SF", cell__data_format_color)
        worksheet.write(row + 7, col + 1, "Steel Filter", cell__data_format)
        worksheet.write(row + 8, col, "M", cell__data_format_color)
        worksheet.write(row + 8, col + 1, "Mason", cell__data_format)
        worksheet.write(row + 9, col, "TM", cell__data_format_color)
        worksheet.write(row + 9, col + 1, "Tiles Mason", cell__data_format)
        worksheet.write(row + 10, col, "P/PO", cell__data_format_color)
        worksheet.write(row + 10, col + 1, "Painter / Polisher", cell__data_format)
        worksheet.write(row + 11, col, "H", cell__data_format_color)
        worksheet.write(row + 11, col + 1, "Helper", cell__data_format)
        worksheet.write(row + 12, col, "SK", cell__data_format_color)
        worksheet.write(row + 12, col + 1, "Store Keeper", cell__data_format)
        worksheet.write(row + 13, col, "CB", cell__data_format_color)
        worksheet.write(row + 13, col + 1, "Camp Boss", cell__data_format)
        worksheet.write(row + 14, col, "OB", cell__data_format_color)
        worksheet.write(row + 14, col + 1, "Office Boy", cell__data_format)
        worksheet.write(row + 15, col, "D", cell__data_format_color)
        worksheet.write(row + 15, col + 1, "Driver", cell__data_format)
        worksheet.write(row + 16, col, "E", cell__data_format_color)
        worksheet.write(row + 16, col + 1, "Electrician", cell__data_format)
        worksheet.write(row + 17, col, "PL", cell__data_format_color)
        worksheet.write(row + 17, col + 1, "Plumber", cell__data_format)
