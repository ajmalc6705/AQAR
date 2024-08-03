# -*- coding: utf-8 -*-
{
    'name': "Aqar Salary Assignment",
    'version': "16.0.1.0.3",
    'category': 'Employee',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to handle salary assignment of an employee.',
    'description': 'This module helps to handle handle salary assignment of an employee',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['hr','base'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/salary_assignment_views.xml',
        'views/hr_employee_views.xml'

    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}