# -*- coding: utf-8 -*-

{
    'name': 'Atheer Multi-delivery',
    'category': 'stock',
    'summary': 'Module for handling multiple delivery against sales order line delivery dates',
    'version': '16.0.0.0',
    'author': 'Atheer',
    'company': 'Atheer',
    'maintainer': 'Atheer',
    'description': """Module for handling multiple delivery against sales order line delivery dates""",
    "license": "LGPL-3",
    "depends": ["sale_stock"],
    "data": [
        "views/sale_order_views.xml",
    ],
    'assets': {
    },
    "installable": True,
    "application": False,
    'images': ['static/description/banner.png'],
    'auto_install': False,
}
