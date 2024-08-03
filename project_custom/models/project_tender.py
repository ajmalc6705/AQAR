# -*- coding: utf-8 -*-

import json
from lxml import etree
from datetime import datetime, date
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class BoqCategory(models.Model):
    _name = 'project.boq.category'
    _inherit = ['mail.thread']
    _rec_name = 'code'
    _description = 'Project Bill Of Quantities Category'

    code = fields.Char("Boq Category Code", required=True)
    name = fields.Char("Boq Category Name")
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    amount_total = fields.Monetary(string='Total Amount', copy=False)

    # From SO(for MO)
    sale_order_id = fields.Many2one('sale.order', 'Sale Order')
    finished_pdt_id = fields.Many2one('product.product', 'Product')


class BOQ(models.Model):
    _name = 'project.boq'
    _inherit = ['mail.thread']
    _rec_name = 'ref'
    _description = 'Project Bill Of Quantities'

    @api.depends('rate', 'labor_rate')
    def get_total_unit_rate(self):
        for rec in self:
            rec.total_rate = round(rec.rate + rec.labor_rate, 3)

    @api.depends('total_rate', 'quantity', 'calc_qty', 'labor_rate', 'rate')
    def get_total_amount(self):
        for rec in self:
            rec.amount_total = rec.quantity * rec.total_rate
            rec.calc_total_amount = rec.calc_qty * rec.total_rate
            rec.material_total = rec.calc_qty * rec.rate
            rec.labor_total = rec.calc_qty * rec.labor_rate

    ref = fields.Char("ref", copy=False)
    description = fields.Text(string="Description", copy=False, required=1)
    unit = fields.Char("Unit", copy=False)
    quantity = fields.Float("Quantity", copy=False)
    # boq_category = fields.Many2one(comodel_name='project.boq.category', string='Category')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    tender_id = fields.Many2one(comodel_name='project.tender', string='Tender Reference', required=1)
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    rate = fields.Monetary(string='Material Unit Rate', copy=False)
    amount_total = fields.Monetary(string='Total Amount as per BOQ Qty', copy=False,
                                   compute=get_total_amount, compute_sudo=True)

    # profit_perc = fields.Float("Profit %", copy=False, default=5)
    calc_qty = fields.Float("Calculated Quantity", copy=False)
    labor_rate = fields.Monetary(string='Labor Unit Rate', copy=False)
    sub_contract_quote = fields.Float(string="Sub Contract Quote", copy=False)
    sub_contract_disc = fields.Float(string="Sub Contract Discount (%)", copy=False)
    sub_contract_cost = fields.Float(string="Sub Contractor Costs (Major items)", copy=False)

    total_rate = fields.Float(string="Total Unit Rate", copy=False, compute=get_total_unit_rate, digits=(16, 3))
    calc_total_amount = fields.Float(string="Total Amount as per Calculated Qty", copy=False,
                                     compute=get_total_amount, compute_sudo=True)
    material_total = fields.Float(string="Material Cost Only as per Calculated Qty", copy=False,
                                  compute=get_total_amount, compute_sudo=True)
    labor_total = fields.Float(string="Labour Cost Only as per Calculated Qty", copy=False,
                               compute=get_total_amount, compute_sudo=True)
    remark = fields.Text(string="Remarks")

    @api.model_create_multi
    def create(self, vals_list):
        """

        @return:
        """
        records = super(BOQ, self).create(vals_list)
        for res in records:
            if res.tender_id and res.tender_id.state != 'draft1':
                raise UserError("BOQ Upload/Update is only allowed in QS Sections")
        return records

    def write(self, vals):
        """

        @return:
        """
        for res in self:
            if res.tender_id and res.tender_id.state != 'draft1':
                raise UserError("BOQ Upload/Update is only allowed in QS Sections")
        return super(BOQ, self).write(vals)

    def unlink(self):
        for res in self:
            if res.tender_id and res.tender_id.state != 'draft1':
                raise UserError("BOQ Upload/Update is only allowed in QS Sections")
        return super(BOQ, self).unlink()


class BOQExtended(models.Model):
    _name = 'project.extend.boq'
    _inherit = ['mail.thread']
    _rec_name = 'ref'
    _description = 'Project Bill Of Quantities'

    # @api.depends('rate', 'labor_rate', 'profit_perc')
    # def get_total_unit_rate(self):
    #     for rec in self:
    #         profit = (rec.rate + rec.labor_rate) * rec.profit_perc
    #         rec.profit = profit
    #         rec.total_rate = round(rec.rate + rec.labor_rate + profit, 3)

    # @api.depends('total_rate', 'quantity', 'calc_qty', 'labor_rate', 'rate')
    @api.depends('rate', 'quantity')
    def get_total_amount(self):
        for rec in self:
            rec.amount_total = rec.quantity * rec.rate
            # rec.calc_total_amount = rec.calc_qty * rec.total_rate
            # rec.material_total = rec.calc_qty * rec.rate
            # rec.labor_total = rec.calc_qty * rec.labor_rate

    ref = fields.Char("Ref", copy=False)
    description = fields.Text(string="Description", copy=False, required=1)

    unit = fields.Char("Unit", copy=False)
    quantity = fields.Float("Quantity", copy=False, tracking=True)

    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    boq_category = fields.Many2one(comodel_name='project.boq.category', string='Category')
    boq_type = fields.Selection([('tender', 'Tender'), ('project', 'Project')],
                                string="BOQ Type", default='tender')
    tender_id = fields.Many2one(comodel_name='project.tender', string='Tender Reference')
    project_id = fields.Many2one(comodel_name='project.project', string='Project')
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    rate = fields.Monetary(string='Unit Rate', copy=False, tracking=True)
    amount_total = fields.Monetary(string='Total Amount', copy=False,
                                   compute=get_total_amount, compute_sudo=True, store=True)

    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")

    # profit_perc = fields.Float("Profit %", copy=False, default=5)
    # calc_qty = fields.Float("Calculated Quantity", copy=False)
    # labor_rate = fields.Monetary(string='Labor Unit Rate', copy=False)
    # sub_contract_quote = fields.Float(string="Sub Contract Quote", copy=False)
    # sub_contract_disc = fields.Float(string="Sub Contract Discount (%)", copy=False)
    #
    # profit = fields.Float(string="Profit", copy=False, compute=get_total_unit_rate)
    # total_rate = fields.Float(string="Total Unit Rate", copy=False, compute=get_total_unit_rate, digits=(16, 3))
    # calc_total_amount = fields.Float(string="Total Amount as per Calculated Qty", copy=False,
    #                                  compute=get_total_amount, compute_sudo=True)
    # material_total = fields.Float(string="Material Cost Only as per Calculated Qty", copy=False,
    #                               compute=get_total_amount, compute_sudo=True)
    # labor_total = fields.Float(string="Labour Cost Only as per Calculated Qty", copy=False,
    #                            compute=get_total_amount, compute_sudo=True)
    remark = fields.Text(string="Remarks")

    # @api.model_create_multi
    # def create(self, vals_list):
    #     """
    #
    #     @return:
    #     """
    #     records = super(BOQ, self).create(vals_list)
    #     for res in records:
    #         if res.tender_id and res.tender_id.state != 'draft1':
    #             raise UserError("BOQ Upload/Update is only allowed in QS Sections")
    #     return records
    #
    # def write(self, vals):
    #     """
    #
    #     @return:
    #     """
    #     for res in self:
    #         if res.tender_id and res.tender_id.state != 'draft1':
    #             raise UserError("BOQ Upload/Update is only allowed in QS Sections")
    #     return super(BOQ, self).write(vals)
    #
    # def unlink(self):
    #     for res in self:
    #         if res.tender_id and res.tender_id.state != 'draft1':
    #             raise UserError("BOQ Upload/Update is only allowed in QS Sections")
    #     return super(BOQ, self).unlink()


