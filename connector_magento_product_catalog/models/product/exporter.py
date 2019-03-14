# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import xmlrpclib

import odoo
from datetime import datetime

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import NothingToDoJob
from odoo.addons.connector.unit.mapper import mapping
from odoo.addons.queue_job.job import identity_exact

from odoo.addons.connector_magento.components.backend_adapter import MAGENTO_DATETIME_FORMAT


class ProductDefinitionExporter(Component):
    _name = 'magento.product.product.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.product']
    #_usage = 'product.definition.exporter'
    
    
    def _should_import(self):
        """ Before the export, compare the update date
        in Magento and the last sync date in Odoo,
        Regarding the product_synchro_strategy Choose 
        to whether the import or the export is necessary
        """
        assert self.binding
        if not self.external_id:
            return False
        if self.backend_record.product_synchro_strategy == 'odoo_first':
            return False
        sync = self.binding.sync_date
        if not sync:
            return True
        record = self.backend_adapter.read(self.external_id,
                                           attributes=['updated_at'])
        if not record['updated_at']:
            # in rare case it can be empty, in doubt, import it
            return True
        sync_date = odoo.fields.Datetime.from_string(sync)
        magento_date = datetime.strptime(record['updated_at'],
                                         MAGENTO_DATETIME_FORMAT)
        return sync_date < magento_date

    
    
    def _delay_import(self):
        """ Schedule an import/export of the record.

        Adapt in the sub-classes when the model is not imported
        using ``import_record``.
        """
        # force is True because the sync_date will be more recent
        # so the import would be skipped
        assert self.external_id
        if self.backend_record.product_synchro_strategy == 'magento_first':
            self.binding.with_delay(identity_key=identity_exact).import_record(self.backend_record,
                                                self.external_id,
                                                force=True)

class ProductProductExportMapper(Component):
    _name = 'magento.product.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.product']

    direct = [
        ('name', 'name'),
        ('default_code', 'sku'),
        ('product_type', 'typeId'),
#         ('lst_price', 'price'),
    ]
    
    @mapping
    def get_extension_attributes(self, record):
        data = {}
        
        data.update(self.get_website_ids(record))
        data.update(self.category_ids(record))
        return {'extension_attributes': data}
    
    
    def get_website_ids(self, record):
        website_ids = [
                s.external_id for s in record.backend_id.website_ids
                ]
        return {'website_ids': website_ids}
    
    def category_ids(self, record):
        #TODO : Map categories from magento
        categ_vals = [
            {
              "position": 0,
              "category_id": record.categ_id.magento_bind_ids.external_id,
#               "extension_attributes": {}
          }
        ]
        for c in record.categ_ids:
            categ_vals.append({
              "position": 1,
              "category_id": c.magento_bind_ids.external_id,
#               "extension_attributes": {}
          })
        return {'category_links': categ_vals}
    
    
    @mapping
    def get_associated_configurable_product_id(self, record):
        
        return {}
    
    @mapping
    def get_storeview(self, record):
        
        return {}
    
    
    @mapping
    def weight(self, record):
        if record.weight:
            val = record.weight
        else:
            val = 0        
        return {'weight' : val}
        
    @mapping
    def attribute_set_id(self, record):
        if record.attribute_set_id:
            val = record.attribute_set_id.external_id
        else:
            # TODO: maybe turn it into defensive option
            # on the magento.backend
            val = 4
        return {'attributeSetId' : val}

    @mapping
    def names(self, record):
        return {}

    @mapping
    def get_common_attributes(self, record):
        """
        Collect attributes to prensent it regarding to
        https://devdocs.magento.com/swagger/index_20.html
        catalogProductRepositoryV1 / POST 
        """
        
        customAttributes = []
        magento_attribute_line_ids = record.magento_attribute_line_ids.filtered(
            lambda att: att.store_view_id.id == False \
             and (
                        att.attribute_text != False
                        or
                        att.attribute_select.id != False
                        or 
                        len(att.attribute_multiselect.ids) > 0
                    )
            
            )
        
        
        
        for values_id in magento_attribute_line_ids:
            """ Deal with Custom Attributes """            
            attributeCode = values_id.attribute_id.attribute_code
            value = values_id.attribute_text
            if values_id.magento_attribute_type == 'boolean':
                try:
                    value = int(values_id.attribute_text)
                except:
                    value = 0
            
            if values_id.magento_attribute_type in ['select',] and \
                    values_id.attribute_select.external_id != False:
                full_value = values_id.attribute_select.external_id
                value = full_value.split('_')[1]
            
            customAttributes.append({
                'attribute_code': attributeCode,
                'value': value
                })     
        
        for values_id in record.attribute_value_ids:
            """ Deal with Attributes in the 'variant' part of Odoo"""
            odoo_value_id = values_id.magento_bind_ids.filtered(
                lambda m: m.backend_id == record.backend_id)    
            attributeCode = odoo_value_id.magento_attribute_id.attribute_code
            value = odoo_value_id.external_id.split('_')[1]
            customAttributes.append({
                'attributeCode': attributeCode,
                'value': value
                })
        result = {'customAttributes': customAttributes}
        return result

    @mapping
    def price(self, record):
        price = record['lst_price']
        return {'price': price}
    
    
    @mapping
    def option_products(self, record):
        #TODO : Map optionnal products
        return {}


    @mapping
    def crossproducts(self, record):
        #TODO : Map cross products
        return {}

