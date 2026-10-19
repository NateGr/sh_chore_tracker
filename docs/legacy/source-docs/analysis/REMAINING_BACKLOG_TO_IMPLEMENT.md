# Remaining Backlog to Implement

Date: 2026-05-24  
Reference baseline: `_bmad-output/planning-artifacts/2026-05-23-recommended-team-actions-execution-plan.md`

## Summary

Actions 1-4 from the 2026-05-23 execution plan appear implemented in code/docs, but several backlog and readiness items remain open. The remaining work is primarily verification, backlog-governance alignment, and unresolved Epic 3 scope.

## Remaining Items

### 1) Action 4 verification evidence (still pending)

- Run and capture test evidence for skip/reassign coverage in `tests/test_services.py`.
- Publish test evidence artifact in planning docs (pass/fail, files executed, timestamp, environment details).

Why still open:
- Skip/reassign tests exist, but readiness artifacts still call out missing execution evidence.

---

### 2) Action 5 live Home Assistant validation (pending)

- Execute live HA validation for lifecycle flows:
  - `complete_chore`
  - `snooze_chore`
  - `skip_chore`
  - `restore_chore`
  - `reassign_chore`
- Verify:
  - state transitions
  - event payloads
  - restart persistence
- Record outcomes in a runtime validation report.

Why still open:
- No live-runtime validation evidence is currently documented.

---

### 3) Action 6 backlog governance alignment (pending)

- Update Epic 3 and story status docs to reflect implemented slices already present in code (person assignment + reassign foundations).
- Add explicit “implemented vs planned” status mapping for Epic 3.
- Add a short decision note on intentional pull-forward scope (if applicable).
- Reconcile stale story-level DoD/task lists that contradict current tests/implementation state.

Why still open:
- Backlog docs still show Epic 3 as fully planned while code contains partial implementation.

---

### 4) Action 7 documentation hygiene cleanup (pending)

- Replace placeholder analysis docs with actionable, current content:
  - `docs/analysis/PROJECT_STATUS_AND_DOCUMENTATION_REVIEW.md`
  - `docs/analysis/REQUIREMENTS_REVIEW_AGENDA.md`
  - `docs/analysis/REVIEW_SUMMARY_START_HERE.md`
- Add “Last Reviewed” metadata and owner on key analysis artifacts.
- Archive/remove obsolete placeholders if replaced elsewhere.

Why still open:
- Current analysis files are placeholders and not decision-useful.

---

### 5) Action 8 release confidence gate package (pending)

- Produce merge-readiness decision artifact tied to concrete runtime evidence.
- Include residual-risk statement and recommendation (`proceed`, `proceed-with-conditions`, or `hold`).

Why still open:
- No final runtime-backed merge recommendation artifact is present yet.

---

### 6) Remaining product backlog scope (Epic 3 not fully delivered)

Documented Epic 3 backlog still includes planned/unmet items, especially:

- Story 3.1 completion criteria not fully closed in backlog artifacts (person-entity change handling, filtering/automation completion markers).
- Story 3.2 planned deliverables beyond current baseline (bulk reassignment, fuller assignment-history/accountability scope, UI workflow expectations).
- Story 3.3 remains planned (edit/delete lifecycle management and cleanup safeguards).

## Out of Scope for This Document

This file is a backlog snapshot only. No implementation or status mutation is performed here.
