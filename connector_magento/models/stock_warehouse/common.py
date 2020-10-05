# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpc.client
from odoo import api, models, fields
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component
from odoo import tools

_logger = logging.getLogger(__name__)


class MagentoStockWarehouse(models.Model):
    _name = 'magento.stock.warehouse'
    _inherit = 'magento.binding'
    _inherits = {'stock.warehouse': 'odoo_id'}
    _description = 'Magento Warehouse'

    odoo_id = fields.Many2one(comodel_name='stock.warehouse',
                              string='Warehouse',
                              required=True,
                              ondelete='cascade')
    location_id = fields.Many2one(comodel_name='stock.location',
                                  string='Location',
                                  ondelete='cascade')
    quantity_field = fields.Selection([
        ('qty_available', 'Available Quantity'),
        ('virtual_available', 'Forecast quantity')
    ], string='Field use for quantity update', required=True, default='virtual_available')
    calculation_method = fields.Selection([
        ('real', 'Use Quantity Field'),
        ('fix', 'Use Fixed Quantity'),
    ], default='real', string='Calculation Method')
    fixed_quantity = fields.Float('Fixed Quantity', default=0.0)
    magento_stock_item_ids = fields.One2many(
        comodel_name='magento.stock.item',
        inverse_name='magento_warehouse_id',
        string="Magento Stock Items",
    )

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_stock(self):
        """ Export the the current stock items """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            # TODO:
            exporter = work.component(usage='record.exporter')
            return exporter.run(self)

    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def import_stock(self):
        """ Export a complete or partial delivery order. """
        # with_tracking is True to keep a backward compatibility (jobs that
        # are pending and miss this argument will behave the same, but
        # it should be called with True only if the carrier_tracking_ref
        # is True when the job is created.
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            # TODO
            pass


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.stock.warehouse',
        inverse_name='odoo_id',
        string="Magento Bindings",
    )


class MagentoStockWarehouseBinder(Component):
    _name = 'magento.stock.warehouse.binder'
    _inherit = 'magento.binder'
    _apply_on = 'magento.stock.warehouse'
    _external_field = 'external_id'

    def to_internal(self, external_id, unwrap=False, external_field=None):
        """
        I have no idea why this is necessary - but under some conditions the access rights did not returned the binding
        """
        if not external_field:
            bindings = self.model.sudo().with_context(active_test=False).search(
                [(self._external_field, '=', tools.ustr(external_id)),
                 (self._backend_field, '=', self.backend_record.id)]
            )
        else:
            bindings = self.model.sudo().with_context(active_test=False).search(
                [(external_field, '=', tools.ustr(external_id)),
                 (self._backend_field, '=', self.backend_record.id)]
            )
        if not bindings:
            if unwrap:
                return self.model.sudo().browse()[self._odoo_field]
            return self.model.browse()
        if len(bindings) > 1:
            _logger.error("Got %s bindings for %s with value %s", len(bindings), external_field, external_id)
        bindings.ensure_one()
        if unwrap:
            bindings = bindings[self._odoo_field]
        return bindings
