# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields, api, _
from odoo.addons.component.core import Component
import urllib.request, urllib.parse, urllib.error
from odoo.addons.queue_job.job import job, related_action


_logger = logging.getLogger(__name__)


class MagentoProductMedia(models.Model):
    _inherit = 'magento.product.media'

    @api.multi
    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    def sync_to_magento(self):
        for binding in self:
            binding.with_delay(identity_key=('magento_product_media_%s' % binding.id)).run_sync_to_magento()


    @api.multi
    @related_action(action='related_action_unwrap_binding')
    @job(default_channel='root.magento')
    def run_sync_to_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.run(self)


class ProductMediaAdapter(Component):
    _inherit = 'magento.product.media.adapter'
    _magento2_name = 'entry'

    def _get_id_from_create(self, result, data=None):
        return result

    def _create_url(self, binding=None):
        def escape(term):
            if isinstance(term, str):
                return urllib.parse.quote(term.encode('utf-8'), safe='')
            return term

        if self.variant_sku:
            return 'products/%s/media' % (escape(self.variant_sku), )
        else:
            pbinding = binding.magento_product_id if binding.magento_product_id else binding.magento_product_tmpl_id
            return 'products/%s/media' % (escape(pbinding.external_id), )

    def _write_url(self, id, binding=None):
        def escape(term):
            if isinstance(term, str):
                return urllib.parse.quote(term.encode('utf-8'), safe='')
            return term

        if self.variant_sku:
            return 'products/%s/media/%s' % (escape(self.variant_sku), id, )
        else:
            pbinding = binding.magento_product_id if binding.magento_product_id else binding.magento_product_tmpl_id
            return 'products/%s/media/s' % (escape(pbinding.external_id), id, )

    def create(self, data, binding=None, storeview_code=None, variant_sku=None):
        self.variant_sku = variant_sku
        return super(ProductMediaAdapter, self).create(data, binding, storeview_code)

    def write(self, id, data, binding=None, storeview_code=None, variant_sku=None):
        self.variant_sku = variant_sku
        return super(ProductMediaAdapter, self).write(id, data, binding, storeview_code)

    def _delete_url(self, id, binding=None):
        def escape(term):
            if isinstance(term, str):
                return urllib.parse.quote(term.encode('utf-8'), safe='')
            return term

        return 'products/%s/media/%s' % (id[1], id[0])
