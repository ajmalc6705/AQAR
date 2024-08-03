# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ScheduledWorkCompletionWiz(models.TransientModel):
    _name = "scheduled.work.completion.wiz"
    _description = _("Scheduled Work Completion Report")

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    building_type = fields.Selection([('all', _('All Building')), ('selected_building', _('Selected Building'))],
                    string='Building Type',default='all')
    building_ids = fields.Many2many(comodel_name='property.building',string="Building's",)

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                if rec.date_from > rec.date_to:
                    raise ValidationError(_("From Date is Greater than To Date"))

    def button_print_report(self):
        self.ensure_one()
        if self.building_type == 'all':
            self.building_ids = []
        data = {
            'ids': [],
            'date_from': self.date_from,
            'date_to': self.date_to,
            'building_ids' : self.building_ids

        }
        return self.env.ref('property_lease_management.scheduled_work_completion_report_tag').report_action(self)
