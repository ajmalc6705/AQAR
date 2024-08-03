# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import RedirectWarning, UserError


class CheckList(models.Model):
    _name = 'property.checklist'
    _rec_name = 'name'
    _description = "Property Checklists"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('partner_id')
    def get_company(self):
        if self.partner_id.is_company:
            self.company = True

    name = fields.Char(string='Name')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Tenant', required=True)
    building = fields.Many2one(comodel_name='property.building', string='Building', required=True)
    property_id = fields.Many2one(comodel_name='property.property', string='Unit', required=True)
    company = fields.Boolean(string='Is Company')
    check_1 = fields.Boolean(string='PRE-TENANCY APPLICATION FORM (FOR DEPARTMENT APPROVAL)')
    check_2 = fields.Boolean(string='TENANT DETAILS FORM (FILLED, SIGNED & STAMPED)')
    check_3 = fields.Boolean(string='PASSPORT & ID / RESIDENT CARD COPY (IF IN PERSONAL NAME)')
    check_4 = fields.Boolean(string='COMPANY REGISTRATION & SIGNATORY COPY (COMMERCIAL TENANTS))')
    check_5 = fields.Boolean(string='SECURITY DEPOSIT AMOUNT (PAID)')
    check_6 = fields.Boolean(string='PDC CHEQUES FOR RENTAL PAYMENT (PAID)')
    check_7 = fields.Boolean(string='KEY HANDING OVER FORM (SIGNED)')
    check_8 = fields.Boolean(string='ASSETS ACKNOWLEDGEMENT FORM (SIGNED)')
    check_9 = fields.Boolean(string='MUNICIPALITY AGREEMENT (SIGNED & PREPARED)')
    # 'check_10' : fields.Boolean('AL THAbAT AGREEMENT (SIGNED & HANDED OVER)')
    check_11 = fields.Boolean(string='MAINTENANCE REQUEST FORM (HANDED OVER)')
    rent_id = fields.Many2one(comodel_name='property.rent', string='Rent')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)
    hand_over_checklist = fields.One2many('checklist.handover.assets', 'hand_over_checklist_id',
                                          string='Handover PunchList')
    inspection_date = fields.Date('Inspection Date')
    checked = fields.Boolean('Checked')
    state = fields.Selection([('draft', 'Care Taker'), ('waiting', 'Waiting for Approval'), ('confirm', 'Confirmed')],
                             string='Status', default='draft')
    remarks = fields.Text(string='Remarks')
    elec_meter_reading = fields.Float(string='Electricity Meter Reading')
    elec_acc_no = fields.Char(string='Electricity Acc. No.', related='property_id.electricity_no')
    elec_meter_no = fields.Char(string='Electricity Meter No.', related='property_id.electricity_meter_no')
    water_meter_reading = fields.Float(string='Water Meter Reading')
    water_acc_no = fields.Char(string='Water Acc. No.', related='property_id.water_account_no')
    water_meter_no = fields.Char(string='Water Meter No.', related='property_id.water_meter_no')
    signature = fields.Binary(string='Signature', copy=False, attachment=True)
    electricity_account_ids = fields.One2many('electricity.account.line', 'handover_checklist_id',
                                              string='Electricity Accounts')
    water_account_ids = fields.One2many('water.account.line', 'handover_checklist_id', string='Water Accounts')

    @api.onchange("property_id")
    def onchange_property_id(self):
        for rec in self:
            if rec.property_id.electricity_account_ids:
                rec.electricity_account_ids = rec.property_id.electricity_account_ids
            if rec.property_id.water_account_ids:
                rec.electricity_account_ids = rec.property_id.water_account_ids

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(CheckList, self).unlink()

    def select_all_working(self):
        for rec in self:
            for line in rec.hand_over_checklist:
                line.write({
                    'yes_working': True,
                    'not_working': False
                })

    def select_all_not_working(self):
        for rec in self:
            print(rec, "select_all_not_workingselect_all_not_working")
            for rec in self:
                for line in rec.hand_over_checklist:
                    line.write({
                        'not_working': True,
                        'yes_working': False,
                    })

    @api.model
    def create(self, vals):
        rent_id = self.env['property.rent'].browse(vals['rent_id'])
        vals['name'] = rent_id.name + '_Handover Checklist'
        res = super(CheckList, self).create(vals)
        partner_id = res.partner_id
        if partner_id.is_company:
            res.check_4 = True
        elif not partner_id.is_company and not partner_id.is_government:
            res.check_3 = True
        return res

    def confirm_check_list(self):
        """ confirming the handover checklist """
        for rec in self:
            rec.state = 'waiting'

    def approve_check_list(self):
        """ approving the handover checklist """
        for rec in self:
            print("sgggggggggg")
            rec.state = 'confirm'

    def send_back_check_list(self):
        """ send back the handover checklist """
        self.state = 'draft'


