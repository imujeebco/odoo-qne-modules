# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero
import json
import logging
from odoo.http import request
import requests
import math
_logger = logging.getLogger(__name__)

# from odoo.addons.odoo_rest_api_master_production.controllers.serializers import Serializer
# from odoo.addons.odoo_rest_api_master_production.controllers.parser import Parser

class apirequest(models.Model):
    _name = 'api.requests'
    name = fields.Char()
    call = fields.Text() # url
    data = fields.Text() # json
    done = fields.Boolean() # json
    type = fields.Char()
    error = fields.Text()
    model = fields.Many2one('ir.model')
    record_id = fields.Integer()

    def re_try(self):
        # auth if needed to pass in header
        # data = json.loads(self.data)
        # data = json.dumps(self.data)
        # print(data)
        data = json.loads(self.data)
        print(data)
        response = requests.request("POST", self.call, headers={}, data=json.loads(self.data))
        if response:
            done = True
            self.error = response.text # for now
        else:
            self.error = response.text


# code for getting vlocation from vendor in place of default from warehouse
# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'
#
#     def _get_destination_location(self):
#         self.ensure_one()
#         if self.dest_address_id:
#             return self.dest_address_id.property_stock_customer.id
#         return self.partner_id.property_stock_supplier.id

#
class StockQuantExtended(models.Model):
    _inherit = 'stock.quant'

    warehouse_id = fields.Many2one('stock.warehouse' ,compute="get_warehouse",store=True)

    @api.depends("location_id")
    def get_warehouse(self):
        for lines in self:
            ware_house_id = self.env["stock.warehouse"].search([("lot_stock_id", "=", lines.location_id.id)])
            lines.warehouse_id = ware_house_id.id


class PartnerExt(models.Model):
    _inherit = 'res.partner'
    distributor_type = fields.Selection([('marketplace','Market Place'),('warehouse','Warehouse')])
    warehouse_id = fields.Many2one('stock.warehouse')
    premier_cust_id = fields.Integer()
    imported_data = fields.Boolean()

    @api.model
    def create(self, vals):
        res = super(PartnerExt, self).create(vals)
        if  res.imported_data == False:
            url = "https://staging.qnepk.com/odoo_services/submit_vendor.php"
            try :
                params = {'odoo_vendor_id': res.id, 'distributor_type': res.distributor_type, 'vendor': res.name,
                          'odoo_wh_id': res.warehouse_id.id}
                response = requests.request("POST", url, headers={}, data=params)
                response_api_decoded = json.loads(response.content.decode())
                if response_api_decoded["StatusCode"] == "404":
                    res = self.env['api.requests'].create({
                        "name": "Contact creation",
                        "call": url,
                        "data": json.dumps(params),
                        "type": "POST",
                        "error":response_api_decoded['userResult']
                    })
                if response.status_code == 404:
                    res = self.env['api.requests'].create({
                        "name": "Product Quantity Update",
                        "call": url,
                        "data": json.dumps(params),
                        "type": "POST",
                        "error": response_api_decoded["userResult"]
                    })
                    print(response.text)
                print(response.text)
            except Exception as error:
                res = self.env['api.requests'].create({
                    "name": "Contact Creation before creation no retry with this",
                    "call": url,
                    "type": "POST",
                    "error": error,
                    "model": self.env.context.get('active_model'),
                    "record_id": self.id
                })
            # print(response.text)
        return res


# class WarehouseExt(models.Model): # not needed customer bnatay hue get karaingai
#     _inherit = 'stock.warehouse'
#     @api.model
#     def create(self, vals):
#         res = super(WarehouseExt, self).create(vals)
#         print(res)
#         # url = "https://staging.qnepk.com/odoo_testing_services/submit_vendor.php"
#         # params = {'odoo_vendor_id': res.id, 'distributor_type': res.distributor_type, 'vendor': res.name}
#         # response = requests.request("POST", url, headers={}, data=params)
#         return res



