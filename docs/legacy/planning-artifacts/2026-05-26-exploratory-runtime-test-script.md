# Exploratory Runtime Test Script

Date: 2026-05-26
Scope: Chore lifecycle runtime validation in Home Assistant debug mode
Branch: feature/readiness-lifecycle-validation
Commit baseline: 90f14d2

## Objective

Validate runtime behavior for lifecycle services under real Home Assistant conditions:

1. complete
2. snooze
3. skip
4. restore
5. reassign

Also validate restart persistence for representative scenarios.

## Preconditions

1. Home Assistant debug runtime is running against /workspaces/home-assistant/config.
2. sh-chore-tracker integration is available in config/custom_components/sh_chore_tracker symlink.
3. You can access Home Assistant UI at http://localhost:8123.
4. You are authenticated in UI (or have a long-lived token for API checks).

## Evidence Collection Rules

For each test case capture:

1. Action performed.
2. Expected state transition.
3. Actual observed state transition.
4. Event payload keys observed.
5. Attribute changes observed.
6. Pass or fail.

Recommended evidence sources:

1. Developer Tools -> States (entity snapshot before and after).
2. Developer Tools -> Events (listen for sh_chore_tracker events).
3. Relevant log excerpts from home-assistant.log.

## Setup Steps (5 minutes)

1. Ensure runtime process is active.
2. Open UI and confirm integration loaded.
3. Identify one test chore entity, for example sensor.chore\_<name>.
4. In Developer Tools -> Events, listen for:
   - sh_chore_tracker_chore_completed
   - sh_chore_tracker_chore_snoozed
   - sh_chore_tracker_chore_skipped
   - sh_chore_tracker_chore_restored
   - sh_chore_tracker_chore_reassigned
5. Record baseline state and attributes of the test entity.

## Test Case 1: Complete

Action:

1. Call service sh_chore_tracker.complete_chore with target entity.

Expected:

1. status becomes complete.
2. completion_count increments by 1.
3. last_completed_date is updated.
4. next_due_date recalculates from completion date.
5. event sh_chore_tracker_chore_completed emitted with keys:
   - entity_id
   - completed_at
   - next_due_date
   - completion_count

Record:

1. Before and after state values.
2. Event payload sample.
3. Pass or fail.

## Test Case 2: Snooze

Action:

1. Call service sh_chore_tracker.snooze_chore with days=3 and reason="exploratory".

Expected:

1. status becomes snoozed.
2. next_due_date advances by 3 days from current due date.
3. snooze_until equals next_due_date.
4. snooze_reason is set.
5. snooze_count increments.
6. event sh_chore_tracker_chore_snoozed emitted with keys:
   - entity_id
   - snoozed_for_days
   - new_due_date
   - snooze_count
   - reason

Record:

1. Due date delta math.
2. Event payload sample.
3. Pass or fail.

## Test Case 3: Skip

Action:

1. Call service sh_chore_tracker.skip_chore with reason="exploratory".

Expected:

1. status becomes skipped.
2. original_due_date captured if not already set.
3. next_due_date advances pattern-forward from current due date.
4. last_skip_date set.
5. skip_reason set.
6. skip_restored is false.
7. event sh_chore_tracker_chore_skipped emitted with keys:
   - entity_id
   - skip_date
   - next_due_date
   - reason

Record:

1. Original vs next due date comparison.
2. Event payload sample.
3. Pass or fail.

## Test Case 4: Restore

Action:

1. Within restore window, call service sh_chore_tracker.restore_chore.

Expected:

1. status returns to pending.
2. skip_restored becomes true.
3. next_due_date resets to original_due_date when available.
4. event sh_chore_tracker_chore_restored emitted with keys:
   - entity_id
   - restore_date
   - original_skip_date

Negative check:

1. Attempt restore again; should be rejected.

Record:

1. First restore result.
2. Second restore rejection behavior.
3. Pass or fail.

## Test Case 5: Reassign

Action:

1. Call service sh_chore_tracker.reassign_chore with person_id set to valid person entity.

Expected:

1. config assigned_person updates.
2. entity attributes reflect new assignment.
3. event sh_chore_tracker_chore_reassigned emitted with keys:
   - entity_id
   - old_person
   - new_person

Negative check:

1. Reassign to unknown person entity should be rejected.

Record:

1. Old and new assignment values.
2. Valid and invalid attempt results.
3. Pass or fail.

## Restart Persistence Checks

Run after at least one snooze and one skip action:

1. Restart Home Assistant.
2. Re-open same chore entity.
3. Verify persisted fields survived restart:
   - status
   - next_due_date
   - snooze_until
   - last_completed_date
   - last_skip_date
   - original_due_date
4. Verify no unexpected resets.

Record:

1. Pre-restart snapshot.
2. Post-restart snapshot.
3. Differences and verdict.

## Pass Criteria

All must be true:

1. All 5 lifecycle flows pass expected state and event checks.
2. Negative-path checks behave correctly (restore repeat rejection, unknown-person reassign rejection).
3. Restart persistence checks pass for representative scenarios.
4. No critical runtime defects found.

## Failure Triage Rules

1. Critical: wrong state transitions, missing required events, or data-loss after restart.
2. High: contract mismatch in key event payload fields.
3. Medium: non-blocking UI or tasking friction.
4. Low: cosmetic or log-only noise without behavior impact.

## Output Mapping

After execution, update:

1. \_bmad-output/planning-artifacts/2026-05-26-runtime-validation-report.md
2. \_bmad-output/planning-artifacts/2026-05-26-merge-readiness-decision.md

Recommended final decision mapping:

1. Proceed: all pass, no critical or high defects.
2. Proceed with conditions: no critical defects, some high/medium with mitigation.
3. Hold: any critical defect or unresolved high defect affecting lifecycle correctness.
