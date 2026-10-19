# ha-chore-tracker — Field Findings and Recommendations

> **Architecture update (2026-10-06):** This document predates the accepted household-hub design. Finding 3's device-per-chore Stage 1 plan is superseded; implementation now migrates directly to one hub with chore subentries. See [the accepted architecture decision](docs/architecture-decision-helper-vs-integration.md).

**Date:** 2026-05-31
**Source:** Field testing feedback + code/doc review (v0.3.0-rc3 deployment)

---

## Purpose of this document

This document records what was discovered while running rc3 in production, explains the
reasoning behind each recommended next step, and provides the technical detail needed to
implement each recommendation. Items that have already been completed or coded in rc3 are
archived at the bottom so the record is not lost.

The structure for each item is:
1. **What was observed** — the concrete problem encountered in production.
2. **Recommended solution** — a specific course of action.
3. **Why this solution** — the reasoning behind the recommendation, including alternatives
   considered and why they were rejected.
4. **Technical detail** — implementation specifics, affected files, and edge cases.

---

## Executive summary

Three independent problems were found in production. They are ordered here by impact:

| # | Problem | Recommended solution | Effort | Status |
|---|---------|---------------------|--------|--------|
| 1 | Entity state is a string, which is useless for sorting/display in cards | Change `native_value` to `days_until_due` (integer) | Small | ✅ Done |
| 2 | No reliable way to identify chore entities by integration | Add `integration_domain` attribute + entity label | Small | ✅ Done |
| 3 | Config flow flat form is confusing; conditional fields are architecturally impossible in helper mode | Migrate directly to the household hub with chore subentries | Large | Superseded by accepted Model C plan |

Items 1 and 2 are independent of each other and independent of item 3. They should ship
first. Item 3 is the most impactful change but also the most disruptive; it requires a
deliberate architecture decision and a data migration plan.

---

## Finding 1 — Entity state string is not useful in dashboard cards

### What was observed

When chore entities are shown in an **auto-entities** card (the standard Lovelace card for
displaying a dynamic list of entities), the card's primary display value is the entity's
state. For these entities the state is the string `pending`, `due`, or `overdue`. That
string is not sortable, not filterable by threshold, and not useful as a display value.

The `days_until_due` attribute already exists and is computed on every update. It is a
signed integer: negative = overdue (e.g. -3 means 3 days overdue), 0 = due today, positive
= days remaining. This is the value users actually want to see and sort by in a dashboard.

### Recommended solution

**Change the sensor's primary state from the status string to the integer `days_until_due`.**

Move the status string (`pending`, `due`, `overdue`, `snoozed`, `skipped`, `complete`) to a
`status` attribute. All existing state information is preserved — it is only moved from the
state field to an attribute. The entity type changes from an opaque string sensor to a
numeric measurement sensor.

### Why this solution

The alternative is to keep the string state and ask users to create template sensors that
compute `days_until_due` per chore. That is a poor user experience: it means every user who
wants a sorted dashboard must write YAML for every chore they own. The integration exists
precisely to remove that kind of boilerplate.

A numeric state is the correct model for this entity. Home Assistant treats numeric sensors
as first-class citizens: they are sortable, filterable by threshold in auto-entities
(`below: 0` = overdue), and displayable with units directly on the card. The `status`
string is still available as an attribute for automations that need it.

This is a breaking change to the state contract. Any existing automation that checks
`state == "pending"` must migrate to `state_attr(entity_id, 'status') == 'pending'`. This
needs to be prominently documented.

### Technical detail

**`custom_components/sh_chore_tracker/sensor.py`**

- Change `native_value` to return `self._days_until_due` (int) instead of the status string.
- Compute `_days_until_due` in a private helper so both `native_value` and
  `extra_state_attributes` share the same calculation.
- Add class-level declarations:
  ```python
  _attr_native_unit_of_measurement = "d"
  _attr_state_class = SensorStateClass.MEASUREMENT
  _attr_device_class = None  # No HA standard device class for "days until event"
  ```
- In `extra_state_attributes`, add `"status": <current_status_string>`. Keep all existing
  attributes unchanged.
- Update the `icon` property to read from `extra_state_attributes["status"]` (or a cached
  `_status` field) instead of `native_value`.

