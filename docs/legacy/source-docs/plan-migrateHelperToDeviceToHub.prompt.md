# Historical Plan: Helper → Device → Hub

> **Superseded:** The two-stage migration below is historical planning material. The accepted implementation goes directly to the household hub described in [architecture-decision-helper-vs-integration.md](architecture-decision-helper-vs-integration.md). Use the direct migration requirements in that decision record; do not implement the former Model B stage or its non-admin create-service proposal.

Source: docs/architecture-decision-helper-vs-integration.md. Two-stage migration:
Stage 1 = Model B (device-per-chore), Stage 2 = Model C (hub with subentries).
Decisions: auto-migrate existing entries in place (no data loss); Stage 2 uses
config_entry.subentries (HA 2025.1+ min version, breaking for older HA).

**Status: Stage 1 implemented and shipped in v0.4.0** (manifest de-helperized,
multi-step ConfigFlow/OptionsFlow, async_migrate_entry v1→v2, device_info on
ChoreEntity, tests rewritten — 143 passed). Stage 2 (hub model) not started.

## Current state (verified via Explore)

- manifest.json: integration_type=helper, version="0.3.0-rc4", no requirements
- config_flow.py: SchemaConfigFlowHandler, single flat schema (\_get_chore_schema),
  CONFIG_FLOW/OPTIONS_FLOW dicts each with one "user"/"init" step, validation in
  \_validate_chore_input()
- **init**.py: async_setup_entry/async_unload_entry, ChoreCoordinator(DataUpdateCoordinator,
  15min interval, Store-backed persistence), RecurrenceEngine (strategy pattern per
  recurrence type), async_setup_services (7 domain-wide services via hass.services.async_register),
  NO async_migrate_entry, PLATFORMS = [Platform.SENSOR]
- sensor.py: ChoreEntity(CoordinatorEntity[ChoreCoordinator], SensorEntity),
  unique*id = f"chore*{entry.entry_id}", NO device_info property, native_value =
  signed int days_until_due, extra_state_attributes rich dict incl. status,
  integration_domain
- const.py: all CONF\_\*, recurrence type, status, service/event constants already
  defined and sufficient for multi-step flow — no changes needed
- date_utils.py: DateCalculator + coerce_date/normalize_first_occurrence_date —
  fully reusable unchanged in both stages
- services.yaml + handlers: 7 services (complete/undo/snooze/skip/restore/reassign/
  reset_next_due_date), domain-wide via \_find_chore_data() lookup — reusable unchanged
- tests: ~100 methods across test_config_flow.py, test_init.py, test_sensor.py,
  test_services.py, test_date_utils.py. Config flow tests will need full rewrite.
- NEXT_STEPS.md Finding 3 already contains a compatible Stage 1 design (4-step flow:
  basic_info → recurrence_type → branch(interval/weekly/monthly/yearly) → first_occurrence)
- No existing subentries/OptionsFlow(class)/DeviceInfo/async_migrate_entry in codebase.

---

## Stage 1 (Model B): Device-per-chore integration

**Steps**

1. **manifest.json**: remove `"integration_type": "helper"`; bump `"version"` to
   integer `2`... actually manifest "version" here refers to add-on version string,
   NOT config-entry schema version — do NOT conflate. Config-entry version is set via
   `VERSION = 2` class attr on the flow handler + entry.version, independent of
   manifest.json's semver `version` field. Manifest version field can stay semver
   (e.g. bump to "0.4.0") — only remove `integration_type`.
2. **const.py**: no changes required (already has all needed keys).
3. **config_flow.py** — full rewrite (_depends on step 1 conceptually, can be done in parallel_):
   - Replace `SchemaConfigFlowHandler` subclass with standard `config_entries.ConfigFlow`
     subclass, `VERSION = 2`.
   - Implement step methods: `async_step_user` (basic_info: chore_name, chore_description,
     assigned_person) → `async_step_recurrence_type` (select type) → branch to
     `async_step_interval_config` / `async_step_weekly_config` / `async_step_monthly_config`
     (handles day_of_month vs ordinal_weekday sub-branch) / `async_step_yearly_config` →
     `async_step_first_occurrence` (date selector, reuse `normalize_first_occurrence_date`
     from date_utils.py for auto-adjustment + confirmation) → `async_create_entry`.
   - Store partial input across steps in `self._data` dict on the flow handler instance.
   - Implement `ChoreTrackerOptionsFlow(config_entries.OptionsFlow)` mirroring the same
     step structure, pre-populated from `config_entry.options`, ending in
     `async_create_entry(data=merged_options)`.
   - Reuse existing validation logic from `_validate_chore_input()` — refactor into
     per-step validators instead of one big validator.
   - Register options flow via `async_get_options_flow` static/classmethod on the
     ConfigFlow class.
