# -*- coding: utf-8 -*-
{
    'name': "Aqar Documents",
    'version': "16.0.1.2.0",
    'category': 'Documents',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to handle document management.',
    'description': 'This module helps to handle sdocument',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['contacts','base','atheer_documents','hr'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/document_renewal_seq.xml',
        'data/mass_confirm_actions.xml',
        'views/document_renewal_views.xml',
        'views/document_submission_views.xml',
        'reports/report_actions.xml',
        'reports/report_document_receiving.xml',
        'reports/report_document_return.xml',
        'views/document_views.xml'


    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
