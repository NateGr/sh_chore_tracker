# First Production Release Review

Review date: 2026-10-29 (local date).
Reviewed commit: `655547657c649a0ec34646f7e3a97312b0a31099`, branch
`import-core-code`, open [PR #4](https://github.com/NateGr/sh_chore_tracker/pull/4).

## Recommendation

**Hold production publication.** Automated integration and release tests pass,
but there is a reproduced lifecycle-contract defect, inaccurate active user
documentation, missing release infrastructure, and no current live-upgrade or
installation evidence. This review did not change runtime code or repository
settings, merge a PR, dispatch a release, or publish anything.

## Verification Evidence

- The Windows `.venv` could not collect the complete suite: Home Assistant and
  voluptuous were absent, and pytest-asyncio was not installed.
- Created an isolated WSL environment at
  `/tmp/sh-chore-tracker-release-review-20261029`, using Python 3.14.4 and the
  exact dependencies in [requirements_test.txt](../requirements_test.txt).
  The Ubuntu Python lacked ensurepip; bootstrapped pip inside that environment
  using the official pip zipapp, without sudo or a system package installation.
- Full local Linux suite: **259 passed**, one upstream Home Assistant HTTP
  deprecation warning. Combined integration/release statement coverage: **88%**.
  Release helper coverage: 99%; sensor coverage: 73%.
- Linux Ruff lint and formatting checks passed using the CI Markdown exclusion.
- `python scripts/release.py check --require-integration` passed. This checks
  metadata/readiness declarations; it is not a live Home Assistant test.
- Windows release-only suite independently passed: **58 tests**.
- GitHub CI passed for the reviewed commit:
  [run 40983189486](https://github.com/NateGr/sh_chore_tracker/actions/runs/40983189486).
  The public HACS step is skipped by design while the repository is private.
- Parsed all **58 tracked Markdown documents** and **83 fenced YAML blocks**
  present before adding this report. Found **50 missing relative-link targets**
  and **three invalid YAML blocks**. Five broken links and one invalid block
  are in active documentation; the rest are historical archive issues.
- The structural audit checks relative file targets, not external URL health
  or heading/line anchor validity. YAML parsing is not equivalent to validating
  every example against Home Assistant or a third-party card schema.

To repeat the full local test run while the temporary environment exists:

```powershell
wsl --exec bash -lc 'cd /mnt/c/git/sh_chore_tracker && PYTHONDONTWRITEBYTECODE=1 COVERAGE_FILE=/tmp/sh-chore-tracker-release-review-20261029/.coverage /tmp/sh-chore-tracker-release-review-20261029/bin/python -m pytest tests/ --cov=scripts --cov=custom_components/sh_chore_tracker --cov-report=term-missing -q'
```

## Findings

### P1: Restore Window Ends At Midnight

The service reference promises a 24-hour skip-restore window. The coordinator
changes `skipped` to `pending` after calendar rollover when the next due date is
in the future. The restore handler requires the status still to be `skipped`.

Reproduced with the actual coordinator update and restore handler, a mocked HA
host, and a fixed UTC clock: skip at 2026-10-28 23:55, refresh at 2026-10-29 00:05,
then restore. After only ten minutes, the status is `pending` and restore raises
`Chore sensor.review is not in skipped state`.

Sources: [lifecycle update](../custom_components/sh_chore_tracker/__init__.py#L859),
[restore guard](../custom_components/sh_chore_tracker/__init__.py#L1521),
[documented contract](service-reference.md#L143).
Existing tests cover rollover and restore separately, not this interaction.
Agree the intended contract, fix the behavior or revise that contract, and add
a regression test before publishing.

### P1: Production Publication Is Not Configured

Live GitHub inspection found the repository is **private**, has **zero release
environments**, and has **zero published releases**. The rulesets endpoint
returned HTTP 403 with a requirement to upgrade the plan or make the repository
public. This does not establish that the documented rulesets exist.

The workflow requires public visibility for non-dry-run releases. Its prepare
and publish jobs use the `release` environment; a new release also requires
`RELEASE_APP_CLIENT_ID` and `RELEASE_APP_PRIVATE_KEY`. No configured main-only
release environment was found. This review did not access credential values.

Complete and verify the [Release App and ruleset setup](maintainer.md#L73).
A successful dry run alone will not prove App credentials or bypass behavior:
the token and push steps are skipped during dry runs.

### P2: Service Examples Cannot Be Used As Written

In [the service reference](service-reference.md):

- The away/reminder examples compare a numeric sensor state to `pending`.
  Use the `status` attribute or numeric comparisons. The daily reminder should
  include due/overdue chores rather than requiring `pending` with a nonpositive
  days-until-due value.
- The error-handling example at line 436 is invalid YAML because of an extra
  closing brace. It also waits for the unprefixed event `chore_completed`
  after a blocking completion call. Correcting only the spelling/brace would
  still leave a race: the completion event can already have fired. Replace the
  example with error handling or postcondition checking that cannot miss it.
- The generic device-press example needs a real device-specific trigger; its
  domain is unspecified. Do not present it as a universally valid trigger.

### P2: Auto-Entities Examples Have The Wrong Structure

Both [recommended card examples](configuration-reference.md#L207) use
`attribute:` where auto-entities expects `attributes:`. They place global
`sort` under `filter` rather than alongside it. Match the
[upstream card configuration](https://github.com/thomasloven/lovelace-auto-entities#usage).
The examples currently do not implement the filtering/sorting they promise.

### P2: Reset Documentation Contradicts The Service

[The configuration reference](configuration-reference.md#L318) describes an
optional replacement date. The actual reset schema accepts only `entity_id`;
the handler recomputes from last completion or configured first occurrence.
[The service reference](service-reference.md#L209) already states this correctly.
Make the configuration reference agree and explain that changing the first due
date is an edit-flow operation, not a reset parameter.

### P2: Scheduling Multiplier Guidance Overstates The UI

[The configuration reference](configuration-reference.md#L52) describes
`pattern_interval` as a required multiplier for every recurrence type, range
1-999, and includes a quarterly example. In the actual
[flow](../custom_components/sh_chore_tracker/config_flow.py#L161), only interval
recurrence displays a multiplier field. Weekly/monthly/yearly creation flows
do not expose it; the engine defaults a missing multiplier to one.

Service validation also limits weekly multipliers to 52, monthly to 60, yearly
to 10; interval weeks/months are limited to 60 and years to 10. Either expose
the promised calendar multipliers or document the UI/service distinction and
actual limits. Illustrative configuration dictionaries are not YAML setup
support: the integration explicitly declares config-entry-only configuration.

### P2: Event, Validation, And History Claims Need Narrowing

[The service reference](service-reference.md#L384) still claims entity ownership
depends on the `sensor.chore_*` prefix. Ownership actually comes from registry
platform/config-entry/subentry mapping, so renamed chore sensors are supported.

The event-system summary uses unprefixed names and says every service call
fires an event. There are eight prefixed event constants; create/list do not
emit the described lifecycle events, and ignored duplicate completions do not
emit completion events. Include undo, reset, and overdue contracts explicitly.
There is no dedicated due-transition event; use the `status` attribute trigger.

Other claims to correct:

- `reason` is a string with no implemented 255-character schema limit.
- The undo window is a fixed 24-hour constant, not a user-configurable setting.
- Skip stores last-skip metadata; reassign updates config and emits an event.
  Neither implements an integration-owned, persistent audit-history list.
- Reassign requires an existing entity but does not check the `person.` domain;
  list-my-chores does check that domain. Do not certify the stronger Person-only
  validation claim without aligning the handler and tests.
- `list_my_chores` is response-only. Document `response_variable` for script or
  automation calls and show the returned `chores` structure. The bare call is
  not a complete automation example.
- Event next-due values use start-of-day ISO datetimes with timezone offsets;
  the completion example's same-time-of-day next due is misleading.

### P2: Active Documentation Links Are Broken

- [Configuration reference](configuration-reference.md#L322): missing PRD,
  architecture, and developer-guide pages (three links).
- [Service reference](service-reference.md#L453): missing PRD and developer
  guide pages (two links).

Link to active material, or explicitly label a link as historical and point to
the archive. Do not silently promote archived architecture into current advice.

### P2: Live Installation And Migration Remain Unverified

The migration tests use mocked registries/stores. This run does not establish
live UI behavior, HACS installation, integration reloads, real registry
ownership changes, or restart persistence after a legacy-to-hub upgrade.
The archived May runtime report tested another branch/architecture; it is not
evidence for the reviewed commit. Preserve that distinction in release notes.

Test a clean install and backed-up helper/device-era upgrades on a disposable
Home Assistant 2026.9 instance. Verify entities/unique IDs, devices, summaries,
disabled states, chores, assignments, counts, due dates, and runtime history
before/after reload and restart. Include all service actions, midnight status
changes, edit/reanchor, delete, and renamed entity IDs.

## README Cross-Reference

The domain/package paths, selected HA minimum, singleton hub and first-chore
flow, four recurrence families, numeric sensor states, summary IDs, service
names, snooze defaults, and status-attribute automation example agree with the
implementation. All three README YAML examples parse.

Minor copy issues: the feature list groups restore with button actions, but
only Complete/Snooze/Skip/Reset buttons exist; restore is service-only. Clarify
that distinction. Fix the manual-install list indentation. Its HACS/release
installation instructions remain procedures to test, not verified evidence;
the private repository currently has no release to install from.

## Maintainer Guide Assessment

The release/ref guards, manual dispatch, metadata-only version commit, frozen
candidate validation, atomic main/tag push, dry-run limits, and publication
recovery descriptions match the workflow/helper. No production workflow was
dispatched during this review.

The guide needs a current first-release checklist rather than import-era tasks:

- Replace completed import steps and the already-removed pending-import notice
  with verified status and remaining gates.
- Record the passing local suite/CI and distinguish those from live-upgrade
  evidence, branding provenance, and hosted permission tests.
- Track the release environment/App/ruleset work as outstanding, not configured.
- Keep the stated HA baseline tied to the exact pinned test dependency. Linux
  testing here used Python 3.14.4; CI pins Python 3.14.2. The wording "or newer"
  in contributor setup is not a promise of compatibility with every future
  Python major/minor release.
- Contributor formatting-apply guidance should use the same Markdown exclusion
  as CI, avoiding accidental rewrites of historical code examples.

The checked security-settings boxes were not independently verified in this
review. Branding ownership/license and the full history/secret audit still
require maintainer evidence; the presence of MIT license text alone does not
establish image provenance.

## Archive Assessment And Scope

All 50 historical Markdown snapshots were included in structural/link/example
auditing. They are explicitly non-authoritative under the
[archive index](legacy/README.md). Historical runtime results and every
aspirational product requirement were not independently revalidated as current
facts. Do not infer completion percentages or first-release gates from them.

| Archive group | Accuracy/status concerns |
| --- | --- |
| Planning artifacts | May test/runtime/proceed decisions reference another commit and architecture; useful evidence of past work, not this release. Many relative source links no longer resolve after archiving. |
| PRD, brief, architecture, migration plan | Mix helper, per-device, and hub designs; older HA/Python floors; calendar/future aggregate claims; obsolete state/service counts. The superseded plan is historical, not an execution checklist. |
| Archived config/service/developer references | Carry old version floors, reset/state/event guidance, environment paths and tooling that do not match this checkout. Archived service reference also has invalid YAML. |
| User stories and epic indexes | Completed/planned flags are inconsistent with current person selection, reassignment, editing, translation selectors, and overdue events. The story index omits stories 3.4/3.5. Calendar, assignment history, and due-event proposals are not current implemented contracts. One recurrence-story YAML block is invalid. |
| Analysis snapshots | Three current-named analysis files are placeholders, not actual status/review reports. The May backlog predates later runtime evidence and the hub work. |
| Older review/checklist archive | Dated completion/test counts and governance requirements are historical, not current release gates. |
| Source-root README/changelog/context/next steps/story check | Useful provenance, but mix obsolete runtime/version/status claims. Next steps contains superseded migration and reset/label proposals. Do not copy its "done" flags into a current checklist. |
| Debugging guides | Refer to nonimported devcontainer/editor/safety tooling. Symlinks alone do not hot-reload already-imported Python code. |
| Entity-validation issue | Its chosen platform-based resolution matches the implementation; the older prefix-based problem/proposals are retained historical context. |

The archive accounts for 45 of the 50 broken relative links and two of the
three YAML parse failures. Preserve snapshots rather than rewriting history;
use active docs and a separately triaged current backlog for future work.

## Remediation Plan

Plan status: cleanup complete; implementation and release phases below are
pending. Proceed in order, validating each change before starting the next.
GitHub settings, visibility changes, credentials, merging, and publication
require explicit maintainer action or approval; this plan does not authorize
those operations automatically.

### Phase 0: Clean Baseline - Complete

- Confirmed the old `custom_components/chore_tracker/` directory contained only
  three untracked files and no tracked files.
- Deleted those files and removed the empty directory at the user's request.
- Reran the full WSL suite after deletion: **259 passed**, **88% combined
  coverage**, with the same single upstream Home Assistant deprecation warning.
- The tracked `custom_components/sh_chore_tracker/` integration was unchanged.

### Phase 1: Restore-Window Correctness - First Implementation Task

Scope: the lifecycle coordinator and restore handler in
[the integration](../custom_components/sh_chore_tracker/__init__.py), plus the
existing [lifecycle tests](../tests/test_init.py) and
[service tests](../tests/test_services.py).

1. Add a failing regression for skip at 23:55, coordinator refresh after
   midnight, and restore at 00:05. Exercise the update and handler together,
   rather than testing only a manually constructed skipped state.
2. Preserve the documented 24-hour restore contract without forcing the
   visible status to remain `skipped` all day. Separate restoration eligibility
   from the status string, using the skip timestamp, original due date, and
   whether the skip has already been restored or superseded.
3. Ensure completion, reset, and explicit schedule reanchoring invalidate stale
   restore eligibility. Confirm the intended handling of a second skip and
   other intervening actions before changing their behavior.
4. Cover same-day and cross-midnight restores, the existing inclusive 24-hour
   boundary and expiry, repeated restore rejection, intervening actions, and
   persisted skip metadata across reload. Do not lose completion history.

Acceptance: regression fails before the fix and passes after it; original due
date is restored; normal due/overdue status resolution still works; targeted
lifecycle/service tests and the complete suite pass.

### Phase 2: Service Contracts And Regression Coverage

Scope: existing service handlers, schemas, and service/config-flow tests. Keep
the `sh_chore_tracker` domain, storage keys, and stable entity identities.

- Enforce an existing `person.` entity consistently for reassignment and
  assigned-person creation input, while preserving the explicit `none` option
  for unassigned chore creation. Cover nonexistent entities, wrong domains,
  valid persons, and preservation of the prior assignment on rejection.
- Exercise actual `async_setup_services` registration, not just direct handler
  calls. Check all nine services, seven chore-action schemas, admin-only create,
  response-only listing, default values, and invalid input handling.
- Verify a listing call captures its response and returns the documented
  `chores` fields. Cover custom entity IDs through registry ownership, not a
  sensor-name prefix.
- Verify event names/payloads, duplicate-completion behavior, reset inputs,
  undo bounds, and recurrence limits using the existing test files/helpers.
- Keep scope limited: do not introduce persistent audit history, a dedicated
  due event, a configurable undo window, or arbitrary new validation limits.

Acceptance: invalid assignment cannot mutate configuration; registered schemas
match the examples; response-only and admin behavior are tested; the full suite
passes. Add tests in existing files unless a separate file is genuinely needed.

### Phase 3: Active Documentation Corrections

Update [README](../README.md), [configuration reference](configuration-reference.md),
[service reference](service-reference.md), [contributor guide](../CONTRIBUTING.md),
and [maintainer guide](maintainer.md).

- Replace text-state checks with status-attribute or numeric-state conditions.
  Make the daily reminder include the intended due/overdue chores.
- Replace the malformed completion-failure example with race-free error or
  postcondition handling. Replace the incomplete generic device trigger with
  a valid, clearly scoped example.
- Correct auto-entities `attributes` and top-level `sort` keys.
- Remove replacement-date claims from reset; document first-date reanchoring
  through the edit flow and the actual reset/undo behavior.
- Document all eight prefixed event types, the calls that emit them, and the
  fact that create/list do not emit those lifecycle events. Explain due-state
  attribute triggers rather than promising a nonexistent due event.
- Document response capture and the listing response shape. Correct entity
  ownership, Person validation, reason limits, history claims, and all-day
  event timestamps to match the verified service contracts.
- For the first release, document calendar multipliers as a UI limitation:
  weekly/monthly/yearly creation does not offer a multiplier field. Describe
  service-supported multipliers and their actual limits separately. Do not
  imply that illustrative configuration dictionaries are supported YAML setup.
  Exposing new calendar controls is a separate scope decision, not a release
  prerequisite if the limitation is accurately documented.
- Fix all five missing active-document links and README button/install wording.
- Align contributor formatting-apply commands with the CI Markdown exclusion.
  Replace stale import tasks with an evidence-backed maintainer checklist.
- Retain archived snapshots unchanged. Clearly label any links to historical
  documents; do not treat archived claims as current implementation evidence.

Acceptance: every active YAML example parses; runnable service examples agree
with registered schemas; numeric/status examples match sensors; auto-entities
structure matches upstream; no active local file links are broken. Reuse the
existing YAML tooling for focused regression tests where practical rather than
adding a documentation framework unnecessarily.

### Phase 4: Automated Candidate Gate

Run the full Linux suite with the pinned Home Assistant baseline, coverage,
Ruff lint/format checks, release-readiness check, and current documentation
checks. Obtain green PR CI including hassfest for the exact resulting commit.
Review coverage of the previously untested registration paths, not only the
aggregate coverage percentage. Ensure no old-name integration directory or
private runtime files are included in Git or the installation package.

Acceptance: all checks pass and no active documentation defects from this
review remain open. Record the candidate SHA, versions, commands, results, and
any remaining limitations; do not carry the baseline's 259-test count forward
as evidence for an untested later commit.

### Phase 5: Live Home Assistant Evidence And Publication Audit

Owner: maintainer, with implementation assistance as needed. Use a disposable
Home Assistant 2026.9 instance and backed-up test data, not a production household.

- Test clean install and both applicable legacy upgrade paths: helper-era and
  device-per-chore to hub. Include already-migrated hub reloads.
- Verify entity/device identity, unique IDs, disabled states, summaries,
  assignments, due dates, counts, and history after upgrade, reload, and restart.
- Exercise UI add/edit/delete, date reanchoring, all actions and service calls,
  custom entity names, restore across midnight, and all recurrence families.
- Verify branding asset ownership/license and audit the files and Git history
  for secrets, household data, and private URLs before changing visibility.
- Write tested migration/repository-switch instructions and document backup
  and recovery steps. Do not promise safe rollback without testing it.

Acceptance: attach a runtime matrix tied to the candidate SHA, explicit outcomes
for each scenario, image provenance, and publication-audit sign-off. Historical
May reports do not satisfy this phase.

### Phase 6: Hosted Release Setup And First Publication

Owner: maintainer. The latest review found a private repo, zero environments,
and unsupported private-repo rulesets under the current plan; recheck live
settings before acting.

1. Choose a supported visibility/plan for enforcement after the publication
   audit. Configure the main-only `release` environment and narrowly scoped
   release App. Enter credentials directly in GitHub, never into chat or files.
2. Configure and verify the required CI check, PR rules, App bypass, main
   force-push/deletion protections, and immutable release tags. Check a failed
   check really blocks merging and that ordinary PRs cannot obtain credentials.
3. Merge the fixed/reviewed PR only after its checks and reviews are satisfied.
   Release dispatches must use main, not the import branch.
4. After the visibility decision, obtain a passing public HACS validation run.
   Perform a release dry run on main. Verify App permissions/bypass separately:
   a dry run skips App token creation and pushing.
5. Verify stale-main rejection, duplicate-tag handling, and publication recovery
   using the maintainer procedures and an appropriate controlled test context.
   Do not move production tags or create extra releases just to test recovery.
6. Confirm the old repo/installed version baseline and choose a higher stable
   version. Current manifest 0.5.0 alone does not establish that baseline.
7. With explicit maintainer authorization, publish once. Verify the resulting
   tag/commit and tagged HACS/manual installations. Add migration and known
   limitation notes, then close the first-release checklist with evidence.

Acceptance: the exact validated candidate is published, tagged installation and
upgrade checks pass, and the release has complete migration/support notes.
Do not enable `integration-ready` or approve production solely because a
metadata check or dry run is green.

## Current Worktree And Next Action

The rogue old-name directory has been deleted and the post-cleanup suite is
green. This report remains a new, uncommitted file. No runtime remediation,
GitHub configuration, commit, push, merge, or publication was performed as part
of the cleanup/plan step.

**Next implementation task:** Phase 1's cross-midnight restore regression and
the smallest compatible fix, followed immediately by focused validation.