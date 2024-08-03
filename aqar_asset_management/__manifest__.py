# -*- coding: utf-8 -*-
{
    'name': 'Aqar Asset Management',
    'version': '16.0.1.0.1',
    'author': "Atheer Global Solutions",
    'website': "https://atheerit.com",
    'category': 'Labelle',
    'license': 'LGPL-3',
    'description': """Accounting Modules Extended""",
    'depends': ['account_asset', 'account'],
    'demo': [],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/account_asset_view.xml',
    ],
    'auto_install': False,
    'installable': True,
}
