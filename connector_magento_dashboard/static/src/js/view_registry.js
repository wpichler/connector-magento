odoo.define('connector_magento_dashboard._view_registry', function (require) {
    "use strict";

    var ConnectorMagentoDashboardView = require('connector_magento_dashboard.ConnectorMagentoDashboardView');
    var view_registry = require('web.view_registry');

    view_registry.add('connector_magento_dashboard', ConnectorMagentoDashboardView);
});
