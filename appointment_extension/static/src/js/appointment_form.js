odoo.define('appointment_extension.attachment', function (require) {
'use strict';
    var publicWidget = require('web.public.widget');
    console.log("dataa")
    var ajax = require('web.ajax');
     var core = require('web.core');
    var session = require('web.session');
    publicWidget.registry.add_attachment = publicWidget.Widget.extend({
        selector: '.div-class-button',
        events: {
            'click #button_add_attachment_payment': 'AttachmentPaymentOnClick',
        },
         AttachmentPaymentOnClick: function (ev) {
         var attachments = ev.target
         var attachment_id = ev.target.closest('div')
         var attachment_name = $(ev.target).parent().find('.file')[0].files[0].name
         var fileInput = $(ev.target).parent().find('.file')[0];  // Get the file input element
         var attachment_file = fileInput.files[0];
         var name = $(ev.target).parent().find('#attachment_name')
         var file = $(ev.target).parent().find('#attachment_file')
         console.log("name",name)
         name.val(attachment_name)
         ev.target.remove();
         console.log("nameeeeee",name)

            // Get the file input element
         var reader = new FileReader();
         reader.onload = function(event){
         var fileContent = event.target.result;
         file.val(fileContent);
         },
            reader.readAsDataURL(attachment_file);  // Read the file content as a data URL
         },
    });
    return publicWidget.registry.add_attachment
});