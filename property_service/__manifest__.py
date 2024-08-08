# -*- coding: utf-8 -*-
{
    'name': "Property Service ",
    'version': "16.0.1.2.2",
    'category': 'Industry',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to manage the service of property',
    'description': 'This module helps to manage the service of property',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['property_lease_management','sales_team', 'purchase',
                'property_reservation'],
    'data': [
        'security/ir_rules.xml',
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/service_sequence.xml',
        # 'data/stages.xml',
        'views/property_service_views.xml',
        'views/service_sale_order_views.xml',
        'views/service_stage_views.xml',

    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

