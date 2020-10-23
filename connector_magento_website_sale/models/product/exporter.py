# -*- coding: utf-8 -*-
# © 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.component.core import Component
import logging

_logger = logging.getLogger(__name__)


class ProductProductExporter(Component):
    _inherit = 'magento.product.product.exporter'

    '''
    def _export_product_links_dependencies(self):
        record = self.binding
        for template in record.alternative_product_ids:
            if template.product_variant_count > 1:
                binding = template.magento_template_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id)
            else:
                binding = template.product_variant_id.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id)
            if binding and len(binding) > 1:
                _logger.error("More than 1 binding for this template %s", template.name)
                raise Exception("More than 1 binding for this template %s", template.name)
            if not binding or not binding.external_id:
                if template.product_variant_count > 1:
                    self._export_dependency(template, "magento.product.template")
                else:
                    self._export_dependency(template.product_variant_id, "magento.product.product")
    '''

    def _export_product_links(self):
        # TODO: Refactor this to use a real mapping and exporter class
        record = self.binding
        a_products = []
        position = 1
        for template in record.alternative_product_ids:
            if template.product_variant_count > 1:
                binding = template.magento_template_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id)
            else:
                binding = template.product_variant_id.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id)
            if not binding or not binding.external_id:
                _logger.info("No binding / No external id on binding for linked product %s", template.display_name)
                continue
            if binding and binding.external_id:
                a_products.append({
                    "sku": record.external_id,
                    "link_type": "related",
                    "linked_product_sku": binding.external_id,
                    "linked_product_type": "configurable" if template.product_variant_count > 1 else 'simple',
                    "position": position,
                })
                position += 1
        if a_products:
            self.backend_adapter.update_product_links(record.external_id, a_products)

    def _export_categories(self):
        """ Export the dependencies for the record"""
        # Check for categories
        if not self.backend_record.auto_create_category:
            return
        categ_exporter = self.component(usage='record.exporter', model_name='magento.product.category')
        _logger.info("Public Category IDS: %s", self.binding.public_categ_ids)
        for categ in self.binding.public_categ_ids:
            magento_categ_id = categ.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == self.binding.backend_id.id)
            if not magento_categ_id:
                # We need to export the category first
                m_categ = self.env['magento.product.category'].with_context(connector_no_export=True).create({
                    'backend_id': self.backend_record.id,
                    'public_categ_id': categ.id,
                })
                categ_exporter.run(m_categ)
        return

    def _check_image_bindings(self):
        for ibinding in self.binding.magento_image_bind_ids.filtered(lambda b: b.type == 'product_image_ids'):
            if not ibinding.odoo_id \
                    or not ibinding.odoo_id.image \
                    or ibinding.odoo_id.id not in self.binding.product_variant_image_ids.ids:
                _logger.info("Do delete image %s", ibinding)
                ibinding.unlink()
        for ibinding in self.binding.magento_image_bind_ids.filtered(lambda b: b.type == 'attribute_image'):
            if not ibinding.odoo_id or not ibinding.odoo_id.image:
                _logger.info("Do delete image %s", ibinding)
                ibinding.unlink()

    def _export_images(self):
        _logger.info("AFTEREXPORT: In _export_images at %s", __name__)
        pass

    def _export_dependencies(self):
        super(ProductProductExporter, self)._export_dependencies()
        #self._export_product_links_dependencies()

    def _after_export(self):
        """ Export the dependencies for the record"""
        _logger.info("AFTEREXPORT: In _after_export at %s", __name__)
        # Export images have to run before the super call - because in the super call there is a sync check
        self._export_images()
        super(ProductProductExporter, self)._after_export()
        self._export_product_links()
        return


class ProductProductExportMapper(Component):
    _inherit = 'magento.product.export.mapper'

    '''
    def category_ids(self, record):
        categ_vals = []
        i = 0
        for categ in record.public_categ_ids:
            magento_categ_id = categ.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id)
            mpos = self.env['magento.product.position'].search([
                ('product_template_id', '=', record.odoo_id.product_tmpl_id.id),
                ('magento_product_category_id', '=', magento_categ_id.id)
            ])
            if magento_categ_id:
                categ_vals.append({
                  "position": mpos.position if mpos else i,
                  "category_id": magento_categ_id.external_id,
                })
                if not mpos:
                    i += 1
        return {'category_links': categ_vals}
    '''
    def category_ids(self, record):
        c_ids = []
        for categ in record.public_categ_ids:
            magento_categ_id = categ.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id)
            if magento_categ_id:
                c_ids.extend([m.external_id for m in magento_categ_id])
        return {
            'attribute_code': 'category_ids',
            'value': c_ids
        }
