# -*- coding: utf-8 -*-

from datetime import datetime,date
from odoo import models, api, fields, _
from odoo.exceptions import UserError
import base64
from io import BytesIO


class LoanOutstandingReportWiz(models.TransientModel):
    _name = "loan.outstanding.report.wiz"
    _description = _("Monthly Rent Collection Report Wizard")

    employee_id = fields.Many2many('hr.employee', string='Employee')
    department_id = fields.Many2many('hr.department', string='Department')
    bu_cc = fields.Many2many('account.analytic.account', string='Business unit',
                             relation='loan_outstanding_report_wiz_bucc_rel')

    def button_print_report(self):
        datas = {}
        if self.employee_id:
            datas['employee_id'] = self.employee_id.ids
        if self.department_id:
            datas['department_id'] = self.department_id.ids
        if self.bu_cc:
            datas['bu_cc'] = self.bu_cc.ids
        domain = [('state', '=', 'approved')]
        if datas.get('employee_id', 0):
            domain.append(('employee_id', 'in', datas.get('employee_id', 0)))
        if datas.get('department_id', 0):
            domain.append(('department', 'in', datas.get('department_id')))
        loans = self.env['hr.loan'].search(domain, order='employee_id ASC')
        if not loans:
            raise UserError("No data found!")
        datas = {'loan': loans.ids,
                 'employee': self.employee_id.ids,
                 'department_id': self.department_id.ids,
                 'bu_cc': self.bu_cc.ids,
                 }
        report = self.env['ir.actions.report']._get_report_from_name(
            'atheer_hr.loan_outstanding_report.xlsx')
        report.report_file = 'Loan Outstanding Report' + '-' + str(date.today())
        return self.env.ref('atheer_hr.loan_outstanding_report_xls').report_action(None, data=datas, config=False)


class LoanOutstandingReport(models.AbstractModel):
    _name = "report.atheer_hr.loan_outstanding_report.xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Loan Outstanding Report"

    def generate_xlsx_report(self, workbook, datas, sheets):
        company_id = self.env.user.company_id
        worksheet = workbook.add_worksheet('Loan Outstanding Report')
        worksheet.freeze_panes(1, 0)
        worksheet.freeze_panes(2, 0)
        worksheet.freeze_panes(3, 0)
        worksheet.freeze_panes(4, 0)
        worksheet.freeze_panes(5, 0)
        worksheet.freeze_panes(6, 0)

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
        format9 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})
        merge_format_head = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 12, 'right': True, 'left': True,
            'bottom': True, 'top': True, 'bg_color': '#41689c'
        })
        merge_format_head_1 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 12, 'right': True, 'left': True,
            'bottom': True, 'top': True, 'bg_color': '#41689c'
        })

        binaryData = self.env.company.report_image1
        if binaryData:
            img_data = base64.b64decode(binaryData)
            im = BytesIO(img_data)
            worksheet.merge_range(0, 0, 0, 0, format2)
            worksheet.insert_image(0, 0, 'report_image1.png', {'image_data': im, 'x_offset': 0, 'y_offset': 0,
                                                               'x_scale': 0.65, 'y_scale': 0.5})

        # Insert Image [company logo]
        def get_partner_address(partner):
            address = "{name}\nP.O Box : {zip}, P.C. : 111, {country}\nTel. : {phone}, Email : {email}".format(
                name=partner.display_name,
                zip=partner.zip,
                phone=partner.phone,
                country=partner.country_id.name,
                email=partner.email
            )
            return address

        def format_date_header(from_date, to_date=False):
            if not from_date:
                return ''
            date = "{from_date}". \
                format(from_date=datetime.strptime(str(from_date), '%Y-%m-%d').strftime('%d-%m-%Y'))
            return date

        col_len = 6
        worksheet.merge_range(0, 1, 0, col_len, get_partner_address(company_id.partner_id), format2)
        worksheet.merge_range(2, 0, 2, col_len, 'Loan Outstanding Report', format1)
        worksheet.set_column(0, 0, 30)
        worksheet.set_column('A:A', 8)
        worksheet.set_column('B:B', 35)
        worksheet.set_column('C:C', 35)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 15)
        worksheet.set_column('G:G', 15)
        worksheet.set_column('H:H', 15)
        worksheet.set_column('I:I', 15)
        worksheet.set_column('J:J', 15)
        worksheet.set_row(0, 50)
        worksheet.set_row(2, 25)

        row = 3

        emp_list = []
        dept_list = []
        if datas['employee']:
            for rec in datas['employee']:
                emp = self.env['hr.employee'].search([('id', '=', rec)])
                loan = self.env['hr.loan'].search([('employee_id', '=', rec), ('state', '=', 'approved')])
                if loan:
                    emp_list.append(emp.name)
            employees = ','.join([str(elem) for elem in emp_list])
            worksheet.merge_range(row + 1, 0, row + 1, 100,
                                  "Employee  : " + employees, format4)
            row += 1

        if datas['department_id']:
            for rec in datas['department_id']:
                dept = self.env['hr.department'].search([('id', '=', rec)])
                loan = self.env['hr.loan'].search([('department', '=', rec), ('state', '=', 'approved')])
                if loan:
                    dept_list.append(dept.name)
            departments = ','.join([str(elem) for elem in dept_list])
            worksheet.merge_range(row + 1, 0, row + 1, 1,
                                  "Department  : " + departments, format4)
            row += 1

        row += 1
        col = 0
        worksheet.merge_range(row, col, row + 1, col, 'No.', merge_format_head)
        worksheet.merge_range(row, col + 1, row + 1, col + 1, 'Employee', merge_format_head)
        worksheet.merge_range(row, col + 2, row + 1, col + 2, 'Date', merge_format_head)
        worksheet.merge_range(row, col + 3, row + 1, col + 3, 'Amount', merge_format_head_1)
        worksheet.merge_range(row, col + 4, row, col + 6, 'Outstanding', merge_format_head)
        worksheet.write(row + 1, col + 4, 'Date Due', format5)
        worksheet.write(row + 1, col + 5, 'Amount', format5)
        worksheet.write(row + 1, col + 6, 'Notes', format5)
        worksheet.freeze_panes(row + 2, 0)
        row += 2
        domain = [('state', '=', 'approved')]
        if datas.get('employee_id', 0):
            domain.append(('employee_id', 'in', datas.get('employee_id', 0)))
        if datas.get('department_id', 0):
            domain.append(('department', 'in', datas.get('department_id')))

        loans = self.env['hr.loan'].search(domain, order='employee_id ASC')
        count = 1
        amt_total = 0
        installment_amt_total = 0
        for record in loans:
            worksheet.write(row, 0, count, format3)
            worksheet.write(row, 1, record.employee_id.name, format3)
            worksheet.write(row, 2, format_date_header(record.date_approved), format3)
            worksheet.write(row, 3, record.amount, format9)
            amt_total += record.amount
            for installment in record.installments.filtered(lambda rec: rec.paid is False):
                worksheet.write(row, 4, format_date_header(installment.date_pay), format9)
                worksheet.write(row, 5, installment.amount, format9)
                installment_amt_total += installment.amount
                worksheet.write(row, 6, '' if not installment.notes else installment.notes, format9)
                row += 1
            if not record.installments:
                row += 1
            count += 1
        worksheet.write(row + 5, 2, 'Total Amount', format5)
        worksheet.write(row + 5, 3, amt_total, format9)
        worksheet.write(row + 5, 4, 'Total Amount', format5)
        worksheet.write(row + 5, 5, installment_amt_total, format9)
