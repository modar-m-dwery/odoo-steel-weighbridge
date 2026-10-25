# ADR 0003: Put invariants in the database, not only in Python

**Status:** accepted

## Context

Two rules must hold even under concurrency:

- a truck has at most one open weighing per company;
- the daily summary job creates one row per company and day, even if it runs twice.

A Python check (`search_count(...)` then `create`) cannot guarantee this: two
transactions can both see "no row yet" and both insert: neither sees the
other's uncommitted row, and under Odoo's `REPEATABLE READ` not even rows
committed after its snapshot started.

## Decision

- `models.UniqueIndex("(truck_plate, company_id) WHERE (state = 'weighed')")`:
  a partial unique index. It only covers open weighings, so completed tickets
  for the same truck are unaffected.
- `models.Constraint("UNIQUE(date, company_id)")` on the daily summary. The job
  still checks first (to stay quiet in the normal case); the constraint is the
  guarantee.
- `CHECK(net_kg >= 0)` as a second line of defence for writes that bypass the ORM.

## Consequences

- The second concurrent transaction fails with a unique violation instead of
  silently duplicating data; Odoo's retry on serialization errors does not
  apply, so the user sees a clear error.
- Constraints are visible in the schema and tested
  (`test_one_open_weighing_per_truck`, `test_daily_summary_job_is_idempotent`).