4. ****init**.py**: add `async_migrate_entry(hass, config_entry)` — since chore data
   schema is unchanged, this only needs to call
   `hass.config_entries.async_update_entry(config_entry, version=2)` and return True
   for entries at version 1. Coordinator, RecurrenceEngine, service registration
   unchanged. _(depends on step 3 for VERSION constant alignment)_
5. **sensor.py**: add `device_info` property to `ChoreEntity`:
   `DeviceInfo(identifiers={(DOMAIN, config_entry.entry_id)}, name=chore_name,
manufacturer="ha-chore-tracker", model="chore")`. Keep `via_device` unset in Stage 1
   (added in Stage 2 once hub device exists). _(independent, parallel with steps 3-4)_
6. **Tests** (_depends on steps 3-5_):
   - Rewrite tests/test_config_flow.py for multi-step flow: one test per step
     transition, one per recurrence-type branch (interval/weekly/monthly-day_of_month/
     monthly-ordinal_weekday/yearly), plus first_occurrence auto-adjustment and
     validation-error redisplay cases.
   - Add test for `async_migrate_entry` in test_init.py (v1 entry → v2, data preserved).
   - Add test for `device_info` presence in test_sensor.py.
   - Existing test_services.py, test_date_utils.py should require no changes — rerun
     to confirm no regressions.
7. **Docs**: update docs/architecture.md (integration pattern section, diagram) and
   NEXT_STEPS.md (mark Finding 3 as implemented). No new markdown files.

**Relevant files**

- `custom_components/sh_chore_tracker/manifest.json` — remove integration_type
- `custom_components/sh_chore_tracker/config_flow.py` — full rewrite (multi-step ConfigFlow + OptionsFlow)
- `custom_components/sh_chore_tracker/__init__.py` — add async_migrate_entry
- `custom_components/sh_chore_tracker/sensor.py` — add device_info to ChoreEntity
- `tests/test_config_flow.py` — full rewrite
- `tests/test_init.py`, `tests/test_sensor.py` — add migration + device_info tests
- `docs/architecture.md`, `NEXT_STEPS.md` — update status

**Verification**

1. `pytest tests/` — all suites green, especially new config_flow and migration tests.
2. Manual: use "🔧 Debug: Full Reset & Test Integration" task, add a chore via
   Integrations → Add Integration → Chore Tracker, confirm multi-step form only shows
   relevant recurrence fields per type, confirm entity appears with a Device page.
3. Manual: simulate pre-existing v1 helper entry (or reuse existing dev config
   storage) and reload — confirm it appears as a device with same entity_id/unique_id,
   no data loss, `async_migrate_entry` log line fires once.
4. Confirm all 7 services still work unchanged against migrated entities.

---

## Stage 2 (Model C): Hub coordinator with subentries

**Depends on Stage 1 shipped and stable.**

**Steps**

1. **New hub config flow**: Add a top-level "Chore Tracker" config entry (singleton —
   guard with `self._async_abort_entries_match({})` or `async_current_entries()` check
   in the flow to prevent multiple hubs). This hub entry has no chore-specific data,
   just acts as the parent.
2. **HubCoordinator** (new class in **init**.py or new hub_coordinator.py): owns a
   dict of all chore subentries' data, aggregates state from each chore's existing
   `ChoreCoordinator` logic (reuse RecurrenceEngine/date_utils unchanged), computes:
   - `next_due` (entity_id + days) across all chores
   - `overdue_count`
   - per-person assigned/overdue counts
