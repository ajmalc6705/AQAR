# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertyPlot(models.Model):
    _name = 'property.plot'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Plot'

    plot_no = fields.Char(string='Plot No', help='sequence of the plot', copy=False,
                          readonly=True,
                          index=True, )
    name = fields.Char(string='Name')
    purchase_date = fields.Date(string='Purchase Date')
    address = fields.Char(string='Address')
    krooki_number = fields.Char(string="Krooki Number")
    land_usage_purpose = fields.Selection([('agriculture', 'Agriculture'),
                                           ('commercial', 'Commercial'),
                                           ('government', 'Government'),
                                           ('industrial', 'Industrial'),
                                           ('residential', 'Residential'),
                                           ('residential_commercial', 'Residential & Commercial')],
                                          'Purpose of Land Usage')
    plot_area = fields.Float(string='Plot Area', help='SqM', digits=(12, 3))
    plot_category_id = fields.Many2one('plot.category', string='Plot Category', help='Purpose of Land Usage')
    mulkiya_no = fields.Char(string='Mulkiya Number')
    owner_id = fields.Many2one('res.partner', string='Owner')
    phase_no = fields.Char(string='Phase No')
    block_no = fields.Char(string='Block No')
    williyat = fields.Char(string='Williyat')
    no_of_allowed_floors = fields.Integer(string='No of Allowed Floors')
    plot_type = fields.Selection([('own', 'Owned'), ('lease', 'Lease'), ('third_party', 'Third Party')],
                                 string='Plot Type')

    def name_get(self):
        res = []
        for each in self:
            name = each.name
            if each.plot_no:
                res.append((each.id, str(name) + ' [' + each.plot_no + ']'))
            else:
                res.append((each.id, name))
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Function for create sequence"""
        for vals in vals_list:
            vals['plot_no'] = self.env['ir.sequence'].next_by_code(
                'plot.sequence')
        return super(PropertyPlot, self).create(vals_list)


class PlotCategory(models.Model):
    _name = 'plot.category'
    _description = 'Plot Category'
    name = fields.Char(string='Name')
