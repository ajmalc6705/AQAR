# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertyUnitView(models.Model):
    _name = 'property.unit.view'
    _description = 'Unit View'

    name = fields.Char(string='Unit View')


class FurnishedType(models.Model):
    _name = 'furnished.type'
    _description = 'Furnished Type'

    name = fields.Char(string='Furnished Type')
