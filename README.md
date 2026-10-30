# SmartHass Chore Tracker

SmartHass Chore Tracker is a Home Assistant custom integration for scheduling,
assigning, and tracking household chores. It creates a household hub with
individual chore sensors, summary sensors, and buttons for common chore actions.

Requires **Home Assistant 2026.9.0 or newer**.

## Features

- Schedule chores using interval, weekly, monthly, or yearly recurrence.
- Assign chores to Home Assistant `person` entities.
- Track due dates, completion counts, overdue chores, and household summaries.
- Complete, snooze, skip, restore, and reset chores from their device buttons or
  Home Assistant services.
- Use chore services and events in automations.
- Persist chore schedules and lifecycle state across Home Assistant restarts.

## Installation

### HACS

1. In HACS, open **Integrations** and select the menu in the upper-right corner.
2. Select **Custom repositories** and add
   `https://github.com/NateGr/sh_chore_tracker` with category **Integration**.
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
        └── button.py
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
chore cannot start with a past first-occurrence date.

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
`recurrence_description`.

The automatically created household summary sensors are:

- `sensor.chores_next_due`: signed days until the nearest chore is due. Its
  attributes identify the chore and its due date.
- `sensor.chores_overdue_count`: number of chores currently overdue.

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
instance. Completion, snooze, skip, restore, reassignment, schedule reset, and
overdue transitions also emit `sh_chore_tracker_*` events; see the service
reference for event names and payloads.

## Upgrading

Back up your Home Assistant configuration before upgrading. Keep only one
installation of the integration active; do not install copies from multiple
repositories at the same time. The integration domain remains `sh_chore_tracker`.
Do not delete existing Home Assistant integration entries when switching
repositories. Tested migration instructions will be published before the old
repository is retired.

## Contributing And Support

- [Contributing](CONTRIBUTING.md): local setup, checks, and pull requests.
- [Maintainer guide](docs/maintainer.md): releases, GitHub setup, and migration.
- [Configuration reference](docs/configuration-reference.md): recurrence
  options, sensors, and setup details.
- [Service reference](docs/service-reference.md): service parameters, events,
  and additional automation examples.
- [Issues](https://github.com/NateGr/sh_chore_tracker/issues): bugs and suggestions.
- [Security policy](.github/SECURITY.md): privately report vulnerabilities.

Distributed under the [MIT license](LICENSE).