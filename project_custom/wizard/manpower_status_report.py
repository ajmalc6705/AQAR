# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import UserError


class LncManpowerStatusReport(models.TransientModel):
    _name = "manpower.status.report"
    _description = "Manpower Status Report"

    @api.onchange('project_id')
    def get_location_domain(self):
        domain = []
        res = dict()
        if self.project_id:
            project_locations = []
            if self.project_id.tender:
                if self.date:
                    loc = self.project_id.tender.location_ids.filtered(lambda x: x.date_create <= self.date).ids
                    project_locations.extend(loc)
                else:
                    project_locations.extend(self.project_id.tender.location_ids.ids)
            else:
                if self.date:
                    loc = self.project_id.location_ids.filtered(lambda x: x.date_create <= self.date).ids
                    project_locations.extend(loc)
                else:
                    project_locations.extend(self.project_id.location_ids.ids)
            domain += [('id', 'in', project_locations)]
        res['domain'] = {'location_id': domain}
        return res

    @api.onchange('date')
    def get_project_domain(self):
        domain = []
        res = dict()
        if self.date:
            domain += [('start_date', '<=', self.date), ('date_end', '>=', self.date)]
        res['domain'] = {'project_id': domain}
        return res

    @api.onchange('project_id')
    def reset_location(self):
        self.location_id = False

    date = fields.Date(string=_('Date'), required=True)
    project_id = fields.Many2one('project.project', string=_('Project'), domain=get_project_domain)
    location_id = fields.Many2one('project.tender.location', string=_('Location'), domain=get_location_domain)

    def get_report_values(self):
        data = {}
        data["form"] = self.read()[0]
        location_obj = self.env['project.tender.location']
        project_obj = self.env['project.project']
        if self.project_id and self.location_id:
            location_rec = self.location_id
            project_rec = self.project_id
        elif self.project_id:
            location_rec = self.project_id.mapped('tender.location_ids').filtered(
                lambda x: x.date_create <= self.date) + self.project_id.mapped('location_ids').filtered(
                lambda x: x.date_create <= self.date)
            project_rec = self.project_id
            if not location_rec:
                raise UserError(_("There are no location records for specified project "))
        else:
            project_rec = project_obj.sudo().search([('start_date', '<=', self.date),
                                                     ('date_end', '>=', self.date)])
            location_rec = project_rec.mapped('tender.location_ids').filtered(
                lambda x: x.date_create <= self.date) + project_rec.mapped('location_ids').filtered(
                lambda x: x.date_create <= self.date)
            if not location_rec:
                raise UserError(_("There is no locations added."))
        project_list = []
        for project in project_rec:
            location_list = []
            location_records = project.mapped('tender.location_ids').filtered(
                lambda x: x.id in location_rec.ids) + project.mapped('location_ids').filtered(
                lambda x: x.id in location_rec.ids)
            if not location_records:
                continue
            for location in location_records:
                current_employees = location.employee_ids
                employee_on_date = set(current_employees.ids)
                if self.date < fields.Date.today():
                    transfer_history = location.mapped('transfer_history'). \
                        filtered(lambda x: self.date <= x.effective_date <= fields.Date.today()). \
                        sorted(key=lambda x: x.effective_date, reverse=True)
                    for history in transfer_history:
                        if history.location_from == location:
                            employee_on_date.add(history.employee_id.id)
                        else:
                            if history.employee_id.id in employee_on_date:
                                employee_on_date.remove(history.employee_id.id)
                elif self.date > fields.Date.today():
                    transfer_history = location.mapped('transfer_history'). \
                        filtered(lambda x: fields.Date.today() < x.effective_date <= self.date). \
                        sorted(key=lambda x: x.effective_date)
                    for history in transfer_history:
                        if history.location_from == location:
                            if history.employee_id.id in employee_on_date:
                                employee_on_date.remove(history.employee_id.id)
                        else:
                            employee_on_date.add(history.employee_id.id)
                for e_exit in location.exit_ids.filtered(lambda x: x.state == 'approve'):
                    if e_exit.last_day_of_work < self.date:
                        if e_exit.employee_id.id in employee_on_date:
                            employee_on_date.remove(e_exit.employee_id.id)
                    elif self.date < e_exit.last_day_of_work < fields.Date.today():
                        employee_on_date.add(e_exit.employee_id.id)
                leaves = self.env['hr.leave'].search([('employee_id', 'in', list(employee_on_date)),
                                                      ('state', '=', 'validate'),
                                                      ('date_from', '<=', self.date),
                                                      ('date_to', '>=', self.date)])
                employees = leaves.mapped('employee_id')
                emp_on_leave_count = len(set(employees))
                current_manpower = len(employee_on_date)
                emp_on_notice = location.exit_ids.filtered(
                    lambda x: x.state == 'approve' and x.last_day_of_work >= self.date >= x.date_create)
                manpower_status = current_manpower - location.manpower
                if manpower_status > 0:
                    manpower_status_str = 'Excess of ' + str(abs(manpower_status)) + ' Employees'
                    manpower_status_type = 'excess'
                elif manpower_status < 0:
                    manpower_status_str = 'Shortage of ' + str(abs(manpower_status)) + ' Employees'
                    manpower_status_type = 'shortage'
                else:
                    manpower_status_str = 'Normal'
                    manpower_status_type = 'normal'
                location_list.append({
                    'name': location.name,
                    'manpower': location.manpower,
                    'current_manpower': current_manpower,
                    'manpower_status': manpower_status,
                    'manpower_status_str': manpower_status_str,
                    'manpower_status_type': manpower_status_type,
                    'emp_on_leave': emp_on_leave_count,
                    'emp_on_notice': len(emp_on_notice) if emp_on_notice else 0,
                    'manpower_available': current_manpower - emp_on_leave_count
                })
            pro_manpower_status = sum([location['manpower_status'] for location in location_list])
            if pro_manpower_status > 0:
                pro_manpower_status_str = 'Excess of ' + str(abs(pro_manpower_status)) + ' Employees'
                pro_manpower_status_type = 'excess'
            elif pro_manpower_status < 0:
                pro_manpower_status_str = 'Shortage of ' + str(abs(pro_manpower_status)) + ' Employees'
                pro_manpower_status_type = 'shortage'
            else:
                pro_manpower_status_str = 'Normal'
                pro_manpower_status_type = 'normal'
            project_list.append({
                'name': project.name,
                'location_list': location_list,
                'manpower': sum([location['manpower'] for location in location_list]),
                'current_manpower': sum([location['current_manpower'] for location in location_list]),
                'emp_on_leave': sum([location['emp_on_leave'] for location in location_list]),
                'manpower_status': pro_manpower_status,
                'manpower_status_type': pro_manpower_status_type,
                'manpower_status_str': pro_manpower_status_str,
                'emp_on_notice': sum([location['emp_on_notice'] for location in location_list]),
                'manpower_available': sum([location['manpower_available'] for location in location_list]),
            })
        data.update({'project_list': project_list})
        total_manpower_status = sum([project['manpower_status'] for project in project_list])
        if total_manpower_status > 0:
            total_manpower_status_str = 'Excess of ' + str(abs(total_manpower_status)) + ' Employees'
            t_manpower_status_type = 'excess'
        elif total_manpower_status < 0:
            total_manpower_status_str = 'Shortage of ' + str(abs(total_manpower_status)) + ' Employees'
            t_manpower_status_type = 'shortage'
        else:
            total_manpower_status_str = 'Normal'
            t_manpower_status_type = 'normal'
        data.update({'total': {
            'manpower': sum([project['manpower'] for project in project_list]),
            'current_manpower': sum([project['current_manpower'] for project in project_list]),
            'emp_on_leave': sum([project['emp_on_leave'] for project in project_list]),
            'manpower_status': total_manpower_status,
            'manpower_status_type': t_manpower_status_type,
            'manpower_status_str': total_manpower_status_str,
            'emp_on_notice': sum([project['emp_on_notice'] for project in project_list]),
            'manpower_available': sum([project['manpower_available'] for project in project_list]),
        }})
        return data

    def button_print_report(self):
        data = self.get_report_values()
        return self.env.ref('project_custom.action_report_manpower_status').report_action(self, data=data)

    def print_xls(self):
        data = self.get_report_values()
        return self.env.ref('project_custom.action_report_manpower_status_xls').report_action(
            self, data=data, config=False)


class ManpowerStatusReportWiz(models.TransientModel):
    _name = "manpower.status.report.wiz"
    _description = _("Manpower Status Report Wizard")

    project_id = fields.Many2many('project.project', string=_('Project'))
    date = fields.Date(_('Date'))

    def button_print_report(self):
        data = {}
        data['project_id'] = self.project_id.ids
        return self.env.ref('project_custom.manpower_status_report_xls').report_action(
            None, data=data, config=False)
