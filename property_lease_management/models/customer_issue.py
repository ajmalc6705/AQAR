# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CustomerIssue(models.Model):
    _name = 'customer.complaints'
    _description = _('Customer Issues')
    _rec_name = 'complaint_no'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def button_dummy(self):
        return True

    @api.depends('product_ids')
    def _total_amount(self):
        """Calculating total  estimated and actual Amount
        """
        total = 0.0
        actual_total = 0.0
        if self.product_ids:
            for line in self.product_ids:
                total += line.subtotal
                actual_total += line.actual_subtotal
        self.estimated_total_amount = total
        self.total_amount = actual_total

    @api.model
    def _get_currency(self):
        company_id = self.env.company
        return company_id.currency_id

    # def compute_mrf_count(self):
    #     if self.mr:
    #         self.mrf_count = 1
    #     else:
    #         self.mrf_count = 0
    #
    # def compute_sr_count(self):
    #     if self.sr:
    #         self.sr_count = 1
    #     else:
    #         self.sr_count = 0

    complaint_no = fields.Char(string='Name', required=True, default=_('Customer Complaints'))
    date = fields.Date(string='Date', default=fields.Date.today)
    building = fields.Many2one(comodel_name='property.building', string='Building', required=True)
    property = fields.Many2one(comodel_name='property.property', string='Unit', required=True,
                               invisible=True, states={'issue': [('invisible', False)]})
    complain_initiated_by = fields.Selection([('care_taker', _('Care Taker')), ('tenant', _('Tenant'))],
                                             string='Complaint Initiated by', default='care_taker')
    care_taker = fields.Char(string='Care Taker')
    user_id = fields.Many2one(comodel_name='res.users', string='Complaint Recorded By',
                              default=lambda self: self.env.user)
    tenant_id = fields.Many2one(comodel_name='res.partner', string='Tenant')
    tenant_ph = fields.Char(string='Tenant Contact No.')
    contact_person = fields.Char(string='Contact Person')
    state = fields.Selection([('issue', _('Issue')),
                              ('with_section', _('Property Management Head')),
                              ('with_section2', _('Property Management Head')),
                              ('with_ceo', _('Procurement Department')), ('approve', _('Approved')),
                              ('done', _('Cleared')), ('cancel', _('Rejected'))],
                             string='Status', default='issue', tracking=True)
    # job allocation
    job_by_suprvsr = fields.Many2one(comodel_name='res.users', string='Job Assigned by Supervisor',
                                     default=lambda self: self.env.user)
    exp_date = fields.Date(string='Expected Completed Date', default=fields.date.today())
    alloc_date = fields.Date(string='Job Allocation Date')
    approved_date = fields.Date(string='Approved Date')
    # job completed
    compl_emp = fields.Many2one(comodel_name='hr.employee', string='Job Completed  Employee')
    approved_by = fields.Many2one(comodel_name='hr.employee', string='Approved By')
    cost = fields.Float(string='Cost of repairs', digits='Property')
    approv_suprvsr = fields.Many2one(comodel_name='res.users', string='Approved  by Supervisor')
    compld_date = fields.Date(string='Job Completed Date')
    parts_replaced = fields.Text(string='Parts Replaced')
    warrenty_cheq = fields.Selection([('no', _('No')), ('yes', _('Yes'))], string='Under Warranty')
    product_ids = fields.One2many(comodel_name='product.complaints', inverse_name='complaint_id', string='Product')
    estimated_total_amount = fields.Float(string='Estimated Total', compute='_total_amount', readonly=True,
                                          store=True, digits='Property')
    total_amount = fields.Float(string='Actual Total', compute='_total_amount', readonly=True, digits='Property',
                                store=True)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', required=True, readonly=True,
                                  default=_get_currency)
    # mr = fields.Many2one(comodel_name='mr', string='Material Requisition')
    # sr = fields.Many2one(comodel_name='mr', string='SR')
    complaint_details = fields.One2many(comodel_name='complaint.details', inverse_name='complaint_id',
                                        string='Complaints')
    complaint_details_1 = fields.One2many(comodel_name='complaint.details', inverse_name='complaint_id',
                                          string='Complaints Details')
    mrf_count = fields.Integer(string='MRF', compute='compute_mrf_count')
    sr_count = fields.Integer(string='SR Count', compute='compute_sr_count')
    company_id = fields.Many2one(comodel_name='res.company', string=_('Company'), change_default=True,
                                 default=lambda self: self.env.company,
                                 readonly=True, states={'draft': [('readonly', False)]})

    doc_ids = fields.Many2many('atheer.documents',
                               string='Documents')
    agreement_no = fields.Many2one(comodel_name='property.rent', string='Agreement No.')
    inspection_date = fields.Datetime(string='Inspection Date')
    residing_since = fields.Date(string='Residing Since', related='agreement_no.residing_since', store=True)
    tenant_years = fields.Char(string='Tenancy Period (Years)', related='agreement_no.tenant_years', store=True)
    remarks = fields.Text("Remarks")
    direct_approve_visibility = fields.Boolean('show direct approve button', default=False,
                                               compute="_compute_button_visibility")
    to_property_visibility = fields.Boolean('show property button', default=False, compute="_compute_button_visibility")

    mrs_date = fields.Date("MRS Date")
    mrs_reference = fields.Char("MRS Reference")
    mrs_project_code_location = fields.Char("MRS Project Code - Location")
    mrs_attachments = fields.Char("MRS Attachments")
    mrs_requested_by = fields.Many2one("res.users", "MRS Requested By", default=lambda self: self.env.user)
    mrs_project_head = fields.Many2one("res.users", "MRS Property Head")
    mrs_procurement_head = fields.Many2one("res.users", "MRS Procurement Head")
    mrs_sheet_ids = fields.One2many(comodel_name='materials.requisition.sheet', inverse_name='customer_complaint_id',
                                    string='MRS Sheet')

    srs_date = fields.Date("SRS Date")
    srs_reference = fields.Char("SRS Reference")
    srs_project_code_location = fields.Char("SRS Project Code - Location")
    srs_attachments = fields.Char("SRS Attachments")
    srs_requested_by = fields.Many2one("res.users", "SRS Requested By", default=lambda self: self.env.user)
    srs_project_head = fields.Many2one("res.users", "SRS Property Head")
    srs_procurement_head = fields.Many2one("res.users", "SRS Procurement Head")
    srs_sheet_ids = fields.One2many(comodel_name='services.requisition.sheet', inverse_name='customer_complaint_id',
                                    string='SRS Sheet')
    send_back_flag = fields.Boolean(default=False)
    procurement_flag = fields.Boolean(default=False)
    procurement_approved = fields.Boolean(default=False)


    @api.onchange('property')
    def _onchange_property(self):
        rent_ids = self.env['property.rent'].search([('property_id', '=', self.property.id)])
        return {'domain': {'agreement_no': [('id', 'in', rent_ids.ids)]}}

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(CustomerIssue, self).unlink()

    def _compute_button_visibility(self):
        """ compute the visibility of the approval buttons """
        for rec in self:
            if rec.state == 'issue':
                if rec.complaint_details.filtered(lambda x: x.priority == 'high'):
                    rec.to_property_visibility = True
                    rec.direct_approve_visibility = False
                else:
                    rec.to_property_visibility = True
                    rec.direct_approve_visibility = True
            else:
                rec.to_property_visibility = False
                rec.direct_approve_visibility = False

    def direct_approve(self):
        """ approve directly """
        if self.complaint_details.filtered(lambda x: x.priority == 'high'):
            raise UserError("You cannot directly approve as there is a Major complaint")
        self.to_approve()
        self.send_back_flag = False

    @api.onchange('tenant_id')
    def onchange_tenant_id(self):
        if self.tenant_id:
            self.tenant_ph = self.tenant_id.phone

    @api.onchange('property')
    def onchange_property(self):
        self.agreement_no = False
        if self.property:
            rent_rec = self.env['property.rent'].search(
                [('property_id', '=', self.property.id), ('state', 'in', ('open', 'notice', 'take_over', 'to_renew'))])
            if rent_rec:
                self.agreement_no = rent_rec[0]
                self.tenant_id = rent_rec[0].partner_id

    @api.onchange('agreement_no')
    def onchange_agreement_no(self):
        # self.agreement_no = False
        if self.agreement_no:
            if self.agreement_no.partner_id:
                self.tenant_id = self.agreement_no.partner_id.id

    def name_get(self):
        res = []
        for each in self:
            name = each.complaint_no
            if each.property:
                res.append((each.id, name + '_' + str(each.property.name)))
            else:
                res.append((each.id, name))
        return res

    @api.model
    def create(self, vals):
        if vals.get('complaint_no', _('Customer Complaints')) == _('Customer Complaints'):
            vals['complaint_no'] = self.env['ir.sequence'].next_by_code('customer.issue') or _('Customer Complaints')
        return super(CustomerIssue, self).create(vals)

    def send_back(self):
        """ move to issue stage """
        for rec in self:
            rec.state = 'issue'
            rec.send_back_flag = True

    def move_to_refuse(self):
        """ move to cancelled stage """
        for rec in self:
            rec.state = 'cancel'
            rec.send_back_flag = False

    def to_approve(self):
        for rec in self:
            rec.send_back_flag = False
            rec.mrs_procurement_head = self.env.user.id
            rec.srs_procurement_head = self.env.user.id
            rec.state = 'approve'
            rec.procurement_approved = True
            employee = self.env['hr.employee'].search([('user_id', '=', self._uid)], limit=1)
            if employee:
                rec.approved_by = employee[0]
            rec.approved_date = fields.date.today()
            maintenance_ids = []
            for complaint in rec.complaint_details:
                complaint.state = 'open'
                maintenance_vals = {'property_id': rec.property.id,
                                    'complaint_id': rec.id,
                                    'asset_id': complaint.asset.id,
                                    'supervisor': rec.job_by_suprvsr.id,
                                    'tenant_id': rec.tenant_id.id,
                                    'building': rec.building.id,
                                    'done_date': rec.exp_date,
                                    'due_date': rec.exp_date,
                                    'maintenance_type': 'adhoc',
                                    'priority': complaint.priority,
                                    'state': 'approved'
                                    }
                maintenance = self.env['property.maintenance'].sudo().create(maintenance_vals)
                maintenance_ids.append(maintenance.id)
            # notification_obj = self.env['atheer.notification']
            # notification_obj._send_instant_notify(title="Maintenance Requests",
            #                                       message='Maintenance Requests created from Client Complaint ' + str(
            #                                           rec.complaint_no),
            #                                       action=self.env.ref(
            #                                           'property_lease_management.action_property_maintenance').id,
            #                                       domain=[['id', 'in', maintenance_ids]],
            #                                       user_type="groups",
            #                                       recipient_ids=[self.env.ref(
            #                                           'property_lease_management.group_property_user').id])
            for line in rec.product_ids:
                line.estimate = True
        return True

    def to_property_head(self):
        for rec in self:
            rec.send_back_flag = False
            # if not self.complaint_details.filtered(lambda x: x.priority == 'high'):
            #     raise UserError("You can directly approve the complaint")
            rec.state = 'with_section'
            # notification_obj = self.env['atheer.notification']
            # notification_obj._send_instant_notify(title="Customer Complaint",
            #                                       message='Pending approval for Customer Complaint ' + str(
            #                                           rec.complaint_no),
            #                                       action=self.env.ref(
            #                                           'property_lease_management.action_customer_issue_form').id,
            #                                       domain=[['id', '=', rec.id]],
            #                                       user_type="groups",
            #                                       recipient_ids=[self.env.ref(
            #                                           'property_lease_management.group_property_head').id])

    def to_srs_and_mrs(self):
        for rec in self:
            if not rec.complaint_details.filtered(lambda x: x.priority == 'high'):
                rec.direct_approve()
            else:
                rec.send_back_flag = False
                rec.state = 'with_section2'
                # notification_obj = self.env['atheer.notification']
                # notification_obj._send_instant_notify(title="Customer Complaint",
                #                                     message='Need to create SRS & MRS for Complaint ' + str(
                #                                         rec.complaint_no),
                #                                     action=self.env.ref(
                #                                         'property_lease_management.action_customer_issue_form').id,
                #                                     domain=[['id', '=', rec.id]],
                #                                     user_type="groups",
                #                                     recipient_ids=[self.env.ref(
                #                                         'property_lease_management.group_property_user').id])

    def sen_to_procurement(self):
        for rec in self:
            rec.send_back_flag = False
            rec.mrs_project_head = self.env.user.id
            rec.srs_project_head = self.env.user.id
            rec.state = 'with_ceo'
            rec.procurement_flag = True
            # notification_obj = self.env['atheer.notification']
            # notification_obj._send_instant_notify(title="Customer Complaint",
            #                                       message='Pending approval for Customer Complaint ' + str(
            #                                           rec.complaint_no),
            #                                       action=self.env.ref(
            #                                           'property_lease_management.action_customer_issue_form').id,
            #                                       domain=[['id', '=', rec.id]],
            #                                       user_type="groups",
            #                                       recipient_ids=[self.env.ref(
            #                                           'property_lease_management.group_property_procurement').id])

    def to_property_head2(self):
        for rec in self:
            rec.state = 'with_section2'
            rec.send_back_flag = False
            # notification_obj = self.env['atheer.notification']
            # notification_obj._send_instant_notify(title="Customer Complaint",
            #                                       message='Pending approval for Customer Complaint ' + str(
            #                                           rec.complaint_no),
            #                                       action=self.env.ref(
            #                                           'property_lease_management.action_customer_issue_form').id,
            #                                       domain=[['id', '=', rec.id]],
            #                                       user_type="groups",
            #                                       recipient_ids=[self.env.ref(
            #                                           'property_lease_management.group_property_head').id])

    def create_mrf(self):
        print("Not needed in Aqar")
        # if not self.mr:
        #     r = []
        #     bu_cc = False
        #     vals = {}
        #     if self.product_ids:
        #         for record in self.product_ids:
        #             if record.type == 'mr':
        #                 lines = {}
        #                 lines['product_id'] = record.name.id
        #                 lines['qty'] = record.qty
        #                 lines['description'] = record.name.name
        #                 lines['uom'] = record.name.uom_id.id
        #                 lines['req_on_site'] = fields.Date.today()
        #                 r.append((0, 0, lines))
        #         if self.building.bu_cc:
        #             bu_cc = self.building.bu_cc.id
        #     vals['type'] = 'other'
        #     vals['mrf_type'] = 'op_expense'
        #     vals['bu_cc'] = bu_cc
        #     vals['mr_no'] = '/'
        #     vals['mr_order_line_3'] = r
        #     mr = self.env['mr'].create(vals)
        #     self.mr = mr
        # action = self.env["ir.actions.act_window"]._for_xml_id('amlak_mr.open_mr_form')
        # form_view = self.env.ref('amlak_mr.view_mr_form')
        # action['views'] = [(form_view.id, 'form')]
        # if self.mr:
        #     action['res_id'] = self.mr and self.mr.id or False
        # return action

    def create_sr(self):
        print("not needed in Aqar")
        # if not self.sr:
        #     r = []
        #     bu_cc = False
        #     vals = {}
        #     if self.product_ids:
        #         for record in self.product_ids:
        #             if record.type == 'mr':
        #                 lines = {}
        #                 lines['product_id'] = record.name.id
        #                 lines['qty'] = record.qty
        #                 lines['description'] = record.name.name
        #                 lines['uom'] = record.name.uom_id.id
        #                 lines['req_on_site'] = fields.Date.today()
        #                 r.append((0, 0, lines))
        #         if self.building.bu_cc:
        #             bu_cc = self.building.bu_cc.id
        #     vals['type'] = 'cons'
        #     vals['request_type'] = 'sr'
        #     vals['bu_cc'] = bu_cc
        #     vals['mr_no'] = '/'
        #     vals['mr_order_line_3'] = r
        #     sr = self.env['mr'].create(vals)
        #     self.sr = sr
        # action = self.env["ir.actions.act_window"]._for_xml_id('amlak_mr.open_mr_form')
        # form_view = self.env.ref('amlak_mr.view_mr_form')
        # action['views'] = [(form_view.id, 'form')]
        # if self.sr:
        #     action['res_id'] = self.sr and self.sr.id or False
        # return action

    def mrf(self):
        print("not needed in Aqar")
        """
        :return:
        """
        # result = self.env.ref('amlak_mr.open_mr_form')
        # result = result.read([])[0]
        # res = self.env.ref('amlak_mr.view_mr_form')
        # result['views'] = [(res and res.id or False, 'form')]
        # if self.mr:
        #     result['res_id'] = self.mr.id
        #     return result


