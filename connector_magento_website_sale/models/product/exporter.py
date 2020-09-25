# -*- coding: utf-8 -*-
# © 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.component.core import Component
from slugify import slugify
import magic
import base64
import logging

_logger = logging.getLogger(__name__)


class ProductProductExporter(Component):
    _inherit = 'magento.product.product.exporter'

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

    '''
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
        """ Export the product.image's associated with this product """
        # First check if the bindings still belong to a real image
        self._check_image_bindings()
        mime = magic.Magic(mime=True)
        _logger.info("Do create images: %s", self.binding.product_variant_image_ids)
        for image in self.binding.product_variant_image_ids.filtered(lambda i: i.image):
            mimetype = mime.from_buffer(base64.b64decode(image.image))
            extension = 'png' if mimetype == 'image/png' else 'jpeg'
            # Find unique filename
            filename = "%s.%s" % (slugify(image.name or self.binding.odoo_id.name, to_lower=True), extension)
            i = 0
            while self.env['magento.product.media'].search_count([
                ('backend_id', '=', self.binding.backend_id.id),
                ('file', '=', filename)
            ]) > 0:
                filename = "%s-%s.%s" % (slugify(image.name or self.binding.odoo_id.name, to_lower=True), i, extension)
                i += 1

            magento_image = image.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == self.binding.backend_id.id)
            if not magento_image:
                # We need to export the category first
                model_key = 'magento_product_id'
                self._export_dependency(image, "magento.product.media", binding_extra_vals={
                    'product_image_id': image.id,
                    'file': filename,
                    'label': image.name,
                    'magento_product_id': self.binding.id,
                    'mimetype': mimetype,
                    'type': 'product_image_ids',
                    'image_type_image': False,
                    'image_type_small_image': False,
                    'image_type_thumbnail': False,
                })
            else:
                magento_image.with_context(no_connector_export=True).update({
                    'mimetype': mimetype,
                    'file': filename,
                    'label': image.name,
                })
                exporter = self.component(usage='record.exporter',
                                          model_name='magento.product.media')
                exporter.run(magento_image)
        return
    '''

    def _after_export(self):
        """ Export the dependencies for the record"""
        super(ProductProductExporter, self)._after_export()
        #self._export_images()
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
