# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

class MagentoStockItemImporter(Component):
    _inherit = 'magento.stock.item.importer'

    def _get_magento_data(self, binding=None):
        """ Return the raw Magento data for ``self.external_id`` """
        if '|' in self.external_id:
            (source_code, sku) = self.external_id.split('|')
            return self.backend_adapter.msi_read(source_code, sku)
        else:
            return super(MagentoStockItemImporter, self)._get_magento_data(binding)

    def _must_skip(self):
        return False if self.magento_record else True


class MagentoStockItemImportMapper(Component):
    _inherit = 'magento.stock.item.import.mapper'

    @mapping
    @only_create
    def magento_product_binding_id(self, record):
        if 'sku' not in record:
            return super(MagentoStockItemImportMapper, self).magento_product_binding_id(record)
        binder = self.binder_for('magento.product.product')
        mproduct = binder.to_internal(record['sku'], unwrap=False)
        if mproduct:
            return {
                'magento_product_binding_id': mproduct.id,
                'magento_product_template_binding_id': None,
                'product_type': 'product',
            }
        binder = self.binder_for('magento.product.template')
        mproduct = binder.to_internal(record['sku'], unwrap=False)
        if mproduct:
            return {
                'magento_product_template_binding_id': mproduct.id,
                'magento_product_binding_id': None,
                'product_type': 'configurable',
            }

    @mapping
    @only_create
    def warehouse_id(self, record):
        if 'source_code' not in record:
            return super(MagentoStockItemImportMapper, self).warehouse_id(record)
        binder = self.binder_for('magento.stock.warehouse')
        mwarehouse = binder.to_internal(record['source_code'], unwrap=False)
        return {
            'magento_warehouse_id': mwarehouse.id,
        }
