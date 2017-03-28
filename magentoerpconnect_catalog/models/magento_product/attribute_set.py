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
class AttributeSetExportMapper(ExportMapper):
    _model_name = 'magento.attribute.set'

    @mapping
    def all(self, record):
        return {'name': record.name,}

    @mapping
    def attributeSet(self, record):
        return


@magento
class AttributeExportMapper(ExportMapper):
    _model_name = 'magento.attribute'

    @mapping
    def all(self, record):
        return {'name': record.name,}

    @mapping
    def options(self, record):
        return
