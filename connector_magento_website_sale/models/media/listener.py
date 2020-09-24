# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import identity_exact
import magic
import base64
from slugify import slugify


class MagentoProductImageExportListener(Component):
    _name = 'magento.product.image.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['product.image']

    def _create_binding(self, record):
        mime = magic.Magic(mime=True)
        mimetype = mime.from_buffer(base64.b64decode(record.image))
        extension = 'png' if mimetype == 'image/png' else 'jpeg'

        if not record.magento_bind_ids and record.base_product_tmpl_id.magento_bind_ids:
            if record.attribute_value_id:
                itype = 'attribute_image'
            else:
                itype = 'product_image_ids'

            for tbinding in record.base_product_tmpl_id.magento_template_bind_ids:
                # Find unique filename
                filename = "%s.%s" % (slugify(record.base_product_tmpl_id.name, to_lower=True), extension)
                i = 0
                while self.env['magento.product.media'].search_count([
                    ('backend_id', '=', tbinding.backend_id.id),
                    ('file', '=', filename)
                ]) > 0:
                    filename = "%s-%s.%s" % (slugify(record.base_product_tmpl_id.name, to_lower=True), i, extension)
                    i += 1
                self.env['magento.product.media'].sudo().with_context(connector_no_export=True).create({
                    'backend_id': tbinding.backend_id.id,
                    'odoo_id': record.id,
                    'magento_product_tmpl_id': tbinding.id,
                    'label': tbinding.odoo_id.name,
                    'file': filename,
                    'type': itype,
                    'position': record.sequence,
                    'mimetype': mimetype,
                    'image_type_image': True if record.is_primary_image else False,
                    'image_type_small_image': True if record.is_primary_image else False,
                    'image_type_thumbnail': True if record.is_primary_image else False,
                })

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        if not record.image:
            return
        self._create_binding(record)
        for binding in record.magento_bind_ids:
            binding.with_delay(identity_key=identity_exact).export_record(binding.backend_id)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if not record.image:
            return
        self._create_binding(record)
        for binding in record.magento_bind_ids:
            binding.with_delay(identity_key=identity_exact).export_record(binding.backend_id)

    def on_record_unlink(self, record):
        for binding in record.magento_bind_ids:
            with binding.backend_id.work_on(binding._name) as work:
                external_id = work.component(usage='binder').to_external(binding)
                if external_id:
                    binding.with_delay(identity_key=identity_exact).export_delete_record(
                        binding.backend_id,
                        external_id
                    )
