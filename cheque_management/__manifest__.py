{
    'name': "Cheque Management",
    'version': '16.0.1.1.7',
    'license': 'LGPL-3',
    'author': "Atheer IT",
    'category': 'Category',
    'depends': ['base', 'account', "cheque_print_config", "petty_cash_management", 'contacts'],
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        'data/mail_activity.xml',
        'security/cheque_security.xml',
        'security/ir_rules.xml',
        'security/ir.model.access.csv',
        'data/cheque_management_data.xml',
        'views/payment_receipt_report_inherited.xml',
        'views/res_partner.xml',
        'views/cheque_management_view.xml',
        'views/payment_signature.xml',
        'report/cheque_receipt.xml'


    ],
    # data files containing optionally loaded demonstration data
    #'demo': [
     #   'demo/demo_data.xml',
    #],
}
