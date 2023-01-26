# -*- coding: utf-8 -*-
{
    'name': "Stock Move Back Date / Past Date",

    'summary': """
    change validation date with scheduled date for stock transfers / picking / receipt / delivery order.
        """,

    'description': """
The problem
===========
In Odoo, when you validate a stock transfer, Odoo applies the current time for the transfer date automatically 
which is sometimes not what you want. For example, you input data for the past.

The solution
============
This module change validation date with scheduled date for stock transfers.

The scheduled date you input here will also be used for accounting entry's date if the product is configured with automated stock valuation.


Editions Supported
==================
1. Community Edition
2. Enterprise Edition
    """,

    'author': 'Kinsoft Indonesia, Kikin Kusumah',
    'website': 'https://kinsoft.id',
    'support': 'kinsoft.indonesia@gmail.com',

    'category': 'Warehouse',
    'version': '1',

    'depends': ['stock_account'],

    'data': [
        # 'views/stock_picking_view.xml'
    ],
    'application': False,
    'installable': True,
    'images': ['static/description/main_screen.jpg'], 
    'price': 45,
    'currency': 'EUR',
    'license': 'OPL-1',
}
