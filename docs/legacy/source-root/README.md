# Chore Tracker

Chore Tracker is a Home Assistant hub integration for recurring household tasks. One hub owns chore subentries, per-chore sensors/devices, lifecycle state, aggregate sensors, and automation services.

## Features

- Interval recurrence: every X days, weeks, months, or years after completion.
- Weekly recurrence: one or more weekdays on a repeating weekly cadence.
- Monthly recurrence: either a day-of-month rule or an ordinal weekday rule such as 1st Monday or last Friday.
- Yearly recurrence: specific month and day with smart overflow handling.
- First occurrence anchoring: new chores start from an explicit first scheduled date instead of implicitly starting from today.
- Household sensors: report the nearest chore due date, overdue count, and whether any chore is overdue.
- Reset next due date: recompute from the last completion, or the first occurrence if never completed.
- Hub services: add a chore and list chores assigned to a selected Person.

## Configuration Model

The integration uses a guided, branching flow when adding or editing a chore. Only the fields for the selected recurrence type are shown. Chore configuration is stored on its hub subentry; mutable lifecycle state is stored by stable chore ID.

Core fields:

- `chore_name`
- `chore_description`
- `recurrence_type`
- `pattern_interval`
- `assigned_person`
- `first_occurrence_date`

Pattern-specific fields:

- Interval: `interval_unit`
- Weekly: `weekly_days`
- Monthly day-of-month: `monthly_mode=day_of_month` with `monthly_day`
- Monthly ordinal weekday: `monthly_mode=ordinal_weekday` with `monthly_ordinal` and `monthly_weekday`
- Yearly: `yearly_month` and `yearly_day`

### First Occurrence Behavior

- On create, `first_occurrence_date` cannot be in the past.
- If the chosen first occurrence does not match the active recurrence rule, the integration rolls it forward to the next valid occurrence.
- In edit flow, the field defaults to the configured first occurrence.
- If the value is unchanged, runtime state is preserved.
- If the value changes, the schedule is reanchored and transient snooze or skip state is cleared.

### Reset Behavior

`reset_next_due_date` has no date override. It calculates the next occurrence from `last_completed_date`; if the chore has never been completed, it uses the normalized `first_occurrence_date`. Snooze and skip overrides are cleared, completion history is retained, and a derived date in the past remains overdue.

### Monthly Ordinal Rules

Monthly chores now support two modes:

- `day_of_month`: examples include the 1st, 15th, or 31st with smart end-of-month overflow.
- `ordinal_weekday`: examples include the 1st Monday, 3rd Wednesday, 5th Sunday, or last Friday.

For `5th` weekday rules, months without a 5th matching weekday are skipped entirely. The integration advances to the next month that actually contains that occurrence.

## Services

The integration provides nine services for chore management and household summaries:

### `complete_chore`

Mark a chore as completed and automatically calculate the next due date.

```yaml
service: sh_chore_tracker.complete_chore
data:
  entity_id: sensor.chore_dishwashing_weekly
```

### `snooze_chore`

Temporarily postpone a chore for a specified number of days.

```yaml
service: sh_chore_tracker.snooze_chore
data:
  entity_id: sensor.chore_dishwashing_weekly
  days: 3
  reason: "Guest coming over"
```

### `skip_chore`

Skip the current occurrence of a chore and move to the next scheduled date.

```yaml
service: sh_chore_tracker.skip_chore
data:
  entity_id: sensor.chore_dishwashing_weekly
  reason: "Vacation this week"
```

### `restore_chore`

Restore a recently skipped chore within a 24-hour window.

```yaml
service: sh_chore_tracker.restore_chore
data:
  entity_id: sensor.chore_dishwashing_weekly
```

### `reassign_chore`

Transfer chore responsibility to a different person.

```yaml
service: sh_chore_tracker.reassign_chore
data:
  entity_id: sensor.chore_dishwashing_weekly
  person_id: person.john_doe
```

### `undo_complete_chore`

Undo a recent completion within the configured restore window.

```yaml
service: sh_chore_tracker.undo_complete_chore
data:
  entity_id: sensor.chore_dishwashing_weekly
```

### `reset_next_due_date`

Reset a chore's next due date using the same normalization rules as the first occurrence field.

```yaml
service: sh_chore_tracker.reset_next_due_date
data:
  entity_id: sensor.chore_dishwashing_weekly
```

The next date is derived from completion history and the recurrence rule. Resetting clears active snooze/skip state but preserves completion history.

### `create_chore`

Add a chore to the hub. This configuration-changing service is admin-only.

```yaml
service: sh_chore_tracker.create_chore
data:
  chore_name: Water plants
  recurrence_type: interval
  pattern_interval: 3
  interval_unit: days
  assigned_person: person.alice
```

### `list_my_chores`

Return chores assigned to a Person entity as a service response.

```yaml
service: sh_chore_tracker.list_my_chores
data:
  person_id: person.alice
```

## 📦 Installation

### Option 1: HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations" → "Custom Repositories"
3. Add `https://github.com/NateGr/ha-chore-tracker` as a custom repository
4. Search for "Chore Tracker" and install
5. Restart Home Assistant

### Option 2: Manual Installation

1. Download the `custom_components/sh_chore_tracker/` directory from this repository
2. Copy it to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Home Assistant Setup

The integration appears once in the Integrations panel. Chores are managed as subentries and appear as chore devices beneath the household hub:

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Click **"Add Integration"** → Search for "Chore Tracker"
3. Follow the wizard to create the hub and its first chore.
4. Add or edit later chores from the hub's subentry controls.

## Testing

Focused tests cover the recurrence engine, date normalization helpers, config flow, and service behavior.

```bash
PYTHONPATH=/workspaces/ha-chore-tracker pytest tests/test_date_utils.py tests/test_init.py tests/test_config_flow.py tests/test_services.py -q
```

## Troubleshooting

- If a new chore starts on an unexpected date, check `first_occurrence_date` and the active recurrence rule. The integration may have rolled the date forward to the next valid occurrence.
- Reset uses the last completion as its recurrence anchor; a chore with no completion uses its configured first occurrence.
- If services are missing after startup, restart Home Assistant and check the integration logs.

### Contributing

This project uses the BMad development methodology. See `.bmad-core/` for workflow documentation and contribution guidelines.

## 📚 Documentation

- **[Product Requirements](docs/prd.md)** - Detailed specifications
- **[Technical Architecture](docs/architecture.md)** - Implementation details
- **[Service Reference](docs/service-reference.md)** - All service calls with parameters and examples
- **[Configuration Reference](docs/configuration-reference.md)** - Configuration options guide
- **[Developer Guide](docs/developer-guide.md)** - Contribution and development workflow
- **[Debugging Safety](DEBUG_SAFETY.md)** - Development environment guide
- **[Project Analysis](docs/analysis/REVIEW_SUMMARY_START_HERE.md)** - Technical analysis and review

## 📋 Project Status

**Current Phase**: Testing & Validation (Post-Implementation)
**Code Maturity**: Development (hub migration and validation in progress)
**Architecture**: One household hub entry with chore subentries

### ✅ Completed (Epic 1 & 2)

- Hub entry and chore subentry architecture
- Advanced recurrence patterns and service handlers
- Comprehensive testing and validation
- Migration from helper-era and device-per-chore entries

### 🚧 Next Steps

- Live Home Assistant instance validation
- Documentation updates and alignment
- Epic 3 & 4 requirements planning (calendar integration, analytics)

---

**Version**: 0.5.0
**Home Assistant**: 2025.1+ (native config subentries required)
