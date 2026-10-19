# Recommended Team Actions Execution Plan

Date: 2026-05-23
Prepared by: Winston (System Architect)
Scope: Execute the 5 recommended actions from the alignment review and close readiness gaps before merge.

## Summary

This plan operationalizes the 5 recommended actions from the alignment review into an execution sequence that reduces merge risk and raises implementation readiness.

Primary outcomes targeted:

1. Resolve behavior ambiguity for skip scheduling.
2. Eliminate code-to-documentation drift in service behavior.
3. Align architecture dependency documentation with actual runtime packaging.
4. Improve service-level confidence via missing test coverage.
5. Validate lifecycle behavior in live Home Assistant runtime.

Expected result if executed fully:

- All explicit findings from the alignment review are closed or converted into explicit design decisions.
- Release readiness improves from "near-aligned" to "operationally aligned with verified behavior".

---

## Plan Overview

Execution order (recommended):

1. Action 1: Decide and codify skip semantics.
2. Action 2: Reconcile service docs with actual behavior.
3. Action 3: Correct architecture dependency section.
4. Action 4: Add focused tests for skip and reassign handlers.
5. Action 5: Run live Home Assistant validation pass.

Rationale:

- Lock behavior decisions first, then document and test against the same contract.
- Finish with live validation to verify end-to-end correctness.

Post-5-actions continuation (required for full readiness):

6. Backlog governance alignment: reflect partially implemented Epic 3 scope in planning artifacts.
7. Documentation hygiene cleanup: replace stale placeholder analysis docs with current, actionable content.
8. Release confidence gate: complete full HA runtime validation evidence before merge decision.

---

## Action-by-Action Execution Steps

## 1) Decide and codify skip semantics

Goal:
- Remove ambiguity around whether skip advances from current due date or recalculates from now.

Implementation steps:
1. Review story acceptance language for Story 2.4 and confirm intended behavior with product/owner.
2. Record one explicit decision in an Architecture Decision Note section in this plan (or a companion ADR).
3. Update implementation accordingly in service handler logic.
4. Ensure event payload semantics remain coherent with chosen behavior.

Deliverables:
- Explicit decision statement.
- Updated code path for skip behavior.
- Matching comments/doc wording.

Exit criteria:
- Team can answer in one sentence: "skip means X".
- Code behavior and story acceptance text no longer conflict.

---

## 2) Reconcile service reference text with current behavior

Goal:
- Ensure service reference accurately reflects runtime behavior and event payloads.

Implementation steps:
1. Update snooze behavior wording to match actual due-date handling.
2. Update restore validation wording to match implemented checks.
3. Verify all event examples map to current emitted keys and event names.
4. Run one reviewer pass for doc/code consistency.

Deliverables:
- Revised service reference sections for snooze and restore.
- Confirmed event payload examples.

Exit criteria:
- No known doc statement contradicts runtime service logic.

---

## 3) Update architecture dependency section to match runtime reality

Goal:
- Keep architecture tech stack honest and maintainable.

Implementation steps:
1. Compare architecture dependency claims with manifest requirements and actual imports.
2. Remove or annotate stale dependency claims.
3. Add a short note clarifying whether dependencies are planned, optional, or active runtime requirements.

Deliverables:
- Updated architecture dependency section.

Exit criteria:
- Architecture docs and packaging metadata tell the same dependency story.

---

## 4) Add focused tests for skip and reassign handlers

Goal:
- Raise confidence for service handlers that currently have weaker coverage.

Implementation steps:
1. Add skip tests for:
   - Next due date computation semantics.
   - Skip state transitions and metadata updates.
   - Event payload contract.
2. Add reassign tests for:
   - Person existence validation.
   - Assignment update persistence/refresh behavior.
   - Reassign event payload contract.
3. Add at least one negative-path test per handler.
4. Run test suite for changed files.

Deliverables:
- New test cases for skip and reassign.
- Passing test results.

Exit criteria:
- Skip and reassign have parity with existing complete/snooze/restore coverage standards.

---

## 5) Run live Home Assistant validation for service flows

Goal:
- Prove behavior in runtime context, not only unit-level context.

Implementation steps:
1. Deploy current branch to the existing HA debug setup.
2. Execute end-to-end lifecycle checks:
   - complete
   - snooze
   - skip
   - restore
   - reassign
3. Verify entity state, attributes, and emitted events after each action.
4. Confirm restart persistence behavior with representative flows.
5. Capture findings in a short validation log.

Deliverables:
- Runtime validation checklist with pass/fail status.
- Log of defects (if any) and follow-up actions.

Exit criteria:
- All lifecycle flows validated in HA runtime with no critical defects.

---

## Post-5-Actions Remaining Work (Full Readiness Track)

These items were intentionally called out as remaining even after the first 5 actions are complete.

## 6) Backlog governance alignment

Goal:
- Bring story status documents in line with actual implementation state, especially Epic 3 partial delivery.

Implementation steps:
1. Update epic status language to distinguish planned scope versus already-implemented slices.
2. Update affected story files with status tags that match code reality.
3. Add a short decision note clarifying whether partial Epic 3 implementation is intentional pull-forward work.

Deliverables:
- Updated epic and story planning artifacts.
- Explicit status mapping between backlog and implemented capabilities.

Exit criteria:
- No contradiction remains between backlog status and shipped code behavior.

## 7) Documentation hygiene cleanup

Goal:
- Remove stale placeholders and ensure analysis docs are decision-useful.

Implementation steps:
1. Replace placeholder analysis content with concise, current summary and links to source artifacts.
2. Archive or delete obsolete placeholder documents if no longer needed.
3. Add "last reviewed" metadata in key analysis docs.

