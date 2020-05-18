# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

import xmlrpc.client

from odoo import _
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class MagentoStockItemExporter(Component):
    _inherit = 'magento.stock.item.exporter'
    _apply_on = ['magento.stock.item']

    def _update(self, data, storeview_code=None):
        if not self.binding.magento_warehouse_id.mw_type == 'msi':
            return super(MagentoStockItemExporter, self)._update(data, storeview_code)
        assert self.external_id
        # special check on data before export
        self._validate_update_data(data)
        (source_code, sku) = self.external_id.split('|')
        return self.backend_adapter.msi_write(source_code, sku, data['qty'])
