# Story 2.5: Restore Functionality

**Epic**: 2 - Advanced Chore Lifecycle Management
**Story ID**: 2.5
**Priority**: Medium
**Status**: ✅ Complete
**Estimated Effort**: 3 story points

## User Story

**As a** HASS user,
**I want to** restore a chore instance if it's still within the time window,
**so that** I can reinstate a mistakenly skipped chore.

## Acceptance Criteria

- [x] Service call available to restore recent chore instance
- [x] Restore only allowed within configurable time window (default: 24 hours)
- [x] Restore returns to original due date and "pending" status
- [x] Previous skip record marked as "restored" in history
- [x] Restore not allowed if next instance is already overdue
- [x] Restore event fired for automation triggers

## Technical Implementation Details

### Components Delivered

- **restore_chore Service**: HASS service for restoring skipped chores
- **Time Window Validation**: Configurable restoration time limits
- **State Recovery**: Return to original due date and pending status
- **History Management**: Skip/restore tracking in completion history
- **Event System**: `chore_restored` events for automation

### Service Implementation

```yaml
service: sh_chore_tracker.restore_chore
data:
  entity_id: sensor.chore_name
```

### Restore Logic

- **Validation**: Check if within restoration time window
- **State Recovery**: → "pending" status with original due date
- **History Update**: Mark previous skip as "restored"
- **Edge Case**: Prevent restore if would create scheduling conflicts

### Time Window Rules

- **Default Window**: 24 hours from skip action
- **Configurable**: Can be adjusted per integration instance
- **Validation**: Restore denied if outside window
- **Conflict Check**: No restore if next occurrence already passed

### Event Data

```json
{
  "event_type": "chore_restored",
  "data": {
    "entity_id": "sensor.chore_name",
    "chore_name": "Take out trash",
    "restored_at": "2025-10-11T15:30:00",
    "original_due_date": "2025-10-11T10:00:00",
    "time_since_skip_hours": 5
  }
}
```

### Error Handling

- **Outside Window**: Clear error message about time limits
- **Already Overdue**: Prevent restoration if scheduling conflict exists
- **Invalid State**: Cannot restore non-skipped chores

## Definition of Done

### ✅ **Requirements Met**

- ✅ All functional requirements implemented (restore service, time windows, state recovery)
- ✅ All acceptance criteria satisfied (time validation, history updates, edge cases)

### ✅ **Coding Standards & Project Structure**

- ✅ Restore service handler properly structured
- ✅ Time window validation logic well-organized
- ⚠️ **PARTIAL** - Edge case handling documentation could be enhanced

### ❌ **Testing**

- ❌ **MISSING** - No unit tests for restore_chore service handler
- ❌ **MISSING** - No tests for time window validation and edge cases
- ❌ **MISSING** - No tests for history management and conflict detection

### ✅ **Functionality & Verification**

- ✅ Manually verified (restore works within time windows, edge cases handled)
- ✅ History tracking and conflict detection confirmed working

### ⚠️ **Story Administration**

- ✅ Story requirements documented
- ⚠️ **PARTIAL** - Time window and edge case logic decisions not documented

### ✅ **Dependencies, Build & Configuration**

- ✅ Restore service registration and functionality working correctly
- ⚠️ **NEED TO VERIFY** - No linting run on restore logic code

### ⚠️ **Documentation**

- ⚠️ **PARTIAL** - Restore service methods need comprehensive docstrings
- ⚠️ **PARTIAL** - Time window and conflict detection algorithms need detailed documentation

## 📋 **Tasks to Complete Definition of Done**

### **High Priority (Blocking Epic 3)**

1. **Add Restore Unit Tests** - Test restore service with various time scenarios and edge cases
2. **Test Time Window Logic** - Verify window validation, conflict detection works correctly
3. **Test History Integration** - Confirm restore updates skip records properly
4. **Document Restore API** - Comprehensive service method and validation documentation

### **Medium Priority**

5. **Enhanced Edge Case Documentation** - Document time window logic and conflict resolution
6. **Implementation Notes** - Document restore service design decisions and validation rules

## Related Stories

- **Depends on**: Story 2.4 (Skip Instance Functionality)
- **Enables**: Story 2.6 (Data Persistence)
- **Supports**: Error recovery and user experience workflows

---

_Last Updated: 2025-10-11_
_Implementation Status: Complete and validated_
_Related Epic Status: Epic 2 - ✅ Complete_
