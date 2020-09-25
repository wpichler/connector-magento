# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class ProductMediaDeleter(Component):
    """ Base deleter for Magento """
    _name = 'magento.product.media.deleter'
    _inherit = 'magento.exporter.deleter'
    _apply_on = ['magento.product.media']

    def run(self, external_id):
        """ Run the synchronization, delete the record on Magento

        :param external_id: identifier of the record to delete
        """
        self.backend_adapter.delete(external_id)
        return 'Record %s deleted on Magento' % (external_id,)
