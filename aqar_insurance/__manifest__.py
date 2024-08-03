# -*- coding: utf-8 -*-
{
    'name': "Aqar Insurance",
    'version': "16.0.1.0.4",
    'category': 'Employee',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to handle employee insurance.',
    'description': 'This module helps to handle employee insurance',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['contacts','base','hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/insurance_seq.xml',
        'views/aqar_insurance_views.xml',
        'views/insurance_type_views.xml'


    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
