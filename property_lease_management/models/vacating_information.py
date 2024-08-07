# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError


class DeductionType(models.Model):
    _name = 'deduction.type'
    _rec_name = 'name'
    _description = 'Deduction Type'

    name = fields.Char(string="Name", required=True)
    is_default_type = fields.Boolean('Deduction Type', default=False,
                                     help="This field will be true only if the evaluation.type if given by the client ie: value added throug data.xml")


class Deduction(models.Model):
    _name = 'deduction.line'
    _rec_name = 'deduction_type_id'
    _description = 'Deduction Line'

    tenant_deposit_release_id = fields.Many2one(comodel_name='tenant.deposit.release')

    ro = fields.Float(string='RO', digits='Property')
    remark = fields.Char(string='Remark', )
    deduction_type_id = fields.Many2one('deduction.type', required=True)


class VacatingInformation(models.Model):
    _name = 'tenant.deposit.release'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reference'
    _check_company_auto = True
    _description = "Vacating Information"

    partner_id = fields.Many2one(comodel_name='res.partner', string='Tenant', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]}, tracking=True,
                                 domain="[('tenant','=',True), ('parent_id', '=', False)]")
    rent_id = fields.Many2one(comodel_name='property.rent', string='Rent', required=True, readonly=True,
                              states={'draft': [('readonly', False)]}, tracking=True)
    building_id = fields.Many2one(comodel_name='property.building', string="Building", store=True, tracking=True,
                                  readonly=True,
                                  states={'draft': [('readonly', False)]}, related='rent_id.building')
    property_id = fields.Many2one(comodel_name='property.property', string='Unit', required=True, readonly=True,
                                  related='rent_id.property_id',
                                  states={'draft': [('readonly', False)]}, tracking=True)

    from_date = fields.Date(string='Lease Start', related="rent_id.from_date", readonly=True, tracking=True)
    to_date = fields.Date(string='Lease End', related="rent_id.to_date", readonly=True, tracking=True)

    reference = fields.Char(string="Reference", tracking=True, readonly=True)

    description = fields.Text(string='Description', tracking=True)

    security_deposit = fields.Float(string='Security Deposit', readonly=True, digits='Property',
                                    related='rent_id.security_deposit', tracking=True)
    amount = fields.Float(string='Amount', digits='Property', tracking=True, readonly=True,
                          states={'draft': [('readonly', False)]}, )
    balance_amount = fields.Float(string='Balance Amount', digits='Property',  store=True, readonly=True,
                                  compute='_compute_amount')

    state = fields.Selection([('draft', 'Draft'),
                              ('property_account', _('Property Accountant')),
                              ('property_head', _('Property Head')),
                              ('approved', _('Approved')),
                              ('rejected', _('Rejected'))], string='Status', default='draft',
                             readonly=True, copy=False, help=_("Gives the status of the Vacating Information"))

    deduction_line_ids = fields.One2many(comodel_name='deduction.line', inverse_name='tenant_deposit_release_id',
                                         readonly=True, states={'draft': [('readonly', False)]},
                                         string='Deduction', tracking=True)
    send_back_flag = fields.Boolean(default=False)
    journal_id = fields.Many2one('account.journal', string='Journal')
    account_id = fields.Many2one('account.account', string='Debit Account', )
    credit_account_id = fields.Many2one('account.account', string='Credit Account', )
    move_id = fields.Many2one('account.move', string='Move Entry')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)

    @api.onchange('rent_id')
    def onchange_rent_id(self):
        for rec in self:
            if rec.rent_id:
                rec.partner_id = rec.rent_id.partner_id.id
                rec.journal_id = rec.rent_id.journal_id.id
                rec.account_id = rec.rent_id.account_id.id
                rec.amount = rec.rent_id.rent_total

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('At this state, it is not possible to delete this record. ')
            return super(VacatingInformation, self).unlink()

    def button_send_to_accountat(self):
        for rec in self:
            rec.state = 'property_account'
            rec.send_back_flag = False
            # notification_obj = self.env['atheer.notification']
            # notification_obj._send_instant_notify(title="Vacating Request",
            #                                       message='Pending approval for vacating request of ' + str(
            #                                           rec.partner_id.name),
            #                                       action=self.env.ref(
            #                                           'property_lease_management.action_tenant_deposit_release').id,
            #                                       domain=[['id', '=', rec.id]],
            #                                       user_type="groups",
            #                                       recipient_ids=[self.env.ref(
            #                                           'property_lease_management.group_property_accountant').id])

    def button_send_to_property_head(self):
        for rec in self:
            rec.state = 'property_head'
            rec.send_back_flag = False
            # notification_obj = self.env['atheer.notification']
            # notification_obj._send_instant_notify(title="Vacating Request",
            #                                       message='Pending approval for vacating request of ' + str(
            #                                           rec.partner_id.name),
            #                                       action=self.env.ref(
            #                                           'property_lease_management.action_tenant_deposit_release').id,
            #                                       domain=[['id', '=', rec.id]],
            #                                       user_type="groups",
            #                                       recipient_ids=[self.env.ref(
            #                                           'property_lease_management.group_property_head').id])

    def button_approve(self):
        for rec in self:
            rec.action_entry()
            rec.state = 'approved'
            rec.send_back_flag = False

    def action_entry(self):
        """ create entry when transaction is done"""
        for rec in self:
            journal_id = rec.journal_id and rec.journal_id.id or False
            if not journal_id:
                raise UserError('Please update the journal details.')
            credit_account_id = rec.credit_account_id and rec.credit_account_id.id or False
            if not credit_account_id:
                raise UserError('Please update the credit account.')
            invoice_lines = []
            for deduction_line in rec.deduction_line_ids:
                if deduction_line.ro > 0:
                    invoice_vals = {
                        'name': deduction_line.deduction_type_id and deduction_line.deduction_type_id.name or '',
                        'account_id': credit_account_id or False,
                        'date': self.from_date,
                        'price_unit': deduction_line.ro,
                        'price_subtotal': deduction_line.ro,
                        'quantity': 1,
                        'tax_ids': [],
                        'display_type': 'product'
                    }
                    invoice_lines.append((0, 0, invoice_vals))
            if invoice_lines:
                vals = {
                    'invoice_date': self.from_date,
                    'move_type': 'out_invoice',
                    'partner_id': rec.partner_id and rec.partner_id.id or False,
                    'invoice_origin': self.reference,
                    'invoice_payment_term_id': rec.partner_id.property_payment_term_id and rec.partner_id.property_payment_term_id.id,
                    'vacating_info_id': self.id,
                    'journal_id': journal_id,
                    'rent_id': rec.rent_id and rec.rent_id.id or False,
                    'invoice_line_ids': invoice_lines
                }
                move = self.env['account.move'].create(vals)
                move.action_post()
                rec.move_id = move.id

    def get_vacating_entry(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Accounting Entry',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', '=', self.move_id.id)]
        }

    def button_send_to_rejected(self):
        for rec in self:
            rec.state = 'rejected'
            rec.send_back_flag = False

    def button_send_back(self):
        for rec in self:
            state_map = {
                'property_head': 'property_account',
                'property_account': 'draft',
            }
            new_state = state_map.get(rec.state)
            if new_state:
                rec.state = new_state
            rec.send_back_flag = True

    @api.depends('security_deposit', 'amount')
    def _compute_amount(self):
        for rec in self:
            if rec.security_deposit and rec.amount:
                rec.balance_amount = rec.security_deposit - rec.amount
            else:
                # self.balance_amount = 0
                rec.balance_amount = rec.security_deposit - rec.amount

    @api.model
    def default_get(self, fields_list):
        res = super(VacatingInformation, self).default_get(fields_list)
        deduction_type_ids = self.env['deduction.type'].search([('is_default_type', '=', True)])
        vals = []
        for type in deduction_type_ids:
            dafault_type = (0, 0, {'deduction_type_id': type.id})
            vals.append(dafault_type)
        res.update({'deduction_line_ids': vals})
        return res

    @api.onchange('deduction_line_ids')
    def onchange_deduction_line_ids(self):
        amount = 0
        for deduction_line_id in self.deduction_line_ids:
            amount = amount + deduction_line_id.ro
        self.amount = amount

    @api.model
    def create(self, vals):
        vals['reference'] = self.env['ir.sequence'].next_by_code('atr.vacating.information.sequence') or 'New'
        result = super(VacatingInformation, self).create(vals)
        return result


class AccountMove(models.Model):
    _inherit = 'account.move'

    vacating_info_id = fields.Many2one('tenant.deposit.release', string='Vacating Info')
