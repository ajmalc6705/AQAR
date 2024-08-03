# -*- coding: utf-8 -*-
{
    'name': 'Cheque Printing Configurations',
    'version': '15.0.1.1.1',
    'sequence': 10,
    'author': 'Atheer Global Solutions',
    'website': "",
    'description': """Cheque Printing Configurations in Journal""",
    'license': 'LGPL-3',
    'depends': [
        'account', 'account_check_printing'
    ],
    'demo': [],
    'data': [
        # Security
        'security/account_security.xml',
        'security/ir.model.access.csv',
        # reports
        'report/cheque_print.xml',
        # Views
        'views/cancelled_cheque.xml',
        'views/journal_view.xml',
        'views/account_payment.xml',
    ],
    'auto_install': False,
    'installable': True,
}
