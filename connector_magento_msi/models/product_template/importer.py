# -*- coding: utf-8 -*-
# Copyright 2020 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class ProductTemplateImporter(Component):
    _inherit = 'magento.product.template.importer'

    def _import_stock(self, binding):
        super(ProductTemplateImporter, self)._import_stock(binding)
        for source in self.env['magento.stock.warehouse'].search([
            ('mw_type', '=', 'msi'),
            ('backend_id', '=', binding.backend_id.id),
        ]):
            stock_importer = self.component(usage='record.importer',
                                            model_name='magento.stock.item')
            stock_importer.run("%s|%s" % (source.external_id, self.magento_record['sku'], ))
