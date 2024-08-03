# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import http
from odoo.http import request
from odoo.addons.purchase.controllers.portal import CustomerPortal
from odoo.addons.web.controllers.main import Binary
from odoo.exceptions import AccessError, MissingError


class PurchaseRFQPortal(CustomerPortal):

    def sh_rfq_portal_xls(self, quote):
        """Method for Download rfq xls report"""
        quote_action = quote.action_rfq_xls()
        return request.redirect(quote_action.get('url'))

    @http.route(['/my/purchase/<int:order_id>'], type='http', auth="public", website=True)
    def portal_my_purchase_order(self, order_id=None, access_token=None, **kw):
        """Controller for purchase order portal form view"""
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        report_type = kw.get('report_type')
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=order_sudo, report_type=report_type, report_ref='purchase.action_report_purchase_order', download=kw.get('download'))
        if report_type == 'sh_rfq_portal_xls':
            return self.sh_rfq_portal_xls(order_sudo)
        confirm_type = kw.get('confirm')
        if confirm_type == 'reminder':
            order_sudo.confirm_reminder_mail(kw.get('confirmed_date'))
        if confirm_type == 'reception':
            order_sudo._confirm_reception_mail()

        values = self._purchase_order_get_page_view_values(order_sudo, access_token, **kw)
        update_date = kw.get('update')
        if order_sudo.company_id:
            values['res_company'] = order_sudo.company_id
        if update_date == 'True':
            return request.render("purchase.portal_my_purchase_order_update_date", values)
        return request.render("purchase.portal_my_purchase_order", values)

    @http.route(['/my/rfq/update/<int:quote_id>'], type='http', auth="user", website=True)
    def portal_my_rfqs_update(self, quote_id=None, report_type=None, access_token=None, message=False, download=False, **kw):
        """Controller for update bid portal form view where all values are readonly"""
        quote_sudo = request.env['purchase.order'].sudo().browse(quote_id)
        try:
            quote = request.env['purchase.order'].sudo().browse(quote_id)
            if quote.sh_allow_portal_access:
                if access_token:
                    if quote.state in ['purchase']:
                        return request.redirect('/my')
                    else:
                        quote_sudo = self._document_check_access('purchase.order', quote_id, access_token=access_token)
                else:
                    if quote.state in ['purchase']:
                        return request.redirect('/my')
                    else:
                        if request.env.user.partner_id.id == quote.partner_id.id:
                            quote_sudo = self._document_check_access('purchase.order', quote_id, access_token=None)
                        else:
                            return request.redirect('/my')
            else:
                if quote.state in ['purchase']:
                    return request.redirect('/my')
                else:
                    if request.env.user.partner_id.id == quote.partner_id.id:
                        quote_sudo = self._document_check_access('purchase.order', quote_id, access_token=None)
                    else:
                        return request.redirect('/my')
        except (AccessError, MissingError):
            return request.redirect('/my')
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=quote_sudo, report_type=report_type, report_ref='purchase.report_purchase_quotation', download=download)
        values = {
            'token': access_token,
            'quotes': quote_sudo,
            'page_name': 'rfq',
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.partner_id.id,
            'report_type': 'html',
        }
        return request.render("sh_rfq_portal.sh_portal_my_rfq_order_update", values)

    @http.route(['/rfq/update'], type='http', auth="public", website=True, csrf=False)
    def custom_rfq_update(self, access_token=None, **kw):
        """Route for Update bid function based on Update bid button"""
        if kw.get('order_id'):
            purchase_order = request.env['purchase.order'].sudo().search(
                [('id', '=', kw.get('order_id'))], limit=1)
            if purchase_order:
                if purchase_order.order_line:
                    for k, v in kw.items():
                        if k != 'currency_id' and k != 'order_id' and '_' not in k and k!='rfq_note':
                            purchase_order_line = request.env['purchase.order.line'].sudo().search(
                                [('order_id', '=', purchase_order.id), ('id', '=', k)], limit=1)
                            if purchase_order_line:
                                price = v
                                if ',' in price:
                                    price = price.replace(",", ".")
                                purchase_order_line.sudo().write({
                                    'price_unit':float(price),
                                    })
                        if k != 'currency_id' and k != 'order_id' and '_' in k and k!='rfq_note':
                            order_line = k.split("_note")
                            purchase_order_line = request.env['purchase.order.line'].sudo().search(
                                [('order_id', '=', purchase_order.id), ('id', '=', int(order_line[0]))], limit=1)
                            if purchase_order_line:
                                note = v
                                purchase_order_line.sudo().write({
                                    'sh_tender_note':note,
                                    })
                        if k=='rfq_note':
                            note = kw.get(k)
                            purchase_order.sudo().write({
                                'sh_supplier_note':note
                                })
                        if k == 'currency_id':
                            if kw.get(k) !='currency':
                                purchase_order.sudo().write({
                                    'currency_id':int(kw.get(k)),
                                })
                                if purchase_order.order_line:
                                    for line in purchase_order.order_line:
                                        line.currency_id = int(kw.get(k))
        url = ''
        po_id = request.env['purchase.order'].sudo().browse(int(kw.get('order_id')))
        if po_id:
            po_id.sh_bid_updated = True
            po_id.state = 'sent'
            if po_id.company_id and po_id.company_id.sh_notify_purchase_representative_po and po_id.user_id:
                request.env['sh.user.push.notification'].sudo().create_user_notification(user=po_id.user_id,name=po_id.name,description="Bid updated from supplier",res_model="purchase.order",res_id=po_id.id)
        if po_id and po_id.sh_allow_portal_access:
            url = '/my/rfq/update/'+str(kw.get('order_id'))+'?access_token='+po_id.access_token
        elif po_id and not po_id.sh_allow_portal_access:
            url = '/my/rfq/update/'+str(kw.get('order_id'))
        return request.redirect(url)

    @http.route(['/rfq/edit'], type='http', auth="user", website=True, csrf=False)
    def custom_rfq_edit(self, **kw):
        """Ruote for Edit Bid Portal Form view"""
        url = '/my/purchase/'+str(kw.get('order_id'))
        return request.redirect(url)

    @http.route(['/rfq/cancel/new'], type='json', auth="public", website=True, csrf=False)
    def cancel_new_rfq(self, **kw):
        """Route For Cancel current rfq and create new rfq based on button click of Cancel and create new"""
        if kw.get('order_id'):
            old_purchase_order_id = request.env['purchase.order'].sudo().browse(int(kw.get('order_id')))
            new_purchase_order_id = False
            if old_purchase_order_id:
                new_purchase_order_id = old_purchase_order_id.copy()
                if new_purchase_order_id:
                    old_purchase_order_id.state = 'cancel'
            url = ''
            if new_purchase_order_id.sh_allow_portal_access:
                url = new_purchase_order_id.get_portal_url()
            else:
                url = '/my/purchase/'+str(new_purchase_order_id.id)
            if url:
                dic = {'url':url}
                return dic
