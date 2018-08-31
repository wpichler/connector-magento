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

    
class CustomAttribute(models.Model):
    _name = 'magento.custom.attribute.values'
     
    """
    This class deal with customs Attrinutes
    """
    
    product_id = fields.Many2one(comodel_name="product.product",
                                string="Product")
 
    backend_id = fields.Many2one(comodel_name="magento.backend",
                                      string="Magento Backend",
                                      related="attribute_id.backend_id")
     
    attribute_id = fields.Many2one(comodel_name="magento.product.attribute",
                                      string="Magento Product Attribute",
                                      required=True)

        
    magento_attribute_type = fields.Selection(
        related="attribute_id.frontend_input")
    
    odoo_field_name = fields.Many2one(comodel_name='ir.model.fields', 
                                      related="attribute_id.odoo_field_name", 
                                      string="Odoo Field Name",) 
    
    attribute_text = fields.Char(string='Magento Text / Value',
                                    size=264,
                                    translate=True
                                    )

    
    _sql_constraints = [
        ('custom_attr_unique_product_uiq', 'unique(attribute_id, product_id, backend_id)', 'This attribute already have a value for this product !')
    ]

