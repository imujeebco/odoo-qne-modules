# -*- coding: utf-8 -*-
import json
import math
import logging
import requests
from odoo import http, _, exceptions
from odoo.http import request
from .serializers import Serializer
from .exceptions import QueryFormatError
from ast import literal_eval

_logger = logging.getLogger(__name__)

#Error Response Retrun Function
def error_response(error, msg):
    return {
        "jsonrpc": "2.0",
        "id": None,
        "error": {
            "code": 200,
            "message": msg,
            "data": {
                "name": str(error),
                "debug": "",
                "message": msg,
                "arguments": list(error.args),
                "exception_type": type(error).__name__
            }
        }
    }


#Odoo APIs Class 
class OdooAPI(http.Controller):

#OLD APIS
#1 - Authentication

    @http.route(
        '/auth/',
        type='json', auth='none', methods=["POST"], csrf=False)
    def authenticate(self, *args, **post):
        try:
            login = post["login"]
        except KeyError:
            raise exceptions.AccessDenied(message='`login` is required.')

        try:
            password = post["password"]
        except KeyError:
            raise exceptions.AccessDenied(message='`password` is required.')

        try:
            db = post["db"]
        except KeyError:
            raise exceptions.AccessDenied(message='`db` is required.')

        url_root = request.httprequest.url_root
        AUTH_URL = f"{url_root}web/session/authenticate/"

        headers = {'Content-type': 'application/json'}

        data = {
            "jsonrpc": "2.0",
            "params": {
                "login": login,
                "password": password,
                "db": db
            }
        }

        res = requests.post(
            AUTH_URL,
            data=json.dumps(data),
            headers=headers
        )

        try:
            session_id = res.cookies["session_id"]
            user = json.loads(res.text)
            user["result"]["session_id"] = session_id
        except Exception:
            return "Invalid credentials."
        return user["result"]

# 2 - Delivery Return
    @http.route('/delivery/return/<int:id>',type='json', auth="user", methods=['POST'], csrf=False)
    def delivery_return_data(self,id, **post):
        try:
            picking = request.env['stock.picking'].search([('id','=',id)])
            if not picking:
                return {"error":"Picking id not found"}
            product_in_picking = picking.move_ids_without_package.product_id.ids

            return_delivery = request.env['stock.picking'].create({
                "partner_id": picking.partner_id.id,
                "picking_type_id": post["data"]["picking_type_id"],
                "location_dest_id": picking.location_id.id,
                "location_id": picking.location_dest_id.id,
                "sale_id": picking.sale_id.id,
                "origin": "Return " + picking.sale_id.name,

            })
            for product_id,qty in zip(post["data"]["product_id"],post["data"]["product_uom_qty"]) :
                product = request.env['product.product'].search([('id','=',product_id)])
                if product:
                    if product.id not in product_in_picking:
                        return_delivery.unlink()
                        return {
                            "error":"This Product doesn't exist in this Picking."
                                }
                if product:
                    return_delivery.move_ids_without_package.create(
                        {'name':"Retun",
                         'product_id': product.id,
                         'product_uom_qty': qty,
                         'product_uom': product.uom_id.id,
                         "to_refund":True,
                         "location_dest_id": return_delivery.location_id.id,
                        "location_id": return_delivery.location_dest_id.id,
                        "picking_id": return_delivery.id,
                         })
            return_delivery.action_confirm()
            return_delivery.action_assign()
            for mv in return_delivery.move_ids_without_package:
                mv.quantity_done = mv.product_uom_qty
            return_delivery.button_validate()
            picking.sale_id.picking_ids += return_delivery
            return {
                "success":True
            }
        except Exception as e:
            return {"error":e}


# CUSTOM FUNCTION -- get the premier customer if dosen't exist create it
    def get_or_create_customer(self,post):
        customer = post['customer_data']
        partner_id = request.env['res.partner'].search([("premier_cust_id", "=", customer["premier_cust_id"])])
        if partner_id:
            post['data']["partner_id"] = partner_id.id
        else:
            partner_id = request.env["res.partner"].create([customer])
            post['data']["partner_id"] = partner_id.id
        return post

