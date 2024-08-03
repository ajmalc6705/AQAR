from odoo import models, fields, api
from ast import literal_eval


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def default_notification_duration(self):
        notify_duration = self.env.ref('atheer_hr.notification_duration_2_months')
        return notify_duration

    insurance_notification = fields.Many2many('notification.duration', 'insurance_notification_rel',
                                              default=default_notification_duration,
                                              string='Insurance Expiry Notification')
    visa_notification = fields.Many2many('notification.duration', 'visa_notification_rel',
                                         default=default_notification_duration,
                                         string='Visa Expiry Notification')
    passport_notification = fields.Many2many('notification.duration', 'passport_notification_rel',
                                             default=default_notification_duration,
                                             string='Passport Expiry Notification')
    civil_notification = fields.Many2many('notification.duration', 'civil_notification_rel',
                                          default=default_notification_duration,
                                          string='Civil Card Expiry Notification')
    contract_notification = fields.Many2many('notification.duration', 'contract_notification_rel',
                                             default=default_notification_duration,
                                             string='Contract Expiry Notification')
    doc_notification = fields.Many2many('notification.duration', 'doc_notification_rel',
                                        default=default_notification_duration,
                                        string='Document Expiry Notification')
    # ====================

    annual_leave_calc_rate = fields.Float('Annual Leave Calculation Rate', digits=(16, 9), default=0.082191781,
                                          config_parameter='atheer_hr.annual_leave_calc_rate')
    annual_leave_type = fields.Many2one('hr.leave.type', string='Annual Leave', domain="[('annual_leave', '=', True)]",
                                        config_parameter='atheer_hr.annual_leave_type')

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        with_user = self.env['ir.config_parameter'].sudo()
        with_user.set_param('atheer_hr.visa_notification', self.visa_notification.ids, )
        with_user.set_param('atheer_hr.passport_notification', self.passport_notification.ids, )
        with_user.set_param('atheer_hr.civil_notification', self.civil_notification.ids, )
        with_user.set_param('atheer_hr.contract_notification', self.contract_notification.ids, )
        with_user.set_param('atheer_hr.doc_notification', self.doc_notification.ids, )
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        with_user = self.env['ir.config_parameter'].sudo()
        visa_notification = with_user.get_param('atheer_hr.visa_notification')
        passport_notification = with_user.get_param('atheer_hr.passport_notification')
        civil_notification = with_user.get_param('atheer_hr.civil_notification')
        contract_notification = with_user.get_param('atheer_hr.contract_notification')
        doc_notification = with_user.get_param('atheer_hr.doc_notification')
        res.update(
            visa_notification=[(6, 0, literal_eval(visa_notification))] if visa_notification else False,
            civil_notification=[(6, 0, literal_eval(civil_notification))] if civil_notification else False,
            contract_notification=[(6, 0, literal_eval(contract_notification))] if contract_notification else False,
            doc_notification=[(6, 0, literal_eval(doc_notification))] if doc_notification else False,
        )
        return res


# todo:to remove

class HrBudgetLeaveSalary(models.Model):
    _name = "hr.budget.leave.salary"
    _description = "Hr Budget Leave Salary"


class LeaveSalary(models.Model):
    _name = 'budget.annual.leave.confirmed'
    _description = "Budget Annual Leave Confirmed"


class HrBudgetGratuity(models.Model):
    _name = "hr.budget.gratuity"
    _description = "Hr Budget Gratuity"


class GratuityConfirmed(models.Model):
    _name = 'budget.gratuity.confirmed'
    _description = 'Budget Gratuity Confirmed'


class HrBudgetVisa(models.Model):
    _name = "hr.budget.visa"
    _description = "HR Budget Visa"


class BudgetVisa(models.Model):
    _name = 'budget.visa.confirmed'
    _description = 'Budget Visa Confirmed'
