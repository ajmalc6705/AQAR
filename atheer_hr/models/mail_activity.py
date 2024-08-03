from odoo import models, fields, api


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    emp_doc_type = fields.Selection([('visa', 'Visa'), ('passport', 'Passport'),
                                     ('civil', 'Civil Id'), ('contract', 'Contract'), ('doc', 'Document')],
                                    string="Employee Document Type")
    doc_id = fields.Many2one('hr.employee.docs', "Document")
    excess_annual_leave = fields.Boolean(string="Excess Annual Leave Reminder", default=False)

    def unlink(self):
        """ Override unlink to delete records activities through (res_model, res_id). """
        notify_activity_type = self.env.ref('atheer_hr.mail_act_employee_doc_expiry')
        res_ids = self.filtered(lambda a: a.activity_type_id == notify_activity_type).mapped('res_id')
        doc_type_ids = self.filtered(lambda a: a.activity_type_id == notify_activity_type).filtered(
            lambda x: x.emp_doc_type != 'doc').mapped('emp_doc_type')
        doc_ids = self.filtered(lambda a: a.activity_type_id == notify_activity_type).filtered(
            lambda x: x.emp_doc_type == 'doc').mapped('doc_id')
        if doc_ids:
            doc_ids.write({'doc_notify': False})
        if res_ids:
            employee_rec_ids = self.env['hr.employee'].browse(res_ids)
            for employee_rec in employee_rec_ids:
                for emp_doc_type in doc_type_ids:
                    pending_expiry_notify = employee_rec.activity_ids.filtered(
                        lambda x: x.emp_doc_type == emp_doc_type and x.id not in self.ids and
                                  x.activity_type_id == notify_activity_type)
                    if not pending_expiry_notify:
                        employee_rec.write({emp_doc_type + '_notify': False})
        # Excessive annual leave notification
        l_ids = self.filtered(lambda a: a.excess_annual_leave).mapped('res_id')
        if l_ids:
            emp_rec_ids = self.env['hr.employee'].browse(l_ids)
            for emp_rec in emp_rec_ids:
                emp_rec.write({'annual_leave_notify': False})
        return super(MailActivity, self).unlink()

    # def _action_done(self, feedback=False, attachment_ids=None):
    #     notify_activity_type = self.env.ref('atheer_hr.mail_act_employee_doc_expiry')
    #     res_ids = self.filtered(lambda a: a.activity_type_id == notify_activity_type).mapped('res_id')
    #     if res_ids:
    #         employee_rec = self.env['hr.employee'].browse(res_ids)
    #         emp_doc_type = self.emp_doc_type
    #         pending_expiry_notify = employee_rec.activity_ids.filtered(
    #             lambda x: x.emp_doc_type == self.emp_doc_type and x.id != self.id)
    #         if not pending_expiry_notify:
    #             employee_rec.write({emp_doc_type+'_notify': False})
    #     return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)
