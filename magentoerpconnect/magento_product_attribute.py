# -*- coding: utf-8 -*-
import logging
from openerp.addons.magentoerpconnect.unit.mapper import mapping, MagentoImportMapper
from openerp import models, fields, api, _
from openerp.addons.connector.queue.job import job

from .unit.backend_adapter import (GenericAdapter,
                                   MAGENTO_DATETIME_FORMAT,
                                   )
from .unit.import_synchronizer import (DelayedBatchImporter,
                                       MagentoImporter,
                                       )
from .unit.mapper import normalize_datetime
from .exception import OrderImportRuleRetry
from .backend import magento
from .connector import get_environment
from .partner import PartnerImportMapper
from .backend import magento

_logger = logging.getLogger(__name__)


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    attribute_code = fields.Char("Attribute Code")
    magento_bind_ids = fields.One2many(
        comodel_name='magento.product.attribute',
        inverse_name='openerp_id',
        string="Magento Bindings",
    )

class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    magento_value = fields.Char("Value Code")



class MagentoProductAttribute(models.Model):
    _name = 'magento.product.attribute'
    _inherit = 'magento.binding'
    _inherits = {'product.attribute': 'openerp_id'}
    _description = 'Magento Product Attributes'

    openerp_id = fields.Many2one(comodel_name='product.attribute',
                                 string='Product Attributes',
                                 required=True,
                                 ondelete='cascade')


@magento
class ProductAttributeAdapter(GenericAdapter):
    _model_name = 'magento.product.attribute'
    _magento_model = 'products/attributes'
    _admin_path = '/{model}/edit/id/{id}'
    _id_field = 'attribute_id'

@magento
class AttributeImportMapper(MagentoImportMapper):
    _model_name = 'magento.product.attribute'

    direct = [
        ('default_frontend_label', 'name'),
        ('attribute_code', 'attribute_code'),
    ]

    @mapping
    def value_ids(self, record):
        values = []
        for attribute_value in record['options']:
            new_value_dict = {
                'name': attribute_value['label'],
                'magento_value': attribute_value['value'],
            }
            values.append((0, 0, new_value_dict))
        return {'value_ids': values}


@magento
class AttributeImporter(DelayedBatchImporter):
    """ Import one Magento Store (create a sale.shop via _inherits) """
    _model_name = ['magento.product.attribute']

    def run(self, filters=None):
        """ Run the synchronization """
        record_ids = self.backend_adapter.search(filters)
        _logger.info('search for magento attrtibutes %s returned %s',
                     filters, record_ids)
        for record_id in record_ids:
            self._import_record(record_id)


@job(default_channel='root.magento')
def product_attribute_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare a batch import of records from Magento """
    if filters is None:
        filters = {}
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(AttributeImporter)
    importer.run(filters)


@magento
class AttributeSetImporter(MagentoImporter):
    """ Import one Magento Store (create a sale.shop via _inherits) """
    _model_name = ['magento.product.attribute',
                   ]