Deliverables:
- Refreshed analysis docs with actionable content.

Exit criteria:
- Analysis docs are current, non-placeholder, and usable for implementation/readiness decisions.

## 8) Release confidence gate (runtime evidence)

Goal:
- Ensure merge/release decisions are backed by real runtime evidence, not doc/test intent alone.

Implementation steps:
1. Execute end-to-end service workflow in live HA (complete, snooze, skip, restore, reassign).
2. Capture evidence: expected state transitions, event payloads, and restart persistence outcomes.
3. Record defects and disposition (fixed/deferred) with clear risk statement.

Deliverables:
- Runtime validation report attached to planning artifacts.

Exit criteria:
- A merge decision can reference concrete runtime evidence and residual-risk statement.

---

## Immediate Next Work (What to perform next)

Next step now:

1. Execute Action 1 immediately: make the skip-semantics decision and lock it.

Why this first:

- Actions 2 and 4 depend on this contract.
- It prevents duplicated rework in docs and tests.

Suggested short execution sprint (single session):

1. 20-30 min: Decision and acceptance alignment for skip semantics.
2. 30-45 min: Code adjustment (if required).
3. 30-45 min: Service reference updates.
4. 45-60 min: Skip and reassign tests.
5. 30-45 min: Quick HA smoke validation.

---

## Ownership and cadence

Recommended owners:

1. Architecture/Tech Lead: Action 1 and Action 3.
2. Dev Lead: Action 1 implementation and Action 4.
3. Documentation owner: Action 2.
4. QA/Integrator: Action 5.

Cadence:

1. Start-of-work checkpoint: confirm behavior contract.
2. Midpoint checkpoint: docs + tests aligned.
3. Final checkpoint: runtime validation complete.

---

## Definition of Done

All of the following are true:

1. Skip semantics decision is explicit and implemented.
2. Service docs contain no known behavior mismatches.
3. Architecture dependency section matches runtime reality.
4. Skip and reassign tests exist and pass.
5. Live HA lifecycle validation passes with documented evidence.

When done, readiness can be treated as implementation-ready for merge decisioning with materially reduced risk.

---

## Execution Status Update (2026-05-23)

Constraint applied for this pass:

- Code and tests were not executed by request.

### Completed in this pass

1. Action 1 completed: Skip semantics were explicitly codified as pattern-forward from current due date.
   - Decision recorded in code comments and implemented in skip handler logic.
2. Action 2 completed: Service-reference behavior text was reconciled to runtime behavior.
   - Snooze wording updated to reflect due-date shift.
   - Restore validation wording updated to reflect implemented checks.
   - Skip behavior wording updated to reflect current-due-date advancement.
3. Action 3 completed: Architecture dependency section updated to match current manifest/runtime reality and separate future/optional dependencies.
4. Action 4 implementation completed: Focused skip and reassign tests were added.

### Remaining after this pass

1. Action 4 verification remains:
   - Test execution and green test evidence are still pending.
2. Action 5 remains pending in full:
   - Live Home Assistant runtime validation was not performed in this environment.
   - Runtime checklist and validation log are still pending.
3. Post-5-actions full-readiness track remains pending:
   - Backlog governance alignment for Epic 3 partial implementation.
   - Documentation hygiene cleanup for placeholder analysis docs.
   - Release confidence gate evidence from live HA execution.

### Updated immediate next steps

1. Execute tests for updated service handlers when dev/test environment is available.
2. Run live HA lifecycle validation for complete, snooze, skip, restore, and reassign.
3. Record test and runtime evidence, then re-evaluate merge readiness.
4. Update backlog status artifacts to reflect Epic 3 partial implementation.
5. Refresh placeholder analysis docs with current content and decisions.

---

## Agent Handoff Implementation Guide

Purpose:
- Allow any follow-on agent to execute the remaining work in a deterministic order with clear completion checks.

Execution order for next agent:

1. Verification pass for Action 4
   - Run targeted tests for skip and reassign handler changes.
   - Capture pass/fail results in a short test evidence note under planning artifacts.
   - If failures occur, patch code/tests and re-run until stable.

2. Action 5 runtime validation pass
   - Use Home Assistant debug environment.
   - Validate complete, snooze, skip, restore, reassign end-to-end.
   - Record state transition evidence, event payload evidence, and restart persistence evidence.

3. Action 6 backlog governance updates
   - Update Epic 3 status language to reflect partial implementation already present in code.
   - Update relevant Epic 3 story documents with status markers and "implemented slice" notes.
   - Add a concise decision note on intentional pull-forward scope.

4. Action 7 documentation hygiene updates
   - Replace placeholder analysis docs with current content.
   - Ensure each updated analysis doc includes "Last Reviewed" date and owner.
   - Archive stale versions if necessary.

5. Action 8 release confidence package
   - Produce a final runtime validation report with residual risk section.
   - State explicit merge recommendation: proceed, proceed-with-conditions, or hold.

Acceptance criteria for handoff completion:

1. Test evidence exists and references exact test files executed.
2. Runtime validation report exists with all 5 service flows documented.
3. Epic/story status docs no longer contradict code reality.
4. Placeholder analysis docs are replaced or retired.
5. Final merge recommendation is documented with residual risks.

Suggested output artifacts for next agent:

1. _bmad-output/planning-artifacts/2026-05-23-test-evidence.md
2. _bmad-output/planning-artifacts/2026-05-23-runtime-validation-report.md
3. _bmad-output/planning-artifacts/2026-05-23-merge-readiness-decision.md