{
    'name': "Aqar Sale",
    'version': '1.0.0,4',
    'license': 'LGPL-3',
    'author': "Atheer IT",
    'category': 'Category',
    'depends': ['base', 'contacts', 'sale'],
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        # 'security/ir.model.access.csv',
        'security/sale_order_security.xml',
        # 'views/sale_cancel_reason.xml',
        'views/res_config_view.xml',
        'views/sale_order.xml',

    ],
}
