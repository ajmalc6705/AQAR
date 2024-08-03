# -*- coding: utf-8 -*-
{
    'name': "Atheer Loan Management",
    'version': '16.0.1.2.1',
    'summary': """Loan details""",
    'description': """Loan Details""",
    'author': "Atheer Global Solutions",
    'website': "https://atheerit.com",
    'category': 'Atheer',
    'license': 'LGPL-3',
    # any module necessary for this one to work correctly
    'depends': ['account_accountant', 'hr_payroll', 'report_xlsx'],

    # always loaded
    'data': [
        'security/loan/ir.model.access.csv',
        'data/data.xml',
        'data/demo_data.xml',
        'views/hr_loan.xml',
        'wizard/loan_split_wizard.xml',
        'wizard/loan_payment_wizard_views.xml'
    ],
}
