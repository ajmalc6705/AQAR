# -*- coding: utf-8 -*-

import base64
from io import BytesIO
from odoo import models
import datetime as DT


class ScheduledWorkCompletionReport(models.AbstractModel):
    _name = 'report.property_lease_management.work_completion_excel_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Scheduled Work Completion Report"

    def generate_xlsx_report(self, workbook, data, wizard):
        """ generating Scheduled Work Completion Report """
        format1 = workbook.add_format({'font_size': 14, 'right': True, 'left': True, 'top': True,
                                       'align': 'center', 'bold': True, 'valign': 'vcenter'})
        format2 = workbook.add_format({'font_size': 10, 'align': 'center', 'right': True, 'top': True, 'bold': True,
                                       'text_wrap': True, 'bottom': True, 'bg_color': '#41689c', 'valign': 'vcenter'})
        format3 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': False, 'right': True, 'left': True,
                                       'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})
        format33 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': False, 'right': True, 'left': True,
                                        'bottom': True, 'top': True, 'valign': 'vcenter', 'text_wrap': True})
        domain = [('date', '>=', wizard.date_from),('date', '<=', wizard.date_to),
                 ('maintenance_type', '=', 'routine'),('state','not in',['draft','send_for_approval','approved','start_the_work'])]
        if wizard.building_ids:
            domain.append(('building','in',wizard.building_ids.ids))
        print(domain)
        maintenances = self.env['property.maintenance'].search(domain)

        query = """ select at.name as Assets , pb.name as Building, pp.name as Property, mt.done_date as Date, count(mt.id)
        from 
        property_maintenance mt
        inner join assets_accessrz_type at on at.id=mt.asset_type_id
        inner join property_building pb on pb.id=mt.building
        inner join property_property pp on pp.id=mt.property_id
        where
        mt.done_date>='{date_from}' and
        mt.done_date<='{date_to}' and
        mt.maintenance_type ='routine' 
        and  mt.state not in  ('draft','send_for_approval','approved','start_the_work') 
        group by at.name,pb.name,pp.name,mt.done_date
        ORDER BY pp.name asc 
        """.format(date_from=wizard.date_from, date_to=wizard.date_to)
        self._cr.execute(query)
        result = self._cr.dictfetchall()

        from collections import defaultdict
        current_vals = sorted(result, key=lambda k: k['assets'])
        t_vals = defaultdict(list)
        for c_val in current_vals:
            t_vals[c_val['assets']].append(c_val)

        assets = maintenances.mapped('asset_type_id')
        buildings = maintenances.mapped('building').sorted(lambda x:x.name)
        row = 0

        for key in t_vals.keys():
            sheet = workbook.add_worksheet(key)
            row = 0
            for building in buildings:
                sheet.set_column(1, 1, 10)
                sheet.set_column(2, 2, 25)
                sheet.set_column(3, 3, 10)
                sheet.set_column(4, 4, 15)
                sheet.set_column(5, 5, 15)
                sheet.set_column(6, 6, 15)
                sheet.set_column(7, 7, 25)
                heading = "Work Completion Report ( " + key + " ) in " + building.name
                sheet.merge_range(row, 0, row + 1, 6, heading, format1)
                row = row + 2
                sheet.set_row(row, 25)
                sheet.write(row, 0, 'SL NO.', format2)
                sheet.write(row, 1, 'Flat No', format2)
                sheet.write(row, 2, 'Tenant Name', format2)
                quantity = key + 's Serviced'
                sheet.write(row, 3, quantity, format2)
                sheet.write(row, 4, 'Date', format2)
                sheet.write(row, 5, 'Signature (Tenant)', format2)
                sheet.write(row, 6, 'Signature (Care Taker)', format2)
                sheet.write(row, 7, 'Remarks', format2)
                row += 1
                for assets in t_vals[key]:
                    sl_no = 1
                    if building.name == assets['building']:
                        sheet.set_row(row, 20)
                        sheet.write(row, 0, sl_no, format3)
                        flat = self.env['property.property'].search([('name', '=', assets['property'])], limit=1)
                        sheet.write(row, 1, flat.name, format3)
                        if flat.rent_id:
                            sheet.write(row, 2, flat.rent_id.partner_id.name, format3)
                        else:
                            sheet.write(row, 2, " ", format3)
                        sheet.write(row, 3, assets['count'], format3)
                        sheet.write(row, 4,
                                    DT.datetime.strptime(str(assets['date']), '%Y-%m-%d %H:%M:%S').strftime(
                                        '%d-%m-%Y'),
                                    format3)
                        sheet.write(row, 5, " ", format3)
                        sheet.write(row, 6, " ", format3)
                        sheet.write(row, 7, " ", format3)
                        sl_no += 1
                        row += 1
                row += 2


        # for asset in assets:
        #     sheet = workbook.add_worksheet(asset.name)
        #     sheet.set_column(1, 1, 10)
        #     sheet.set_column(2, 2, 25)
        #     sheet.set_column(3, 3, 10)
        #     sheet.set_column(4, 4, 15)
        #     sheet.set_column(5, 5, 15)
        #     sheet.set_column(6, 6, 25)
        #     row = 0
        #     for building in buildings:
        #         sl_no = 1
        #         maintenance_data = maintenances.search(
        #             [('asset_type_id', '=', asset.id), ('building', '=', building.id)])
        #         heading = "Work Completion Report ( " + asset.name + " ) in " + building.name
        #         sheet.merge_range(row, 0, row + 1, 6, heading, format1)
        #         row = row + 2
        #         sheet.set_row(row, 25)
        #         sheet.write(row, 0, 'SL NO.', format2)
        #         sheet.write(row, 1, 'Flat No', format2)
        #         sheet.write(row, 2, 'Tenant Name', format2)
        #         sheet.write(row, 3, 'Date', format2)
        #         sheet.write(row, 4, 'Signature (Tenant)', format2)
        #         sheet.write(row, 5, 'Signature (Care Taker)', format2)
        #         sheet.write(row, 6, 'Remarks', format2)
        #         row += 1
        #         for maintenance in maintenance_data:
        #             sheet.set_row(row, 20)
        #             sheet.write(row, 0, sl_no, format3)
        #             sheet.write(row, 1, maintenance.property_id.name, format3)
        #             if maintenance.tenant_id:
        #                 sheet.write(row, 2, maintenance.tenant_id.name, format3)
        #             else:
        #                 sheet.write(row, 2, " ", format3)
        #             sheet.write(row, 3,
        #                         DT.datetime.strptime(str(maintenance.done_date), '%Y-%m-%d %H:%M:%S').strftime('%d-%m-%Y'),
        #                         format3)
        #             sheet.write(row, 4, " ", format3)
        #             sheet.write(row, 5, " ", format3)
        #             sheet.write(row, 6, " ", format3)
        #             sl_no += 1
        #             row += 1
        #         row += 2
