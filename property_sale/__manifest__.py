# -*- coding: utf-8 -*-
{
    'name': "Property Sale ",
    'version': "16.0.1.0.4",
    'category': 'Industry',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to manage the sale of property',
    'description': 'This module helps to manage the sale of property',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['base', 'crm', 'parking_management', 'property_lease_management', 'atheer_documents',
                'property_reservation', ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/sale_seq.xml',
        'data/doc_type.xml',
        'wizard/cancel_reason_views.xml',
        'wizard/cancel_mulkiya_views.xml',
        'wizard/resale_wizard_views.xml',
        'views/property_sale_views.xml',
        'views/property_reservation_views.xml',
        'views/property_mulkiya_transfer_views.xml',
        'views/mulkiya_stages_views.xml',
        'views/property_resale_views.xml',
        'views/account_move_property_sale_views.xml'

    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
