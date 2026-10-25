from odoo.tests import TransactionCase


class WeighbridgeCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Scrap Yard"})
        cls.Ticket = cls.env["steel.weigh.ticket"]

    def make_ticket(self, **values):
        vals = {
            "partner_id": self.partner.id,
            "truck_plate": "TRK-1",
            "ticket_type": "purchase",
            "gross_kg": 20000.0,
            "tare_kg": 8000.0,
            "price_per_ton": 100.0,
        }
        vals.update(values)
        return self.Ticket.create(vals)

    def make_done_ticket(self, **values):
        ticket = self.make_ticket(**values)
        ticket.action_weigh()
        ticket.action_done()
        return ticket
