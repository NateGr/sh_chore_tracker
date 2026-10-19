# Story 3.1: Person Assignment Integration

**Epic**: 3 - Person Assignment & Advanced Features
**Story ID**: 3.1
**Priority**: High
**Status**: 🎯 Planned
**Estimated Effort**: 6 story points

## User Story

**As a** HASS user,
**I want to** assign chores to specific people using HASS Person entities,
**so that** household members have clear responsibility for tasks.

## Acceptance Criteria

- [ ] Chore creation/edit includes person assignment dropdown
- [ ] Dropdown populated with available HASS Person entities
- [ ] Entity attribute shows assigned person name and ID
- [ ] Unassigned chores supported (personal tasks)
- [ ] Person entity changes reflected in chore assignments
- [ ] Person-based filtering possible for automations

## Technical Implementation Details

### Components to Deliver

- **Person Entity Integration**: Integration with HASS person registry
- **Assignment UI**: Config flow person selection dropdown
- **Entity Attributes**: `assigned_person` attribute with person info
- **Dynamic Updates**: Real-time person entity change handling
- **Automation Support**: Person-based automation triggers

### Person Integration Strategy

- **Entity Discovery**: Enumerate available person entities
- **Assignment Storage**: Store person entity ID in chore config
- **Display Logic**: Show person name in UI and attributes
- **Validation**: Handle deleted/renamed person entities gracefully

### Planned Attributes

```json
{
  "assigned_person": {
    "entity_id": "person.john_doe",
    "name": "John Doe",
    "assigned_at": "2025-10-11T10:00:00"
  }
}
```

### Config Flow Enhancement

- **Person Selector**: Native HASS person entity selector
- **Optional Assignment**: Support for unassigned chores
- **Assignment Updates**: Allow changing assignments via options flow

## Definition of Done

### 🎯 **Requirements (Planned)**

- [ ] All functional requirements to be implemented (person assignment, UI integration, entity attributes)
- [ ] All acceptance criteria to be satisfied (person dropdown, assignments, filtering)

### 🎯 **Coding Standards & Project Structure (Planned)**

- [ ] Person integration code to follow HASS entity registry patterns
- [ ] Config flow person selector to use native HASS components
- [ ] Person entity validation and error handling to be implemented
- [ ] Code to include comprehensive documentation and comments

### 🎯 **Testing (Planned)**

- [ ] Unit tests for person assignment logic and validation
- [ ] Tests for person entity discovery and selection
- [ ] Tests for person entity change handling (rename, delete scenarios)
- [ ] Integration tests for config flow person selector
- [ ] Tests for automation integration and person-based filtering

### 🎯 **Functionality & Verification (Planned)**

- [ ] Manual verification of person assignment UI and functionality
- [ ] Verification of person entity integration and attribute updates
- [ ] Testing of person entity change scenarios and graceful handling

### 🎯 **Story Administration (Planned)**

- [ ] Story implementation to be documented with decisions and approach
- [ ] Person integration design patterns to be documented
- [ ] Story completion notes to include person entity integration lessons learned

### 🎯 **Dependencies, Build & Configuration (Planned)**

- [ ] Integration to build successfully with person entity dependencies
- [ ] Person entity integration to pass linting and code quality checks
- [ ] Config flow person selector to integrate seamlessly with HASS UI

### 🎯 **Documentation (Planned)**

- [ ] Person assignment methods to have comprehensive docstrings
- [ ] Person entity integration to be fully documented with examples
- [ ] User documentation to include person assignment setup and usage

## Related Stories

- **Depends on**: [Epic 2 complete](../epic-2/README.md) (All lifecycle management)
- **Enables**: [Story 3.2: Chore Reassignment](story-3.2-chore-reassignment.md)
- **Foundation for**: Person-based automation workflows
- **Epic**: [Epic 3 Overview](README.md)
- **Previous Epic**: [Epic 2: Advanced Chore Lifecycle Management](../epic-2/README.md)

---

_Last Updated: 2025-10-11_
_Implementation Status: Planned for Epic 3_
_Related Epic Status: Epic 3 - 🎯 Planned_
