# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context, get_lang


class Mailactivity(models.Model):
    _inherit = 'mail.activity'

    def action_feedback(self, feedback=False, attachment_ids=None):
        admin = self.env['res.users'].browse(2)
        odoobot = self.env['res.users'].browse(1)
        if self.user_id:
            if self.user_id.id != self.env.user.id and admin and odoobot:
                raise UserError(_('Only the assigned user has access to mark it as done'))

        messages, _next_activities = self.with_context(clean_context(self.env.context))._action_done(feedback=feedback,
                                                                                                     attachment_ids=attachment_ids)
        return messages[0].id if messages else False

    def action_feedback_schedule_next(self, feedback=False, attachment_ids=None):
        admin = self.env['res.users'].browse(2)
        odoobot = self.env['res.users'].browse(1)
        if self.user_id:
            if self.user_id.id != self.env.user.id and admin and odoobot:
                raise UserError(_('Only the assigned user has access to mark it as done'))
        ctx = dict(
            clean_context(self.env.context),
            default_previous_activity_type_id=self.activity_type_id.id,
            activity_previous_deadline=self.date_deadline,
            default_res_id=self.res_id,
            default_res_model=self.res_model,
        )
        _messages, next_activities = self._action_done(feedback=feedback,
                                                       attachment_ids=attachment_ids)  # will unlink activity, dont access self after that
        if next_activities:
            return False
        return {
            'name': _('Schedule an Activity'),
            'context': ctx,
            'view_mode': 'form',
            'res_model': 'mail.activity',
            'views': [(False, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def unlink(self):
        admin = self.env['res.users'].browse(2)
        odoobot = self.env['res.users'].browse(1)
        allowed_user_list = []
        for rec in self:
            create_user = rec.create_uid
            if create_user:
                allowed_user_list.append(create_user.id)
            assigned_user = rec.user_id
            if assigned_user:
                allowed_user_list.append(assigned_user.id)
            if self.env.user.id not in allowed_user_list and admin and odoobot:
                raise UserError(_('Only the created/assigned user has access to cancel/delete the schedule activity'))
        res = super().unlink()
        return res
