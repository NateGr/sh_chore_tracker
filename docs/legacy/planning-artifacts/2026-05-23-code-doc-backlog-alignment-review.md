# Code, Documentation, and Backlog Alignment Review

Date: 2026-05-23
Reviewer Persona: Winston (System Architect)
Scope: Current feature branch plus project planning docs

## Executive Verdict

The integration is close to aligned, but not fully aligned.

- Code and documentation are mostly consistent on lifecycle services and event names.
- Two notable behavior mismatches remain in service docs versus runtime behavior.
- Backlog status is directionally accurate at epic level, but story-level completion for Epic 2 has one semantic gap and Epic 3 is partially pre-implemented in code.

---

## A) Is Code and Documentation Aligned?

### What is aligned

1. Service event naming and payload shape for complete and snooze are aligned.
- Code emits complete event payload at [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L847).
- Code emits snooze event payload at [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L891).
- Docs reflect these event names and keys at [docs/service-reference.md](docs/service-reference.md#L34) and [docs/service-reference.md](docs/service-reference.md#L68).

2. Persistence architecture exists and is integrated into setup and service transitions.
- Load on setup at [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L381).
- Store-backed load/save methods at [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L587) and [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L615).

### Where alignment is off

1. Snooze behavior text in docs does not match runtime behavior.
- Docs say original due date is maintained at [docs/service-reference.md](docs/service-reference.md#L63).
- Code currently advances next_due_date directly at [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L876).

2. Restore validation claim in docs is stricter than implementation.
- Docs state restore blocks when next occurrence is overdue at [docs/service-reference.md](docs/service-reference.md#L132).
- Code only validates skipped state, already-restored state, and time window at [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L967) and [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L978).

3. Architecture dependency documentation is stale.
- Architecture lists external libraries in the stack section, but runtime requirements are empty in [custom_components/sh_chore_tracker/manifest.json](custom_components/sh_chore_tracker/manifest.json#L9).

---

## B) Where Is Code Relative to the Backlog?

### Backlog state from planning docs

1. Epic 1 marked complete at [docs/user-stories/epic-1/README.md](docs/user-stories/epic-1/README.md#L3).
2. Epic 2 marked complete at [docs/user-stories/epic-2/README.md](docs/user-stories/epic-2/README.md#L3).
3. Epic 3 marked planned at [docs/user-stories/epic-3/README.md](docs/user-stories/epic-3/README.md#L3).

### Code reality vs backlog

1. Epic 1 appears implemented and stable.
- Core setup, coordinator, and entity wiring present at [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L372) and [custom_components/sh_chore_tracker/sensor.py](custom_components/sh_chore_tracker/sensor.py#L22).

2. Epic 2 is mostly implemented, with one key semantic risk in Story 2.4.
- Complete, snooze, skip, restore handlers are present and wired via service dispatch at [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L640) and [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L810).
- Skip currently computes next due using current time, not explicit advancement from existing due date at [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L936).

3. Epic 3 is partially pre-implemented despite planned status.
- Person assignment field exists in config flow at [custom_components/sh_chore_tracker/config_flow.py](custom_components/sh_chore_tracker/config_flow.py#L178).
- Assigned person appears on entity attributes at [custom_components/sh_chore_tracker/sensor.py](custom_components/sh_chore_tracker/sensor.py#L181).
- Reassign service exists at [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L1011).

Conclusion on backlog position:
- Delivery is ahead of backlog in selected Epic 3 capabilities.
- Epic 2 completion claim is plausible overall, but Story 2.4 acceptance semantics should be reconciled before calling it fully closed.

---

## C) Potential Issues

### High

1. Skip scheduling semantics may violate story intent.
- Current implementation recalculates from now at [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L936), which can diverge from a strict pattern-forward from current due date.

### Medium

2. Documentation drift on snooze behavior.
- Docs describe preserving original due date at [docs/service-reference.md](docs/service-reference.md#L63), but code mutates next_due_date at [custom_components/sh_chore_tracker/__init__.py](custom_components/sh_chore_tracker/__init__.py#L876).

3. Documentation drift on restore validation.
- Docs mention overdue-based restore rejection at [docs/service-reference.md](docs/service-reference.md#L132), but code does not implement that condition.

4. Architecture dependency section appears outdated.
- Listed third-party runtime libs are not reflected in manifest requirements at [custom_components/sh_chore_tracker/manifest.json](custom_components/sh_chore_tracker/manifest.json#L9).

### Test and verification risk

5. Service test coverage is improved but uneven.
- Complete, snooze, restore have explicit test classes in [tests/test_services.py](tests/test_services.py#L65), [tests/test_services.py](tests/test_services.py#L182), and [tests/test_services.py](tests/test_services.py#L304).
- No dedicated skip or reassign service test class is visible in [tests/test_services.py](tests/test_services.py).

---

## Recommended Team Actions

1. Decide and codify skip semantics:
- Either update skip logic to advance from current due date, or
- Update story acceptance and docs to explicitly allow completion-based recalculation.

2. Reconcile service reference text with current behavior:
- Snooze due-date statement.
- Restore overdue-validation statement.

3. Update architecture dependency section to match manifest reality.

4. Add focused tests for skip and reassign handlers.

5. Run live Home Assistant validation for service flows before final merge.

---

Prepared for architecture and implementation-readiness review.