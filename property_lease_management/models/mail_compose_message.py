from odoo import models, fields
from dateutil.relativedelta import relativedelta


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        res = super(MailComposeMessage, self).action_send_mail()
        if self.model == 'property.rent':
            today = fields.date.today()
            rent_id = self.env['property.rent'].browse(self.res_id)
            rent_id.update({'notification_ids': [(0, 0, {'rent_id': rent_id.id,
                                                         'building_id': rent_id.building.id,
                                                         'property_id': rent_id.property_id.id,
                                                         'partner_id': rent_id.partner_id.id,
                                                         'notification_date': today,
                                                         'description': 'Manually Created Notification',
                                                         'notification_type': 'rent_expiry'})]})
        return res
