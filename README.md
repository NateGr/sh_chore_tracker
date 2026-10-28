# SmartHass Chore Tracker

SmartHass Chore Tracker is a Home Assistant custom integration for scheduling,
assigning, and tracking household chores. It creates a household hub with
individual chore sensors, summary sensors, and buttons for common chore actions.

> **Branch status:** These instructions describe the `import-core-code` branch.
> It has not been merged into the repository's default `main` branch, and there
> are no published releases or tags yet. The manual installation below installs
> this branch directly. This repository is private, so you need repository
> access to download it. HACS and release-archive installation are not available
> until the integration is published from a HACS-installable branch.

The integration uses native Home Assistant config subentries and therefore
requires **Home Assistant 2025.1 or newer**. The minimum supported release and
startup migration behavior have not yet been verified. Back up your Home
Assistant configuration and storage before installing or upgrading.

## Features

- Schedule chores using interval, weekly, monthly, or yearly recurrence.
- Assign chores to Home Assistant `person` entities.
- Track due dates, completion counts, overdue chores, and household summaries.
- Complete, snooze, skip, restore, and reset chores from their device buttons or
  Home Assistant services.
- Use chore services and events in automations.
- Persist chore schedules and lifecycle state across Home Assistant restarts.

## Install from `import-core-code`

This is a manual installation from the current development branch, not an
installation from a published release.

1. Download the [import-core-code branch ZIP](https://github.com/NateGr/sh_chore_tracker/archive/refs/heads/import-core-code.zip).
2. Extract the ZIP and copy its `custom_components/chore_tracker` directory
   into `<config>/custom_components/chore_tracker`, where `<config>` is your
   Home Assistant configuration directory. Create `custom_components` if it
   does not already exist.
3. Confirm that `manifest.json` is at
   `<config>/custom_components/chore_tracker/manifest.json`.
4. Restart Home Assistant.

For example, the resulting directory layout should look like this:

```text
<config>/
└── custom_components/
    └── chore_tracker/
        ├── __init__.py
        ├── manifest.json
        ├── sensor.py
        └── button.py
```

The repository's default branch is currently `main`, and it does not yet
contain this integration. Do not add this repository as a HACS custom
integration until the integration has been merged to a HACS-installable branch
and a release has been published. Once available, install **SmartHass Chore
Tracker** through HACS, restart Home Assistant, and add the integration from
**Settings > Devices & services**.

## Configure the Household

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
action: chore_tracker.complete_chore
data:
  entity_id: sensor.chore_take_out_trash
```

```yaml
action: chore_tracker.snooze_chore
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
overdue transitions also emit `chore_tracker_*` events; see the service
reference for event names and payloads.

## Existing Installations and Upgrades

The integration domain is `chore_tracker`. Back up Home Assistant before
installing or upgrading, and do not install copies of the integration from
multiple repositories at the same time. This branch includes startup migration
code for legacy per-chore entries, but the migration and minimum supported
Home Assistant version have not been verified in a live upgrade; review the
backup and migration implications before using it with an existing installation.

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