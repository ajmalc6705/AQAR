# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ManpowerTransfer(models.Model):
    _name = 'manpower.transfer'
    _inherit = ['mail.thread']
    _description = 'Manpower Transfer'

    @api.onchange('project_from', 'location_from')
    def set_project_to(self):
        for rec in self:
            rec.update({
                'employees_from': [(5,)]
            })
            if not rec.project_to and rec.project_from:
                rec.project_to = rec.project_from
            employee_ids = rec.location_from.mapped('employee_ids')
            rec.update({
                'employees_from': [(0, 0, {
                    'employee_id': emp.id
                }) for emp in employee_ids]
            })

    @api.onchange('location_to')
    def set_gate_pass_availability(self):
        for rec in self:
            if rec.location_to:
                rec.update({
                    'employees_from': [(5,)]
                })
                employee_ids = rec.location_from.mapped('employee_ids')
                employees_from = []
                for emp in employee_ids:
                    gate_pass = self.env['project.gatepass.list'].search([
                        ('employee_id', '=', emp.id), ('pass_date_start', '<=', rec.effective_date),
                        ('pass_date_end', '>=', rec.effective_date),
                        ('state', '=', 'confirm'), ('location_ids', 'in', [rec.location_to.id])])
                    employees_from.append((0, 0, {
                        'employee_id': emp.id,
                        'gate_pass_available': 'yes' if gate_pass else 'no'
                    }))
                rec.update({
                    'employees_from': employees_from
                })

    @api.onchange('project_from', 'project_to', 'location_from', 'location_to')
    def get_tender_domain(self):
        loc_from_domain = []
        loc_to_domain = []
        res = dict()
        if self.project_from and self.project_to and self.location_from and self.location_to:
            if self.project_from == self.project_to and self.location_to == self.location_from:
                raise UserError("You cant transfer to same location, Please change the location or project")
        if self.project_from:
            pro_from_locations = self.env['project.tender.location'].search([('project_id', '=', self.project_from.id)])
            loc_from_domain += [('id', 'in', pro_from_locations.ids)]
        if self.project_to:
            pro_to_locations = self.env['project.tender.location'].search([('project_id', '=', self.project_to.id)])
            loc_to_domain += [('id', 'in', pro_to_locations.ids)]
        if self.location_from and self.project_to:
            if self.project_from and self.project_from == self.project_to:
                pro_from_locations = self.env['project.tender.location'].search(
                    [('project_id', '=', self.project_to.id),
                     ('id', '!=', self.location_from.id)])
                loc_to_domain = [('id', 'in', pro_from_locations.ids)]
            else:
                pro_from_locations = self.env['project.tender.location'].search(
                    [('project_id', '=', self.project_to.id)])
                loc_to_domain = [('id', 'in', pro_from_locations.ids)]
        res['domain'] = {
            'location_from': loc_from_domain,
            'location_to': loc_to_domain
        }
        return res

    # @api.multi
    # @api.constrains('effective_date')
    # def check_date(self):
    #     for rec in self:
    #         if fields.Date.from_string(rec.effective_date) < date.today():
    #             raise UserError(_('You can\'t create transfer on previous date.'))

    name = fields.Char(string='Ref:', copy=False, default=lambda self: '/', readonly=True)
    transfer_type = fields.Selection([('p2p', 'Project to Project'),
                                      ('l2l', 'Location to Location')], string='Transfer Type')
    effective_date = fields.Date(string='Effective Date', required=True,
                                 readonly=True, states={'draft': [('readonly', False)]})
    project_from = fields.Many2one('project.project', string='Project From', required=True,
                                   readonly=True, states={'draft': [('readonly', False)]})
    project_to = fields.Many2one('project.project', string='Project To', required=True,
                                 readonly=True, states={'draft': [('readonly', False)]})
    location_from = fields.Many2one('project.tender.location', string='Location From', required=True,
                                    readonly=True, states={'draft': [('readonly', False)]})
    location_to = fields.Many2one('project.tender.location', string='Location To', required=True,
                                  readonly=True, states={'draft': [('readonly', False)]})
    employees_from = fields.One2many('manpower.transfer.line', 'transfer_id',
                                     string='Employees From', domain=[('state', '=', 'draft')])
    employees_to = fields.One2many('manpower.transfer.line', 'transfer_id',
                                   string='Employees To', domain=[('state', '=', 'done')])
    is_transferred = fields.Boolean(string='Is Transferred', default=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    state = fields.Selection([('draft', 'Draft'),
                              ('section_head', 'Section Head'),
                              ('pa', 'Personal Affairs'),
                              ('pa_section_head', 'PA Section Head'),
                              ('payroll_acc', 'Payroll Accountant'),
                              ('confirmed', 'Confirmed')], string='State', default='draft', tracking=True)
    remarks = fields.Text(string='Remarks', copy=False,
                          readonly=True, states={'draft': [('readonly', False)]})

    @api.model
    def create(self, vals):
        if 'name' not in vals or vals['name'] == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('manpower.transfer') or '/'
        res = super(ManpowerTransfer, self).create(vals)
        return res

    def send_to_section_head(self):
        for rec in self:
            if rec.project_from and rec.project_to and rec.location_from and rec.location_to:
                if rec.project_from == rec.project_to and rec.location_to == rec.location_from:
                    raise UserError("You cant transfer to same location, Please check the locations")
            rec.state = 'section_head'

    def send_to_pa(self):
        for rec in self:
            rec.state = 'pa'

    def send_to_pa_section_head(self):
        for rec in self:
            rec.state = 'pa_section_head'

    def send_to_payroll_acc(self):
        for rec in self:
            rec.state = 'payroll_acc'

    def send_back(self):
        """send back to previous state"""
        for record in self:
            if record.state == 'section_head':
                record.write({'state': 'draft'})
            elif record.state == 'pa':
                record.write({'state': 'draft'})
            elif record.state == 'pa_section_head':
                record.write({'state': 'draft'})
            elif record.state == 'payroll_acc':
                record.write({'state': 'draft'})

    def action_confirm(self):
        for rec in self:
            if not rec.employees_to.filtered(lambda x: x.state == 'done'):
                raise UserError(_("Please select some employees for transfer."))
            not_transferred = rec.employees_from.filtered(lambda x: x.state == 'draft')
            for emp in not_transferred:
                emp.unlink()
            rec.state = 'confirmed'
            rec.update_manpower_transfer()

    def update_manpower_transfer(self):
        for rec in self.search([('state', '=', 'confirmed'),
                                ('is_transferred', '=', False),
                                ('effective_date', '=', fields.Date.today())]):
            for line in rec.employees_to:
                query = "DELETE FROM loc_employee_rel where employee_id = '" + str(line.employee_id.id) + "' " \
                                                                                                          "AND location_id = '" + str(
                    rec.location_from.id) + "'"
                self._cr.execute(query)
                u_query = "INSERT INTO loc_employee_rel VALUES('" + str(rec.location_to.id) + "', '" + str(
                    line.employee_id.id) + "')"
                self._cr.execute(u_query)
                # rec.location_from.update({
                #     'employee_ids': [(3, line.employee_id.id,)],
                # })
                # rec.location_to.update({
                #     'employee_ids': [(4, line.employee_id.id,)],
                # })
                line.employee_id.current_project_id = rec.project_to.id
                line.employee_id.current_location_id = rec.location_to.id
                values = {
                    'employee_id': line.employee_id.id,
                    'mode_of_activity': 'transfer',
                    'from_location': rec.location_from.id,
                    'to_location': rec.location_to.id,
                    'name': rec.name,
                }
                self.env['manpower.history'].create(values)
            rec.is_transferred = True

    def unlink(self):
        """retrict deleting the record, if it is not in draft state"""
        for record in self:
            if record.state != 'draft':
                raise UserError("Only the Draft transfer can delete")
        return super(ManpowerTransfer, self).unlink()


class ManpowerTransferLine(models.Model):
    _name = 'manpower.transfer.line'
    _description = 'Manpower Transfer Line'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    gate_pass_available = fields.Selection([('yes', 'Available'), ('no', 'Not Available')], string='Gate Pass')
    transfer_id = fields.Many2one('manpower.transfer', string='Transfer')
    project_from = fields.Many2one('project.project', string='Project From', related='transfer_id.project_from')
    project_to = fields.Many2one('project.project', string='Project To', related='transfer_id.project_to')
    location_from = fields.Many2one('project.tender.location', string='Location From',
                                    related='transfer_id.location_from')
    effective_date = fields.Date(string='Transfer Date', related='transfer_id.effective_date', store=True)
    location_to = fields.Many2one('project.tender.location', string='Location To', related='transfer_id.location_to')
    transfer_state = fields.Selection(string='Transfer State', related='transfer_id.state')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], string='State', default='draft')

    def action_transfer(self):
        for rec in self:
            exit_rec = self.env['hr.exit'].search([('employee_id', '=', rec.employee_id.id), ('state', '=', 'approve')])
            if exit_rec:
                raise UserError(_('Selected employee is going to exit from the organization.'))
            rec.update({
                'state': 'done'
            })

    def action_return_transfer(self):
        for rec in self:
            rec.update({
                'state': 'draft'
            })