**`custom_components/sh_chore_tracker/const.py`**

- Import `SensorStateClass` from `homeassistant.components.sensor` and expose it if needed
  by other files.

**Breaking change documentation required in:**
- `custom_components/sh_chore_tracker/README.md`
- `docs/configuration-reference.md`
- `CHANGELOG.md` (note this as a breaking change in v0.4.0)

**`tests/test_sensor.py`**

- Update all assertions that check `entity.native_value == "pending"` (or any other status
  string) to instead check `entity.native_value == <expected_integer>`.
- Add assertions that `extra_state_attributes["status"]` returns the correct status string.

---

## Finding 2 — No reliable way to identify chore entities by integration

### What was observed

To filter entities in an auto-entities card to show only chores, users currently check
whether the entity ID starts with `sensor.chore_`. This has two problems:

1. **Entity IDs can be renamed.** Home Assistant allows any entity to be renamed in the
   entity registry. A user who renames `sensor.chore_vacuum` to `sensor.vacuum_chore` will
   break their own filter immediately.
2. **It is not exclusive to this integration.** Any sensor whose name starts with "chore_"
   — whether it belongs to this integration or not — will match the filter.

### Recommended solution

**Add `integration_domain: sh_chore_tracker` as a permanent read-only attribute on every
chore entity, and additionally assign a HA entity label `sh_chore_tracker` to each entity
during setup.**

Either mechanism alone is sufficient. Together they provide a robust and redundant
identification path.

### Why this solution

**Why an attribute?** Attributes are the simplest and most universally supported
identification mechanism. They work in auto-entities filter conditions, YAML templates, and
automations without any special HA version requirements. The `integration_domain` attribute
is a well-established pattern in HA integrations.

**Why also an entity label?** Entity labels (introduced in HA 2024.4) can be used as
direct filters in the HA dashboard entity picker and in auto-entities. Labels survive entity
renames because they are stored in the entity registry, not derived from the entity ID. They
provide a cleaner user experience for filtering in newer HA versions.

**Why not just use the entity registry's platform field?** The platform field is set
automatically to `sh_chore_tracker` by HA. However, it is not exposed as a filterable
attribute in auto-entities or in YAML conditions without custom template lookups. The
attribute approach is more accessible to non-technical users.

### Technical detail

**`custom_components/sh_chore_tracker/sensor.py`**

In `ChoreEntity.extra_state_attributes`, add unconditionally:
```python
"integration_domain": DOMAIN,
```

This attribute will always be `sh_chore_tracker` and will never change for any entity
created by this integration.

In `async_setup_entry`, after `async_add_entities`, apply the entity label. Look up the
entity in the registry and add the label:

```python
registry = er.async_get(hass)
entity_entries = er.async_entries_for_config_entry(registry, config_entry.entry_id)
for entry in entity_entries:
    registry.async_update_entity(entry.entity_id, labels=entry.labels | {"sh_chore_tracker"})
```

The label application should be wrapped in a `try/except` so that older HA versions
(pre-2024.4 which do not support labels) degrade gracefully, keeping the attribute as the
reliable fallback.

**`docs/configuration-reference.md`** — add a section showing the recommended auto-entities
filter:

```yaml
type: custom:auto-entities
card:
  type: entities
filter:
  include:
    - attribute:
        integration_domain: sh_chore_tracker
  sort:
    method: attribute
    attribute: days_until_due
    numeric: true
```

**`tests/test_sensor.py`** — add assertion that `extra_state_attributes["integration_domain"]`
equals `"sh_chore_tracker"` for all entity states.

---

## Finding 3 — Historical Config Flow UX Finding `[SUPERSEDED BY MODEL C]`

### What was observed

The configuration form shows all recurrence fields at once regardless of which recurrence
type is selected. A user choosing "weekly" recurrence still sees interval, monthly, and
yearly fields — all of which are irrelevant and should be hidden. The form is already
confusing and will only get worse as features are added.

The root cause is architectural: this integration is declared as `"integration_type":
"helper"` in `manifest.json`, which causes HA to use `SchemaConfigFlowHandler` for its
configuration. This handler renders a single flat form. It has **no supported mechanism for
conditional field visibility**.

### Recommended solution

