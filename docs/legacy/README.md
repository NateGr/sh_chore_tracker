# Legacy Documentation and Backlogs

This archive preserves documentation from `C:\git\ha-chore-tracker`, branch
`copilot/assess-chores-architecture`, as copied on 2026-10-17. The archived files
are snapshots, not active instructions or a verified statement of current status.

## Start Here

- [Remaining backlog snapshot](source-docs/analysis/REMAINING_BACKLOG_TO_IMPLEMENT.md)
- [User-story index](source-docs/user-stories/README.md)
- [Field findings and recommendations](source-root/NEXT_STEPS.md)
- [Development context snapshot](source-root/context.md)
- [Recommended team actions](planning-artifacts/2026-05-23-recommended-team-actions-execution-plan.md)
- [Accepted hub architecture decision](source-docs/architecture-decision-helper-vs-integration.md)
- [Historical migration plan](source-docs/plan-migrateHelperToDeviceToHub.prompt.md), marked superseded in the source

## Archive Layout

- `source-docs/` contains the source repository's complete `docs/` tree, including
  user stories, product requirements, architecture notes, reviews, and old
  development-environment guidance.
- `source-root/` contains the source README, changelog, `NEXT_STEPS.md`, context
  handoff, and the dated story checklist.
- `issues/` contains the source repository's issue/backlog note.
- `planning-artifacts/` contains dated backlog, test, runtime, and merge-readiness
  records. They are preserved as evidence, not carried forward as current gates.

The source agent and tooling directories were not imported. Some archived prose
still mentions that workflow and should be read as historical context only.

## Status Caveats

- The user-story index describes Epic 3 as entirely planned, but later source code
  implements some person-assignment and hub capabilities. Reconcile each story
  against the current code and tests before using it as an active backlog.
- The May 2026 runtime and merge-readiness reports refer to an earlier branch and
  predate the current hub implementation. They do not validate this import.
- Source docs describe multiple architectures. The current destination uses the
  hub package under the preserved `sh_chore_tracker` domain.

Use the current [maintainer guide](../maintainer.md) for import, compatibility,
migration, and release requirements. The next planning task is to triage these
snapshots into completed, still-needed, deferred, and obsolete items without
editing the archived originals.