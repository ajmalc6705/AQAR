# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class OpportunityReportWiz(models.TransientModel):
    _name = "property.opportunity.report.wiz"
    _description = _("Property Opportunity Report Wizard")

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                if rec.date_from > rec.date_to:
                    raise ValidationError(_("From Date is Greater than To Date"))

    # def button_print_report(self):
    #     self.ensure_one()
    #     data = self.read()[0]
    #     data['property_ids'] = self.env.context.get('active_ids', [])
    #     property_ids = self.env['property.property'].browse(data['property_ids'])
    #     datas = {
    #         'ids': [],
    #         'model': 'property.property',
    #         'form': data
    #     }
    #     # return self.env.ref('property_lease_management.report_income_and_lost_opportunity').report_action(
    #     #     property_ids, data=datas)
    #     return self.env.ref('property_lease_management.report_income_and_lost_opportunity').report_action(
    #         property_ids, data=datas)
    def button_print_report(self):
        self.ensure_one()
        data = self.read()[0]
        data['property_ids'] = self.env.context.get('active_ids', [])
        property_ids = self.env['property.property'].browse(data['property_ids'])
        datas = {
            'ids': [],
            'model': 'property.property',
            'form': data
        }
        print(data)
        print(datas, 'Datas')
        return self.env.ref('property_lease_management.action_report_income_and_lost_opportunity').report_action(property_ids, data=datas)