class ManpowerHistory(models.Model):
    _name = 'manpower.history'
    _description = 'Manpower History'

    name = fields.Char(string='Reference', copy=False)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', copy=False)
    mode_of_activity = fields.Selection([('transfer', 'Transfer'),
                                         ('resig', 'Resignation'),
                                         ('retire', 'Retirement'),
                                         ('term', 'Termination'),
                                         ('abs', 'Absconding'),
                                         ], string='Type')
    from_location = fields.Many2one(comodel_name='project.tender.location', string='From Location')
    to_location = fields.Many2one(comodel_name='project.tender.location', string='To Location')
    project = fields.Boolean(string='Project', copy=False)
    project_from = fields.Many2one('project.project', string='Project From')
    project_to = fields.Many2one('project.project', string='Project To')


class ManpowerTransferProject(models.Model):
    _name = 'manpower.transfer.project'
    _inherit = ['mail.thread']
    _description = 'Project Manpower Transfer'
    _order = 'id DESC'

    @api.onchange('project_from', 'job_type')
    def set_project_to(self):
        try:
            for rec in self:
                rec.update({
                    'employees_from': [(5,)],
                    'employees_to': [(5,)]
                })
                emp_dict = []
                if rec.job_type == 'all':
                    # import ipdb;ipdb.set_trace()
                    # employee_ids = rec.project_from.mapped('w_supervisor')
                    for w_sup in rec.project_from.mapped('w_supervisor'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_supervisor'}
                        emp_dict.append(vals)
                    for w_sup in rec.project_from.mapped('w_fm'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_fm'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_fm')
                    # employee_ids += rec.project_from.mapped('w_ch')
                    for w_sup in rec.project_from.mapped('w_ch'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_ch'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_sh')
                    for w_sup in rec.project_from.mapped('w_sh'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_sh'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_fc')
                    for w_sup in rec.project_from.mapped('w_fc'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_fc'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_sf')
                    for w_sup in rec.project_from.mapped('w_sf'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_sf'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_mason')
                    for w_sup in rec.project_from.mapped('w_mason'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_mason'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_tm')
                    for w_sup in rec.project_from.mapped('w_tm'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_tm'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_ppo')
                    for w_sup in rec.project_from.mapped('w_ppo'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_ppo'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_helper')
                    for w_sup in rec.project_from.mapped('w_helper'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_helper'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_sk')
                    for w_sup in rec.project_from.mapped('w_sk'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_sk'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_cb')
                    for w_sup in rec.project_from.mapped('w_cb'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_cb'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_ob')
                    for w_sup in rec.project_from.mapped('w_ob'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_ob'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_driver')
                    for w_sup in rec.project_from.mapped('w_driver'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_fm'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('m_supervisor')
                    for w_sup in rec.project_from.mapped('m_supervisor'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'm_supervisor'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_elec')
                    for w_sup in rec.project_from.mapped('w_elec'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_elec'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_pl')
                    for w_sup in rec.project_from.mapped('w_pl'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_pl'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('m_helper')
                    for w_sup in rec.project_from.mapped('m_helper'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'm_helper'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('m_cable')
                    for w_sup in rec.project_from.mapped('m_cable'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'm_cable'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('m_ac_tech')
                    for w_sup in rec.project_from.mapped('m_ac_tech'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'm_ac_tech'}
                        emp_dict.append(vals)
                    # employee_ids += rec.project_from.mapped('w_jcb_rcc_optr')
                    for w_sup in rec.project_from.mapped('w_jcb_rcc_optr'):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': 'w_jcb_rcc_optr'}
                        emp_dict.append(vals)
                else:
                    # employee_ids = rec.project_from.mapped(rec.job_type)
                    for w_sup in rec.project_from.mapped(rec.job_type):
                        vals = {'emp': w_sup.id,
                                'job_id': w_sup.job_id.id,
                                'job_type': str(rec.job_type)}
                        emp_dict.append(vals)
                rec.update({
                    'employees_from': [(0, 0, {
                        'employee_id': emp['emp'],
                        'job_id': emp['job_id'],
                        'job_type': emp['job_type'],
                    }) for emp in emp_dict]
                })
        except Exception as e:
            pass

    name = fields.Char(string='Ref:', copy=False, default=lambda self: '/', readonly=True)
    effective_date = fields.Date(string='Effective Date', required=True,
                                 readonly=True, states={'draft': [('readonly', False)]})
    project_from = fields.Many2one('project.project', string='Project From', required=True,
                                   readonly=True, states={'draft': [('readonly', False)]})
    project_to = fields.Many2one('project.project', string='Project To', required=True,
                                 readonly=True, states={'draft': [('readonly', False)]})
    employees_from = fields.One2many('manpower.transfer.line.project', 'transfer_id',
                                     string='Employees From', domain=[('state', '=', 'draft')])
    employees_to = fields.One2many('manpower.transfer.line.project', 'transfer_id',
                                   string='Employees To', domain=[('state', '=', 'done')])
    is_transferred = fields.Boolean(string='Is Transferred', default=False)
    state = fields.Selection([('draft', 'Draft'),
                              ('section_head', 'Section Head'),
                              ('pa', 'Personal Affairs'),
                              ('pa_section_head', 'PA Section Head'),
                              ('payroll_acc', 'Payroll Accountant'),
                              ('confirmed', 'Confirmed')], string='State', default='draft', tracking=True)
    remarks = fields.Text(string='Remarks', copy=False,
                          readonly=True, states={'draft': [('readonly', False)]})
    job_type = fields.Selection([('all', 'ALL'),
                                 ('w_supervisor', 'Supervisor'),
                                 ('w_fm', 'Foreman'),
                                 ('w_ch', 'Charge hand'),
                                 ('w_sh', 'Shuttering Carpenter'),
                                 ('w_fc', 'Furniture Carpenter'),
                                 ('w_sf', 'Steel Fitter'),
                                 ('w_mason', 'Mason'),
                                 ('w_tm', 'Tiles Mason'),
                                 ('w_ppo', 'Painter/Polisher'),
                                 ('w_helper', 'Helper'),
                                 ('w_sk', 'Store Keeper'),
                                 ('w_cb', 'Camp Boss'),
                                 ('w_ob', 'Office Boy'),
                                 ('w_driver', 'Driver'),
                                 ('m_supervisor', 'MEP Supervisor'),
                                 ('w_elec', 'Electrician'),
                                 ('w_pl', 'Plumber'),
                                 ('m_helper', 'MEP Helper'),
                                 ('m_cable', 'Structured Cabling'),
                                 ('m_ac_tech', 'A/C Tech'),
                                 ('w_jcb_rcc_optr', 'JCB/RCC/Oprtr'),
                                 ], string='Worker Type', copy=False, readonly=True,
                                states={'draft': [('readonly', False)]})

    @api.model
    def create(self, vals):
        if 'name' not in vals or vals['name'] == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('manpower.transfer.project') or '/'
        res = super(ManpowerTransferProject, self).create(vals)
        return res

    def send_to_section_head(self):
        for rec in self:
            if not rec.employees_to:
                raise UserError(_("Please select some employees for transfer."))
            if rec.project_from and rec.project_to:
                if rec.project_from == rec.project_to:
                    raise UserError("You cant transfer to same Project.")
            rec.state = 'section_head'

    def send_back(self):
        """send back to previous state"""
        for record in self:
            if record.state == 'section_head':
                record.write({'state': 'draft'})

    def action_confirm(self):
        """confirm the manpower transfer"""
        for rec in self:
            if not rec.employees_to.filtered(lambda x: x.state == 'done'):
                raise UserError(_("Please select some employees for transfer."))
            not_transferred = rec.employees_from.filtered(lambda x: x.state == 'draft')
            for emp in not_transferred:
                emp.unlink()
            rec.state = 'confirmed'
            rec.update_manpower_transfer()

    def update_manpower_transfer(self):
        """
        cron job to transfer the manpower between the projects
        :return: None
        """
        for rec in self.search([('state', '=', 'confirmed'),
                                ('is_transferred', '=', False),
                                ('effective_date', '<=', fields.Date.today())]):
            for line in rec.employees_to:
                if not rec.project_from == rec.project_to:
                    rec.project_from.update({
                        str(line.job_type): [(3, line.employee_id.id,)],
                    })
                    rec.project_to.update({
                        str(line.n_job_type if line.n_job_type else line.job_type): [(4, line.employee_id.id,)],
                    })
                    line.employee_id.current_project_id = rec.project_to.id
                    values = {
                        'employee_id': line.employee_id.id,
                        'mode_of_activity': 'transfer',
                        'name': rec.name,
                        'project_from': rec.project_from.id,
                        'project_to': rec.project_to.id,
                        'project': True,
                    }
                    self.env['manpower.history'].create(values)
                if line.r_person:
                    line.employee_id.parent_id = line.r_person.id  # change the reporting person
            rec.is_transferred = True

    def unlink(self):
        """restrict deleting the record, if it is not in draft state"""
        for record in self:
            if record.state != 'draft':
                raise UserError("Only the Draft transfer can delete")
        return super(ManpowerTransferProject, self).unlink()


class ManpowerTransferLineProject(models.Model):
    _name = 'manpower.transfer.line.project'
    _description = 'Manpower Transfer Project Line'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    gate_pass_available = fields.Selection([('yes', 'Available'), ('no', 'Not Available')], string='Gate Pass')
    transfer_id = fields.Many2one('manpower.transfer.project', string='Transfer')
    project_from = fields.Many2one('project.project', string='Project From', related='transfer_id.project_from')
    project_to = fields.Many2one('project.project', string='Project To', related='transfer_id.project_to')
    effective_date = fields.Date(string='Transfer Date', related='transfer_id.effective_date', store=True)
    transfer_state = fields.Selection(related='transfer_id.state', string='Transfer State')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], string='State', default='draft')
    job_id = fields.Many2one(comodel_name='hr.job', string='Job', copy=False)
    job_type = fields.Selection([('w_supervisor', 'Supervisor'),
                                 ('w_fm', 'Foreman'),
                                 ('w_ch', 'Charge hand'),
                                 ('w_sh', 'Shuttering Carpenter'),
                                 ('w_fc', 'Furniture Carpenter'),
                                 ('w_sf', 'Steel Fitter'),
                                 ('w_mason', 'Mason'),
                                 ('w_tm', 'Tiles Mason'),
                                 ('w_ppo', 'Painter/Polisher'),
                                 ('w_helper', 'Helper'),
                                 ('w_sk', 'Store Keeper'),
                                 ('w_cb', 'Camp Boss'),
                                 ('w_ob', 'Office Boy'),
                                 ('w_driver', 'Driver'),
                                 ('m_supervisor', 'MEP Supervisor'),
                                 ('w_elec', 'Electrician'),
                                 ('w_pl', 'Plumber'),
                                 ('m_helper', 'MEP Helper'),
                                 ('m_cable', 'Structured Cabling'),
                                 ('m_ac_tech', 'A/C Tech'),
                                 ('w_jcb_rcc_optr', 'JCB/RCC/Oprtr'),
                                 ], string='Worker Job', copy=False)
    n_job_type = fields.Selection([('w_supervisor', 'Supervisor'),
                                   ('w_fm', 'Foreman'),
                                   ('w_ch', 'Charge hand'),
                                   ('w_sh', 'Shuttering Carpenter'),
                                   ('w_fc', 'Furniture Carpenter'),
                                   ('w_sf', 'Steel Fitter'),
                                   ('w_mason', 'Mason'),
                                   ('w_tm', 'Tiles Mason'),
                                   ('w_ppo', 'Painter/Polisher'),
                                   ('w_helper', 'Helper'),
                                   ('w_sk', 'Store Keeper'),
                                   ('w_cb', 'Camp Boss'),
                                   ('w_ob', 'Office Boy'),
                                   ('w_driver', 'Driver'),
                                   ('m_supervisor', 'MEP Supervisor'),
                                   ('w_elec', 'Electrician'),
                                   ('w_pl', 'Plumber'),
                                   ('m_helper', 'MEP Helper'),
                                   ('m_cable', 'Structured Cabling'),
                                   ('m_ac_tech', 'A/C Tech'),
                                   ('w_jcb_rcc_optr', 'JCB/RCC/Oprtr'),
                                   ], string='New Worker Job', copy=False)
    r_person = fields.Many2one(comodel_name='hr.employee', string='New Reporting Person', copy=False,
                               domain=[('admin_staff', '=', True)])

    def action_transfer(self):
        for rec in self:
            rec.project_to.update({
                rec.job_type: [(4, rec.employee_id.id)]
            })
            # exit_rec = self.env['hr.exit'].search([('employee_id', '=', rec.employee_id.id), ('state', '=', 'approve')])
            # if exit_rec:
            #     raise UserError(_('Selected employee is going to exit from the organization.'))
            rec.update({
                'state': 'done'
            })

    def action_return_transfer(self):
        for rec in self:
            rec.update({
                'state': 'draft'
            })
