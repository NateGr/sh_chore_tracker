# Runtime Validation Report

Date: 2026-05-27T00:37:00+00:00
Environment: Home Assistant debug runtime in devcontainer, port 8123
Branch: feature/readiness-lifecycle-validation
Commit: 90f14d2 (+ datetime normalization patch applied 2026-05-27)
Test entity: sensor.chore_test_chore_2

## Validation Matrix

1. Complete
   - State transition: pending → complete
   - Event payload: sh_chore_tracker_chore_completed emitted with entity_id, completed_at, next_due_date, completion_count
   - Attributes update: completion_count incremented to 1, last_completed_date set, icon updated to mdi:check-circle
   - Result: Pass

2. Snooze
   - State transition: pending → snoozed (validated in prior session 2026-05-26)
   - Event payload: sh_chore_tracker_chore_snoozed emitted, attributes appeared including snooze_until and snooze_reason
   - Attributes update: next_due_date advanced by snooze days, snooze fields present
   - Result: Pass

3. Skip
   - State transition: complete → skipped
   - Event payload: sh_chore_tracker_chore_skipped emitted with entity_id, skip_date, next_due_date, reason
   - Attributes update: next_due_date advanced pattern-forward (2026-05-27 → 2026-05-28 for daily interval), last_skip_date set, skip_restored=false
   - Result: Pass

4. Restore
   - State transition: skipped → pending
   - Event payload: sh_chore_tracker_chore_restored emitted with entity_id, restore_date, original_skip_date
   - Attributes update: next_due_date restored to original (2026-05-27), skip_restored=true
   - Result: Pass

5. Reassign
   - State transition: Not executed (no person entity available in test environment)
   - Event payload: Not executed
   - Attributes update: Not executed
   - Result: Deferred — service handler is unit-tested (TestReassignChoreHandler, 2 cases pass); runtime execution blocked by absence of person entity in devcontainer

## Restart Persistence Validation

1. Scenario: post-skip-restore restart
   - Pre-restart state: pending, next_due_date=2026-05-27, completion_count=1, last_completed_date set, skip_restored=true
   - Post-restart state: pending, next_due_date=2026-05-27, completion_count=1, last_completed_date=2026-05-26T17:29:19-07:00, last_skip_date=2026-05-26T17:32:23-07:00, skip_restored=true
   - Result: Pass — all fields survived restart with no resets or regressions

## Defects Found and Disposition

1. Defect: Entity attributes collapsed to icon and friendly_name only after complete_chore when next_due_date was timezone-naive.
   - Severity: High
   - Root cause: RecurrenceEngine.calculate_next_due_date returned naive datetime; sensor attribute math crashed on naive vs aware comparison.
   - Action: Fixed 2026-05-27 — normalize returned datetime to HA local timezone in RecurrenceEngine and \_calculate_initial_due_date; harden sensor attribute renderer with explicit tzinfo guard.
   - Owner: Dev Lead
   - Status: Resolved

2. Defect: Attribute keys completion_count and last_completed_date used stale fallback key names.
   - Severity: Medium
   - Root cause: Sensor extra_state_attributes read completed_count and last_completed instead of completion_count and last_completed_date.
   - Action: Fixed 2026-05-27 — added canonical key read with backward-compatible fallback.
   - Owner: Dev Lead
   - Status: Resolved

3. Defect: recurrence_description shows Every day but interval_days attribute shows 7.
   - Severity: Low (cosmetic / UI consistency only, no behavioral impact)
   - Root cause: interval_days attribute emits legacy key fallback instead of active pattern_interval + interval_unit config.
   - Action: Noted for follow-up; non-blocking for merge.
   - Owner: Dev Lead
   - Status: Open, deferred

4. Defect: Debug Check Integration Status task fails due to shell quoting in zsh.
   - Severity: Low (tooling only, no behavioral impact)
   - Action: Superseded by direct curl API validation approach used in this session.
   - Status: Deferred

## Residual Risks

1. Reassign service flow was not executed in live runtime; covered by unit tests only.
2. interval_days attribute reports legacy value; cosmetic discrepancy with recurrence_description.

## Overall Runtime Verdict

- Pass or fail: Pass
- Notes: Four of five lifecycle flows validated end-to-end in authenticated HA runtime with correct state transitions, event payloads, attribute updates, and restart persistence. Reassign deferred to unit test coverage only due to devcontainer environment constraint. No critical or high defects remain open.
