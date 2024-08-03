# -*- coding: utf-8 -*-

from odoo import models,fields,api,_

class PaymentTerm(models.Model):
    _name = 'payment.term'
    _description = 'Payment Term'

    name = fields.Char(string="Payment Term")
    description = fields.Html(string='Description')