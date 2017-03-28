# -*- coding: utf-8 -*-
import logging
from openerp import models, fields
from openerp.addons.connector.unit.mapper import (mapping,
                                                  only_create,
                                                  ImportMapper
                                                  )
from openerp.addons.magentoerpconnect.unit.mapper import MagentoImportMapper
from .unit.backend_adapter import GenericAdapter
from .unit.import_synchronizer import MagentoImporter
from .backend import magento

_logger = logging.getLogger(__name__)


class ProductImage(models.Model):
    _inherit = 'base_multi_image.image'

    magento_bind_ids = fields.One2many(
        comodel_name='magento.media',
        inverse_name='openerp_id',
        string="Magento Media",
    )


class MagentoMedia(models.Model):
    _name = 'magento.media'
    _inherit = 'magento.binding'
    _inherits = {'base_multi_image.image': 'openerp_id'}
    _description = 'Magento Media'

    sku = fields.Char("Product Code")
    openerp_id = fields.Many2one(comodel_name='base_multi_image.image',
                                 string='Product Image',
                                 required=True,
                                 ondelete='cascade')


@magento
class MagentoMediaAdapter(GenericAdapter):
    _model_name = 'magento.media'
    _magento_model = 'products/{sku}/media'
    _search_path = 'sets/list'
    _admin_path = '/{model}/edit/id/{id}'


    def create(self, data):
        """ Create a record on the external system """
        sku = data['sku']
        del data['sku']
        return self.magento.post('products/%s/media' % sku, {
            'entry': data
        })


@magento
class MagentoMediaImportMapper(MagentoImportMapper):
    _model_name = 'magento.media'

    # TODO
    direct = [
        ('attribute_set_name', 'name'),
    ]

@magento
class MagentoMediaImporter(MagentoImporter):
    """ Import one Magento Store (create a sale.shop via _inherits) """
    _model_name = ['magento.media',
                   ]
