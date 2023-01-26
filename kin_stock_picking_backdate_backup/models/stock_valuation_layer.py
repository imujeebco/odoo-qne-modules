from datetime import datetime
from psycopg2.extensions import AsIs

from odoo import models, api, fields, _

from odoo.exceptions import UserError


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    org_create_date = fields.Datetime(string='Origin Create Date', readonly=True, help="A technical field to store original create date."
                                      " When backdate is applied, we changed the value of create_date so this field is important to store"
                                      " its original value.")

    @api.model_create_multi
    def create(self, vals_list):
        # print("vals_list:")
        # print(vals_list)
        now = fields.Datetime.now()
        for vals in vals_list:
            vals['org_create_date'] = now
        records = super(StockValuationLayer, self).create(vals_list)

        # force create_date and write_date with context's manual_validate_date_time
        manual_validate_date_time = self._context.get('manual_validate_date_time', False)
        org_price_unit = self._context.get('org_price_unit', False)
        org_value = self._context.get('org_value', False)
        if manual_validate_date_time and org_value:
            if isinstance(manual_validate_date_time, datetime):
                manual_validate_date_time = fields.Datetime.to_string(manual_validate_date_time)

            # we use SQL to write create_date and write_date
            # since Odoo does not allow changing those using its API
            if records:
                for svl in records:
                    move_id = svl.stock_move_id.id
                    if org_value[move_id] > 0:
                        self.env.cr.execute("""
                        UPDATE %s
                        SET create_date=%s, write_date=%s,
                        unit_cost=%s, value=%s
                        WHERE id = %s
                        """, (
                            AsIs(self._table),
                            manual_validate_date_time,
                            manual_validate_date_time,
                            org_price_unit[move_id],
                            org_value[move_id],
                            svl.id
                            )
                        )
                    else:
                        self.env.cr.execute("""
                            UPDATE %s
                            SET create_date=%s, write_date=%s
                            WHERE id = %s
                            """, (
                            AsIs(self._table),
                            manual_validate_date_time,
                            manual_validate_date_time,
                            svl.id
                            )
                        )

        return records

