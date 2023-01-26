# -*- coding: utf-8 -*-
{
    'name': "Odoo REST API",

    'summary': """
        Odoo REST API""",

    'description': """
        Odoo REST API
    """,

    'author': "Yezileli Ilomo",
    'website': "http://www.singo.africa",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'developers',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','product','stock','purchase_stock','purchase'], # remove later sale

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/sol_ext.xml', # remove later
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    "application": True,
    "installable": True,
    "auto_install": False,

    'external_dependencies': {
        'python': ['pypeg2', 'requests']
    }
}