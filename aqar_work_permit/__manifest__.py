# -*- coding: utf-8 -*-
{
    'name': "Aqar Employee Work Permit",
    'version': "16.0.1.0.3",
    'category': 'Employee',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to handle work permit of an employee.',
    'description': 'This module helps to handle handle work permit of an employee',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['hr','base','hr_skills'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/work_permit_views.xml',
        'views/hr_employee_views.xml'

    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}