# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields, api, _
from odoo.addons.component.core import Component
import urllib.request, urllib.parse, urllib.error
from urllib.parse import urljoin
import base64
import uuid
import requests
from odoo.addons.queue_job.job import identity_exact
from odoo.addons.queue_job.job import job, related_action
from slugify import slugify


_logger = logging.getLogger(__name__)


class MagentoProductMedia(models.Model):
    _name = 'magento.product.media'
    _inherit = 'magento.binding'
    _description = 'Magento Product Media'
    _order = 'position'

    @api.depends('backend_id', 'file')
    def _compute_url(self):
        for media in self:
            media.url = urljoin(media.backend_id.location, "/pub/media/catalog/product%s" % media.file)

    @api.depends('url')
    def _get_image(self):
        for media in self:
            try:
                f = requests.get(media.url)
                if f.status_code == 200:
                    media.image = base64.b64encode(f.content)
                f.close()
            except Exception as e:
                _logger.error("Got Exception %s while trying to fetch image on %s", e, media.url)

    magento_product_id = fields.Many2one(comodel_name='magento.product.product',
                                         string='Magento Product',
                                         required=False,
                                         ondelete='cascade')
    magento_product_tmpl_id = fields.Many2one(comodel_name='magento.product.template',
                                              string='Magento Product Template',
                                              required=False,
                                              ondelete='cascade')
    p_image = fields.Binary(related='magento_product_id.odoo_id.image')
    pt_image = fields.Binary(related='magento_product_tmpl_id.odoo_id.image')
    label = fields.Char(string="Label")
    type = fields.Selection([
        ('product_image', 'Product Image'),
        ('product_image_ids', 'Extra Product Images'),
        ('attribute_image', 'Attribute Image'),
    ], string='Type')
    file = fields.Char(string="File", required=True)
    url = fields.Char(string="URL", compute='_compute_url', store=False)
    image = fields.Binary(string="Image", compute='_get_image')
    position = fields.Integer(string="Position", default=0)
    disabled = fields.Boolean(string="Disabled", default=False)
    mimetype = fields.Char(string="Mimetype", required=True, default='image/jpeg')
    media_type = fields.Selection([
        ('image', _('Image')),
        ('external-video', _('External Video')),
    ], default='image', string='Media Type')
    image_type_image = fields.Boolean(string="Image", default=False)
    image_type_small_image = fields.Boolean(string="Small Image", default=False)
    image_type_thumbnail = fields.Boolean(string="Thumbnail", default=False)
    image_type_swatch = fields.Boolean(string="Swatch", default=False)

    _sql_constraints = [
        ('file_uniq', 'unique(backend_id, magento_product_id, file)',
         'The filename must be unique.'),
    ]

    @api.model
    def create(self, vals):
        if 'magento_product_id' in vals and vals['magento_product_id']:
            existing = self.search_count([
                ('backend_id', '=', vals['backend_id']),
                ('magento_product_id', '=', vals['magento_product_id']),
                ('file', '=', vals['file']),
            ])
        elif 'magento_product_tmpl_id' in vals and vals['magento_product_tmpl_id']:
            existing = self.search_count([
                ('backend_id', '=', vals['backend_id']),
                ('magento_product_tmpl_id', '=', vals['magento_product_tmpl_id']),
                ('file', '=', vals['file']),
            ])
        if existing:
            extension = 'png' if vals['mimetype']=='image/png' else 'jpeg'
            vals['file'] = "%s.%s" % (uuid.uuid4(), extension)
        return super(MagentoProductMedia, self).create(vals)

    @api.model
    def get_unique_filename(self, image, backend_id, mimetype):
        extension = 'png' if mimetype == 'image/png' else 'jpeg'
        # Find unique filename
        filename = "%s.%s" % (slugify(image.base_product_tmpl_id.name, to_lower=True),  extension)
        i = 0
        while self.env['magento.product.media'].search_count([
            ('backend_id', '=', backend_id.id),
            ('file', '=', filename)
        ]) > 0:
            filename = "%s-%s.%s" % (slugify(image.base_product_tmpl_id.name, to_lower=True), i, extension)
            i += 1
        return filename

    @job(default_channel='root.magento.image', retry_pattern={
        1: 1 * 60,
        5: 5 * 60,
    })
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_record(self, backend_id, fields=None):
        return super(MagentoProductMedia, self).export_record(backend_id, fields)

    @api.multi
    @job(default_channel='root.magento')
    def sync_from_magento(self):
        for binding in self:
            binding.with_delay(identity_key=identity_exact).run_sync_from_magento()

    @api.multi
    @job(default_channel='root.magento')
    def run_sync_from_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(self.external_id, force=True)


class ProductTemplate(models.Model):
    _inherit = 'magento.product.template'

    magento_image_bind_ids = fields.One2many(
        comodel_name='magento.product.media',
        inverse_name='magento_product_tmpl_id',
        string='Magento Images',
    )


class MagentoProductProduct(models.Model):
    _inherit = 'magento.product.product'

    magento_image_bind_ids = fields.One2many(
        comodel_name='magento.product.media',
        inverse_name='magento_product_id',
        string='Magento Images',
    )


class ProductMediaAdapter(Component):
    _name = 'magento.product.media.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.media'
    _magento2_key = 'entry_id'

    def _read_url(self, id, sku):
        def escape(term):
            if isinstance(term, str):
                return urllib.parse.quote(term.encode('utf-8'), safe='')
            return term

        return 'products/%s/media/%s' % (escape(sku), id)

    def read(self, id, sku, attributes=None, storeview_code=None, binding=None):
        if self.work.magento_api._location.version == '2.0':
            return self._call(self._read_url(id, sku), None, storeview=storeview_code)

