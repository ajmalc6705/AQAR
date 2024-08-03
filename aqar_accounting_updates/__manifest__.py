# -*- coding: utf-8 -*-
###################################################################################

# Author       :  Merlin Thomas

###################################################################################

{
    "name": "Aqar Account Updates",
    "summary": """ Aqar accounting """,
    "category": "account",
    "version": "16.0.1.0.8",
    "author": "Atheer",
    "license": "LGPL-3",
    "website": "https://www.atheer.com",
    "description": """ Account """,
    "depends": ['base','sale_management','account', 'account_accountant', 'account_asset'],
    "data": [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/account_account.xml',
        'views/account_move.xml',
        'views/account_payment.xml',
        'views/account_journal.xml',
        'views/res_company.xml',
        'views/account_asset_location.xml',
        'views/bank_guarantee_views.xml',
        'reports/bank_guarantee_report.xml',
        'reports/bank_guarantee_template.xml',
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
