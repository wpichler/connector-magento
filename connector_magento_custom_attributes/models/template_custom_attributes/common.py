# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
from odoo import api, models, fields
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import IDMissingInBackend

_logger = logging.getLogger(__name__)

    
class MagentoCustomAttribute(models.Model):
    _inherit = 'magento.custom.template.attribute.values'
         
    """
    This class deal with customs Attributes for templates
    Has to be merged / Refactor with the one in connector_magento
    """

    @api.multi
    def _get_field_values_from_magento_type(self, mattribute, attribute):
        """ Check Magento ftontend type and provide adequat values
        @param dict attribute : 2 entry dictionnary with attribute code and value
        """
        self.ensure_one()
        att_id = mattribute
        value = attribute['value']
        custom_vals = {
            'attribute_id': att_id.id,
            'attribute_text': value,
            'attribute_select': False,
            'attribute_multiselect': False,
        }

        if att_id.frontend_input == 'boolean':
            custom_vals.update({'attribute_text': str(int(value))})
        if att_id.frontend_input == 'select':
            value_ids = att_id.magento_attribute_value_ids
            select_value = value_ids.filtered(
                lambda v: v.external_id.split('_')[1] == value)

            custom_vals.update({
                'attribute_text': False,
                'attribute_multiselect': False,
                'attribute_select': select_value.magento_bind_ids[0].id or False
            })
        if att_id.frontend_input == 'multiselect':
            if not isinstance(value, list ):
                value = [value]
            value_ids = att_id.magento_attribute_value_ids
            select_value_ids = value_ids.filtered(
                lambda v:
                    v.external_id.split('_')[1] in value
            )
            custom_vals.update({
                'attribute_text': False,
                'attribute_select': False,
                'attribute_multiselect': [(6, False, [v.id for v in select_value_ids])]
            })
   
        return custom_vals


    @api.constrains('attribute_id')
    def check_attribute_id(self):
        self.ensure_one()
        res = self
        if 'no_update' in self._context and \
            self._context.get('no_update', False):
            return
        if res.odoo_field_name.id != False:
            odoo_field_name = res.odoo_field_name
            custom_vals = {
                    odoo_field_name.name: res.attribute_text,
            }
            if res.magento_attribute_type == 'boolean':
                custom_vals.update({
                    odoo_field_name.name: int(res.attribute_text),
                    })
            if res.magento_attribute_type == 'select':
                custom_vals.update({
                    odoo_field_name.name: res.attribute_select.odoo_id.id,
                    })
            if res.magento_attribute_type == 'multiselect':
                custom_vals.update({
                    odoo_field_name.name: [
                        (6, False, 
                         [s.odoo_id.id for s in res.attribute_multiselect])
                        ],
                    })
            
            res.product_id.with_context(no_update=True).write(custom_vals)
        
    _sql_constraints = [
        ('custom_attr_unique_product_uiq', 'unique(attribute_id, product_id, backend_id)', 'This attribute already have a value for this product !')
    ]

