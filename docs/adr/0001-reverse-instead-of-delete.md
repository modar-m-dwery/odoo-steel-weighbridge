# ADR 0001: Cancel tickets by reversal, never by deletion

**Status:** accepted

## Context

A completed weighbridge ticket is a business document: it has a number, a
weight, a price and an amount that may already be invoiced or reported.
Deleting it would remove the audit trail and leave a gap in the numbering.

## Options

1. Allow `unlink()` on completed tickets.
2. Create an opposite ticket and mark the original as `reversed`.

## Decision

Option 2. `action_reverse()` copies the ticket with a negative price, links it
to the original (`reversed_ticket_id`) and sets the original to `reversed`. The
pair nets to zero in every report. Only draft tickets can be deleted
(`@api.ondelete`), and a ticket can be reversed once.

This follows the pattern Odoo uses for journal entries (`account.move._reverse_moves`).

## Consequences

- Full audit trail, unbroken numbering, safe with period locks.
- Two rows per cancelled ticket. Weights stay positive on both (the database
  forbids negative net weight), so reports count *effective* tickets only:
  `state = done` and not a reversal. A reversed ticket and its reversal drop
  out together; the monthly statement, the analysis view and the daily summary
  all use this rule.