**Migrate from helper integration to a device/service integration and rewrite the config
flow as a multi-step flow using standard `ConfigFlow` and `OptionsFlow`.**

This allows the form to be split into steps where each step shows only the fields relevant
to the choices made in prior steps.

### Why this solution — and why not the alternatives

**Alternative A: Stay as a helper and improve the flat form copy.**
This was the previous recommendation in this document. After deploying to production it is
clear this approach has a ceiling. No matter how good the labels and descriptions are, a
form with 10+ fields where 6–8 of them are irrelevant to the user's choice is a bad
experience. Copy polish is a workaround, not a solution. The fundamental problem is the
flat form.

**Alternative B: Stay as a helper and use JavaScript-based card or frontend tricks.**
HA does not support custom frontend logic in the config flow. This is not a viable option.

**Alternative C (recommended): Migrate to device integration with a multi-step flow.**
This is the correct solution. A standard `ConfigFlow` subclass allows the flow to branch
across multiple screens based on what the user selected in the previous screen. The
`OptionsFlow` for editing an existing chore can follow the same branch structure. Users only
ever see the fields that apply to their chosen recurrence type.

**Why this is disruptive and what mitigates that:**
- Existing helper entries will be invisible in the Integrations panel and may lose their
  config data if a migration handler is not implemented. This is mitigated by implementing
  `async_migrate_entry`.
- The Helpers panel is where users expect to find this integration today. Moving to the
  Integrations panel is a different UX location. This should be documented clearly in
  release notes.
- The config flow code will need a full rewrite. The scheduling logic (`__init__.py`,
  `date_utils.py`) is unaffected.

**Decision required:** This is a one-way door. Once migrated and shipped, rolling back
would break existing user entries again. The migration should be planned carefully and
shipped as v0.4.0 with explicit breaking-change release notes.

### Technical detail

#### Step 1 — Change `manifest.json`

Remove `"integration_type": "helper"`. The integration will then appear in the Integrations
panel instead of the Helpers panel.

```json
{
  "domain": "sh_chore_tracker",
  "name": "Chore Tracker",
  "config_flow": true,
  "iot_class": "calculated",
  "version": 2
}
```

Bumping `version` to `2` triggers `async_migrate_entry` for all existing installations.

#### Step 2 — Implement `async_migrate_entry` in `__init__.py`

```python
async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entry to current version."""
    if config_entry.version == 1:
        # Version 1 was helper integration; data shape is identical, just migrate version
        hass.config_entries.async_update_entry(config_entry, version=2)
        return True
    return False
```

The data schema for each chore entry does not change — only the integration type in the
manifest changes. This makes the migration trivial for existing entries.

#### Step 3 — Rewrite `config_flow.py`

Replace `SchemaConfigFlowHandler` with a standard `ConfigFlow` and `OptionsFlow`.
The create flow becomes:

```
Step 1: basic_info
  Fields: chore_name, chore_description, assigned_person
  → always proceeds to step 2

Step 2: recurrence_type
  Fields: recurrence_type (selector: interval / weekly / monthly / yearly)
  → branches to step 3a, 3b, 3c, or 3d based on selection

Step 3a: interval_config   (only if recurrence_type == "interval")
  Fields: pattern_interval, interval_unit

Step 3b: weekly_config     (only if recurrence_type == "weekly")
  Fields: weekly_days (multi-select)

Step 3c: monthly_config    (only if recurrence_type == "monthly")
  Fields: monthly_mode → if day_of_month: monthly_day
                       → if ordinal_weekday: monthly_ordinal, monthly_weekday

Step 3d: yearly_config     (only if recurrence_type == "yearly")
  Fields: yearly_month, yearly_day

Step 4: first_occurrence   (all recurrence types)
  Fields: first_occurrence_date
  Validation: auto-adjust to next valid occurrence, display confirmation
```

The `OptionsFlow` for editing an existing chore follows the same structure, pre-populated
from the existing config entry data.

Routing between steps is done via `async_step_<name>` methods that call
`async_show_form` or `self._goto_step()`:

