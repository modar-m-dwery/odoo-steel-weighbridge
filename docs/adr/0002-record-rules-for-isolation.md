# ADR 0002: Isolate sales and purchases with record rules

**Status:** accepted

## Context

Sales clerks must only see sale tickets, purchase clerks only purchase tickets,
and managers both. Each company must only see its own tickets. The isolation
has to hold for every read path: list views, `search_count`, `_read_group`,
related fields and exports, not only for the menu a clerk happens to open.

## Options

1. Override `search()` / `read()` to filter by ticket type.
2. Domain filters on the menu actions.
3. `ir.rule` records bound to groups, plus a global multi-company rule.

## Decision

Option 3. Two group rules (`ticket_type = sale` for sales clerks,
`ticket_type = purchase` for purchase clerks). The manager group implies both
clerk groups, and Odoo combines group rules with OR, so managers see both.
A global rule `company_id in company_ids` is combined with AND on top.

Option 1 misses paths that do not go through `search()`; option 2 is only
cosmetic.

## Consequences

- Isolation is enforced by the ORM on every query and reviewed as security
  data, not scattered code.
- Developers must know how rules combine (group rules OR, global rules AND).
  `tests/test_security.py` pins this behaviour.
