# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from odoo.addons.component.core import Component
from odoo.addons.connector.exception import MappingError
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo import tools

_logger = logging.getLogger(__name__)


class AttributeValueImporter(Component):
    _name = 'magento.product.attribute.value.import'
    _inherit = ['magento.importer']
    _apply_on = ['magento.product.attribute.value']
    _magento_id_field = 'external_id'

    def _create_data(self, map_record, **kwargs):
        return map_record.values(for_create=True, magento_attribute=self.magento_attribute)

    def _update_data(self, map_record, **kwargs):
        return map_record.values(magento_attribute=self.magento_attribute, **kwargs)

    def run(self, external_id, **kwargs):
        self.magento_attribute = kwargs.get("magento_attribute", None)
        return super(AttributeValueImporter, self).run(external_id, *kwargs)


class AttributeValueImportMapper(Component):
    _name = 'magento.product.attribute.value.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.product.attribute.value']

    direct = [
        ('label', 'label'), # Was name
    ]

    @mapping
    def code_and_default_values(self, record):
        return {
            'code': record['value'],
            'main_text_code': record['value']
        }
    
    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @only_create
    @mapping
    def odoo_id(self, record):
        odoo_value = self.env['product.attribute.value'].search([
            ('name', '=', record.get('label')),
            ('attribute_id', '=', self.options.magento_attribute.odoo_id.id)
        ])
        return {
            'odoo_id': odoo_value.id if odoo_value and len(odoo_value)==1 else None,
            'magento_attribute_id': self.options.magento_attribute.id,
        }

    '''
    def finalize(self, map_record, values):
        if map_record.parent:
            # Generate external_id as attribute_id and code
            values.update({
                'external_id': "%s_%s" % (str(map_record.parent.source.get('attribute_id')), tools.ustr(values.get('code'))),
            })
            # Fetch odoo attribute id - is required
            attribute_binder = self.binder_for(model='magento.product.attribute')
            magento_attribute = attribute_binder.to_internal(map_record.parent.source.get('attribute_id'), unwrap=False)
            if magento_attribute:
                # Set odoo attribute id if it does already exists
                values.update({
                    'attribute_id': magento_attribute.odoo_id.id
                })
            # Search for existing entry
            binder = self.binder_for(model='magento.product.attribute.value')
            magento_value = binder.to_internal(values['external_id'], unwrap=False)
            if magento_value:
                values.update({'id': magento_value.id})
                return values
            # Do also search for an existing odoo value with the same name
            odoo_value = self.env['product.attribute.value'].search([
                ('name', '=', values.get('name')),
                ('attribute_id', '=', magento_attribute.odoo_id.id)
            ])
            if odoo_value:
                # By passing the odoo id it will not try to create a new odoo value !
                values.update({'odoo_id': odoo_value.id})
        return values
    '''