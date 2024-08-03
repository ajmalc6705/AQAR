# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError


class GatePass(models.Model):
    _name = 'project.gate.pass'
    _inherit = ['mail.thread']
    _description = 'Project Gate Pass'

    # @api.model
    # def gate_pass_expiry(self):
    #     self.env['product.template']._product_available(self._cr, self._uid, self._ids, context=None)
    #     gate_pass_ids = self.env['project.gate.pass'].search([])
    #     for gate_pass_id in gate_pass_ids:
    #         fmt = '%Y-%m-%d'
    #         current_date = fields.date.today()
    #         date_to = self.pass_date_end
    #         d1 = datetime.strptime(str(current_date), fmt)
    #         d2 = datetime.strptime(gate_pass_id.pass_date_end, fmt)
    #         if  gate_pass_id.state not in ['cancel', 'exp']:
    #             if d2 <= d1:
    #                 gate_pass_id.state = 'exp'

    @api.depends('project')
    def get_date(self):
        for rec in self:
            if rec.project:
                rec.project_date_start = rec.project.date_start
                rec.project_date_end = rec.project.date
            else:
                rec.project_date_start = rec.project.date_start
                rec.project_date_end = rec.project.date

    def request(self):
        # if self.photo and self.visa and self.resident_card and self.mulkiya and self.cover_letter and self.agreement and self.driving_license and self.no_people:
        if self.state == 'draft' and self.name == '/':
            self.name = self.env['ir.sequence'].get('gp') or '/'
        users = self.env['res.users'].search([])
        for i in users:
            partners = []
            # user = self.env['res.users'].browse(i)
            if i.has_group('project_custom.group_gp_app'):
                partners.append(i.partner_id.id)
            if partners:
                self.message_subscribe(SUPERUSER_ID, partners)
        self.state = 'validate1'

    def verify(self):
        self.state = 'validate2'

    def done(self):
        self.state = 'done'

    def action_confirm(self):
        self.state = 'confirm'

    def cancel(self):
        self.state = 'cancel'

    def send_back(self):
        if self.state == 'validate1':
            self.state = 'draft'

    def unlink(self):
        restricted_rec = any(rec.name != '/' for rec in self)
        if restricted_rec:
            raise UserError('Action Denied !!! Doc No. assigned.')
        else:
            super(GatePass, self).unlink()

    name = fields.Char('Doc. No.', required=True, copy=False, default='/')
    project_type = fields.Selection([('construction', 'Construction')],
                                    string='Project Type', default='construction', required=True)
    requested_by = fields.Many2one('hr.employee', 'Requested By', required=True,
                                   readonly=True, states={'draft': [('readonly', False)]})
    project = fields.One2many('project.project', 'gate_pass', 'Project',
                              readonly=True, states={'draft': [('readonly', False)]})
    project_date_start = fields.Date('Project Start Date', compute='get_date')
    project_date_end = fields.Date('Project End Date', compute='get_date')
    site_place = fields.Char('Site Location', readonly=True, states={'draft': [('readonly', False)]})
    location_ids = fields.Many2many('project.tender.location', 'gate_pass_loc_rel', string='Locations',
                                    readonly=True, states={'draft': [('readonly', False)]})
    gate_no = fields.Char('Gate No', readonly=True, states={'draft': [('readonly', False)]})
    pass_req = fields.Selection([('sub', 'Sub Contractor'), ('staff', 'Staff')], string="Pass Required For",
                                default='staff', required=True, readonly=True, states={'draft': [('readonly', False)]})
    pass_type = fields.Selection([('temp', 'Temporary'), ('perm', 'Permanent')], string="Type Of pass",
                                 default='temp', required=True, readonly=True, states={'draft': [('readonly', False)]})
    supplier_id = fields.Many2one('res.partner', string='Subcontractor',
                                  readonly=True, states={'draft': [('readonly', False)]})
    no_people = fields.Integer('No. Of People', required=True, default=1,
                               readonly=True, states={'draft': [('readonly', False)]})
    no_vehicle = fields.Integer('No. Of Vehicles', readonly=True, states={'draft': [('readonly', False)]})
    gate_pass_list = fields.One2many('project.gatepass.list', 'gate_pass', string='Gate Pass List')
    photo = fields.Boolean('2 Passport Size Photograph')
    visa = fields.Boolean('1 Passport Visa Photocopy')
    resident_card = fields.Boolean('1 Resident Card Photocopy')
    mulkiya = fields.Boolean('1 Mulkia Copy')
    cover_letter = fields.Boolean('1 Cover Letter')
    agreement = fields.Boolean('1 Agreement Copy')
    driving_license = fields.Boolean('1 Driving License')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    state = fields.Selection([('draft', 'Draft'), ('validate1', 'Waiting Internal Verification'),
                              ('validate2', 'Waiting Approval'), ('validate3', 'Waiting Client Approval'),
                              ('done', 'Active'), ('confirm', 'Confirmed'),
                              ('cancel', 'Cancelled'), ('exp', 'Expired')], tracking=True,
                             string="Status", required=True, default='draft')


class GatePassList(models.Model):
    _name = 'project.gatepass.list'
    _description = 'Project Gate Pass List'

    @api.depends('employee_id')
    def get_job(self):
        for rec in self:
            rec.designation = rec.employee_id.job_id
            # rec.labour_id = rec.employee_id.otherid

    gate_pass = fields.Many2one('project.gate.pass')
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    labour_id = fields.Char('Residence ID')
    # labour_id = fields.Char('Residence ID', compute='get_job')
    pass_date_start = fields.Date('Start Date', required=True)
    pass_date_end = fields.Date('End Date', required=True)
    designation = fields.Many2one('hr.job', 'Designation', compute='get_job')
    doc_id = fields.Binary(string='Document')
    doc_filename = fields.Char(string='Filename')
    location_ids = fields.Many2many('project.tender.location', string='Locations', related='gate_pass.location_ids')
    project_type = fields.Selection(string='Project Type', related='gate_pass.project_type')
    state = fields.Selection(string="Status", related='gate_pass.state')
