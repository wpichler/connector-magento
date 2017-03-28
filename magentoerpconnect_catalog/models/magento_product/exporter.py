# -*- coding: utf-8 -*-
#
#    Author: Damien Crier
#    Copyright 2015 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from openerp import models, fields
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ExportMapper)
from openerp.addons.magentoerpconnect.unit.delete_synchronizer import (
    MagentoDeleteSynchronizer)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    export_record, MagentoExporter)
from openerp.addons.magentoerpconnect.backend import magento
from openerp.addons.connector.exception import MappingError
from openerp.addons.connector.event import (
    on_record_write,
    on_record_create
    )
from openerp.addons.connector.connector import ConnectorUnit
import logging
_logger = logging.getLogger(__name__)
import openerp.addons.magentoerpconnect.consumer as magentoerpconnect
from openerp.addons.magentoerpconnect.product import ProductInventoryExporter
from openerp.addons.magentoerpconnect_catalog.models.magento_product.media import MagentoMediaExporter
from openerp.addons.magentoerpconnect.connector import get_environment

@on_record_write(model_names=[
    'magento.product.product',
])
def delay_export(session, model_name, record_id, vals=None):
    if vals.get('active', True) is False:
        magentoerpconnect.delay_unlink(session, model_name, record_id)


@magento
class ProductProductDeleteSynchronizer(MagentoDeleteSynchronizer):
    """ Partner deleter for Magento """
    _model_name = ['magento.product.product']


@magento
class ProductProductConfigurableExport(ConnectorUnit):
    _model_name = ['magento.product.product']

    def _export_configurable_link(self, binding):
        """ Export the link for the configurable product"""
        return


def delay_export2(session, model_name, record_id, vals=None):
    magentoerpconnect.delay_export(session, model_name,
                                   record_id, vals=vals)


@magento
class ProductProductExportMapper(ExportMapper):
    _model_name = 'magento.product.product'

    @mapping
    def all(self, record):
        return {'name': record.name,
                # 'description': record.description,
                'weight': record.weight,
                'price': record.list_price,
                'attribute_set_id': 4,
                'type_id': "simple"
                # 'short_description': record.description_sale,
                # 'type': record.product_type,
                # 'product_type': record.product_type,
                }

    @mapping
    def sku(self, record):
        sku = record.default_code
        if not sku:
            raise MappingError("The product attribute "
                               "default code cannot be empty.")
        return {'sku': sku}

    @mapping
    def updated_at(self, record):
        updated_at = record.updated_at
        if not updated_at:
            updated_at = '1970-01-01'
        return {'updated_at': updated_at}

    @mapping
    def created_at(self, record):
        created_at = record.created_at
        if not created_at:
            created_at = '1970-01-01'
        return {'created_at': created_at}

    """@mapping
    def website_ids(self, record):
        website_ids = []
        for website_id in record.website_ids:
            magento_id = website_id.magento_id
            website_ids.append(magento_id)
        return {'website_ids': website_ids}"""

    @mapping
    def status(self, record):
        return {'status': record.active and "1" or "2"}

    """@mapping
    def tax_class(self, record):
        binder = self.get_binder_for_model('magento.tax.class')
        tax_class_id = binder.to_backend(record.tax_class_id.id, wrap=True)
        return {'tax_class_id': str(tax_class_id)}

    @mapping
    def category(self, record):
        categ_ids = []
        if record.categ_id:
            for m_categ in record.categ_id.magento_bind_ids:
                if m_categ.backend_id.id == self.backend_record.id:
                    categ_ids.append(m_categ.magento_id)

        for categ in record.categ_ids:
            for m_categ in categ.magento_bind_ids:
                if m_categ.backend_id.id == self.backend_record.id:
                    categ_ids.append(m_categ.magento_id)
        return {'categories': categ_ids}"""


@magento
class ProductProductExporter(MagentoExporter):
    _model_name = ['magento.product.product']

    create_mode = False

    def _run(self, fields=None):
        self.create_mode = not(bool(self.magento_id))
        return super(ProductProductExporter, self)._run(fields=fields)

    @property
    def mapper(self):
        if self._mapper is None:
            self._mapper = self.unit_for(
                ProductProductExportMapper)
        return self._mapper

    def _should_import(self):
        """Product are only edited on OpenERP Side"""
        return False

    def _create(self, data):
        """ Create the Magento record """
        # special check on data before export
        # sku = data.pop('sku')
        # attr_set_id = data.pop('attrset')
        # product_type = data.pop('product_type')
        self._validate_data(data)
        return self.backend_adapter.create({'product': data})

    def _after_export(self):
        # translation export     NO
        # translation_exporter = self.unit_for(ProductProductTranslationExporter)
        # translation_exporter.run(self.binding_id)

        # if self.create_mode:
        #     inventory_exporter = self.unit_for(ProductInventoryExporter)
        #     inventory_exporter.run(self.binding_id, ['magento_qty'])
        if self.create_mode:
            binder = self.binder_for("magento.media")
            for image in self.binding_record.image_ids:
                magento_id = binder.to_backend(image.id, wrap=True)
                env = get_environment(self.session, "magento.media", self.backend_record.id)
                if not magento_id:
                    media_obj = self.env['magento.media'].create({
                        'openerp_id': image.id,
                        'backend_id': self.backend_record.id,
                        'sku': self.binding_record.code,
                    })
                    media_exporter = env.get_connector_unit(MagentoMediaExporter)
                    export_record(self.session, 'magento.media', media_obj.id)
                    magento_id = binder.to_backend(image.id, wrap=True)
                if not magento_id:
                    # well, this sucks
                    return  # TODO
                # media_exporter.run(media)


# @job(default_channel='root.magento')
# @related_action(action=unwrap_binding)
# def export_product(session, model_name, record_id):
#     """ Export a product. """
#     product = session.env[model_name].browse(record_id)
#     backend_id = product.backend_id.id
#     env = get_environment(session, model_name, backend_id)
#     product_exporter = env.get_connector_unit(ProductProductExporter)
#     return product_exporter.run(record_id)
