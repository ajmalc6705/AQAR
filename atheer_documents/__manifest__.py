# -*- coding: utf-8 -*-
{
    'name': "Atheer Documents",
    'version': "16.0.2.1.5",
    'category': 'Documents',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to handle document management.',
    'description': 'This module helps to handle document',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['contacts', 'base'],
    'data': [
        'security/security_groups.xml',
        'security/ir_rules.xml',
        'security/ir.model.access.csv',
        'data/doc_seq.xml',
        'data/document_notification_cron_job.xml',
        'data/document_mail_template.xml',
        'views/document_views.xml',
        'views/document_type_views.xml',
        'views/expiry_duration.xml',

    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
