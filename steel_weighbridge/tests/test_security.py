from odoo import Command
from odoo.tests import tagged

from .common import WeighbridgeCase


@tagged("post_install", "-at_install")
class TestWeighbridgeSecurity(WeighbridgeCase):

    def _user(self, login, group_xmlid, company=None):
        company = company or self.env.company
        return self.env["res.users"].create({
            "name": login,
            "login": login,
            "company_id": company.id,
            "company_ids": [Command.set([company.id])],
            "group_ids": [Command.set([self.env.ref(group_xmlid).id])],
        })

    def test_clerks_see_their_side_and_managers_see_both(self):
        self.make_ticket(truck_plate="S1", ticket_type="sale")
        self.make_ticket(truck_plate="P1", ticket_type="purchase")
        clerk = self._user("sales_clerk", "steel_weighbridge.group_weighbridge_sales")
        manager = self._user("wb_manager", "steel_weighbridge.group_weighbridge_manager")

        clerk_types = set(self.Ticket.with_user(clerk).search([]).mapped("ticket_type"))
        manager_types = set(self.Ticket.with_user(manager).search([]).mapped("ticket_type"))
        self.assertEqual(clerk_types, {"sale"})
        self.assertEqual(manager_types, {"sale", "purchase"})
        # The rule protects aggregates too, not only list views.
        self.assertEqual(
            self.Ticket.with_user(clerk).search_count([("ticket_type", "=", "purchase")]), 0)

    def test_companies_are_isolated(self):
        other_company = self.env["res.company"].create({"name": "Other Steel Co"})
        self.make_ticket(truck_plate="HOME-1")
        self.make_ticket(truck_plate="AWAY-1", company_id=other_company.id)
        manager = self._user("home_manager", "steel_weighbridge.group_weighbridge_manager")

        plates = self.Ticket.with_user(manager).search([]).mapped("truck_plate")
        self.assertIn("HOME-1", plates)
        self.assertNotIn("AWAY-1", plates)
