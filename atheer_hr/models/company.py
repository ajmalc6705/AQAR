from odoo import models, fields, _
import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    report_image1 = fields.Binary(string="Atheer Logo")
    report_image2 = fields.Binary(string="Aban Logo")
    report_image3 = fields.Binary(string="Mawa Logo")
    report_image4 = fields.Binary(string="Windar Logo")

    # TODO: TO REMOVE AFTER GO LIVE
    def update_salary_struct(self):
        contracts = self.env['hr.contract'].search([('state', '=', 'open')])
        for contract in contracts:
            try:
                contract.action_confirm()
            except Exception as e:
                _logger.exception(str(e))
                continue

