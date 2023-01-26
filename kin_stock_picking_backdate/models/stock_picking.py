from odoo import models, api, _
from datetime import date

from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        if self.scheduled_date:
            self.env.context = dict(self.env.context)
            scheduled_date = self.scheduled_date
            accounting_date = scheduled_date.date()
            self.env.context.update({
                'manual_validate_date_time': scheduled_date,
                'picking_type_code': self.picking_type_id.code,
                'force_period_date': accounting_date
            })
            res = super(StockPicking, self)._action_done()

            manual_validate_date_time = self._context.get('manual_validate_date_time', False)
            if manual_validate_date_time:
                self.filtered(lambda x: x.state == 'done').write({'date_done': manual_validate_date_time})
            return False