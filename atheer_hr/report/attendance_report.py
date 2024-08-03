# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AttendanceReportPdf(models.AbstractModel):
    _name = 'report.atheer_hr.action_attendance_report_pdf'
    _description = "Attendance Pdf"

    @api.model
    def _get_report_values(self, docids, data):
        company_id = self.env.company
        docs = self.env['wizard.attendance.history'].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': 'wizard.attendance.history',
            'docs': docs,
            'data': data,
            'company': company_id,
        }
