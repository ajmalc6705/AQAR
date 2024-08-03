# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class AqarContract(models.Model):
    _name = 'aqar.contract'
    _description = 'Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'contract_seq'

    name = fields.Char(string='Name', help="Name of the Contract")
    contract_seq = fields.Char(string='Contract', copy=False,
                               readonly=True, help="Sequence for Contract",
                               index=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Customer')
    building_id = fields.Many2one('property.building', string='Building')
    unit_id = fields.Many2many('property.property', string='Unit')
    unit_ids = fields.Many2many('property.property', string="Unit Ids", compute='_compute_unit_ids')
    unit_count = fields.Integer(string="Total Units", compute='_compute_units')
    contract_categ_id = fields.Many2one('aqar.contract.category', string='Contract Category')
    date = fields.Date(string='Date', default=fields.Date.today())
    start_date = fields.Date(string="Contract Start Date")
    end_date = fields.Date(string="Contract End Date")
    contract_amt = fields.Float(string='Contract Amount', digits=(12, 3))
    user_ids = fields.Many2many('res.users', string='User')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 help="Company")
    parent_id = fields.Many2one('aqar.contract', string='Parent Name')
    renew_id = fields.Many2one('aqar.contract', string='Old Contract')
    child_ids = fields.One2many('aqar.contract', 'parent_id', string='Child Tags')
    subcontract_count = fields.Integer("Sub-Contract Count", compute='_compute_subcontract_count')
    contract_type = fields.Selection([('issues', 'Issue'), ('receipt', 'Receipt')], string='Contract Type')
    contract_mode = fields.Selection([('general', 'General'), ('property', 'Property')], string='Contract Mode',
                                     default='general')
    is_create_renew = fields.Boolean(string='Is Create Renew')
    state = fields.Selection([('draft', 'Draft'), ('running', 'Running'), ('expire', 'Expired'),
                              ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    doc_ids = fields.Many2many('atheer.documents', string='Documents')
    terms = fields.Html(string="Terms and Conditions")
    notes = fields.Html(string="Description")
    active = fields.Boolean('Active', default=True, tracking=True)
    renewal_count = fields.Integer(compute="_compute_origin_renewal_count", string='Renewal Count')

    def name_get(self):
        res = []
        for each in self:
            name = each.name
            if each.contract_seq:
                res.append((each.id, str(name) + ' [' + each.contract_seq + ']'))
            else:
                res.append((each.id, name))
        return res

    @api.onchange('contract_categ_id')
    def _onchange_user(self):
        for rec in self:
            if rec.contract_categ_id.user_notification_ids:
                rec.user_ids = rec.contract_categ_id.user_notification_ids.ids
            if rec.contract_categ_id:
                rec.company_id = rec.contract_categ_id.company_id.id

    @api.depends('child_ids')
    def _compute_subcontract_count(self):
        subcontract_per_count = self._get_subcontract_ids_per_contract_id()
        for task in self:
            task.subcontract_count = len(subcontract_per_count.get(task.id, []))

    def _get_subcontract_ids_per_contract_id(self):
        if not self:
            return {}

        res = dict.fromkeys(self._ids, [])
        if all(self._ids):
            self.env.cr.execute(
                """
         WITH RECURSIVE task_tree
                     AS (
                     SELECT id, id as supertask_id
                       FROM aqar_contract
                      WHERE id IN %(ancestor_ids)s
                      UNION
                         SELECT t.id, tree.supertask_id
                           FROM aqar_contract t
                           JOIN task_tree tree
                             ON tree.id = t.parent_id
               ) SELECT supertask_id, ARRAY_AGG(id)
                   FROM task_tree
                  WHERE id != supertask_id
               GROUP BY supertask_id
                """,
                {
                    "ancestor_ids": tuple(self.ids),
                    "active": self._context.get('active_test', True),
                }
            )
            res.update(dict(self.env.cr.fetchall()))
        else:
            res.update({
                task.id: task._get_contracts_recursively().ids
                for task in self
            })
        return res

    def _get_contracts_recursively(self):
        children = self.child_ids
        if not children:
            return self.env['aqar.contract']
        return children + children._get_contracts_recursively()

    @api.constrains('start_date', 'end_date')
    def check_date(self):
        """ Check the date validations of start date and end date"""
        if self.end_date < self.start_date:
            raise UserError(_('Contract Start Date should be less than End Date'))

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            if vals.get('contract_seq', 'New') == 'New':
                vals['contract_seq'] = self.env['ir.sequence'].next_by_code(
                    'contract.sequence') or 'New'
        return super(AqarContract, self).create(vals_list)

    @api.depends('building_id')
    def _compute_unit_ids(self):
        """ dynamic domain for unit"""
        self.unit_ids = False
        for rec in self:
            unit = self.env['property.property'].search([('parent_building', '=', rec.building_id.id)])
            rec.unit_ids = unit.mapped('id')

    @api.depends('unit_id')
    def _compute_units(self):
        """ calculate the total units"""
        self.unit_count = 0
        for rec in self:
            rec.unit_count = len(rec.unit_id)

    def action_running(self):
        """ change the state running state """
        self.write({'state': 'running'})

    def action_expire(self):
        """ change the state Expire state """
        self.write({'state': 'expire'})

    def action_reset_draft(self):
        """ change the state Draft state """
        self.write({'state': 'draft'})

    def action_renew(self):
        """ renew the contract """
        context = {'default_name': self.name,
                   'default_partner_id': self.partner_id.id,
                   'default_building_id': self.building_id.id,
                   'default_unit_id': self.unit_id.ids,
                   'default_unit_count': self.unit_count,
                   'default_contract_categ_id': self.contract_categ_id.id,
                   'default_contract_amt': self.contract_amt,
                   'default_user_ids': self.user_ids.ids,
                   'default_company_id': self.company_id.id,
                   'default_renew_id': self.id,
                   'default_is_create_renew': True,
                   }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contract Renewal'),
            'view_mode': 'form',
            'res_model': 'aqar.contract',
            'context': context,
        }
        # contract = self.env['aqar.contract'].create({
        #     'name': self.name,
        #     'partner_id': self.partner_id.id,
        #     'building_id': self.building_id.id,
        #     'unit_id': self.unit_id.ids,
        #     'unit_count': self.unit_count,
        #     'contract_categ_id': self.contract_categ_id.id,
        #     'contract_amt': self.contract_amt,
        #     'user_ids': self.user_ids.ids,
        #     'company_id': self.company_id.id,
        #     'renew_id': self.id,
        #     'is_create_renew': True,
        # })

    def action_show_renewed(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Renewed Contract',
            'view_mode': 'tree,form',
            'res_model': 'aqar.contract',
            'domain': [('renew_id', '=', self.id)],

        }

    @api.depends('renew_id')
    def _compute_origin_renewal_count(self):
        """Compute the count of Renewed Record."""
        for rec in self:
            renewal_obj = self.env['aqar.contract'].search([('renew_id', '=', rec.id)])
            rec.renewal_count = len(renewal_obj)


    def expiry_notification_reminder(self):
        """ automatic notification reminder based on doc type"""
        doc = self.search([])
        days = []
        exp_date = 0
        for rec in doc:
            mail_sent = 0
            if rec.end_date:
                if rec.end_date == fields.Date.today():
                    rec.state = 'expire'
                for expire_days in rec.contract_categ_id.doc_expiry_before_days:
                    if mail_sent == 0:
                        if expire_days.period == 'days':
                            days = expire_days.duration
                        elif expire_days.period == 'months':
                            days = expire_days.duration * 30
                        exp_date = rec.end_date - timedelta(days=days)
                        if fields.Date.today() == rec.end_date or fields.Date.today() == exp_date:
                            if rec.contract_categ_id.email_notification:
                                mail_template = self.env.ref('aqar_contracts.contract_letter_email')
                                if mail_template:
                                    for user in rec.contract_categ_id.user_ids:
                                        template_rec = mail_template
                                        template_rec.write({'email_to': user.id})
                                        template_rec.send_mail(rec.id, force_send=True)
                                    mail_sent = 1
                            if rec.contract_categ_id.odoo_notification:
                                for user in rec.contract_categ_id.user_ids:
                                    self.env['mail.activity'].create({
                                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                        'summary': 'Contract Expiry',
                                        'date_deadline': rec.end_date,
                                        'user_id': user.id,
                                        'res_model_id': self.env['ir.model']._get_id('aqar.contract'),
                                        'res_id': rec.id,
                                    })
                                mail_sent = 1
