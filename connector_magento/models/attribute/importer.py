# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
import uuid
from odoo import tools

_logger = logging.getLogger(__name__)


class AttributeBatchImporter(Component):
    """ Import the Magento Products attributes.

    For every product attributes in the list, a delayed job is created.
    Import from a date
    """
    _name = 'magento.product.attribute.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.product.attribute']
    

class AttributeImporter(Component):
    _name = 'magento.product.attribute.import'
    _inherit = ['magento.importer']
    _apply_on = ['magento.product.attribute']
    _magento_id_field = 'attribute_id'

    def _after_import(self, binding):
        record = self.magento_record
        importer = self.component(
            usage='record.importer',
            model_name='magento.product.attribute.value'
        )
        # Do import attribute values here
        for i in range(len(record['options'])):
            value = record['options'][i]
            if not value['value']:
                continue
            value['external_id'] = "%s_%s" % (str(record.get('attribute_id')), tools.ustr(value.get('value')))
            importer.run(value, magento_attribute=binding)

    def _before_import(self):
        record = self.magento_record
        # Check for duplicate values here
        existing_values = []
        existing_names = []
        for i in range(len(record['options'])):
            value = record['options'][i]
            if value['value'] in existing_values:
                raise Exception('Value %s is a duplicate in %s' % (value['value'], record['default_frontend_label']))
            existing_values.append(value['value'])
            if value['label'] in existing_names and self.backend_record.rename_duplicate_values:
                self.magento_record['options'][i]['label'] = "%s (%s)" % (value['label'], str(uuid.uuid4()))
            elif value['label'] in existing_names and not self.backend_record.rename_duplicate_values:
                raise Exception('Value %s is a duplicate in %s' % (value['label'], record['default_frontend_label']))
            existing_names.append(value['label'])


    def _update(self, binding, data):
        """ Update an OpenERP record """
        # special check on data before import
        self._validate_data(data)
        binding.with_context(connector_no_export=True).write(data)
        _logger.debug('%d updated from magento %s', binding, self.external_id)
        # Disabled for now - should be configurable using backend option
        '''
        record = self.magento_record
        values = [r['value'] for r in record['options']]
        _logger.info("Got values from magento: %s", values)
        odoo_magento_values = self.env['magento.product.attribute.value'].search([
            ('magento_attribute_id', '=', binding.id),
            ('code', 'not in', values),
        ])
        _logger.info("Got following odoo magento values %s to delete: %r", [
            ('magento_attribute_id', '=', binding.id),
            ('code', 'not in', values),
        ], odoo_magento_values)
        odoo_magento_values.with_context(connector_no_export=True).unlink()
        '''
        return


class AttributeImportMapper(Component):
    _name = 'magento.product.attribute.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.product.attribute']

    direct = [
              ('attribute_code', 'attribute_code'),
              ('attribute_id', 'attribute_id'),
              ('attribute_id', 'external_id'),
              ('frontend_input', 'frontend_input')]
    
    @only_create
    @mapping
    def get_att_id(self, record):
        # Check if we want to always create new odoo attributes
        if self.backend_record.always_create_new_attributes:
            return {}
        # Else search for existing attribute
        att_id = self.env['product.attribute'].search([
            ('name', '=ilike', self._get_name(record)['name'])
        ], limit=1)
        if att_id:
            return {'odoo_id': att_id.id}
        return {}
    
    @mapping
    def _get_name(self, record):
        name = record['attribute_code']
        if 'default_frontend_label' in record and record['default_frontend_label']:
            name = record['default_frontend_label'] 
        return {'name': name}
    
    @only_create
    @mapping
    def create_variant(self, record):
        # Is by default not set - will get set as soon as this attribute appears in a configureable product
        return

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}
