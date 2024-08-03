from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from lxml import etree
import json


class EvaluationType(models.Model):
    _name = 'performance.evaluation.type'
    _description = "Performance evaluation type"
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)
    is_default_type = fields.Boolean('Evaluation Type', default=True,
                                     help="This field will be true only if the evaluation.type if given by the client ie: value added throug data.xml")


class EmployeeEvaluationLine(models.Model):
    _name = 'performance.evaluation.line'
    _description = "Performance Evaluation Line"
    _rec_name = 'evaluation_type'

    performance_evaluation_id = fields.Many2one('performance.evaluation')
    evaluation_type = fields.Many2one('performance.evaluation.type', required=True)
    employee_rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('below_average', 'Below Average'),
    ], string='Employee Rating', copy=False, index=True)


class EvaluationState(models.Model):
    _name = 'performance.evaluation.state'
    _description = "Performance Evaluation State"
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)
    is_for_expat_staff = fields.Boolean('Is for expat_staff?', default=False)
    is_for_expat_labor = fields.Boolean('Is for expat_labor?', default=False)
    is_for_omani_labor = fields.Boolean('Is for omani_labor?', default=False)
    is_for_omani_staff = fields.Boolean('Is for omani_staff?', default=False)
    fold = fields.Boolean(string='Folded in Kanban',
                          help='This stage is folded in the kanban view when there are no records in that stage to display.')


