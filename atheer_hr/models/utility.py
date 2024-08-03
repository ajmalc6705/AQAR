from odoo import models, fields, api, _
from lxml import etree
import json
from odoo.exceptions import UserError


class UtilityAccounts(models.Model):
    _name = 'utility.accounts'
    _description = "Utility Bills"
    _rec_name = 'acc_no'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    bill_type = fields.Selection(
        [('water', 'Water'), ('electricity', 'Electricity'), ('wifi', 'Internet'), ('mobile_bill', 'GSM'),
         ('pasi', 'PASI'), ('land_line', 'LandLine')],
        string="Bill Type", required=True)
    acc_no = fields.Char(string="Account Number", required=True)
    acc_user = fields.Char(string="Account User", required=True)
    account_id = fields.Many2one('account.account', string='Account')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.constrains('acc_no')
    def constrain_acc_no(self):
        utility_rec = self.search_count([('acc_no', '=', self.acc_no), ('bill_type', '=', self.bill_type)])
        if utility_rec > 1:
            raise UserError(_('You cannot have the same account number %s for the same bill type %s.') % (
                self.acc_no, dict(self._fields['bill_type'].selection).get(self.bill_type, False)))

    def unlink(self):
        for record in self:
            utility_approval_rec = self.env['utility.bill.details'].search([('acc_no', '=', record.acc_no)])
            if utility_approval_rec:
                raise UserError(
                    _('You cannot delete this as the bill type %s is being used by utility approval.',
                      dict(self._fields['bill_type'].selection).get(self.bill_type, False))
                )
            return super(UtilityAccounts, self).unlink()


