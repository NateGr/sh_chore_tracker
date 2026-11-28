<p align="center">
  <img src="custom_components/sh_chore_tracker/icon.png" alt="SmartHass Chore Tracker" width="96">
</p>

<p align="center">
  <a href="https://github.com/NateGr/sh_chore_tracker/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/NateGr/sh_chore_tracker/ci.yml?branch=main&label=CI&logo=github" alt="CI status"></a>
  <a href="https://github.com/NateGr/sh_chore_tracker/releases/latest"><img src="https://img.shields.io/github/v/release/NateGr/sh_chore_tracker?logo=github" alt="Latest release"></a>
  <a href="https://github.com/NateGr/sh_chore_tracker/releases"><img src="https://img.shields.io/github/downloads/NateGr/sh_chore_tracker/total?logo=github&label=downloads" alt="GitHub downloads"></a>
  <a href="https://hacs.xyz/"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg?logo=homeassistantcommunitystore&logoColor=white" alt="HACS Custom"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-2026.9.0%2B-41BDF5?logo=homeassistant&logoColor=white" alt="Home Assistant 2026.9.0+"></a>
  <a href="https://github.com/NateGr/sh_chore_tracker/stargazers"><img src="https://img.shields.io/github/stars/NateGr/sh_chore_tracker?style=flat&logo=github" alt="GitHub stars"></a>
  <a href="https://github.com/NateGr/sh_chore_tracker/issues"><img src="https://img.shields.io/github/issues/NateGr/sh_chore_tracker" alt="Open issues"></a>
  <a href="https://github.com/NateGr/sh_chore_tracker/commits/main"><img src="https://img.shields.io/github/last-commit/NateGr/sh_chore_tracker" alt="Last commit"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/NateGr/sh_chore_tracker" alt="MIT license"></a>
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=NateGr&repository=sh_chore_tracker&category=integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in HACS"></a>
  <a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=sh_chore_tracker"><img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Add integration"></a>
</p>

# SmartHass Chore Tracker

SmartHass Chore Tracker is a Home Assistant custom integration for scheduling,
assigning, and tracking household chores. It creates a household hub with
individual chore sensors, summary sensors, and buttons for common chore actions.

Requires **Home Assistant 2026.9.0 or newer**.

## Features

- Schedule chores using interval, weekly, monthly, or yearly recurrence.
- Assign chores to Home Assistant `person` entities.
- Track due dates, completion counts, overdue chores, and household summaries.
- Complete, snooze, skip, and reset chores from their device buttons or Home
  Assistant services; restore skipped chores through the restore service.
- Use chore services and events in automations.
- Persist chore schedules and lifecycle state across Home Assistant restarts.
- View actual chore due dates and projected occurrences in an automatic household calendar.

## Installation

### HACS

1. In HACS, open **Integrations** and select the menu in the upper-right corner.
2. Select **Custom repositories** and add
   `https://github.com/NateGr/sh_chore_tracker` with category **Integration**,
   or use the **Open in HACS** badge above.
3. Find **SmartHass Chore Tracker**, install it, and restart Home Assistant.

If the integration is listed in the HACS catalog, find it under **Integrations**
and install it directly.

### Manual

