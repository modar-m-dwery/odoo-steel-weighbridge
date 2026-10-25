from odoo import api, fields, models


class SteelDailySummary(models.Model):
    _name = "steel.daily.summary"
    _description = "Weighbridge Daily Summary"
    _order = "date desc, company_id"

    date = fields.Date(required=True, index=True, readonly=True)
    company_id = fields.Many2one("res.company", required=True, readonly=True)
    ticket_count = fields.Integer(string="Completed Tickets", readonly=True)
    net_ton = fields.Float(string="Net (t)", digits=(16, 3), readonly=True)

    # The cron checks before inserting; the constraint keeps that promise even
    # if two workers run the job at the same time.
    _date_company_unique = models.Constraint(
        "UNIQUE(date, company_id)",
        "There is already a summary for this company and day.",
    )

    @api.model
    def _cron_build_daily_summary(self):
        """Store today's completed tonnage per company. Safe to run repeatedly."""
        today = fields.Date.context_today(self)
        done_companies = self.search([("date", "=", today)]).company_id
        totals = {
            company: (count, tons)
            for company, count, tons in self.env["steel.weigh.ticket"]._read_group(
                [("date", "=", today), ("state", "=", "done"), ("is_reversal", "=", False)],
                groupby=["company_id"],
                aggregates=["__count", "net_ton:sum"],
            )
        }
        self.create([
            {
                "date": today,
                "company_id": company.id,
                "ticket_count": totals.get(company, (0, 0.0))[0],
                "net_ton": totals.get(company, (0, 0.0))[1],
            }
            for company in self.env["res.company"].search([]) - done_companies
        ])
