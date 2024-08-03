# -*- coding: utf-8 -*-
{
    'name': "Atheer HR",
    'version': '16.0.7.9.7',
    'author': "Atheer IT Solution",
    'website': "https://atheerit.com",
    'category': 'Atheer',
    'license': "OPL-1",
    'summary': """
        HR Customization Module""",

    'description': """
        HR Customization Module
    """,

    # any module necessary for this one to work correctly
    'depends': ['hr', 'hr_contract', 'hr_attendance', 'report_xlsx', 'contacts', 'hr_timesheet',
                'hr_payroll_holidays', 'hr_payroll_account', 'atheer_loan_management', 'hr_employee_relative','aqar_salary_assignment_request'],

    # always loaded
    'data': [
        # security
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        # data
        'data/data.xml',
        'data/sequence.xml',
        'data/loan_reason_demo_data.xml',
        'data/salary_package_type.xml',
        'data/salary_rule.xml',
        # views
        'views/company.xml',
        'views/employee.xml',
        'views/hr_emp_blood_groups.xml',
        # 'views/evaluation_recommendation.xml',
        'views/hr_bank.xml',
        'views/hr_job.xml',
        'views/hr_contract.xml',
        'views/doc_master.xml',
        'views/performance_evaluation.xml',
        'views/evaluation_type_master.xml',
        'views/hr_leave.xml',
        'views/notification_duration.xml',
        'views/hr_payslip_view.xml',
        # 'views/hr_payslip_template.xml',
        'views/hr_calendar.xml',
        'views/hr_attendance.xml',
        'views/hr_attendance_amendment.xml',
        'views/hr_leave_types.xml',
        'views/hr_leave_return.xml',
        'views/hr_leave_salary_balance.xml',
        'views/increment_and_promotion.xml',
        'views/annual_bonus.xml',
        # 'views/hr_loan.xml',
        # 'views/hr_loan_adjustments.xml',
        'views/loan_addition_deduction.xml',
        'views/hr_payroll_hold.xml',
        'views/hr_payroll_release.xml',
        'views/gratuity.xml',
        'views/hr_resignation.xml',
        'views/final_settlement.xml',
        'views/airticket.xml',
        'views/utility.xml',
        'views/public_holidays.xml',
        'views/hr_config.xml',
        'views/employee_training_view.xml',
        'views/hr_import_timesheet_view.xml',
        'views/hr_main_timesheet_view.xml',
        'views/hr_clearance_visa.xml',
        'views/hr_leave_encashment.xml',
        # wizard
        'wizard/attendance_wizard.xml',
        'wizard/loan_split_wizard.xml',
        # 'wizard/loan_outstanding_report.xml',
        'wizard/message_wizard.xml',
        # report
        'report/report_layout.xml',
        'report/employe_joining_report.xml',
        'report/employe_visa_renewal_report.xml',
        'report/performance_evaluation_report.xml',
        # 'report/visa_renewal/wizard_visa_renewal_report_view.xml',
        # 'report/visa_renewal/visa_renewal_pdf_report.xml',
        # 'report/visa_renewal/visa_renewal_xlsx_report.xml',
        # 'report/visa_renewal/visa_renewal_undertaking_letter.xml',
        'report/employee_training/emp_training_report.xml',
        'report/attendance_report_pdf.xml',
        'report/attendance_management_report_xlsx.xml',
        'report/hr_payslip_pdf_report.xml',
        'report/hr_payslip_batch_report.xml',
        'report/report_increment_and_promotion.xml',
        'report/report_final_settlement.xml',
        'report/experience_certificate.xml',
        'report/report_resignation.xml',
        'report/loan_report.xml',
        'report/report_utility_approval.xml',
        'report/leave_request_report.xml',
        'report/wps_xlxs.xml',

        'report/report.xml',
    ],
    'application': True,
    'demo': [
        'data/loan_reason_demo_data.xml'],
    'assets': {
        'web.assets_backend': [
            'atheer_hr/static/src/js/settings_icon.js',
        ],
        'web.report_assets_common': [
            'atheer_hr/static/src/css/*',
        ],
    },

}
