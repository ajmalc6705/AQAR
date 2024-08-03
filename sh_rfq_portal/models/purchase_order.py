# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api
import xlwt
from odoo.exceptions import UserError
import base64
import io
from datetime import timedelta

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    sh_supplier_note = fields.Text('Supplier Note ')
    sh_allow_portal_access = fields.Boolean('Allow Portal Access ?')
    sh_time_limit = fields.Integer('Time Limit')
    sh_last_date_of_portal_access = fields.Date('Last date of portal access')
    sh_bid_updated = fields.Boolean('Bid Updated',copy=False)

    @api.onchange('sh_last_date_of_portal_access')
    def onchange_sh_last_date_of_portal_access(self):
        """Method for deactivate portal access of each rfq based on time limit"""
        self.ensure_one()
        if self.sh_last_date_of_portal_access:
            delta = self.sh_last_date_of_portal_access - fields.Date.today()
            self.sh_time_limit = delta.days
        if self.sh_last_date_of_portal_access and self.sh_last_date_of_portal_access < fields.Date.today():
            self.sh_allow_portal_access = False

    @api.onchange('sh_allow_portal_access','sh_time_limit')
    def onchange_sh_time_limit(self):
        """Calculated Last date of portal access based on time limit params"""
        self.ensure_one()
        if self.sh_allow_portal_access:
            self.sh_last_date_of_portal_access = fields.Date.today() + timedelta(days=self.sh_time_limit)
        else:
            self.sh_last_date_of_portal_access = False

    @api.model
    def _run_auto_deactivate_po_portal_access(self):
        """Scheduler for deactivate portal access of each rfq based last date of portal access"""
        orders = self.env['purchase.order'].sudo().search([('sh_allow_portal_access','=',True),('sh_last_date_of_portal_access','!=',False)])
        if orders:
            for order in orders:
                if order.sh_last_date_of_portal_access == fields.Date.today():
                    order.sh_allow_portal_access = False
                    order.sh_last_date_of_portal_access = False

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s %s' % ('Purchase', self.name)

    #method for rfq xls report file
    def action_rfq_xls(self):
        self.ensure_one()
        workbook = xlwt.Workbook()
        worksheet = False
        if self.state in ['draft','sent']:
            worksheet = workbook.add_sheet('Request For Quotation')
        elif self.state in ['purchase','done']:
            worksheet = workbook.add_sheet('Purchase Order')
        elif self.state in ['cancel']:
            worksheet = workbook.add_sheet('Cancelled Purchase')
        bold_normal = xlwt.easyxf(
            'font:height 200,bold True;align: vert center;align: horiz center;'
        )
        header = xlwt.easyxf(
            'font:height 200,bold True;align: vert center;align: horiz center;pattern: pattern solid, fore_colour gray25;'
        )
        bold = xlwt.easyxf(
            'font:height 300,bold True;align: vert center;align: horiz center;pattern: pattern solid, fore_colour gray25;'
        )
        normal = xlwt.easyxf('font:height 200;align: vert top;')
        normal_data = xlwt.easyxf(
            'font:height 200;align: vert center;align: horiz center;')
        worksheet.col(0).width = 8000
        worksheet.col(1).width = 8000
        worksheet.col(2).width = 8000
        worksheet.col(3).width = 8000
        worksheet.col(4).width = 8000
        worksheet.col(5).width = 8000
        worksheet.col(6).width = 8000
        worksheet.col(7).width = 8000
        worksheet.col(8).width = 8000
        worksheet.col(9).width = 8000
        worksheet.col(10).width = 8000
        worksheet.col(11).width = 8000
        worksheet.write_merge(1, 1, 0, 0, 'Shipping Address', bold_normal)
        company_address = ''
        if self.env.company.city:
            company_address+=self.env.company.city
        if self.env.company.street:
            company_address+='\n' + self.env.company.street
        if self.env.company.state_id:
            company_address+='\n' + self.env.company.state_id.name
        if self.env.company.country_id:
            company_address+='\n' + self.env.company.country_id.name
        if self.env.company.phone:
            company_address+='\n' + self.env.company.phone
        partner_address = ''
        if self.partner_id:
            partner_address+=self.partner_id.name
        if self.partner_id.street:
            partner_address+='\n' + self.partner_id.street
        if self.partner_id.state_id:
            partner_address+='\n' + self.partner_id.state_id.name
        if self.partner_id.country_id:
            partner_address+='\n' + self.partner_id.country_id.name
        if self.partner_id.phone:
            partner_address+='\n' + self.partner_id.phone
        worksheet.write_merge(
            1, 5, 1, 2,company_address, normal)
        worksheet.write_merge(
            1, 5, 3, 4, partner_address, normal)
        if self.state in ['draft','sent']:
            worksheet.write_merge(10, 10, 0, 4, 'Request for Quotation ' + self.name,bold)
        elif self.state in ['purchase','done']:
            worksheet.write_merge(10, 10, 0, 4, 'Purchase Order ' + self.name,bold)

        worksheet.write_merge(13, 13, 0, 0, 'Description', header)
        worksheet.write_merge(13, 13, 1, 1, 'Product Ref', header)
        worksheet.write_merge(13, 13, 2, 2, 'Expected Date', header)
        worksheet.write_merge(13, 13, 3, 3, 'Qty', header)
        worksheet.write_merge(13, 13, 4, 4, 'Unit Price', header)

        line_var = 14
        if self.order_line:
            for line in self.order_line:
                if not line.display_type:
                    worksheet.write_merge(line_var, line_var, 0, 0,
                                        line.name, normal_data)
                    worksheet.write_merge(line_var, line_var, 1, 1,
                                        line.product_id.default_code or '', normal_data)
                    worksheet.write_merge(line_var, line_var, 2, 2,
                                        str(line.date_planned) or '', normal_data)
                    worksheet.write_merge(line_var, line_var, 3, 3,
                                        line.product_qty or 0.0, normal_data)
                    worksheet.write_merge(line_var, line_var, 4, 4,
                                        line.price_unit or 0.0, normal_data)
                if line.display_type == 'line_section':
                    worksheet.write_merge(line_var, line_var, 0, 12,
                                        line.name or 0.0, bold_normal)
                if line.display_type == 'line_note':
                    worksheet.write_merge(line_var, line_var, 0, 12,
                                        line.name or 0.0, bold_normal)
                line_var = line_var + 1

        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {}
        if self.state in ['draft','sent']:
            attachment_vals.update({
                "name": "Request for quotation.xls",
                "res_model": "purchase.order",
                "type": "binary",
                "res_id":self.id,
                "datas": data,
                "public": True,
            })
        elif self.state in ['purchase','done']:
            attachment_vals.update({
                "name": "Purchase Order.xls",
                "res_model": "purchase.order",
                "res_id":self.id,
                "type": "binary",
                "datas": data,
                "public": True,
            })
        elif self.state in ['cancel']:
            attachment_vals.update({
                "name": "Cancelled Purchase Order.xls",
                "res_model": "purchase.order",
                "res_id":self.id,
                "type": "binary",
                "datas": data,
                "public": True,
            })
        fp.close()
        if self.state in ['draft','sent']:
            attachment = IrAttachment.search(
                [('name', '=', 'Request For Quotation'), ('type', '=', 'binary'),
                ('res_model', '=', 'purchase.order')],
                limit=1)
            if attachment:
                attachment.write(attachment_vals)
            else:
                attachment = IrAttachment.create(attachment_vals)
            #TODO: make user error here
            if not attachment:
                raise UserError('There is no attachments...')

            url = "/web/content/" + str(attachment.id) + "?download=true"
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
                'attachment':attachment,
            }
        elif self.state in ['purchase','done']:
            attachment = IrAttachment.search(
                [('name', '=', 'Purchase Order'), ('type', '=', 'binary'),
                ('res_model', '=', 'purchase.order')],
                limit=1)
            if attachment:
                attachment.write(attachment_vals)
            else:
                attachment = IrAttachment.create(attachment_vals)
            #TODO: make user error here
            if not attachment:
                raise UserError('There is no attachments...')

            url = "/web/content/" + str(attachment.id) + "?download=true"
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
                'attachment':attachment,
            }
        elif self.state in ['cancel']:
            attachment = IrAttachment.search(
                [('name', '=', 'Purchase Order'), ('type', '=', 'binary'),
                ('res_model', '=', 'purchase.order')],
                limit=1)
            if attachment:
                attachment.write(attachment_vals)
            else:
                attachment = IrAttachment.create(attachment_vals)
            #TODO: make user error here
            if not attachment:
                raise UserError('There is no attachments...')

            url = "/web/content/" + str(attachment.id) + "?download=true"
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
                'attachment':attachment,
            }

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sh_tender_note = fields.Char('Note/Comment')
