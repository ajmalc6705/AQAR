from odoo import api, fields, models, _
import base64
from io import BytesIO
import datetime as DT
from datetime import date
from odoo.exceptions import UserError, ValidationError


class VisaRenewalReportWizard(models.TransientModel):
    _name = "visa.renewal.report.wizard"
    _description = "visa renewal Report"

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    data = fields.Binary('File', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
    name = fields.Char('File Name', readonly=True)
    company_id = fields.Many2one('res.company', string='Currency', default=lambda self: self.env.company.id)

    def print_pdf_visa_renewal_report(self):
        # return True
        docids = self.env['visa.renewal.report.wizard'].search([]).ids

        renewal_ids = self._get_report_data()

        data = {
            'doc_ids': docids,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'ids': renewal_ids,
        }
        return self.env.ref('atheer_hr.visa_renewal_report').report_action(self, data)

    def xlsx_report(self):
        data = self._get_report_data()
        report = self.env['ir.actions.report']._get_report_from_name('atheer_hr.visa_renewal_report')
        report.report_file = 'Visa Renewal Report' + '-' + str(date.today())
        return self.env.ref('atheer_hr.visa_renewal_report_xlsx').report_action(
            None, data=data, config=False)

    def _get_report_data(self):
        if str(self.start_date) > str(self.end_date):
            raise ValidationError("End date must be greater than start date")
        start_date = self.start_date
        end_date = self.end_date

        where_qry = "he.visa_expire between'" + str(start_date) + "'and'" + str(end_date) + "'"

        data_qry = (''' select he.emp_id as emp_id,he.name as emp_name,hd.name as department,hj.name as designation ,
                    he.visa_no as visa_no,to_char(he.visa_start_date, 'MM-DD-YYYY') as visa_start_date,to_char(he.visa_expire, 'MM-DD-YYYY') as visa_expire
                    from hr_employee he
                    LEFT JOIN hr_department hd on he.department_id = hd.id
                    LEFT JOIN hr_job hj on he.job_id = hj.id where %s
                    ''') % (where_qry)
        self.env.cr.execute(data_qry)
        data = self.env.cr.dictfetchall()
        if not data:
            raise UserError("No data found!")
        model = self.env.context.get('active_model')

        data = {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'today': fields.Date.today(),
            'company': self.env.company,

        }
        return data


class VisaRenewalReportExcel(models.AbstractModel):
    _name = 'report.atheer_hr.visa_renewal_report'
    _description = "Visa Renewal Report"
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, datas, projects):

        company_id = self.env.user.company_id
        sheet = workbook.add_worksheet('VISA RENEWAL REPORT')
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
        format4 = workbook.add_format({'font_size': 11, 'align': 'left', 'bold': False, 'right': False, 'left': False,
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

        col_len = 6
        sheet.merge_range(0, 1, 0, col_len, get_partner_address(company_id.partner_id), format2)
        sheet.merge_range(2, 0, 2, col_len, 'VISA RENEWAL REPORT', format1)
        sheet.set_column(0, 0, 30)
        sheet.set_column(0, 0, 30)
        sheet.set_column('A:A', 14)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 10)
        sheet.set_column('F:F', 18)
        sheet.set_column('G:G', 18)
        sheet.set_row(0, 50)
        sheet.set_row(2, 25)

        row = 3
        sheet.merge_range(row, 0, row, 1,
                          "Start Date  : " + DT.datetime.strptime(datas['start_date'], '%Y-%m-%d').strftime('%d-%m-%Y'),
                          format4)
        sheet.merge_range(row, 3, row, 4,
                          "End Date: " + DT.datetime.strptime(datas['end_date'], '%Y-%m-%d').strftime('%d-%m-%Y'),
                          format4)

        row += 2
        col = 0
        sheet.write(row, col, 'Emp ID', format5)
        sheet.write(row, col + 1, 'Employee', format5)
        sheet.write(row, col + 3, 'Designation', format5)
        sheet.write(row, col + 2, 'Department', format5)
        sheet.write(row, col + 4, 'Visa No', format5)
        sheet.write(row, col + 5, 'Visa Start Date', format5)
        sheet.write(row, col + 6, 'Visa Expiry Date', format5)

        row += 1
        for line in datas['data']:
            if line['visa_start_date']:
                 visa_start_date = DT.datetime.strptime(str(line['visa_start_date']), '%m-%d-%Y').strftime('%d-%m-%Y')
            else:
                visa_start_date = line['visa_start_date']
            if line['visa_expire']:
               visa_expire = DT.datetime.strptime(str(line['visa_expire']), '%m-%d-%Y').strftime('%d-%m-%Y')
            else:
                visa_expire = line['visa_expire']
            sheet.write(row, 0, line['emp_id'], format3)
            sheet.write(row, 1, line['emp_name'], format3)
            sheet.write(row, 3, line['designation'], format3)
            sheet.write(row, 2, line['department'], format3)
            sheet.write(row, 4, line['visa_no'], format9)
            sheet.write(row, 5, visa_start_date, format9)
            sheet.write(row, 6, visa_expire, format9)

            row += 1
