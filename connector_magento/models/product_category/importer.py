# -*- coding: utf-8 -*-
# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError
import logging
from odoo.addons.queue_job.exception import NothingToDoJob

_logger = logging.getLogger(__name__)


class ProductCategoryBatchImporter(Component):
    """ Import the Magento Product Categories.

    For every product category in the list, a delayed job is created.
    A priority is set on the jobs according to their level to rise the
    chance to have the top level categories imported first.
    """
    _name = 'magento.product.category.batch.importer'
    _inherit = 'magento.delayed.batch.importer'
    _apply_on = ['magento.product.category']

    def _import_record(self, external_id, job_options=None):
        """ Delay a job for the import """
        super(ProductCategoryBatchImporter, self)._import_record(
            external_id, job_options=job_options
        )

    def run(self, filters=None):
        """ Run the synchronization """
        if self.work.magento_api._location.version == '2.0':

            importer = self.component(usage='record.importer')
            tree = self.backend_adapter.search_read()

            def import_branch(branch):
                children = branch.pop('children_data', [])
                importer.run(branch['id'])
                for child in children:
                    import_branch(child)

            import_branch(tree)
        else:
            from_date = filters.pop('from_date', None)
            to_date = filters.pop('to_date', None)
            if from_date or to_date:
                updated_ids = self.backend_adapter.search(filters,
                                                        from_date=from_date,
                                                        to_date=to_date)
            else:
                updated_ids = None

            base_priority = 10

            def import_nodes(tree, level=0):
                for node_id, children in tree.items():
                    # By changing the priority, the top level category has
                    # more chance to be imported before the childrens.
                    # However, importers have to ensure that their parent is
                    # there and import it if it doesn't exist
                    if updated_ids is None or node_id in updated_ids:
                        job_options = {
                            'priority': base_priority + level,
                        }
                        self._import_record(
                            node_id, job_options=job_options)
                    import_nodes(children, level=level + 1)
            tree = self.backend_adapter.tree()
            import_nodes(tree)


class ProductCategoryImporter(Component):
    _name = 'magento.product.category.importer'
    _inherit = 'magento.importer'
    _apply_on = ['magento.product.category']

    def _import_dependency(self, external_id, binding_model,
                           importer=None, always=False, external_field=None):
        """ Import a dependency.

        The importer class is a class or subclass of
        :class:`MagentoImporter`. A specific class can be defined.

        :param external_id: id of the related binding to import
        :param binding_model: name of the binding model for the relation
        :type binding_model: str | unicode
        :param importer_component: component to use for import
                                   By default: 'importer'
        :type importer_component: Component
        :param always: if True, the record is updated even if it already
                       exists, note that it is still skipped if it has
                       not been modified on Magento since the last
                       update. When False, it will import it only when
                       it does not yet exist.
        :type always: boolean
        """
        if not external_id:
            return
        binder = self.binder_for(binding_model)
        if always or not binder.to_internal(external_id, external_field=external_field) or not binder.to_internal(external_id, external_field=external_field).odoo_id:
            if importer is None:
                importer = self.component(usage='record.importer',
                                          model_name=binding_model)
            try:
                importer.run(external_id)
            except NothingToDoJob:
                _logger.info(
                    'Dependency import of %s(%s) has been ignored.',
                    binding_model._name, external_id
                )

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magento_record
        # import parent category
        # the root category has a 0 parent_id
        self._import_dependency(record.get('parent_id'), self.model)

    def _is_uptodate(self, binding):
        # TODO: Remove for production
        return False

    def _create(self, data):
        binding = super(ProductCategoryImporter, self)._create(data)
        _logger.info("Created binding: %s", binding)
        self.backend_record.add_checkpoint(binding)
        return binding

    def _update(self, binding, data):
        return super(ProductCategoryImporter, self)._update(binding, data)

    def _check_product_category(self, binding, template):
        pass

    def _import_categorie_product_positions(self, binding):
        product_links = self.backend_adapter.get_assigned_product(self.external_id)
        _logger.info("Got product links: %s", product_links)
        # [{'sku': 'loden-bezugsstoff-bergen', 'position': 0, 'category_id': '90'}]
        binder = self.binder_for('magento.product.template')
        pbinder = self.binder_for('magento.product.product')
        for category_link in product_links:
            template = binder.to_internal(category_link['sku'], unwrap=True)
            if not template:
                product = pbinder.to_internal(category_link['sku'], unwrap=True)
                if not product:
                    _logger.info("Product Template or Product with SKU %s is still missing.", category_link['sku'])
                    continue
                template = product.product_tmpl_id
            # Search for position
            position = self.env['magento.product.position'].search([
                ('magento_product_category_id.backend_id', '=', self.backend_record.id),
                ('product_template_id', '=', template.id),
                ('magento_product_category_id', '=', binding.id),
            ])
            if not position:
                self.env['magento.product.position'].with_context(connector_no_export=True).create({
                    'product_template_id': template.id,
                    'magento_product_category_id': binding.id,
                    'position': category_link['position'],
                })
            else:
                position.with_context(connector_no_export=True).update({
                    'position': category_link['position'],
                })
            self._check_product_category(binding, template)

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        translation_importer = self.component(usage='translation.importer')
        translation_importer.run(self.external_id, binding)
        self._import_categorie_product_positions(binding)


class ProductCategoryImportMapper(Component):
    _name = 'magento.product.category.import.mapper'
    _inherit = 'magento.import.mapper'
    _apply_on = 'magento.product.category'

    direct = [
        ('description', 'description'),
        ('name', 'magento_name'),
    ]
    
    @mapping
    def external_id(self, record):
        if self.work.magento_api._location.version == '2.0':
            return {'external_id': record['id']}
        return {'external_id': record['category_id']}

    @mapping
    def name(self, record):
        if record['level'] == '0':  # top level category; has no name
            return {'name': self.backend_record.name}
        if record['name']:  # may be empty in storeviews
            return {'name': record['name']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    @only_create
    def odoo_id(self, record):
        binder = self.binder_for()
        categ_id = binder.to_internal(record['id'])
        if record.get('parent_id'):
            parent_binding = binder.to_internal(record['parent_id'])
        if self.backend_record.auto_create_category_on_import and (not categ_id or not categ_id.odoo_id):
            odoo_category = self.env['product.category'].create({
                'name': record['name'],
                'parent_id': parent_binding.odoo_id.id if parent_binding and parent_binding.odoo_id else None,
            })
            return {
                'odoo_id': odoo_category.id,
                'magento_parent_id': parent_binding.id if parent_binding else None,
            }
