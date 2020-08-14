from odoo import api, fields, models


class ProductSync(models.Model):
    _name = 'magento.product.sync'
    _rec_name = 'name'
    _description = 'Product Sync Model'

    name = fields.Char()
    backend_id = fields.Many2one('magento.backend', required=True, string="Backend")
    magento_raw = fields.Text('Raw data from Magento')
    side = fields.Selection([
        ('magento', 'Magento'),
        ('odoo', 'Odoo Exported'),
        ('both', 'Both'),
    ], string="Side")
    magento_type_id = fields.Selection([
        ('configurable', 'Configurable'),
        ('bundle', 'Bundle'),
        ('simple', 'Simple'),
    ], string="Magento Produkt type")
    magento_sku = fields.Char('Magento SKU')
    magento_id = fields.Char('Magento ID')
    magento_price = fields.Float('Magento Price')
    magento_status = fields.Selection([
        ('2', 'Disabled'),
        ('1', 'Enabled'),
    ], default='1', string="Status")
    magento_visibility = fields.Selection([
        ('1', 'Not Visible'),
        ('2', 'In Catalog'),
        ('3', 'In Search'),
        ('4', 'Both'),
    ], string="Visibility")
    magento_url_key = fields.Char('Magento URL Key')
    magento_product_id = fields.Many2one('magento.product.product', string='Magento Product')
    magento_configurable_id = fields.Many2one(related='magento_product_id.magento_configurable_id', store=True)
    magento_template_id = fields.Many2one('magento.product.template', string='Magento Template')
    magento_bundle_id = fields.Many2one('magento.product.bundle', string='Magento Bundle')
    error = fields.Text('Error')

    def button_delete_binding(self):
        for sync in self:
            if sync.magento_product_id:
                sync.magento_product_id.unlink()
            if sync.magento_template_id:
                sync.magento_template_id.unlink()
            if sync.magento_bundle_id:
                sync.magento_bundle_id.unlink()

    def button_sync_from_magento(self):
        for sync in self:
            if sync.magento_type_id == 'configurable':
                sync.magento_template_id.sync_from_magento()
            if sync.magento_type_id == 'product':
                sync.magento_product_id.sync_from_magento()
            if sync.magento_type_id == 'bundle':
                sync.magento_bundle_id.sync_from_magento()
