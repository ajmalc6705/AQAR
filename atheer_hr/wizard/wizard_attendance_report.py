# -*- coding: utf-8 -*-
from datetime import date
import datetime as DT
import base64
from io import BytesIO
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class AttendanceReport(models.TransientModel):
    _name = "wizard.attendance.history"
    _description = 'Attendance Report"'

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    employee = fields.Many2one('hr.employee', string="Employee")
    print_date = fields.Date(default=fields.Date.context_today)

    def _get_attendance_pdf_filename_with_date(self):
        today_date = date.today()
        name = "ATTENDANCE PDF REPORT" + str(today_date)
        return name

    def pdf_report(self):
        if str(self.start_date) > str(self.end_date):
            raise ValidationError("End date must be greater than start date")
        docids = self.env['wizard.attendance.history'].search([]).ids
        attendance = self.generate_data()
        data = {
            'doc_ids': docids,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'employee': self.employee.name,
            'ids': attendance,
        }
        return self.env.ref('atheer_hr.report_attendance_details').report_action(self, data=data)

    def xlsx_report(self):
        data = self.generate_data()
        report = self.env['ir.actions.report']._get_report_from_name(
            'atheer_hr.attendance_management_report')
        report.report_file = 'Attendance Report' + '-' + str(date.today())
        return self.env.ref('atheer_hr.attendance_management_report_xlsx').report_action(
            None, data=data, config=False)

    def generate_data(self):
        start_date = self.start_date
        end_date = self.end_date
        employee = self.employee

        st_date = self.start_date
        en_date = self.end_date + relativedelta(days=1)

        where_qry = "ha.date between'" + str(start_date) + "'and'" + str(end_date) + "'"
        if self.employee:
            where_qry += " and ha.employee_id = '" + str(employee.id) + "'"

        data_qry = (''' select he.emp_id as employee_id,he.name as emp_name,hj.name as designation,
                        ('%s'::date - '%s'::date) as total_days,
  						((count(ha.attendance_type='partial_day'or NULL)*0.5) + count(ha.attendance_type='pr_present' or NULL)) as pr_days, 
                        count(ha.attendance_type='absent'  OR NULL) as absent,
                        count(ha.attendance_type='sick_leave'  OR NULL) as sick_leave,
                        count(ha.attendance_type='annual_leave' OR NULL) as annual_leave,
                        (count(ha.attendance_type='pr_present' OR NULL)  + (count(ha.attendance_type='partial_day'or NULL)*0.5)+  count(ha.attendance_type='sick_leave' OR NULL)  + count(ha.attendance_type='annual_leave' OR NULL)) as total_pay_days
                        from hr_attendance ha
                        LEFT JOIN hr_employee he ON ha.employee_id = he.id
                        LEFT JOIN hr_job hj ON he.job_id = hj.id where %s
                        group by he.employee_id,he.name,hj.name,%s,%s''') % (
            en_date, st_date, where_qry, self.start_date, self.end_date)

        self.env.cr.execute(data_qry)
        x = self.end_date - self.start_date
        data = self.env.cr.dictfetchall()
        if not data:
            raise UserError("No data found!")
        model = self.env.context.get('active_model')
        if self.employee:
            employee = self.employee.name
        else:
            employee = False

        data = {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'employee': employee,
            'today': fields.Date.today(),
            'company': self.env.company,

        }
        return data


class AttendanceReportExcel(models.AbstractModel):
    _name = 'report.atheer_hr.attendance_management_report'
    _description = "Attendance Report"
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, datas, projects):
        company_id = self.env.user.company_id
        sheet = workbook.add_worksheet('ATTENDANCE REPORT')
        sheet.freeze_panes(1, 0)
        sheet.freeze_panes(2, 0)
        sheet.freeze_panes(3, 0)
        sheet.freeze_panes(4, 0)
        sheet.freeze_panes(5, 0)
        sheet.freeze_panes(6, 0)
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

        binaryData = self.env.company.report_image1
        if binaryData:
            img_data = base64.b64decode(binaryData)
            im = BytesIO(img_data)
            sheet.merge_range(0, 0, 0, 0, format2)
            sheet.insert_image(0, 0, 'report_image1.png', {'image_data': im, 'x_offset': 0, 'y_offset': 0,
                                                           'x_scale': 0.65, 'y_scale': 0.5})

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

        col_len = 8
        sheet.merge_range(0, 1, 0, col_len, get_partner_address(company_id.partner_id), format2)
        sheet.merge_range(2, 0, 2, col_len, 'ATTENDANCE REPORT', format1)
        sheet.set_column(0, 0, 30)
        sheet.set_column('A:A', 14)
        sheet.set_column('B:B', 35)
        sheet.set_column('C:C', 35)
        sheet.set_column('D:D', 5)
        sheet.set_column('E:E', 4)
        sheet.set_column('F:F', 8)
        sheet.set_column('G:G', 4)
        sheet.set_column('H:H', 4)
        sheet.set_column('I:I', 20)
        sheet.set_row(0, 50)
        sheet.set_row(2, 25)

        row = 3
        sheet.merge_range(row, 0, row, 1,
                          "Start Date  : " + DT.datetime.strptime(datas['start_date'], '%Y-%m-%d').strftime('%d-%m-%Y'),
                          format4)
        sheet.merge_range(row, 3, row, 6,
                          "End Date: " + DT.datetime.strptime(datas['end_date'], '%Y-%m-%d').strftime('%d-%m-%Y'),
                          format4)
        if datas['employee']:
            sheet.merge_range(row + 1, 0, row + 1, 1,
                              "Employee  : " + datas['employee'], format4)
            row += 1

        row += 2
        col = 0
        sheet.write(row, col, 'Emp ID', format5)
        sheet.write(row, col + 1, 'Employee', format5)
        sheet.write(row, col + 2, 'Designation', format5)
        sheet.write(row, col + 3, 'Total', format5)
        sheet.write(row, col + 4, 'PR', format5)
        sheet.write(row, col + 5, 'Absent', format5)
        sheet.write(row, col + 6, 'SL', format5)
        sheet.write(row, col + 7, 'AL', format5)
        sheet.write(row, col + 8, 'Total payable days', format5)

        row += 1
        for line in datas['data']:
            sheet.write(row, 0, line['employee_id'], format3)
            sheet.write(row, 1, line['emp_name'], format3)
            sheet.write(row, 2, line['designation'], format3)
            sheet.write(row, 3, line['total_days'], format9)
            sheet.write(row, 4, line['pr_days'], format9)
            sheet.write(row, 5, line['absent'], format9)
            sheet.write(row, 6, round(line['sick_leave'], 1), format9)
            sheet.write(row, 7, round(line['annual_leave'], 1), format9)
            sheet.write(row, 8, line['total_pay_days'], format9)
            row += 1
