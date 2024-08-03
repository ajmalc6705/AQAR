# -*- coding: utf-8 -*-

from odoo import models,fields,api,_


class CommunityStages(models.Model):
    _name = 'community.stages'
    _rec_name = 'name'
    _description = 'Community stages'


    name = fields.Char(string="Name")