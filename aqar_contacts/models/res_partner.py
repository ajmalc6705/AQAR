from odoo import _, api, models,fields
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = "res.partner"


    additional_email = fields.Char(string="Additional Email", copy=False)
    email = fields.Char(copy=False)
    mobile = fields.Char(unaccent=False, copy=False)
    id_type_id = fields.Many2one('id.type', string='Civil ID Type')
    id_number = fields.Char(string='Civil ID Number')
    customer_type_id = fields.Many2many('customer.type', 'customer_type_rel', 'customer_id', 'type_id', string='Customer Type',default=lambda self: self.env.user.customer_type_ids.ids)
    # customer_type_ids = fields.Many2many('customer.type', 'customer_customer_type_rel', 'customer_type_id', 'contact_type_id', string='Customer Types')

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if hasattr(self.env.user, 'customer_type_ids') and self.env.user.customer_type_ids:
            user_customer_type_ids = self.env.user.customer_type_ids.ids
            args += [('customer_type_id', 'in', user_customer_type_ids)]

        return super(ResPartner, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        # Check if the current user has 'customer_type_ids' field
        if hasattr(self.env.user, 'customer_type_ids'):
            user_customer_type_ids = self.env.user.customer_type_ids.ids
            if user_customer_type_ids:
                if args:
                    args.insert(0, '&')

                args =  args + [['customer_type_id','in', user_customer_type_ids]]
        if name:
            name = name.split(' / ')[-1]
            args = [('name', operator, name)] + args

        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    @api.constrains("mobile")
    def _check_mobile_unique(self):
        if self.mobile and self.env.company.partner_mobile_unique:
            self._check_field_unique("mobile", "mobile number")

    @api.constrains("email")
    def _check_email_unique(self):
        if self.email and self.env.company.partner_email_unique:
            self._check_field_unique("email", "email address")

    @api.constrains("additional_email")
    def _check_additional_email_unique(self):
        if self.additional_email and self.env.company.partner_additional_email_unique:
            self._check_field_unique("additional_email", "additional email address")

    def _check_field_unique(self, field_name, field_description):
        for partner in self:
            field_value = getattr(partner, field_name)
            if field_value:
                domain = [
                    (field_name, "=", field_value),
                    ("id", "!=", partner.id),
                ]
                if partner.company_id:
                    domain.append(("company_id", "=", partner.company_id.id))

                duplicate_partners = self.search(domain)
                if duplicate_partners:
                    raise UserError(
                        _(
                            f"The {field_description} already exists for another partner. "
                        )
                    )



class IDType(models.Model):
    _name = 'id.type'
    _description = "ID Type"

    name = fields.Char(string='ID Type')

class CustomerType(models.Model):
    _name = 'customer.type'
    _description = "Customer Type"

    name = fields.Char(string='Customer Type')
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        # Check if the current user has 'customer_type_ids' field
        if self._context.get('contact_view', False):
            user_customer_type_ids = self.env.user.customer_type_ids.ids
            if user_customer_type_ids:
                if args:
                    args.insert(0, '&')
    
                args =  args + [['id','in', user_customer_type_ids]]
        if name:
            name = name.split(' / ')[-1]
            args = [('name', operator, name)] + args
    
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
