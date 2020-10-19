# -*- coding: utf-8 -*-
# © 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError


class ProductCategoryImporter(Component):
    _inherit = 'magento.product.category.importer'

    def _check_product_category(self, binding, template):
        '''
        Here we do check if the product is in the categ_ids
        :param binding:
        :param template:
        :return:
        '''
        if binding.public_categ_id and binding.public_categ_id.id not in template.public_categ_ids.ids:
            # Set this as a new public categorie
            template.with_context(connector_no_export=True).public_categ_ids = [(4, binding.public_categ_id.id)]

    def _update_parent_link(self, binding):
        if binding.magento_parent_id and binding.magento_parent_id.public_categ_id:
            binding.with_context(connector_no_export=True).public_categ_id.parent_id = binding.magento_parent_id.public_categ_id.id

    def _after_import(self, binding):
        super(ProductCategoryImporter, self)._after_import(binding)
        self._update_parent_link(binding)


class ProductCategoryImportMapper(Component):
    _inherit = 'magento.product.category.import.mapper'

    @mapping
    @only_create
    def odoo_id(self, record):
        binder = self.binder_for()
        parent_binding = None
        if record.get('parent_id'):
            parent_binding = binder.to_internal(record['parent_id'])
        # Do search for existing category
        if parent_binding:
            odoo_category = self.env['product.public.category'].search([
                ('name', '=ilike', record['name']),
                ('parent_id', '=', parent_binding.public_categ_id.id)
            ])
        else:
            odoo_category = self.env['product.public.category'].search([
                ('name', '=ilike', record['name']),
                ('parent_id', '=', None)
            ])
        if odoo_category:
            return {
                'public_categ_id': odoo_category.id,
                'odoo_id': None,
            }
        # Not found yet - so create it ?
        if self.backend_record.auto_create_category_on_import:
            data = {
                'name': record['name']
            }
            if parent_binding:
                data.update({
                    'parent_id': parent_binding.odoo_id.id,
                })
            odoo_category = self.env['product.public.category'].create(data)
            return {
                'public_categ_id': odoo_category.id,
                'odoo_id': None,
            }

    @mapping
    def parent_id(self, record):
        binder = self.binder_for()
        parent_binding = None
        if record.get('parent_id'):
            parent_binding = binder.to_internal(record['parent_id'])
        if parent_binding:
            return {
                'magento_parent_id': parent_binding.id,
            }
