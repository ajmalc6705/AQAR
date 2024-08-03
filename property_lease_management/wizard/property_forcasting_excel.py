# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class PropertyForcastingExcelReport(models.TransientModel):
    _name = "property.forcasting.excel.wizard"
    _description = _("Property Forcasting Report")

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    building_select = fields.Selection([('all', 'All Buildings'),
                                        ('choose', 'Choose Building')], 'Building',
                                       required=True)
    building_ids = fields.Many2many('property.building', string='Choose Buildings', store=True)

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                if rec.date_from > rec.date_to:
                    raise ValidationError(_("From Date is Greater than To Date"))

    def button_print_report(self):
        self.ensure_one()
        if self.building_select == 'all':
            building = self.env['property.building'].search([])
        else:
            building = self.building_ids
        datas = {
            'ids': [],
            'date_from': self.date_from,
            'date_to': self.date_to,
            'building_select': self.building_select,
            'building_ids': building.ids
        }
        return self.env.ref('property_lease_management.property_forcasting_excel_tag').report_action(self)