class ChecklistTakeover(models.Model):
    _name = 'property.checklist.takeover'
    _rec_name = 'name'
    _description = "Property Checklist Takeover"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.onchange('elec_water_paid', 'rent_paid', 'maintenance_paid', 'check_8')
    def check(self):
        if self.elec_water_paid and self.rent_paid and self.maintenance_paid and self.check_8:
            pass
        else:
            self.keys_received = False

    @api.onchange('keys_received')
    def key_received(self):
        if self.elec_water_paid and self.rent_paid and self.maintenance_paid and self.check_8:
            rent_id = self.env['property.rent'].browse(self.rent_id.id)
            return
        else:
            self.keys_received = False

    @api.onchange('inspection_report')
    def onchange_inspection_report(self):
        pass

    @api.depends('inspection_report')
    def _compute_total(self):
        for rec in self:
            total = sum(inspect_rec.amount for inspect_rec in rec.inspection_report)
            rec.amount_total = total

    name = fields.Char(string='Name')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Tenant', required=True)
    building = fields.Many2one(comodel_name='property.building', string='Building', required=True)
    property_id = fields.Many2one(comodel_name='property.property', string='Unit', required=True)
    # inspection_date = fields.Date(string='Maintenance Inspection Date')
    # maintenance_check = fields.One2many(comodel_name='checklist.takeover.maintenance',
    #                                     inverse_name='takeover_checklist', string='Maintenance Check')
    inspection_report = fields.One2many(comodel_name='checklist.takeover.inspection', inverse_name='takeover_checklist',
                                        string='Maintenance Inspection')
    inspection_report_date = fields.Date(string='Inspection Report Date')
    elec_meter_reading = fields.Float(string='Electricity Meter Reading')
    elec_acc_no = fields.Char(string='Electricity Acc. No.', related='property_id.electricity_no')
    elec_meter_no = fields.Char(string='Electricity Meter No.', related='property_id.electricity_meter_no')
    water_meter_reading = fields.Float(string='Water Meter Reading')
    water_acc_no = fields.Char(string='Water Acc. No.', related='property_id.water_account_no')
    water_meter_no = fields.Char(string='Water Meter No.', related='property_id.water_meter_no')
    rent_id = fields.Many2one(comodel_name='property.rent', string='Rent')
    keys_received = fields.Boolean(string='Keys Received')
    elec_water_paid = fields.Boolean(string='1. The electricity & Water outstanding as per the above readings settled.')
    rent_paid = fields.Boolean(string='2. Rental payments cleared till the date of occupancy')
    maintenance_paid = fields.Boolean(string='3. Maintenance charges, if any, cleared by the tenant')
    check_8 = fields.Boolean(string='ASSETS ACKNOWLEDGEMENT FORM (Verified)')
    amount_total = fields.Float(string='Total', compute=_compute_total, digits='Product Price')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)
    take_over_checklist = fields.One2many('checklist.takeover.assets', 'turn_over_checklist_id',
                                          string='Turn-Over PunchList')
    inspection_date = fields.Date('Inspection Date')
    checked = fields.Boolean('Checked')
    state = fields.Selection([('draft', 'Draft'), ('waiting', 'Waiting for Approval'), ('confirm', 'Confirmed')],
                             string='Status', default='draft')
    hand_over_checklist = fields.One2many('checklist.handover.assets', 'hand_take_over_checklist_id',
                                          string='Handover PunchList')
    remarks = fields.Text(string='Remarks')
    signature = fields.Binary(string='Signature', copy=False, attachment=True)

    expiry_date = fields.Date(string="Expiry Date", related='rent_id.to_date')
    agreement_no = fields.Char(string="Agreement No.", related='rent_id.name')
    municipality_agreement_no = fields.Char(string="Municipality Agreement No.",
                                            related='rent_id.muncipality_agreemnt_no')
    dispute_cheque_ids = fields.Many2many('dispute.cheque.bounce', string='Dispute Management',
                                          compute='_compute_domain_values')
    legal_action_ids = fields.Many2many('dispute.legal.action', string='Legal Action', compute='_compute_domain_values')
    resolved = fields.Boolean(string='Resolved', default=False)
    electricity_account_ids = fields.One2many('electricity.account.line', 'takeover_checklist_id',
                                              string='Electricity Accounts')
    water_account_ids = fields.One2many('water.account.line', 'takeover_checklist_id', string='Water Accounts')

    @api.onchange("property_id")
    def onchange_property_id(self):
        for rec in self:
            if rec.property_id.electricity_account_ids:
                rec.electricity_account_ids = rec.property_id.electricity_account_ids
            if rec.property_id.water_account_ids:
                rec.electricity_account_ids = rec.property_id.water_account_ids

    @api.depends('rent_id')
    def _compute_domain_values(self):
        self.dispute_cheque_ids = False
        self.legal_action_ids = False
        for rec in self:
            action = self.env['dispute.legal.action'].search([('rent_id', '=', self.rent_id.id)])
            rec.legal_action_ids = action.mapped('id')
            dispute = self.env['dispute.cheque.bounce'].search([('rent_id', '=', self.rent_id.id)])
            rec.dispute_cheque_ids = dispute.mapped('id')

    def select_all_working(self):
        for rec in self:
            for line in rec.take_over_checklist:
                line.write({
                    'not_working': False,
                    'yes_working': True,
                })

    def select_all_not_working(self):
        for rec in self:
            print(rec, "select_all_not_workingselect_all_not_working")
            for rec in self:
                for line in rec.take_over_checklist:
                    line.write({
                        'not_working': True,
                        'yes_working': False,
                    })

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("You can't delete the checklist. Kindly contact the admin"))
        return super(ChecklistTakeover, self).unlink()

    def confirm_check_list(self):
        """ confirming the handover checklist """
        self.state = 'waiting'

    def approve_check_list(self):
        """ approving the handover checklist """
        if not self.resolved:
            raise UserError(_('Checklist Cannot Confirmed Until Resolved is False'))
        self.state = 'confirm'

    def send_back_check_list(self):
        """ send back the handover checklist """
        self.state = 'draft'

    def create(self, vals):
        rent_id = self.env['property.rent'].browse(vals['rent_id'])
        vals['name'] = rent_id.name + '_Takeover Checklist'
        res = super(ChecklistTakeover, self).create(vals)
        items = [{'takeover_checklist': res, 'item': 'gen_clean'},
                 {'takeover_checklist': res, 'item': 'painting'},
                 {'takeover_checklist': res, 'item': 'door_window'},
                 {'takeover_checklist': res, 'item': 'furniture'},
                 {'takeover_checklist': res, 'item': 'ceiling'},
                 {'takeover_checklist': res, 'item': 'floor'},
                 {'takeover_checklist': res, 'item': 'kitchen_cab'},
                 {'takeover_checklist': res, 'item': 'plumbing'},
                 {'takeover_checklist': res, 'item': 'air_con'},
                 {'takeover_checklist': res, 'item': 'electrical'},
                 {'takeover_checklist': res, 'item': 'fire'},
                 {'takeover_checklist': res, 'item': 'kitchen_equip'},
                 {'takeover_checklist': res, 'item': 'others'},
                 ]
        return res

    def write(self, vals):
        res = super(ChecklistTakeover, self).write(vals)
        if 'keys_received' in vals:
            rent_id = self.env['property.rent'].browse(self.rent_id.id)
            if vals['keys_received']:
                rent_id.write({'key_received': True})
            if not vals['keys_received']:
                rent_id.write({'key_received': False})
        return res


