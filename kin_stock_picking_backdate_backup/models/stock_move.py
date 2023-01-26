from odoo import models, api, fields, _
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _set_backdate(self, backdate):
        """
        set backdate for done stock moves and their conresponding done stock move lines
        """
        stock_moves = self.filtered(lambda x: x.state == 'done')
        org_price_unit = self._context.get('org_price_unit', False)
        for move in stock_moves:
            move.write({'date': backdate, 'price_unit': org_price_unit[move.id]})

        move_line_ids = self.mapped('move_line_ids').filtered(lambda x: x.state == 'done')
        if move_line_ids:
            move_line_ids.write({'date': backdate})


    def _action_done(self, cancel_backorder=False):
        self.env.context = dict(self.env.context)
        org_value = self._context.get('org_value', False)
        if org_value:
            pass
        else:
            org_qty = {}
            org_price_unit = {}
            org_value = {}
            for record in self:
                move_id = record.id
                org_qty[move_id] = record.product_qty
                org_price_unit[move_id] = record.price_unit
                org_value[move_id] = org_qty[move_id] * org_price_unit[move_id]

            self.env.context.update({
                'org_qty': org_qty,
                'org_price_unit': org_price_unit,
                'org_value': org_value
            })

        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        manual_validate_date_time = self._context.get('manual_validate_date_time', False)
        if manual_validate_date_time:
            # print(org_price_unit)
            # raise UserError(_("bisa kin price unit: " + str(org_price_unit)))
            self._set_backdate(manual_validate_date_time)
        return res

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id,
                                  cost):
        self.ensure_one()
        AccountMove = self.env['account.move'].with_context(default_journal_id=journal_id)

        move_lines = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, description)
        if move_lines:
            # print('move_lines:')
            # print(move_lines)
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            new_account_move = AccountMove.sudo().create({
                'journal_id': journal_id,
                'line_ids': move_lines,
                'date': date,
                'ref': description,
                'stock_move_id': self.id,
                'stock_valuation_layer_ids': [(6, None, [svl_id])],
                'move_type': 'entry',
            })

            manual_validate_date_time = self._context.get('manual_validate_date_time', False)
            picking_type_code = self._context.get('picking_type_code', False)
            org_value = self._context.get('org_value', False)
            if manual_validate_date_time and picking_type_code == 'incoming':
                debit_line_ids = new_account_move.line_ids.filtered(lambda x: x.credit == 0)
                if debit_line_ids:
                    self.env.cr.execute("""
                        UPDATE account_move_line
                        SET debit=%s,
                        balance=%s
                        WHERE id in %s
                        """, (
                        org_value[self.id],
                        org_value[self.id],
                        tuple(debit_line_ids.ids)
                        )
                    )

                credit_line_ids = new_account_move.line_ids.filtered(lambda x: x.debit == 0)
                if credit_line_ids:
                    self.env.cr.execute("""
                        UPDATE account_move_line
                        SET credit=%s,
                        balance=-%s
                        WHERE id in %s
                        """, (
                        org_value[self.id],
                        org_value[self.id],
                        tuple(credit_line_ids.ids)
                        )
                    )

            new_account_move._post()