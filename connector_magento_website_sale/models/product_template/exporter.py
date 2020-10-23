# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.addons.component.core import Component
import logging


_logger = logging.getLogger(__name__)


class ProductTemplateDefinitionExporter(Component):
    _inherit = 'magento.product.template.exporter'

    def _after_export(self):
        _logger.info("AFTEREXPORT: In _after_export at %s", __name__)
        super(ProductTemplateDefinitionExporter, self)._after_export()

    def _export_images(self):
        _logger.info("AFTEREXPORT: In _export_images at %s", __name__)
        listener = self.component(usage='event.listener',
                                  model_name='product.image')
        for image in self.binding.odoo_id.base_product_image_ids:
            listener._check_create_binding(image, do_delay=True)
        super(ProductTemplateDefinitionExporter, self)._export_images()



class ProductTemplateExportMapper(Component):
    _inherit = 'magento.product.template.export.mapper'

    def category_ids(self, record):
        _logger.info("Product categories: %s", record.public_categ_ids)
        c_ids = []
        for c in record.public_categ_ids:
            c_ids.extend([bind.external_id for bind in c.magento_bind_ids.filtered(lambda m: m.backend_id == record.backend_id)])
        return {
            'attribute_code': 'category_ids',
            'value': c_ids
        }

    '''
    def category_ids(self, record):
        categ_vals = []
        _logger.info("Public Category IDS: %s. Options: %s", record.public_categ_ids, self.options)
        for categ in record.public_categ_ids:
            magento_categ_id = categ.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == record.backend_id.id)
            mpos = self.env['magento.product.position'].search([
                ('product_template_id', '=', record.odoo_id.id),
                ('magento_product_category_id', '=', magento_categ_id.id)
            ])
            if magento_categ_id:
                categ_vals.append({
                  "category_id": magento_categ_id.external_id,
                  "position": mpos.position if mpos else 0
                })
        return {'category_links': categ_vals}
    '''