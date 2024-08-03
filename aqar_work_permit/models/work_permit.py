# -*- coding: utf-8 -*-


from odoo import models, fields, api, _


class HrWorkPermit(models.Model):
    _name = 'hr.work.permit'
    _description = 'Hr Work Permit'
    _rec_name = 'ref'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    ref = fields.Char(string='Number', copy=False,
                      readonly=True,
                      index=True, default=lambda self: _('New'))
    name = fields.Char(string='Name')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female'), ('others', 'Others')], string='Gender')
    job_id = fields.Many2one('hr.job', string='Job Title')
    partner_id = fields.Many2one('res.partner', string='Visa Company')
    utilized_workers = fields.Integer(string='Utilized Workers', compute='_compute_workers')
    notes = fields.Html(string='Remarks')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('cancel', 'Cancel')], string='Status',
                             default='draft')

    @api.depends('company_id')
    def _compute_workers(self):
        self.utilized_workers = False
        for rec in self:
            employee = self.env['hr.employee'].search_count([('work_permit_id', '=', rec.id)])
            rec.utilized_workers = employee

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code(
                    'work.permit.sequence') or 'New'
        res = super(HrWorkPermit, self).create(vals_list)
        return res

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, '%s - %s' % (rec.ref, rec.partner_id.name)))

        return result

    def action_cancel(self):
        """ function which triggers in cancel button"""
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        """ function that triggers when reset to draft button"""
        self.write({'state': 'draft'})

    def action_approve(self):
        self.write({'state': 'confirm'})


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    work_permit_id = fields.Many2one('hr.work.permit', string='Work Permit')


class HrEmployeePublicWorkPermitInherit(models.Model):
    _inherit = 'hr.employee.public'

    work_permit_id = fields.Many2one('hr.work.permit', string='Work Permit')
