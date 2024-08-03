from odoo import models, fields


class TenderLostWizard(models.TransientModel):
    _name = 'tender.lost.reason'
    _description = "Lost Reason"

    lost_reason = fields.Text(string="Lost Reason", required=1)
    tender_id = fields.Many2one('project.tender', string="Tender")

    def lost(self):
        if self.tender_id.parent_tender:
            for tender in self.tender_id.child_ids:
                tender.state = 'close'
            self.tender_id.parent_tender.state = 'close'
            self.tender_id.state = 'close'
            self.tender_id.lost_reason = self.lost_reason
        else:
            self.tender_id.state = 'close'
            self.tender_id.lost_reason = self.lost_reason
