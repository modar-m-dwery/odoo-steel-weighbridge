from odoo import api, models


class SteelStatement(models.AbstractModel):
    _name = "steel.statement"
    _description = "Weighbridge Monthly Statement"

    @api.model
    def monthly_totals(self, currency_id):
        """Monthly ticket amounts in one currency, computed by the database.

        Amounts are never added across currencies: the caller asks for one
        currency at a time, and record rules of the current user still apply.
        Only effective tickets count: a reversed ticket and its reversal drop
        out together.
        """
        groups = self.env["steel.weigh.ticket"]._read_group(
            [("currency_id", "=", currency_id), ("state", "=", "done"), ("is_reversal", "=", False)],
            groupby=["date:month"],
            aggregates=["amount:sum"],
        )
        return {month.strftime("%Y-%m"): total for month, total in groups}
