# -*- encoding: UTF-8 -*-

{
    'name': "Purchase Order Type",
    "version": "16.0.1.7.5",
    'summary': """Purchase Order Type""",
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global IT Solutions',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    "license": "LGPL-3",
    'category': 'purchase',
    'description': """This module adds purchase type in purchase.
    """,
    'depends': ['purchase', 'purchase_requisition', 'project', 'aqar_project_assignment', 'fleet', 'sign'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/po_signature_password_check_wizard_ciews.xml',
        'views/ir_res_config_settings_views.xml',
        'views/purchase_order.xml',
        'views/purchase_requisition.xml',
        'views/res_users_signature_views.xml',
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
}
