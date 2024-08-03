from odoo import fields, models


class MaintenanceAttachment(models.TransientModel):
    _name = 'maintenance.attachment'
    _description = 'Change the state of sale order'

    attachment_id = fields.Binary(string='Attachment')

    def upload_attachment(self):
        active_ids = self._context.get('active_ids', []) or []
        for record in self.env['property.maintenance'].browse(active_ids):
            record.attachment_id = self.attachment_id
