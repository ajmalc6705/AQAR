# -*- coding: utf-8 -*-
{
    'name': "Property Community",
    'version': "16.0.1.2.0",
    'category': 'Helpdesk',
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'summary': 'This module helps to handle Community Property.',
    'description': 'This module helps to handle Community Property',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    'depends': ['base','property_lease_management', 'crm','account'],
    'data': [
        'security/security_groups.xml',
        'security/ir_rules.xml',
        'security/ir.model.access.csv',

        'data/stages_data.xml',

        'wizard/community_invoice_views.xml',
        'wizard/levy_summary_report.xml',

        'views/levy_master_views.xml',
        'views/property_management_views.xml',
        'views/community_tenant_request_views.xml',
        'views/res_config_settings_views.xml',
        'views/community_views.xml',
        'views/community_budget_views.xml',
        'views/ownership_change_view.xml',
        'views/account_account_inherit_views.xml',

        'reports/report_sublevy_budget.xml',
        'reports/report_community_invoice.xml',

        'wizard/report_sublevy_budget_views.xml'

    ],
    'assets': {
        'web.assets_backend': [
            'property_community/static/src/js/action_manager.js',
        ],
    },
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
