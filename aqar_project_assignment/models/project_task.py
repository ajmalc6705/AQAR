# -*- coding: utf-8 -*-

from odoo import models,fields,api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    type_of_task = fields.Selection([('property','Property'),('general','General')],string='Type of Task',)
    building_id = fields.Many2one('property.building',string='Building')
    property_id = fields.Many2one('property.property',string='Unit')
    is_assignment = fields.Boolean(string='Is Assignment')
    project_ids = fields.Many2many('project.project',string='Project',compute='_compute_project')

    @api.depends('company_id')
    def _compute_project(self):
        self.project_ids = False
        for rec in self:
            if rec.is_assignment:
                projects = self.env['project.project'].search([('is_assignment','=',True)])
                rec.project_ids = projects.mapped('id')
            else:
                projects = self.env['project.project'].search([('is_assignment','=',False)])
                rec.project_ids = projects.mapped('id')




    @api.model_create_multi
    def create(self, vals_list):
        leads = super(ProjectTask, self).create(vals_list)
        for vals in vals_list:
            project_id = self.env['project.project'].browse(vals['project_id'])
            if project_id.is_assignment:
                leads.is_assignment = True
        return leads


class Project(models.Model):
    _inherit = 'project.project'

    is_assignment = fields.Boolean(string='Is Assignment')