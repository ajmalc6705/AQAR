# -*- coding: utf-8 -*-
{
    'name': "Aqar Reports",
    'version': "16.0.1.0.3",
    'category': 'Reports',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to handle Reports.',
    'description': 'This module helps to handle Reports',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['contacts', 'base', 'purchase', 'purchase_requisition', 'project', 'aqar_project_assignment'],
    'data': [
        'security/ir.model.access.csv',
        # 'reports/purchase_report.xml',
        'reports/report_purchase_document_template.xml',
        'views/purchase_views.xml'

    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
