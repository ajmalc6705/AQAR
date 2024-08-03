# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RenewProjectContract(models.TransientModel):
    _name = 'project.contract.renew'
    _description = 'Project Contract Renew'

    @api.onchange('contract_id', 'contract_end_date')
    def get_default_start_date(self):
        for rec in self:
            rec.start_date = fields.Date.from_string(rec.contract_end_date) + relativedelta(days=1)

    contract_id = fields.Many2one('project.project', string='Contract')
    contract_end_date = fields.Date(string='Contract End Date', related='contract_id.date_end')
    start_date = fields.Date(string='New Start Date', required=True, default=get_default_start_date)
    expiration_date = fields.Date(string='New End Date', required=True)

    def renew_contract(self):
        for rec in self:
            rec.contract_id.update({
                'state': 'open',
                'contract_history': [(0, 0, {
                    'start_date': rec.start_date,
                    'expiration_date': rec.expiration_date,
                    'history_type': 'extended'
                })],
                'date_end': rec.expiration_date
            })

    @api.constrains('start_date', 'expiration_date')
    @api.onchange('start_date', 'expiration_date')
    def onchange_request_date(self):
        for rec in self:
            if rec.start_date and rec.start_date <= rec.contract_end_date:
                raise ValidationError("Contract already running on this date")
            if rec.start_date and rec.expiration_date and rec.start_date > rec.expiration_date:
                raise ValidationError(_('End Date cannot be set before Start Date.'))
