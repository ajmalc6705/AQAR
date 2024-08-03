# *-* Coding :UTF-8 *-*

from odoo import api, fields, models, _


class ResUsersInheritSignPassword(models.Model):
    _inherit = "res.users"

    @property
    def SELF_READABLE_FIELDS(self):
        """ The list of fields a user can read on their own user record.
        In order to add fields, please override this property on model extensions.
        """
        return [
            'sign_signature', 'sign_initials', 'signature', 'company_id', 'login', 'email', 'name', 'image_1920',
            'image_1024', 'image_512', 'image_256', 'image_128', 'lang', 'tz',
            'tz_offset', 'groups_id', 'partner_id', '__last_update', 'action_id',
            'avatar_1920', 'avatar_1024', 'avatar_512', 'avatar_256', 'avatar_128',

        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        """ The list of fields a user can write on their own user record.
        In order to add fields, please override this property on model extensions.
        """
        return ['sign_signature', 'sign_initials', 'signature', 'action_id', 'company_id', 'email', 'name', 'image_1920',
                'lang',
                'tz']

    sign_password = fields.Char(string='Signature Password', help="Enter Signature password")
    # ******* Override **********
    sign_signature = fields.Binary(string="Digital Signature", copy=False, groups="base.group_user")
    sign_initials = fields.Binary(string="Digital Initials", copy=False, groups="base.group_user")
    sign_signature_frame = fields.Binary(string="Digital Signature Frame", copy=False, groups="base.group_user")
    sign_initials_frame = fields.Binary(string="Digital Initials Frame", copy=False, groups="base.group_user")