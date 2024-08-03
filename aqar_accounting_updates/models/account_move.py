from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    zakath = fields.Boolean(string='Zakath',
                            related="journal_id.zakath",
                            help="Activate Zakath and to view the Zakath Amount")
    zakath_amount = fields.Float(string='Zakath Amount',
                                 related="journal_id.zakath_amount",
                                 help="(Current Assets - Current Liabilities) * 2.575 / 100",
                                 compute="_compute_zakath_amount")
    approval_status = fields.Boolean(default=False, string="Approval Status One",
                                     help="Used to identify First approval status")
    approval_status_2 = fields.Boolean(default=False, string="Approval Status Two",
                                       help="Used to identify second approval status")

    def button_draft(self):
        self.approval_status = False
        self.approval_status_2 = False
        return super(AccountMove, self).button_draft()

    def approve_status_move(self):
        for rec in self:
            rec.approval_status = True

    def update_approve_status_two(self):
        for rec in self:
            rec.approval_status_2 = True

    def action_post(self):
        # to block the posting if there is no analytic distribution
        for move in self:
            for line in move.line_ids:
                if line.account_id.is_analytic_account_required:
                    if not line.analytic_distribution:
                        raise ValidationError(_('Analytic Distribution is mandatory for this Account.'))
        res = super(AccountMove, self).action_post()
        # to generate notification for the Internal memo user
        for rec in self:
            for line in rec.line_ids:
                company = self.env['res.company'].search([('partner_id', '=', line.partner_id.id)], limit=1)
                notify_user = company.internal_users
                amount = 0
                if line.debit:
                    amount = line.debit
                else:
                    amount = line.credit
                if notify_user:
                    activity = self.env['mail.activity'].create({
                        'activity_type_id': self.env.ref('aqar_accounting_updates.mail_activity_internal_memo').id,
                        # 'note': "Internal Memo",
                        'note': "Internal Memo \n" + line.name,
                        'user_id': notify_user.id,
                        'res_id': rec.id,
                        'res_model_id': self.env['ir.model']._get_id('account.move'),
                        'date_deadline': fields.date.today(),
                        'summary': "An accounting entry {ref} is made by {company} on {date} for an amount of {amount}".format(
                            ref=rec.name, company=rec.company_id.name, date=rec.date, amount=amount),
                    })
        return res
