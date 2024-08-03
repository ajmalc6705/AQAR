odoo.define('custom_base.settings', function (require) {
"use strict";

var BaseSettingRenderer = require('base.settings').Renderer;

BaseSettingRenderer.include({

    _getAppIconUrl: function (module) {
        if (module == 'visa_renewal') {
            return "atheer_hr/static/src/img/performance-management.png";
        }
        else {
            return this._super.apply(this, arguments);
        }
    }
});
});
