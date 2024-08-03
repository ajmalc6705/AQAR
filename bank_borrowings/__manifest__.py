# -*- coding: utf-8 -*-
{
    "name": "Bank Borrowings",
    "summary": """ Aqar accounting """,
    "category": "account",
    "version": "16.0.1.0.1",
    "author": "Atheer",
    "license": "LGPL-3",
    "website": "https://www.atheer.com",
    "description": """ Account """,
    "depends": ['base', 'account'],
    "data": [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/bank_borrowings.xml',
        'views/borrowing_type_views.xml'
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
