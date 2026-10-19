# Story 3.5: Due-State Event Decision and Implementation

**Epic**: Epic 3 — Person Assignment & Advanced Features
**Status**: 🎯 Planned
**Effort**: 2 story points
**Priority**: Low

## User Story

**As a** Home Assistant automation author,
**I want** a clear, predictable event contract for chores entering the `due` state,
**so that** I can build reliable reminders and escalations without duplicate or ambiguous triggers.

## Background

The integration now has a date-only lifecycle model with explicit `due` and `overdue` states. `overdue` transition events are implemented and emitted once per transition. The `due` transition event is currently deferred and requires a product/architecture decision before implementation.

This story captures that decision and, if approved, provides implementation and test coverage for a `sh_chore_tracker_chore_due` event.

## Decision Questions

1. Do we need a dedicated `due` event, or are state triggers (`to: due`) sufficient?
2. If implemented, should the `due` event fire only once per transition into due?
3. Should `due` events fire for all transition paths (`pending->due`, `complete->due`, `skipped->due`, `snoozed->due`)?
4. What payload keys are required for stable automations?

## Acceptance Criteria

- [ ] Decision recorded: implement `due` event now, or explicitly defer
- [ ] If implemented: event fires only on transition into `due` (no refresh spam)
- [ ] If implemented: payload includes `entity_id`, `entry_id`, `from_status`, `to_status`, `effective_date`, and `next_due_date`
- [ ] If implemented: regression tests cover one-time firing across all supported transition paths
- [ ] Service reference and architecture docs updated to reflect final behavior

## Proposed Payload Contract (if implemented)

```yaml
event_type: sh_chore_tracker_chore_due
data:
  entity_id: sensor.chore_example
  entry_id: abc123
  from_status: pending
  to_status: due
  effective_date: "2026-05-28"
  next_due_date: "2026-05-28T00:00:00-07:00"
```

## Out of Scope

- Changing recurrence calculations
- Altering service handler behavior
- Notification policy design (handled by user automations)
