# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class LevyMaster(models.Model):
    _name = 'levy.master'
    _description = 'Levy Master'
    _rec_name = 'levy_code'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    levy_code = fields.Char(string='Levy Code')
    levy_name = fields.Char(string='Levy Name')
    sequence = fields.Integer(string='Sequence')
    sub_levy_ids = fields.One2many('sub.levy.line', 'levy_id', string='Sub Levy')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    _sql_constraints = [
        ("levy_code_uniq", "unique (levy_code)", "Levy Code already exists!"),
    ]


class SubLevyLine(models.Model):
    _name = 'sub.levy.line'
    _rec_name = "sub_levy_name"
    _description = 'Sub Levy'

    sub_levy_code = fields.Char(string='Sub Levy Code')
    sub_levy_name = fields.Char(string='Sub Levy Name')
    levy_id = fields.Many2one('levy.master', string='Levy')
    sub_levy_account_id = fields.Many2one('account.account', string='Sub Levy A/C')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