class VendorPriceSetup(models.Model):
    _name = 'vendor.prices.setup'
    product_vender_id = fields.Many2one('res.partner',inverse="set_vendor_price")#,inverse="set_vendor_price"
    product_sale_price = fields.Float()
    product_cost_price = fields.Float(inverse="set_vendor_price")
    market_retail_price = fields.Float() # market
    product_id = fields.Many2one('product.product')
    # product_template_id = fields.Many2one('product.template')
    is_active = fields.Boolean()
    def set_vendor_price(self):
        for lines in self:
            seller_ref = self.env['product.supplierinfo'].search([('product_tmpl_id','=',lines.product_id.product_tmpl_id.id),('name','=',lines.product_vender_id.id) ])
            if seller_ref:
                print("Already There")
            else :
                seller = self.env['product.supplierinfo'].create({
                    "name":lines.product_vender_id.id,
                    "price":lines.product_cost_price,
                    "product_tmpl_id":lines.product_id.product_tmpl_id.id,
                    "product_id":lines.product_id.id
                })
    def activate(self):

        self.is_active = True
        self.product_id.lst_price =self.product_sale_price
        # self.product_id.standard_price =self.product_cost_price
        self.product_id.market_retail_price =self.market_retail_price
        remove_other = self.env['vendor.prices.setup'].search([('product_id','=',self.product_id.id),('id','!=',self.id)])
        for lines in remove_other:
            lines.is_active = False
        seller_ref = self.env['product.supplierinfo'].search(
            [('product_tmpl_id', '=', self.product_id.product_tmpl_id.id), ('name', '=', self.product_vender_id.id)])
        if seller_ref:
            seller_ref.price = self.product_cost_price
# class ProductTemplateExt(models.Model):
#     _inherit = 'product.template'
#     vendor_price_ids = fields.One2many('vendor.prices.setup','product_template_id')
class ProductExt(models.Model):
    _inherit = 'product.product'
    vendor_price_ids = fields.One2many('vendor.prices.setup','product_id',inverse='_set_prices')
    market_retail_price = fields.Float()
    is_pack = fields.Boolean()
    product_bundle_quantity = fields.Integer()

    @api.depends('stock_move_ids.product_qty', 'stock_move_ids.state')
    @api.depends_context(
        'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
        'company_owned', 'force_company', 'location', 'warehouse',
    )
    def _compute_quantities(self):
        products = self.filtered(lambda p: p.type != 'service')
        res = products._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'),
                                                self._context.get('package_id'), self._context.get('from_date'),
                                                self._context.get('to_date'))

        for product in products:
            product.qty_available = res[product.id]['qty_available']
            product.product_bundle_quantity = res[product.id]['free_qty']
            product.incoming_qty = res[product.id]['incoming_qty']
            product.outgoing_qty = res[product.id]['outgoing_qty']
            product.virtual_available = res[product.id]['virtual_available']
            product.free_qty = res[product.id]['free_qty']

        # Services need to be set with 0.0 for all quantities
        services = self - products
        services.qty_available = 0.0
        services.incoming_qty = 0.0
        services.outgoing_qty = 0.0
        services.virtual_available = 0.0
        services.free_qty = 0.0
        ""
    def _set_prices(self):
        print("LOLOLOLOLOLOL")


class StockInvetoryExt(models.Model):
    _inherit = 'stock.inventory'


    def post_inventory(self):
        # The inventory is posted as a single step which means quants cannot be moved from an internal location to another using an inventory
        # as they will be moved to inventory loss, and other quants will be created to the encoded quant location. This is a normal behavior
        # as quants cannot be reuse from inventory location (users can still manually move the products before/after the inventory if they want).
        ids = self.mapped('move_ids').filtered(lambda move: move.state != 'done')._action_done()
        # call API May be but search self.line_ids.filtered(lambda l: l.difference_qty != 0).mapped('difference_qty')
        print(ids.mapped("name"))
        return True

