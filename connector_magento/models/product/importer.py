# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import requests
import base64
import sys

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError, InvalidDataError
from ...components.mapper import normalize_datetime
import html2text

_logger = logging.getLogger(__name__)


class ProductBatchImporter(Component):
    """ Import the Magento Products.

    For every product category in the list, a delayed job is created.
    Import from a date
    """
    _name = 'magento.product.product.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.product.product']

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        to_date = filters.pop('to_date', None)
        '''
        const VISIBILITY_NOT_VISIBLE    = 1;
        const VISIBILITY_IN_CATALOG     = 2;
        const VISIBILITY_IN_SEARCH      = 3;
        const VISIBILITY_BOTH           = 4;        
        '''
        filters['visibility'] = {'gt': 1}
        filters['type_id'] = {'eq': 'simple'}
        filters['status'] = {'eq': 1}
        external_ids = self.backend_adapter.search(filters,
                                                   from_date=from_date,
                                                   to_date=to_date)
        _logger.info('search for magento products %s returned %s',
                     filters, external_ids)
        for external_id in external_ids:
            self._import_record(external_id)


class ProductImportMapper(Component):
    _name = 'magento.product.product.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = ['magento.product.product']

    direct = [('price', 'magento_price'),
              ('weight', 'weight'),
              ('short_description', 'description_sale'),
              ('url_key', 'magento_url_key'),
              ('sku', 'external_id'),
              ('type_id', 'product_type'),
              ('id', 'magento_id'),
              (normalize_datetime('created_at'), 'created_at'),
              (normalize_datetime('updated_at'), 'updated_at'),
              ]

    @mapping
    def description(self, record):
        if 'description' in record:
            return {
                'description': html2text.html2text(record['description']),
            }

    @mapping
    def default_code_on_create(self, record):
        if self.backend_record.default_code_method == 'none':
            return
        if self.backend_record.default_code_method in ['update', 'overwrite']:
            return {
                'default_code': record['sku']
            }

    @mapping
    def default_code_on_update(self, record):
        if self.backend_record.default_code_method == 'none':
            return
        if self.backend_record.default_code_method == 'overwrite':
            return {
                'default_code': record['sku']
            }

    @mapping
    def magento_name(self, record):
        return {
            'magento_name': record['name']
        }

    @mapping
    def is_active(self, record):
        """Check if the product is active in Magento
        In Odoo set it always active - and map the status into magento_status
        2.0 REST API returns an integer, 1.x a string. """
        return {
            'active': True,
            'magento_status': str(record.get('status')),
        }

    @mapping
    def price(self, record):
        _logger.info("Do use price: %r", record.get('price', 0.0))
        return {
            'lst_price': record.get('price', 0.0),
        }

    @mapping
    def cost(self, record):
        return {
            'standard_price': record.get('cost', 0.0),
        }

    @mapping
    def product_name(self, record):
        return {
            'name': record.get('name', ''),
        }

    @mapping
    def tax_class_id(self, record):
        tax_attribute = [a for a in record['custom_attributes'] if a['attribute_code'] == 'tax_class_id']
        if not tax_attribute:
            return {}
        binder = self.binder_for('magento.account.tax')
        mtax = binder.to_internal(tax_attribute[0]['value'], unwrap=False)
        if int(tax_attribute[0]['value']) == 0:
            return {}
        if not mtax:
            raise MappingError("The tax class with the id %s "
                               "is not imported." %
                               tax_attribute[0]['value'])
        if not mtax.odoo_id:
            raise MappingError("The tax class with the id %s "
                               "is not mapped to an odoo tax." %
                               tax_attribute[0]['value'])
        data = {}
        if mtax.product_tax_ids:
            data.update({'taxes_id': [(6, 0, mtax.product_tax_ids.ids)]})
        else:
            data.update({'taxes_id': [(4, mtax.odoo_id.id)]})
        if mtax.product_tax_purchase_ids:
            data.update({'supplier_taxes_id': [(6, 0, mtax.product_tax_purchase_ids.ids)]})
        return data

    @mapping
    def attributes(self, record):
        attribute_binder = self.binder_for('magento.product.attribute')
        line_binder = self.binder_for('magento.template.attribute.line')
        value_binder = self.binder_for('magento.product.attribute.value')
        attribute_value_ids = [(5, )]
        attribute_line_ids = [(5, )]
        for attribute in record['custom_attributes']:
            mattribute = attribute_binder.to_internal(attribute['attribute_code'], unwrap=False, external_field='attribute_code')
            if mattribute.create_variant == 'no_variant':
                # We do ignore attributes which do not create a variant
                continue
            if not mattribute:
                raise MappingError("The product attribute %s is not imported." %
                                   mattribute.name)
            if str(attribute['value'])=='0' and mattribute.frontend_input == 'select':
                # We do ignore attributes with value 0 on select attribute types - magento seems to be buggy here
                continue
            mvalue = value_binder.to_internal("%s_%s" % (mattribute.attribute_id, str(attribute['value'])), unwrap=False)
            if not mvalue:
                raise MappingError("The product attribute value %s in attribute %s is not imported." %
                                   (str(attribute['value']), mattribute.name))
            attribute_value_ids.append((4, mvalue.odoo_id.id))
            # Also create an attribute.line.value entrie here
            attribute_line_ids.append((0, 0, {
                'attribute_id': mattribute.odoo_id.id,
                'value_ids': [(6, 0, [mvalue.odoo_id.id])],
            }))
        return {
            'attribute_value_ids': attribute_value_ids,
            'attribute_line_ids': attribute_line_ids,
        }

    @mapping
    def type(self, record):
        if record['type_id'] == 'simple':
            return {'type': 'product'}
        elif record['type_id'] in ('virtual', 'downloadable', 'giftcard'):
            return {'type': 'service'}
        return

    @mapping
    def website_ids(self, record):
        website_ids = []
        binder = self.binder_for('magento.website')
        for mag_website_id in record['extension_attributes']['website_ids']:
            website_binding = binder.to_internal(mag_website_id)
            website_ids.append((4, website_binding.id))
        return {'website_ids': website_ids}

    @mapping
    def categories(self, record):
        mag_categories = record.get('categories', record.get('category_ids', None))
        if not mag_categories:
            return
        binder = self.binder_for('magento.product.category')

        category_ids = []
        main_categ_id = None

        for mag_category_id in mag_categories:
            mcat = binder.to_internal(mag_category_id, unwrap=False)
            if not mcat:
                raise MappingError("The product category with "
                                   "magento id %s is not imported." %
                                   mag_category_id)

            if mcat.odoo_id:
                category_ids.append(mcat.odoo_id.id)

        if category_ids:
            main_categ_id = category_ids.pop(0)

        if main_categ_id is None:
            default_categ = self.backend_record.default_category_id
            if default_categ:
                main_categ_id = default_categ.id

        result = {'categ_ids': [(6, 0, category_ids)]}
        if main_categ_id:  # OpenERP assign 'All Products' if not specified
            result['categ_id'] = main_categ_id
        return result

    @mapping
    def attribute_set_id(self, record):
        binder = self.binder_for('magento.product.attributes.set')
        attribute_set = binder.to_internal(record['attribute_set_id'])

        _logger.debug("-------------------------------------------> Import custom attributes %r" % attribute_set)
        link_value = []
        for att in attribute_set.attribute_ids:
            _logger.debug("Import custom att %r" % att)

            if record.get(att.name):
                try:
                    searchn = '_'.join((att.external_id, str(record.get(att.name)))).encode('utf-8')
                except UnicodeEncodeError:
                    searchn = '_'.join((att.external_id, record.get(att.name))).encode('utf-8')
                att_val = self.env['magento.product.attribute.value'].search(
                    [('external_id', '=', searchn)], limit=1)
                _logger.debug("Import custom att_val %r %r " % (att_val, searchn))
                if att_val:
                    link_value.append(att_val[0].odoo_id.id)
        # TODO: Switch between standr Odoo class or to the new class
        return {'attribute_set_id': attribute_set.id, 'attribute_value_ids': [(6, 0, link_value)]}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def no_stock_sync(self, record):
        return {'no_stock_sync': self.backend_record.no_stock_sync}

    def _get_odoo_product(self, record):
        return self.env['product.product'].search([
            ('default_code', '=', record['sku'])
        ], limit=1)

    @only_create
    @mapping
    def odoo_id(self, record):
        """ Will bind the product to an existing one with the same code """
        product = self._get_odoo_product(record)
        if product:
            return {'odoo_id': product.id}


