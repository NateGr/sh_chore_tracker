# Debug Execution Packet

Date: 2026-05-26
Prepared by: Winston (System Architect)
Scope: Immediate preparation for executing remaining readiness actions in devcontainer.

## Session Objective

Complete the remaining readiness actions with evidence:

1. Action 4 verification (execute and record tests).
2. Action 5 runtime validation in Home Assistant debug mode.
3. Action 8 merge-readiness evidence package.

## What Is Already Done

1. Skip semantics decision and implementation are documented as completed in prior planning artifacts.
2. Service documentation and architecture dependency updates are documented as completed in prior planning artifacts.
3. Skip and reassign tests are documented as added, but execution evidence is still pending.

## Remaining Work To Execute Now

1. Run targeted tests for lifecycle services, with focus on skip and reassign.
2. Start Home Assistant in debug mode and validate lifecycle flows:
   - complete
   - snooze
   - skip
   - restore
   - reassign
3. Record runtime evidence, residual risks, and merge recommendation.

## Recommended Run Order

1. Environment sanity checks.
2. Targeted tests and evidence capture.
3. Debug runtime start.
4. Lifecycle flow validation.
5. Restart persistence validation.
6. Evidence write-up and merge recommendation.

## Command Checklist

Run from repository root for ha-chore-tracker unless noted otherwise.

1. Confirm clean branch and context:
   - git status
   - git branch --show-current

2. Run focused tests first:
   - pytest tests/test_services.py -k "skip or reassign" -q
   - pytest tests/test_services.py -q

3. If tests pass, start Home Assistant debug workflow (workspace task):
   - Use task: Debug Full Reset and Test Integration

4. Optional quick inspection task during runtime:
   - Use task: Debug Check Integration Status

5. Optional log inspection task:
   - Use task: View Home Assistant Logs

## Runtime Validation Checklist

For each lifecycle flow, verify all three checkpoints:

1. State transition is correct.
2. Event name and payload keys are correct.
3. Entity attributes update as expected.

Flows:

1. Complete
2. Snooze
3. Skip
4. Restore
5. Reassign

## Restart Persistence Validation

After representative actions:

1. Restart Home Assistant.
2. Verify persisted fields remain correct after reload.
3. Confirm no regression in state, next due date, assigned person, and skipped metadata.

## Evidence Artifacts To Produce

Create these files in planning artifacts:

1. 2026-05-26-test-evidence.md
2. 2026-05-26-runtime-validation-report.md
3. 2026-05-26-merge-readiness-decision.md

## Suggested Templates

### Test Evidence Template

- Date and environment.
- Commands executed.
- Pass/fail by test group.
- Failures with file and test names.
- Final test verdict.

### Runtime Validation Report Template

- Environment and build revision.
- Validation matrix for complete, snooze, skip, restore, reassign.
- Event payload verification notes.
- Restart persistence verification notes.
- Defects found and disposition.

### Merge Readiness Decision Template

- Decision: proceed, proceed with conditions, or hold.
- Blocking issues.
- Residual risks.
- Required follow-ups and owners.

## Risk Watchlist

1. Skip behavior regressions around date advancement semantics.
2. Reassign validation edge cases for unknown persons.
3. Runtime-only mismatches between service docs and actual emitted payloads.
4. Persistence issues only visible after restart.

## Definition of Done For This Session

All conditions below are true:

1. Targeted tests executed with evidence captured.
2. All five lifecycle flows validated in debug runtime.
3. Restart persistence validated for representative scenarios.
4. Evidence artifacts created with explicit pass/fail and residual risk statement.
5. Merge readiness decision documented.
