# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpc.client
from odoo import api, models, fields
from odoo.addons.queue_job.job import job, related_action
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class MagentoStockWarehouse(models.Model):
    _inherit = 'magento.stock.warehouse'

    mw_type = fields.Selection([
        ('magento', 'Magento Warehouse'),
        ('msi', 'MSI'),
    ], default="magento", string="Magento Warehouse Type")
