# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class ProductMediaDeleter(Component):
    """ Base deleter for Magento """
    _name = 'magento.product.media.deleter'
    _inherit = 'magento.exporter.deleter'
    _apply_on = ['magento.product.media']

