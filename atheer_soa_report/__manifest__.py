# -*- coding: utf-8 -*-
{
    'name': "Atheer Customer SOA",
    'version': '15.0.0.1.5',
    'summary': """Customer Statement of Account""",
    'description': """Partner Outstanging Statement with the details of the
                            transactions reference, currency, balance amount and age""",
    'author': "Atheer Global Solutions",
    'website': "https://atheerit.com",
    'category': 'Atheer',
    'license': 'LGPL-3',
    # any module necessary for this one to work correctly
    'depends': ['account', 'account_accountant'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_view.xml',
        'wizard/soa_report_wizard.xml',
        'wizard/soa_confirmation_report_wizard.xml',
        'reports/customer_soa_report.xml',
        'reports/customer_balance_confirmation_report.xml',
    ],
}