class PickingExt(models.Model):
    _inherit = "stock.picking"

    def button_validate_api(self):
        pickings_not_to_backorder = self.env['stock.picking']
        # update_qty = self.env['product.product']
        pickings_to_backorder = self
        # pickings_not_to_backorder = self.browse(self.env.context['picking_ids_not_to_backorder'])
        # pickings_to_backorder = self - pickings_not_to_backorder
        # pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
        pickings_to_backorder.with_context(cancel_backorder=True)._action_done()
        self.validate_method_update_qty()
        return True

    def get_serialized_data(self,record):
        data = {"products":[]}
        for lines in record:
            quantity = self.env['stock.quant'].search(
                [('product_id', '=', lines.product_id.id), ('location_id', '=', lines.location_dest_id.id)],
                limit=1)
            print(quantity)
            product_id = request.env['product.product'].search([("id","=",lines.product_id.id)])
            data["products"].append({"productId":product_id.retailo_sku,
                                "quantity":quantity.quantity
                                })
        return data


    def update_qty_web_hook(self, qty, product_id):
        url = "https://staging.qnepk.com/odoo_services/submit_stock_webhook.php"
        params = {'odoo_vendor_id': 320,
                  'odoo_wh_id': 1,
                  'odoo_prod_id': product_id,
                  'stock_qty': qty}
        response = requests.request("POST", url, headers={}, data=params)
        response_api_decoded = json.loads(response.content.decode())
        print(params)
        print(response_api_decoded)
        _logger.info(params)


    def button_validate(self):
        res = super(PickingExt, self).button_validate()
        if res==True:
            self.validate_method_update_qty()

        return res



    def validate_method_update_qty(self):
        for line in self.move_line_ids:
            print(line)
            line.product_id._compute_quantities()
            qty = line.product_id.product_bundle_quantity
            self.update_qty_web_hook(qty, line.product_id.id)
            bom_id = request.env['mrp.bom'].search([('product_id', '=', line.product_id.id)])
            component_product_object = []
            updated_bundle = []
            if bom_id:
                for product_in_bil in bom_id.bom_line_ids:
                    component_product_object.append(product_in_bil.product_id)
                    product_in_bil.product_id._compute_quantities()
                    qty = product_in_bil.product_id.product_bundle_quantity
                    updated_bundle.append(product_in_bil.product_id.id)
                    self.update_qty_web_hook(qty, product_in_bil.product_id.id)

                    bom_line_id = request.env['mrp.bom.line'].search(
                        [('product_id', '=', product_in_bil.product_id.id)])
                    for bill in bom_line_id:
                        if bill.bom_id.product_id not in updated_bundle:
                            updated_bundle.append(bill.bom_id.product_id.id)
                            if bill.bom_id.product_id:
                                bill.bom_id.product_id._compute_quantities()
                                qty = bill.bom_id.product_id.product_bundle_quantity
                                self.update_qty_web_hook(qty, bill.bom_id.product_id.id)
            bom_line_id = request.env['mrp.bom.line'].search([('product_id', '=', line.product_id.id)])
            if bom_line_id:
                for bill in bom_line_id:
                    if bill.id not in updated_bundle:
                        updated_bundle.append(bill.bom_id.product_id.id)
                        if bill.bom_id.product_id:
                            bill.bom_id.product_id._compute_quantities()
                            qty = bill.bom_id.product_id.product_bundle_quantity
                            self.update_qty_web_hook(qty, bill.bom_id.product_id.id)


    def button_validate1(self):
        # Clean-up the context key at validation to avoid forcing the creation of immediate
        # transfers.
        ctx = dict(self.env.context)
        ctx.pop('default_immediate_transfer', None)
        self = self.with_context(ctx)

        # Sanity checks.
        pickings_without_moves = self.browse()
        pickings_without_quantities = self.browse()
        pickings_without_lots = self.browse()
        products_without_lots = self.env['product.product']
        for picking in self:
            if not picking.move_lines and not picking.move_line_ids:
                pickings_without_moves |= picking

            picking.message_subscribe([self.env.user.partner_id.id])
            picking_type = picking.picking_type_id
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            no_quantities_done = all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in picking.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
            no_reserved_quantities = all(float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in picking.move_line_ids)
            if no_reserved_quantities and no_quantities_done:
                pickings_without_quantities |= picking

            if picking_type.use_create_lots or picking_type.use_existing_lots:
                lines_to_check = picking.move_line_ids
                if not no_quantities_done:
                    lines_to_check = lines_to_check.filtered(lambda line: float_compare(line.qty_done, 0, precision_rounding=line.product_uom_id.rounding))
                for line in lines_to_check:
                    product = line.product_id
                    if product and product.tracking != 'none':
                        if not line.lot_name and not line.lot_id:
                            pickings_without_lots |= picking
                            products_without_lots |= product

        # if not self._should_show_transfers():
        #     if pickings_without_moves:
        #         raise UserError(_('Please add some items to move.'))
        #     if pickings_without_quantities:
        #         raise UserError(self._get_without_quantities_error_message())
        #     if pickings_without_lots:
        #         raise UserError(_('You need to supply a Lot/Serial number for products %s.') % ', '.join(products_without_lots.mapped('display_name')))
        # else:
        #     message = ""
        #     if pickings_without_moves:
        #         message += _('Transfers %s: Please add some items to move.') % ', '.join(pickings_without_moves.mapped('name'))
        #     if pickings_without_quantities:
        #         message += _('\n\nTransfers %s: You cannot validate these transfers if no quantities are reserved nor done. To force these transfers, switch in edit more and encode the done quantities.') % ', '.join(pickings_without_quantities.mapped('name'))
        #     if pickings_without_lots:
        #         message += _('\n\nTransfers %s: You need to supply a Lot/Serial number for products %s.') % (', '.join(pickings_without_lots.mapped('name')), ', '.join(products_without_lots.mapped('display_name')))
        #     if message:
        #         raise UserError(message.lstrip())

        # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
        # moves and/or the context and never call `_action_done`.
        # if not self.env.context.get('button_validate_picfking_ids'):
        #     self = self.with_context(button_validate_picking_ids=self.ids)
        # res = self._pre_action_done_hook()
        # if res is not True:
        #     return res

        # Call `_action_done`.
        if self.env.context.get('picking_ids_not_to_backorder'):
            pickings_not_to_backorder = self.browse(self.env.context['picking_ids_not_to_backorder'])
            pickings_to_backorder = self - pickings_not_to_backorder
        else:
            pickings_not_to_backorder = self.env['stock.picking']
            pickings_to_backorder = self
        # pickings_not_to_backorder.with_context(cancel_backorder=True).action_done()
        # pickings_to_backorder.with_context(cancel_backorder=False).action_done()
        url = "https://staging.qnepk.com/odoo_services/submit_stock.php"
        if self.picking_type_code == "incoming":
            try:
                import requests
                ware_house_id = self.env["stock.warehouse"].search([("lot_stock_id", "=", self.location_dest_id.id)])
    # Check here why no lines

                if self.move_ids_without_package:
                    for move_lines in self.move_ids_without_package:
                        quant = self.env['stock.quant'].search(
                            [('product_id', '=', move_lines.product_id.id), ('location_id', '=', self.location_dest_id.id)],
                            limit=1)
                        quantity = quant.available_quantity
                        params = {"odoo_prod_id": move_lines.product_id.id,
                                  "stock_qty_updated": move_lines.quantity_done,
                                  "stock_qty": quantity,
                                  "odoo_wh_id": ware_house_id.id,
                                  "odoo_loc_id":move_lines.location_dest_id.id,
                                  "odoo_vendor_id":self.partner_id.id
                                  }


                        response = requests.request("POST", url, headers={}, data=params)
                        print(response.text)
                        response_api_decoded = json.loads(response.content.decode())
                        if response_api_decoded["StatusCode"] == "404":
                            res = self.env['api.requests'].create({
                                "name": "Product Quantity Update",
                                "call": url,
                                "data": json.dumps(params),
                                "type": "POST",
                                "error":response_api_decoded["userResult"]
                            })
                        if response.status_code == 404:
                            res = self.env['api.requests'].create({
                                "name": "Product Quantity Update",
                                "call": url,
                                "data": json.dumps(params),
                                "type": "POST",
                            })
                # else: # this may not be needed
                #     for values in lines_to_check:
                #         quant = self.env['stock.quant'].search([('product_id','=',values.product_id.id),('location_id','=',self.location_dest_id.id)],limit=1)
                #         quantity = quant.available_quantity
                #         params = {"odoo_prod_id": values.product_id.id,
                #                   "stock_qty_updated": values.qty_done,
                #                   "stock_qty": quantity,
                #                   "odoo_wh_id":ware_house_id.id,
                #                   "odoo_loc_id": self.location_dest_id.id,
                #                   "odoo_vendor_id":self.partner_id.id
                #
                #                   }
                #         response = requests.request("POST", url, headers={}, data=params)
                #         if response.status_code == 404:
                #             res = self.env['api.requests'].create({
                #                 "name": "Test",
                #                 "call": url,
                #                 "data": json.dumps(params),
                #                 "type": "POST",
                #                 "model":self.env.context.get('active_model'),
                #                 "record_id":self.id
                #
                #             })
            except Exception as error:
                    res = self.env['api.requests'].create({
                        "name": "Product Quantity Update before send",
                        "call": url,
                        "type": "POST",
                        "error": error,
                        "model": self.env.context.get('active_model'),
                        "record_id": self.id
                    })
        return True




