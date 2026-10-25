from odoo import fields
from odoo.tests import tagged

from .common import WeighbridgeCase


@tagged("post_install", "-at_install")
class TestWeighbridgeReporting(WeighbridgeCase):

    def test_monthly_totals_never_mix_currencies(self):
        usd = self.env.ref("base.USD")
        eur = self.env.ref("base.EUR")
        # 1 tonne per ticket: USD 100 + USD 50, and a EUR ticket that must not leak in.
        for plate, currency, price in (("C1", usd, 100.0), ("C2", usd, 50.0), ("C3", eur, 999.0)):
            self.make_done_ticket(truck_plate=plate, currency_id=currency.id,
                                  price_per_ton=price, gross_kg=9000.0, tare_kg=8000.0)
        totals = self.env["steel.statement"].monthly_totals(usd.id)
        self.assertAlmostEqual(sum(totals.values()), 150.0, places=2)

    def test_reversed_pairs_cancel_out_in_totals(self):
        usd = self.env.ref("base.USD")
        ticket = self.make_done_ticket(currency_id=usd.id, gross_kg=9000.0, tare_kg=8000.0,
                                       price_per_ton=100.0)
        ticket.action_reverse()
        totals = self.env["steel.statement"].monthly_totals(usd.id)
        self.assertAlmostEqual(sum(totals.values()), 0.0, places=2)

    def test_daily_summary_job_is_idempotent(self):
        self.make_done_ticket(truck_plate="D1")
        self.make_done_ticket(truck_plate="D2").action_reverse()
        Summary = self.env["steel.daily.summary"]
        Summary._cron_build_daily_summary()
        Summary._cron_build_daily_summary()

        today = fields.Date.context_today(Summary)
        summary = Summary.search([("date", "=", today), ("company_id", "=", self.env.company.id)])
        self.assertEqual(len(summary), 1, "running the job twice must not duplicate the summary")
        # D1 counts; D2 was reversed and its reversal is excluded.
        self.assertEqual(summary.ticket_count, 1)
        self.assertAlmostEqual(summary.net_ton, 12.0, places=3)

    def test_ticket_report_renders(self):
        ticket = self.make_done_ticket(truck_plate="PRINT-1")
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(
            "steel_weighbridge.action_report_weigh_ticket", ticket.ids)
        html = html.decode() if isinstance(html, bytes) else str(html)
        self.assertIn(ticket.name, html)
        self.assertIn("PRINT-1", html)
