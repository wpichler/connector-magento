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


class AttributeSet(models.Model):
    _name = 'attribute.set'

    name = fields.Char(string="Name")
    attribute_ids = fields.Many2many('product.attribute')
    magento_bind_ids = fields.One2many(
        comodel_name='magento.attribute.set',
        inverse_name='openerp_id',
        string="Magento Bindings",
    )


class MagentoAttributeSet(models.Model):
    _name = 'magento.attribute.set'
    _inherit = 'magento.binding'
    _inherits = {'attribute.set': 'openerp_id'}
    _description = 'Magento Attribute Set'

    openerp_id = fields.Many2one(comodel_name='attribute.set',
                                 string='Attribute Set',
                                 required=True,
                                 ondelete='cascade')
    magento_parent_id = fields.Many2one(
        comodel_name='magento.attribute.set',
        string='Magento Parent Attribute Set',
        ondelete='cascade',
    )
    magento_child_ids = fields.One2many(
        comodel_name='magento.product.category',
        inverse_name='magento_parent_id',
        string='Magento Child Categories',
    )

@magento
class ProductAttributeSetAdapter(GenericAdapter):
    _model_name = 'magento.attribute.set'
    _magento_model = 'products/attribute-sets'
    _search_path = 'sets/list'
    _admin_path = '/{model}/edit/id/{id}'


@magento
class AttributeSetImportMapper(MagentoImportMapper):
    _model_name = 'magento.attribute.set'

    direct = [
        ('attribute_set_name', 'name'),
    ]

@magento
class AttributeSetImporter(MagentoImporter):
    """ Import one Magento Store (create a sale.shop via _inherits) """
    _model_name = ['magento.attribute.set',
                   ]
