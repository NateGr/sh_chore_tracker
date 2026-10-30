# Chore Tracker Configuration Reference

## Overview

This document describes the Chore Tracker household hub and its chore subentry flow. The guided flow shows only the fields that match the selected recurrence rule.

Use the Home Assistant UI for normal setup and edits. YAML examples in this document are illustrative only.

The hub uses native Home Assistant config subentries and requires Home Assistant 2026.9.0 or newer. Back up Home Assistant configuration and storage before installing or upgrading. Test upgrades from an existing Chore Tracker installation in a disposable Home Assistant instance before applying them to a live household.

## Configuration Methods

### UI Configuration Flow

1. Go to **Settings → Devices & Services → Integrations**.
2. Add **Chore Tracker**. The first flow creates the household hub and its first chore.
3. Add or edit later chores from the hub's chore subentry controls.

The hub owns chore configuration and lifecycle state. Each chore is a native config subentry and appears as a device linked beneath the Chore Tracker hub.

## Configuration Options

### Basic Fields

#### Chore Name (`chore_name`)

- **Type:** String
- **Required:** Yes
- **Description:** Display name for the chore.

#### Description (`chore_description`)

- **Type:** String
- **Required:** No
- **Description:** Optional details for the chore.

#### Assigned Person (`assigned_person`)

- **Type:** Select
- **Required:** No
- **Options:** Home Assistant person entities plus `none`
- **Description:** Person responsible for the chore.

### Common Scheduling Fields

#### Recurrence Type (`recurrence_type`)

- **Type:** Select
- **Required:** Yes
- **Options:** `interval`, `weekly`, `monthly`, `yearly`

#### Pattern Interval (`pattern_interval`)

- **Type:** Number
- **Required:** Yes
- **Range:** 1-999
- **Description:** Frequency multiplier for the selected recurrence rule.

#### First Occurrence Date (`first_occurrence_date`)

- **Type:** Date
- **Required:** Yes
- **Default on create:** Today
- **Default on edit:** Configured first occurrence; leaving it unchanged preserves the current runtime schedule
- **Description:** The first scheduled due date and schedule anchor.

Behavior:

- Create flow rejects past dates.
- If the selected date does not match the recurrence rule, the integration rolls it forward to the next valid occurrence.
- In edit flow, leaving the value unchanged preserves the current schedule.
- Changing the value reanchors the schedule and clears transient snooze or skip state.

## Household Entities

The hub exposes two aggregate entities in the automatically created **Overall summary** group:

- `sensor.chores_next_due`: signed days until the nearest scheduled chore; attributes identify the chore and due date.
- `sensor.chores_overdue_count`: current overdue chore count. A value greater than zero indicates overdue chores.

On the next integration load, generic summary IDs such as `sensor.chore_tracker` and `sensor.chore_tracker_2` are migrated to these defaults. Custom entity IDs are preserved; occupied defaults receive a numeric suffix. Update dashboards and automations that reference the old generic IDs. The redundant "Any chore overdue" binary sensor is removed; use the overdue count instead.

Existing hubs receive the summary group automatically on their next load, without recreating chores. The summary device moves into this group instead of appearing under "Devices that don't belong to a sub-entry". The integration includes local Smart Hass branding; restart Home Assistant and refresh the browser after updating to load the icon.

## Chore Device Controls

Each chore device includes four button entities alongside its sensor:

- **Complete** marks the chore complete and calculates the next due date.
- **Snooze** postpones the chore by the default three days. Use the `snooze_chore` action to specify a different duration or a reason.
- **Skip** skips the current occurrence and moves to the next scheduled one.
- **Reset next due date** recalculates the due date from the last completion or first occurrence and clears snooze and skip overrides.

These controls are available on the chore's device page and can be added to dashboards. They do not modify Home Assistant's standard sensor more-info popup. The overall summary device has no chore action buttons.

## Pattern-Specific Fields

### Interval Recurrence

#### Interval Unit (`interval_unit`)

- **Type:** Select
- **Required:** When `recurrence_type=interval`
- **Options:** `days`, `weeks`, `months`, `years`

### Weekly Recurrence

#### Weekly Days (`weekly_days`)

- **Type:** Multi-select
- **Required:** When `recurrence_type=weekly`
- **Options:** monday, tuesday, wednesday, thursday, friday, saturday, sunday

### Monthly Recurrence

#### Monthly Rule Type (`monthly_mode`)

- **Type:** Select
- **Required:** When `recurrence_type=monthly`
- **Options:** `day_of_month`, `ordinal_weekday`

#### Monthly Day (`monthly_day`)

- **Type:** Number
- **Required:** When `recurrence_type=monthly` and `monthly_mode=day_of_month`
- **Range:** 1-31
- **Description:** Numeric day of month with smart end-of-month overflow.

#### Monthly Ordinal (`monthly_ordinal`)

- **Type:** Select
- **Required:** When `recurrence_type=monthly` and `monthly_mode=ordinal_weekday`
- **Options:** `first`, `second`, `third`, `fourth`, `fifth`, `last`

#### Monthly Weekday (`monthly_weekday`)

