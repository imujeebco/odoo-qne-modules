from odoo import api, fields, models,exceptions
class SaleOrder(models.Model):
    _inherit = "sale.order"
    register_payment_journal_id = fields.Many2one('account.journal',default=False)

    def action_confirm(self):
        imediate_obj = self.env['stock.immediate.transfer']
        old_so_date = self.date_order
        res = super(SaleOrder,self).action_confirm()
        self.write({
            'date_order':old_so_date,
            'effective_date':old_so_date,
            'expected_date':old_so_date
        })

        for order in self:

            warehouse = order.warehouse_id
            for picking in self.picking_ids:
                picking.scheduled_date = old_so_date
                picking.date_done = old_so_date


            if warehouse.is_delivery_set_to_done and order.picking_ids:
                for picking in self.picking_ids:
                    picking.action_assign()
                    picking.action_confirm()
                    for mv in picking.move_ids_without_package:
                        mv.quantity_done = mv.product_uom_qty
                    picking.button_validate()
                    picking.date_done = old_so_date

            if warehouse.create_invoice and not order.invoice_ids:
                order._create_invoices()

            if warehouse.validate_invoice and order.invoice_ids:
                for invoice in order.invoice_ids:
                    invoice.invoice_date = old_so_date
                    invoice.date = old_so_date
                    invoice.action_post()


                    # Register payment if journal is attached on SO
                    if order.register_payment_journal_id:
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



        return res  
