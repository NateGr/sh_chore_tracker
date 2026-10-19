# Changelog

All notable changes to the HASS sh-chore-tracker Integration will be documented in this file.

## [0.5.0] - Unreleased - Household Hub Architecture

### Architecture

- Replaced per-chore config entries with one household hub and native chore subentries.
- Consolidated lifecycle state under one hub coordinator and Store map keyed by stable chore ID.
- Added next-due, overdue-count, and any-overdue household entities.
- Added admin-only `create_chore` and response-only `list_my_chores` services.
- Migrates helper-era and device-per-chore entries while preserving chore entity IDs, devices, and runtime history.

### Service behavior

- Removed `configure_chore`; use the hub's chore subentry controls to edit chores.
- `reset_next_due_date` now derives from the last completion, or the first occurrence if never completed. It clears snooze/skip overrides, preserves completion history, and has no date override.
- Reassignment now persists in chore subentry configuration.

### Breaking changes

- Chores move under one Chore Tracker hub entry in the Integrations panel.
- Native config subentries require Home Assistant 2025.1 or newer.

### Sensor state contract

### 💥 Breaking Changes

#### Sensor state is now a signed integer (`days_until_due`)

The entity's primary state has changed from a status string to a **signed integer** representing
days until the chore is due.

| Old state value | New equivalent |
|-----------------|----------------|
| `"pending"` | Positive integer (days remaining) |
| `"due"` | `0` |
| `"overdue"` | Negative integer (days overdue) |
| `"snoozed"` | Positive integer + `status` attribute = `"snoozed"` |
| `"skipped"` | Positive integer + `status` attribute = `"skipped"` |
| `"complete"` | Positive integer + `status` attribute = `"complete"` |

**Migration:** Replace any automation that checks `state == "pending"` (or any other status
string) with a `status` attribute check:

```yaml
# Old
condition:
  condition: state
  entity_id: sensor.chore_vacuum
  state: "overdue"

# New
condition:
  condition: template
  value_template: "{{ state_attr('sensor.chore_vacuum', 'status') == 'overdue' }}"
```

#### `days_until_due` attribute kept and consistent with state

`days_until_due` remains available as an attribute and will always equal the sensor's state value. Both `states(entity_id) | int` and `state_attr(entity_id, 'days_until_due')` return the same signed integer.

### ✨ New Attributes

- **`status`** — The chore lifecycle string (`pending`, `due`, `overdue`, `snoozed`, `skipped`, `complete`).
- **`integration_domain`** — Always `sh_chore_tracker`. Use this for reliable entity filtering in auto-entities cards without relying on entity ID prefixes.

### 📚 Documentation Updates

- `docs/configuration-reference.md` updated with entity state contract, `status` attribute reference, and recommended auto-entities filter.

## [0.3.0-rc4] - 2026-05-31 - Lifecycle Queue Semantics Alignment

### ✨ Lifecycle and Behavior Updates

- **Complete rollover queueing**: completed chores now transition to `pending` after day rollover when `next_due_date` is still in the future.
- **Skipped rollover queueing**: skipped chores now transition to `pending` after day rollover when `next_due_date` is still in the future.
- **Due/overdue precedence preserved**: complete/skipped chores still transition to `due` or `overdue` once `next_due_date` is reached.

### 🧪 Test Coverage Additions

- Added coordinator lifecycle tests for complete/skipped rollover-to-pending behavior.
- Added regression coverage ensuring complete remains complete on the same day before future due dates.

### 📚 Documentation Updates

- Clarified coordinator-cadence lifecycle evaluation notes in architecture docs.

## [0.3.0-rc1] - 2026-05-27 - Lifecycle Semantics & Runtime Stabilization

### ✨ Lifecycle and Behavior Updates

- **Date-only lifecycle semantics**: chore status transitions now evaluate on local calendar dates rather than timestamp precision.
- **New `due` state**: chores due today are now represented explicitly as `due`.
- **Improved state transitions**: complete/snoozed/skipped flows now align to day-rollover behavior in the coordinator.
- **Overdue transition event support**: `sh_chore_tracker_chore_overdue` is emitted on transition into overdue (single-fire transition behavior).

### 🐛 Fixes

