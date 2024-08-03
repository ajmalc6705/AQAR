# -*- coding: utf-8 -*-


from odoo import models, api, fields, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_type_id = fields.Many2one('purchase.type', string='Purchase Type')
    project_id = fields.Many2one('project.project', string='Project', domain=[('is_assignment', '=', False)])
    contact_person = fields.Char(string='Contact Person')
    co_stamp_seal = fields.Binary(string="Company  Stamp")

    @api.onchange('requisition_id')
    def _onchange_project_id(self):
        for rec in self:
            if rec.requisition_id:
                rec.project_id = rec.requisition_id.project_id

    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        company_id = self.env.company
        if company_id:
            defaults['co_stamp_seal'] = company_id.co_stamp_seal
        return defaults



class PurchaseType(models.Model):
    _name = 'purchase.type'
    _description = 'Purchase Type'

    name = fields.Char(string='Name')


class ResCompany(models.Model):
    _inherit = 'res.company'

    header = fields.Html(string='Header')
    footer = fields.Html(string='Footer')
    co_stamp_seal = fields.Binary(string="Company  Stamp")
