# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AssetLocation(models.Model):
    _name = 'account.asset.location'
    _description = 'Account Asset Location'
    _rec_name = 'name'
    _order = 'seq, name, id'

    seq = fields.Char(string='Sequence No', copy=False,
                      readonly=True,
                      index=True, default=lambda self: _('New'))
    name = fields.Char(string='Name')

    # # def name_get(self):
    # #     # TDE: this could be cleaned a bit I think
    # def _name_get(self):
    #     name = self.get('name', '')
    #     code = self._context.get('seq', True) or False
    #     if code:
    #         name = '[%s] %s' % (code, name)
    #     return (self['id'], name)

    def name_get(self):
        # TDE: this could be cleaned a bit I think
        """ To display name with sequence e number"""
        def _name_get(d):
            name = d.get('name', '')
            code = self._context.get('display_seq', True) and d.get('seq', False) or False
            if code:
                name = '[%s] %s' % (code, name)
            return (d['id'], name)

        result = []
        for location in self.sudo():
            name = location.name
            mydict = {
                'id': location.id,
                'name': name,
                'seq': location.seq,
            }
            result.append(_name_get(mydict))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('seq', 'New') == 'New':
                vals['seq'] = self.env['ir.sequence'].next_by_code(
                    'asset.location.sequence') or 'New'
        res = super(AssetLocation, self).create(vals_list)
        return res


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    account_location_id = fields.Many2one('account.asset.location', string='Asset Location')
    valuation_line_ids = fields.One2many('asset.valuation', 'asset_id', string='Valuation')


class Assetvaluation(models.Model):
    _name = 'asset.valuation'
    _description = 'Asset Valuation'

    date = fields.Date(string='Date')
    description = fields.Char(string='Description')
    valuator_id = fields.Many2one('res.partner', string='Valuator')
    valuation_amount = fields.Float(string='Valuation Amount')
    asset_id = fields.Many2one('account.asset')
