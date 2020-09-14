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
    """
[
  {
    'id': 139519,
    'media_type': 'image',
    'label': 'PO-Mona Lech',
    'position': 0,
    'disabled': False,
    'types': [
      
    ],
    'file': '/9/3/93bead63-2530-48a8-bcbc-37339772e8f3_1.jpeg'
  },
  {
    'id': 147882,
    'media_type': 'image',
    'label': 'PO-Mona Lech',
    'position': 0,
    'disabled': False,
    'types': [
      
    ],
    'file': '/p/o/po-mona-lech_1.jpeg'
  },
  {
    'id': 148867,
    'media_type': 'image',
    'label': 'PO-Mona Lech',
    'position': 0,
    'disabled': False,
    'types': [
      
    ],
    'file': '/f/9/f965eef0-c53c-4d6c-a744-e8014babc72a_1.jpeg'
  },
  {
    'id': 148868,
    'media_type': 'image',
    'label': 'PO-Mona Lech',
    'position': 0,
    'disabled': False,
    'types': [
      
    ],
    'file': '/c/2/c2538bce-3ab3-4f2b-ac7e-fab468cb4114.jpeg'
  },
  {
    'id': 148869,
    'media_type': 'image',
    'label': 'PO-Mona Lech',
    'position': 0,
    'disabled': False,
    'types': [
      
    ],
    'file': '/f/4/f49a9c6f-3ff1-4ddd-8f02-979bcb979d35_1.jpeg'
  },
  {
    'id': 148870,
    'media_type': 'image',
    'label': 'PO-Mona Lech',
    'position': 0,
    'disabled': False,
    'types': [
      
    ],
    'file': '/9/3/93bead63-2530-48a8-bcbc-37339772e8f3_3.jpeg'
  },
  {
    'id': 148879,
    'media_type': 'image',
    'label': 'PO-Mona Lech',
    'position': 1,
    'disabled': False,
    'types': [
      'image',
      'small_image',
      'thumbnail'
    ],
    'file': '/p/o/po-mona-lech-23_1.jpeg'
  },
  {
    'id': 148845,
    'media_type': 'image',
    'label': 'PO-Mona Lech',
    'position': 10,
    'disabled': False,
    'types': [
      
    ],
    'file': '/5/4/5489dfb3-45e3-4af2-8278-e9b337308ad1.jpeg'
  },
  {
    'id': 148846,
    'media_type': 'image',
    'label': 'PO-Mona Lech',
    'position': 10,
    'disabled': False,
    'types': [
      
    ],
    'file': '/f/e/fe5751c5-620e-415b-b1ba-c437e5da83d4_1.jpeg'
  }
]    
    """
    def _export_images(self):
        """ Export the product.image's associated with this product """
        magento_media = self.backend_adapter.get_media(self.external_id)
        _logger.info("Got Magento Media: %s", magento_media)
        mime = magic.Magic(mime=True)
        for image in self.binding.product_image_ids.filtered(lambda i: i.image):
            magento_image = image.magento_bind_ids.filtered(lambda bc: bc.backend_id.id == self.binding.backend_id.id)
            if not magento_image:
                mimetype = mime.from_buffer(base64.b64decode(image.image))
                extension = 'png' if mimetype == 'image/png' else 'jpeg'
                # We need to export the category first
                if 'magento.product.template' in self._apply_on:
                    model_key = 'magento_product_tmpl_id'
                else:
                    model_key = 'magento_product_id'
                self._export_dependency(image, "magento.product.media", binding_extra_vals={
                    'product_image_id': image.id,
                    'file': "%s.%s" % (slugify(image.name, to_lower=True), extension),
                    'label': image.name,
                    model_key: self.binding.id,
                    'mimetype': mimetype,
                    'type': 'product_image_ids',
                    'image_type_image': False,
                    'image_type_small_image': False,
                    'image_type_thumbnail': False,
                })
            else:
                exporter = self.component(usage='record.exporter',
                                          model_name='magento.product.media')
                exporter.run(magento_image)
        return

    def _after_export(self):
        """ Export the dependencies for the record"""
        super(ProductProductExporter, self)._after_export()
        self._export_images()
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
