import logging

import psycopg2
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SteelWeighTicket(models.Model):
    _name = "steel.weigh.ticket"
    _description = "Weighbridge Ticket"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"
    _check_company_auto = True

    name = fields.Char(default="/", copy=False, index=True, readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner", string="Partner", required=True, tracking=True, check_company=True)
    ticket_type = fields.Selection(
        [("purchase", "Purchase"), ("sale", "Sale")],
        string="Type", required=True, default="purchase", tracking=True)
    truck_plate = fields.Char(required=True, index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company", required=True, index=True, default=lambda self: self.env.company)

    gross_kg = fields.Float(string="Gross (kg)", digits=(16, 1), tracking=True)
    tare_kg = fields.Float(string="Tare (kg)", digits=(16, 1), tracking=True)
    net_kg = fields.Float(
        string="Net (kg)", digits=(16, 1), compute="_compute_net_kg", store=True)
    # Editable in both directions: setting tonnes writes back the gross weight.
    net_ton = fields.Float(
        string="Net (t)", digits=(16, 3), compute="_compute_net_ton",
        inverse="_inverse_net_ton", store=True)

    currency_id = fields.Many2one(
        "res.currency", required=True, default=lambda self: self.env.company.currency_id)
    price_per_ton = fields.Monetary(string="Price per Ton", currency_field="currency_id", tracking=True)
    amount = fields.Monetary(
        compute="_compute_amount", store=True, currency_field="currency_id")

    state = fields.Selection(
        [("draft", "Draft"), ("weighed", "Weighed"),
         ("done", "Done"), ("reversed", "Reversed")],
        default="draft", required=True, copy=False, tracking=True)
    is_reversal = fields.Boolean(readonly=True, copy=False)
    reversed_ticket_id = fields.Many2one(
        "steel.weigh.ticket", string="Reverses", readonly=True, copy=False)
    reversal_ids = fields.One2many(
        "steel.weigh.ticket", "reversed_ticket_id", string="Reversals", readonly=True)

    # Two open weighings for one truck would double-count the load. A Python
    # check cannot stop two concurrent transactions; a partial unique index can.
    _one_open_weighing_per_truck = models.UniqueIndex(
        "(truck_plate, company_id) WHERE (state = 'weighed')",
        "This truck already has an open weighing.",
    )
    # Second line of defence for writes that bypass the ORM.
    _non_negative_net = models.Constraint(
        "CHECK(net_kg >= 0)",
        "Net weight cannot be negative.",
    )

    @api.depends("gross_kg", "tare_kg")
    def _compute_net_kg(self):
        for ticket in self:
            # Draft tickets may be half-filled (gross not weighed yet).
            ticket.net_kg = max(ticket.gross_kg - ticket.tare_kg, 0.0)

    @api.depends("net_kg")
    def _compute_net_ton(self):
        for ticket in self:
            ticket.net_ton = ticket.net_kg / 1000.0

    def _inverse_net_ton(self):
        for ticket in self:
            ticket.gross_kg = ticket.tare_kg + ticket.net_ton * 1000.0

    @api.depends("net_ton", "price_per_ton")
    def _compute_amount(self):
        for ticket in self:
            ticket.amount = ticket.net_ton * ticket.price_per_ton

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("steel.weigh.ticket") or "/"
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_only_drafts(self):
        if any(ticket.state != "draft" for ticket in self):
            raise UserError(_("Only draft tickets can be deleted. Reverse a completed ticket instead."))

    def action_weigh(self):
        for ticket in self:
            if ticket.state != "draft":
                raise UserError(_("Only draft tickets can be weighed."))
            if ticket.gross_kg <= 0 or ticket.tare_kg < 0 or ticket.tare_kg > ticket.gross_kg:
                raise ValidationError(_(
                    "Ticket %s: gross weight must be positive and not lower than the tare.",
                    ticket.name))
            ticket.state = "weighed"

    def action_reset_to_draft(self):
        for ticket in self:
            if ticket.state != "weighed":
                raise UserError(_("Only weighed tickets can be reset to draft."))
            ticket.state = "draft"

    def action_done(self):
        for ticket in self:
            if ticket.state != "weighed":
                raise UserError(_("Only weighed tickets can be completed."))
            ticket.state = "done"

    def action_reverse(self):
        """Cancel completed tickets by creating opposite tickets.

        The original stays in the database with state ``reversed`` so the audit
        trail and the numbering are kept; the pair nets to zero.
        """
        reversals = self.browse()
        for ticket in self:
            if ticket.state != "done" or ticket.is_reversal:
                raise UserError(_("Only completed tickets can be reversed, and only once."))
            reversal = ticket.copy({
                "is_reversal": True,
                "reversed_ticket_id": ticket.id,
                "price_per_ton": -ticket.price_per_ton,
                "state": "done",
            })
            ticket.state = "reversed"
            ticket.message_post(body=Markup(_("Reversed by %s")) % reversal._get_html_link())
            reversals |= reversal
        return reversals

    @api.model
    def action_bulk_done(self, ticket_ids):
        """Complete many tickets; one failure must not roll back the others."""
        result = {"done": 0, "failed": 0}
        for ticket in self.browse(ticket_ids):
            try:
                with self.env.cr.savepoint():
                    ticket.action_done()
            except (UserError, ValidationError, psycopg2.Error) as error:
                _logger.warning("Weigh ticket %s not completed: %s", ticket.id, error)
                result["failed"] += 1
            else:
                result["done"] += 1
        return result
