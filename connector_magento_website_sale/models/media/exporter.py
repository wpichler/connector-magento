# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
import os.path
import logging

_logger = logging.getLogger(__name__)


class ProductMediaExportMapper(Component):
    _inherit = 'magento.product.media.export.mapper'

    @mapping
    @only_create
    def get_content(self, record):
        if record.type not in ['product_image_ids', 'attribute_image']:
            return super(ProductMediaExportMapper, self).get_content(record)
        if not record.odoo_id.image:
            raise Exception('Missing image content on image %s on product %s, template: %s', record.odoo_id, record.magento_product_id, record.magento_product_tmpl_id)
        return {'content': {
            'base64_encoded_data': record.odoo_id.image.decode('ascii'),
            'type': record.mimetype,
            'name': os.path.basename(record.file),
        }}

    @mapping
    def position(self, record):
        if record.odoo_id and record.odoo_id.sequence and record.odoo_id.sequence > 0:
            return {
                'position': record.odoo_id.sequence
            }
        if record.position is False:
            return {}
        return {
            'position': record.position
        }

    @mapping
    def get_types(self, record):
        itypes = []
        if record.type in ['product_image_ids', 'attribute_image'] and record.odoo_id and record.odoo_id.is_primary_image:
            itypes.append('image')
            itypes.append('small_image')
            itypes.append('thumbnail')
            itypes.append('swatch_image')
            return {'types': itypes}
        else:
            return super(ProductMediaExportMapper,self).get_types(record)