- **Type:** Select
- **Required:** When `recurrence_type=monthly` and `monthly_mode=ordinal_weekday`
- **Options:** monday, tuesday, wednesday, thursday, friday, saturday, sunday

Monthly ordinal rules support patterns such as the 1st Monday, 3rd Wednesday, 5th Sunday, and last Friday. For `5th` weekday rules, months without a fifth matching weekday are skipped until the next valid month.

### Yearly Recurrence

#### Yearly Month (`yearly_month`)

- **Type:** Select
- **Required:** When `recurrence_type=yearly`
- **Options:** 1-12

#### Yearly Day (`yearly_day`)

- **Type:** Number
- **Required:** When `recurrence_type=yearly`
- **Range:** 1-31

## Entity State Contract

### Sensor State

The primary sensor state is a **signed integer** representing days until the chore is due.

| Value | Meaning |
|-------|---------|
| Negative (e.g. `-3`) | Overdue by that many days |
| `0` | Due today |
| Positive (e.g. `7`) | Due in that many days |

The state has unit `d` (days) and state class `measurement`.

### `status` Attribute

The `status` attribute carries the chore's lifecycle string value.

| Value | Meaning |
|-------|---------|
| `pending` | Scheduled but not yet due |
| `due` | Due today |
| `overdue` | Past due date |
| `snoozed` | Temporarily deferred |
| `skipped` | Current instance skipped |
| `complete` | Marked complete, awaiting next recurrence |

Use `status` in automations where you previously checked the entity state directly:

```yaml
# Old (no longer works — state is now an integer)
condition:
  alias: "Chore is overdue"
  condition: state
  entity_id: sensor.chore_vacuum
  state: "overdue"

# New
condition:
  alias: "Chore is overdue"
  condition: template
  value_template: "{{ state_attr('sensor.chore_vacuum', 'status') == 'overdue' }}"
```

### `integration_domain` Attribute

Every chore entity exposes `integration_domain: sh_chore_tracker`. Use this for reliable entity filtering that survives entity renames.

### Recommended auto-entities Filter

```yaml
type: custom:auto-entities
card:
  type: entities
filter:
  include:
    - attribute:
        integration_domain: sh_chore_tracker
  sort:
    method: state
    numeric: true
```

This shows all chore entities sorted by `days_until_due` (most overdue first).

To show only overdue chores (`below: 0`):

```yaml
type: custom:auto-entities
card:
  type: entities
filter:
  include:
    - attribute:
        integration_domain: sh_chore_tracker
      state: < 0
  sort:
    method: state
    numeric: true
```



### Daily Chore

```yaml
chore_name: "Check mail"
recurrence_type: "interval"
pattern_interval: 1
interval_unit: "days"
first_occurrence_date: "2026-06-01"
```

### Weekly Chore

```yaml
chore_name: "Mow lawn"
recurrence_type: "weekly"
pattern_interval: 1
weekly_days: ["saturday"]
first_occurrence_date: "2026-06-06"
```

### Quarterly Day-of-Month Chore

```yaml
chore_name: "Service HVAC"
recurrence_type: "monthly"
pattern_interval: 3
monthly_mode: "day_of_month"
monthly_day: 1
first_occurrence_date: "2026-07-01"
```

### Monthly Ordinal Chore

```yaml
chore_name: "Replace filter"
recurrence_type: "monthly"
pattern_interval: 1
monthly_mode: "ordinal_weekday"
monthly_ordinal: "first"
monthly_weekday: "monday"
first_occurrence_date: "2026-06-01"
```

### Yearly Chore

```yaml
chore_name: "Tax preparation"
recurrence_type: "yearly"
pattern_interval: 1
yearly_month: 4
yearly_day: 15
first_occurrence_date: "2027-04-15"
```

## Validation Rules

### Required Fields

- `chore_name`
- `recurrence_type`
- `pattern_interval`
- `first_occurrence_date`

### Conditional Requirements

- When `recurrence_type=interval`: `interval_unit`
- When `recurrence_type=weekly`: `weekly_days`
- When `recurrence_type=monthly` and `monthly_mode=day_of_month`: `monthly_day`
- When `recurrence_type=monthly` and `monthly_mode=ordinal_weekday`: `monthly_ordinal` and `monthly_weekday`
- When `recurrence_type=yearly`: `yearly_month` and `yearly_day`

### Smart Overflow and Normalization Rules

- Monthly day-of-month rules use the last day of the month when the chosen day does not exist.
- Monthly `fifth` weekday rules skip months that do not contain that fifth weekday.
- Yearly February 29 rolls to February 28 in non-leap years.
- First occurrence and reset dates are normalized forward to the next valid occurrence when necessary.

## Reset Service Contract

The `reset_next_due_date` service uses the exact same normalization rules as `first_occurrence_date`. If you provide a replacement date that does not match the active recurrence rule, the date is rolled forward to the next valid occurrence before the chore is updated.

## Related Documentation

- [Product Requirements Document](../docs/prd.md)
- [Architecture Document](../docs/architecture.md)
- [Service Reference](service-reference.md)
- [Developer Guide](developer-guide.md)
