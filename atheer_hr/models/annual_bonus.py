# -*- coding: utf-8 -*-

from datetime import date
from odoo.exceptions import UserError
from odoo import fields, models, api, _
from lxml import etree
import json


class AnnualBonus(models.Model):
    _name = "annual.bonus"
    _description = 'Annual Bonus'
    _inherit = ['mail.thread']
    _rec_name = 'reference'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', required=True,
                                  tracking=True)
    designation = fields.Many2one('hr.job', string='Designation', readonly=True, related='employee_id.job_id',
                                  tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True,
                                    related='employee_id.department_id',
                                    tracking=True)
    effective_date = fields.Date(string="Effective Date", required=True)
    bonus_amount = fields.Float(string="Bonus Amount", required=True, digits=(12, 3))
    state = fields.Selection([
        ('hr', 'HR Manager'),
        ('ceo', 'CEO'),
        ('approved', 'Approved'),
        ('reject', 'Refused'),
    ], default='hr', copy=False, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    approval_person = fields.Many2one('res.users', string="Approved By", readonly=True)
    hr_remarks = fields.Char(string="HR Remarks", readonly=False, states={'approved': [('readonly', True)]})
    ceo_remarks = fields.Char(string="CEO Remarks", readonly=False, states={'approved': [('readonly', True)]})
    bonus_id = fields.Many2one('hr.payslip')
    reference = fields.Char(string="Reference", copy=False, tracking=True, readonly=True)
    today_date = fields.Date(string="Date", readonly=True, store=True)
    rejected_by = fields.Many2one('res.users', string="Refused By")
    rejected_date = fields.Date(string="Refused Date")
    # access flags
    send_back_flag = fields.Boolean(default=False)
    left_hr_flag = fields.Boolean(default=False)
    left_ch_flag = fields.Boolean(default=False)

    @api.model
    def create(self, vals):
        vals['reference'] = self.env['ir.sequence'].next_by_code('annual.bonus') or 'New'
        result = super(AnnualBonus, self).create(vals)
        return result

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(AnnualBonus, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                       submenu=False)
        form_view_id = self.env.ref('atheer_hr.view_annual_bonus_form').id
        if res.get('view_id', False) == form_view_id and res.get('type', False) == 'form':
            doc = etree.XML(res['arch'])
            if len(doc):
                if not self.env.user.has_group('atheer_hr.group_hr_manager'):
                    node = doc.xpath("//field[@name='hr_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('atheer_hr.group_hr_ceo'):
                    node = doc.xpath("//field[@name='ceo_remarks']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)

                return res
        return res

    def sent_to_ceo(self):
        for rec in self:
            rec.left_ch_flag = True
            rec.send_back_flag = False
            rec.write({'state': 'ceo'})

    def approve(self):
        for rec in self:
            rec.write({'state': 'approved', 'approval_person': self.env.user.id, 'today_date': date.today()})

    def action_reject(self):
        for rec in self:
            rec.write({'state': 'reject', 'rejected_by': self.env.user.id, 'rejected_date': date.today()})

    def send_back(self):
        """
        send backs to previous state
        """
        for rec in self:
            if rec.state == 'ceo':
                rec.state = 'hr'
                rec.send_back_flag = True

    def unlink(self):
        for record in self:
            if not self.env.ref('base.user_admin').id or not self.env.ref(
                    'base.user_root').id or not self.env.user.has_group('base.group_system'):
                if record.state != 'hr':
                    raise UserError(
                        _('You cannot delete the annual bonus %s in the current state.', record.reference)
                    )
            return super(AnnualBonus, self).unlink()
