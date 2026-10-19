# Architecture Decision: Household Chore Tracker Hub

**Date:** 2026-10-06
**Status:** Accepted — Model C
**Scope:** Architecture, usability, multi-user assignment, future extensibility
**Breaking changes:** Acceptable

## Decision

Use one singleton Chore Tracker hub config entry with one native config subentry per chore. The hub owns the coordinator, state store, aggregate entities, and hub services. Each chore remains an individual entity/device linked beneath the hub.

Migrate directly from the existing helper-era and device-per-chore layouts. Preserve each chore's entity/device identity and runtime history using its previous config-entry ID as the stable chore ID. Chore creation through `create_chore` is admin-only; non-admin creation would require a separate authenticated UI workflow.

The supported Home Assistant floor is 2025.1 because the implementation uses native config subentries.

---

## Background

The project passed through the helper and device-per-chore models. The selected target is the hub model: one entry in **Integrations**, with chore subentries and chore devices underneath it.

The question is whether that is the right long-term home for this integration, or whether migrating to a **device/service integration** (appearing in the **Integrations** panel) unlocks enough capability to justify the migration cost.

This document covers the architectural trade-offs in three dimensions:
1. Architecture — what each model allows structurally.
2. Usability — what the end-user experience looks like in practice.
3. Future roadmap — what becomes possible or impossible in each model.

Models A and B below are retained as historical alternatives; Model C is the accepted architecture.

---

## Model A — Helper Integration (historical)

Each chore is an independent config entry with its own coordinator. Entities live in the Helpers panel.

### Architecture pros

- **Conceptually simple.** Each chore is self-contained. There is no shared device, no coordination between chores, and no risk of one chore's state corrupting another's.
- **Already working.** This is the deployed production state. No migration required.
- **HA-native helper semantics.** Helpers are designed for exactly this use case — user-defined virtual entities. The HA UI supports listing, renaming, and deleting helpers without going into the Integrations panel.
- **Lower complexity ceiling.** For simple household use, the lack of cross-chore awareness is not a problem. The individual chore entities are perfectly automatable on their own.

### Architecture cons

- **Flat config form is structurally limited.** `SchemaConfigFlowHandler` (required by helper mode) renders a single flat form. There is no supported mechanism for conditional field visibility. Choosing "weekly" recurrence still shows interval and monthly fields. This is a ceiling, not a bug — it cannot be fixed within helper mode.
- **No cross-chore sensors are possible.** A "days until next chore" sensor, a "total overdue count" sensor, or a "chore summary card" entity all require a coordinator that knows about all chores. That coordinator cannot exist in the helper model because each chore is a completely independent entry.
- **No shared device.** There is no place in the HA UI where a user can see all chores at once in the Devices panel or as a single card. They must filter by attribute or entity ID prefix, which is fragile.
- **Multi-user assignment is harder to expand.** The current `reassign_chore` service works, but building a proper household-member management layer — with assignment notifications, acceptance/rejection flows, or per-person views — requires a coordinating layer that helper mode makes awkward.
- **No service actions on "all chores."** Services like "complete all overdue chores for me" or "snooze all chores assigned to [person]" require cross-chore awareness that the helper model does not support natively.

### Usability pros

- Familiar to HA users. Helpers are a first-class HA concept that users already know.
- Adding a new chore is fast — go to Helpers, click Add, fill the form.

### Usability cons

- The config form is already confusing (10+ fields visible at once, most irrelevant to the chosen recurrence type). This will get worse as features are added.
- No single place to see "all my chores" without a custom dashboard card.
- Deleting all chores requires deleting each helper individually.

---

## Model B — Device Integration (intermediate model)

Remove `"integration_type": "helper"` from `manifest.json`. Each chore becomes its own "device" in the Integrations panel. The config flow is rewritten as a multi-step `ConfigFlow`.

### Architecture pros

- **Multi-step config flow is now possible.** The standard `ConfigFlow` supports branching across screens. Step 1 collects basic info, step 2 selects recurrence type, step 3 shows only the fields relevant to that type. This fully solves the flat-form UX problem.
- **Options flow (edit chore) follows the same branch structure.** Editing a chore shows a pre-populated multi-step form, which is a dramatically better UX than the current flat edit form.
- **Each chore appears in the Integrations panel.** Users can see and manage chores from the standard Integrations page.
- **Device model is well-supported in HA.**  `DeviceInfo` is a first-class HA concept with full UI support.

### Architecture cons

- **Each chore is still isolated.** The device-per-chore model does not solve cross-chore awareness by itself. You still need a separate "hub" coordinator or a separate integration entry to aggregate data across chores.
- **Migration required.** Existing helper entries will not automatically appear as integration entries. An `async_migrate_entry` handler must be implemented. If migration fails, users lose their chore data.
- **UX location change.** Users who are used to Helpers → Add Helper will need to go to Integrations → Add Integration → Chore Tracker instead. This is a different workflow and will require release notes.
- **One chore = one integration entry.** The Integrations page with 20 chores listed as 20 separate integrations is untidy. Most integrations are one per physical or logical service, not one per entity.
- **No logical grouping at the integration level.** Unless a "hub" entry is added (see Model C), there is no entry that represents "Chore Tracker as a whole."

### Usability pros

- Significantly cleaner creation and edit forms.
- Each chore has an Options button in the Integrations panel for editing.

### Usability cons

- The Integrations panel becomes cluttered with one entry per chore.
- Still no single "all chores" view without a custom dashboard card.

---

## Model C — Household Hub Integration (accepted)

A single "Chore Tracker" hub entry appears in the Integrations panel. Individual chores are added as devices beneath the hub via a sub-entry or options flow, rather than as independent config entries.

