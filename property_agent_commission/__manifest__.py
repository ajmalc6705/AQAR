# -*- coding: utf-8 -*-
{
    'name': "Property Agent Commission ",
    'version': "16.0.0.0.4",
    'category': 'Industry',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to manage the agent commission of property',
    'description': 'This module helps to manage the agent commission of property',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': [ 'contacts',"property_agent_payment"],
    'data': [

        'security/ir.model.access.csv',
        'data/agent_commission_seq.xml',

        'views/agent_commission_views.xml',

    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
