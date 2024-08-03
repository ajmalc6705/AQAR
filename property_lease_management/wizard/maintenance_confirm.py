from odoo import fields, models, _


class MaintenanceState(models.TransientModel):
    _name = 'maintenance.update'
    _description = 'Change the state of sale order'

    def update_confirm(self):
        active_ids = self._context.get('active_ids', []) or []
        for record in self.env['property.maintenance'].browse(active_ids):
            if record.state == 'draft':
                record.state = 'send_for_approval'

    def update_new_approve(self):
        active_ids = self._context.get('active_ids', []) or []
        for record in self.env['property.maintenance'].browse(active_ids):
            if record.state == 'send_for_approval':
                record.write({'state': 'approved'})

    def update_start_the_work(self):
        active_ids = self._context.get('active_ids', []) or []
        for record in self.env['property.maintenance'].browse(active_ids):
            if record.state == 'approved':
                record.write({'state': 'start_the_work'})

    def update_mark_completed(self):
        active_ids = self._context.get('active_ids', []) or []
        for record in self.env['property.maintenance'].browse(active_ids):
            if record.state == 'start_the_work':
                # view_id = self.env['ir.model.data'].sudo().get_object_reference('amlak_property_management',
                #                                                                 'view_customer_complaint_form')
                record.state = 'done'
                record.complaint_id.cost = record.cost
                record.complaint_id.approv_suprvsr = record.supervisor
                record.complaint_id.compld_date = record.done_date
                record.complaint_id.parts_replaced = record.description
                if record.next_date:
                    record.asset_id.expiry_date = record.next_date
                record.complaint_id.cost = record.cost