This is the architecture used by integrations like Hue, Z-Wave, and most multi-device integrations.

### Architecture pros

- **Cross-chore sensors become straightforward.** The hub coordinator knows about all chores. Sensors like "days_until_next_chore", "total_overdue_count", "my_assigned_chores_count" are trivially derivable.
- **Multi-step config flow per chore.** Each chore is added or edited via a native `ConfigSubentryFlow` with branching steps. Full conditional field visibility.
- **One Integrations entry for the whole household.** The Integrations panel shows a single "Chore Tracker" entry. Inside it are all chores as sub-devices. Clean, intuitive.
- **Single place to manage everything.** Reload, delete, or configure the entire integration from one place.
- **Multi-user assignment architecture becomes natural.** The hub coordinator can maintain a roster of household members, track chore ownership across members, and emit aggregate events. This is where "allow others to create a chore" (see below) becomes implementable.
- **Derived sensors are first-class.** The hub can expose:
  - `sensor.chore_tracker_next_due` — entity ID + days until next due chore.
  - `sensor.chore_tracker_overdue_count` — total overdue chores.
  - `sensor.chore_tracker_my_chores` — count of chores assigned to the current user.
  - `binary_sensor.chore_tracker_any_overdue` — simple trigger for automations.
- **Services on the hub.** Services like "snooze all my chores" or "complete all overdue chores" can be registered at the hub level and operate across all chores.

### Architecture cons

- **Most complex migration.** Moving from flat helper entries to sub-entries under a hub is the largest breaking change of the three models. Every existing chore entry must be imported into the hub's options data.
- **More code to write.** Hub coordinator, hub config flow, sub-entry or options-flow management for chores, device_info for each chore entity. This is significant development effort.
- **Sub-entries are a newer HA feature.** `config_entry.subentries` (HA 2025.1+) is the modern way to do this, but adds a minimum HA version requirement. The alternative is to use the options flow to manage chores as data within the single hub entry — this works on all HA versions but is less idiomatic.

### Usability pros

- Best possible UX: one integration, all chores visible as devices beneath it.
- Adding a chore via the hub options flow can be a guided multi-step wizard.
- Summary sensors available immediately without any user template work.
- The "reload" button in the Integrations panel reloads all chores at once.

### Usability cons

- Initial setup requires going to Integrations → Add → Chore Tracker (one time), then configure. Slightly more steps than "Helpers → Add Helper".
- Migrating from the previous helper/device-per-chore architecture requires a handler that imports existing chores and preserves state and registry identity.

---

## Multi-user assignment: what is and is not possible in each model

This is explicitly called out because it is a stated goal.

### Current state

`reassign_chore` service exists and works. It updates the `assigned_person` config attribute. The entity shows `assigned_person` as an attribute. There is no push notification, no acceptance flow, no per-person view.

### What "assigning chores to others" needs architecturally

| Feature | Helper (A) | Device per chore (B) | Hub model (C) |
|---------|-----------|---------------------|---------------|
| Reassign service | ✅ (exists) | ✅ (simple carry-over) | ✅ (improved) |
| Person roster management | ❌ no shared state | ⚠️ awkward | ✅ reuses Home Assistant Person entities |
| Per-person chore listing | ❌ | ❌ | ✅ response-only service |
| "Chores available to claim" list | ❌ | ❌ | ✅ |
| Assignment notification event | ✅ (limited) | ✅ (limited) | ✅ (rich) |
| Create chore service | ❌ | ⚠️ each person adds their own entry | ✅ admin-only configuration service |
| Non-admin chore creation | ❌ | ❌ | Requires a separate authenticated UI workflow |

**Key insight:** Reassignment and Person-filtered listing are available through hub services. The create service is admin-only because it changes integration configuration. A non-admin create workflow is explicitly out of scope until it has a dedicated authenticated UI.

### "Would it be possible for others to create a chore?"

Yes, through an admin-only hub service:

```yaml
service: sh_chore_tracker.create_chore
data:
  chore_name: "Walk the dog"
  recurrence_type: daily
  assigned_person: person.alice
```

The service validates the recurrence configuration and adds a chore subentry. Non-admin creation would require a separate authenticated UI rather than granting configuration-changing service access.

---

## Comparison summary

| Dimension | A: Helper | B: Device per chore | C: Hub model |
|-----------|-----------|---------------------|--------------|
| Config form UX | ❌ flat, confusing | ✅ multi-step | ✅ multi-step |
| Cross-chore sensors | ❌ | ❌ | ✅ |
| Summary sensors (next due, overdue count) | ❌ | ❌ | ✅ |
| Single Integrations panel entry | ❌ one per chore | ❌ one per chore | ✅ |
| Multi-user roster | ❌ | ❌ | ✅ |
| Others can create chores via service | ❌ | ❌ | ✅ |
| Migration complexity | none | medium | high |
| Development effort | none | medium | high |
| HA version requirement | any | any | HA 2025.1+ for subentries, OR options-flow workaround for all versions |
| Breaking change | no | yes | yes |
| Future extensibility | low | medium | high |

---

## Implementation Contract

1. One hub entry owns chore subentries, a single coordinator, and one versioned Store map.
2. Each chore retains its own sensor/device and stable identity across migration.
3. Household entities report next due, overdue count, and any-overdue status.
4. Per-chore services target entities through their config subentry IDs. Hub services create a chore (admin-only) and return chores assigned to a requested Person.
5. Reset derives the next occurrence from the last completion, or from the first occurrence if never completed. It clears snooze/skip overrides, preserves completion history, and leaves past due dates overdue.
6. Migration is resumable: import config/state and move registry ownership before removing old entries.

The hub migration is a breaking change. Release notes must explain the new Integrations-panel location, the migration behavior, and the reset contract.
