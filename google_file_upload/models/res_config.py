# -*- coding: utf-8 -*-
# Part of Laxicon Solution. See LICENSE file for full copyright and
# licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"

    drive_folder_id = fields.Char(related='company_id.drive_folder_id', readonly=False,
                                  help="make a folder on drive in which you want to upload files; then open that folder; the last thing in present url will be folder id")
    folder_type = fields.Selection(related='company_id.folder_type', readonly=False)
    model_ids = fields.Many2many('ir.model', related='company_id.model_ids', readonly=False, string="Models")