# 3 - Sale Deliveries - Confirm
    @http.route(
    '/sale_deliveries/confirm/<int:id>',
    type='json', auth="user", methods=['POST'], csrf=False)
    def sale_model_data(self,id, **post):
        try:
            order_id = request.env["sale.order"].search([('id','=',id)])
            order_id.action_confirm()
            picking_ids = order_id.picking_ids
            for picking in picking_ids:
                if picking.state not in ["done","cancel"]:
                    picking.action_assign()
                    picking.action_confirm()
                    for mv in picking.move_ids_without_package:
                        mv.quantity_done = mv.product_uom_qty
                    picking.button_validate()
        except Exception as error:
            return {'error':error,
                    'success':0,
                    'ids':False}
        return {'error':False,
                    'success':1,
                    'delivery_ids':picking_ids.ids}

#4 - Generic Model - Custom Function Call
    @http.route(
        '/object/<string:model>/<string:function>',
        type='json', auth='user', methods=["POST"], csrf=False)
    def call_model_function(self, model, function, **post):
        args = []
        kwargs = {}
        if "args" in post:
            args = post["args"]
        if "kwargs" in post:
            kwargs = post["kwargs"]
        model = request.env[model]
        result = getattr(model, function)(*args, **kwargs)
        return result

# 5 Generic Model - Custom ID - Custom Function Call
    @http.route(
        '/object/<string:model>/<int:rec_id>/<string:function>',
        type='json', auth='user', methods=["POST"], csrf=False)
    def call_obj_function(self, model, rec_id, function, **post):
        args = []
        kwargs = {}
        if "args" in post:
            args = post["args"]
        if "kwargs" in post:
            kwargs = post["kwargs"]
        obj = request.env[model].browse(rec_id).ensure_one()
        result = getattr(obj, function)(*args, **kwargs)
        return result


# 6) Generic Model - GET ALL DATA
    @http.route(
        '/api/<string:model>',
        type='http', auth='user', methods=['GET'], csrf=False)
    def get_model_data(self, model, **params):
        if model == 'stock.quant':
            par = literal_eval(params['filter'])
            for param in par:
                if param[0] == 'product_id':
                    product = request.env['product.product'].search([('is_pack','=',True),('id','=',param[2])])
                    if product:
                        res =   {"result": [
                                    {
                                        "id": product.id,
                                        "available_quantity": product.product_bundle_quantity
                                    }
                                ]}
                        return http.Response(
                            json.dumps(res),
                            status=200,
                            mimetype='application/json'
                        )


        try:
            records = request.env[model].search([])
        except KeyError as e:
            msg = "The model `%s` does not exist." % model
            res = error_response(e, msg)
            return http.Response(
                json.dumps(res),
                status=200,
                mimetype='application/json'
            )

        if "query" in params:
            query = params["query"]
        else:
            query = "{*}"

        if "order" in params:
            orders = json.loads(params["order"])
        else:
            orders = ""

        if "filter" in params:
            filters = json.loads(params["filter"])
            records = request.env[model].search(filters, order=orders)

        prev_page = None
        next_page = None
        total_page_number = 1
        current_page = 1

        if "page_size" in params:
            page_size = int(params["page_size"])
            count = len(records)
            total_page_number = math.ceil(count / page_size)

            if "page" in params:
                current_page = int(params["page"])
            else:
                current_page = 1  # Default page Number
            start = page_size * (current_page - 1)
            stop = current_page * page_size
            records = records[start:stop]
            next_page = current_page + 1 \
                if 0 < current_page + 1 <= total_page_number \
                else None
            prev_page = current_page - 1 \
                if 0 < current_page - 1 <= total_page_number \
                else None

        if "limit" in params:
            limit = int(params["limit"])
            records = records[0:limit]

        try:
            serializer = Serializer(records, query, many=True)
            data = serializer.data
        except (SyntaxError, QueryFormatError) as e:
            res = error_response(e, e.msg)
            return http.Response(
                json.dumps(res),
                status=200,
                mimetype='application/json'
            )

        res = {
            "count": len(records),
            "prev": prev_page,
            "current": current_page,
            "next": next_page,
            "total_pages": total_page_number,
            "result": data
        }
        
        return http.Response(
            json.dumps(res),
            status=200,
            mimetype='application/json'
        )