class ChecklistTakeoverAssets(models.Model):
    _name = 'checklist.takeover.assets'
    _description = "Assets in Takeover Checklist"

    name = fields.Char('Session')
    sl_no = fields.Char('Sr. No.')
    quantity = fields.Integer('Quantity')
    description = fields.Char('Description')
    remarks = fields.Text('Remarks')
    yes_working = fields.Boolean('Working')
    not_working = fields.Boolean('Not Working')
    session_head = fields.Boolean('Session Head', default=False)
    turn_over_checklist_id = fields.Many2one('property.checklist.takeover')
    state = fields.Selection(related="turn_over_checklist_id.state")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    @api.onchange('yes_working')
    def onchange_working(self):
        """ onchange working and not working"""
        for rec in self:
            if rec.yes_working:
                rec.not_working = False

    @api.onchange('not_working')
    def onchange_not_working(self):
        """ onchange working and not working"""
        for rec in self:
            if rec.not_working:
                rec.yes_working = False


class ChecklistHandoverAssets(models.Model):
    _name = 'checklist.handover.assets'
    _description = "Assets in Handover Checklist"

    name = fields.Char('Session')
    sl_no = fields.Char('Sr. No.')
    quantity = fields.Integer('Quantity')
    description = fields.Char('Description')
    remarks = fields.Text('Remarks')
    yes_working = fields.Boolean('Working')
    not_working = fields.Boolean('Not Working')
    session_head = fields.Boolean('Session Head', default=False)
    hand_over_checklist_id = fields.Many2one('property.checklist')
    hand_take_over_checklist_id = fields.Many2one('property.checklist.takeover')
    state = fields.Selection(related="hand_over_checklist_id.state")

    @api.onchange('yes_working')
    def onchange_working(self):
        """ onchange working and not working"""
        for rec in self:
            if rec.yes_working:
                rec.not_working = False

    @api.onchange('not_working')
    def onchange_not_working(self):
        """ onchange working and not working"""
        for rec in self:
            if rec.not_working:
                rec.yes_working = False


