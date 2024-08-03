# -*- coding: utf-8 -*-
{
    'name': 'Aqar LC Letter',
    'version': '16.0.0.1',
    'license': 'LGPL-3',
    'category': 'Account',
    "sequence": 1,
    "author": "Atheer Global Solutions LLC, ",
    'website': 'http://www.atheerit.com',
    'summary': '',
    'depends': ['purchase', 'account','base','account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',

        'views/cancel_reason.xml',
        'views/account_payment.xml',
        'views/purchase.xml',
        'views/lc_letter.xml',
        # 'views/internship_enquiry_view.xml',

        'menus/menus.xml',
   ],


    'installable': True,
    'auto_install': False,
    'application': True,

}
