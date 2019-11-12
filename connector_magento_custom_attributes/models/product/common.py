# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import ast
from odoo.osv.orm import setup_modifiers
from lxml import etree
from odoo import api, models, fields
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action

_logger = logging.getLogger(__name__)



class MagentoProductProduct(models.Model):
    _inherit = 'magento.product.product'
    
    @api.depends('magento_attribute_line_ids')
    def _compute_custom_values_count(self):
        for product in self:
            product.custom_values_count = len(product.magento_attribute_line_ids)

    magento_attribute_line_ids = fields.One2many(comodel_name='magento.custom.attribute.values',
                                                 inverse_name='magento_product_id', 
                                                 string='Magento Simple Custom Attributes Values',
                                        )
    custom_values_count = fields.Integer('Custom Values Count', compute='_compute_custom_values_count')

    @api.multi
    def check_field_mapping(self, field, vals=None):
        # Check if the Odoo Field has a matching attribute in Magento
        # Update the value
        self.ensure_one()
        #         att_id = 0
        odoo_fields = self.env['ir.model.fields'].search([
            ('name', '=', field),
            ('model', 'in', ['product.product', 'product.template'])
        ])

        att_ids = self.env['magento.product.attribute'].search([
            ('odoo_field_name', 'in', [o.id for o in odoo_fields]),
            ('backend_id', '=', self.backend_id.id)
        ])

        if len(att_ids) == 0:
            # Nothing to do
            return
        
        value = vals[field] if vals and hasattr(vals, field) else self[field]
        for att_id in att_ids:
            custom_vals = {
                'magento_product_id': self.id,
                'attribute_id': att_id.id,
                'attribute_text': value,
                'attribute_select': False,
                'attribute_multiselect': False,
            }
            odoo_field_type = odoo_fields[0].ttype
            if odoo_field_type in ['many2one', 'many2many'] and 'text' in att_id.frontend_input:
                custom_vals.update({'attribute_text': str([v.magento_bind_ids.external_id for v in value])})

            if att_id.frontend_input == 'boolean':
                custom_vals.update({'attribute_text': str(int(value))})
            if att_id.frontend_input == 'select':
                custom_vals.update({
                    'attribute_text': False,
                    'attribute_multiselect': False,
                    'attribute_select': value.magento_bind_ids.id or False
                })
            if att_id.frontend_input == 'multiselect':
                custom_vals.update({
                    'attribute_text': False,
                    'attribute_select': False,
                    'attribute_multiselect': [(6, False, [v.id for v in value.magento_bind_ids])]
                })
            custom_model = self.env['magento.custom.attribute.values']
            existing = custom_model.search([
                ('magento_product_id', '=', self.id),
                ('attribute_id', '=', att_id.id)
            ])
            if not existing:
                custom_model.with_context(no_update=True).create(custom_vals)
            else:
                existing.with_context(no_update=True).write(custom_vals)

    @api.multi
    def recheck_field_mapping(self, values=None):
        for mproduct in self:
            attribute_set_id = mproduct.attribute_set_id or mproduct.backend_id.default_attribute_set_id
            attributes = attribute_set_id.attribute_ids.filtered(lambda x: x.odoo_field_name)
            for att in attributes:
                mproduct.check_field_mapping(att.odoo_field_name.name, vals=values)

    @api.model
    def create(self, vals):
        mg_prod_id = super(MagentoProductProduct, self).create(vals)
        mg_prod_id.recheck_field_mapping()
        return mg_prod_id


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ProductProduct, self).fields_view_get(
            view_id=view_id, 
            view_type=view_type, 
            toolbar=toolbar,
            submenu=submenu)

        if res['model'] in ['product.template', 'product.product'] and \
                res['type'] == 'form':
            doc = etree.XML(res['arch'])
            mapped_field_ids = self.env['magento.product.attribute'].search(
                [('odoo_field_name', '!=', False)]).mapped('odoo_field_name')

            for field in mapped_field_ids:
                nodes = doc.xpath("//field[@name='%s']" % field.name)
                for node in nodes:
                    node.set('class', 'magento-mapped-field-view')
                    help = node.get('help', '')
                    node.set('help', '** Magento ** \n %s' % help)
                    setup_modifiers(
                        node, res['fields'][field.name])
            res['arch'] = etree.tostring(doc)
        return res
