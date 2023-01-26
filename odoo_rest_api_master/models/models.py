# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero
import json
from odoo.http import request
import requests

from odoo.addons.odoo_rest_api_master.controllers.serializers import Serializer
from odoo.addons.odoo_rest_api_master.controllers.parser import Parser

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


#     is_vendor =fields.Char(string="Is Vendor",compute="_check_vendor",default=False)
#     # vendor_ids = fields.Many2one('res.partner', string='Vendor')
#     partner_id = fields.Many2one('res.partner', string='Vendor')
#
#     @api.depends('lot_id','product_id')
#     def _check_vendor(self):
#         for record in self:
#             record.sudo().write({'is_vendor': False})
#             if record.lot_id and record.product_id and record.location_id:
#                 move_lines= self.env['stock.move.line'].search([('product_id','=',record.product_id.id),
#                                                                 ('lot_id','=',record.lot_id.id),
#                                                                 ])
#                 for lines in move_lines:
#                     if  lines.location_id.id == record.location_id.id or lines.location_dest_id.id == record.location_id.id:
#                         record.sudo().write({'partner_id' : lines.vendor_id.id})
#                         # record.sudo().write({'vendor_ids' : lines.vendor_id.id})
#                         record.sudo().write({'is_vendor' : "True"})
#
#             inventory_line = self.env['stock.inventory.line'].search([('product_id','=',record.product_id.id),
#                                                                       ('location_id','=',record.location_id.id),
#                                                                       ('product_qty','=',record.inventory_quantity),
#                                                                       ])
#             # Sort of ambiguity on updation of vendor on inventory report from receipt and inventory adjustment.
#             for lines in inventory_line:
#                 if lines.product_id.id == record.product_id.id and lines.product_qty ==record.inventory_quantity:
#                     record.sudo().write({'partner_id': inventory_line[0].vendor_id.id})
#                     # record.sudo().write({'vendor_ids': inventory_line[0].vendor_id.id})
#                     # record.sudo().write({'vendor_ids': lines.vendor_id.id})
#                     record.sudo().write({'is_vendor': "True"})
#
#     @api.model
#     def _get_inventory_fields_create(self):
#         """ Returns a list of fields user can edit when he want to create a quant in `inventory_mode`.
#         """
#         return ['partner_id','product_id', 'location_id', 'lot_id', 'package_id', 'owner_id', 'inventory_quantity']
#





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
            url = "https://staging.qne.com.pk/odoo_services/submit_vendor.php"
            try :
                params = {'odoo_vendor_id': res.id, 'distributor_type': res.distributor_type, 'vendor': res.name, 'odoo_wh_id': res.warehouse_id.id}
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
#         # url = "https://staging.qne.com.pk/odoo_services/submit_vendor.php"
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
    # imported_data = fields.Boolean()

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


    def button_validate(self):
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

        if not self._should_show_transfers():
            if pickings_without_moves:
                raise UserError(_('Please add some items to move.'))
            if pickings_without_quantities:
                raise UserError(self._get_without_quantities_error_message())
            if pickings_without_lots:
                raise UserError(_('You need to supply a Lot/Serial number for products %s.') % ', '.join(products_without_lots.mapped('display_name')))
        else:
            message = ""
            if pickings_without_moves:
                message += _('Transfers %s: Please add some items to move.') % ', '.join(pickings_without_moves.mapped('name'))
            if pickings_without_quantities:
                message += _('\n\nTransfers %s: You cannot validate these transfers if no quantities are reserved nor done. To force these transfers, switch in edit more and encode the done quantities.') % ', '.join(pickings_without_quantities.mapped('name'))
            if pickings_without_lots:
                message += _('\n\nTransfers %s: You need to supply a Lot/Serial number for products %s.') % (', '.join(pickings_without_lots.mapped('name')), ', '.join(products_without_lots.mapped('display_name')))
            if message:
                raise UserError(message.lstrip())

        # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
        # moves and/or the context and never call `_action_done`.
        if not self.env.context.get('button_validate_picking_ids'):
            self = self.with_context(button_validate_picking_ids=self.ids)
        res = self._pre_action_done_hook()
        if res is not True:
            return res

        # Call `_action_done`.
        if self.env.context.get('picking_ids_not_to_backorder'):
            pickings_not_to_backorder = self.browse(self.env.context['picking_ids_not_to_backorder'])
            pickings_to_backorder = self - pickings_not_to_backorder
        else:
            pickings_not_to_backorder = self.env['stock.picking']
            pickings_to_backorder = self
        pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
        pickings_to_backorder.with_context(cancel_backorder=False)._action_done()
        url = "https://staging.qne.com.pk/odoo_services/submit_stock.php"
        if self.picking_type_code == "incoming":
            try:
                import requests
                # pickings_to_validate.partner_id.id
                # pickings_to_validate.move_lines.product_id.id
                # pickings_to_validate.move_lines.quantity_done
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
    # def action_done(self):  # For 13 not in 14
    #     """Changes picking state to done by processing the Stock Moves of the Picking
    #
    #     Normally that happens when the button "Done" is pressed on a Picking view.
    #     @return: True
    #     """
    #     self._check_company()
    #
    #     todo_moves = self.mapped('move_lines').filtered(lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
    #     # Check if there are ops not linked to moves yet
    #     for pick in self:
    #         if pick.owner_id:
    #             pick.move_lines.write({'restrict_partner_id': pick.owner_id.id})
    #             pick.move_line_ids.write({'owner_id': pick.owner_id.id})
    #
    #         # # Explode manually added packages
    #         # for ops in pick.move_line_ids.filtered(lambda x: not x.move_id and not x.product_id):
    #         #     for quant in ops.package_id.quant_ids: #Or use get_content for multiple levels
    #         #         self.move_line_ids.create({'product_id': quant.product_id.id,
    #         #                                    'package_id': quant.package_id.id,
    #         #                                    'result_package_id': ops.result_package_id,
    #         #                                    'lot_id': quant.lot_id.id,
    #         #                                    'owner_id': quant.owner_id.id,
    #         #                                    'product_uom_id': quant.product_id.uom_id.id,
    #         #                                    'product_qty': quant.qty,
    #         #                                    'qty_done': quant.qty,
    #         #                                    'location_id': quant.location_id.id, # Could be ops too
    #         #                                    'location_dest_id': ops.location_dest_id.id,
    #         #                                    'picking_id': pick.id
    #         #                                    }) # Might change first element
    #         # # Link existing moves or add moves when no one is related
    #         for ops in pick.move_line_ids.filtered(lambda x: not x.move_id):
    #             # Search move with this product
    #             moves = pick.move_lines.filtered(lambda x: x.product_id == ops.product_id)
    #             moves = sorted(moves, key=lambda m: m.quantity_done < m.product_qty, reverse=True)
    #             if moves:
    #                 ops.move_id = moves[0].id
    #             else:
    #                 new_move = self.env['stock.move'].create({
    #                                                 'name': _('New Move:') + ops.product_id.display_name,
    #                                                 'product_id': ops.product_id.id,
    #                                                 'product_uom_qty': ops.qty_done,
    #                                                 'product_uom': ops.product_uom_id.id,
    #                                                 'description_picking': ops.description_picking,
    #                                                 'location_id': pick.location_id.id,
    #                                                 'location_dest_id': pick.location_dest_id.id,
    #                                                 'picking_id': pick.id,
    #                                                 'picking_type_id': pick.picking_type_id.id,
    #                                                 'restrict_partner_id': pick.owner_id.id,
    #                                                 'company_id': pick.company_id.id,
    #                                                })
    #                 ops.move_id = new_move.id
    #                 new_move._action_confirm()
    #                 todo_moves |= new_move
    #                 #'qty_done': ops.qty_done})
    #     todo_moves._action_done(cancel_backorder=self.env.context.get('cancel_backorder'))
    #     # VIA API
    #     record = todo_moves.move_line_nosuggest_ids.move_id
    #     #
    #     url = "https://staging.qne.com.pk/odoo_services/submit_stock.php"
    #     # params = {'odoo_vendor_id': res.id, 'distributor_type': res.distributor_type, "vendor": res.name}
    #     # response = requests.request("POST", url, headers={}, data=params)
    #
    #
    #     print("Actual Data to send")
    #     self.write({'date_done': fields.Datetime.now()})
    #     self._send_confirmation_email()
    #     return True


