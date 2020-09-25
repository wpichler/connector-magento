# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
import os.path
import logging
import uuid

_logger = logging.getLogger(__name__)


class ProductMediaExporter(Component):
    _name = 'magento.product.media.exporter'
    _inherit = 'magento.exporter'
    _apply_on = ['magento.product.media']

    def _should_import(self):
        return False

    def _update_binding_record_after_write(self, data):
        self.external_id = data

    def _create(self, data, storeview_code=None):
        """ Create the Magento record """
        # special check on data before export
        self._validate_create_data(data)
        if self.binding.type == 'attribute_image':
            # We have to create this image for every variant with this attribute on magento side
            external_ids = ""
            # First - create product template image
            eid = self.backend_adapter.create(data, binding=self.binding, storeview_code=storeview_code,
                                              variant_sku=self.binding.magento_product_tmpl_id.external_id)
            external_ids += (";" if external_ids > "" else "") + self.binding.magento_product_tmpl_id.external_id + "|=" + str(eid)

            for variant in self.binding.magento_product_tmpl_id.product_variant_ids.filtered(lambda
                                                                                                     v: not self.binding.odoo_id.attribute_value_id or self.binding.odoo_id.attribute_value_id.id in v.attribute_value_ids.ids):
                vbinding = variant.magento_bind_ids.filtered(lambda vb: vb.backend_id == self.binding.backend_id)
                if vbinding:
                    data.update({
                        'file': "%s-%s" % (uuid.uuid4(), data['file'], )
                    })
                    eid = self.backend_adapter.create(data, binding=self.binding, storeview_code=storeview_code,
                                                      variant_sku=vbinding[0].external_id)
                    external_ids += (";" if external_ids > "" else "") + vbinding[0].external_id + "|=" + str(eid)
            return external_ids
        else:
            return self.backend_adapter.create(data, binding=self.binding, storeview_code=storeview_code)

    def _update(self, data, storeview_code=None):
        """ Update an Magento record """
        assert self.external_id
        # We have to delete and recreate because of a bug in magento 2
        do_delete = 'content' in data
        if do_delete:
            try:
                if self.binding.type == 'attribute_image':
                    eids = self.binding.external_id.split(";")
                    for eid in eids:
                        (sku, iid) = eid.split("|=")
                        self.backend_adapter.delete((iid, sku,))
                else:
                    self.backend_adapter.delete((self.binding.external_id,
                                                 self.binding.magento_product_id.external_id if self.binding.magento_product_id else self.binding.magento_product_tmpl_id.external_id,))
            except:
                _logger.info("Got error on delete old media - ignore it")
        if self.binding.type == 'attribute_image':
            # We have to create this image for every variant with this attribute on magento side
            external_ids = ""
            # First - create product template image
            if not do_delete:
                eids = self.binding.external_id.split(";")
                for eid in eids:
                    (sku, iid) = eid.split("|=")
                    if sku == self.binding.magento_product_tmpl_id.external_id:
                        data.update({
                            'id': iid,
                        })
                        self.backend_adapter.write(iid, data, binding=self.binding,
                                                   storeview_code=storeview_code,
                                                   variant_sku=self.binding.magento_product_tmpl_id.external_id)
                        external_ids += (";" if external_ids > "" else "") + self.binding.magento_product_tmpl_id.external_id + "|=" + str(iid)
                        break
            if do_delete:
                eid = self.backend_adapter.create(data, binding=self.binding, storeview_code=storeview_code,
                                                  variant_sku=self.binding.magento_product_tmpl_id.external_id)
                external_ids += (";" if external_ids > "" else "") + self.binding.magento_product_tmpl_id.external_id + "|=" + str(eid)

            for variant in self.binding.magento_product_tmpl_id.product_variant_ids.filtered(lambda
                                                                                                     v: not self.binding.odoo_id.attribute_value_id or self.binding.odoo_id.attribute_value_id.id in v.attribute_value_ids.ids):
                vbinding = variant.magento_bind_ids.filtered(lambda vb: vb.backend_id == self.binding.backend_id)
                if vbinding:
                    if do_delete:
                        eid = self.backend_adapter.create(data, binding=self.binding, storeview_code=storeview_code,
                                                          variant_sku=vbinding[0].external_id)
                        external_ids += (";" if external_ids > "" else "") + vbinding[0].external_id + "|=" + str(eid)
                    else:
                        eids = self.binding.external_id.split(";")
                        for eid in eids:
                            (sku, iid) = eid.split("|=")
                            if sku == vbinding.external_id:
                                data.update({
                                    'id': iid,
                                })
                                _logger.info("Do update with: %s", data)
                                self.backend_adapter.write(iid, data, binding=self.binding,
                                                           storeview_code=storeview_code,
                                                           variant_sku=vbinding[0].external_id)
                                external_ids += (";" if external_ids > "" else "") + vbinding[0].external_id + "|=" + str(iid)
            return external_ids
        else:
            if do_delete:
                return self.backend_adapter.create(data, self.binding)
            else:
                self.backend_adapter.write(self.binding.external_id, data, self.binding)
                return self.binding.external_id

    def _has_to_skip(self):
        if not self.binding.magento_product_id.image and not self.binding.magento_product_tmpl_id.image:
            return True
        else:
            return False

    def _run(self, fields=None):
        """ Flow of the synchronization, implemented in inherited classes"""
        assert self.binding

        if not self.external_id:
            fields = None  # should be created with all the fields

        if self._has_to_skip():
            return

        # export the missing linked resources
        self._export_dependencies()

        # prevent other jobs to export the same record
        # will be released on commit (or rollback)
        self._lock()

        map_record = self._map_data()

        if self.external_id:
            if 'image' in fields:
                # We have to delete old images first - then create new images - so we need create data
                record = self._create_data(map_record, fields=fields)
            else:
                record = self._update_data(map_record, fields=fields)
            if not record:
                return _('Nothing to export.')
            data = self._update(record)
            self._update_binding_record_after_create(data)
        else:
            record = self._create_data(map_record, fields=fields)
            if not record:
                return _('Nothing to export.')
            data = self._create(record)
            if not data:
                raise UserWarning('Create did not returned anything on %s with binding id %s', self._name,
                                  self.binding.id)
            self._update_binding_record_after_create(data)
        return _('Record exported with ID %s on Magento.') % self.external_id


