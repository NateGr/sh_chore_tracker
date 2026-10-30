# Chore Tracker Service Reference

## Overview

The Chore Tracker hub provides chore lifecycle services and household create/list services. Chore-targeted services resolve the chore entity to its hub subentry.

The entity pickers for chore-targeted actions filter by the integration's device model `chore`. Summary devices use model `Summary` and are excluded. This filtering also works when chore entities are renamed.

Each chore device also exposes Complete, Snooze, Skip, and Reset next due date button entities. They invoke the same services described below, using the chore's current sensor entity ID. The Snooze button uses the default three-day duration; use the service for a custom duration or reason.

## Service Calls

### complete_chore

Mark a chore as completed and calculate the next due date.

#### Parameters

- **entity_id** (required): Entity ID of the chore to complete
- **completion_date** (optional): Custom completion date (ISO format)

#### Example

```yaml
service: sh_chore_tracker.complete_chore
data:
  entity_id: sensor.chore_take_out_trash
  completion_date: "2025-01-15T10:00:00"
```

#### Behavior

- Updates chore status to "complete"
- Increments completion count
- Calculates next due date using recurrence engine
- Fires `sh_chore_tracker_chore_completed` event
- Clears any snooze state

#### Events Fired

```yaml
event_type: sh_chore_tracker_chore_completed
data:
  entity_id: sensor.chore_take_out_trash
  completed_at: "2025-01-15T10:00:00"
  next_due_date: "2025-01-22T00:00:00+00:00"
  completion_count: 5
```

### snooze_chore

Temporarily postpone a chore for a specified number of days.

#### Parameters

- **entity_id** (required): Entity ID of the chore to snooze
- **days** (optional): Number of days to snooze (1-365, default: 3)
- **reason** (optional): Reason for snoozing

#### Example

```yaml
service: sh_chore_tracker.snooze_chore
data:
  entity_id: sensor.chore_clean_kitchen
  days: 3
  reason: "Company coming over"
```

#### Behavior

- Updates chore status to "snoozed"
- Pushes `next_due_date` forward by the snooze duration
- Sets snooze expiration (`snooze_until`) to the new due date
- On snooze expiry, automatically resolves to `due`, `pending`, or `overdue` from `next_due_date`

#### Events Fired

```yaml
event_type: sh_chore_tracker_chore_snoozed
data:
  entity_id: sensor.chore_clean_kitchen
  snoozed_for_days: 3
  new_due_date: "2025-01-18T00:00:00"
  snooze_count: 1
  reason: "Company coming over"
```

### skip_chore

Skip the current occurrence of a chore and move to the next scheduled date.

#### Parameters

- **entity_id** (required): Entity ID of the chore to skip
- **reason** (optional): Reason for skipping

#### Example

```yaml
service: sh_chore_tracker.skip_chore
data:
  entity_id: sensor.chore_mow_lawn
  reason: "Weather too wet"
```

#### Behavior

- Updates chore status to "skipped" temporarily
- Advances next due date from the current due date using the original recurrence pattern
- Allows restoration within 24-hour window
- Stores the latest skip timestamp and original due date, not a full audit log

#### Events Fired

```yaml
event_type: sh_chore_tracker_chore_skipped
data:
  entity_id: sensor.chore_mow_lawn
  skip_date: "2025-01-18T10:30:00"
  next_due_date: "2025-01-25T00:00:00"
  reason: "Weather too wet"
```

### restore_chore

Restore a recently skipped chore instance.

#### Parameters

- **entity_id** (required): Entity ID of the skipped chore to restore

#### Example

```yaml
service: sh_chore_tracker.restore_chore
data:
  entity_id: sensor.chore_mow_lawn
```

#### Behavior

- Works up to and including 24 hours after the latest skip, even across midnight
- Restores original due date
- Resolves status to pending, due, or overdue from the restored due date
- Marks the skip restored so it cannot be restored twice
- Completion, snooze, reset, or changing the first occurrence supersedes the
  previous skip. A second skip records a new original due date; restore undoes
  only that latest skip. Reassignment alone preserves restore eligibility.

#### Validation

- Must be called within 24 hours of skip
- Chore must retain an eligible skip timestamp and original due date; its
  visible status need not still be `skipped`
- Chore must not already be restored

#### Events Fired

```yaml
event_type: sh_chore_tracker_chore_restored
data:
  entity_id: sensor.chore_mow_lawn
  restore_date: "2025-01-18T11:00:00"
  original_skip_date: "2025-01-18T10:30:00"
```

### reassign_chore