```python
async def async_step_recurrence_type(self, user_input=None):
    if user_input is not None:
        self._data.update(user_input)
        rt = user_input[CONF_RECURRENCE_TYPE]
        if rt == RECURRENCE_TYPE_INTERVAL:
            return await self.async_step_interval_config()
        elif rt == RECURRENCE_TYPE_WEEKLY:
            return await self.async_step_weekly_config()
        elif rt == RECURRENCE_TYPE_MONTHLY:
            return await self.async_step_monthly_config()
        elif rt == RECURRENCE_TYPE_YEARLY:
            return await self.async_step_yearly_config()
    return self.async_show_form(step_id="recurrence_type", data_schema=RECURRENCE_TYPE_SCHEMA)
```

#### Step 4 — Optional: group chores under a single device

With the device integration model, multiple chores can be grouped under a single logical
device named "Chore Tracker" in the HA device registry. This makes all chores visible in
one place in the Devices panel. This is optional for v0.4.0 but is straightforward to add:

```python
from homeassistant.helpers.device_registry import DeviceInfo

class ChoreEntity(CoordinatorEntity, SensorEntity):
    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=self._chore_name,
            manufacturer="ha-chore-tracker",
        )
```

#### Files impacted

| File | Change type |
|------|------------|
| `manifest.json` | Remove `integration_type: helper`, bump `version` to `2` |
| `config_flow.py` | Full rewrite — multi-step `ConfigFlow` + `OptionsFlow` |
| `__init__.py` | Add `async_migrate_entry` |
| `sensor.py` | Optionally add `device_info` property |
| `tests/test_config_flow.py` | Full rewrite to match new multi-step flow |
| `docs/architecture.md` | Update integration type description |
| `CHANGELOG.md` | Document as breaking change in v0.4.0 |

---

## Archive — Prior backlog items (completed or coded in rc3)

> These items are kept for reference. They are no longer part of the active backlog.

---

### ~~P0 — First Occurrence / Initial Next Due Date Support~~ `[DONE]`

Added `first_occurrence_date` field to create/edit flows. Defaults to today; blocks past
dates on initial creation. Auto-adjusts to next valid occurrence for the selected recurrence
rule. Edit flow pre-fills from the live `next_due_date` in coordinator state.

---

### ~~P1 — Reset Next Due Date Service~~ `[DONE]`

Added `reset_next_due_date` service. Accepts optional replacement date; reuses
first-occurrence validation rules. Clears conflicting state (`skipped`, `snoozed`) on reset.

---

### ~~P1 — Integration-Based Entity Validation~~ `[DONE]`

Service handlers now validate ownership using the entity registry `platform` field (`entry.platform == DOMAIN`) instead of entity-id naming conventions. This keeps service calls working when entities are renamed and blocks lookalike entities from other integrations.

---

### ~~P1 — Config Flow Contract Cleanup~~ `[CODED, NEEDS BROADER TESTING]`

`config_flow.py` unified to new pattern model. `strings.json` still needs a final string
pass. `README.md` and `docs/configuration-reference.md` updated but not fully validated
end-to-end.

---

### ~~P1 — Flat Schema Guardrails~~ `[CODED, NEEDS BROADER TESTING]`

Labels, descriptions, and option-group guidance added to the flat form. Invalid field
combinations are rejected. The multi-step UX is now planned for v0.4.0 via the device
integration migration (Finding 3 above) rather than as a flat-schema workaround.

---

### ~~P1 — Monthly "Nth Weekday" Recurrence~~ `[CODED, NEEDS BROADER TESTING]`

`monthly_mode` selector added (day-of-month or ordinal weekday). `monthly_ordinal` and
`monthly_weekday` fields added. The `5th` weekday variant skips months that do not contain
a 5th occurrence. `last` is always distinct from `5th`.

---

## What to do next (priority order)

1. **Ship Finding 1 (numeric state) and Finding 2 (identity attribute) as a patch to rc3.**
   Both changes are small, independent, and provide immediate user value without requiring
   any architecture decision.

2. **Make the architecture decision for Finding 3** before starting v0.4.0 planning. The
   recommendation is to migrate to device integration. Once decided, add `async_migrate_entry`,
   rewrite the config flow, and release as v0.4.0 with explicit breaking-change release notes.

3. **Complete rc3 runtime validation** before shipping a stable release. Validate all four
   recurrence types, all six ordinal variants, the `5th`-weekday skip behavior, the reset
   service, and all five service actions in a live HA environment.
