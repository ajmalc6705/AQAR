# -*- coding: utf-8 -*-
{
    'name': "Appointment Extension",
    'version': "16.0.1.0.2",
    'category': 'Marketing/Online Appointment',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to handle Appointments.',
    'description': 'This module helps to handle Appointments',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['appointment'],
    'data': [
        'security/appointment_groups.xml',
        'data/appointment_sequence.xml',
        'views/appointment_views.xml',
        'views/appointment_form_views.xml',
        'views/appointment_templates.xml',

    ],
    # 'assets': {
    #     'web.assets_frontend': [
    #         'appointment_extension/static/src/js/appointment_form.js'
    #     ],
    # },
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