class SaleOrder(models.Model):
    _inherit = "sale.order"

    def update_qty_server_cancel_order(self):
        self.ensure_one()

        if self.state == 'done':
            self.action_unlock()
        self.action_cancel()
        for line in self.order_line:
            line.product_id._compute_quantities()
            qty = line.product_id.product_bundle_quantity
            self.update_qty_web_hook(qty, line.product_id.id)
            bom_id = request.env['mrp.bom'].search([('product_id', '=', line.product_id.id)])
            component_product_object = []
            updated_bundle = []
            if bom_id:
                for product_in_bil in bom_id.bom_line_ids:
                    component_product_object.append(product_in_bil.product_id)
                    product_in_bil.product_id._compute_quantities()
                    qty = product_in_bil.product_id.product_bundle_quantity
                    updated_bundle.append(product_in_bil.product_id.id)
                    self.update_qty_web_hook(qty, product_in_bil.product_id.id)

                    bom_line_id = request.env['mrp.bom.line'].search([('product_id', '=', product_in_bil.product_id.id)])
                    for bill in bom_line_id:
                        if bill.bom_id.product_id not in updated_bundle:
                            updated_bundle.append(bill.bom_id.product_id.id)
                            if bill.bom_id.product_id:
                                bill.bom_id.product_id._compute_quantities()
                                qty = bill.bom_id.product_id.product_bundle_quantity
                                self.update_qty_web_hook(qty, bill.bom_id.product_id.id)
            bom_line_id = request.env['mrp.bom.line'].search([('product_id', '=', line.product_id.id)])
            if bom_line_id:
                for bill in bom_line_id:
                    if bill.id not in updated_bundle:
                        updated_bundle.append(bill.bom_id.product_id.id)
                        if bill.bom_id.product_id:
                            bill.bom_id.product_id._compute_quantities()
                            qty = bill.bom_id.product_id.product_bundle_quantity
                            self.update_qty_web_hook(qty, bill.bom_id.product_id.id)




    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for line in self.order_line:
            line.product_id._compute_quantities()
            qty = line.product_id.product_bundle_quantity
            self.update_qty_web_hook(qty, line.product_id.id)
            bom_id = request.env['mrp.bom'].search([('product_id', '=', line.product_id.id)])
            component_product_object = []
            updated_bundle = []
            if bom_id:
                for product_in_bil in bom_id.bom_line_ids:
                    component_product_object.append(product_in_bil.product_id)
                    product_in_bil.product_id._compute_quantities()
                    qty = product_in_bil.product_id.product_bundle_quantity
                    updated_bundle.append(product_in_bil.product_id.id)
                    self.update_qty_web_hook(qty, product_in_bil.product_id.id)

                    bom_line_id = request.env['mrp.bom.line'].search([('product_id', '=', product_in_bil.product_id.id)])
                    for bill in bom_line_id:
                        if bill.bom_id.product_id not in updated_bundle:
                            updated_bundle.append(bill.bom_id.product_id.id)
                            if bill.bom_id.product_id:
                                bill.bom_id.product_id._compute_quantities()
                                qty = bill.bom_id.product_id.product_bundle_quantity
                                self.update_qty_web_hook(qty, bill.bom_id.product_id.id)
            bom_line_id = request.env['mrp.bom.line'].search([('product_id', '=', line.product_id.id)])
            if bom_line_id:
                for bill in bom_line_id:
                    if bill.id not in updated_bundle:
                        updated_bundle.append(bill.bom_id.product_id.id)
                        if bill.bom_id.product_id:
                            bill.bom_id.product_id._compute_quantities()
                            qty = bill.bom_id.product_id.product_bundle_quantity
                            self.update_qty_web_hook(qty, bill.bom_id.product_id.id)

        return res

    def update_qty_web_hook(self, qty, product_id):
        url = "https://staging.qnepk.com/odoo_services/submit_stock_webhook.php"
        params = {'odoo_vendor_id': 320,
                  'odoo_wh_id': 1,
                  'odoo_prod_id': product_id,
                  'stock_qty': qty}
        response = requests.request("POST", url, headers={}, data=params)
        response_api_decoded = json.loads(response.content.decode())
        print(params)
        print(response_api_decoded)
        _logger.info(params)


    def create_invoice_api(self, partnerId, register_payment_journal_id, invoice_date):
        payment = self.env["sale.advance.payment.inv"].create({})
        # account_move = self.env["account.move"]
        order = self
        old_so_date = self.date_order
        invoice_id = payment.with_context(active_ids=self.id).create_invoices()
        print(self.invoice_ids)
        for invoice in self.invoice_ids:
            if partnerId:
                invoice.partner_id = partnerId
            if invoice_date:
                invoice.invoice_date = invoice_date
            invoice.action_post()
            # invoice.resolve_payment()

            payment_method_manual_in = self.env.ref(
                "account.account_payment_method_manual_in"
            )
            if not register_payment_journal_id:
                register_payment_journal_id = order.register_payment_journal_id.id

            if register_payment_journal_id > 0:
                register_payments = (
                    self.env["account.payment.register"]
                        .with_context(active_model='account.move', active_ids=[invoice.id],
                                      journal_id=order.register_payment_journal_id.id).create(
                        {"payment_method_id": payment_method_manual_in.id,
                         "journal_id": register_payment_journal_id,
                         "payment_date": invoice_date
                         })
                )
                payment = self.env["account.payment"].browse(
                    register_payments.action_create_payments()
                )
        print("invoice_id")
        return invoice_id

    def create_invoice_api_old(self):
        payment = self.env["sale.advance.payment.inv"].create({})
        # account_move = self.env["account.move"]
        order = self
        old_so_date = self.date_order
        invoice_id = payment.with_context(active_ids=self.id).create_invoices()
        print(self.invoice_ids)
        for invoice in self.invoice_ids:
            invoice.action_post()
            # invoice.resolve_payment()

            payment_method_manual_in = self.env.ref(
                "account.account_payment_method_manual_in"
            )
            register_payments = (
                self.env["account.payment.register"]
                    .with_context(active_model='account.move', active_ids=[invoice.id],
                                  journal_id=order.register_payment_journal_id.id).create(
                    {"payment_method_id": payment_method_manual_in.id,
                     "journal_id": order.register_payment_journal_id.id,
                     "payment_date": old_so_date
                     })
            )
            payment = self.env["account.payment"].browse(
                register_payments.action_create_payments()
            )

        print("invoice_id")
        return invoice_id


