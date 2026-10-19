# Story 3.2: Chore Reassignment

**Epic**: 3 - Person Assignment & Advanced Features
**Story ID**: 3.2
**Priority**: Medium
**Status**: 🎯 Planned
**Estimated Effort**: 4 story points

## User Story

**As a** HASS user,
**I want to** reassign chores to different people,
**so that** I can adjust responsibilities as needed.

## Acceptance Criteria

- [ ] Service call available to reassign chore to new person
- [ ] Entity attribute updated with new person assignment
- [ ] Change history tracked for accountability
- [ ] Reassignment event fired for automation triggers
- [ ] UI supports easy reassignment through standard HASS controls
- [ ] Bulk reassignment supported for multiple chores

## Technical Implementation Details

### Components to Deliver

- **reassign_chore Service**: HASS service for changing assignments
- **History Tracking**: Assignment change audit trail
- **Event System**: `chore_reassigned` events for automation
- **Bulk Operations**: Multi-chore reassignment support
- **UI Integration**: Standard HASS service call interfaces

### Planned Service Implementation

```yaml
service: sh_chore_tracker.reassign_chore
data:
  entity_id: sensor.chore_name
  person_entity_id: person.jane_doe

# Bulk reassignment
service: sh_chore_tracker.reassign_chore
data:
  entity_id:
    - sensor.chore_1
    - sensor.chore_2
  person_entity_id: person.jane_doe
```

### Assignment History

- **Change Log**: Track all assignment changes
- **Accountability**: Who changed what when
- **Audit Trail**: Support for household management

### Planned Event Data

```json
{
  "event_type": "chore_reassigned",
  "data": {
    "entity_id": "sensor.chore_name",
    "chore_name": "Take out trash",
    "previous_person": "person.john_doe",
    "new_person": "person.jane_doe",
    "reassigned_at": "2025-10-11T10:30:00",
    "reassigned_by": "user_id"
  }
}
```

## Definition of Done

### 🎯 **Requirements (Planned)**

- [ ] All functional requirements to be implemented (reassignment service, history tracking, events)
- [ ] All acceptance criteria to be satisfied (service calls, UI integration, bulk operations)

### 🎯 **Coding Standards & Project Structure (Planned)**

- [ ] Reassignment service to follow HASS service patterns
- [ ] History tracking logic to be well-structured and efficient
- [ ] Bulk operation handling to be properly implemented
- [ ] Code to include comprehensive documentation and validation

### 🎯 **Testing (Planned)**

- [ ] Unit tests for reassign_chore service with various scenarios
- [ ] Tests for assignment history tracking and audit trail
- [ ] Tests for event firing during reassignment
- [ ] Tests for bulk reassignment functionality
- [ ] Integration tests for UI reassignment workflows

### 🎯 **Functionality & Verification (Planned)**

- [ ] Manual verification of reassignment service and UI integration
- [ ] Verification of history tracking and change accountability
- [ ] Testing of bulk reassignment scenarios and edge cases

### 🎯 **Story Administration (Planned)**

- [ ] Story implementation to be documented with reassignment patterns
- [ ] Assignment history design to be documented
- [ ] Story completion notes to include reassignment workflow lessons learned

### 🎯 **Dependencies, Build & Configuration (Planned)**

- [ ] Integration to build successfully with reassignment service
- [ ] Reassignment logic to pass linting and code quality checks
- [ ] Service registration to integrate properly with HASS

### 🎯 **Documentation (Planned)**

- [ ] Reassignment service methods to have comprehensive docstrings
- [ ] Assignment history tracking to be fully documented
- [ ] Bulk operations and UI integration to include usage examples

## Related Stories

- **Depends on**: Story 3.1 (Person Assignment Integration)
- **Enables**: Story 3.3 (Chore Edit and Delete)
- **Supports**: Dynamic household management workflows

---

_Last Updated: 2025-10-11_
_Implementation Status: Planned for Epic 3_
_Related Epic Status: Epic 3 - 🎯 Planned_
