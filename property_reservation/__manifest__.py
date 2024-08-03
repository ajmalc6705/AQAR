# -*- coding: utf-8 -*-
{
    'name': "Property Reservation ",
    'version': "16.0.1.0.9",
    'category': 'Industry',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to manage the reservation of property',
    'description': 'This module helps to manage the reservation of property',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['base', 'crm', 'parking_management', 'property_lease_management', 'atheer_documents','sale_crm','aqar_crm'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/reservation_seq.xml',
        'data/reservation_cron_jobs.xml',
        'wizard/cancel_reason_views.xml',
        'views/property_reservation_views.xml',
        'views/lead_views.xml',
        'views/payment_terms_views.xml',
        'reports/reservation_report_action.xml',

    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