# INVENTORY ADJUSTMENT WORK  NOT NEEDED FOR PREMIER
# class InventoryExt(models.Model):
#     _inherit = "stock.inventory"
#     def action_validate(self):
#         if not self.exists():
#             return
#         self.ensure_one()
#         if not self.user_has_groups('stock.group_stock_manager'):
#             raise UserError(_("Only a stock manager can validate an inventory adjustment."))
#         if self.state != 'confirm':
#             raise UserError(_(
#                 "You can't validate the inventory '%s', maybe this inventory " +
#                 "has been already validated or isn't ready.") % (self.name))
#
#         record = self.line_ids.filtered(lambda l: l.difference_qty != 0)
#         # API CALL HERE FOR ADJUST INVENTORY
#         # query = '{id,location_id{name,location_id{id,name}},product_id{id,name},theoretical_qty,product_qty,difference_qty}'
#         # serializer = Serializer(record, query,many=True)
#         # print(serializer)
#         # data = serializer.data
#
#         # Start HERE
#         url = "https://staging.qne.com.pk/odoo_services/submit_stock.php"
#         try:
#             for lines in record:
#                 ware_house_id = self.env["stock.warehouse"].search([("lot_stock_id", "=", lines.location_id.id)])
#
#                 params = {"odoo_prod_id": lines.product_id.id,
#                           "stock_qty": lines.product_qty,
#                           "odoo_wh_id": ware_house_id.id,
#                           "odoo_loc_id": lines.location_id.id,
#                           }
#                 response = requests.request("POST", url, headers={}, data=params)
#                 print(response.text)
#                 response_api_decoded = json.loads(response.content.decode())
#                 if response_api_decoded["StatusCode"] == "404":
#                     res = self.env['api.requests'].create({
#                         "name": "Product Quantity Update adjustment",
#                         "call": url,
#                         "data": json.dumps(params),
#                         "type": "POST",
#                         "error": response_api_decoded["userResult"]
#                     })
#                 if response.status_code == 404:
#                     res = self.env['api.requests'].create({
#                         "name": "Product Quantity Update adjustment",
#                         "call": url,
#                         "data": json.dumps(params),
#                         "type": "POST",
#                     })
#                 print(params)
#         except Exception as error:
#             res = self.env['api.requests'].create({
#                 "name": "Contact Creation before creation no retry with this",
#                 "call": url,
#                 "type": "POST",
#                 "error": error,
#                 "model": self.env.context.get('active_model'),
#                 "record_id": self.id
#             })
#         # END HERE
#         # json_data =  json.loads(request.httprequest.data)
#         # json_data["params"] = data
#         # print(json_data)
#         # API CALL HERE FOR ADJUST INVENTORY
#
#         # self.line_ids.filtered(lambda l: l.difference_qty != 0).mapped('difference_qty')
#         # self.line_ids.filtered(lambda l: l.difference_qty != 0).mapped('product_id')
#         inventory_lines = self.line_ids.filtered(lambda l: l.product_id.tracking in ['lot', 'serial'] and not l.prod_lot_id and l.theoretical_qty != l.product_qty)
#
#         lines = self.line_ids.filtered(lambda l: float_compare(l.product_qty, 1, precision_rounding=l.product_uom_id.rounding) > 0 and l.product_id.tracking == 'serial' and l.prod_lot_id)
#         if inventory_lines and not lines:
#             wiz_lines = [(0, 0, {'product_id': product.id, 'tracking': product.tracking}) for product in inventory_lines.mapped('product_id')]
#             wiz = self.env['stock.track.confirmation'].create({'inventory_id': self.id, 'tracking_line_ids': wiz_lines})
#             return {
#                 'name': _('Tracked Products in Inventory Adjustment'),
#                 'type': 'ir.actions.act_window',
#                 'view_mode': 'form',
#                 'views': [(False, 'form')],
#                 'res_model': 'stock.track.confirmation',
#                 'target': 'new',
#                 'res_id': wiz.id,
#             }
#
#         self._action_done()
#         self.line_ids._check_company()
#         self._check_company()
#         return True
