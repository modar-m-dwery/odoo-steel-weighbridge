import psycopg2

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import WeighbridgeCase


@tagged("post_install", "-at_install")
class TestWeighTicket(WeighbridgeCase):

    def test_net_weight_and_tonnage(self):
        ticket = self.make_ticket(gross_kg=20000.0, tare_kg=8000.0, price_per_ton=100.0)
        self.assertEqual(ticket.net_kg, 12000.0)
        self.assertAlmostEqual(ticket.net_ton, 12.0, places=3)
        self.assertAlmostEqual(ticket.amount, 1200.0, places=2)

    def test_setting_tonnes_updates_gross_weight(self):
        ticket = self.make_ticket(gross_kg=0.0, tare_kg=5000.0)
        ticket.net_ton = 3.0
        self.assertAlmostEqual(ticket.gross_kg, 8000.0, places=1)
        self.assertEqual(ticket.net_kg, 3000.0)

    def test_batch_create_numbers_every_ticket(self):
        tickets = self.Ticket.create([
            {"partner_id": self.partner.id, "truck_plate": "T1"},
            {"partner_id": self.partner.id, "truck_plate": "T2"},
        ])
        self.assertEqual(len(set(tickets.mapped("name"))), 2)
        self.assertNotIn("/", tickets.mapped("name"))

    def test_weighing_rejects_impossible_weights(self):
        ticket = self.make_ticket(gross_kg=7000.0, tare_kg=8000.0)
        with self.assertRaises(ValidationError):
            ticket.action_weigh()
        self.assertEqual(ticket.state, "draft")

    def test_reverse_keeps_original_and_nets_to_zero(self):
        ticket = self.make_done_ticket(price_per_ton=100.0)
        reversal = ticket.action_reverse()
        self.assertTrue(ticket.exists(), "the original ticket must never be deleted")
        self.assertEqual(ticket.state, "reversed")
        self.assertEqual(reversal.reversed_ticket_id, ticket)
        self.assertTrue(reversal.is_reversal)
        self.assertNotEqual(reversal.name, ticket.name)
        self.assertAlmostEqual(ticket.amount + reversal.amount, 0.0, places=2)

    def test_reverse_only_completed_tickets_once(self):
        draft = self.make_ticket()
        with self.assertRaises(UserError):
            draft.action_reverse()
        ticket = self.make_done_ticket(truck_plate="TRK-2")
        reversal = ticket.action_reverse()
        with self.assertRaises(UserError):
            ticket.action_reverse()
        with self.assertRaises(UserError):
            reversal.action_reverse()

    def test_only_drafts_can_be_deleted(self):
        ticket = self.make_done_ticket()
        with self.assertRaises(UserError):
            ticket.unlink()
        self.make_ticket(truck_plate="TRK-3").unlink()

    @mute_logger("odoo.sql_db")
    def test_one_open_weighing_per_truck(self):
        first = self.make_ticket(truck_plate="DUP-9")
        first.action_weigh()
        self.env.flush_all()
        second = self.make_ticket(truck_plate="DUP-9")
        with self.assertRaises(psycopg2.errors.UniqueViolation), self.env.cr.savepoint():
            second.action_weigh()
            self.env.flush_all()

    @mute_logger("odoo.addons.steel_weighbridge.models.weigh_ticket")
    def test_bulk_complete_isolates_failures(self):
        ok_1 = self.make_ticket(truck_plate="B1")
        ok_1.action_weigh()
        still_draft = self.make_ticket(truck_plate="B2")
        ok_2 = self.make_ticket(truck_plate="B3")
        ok_2.action_weigh()
        result = self.Ticket.action_bulk_done([ok_1.id, still_draft.id, ok_2.id])
        self.assertEqual(result, {"done": 2, "failed": 1})
        self.assertEqual((ok_1 | ok_2).mapped("state"), ["done", "done"])
        self.assertEqual(still_draft.state, "draft")
