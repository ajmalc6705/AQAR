# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Request For Quotation-Portal",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "purchases",
    "license": "OPL-1",
    "summary": " Manage Multiple RFQs Module, Vendor Change RFQ Price App, Manage Request For Quotation Price, Request For Quote Update Price, Automatic Backend Price Change Odoo, Client Change RFQ Price ,Supplier Change Quotation Price Odoo request for quotation portal RFQ portal",
    "description": """
    Nowadays in a competitive market, several vendors sell the same products and everyone has their own price so it will difficult to manage multiple RFQ's at a time even in odoo there is no kind of feature where you can manage multiple requests for quotations in a single list. Currently in odoo vendor can see a purchase order, the vendor can't able to see RFQ this module provides vendor to see RFQ, where the vendor can change the price from portal or website for RFQ's. Changed price automatically updates in odoo backend.""",
    "version": "16.0.2",
    "depends": ["purchase","sh_backend_base"],
    "application": True,
    "data": [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_order_templates.xml',
    ],
    'assets': {
    'web.assets_frontend': [
        'sh_rfq_portal/static/src/js/portal.js',
    ],
    },
    "images": ["static/description/background.png", ],
    "live_test_url": "https://youtu.be/fC170lmqIqU",
    "auto_install": False,
    "installable": True,
    "price": 35,
    "currency": "EUR"
}
