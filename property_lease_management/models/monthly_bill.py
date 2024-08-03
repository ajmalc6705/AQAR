# -*- coding: utf-8 -*-

import json
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree
import json

PAYMENT_STATE_SELECTION = [
    ('not_paid', 'Not Paid'),
    ('in_payment', 'In Payment'),
    ('paid', 'Paid'),
    ('partial', 'Partially Paid'),
    ('reversed', 'Reversed'),
    ('invoicing_legacy', 'Invoicing App Legacy'),
]


class BillType(models.Model):
    _name = 'bill.type'
    _rec_name = 'name'
    _description = 'Bill Type'

    name = fields.Char(string="Name", required=True)


class MonthlyBill(models.Model):
    _name = 'monthly.bill'
    # _rec_name = 'building_id'
    _description = 'Monthly Bill'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('monthly.bill') or _('New')
        return super().create(vals_list)

    def unlink(self):
        for record in self:
            if record.monthly_bill_approval_id:
                raise UserError('You cannot delete an item linked to a Monthly Bill Approval entry. ')

        return super(MonthlyBill, self).unlink()

    name = fields.Char(string='Ref No', copy=False, readonly=True,
                       index=True, default=lambda self: _('New'))
    building_id = fields.Many2one('property.building', 'Building', store=True, required=True)
    property_id = fields.Many2one(comodel_name='property.property', string='Unit', store=True, copy=False,
                                  tracking=True)
    effective_date = fields.Date(string="Bill Date", required=True)
    bill_type = fields.Many2one(comodel_name='bill.type', string="Bill Type", required=True)
    electricity_account = fields.Char('Building Electricity Account', related="building_id.electricity_account")
    electricity_account_id = fields.Many2one('electricity.account.line', string='Electricity Accounts',
                                            )
    water_account = fields.Char('Building Water Account', related="building_id.water_account")
    water_account_id = fields.Many2one('water.account.line', string='Water Accounts',)
    previous_reading = fields.Float('Previous Reading', digits='Property')
    previous_reading_date = fields.Date(string='Previous Reading Date')
    current_reading = fields.Float('Current Reading', digits='Property')
    reading_type_id = fields.Many2one('reading.type', string='Reading Type')
    current_reading_date = fields.Date(string='Current Reading Date')
    consumed_reading = fields.Float('Consumed Reading', digits='Property')
    kwh = fields.Float('Consumed KWH', digits='Property')
    sewage_rate = fields.Float('Sewage Rate', digits='Property', tracking=True, copy=False)
    unit_rate = fields.Float('Unit Rate', digits='Property', tracking=True, copy=False)
    unit_amount = fields.Float('Unit Amount', digits="Product Price", copy=False)
    other_charges = fields.Float('Other Charges', digits="Product Price", tracking=True, copy=False)
    tax_amount = fields.Float('Tax Amount', digits='Property', copy=False)
    total_amount = fields.Float('Total Amount', digits="Product Price", tracking=True, copy=False)

    monthly_bill_approval_id = fields.Many2one('monthly.bill.approval', 'Approvals', copy=False)
    approval_state = fields.Selection(related="monthly_bill_approval_id.state",
                                      string='Monthly bill Approval State', copy=False,
                                      )
    is_bill_paid = fields.Boolean('Bill is Paid', compute="_compute_is_bill_paid")
    tax_id = fields.Many2one('account.tax', string='Tax', tracking=True)
    wifi_amount = fields.Float('Amount', digits='Property', copy=False)
    is_electricity = fields.Boolean('IS electricity', compute="compute_is_electricity")
    trip_count = fields.Integer('Trip Count', default=1, copy=False)
    is_trip_shown = fields.Boolean('Is Trip Shown', compute="_compute_is_trip_shown")
    company_id = fields.Many2one('res.company', string="Company", help='company', default=lambda self: self.env.company)

    @api.onchange('property_id')
    def _onchange_property(self):
        rent_ids = self.env['property.property'].browse(self.property_id.id)
        return {'domain': {
            'electricity_account_ids': [('id', 'in', rent_ids.electricity_account_ids.mapped('id'))],
            'water_account_ids': [('id', 'in', rent_ids.water_account_ids.mapped('id'))],
        }}

    @api.depends('monthly_bill_approval_id')
    def _compute_is_bill_paid(self):
        for record in self:
            if record.monthly_bill_approval_id.payment_state == 'paid':
                record.is_bill_paid = True
            else:
                record.is_bill_paid = False

    @api.depends('bill_type')
    def _compute_is_trip_shown(self):
        for record in self:
            if record.bill_type.name == 'Sewage removal':
                record.is_trip_shown = True
            else:
                record.is_trip_shown = False

    @api.onchange('bill_type')
    def compute_is_electricity(self):
        """ find eletricity or not """
        for rec in self:
            if rec.bill_type.name in ['Water', 'Electricity']:
                rec.is_electricity = True
            else:
                rec.is_electricity = False

    # @api.onchange('building_id', 'bill_type')
    # def onchange_building_bill_type(self):
    #     """ function to find the previous reading """
    #     for rec in self:
    #         if rec.building_id and rec.bill_type:
    #             bills = self.env['monthly.bill'].sudo().search([('building_id', '=', rec.building_id.id),
    #                                                             ('bill_type', '=', rec.bill_type.id)],
    #                                                            order='effective_date desc')
    #             if bills:
    #                 rec.previous_reading = bills[0].current_reading
    #             else:
    #                 rec.previous_reading = 0

    @api.onchange('unit_rate', 'consumed_reading', 'tax_id', 'bill_type', 'wifi_amount', 'sewage_rate', 'trip_count',
                  'other_charges')
    def onchange_unit_rate(self):
        for rec in self:
            if rec.bill_type.name in ['Water', 'Electricity']:
                rec.is_electricity = True
                if rec.unit_rate or rec.consumed_reading or rec.other_charges or rec.sewage_rate or rec.tax_id:
                    rec.unit_amount = rec.unit_rate * rec.consumed_reading
                    total_untaxed_amount = rec.unit_amount + rec.sewage_rate + rec.other_charges
                    tax_res = rec.tax_id._origin.compute_all(total_untaxed_amount)
                    res = sum(tax['amount'] for tax in tax_res['taxes'])
                    rec.tax_amount = res
                    sewage_rate = 0
                    if rec.bill_type.name == 'Water':
                        sewage_rate = rec.sewage_rate

                    rec.total_amount = rec.tax_amount + rec.unit_amount + sewage_rate + rec.other_charges

            else:
                rec.is_electricity = False
                trip_count = 1
                if rec.bill_type.name == 'Sewage removal':
                    if rec.trip_count >= 1:
                        trip_count = rec.trip_count
                    else:
                        raise UserError(_('Trip count must be greater than 1'))
                total_amount = rec.wifi_amount * trip_count
                tax_res = rec.tax_id._origin.compute_all(total_amount)
                tax_amount = sum(tax['amount'] for tax in tax_res['taxes'])
                rec.total_amount = rec.wifi_amount * trip_count + tax_amount
                rec.unit_amount = rec.wifi_amount
                rec.tax_amount = tax_amount
            # if rec.bill_type.name in ['Water', 'Electricity'] and rec.current_reading and rec.previous_reading:
            #     if rec.current_reading < rec.previous_reading:
            #         raise UserError("Current reading must be grater than previous reading ")

    # @api.onchange('current_reading')
    # def onchange_current_reading(self):
    #     for rec in self:
    #         if rec.current_reading:
    #             rec.consumed_reading = rec.current_reading - rec.previous_reading

    def view_monthly_bill(self):
        for rec in self:
            monthly_bills = self.env['monthly.bill'].search([('id', '=', rec.id)]).id
            return {
                'type': 'ir.actions.act_window',
                'name': ('Maintenance'),
                'view_mode': 'tree,form',
                'res_model': 'monthly.bill',
                'target': 'current',
                'context': {'create': False},
                'domain': [('id', '=', monthly_bills)],
            }


