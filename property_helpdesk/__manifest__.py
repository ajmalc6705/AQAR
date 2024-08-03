# -*- coding: utf-8 -*-
{
    'name': "Property Helpdesk",
    'version': "16.0.1.0.1",
    'category': 'Helpdesk',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to handle complaint.',
    'description': 'This module helps to handle complaint',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['web', 'helpdesk', 'property_lease_management'],
    'data': [
        'views/helpdesk_ticket_views.xml',
        'views/customer_complaints_views.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
