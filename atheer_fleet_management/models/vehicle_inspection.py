from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class VehicleInspection(models.Model):
    _name = 'vehicle.inspection'
    _description = 'Vehicle Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", readonly=True, copy=False, required=True, default=lambda self: _('New'))
    vehicle = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True)
    odometer_reading = fields.Integer(string='Odometer Reading', tracking=True)
    odometer_id = fields.Many2one('fleet.vehicle.odometer', string="Odometer", tracking=True)
    images = fields.Binary(string='Images')
    inspection_date = fields.Date(string='Date', tracking=True)
    inspected_by = fields.Many2one('res.partner', string='Inspected By', required=True, tracking=True)
    driver = fields.Many2one('res.partner', string='Driver', tracking=True)
    description = fields.Text(string='Inspection Details')
    condition = fields.Selection([('good', 'Good'), ('average', 'Average'), ('bad', 'Bad')], string='Condition')
    remarks = fields.Text(string='Remarks')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], string='State', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def confirm(self):
        for record in self:
            record.state = 'done'
            if not record.odometer_reading:
                raise ValidationError(_('Emptying the odometer value of a vehicle is not allowed.'))
            if not record.odometer_id:
                odometer = self.env['fleet.vehicle.odometer'].create({
                    'value': record.odometer_reading,
                    'date': record.inspection_date or fields.Date.context_today(record),
                    'vehicle_id': record.vehicle.id
                })
                record.odometer_id = odometer
            else:
                record.odometer_id.value = record.odometer_reading
                record.odometer_id.date = record.inspection_date
                record.odometer_id.vehicle_id = record.vehicle.id

    def reset_to_draft(self):
        self.state = 'draft'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vehicle.inception') or 'New'
        return super(VehicleInspection, self).create(vals_list)