# 7) Generic Model - Specific ID - Get Specific Record Data
    @http.route('/api/<string:model>/<int:rec_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_model_rec(self, model, rec_id, **params):
        try:
            records = request.env[model].search([])
        except KeyError as e:
            msg = "The model `%s` does not exist." % model
            res = error_response(e, msg)
            return http.Response(
                json.dumps(res),
                status=200,
                mimetype='application/json'
            )

        if "query" in params:
            query = params["query"]
        else:
            query = "{*}"

        # TODO: Handle the error raised by `ensure_one`
        record = records.browse(rec_id).ensure_one()

        try:
            serializer = Serializer(record, query)
            data = serializer.data
        except (SyntaxError, QueryFormatError) as e:
            res = error_response(e, e.msg)
            return http.Response(
                json.dumps(res),
                status=200,
                mimetype='application/json'
            )

        return http.Response(
            json.dumps(data),
            status=200,
            mimetype='application/json'
        )

# 8) Generic Model - Post Data to a model.
    @http.route(
        '/api/<string:model>/',
        type='json', auth="user", methods=['POST'], csrf=False)
    def post_model_data(self, model, **post):
        try:
            if 'customer_data' in post.keys():
                self.get_or_create_customer(post)
            data = post['data']
        except KeyError:
            msg = "`data` parameter is not found on POST request body"
            raise exceptions.ValidationError(msg)

        try:
            model_to_post = request.env[model]
        except KeyError:
            msg = "The model `%s` does not exist." % model
            raise exceptions.ValidationError(msg)

        # TODO: Handle data validation

        if "context" in post:
            context = post["context"]
            record = model_to_post.with_context(**context).create(data)
        else:
            record = model_to_post.create(data)
        return record.id

# 9) Generic Model - Specific ID - Update/Put Data
    # This is for single record update
    @http.route(
        '/api/<string:model>/<int:rec_id>/',
        type='json', auth="user", methods=['PUT'], csrf=False)
    def put_model_record(self, model, rec_id, **post):
        try:
            data = post['data']
        except KeyError:
            msg = "`data` parameter is not found on PUT request body"
            raise exceptions.ValidationError(msg)

        try:
            model_to_put = request.env[model]
        except KeyError:
            msg = "The model `%s` does not exist." % model
            raise exceptions.ValidationError(msg)

        if "context" in post:
            # TODO: Handle error raised by `ensure_one`
            rec = model_to_put.with_context(**post["context"])\
                .browse(rec_id).ensure_one()
        else:
            rec = model_to_put.browse(rec_id).ensure_one()

        # TODO: Handle data validation
        for field in data:
            if isinstance(data[field], dict):
                operations = []
                for operation in data[field]:
                    if operation == "push":
                        operations.extend(
                            (4, rec_id, _)
                            for rec_id
                            in data[field].get("push")
                        )
                    elif operation == "pop":
                        operations.extend(
                            (3, rec_id, _)
                            for rec_id
                            in data[field].get("pop")
                        )
                    elif operation == "delete":
                        operations.extend(
                            (2, rec_id, _)
                            for rec_id
                            in data[field].get("delete")
                        )
                    else:
                        data[field].pop(operation)  # Invalid operation

                data[field] = operations
            elif isinstance(data[field], list):
                data[field] = [(6, _, data[field])]  # Replace operation
            else:
                pass

        try:
            return rec.write(data)
        except Exception as e:
            # TODO: Return error message(e.msg) on a response
            return False


# 10)    Generic Model - Bulk Update

    # This is for bulk update
    @http.route(
        '/api/<string:model>/',
        type='json', auth="user", methods=['PUT'], csrf=False)
    def put_model_records(self, model, **post):
        try:
            data = post['data']
        except KeyError:
            msg = "`data` parameter is not found on PUT request body"
            raise exceptions.ValidationError(msg)

        try:
            model_to_put = request.env[model]
        except KeyError:
            msg = "The model `%s` does not exist." % model
            raise exceptions.ValidationError(msg)

        # TODO: Handle errors on filter
        filters = post["filter"]

        if "context" in post:
            recs = model_to_put.with_context(**post["context"])\
                .search(filters)
        else:
            recs = model_to_put.search(filters)

        # TODO: Handle data validation
        for field in data:
            if isinstance(data[field], dict):
                operations = []
                for operation in data[field]:
                    if operation == "push":
                        operations.extend(
                            (4, rec_id, _)
                            for rec_id
                            in data[field].get("push")
                        )
                    elif operation == "pop":
                        operations.extend(
                            (3, rec_id, _)
                            for rec_id
                            in data[field].get("pop")
                        )
                    elif operation == "delete":
                        operations.extend(
                            (2, rec_id, _)
                            for rec_id in
                            data[field].get("delete")
                        )
                    else:
                        pass  # Invalid operation

                data[field] = operations
            elif isinstance(data[field], list):
                data[field] = [(6, _, data[field])]  # Replace operation
            else:
                pass

        if recs.exists():
            try:
                return recs.write(data)
            except Exception as e:
                # TODO: Return error message(e.msg) on a response
                return False
        else:
            # No records to update
            return True


# 11)    Generic Model - Specific ID - Delete
    # This is for deleting one record
    @http.route(
        '/api/<string:model>/<int:rec_id>/',
        type='http', auth="user", methods=['DELETE'], csrf=False)
    def delete_model_record(self, model,  rec_id, **post):
        try:
            model_to_del_rec = request.env[model]
        except KeyError as e:
            msg = "The model `%s` does not exist." % model
            res = error_response(e, msg)
            return http.Response(
                json.dumps(res),
                status=200,
                mimetype='application/json'
            )

        # TODO: Handle error raised by `ensure_one`
        rec = model_to_del_rec.browse(rec_id).ensure_one()

        try:
            is_deleted = rec.unlink()
            res = {
                "result": is_deleted
            }
            return http.Response(
                json.dumps(res),
                status=200,
                mimetype='application/json'
            )
        except Exception as e:
            res = error_response(e, str(e))
            return http.Response(
                json.dumps(res),
                status=200,
                mimetype='application/json'
            )


# 12)    Generic Model - Bulk Deletion
    # This is for bulk deletion
    @http.route(
        '/api/<string:model>/',
        type='http', auth="user", methods=['DELETE'], csrf=False)
    def delete_model_records(self, model, **post):
        filters = json.loads(post["filter"])

        try:
            model_to_del_rec = request.env[model]
        except KeyError as e:
            msg = "The model `%s` does not exist." % model
            res = error_response(e, msg)
            return http.Response(
                json.dumps(res),
                status=200,
                mimetype='application/json'
            )

        # TODO: Handle error raised by `filters`
        recs = model_to_del_rec.search(filters)

        try:
            is_deleted = recs.unlink()
            res = {
                "result": is_deleted
            }
            return http.Response(
                json.dumps(res),
                status=200,
                mimetype='application/json'
            )
        except Exception as e:
            res = error_response(e, str(e))
            return http.Response(
                json.dumps(res),
                status=200,
                mimetype='application/json'
            )


# 13)     Generic Model - Specific ID - Get Specific Field

    @http.route(
        '/api/<string:model>/<int:rec_id>/<string:field>',
        type='http', auth="user", methods=['GET'], csrf=False)
    def get_binary_record(self, model,  rec_id, field, **post):
        try:
            request.env[model]
        except KeyError as e:
            msg = "The model `%s` does not exist." % model
            res = error_response(e, msg)
            return http.Response(
                json.dumps(res),
                status=200,
                mimetype='application/json'
            )

        rec = request.env[model].browse(rec_id).ensure_one()
        if rec.exists():
            src = getattr(rec, field).decode("utf-8")
        else:
            src = False
        return http.Response(
            src
        )



#OUR CODE STARTS------------------>>>>>>

#1) Sale Order Confirm and Do Draft is Generated

    @http.route('/sale_confirm/order_confirm/<int:id>', type='json', auth="user", methods=['POST'], csrf=False)
    def sale_model_data_confirm(self, id, **post):
        # request.session.authenticate("qne_api", "admin", 'admin')
        # print()
        try:
            order_id = request.env["sale.order"].search([('id', '=', id)])
            order_id.ensure_one()
            order_id.action_confirm()
            
        except Exception as error:
            return {'error': error,
                    'success': 0,
                    'ids': False}
        return {'error': False,
                'success': 1,
                'delivery_ids': order_id.ids}


    @http.route('/sale_cancel/order_cancel/<int:id>', type='json', auth="user", methods=['POST'], csrf=False)
    def sale_model_data_cancel(self, id, **post):
        try:
            order_id = request.env["sale.order"].search([('id', '=', id)])
            order_id.update_qty_server_cancel_order()
        except Exception as error:
            return {'error': error,
                    'success': 0,
                    'ids': False}
        return {'error': False,
            'success': 1,
            'delivery_ids': order_id.ids}

#2) Delivery Order is Validated with Updated Quantities

    @http.route('/do/validate/<int:id>', type='json', auth="user", methods=['PUT'], csrf=False)
    def do_model_data(self, id, data, **post):
        # -----------------API BODY---------------------
        # {"jsonrpc": "2.0", "params": {
        #     "data":
                # [{"product_id": 17, "qty": 3.0}, {"product_id": 18, "qty": 2.0}]}}
        #-------------------------------------------------------------------
        # request.session.authenticate("qne_api", "admin", 'admin')
        # print()
        try:
            order_id = request.env["sale.order"].search([('id', '=', id)])
            # order_id.action_confirm()
            picking_ids = order_id.picking_ids
            #pickings_not_to_backorder = self.browse(self.env.context['picking_ids_not_to_backorder'])
            for picking in picking_ids:
                if picking.state not in ["done", "cancel"]:
                    if 'scheduled_date' in post.keys():
                        picking.scheduled_date = post['scheduled_date']
                    # picking.action_assign()
                    # picking.action_confirm()
                    for mv in picking.move_ids_without_package:
                        for i in  data:

                            bom_id = request.env['mrp.bom'].search([('product_id', '=', i["product_id"])])
                            if bom_id:
                                for product_in_bil in bom_id.bom_line_ids:

                                    if mv.product_id.id == product_in_bil.product_id.id:
                                        for b in product_in_bil:
                                            mv.quantity_done = i['qty'] * b.product_qty
                            else:
                                if mv.product_id.id == i["product_id"]:
                                    print("yasir")
                                    mv.quantity_done = i['qty']
                        # print("=============")
                        # mv.product_id = data[0]['product_id']
                        # mv.quantity_done = data[0]['qty']
                        # print(mv.quantity_done)
                    picking.button_validate_api()
                    #pickings_not_to_backorder = picking.browse(self.env.context['picking_ids_not_to_backorder'])
                    #pickings_to_backorder = picking - pickings_not_to_backorder
                    #pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
                    #pickings_to_backorder.with_context(cancel_backorder=False)._action_done()
                    #pickings_not_to_backorder = self.browse(self.env.context['picking_ids_not_to_backorder'])
                   # pickings_not_to_backorder.with_context(cancel_backorder=True).action_done()
           #         picking.button_validate()
                    #picking.button_validate().backorder_id.process_cancel_backorder()
                   # picking.backorder_id.process_cancel_backorder()
        except Exception as error:
            return {'error': error,
                    'success': 0,
                    'ids': False}
        return {'error': False,
                'success': 1,
                'delivery_ids': order_id.ids}

#3 - [8:03 pm, 27/04/2022] sundus odoo consultant: Deliver order validate invoice post ki ek API banani hai 
# Lkn is API ko banaty hoye ek condition ye bhi lagegi ky quantities Jo vendor bill py jayegi Billing ke lye wo done quantities wali hongi reserved quantities NHi hongi
# [8:04 pm, 27/04/2022] sundus odoo consultant: Mtlb ky order wali quantities NHi blky Jo actual sales or done quantities Hain wo vendor ky bill py jayegi


#3) Delivery Order is Validated with Updated Quantities


    @http.route('/create/invoice/<int:id>', type='json', auth="user", methods=['POST'], csrf=False)
    def create_invoice(self, id, **post):
        try:
            partnerId = None
            invoice_date = None
            register_payment_journal_id = None
            order_id = request.env["sale.order"].search([('id', '=', id)])
            if 'customer_data' in post.keys():
                partnerId = self.get_or_create_customer_inv(post)
            if 'register_payment_journal_id' in post.keys():
                register_payment_journal_id = int(post['register_payment_journal_id'])
            if 'invoice_date' in post.keys():
                invoice_date = post['invoice_date']
            invoice_id = order_id.create_invoice_api(partnerId, register_payment_journal_id, invoice_date)
            print(invoice_id)
        except Exception as error:
            return {'error':error,
                    'success':0,
                    'ids':False}
        return {'error':False,
                    'success':1,
                    'invoice_id':invoice_id}



    def get_or_create_customer_inv(self,post):
        customer = post['customer_data']
        partner_id = request.env['res.partner'].search([("premier_cust_id", "=", customer["premier_cust_id"])])
        if partner_id:
            partnerId = partner_id.id
        else:
            partner_id = request.env["res.partner"].create([customer])
            partnerId = partner_id.id
        return partnerId
