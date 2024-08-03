from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class AccidentDetails(models.Model):
    _name = 'accident.details'
    _description = 'Accident Details'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", readonly=True, copy=False, required=True, default=lambda self: _('New'))
    vehicle = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True)
    vin_sn = fields.Char('Chassis Number',
                         related="vehicle.vin_sn",
                         help='Unique number written on the vehicle motor (VIN/SN number)',
                         copy=False)
    number_plate = fields.Many2one('master.number.plate', string='Vehicle Number', tracking=True)
    km_reading = fields.Integer(string='KM Reading', tracking=True)
    accident_date = fields.Date("Accident Date")
    cash_by_employee = fields.Integer(string='Cash By Employee', tracking=True)
    cash_by_company = fields.Integer(string='Cash by Company', tracking=True)
    insurance_amount = fields.Integer(string='Insurance Claim Amount', tracking=True)
    driver = fields.Many2one('res.partner', string='Driver', tracking=True)
    company_name = fields.Many2one('res.partner', string='Repaired Company Name',
                                   help="Name of the vendor who repaired the Accident",
                                   tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    description = fields.Text(string='Accident Reason')
    vehicle_condition = fields.Text(string='Vehicle Condition')
    claim_number = fields.Char(string="Claim Number", copy=False)
    attachment_ids = fields.Many2many('ir.attachment', string="ROP Report",
                                      help='You can attach the copy of ROP document',
                                      copy=False)
    accident_image_128 = fields.Image("Accident Car", max_width=128, max_height=128)
    repair_image_128 = fields.Image("Repaired Car", max_width=128, max_height=128)
    claim_type = fields.Selection([('cash', 'Cash'), ('insurance', 'Insurance')], string='Claim Type')
    remarks = fields.Text(string='Remarks')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], string='State', default='draft', tracking=True)

    def confirm(self):
        for record in self:
            record.state = 'done'

    def reset_to_draft(self):
        self.state = 'draft'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('accident.details') or 'New'
        return super(AccidentDetails, self).create(vals_list)