class ProductCustom(models.Model):
    _inherit = "product.template"

    def update_product_invoicing_policy(self):
        products = self.search([('invoice_policy', '=', 'order')],limit=1000)
        print(products,"------------------------------------------")
        # records = self.search([])
        for product in products:
            product.invoice_policy = 'delivery'

#
# class AccountMoveLine(models.Model):
#     _inherit = "account.move.line"
#
#     def create(self, vals):
#         res = super(AccountMoveLine, self).create(vals)
#         for line in res:
#             if line.move_id.move_type =='out_invoice' and line.account_internal_group == 'income':
#               # for line in lines:
#
#                 print(line,"-------------")
#                 bom_id = request.env['mrp.bom'].search([('product_id', '=', line.product_id.id)])
#                 # print(bom_id)
#                 if bom_id:
#                     line.product_id._compute_quantities()
#                     product_stock = self.env["product.product"].search([('id', '=', line.product_id.id)])
#                     qty_new = product_stock.product_bundle_quantity
#                     for product_in_bil in bom_id.bom_line_ids:
#                         product_stock = self.env["stock.quant"].search([('product_id', '=', product_in_bil.product_id.id),
#                                                                         ('warehouse_id', '=',1)])
#                         for product_stock_qty in product_stock:
#                             qty_new = product_stock_qty.quantity - product_stock_qty.reserved_quantity #- line.quantity*product_in_bil.product_qty
#                             self.update_qty_web_hook_invoice(qty_new, product_in_bil.product_id.id)
#                 else:
#                     product_updated_qty = 0
#                     product_stock = self.env["stock.quant"].search([('product_id', '=', line.product_id.id),
#                                                                     ('warehouse_id', '=',1)])
#                     for product_stock_qty in product_stock:
#                         product_updated_qty = qty_new = product_stock_qty.quantity - product_stock_qty.reserved_quantity
#                         self.update_qty_web_hook_invoice(qty_new, line.product_id.id)
#                     bom_line_id = request.env['mrp.bom.line'].search([('product_id', '=', line.product_id.id)])
#                     for bill in bom_line_id:
#                         if bill.bom_id.product_id:
#                             qty_new = math.ceil(product_updated_qty/bill.product_qty)
#                             self.update_qty_web_hook_invoice(qty_new, bill.bom_id.product_id.id)
#
#         return res
#     def update_qty_web_hook_invoice(self, qty, product_id ):
#         url = "https://staging.qnepk.com/odoo_services/submit_stock_webhook.php"
#         params = {'odoo_vendor_id': 320,
#                   'odoo_wh_id': 1,
#                   'odoo_prod_id': product_id,
#                   'stock_qty': qty}
#         response = requests.request("POST", url, headers={}, data=params)
#         response_api_decoded = json.loads(response.content.decode())
#         print(params)
#         _logger.info(params)