class PerformanceEvaluation(models.Model):
    _name = 'performance.evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _description = "Performance Evaluation"

    def dynamic_selection(self):
        if self.env.user.has_group('atheer_hr.group_hr_site_engineer'):
            select = [('omani_labor', 'Omani Labor'), ('expat_labor', 'Expat Labor')]
        else:
            select = [('omani_staff', 'Omani Staff'), ('omani_labor', 'Omani Labor'),
                      ('expat_staff', 'Expat Staff'),
                      ('expat_labor', 'Expat Labor')]
        return select

    name = fields.Char(string='No.', required=True, default='/')
    employee_category = fields.Selection(selection=dynamic_selection, string='Employee Category')

    employee_id = fields.Many2one('hr.employee', string="Employee")
    prepared_by = fields.Many2one('hr.employee', string="Prepared By",
                                  default=lambda self: self.env.user.employee_id.id, readonly="1")
    approved_by = fields.Many2one('hr.employee', string="Approved by")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id.id)
    site_in_charge_id = fields.Many2one('hr.employee', string="Site In-Charge")

    performance_evaluation_line_ids = fields.One2many('performance.evaluation.line', 'performance_evaluation_id',
                                                      "Performance Evaluation")
    trade = fields.Many2one('hr.job', string="Designation", related='employee_id.job_id')
    prepared_by_designation = fields.Many2one('hr.job', string="Designation ", related='prepared_by.job_id')
    department_id = fields.Many2one('hr.department', string="Department ", related='employee_id.department_id')

    site_remark = fields.Text(string="Remarks by Site In-Charge")
    recommendation_remark = fields.Text(string="Remarks")
    hr_remark = fields.Text(string="HR Remarks")
    ceo_remark = fields.Text(string="CEO Remarks")
    hod_remark = fields.Text(string="HOD Remarks")
    pm_remark = fields.Text(string="Project Manager Remarks")
    approval_note = fields.Text(string="Approval Note")

    visa_expire_date = fields.Date(string="Visa Valid Up To", related='employee_id.visa_expire')
    joining_date = fields.Date(string="Joining Date", related='employee_id.joining_date')

    joining_salary = fields.Float(string="Joining Salary", related='employee_id.joining_salary')
    current_salary = fields.Float(string="Current Salary")
    create_uid = fields.Many2one('res.users', index=True)
    appraisal_for = fields.Selection([
        ('completed_probation', 'Completed probation'),
        ('visa_renewal', 'Visa renewal'),
        ('proceeding_on_leave', 'Proceeding on leave'),
        ('quarterly_appraisal', 'Quarterly appraisal'),
        ('demobilising', 'Demobilising'),
        ('general', 'General'),
    ], string='Appraisal For', copy=False)
    overall_rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('below_average', 'Below Average'),
    ], string='Overall Rating ', copy=False, index=True, tracking=True)
    recommendations = fields.Many2many('evaluation.recommendation', string="Recommendation", copy=False, index=True,
                                       tracking=True)
    state = fields.Selection([
        ('hr_one', 'HR'),
        ('hod', 'HOD'),
        ('site_engineer', 'Site Engineer'),
        ('project_manager', 'Project Manager'),
        ('hr_two', 'HR'),
        ('commerccial_head', 'Commerccial Head'),
        ('ceo', 'CEO'),
        ('approved', 'Approved'),
        ('refuse', 'Refused'),
    ], string='Status', default='hr_one', store=True, copy=False, index=True, tracking=True)
    rejected_person_id = fields.Many2one('res.users', string="Refused By")
    rejected_date = fields.Datetime(string="Refused Date")
    # access flags
    send_back_flag = fields.Boolean(default=False)
    left_se_flag = fields.Boolean(default=False)
    left_hr_flag = fields.Boolean(default=False)
    left_pm_flag = fields.Boolean(default=False)
    left_hr_two_flag = fields.Boolean(default=False)
    left_hod_flag = fields.Boolean(default=False)
    left_ch_flag = fields.Boolean(default=False)
    hod_user_id = fields.Many2one('res.users', compute='compute_hod_user_id', store=True, tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('performance.evaluation') or '/'
        return super(PerformanceEvaluation, self).create(vals)

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(PerformanceEvaluation, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                                 submenu=False)
        form_view_id = self.env.ref('atheer_hr.view_performance_evaluation_form').id
        if res.get('view_id', False) == form_view_id and res.get('type', False) == 'form':
            doc = etree.XML(res['arch'])
            if len(doc):
                if not self.env.user.has_group('atheer_hr.group_hr_manager'):
                    node = doc.xpath("//field[@name='hr_remark']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('atheer_hr.group_hr_hod'):
                    node = doc.xpath("//field[@name='hod_remark']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('atheer_hr.group_hr_site_engineer'):
                    node = doc.xpath("//field[@name='site_remark']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                if not self.env.user.has_group('atheer_hr.group_hr_ceo'):
                    node = doc.xpath("//field[@name='ceo_remark']")[0]
                    node.set("readonly", "1")
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
                    res['arch'] = etree.tostring(doc)
                return res
        return res

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        for rec in self:
            if rec.employee_id:
                if rec.employee_id.contract_id:
                    rec.current_salary = rec.employee_id.contract_id.gross_salary
                else:
                    rec.current_salary = rec.joining_salary

    @api.depends('employee_id')
    def compute_hod_user_id(self):
        for record in self:
            if record.employee_id.department_id.manager_id:
                record.hod_user_id = record.employee_id.department_id.manager_id.user_id.id
            else:
                record.hod_user_id = False

    @api.constrains('employee_category', 'employee_id')
    def check_appraisal_required(self):
        for rec in self:
            if not rec.appraisal_for:
                raise ValidationError(_('Please Choose appraisal for.'))

    @api.onchange('employee_category')
    def _onchange_employee_category(self):
        for rec in self:
            if rec.employee_category == 'expat_labor':
                rec.state = 'site_engineer'
                return {'domain': {'employee_id': [('employee_category', '=', 'expat_labor')]}}
            elif rec.employee_category == 'expat_staff':
                rec.state = 'hr_one'
                return {'domain': {'employee_id': [('employee_category', '=', 'expat_staff')]}}
            elif rec.employee_category == 'omani_staff':
                rec.state = 'hr_one'
                return {'domain': {'employee_id': [('employee_category', '=', 'omani_staff')]}}
            elif rec.employee_category == 'omani_labor':
                rec.state = 'site_engineer'
                return {'domain': {'employee_id': [('employee_category', '=', 'omani_labor')]}}

    # load all values as performance.evaluation.line in performance.evaluation
    @api.model
    def default_get(self, fields_list):
        res = super(PerformanceEvaluation, self).default_get(fields_list)
        evaluation_type_ids = self.env['performance.evaluation.type'].search([('is_default_type', '=', True)])
        vals = []
        for type in evaluation_type_ids:
            dafault_type = (0, 0, {'evaluation_type': type.id})
            vals.append(dafault_type)
        res.update({'performance_evaluation_line_ids': vals})
        return res

    def send_to_hod(self):
        for rec in self:
            rec.left_hr_flag = True
            rec.send_back_flag = False
            rec.write({'state': 'hod'})

    def send_to_project_manager(self):
        for rec in self:
            rec.left_se_flag = True
            rec.send_back_flag = False
            rec.write({'state': 'project_manager'})

    def send_to_site_engineer(self):
        for rec in self:
            rec.write({'state': 'site_engineer'})

    def send_to_hr(self):
        for rec in self:
            if rec.employee_category in ['expat_staff', 'omani_staff']:
                rec.left_hod_flag = True
                rec.send_back_flag = False
            if rec.employee_category in ['expat_labor', 'omani_labor']:
                rec.left_pm_flag = True
                rec.send_back_flag = False
            rec.write({'state': 'hr_two'})

    def send_to_ceo(self):
        for rec in self:
            rec.send_back_flag = False
            rec.write({'state': 'ceo'})

    def to_approve(self):
        '''To Do give access rights and permissions and sent notification'''
        for rec in self:
            if rec.employee_category in ['omani_staff', 'expat_staff']:
                rec.send_back_flag = False
            if rec.employee_category in ['omani_labor', 'expat_labor']:
                rec.send_back_flag = False
            rec.write({'state': 'approved'})

    def send_back(self):
        for rec in self:
            if rec.state == 'ceo':
                rec.send_back_flag = True
                rec.write({'state': 'commerccial_head'})
            elif rec.state == 'commerccial_head':
                rec.send_back_flag = True
                rec.write({'state': 'hr_two'})
            elif rec.state == 'site_engineer':
                rec.send_back_flag = True
                rec.write({'state': 'hr_one'})
            elif rec.state == 'project_manager':
                rec.send_back_flag = True
                rec.write({'state': 'site_engineer'})
            elif rec.state == 'hr_two':
                if rec.employee_category in ['expat_staff', 'omani_staff']:
                    rec.send_back_flag = True
                    rec.write({'state': 'hod'})
                if rec.employee_category in ['expat_labor', 'omani_labor']:
                    rec.send_back_flag = True
                    rec.write({'state': 'project_manager'})
            elif rec.state == 'hod':
                rec.send_back_flag = True
                rec.write({'state': 'hr_one'})

    def action_reject(self):
        for rec in self:
            refuser = str(self.env.user.name)
            rec.state = 'refuse'
            rec.rejected_person_id = self.env.user.id
            rec.rejected_date = fields.Datetime.now()

    def unlink(self):
        for record in self:
            if record.state not in ['hr_one', 'site_engineer']:
                raise UserError(
                    _('You cannot delete the performance evaluation %s in the current state.') % (record.name))
        return super(PerformanceEvaluation, self).unlink()


class EvaluationRecommendation(models.Model):
    _name = 'evaluation.recommendation'
    _description = "Performance evaluation Recommendation"

    name = fields.Char(string="Name", required=True)
