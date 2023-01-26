from odoo import models, api, fields


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, in_date=None):
        """ Increase or decrease `reserved_quantity` of a set of quants for a given set of
        product_id/location_id/lot_id/package_id/owner_id.

        :param product_id:
        :param location_id:
        :param quantity:
        :param lot_id:
        :param package_id:
        :param owner_id:
        :param datetime in_date: Should only be passed when calls to this method are done in
                                 order to move a quant. When creating a tracked quant, the
                                 manual_validate_date_time or the current datetime will be used.
        :return: tuple (available_quantity, in_date as a datetime)
        """
        if not in_date:
            manual_validate_date_time = self._context.get('manual_validate_date_time', False)
            if manual_validate_date_time:
                in_date = fields.Datetime.from_string(manual_validate_date_time)
        return super(StockQuant, self)._update_available_quantity(product_id, location_id, quantity, lot_id=lot_id, package_id=package_id, owner_id=owner_id, in_date=in_date)
