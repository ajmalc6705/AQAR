{
    'name': "Petty Cash Management UAE",
    'version': '16.0.1.7.1',
    'license': 'LGPL-3',
    'author': "Atheer IT",
    'category': 'Category',
    'description': """
    Petty Cash Management for Labelle UAE
    """,
    'depends': ['base','account', 'account_accountant', 'hr'],
    # data files always loaded at installation
    'data': [
        'security/petty_cash_security.xml',
        'security/ir.model.access.csv',

        'security/ir_rules.xml',

        'data/petty_cash_data.xml',
        'views/hr_employee_view_inherited.xml',
        'views/add_petty_cash_view.xml',
        'views/petty_cash_expense_view.xml',
        'views/account_journal_view.xml',
        'views/petty_cash_expense_type_view.xml',
        'views/reject_reason.xml',
        'report/petty_cash_receipt.xml',
        'report/petty_expense_receipt.xml'
    ],
    # data files containing optionally loaded demonstration data
    # 'demo': [
    #   'demo/demo_data.xml',
    # ],
}