- **`configure_chore` service fix**: replaced unsupported reconfigure flow init with options flow init.
- **`days_until_due` correction**: switched to date-delta semantics so tomorrow reports `1` and day-after-tomorrow reports `2`.
- **Sensor attribute stability**: hardened datetime handling and canonical field mapping for completion metadata.

### 🔧 UX and Configuration Improvements

- **Weekly day ordering**: weekly selector options now render in natural order (Monday through Sunday).
- **Config labels**: improved configuration label coverage and clarity in translation files.

### 🧪 Test Coverage Additions

- Added coordinator lifecycle tests for date-only transitions and overdue event emission behavior.
- Added regression test coverage for `configure_chore` options-flow startup path.
- Added sensor regression tests for `days_until_due` date-delta behavior.

### 📚 Architecture and Backlog Updates

- Documented lifecycle state diagram and date-only transition model.
- Recorded due-event decision path and added backlog tracking story for future due-event contract discussion.

## [0.2.0] - 2025-10-13 - Config Flow & Testing Complete

### ✨ Major Features Added

- **All-Day Event Architecture**: Complete transition from time-based to date-only calculations
- **Unified Pattern System**: `CONF_PATTERN_INTERVAL` and `CONF_INTERVAL_UNIT` across all recurrence types
- **Modern Config Flow**: Updated to use Home Assistant's selector-based schema
- **Comprehensive Test Suite**: 67 unit tests covering all components and edge cases

### 🔧 Config Flow Updates

- **Modern UI Components**: Replaced basic input fields with SelectSelector and NumberSelector
- **Person Assignment Integration**: Dropdown selection of Home Assistant Person entities
- **Legacy Data Migration**: Automatic conversion from old `interval_days` to `pattern_interval`
- **Input Validation**: Comprehensive validation for all recurrence pattern types
- **String Value Support**: Fixed SelectSelector month options to use proper string values

### 🧪 Testing Infrastructure

#### Config Flow Tests (18 tests)

- Schema generation with defaults and existing data
- Legacy data migration validation
- Person entity integration testing
- Input validation for all recurrence types
- Field constraint verification

#### DateCalculator Tests (22 tests)

- Smart month addition with day adjustment (Jan 31 → Feb 29)
- Leap year handling for February dates
- Weekday occurrence calculations
- Year rollover scenarios and edge cases
- Interval unit conversions (days, weeks, months, years)

#### RecurrenceEngine Tests (25 tests)

- All pattern types: interval, weekly, monthly, yearly
- Multi-interval patterns: bi-weekly, quarterly, bi-annual
- Smart date handling for month-end scenarios
- Leap day calculations and edge cases
- Pattern validation and description generation

#### Integration Tests (2 tests)

- Async setup and unload entry functionality
- Platform integration validation

### 🐛 Bug Fixes

- **Bi-Weekly Logic**: Fixed RecurrenceEngine calculation for multi-week patterns (Jan 1 → Jan 17 for 2-week Wednesday pattern)
- **DateCalculator Edge Cases**: Corrected behavior for empty weekday lists and invalid units
- **SelectSelector Values**: Fixed month options to use string values instead of integers
- **Async Test Configuration**: Proper pytest-asyncio marks for all async test methods

### 🔄 Architectural Improvements

- **All-Day Event Model**: Eliminated time complexity, focusing purely on date calculations
- **Smart Date Arithmetic**: Enhanced month/year calculations with proper overflow handling
- **Functional Composition**: RecurrenceEngine delegates to specialized DateCalculator methods
- **Legacy Support**: Maintains backward compatibility while enabling modern features

### 🎯 Technical Enhancements

- **Pattern Interval Unification**: Single `pattern_interval` field replaces pattern-specific intervals
- **Interval Unit System**: Flexible unit specification (days, weeks, months, years) for interval patterns
- **Async Mock Support**: Proper AsyncMock configuration for integration tests
- **Import Organization**: Clean separation of concerns between modules

### 📋 TODOs Added

1. **Live Testing**: Validate changes in actual Home Assistant instance
2. **State Field Architecture**: Define entity state content and automation use cases

---

## [0.1.0] - 2024 - Initial Architecture & Planning

### 🏗️ Project Foundation

- **Project Brief**: Vision and requirements definition
- **Technical Architecture**: Complete implementation blueprint
- **RecurrenceEngine Core**: Initial pattern calculation logic
- **Development Environment**: VS Code DevContainer setup with debugging support
