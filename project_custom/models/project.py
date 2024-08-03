# -*- coding: utf-8 -*-

import ast
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.addons.analytic.models.analytic_account import AccountAnalyticAccount as BaseAnalyticAccount
from odoo.addons.project.models.project import Project as BaseProject

_TASK_STATE = [
    ('draft', 'New'),
    ('open', 'In Progress'),
    ('pending', 'Pending'),
    ('done', 'Done'),
    ('cancelled', 'Cancelled')]


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    def name_get(self):
        if self._context.get('from_mr'):
            res = []
            for analytic in self:
                name = analytic.name
                if analytic.project_ids and analytic.project_ids.proj_code:
                    name = analytic.project_ids.proj_code
                res.append((analytic.id, name))
        else:
            res = super(AccountAnalyticAccount, self).name_get()
        return res

    def get_project_details(self):
        for rec in self:
            project_id = self.env['project.project'].search([('analytic_account_id', '=', rec.id)], limit=1)
            if project_id:
                rec.construction = project_id.construction
            else:
                rec.construction = rec.is_construction

    def set_project_details(self):
        for rec in self:
            rec.is_construction = rec.construction

    @api.depends('project_ids')
    def get_is_product(self):
        for rec in self:
            is_project = False
            if rec.project_ids:
                if rec.project_ids.analytic_account_id.id == rec.id:
                    is_project = True
            rec.update({
                'is_project': is_project
            })

    construction = fields.Boolean('Construction', compute=get_project_details, inverse=set_project_details, store=True)
    is_construction = fields.Boolean('Is Construction', compute=set_project_details)
    has_child = fields.Boolean(string='Is a parent ?', copy=False)
    is_project = fields.Boolean(string="Is Project", compute=get_is_product, store=True)

    # For munavoor
    boq_category = fields.Many2one(comodel_name='project.boq.category', string='Category')
    project_ids = fields.Many2one('project.project', string='Project')
    tender_id = fields.Many2one('project.tender', string='Tender', related='project_ids.tender')
    boq_count = fields.Integer("BOQ Count", compute='compute_boq_count')

    boq_ids = fields.One2many('project.extend.boq', 'analytic_account_id', string="BOQ")

    # project_count = fields.Integer("Project Count", compute=False)

    def action_view_boq(self):
        view_id = self.env.ref('project_custom.view_boq_tree')
        domain = [('boq_category', '=', self.boq_category.id), '|',
                  ('tender_id', 'in', self.project_ids.mapped('tender').ids),
                  ('project_id', '=', self.project_ids.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bill Of Quantities'),
            'res_model': 'project.extend.boq',
            'view_mode': 'tree',
            'limit': 99999999,
            'search_view_id': self.env.ref('account.view_account_search').id,
            'views': [[view_id and view_id.id, 'list']],
            'domain': domain,
            'context': {
                'default_boq_category': self.boq_category.id,
                'search_default_group_by_boq_category': True,
                'create': False,
                'edit': False,
                'delete': False
            }
        }

    def compute_boq_count(self):
        """

        @return:
        """
        for record in self:
            if record.project_ids and record.boq_category:
                count = self.env['project.extend.boq'].search_count([('boq_category', '=', record.boq_category.id), (
                    'tender_id', 'in', record.project_ids.mapped('tender').ids)])
                record.boq_count = count or 0
            else:
                record.boq_count = 0

    def unlink(self):
        projects = self.env['project.project'].search([('analytic_account_ids', 'in', self.ids)])
        has_tasks = self.env['project.task'].search_count([('project_id', 'in', projects.ids)])
        if has_tasks:
            raise UserError(_('Please remove existing tasks in the project linked to the accounts you want to delete.'))
        return super(BaseAnalyticAccount, self).unlink()

    def action_view_projects(self):
        result = {
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "views": [[False, "form"]],
            "context": {"create": False},
            "name": "Projects",
            "res_id": self.project_ids.id
        }
        return result

    # ===============================================

    @api.onchange('construction')
    def onchange_type(self):
        if self.construction:
            self.use_tasks = True

    # @api.depends('project_ids')
    # def _compute_project_count(self):
    #     project_data = self.env['project.project'].read_group([('analytic_account_ids.ids', 'in', self.ids)],
    #                                                           ['analytic_account_ids'], ['analytic_account_ids'])
    #     print(project_data, "sssssssssssssssssssssssssssssss")
    #     mapping = {m['analytic_account_id'][0]: m['analytic_account_id_count'] for m in project_data}
    #     for account in self:
    #         account.project_count = mapping.get(account.id, 0)


class ProjectMaster(models.Model):
    _inherit = "project.project"

    def get_cost_and_revenue(self):
        action = self.env["ir.actions.actions"]._for_xml_id("analytic.account_analytic_line_action")
        action['domain'] = ['|', ('account_id', 'in', self.analytic_account_ids.ids),
                            ('account_id', '=', self.analytic_account_id.id)]
        action['context'] = {'search_default_group_date': 1, 'default_account_id': self.analytic_account_id.id}
        return action

    def open_view_project_all_settings(self):
        action = self.with_context(active_id=self.id, active_ids=self.ids) \
            .env.ref('project_custom.open_view_project_all_settings') \
            .sudo().read()[0]
        action['display_name'] = self.name
        action['res_id'] = self.id
        return action

    def write(self, vals):
        team = []
        partner_ids = []
        if vals.get('analytic_account_ids', False):
            for line in vals.get('analytic_account_ids'):
                if line[0] == 3:
                    analytic_acc_id = line[1]
                    # analytic_account = self.env['account.analytic.account'].browse(analytic_acc_id)
                    budget_rec = self.env['crossovered.budget'].search([
                        ('analytic_account_id', '=', analytic_acc_id), ('state', '!=', 'cancel')])
                    budget_line_rec = self.env['crossovered.budget.lines'].search([
                        ('analytic_account_id', '=', analytic_acc_id), ('state', '!=', 'cancel')])

                    # SO
                    sale_rec = self.env['purchase.order'].search([
                        ('analytic_account_id', '=', analytic_acc_id), ('state', '!=', 'cancel')])

                    # PO
                    po_rec = self.env['purchase.order'].search([
                        ('bu_cc', '=', analytic_acc_id), ('state', '!=', 'cancel')])
                    po_line_rec = self.env['purchase.order.line'].search([
                        ('account_analytic_id', '=', analytic_acc_id), ('state', '!=', 'cancel')])

                    # Move Line
                    move_rec = self.env['account.move.line'].search([
                        ('analytic_account_id', '=', analytic_acc_id), ('state', '!=', 'cancel')])

                    # Project Tender
                    tender_rec = self.env['project.tender'].search([
                        ('analytic_account_id', '=', analytic_acc_id), ('state', '!=', 'cancel')])

                    # MR
                    mr_rec = self.env['mr'].search([
                        ('bu_cc', '=', analytic_acc_id), ('state', '!=', 'cancel')])
                    mr_line_rec = self.env['mr.order.line'].search([
                        ('analytic_account_id', '=', analytic_acc_id), ('state', '!=', 'cancel')])
                    if budget_rec or budget_line_rec or mr_rec or mr_line_rec or po_rec or po_line_rec \
                            or sale_rec or tender_rec or move_rec:
                        raise UserError(_("Analytic account can't be deleted. Already linked with other records ."))

        if vals.get('analytic_account_id', False):
            proj = self.env['project.project'].search(
                [('analytic_account_id', '=', vals.get('analytic_account_id', False))])
            if proj:
                raise UserError('Duplication of Projects not allowed, Please Contact FM to create new project')
        # if 'construction' in vals and vals['construction']:
        #     group_cons_plan = \
        #         self.env['ir.model.data'].get_object_reference('project_custom', 'group_cons_plan')[
        #             1]
        #     group_cons_manager = \
        #         self.env['ir.model.data'].get_object_reference('project_custom', 'group_cons_manager')[1]
        #     g_users = self.env['res.groups'].browse([group_cons_plan, group_cons_manager])
        #     team.extend(g_users.mapped('users').ids)
        if vals.get('members') or vals.get('user_id'):
            if vals.get('user_id'):
                team.append(vals.get('user_id'))
            elif vals.get('members'):
                team.extend(vals['members'][0][2])
        if team:
            for project in self:
                for i in project.members:
                    team.append(i.id)
            partner_ids = self.env['res.users'].browse(list(set(team))).mapped('partner_id.id')
            vals['members'] = [(6, 0, list(set(team)))]
        self.message_subscribe(partner_ids=partner_ids)
        res = super(ProjectMaster, self).write(vals)
        if vals.get('project_type'):
            self.analytic_account_group_id = self.project_type.analytic_group_id.id
            self.analytic_account_id.group_id = self.project_type.analytic_group_id.id
        return res

    # @api.model_create_multi
    # def create(self, vals_list):
    #     """restricting the duplication of project"""
    #     self = self.with_context(mail_create_nosubscribe=True)
    #     valid_vals_list = []
    #     for vals in vals_list:
    #         r = []
    #         if vals.get('analytic_account_id', False):
    #             proj = self.env['project.project'].search(
    #                 [('analytic_account_id', '=', vals.get('analytic_account_id', False))])
    #             if proj:
    #                 raise UserError('Duplication of Projects not allowed, Please Contact FM to create new project')
    #         if r:
    #             partner_ids = self.env['res.users'].browse(list(set(r))).mapped('partner_id.id')
    #             self.message_subscribe(partner_ids=partner_ids)
    #             vals['members'] = [(6, 0, list(set(r)))]
    #         vals['project_code'] = self.env['ir.sequence'].next_by_code(
    #             'project.project.code', sequence_date=vals['start_date']) if "start_date" in vals else '/' or '/'
    #         new_alias = not vals.get('alias_id')
    #         if new_alias:
    #             alias_vals, record_vals = self._alias_filter_fields(vals)
    #             alias_vals.update(self._alias_get_creation_values())
    #             alias = self.env['mail.alias'].sudo().create(alias_vals)
    #             record_vals['alias_id'] = alias.id
    #             valid_vals_list.append(record_vals)
    #         else:
    #             valid_vals_list.append(vals)
    #     records = super(ProjectMaster, self).create(valid_vals_list)
    #     for rec in records:
    #         # rec.analytic_account_id = rec._create_analytic_account()
    #         analytic_group = self.env['account.analytic.group'].sudo().create({
    #             'name': rec.name,
    #             'company_id': rec.company_id.id,
    #             'parent_id': rec.project_type.analytic_group_id.id,
    #         })
    #         rec.analytic_account_group_id = analytic_group.id
    #         # rec.analytic_account_id.group_id = analytic_group.id
    #         # rec.analytic_account_id.project_ids = rec.id
    #         rec.alias_id.sudo().write(rec._alias_get_creation_values())
    #     return records

    @api.model
    def create(self, vals):
        """restricting the duplication of project"""
        r = []
        if vals.get('analytic_account_id', False):
            proj = self.env['project.project'].search(
                [('analytic_account_id', '=', vals.get('analytic_account_id', False))])
            if proj:
                raise UserError('Duplication of Projects not allowed, Please Contact FM to create new project')
        else:
            analytic_account = self.env['account.analytic.account'].create({
                'name': vals.get('name'),
                'company_id': vals.get('company_id'),
                'partner_id': vals.get('partner_id'),
                'active': True,
            })
            vals.update({'analytic_account_id': analytic_account.id})
        if r:
            partner_ids = self.env['res.users'].browse(list(set(r))).mapped('partner_id.id')
            self.message_subscribe(partner_ids=partner_ids)
            vals['members'] = [(6, 0, list(set(r)))]
        vals['project_code'] = self.env['ir.sequence'].next_by_code('project.project.code',
                                                                    sequence_date=vals[
                                                                        'start_date']) if "start_date" in vals else '/' or '/'
        new_alias = not vals.get('alias_id')
        if new_alias:
            alias_vals, record_vals = self._alias_filter_fields(vals)
            alias_vals.update(self._alias_get_creation_values())
            alias = self.env['mail.alias'].sudo().create(alias_vals)
            vals['alias_id'] = alias.id
        res = super(ProjectMaster, self).create(vals)
        # Commented By Ajmal
        # analytic_group = self.env['account.analytic.group'].sudo().create({
        #     'name': res.name,
        #     'company_id': res.company_id.id,
        #     'parent_id': res.project_type.analytic_group_id.id,
        # })
        # res.analytic_account_group_id = analytic_group.id
        # res.analytic_account_id.group_id = analytic_group.id
        res.analytic_account_id.project_ids = res.id
        res.alias_id.sudo().write(res._alias_get_creation_values())
        return res

    def _visit_count(self):
        gate_pass = self.env['project.site.visit']
        count = gate_pass.search_count([('project', '=', self.id)])
        self.visit_count = count

    def return_site_visit(self):
        """ This opens the xml view specified in xml_id for the site visits """
        xml_id = 'open_visit_form'
        res = self.env['ir.actions.act_window']._for_xml_id(f"project_custom.{xml_id}")
        res['context'] = {'default_project': self.id}
        res['domain'] = [('project', '=', self.id)]
        return res

    def _log_count(self):
        gate_pass = self.env['project.correspondence']
        count = gate_pass.search_count([('project', '=', self.id)])
        self.log_count = count

    def _task_count(self):
        gate_pass = self.env['project.gate.pass']
        count = gate_pass.search_count([('project', '=', self.id)])
        self.pass_count = count

    def _util_count(self):
        gate_pass = self.env['project.utility']
        count = gate_pass.search_count([('project', '=', self.id)])
        self.utility_count = count

    def _inv_count(self):
        inv_lines = self.env['account.move']
        count = inv_lines.search_count([('partner_id', '=', self.partner_id.id), ('move_type', '!=', 'entry')])
        self.inv_count = count

    def _mrf_count(self):
        inv_lines = self.env['mr']
        count = inv_lines.search_count([('bu_cc', '=', self.analytic_account_id.id), ('request_type', '=', 'mr')])
        self.mrf_count = count

    def _sr_count(self):
        inv_lines = self.env['mr']
        count = inv_lines.search_count([('bu_cc', '=', self.analytic_account_id.id), ('request_type', '=', 'sr')])
        self.sr_count = count

    def _po_count(self):
        inv_lines = self.env['purchase.order']
        count = inv_lines.search_count([('bu_cc', '=', self.analytic_account_id.id)])
        self.po_count = count

    def _ts_count(self):
        ts_lines = self.env['account.analytic.line']
        count = ts_lines.search_count([('account_id', '=', self.analytic_account_id.id)])
        self.ts_count = count

    def attachment_tree_view(self):
        task_ids = self.env['project.task'].search([('project_id', '=', self.id)])
        domain = [
            '|',
            '&', ('res_model', '=', 'project.project'), ('res_id', '=', self.id),
            '&', ('res_model', '=', 'project.task'), ('res_id', 'in', task_ids.ids), ('app_type', '=', 'draw')]
        res_id = self.id
        return {
            'name': 'Attachments',
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'limit': 80,
            'context': "{'default_app_type':'draw' , 'default_res_model': '%s','default_res_id': %d}" % (
                self._name, res_id)
        }

    def _get_attached_docs(self):
        attachment = self.env['ir.attachment']
        task = self.env['project.task']
        project_attachments = attachment.search_count(
            [('app_type', '=', 'draw'), ('res_model', '=', 'project.project'), ('res_id', '=', self.id)])
        task_ids = task.search([('project_id', '=', self.id)])
        task_attachments = 0
        for i in task_ids:
            task_attachments += attachment.search_count(
                [('app_type', '=', 'draw'), ('res_model', '=', 'project.task'), ('res_id', '=', i.id)])
        self.doc_count = (project_attachments or 0) + (task_attachments or 0)

    def _get_attached_om(self):
        attachment = self.env['ir.attachment']
        count = attachment.search_count(
            [('res_model', '=', 'project.project'), ('app_type', '=', 'om'), ('res_id', '=', self.id)])
        self.om_count = count or 0

    def return_mrf(self):
        if self._context.get('xml_id'):
            ctx = dict(self.env.context, default_bu_cc=self.analytic_account_id.id)
            res = self.env['ir.actions.act_window']._for_xml_id('amlak_mr.open_mr_form')
            ctx.update(default_type='cons', group_by=False)
            res['domain'] = [('bu_cc', '=', self.analytic_account_id.id), ('request_type', '=', 'mr')]
            res['context'] = ctx
            return res
        return False

    def action_return_sr(self):
        if self._context.get('xml_id'):
            ctx = dict(self.env.context, default_bu_cc=self.analytic_account_id.id)
            res = self.env['ir.actions.act_window']._for_xml_id('amlak_mr.open_sr_form')
            ctx.update(default_type='cons', group_by=False)
            res['domain'] = [('bu_cc', '=', self.analytic_account_id.id), ('request_type', '=', 'sr')]
            res['context'] = ctx
            return res
        return False

    def return_timesheet(self):
        if self._context.get('xml_id'):
            ctx = dict(self.env.context, default_account_id=self.analytic_account_id.id)
            res = self.env['ir.actions.act_window']._for_xml_id(f"hr_timesheet.{self._context['xml_id']}")
            ctx.update(group_by=False, search_default_groupby_user=1, search_default_groupby_month=1)
            res['domain'] = [('account_id', '=', self.analytic_account_id.id)]
            res['context'] = ctx
            return res
        return False

    def return_po(self):
        if self._context.get('xml_id'):
            ctx = dict(self.env.context, default_bu_cc=self.analytic_account_id.id)
            res = self.env['ir.actions.act_window']._for_xml_id(f"purchase.{self._context['xml_id']}")
            ctx.update(group_by=False)
            res['domain'] = [('bu_cc', '=', self.analytic_account_id.id)]
            res['context'] = ctx
            return res
        return False

    def om_view(self):
        domain = [('res_model', '=', 'project.project'), ('res_id', '=', self.id), ('app_type', '=', 'om')]
        return {
            'name': ('O&M'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'context': "{'default_app_type':'om','default_res_model': '%s','default_res_id': %d}" % (
                self._name, self.id)
        }

    def return_gate_pass(self):
        """ This opens the xml view specified in xml_id for gate pass """
        if self._context.get('xml_id'):
            ctx = dict(self.env.context, default_project=[(6, 0, [self.id])])
            res = self.env['ir.actions.act_window']._for_xml_id(f"project_custom.{self._context['xml_id']}")
            ctx.update(group_by=False)
            res['domain'] = [('project', '=', self.id)]
            res['context'] = ctx
            return res
        return False

    def return_log(self):
        """ This opens the xml view specified in xml_id for the correspondence log"""
        if self._context.get('xml_id'):
            ctx = dict(self.env.context, default_project=self.id)
            res = self.env['ir.actions.act_window']._for_xml_id(f"project_custom.{self._context['xml_id']}")
            ctx.update(group_by=False)
            res['domain'] = [('project', '=', self.id)]
            res['context'] = ctx
            return res
        return False

    def return_utility(self):
        """ This opens the xml view specified in xml_id for the utility """
        if self._context.get('xml_id'):
            res = self.env['ir.actions.act_window']._for_xml_id(f"project_custom.{self._context['xml_id']}")
            ctx = dict(self.env.context, default_project=self.id)
            res['domain'] = [('project', '=', self.id)]
            ctx.update(group=False)
            res['context'] = ctx
            return res
        return False

    def tender_locations(self):
        # if self.tender:
        #     domain = [('tender_id', '=', self.tender.id)]
        #     context = {'default_tender_id': self.id}
        # else:
        domain = [('project_id', '=', self.id)]
        context = {'default_project_id': self.id}
        return {
            'name': 'Locations',
            'domain': domain,
            'res_model': 'project.tender.location',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': context
        }

    def duplicate_template(self):
        """To prevent changing Cost Center/ Analytic Account name on changing project name."""
        return False

    @api.onchange('tender', 'is_from_tender')
    def get_location(self):
        if self.is_from_tender and self.tender:
            self.location = self.tender.location
        else:
            self.location = False
            self.tender = False

    @api.depends('tender', 'is_from_tender', 'location_ids')
    def get_location_count(self):
        for rec in self:
            # if rec.is_from_tender and rec.tender:
            #     rec.location_count = len(rec.tender.location_ids)
            # else:
            rec.location_count = len(rec.location_ids)

    def get_invoice_count(self):
        for rec in self:
            # TODO : To confirm
            # out_invoice = self.env['account.move'].search([
            #     ('move_type', '=', 'out_invoice')])
            # in_invoice = self.env['account.move'].search([
            #     ('move_type', '=', 'in_invoice')])
            out_invoice = self.env['account.move.line'].search([
                ('move_id.move_type', '=', 'out_invoice'), ('analytic_account_id', '=', rec.analytic_account_id.id)])
            in_invoice = self.env['account.move.line'].search([
                ('move_id.move_type', '=', 'in_invoice'), ('analytic_account_id', '=', rec.analytic_account_id.id)])
            rec.update({
                'in_invoice_count': len(set(in_invoice.mapped('move_id'))),
                'out_invoice_count': len(set(out_invoice.mapped('move_id')))
            })

    def action_open_out_invoice(self):
        for rec in self:
            action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
            out_invoice = self.env['account.move.line'].search([
                ('move_id.move_type', '=', 'out_invoice'), ('analytic_account_id', '=', rec.analytic_account_id.id)])
            action['domain'] = [('move_type', '=', 'out_invoice'),
                                ('id', 'in', list(set(out_invoice.mapped('move_id').ids)))]
            return action

    def action_open_in_invoice(self):
        for rec in self:
            action = self.env.ref('account.action_move_in_invoice_type').sudo().read()[0]
            in_invoice = self.env['account.move.line'].search([
                ('move_id.move_type', '=', 'in_invoice'), ('analytic_account_id', '=', rec.analytic_account_id.id)])
            action['domain'] = [('move_type', '=', 'in_invoice'),
                                ('id', 'in', list(set(in_invoice.mapped('move_id').ids)))]
            return action

    def get_manpower_details(self):
        for rec in self:
            # if rec.is_from_tender:
            #     locations = self.env['project.tender.location'].search([('tender_id', '=', rec.tender.id)])
            # else:
            locations = self.env['project.tender.location'].search([('project_id', '=', rec.id)])
            manpower_required = sum([location['manpower'] for location in locations]) if locations else 0
            current_manpower = sum([location['current_manpower'] for location in locations]) if locations else 0
            if manpower_required == current_manpower:
                manpower_status = 'normal'
            elif manpower_required < current_manpower:
                manpower_status = 'excess'
            else:
                manpower_status = 'shortage'
            rec.update({
                'manpower': manpower_required,
                'current_manpower': current_manpower,
                'manpower_available': sum([location['manpower_available']
                                           for location in locations]) if locations else 0,
                'emp_on_leave_count': sum([location['emp_on_leave_count']
                                           for location in locations]) if locations else 0,
                'manpower_status': manpower_status,
                'status_amount': abs(manpower_required - current_manpower)
            })

    def get_sub_contract_details(self):
        for rec in self:
            rec.sub_contract_count = len(rec.sub_contract_ids) if rec.sub_contract_ids else 0

    project_code = fields.Char(string='Project Sequence', readonly=True, copy=False, default='/')
    proj_code = fields.Char(string="Project Code")
    construction = fields.Boolean('Construction', default=True)
    landscaping = fields.Boolean('Landscaping')
    is_contract = fields.Boolean('Contract')
    is_from_tender = fields.Boolean(string='From Tender ?')
    tender = fields.Many2one('project.tender', string='Tender')
    contract_history = fields.One2many('project.contract.history', 'contract_id',
                                       string='Contract History', readonly=True)
    contract_value = fields.Float(string='Contract Value')
    # user_id = fields.Many2one('res.users',string='Project Manager')
    w_supervisor = fields.Many2many('hr.employee', 'emp_project_rel_1', 'project_id', 'employee_id',
                                    string='Workers Supervisor')
    w_fm = fields.Many2many('hr.employee', 'emp_project_rel_2', 'project_id', 'employee_id', string='Foreman')
    w_ch = fields.Many2many('hr.employee', 'emp_project_rel_3', 'project_id', 'employee_id', string='Charge hand')
    w_sh = fields.Many2many('hr.employee', 'emp_project_rel_4', 'project_id', 'employee_id',
                            string='Shuttering Carpenter')
    w_fc = fields.Many2many('hr.employee', 'emp_project_rel_5', 'project_id', 'employee_id',
                            string='Furniture Carpenter')
    w_sf = fields.Many2many('hr.employee', 'emp_project_rel_6', 'project_id', 'employee_id', string='Steel Fitter')
    w_mason = fields.Many2many('hr.employee', 'emp_project_rel_7', 'project_id', 'employee_id', string='Mason')
    w_tm = fields.Many2many('hr.employee', 'emp_project_rel_8', 'project_id', 'employee_id', string='Tiles Mason')
    w_ppo = fields.Many2many('hr.employee', 'emp_project_rel_9', 'project_id', 'employee_id', string='Painter/Polisher')
    w_helper = fields.Many2many('hr.employee', 'emp_project_rel_10', 'project_id', 'employee_id',
                                string='Workers Helper')
    w_sk = fields.Many2many('hr.employee', 'emp_project_rel_11', 'project_id', 'employee_id', string='Store Keeper')
    w_cb = fields.Many2many('hr.employee', 'emp_project_rel_12', 'project_id', 'employee_id', string='Camp Boss')
    w_ob = fields.Many2many('hr.employee', 'emp_project_rel_13', 'project_id', 'employee_id', string='Office Boy')
    w_driver = fields.Many2many('hr.employee', 'emp_project_rel_14', 'project_id', 'employee_id', string='Driver')
    m_supervisor = fields.Many2many('hr.employee', 'emp_project_rel_15', 'project_id', 'employee_id',
                                    string='MEP Supervisor')
    w_elec = fields.Many2many('hr.employee', 'emp_project_rel_16', 'project_id', 'employee_id', string='Electrician')
    w_pl = fields.Many2many('hr.employee', 'emp_project_rel_17', 'project_id', 'employee_id', string='Plumber')
    m_helper = fields.Many2many('hr.employee', 'emp_project_rel_18', 'project_id', 'employee_id', string='MEP Helper')
    m_cable = fields.Many2many('hr.employee', 'emp_project_rel_19', 'project_id', 'employee_id',
                               string='Structured Cabling')
    m_ac_tech = fields.Many2many('hr.employee', 'emp_project_rel_20', 'project_id', 'employee_id', string='A/C Tech')
    w_jcb_rcc_optr = fields.Many2many('hr.employee', 'emp_project_rel_21', 'project_id', 'employee_id',
                                      string='JCB/RCC/Oprtr')
    doc_count = fields.Integer(compute='_get_attached_docs', string="Document Count")
    ts_count = fields.Integer(compute='_ts_count', string="Timesheet")
    pass_count = fields.Integer(compute='_task_count', string="Gate Pass Count")
    gate_pass_ids = fields.One2many('project.gate.pass', 'project', string="All Gate Pass")
    utility_count = fields.Integer(compute='_util_count', string="Utility Count")
    om_count = fields.Integer(compute='_get_attached_om', string="O&M")
    utility_ids = fields.One2many('project.utility', 'project', string='Utility')
    log_count = fields.Integer(compute='_log_count', string="Log Count")
    log_ids = fields.One2many('project.correspondence', 'project', string='Comm. Log')
    inv_count = fields.Integer(compute='_inv_count', string="Invoice Count")
    mrf_count = fields.Integer(compute='_mrf_count', string="MRF Count")
    sr_count = fields.Integer(compute='_sr_count', string="SR Count")
    visit_count = fields.Integer(compute='_visit_count', string="Visit")
    site_visit = fields.One2many('project.site.visit', 'tender', string='Site Visit')
    po_count = fields.Integer(compute='_po_count', string="PO Count")
    bond_date_start = fields.Date('Bond Start Date')
    bond_date_end = fields.Date('Bond End Date')
    bond_file = fields.Binary('Bond Document')
    location = fields.Char(string="Tender Location")
    location_id = fields.Many2one('stock.location', string='Stock Location')
    consumption_loc = fields.Many2one('stock.location', string='Consumption Location')
    location_ids = fields.One2many('project.tender.location', 'project_id', 'Locations')
    location_count = fields.Integer('Location Count', compute=get_location_count)
    invoice_schedule = fields.Selection([('monthly', 'Monthly'), ('quarterly', 'Quarterly'),
                                         ('half_yearly', 'Half Yearly'), ('yearly', 'Yearly'), ('1_time', '1 time')])
    state = fields.Selection(
        [('draft', 'Draft'), ('section_head', 'Section Head'), ('manager', 'Manager'),
         ('open', 'In Progress'), ('cancelled', 'Cancelled'), ('pending', 'Pending'),
         ('close', 'Closed')], 'Status', tracking=True, required=True, copy=False, default='draft')
    start_date = fields.Date('Project Start Date', copy=False)
    date_end = fields.Date('Project End Date', copy=False)
    gate_pass = fields.Many2one('project.gate.pass', string='Gate Pass')

    manpower = fields.Integer(string='Manpower Required', compute=get_manpower_details)
    current_manpower = fields.Integer(string='Manpower Allocated', compute=get_manpower_details)
    # emp_on_leave = fields.Many2many('hr.employee', string='Employees on Leave', compute=get_manpower_details)
    emp_on_leave_count = fields.Integer(string='Employees on Leave', compute=get_manpower_details)
    manpower_available = fields.Integer(string='Manpower Available', compute=get_manpower_details)
    manpower_status = fields.Selection([('excess', 'Excess'), ('normal', 'Normal'),
                                        ('shortage', 'Shortage')], string='Manpower Status',
                                       compute=get_manpower_details)
    status_amount = fields.Integer(string='Shortage/ Excess Amount', compute=get_manpower_details)
    sub_contract_ids = fields.One2many('project.sub.contract', 'project_id', string='Sub Contracts')
    sub_contract_count = fields.Integer(string='Sub Contract Count', compute=get_sub_contract_details)
    profit_amount = fields.Float("Profit Amount", related='tender.profit_amount')
    insurance_start = fields.Date("Insurance Start Date")
    insurance_end = fields.Date("Insurance End Date")
    insurance_doc = fields.Binary("Insurance Document")
    in_invoice_count = fields.Integer("Supplier Invoices", compute=get_invoice_count)
    out_invoice_count = fields.Integer("Customer Invoices", compute=get_invoice_count)
    members = fields.Many2many('res.users', 'project_user_rel', 'project_id', 'uid', 'Project Members',
                               help="Project's members are users who can have an access to the tasks related "
                                    "to this project.",
                               states={'close': [('readonly', True)], 'cancelled': [('readonly', True)]},
                               tracking=True, readonly=False)
    privacy_visibility = fields.Selection([
        ('followers', 'Invited internal users'),
        ('employees', 'All internal users'),
        ('portal', 'Invited portal users and all internal users'),
    ], string='Visibility', required=True, default='followers',
        help="Defines the visibility of the tasks of the project:\n"
             "- Invited internal users: employees may only see the followed project and tasks.\n"
             "- All internal users: employees may see all project and tasks.\n"
             "- Invited portal and all internal users: employees may see everything."
             "   Portal users may see project and tasks followed by\n"
             "   them or by someone of their company.")

    # For Munavoor
    project_type = fields.Many2one('project.type', string="Project Type", required=False,
                                   readonly=True, states={'draft': [('readonly', False)]})
    # Commented By Ajmal
    # project_analytic_type = fields.Many2one('account.analytic.group', related='project_type.analytic_group_id')
    boq_count = fields.Integer(compute='boq_counted', string="BOQ Count")
    analytic_account_ids = fields.One2many('account.analytic.account', 'project_ids',
                                           string='Analytic Accounts', copy=False)
    analytic_account_count = fields.Integer("Project Count", compute='_compute_analytic_account_count')
    # Commented By Ajmal
    # analytic_account_group_id = fields.Many2one('account.analytic.group', string="Analytic Group", copy=False,
    #                                             ondelete='set null', check_company=True,
    #                                             domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    #                                             help="""Analytic group to which this project is linked for
    #                                           financial management. Use an analytic account  under this analytic group
    #                                           to record cost and revenue on your project.""")
    advance_bond_start = fields.Date("Advance Start Date")
    advance_bond_end = fields.Date("Advance End Date")
    advance_bond_doc = fields.Binary("Advance Document")

    attachment_ids = fields.Many2many('ir.attachment', 'project_drawing_rel', 'project_id', 'attachment_id',
                                     string='Drawings')

    def boq_counted(self):
        count = 0
        if self.tender:
            count_exteded = self.env['project.extend.boq'].search_count([('tender_id', '=', self.tender.id)])
            count = count_exteded
        self.boq_count = count

    @api.depends('analytic_account_ids')
    def _compute_analytic_account_count(self):
        analytic_account_data = self.env['account.analytic.account'].read_group([('project_ids', 'in', self.ids)],
                                                                                ['project_ids'], ['project_ids'])
        mapping = {m['project_ids'][0]: len(m['project_ids']) for m in analytic_account_data}
        for project in self:
            project.analytic_account_count = mapping.get(project.id, 0)

    def unlink(self):
        # If some projects to unlink have some timesheets entries, these
        # timesheets entries must be unlinked first.
        # In this case, a warning message is displayed through a RedirectWarning
        # and allows the user to see timesheets entries to unlink.
        projects_with_timesheets = self.filtered(lambda p: p.timesheet_ids)
        if projects_with_timesheets:
            if len(projects_with_timesheets) > 1:
                warning_msg = _(
                    "These projects have some timesheet entries referencing them. Before removing these projects, you have to remove these timesheet entries.")
            else:
                warning_msg = _(
                    "This project has some timesheet entries referencing it. Before removing this project, you have to remove these timesheet entries.")
            raise RedirectWarning(
                warning_msg, self.env.ref('hr_timesheet.timesheet_action_project').id,
                _('See timesheet entries'), {'active_ids': projects_with_timesheets.ids})
        # Check project is empty
        for project in self.with_context(active_test=False):
            if project.tasks:
                raise UserError(
                    _('You cannot delete a project containing tasks. You can either archive it or first delete all of its tasks.'))
        # Delete the empty related analytic account
        analytic_accounts_to_delete = self.env['account.analytic.account']
        # # Commented By Ajmal
        # analytic_groups_to_delete = self.env['account.analytic.group']
        for project in self:
            if project.analytic_account_ids:
                empty_analytic_accounts = project.analytic_account_ids.filtered(lambda x: not x.line_ids)
                analytic_accounts_to_delete |= empty_analytic_accounts
            #     # Commented By Ajmal
            # if project.analytic_account_group_id:
            #     analytic_groups_to_delete |= project.analytic_account_group_id
        result = super(BaseProject, self).unlink()
        analytic_accounts_to_delete.unlink()
        # Commented By Ajmal
        # analytic_groups_to_delete.unlink()
        return result

    def action_view_account_analytic_line(self):
        """ return the action to see all the analytic lines of the project's analytic account """
        action = self.env["ir.actions.actions"]._for_xml_id("analytic.account_analytic_line_action")
        # action['context'] = {'default_account_id': self.analytic_account_id.id}
        action['domain'] = [('account_id', 'in', self.analytic_account_ids.ids)]
        return action

    # Commented By Ajmal
    # def _create_analytic_account(self):
    #     for project in self:
    #         analytic_group = self.env['account.analytic.group'].create({
    #             'name': project.name,
    #             'company_id': project.company_id.id,
    #             'parent_id': project.project_analytic_type.id
    #         })
    #         # project.write({})
    #         analytic_account = self.env['account.analytic.account'].create({
    #             'name': project.name,
    #             'company_id': project.company_id.id,
    #             'partner_id': project.partner_id.id,
    #             'active': True,
    #             'group_id': analytic_group.id,
    #         })
    #         project.write({'analytic_account_id': analytic_account.id, 'analytic_account_group_id': analytic_group.id})

    # Commented By Ajmal
    # @api.model
    # def _create_analytic_account_from_values(self, values):
    #     if values.get('project_type', False):
    #         project_type = self.env['project.type'].browse(values.get('project_type'))
    #         parent_analytic_group = project_type.analytic_group_id.id
    #     else:
    #         parent_analytic_group = self.env.ref('project_custom.analytic_group_for_projects').id
    #     analytic_group = self.env['account.analytic.group'].create({
    #         'name': values.get('name', _('Unknown Analytic Account')),
    #         'company_id': values.get('company_id') or self.env.company.id,
    #         'parent_id': parent_analytic_group
    #     })
    #     return analytic_group

    # hr_timesheet module
    # @api.depends('analytic_account_ids')
    # def _compute_allow_timesheets(self):
    #     without_account = self.filtered(lambda t: not t.analytic_account_ids and t._origin)
    #     without_account.update({'allow_timesheets': False})

    @api.constrains('allow_timesheets', 'analytic_account_id')
    def _check_allow_timesheet(self):
        for project in self:
            if project.allow_timesheets and not project.analytic_account_id:
                raise ValidationError(
                    _('To allow timesheet, your project %s should have an analytic account group set.', project.name))

    def update_tender_analytic_accounts(self):
        for project in self:
            if project.analytic_account_group_id and project.is_from_tender and project.tender:
                analytic_account_obj = self.env['account.analytic.account']
                if project.tender.analytic_account_id:
                    project.tender.analytic_account_id.update({
                        'group_id': project.analytic_account_group_id.id,
                        'project_ids': project.id
                    })
                boq_category_ids = project.tender.extended_boq_ids.mapped('boq_category')
                for boq_category in boq_category_ids:
                    is_available = project.analytic_account_ids.filtered(lambda x: x.boq_category == boq_category)
                    boq_ids = project.tender.extended_boq_ids.filtered(lambda x: x.boq_category == boq_category)
                    if not is_available:
                        analytic_account_obj.create({
                            'name': boq_category.name or boq_category.code,
                            'code': boq_category.code,
                            'group_id': project.analytic_account_group_id.id,
                            'project_ids': project.id,
                            'boq_category': boq_category.id,
                            'boq_ids': [(6, 0, boq_ids.ids)]
                        })

    def open_boq(self):
        for rec in self:
            if rec.tender:
                ctx = self.env.context.copy()
                action = self.env["ir.actions.act_window"]._for_xml_id('project_custom.action_project_extend_boq')
                ctx.update({'default_tender_id': rec.tender.id, 'create': False, 'edit': False, 'delete': False})
                action['context'] = ctx
                action['domain'] = [('tender_id', '=', rec.tender.id)]
                return action

    # ================================================

    def get_budget(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget'),
            'res_model': 'crossovered.budget',
            'view_mode': 'tree',
            'domain': [('analytic_account_id', '=', self.analytic_account_id.id)],
            'views': [[False, "tree"], [False, "form"]],
        }

    def get_stock(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Current Stock'),
            'res_model': 'stock.quant',
            'view_mode': 'tree',
            'domain': [('location_id', 'child_of', self.location_id.ids)],
            'context': {
                'search_default_productgroup': 1
            }
        }

    def send_to_section_head(self):
        for rec in self:
            rec.state = 'section_head'

    def send_to_manager(self):
        for rec in self:
            rec.state = 'manager'

    def action_confirm(self):
        for rec in self:
            if not rec.location_id:
                parent_location_data = self.env['stock.warehouse'].search_read(
                    [('company_id', '=', self.env.company.id)], ['view_location_id'], limit=1)
                location = self.env['stock.location'].sudo().create({
                    'name': rec.name,
                    'usage': 'internal',
                    'location_id': parent_location_data[0]['view_location_id'][0],
                    'company_id': rec.company_id.id,
                })
            else:
                location = rec.location_id
            if not rec.consumption_loc:
                consumption_loc = self.env['stock.location'].sudo().create({
                    'name': rec.name + ' - Consumption',
                    'usage': 'production',
                    'company_id': rec.company_id.id,
                })
            else:
                consumption_loc = rec.consumption_loc
            rec.update({
                'state': 'open',
                'location_id': location.id,
                'consumption_loc': consumption_loc.id,
                'contract_history': [(0, 0, {
                    'start_date': rec.start_date,
                    'expiration_date': rec.date_end,
                    'history_type': 'beginning'
                })]
            })

    def set_open(self):
        for rec in self:
            if rec.state == 'pending':
                rec.state = 'open'
            else:
                rec.state = 'draft'

    def set_done(self):
        if self.mapped('w_supervisor') or self.mapped('w_fm') or self.mapped(
                'w_ch') or self.mapped('w_sh') \
                or self.mapped('w_fc') or self.mapped('w_sf') or self.mapped('w_mason') or self.mapped('w_tm') \
                or self.mapped('w_ppo') or self.mapped('w_helper') or self.mapped('w_sk') or self.mapped('w_cb') \
                or self.mapped('w_ob') or self.mapped('w_driver') or self.mapped('m_supervisor') \
                or self.mapped('w_elec') or self.mapped('w_pl') or self.mapped('m_helper') or self.mapped('m_cable') \
                or self.mapped('m_ac_tech') or self.mapped('w_jcb_rcc_optr'):
            raise UserError('Please transfer all the workers to the another project, then close the project')
        return self.write({'state': 'close'})


class ProjectTask(models.Model):
    _inherit = 'project.task'

    state = fields.Selection(related='stage_id.state', store=True, readonly=True)

    # For Munavoor
    analytic_account_active = fields.Boolean("Active Analytic Account", compute='_compute_analytic_accounts_active')

    @api.depends('project_id.analytic_account_ids')
    def _compute_analytic_accounts_active(self):
        """ Overridden in sale_timesheet """
        for task in self:
            if any(analytic_account_id.active for analytic_account_id in task.project_id.analytic_account_ids):
                task.analytic_account_active = True
            else:
                task.analytic_account_active = False

    # =========================================================


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    state = fields.Selection(_TASK_STATE, 'State')
    fold_statusbar = fields.Boolean('Folded in Statusbar')

    @api.model
    def _init_fold_statusbar(self):
        """ On module install initialize fold_statusbar values """
        for rec in self.search([]):
            rec.fold_statusbar = rec.fold


class UtilityMaster(models.Model):
    _name = 'project.utility'
    _description = 'Project Utility'

    def verify(self):
        if self.util_type == 'elec' and not (self.elc_meter_no):
            raise UserError('Electricity Meter No. !!.')
        elif self.util_type == 'water' and not (self.water_meter_no):
            raise UserError('Water Meter No. !!.')
        self.state = 'open'

    def cancel(self):
        if self.util_type == 'elec' and not (self.elc_meter_reading):
            raise UserError('Electricity Meter Reading !!.')
        elif self.util_type == 'water' and not (self.water_meter_reading):
            raise UserError('Water Meter Reading !!.')
        self.state = 'cancel'

    def close(self):
        if self.util_type == 'elec' and not (self.elc_meter_reading):
            raise UserError('Electricity Meter Reading !!.')
        elif self.util_type == 'water' and not (self.water_meter_reading):
            raise UserError('Water Meter Reading !!.')
        self.state = 'close'

    name = fields.Char('Doc. No.', required=True, copy=False, default='/')
    project_type = fields.Selection([('construction', 'Construction')],
                                    string='Project Type', default='construction', required=True)
    project = fields.Many2one('project.project', 'Project')
    date_start = fields.Date('From Date', required=True, default=fields.Date.today)
    date_end = fields.Date('End Date', required=True)
    util_type = fields.Selection(
        [('tele', 'Telephone'), ('water', 'Water'), ('elec', 'Electricity'), ('net', 'Internet')],
        string="Utility Type", required=True, default='tele')
    amount_total = fields.Float('Amount')
    water_meter_id = fields.Char('Water Meter No.')
    water_meter_reading = fields.Char('Water Meter Reading')
    elc_meter_id = fields.Char('Electricity Meter No.')
    elc_meter_reading = fields.Char('Electricity Meter Reading')
    responsible = fields.Many2one('hr.employee', string="Responsible Employee")
    remarks = fields.Text('Remarks')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    state = fields.Selection(
        [('draft', 'Draft'), ('open', 'In Progress'), ('cancel', 'Cancelled'), ('close', 'Closed')], 'Status',
        required=True, copy=False, default='draft')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('util') or '/'
        return super(UtilityMaster, self).create(vals)


class CorrespondenceLog(models.Model):
    _name = 'project.correspondence'
    _inherit = ['mail.thread']
    _description = 'Project Correspondence'

    def verify(self):
        if not self.date_response:
            self.date_response = self.date_rec if self.date_rec else self.date_sent + timedelta(days=7)
        self.state = 'open'

    def close(self):
        self.state = 'close'

    def send(self):
        if not self.date_response:
            self.date_response = fields.Date.today()
        self.state = 'review'

    @api.depends('date_rec', 'date_sent')
    def get_due_date(self):
        for rec in self:
            if rec.date_rec or rec.date_sent:
                rec.due_date = rec.date_rec if rec.date_rec else rec.date_sent + relativedelta(days=10)
            else:
                rec.due_date = False

    def _get_employee(self):
        """get the related employee """
        record = self.env['hr.employee'].search([('user_id', '=', self._uid)], limit=1)
        if record:
            return record.id
        else:
            return False

    name = fields.Char('Doc. No.', required=True, copy=False, default='/')
    type = fields.Selection([('in', 'IN'), ('out', 'OUT')], string='Type', tracking=True, default='in')
    project_type = fields.Selection([('construction', 'Construction')],
                                    string='Project Type', default='construction', required=True)
    project = fields.Many2one('project.project', 'Project')
    tender = fields.Many2one('project.tender', 'Tender')
    client = fields.Many2one('res.partner', string='Client')
    client_ref_no = fields.Char('Client Ref. No.')
    date_rec = fields.Datetime('Date Received')
    date_sent = fields.Datetime('Date Sent')
    initiated_by = fields.Many2one('hr.employee', string='Initiated By', default=_get_employee)
    action_by = fields.Many2one('hr.employee', string='Action By (Employee)')
    responsible = fields.Many2many('hr.employee', string='Responsible')
    due_date = fields.Datetime('Due Date', compute=get_due_date)
    date_response = fields.Datetime('Date Of Response')
    in_doc = fields.Char('Inward Correspondence Ref.')
    out_doc = fields.Char('Outward Correspondence Ref.')
    description = fields.Text('Description')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    state = fields.Selection(
        [('draft', 'Draft'), ('open', 'Waiting Action'), ('review', 'Waiting Validation'), ('close', 'Closed')],
        'Status', required=True, copy=False, tracking=True, default='draft')
    action_by_ids = fields.Many2many('hr.employee', 'project_correspondence_rel', 'correspondence_id', 'employee_id',
                                     string='Action By', copy=False)

    def add_follower(self, employee_ids):
        employee_ids = self.env['hr.employee'].browse(employee_ids)
        partner_ids = employee_ids.mapped('user_id.partner_id.id')
        if partner_ids:
            self.message_subscribe(partner_ids=partner_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('cl') or '/'
        res = super(CorrespondenceLog, self).create(vals)
        emp_ids = []
        if vals.get('action_by_ids'):
            emp_ids += vals.get('action_by_ids')[0][2]
        if vals.get('responsible'):
            emp_ids += vals.get('responsible')[0][2]
        if emp_ids:
            self.add_follower(emp_ids)
        return res

    def write(self, vals):
        emp_ids = []
        if vals.get('action_by_ids'):
            emp_ids += vals.get('action_by_ids')[0][2]
        if vals.get('responsible'):
            emp_ids += vals.get('responsible')[0][2]
        if emp_ids:
            self.add_follower(emp_ids)
        res = super(CorrespondenceLog, self).write(vals)
        return res

    def unlink(self):
        """restrict unlink if the record is not in draft state"""
        for record in self:
            if record.state != 'draft':
                raise UserError('You cannot delete a record if it is not in draft state')
        return super(CorrespondenceLog, self).unlink()


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    location_id = fields.Many2one('project.tender.location', string='Location')


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    current_project_id = fields.Many2one(comodel_name='project.project', readonly=True, copy=False,
                                         string='Project')
    project_code = fields.Char(string='Project Code')
    # project_code = fields.Char(string='Project Code', related='current_project_id.analytic_account_id.code')
    current_location_id = fields.Many2one(comodel_name='project.tender.location', readonly=True, copy=False,
                                          string='Location')


class IRAttachment(models.Model):
    _inherit = 'ir.attachment'

    app_type = fields.Selection(
        [('let', 'Letters'), ('draw', 'Drawings'), ('om', 'O&M'), ('cv', 'CV'), ('cert', 'Certificate'),
         ('other', 'Other')], string='Attachment Type')
    draw_type = fields.Selection(
        [('con', 'Construction Drawing'), ('work', 'Working Drawing'), ('build', 'As Build Drawing')],
        string='Drawing Category')

# Commented By Ajmal
# class AccountAnalyticGroup(models.Model):
#     _inherit = 'account.analytic.group'
#
#     project_ids = fields.One2many('project.project', 'analytic_account_group_id', string='Projects')
#
#     def unlink(self):
#         for rec in self:
#             if rec.project_ids:
#                 raise UserError(_("Please delete project of the selected analytic group."))
#         return super(AccountAnalyticGroup, self).unlink()


class ProjectType(models.Model):
    _name = 'project.type'
    _description = 'Project Type'
    # Commented By Ajmal
    # _inherits = {'account.analytic.group': 'analytic_group_id'}

    # def get_parent_group(self):
    #     group_id = self.env.ref('project_custom.analytic_group_for_projects')
    #     return group_id

    # @api.model
    # def default_get(self, fields):
    #     res = super(ProjectType, self).default_get(fields)
    #     group_id = self.env.ref('project_custom.analytic_group_for_projects')
    #     res['parent_id'] = group_id
    #     return res

    # # Commented By Ajmal
    # analytic_group_id = fields.Many2one('account.analytic.group', string="Account Analytic Group",
    #                                     auto_join=True, index=True, ondelete="cascade", required=True)
    # ?**********


    # parent_id = fields.Many2one('account.analytic.group', string="Parent", ondelete='cascade', default=get_parent_group)
