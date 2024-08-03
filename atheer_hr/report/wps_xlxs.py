from odoo import models, fields, api
from datetime import date
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
import io
import base64
from io import BytesIO
import datetime as DT
import logging
_logger = logging.getLogger(__name__)


class ReportPayslipWpsBatchBank(models.AbstractModel):
    _name = 'report.atheer_hr.report_payslip_wps_batch_bank'
    _description = "WPS Batch Report"
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, datas, objs):
        company_id = self.env.company
        sheet = workbook.add_worksheet('WPS Batch Report')
        sheet.freeze_panes(1, 0)
        sheet.freeze_panes(2, 0)
        sheet.freeze_panes(3, 0)
        sheet.freeze_panes(4, 0)
        sheet.freeze_panes(5, 0)
        sheet.freeze_panes(6, 0)
        sheet.freeze_panes(7, 0)
        format1 = workbook.add_format({'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True,
                                       'align': 'center', 'bold': True, 'bg_color': '#41689c', 'valign': 'vcenter'})
        format2 = workbook.add_format({'font_size': 14, 'align': 'center', 'right': True,
                                       'bottom': True, 'top': True, 'bold': True, 'valign': 'vcenter'})
        format3 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})
        format4 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': False, 'right': False, 'left': False,
                                       'bottom': False, 'top': False})
        format5 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'bg_color': '#41689c'})
        binaryData = self.env.company.logo
        
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

        col_len = 12
        sheet.merge_range(0, 1, 0, col_len, get_partner_address(company_id.partner_id), format2)
        sheet.merge_range(2, 0, 2, col_len, 'WPS REPORT', format1)
        sheet.set_column(0, 0, 30)
        sheet.set_column('A:A', 10)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 25)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 15)
        sheet.set_column('J:J', 15)
        sheet.set_column('K:K', 15)
        sheet.set_column('L:L', 15)

        sheet.set_row(0, 50)
        sheet.set_row(2, 25)
        row = 3
        col = 0
        sheet.merge_range(row, 0, row, 1,
                          "Period From  : " + DT.datetime.strptime(str(objs.date_start), '%Y-%m-%d').strftime('%d-%m-%Y'),
                          format4)
        sheet.merge_range(row, 3, row, 8,
                          "Batch Name: " + objs.name,
                          format4)
        row += 1
        sheet.merge_range(row, 0, row, 1,
                          "Period To : " + DT.datetime.strptime(str(objs.date_end), '%Y-%m-%d').strftime('%d-%m-%Y'),
                          format4)
        sheet.merge_range(row, 3, row, 4,
                          "Company : " + objs.company_id.name,
                          format4)
        
        row += 2
        sheet.write(row, col, 'ID Type', format5)
        sheet.write(row, col + 1, 'ID No.', format5)
        sheet.write(row, col + 2, 'Employee Name', format5)
        sheet.write(row, col + 3, 'Bank Account', format5)
        sheet.write(row, col + 4, 'Account Number', format5)
        sheet.write(row, col + 5, 'Salary Freq', format5)
        sheet.write(row, col + 6, 'No of Working Days', format5)
        sheet.write(row, col + 7, 'Extra Hours', format5) 
        sheet.write(row, col + 8, 'Basic Salary', format5)
        sheet.write(row, col + 9, 'Extra Income', format5) 
        sheet.write(row, col + 10, 'Deductions', format5) 
        sheet.write(row, col + 11, 'PASI', format5) 
        sheet.write(row, col + 12, 'Net Salary', format5) 

        row += 1
        for line in objs.slip_ids:
            pasi = 0.0
            for line_id in line.line_ids:
                if line_id.code == 'ASI':
                    pasi = line_id.total
            sheet.write(row, 0, 'C', format3)
            sheet.write(row, 1, line.employee_id.employee_id, format3)
            sheet.write(row, 2, line.employee_id.name, format3)
            sheet.write(row, 3, line.employee_id.bank_id.name, format3)
            sheet.write(row, 4, line.employee_id.bank_account, format3)
            sheet.write(row, 5, 'M', format3)
            sheet.write(row, 6, line.total_worked_days, format3)
            sheet.write(row, 7, line.ot_hours, format3)
            sheet.write(row, 8, line.basic_wage, format3)
            sheet.write(row, 9, line.ot_salary, format3)
            sheet.write(row, 10, line.deductions, format3)
            sheet.write(row, 11, pasi, format3)
            sheet.write(row, 12, line.computed_salary, format3)
            row += 1
