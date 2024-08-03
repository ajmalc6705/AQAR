# -*- coding: utf-8 -*-
{
    'name': "Aqar Hr Vacancy Request",
    'version': "16.0.1.0.2",
    'category': 'Employee',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to handle Manpower request in Hr.',
    'description': 'This module helps to handle Manpower request in Hr',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['hr','base','hr_skills'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/hr_vacancy_request_views.xml'

    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
