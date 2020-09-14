# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
import os.path


class ProductMediaExportMapper(Component):
    _inherit = 'magento.product.media.export.mapper'

    @mapping
    def get_content(self, record):
        if not record.type == 'product_image_ids':
            return super(ProductMediaExportMapper, self).get_content(record)
        if not record.odoo_id.image:
            raise Exception('Missing image content on image %s on product %s, template: %s', record.odoo_id, record.magento_product_id, record.magento_product_tmpl_id)
        return {'content': {
            'base64_encoded_data': record.odoo_id.image.decode('ascii'),
            'type': record.mimetype,
            'name': os.path.basename(record.file),
        }}
