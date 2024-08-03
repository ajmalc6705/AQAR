# -*- coding: utf-8 -*-
import base64
import json
import pytz
import re
import uuid

from pytz.exceptions import UnknownTimeZoneError

from babel.dates import format_datetime, format_date, format_time
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.urls import url_encode

from odoo import exceptions, http, fields, _
from odoo.http import request, route
from odoo.osv import expression
from odoo.tools import plaintext2html, DEFAULT_SERVER_DATETIME_FORMAT as dtf
from odoo.tools.mail import is_html_empty
from odoo.tools.misc import babel_locale_parse, get_lang
from odoo.addons.base.models.ir_qweb import keep_query
from odoo.addons.http_routing.models.ir_http import unslug
from odoo.addons.appointment.controllers.appointment import AppointmentController


class WebsiteAppointment(AppointmentController):

    @http.route(['/appointment/<int:appointment_type_id>/submit'],
                type='http', auth="public", website=True, methods=["POST"])
    def appointment_form_submit(self, appointment_type_id, datetime_str, duration_str, staff_user_id, name, phone, email,
                                **kwargs):
        pdf_file = request.httprequest.files.get('attachment_name')
        """
        Create the event for the appointment and redirect on the validation page with a summary of the appointment.

        :param appointment_type_id: the appointment type id related
        :param datetime_str: the string representing the datetime
        :param staff_user_id: the user selected for the appointment
        :param name: the name of the user sets in the form
        :param phone: the phone of the user sets in the form
        :param email: the email of the user sets in the form
        """
        appointment_type = self._fetch_and_check_private_appointment_types(
            kwargs.get('filter_appointment_type_ids'),
            kwargs.get('filter_staff_user_ids'),
            kwargs.get('invite_token'),
            current_appointment_type_id=int(appointment_type_id),
        )
        if not appointment_type:
            raise NotFound()
        timezone = request.session.get('timezone') or appointment_type.appointment_tz
        tz_session = pytz.timezone(timezone)
        date_start = tz_session.localize(fields.Datetime.from_string(datetime_str)).astimezone(pytz.utc).replace(
            tzinfo=None)
        duration = float(duration_str)
        date_end = date_start + relativedelta(hours=duration)
        invite_token = kwargs.get('invite_token')

        # check availability of the selected user again (in case someone else booked while the client was entering the form)
        staff_user = request.env['res.users'].sudo().browse(int(staff_user_id)).exists()
        if staff_user not in appointment_type.sudo().staff_user_ids:
            raise NotFound()
        if staff_user and not staff_user.partner_id.calendar_verify_availability(date_start, date_end):
            return request.redirect(
                '/appointment/%s?%s' % (appointment_type.id, keep_query('*', state='failed-staff-user')))

        Partner = self._get_customer_partner() or request.env['res.partner'].sudo().search([('email', '=like', email)],
                                                                                           limit=1)
        if Partner:
            if not Partner.calendar_verify_availability(date_start, date_end):
                return request.redirect(
                    '/appointment/%s?%s' % (appointment_type.id, keep_query('*', state='failed-partner')))
            if not Partner.mobile:
                Partner.write({'mobile': phone})
            if not Partner.email:
                Partner.write({'email': email})
        else:
            Partner = Partner.create({
                'name': name,
                'mobile': Partner._phone_format(phone, country=self._get_customer_country()),
                'email': email,
                'lang': request.lang.code,
            })

        # partner_inputs dictionary structures all answer inputs received on the appointment submission: key is question id, value
        # is answer id (as string) for choice questions, text input for text questions, array of ids for multiple choice questions.
        partner_inputs = {}
        appointment_question_ids = appointment_type.question_ids.ids
        for k_key, k_value in [item for item in kwargs.items() if item[1]]:
            question_id_str = re.match(r"\bquestion_([0-9]+)\b", k_key)
            if question_id_str and int(question_id_str.group(1)) in appointment_question_ids:
                partner_inputs[int(question_id_str.group(1))] = k_value
                continue
            checkbox_ids_str = re.match(r"\bquestion_([0-9]+)_answer_([0-9]+)\b", k_key)
            if checkbox_ids_str:
                question_id, answer_id = [int(checkbox_ids_str.group(1)), int(checkbox_ids_str.group(2))]
                if question_id in appointment_question_ids:
                    partner_inputs[question_id] = partner_inputs.get(question_id, []) + [answer_id]

        # The answer inputs will be created in _prepare_calendar_values from the values in question_answer_inputs
        question_answer_inputs = []
        base_answer_input_vals = {
            'appointment_type_id': appointment_type.id,
            'partner_id': Partner.id,
        }
        description_bits = []
        description = ''

        if phone:
            description_bits.append(_('Mobile: %s', phone))
        if email:
            description_bits.append(_('Email: %s', email))

        for question in appointment_type.question_ids.filtered(lambda question: question.id in partner_inputs.keys()):
            if question.question_type == 'checkbox':
                answers = question.answer_ids.filtered(lambda answer: answer.id in partner_inputs[question.id])
                question_answer_inputs.extend([
                    dict(base_answer_input_vals, question_id=question.id, value_answer_id=answer.id) for answer in answers
                ])
                description_bits.append('%s: %s' % (question.name, ', '.join(answers.mapped('name'))))
            elif question.question_type in ['select', 'radio']:
                question_answer_inputs.append(
                    dict(base_answer_input_vals, question_id=question.id, value_answer_id=int(partner_inputs[question.id]))
                )
                selected_answer = question.answer_ids.filtered(lambda answer: answer.id == int(partner_inputs[question.id]))
                description_bits.append('%s: %s' % (question.name, selected_answer.name))
            elif question.question_type == 'char':
                question_answer_inputs.append(
                    dict(base_answer_input_vals, question_id=question.id,
                         value_text_box=partner_inputs[question.id].strip())
                )
                description_bits.append('%s: %s' % (question.name, partner_inputs[question.id].strip()))
            elif question.question_type == 'text':
                question_answer_inputs.append(
                    dict(base_answer_input_vals, question_id=question.id,
                         value_text_box=partner_inputs[question.id].strip())
                )
                description_bits.append('%s:<br/>%s' % (question.name, plaintext2html(partner_inputs[question.id].strip())))

        if description_bits:
            description = '<ul>' + ''.join(['<li>%s</li>' % bit for bit in description_bits]) + '</ul>'

        # FIXME AWA/TDE double check this and/or write some tests to ensure behavior
        # The 'mail_notify_author' is only placed here and not in 'calendar.attendee#_send_mail_to_attendees'
        # Because we only want to notify the author in the context of Online Appointments
        # When creating a meeting from your own calendar in the backend, there is no need to notify yourself
        event = request.env['calendar.event'].with_context(
            mail_notify_author=True,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            allowed_company_ids=staff_user.company_ids.ids,
        ).sudo().create(
            self._prepare_calendar_values(appointment_type, date_start, date_end, duration, description,
                                          question_answer_inputs, name, staff_user, Partner, invite_token)
        )
        Attachments = request.env['ir.attachment']
        name = kwargs['attachment_name']
        file_val = kwargs.get('attachment_name')
        if pdf_file:
            pdf_content = pdf_file.read()
            attachment = request.env['ir.attachment'].sudo().create({
                'name': pdf_file.filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'calendar.event',
                'store_fname': name,
                'res_id': event.id
            })
        event.attendee_ids.write({'state': 'accepted'})
        return request.redirect(
            '/calendar/view/%s?partner_id=%s&%s' % (event.access_token, Partner.id, keep_query('*', state='new')))