class MonthlyBillApproval(models.Model):
    _name = 'monthly.bill.approval'
    # _rec_name = 'bill_type'
    _description = 'Monthly Bill Approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('monthly.bill.approval') or _('New')
        return super().create(vals_list)

    name = fields.Char(string='Ref No', copy=False, readonly=True,
                       index=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', 'Vendor', copy=False, tracking=True)
    from_date = fields.Date('From Date', required=True, copy=False, )
    to_date = fields.Date('To Date', required=True, copy=False, )
    building_select = fields.Selection([('all', 'All Buildings'), ('choose', 'Choose Building')], 'Building',
                                       required=True)
    building_ids = fields.Many2many('property.building', string='Choose Buildings', store=True)
    bill_type = fields.Many2one(comodel_name='bill.type', string="Bill Type", required=True, copy=False, )
    remarks = fields.Text('Remarks')
    property_remarks = fields.Text('Property Remarks')
    total_unit_amount = fields.Float('Total UnTaxed Amount', digits='Property')
    total_tax_amount = fields.Float(' Total Tax Amount', digits='Property')
    total_total_amount = fields.Float('Total Taxed Amount', digits='Property')
    approved_by = fields.Many2one('res.users', 'Approved By')
    approved_date = fields.Date(string='Approved Date')
    state = fields.Selection([('draft', _('Draft')),
                              ('property_head', _('Property head')),
                              ('accountant', _('Accountant')),
                              ('paid', _('Paid')),
                              ('reject', _('Rejected'))], string='State', copy=False, default='draft')
    monthly_bill_ids = fields.Many2many('monthly.bill', 'rel_monthly_bill_approval_id', 'monthly_bill_id',
                                        "monthly_bill_approval_id", 'Monthly Bills', )
    # monthly_bill_id = fields.Many2one('monthly.bill')
    is_electricity = fields.Boolean('IS electricity', compute="compute_is_electricity", copy=False, )
    send_back_flag = fields.Boolean(default=False)
    company_id = fields.Many2one('res.company', string="Company", help='company', default=lambda self: self.env.company)
    move_id = fields.Many2one('account.move', string='Bill Entry', )
    bill_count = fields.Integer('Bill Count', compute="_compute_bill_count")
    payment_state = fields.Selection(selection=PAYMENT_STATE_SELECTION, string="Payment Status",
                                     compute='_compute_payment_state', store=True, readonly=True,
                                     copy=False,
                                     tracking=True,
                                     )
    invoice_state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancel'), ],
                                     string="Invoice Status",
                                     compute='_compute_invoice_state', store=True, readonly=True,
                                     copy=False,
                                     tracking=True,
                                     )

    @api.depends('move_id.payment_state')
    def _compute_payment_state(self):
        for record in self:
            if record.move_id:
                record.payment_state = record.move_id.payment_state
            else:
                record.payment_state = False

    @api.depends('move_id.state')
    def _compute_invoice_state(self):
        for record in self:
            if record.move_id:
                record.invoice_state = record.move_id.state
            else:
                record.invoice_state = False

    def onchange_payment_state(self):
        """ Onchange state account into paid while the invoice is paid """
        for rec in self:
            if rec.payment_state == 'paid':
                rec.send_to_paid()
            else:
                rec.write({'state': 'accountant'})

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(MonthlyBillApproval, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                               submenu=False)
        form_view_id = self.env.ref('property_lease_management.view_client_information_form').id
        if res.get('view_id', False) == form_view_id and res.get('type', False) == 'form':
            doc = etree.XML(res['arch'])
            if doc:
                if (not self.env.user.has_group('property_lease_management.group_property_user') or
                        not self.env.user.has_group('property_lease_management.group_property_head')):
                    node = doc.xpath("//field[@name='property_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('property_lease_management.group_property_accountant'):
                    node = doc.xpath("//field[@name='remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                return res
        return res

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
            record.monthly_bill_ids.write({'monthly_bill_approval_id': False})
        return super(MonthlyBillApproval, self).unlink()

    @api.onchange('bill_type')
    def compute_is_electricity(self):
        """ find electricity or not """
        for rec in self:
            if rec.bill_type.name in ['Water', 'Electricity']:
                rec.is_electricity = True
            else:
                rec.is_electricity = False

    def send_to_property_head(self):
        """ sending for approval """
        if not self.monthly_bill_ids:
            raise ValidationError(_("There is no Bills please Add Monthly Bills' "))
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'monthly.bill.approval')]).id
        # Remove Old Activities related to the current record
        self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id),
        ]).unlink()
        for bill in self.monthly_bill_ids:
            if not bill.monthly_bill_approval_id:
                bill.monthly_bill_approval_id = self.id
            else:
                raise ValidationError(
                    _("The Bill '%s' All ready Linked with '%s' Please Verify Again", bill.name,
                      bill.monthly_bill_approval_id.name))

        self.write({'state': 'property_head'})
        # self.state = "property_head"
        self.send_back_flag = False
        # notification_obj = self.env['atheer.notification']
        # notification_obj._send_instant_notify(title="Monthly Bills Approval",
        #                                       message='Pending approval for Monthly Bill of ' + str(self.bill_type),
        #                                       action=self.env.ref(
        #                                           'property_lease_management.action_monthly_bill_approval').id,
        #                                       domain=[['id', '=', self.id]],
        #                                       user_type="groups",
        #                                       recipient_ids=[self.env.ref(
        #                                           'property_lease_management.group_property_head').id])

    def send_to_accountant(self):
        """ sending for approval """
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'monthly.bill.approval')]).id
        # Remove Old Activities related to the current record
        self.env['mail.activity'].search([
            ('res_id', '=', self.id),
            ('res_model_id', '=', res_model_id),
        ]).unlink()
        self.write({'state': 'accountant'})
        # self.state = "accountant"
        self.send_back_flag = False

        # notification_obj = self.env['atheer.notification']
        # notification_obj._send_instant_notify(title="Monthly Bills Approval",
        #                                       message='Pending approval for Monthly Bill of ' + str(self.bill_type),
        #                                       action=self.env.ref(
        #                                           'property_lease_management.action_monthly_bill_approval').id,
        #                                       domain=[['id', '=', self.id]],
        #                                       user_type="groups",
        #                                       recipient_ids=[self.env.ref(
        #                                           'property_lease_management.group_property_accountant').id])

    def send_to_paid(self):
        """ approving the Monthly bill """
        self.write({'state': 'paid'})
        self.approved_by = self.env.user.id
        self.approved_date = fields.date.today()

    def send_back(self):
        """ Send back to previous state """
        for rec in self:
            state_map = {
                'accountant': 'property_head',
                'property_head': 'draft',
            }
            new_state = state_map.get(rec.state)
            res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'monthly.bill.approval')]).id
            # Remove Old Activities related to the current record
            self.env['mail.activity'].search([
                ('res_id', '=', self.id),
                ('res_model_id', '=', res_model_id),
            ]).unlink()
            if new_state:
                rec.state = new_state
            rec.send_back_flag = True
            if rec.state == 'draft':
                for bill in rec.monthly_bill_ids:
                    if bill.monthly_bill_approval_id:
                        bill.monthly_bill_approval_id = False

    def reject_bills(self):
        """ To reject Bill and  """
        for rec in self:
            if not rec.move_id or rec.move_id.state == 'draft':
                rec.move_id.button_cancel()
            else:
                raise ValidationError(_("The Bill '%s' is all redy posted, Please Check Again ") % rec.move_id.name)

            rec.write({"state": "reject"})
            rec.send_back_flag = False
            for bill in rec.monthly_bill_ids:
                if bill.monthly_bill_approval_id:
                    bill.monthly_bill_approval_id = False

    @api.onchange('building_select', 'building_ids', 'bill_type', 'from_date', 'to_date')
    def get_bills(self):
        """ function to get the bill in a period """
        for rec in self:
            if rec.bill_type.name in ['Water', 'Electricity']:
                rec.is_electricity = True
            else:
                rec.is_electricity = False
            if rec.from_date and rec.to_date and rec.building_select and rec.bill_type:
                total_sevage_amount = total_unit_amount = tax_amount = total_taxed_amount = 0
                if rec.building_select == 'all':
                    building_ids = self.env['property.building'].search([]).ids
                else:
                    building_ids = rec.building_ids.ids
                monthly_bills = self.env['monthly.bill'].search([('effective_date', '>=', rec.from_date),
                                                                 ('effective_date', '<=', rec.to_date),
                                                                 ('building_id', 'in', building_ids),
                                                                 ('bill_type', '=', rec.bill_type.id),
                                                                 ('company_id', '=', rec.company_id.id),
                                                                 ('monthly_bill_approval_id', '=', False)
                                                                 ])

                for bill in monthly_bills:
                    total_unit_amount += bill.unit_amount + bill.sewage_rate + bill.other_charges
                    tax_amount += bill.tax_amount
                    if bill.bill_type.name == 'Water':
                        total_sevage_amount += bill.sewage_rate

                rec.total_tax_amount = tax_amount
                rec.total_unit_amount = total_unit_amount

                # total_taxed_amount += total_unit_amount + tax_amount
                rec.total_total_amount = rec.total_unit_amount + rec.total_tax_amount
                rec.monthly_bill_ids = [(5, 0, 0)]
                rec.monthly_bill_ids = [(6, 0, monthly_bills.ids)]

    def button_action_create_bill(self):
        for rec in self:
            # Restrict to create Bill while all ready bill is created
            if rec.move_id:
                raise ValidationError(_("All ready a Bill Created Please check bill ref is '%s' ") % rec.move_id.name)

            if not rec.monthly_bill_ids:
                raise ValidationError(_("There is no Bills please Add Bills' "))
            move = self.env['account.move'].create({
                'partner_id': self.partner_id.id,
                'move_type': 'in_invoice',
                'monthly_approval_bill_id': self.id,
                'ref': rec.name,
                'invoice_line_ids': [
                    (0, 0, {
                        'name': 'Monthly Bills : ' + str(vals.building_id.name) + '-' + str(
                            vals.property_id.name) + '-' + str(vals.bill_type.name),
                        'quantity': 1,
                        'price_unit': vals.unit_amount + vals.sewage_rate + vals.other_charges,
                        'tax_ids': [(6, 0, vals.tax_id.ids)]
                    }) for vals in rec.monthly_bill_ids
                ]
            })
            self.move_id = move.id
            return {
                'type': 'ir.actions.act_window',
                'name': 'Vendor Bill',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': move.id,
                'target': 'current',
            }

    def button_action_view_bill(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bill',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('monthly_approval_bill_id', '=', self.id)],
        }

    def _compute_bill_count(self):
        """Compute the count of Bills related to thisMonthly bill approval."""
        for rec in self:
            bill_obj = self.env['account.move'].search([('monthly_approval_bill_id', '=', self.id)])
            # print(bill_obj)
            rec.bill_count = len(bill_obj)


class ReadingType(models.Model):
    _name = 'reading.type'
    _description = 'Reading Type'
    name = fields.Char(string='Name')


class AccountMoveInheritMonthlyBillApproval(models.Model):
    _inherit = 'account.move'

    monthly_approval_bill_id = fields.Many2one('monthly.bill.approval', string='Monthly Approval Bill')