class ProductMediaExportMapper(Component):
    _name = 'magento.product.media.export.mapper'
    _inherit = 'magento.export.mapper'
    _apply_on = ['magento.product.media']

    direct = [
        ('label', 'label'),
        ('disabled', 'disabled'),
    ]

    @mapping
    def media_type(self, record):
        # direct mappings will get in the result is fields is set  but media_type is always needed
        return {
            'media_type': record.media_type
        }

    @mapping
    def position(self, record):
        if record.position is False:
            return {}
        return {
            'position': record.position
        }

    @mapping
    def get_types(self, record):
        itypes = []
        if record.image_type_image:
            itypes.append('image')
        if record.image_type_small_image:
            itypes.append('small_image')
        if record.image_type_thumbnail:
            itypes.append('thumbnail')
        if record.image_type_swatch:
            itypes.append('swatch_image')
        return {'types': itypes}

    @mapping
    @only_create
    def get_file(self, record):
        return {'file': record.file}

    '''
    @mapping
    def get_id(self, record):
        if self.options.for_create:
            return None
        return {
            'id': record.external_id,
        }
    '''

    @mapping
    @only_create
    def get_content(self, record):
        return {'content': {
            'base64_encoded_data': record.magento_product_id.image.decode(
                'ascii') if record.magento_product_id else record.magento_product_tmpl_id.image.decode('ascii'),
            'type': record.mimetype,
            'name': os.path.basename(record.file),
        }}
