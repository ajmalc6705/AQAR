# -*- coding: utf-8 -*-
{
    'name': "Aqar Contract",
    'version': "16.0.1.0.9",
    'category': 'Industry',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to manage the Contract',
    'description': 'This module helps to manage the contract',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['base', 'crm', 'atheer_documents', 'property_lease_management',
                ],
    'data': [
        'security/security_groups.xml',
        'security/record_rule.xml',
        'security/ir.model.access.csv',
        'data/contracts_seq.xml',
        'data/contract_mail_template.xml',
        'data/expiry_notification_cron_job.xml',
        'views/aqar_contract_views.xml',
        'views/aqar_contract_categ_views.xml',

    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
