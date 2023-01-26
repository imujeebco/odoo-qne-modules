# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

import xlwt
from io import BytesIO

from odoo import api, fields, models, _


class StockRotationReport(models.TransientModel):
    _name = "stock.rotation.report"

    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouse')
    category_ids = fields.Many2many('product.category', string='Category')
    product_ids = fields.Many2many('product.product', string='Product')
    include_warehouse = fields.Boolean(string= 'Include All Warehouse?', default=True)
    include_category = fields.Boolean(string= 'Include All Category?', default=True)
    include_product = fields.Boolean(string= 'Include All product?', default=True)

    @api.onchange('warehouse_ids', 'category_ids', 'product_ids')
    def onchang_warehouse_ids(self):
        if not self.warehouse_ids:
            self.include_warehouse = True
        if not self.category_ids:
            self.include_category = True
        if not self.product_ids:
            self.include_product = True

    def print_report(self):
        """
        This method is to print PDF report on given qweb report action
        """
        datas = {'form': self.read()[0],
                'get_stock_moves': self.get_stock_moves_details()
            }
        return self.env.ref('cit_stock_rotation_report.action_report_stock_rotation').report_action([], data=datas)

    def get_stock_moves_details(self):
        dataDict = {}
        dateFrom = self.date_from
        dateTo = self.date_to
        self.env.cr.execute("""
            SELECT id
            FROM stock_move
            WHERE
                state = 'done' AND
                date >= %s AND date <= %s""",
            (str(dateFrom) + ' 00:00:00', str(dateTo) + ' 23:59:59'))
        StockMoveID = [move[0] for move in self.env.cr.fetchall()]

        domain = [('id', 'in', StockMoveID)]
        if self.warehouse_ids:
            domain.append(('warehouse_id', 'in', self.warehouse_ids.ids))
        if self.category_ids:
            domain.append(('product_id.categ_id', 'in', self.category_ids.ids))
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))

        stockMoves = self.env['stock.move'].search(domain)
        if stockMoves:
            self.env.cr.execute("""
                SELECT sm.product_id, pt.name AS product, pc.id AS categ_id, pc.name AS category,
                    sm.warehouse_id, sw.name AS warehouse,
                    SUM(CASE WHEN spt.code = 'incoming' THEN sm.product_uom_qty ELSE 0 END) AS incooming_qty,
                    SUM(CASE WHEN spt.code = 'outgoing' THEN sm.product_uom_qty ELSE 0 END) AS outgoing_qty,
                    SUM(CASE WHEN spt.code = 'internal' THEN sm.product_uom_qty ELSE 0 END) AS internal_qty
                FROM
                    stock_move AS sm
                JOIN
                    stock_picking_type AS spt ON spt.id = sm.picking_type_id
                JOIN
                    product_product AS pp ON pp.id = sm.product_id
                JOIN
                    product_template AS pt ON pt.id = pp.product_tmpl_id
                JOIN
                    product_category AS pc ON pc.id = pt.categ_id
                JOIN
                    stock_warehouse AS sw ON sw.id = sm.warehouse_id
                WHERE
                    sm.id IN %s
                GROUP BY
                    sm.product_id, pt.name, pc.id, pc.name, sm.warehouse_id, sw.name
            """,(tuple(stockMoves.ids),))
            StockMoveDict = self.env.cr.dictfetchall()

            productObj = self.env['product.product']
            for move in StockMoveDict:
                self.env.cr.execute("""
                    SELECT Cast(max(create_date) AS DATE), count(*)
                    FROM sale_order_line
                    WHERE create_date >= %s AND create_date <= %s AND product_id = %s""",
                    (str(dateFrom) + ' 00:00:00', str(dateTo) + ' 23:59:59', move['product_id']))
                saleLine = self.env.cr.fetchone()

                self.env.cr.execute("""
                    SELECT Cast(max(create_date) AS DATE), count(*)
                    FROM purchase_order_line
                    WHERE create_date >= %s AND create_date <= %s AND product_id = %s""",
                    (str(dateFrom) + ' 00:00:00', str(dateTo) + ' 23:59:59', move['product_id']))
                purchaseLine = self.env.cr.fetchone()

                move.update({
                    'opening': productObj.browse(move['product_id']).with_context({'to_date':dateFrom}).qty_available,
                    'cost_price': productObj.browse(move['product_id']).standard_price,
                    'sale_price': productObj.browse(move['product_id']).lst_price,
                    'reference': productObj.browse(move['product_id']).default_code or '',
                    'last_sale_date': saleLine[0] if saleLine and saleLine[0] else '',
                    'sale_count': saleLine[1] if saleLine else 0,
                    'last_purchase_date': purchaseLine[0] if purchaseLine and purchaseLine[0] else '',
                    'purchase_count': purchaseLine[1] if purchaseLine else 0,
                    'ending': productObj.browse(move['product_id']).with_context({'to_date':dateTo}).qty_available,
                })

            for sm in StockMoveDict:
                dataDict.setdefault(sm.get('warehouse'),{}).setdefault(sm.get('category'),[])
                dataDict[sm.get('warehouse')][sm.get('category')].append({
                                                'product_id': sm.get('product_id'),
                                                'product': sm.get('product'),
                                                'reference': sm.get('reference'),
                                                'cost_price': sm.get('cost_price'),
                                                'sale_price': sm.get('sale_price'),
                                                'opening': sm.get('opening'),
                                                'incooming_qty': sm.get('incooming_qty'),
                                                'internal_qty': sm.get('internal_qty'),
                                                'outgoing_qty': sm.get('outgoing_qty'),
                                                'purchase_count': sm.get('purchase_count'),
                                                'last_purchase_date': sm.get('last_purchase_date'),
                                                'sale_count': sm.get('sale_count'),
                                                'last_sale_date': sm.get('last_sale_date'),
                                                'ending': sm.get('ending'),
                                            })
        return dataDict

    def stock_rotation_export_excel(self):
        """
        This methods make Export in Stock Rotation Excel
        """
        import base64
        filename = 'Stock Rotation Export.xls'
        workbook = xlwt.Workbook()
        style = xlwt.XFStyle()
        tall_style = xlwt.easyxf('font:height 720;') # 36pt
        # Create a font to use with the style
        font = xlwt.Font()
        font.name = 'Times New Roman'
        font.bold = True
        font.height = 250
        style.font = font
        xlwt.add_palette_colour("custom_colour", 0x21)
        workbook.set_colour_RGB(0x21, 105, 105, 105)
        xlwt.add_palette_colour("custom_colour_new", 0x22)
        workbook.set_colour_RGB(0x22, 169, 169, 169)
        worksheet = workbook.add_sheet("Stock Rotation")
        styleheader = xlwt.easyxf('font: bold 1, colour white, height 245; pattern: pattern solid, fore_colour custom_colour')
        stylecolumnheader = xlwt.easyxf('font: bold 1, colour white, height 200; pattern: pattern solid, fore_colour custom_colour')
        zero_col = worksheet.col(0)
        zero_col.width = 236 * 11
        first_col = worksheet.col(1)
        first_col.width = 236 * 40
        second_col = worksheet.col(2)
        second_col.width = 236 * 18
        third_col = worksheet.col(3)
        third_col.width = 236 * 13
        fourth_col = worksheet.col(4)
        fourth_col.width = 236 * 13
        fifth_col = worksheet.col(5)
        fifth_col.width = 236 * 13
        sixth_col = worksheet.col(6)
        sixth_col.width = 236 * 13
        seven_col = worksheet.col(7)
        seven_col.width = 236 * 13
        eight_col = worksheet.col(8)
        eight_col.width = 236 * 13
        nine_col = worksheet.col(9)
        nine_col.width = 236 * 16
        ten_col = worksheet.col(10)
        ten_col.width = 236 * 19
        eleven_col = worksheet.col(11)
        eleven_col.width = 236 * 13
        twelve_col = worksheet.col(12)
        twelve_col.width = 236 * 15
        thirteen_col = worksheet.col(13)
        thirteen_col.width = 236 * 13
        #HEADER
        worksheet.write_merge(0, 1, 0, 13, '   Stock Rotation/Movement of Products', style = styleheader)
        worksheet.write_merge(2, 2, 0, 1, 'Start Date : '+ str(self.date_from))
        worksheet.write_merge(3, 3, 0, 1, 'End Date : '+ str(self.date_to))
        #SUB-HEADER
        row = 4
        worksheet.write(row, 0, 'Product ID', stylecolumnheader)
        worksheet.write(row, 1, 'Product Name', stylecolumnheader)
        worksheet.write(row, 2, 'Internal Reference', stylecolumnheader)
        worksheet.write(row, 3, 'Cost Price', stylecolumnheader)
        worksheet.write(row, 4, 'Sale Price', stylecolumnheader)
        worksheet.write(row, 5, 'Opening', stylecolumnheader)
        worksheet.write(row, 6, 'Incoming', stylecolumnheader)
        worksheet.write(row, 7, 'Outgoing', stylecolumnheader)
        worksheet.write(row, 8, 'Internal', stylecolumnheader)
        worksheet.write(row, 9, 'Purchase Count', stylecolumnheader)
        worksheet.write(row, 10, 'Last Purchase Date', stylecolumnheader)
        worksheet.write(row, 11, 'Sale Count', stylecolumnheader)
        worksheet.write(row, 12, 'Last Sale Date', stylecolumnheader)
        worksheet.write(row, 13, 'Ending', stylecolumnheader)
        row = 5
        data = self.get_stock_moves_details()

        for warehouse in data:
            worksheet.write_merge(row, row, 0, 13, 'Warehouse: '+ str(warehouse))
            for category in data[warehouse]:
                row += 1
                worksheet.write_merge(row, row, 0, 13, 'Category: '+ str(category))
                for line in data[warehouse][category]:
                    row += 1
                    worksheet.write(row, 0, line.get('product_id'))
                    worksheet.write(row, 1, line.get('product'))
                    worksheet.write(row, 2, line.get('reference'))
                    worksheet.write(row, 3, line.get('cost_price'))
                    worksheet.write(row, 4, line.get('sale_price'))
                    worksheet.write(row, 5, line.get('opening'))
                    worksheet.write(row, 6, line.get('incooming_qty'))
                    worksheet.write(row, 7, line.get('outgoing_qty'))
                    worksheet.write(row, 8, line.get('internal_qty'))
                    worksheet.write(row, 9, line.get('purchase_count'))
                    worksheet.write(row, 10, line.get('last_purchase_date'))
                    worksheet.write(row, 11, line.get('sale_count'))
                    worksheet.write(row, 12, line.get('last_sale_date'))
                    worksheet.write(row, 13, line.get('ending'))
            row += 2

        buffer = BytesIO()
        workbook.save(buffer)
        export_id = self.env['stock.rotation.export.excel'].create(
                        {'excel_file': base64.encodestring(buffer.getvalue()), 'file_name': filename})
        buffer.close()

        return {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'stock.rotation.export.excel',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class stock_rotation_export_excel(models.TransientModel):
    _name= "stock.rotation.export.excel"
    _description = "Stock Rotation Excel Report"

    excel_file = fields.Binary('Download Stock Rotation')
    file_name = fields.Char('File', size=64)
