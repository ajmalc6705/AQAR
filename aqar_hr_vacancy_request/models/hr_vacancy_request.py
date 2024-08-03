# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrvacancyRequest(models.Model):
    _name = 'hr.vacancy.request'
    _description = 'Hr Vacancy Request'
    _rec_name = 'ref'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    ref = fields.Char(string='Number', copy=False,
                      readonly=True,
                      index=True, default=lambda self: _('New'))
    date = fields.Date(string='Date')
    dept_id = fields.Many2one('hr.department', string='Department')
    project_code = fields.Char(string='Project Code')
    job_position_based_on = fields.Selection([('new', 'New'), ('existing', 'Existing')], string='Job Position',
                                             default='new')
    job_id = fields.Many2one('hr.job', string='Job Title')
    job_name = fields.Char(string='Job Title')
    existing_target = fields.Integer(string='Existing Target', related='job_id.no_of_recruitment')
    target = fields.Integer(string='Target')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    skill_ids = fields.Many2many('hr.skill', string='Skill')
    educational_qualification_ids = fields.Many2many('educational.qualifications')
    certification_ids = fields.Many2many('certifications')
    notes = fields.Html(string='Other Specifications')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('cancel', 'Cancel')], string='Status',
                             default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code(
                    'vacancy.sequence') or 'New'
        res = super(HrvacancyRequest, self).create(vals_list)
        return res

    def action_cancel(self):
        """ function which triggers in cancel button"""
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        """ function that triggers when reset to draft button"""
        self.write({'state': 'draft'})

    def action_approve(self):
        if self.job_position_based_on == 'new':
            job = self.env['hr.job'].create({
                'name': self.job_name,
                'department_id': self.dept_id.id,
                'no_of_recruitment': self.target,
                'company_id': self.company_id.id
            })
            self.job_id = job.id
        elif self.job_position_based_on == 'existing':
            self.job_id.no_of_recruitment = self.existing_target + self.target
        self.write({'state': 'confirm'})

    def get_job_position(self):
        """get the job position"""
        return {
            'type': 'ir.actions.act_window',
            'name': ('Job Position'),
            'view_mode': 'tree,form',
            'res_model': 'hr.job',
            'context': {'create': False},
            'domain': [('id', '=', self.job_id.id)],
        }


class EducationalQualification(models.Model):
    _name = 'educational.qualifications'
    _description = 'Educational Qualifications'

    name = fields.Char(string='Educational Qualification')
    type_name = fields.Char(string='Type')


class Certifications(models.Model):
    _name = 'certifications'
    _description = 'Certifications'

    name = fields.Char(string='Certification')
    type_name = fields.Char(string='Type')
