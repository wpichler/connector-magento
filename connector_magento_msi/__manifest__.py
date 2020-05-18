# -*- coding: utf-8 -*-
# © 2020 Wolfgang Pichler, Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Magento Connector MSI',
    'version': '12.0.1.0.0',
    'category': 'Connector',
    'depends': ['connector_magento', 'stock'],
    'external_dependencies': {
        'python': ['magento'],
    },
    'author': "Callino,Odoo Community Association (OCA)",
    'license': 'AGPL-3',
    'website': 'http://www.odoo-magento-connector.com',
    'data': [
             'views/magento_backend_views.xml',
             'views/stock_item.xml',
             'views/warehouse.xml',
             ],
    'installable': True,
    'application': False,
}
