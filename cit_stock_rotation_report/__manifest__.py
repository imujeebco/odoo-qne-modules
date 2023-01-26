# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

{
    'name': 'Stock Rotation/Products Movements Report',
    'version': '14.0.1.0',
    'summary': 'Products Movement',
    'category': 'Stock',
    'description': """
        This module allows you to print a stock rotation report in pdf or excel.
        It will give you the all movement of products between given period.
    """,
    'author': 'Caret IT Solutions Pvt. Ltd.',
    'website': 'https://www.caretit.com',
    'depends': ['stock', 'sale_management', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/stock_rotation_report_view.xml',
        'report/report_stock_rotation.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'price': 25.00,
    'currency': 'USD',
}
