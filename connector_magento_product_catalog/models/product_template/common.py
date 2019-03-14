# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib
import ast
from lxml import etree
from odoo.osv.orm import setup_modifiers
from odoo import api, models, fields
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.queue_job.job import identity_exact

_logger = logging.getLogger(__name__)



class MagentoProductTemplate(models.Model):
    _name = 'magento.product.template'
    _inherit = 'magento.binding'
    _inherits = {'product.template': 'odoo_id'}
    _description = 'Magento Product Template'
    
    @api.model
    def product_type_get(self):
        return [
            ('simple', 'Simple Product'),
            ('configurable', 'Configurable Product'),
            ('virtual', 'Virtual Product'),
            ('downloadable', 'Downloadable Product'),
            ('giftcard', 'Giftcard')
            # XXX activate when supported
            # ('grouped', 'Grouped Product'),
            # ('bundle', 'Bundle Product'),
        ]

    @api.depends('odoo_id',)
    @api.multi
    def _is_configurable(self):
        self.ensure_one()
        self.product_type = 'simple'
        if self.odoo_id.product_variant_count > 1:
            self.product_type = 'configurable'
        
    attribute_set_id = fields.Many2one('magento.product.attributes.set',
                                       
                                       string='Attribute set')
    
        
    odoo_id = fields.Many2one(comodel_name='product.template',
                              string='Product Template',
                              required=True,
                              ondelete='restrict')
    # XXX website_ids can be computed from categories
    website_ids = fields.Many2many(comodel_name='magento.website',
                                   string='Websites',
                                   readonly=True)
    
    created_at = fields.Date('Created At (on Magento)')
    updated_at = fields.Date('Updated At (on Magento)')
    product_type = fields.Selection(selection='product_type_get',
                                    string='Magento Product Type',
                                    compute=_is_configurable,
                                    required=True)
    
    magento_template_attribute_line_ids = fields.One2many(
                    comodel_name='magento.custom.template.attribute.values', 
                    inverse_name='magento_product_template_id', 
                    string='Magento Simple Custom Attributes Values for templates',
                                        )
    
    
    @api.multi
    def export_product_template_button(self, fields=None):
        self.ensure_one()
        self.with_delay(priority=20,
                        identity_key=identity_exact).export_product_template()

        
    @job(default_channel='root.magento')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_product_template(self, fields=None):
        """ Export the attributes configuration of a product. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            #TODO make different usage
            exporter = work.component(usage='record.exporter')
            return exporter.run(self)
        
        
    def action_magento_template_custom_attributes(self):
        action = self.env['ir.actions.act_window'].for_xml_id(
            'connector_magento_product_catalog', 
            'action_magento_custom_template_attributes')
        
        action['domain'] = unicode([('magento_product_template_id', '=', self.id)])
        ctx = action.get('context', '{}') or '{}'
        
        action_context = ast.literal_eval(ctx)
        action_context.update({
            'default_attribute_set_id': self.attribute_set_id.id,
            'default_magento_product_template_id': self.id,
            'search_default_wt_odoo_mapping': True})
#         
# #         action_context = ctx
#         action_context.update({
#             'default_project_id': self.project_id.id})
        action['context'] = action_context
        return action
        
    @api.model
    def create(self, vals):
        mg_prod_id = super(MagentoProductTemplate, self).create(vals)
        attributes = mg_prod_id.attribute_set_id.attribute_ids
        cstm_att_mdl = self.env['magento.custom.template.attribute.values']
        for att in attributes:
            vals = {
                'magento_product_template_id': mg_prod_id.id,
                'attribute_id': att.id,
                }
            if not self._context.get('from_copy', False):
                cstm_att_mdl.create(vals)
        return mg_prod_id
    
    

    @api.multi
    def check_field_mapping(self, field, vals):
        # Check if the Odoo Field has a matching attribute in Magento
        # Update the value
        # Return an appropriate dictionnary
        self.ensure_one()
#         att_id = 0
        
        if self._context.get('from_copy', False):
            return
        custom_model = self.env['magento.custom.template.attribute.values']
        odoo_fields = self.env['ir.model.fields'].search([
                    ('name', '=', field),
                    ('model', 'in', [ 'product.template'])])
        
        att_ids = self.env['magento.product.attribute'].search(
            [('odoo_field_name', 'in', [o.id for o in odoo_fields]),
             ('backend_id', '=', self.backend_id.id)
             ])
        
        if len(att_ids) > 0:
            att_id = att_ids[0]
            values = custom_model.search(
                [('magento_product_template_id', '=', self.id),
                 ('attribute_id', '=', att_id.id)
                 ])
            custom_vals = {
                    'magento_product_template_id': self.id,
                    'attribute_id': att_id.id,
                    'attribute_text': self[field],
                    'attribute_select': False,
                    'attribute_multiselect': False,
            }
            odoo_field_type = odoo_fields[0].ttype
            if odoo_field_type in ['many2one', 'many2many'] \
                    and 'text' in att_id.frontend_input:
                custom_vals.update({
                    'attribute_text': str(
                        [v.magento_template_bind_ids.external_id for v in self[field]
                         ])})
            
            if att_id.frontend_input == 'boolean':
                custom_vals.update({
                    'attribute_text': str(int(self[field]))})
            if att_id.frontend_input == 'select':
                custom_vals.update({
                    'attribute_text': False,
                    'attribute_multiselect': False,
                    'attribute_select': self[field].magento_template_bind_ids[0].id})
            if att_id.frontend_input == 'multiselect':
                custom_vals.update({
                    'attribute_text': False,
                    'attribute_multiselect': False,
                    'attribute_multiselect': 
                    [(6, False, [
                        v.id for v in self[field].magento_template_bind_ids] )]})
            if len(values) == 0:    
                custom_model.with_context(no_update=True).create(custom_vals)
            else:
                values.with_context(no_update=True).write(custom_vals)
    
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    
    magento_template_bind_ids = fields.One2many(
        comodel_name='magento.product.template',
        inverse_name='odoo_id',
        string='Magento Template Bindings',
    )     
   
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        context = self._context
        res = super(ProductTemplate, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

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
   

    @api.multi
    def write(self, vals):
        org_vals = vals.copy()
        res = super(ProductTemplate, self).write(vals)
#         variant_ids = self.product_variant_ids
#         prod_ids = variant_ids.filtered(lambda p: len(p.magento_bind_ids) > 0)
        for tpl  in self:
            for prod in tpl.magento_template_bind_ids:
                for key in org_vals :
                    prod.check_field_mapping(key, vals)
        return res              


    
    @api.multi
    def copy(self, default=None):
        self_copy = self.with_context(from_copy=True)
        new = super(ProductTemplate, self_copy).copy(default=default)
        for mg_prod_id in self.magento_template_bind_ids:
            new_mg_prod_id = mg_prod_id.with_context(from_copy=True).copy({
                'external_id': False,
                'odoo_id': new.id
                })
            
            values = self.env['magento.custom.template.attribute.values'].search(
                [('product_template_id', '=', self.id)])
            
            for val in values:
                vals = val.copy_data({
                    'magento_product_template_id': new_mg_prod_id.id
                    })
                new_val_id = self.env['magento.custom.template.attribute.values'].\
                            with_context(from_copy=True).create(vals[0])
        return new




class ProductTemplateAdapter(Component):
    _name = 'magento.product.template.adapter'
    _inherit = 'magento.adapter'
    _apply_on = 'magento.product.template'
    
    _magento_model = 'catalog_product'
    _magento2_model = 'products'
    _magento2_search = 'products'
    _magento2_key = 'sku'
    _admin_path = '/{model}/edit/id/{id}'
    
    
    def create(self, data):
        """ Create a record on the external system """
        if self.work.magento_api._location.version == '2.0': 
            datas = self.get_product_datas(data)
            datas['product'].update(data)
            new_product = super(ProductTemplateAdapter, self)._call(
                'products', datas , 
                http_method='post')            
            return new_product['id']
             
             
        return self._call('%s.create' % self._magento_model,
                          [customer_id, data])
    
    
    
    def get_product_datas(self, data, id=None, saveOptions=True):
        """ Hook to implement in other modules"""
        visibility = 4 
        
        product_datas = {
            'product': {
                "sku": data['sku'] or data['default_code'],
                "name": data['name'],
                "attributeSetId": data['attributeSetId'],
                "price": 0,
                "status": 1,
                "visibility": visibility,
                "typeId": data['typeId'],
                "weight": data['weight'] or 0.0,
#                           
            }
            ,"saveOptions": saveOptions
            }
        if id is None:
            product_datas['product'].update({'id': 0})
        return product_datas


    def write(self, id, data, storeview_id=None):
        """ Update records on the external system """
        # XXX actually only ol_catalog_product.update works
        # the PHP connector maybe breaks the catalog_product.update
        if self.work.magento_api._location.version == '2.0':
            datas = self.get_product_datas(data, id)
            datas['product'].update(data)
            _logger.info("Prepare to call api with %s " % datas)
            #Replace by the 
            id  = data['sku']
            super(ProductTemplateAdapter, self)._call(
                'products/%s' % id, datas, 
                http_method='put')
            
            stock_datas = {"stockItem":{
                'is_in_stock': True}}
            return super(ProductTemplateAdapter, self)._call(
                    'products/%s/stockItems/1' % id, 
                    stock_datas, 
                    http_method='put')
#             raise NotImplementedError  # TODO
        return self._call('ol_catalog_product.update',
                          [int(id), data, storeview_id, 'id'])