Transfer chore responsibility to a different person.

#### Parameters

- **entity_id** (required): Entity ID of the chore to reassign
- **person_id** (required): Entity ID of the new assigned person

#### Example

```yaml
service: sh_chore_tracker.reassign_chore
data:
  entity_id: sensor.chore_vacuum_living_room
  person_id: person.jane
```

#### Behavior

- Updates assigned_person attribute
- Maintains all other chore state
- Persists the new assignment and emits a reassignment event; no persistent
  assignment audit-history list is maintained by this integration

#### Validation

- person_id must be a valid Person entity
- Person entity must exist in Home Assistant
- The assignment is saved to the chore subentry and survives reloads.

#### Events Fired

```yaml
event_type: sh_chore_tracker_chore_reassigned
data:
  entity_id: sensor.chore_vacuum_living_room
  old_person: person.john
  new_person: person.jane
  reassign_date: "2025-01-18T11:15:00"
```

### Removed: `configure_chore`

This service is no longer available. Add and edit chores through the hub's chore subentry controls.

### reset_next_due_date

Recalculate from the last completion, or from `first_occurrence_date` if the chore has never been completed. There is no replacement-date parameter. Reset clears snooze/skip overrides, preserves completion history, and leaves a past due date overdue.

```yaml
service: sh_chore_tracker.reset_next_due_date
data:
  entity_id: sensor.chore_vacuum_living_room
```

### undo_complete_chore

Restore the previous chore state after an accidental completion, within the
fixed 24-hour undo window. This window is not a configurable setting. Reset or
changing the first occurrence clears the completion snapshot.

```yaml
service: sh_chore_tracker.undo_complete_chore
data:
  entity_id: sensor.chore_vacuum_living_room
```

### create_chore (admin only)

Add a validated chore subentry to the household hub. This changes integration configuration and requires an administrator.

```yaml
service: sh_chore_tracker.create_chore
data:
  chore_name: Water plants
  recurrence_type: interval
  pattern_interval: 3
  interval_unit: days
  assigned_person: person.alice
```

### list_my_chores (service response)

Return chores assigned to the specified Person entity.

```yaml
service: sh_chore_tracker.list_my_chores
data:
  person_id: person.alice
response_variable: my_chores
```

Use this as a script/automation action with response capture. In Developer Tools,
request the response. This response-only service cannot be called without one.
The returned dictionary has a `chores` list; each item contains `chore_id`,
`entity_id`, `name`, `status`, `next_due_date`, and `days_until_due`. For example:

```yaml
chores:
  - chore_id: example_id
    entity_id: sensor.chore_water_plants
    name: Water plants
    status: pending
    next_due_date: "2026-11-01T00:00:00+00:00"
    days_until_due: 3
```

## Service Schemas

### Complete Chore Schema

```python
vol.Schema({
    vol.Required("entity_id"): cv.entity_ids,
    vol.Optional("completion_date"): cv.datetime,
})
```

### Snooze Chore Schema

```python
vol.Schema({
    vol.Required("entity_id"): cv.entity_ids,
    vol.Optional("days", default=DEFAULT_SNOOZE_DAYS): vol.All(
        vol.Coerce(int), vol.Range(min=1, max=365)
    ),
    vol.Optional("reason"): cv.string,
})
```

### Skip Chore Schema

```python
vol.Schema({
    vol.Required("entity_id"): cv.entity_ids,
    vol.Optional("reason"): cv.string,
})
```

### Restore Chore Schema

```python
vol.Schema({
    vol.Required("entity_id"): cv.entity_ids,
})
```

### Reassign Chore Schema

```python
vol.Schema({
    vol.Required("entity_id"): cv.entity_ids,
    vol.Required("person_id"): cv.entity_id,
})
```

## Automation Examples

### Complete Chore on Button Press

```yaml
automation:
  trigger:
    platform: state
    entity_id: binary_sensor.physical_chore_button
    from: "off"
    to: "on"
  action:
    service: sh_chore_tracker.complete_chore
    data:
      entity_id: sensor.chore_take_out_trash
```

### Snooze Chore When Away

```yaml
automation:
  trigger:
    platform: zone
    entity_id: person.john
    zone: zone.work
    event: enter
  condition:
    condition: state
    entity_id: sensor.chore_walk_dog
    attribute: status
    state: pending
  action:
    service: sh_chore_tracker.snooze_chore
    data:
      entity_id: sensor.chore_walk_dog
      days: 1
      reason: "At work"
```

### Daily Chore Reminder

