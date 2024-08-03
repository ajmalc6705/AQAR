# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    sh_notify_purchase_representative_po = fields.Boolean('Notify Purchase Buyer while update bid from portal')


class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_notify_purchase_representative_po = fields.Boolean('Notify Purchase Buyer while update bid from portal',related='company_id.sh_notify_purchase_representative_po',readonly=False)