3. **Convert chores to subentries**: adopt `config_entry.subentries` API (HA 2025.1+).
   Each chore's config flow (built in Stage 1) becomes the _subentry flow_ attached to
   the hub entry instead of a standalone entry. Requires:
   - `async_get_supported_subentry_types` on hub's ConfigFlow class returning a
     `{"chore": ChoreSubentryFlow}` mapping.
   - `ChoreSubentryFlow(config_entries.ConfigSubentryFlow)` reusing the exact step
     methods built in Stage 1 (basic_info → recurrence_type → branch → first_occurrence).
4. **Migration Stage1→Stage2**: `async_migrate_entry` (or a one-time repair/import
   flow) that takes each standalone Stage-1 chore config entry and re-creates it as a
   subentry under a newly created (or existing) hub entry, then removes the old
   standalone entry. This is the highest-risk step — must be idempotent and safe to
   retry; log every subentry created; on any failure, abort without deleting the
   original entry.
5. **sensor.py**: update `device_info` to add `via_device=(DOMAIN, hub_entry.entry_id)`
   linking each chore device to the hub device. Add hub-level entities in a new
   platform setup (e.g. `sensor.py` additional entities or a `binary_sensor.py`):
   `sensor.chore_tracker_next_due`, `sensor.chore_tracker_overdue_count`,
   per-person count sensors, `binary_sensor.chore_tracker_any_overdue`.
6. **Hub-level services**: add `create_chore` (adds a subentry programmatically,
   enabling Companion App/service-call chore creation without UI) and
   `list_my_chores` (template-friendly sensor or service response). Keep existing 7
   per-chore services unchanged — they still resolve via `_find_chore_data()`.
7. **Tests**: new test_hub_coordinator.py (aggregation logic), tests for subentry flow
   steps (can mostly mirror Stage 1 config_flow tests), tests for create_chore/
   list_my_chores services, migration test for Stage1→Stage2 conversion.
8. **Docs**: update docs/architecture.md diagram to show hub + subentries, update
   docs/service-reference.md for the 2 new services, update
   docs/configuration-reference.md for hub setup flow.

**Relevant files**

- `custom_components/sh_chore_tracker/__init__.py` — HubCoordinator, migration logic, new services
- `custom_components/sh_chore_tracker/config_flow.py` — hub ConfigFlow + ChoreSubentryFlow
- `custom_components/sh_chore_tracker/sensor.py` — hub aggregate sensors, via_device link
- `custom_components/sh_chore_tracker/services.yaml` — create_chore, list_my_chores
- `custom_components/sh_chore_tracker/manifest.json` — bump min HA version requirement (2025.1+)
- new `tests/test_hub_coordinator.py`
- `docs/architecture.md`, `docs/service-reference.md`, `docs/configuration-reference.md`

**Verification**

1. `pytest tests/` full suite green including new hub tests.
2. Manual: fresh install creates one hub entry; adding chores via hub's subentry flow
   shows them as devices under the hub in Integrations panel.
3. Manual: `create_chore` service call from Developer Tools creates a new chore
   subentry and entity without touching the UI.
4. Manual: verify aggregate sensors (`next_due`, `overdue_count`) update correctly
   when chores are completed/snoozed/skipped.
5. Manual: run Stage1→Stage2 migration against a HA instance with existing Stage-1
   standalone chore entries; confirm all chores appear as subentries with preserved
   state, and no orphaned standalone entries remain.

---

## Decisions

- Auto-migrate existing entries in place at both stage transitions (no user data
  re-entry, entity_ids preserved where possible).
- Stage 2 uses native `config_entry.subentries` (HA 2025.1+), accepting the higher
  minimum HA version as a breaking requirement — documented in release notes.
- Both stages ship with explicit breaking-change release notes (per architecture doc).
- Manifest.json's semver `version` field is independent of config-entry schema
  `VERSION`; only the latter needs bumping for `async_migrate_entry` to trigger.

## Scope boundaries

- Included: full config_flow rewrite, migration handlers for both transitions,
  device_info/hub linking, hub aggregate sensors, 2 new hub services, test rewrites.
- Excluded (not part of this plan): mobile Companion App action definitions,
  assignment acceptance/rejection workflow UI, notification push logic — these are
  future work enabled by but not delivered in this migration.
