# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ProjectTenderChallenge(models.Model):
    _name = 'project.tender.challenge'
    _inherit = ['mail.thread']
    _description = 'Project Tender Challenges'

    tender_id = fields.Many2one(comodel_name='project.tender', string='Tender')
    challenge_type = fields.Many2one(comodel_name='tender.challenge.type', string='Challenge Type')
    remark = fields.Text(string="Remark")
    create_uid = fields.Many2one('res.users', 'Created by', index=True, readonly=True)
    write_uid = fields.Many2one('res.users', 'Write By', index=True, readonly=True)


class TenderChallengeType(models.Model):
    _name = 'tender.challenge.type'
    _description = 'Tender Challenge Type'

    name = fields.Char(string="Name", required=True)
    description = fields.Char(string="Description")
