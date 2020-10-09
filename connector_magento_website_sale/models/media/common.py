# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields, api, _
from odoo.addons.component.core import Component
import urllib.request, urllib.parse, urllib.error
from urllib.parse import urljoin
import base64


_logger = logging.getLogger(__name__)

class MagentoProductMedia(models.Model):
    _inherit = 'magento.product.media'

    @api.depends('type', 'magento_product_id', 'magento_product_tmpl_id', 'odoo_id')
    def _get_local_image(self):
        media_ids = self.filtered(lambda m: m.type in ('product_image_ids', 'attribute_image'))
        super(MagentoProductMedia, self.filtered(lambda m: m.type not in ('product_image_ids', 'attribute_image')))._get_local_image()
        for media in media_ids:
            media.local_image = media.image_image

    odoo_id = fields.Many2one('product.image', string="Product Image")
    image_image = fields.Binary(related='odoo_id.image')


class ProductImage(models.Model):
    _inherit = 'product.image'

    magento_bind_ids = fields.One2many('magento.product.media', 'odoo_id', string="Magento Image")
