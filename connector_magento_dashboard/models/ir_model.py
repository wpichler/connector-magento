from odoo.addons import base
if 'connector_magento_dashboard' not in base.models.ir_actions.VIEW_TYPES:
    base.models.ir_actions.VIEW_TYPES.append(('connector_magento_dashboard', 'Magento Dashboard'))
