from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class FleetRequest(models.Model):
    _name = 'fleet.request'
    _description = 'Fleet Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", readonly=True, copy=False, required=True, default=lambda self: _('New'))
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True)
    odometer_id = fields.Many2one('fleet.vehicle.odometer', string="Odometer", tracking=True)
    return_odometer_id = fields.Many2one('fleet.vehicle.odometer', string="Return Odometer", tracking=True)
    odometer_reading = fields.Integer(string='Odometer Reading', tracking=True)
    odometer_reading_return = fields.Integer(string='Return Odometer Reading', tracking=True)
    requested_by = fields.Many2one('res.partner', string='Requested By', tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today())
    date_from = fields.Datetime(string='Date From', tracking=True)
    date_to = fields.Datetime(string='Date To', tracking=True)
    actual_return_date = fields.Datetime(string='Actual Return Date', )
    number_plate = fields.Many2one('master.number.plate', related="vehicle_id.number_plate", string='Vehicle Number',
                                   tracking=True)
    vin_sn = fields.Char('Chassis Number',
                         related="vehicle_id.vin_sn",
                         help='Unique number written on the vehicle motor (VIN/SN number)',
                         copy=False)
    is_chargeable = fields.Selection([('yes', 'Yes'),
                                      ('no', 'No')], 'IS Chargeable', default='no', )
    amount = fields.Float(string='Amount', tracking=True, digits=(12, 3))
    remarks = fields.Text(string='Remarks')
    return_date = fields.Date(string='Return Date', tracking=True)
    condition = fields.Selection([('good', 'Good'),
                                  ('average', 'Average'),
                                  ('bad', 'Bad')], string='Condition')
    return_remark = fields.Text(string='Return Remarks')
    inspected_by = fields.Many2one('res.partner', string='Inspected By', tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('returned', 'Returned')], string='State',
                             default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def reset_to_draft(self):
        for record in self:
            self.state = 'draft'

    def confirm(self):
        for record in self:
            record.actual_return_date = record.date_to
            if record.is_chargeable == 'yes':
                if record.amount <= 0:
                    raise ValidationError(_('The Amount Should Greater than Zero.'))
            if not record.odometer_reading:
                raise ValidationError(_('Emptying the odometer value of a vehicle is not allowed.'))
            if not record.odometer_id:
                odometer = self.env['fleet.vehicle.odometer'].create({
                    'value': record.odometer_reading,
                    'date': record.date_from or fields.Date.context_today(record),
                    'vehicle_id': record.vehicle_id.id
                })
                record.odometer_id = odometer
            else:
                record.odometer_id.value = record.odometer_reading
                record.odometer_id.date = record.date_from
                record.odometer_id.vehicle_id = record.vehicle_id.id

        self.state = 'confirmed'

    def returned(self):
        for record in self:
            if not record.odometer_reading_return:
                raise ValidationError(_('Emptying the Return odometer value of a vehicle is not allowed.'))
            if not record.return_odometer_id:
                odometer = self.env['fleet.vehicle.odometer'].create({
                    'value': record.odometer_reading_return,
                    'date': record.actual_return_date or fields.Date.context_today(record),
                    'vehicle_id': record.vehicle_id.id
                })
                record.return_odometer_id = odometer
            else:
                record.return_odometer_id.value = record.odometer_reading
                record.return_odometer_id.date = record.inspection_date
                record.return_odometer_id.vehicle_id = record.vehicle_id.id

        self.state = 'returned'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.request') or 'New'
        return super(FleetRequest, self).create(vals_list)
