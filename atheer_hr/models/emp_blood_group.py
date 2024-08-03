# *-* coding:UTF-8 *-*

from odoo import api, fields, models, _


class HrBloodGroups(models.Model):
    _name = "emp.blood.groups"
    _description = " HR Employee Blood Groups"

    name = fields.Char('Name', required=1)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', 'The name of the Blood group must be unique!'),
    ]
