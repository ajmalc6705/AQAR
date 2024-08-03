# -*- coding: utf-8 -*-

from odoo import models,fields,api,_

class AqarInsurance(models.Model):
    _name = 'aqar.insurance'
    _description = 'Insurance'
    _rec_name = 'ref'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    ref = fields.Char(string='Doc Number', copy=False,
                      readonly=True,
                      index=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee',string='Employee')
    insurance_company_id = fields.Many2one('res.partner',string='Insurance Company')
    period = fields.Integer(string='Period')
    coverage_amount = fields.Monetary(string='Coverage Amount')
    insurance_type_id = fields.Many2one('insurance.type',string='Insurance Type')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('cancel', 'Cancel')], string='Status',
                             default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code(
                    'insurance.sequence') or 'New'
        res = super(AqarInsurance, self).create(vals_list)
        return res

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_approve(self):
        self.write({'state': 'confirm'})


class InsuranceType(models.Model):
    _name = 'insurance.type'
    _description = "Employee Insurance Type"
    _rec_name = 'name'

    name = fields.Char(string='Name')