class Tender(models.Model):
    _name = 'project.tender'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'tender_no'
    _description = 'Project Tender'

    def write(self, vals):
        res = super(Tender, self).write(vals)
        if vals.get('project_duration'):
            self.message_post(body="Project Duration Changed")
        if vals.get('mobilization_duration'):
            self.message_post(body="Mobilisation Duration Changed")
        if vals.get('project_buffer_amount'):
            self.message_post(body="Project Buffer Amount  Changed")
        if vals.get('manpower'):
            self.message_post(body="Manpower  Changed")
        if vals.get('project_cost'):
            self.message_post(body="Project Cost  Changed")
        if vals.get('profit_perc'):
            self.message_post(body="Profit  Changed")
        if vals.get('profit_amount'):
            self.message_post(body="Project Amount  Changed")
        if vals.get('project_total'):
            self.message_post(body="Project Total  Changed")
        self.message_subscribe([self.env.user.partner_id.id])
        return res

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', '/') == '/':
    #         vals['name'] = self.env['ir.sequence'].next_by_code('tdr') or '/'
    #     return super(Tender, self).create(vals)
    #
    # def _get_report_base_filename(self):
    #     self.ensure_one()
    #     return 'Project Tender-%s' % (self.name)

    def qs(self):
        for rec in self:
            if rec.state == 'draft':
                if not rec.foc and not rec.amount:
                    raise UserError('Tender Purchase Amount not specified !!!!')
                rec.state = 'draft1'
            elif rec.state == 'boq':
                if rec.revision and not rec.date_revision:
                    raise UserError('Revision Date not specified !!!!')
                if not rec.project_duration and not rec.mobilization_duration:
                    raise UserError('Project/Mobilization duration not specified !!!!')
                if rec.project_cost < 1:
                    raise UserError('Project Cost Not defined !!!!')
                rec.state = 'draft1'
            rec.activity_update()
            m_group = self.env.ref('project_custom.group_qs_head')
            m_partners = m_group.notify_users_ids.mapped('partner_id')
            mail_vals = {
                'subject_msg': "Waiting QS Head Approval",
                'status_msg': "waiting for QS head Approval",
                'm_partners': m_partners
            }
            rec.action_send_notification(mail_vals)

    def operations(self):
        for rec in self:
            if rec.state == 'draft1':
                if not rec.foc and not rec.amount:
                    raise UserError('Tender Purchase Amount not specified !!!!')
                if not rec.boq_count:
                    raise UserError('Please Upload BOQ !!!!')
                if rec.revision and not rec.date_revision:
                    raise UserError('Revision Date not specified !!!!')
                if not rec.project_duration and not rec.mobilization_duration:
                    raise UserError('Project/Mobilization duration not specified !!!!')
                if rec.project_cost < 1:
                    raise UserError('Project Cost !!!!')
                rec.state = 'draft2'
                rec.activity_update()
                m_group = self.env.ref('project.group_project_manager')
                m_partners = m_group.notify_users_ids.mapped('partner_id')
                mail_vals = {
                    'subject_msg': "Waiting Project Manager Approval",
                    'status_msg': "waiting for project manager Approval",
                    'm_partners': m_partners
                }
                rec.action_send_notification(mail_vals)

    def action_send_coo(self):
        for rec in self:
            rec.state = 'open'
            rec.activity_update()
            m_group = self.env.ref('atr_hr_custom.group_hr_coo')
            m_partners = m_group.notify_users_ids.mapped('partner_id')
            mail_vals = {
                'subject_msg': "Waiting COO Approval",
                'status_msg': "waiting for coo Approval",
                'm_partners': m_partners
            }
            rec.action_send_notification(mail_vals)

    def action_send_ceo(self):
        for rec in self:
            rec.state = 'validate1'
            rec.activity_update()
            m_group = self.env.ref('atr_hr_custom.group_hr_ceo')
            m_partners = m_group.notify_users_ids.mapped('partner_id')
            mail_vals = {
                'subject_msg': "Waiting CEO Approval",
                'status_msg': "waiting for ceo Approval",
                'm_partners': m_partners
            }
            rec.action_send_notification(mail_vals)

    def validate1(self):
        for rec in self:
            rec.state = 'client'
            rec.activity_update()

    def done(self):
        if self.state in ('validate1', 'validate2'):
            self.state = 'ready'
        elif self.state == 'validate22':
            self.state = 'client'

    def lost(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lost Reason of Tender - ' + str(self.tender_no)),
            'res_model': 'tender.lost.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_tender_id': self.id},
            'views': [[False, 'form']]
        }

    def won(self):
        if self.parent_tender:
            for tender in self.child_ids:
                tender.state = 'won'
            self.parent_tender.state = 'won'
            self.state = 'won'
        else:
            self.state = 'won'

    def revise(self):
        revision_count = 0
        vals = {}
        if self.parent_tender:
            vals['parent_tender'] = self.parent_tender.id
            for i in self.parent_tender.child_ids:
                revision_count += 1
            vals['tender_no'] = self.parent_tender.tender_no + "-" + "Revision" + "-" + str(revision_count + 1)
        else:
            vals['parent_tender'] = self.id
            revision_count += 1
            vals['tender_no'] = self.tender_no + "-" + "Revision" + "-" + str(revision_count)
        vals['tender_ref'] = self.tender_ref
        vals['project_buffer_amount'] = self.project_buffer_amount
        vals['extended_days'] = self.extended_days
        vals['minimum_monthly_claim'] = self.minimum_monthly_claim
        vals['tender_source_id'] = self.tender_source_id.id
        vals['work_id'] = self.work_id.id
        vals['bond_date_start'] = self.bond_date_start
        vals['bond_date_end'] = self.bond_date_end
        vals['bond_file'] = self.bond_file
        vals['bond_value'] = self.bond_value
        vals['insurance_start'] = self.insurance_start
        vals['insurance_end'] = self.insurance_end
        vals['type_contract'] = self.type_contract.id
        vals['insurance_doc'] = self.insurance_doc
        vals['advance_payment'] = self.advance_payment
        vals['manpower'] = self.manpower
        vals['payment_term_id'] = self.payment_term_id.id
        vals['tender_title'] = self.tender_title
        vals['profit_perc'] = self.profit_perc
        vals['priority'] = self.priority
        vals['project_tender_type'] = self.project_tender_type.id
        vals['sub_type'] = self.sub_type.id
        vals['location'] = self.location
        vals['analytic_account_id'] = self.analytic_account_id.id
        vals['related_rfq'] = self.related_rfq.id if self.related_rfq else None
        vals['project_cost'] = self.project_cost
        vals['client'] = self.client
        vals['date_tender'] = self.date_tender
        vals['date_collection'] = self.date_collection
        vals['date_submission'] = self.date_submission
        vals['date_receipt'] = self.date_receipt
        vals['project_duration'] = self.project_duration
        vals['mobilization_duration'] = self.mobilization_duration
        vals['foc'] = self.foc
        vals['amount'] = self.amount
        vals['payment_mode'] = self.payment_mode
        vals['date_payment'] = self.date_payment
        vals['bond'] = self.bond
        vals['description'] = self.description
        vals['revision'] = True
        vals['state'] = 'boq'
        vals['construction_team_ids'] = self.construction_team_ids.ids
        vals['aluminium_team_ids'] = self.aluminium_team_ids.ids
        vals['qs_team_ids'] = self.qs_team_ids.ids
        self.state = 'revise'
        self.revised_date = fields.date.today()
        self.revised = 'True'
        tender = self.env['project.tender'].create(vals)
        sites_data = self.env['project.site.visit'].search([('tender', '=', self.id)])
        for site in sites_data:
            self.env['project.site.visit'].create({
                'tender': tender.id,
                'landscaping': site.landscaping,
                'type': site.type,
                'date_visit': site.date_visit,
                'address': site.address,
                'site_distance': site.site_distance,
                'site_weather': site.site_weather,
                'site_access': site.site_access,
                'site_condition': site.site_condition,
                'site_adj_structure': site.site_adj_structure,
                'site_obstruction': site.site_obstruction,
                'site_presence': site.site_presence,
                'site_soil': site.site_soil,
                'site_extra': site.site_extra,
                'site_temp': site.site_temp,
                'site_rmc': site.site_rmc,
                'site_resource': site.site_resource,
                'site_camp': site.site_camp,
                'site_water': site.site_water,
                'site_elec': site.site_elec,
                'description': site.description,
                'type_contract': site.type_contract,
                'total_area': site.total_area,
                'manpower': site.manpower,
                'transport': site.transport,
                'visit_scope': site.visit_scope,
                'obstructions': site.obstructions,
                'accommodation': site.accommodation,
                'visit_details': site.visit_details,
                'project_no': site.project_no,
                'substitutes': site.substitutes,
                'machineries': site.machineries,
                'responsible_id': site.responsible_id.id,
                'contractor_id': site.contractor_id.id,
                # 'stat/e': site.state,

            })
            print(site)

    def ready(self):
        if not self.foc and not self.date_payment:
            raise UserError('Payment Date not specified')
        else:
            self.state = 'done'

    def boq(self):
        self.state = 'boq'

    def close(self):
        for rec in self:
            rec.state = 'close'
            rec.activity_update()

    def sent_back(self):
        for rec in self:
            if rec.state == 'draft1' and rec.revision:
                rec.state = 'boq'
            elif rec.state == 'draft1':
                rec.state = 'draft'
            elif rec.state == 'draft2':
                rec.state = 'draft1'
            elif rec.state == 'open':
                rec.state = 'draft2'
            elif rec.state == 'validate1':
                rec.state = 'open'
            elif rec.state == 'validate2':
                rec.state = 'validate1'
            elif rec.state in ('qs_head_1', 's_head_1'):
                rec.state = 'boq'
            elif rec.state == 'open_1' and rec.tender_type == 'construction':
                rec.state = 'qs_head_1'
            elif rec.state == 'validate11':
                rec.state = 'open_1'
            elif rec.state == 'validate22':
                rec.state = 'validate11'
            rec.activity_reset()

    def _visit_count(self):
        gate_pass = self.env['project.site.visit']
        count = gate_pass.search_count([('tender', '=', self.id)])
        self.visit_count = count

    def boq_counted(self):
        boq_pool = self.env['project.boq']
        count = boq_pool.search_count([('tender_id', '=', self.id)])
        self.boq_count = count

    def _boq_ext_count(self):
        boq_pool = self.env['project.extend.boq']
        count = boq_pool.search_count([('tender_id', '=', self.id)])
        self.boq_ext_count = count

    def return_site_visit(self):
        """ This opens the xml view specified in xml_id for the site visits """
        if self._context.get('xml_id'):
            res = self.env['ir.actions.act_window']._for_xml_id(f"project_custom.{self._context['xml_id']}")
            res['context'] = {'default_tender': self.id}
            res['domain'] = [('tender', '=', self.id)]
            return res
        else:
            return False

    @api.depends('tender_addendum')
    def latest_sub_date(self):
        latest = self.env['project.tender.addendum'].search([('tender', '=', self.id)], limit=1,
                                                            order='date_submission desc')
        self.date_submission_latest = latest.date_submission

    def get_contract_type_list(self):
        result = [('lump_sum', 'Lump Sum')]
        result += [('unit_rate', 'Unit Rate'), ('manpower_rate', 'Manpower Rate'), ('56', 'Clause 56'),
                   ('55', 'Clause 55')]
        return result

    @api.depends('boq_count')
    def get_project_cost(self):
        for rec in self:
            boq_ids = self.env['project.extend.boq'].search([('tender_id', '=', self.id)])
            if not boq_ids:
                boq_ids = self.env['project.boq'].search([('tender_id', '=', self.id)])
            project_cost = sum(boq_ids.mapped('amount_total'))
            rec.project_cost = project_cost

    @api.depends('profit_perc', 'project_cost')
    def get_project_total(self):
        for rec in self:
            project_total = 0.0
            profit_amount = 0.0
            if rec.project_cost and rec.profit_perc:
                project_total = rec.project_cost * (1 + rec.profit_perc / 100)
                profit_amount = project_total - rec.project_cost
            elif rec.project_cost:
                project_total = rec.project_cost
            rec.update({
                'project_total': project_total,
                'profit_amount': profit_amount
            })

    @api.depends('bond_value', 'project_cost')
    def get_bond_amount(self):
        for rec in self:
            bond_amount = 0.0
            if rec.project_cost and rec.bond_value:
                bond_amount = (rec.project_cost * rec.bond_value) / 100
            rec.update({
                'bond_amount': bond_amount
            })

    def open_boq(self):
        for rec in self:
            ctx = self.env.context.copy()
            action = self.env["ir.actions.act_window"]._for_xml_id('project_custom.action_project_boq')
            ctx.update({'default_tender_id': rec.id})
            action['context'] = ctx
            action['domain'] = [('tender_id', '=', rec.id)]
            return action

    def open_ext_boq(self):
        for rec in self:
            ctx = self.env.context.copy()
            action = self.env["ir.actions.act_window"]._for_xml_id('project_custom.action_project_extend_boq')
            ctx.update({'default_tender_id': rec.id})
            action['context'] = ctx
            action['domain'] = [('tender_id', '=', rec.id)]
            return action

    def open_parent(self):
        if self.parent_tender:
            domain = [('id', '=', self.parent_tender.id)]
            return {
                'type': 'ir.actions.act_window',
                'name': _('Parent Tender'),
                'res_model': 'project.tender',
                'view_mode': 'tree,form',
                'domain': domain,
            }

    # name = fields.Char('Doc. No.', required=True, copy=False)
    project = fields.One2many('project.project', 'tender', 'Project')
    tender_type = fields.Selection([('construction', 'Construction')],
                                   string='Tender Type', default='construction')
    client = fields.Char(string='Client')
    date_tender = fields.Date('Invitation Date', tracking=True)
    date_collection = fields.Date('Collection Date', tracking=True)
    date_receipt = fields.Date('Receipt Date', tracking=True)
    date_visit = fields.Date('Site Visit Date', tracking=True)
    date_submission = fields.Date('Submission Date', tracking=True)
    date_submission_latest = fields.Date('Latest Submission Date', compute='latest_sub_date')
    manpower = fields.Integer("Manpower Required", tracking=True)
    project_duration = fields.Char("Project Duration")
    mobilization_duration = fields.Char("Mobilisation Duration")
    project_cost = fields.Float("Project Cost", compute=get_project_cost)
    profit_perc = fields.Float("Profit %")
    profit_amount = fields.Float("Profit Amount", compute=get_project_total)
    project_total = fields.Float("Project Total", compute=get_project_total)
    foc = fields.Boolean('Free of Cost', tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    location = fields.Char('Tender Location', tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    priority = fields.Selection([('major', 'Major'), ('minor', 'Minor')], string='Priority', default='major')
    type = fields.Selection([('min', 'Ministry'), ('private', 'Private'), ('other', 'Others')],
                            string='Type')

    type_contract = fields.Many2one('project.tender.contract.type', string='Contract Type')
    tender_no = fields.Char('Tender No.', tracking=True, copy=False, default='/', readonly=1)
    tender_ref = fields.Char('Tender Reference', tracking=True)
    tender_title = fields.Char('Tender Title', tracking=True)
    # tender_title = fields.Char('Tender Title')
    visit_count = fields.Integer(compute='_visit_count', string="Visit")
    boq_count = fields.Integer(compute='boq_counted', string="BOQ Count")
    site_visit = fields.One2many('project.site.visit', 'tender', string='Site Visit')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Business Unit',
                                          tracking=True)
    payment_mode = fields.Selection([('cash', 'Cash'), ('bank', 'Bank'), ('debit', 'Debit Card')],
                                    string='Payment Mode', default="cash", tracking=True, readonly=True,
                                    states={'draft': [('readonly', False)]})
    amount = fields.Float('Tender Purchase Amount', tracking=True, readonly=True,
                          states={'draft': [('readonly', False)]})
    date_payment = fields.Date('Payment Date', tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    bond = fields.Boolean('Bond Required', tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    bond_value = fields.Float('Bond Value', tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    bond_amount = fields.Float('Bond Amount', compute=get_bond_amount)
    bond_validity = fields.Date('Bond Validity', readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Html('Description', tracking=True)
    date_docs = fields.Date('Date of Docs. Received', tracking=True)
    available_days = fields.Float('Working Days Available', tracking=True)
    tender_docs = fields.One2many('project.tender.collection', 'tender', string='Documents')
    tender_query = fields.One2many('project.tender.query', 'tender', string='Query')
    revised = fields.Boolean('Revised')
    revision = fields.Boolean('Revision')
    parent_tender = fields.Many2one('project.tender', 'Parent Tender')
    date_revision = fields.Date('Revision Date', tracking=True)
    revised_date = fields.Date('Revised Date', tracking=True)
    child_ids = fields.One2many('project.tender', 'parent_tender', 'Revisions')
    location_ids = fields.One2many('project.tender.location', 'tender_id', 'Locations')
    tender_addendum = fields.One2many('project.tender.addendum', 'tender', string='Addendums & Circular')
    competitor_ids = fields.One2many('project.tender.competitor', 'tender', string='Competitor Details')
    state = fields.Selection([('draft', 'Draft'),
                              ('draft1', 'With QS Head'),
                              ('draft2', 'With Projects Manager'),
                              ('open', 'With COO'),
                              ('validate1', 'With CEO'),
                              # ('validate2', 'With CEO'),
                              # ('ready', 'Tender Approved'),
                              # ('done', 'Tender Purchased'),
                              ('boq', 'BOQ'),
                              # ('qs_head_1', 'With QS Head'),
                              # ('s_head_1', 'With Section Head'),
                              # ('open_1', 'With HOD'),
                              # ('validate11', 'With COO'),
                              # ('validate22', 'With CEO'),
                              ('client', 'Waiting For Results'),
                              ('revise', 'Revised'),
                              ('won', 'Tender Awarded'), ('close', 'Tender Lost'), ('cancel', 'Cancelled')],
                             'Status', required=True, tracking=True, copy=False, default='draft')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    boq_ids = fields.One2many('project.boq', 'tender_id', string="Tender BOQ's")
    tender_source_id = fields.Many2one('project.tender.source', string="Tender source", tracking=True)
    work_id = fields.Many2one('project.tender.work.type', string="Type Of work", tracking=True)
    project_tender_type = fields.Many2one('project.tender.type', string='Project Tender Type', tracking=True)
    sub_type = fields.Many2one('project.tender.subtype', string='Sub Type', tracking=True)
    extended_days = fields.Char(string="Extended days", tracking=True)
    bond_date_start = fields.Date('Bond Start Date', tracking=True, readonly=True,
                                  states={'draft': [('readonly', False)]})
    bond_date_end = fields.Date('Bond End Date', tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    bond_file = fields.Binary('Bond Document', readonly=True, states={'draft': [('readonly', False)]})
    insurance_start = fields.Date("Insurance Start Date", tracking=True, readonly=True,
                                  states={'draft': [('readonly', False)]})
    insurance_end = fields.Date("Insurance End Date", tracking=True, readonly=True,
                                states={'draft': [('readonly', False)]})
    insurance_doc = fields.Binary("Insurance Document", tracking=True, readonly=True,
                                  states={'draft': [('readonly', False)]})
    advance_payment = fields.Float(string="Advance Payment", tracking=True)
    construction_team_ids = fields.Many2many('res.users',
                                             'tender_construction_team_rel',
                                             'tender_id', 'user_id', string="Construction Team")
    aluminium_team_ids = fields.Many2many('res.users',
                                          'tender_aluminiumteam_rel',
                                          'tender_id', 'user_id', string="Aluminium Team")
    qs_team_ids = fields.Many2many('res.users',
                                   'tender_qs_team_rel',
                                   'tender_id', 'user_id', string="QS Team")
    lost_reason = fields.Text(string="Lost Reason", tracking=True)
    minimum_monthly_claim = fields.Float(string="Minimum Monthly Claim", tracking=True)
    project_buffer_amount = fields.Float(string="Project Buffer Amount  %")
    related_rfq = fields.Many2one('purchase.order', string="Related RFQ", tracking=True)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', tracking=True)
    tender_docs_revised = fields.One2many('project.tender.collection.revised', 'tender', string='Revised Documents')
    extended_boq_ids = fields.One2many('project.extend.boq', 'tender_id', string="Extended Tender BOQ's")
    boq_ext_count = fields.Integer(compute='_boq_ext_count', string="BOQ Count (Extended)")
    challenge_ids = fields.One2many('project.tender.challenge', 'tender_id', string="Challenges", readonly=False,
                                    states={'won': [('readonly', True)], 'close': [('readonly', True)],
                                            'revise': [('readonly', True)], 'cancel': [('readonly', True)]})
    # mrf_count = fields.Integer(string='MRF', compute='compute_mrf_count')
    #
    # def compute_mrf_count(self):
    #     inv_lines = self.env['mr']
    #     count = inv_lines.search_count([('project_tender_id', '=', self.id)])
    #     self.mrf_count = count

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(Tender, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=False)
        if view_type == 'form':
            root = etree.fromstring(res['arch'])
            if root is not None and not self.env.user.has_group('atr_hr_custom.group_hr_ceo'):
                node = root.xpath("//field[@name='profit_perc']")[0]
                node.set("readonly", "1")
                modifiers = json.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set("modifiers", json.dumps(modifiers))
                res['arch'] = etree.tostring(root)
        return res

    def return_mrf(self):
        if self._context.get('xml_id'):
            ctx = dict(self.env.context, default_project_tender_id=self.id)
            res = self.env['ir.actions.act_window']._for_xml_id('project_custom.open_mr_form')
            ctx.update(default_type='cons', group_by=False)
            res['domain'] = [('project_tender_id', '=', self.id)]
            res['context'] = ctx
            return res
        return False

    # @api.onchange('project_duration')
    # @api.constrains('project_duration')
    # def update_project_duration(self):
    #     if self.project_duration:
    #         self.message_post(body="cahnged %s Refused." % self.project_duration,
    #                             subtype_xmlid="mail.mt_comment",
    #                             message_type="comment")
    #     else:
    #         return False
            # if record.project_duration:
            #     return record.message_post(body="JJJJJJJJJJJJJJJJJJJJj")

    @api.onchange('qs_team_ids')
    def get_qs_team_ids(self):
        for user in self.qs_team_ids:
            if user._origin.partner_id.id not in self.message_partner_ids.ids:
                self.message_subscribe([user._origin.partner_id.id])

    @api.onchange('construction_team_ids')
    def getconstruction_team_ids(self):
        for user in self.construction_team_ids:
            if user._origin.partner_id.id not in self.message_partner_ids.ids:
                self.message_subscribe([user._origin.partner_id.id])

    @api.onchange('aluminium_team_ids')
    def get_aluminium_team_ids(self):
        for user in self.aluminium_team_ids:
            if user._origin.partner_id.id not in self.message_partner_ids.ids:
                self.message_subscribe([user._origin.partner_id.id])

    # def copy(self, default=None):
    #     raise UserError("Duplication Restricted")

    @api.model
    def create(self, vals):
        if vals.get('tender_no', '/') == '/':
            vals['tender_no'] = self.env['ir.sequence'].next_by_code('tnd') or '/'
        return super(Tender, self).create(vals)

    def tender_submission_reminder(self):
        """
        cron job to set reminder for tender submission
        :return: None
        """
        for tender in self.search([('state', 'in', ['draft', 'draft1', 'draft2', 'open', 'validate1','boq']),
                                   ('date_submission', '>', fields.Date.today())]):
            delta = tender.date_submission - fields.Date.today()
            if delta.days == 7:
                tender.activity_schedule(
                    'project_custom.mail_activity_tender_submission', tender.date_submission,
                    _("Only 7 Days left to Submit the tender."),
                    user_id=tender.create_uid.id)
            elif delta.days == 15:
                tender.activity_schedule(
                    'project_custom.mail_activity_tender_submission', tender.date_submission,
                    _("Only 15 Days left to Submit the tender."),
                    user_id=tender.create_uid.id)
            else:
                pass

    def _get_responsible_for_approval(self):
        for rec in self:
            if rec.state == 'draft1':
                group = self.env.ref('project_custom.group_qs_head').notify_users_ids
            elif rec.state == 'draft2':
                group = self.env.ref('project.group_project_manager').notify_users_ids
            elif rec.state == 'open':
                group = self.env.ref('atr_hr_custom.group_hr_coo').notify_users_ids
            elif rec.state == 'validate1':
                group = self.env.ref('atr_hr_custom.group_hr_ceo').notify_users_ids
            else:
                group = self.env.ref('project.group_project_manager').notify_users_ids
            return group.ids

    def activity_update(self):
        to_clean, to_do = self.env['project.tender'], self.env['project.tender']
        for rec in self:
            responsible_users = rec.sudo()._get_responsible_for_approval()
            note = _(
                'New Project Tender with collection start date on %(collect_date)s is created by %(user)s',
                user=rec.create_uid.name,
                collect_date=rec.date_collection
            )
            if rec.state in ('draft', 'boq'):
                to_clean |= rec
            elif rec.state == 'draft1':
                if responsible_users:
                    for responsible_user in responsible_users:
                        rec.activity_schedule(
                            'project_custom.mail_act_tender_qs_approval',
                            note=note,
                            user_id=responsible_user)
                else:
                    rec.activity_schedule(
                        'project_custom.mail_act_tender_qs_approval',
                        note=note,
                        user_id=self.env.user.id)
            elif rec.state == 'draft2':
                rec.activity_feedback(['project_custom.mail_act_tender_qs_approval'])
                if responsible_users:
                    for responsible_user in responsible_users:
                        rec.activity_schedule(
                            'project_custom.mail_act_tender_pm_approval',
                            note=note,
                            user_id=responsible_user)
                else:
                    rec.activity_schedule(
                        'project_custom.mail_act_tender_pm_approval',
                        note=note,
                        user_id=self.env.user.id)
            elif rec.state == 'open':
                rec.activity_feedback(['project_custom.mail_act_tender_pm_approval'])
                if responsible_users:
                    for responsible_user in responsible_users:
                        rec.activity_schedule(
                            'project_custom.mail_act_tender_coo_approval',
                            note=note,
                            user_id=responsible_user)
                else:
                    rec.activity_schedule(
                        'project_custom.mail_act_tender_coo_approval',
                        note=note,
                        user_id=self.env.user.id)
            elif rec.state == 'validate1':
                rec.activity_feedback(['project_custom.mail_act_tender_coo_approval'])
                if responsible_users:
                    for responsible_user in responsible_users:
                        rec.activity_schedule(
                            'project_custom.mail_act_tender_ceo_approval',
                            note=note,
                            user_id=responsible_user)
                else:
                    rec.activity_schedule(
                        'project_custom.mail_act_tender_ceo_approval',
                        note=note,
                        user_id=self.env.user.id)
            elif rec.state in ('client', 'close'):
                rec.activity_feedback(['project_custom.mail_act_tender_ceo_approval'])
        if to_clean:
            to_clean.activity_unlink(['project_custom.mail_act_tender_qs_approval',
                                      'project_custom.mail_act_tender_pm_approval',
                                      'project_custom.mail_act_tender_coo_approval',
                                      'project_custom.mail_act_tender_ceo_approval'])
        if to_do:
            to_clean.activity_feedback(['project_custom.mail_act_tender_qs_approval',
                                        'project_custom.mail_act_tender_pm_approval',
                                        'project_custom.mail_act_tender_coo_approval',
                                        'project_custom.mail_act_tender_ceo_approval'])

    def activity_reset(self):
        for rec in self:
            responsible_users = rec.sudo()._get_responsible_for_approval()
            note = _(
                'New Project Tender with collection start date on %(collect_date)s is created by %(user)s',
                user=rec.create_uid.name,
                collect_date=rec.date_collection
            )
            if rec.state in ('draft', 'boq'):
                rec.activity_unlink(['project_custom.mail_act_tender_qs_approval',
                                     'project_custom.mail_act_tender_pm_approval',
                                     'project_custom.mail_act_tender_coo_approval',
                                     'project_custom.mail_act_tender_ceo_approval'])
            elif rec.state == 'draft1':
                if responsible_users:
                    for responsible_user in responsible_users:
                        rec.activity_schedule(
                            'project_custom.mail_act_tender_qs_approval',
                            note=note,
                            user_id=responsible_user)
                else:
                    rec.activity_schedule(
                        'project_custom.mail_act_tender_qs_approval',
                        note=note,
                        user_id=self.env.user.id)
                rec.activity_unlink(['project_custom.mail_act_tender_pm_approval',
                                     'project_custom.mail_act_tender_coo_approval',
                                     'project_custom.mail_act_tender_ceo_approval'])
            elif rec.state == 'draft2':
                if responsible_users:
                    for responsible_user in responsible_users:
                        rec.activity_schedule(
                            'project_custom.mail_act_tender_pm_approval',
                            note=note,
                            user_id=responsible_user)
                else:
                    rec.activity_schedule(
                        'project_custom.mail_act_tender_pm_approval',
                        note=note,
                        user_id=self.env.user.id)
                rec.activity_unlink(['project_custom.mail_act_tender_coo_approval',
                                     'project_custom.mail_act_tender_ceo_approval'])
            elif rec.state == 'open':
                if responsible_users:
                    for responsible_user in responsible_users:
                        rec.activity_schedule(
                            'project_custom.mail_act_tender_coo_approval',
                            note=note,
                            user_id=responsible_user)
                else:
                    rec.activity_schedule(
                        'project_custom.mail_act_tender_coo_approval',
                        note=note,
                        user_id=self.env.user.id)
                rec.activity_unlink(['project_custom.mail_act_tender_ceo_approval'])

    def action_send_notification(self, vals):
        for rec in self:
            subject_msg = vals['subject_msg']
            status_msg = vals['status_msg']
            m_partners = vals['m_partners']
            company_id = self.env.user.company_id
            req_type = "Project Tender"
            action = self.env.ref('project_custom.open_tender_form')
            subject = req_type + ' ' + subject_msg
            portal_link = "%s/?db=%s#id=%s&action=%s&view_type=form" % (
                self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                self.env.cr.dbname,
                rec.id, action.id)
            body_html = """
            Hi,
            <br><br>
            <p>%s <a href="%s">%s</a> is %s.<p>
            """ % (req_type, portal_link, rec.tender_no, status_msg)
            mail_id = self.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body_html,
                'email_from': company_id.partner_id.email_formatted if company_id else self.env.user.email_formatted,
                'partner_ids': [(4, m_partner) for m_partner in m_partners.ids],
                'model': 'project.tender',
                'res_id': rec.id
            })
            mail_id.sudo().send()


class TenderDocCollection(models.Model):
    _name = 'project.tender.collection'
    _description = 'For Tender Documents'

    tender = fields.Many2one('project.tender', string="Tender")
    date_collection = fields.Date('Collection Date', required=True)
    description = fields.Char('Document Description', required=True)
    attachment = fields.Binary('Document')
    attach_name = fields.Char('Document Name')
    remarks = fields.Char('Remarks')


class TenderDocCollectionRevised(models.Model):
    _name = 'project.tender.collection.revised'
    _description = 'For Tender Documents'

    tender = fields.Many2one('project.tender')
    date_collection = fields.Date('Collection Date', required=True)
    description = fields.Char('Document Description', required=True)
    attachment = fields.Binary('Document')
    attach_name = fields.Char('Document Name')
    remarks = fields.Char('Remarks')


class TenderQuery(models.Model):
    _name = 'project.tender.query'
    _description = 'For Tender Query'

    tender = fields.Many2one('project.tender')
    date = fields.Date('Date', required=True)
    description = fields.Char('Query', required=True)
    attachment = fields.Binary('Document')
    attach_name = fields.Char('Document Name')
    reply_date = fields.Date('Reply Date')
    attachment_reply = fields.Binary('Reply Doc.')
    attach_reply_name = fields.Char('Reply Document Name')


class TenderAddendum(models.Model):
    _name = 'project.tender.addendum'
    _description = 'For Tender Addendums'

    tender = fields.Many2one('project.tender')
    sl_no = fields.Integer('SL.No.')
    date = fields.Date('Date', required=True)
    description = fields.Char('Addendum & Circular', required=True)
    date_submission = fields.Date('Revised Submission Date')
    attachment = fields.Binary('Document')
    attach_name = fields.Char('Document Name')
    remarks = fields.Char('Remarks')


class TenderCompetitor(models.Model):
    _name = 'project.tender.competitor'
    _description = 'Tender Competitor'

    tender = fields.Many2one('project.tender')
    company_name = fields.Char('Company Name')
    value = fields.Char('Value')
    position = fields.Char('Position')


class TenderSiteVisit(models.Model):
    _name = 'project.site.visit'
    _inherit = ['mail.thread']
    _description = 'Project Site Visit'

    def verify(self):
        self.state = 'open'

    def close(self):
        self.state = 'close'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_send_sh(self):
        for rec in self:
            rec.state = 'section_head'

    name = fields.Char('Doc. No.', required=True, copy=False, default='/')
    landscaping = fields.Boolean('Landscaping')
    type = fields.Selection([('tender', 'Tender'), ('project', 'Project')], 'Type', default='project')
    tender = fields.Many2one('project.tender', 'Tender')
    project = fields.Many2one('project.project', 'Project', readonly=True, states={'draft': [('readonly', False)]})
    date_visit = fields.Date('Site Visit Date', readonly=True, states={'draft': [('readonly', False)]})
    address = fields.Text('Address', required=True)
    site_distance = fields.Char('Distance From Muscat')
    site_weather = fields.Text('General Weather Conditions')
    site_access = fields.Text('Access Road to Site')
    site_condition = fields.Text('Site Condition')
    site_adj_structure = fields.Text('Adjacent Structures')
    site_obstruction = fields.Text('Site Obstruction')
    site_presence = fields.Text(
        "Presence of Sub Structure / Underground Utilities and its location and Requirement of Relocation")
    site_soil = fields.Text('Soil Data')
    site_extra = fields.Text('Work in Security Area (Additional Requirements)')
    site_temp = fields.Text('Temporary Fencing Requirements')
    site_rmc = fields.Text('Availability  of RMC Plant and Distance from Site')
    site_resource = fields.Text('Availability of Other Resources (Vendor/Subcontractors)')
    site_camp = fields.Text('Availability and Location Land for Labour Camp, Site Office & Store')
    site_water = fields.Text('Water available, Nearest Tapping Point and Approx. Distance from Site')
    site_elec = fields.Text('Electricity available, Nearest Tapping Point and Approx. Distance from Site')
    description = fields.Text('Other Comments')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    state = fields.Selection([('draft', 'Draft'), ('section_head', 'Section Head'),
                              ('open', 'Waiting Validation'), ('close', 'Verified'),
                              ('done', 'Done')], 'Status',
                             required=True, default='draft',
                             copy=False, tracking=True)
    # Extra fields for L&C
    is_section_head = fields.Boolean(string='Is Section Head', default=False, compute='get_user_access')
    type_contract = fields.Selection(selection=[('lump_sum', 'Lump Sum'),
                                                ('unit_rate', 'Unit Rate'),
                                                ('manpower_rate', 'Manpower Rate')], string='Type Of Contract')
    total_area = fields.Float(string='Total Area')
    manpower = fields.Integer(string='Manpower Required')
    responsible_id = fields.Many2one('hr.employee', string='Conduct By')
    contractor_id = fields.Many2one('hr.employee', string='Contractor')
    project_no = fields.Char(string='Project No')
    visit_details = fields.Text(string='Report Details')
    visit_scope = fields.Text(string='Brief Scope')
    transport = fields.Text(string='Transport')
    accommodation = fields.Text(string='Accommodation')
    obstructions = fields.Text(string='Obstructions')
    machineries = fields.Text(string='Machineries')
    substitutes = fields.Text(string='Substitutes')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('cl') or '/'
        return super(TenderSiteVisit, self).create(vals)

    @api.depends()
    def get_user_access(self):
        for rec in self:
            is_section_head = False
            if self._uid in (1, 2) or self.user_has_groups('project_custom.group_lnc_head'):
                is_section_head = True
            rec.update({
                'is_section_head': is_section_head
            })


class TenderLocation(models.Model):
    _name = 'project.tender.location'
    _description = 'Project Tender Location'

    @api.depends('employee_ids')
    def _get_location_manpower(self):
        for rec in self:
            rec.current_manpower = len(rec.employee_ids)

    def set_employee_gp_details(self):
        for rec in self:
            emp_with_gp = []
            emp_with_out_gp = []
            for emp in rec.employee_ids:
                gate_pass = self.env['project.gatepass.list'].search([
                    ('employee_id', '=', emp.id), ('pass_date_start', '<=', fields.Date.today()),
                    ('pass_date_end', '>=', fields.Date.today()),
                    ('state', '=', 'confirm'), ('location_ids', 'in', [rec.id])])
                if gate_pass:
                    emp_with_gp.append(emp.id)
                else:
                    emp_with_out_gp.append(emp.id)
            rec.update({
                'emp_with_gp': [(6, 0, emp_with_gp)],
                'emp_with_out_gp': [(6, 0, emp_with_out_gp)],
            })

    @api.depends('emp_on_leave_count', 'current_manpower')
    def get_manpower_available(self):
        for rec in self:
            rec.manpower_available = rec.current_manpower - rec.emp_on_leave_count

    def get_employees_on_leave(self):
        for rec in self.search([]):
            rec.get_employee_leaves()

    def get_employee_leaves(self):
        for rec in self:
            leaves = self.env['hr.leave'].search([('employee_id', 'in', rec.employee_ids.ids),
                                                  ('state', '=', 'validate')])
            employees = leaves.filtered(
                lambda x: fields.Date.from_string(x.date_from) <= date.today() <= fields.Date.from_string(x.date_to)). \
                mapped('employee_id')
            rec.emp_on_leave = employees
            rec.emp_on_leave_count = len(set(employees))

    @api.depends('employee_ids')
    def get_leave_history(self):
        for rec in self:
            leaves = self.env['hr.leave'].search([('employee_id', 'in', rec.employee_ids.ids),
                                                  ('date_to', '>=', fields.Datetime.now()),
                                                  ('state', '=', 'validate')])
            rec.leave_history = leaves

    def get_transfer_history(self):
        for rec in self:
            transfers = self.env['manpower.transfer'].search([('state', '=', 'confirmed')]).filtered(
                lambda x: x.location_from.id == rec.id or x.location_to.id == rec.id).mapped('employees_to')
            rec.transfer_history = transfers

    @api.constrains('employee_ids')
    def check_employee_allocated(self):
        for rec in self:
            allocated = self.env['project.project'].search(
                [('state', 'not in', ('cancelled', 'close'))]).mapped('tender.location_ids'). \
                filtered(lambda x: x.id != rec.id). \
                mapped('employee_ids').ids
            location_employees = rec.employee_ids.ids
            if len(list(set(location_employees) & set(allocated))) > 0:
                raise UserError(_("Employee Already allocated for project"))

    @api.onchange('employee_ids')
    def onchange_check_employee_allocated(self):
        allocated = []
        locations = self.env['project.project'].search(
            [('state', 'not in', ('cancelled', 'close'))]).mapped('tender.location_ids')
        for loc in locations:
            if type(loc.id) == int and loc.id != self._origin.id:
                allocated.extend(loc.mapped('employee_ids').ids)
        location_employees = self.employee_ids.ids
        if len(list(set(location_employees) & set(allocated))) > 0:
            raise UserError(_("Employee Already allocated for project"))

    def get_create_date(self):
        for rec in self:
            rec.date_create = fields.Datetime.from_string(rec.create_date).date() if rec.create_date else False

    name = fields.Char(string='Location', required=True)
    manpower = fields.Integer(string='Manpower Required')
    date_create = fields.Date(string='Create Date', compute=get_create_date)
    employee_ids = fields.Many2many('hr.employee', 'loc_employee_rel', 'location_id', 'employee_id',
                                    string='Employees')
    emp_with_gp = fields.Many2many('hr.employee', 'loc_employee_with_gp_rel', 'location_id', 'employee_id',
                                   string='Employees with Gate Pass', compute=set_employee_gp_details)
    emp_with_out_gp = fields.Many2many('hr.employee', 'loc_employee_with_out_gp_rel', 'location_id', 'employee_id',
                                       string='Employees without Gate Pass', compute=set_employee_gp_details)
    current_manpower = fields.Integer(string='Manpower Allocated', compute=_get_location_manpower)
    tender_id = fields.Many2one('project.tender', string='Tender')
    project_id = fields.Many2one('project.project', string='Project')
    transfer_history = fields.Many2many('manpower.transfer.line', compute=get_transfer_history)
    leave_history = fields.One2many('hr.leave', 'location_id', compute=get_leave_history, store=True)
    emp_on_leave = fields.Many2many('hr.employee', string='Employees on Leave', compute=get_employee_leaves)
    emp_on_leave_count = fields.Integer(string='Employees on Leave Count', compute=get_employee_leaves)
    manpower_available = fields.Integer(string='Manpower Available', compute=get_manpower_available)
    toggle_employee_visibility = fields.Boolean(string='Toggle Employees', default=False, copy=False)

    def toggle_employee(self):
        for record in self:
            if record.toggle_employee_visibility:
                record.toggle_employee_visibility = False
            else:
                record.toggle_employee_visibility = True

    def update_employee_exit(self):
        for rec in self:
            exit_emp_ids = rec.exit_ids.filtered(
                lambda x: x.state == 'approve' and x.last_day_of_work < fields.Date.today()).mapped('employee_id')
            if exit_emp_ids:
                rec.update({
                    'employee_ids': [(5, exit_emp_ids.ids)]
                })

    def name_get(self):
        if self._context.get('lnc'):
            res = []
            for loc in self:
                if loc.project_id:
                    res.append((loc.id, loc.project_id.sudo().name + '/' + loc.name))
                elif loc.tender_id and loc.tender_id.project:
                    res.append((loc.id, loc.tender_id.project.sudo().name + '/' + loc.name))
            return res
        else:
            return super(TenderLocation, self).name_get()

    @api.model
    def create(self, values):
        """extending the create method to update the emp master with current location of the emp"""
        result = super(TenderLocation, self).create(values)
        if values.get('employee_ids', False):
            emp_ids = self.env['hr.employee'].search([('id', 'in', values.get('employee_ids', False)[0][2])])
            for emp in emp_ids:
                emp.current_project_id = result.project_id
                emp.current_location_id = result.id
        return result

    def write(self, values):
        """extending the write method to update the emp master with current location of the emp"""
        for record in self:
            if values.get('employee_ids', False):
                newemp = values.get('employee_ids', False)[0][2]
                old_emp = [e.id for e in record.employee_ids]
                new_emp = [item for item in newemp if item not in old_emp]
                d_emp1 = [item for item in old_emp if item not in newemp]
                ch_emp = new_emp + d_emp1
                emp_ids = self.env['hr.employee'].search([('id', 'in', ch_emp)])
                for c_m in ch_emp:
                    if c_m not in old_emp:
                        for emp in emp_ids:
                            emp.current_project_id = record.project_id
                            emp.current_location_id = record.id
                    elif c_m not in newemp:
                        self._cr.execute("UPDATE hr_employee SET current_project_id=NULL WHERE id = {0}".format(
                            c_m))
                        self._cr.execute("UPDATE hr_employee SET current_location_id=NULL WHERE id = {0}".format(
                            c_m))
        return super(TenderLocation, self).write(values)


class TenderType(models.Model):
    _name = 'project.tender.type'
    _rec_name = 'name'
    _description = 'Tender Type'

    name = fields.Char(string="Type")


class TenderSubType(models.Model):
    _name = 'project.tender.subtype'
    _rec_name = 'name'
    _description = 'Tender Sub Type'

    name = fields.Char(string="Type")


class TenderSource(models.Model):
    _name = 'project.tender.source'
    _rec_name = 'name'
    _description = 'Tender Source'

    name = fields.Char(string="Name")


class TypeOfWork(models.Model):
    _name = 'project.tender.work.type'
    _rec_name = 'name'
    _description = 'Type Of Work'

    name = fields.Char(string="Name")


class ContractType(models.Model):
    _name = 'project.tender.contract.type'
    _rec_name = 'name'
    _description = 'Contract Type'

    name = fields.Char(string="Name")


# class Mr(models.Model):
#     _inherit = 'mr'
#
#     project_tender_id = fields.Many2one('project.tender', string="Project Tender")
#
#
# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'
#
#     project_tender_id = fields.Many2one('project.tender', string="Project Tender", related='mrf_id.project_tender_id')
#
#
# class PurchaseReq(models.Model):
#     _inherit = 'purchase.requisition'
#
#     project_tender_id = fields.Many2one('project.tender', string="Project Tender", related='mrf_id.project_tender_id')




