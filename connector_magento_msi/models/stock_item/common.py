# -*- coding: utf-8 -*-
# Copyright 2020 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import xmlrpc.client
from odoo import api, models, fields
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.queue_job.job import identity_exact

_logger = logging.getLogger(__name__)


class MagentoStockItemAdapter(Component):
    _inherit = 'magento.stock.item.adapter'

    def msi_read(self, source_code, sku):
        params = self.get_searchCriteria({
            'sku': {'eq': sku},
            'source_code': {'eq': source_code},
        })
        res = self._call('inventory/source-items',params)
        return res['items'][0] if len(res['items'])>0 else None

    def msi_write(self, source_code, sku, qty):
        self._call('inventory/source-items', {
          "sourceItems": [{
            "source_code": source_code,
            "sku": sku,
            "quantity": qty,
            "status": 1
          }]
        }, http_method='post')
        return True
