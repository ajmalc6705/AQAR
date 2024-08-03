# # -*- coding: utf-8 -*-

from odoo import models, fields, _, api


class AccountAsset(models.Model):
    _inherit = "account.asset"
    _rec_name = 'asset_code'

    asset_code = fields.Char("Asset Code", default="New", required=True, readonly=True)
    yearly_percentage = fields.Float('Yearly Percentage', default=0)
    location_id = fields.Many2one('stock.location', string="Location")
    supplier_id = fields.Many2one('res.partner', string="Supplier")
    asset_active_date = fields.Date(string="Asset Active Date")
    warranty_expiry_date = fields.Date(string="Warranty Expiry Date")
    asset_quantity = fields.Float("Asset Quantity")
    monthly_depreciation = fields.Float(string="Monthly Depreciation", compute="compute_depreciation", help="Calculate monthly percentage in amount as per yearly percentage")
    depreciated_amount = fields.Float(string="Depreciated Amount", compute="compute_depreciation")
    remaining_amount = fields.Float(string="Remaining Amount", compute="compute_depreciation")
    duration_months = fields.Float(string="Duration in Months", compute="compute_depreciation", help="Auto calculating the number of months as per yearly percentage")
    tax_based_amount = fields.Float('Tax Based Amount')
    tax_based_months = fields.Float('Tax Based Months')
    tax_based_method = fields.Selection([('linear', 'Straight Line'), ('degressive', 'Declining')],
                                        default="linear", string='Tax Based Method', required=True)
    monthly_amount = fields.Float('Monthly Amount', compute="compute_monthly_amount")
    old_location_id = fields.Many2one('stock.location', string="Old Location")

    @api.onchange('original_value', 'method', 'method_number', 'method_period')
    def onchange_original_value(self):
        self.tax_based_amount = self.original_value
        self.tax_based_method = self.method if self.method == 'linear' else 'degressive'
        self.tax_based_months = self.method_number * int(self.method_period)
        if self.tax_based_method == 'linear':
            self.monthly_amount = self.original_value / self.tax_based_months if self.tax_based_months else 0
        else:
            self.monthly_amount = 0

    @api.onchange('tax_based_amount', 'tax_based_months', 'tax_based_method')
    def compute_monthly_amount(self):
        if self.tax_based_method == 'linear':
            self.monthly_amount = self.tax_based_amount / self.tax_based_months if self.tax_based_months else 0
        else:
            self.monthly_amount = 0

    def write(self, vals):
        if vals.get('location_id'):
            vals['old_location_id'] = self.location_id.id
        res = super(AccountAsset, self).write(vals)
        return res

    # @api.onchange('location_id')
    # def onchange_location_id(self):
    #     self.old_location_id = self.location_id
    @api.onchange('location_id')
    def asset_location_change(self):
        print("===", self)
        self.env['asset.location.change'].create({'asset_id': self._origin.id,
                                                  'old_location_id': self.old_location_id.id,
                                                  'new_location_id': self.location_id.id,
                                                  })

    @api.depends('original_value', 'model_id')
    @api.onchange('original_value', 'model_id')
    def compute_depreciation(self):
        monthly_depreciation = self.original_value * self.model_id.yearly_percentage
        self.monthly_depreciation = monthly_depreciation
        one_year_dep = monthly_depreciation / 12 if monthly_depreciation else 0
        self.duration_months = (self.original_value / one_year_dep) if one_year_dep else 0
        self.depreciated_amount = sum(self.depreciation_move_ids.filtered(lambda x:x.state == 'posted').mapped('depreciation_value'))
        self.remaining_amount = sum(self.depreciation_move_ids.filtered(lambda x:x.state == 'draft').mapped('depreciation_value'))

    @api.model
    def create(self, vals):
        vals['asset_code'] = self.env['ir.sequence'].next_by_code('account.asset') or _('New')
        res = super(AccountAsset, self).create(vals)
        return res


class AssetLocationChange(models.Model):
    _name = "asset.location.change"
    _rec_name = 'asset_id'
    _description = 'Asset Location change'

    asset_id = fields.Many2one('account.asset', string="Asset")
    old_location_id = fields.Many2one('stock.location', string="Old Value")
    new_location_id = fields.Many2one('stock.location', string="New Value")