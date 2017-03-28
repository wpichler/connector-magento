# -*- coding: utf-8 -*-
from openerp import models, fields
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ExportMapper)
from openerp.addons.magentoerpconnect.unit.delete_synchronizer import (
    MagentoDeleteSynchronizer)
from openerp.addons.magentoerpconnect.unit.export_synchronizer import (
    MagentoExporter)
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


@magento
class MagentoMediaExport(ConnectorUnit):
    _model_name = ['magento.media']


@magento
class MagentoMediaExportMapper(ExportMapper):
    _model_name = 'magento.media'

    @mapping
    def all(self, record):
        return {'label': record.name,
                # 'comments': record.comments,
                'file': record.name,
                'media_type': "image",
                'sku': record.sku,
                }

    @mapping
    def content(self, record):
        content_dict = {
            'base64_encoded_data': record.file_db_store,
            'type': record.mimetype if record.mimetype else "image/jpeg",
            'name': record.name,
        }
        return {'content': content_dict}

@magento
class MagentoMediaExporter(MagentoExporter):
    _model_name = ['magento.media']

    @property
    def mapper(self):
        if self._mapper is None:
            self._mapper = self.unit_for(
                MagentoMediaExportMapper)
        return self._mapper

    def _should_import(self):
        """Product are only edited on OpenERP Side"""
        return False

    def _create(self, data):
        """ Create the Magento record """
        self._validate_data(data)
        return self.backend_adapter.create(data)
