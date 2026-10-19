# Epic 3: Person Assignment & Advanced Features

**Status**: 🎯 **PLANNED**
**Total Effort**: 15 story points
**Timeline**: Ready for implementation

## Epic Goal

Enable person assignments using HASS Person entities and provide enhanced chore management capabilities that make the integration production-ready for household management.

## Epic Description

This epic adds person assignment functionality and advanced management features that enhance the basic chore tracking system. Users can assign responsibilities to household members using native HASS Person entities, manage assignments dynamically, and edit/delete chores as needs change. This completes the integration's core feature set for household chore management.

## User Value

Users can assign chores to specific family members, change assignments as responsibilities shift, and manage their chore setup effectively. The integration becomes a comprehensive household management tool that leverages existing HASS Person entities for seamless integration.

## Stories in this Epic

### [Story 3.1: Person Assignment Integration](story-3.1-person-assignment-integration.md) 🎯

**Effort**: 6 story points | **Priority**: High

Integrates with HASS Person entities to enable chore assignments. Provides person selection in config flow and rich person information in entity attributes.

**Planned Deliverables**: Person entity integration, assignment UI, person attributes, automation support.

---

### [Story 3.2: Chore Reassignment](story-3.2-chore-reassignment.md) 🎯

**Effort**: 4 story points | **Priority**: Medium

Implements reassign_chore service for changing person assignments. Includes change tracking and bulk reassignment capabilities.

**Planned Deliverables**: reassign_chore service, assignment history, bulk operations, accountability tracking.

---

### [Story 3.3: Chore Edit and Delete](story-3.3-chore-edit-and-delete.md) 🎯

**Effort**: 5 story points | **Priority**: Medium

Provides complete chore lifecycle management through config flow options. Enables editing all chore properties and safe deletion with cleanup.

**Planned Deliverables**: Edit functionality, delete handling, confirmation dialogs, history preservation.

---

### [Story 3.4: Config Flow Translatable Labels](story-3.4-config-flow-i18n.md) 🎯

**Effort**: 2 story points | **Priority**: Low

Replaces all hardcoded SelectSelector option labels in the config flow with HA translation-key references so every dropdown (recurrence type, interval unit, weekdays, months) is fully translatable through the standard HA i18n system.

**Planned Deliverables**: Translation keys in strings.json for all selector options, en.json baseline translations, removal of hardcoded label strings from config_flow.py.

---

### [Story 3.5: Due-State Event Decision and Implementation](story-3.5-due-state-event-decision.md) 🎯

**Effort**: 2 story points | **Priority**: Low

Define and implement a clear event contract for the new `due` lifecycle state, including transition semantics, payload schema, and anti-spam guarantees.

**Planned Deliverables**: Decision record for due-event behavior, optional `sh_chore_tracker_chore_due` event implementation (if approved), regression tests for single-fire transition behavior, and service-reference updates.

---

## Epic Completion Criteria

- [ ] Person assignment integration with HASS Person entities
- [ ] Dynamic reassignment with change tracking
- [ ] Complete chore editing capabilities
- [ ] Safe chore deletion with proper cleanup
- [ ] Person-based filtering for automation scenarios
- [ ] Bulk operations for household management efficiency
- [ ] Config flow selector labels fully translatable via HA i18n system
- [ ] Due-state event contract decided and implemented (or explicitly deferred)

## Planned Technical Approach

### Person Entity Integration

- **Discovery**: Enumerate available HASS Person entities
- **Storage**: Store person entity IDs in chore configuration
- **Display**: Show person names in UI and entity attributes
- **Validation**: Handle person entity changes gracefully

### Service Extensions

- **reassign_chore**: Change person assignments with history
- **Bulk Operations**: Multi-chore operations for efficiency
- **Event System**: Assignment change events for automation

### Config Flow Enhancement

- **Person Selector**: Native HASS person entity selector
- **Edit Options**: Comprehensive chore property editing
- **Delete Handling**: Confirmation dialogs and cleanup

### Advanced Features

- **Assignment History**: Track all assignment changes
- **Bulk Management**: Household-scale chore management
- **Automation Integration**: Person-based automation triggers

## Dependencies

### Required from Epic 2

- ✅ Stable service handler architecture
- ✅ Robust config flow foundation
- ✅ Event system for notifications
- ✅ Reliable state persistence

### HASS Integration Points

- **Person Entities**: Integration with HASS person registry
- **Entity Attributes**: Extended attribute system
- **Service Definitions**: Additional service handlers
- **Config Options**: Enhanced options flow

## Success Metrics

### Functionality Metrics

- [ ] Person assignment success rate: 100%
- [ ] Reassignment operations complete < 1 second
- [ ] Edit operations preserve data integrity: 100%
- [ ] Delete operations clean up completely: 100%

### User Experience Metrics

- [ ] Assignment workflow intuitive and efficient
- [ ] Bulk operations significantly faster than individual
- [ ] Edit interface comprehensive and user-friendly
- [ ] Delete confirmations prevent accidental data loss

## Future Enhancements Beyond Epic 3

### Phase 2 Possibilities

- **Chore Groups/Categories**: Organize by room or type
- **SubActions**: Multi-step chore breakdowns
- **Calendar Integration**: Native HASS calendar platform
- **Advanced Automation**: Template-based chore creation

---

_Epic Status: 🎯 Planned | Ready for Implementation | Last Updated: 2025-10-11_
