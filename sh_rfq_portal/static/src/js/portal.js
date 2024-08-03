odoo.define("sh_rfq_portal.update_bid", function (require) {
    "use strict";
    require("web.dom_ready");
    var concurrency = require("web.concurrency");
    var core = require("web.core");
    var publicWidget = require("web.public.widget");
    publicWidget.registry.sh_rfq_portal = publicWidget.Widget.extend({
    	selector:"#rfq_content,#quote_content",
    	events: {
            'click .cancel_2': '_onClickCancelBid',
            'click .btn_cancel_bid_new_modal':'_onClickYesButton',
            'click .cancel_and_create_new':'_onClickCancelUpdated'
        },
        start: function () {
            var def = this._super.apply(this, arguments);
            return def;
        },
        
        /*Click method of cancel bid button to open bootstrap cancel modal*/
        _onClickCancelBid: function (ev) {
        	ev.preventDefault();
        	var self = this;
            $('.cancel_bid_update').modal('show');
        },
        /*Click method of cancel bid button to open bootstrap cancel modal*/
        _onClickCancelUpdated: function (ev) {
        	ev.preventDefault();
        	var self = this;
            $('.cancel_bid_new').modal('show');
        },
        /*Click method of cancel old rfq and create new from bootstrap modal*/
        _onClickYesButton: function (ev) {
        	ev.preventDefault();
        	var self = this;
        	return this._rpc({
                route: "/rfq/cancel/new",
                params: {order_id: $('#order_id').val()},
            }).then((data) => {
                _.each(data, function (record) {
                    window.location.href = record;
                });
            });
        },
    });
});