```yaml
automation:
  trigger:
    platform: time
    at: "09:00:00"
  condition:
    condition: and
    conditions:
      - condition: template
        value_template: "{{ state_attr('sensor.chore_check_mail', 'status') in ['due', 'overdue'] }}"
  action:
    service: notify.mobile_app
    data:
      message: "Don't forget to check the mail!"
```

### Weekly Chore Assignment Rotation

```yaml
automation:
  trigger:
    platform: time
    at: "00:00:00"
  condition:
    condition: template
    value_template: "{{ now().weekday() == 0 }}" # Monday
  action:
    - service: sh_chore_tracker.reassign_chore
      data:
        entity_id: sensor.chore_vacuum
        person_id: >
          {% set people = ['person.alice', 'person.bob', 'person.charlie'] %}
          {% set week_num = (now().isocalendar()[1]) %}
          {{ people[week_num % people|length] }}
```

## Error Handling

### Common Errors

#### ServiceValidationError: Chore entity not found

- **Cause:** The entity registry does not map the entity to a loaded chore
  subentry owned by this integration.
- **Solution:** Use the chore sensor's current registered entity ID. Renamed
  chore sensors work; matching a `sensor.chore_` prefix alone is not sufficient.

#### ServiceValidationError: Person entity not found

- **Cause:** person_id doesn't exist
- **Solution:** Check Settings → Persons for valid entity IDs

#### ServiceValidationError: Invalid snooze days

- **Cause:** days parameter outside 1-365 range
- **Solution:** Use valid day count

### Validation Rules

- **entity_id**: Must map through the entity registry to this integration's
  loaded chore subentry. Chore actions accept one entity ID or a list.
- **person_id**: Must be valid Person entity
- **days**: 1-365 for snooze
- **completion_date**: Valid ISO datetime string
- **reason**: Optional string; no 255-character schema limit is imposed

## Event System

Lifecycle events use these exact names and payload keys:

| Event | Payload keys |
| --- | --- |
| `sh_chore_tracker_chore_completed` | `entity_id`, `completed_at`, `next_due_date`, `completion_count` |
| `sh_chore_tracker_chore_complete_undone` | `entity_id`, `undo_date`, `undone_completion_date`, `status`, `next_due_date`, `completion_count` |
| `sh_chore_tracker_chore_snoozed` | `entity_id`, `snoozed_for_days`, `new_due_date`, `snooze_count`, `reason` |
| `sh_chore_tracker_chore_skipped` | `entity_id`, `skip_date`, `next_due_date`, `reason` |
| `sh_chore_tracker_chore_restored` | `entity_id`, `restore_date`, `original_skip_date` |
| `sh_chore_tracker_chore_reassigned` | `entity_id`, `old_person`, `new_person`, `reassign_date` |
| `sh_chore_tracker_chore_overdue` | `entity_id`, `entry_id`, `chore_id`, `from_status`, `to_status`, `effective_date`, `next_due_date` |
| `sh_chore_tracker_chore_schedule_reset` | `entity_id`, `anchor_date`, `next_due_date`, `status` |

Create/list do not emit these lifecycle events. An ignored duplicate completion
does not emit another completion event. Overdue events fire once when a refresh
changes the status to overdue; there is no dedicated due-transition event.
Use a state trigger on the `status` attribute for due reminders. Due dates are
all-day values serialized at local start-of-day with a timezone offset; example
offsets depend on the Home Assistant timezone.

## Best Practices

### Service Call Timing

- Use `complete_chore` immediately after task completion
- Use `snooze_chore` for temporary postponements
- Use `skip_chore` for permanent skips of specific occurrences
- Use `restore_chore` within 24 hours if skip was accidental

### Automation Integration

- Combine with presence detection for smart snoozing
- Use calendar integration for scheduled reminders
- Monitor completion events for habit tracking

### Error Handling in Automations

Failed service calls normally stop an automation or script and appear in its
trace. This script checks the state after a successful blocking completion call;
it does not swallow service errors. Do not wait for a completion event after
calling complete: that event can already have fired before the wait starts.

```yaml
script:
  complete_and_check_chore:
    sequence:
      - service: sh_chore_tracker.complete_chore
        data:
          entity_id: sensor.chore_example
      - condition: template
        value_template: "{{ state_attr('sensor.chore_example', 'status') != 'complete' }}"
      - service: persistent_notification.create
        data:
          message: "The chore did not reach complete status. Check its current due date."
```

## Related Documentation

- [Configuration Reference](configuration-reference.md)
- [Contributor Guide](../CONTRIBUTING.md)
- [Maintainer Guide](maintainer.md)
