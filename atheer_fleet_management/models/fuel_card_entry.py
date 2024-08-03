from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class FuelCardEntry(models.Model):
    _name = 'fuel.card.entry'
    _description = 'Fuel Card Entry'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']

    name = fields.Char(string="Name", readonly=True, copy=False, required=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Supplier', required=True, tracking=True)
    date_from = fields.Date(string='Period From', required=True,
                            help='Start Date')
    date_to = fields.Date(string='Period To', required=True,
                          help='Ending Date, included in the fiscal year.')
    bill_date = fields.Date(string='Bill Date', tracking=True, default=fields.Date.today())
    bill_reference = fields.Char(string='Bill Reference', copy=False)
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', )
    service_charge = fields.Float(string='Service Charges', tracking=True, digits=(12, 3), copy=False)
    service_tax_ids = fields.Many2many('account.tax', string='Service VAT',
                                       domain=[('type_tax_use', '=', 'purchase')], )
    analytic_distribution = fields.Json("Analytic Distribution", store=True, copy=False)

    total_service_amount = fields.Float(string='Total Service Amount', store=True,
                                        compute="compute_total_service_amount", tracking=True,
                                        digits=(12, 3,), copy=False)

    total_amount_tax = fields.Float(string='Total VAT', store=True, compute="_amount_all", tracking=True,
                                    digits=(12, 3,), copy=False)
    total_consumed_amount = fields.Float(string='Total Consumption Amount', store=True, tracking=True, digits=(12, 3),
                                         compute="_amount_all")
    total_amount = fields.Float(string='Total Amount', store=True, tracking=True, digits=(12, 3),
                                compute="_amount_all")
    total_bill_amount = fields.Float(string='Total Bill Amount', store=True, tracking=True, digits=(12, 3),
                                     compute="_amount_total")
    remarks = fields.Text(string='Remarks')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'), ('invoice', 'Invoiced')], string='State',
                             default='draft', tracking=True)

    consumption_ids = fields.One2many('fuel.consumption', 'fuel_entry_id', 'Consumption Details')
    journal_id = fields.Many2one('account.journal', string='Journal', copy=False, )

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean('Active', default=True, tracking=True, copy=False, )
    is_fuel_consumption_lines_added = fields.Boolean('Consumption Lines Added', default=False, tracking=True,
                                                     copy=False, )

    def confirm(self):
        for record in self:
            if record.service_charge > 0:
                if not record.analytic_distribution:
                    raise UserError(_("Please Select Analytic Account under Service Details ", ))
            for line in record.consumption_ids:
                if not line.analytic_distribution:
                    raise UserError(_(
                        "The consumption Line have no analytic account Please Add analytic account for (%s)",
                        line.fuel_card.name
                    ))
            record.write({'state': 'done'})

    def reset_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise UserError(_('You cannot delete a fuel card entry that is in %s state.') % (rec.state,))
        return super(FuelCardEntry, self).unlink()

    def action_generate_consumption_lines(self):
        for record in self:
            item_dict = []
            fuel_card_obj = self.env['master.fuel.card'].search(
                [('company_id', '=', self.company_id.id), ('active', '=', True)])
            if fuel_card_obj:
                record.is_fuel_consumption_lines_added = True
                for line in fuel_card_obj:
                    vals = (0, 0, {
                        'fuel_card': line.id,
                        'company_id': record.company_id.id,
                    })
                    item_dict.append(vals)
                record.write({'consumption_ids': item_dict})
            else:
                record.is_fuel_consumption_lines_added = False
                raise UserError("No fuel card records found, please check again")

    @api.depends('consumption_ids', )
    def _amount_all(self):
        """
        Compute the total amounts for the Consumption Lines .
        """
        self.total_amount_tax = self.total_amount = self.total_consumed_amount = 0
        for rec in self:
            rec.total_amount_tax = sum(rec.consumption_ids.mapped('amount_vat'))
            rec.total_amount = sum(rec.consumption_ids.mapped('tax_amount'))
            rec.total_consumed_amount = sum(rec.consumption_ids.mapped('amount'))

    @api.depends('service_tax_ids', 'service_charge')
    def compute_total_service_amount(self):
        """
        Compute the total Bill amount amounts  .
        """
        self.total_service_amount = 0
        for rec in self:
            service_amount = rec.service_charge
            taxes = rec.service_tax_ids.compute_all(service_amount, rec.currency_id)
            amount_tax = taxes['total_included'] - taxes['total_excluded']
            rec.update({
                # 'amount_vat': amount_tax,
                'total_service_amount': service_amount + amount_tax,
            })

    @api.depends('total_consumed_amount', 'total_service_amount')
    def _amount_total(self):
        """
        Compute the total Bill amount amounts  .
        """
        self.total_bill_amount = 0
        for rec in self:
            rec.total_bill_amount = rec.total_consumed_amount + rec.total_service_amount

    def button_view_move(self):
        domain = "[('fuel_card_id', '=', " + str(self.id) + ")]"
        return {'name': _("Fuel Bills"),
                'view_mode': 'tree,form',
                'view_type': 'tree',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'domain': domain,
                'context': {'default_fuel_card_id': self.id, }
                }
        return action

    def create_invoice(self):
        fuel_card_details = self.env['account.move'].search([('fuel_card_id', '=', self.id)], limit=1)
        if not self.journal_id:
            raise UserError(_("Please Select Journal", ))
        if not fuel_card_details:
            move_lines = []
            for line in self.consumption_ids:
                print(line)
                name = _(" Fuel Entry %s  for the fuel Card %s of vehicle %s", self.name, line.fuel_card.name,
                         line.vehicle.name)

                move_lines.append((0, 0,
                                   {
                                       'name': name,
                                       'tax_ids': [(6, 0, line.tax_ids.ids)],
                                       'analytic_distribution': line.analytic_distribution,
                                       # 'analytic_distribution': {
                                       #     line.analytic_account_id.id: 100},
                                       'price_unit': line.tax_amount,
                                   }))

                # print("NAME**********************", Ajmal)
            if self.service_charge > 0:
                name = _(" Service Charges For the fuel entry %s  ", self.name, )
                move_lines.append((0, 0,
                                   {
                                       'name': name,
                                       'price_unit': self.service_charge,
                                       'tax_ids': [(6, 0, self.service_tax_ids.ids)],
                                       'analytic_distribution': self.analytic_distribution,
                                       #     self.service_analytic_account_id.id: 100},
                                       # 'analytic_distribution': {
                                       #     self.service_analytic_account_id.id: 100},

                                   }))
            new_move = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.partner_id.id,
                'invoice_date': self.bill_date,
                'ref': self.bill_reference,
                'date': self.bill_date,
                # 'date': fields.Date.today(),
                # 'invoice_date': fields.Date.today(),
                'journal_id': self.journal_id.id,
                'fuel_card_id': self.id,
                'invoice_line_ids': move_lines
            })
        else:
            new_move = fuel_card_details

        self.write({'state': 'invoice'})

        action = {
            'name': _("Bills"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': new_move.id,  # Use 'res_id' instead of 'view_id' to specify the record to open
            'context': {'create': False},
        }
        return action

        # return new_move
        # action = {
        #     'name': _("Vendor Bill"),
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'account.move',
        #     'context': {
        #                 'default_invoice_date': fields.Date.today(),
        #                 'default_amount': self.total_bill_amount,
        #                 'bill_reference': self.bill_reference,
        #                 'default_partner_type': 'vendor',
        #                 'default_currency_id': self.currency_id.id,
        #                 'default_date': fields.Date.today()},
        #                 'default_invoice_line_ids': fields.Date.today()},
        #     'view_mode': 'form',
        #     'domain': [],
        # }

        # for record in self:
        #     record.state = 'draft'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fuel.card.entry') or 'New'
        return super(FuelCardEntry, self).create(vals_list)


class FuelConsumption(models.Model):
    _name = 'fuel.consumption'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']
    _description = 'Fuel Card Consumption'

    fuel_card = fields.Many2one('master.fuel.card', 'Fuel Card', check_company=True, )
    vehicle = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True,
                              related="fuel_card.vehicle_id",
                              )
    fuel_card_limit = fields.Float(string='Limit/Month', tracking=True, store=True,
                                   related="fuel_card.petrol_limit_per_month",
                                   digits=(12, 3))
    fuel_entry_id = fields.Many2one('fuel.card.entry', string='Fuel Entry')
    date = fields.Date(string='Date', tracking=True)

    tax_amount = fields.Float(string='Consumed amount', tracking=True, digits=(12, 3))
    amount = fields.Float(string='Amount with VAT', compute="_compute_amount", tracking=True, digits=(12, 3))
    amount_vat = fields.Float(string='VAT Amount', compute="_compute_amount", tracking=True, digits=(12, 3))
    odometer_reading = fields.Float(string='Odometer', tracking=True)
    fuel_consumption = fields.Float(string='Consumption', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    analytic_distribution = fields.Json("Analytic Distribution", store=True, copy=False)
    # analytic_account_id = fields.Many2one(comodel_name='account.analytic.account', string="Analytic Account",
    #                                       copy=False,  # Unrequired company
    #                                       )
    tax_ids = fields.Many2many('account.tax', 'consumption_line_tax_rel', 'fuel_consumption_id', 'tax_id',
                               string='VAT', domain=[('type_tax_use', '=', 'purchase')],
                               default=lambda
                                   self: self.env.companies.account_purchase_tax_id or self.env.companies.root_id.account_purchase_tax_id)
    currency_id = fields.Many2one(string="Company Currency", related='fuel_entry_id.currency_id', )
    state = fields.Selection(related='fuel_entry_id.state', string="Order Status",
                             copy=False, store=True, precompute=True)

    @api.depends('tax_ids', 'tax_amount')
    def _compute_amount(self):
        """ To compute Total amount and Tax amount in consumption lines"""
        for rec in self:
            amount = rec.tax_amount
            taxes = rec.tax_ids.compute_all(amount, rec.currency_id, )

            amount_tax = taxes['total_included'] - taxes['total_excluded']
            rec.update({
                'amount_vat': amount_tax,
                'amount': amount + amount_tax,
            })


class AccountMoveFuel(models.Model):
    _inherit = 'account.move'

    fuel_card_id = fields.Many2one('fuel.card.entry', string='Fuel Card Id')
