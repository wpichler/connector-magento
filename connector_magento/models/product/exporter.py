# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import odoo
from datetime import datetime

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from slugify import slugify
from odoo.addons.connector_magento.components.backend_adapter import MAGENTO_DATETIME_FORMAT
import magic
import base64
import logging

_logger = logging.getLogger(__name__)


class ProductProductExporterPrice(Component):
    _name = 'magento.product.product.exporter.price'
    _inherit = 'magento.exporter'
    _usage = 'record.exporter.price'
    _apply_on = ['magento.product.product']

    def _run(self, fields=None):
        assert self.binding
        if not self.binding.external_id:
            return
        product = self.binding.odoo_id
        # We do have to update the price per website
        websites = self.binding.website_ids
        if not websites:
            websites = self.env['magento.website'].search([('backend_id', '=', self.binding.backend_id.id)])
        for website in websites:
            price = product.with_context(pricelist=website.pricelist_id.id).price
            if not website.store_ids or not website.store_ids[0].storeview_ids:
                continue
            storeview = website.store_ids[0].storeview_ids[0]
            self.backend_adapter.update_price(self.binding.external_id, storeview.code, price)
