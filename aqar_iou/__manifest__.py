# -*- coding: utf-8 -*-
{
    'name': "Aqar IOU",
    'version': "16.0.1.0.4",
    'category': 'Employee',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to handle IoU in employees.',
    'description': 'This module helps to handle sdocument',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['hr','base'],
    'data': [
        'security/ir.model.access.csv',
        'data/iou_sequence.xml',
        'views/aqar_iou_views.xml'

    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
