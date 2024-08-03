# -*- encoding: UTF-8 -*-

{
    'name': "Purchase Order Line",
    'version': '17.1.2.7',
    'summary': """Purchase View""",
    'author': 'Atheer Global Solutions',
    'company': 'Atheer Global Solutions',
    'maintainer': 'Global Solutions',
    'website': 'https://www.atheerit.com',
    "license":  "LGPL-3",
    'category': 'purchase',
    'description': """This modual help you to explore Purchase Order Line with tree, kanban, paovet, graph, calendar View.
    """,
    'depends': ['purchase', 'aqar_reports'],
    'data': [
        'views/purchase_view.xml',
        'report/purchase_report_inherit.xml',
    ],
    "application":  False,
    "installable":  True,
    "auto_install":  False,
    "pre_init_hook":  "pre_init_check",
}