class ProductImporter(Component):
    _name = 'magento.product.product.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.product']
    _magento_id_field = 'sku'

    def _is_uptodate(self, binding):
        # TODO: Remove for production - only to test the update
        return False

    def _import_bundle_dependencies(self):
        """ Import the dependencies for a Bundle """
        bundle = self.magento_record['_bundle_data']
        for option in bundle['options']:
            for selection in option['selections']:
                self._import_dependency(selection['product_id'],
                                        'magento.product.product')

    def _import_stock_warehouse(self):
        record = self.magento_record
        stock_item = record['extension_attributes']['stock_item']
        binder = self.binder_for('magento.stock.warehouse')
        mwarehouse = binder.to_internal(stock_item['stock_id'])
        if not mwarehouse:
            # We do create the warehouse binding directly here - did not found a mapping on magento api
            binding = self.env['magento.stock.warehouse'].create({
                'backend_id': self.backend_record.id,
                'external_id': stock_item['stock_id'],
                'odoo_id': self.backend_record.warehouse_id.id,
            })
            self.backend_record.add_checkpoint(binding)

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        # import related categories
        for mag_category_id in record.get(
                'categories', record.get('category_ids', None)):
            _logger.info("Do import product category %s", mag_category_id)
            self._import_dependency(mag_category_id,
                                    'magento.product.category')
        for attribute in record.get('custom_attributes'):
            # It will only import if it does not already exists - so it is safe to call it here
            # With always=True it will force the import / update
            self._import_dependency(attribute['attribute_code'],
                                    'magento.product.attribute', external_field='attribute_code')
        if record['type_id'] == 'bundle':
            self._import_bundle_dependencies()

        self._import_stock_warehouse()

    def _validate_product_type(self, data):
        """ Check if the product type is in the selection (so we can
        prevent the `except_orm` and display a better error message).
        """
        product_type = data['product_type']
        product_model = self.env['magento.product.template']
        types = product_model.product_type_get()
        available_types = [typ[0] for typ in types]
        if product_type not in available_types:
            raise InvalidDataError("The product type '%s' is not "
                                   "yet supported in the connector." %
                                   product_type)

    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        if self.magento_record['type_id'] == 'configurable':
            return _('The configurable product is not imported in Odoo, '
                     'because only the simple products are used in the sales '
                     'orders.')

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``_create`` or
        ``_update`` if some fields are missing or invalid

        Raise `InvalidDataError`
        """
        self._validate_product_type(data)

    def _get_binding(self):
        binding = super(ProductImporter, self)._get_binding()
        if not binding:
            # Do search using the magento_id - maybe the sku did changed !
            binding = self.env['magento.product.product'].search([
                ('backend_id', '=', self.backend_record.id),
                ('magento_id', '=', self.magento_record['id']),
            ])
            # if we found binding here - then the update will also update the external_id on the binding record
        return binding

    def _preprocess_magento_record(self):
        for attr in self.magento_record.get('custom_attributes', []):
            self.magento_record[attr['attribute_code']] = attr['value']
        return

    def run(self, external_id, force=False, binding_template_id=None, binding=None):
        self._binding_template_id = binding_template_id
        return super(ProductImporter, self).run(external_id, force, binding=binding)

    def _update(self, binding, data):
        if self._binding_template_id:
            data['product_tmpl_id'] = self._binding_template_id.odoo_id.id
            data['magento_configurable_id'] = self._binding_template_id.id
            # Name is set on product template on configurables
            if 'name' in data:
                del data['name']
        _logger.info("Data: %s", data)
        super(ProductImporter, self)._update(binding, data)
        return

    def _create(self, data):
        if self._binding_template_id:
            data['product_tmpl_id'] = self._binding_template_id.odoo_id.id
            data['magento_configurable_id'] = self._binding_template_id.id
            # Name is set on product template on configurables
            if 'name' in data:
                del data['name']
            if 'standard_price' in data:
                del data['standard_price']
            if 'lst_price' in data:
                del data['lst_price']

        binding = super(ProductImporter, self)._create(data)
        self.backend_record.add_checkpoint(binding)
        return binding

    def _after_import(self, binding):
        def sort_by_position(elem):
            return elem.position

        """ Hook called at the end of the import """
        translation_importer = self.component(
            usage='translation.importer',
        )
        translation_importer.run(
            self.external_id,
            binding,
            mapper='magento.product.product.import.mapper'
        )
        # Do import stock item
        self._import_stock(binding)
        # Do import media items
        # Disabled for now - needs more checks
        #self._do_media_import(binding)
        # Do import bundle data
        if self.magento_record['type_id'] == 'bundle':
            bundle_importer = self.component(usage='product.bundle.importer')
            bundle_importer.run(binding, self.magento_record)

    def _do_media_import(self, binding):
        def sort_by_position(elem):
            return elem.position

        media_importer = self.component(usage='product.media.importer', model_name='magento.product.media')
        mids = []
        for media in self.magento_record['media_gallery_entries']:
            media_importer.run(media, binding)
            mids.append(media['id'])
        # Delete media bindings which are not available anymore
        for media_binding in binding.magento_image_bind_ids.filtered(lambda m: int(m.external_id) not in mids):
            media_binding.unlink()
        # Here do choose the image at the smallest position as the main image
        for media_binding in sorted(binding.magento_image_bind_ids.filtered(lambda m: m.media_type == 'image' and m.image_type_image), key=sort_by_position):
            binding.odoo_id.with_context(connector_no_export=True).image = media_binding.image
            break
        if not binding:
            for media_binding in sorted(binding.magento_image_bind_ids.filtered(lambda m: m.media_type == 'image'), key=sort_by_position):
                binding.odoo_id.with_context(connector_no_export=True).image = media_binding.image
                break

    def _import_stock(self, binding):
        stock_importer = self.component(usage='record.importer',
                                        model_name='magento.stock.item')
        stock_importer.run(self.magento_record['extension_attributes']['stock_item'])


class ProductUpdateWriteMapper(Component):
    _name = 'magento.product.product.update.write.mapper'
    _inherit = 'magento.import.mapper'
    _usage = 'record.update.write'
    _apply_on = ['magento.product.product']

    direct = [('price', 'magento_price'),
              ('url_key', 'magento_url_key'),
              ('sku', 'external_id'),
              ('id', 'magento_id'),
              (normalize_datetime('created_at'), 'created_at'),
              (normalize_datetime('updated_at'), 'updated_at'),
              ]

    @mapping
    def magento_name(self, record):
        return {
            'magento_name': record['name']
        }

    @mapping
    def website_ids(self, record):
        website_ids = []
        binder = self.binder_for('magento.website')
        for mag_website_id in record['extension_attributes']['website_ids']:
            website_binding = binder.to_internal(mag_website_id)
            website_ids.append((4, website_binding.id))
        return {'website_ids': website_ids}

    @mapping
    def attribute_set_id(self, record):
        binder = self.binder_for('magento.product.attributes.set')
        attribute_set = binder.to_internal(record['attribute_set_id'])
        return {'attribute_set_id': attribute_set.id}

    @mapping
    def no_stock_sync(self, record):
        return {'no_stock_sync': self.backend_record.no_stock_sync}

    @mapping
    def category_positions(self, record):
        # Only for simple products
        if not record['type_id'] == 'simple':
            return {}
        if not 'extension_attributes' in record or not'category_links' in record['extension_attributes']:
            return {}
        data = []
        for position in record['extension_attributes']['category_links']:
            binder = self.binder_for('magento.product.category')
            magento_category = binder.to_internal(position['category_id'])
            if not magento_category:
                raise ValueError('Magento category with id %s is missing on odoo side.' % position['category_id'])
            magento_position = self.env['magento.product.position'].search([
                ('magento_product_category_id', '=', magento_category.id),
                ('product_template_id', '=', self.options.binding.odoo_id.product_tmpl_id.id),
            ])
            if magento_position:
                data.append((1, magento_position.id, {
                    'position': position['position'],
                }))
            else:
                data.append((0, 0, {
                    'product_template_id': self.options.binding.odoo_id.product_tmpl_id.id,
                    'magento_product_category_id': magento_category.id,
                    'position': position['position'],
                }))
        return {'magento_product_position_ids': data}


class ProductUpdateCreateMapper(Component):
    _name = 'magento.product.product.update.create.mapper'
    _inherit = 'magento.product.product.update.write.mapper'
    _usage = 'record.update.create'
    _apply_on = ['magento.product.product']