1. Download the latest release from
   [GitHub Releases](https://github.com/NateGr/sh_chore_tracker/releases).
2. Extract the archive and copy `custom_components/sh_chore_tracker` into your
   Home Assistant configuration directory at
   `<config>/custom_components/sh_chore_tracker`. Create `custom_components` if it
   does not already exist.
3. Confirm that `<config>/custom_components/sh_chore_tracker/manifest.json`
   exists, then restart Home Assistant.

For example, the resulting directory layout should look like this:

```text
<config>/
└── custom_components/
    └── sh_chore_tracker/
        ├── __init__.py
        ├── manifest.json
        ├── sensor.py
        ├── button.py
        └── ...
```

## Setup

1. In Home Assistant, open **Settings > Devices & services** and select **Add
   Integration**.
2. Search for **SmartHass Chore Tracker** and select it.
3. Follow the setup flow to create the household hub and its first chore:
   provide a name, optionally add a description and person, choose a recurrence
   pattern, and select the first due date.
4. Open the integration's hub to add or edit other chores.

Each chore is configured in the UI; a separate YAML configuration is not
required. Examples of schedules you can create in the flow:

| Chore | Schedule |
|---|---|
| Take out trash | Every 3 days (`interval`, `3`, `days`) |
| Water plants | Every Monday and Thursday (`weekly`) |
| Replace the air filter | First Monday of each month (`monthly`, ordinal weekday) |
| Clean gutters | October 15 every year (`yearly`) |

The first occurrence is the schedule's starting due date. When a date does not
match the selected recurrence, it is normalized to the next valid date. A new
chore cannot start with a past first-occurrence date (editing an existing chore
is not subject to this check).

## Entities and Due Status

Each chore has a sensor, normally named like `sensor.chore_take_out_trash`.
Home Assistant entity IDs can be changed, so use the entity ID shown in your
instance. The sensor state is the signed number of days until its next due
date:

| Sensor state | Meaning |
|---:|---|
| `-2` | Two days overdue |
| `0` | Due today |
| `5` | Due in five days |

Use the sensor's `status` attribute for lifecycle status rather than expecting a
text state. Common values include `pending`, `due`, `overdue`, `snoozed`,
`skipped`, and `complete`. Other useful attributes include `next_due_date`,
`days_until_due`, `completion_count`, `assigned_person`, and
`recurrence_description`. The recurrence is also exposed as recorded attributes:
`recurrence_type` and `pattern_interval`, plus `interval_unit` (interval),
`weekly_days` (weekly), `monthly_mode` with `monthly_day` or
`monthly_ordinal`/`monthly_weekday` (monthly), or `yearly_month`/`yearly_day`
(yearly).

The automatically created household summary sensors are:

- `sensor.chores_next_due`: signed days until the nearest chore is due. Its
  attributes identify the chore and its due date.
- `sensor.chores_overdue_count`: number of chores currently overdue.

### Completion history

Each chore's device also has two history sensors:

- **Last completed** (timestamp): changes only when the chore is completed, so
  Home Assistant's History panel shows each completion and
  `states('sensor.<chore>_last_completed')` gives the latest one. Undoing a
  completion reverts it to the previous value.
- **Completions** (`state_class: total`): the running completion count. Use a
  statistics graph card to chart completions per day, week, or month.

The chore sensor's `last_completed_date`, `description`, `recurrence_description`,
`integration_domain`, and `created_at` attributes are still available live but are
excluded from the recorder to keep the database small; use the history sensors
for history.

Changing a chore's configuration fires `sh_chore_tracker_chore_config_changed`
with a `changed` map of `{field: {old, new}}`. Completion, undo, snooze, skip, and
config-change events appear in the Logbook.

## Chore Calendar

The integration automatically creates one read-only household calendar, normally
`calendar.chores`, in the **Overall summary** group. Existing hubs receive it on
their next load after updating. Select it in Home Assistant's **Calendar** view,
or add a calendar dashboard card:

```yaml
type: calendar
entities:
  - calendar.chores
```

Each chore's current due date appears as an all-day event. Further occurrences
within the date range being viewed are labelled **(projected)** and assume the
chore is completed on every scheduled due date. Navigating to another month
generates that month's events; no separate calendar events are stored.

Overdue chores remain on their actual due dates, with hypothetical projections
continuing from those dates. Completing, snoozing, skipping, restoring, or editing
a chore updates its calendar dates. Use the existing chore controls for these
actions; events cannot be edited directly in the calendar.

This is not completion history. Projections are neither recorded completions nor
committed due dates, and calendar automations can see them too. Keep using chore
sensors for authoritative due/overdue notifications.

Month and year schedules require whole-number intervals. If an older schedule
contains a fractional interval, its actual due date remains visible, but its
projections are omitted and a warning is logged until you edit the schedule.

Adding the configured integration hub creates the calendar; removing the hub
removes it. Installing integration files alone does not create a calendar.
Remove the hub before uninstalling the files through HACS.

## Use Chore Actions

Every chore device has **Complete**, **Snooze**, **Skip**, and **Reset next due
date** buttons. You can also call services from an automation or from
**Developer tools > Actions**.

For example, complete a chore or snooze it for five days:

```yaml
action: sh_chore_tracker.complete_chore
data:
  entity_id: sensor.chore_take_out_trash
```

```yaml
action: sh_chore_tracker.snooze_chore
data:
  entity_id: sensor.chore_water_plants
  days: 5
  reason: "Away on vacation"
```

Use the actual entity IDs in your Home Assistant instance. The snooze duration
is optional (default: 3 days; allowed: 1–365). Other available services include
`skip_chore`, `restore_chore`, `reset_next_due_date`, `undo_complete_chore`,
`reassign_chore`, `create_chore`, and `list_my_chores`.

### Automation example: notify when a chore is overdue

This example triggers when the chore's `status` attribute changes to `overdue`:

```yaml
alias: Notify when taking out the trash is overdue
triggers:
  - trigger: state
    entity_id: sensor.chore_take_out_trash
    attribute: status
    to: "overdue"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: Chore overdue
      message: Taking out the trash is overdue.
mode: single
```

Replace the example sensor and notification service with the ones from your
instance. Completion (and undo), snooze, skip, restore, reassignment, schedule reset,
and overdue transitions also emit `sh_chore_tracker_*` events (for example
`sh_chore_tracker_chore_completed`); see the service
reference for event names and payloads.

## Updates

Before installing future updates, back up your Home Assistant configuration and
check the [release notes](https://github.com/NateGr/sh_chore_tracker/releases)
for any required steps.

## Contributing And Support

- [Contributing](CONTRIBUTING.md): local setup, checks, and pull requests.
- [Maintainer guide](docs/maintainer.md): releases, GitHub setup, and migration.
- [Configuration reference](docs/configuration-reference.md): recurrence
  options, sensors, and setup details.
- [Service reference](docs/service-reference.md): service parameters, events,
  and additional automation examples.
- [Issues](https://github.com/NateGr/sh_chore_tracker/issues): bugs and suggestions.
- [Security policy](.github/SECURITY.md): privately report vulnerabilities.

## Acknowledgements

SmartHass Chore Tracker was inspired by
[Chore Helper for Home Assistant](https://github.com/VolantisDev/ha-chore-helper).
Thank you to VolantisDev and the project's contributors for their work on
recurring chore management in Home Assistant.

Distributed under the [MIT license](LICENSE).