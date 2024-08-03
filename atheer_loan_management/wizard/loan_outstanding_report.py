# -*- coding: utf-8 -*-

from datetime import datetime, date
from odoo import models, api, fields, _
from odoo.exceptions import UserError


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
        if datas.get('bu_cc', 0):
            domain.append(('account_analytic_id', 'in', datas.get('bu_cc')))
        loans = self.env['hr.loan'].search(domain, order='employee_id ASC')
        if not loans:
            raise UserError("No data found!")
        datas = {'loan': loans.ids}
        return self.env.ref('atheer_loan_management.loan_outstanding_report_xls').report_action(None, data=datas, config=False)


class LoanOutstandingReport(models.AbstractModel):
    _name = "report.atheer_loan_management.loan_outstanding_report.xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Loan Outstanding Report"

    def generate_xlsx_report(self, workbook, datas, sheets):
        company_id = self.env.user.company_id
        worksheet = workbook.add_worksheet('Loan Outstanding Report')

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
        cell__data_format = workbook.add_format({
            'bold': 0,
            'border': 1,
            'align': 'left',
            'valign': 'bottom',
            'font_size': 10,
        })
        cell__data_format_footer = workbook.add_format({
            'bold': 0,
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 10,
        })
        cell__data_format_footer_bold = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'right',
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

        def get_period_ids(rent, name):
            periods = self.env['rent.period.lines'].search([('rent_ids', 'in', [rent]), ('name', '=', name.name)],
                                                           limit=1)
            if periods:
                date = "{from_date} - {to_date}". \
                    format(from_date=datetime.strptime(str(periods.from_date), '%Y-%m-%d').strftime('%d-%m-%Y'),
                           to_date=datetime.strptime(str(periods.to_date), '%Y-%m-%d').strftime('%d-%m-%Y'))
                return date
            else:
                return ''

        def format_date_header(from_date, to_date=False):
            if not from_date:
                return ''
            date = "{from_date}". \
                format(from_date=datetime.strptime(str(from_date), '%Y-%m-%d').strftime('%d-%m-%Y'))
            return date

        # Datas
        row = 1
        col = 0

        worksheet.merge_range(row, col, row + 1, col, 'No.', merge_format_head)
        worksheet.merge_range(row, col + 1, row + 1, col + 1, 'Employee', merge_format_head)
        worksheet.merge_range(row, col + 2, row + 1, col + 2, 'Date', merge_format_head)
        worksheet.merge_range(row, col + 3, row + 1, col + 3, 'Amount', merge_format_head)
        worksheet.merge_range(row, col + 4, row, col + 6, 'Outstanding', merge_format_head)
        worksheet.write(row + 1, col + 4, 'Date Due', cell_format)
        worksheet.write(row + 1, col + 5, 'Amount', cell_format)
        worksheet.write(row + 1, col + 6, 'Notes', cell_format)

        col = 4
        # col width
        worksheet.set_column(0, 0, 4)
        worksheet.set_column(1, 6, 25)

        #  1,2 th row height
        worksheet.set_row(0, 17)
        worksheet.set_row(1, 17)
        worksheet.set_row(2, 17)
        row = 3
        col = 0
        # data
        domain = [('state', '=', 'approved')]
        if datas.get('employee_id', 0):
            domain.append(('employee_id', 'in', datas.get('employee_id', 0)))
        if datas.get('department_id', 0):
            domain.append(('department', 'in', datas.get('department_id')))
        if datas.get('bu_cc', 0):
            domain.append(('account_analytic_id', 'in', datas.get('bu_cc')))
        loans = self.env['hr.loan'].search(domain, order='employee_id ASC')
        count = 1
        for record in loans:
            worksheet.write(row, col, count, cell__data_format)
            worksheet.write(row, col + 1, record.employee_id.name, cell__data_format)
            worksheet.write(row, col + 2, format_date_header(record.date_approved), cell__data_format)
            worksheet.write(row, col + 3, record.amount, cell__data_format)
            for installment in record.installments.filtered(lambda rec: rec.paid is False):
                worksheet.write(row, col + 4, format_date_header(installment.date_pay), cell__data_format)
                worksheet.write(row, col + 5, installment.amount, cell__data_format)
                worksheet.write(row, col + 6, '' if not installment.notes else installment.notes, cell__data_format)
                row += 1
            if not record.installments:
                row += 1
            count += 1

        col = 6
        # Merge Header
        formatted_date = format_date_header(str(date.today()))
        worksheet.merge_range(0, 0, 0, col, 'Loan Outstanding Report  %s' % formatted_date, merge_format_head)
