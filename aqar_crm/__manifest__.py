# -*- coding: utf-8 -*-
{
    'name': "Atheer CRM ",
    'version': "16.0.1.0.4",
    'category': 'CRM',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to handle CRM for Property',
    'description': 'This module helps to handle CRM for Property',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['crm','base', 'account', 'property_lease_management'],
    'data': [
        'security/ir.model.access.csv',
        'reports/sale_offer_reports.xml',
        'reports/rent_offer_reports.xml',
        'data/crm_mail_template.xml',
        'data/crm_sale_offer_template.xml',
        'data/crm_sequence.xml',
        'views/crm_lead_views.xml',
        'views/terms_conditions_views.xml',
        'views/units_views.xml',

    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
