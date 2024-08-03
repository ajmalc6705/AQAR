# -*- coding: utf-8 -*-
{
    'name': "Dynamic Approval All in One",

    'summary': """
        The most configurable dynamic approval app in Odoo, can be used for all default modules and third party modules""",

    'description': """
        Configurable dynamic approval process all in one for selected model or form in all odoo modules including
        custom module / third party modules.
    """,

    'author': "Adi Nurcahyo",
    'website': "https://www.linkedin.com/in/adinc13",
    'support': "https://www.linkedin.com/in/adinc13",
    'category': 'Tools',
    'version': '16.0.1.2.2',
    'sequence': 0,
    "auto_install": False,
    "installable": True,
    "application": True,
    "license": "OPL-1",
    "images": [
        'static/description/banner.gif'
    ],
    # "price": 114.29,
    # discount price for first release
    "price": 57.31,
    "currency": "EUR",
    "live_test_url": "https://apps.adinc.my.id/login_employee?login=demo&password=demo&action=dynamic_approval.action_window_dynamic_approval",
    # "live_test_url": "https://youtu.be/Mzu872MW6eE",

    # any module necessary for this one to work correctly
    'depends': [
        'base','mail'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/menu.xml',
        'views/dynamic_approval.xml',
        'views/dynamic_approval_wizard.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