class MaterialsRequisitionSheet(models.Model):
    _name = 'materials.requisition.sheet'
    _description = 'Materials Requisition Sheet'

    description = fields.Char(string='Descrption')
    required_date = fields.Date(string='Required Date')
    allocated_budget_ro = fields.Char(string='Allocated Budget (R.O)')
    remarks = fields.Char(string='Remarks')
    customer_complaint_id = fields.Many2one(
        string='Customer Complaint',
        comodel_name='customer.complaints',
    )


class ServicesRequisitionSheet(models.Model):
    _name = 'services.requisition.sheet'
    _description = 'Services Requisition Sheet'

    description = fields.Char(string='Descrption')
    required_date = fields.Date(string='Required Date')
    allocated_budget_ro = fields.Char(string='Allocated Budget (R.O)')
    remarks = fields.Char(string='Remarks')
    customer_complaint_id = fields.Many2one(
        string='Customer Complaint',
        comodel_name='customer.complaints',
    )


class ProductComplaints(models.Model):
    _name = 'product.complaints'
    _description = "Product Complaint Details"

    def onchange_product(self, product_id):
        """onchange for the product name"""
        result = {}
        if product_id:
            product = self.env['product.product'].browse(product_id)
            result['decryption'] = product.name
        return {'value': result}

    @api.depends('estimated_cost', 'qty', 'discount', 'actual_qty', 'actual_unit_price')
    def _compute_price(self):
        if not self.complaint_id.state == 'approve':
            self.actual_qty = self.qty
            self.actual_unit_price = self.estimated_cost
        self.subtotal = (self.estimated_cost - self.discount) * self.qty
        self.actual_subtotal = self.actual_unit_price * self.actual_qty

    name = fields.Many2one(comodel_name='product.product', string='Product')
    estimated_cost = fields.Float(string='Estimated Unit Cost', required=True, digits='Property')
    decryption = fields.Char(string='Description', required=True)
    qty = fields.Float(string='Estimated Quantity', required=True, default=1.00)
    discount = fields.Float(string='Discount On Unit Price', digits="Property")
    subtotal = fields.Float(compute='_compute_price', string='Subtotal', store=True, digits='Property')
    complaint_id = fields.Many2one(comodel_name='customer.complaints', string='Complaints')
    type = fields.Selection([('mr', _('MR')), ('in_house', _('In House')),
                             ('petty_cash', _('Petty Cash')),
                             ('petty_cash_imprest', _('Petty Cash Imprest'))
                             ], string='Type', default='mr')
    # to get the actual cost , it's better to do it update this table rather than adding a new model.
    estimate = fields.Boolean(string='Estimate', default=False)
    actual_qty = fields.Float(string='Actual Quantity')
    actual_unit_price = fields.Float(string='Actual Unit Price', digits='Property')
    actual_subtotal = fields.Float(compute='_compute_price', string='Sub total', store=True, digits='Property')
    company_id = fields.Many2one(comodel_name='res.company', related='complaint_id.company_id',
                                 string='Company', store=True, readonly=True)

    def write(self, vals):
        """
        :param vals:
        :return:
        """
        res = super(ProductComplaints, self).write(vals)
        for record in self:
            if "estimated_cost" in vals or 'qty' in vals:
                if record.complaint_id and not record.complaint_id.state == 'approve':
                    record.actual_qty = record.qty
                    record.actual_unit_price = record.estimated_cost
                record.subtotal = (record.estimated_cost - record.discount) * record.qty
                record.actual_subtotal = record.actual_unit_price * record.actual_qty
        return res