class ChecklistTakeoverInspection(models.Model):
    _name = 'checklist.takeover.inspection'
    _description = "Checklist Takeover Inspection"

    @api.model
    def default_get(self, fields):
        vals = super(ChecklistTakeoverInspection, self).default_get(fields)
        context_keys = self.env.context.keys()
        next_sequence = 1
        if 'inspection_report' in context_keys:
            if len(self.env.context.get('inspection_report')) > 0:
                next_sequence = len(self.env.context.get('inspection_report')) + 1
        vals['sl_no'] = next_sequence
        return vals

    takeover_checklist = fields.Many2one(comodel_name='property.checklist.takeover', string='Takeover Checklist')
    state = fields.Selection(related="takeover_checklist.state")
    sl_no = fields.Integer(string='SL.No.')
    description = fields.Text(string='Description of Works')
    remarks = fields.Text(string='Remarks')
    amount = fields.Float(string='Amount', digits='Property')


class AgreementCancellation(models.Model):
    _name = 'agreement.cancellation'
    _rec_name = 'rent_id'
    _description = "Agreement Cancellation"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    rent_id = fields.Many2one(comodel_name='property.rent')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Tenant', required=True)
    building = fields.Many2one(comodel_name='property.building', string='Building', required=True)
    property_id = fields.Many2one(comodel_name='property.property', string='Unit', required=True)
    reason = fields.Selection([('cancel', 'Finish & Left'), ('termination', 'Premature Cancellation')],
                              string='Reason', default='cancel')
    remarks = fields.Text(string='Remarks')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Cancellation Confirmed'),
                              ('done', 'Done'), ], string='Status', readonly=True, copy=False, default='draft',
                             help=_("Gives the status of the cancellation"))
    date_vacate = fields.Date(string='Cancellation Date')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(AgreementCancellation, self).unlink()

    def button_confirm(self):
        """
        Cancel Rent Agreements from the cancellation Form. We skip the current period invoice from cancelling
        but instead we make that in draft state to do corrections from the property Accountant.
        :return:
        """
        if self.reason == 'termination':
            vacate_period = self.env['rent.period.lines'].search(
                [('rent_ids', '=', self.rent_id.id), ('from_date', '<=', self.date_vacate),
                 ('to_date', '>=', self.date_vacate)])
            if vacate_period:
                invoice = self.env['account.move'].search(
                    [('rent_id', '=', self.rent_id.id), ('rental_period_id', '=', vacate_period.id)])
                invoice.button_draft()
                cancel_period = self.env['rent.period.lines'].search(
                    [('rent_ids', '=', self.rent_id.id),
                     ('to_date', '>=', self.date_vacate), ('id', '!=', vacate_period.id)])
                for invoice in self.rent_id.invoice_ids:
                    if invoice.rental_period_id in cancel_period:  # skipping current period's invoice.
                        # account.move can only delete FM, so bypassing that validation using context
                        # and the same will be checking on the cancellation of JV
                        invoice.with_context(rent=True).button_cancel()
        self.rent_id.state = 'close'
        self.write({'state': 'confirm'})

    # def pay_deposit(self):
    #     dummy, view_id = self.env['ir.model.data'].get_object_reference('property_management',
    #                                                                     'view_property_receipt_dialog_form')
    #     rent_obj = self.env['property.rent'].browse(self.rent_id.id)
    #     return {
    #         'name': _("Pay Amount"),
    #         'view_mode': 'form',
    #         'view_id': view_id,
    #         'tag': 'reload',
    #         'target': 'new',
    #         'stay_open': True,
    #         'view_type': 'form',
    #         'res_model': 'property.voucher',
    #         'type': 'ir.actions.act_window',
    #         'nodestroy': True,
    #         'domain': '[]',
    #         'context': {
    #             'default_partner_id': self.partner_id.id,
    #             'default_agreement_id': self.rent_id.id,
    #             'default_type': 'receipt',
    #             'default_installment_type': 'installment',
    #             'default_building': self.building.id,
    #             'default_property_id': self.property_id.id,
    #             'default_account_id': self.partner_id.property_account_receivable_id.id,
    #         }
    #     }

    def make_maintenance(self):
        view_ref = self.env.ref('property_lease_management.view_customer_complaint_form')
        view_id = view_ref and view_ref.id or False,
        rent_obj = self.env['property.rent'].browse(self.rent_id.id)

        return {
            'name': _("Maintenance Job"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'tag': 'reload',
            'res_model': 'customer.complaints',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'stay_open': True,
            'domain': '[]',
            'context': {
                'default_date': fields.Date.today(),
                'default_partner_id': rent_obj.partner_id.id,
                'default_building': rent_obj.building.id,
                'default_property': rent_obj.property_id.id,
                'default_agreement_no': self.rent_id.id,
            }
        }

    def done(self):
        self.write({'state': 'done'})
        self.rent_id.property_id.state = 'open'
        self.rent_id.state = 'close'