class UtilityApproval(models.Model):
    _name = 'utility.approval'
    _description = "Utility Approval"
    _rec_name = 'reference'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "reference desc"

    def _default_currency_id(self):
        return self.env.user.company_id.currency_id

    reference = fields.Char(string="Reference", tracking=True, readonly=True)
    bill_month = fields.Selection(
        [('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
         ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'), ('9', 'September'),
         ('10', 'October'), ('11', 'November'), ('12', 'December')],
        default=lambda self: str(fields.datetime.now().month), string="Bill Month", required=True)
    bill_year = fields.Char(string="Bill Year", default=lambda self: str(fields.Date.today().year))
    bill_type = fields.Selection(
        [('water', 'Water'), ('electricity', 'Electricity'), ('wifi', 'Internet'), ('mobile_bill', 'GSM'),
         ('pasi', 'PASI'), ('land_line', 'LandLine')],
        string="Bill Type", required=True)
    acc_no = fields.Char(string="Account No.")
    acc_user = fields.Char(string="Account User")

    state = fields.Selection(
        [('hr', 'HR'), ('approved', 'Approved'), ('bill_paid', 'Bill Paid'),
         ('refused', 'Refused')], string='Status', tracking=True, required=True, default='hr')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    hr_remarks = fields.Char(string="HR Remarks", readonly=False)
    account_remarks = fields.Char(string="Account Remarks", readonly=False)
    water_bill_ids = fields.One2many(comodel_name='utility.bill.details', inverse_name='water_utility_approval_id',
                                     string="Water Bill Details")
    electricity_bill_ids = fields.One2many(comodel_name='utility.bill.details',
                                           inverse_name='electricity_utility_approval_id',
                                           string="Electricity Bill Details")
    other_bill_ids = fields.One2many(comodel_name='utility.bill.details', inverse_name='other_utility_approval_id',
                                     string="Other Bill Details")
    total_amount = fields.Float(string="Total Amount", readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self._default_currency_id())
    created_user = fields.Many2one(comodel_name='res.users', default=lambda self: self.env.user)
    approval_person_id = fields.Many2one('res.users', string="Approved By",
                                         readonly=True)
    approval_date = fields.Datetime(string="Approval Date", readonly=True)
    rejected_person_id = fields.Many2one('res.users', string="Refused By")
    rejected_date = fields.Datetime(string="Refused Date")
    # access flags
    send_back_flag = fields.Boolean(default=False)
    left_hr_flag = fields.Boolean(default=False)
    partner_id = fields.Many2one('res.partner', string='Supplier')
    journal_id = fields.Many2one('account.journal', string='Journal',domain=[('type','=','purchase')])
    bill_date = fields.Date(string='Bill Date')
    create_bill_flag = fields.Boolean(default=False)
    bill_id = fields.Many2one('account.move', string='Bill')

    def action_view_bill(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Bills',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.bill_id.id,
        }

    def action_create_bill(self):
        """ function for create bill"""
        line_ids = False
        if self.bill_type == 'water':
            line_ids = self.water_bill_ids
        elif self.bill_type == 'electricity':
            line_ids = self.electricity_bill_ids
        elif self.bill_type in ['wifi', 'mobile_bill','land_line','pasi']:
            line_ids = self.other_bill_ids
        tax_ids = []
        if line_ids:
            move = self.env['account.move'].create({
                'partner_id': self.partner_id.id,
                'move_type': 'in_invoice',
                'invoice_date': self.bill_date,
                'journal_id': self.journal_id.id,
                'invoice_line_ids': [
                    (0, 0, {
                        'quantity': 1,
                        'price_unit': val.untaxed_amount,
                        'account_id': val.account_id.id,
                        'tax_ids': [(6, 0, val.tax_id.ids)]
                    }) for val in line_ids
                ]
            })
            move.action_post()
            self.create_bill_flag = True
            self.bill_id = move.id

    @api.model
    def create(self, vals):
        vals['reference'] = self.env['ir.sequence'].next_by_code('utility.approval') or 'New'
        result = super(UtilityApproval, self).create(vals)
        return result

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(UtilityApproval, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                           submenu=False)
        form_view_id = self.env.ref('atheer_hr.view_utility_approval_form').id

        if res.get('view_id', False) == form_view_id and res.get('type', False) == 'form':
            doc = etree.XML(res['arch'])
            if len(doc):
                if not self.env.user.has_group('atheer_hr.group_hr_manager'):
                    node = doc.xpath("//field[@name='hr_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('atheer_hr.group_hr_accounts'):
                    node = doc.xpath("//field[@name='account_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)

                return res
        return res

    @api.onchange('water_bill_ids', 'electricity_bill_ids', 'other_bill_ids')
    def _calculate_total_amount(self):
        total_amt = 0
        if self.bill_type == 'water':
            for rec in self.water_bill_ids:
                total_amt += rec.net_payable_amount
        if self.bill_type == 'electricity':
            for rec in self.electricity_bill_ids:
                total_amt += rec.net_payable_amount
        if self.bill_type in ['wifi', 'mobile_bill','pasi','land_line']:
            for rec in self.other_bill_ids:
                total_amt += rec.net_payable_amount
        self.total_amount = total_amt

    def action_bill_paid(self):
        for rec in self:
            rec.state = 'bill_paid'

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'
            rec.approval_person_id = self.env.user.id
            rec.approval_date = fields.Datetime.now()
            if rec.water_bill_ids:
                for each in rec.water_bill_ids:
                    each.state = 'approved'
            if rec.electricity_bill_ids:
                for each in rec.electricity_bill_ids:
                    each.state = 'approved'
            if rec.other_bill_ids:
                for each in rec.other_bill_ids:
                    each.state = 'approved'
            approver = str(self.env.user.name)
            group_ids = self.env.ref('atheer_hr.group_hr_manager').ids
            acc_group_id = self.env.ref('atheer_hr.group_hr_accounts').id
            group_ids.append(acc_group_id)

    def action_reject(self):
        for rec in self:
            rec.state = 'refused'
            rec.rejected_person_id = self.env.user.id
            rec.rejected_date = fields.Datetime.now()
            if rec.water_bill_ids:
                for each in rec.water_bill_ids:
                    each.state = 'refused'
            if rec.electricity_bill_ids:
                for each in rec.electricity_bill_ids:
                    each.state = 'refused'
            if rec.other_bill_ids:
                for each in rec.other_bill_ids:
                    each.state = 'refused'
            refuser = str(self.env.user.name)
            group_ids = self.env.ref('atheer_hr.group_hr_manager').ids

    def send_back(self):

        for rec in self:
            rec.state = 'hr'
            rec.send_back_flag = True
            group_ids = self.env.ref('atheer_hr.group_hr_manager').ids

    @api.onchange('bill_type', 'bill_month', 'bill_year')
    def onchange_bill_type(self):
        wifi_utility_obj = self.env['utility.accounts'].search([('bill_type', '=', 'wifi')])
        pasi_utility_obj = self.env['utility.accounts'].search([('bill_type', '=', 'pasi')])
        land_line_utility_obj = self.env['utility.accounts'].search([('bill_type', '=', 'land_line')])
        mobile_bill_utility_obj = self.env['utility.accounts'].search([('bill_type', '=', 'mobile_bill')])
        water_utility_obj = self.env['utility.accounts'].search([('bill_type', '=', 'water')])
        electricity_utility_obj = self.env['utility.accounts'].search([('bill_type', '=', 'electricity')])
        for rec in self:
            water_line_ids = []
            electricity_line_ids = []
            other_line_ids = []
            # fetching paci
            if rec.bill_type == 'pasi':
                rec.other_bill_ids = [(5, 0, 0)]
                for each in pasi_utility_obj:
                    # fetching pasi details obj for same month in order to avoid duplication of records
                    same_month_wifi_utility_details_pasi = self.env['utility.bill.details'].search(
                        [('bill_type', '=', 'pasi'), ('acc_no', '=', each.acc_no), ('bill_month', '=', rec.bill_month),
                         ('bill_year', '=', rec.bill_year), ('state', 'in', ['approved', 'bill_paid'])], limit=1)
                    if each.acc_no != same_month_wifi_utility_details_pasi.acc_no:
                        vals = {
                            'acc_no': each.acc_no,
                            'account_id': each.account_id,
                            'acc_user': each.acc_user,
                            'bill_month': rec.bill_month,
                            'bill_type': rec.bill_type,
                        }
                        other_line_ids.append((0, 0, vals))
                self.other_bill_ids = other_line_ids
            # fetching landline
            if rec.bill_type == 'land_line':
                rec.other_bill_ids = [(5, 0, 0)]
                for each in land_line_utility_obj:
                    # fetching wifi details obj for same month in order to avoid duplication of records
                    same_month_land_line_utility_details = self.env['utility.bill.details'].search(
                        [('bill_type', '=', 'land_line'), ('acc_no', '=', each.acc_no), ('bill_month', '=', rec.bill_month),
                         ('bill_year', '=', rec.bill_year), ('state', 'in', ['approved', 'bill_paid'])], limit=1)
                    if each.acc_no != same_month_land_line_utility_details.acc_no:
                        vals = {
                            'acc_no': each.acc_no,
                            'account_id': each.account_id,
                            'acc_user': each.acc_user,
                            'bill_month': rec.bill_month,
                            'bill_type': rec.bill_type,
                        }
                        other_line_ids.append((0, 0, vals))
                self.other_bill_ids = other_line_ids
            # fetching wifi details if the bill type is wifi
            if rec.bill_type == 'wifi':
                rec.other_bill_ids = [(5, 0, 0)]
                for each in wifi_utility_obj:
                    # fetching wifi details obj for same month in order to avoid duplication of records
                    same_month_wifi_utility_details = self.env['utility.bill.details'].search(
                        [('bill_type', '=', 'wifi'), ('acc_no', '=', each.acc_no), ('bill_month', '=', rec.bill_month),
                         ('bill_year', '=', rec.bill_year), ('state', 'in', ['approved', 'bill_paid'])], limit=1)
                    if each.acc_no != same_month_wifi_utility_details.acc_no:
                        vals = {
                            'acc_no': each.acc_no,
                            'account_id': each.account_id,
                            'acc_user': each.acc_user,
                            'bill_month': rec.bill_month,
                            'bill_type': rec.bill_type,
                        }
                        other_line_ids.append((0, 0, vals))
                self.other_bill_ids = other_line_ids
            # fetching wifi details if the bill type is mobile_bill
            if rec.bill_type == 'mobile_bill':
                rec.other_bill_ids = [(5, 0, 0)]
                for each in mobile_bill_utility_obj:
                    # fetching mobile details obj for same month in order to avoid duplication of records
                    same_month_mobile_utility_details = self.env['utility.bill.details'].search(
                        [('bill_type', '=', 'mobile_bill'), ('acc_no', '=', each.acc_no),
                         ('bill_month', '=', rec.bill_month),
                         ('bill_year', '=', rec.bill_year), ('state', 'in', ['approved', 'bill_paid'])], limit=1)
                    if each.acc_no != same_month_mobile_utility_details.acc_no:
                        vals = {
                            'acc_no': each.acc_no,
                            'account_id': each.account_id,
                            'acc_user': each.acc_user,
                            'bill_month': rec.bill_month,
                            'bill_year': rec.bill_year,
                            'bill_type': rec.bill_type,
                        }
                        other_line_ids.append((0, 0, vals))
                self.other_bill_ids = other_line_ids
            bill_year = rec.bill_year
            if rec.bill_month == '1':
                bill_year = int(bill_year) - 1
            else:
                bill_year = rec.bill_year
            if rec.bill_month == '1':
                bill_month = '12'
            else:
                bill_month = int(rec.bill_month) - 1
            # fetching water details if the bill type is water
            if rec.bill_type in ['water']:
                rec.water_bill_ids = [(5, 0, 0)]
                for each in water_utility_obj:
                    # fetching water details obj for last month in order to get last reading for the current month
                    utility_last_reading_details = self.env['utility.bill.details'].search(
                        [('bill_type', '=', 'water'), ('acc_no', '=', each.acc_no), ('bill_month', '=', bill_month),
                         ('bill_year', '=', str(bill_year)), ('state', 'in', ['approved', 'bill_paid'])], limit=1)
                    last_reading = ''
                    if utility_last_reading_details:
                        last_reading = utility_last_reading_details.current_reading
                    # fetching water details obj for same month in order to avoid duplication of records
                    same_month_utility_details = self.env['utility.bill.details'].search(
                        [('bill_type', '=', 'water'), ('acc_no', '=', each.acc_no), ('bill_month', '=', rec.bill_month),
                         ('bill_year', '=', rec.bill_year), ('state', 'in', ['approved', 'bill_paid'])], limit=1)
                    if each.acc_no != same_month_utility_details.acc_no:
                        vals = {
                            'acc_no': each.acc_no,
                            'account_id': each.account_id,
                            'acc_user': each.acc_user,
                            'bill_month': rec.bill_month,
                            'bill_year': rec.bill_year,
                            'bill_type': rec.bill_type,
                            'last_reading': last_reading
                        }
                        water_line_ids.append((0, 0, vals))
                self.water_bill_ids = water_line_ids
            # fetching electricity details if the bill type is electricity
            if rec.bill_type in ['electricity']:
                rec.electricity_bill_ids = [(5, 0, 0)]
                for each in electricity_utility_obj:
                    # fetching electricity details obj for last month in order to get last reading for the current month
                    ele_utility_last_reading_details = self.env['utility.bill.details'].search(
                        [('bill_type', '=', 'electricity'), ('acc_no', '=', each.acc_no),
                         ('bill_month', '=', bill_month),
                         ('bill_year', '=', str(bill_year)), ('state', 'in', ['approved', 'bill_paid'])], limit=1)
                    last_reading = ''
                    if ele_utility_last_reading_details:
                        last_reading = ele_utility_last_reading_details.current_reading
                    # fetching electricity details obj for same month in order to avoid duplication of records
                    same_month_ele_utility_details = self.env['utility.bill.details'].search(
                        [('bill_type', '=', 'electricity'), ('acc_no', '=', each.acc_no),
                         ('bill_month', '=', rec.bill_month),
                         ('bill_year', '=', rec.bill_year), ('state', 'in', ['approved', 'bill_paid'])], limit=1)
                    if each.acc_no != same_month_ele_utility_details.acc_no:
                        vals = {
                            'acc_no': each.acc_no,
                            'account_id': each.account_id,
                            'acc_user': each.acc_user,
                            'bill_month': rec.bill_month,
                            'bill_year': rec.bill_year,
                            'bill_type': rec.bill_type,
                            'last_reading': last_reading
                        }
                        electricity_line_ids.append((0, 0, vals))
                self.electricity_bill_ids = electricity_line_ids

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref('atheer_hr.action_report_utility_approval').report_action(self)

    def unlink(self):
        for record in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if record.state != 'hr':
                    raise UserError(
                        _('You cannot delete the utility approval %s in the current state.', record.reference)
                    )
            return super(UtilityApproval, self).unlink()


class UtilityBillDetails(models.Model):
    _name = 'utility.bill.details'
    _description = "Utility Approval"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'acc_user'

    def _default_currency_id(self):
        return self.env.user.company_id.currency_id

    water_utility_approval_id = fields.Many2one(comodel_name='utility.approval', ondelete="cascade")
    electricity_utility_approval_id = fields.Many2one(comodel_name='utility.approval', ondelete="cascade")
    other_utility_approval_id = fields.Many2one(comodel_name='utility.approval', ondelete="cascade")
    bill_month = fields.Selection(
        [('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
         ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'), ('9', 'September'),
         ('10', 'October'), ('11', 'November'), ('12', 'December')], string="Bill Month")
    bill_year = fields.Char(string="Bill Year", default=lambda self: str(fields.Date.today().year))

    bill_type = fields.Selection(
        [('water', 'Water'), ('electricity', 'Electricity'), ('wifi', 'Internet'), ('mobile_bill', 'GSM'),
         ('pasi', 'PASI'), ('land_line', 'LandLine')],
        string="Bill Type")
    acc_no = fields.Char(string="Account No")
    acc_user = fields.Char(string="Account User")
    account_id = fields.Many2one('account.account', string='Account')
    last_reading = fields.Float(string="Last Reading")
    current_reading = fields.Float(string="Current Reading")
    consumed_unit = fields.Float(string="Consumed Unit", readonly=True)
    tariff = fields.Float(string="Tariff")
    consumed_unit_amount = fields.Float(string="Consumed Unit Amount", readonly=True)
    municipality_fees = fields.Float(string="Municipality Fees")
    municipality_amount = fields.Float(string="Municipality Amount", readonly=True)
    total_amount = fields.Float(string="Total Amount", readonly=True)
    tax_id = fields.Many2one(comodel_name='account.tax', string="Vat",domain=[('type_tax_use', '=', 'purchase')])
    vat_amount = fields.Float(string="Vat Amount", readonly=True)
    sewage_unit_rate = fields.Float(string="Sewage Unit Rate")
    sewage_amount = fields.Float(string="Sewage Amount", readonly=True)
    vat_amount_for_sewage = fields.Float(string="Vat Amount For Sewage Unit", readonly=True)
    sewage_service_fee = fields.Float(string="Sewage Service Fee")
    sewage_service_tax = fields.Many2one(comodel_name='account.tax', string="Sewage Service Tax")
    sewage_service_tax_amount = fields.Float(string="Sewage Service Tax Amount", readonly=True)
    untaxed_amount = fields.Float(string="Untaxed Amount", readonly=False)
    net_payable_amount = fields.Float(string="Net Payable Amount", readonly=False)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self._default_currency_id())
    state = fields.Selection(
        [('hr', 'HR'), ('approved', 'Approved'), ('bill_paid', 'Bill Paid'),
         ('refused', 'Refused')], string='Status')

    @api.onchange('current_reading', 'last_reading', 'tariff', 'municipality_fees', 'tax_id', 'sewage_unit_rate',
                  'sewage_service_fee', 'sewage_service_tax', 'net_payable_amount')
    def calculate_consumed_unit(self):
        bill_type = ''
        if self.water_utility_approval_id:
            bill_type = 'water'
        elif self.electricity_utility_approval_id:
            bill_type = 'electricity'
        for rec in self:
            if bill_type in ['water', 'electricity']:
                rec.consumed_unit = rec.current_reading - rec.last_reading
                rec.consumed_unit_amount = rec.consumed_unit * rec.tariff
                if bill_type == 'water':
                    rec.total_amount = rec.consumed_unit_amount
                    rec.vat_amount = rec.total_amount * rec.tax_id.amount / 100
                    rec.sewage_amount = rec.consumed_unit * rec.sewage_unit_rate
                    rec.vat_amount_for_sewage = rec.sewage_amount * rec.tax_id.amount / 100
                    rec.sewage_service_tax_amount = rec.sewage_service_fee * rec.sewage_service_tax.amount / 100
                    rec.untaxed_amount = rec.total_amount +  rec.sewage_amount +  rec.sewage_service_fee
                    rec.net_payable_amount = rec.total_amount + rec.vat_amount + rec.sewage_amount + rec.vat_amount_for_sewage + \
                                             rec.sewage_service_tax_amount + rec.sewage_service_fee
                if bill_type == 'electricity':
                    rec.municipality_amount = rec.municipality_fees * rec.consumed_unit_amount / 100
                    rec.total_amount = rec.consumed_unit_amount + rec.municipality_amount
                    rec.vat_amount = rec.total_amount * rec.tax_id.amount / 100
                    rec.untaxed_amount = rec.total_amount
                    rec.net_payable_amount = rec.total_amount + rec.vat_amount
            if rec.bill_type in ['wifi','pasi','land_line','mobile_bill']:
                rec.vat_amount = rec.untaxed_amount * rec.tax_id.amount / 100
                rec.net_payable_amount = rec.untaxed_amount + rec.vat_amount

    def _valid_field_parameter(self, field, name):
        return name == 'ondelete' or super()._valid_field_parameter(field, name)

    def unlink(self):
        for record in self:
            if record.state in ['hr', 'approved', 'bill_paid', 'refused']:
                raise UserError(
                    _('You cannot delete the utility bill details as it is being used by utility approval.')
                )
            return super(UtilityBillDetails, self).unlink()