class ComplaintDetails(models.Model):
    _name = 'complaint.details'
    _description = "Complaint Details"

    name = fields.Text(string='Complaint')
    asset = fields.Many2one(comodel_name='assets.accessrz', string='Asset')
    comments = fields.Text(string='Comments')
    responsible = fields.Selection([('company', _('Al Thabat')), ('land', _('Land Lord')), ('tenant', _('Tenant'))],
                                   string='Maintenance Liability', default='tenant')
    complaint_id = fields.Many2one(comodel_name='customer.complaints', string='Complaints')
    property = fields.Many2one(comodel_name='property.property', string='Unit', related="complaint_id.property")
    priority = fields.Selection([('high', 'Major'), ('low', 'Minor')],
                                string='Priority', default='high')
    date_approved = fields.Date(string='Date Completed')
    state = fields.Selection([('draft0', 'Draft'), ('draft', 'Draft'), ('open', 'Open'), ('done', 'Done')],
                             default='draft0', string='State', copy=False, readonly=1)
    parent_state = fields.Selection(string='state', related='complaint_id.state', store=True, readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', related='complaint_id.company_id',
                                 string='Company', store=True, readonly=True)

    def unlink(self):
        for record in self:
            if record.state not in ['draft', 'draft0']:
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(ComplaintDetails, self).unlink()

    def set_to_done(self):
        """
        close the whole the master if all complaints are closed.
        :return:
        """
        if self.date_approved:
            self.state = 'done'
            done = True
            for complaint in self.complaint_id.complaint_details:
                if complaint.state == 'open':
                    done = False
            if done:
                self.complaint_id.state = 'done'
        else:
            raise UserError(_('Date Completed is required'))


class ComplaintPettyCash(models.AbstractModel):
    _name = 'report.property_management.tenant_maintenance_petty_report'
    _description = "Complaint Petty Cash"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['customer.complaints'].browse(docids)
        maintenance_lines = {}
        petty_cash_lines = docs.product_ids.filtered(lambda line: line.type == 'petty_cash')
        petty_cash_imprest = docs.product_ids.filtered(
            lambda line: line.type == 'petty_cash_imprest')
        if petty_cash_lines:
            maintenance_lines.update({'petty_cash': petty_cash_lines})
        if petty_cash_imprest:
            maintenance_lines.update({'petty_cash_imprest': petty_cash_imprest})

        return {
            'doc_ids': docids,
            'doc_model': 'customer.complaints',
            'docs': docs,
            'maintenance_lines': maintenance_lines,
        }
