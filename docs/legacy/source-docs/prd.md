# HASS sh-chore-tracker Integration Product Requirements Document (PRD)

## Goals and Background Context

### Goals

- Create a reliable, feature-rich HASS chore management integration that replaces buggy existing solutions
- Provide flexible recurrence patterns supporting both fixed schedules and interval-based timing
- Integrate seamlessly with HASS Calendar for visual task management
- Enable person assignments using native HASS Person objects
- Support complete/snooze functionality with configurable timing
- Establish proper entity architecture where each chore is a dedicated HASS entity
- Achieve 500+ installations within 6 months with 4.5+ star rating
- Enable automation integration through rich entity states

### Background Context

The HASS ecosystem currently lacks a reliable chore management integration. Existing solutions like ha-chore-helper suffer from bugs, limited recurrence patterns, and poor integration with the broader HASS ecosystem. Users are forced to resort to external apps or create complex manual automations, losing the benefits of unified home automation. This integration addresses these gaps by providing enterprise-grade chore management with deep HASS integration, flexible scheduling capabilities, and robust entity architecture that enables powerful automation scenarios.

### Change Log

| Date       | Version | Description                                                                                                                 | Author           |
| ---------- | ------- | --------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| 2025-10-07 | v1.0    | Initial PRD creation from project brief                                                                                     | John (PM)        |
| 2025-10-13 | v1.1    | Added all-day event model, manual-only service control, and single instance management architecture                         | Business Analyst |
| 2025-10-13 | v1.2    | Added start date management, edge case handling (monthly overflow, weekend collisions), and completion-based interval logic | Business Analyst |
| 2026-01-05 | v1.3    | Updated for implementation completion - Epic 1 & 2 complete, added DateCalculator FRs, updated architecture to Helper integration | Repository Analysis Agent |

## Requirements

### Functional Requirements

| ID   | Requirement                                                                                                                                                   |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR1  | The system shall allow users to create chores with title, description, and configurable recurrence patterns                                                   |
| FR2  | The system shall support INTERVAL, WEEKLY, MONTHLY, and YEARLY recurrence patterns                                                                             |
| FR3  | The system shall support both fixed scheduling (WEEKLY, MONTHLY, YEARLY) and interval-based scheduling (INTERVAL after completion)                           |
| FR4  | The system shall create a dedicated HASS entity for each chore with comprehensive attributes for automation                                                   |
| FR5  | The system shall integrate with HASS Person objects for chore assignments                                                                                     |
| FR6  | The system shall provide "complete_chore" service that updates chore status and calculates next due date using RecurrenceEngine                               |
| FR7  | The system shall provide "snooze_chore" service with configurable day count and optional reason                                                                |
| FR8  | The system shall provide "skip_chore" service to skip current occurrence with optional reason and 24-hour restore window                                      |
| FR9  | The system shall provide "restore_chore" service to restore skipped chores within 24-hour window                                                               |
| FR10 | The system shall provide "reassign_chore" service to transfer chores to different persons                                                                      |
| FR11 | The system shall treat all chores as "all-day events" with no time component - minimum unit is 1 day                                                          |
| FR12 | The system shall maintain single instance per chore - no spawning multiple instances when overdue                                                             |
| FR13 | The system shall keep chores in overdue state until explicitly acknowledged via service calls (complete/snooze/skip)                                          |
| FR14 | The system shall calculate next due dates based on completion date (not time) regardless of actual completion timestamp                                       |
| FR15 | The system shall integrate with HASS Calendar to display chore due dates as all-day events (Epic 3)                                                           |
| FR16 | The system shall provide a HASS config flow for easy setup and configuration (Helper integration pattern)                                                     |
| FR17 | The system shall persist chore data across HASS restarts                                                                                                      |
| FR18 | The system shall allow editing and deletion of existing chores through entity-level configuration                                                              |
| FR19 | The system shall calculate and display days overdue for past-due chores                                                                                       |
| FR20 | The system shall support reassignment of chores to different persons                                                                                          |
| FR21 | The system shall provide 5 service calls: complete_chore, snooze_chore, skip_chore, restore_chore, reassign_chore                                             |
| FR22 | The system shall implement DateCalculator utility for complex date arithmetic (leap years, month-end overflow)                                                |
| FR23 | The system shall support legacy data migration from old interval_days format to pattern_interval                                                                |
| FR24 | The system shall handle monthly date overflow with "smart last day" logic (use target date if available, otherwise last day of month)                         |
| FR25 | The system shall maintain strict calendar dates for all patterns (no automatic weekday shifting)                                                              |
| FR26 | The system shall fire events for all state transitions (chore_completed, chore_snoozed, chore_skipped, chore_restored, chore_reassigned, chore_overdue)       |

### Non-Functional Requirements

| ID   | Requirement                                                                                                                             |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------- |
| NFR1 | ✅ **[COMPLETE] The integration supports full debugging with breakpoints, variable inspection, and real-time code changes in VS Code** |
| NFR2 | The integration must maintain compatibility with Home Assistant Core 2024.1+                                                            |
| NFR3 | Entity state updates must complete within 1 second under normal load                                                                    |
| NFR4 | The integration must follow HASS development best practices and coding standards                                                        |
| NFR5 | The system must handle up to 100 active chores without performance degradation                                                          |
| NFR6 | The integration must provide comprehensive error handling and logging                                                                   |
| NFR7 | All user data must persist reliably across system restarts with zero data loss                                                          |
| NFR8 | The integration must be installable via HACS (Home Assistant Community Store)                                                           |
| NFR9 | The integration must have comprehensive unit test coverage (67 tests covering all components and edge cases)                           |

## User Interface Design Goals

### Overall UX Vision

The integration should provide a minimal, intuitive configuration experience that feels completely native to Home Assistant. Focus on integration setup and basic chore management through standard HASS UI patterns. All advanced features accessible through native HASS entity management.

### Key Interaction Paradigms

- **Configuration Flow:** Standard HASS config flow for integration setup
- **Entity Management:** Native HASS entity creation and editing interfaces
- **Native Cards:** Standard HASS entity cards for chore display and actions
- **Standard Controls:** Use HASS built-in buttons and controls for complete/snooze actions

### Core Screens and Views (MVP Only)

- **Integration Setup Screen:** Initial configuration and integration setup
- **Chore Creation/Edit Form:** Simple chore configuration with basic recurrence options
- **Native Entity Cards:** Standard HASS entity cards displaying chore status and actions

### Backlog (Post-MVP)

- ~~Chore Management Dashboard~~ → Use native HASS entities page
- ~~Calendar View~~ → Phase 2 feature
- ~~Settings/Configuration Screen~~ → Use standard HASS integration options
- **Chore SubActions:** Multi-step chores with intermediate checkpoints (e.g., "Check salt level" → "Refill water softener")

### Accessibility

WCAG AA - Inherit from native HASS components, no custom accessibility implementation needed.

### Branding

Complete integration with HASS design system - no custom styling required. Automatically inherits user's theme.

### Target Device and Platforms

Web Responsive - Native HASS web interface with responsive design inherited from HASS framework.

## Business Rules Summary

The following business rules govern chore behavior and have been finalized through requirements analysis:

### Core Architecture Rules

1. **All-Day Events**: Chores operate on calendar dates only (minimum unit: 1 day, no time component)
2. **Manual Control**: All state changes require explicit service calls (no auto-completion/snoozing/skipping)
3. **Single Instance**: One active chore instance maximum per chore (no spawning when overdue)
4. **Overdue Persistence**: Chores remain overdue until manual acknowledgment via service calls

### Start Date Rules

5. **Default Today**: Start date defaults to current date
6. **No Past Dates**: Start dates cannot be before today
7. **Immediate Start**: If start date matches recurrence pattern, first occurrence is immediate
8. **Next Valid**: If start date doesn't match pattern, calculate next valid occurrence from start date

### Edge Case Rules

9. **Monthly Overflow**: Use "smart last day" logic - target date if month has it, otherwise last day of month
   - Example: "Every 31st" → Jan 31st, Feb 28th, Mar 31st, Apr 30th
10. **Weekend Collisions**: Maintain strict calendar dates regardless of day-of-week (no automatic shifting)
11. **Completion-Based**: Next due calculated from completion **date** regardless of completion timestamp

### Service Call Rules

12. **Complete**: Updates to next occurrence based on recurrence pattern and completion date
13. **Snooze**: Postpones current due date by specified days, maintains single instance
14. **Skip**: Moves to next occurrence based on original schedule (not completion-based)

## Technical Assumptions

### Repository Structure

Monorepo - Single repository following standard HASS custom integration structure with all components in one place for simplified development and distribution.

### Service Architecture

**Household Hub Architecture** - Built as a native Home Assistant hub integration following the modern integration patterns:

- **Hub Pattern**: One household config entry with one chore subentry per chore
- **Subentry Config**: Guided add/edit flows scoped to the hub
- **DataUpdateCoordinator**: One hub coordinator manages all chore lifecycle state
- **Custom Entity Classes**: ChoreEntity sensor platform for chore representation
- **Modern Config Flow**: Selector-based UI with proper validation and person assignment
- **Native HASS Data Storage**: Integration with HASS storage API for persistence

### Recurrence Engine Architecture

**Functional Composition with Strategy Pattern** - Date calculations implemented as pure functions:

- Strategy dictionary for pattern calculators (interval, weekly, monthly, yearly)
- DateCalculator utility class for complex date arithmetic
- No inheritance hierarchy - functional approach for extensibility
- Easy addition of new patterns: implement function + register in dictionary
- All calculations return date objects (no time components)

### Chore Lifecycle Management

**All-Day Event Model:**

- All chores operate as calendar-day based tasks (minimum unit: 1 day)
- No time component required - chores are "all-day events"
- Next due dates calculated based on completion **date**, not timestamp

**Manual-Only Service Control:**

- `sh_chore_tracker.complete_chore` - Mark chore as completed
- `sh_chore_tracker.snooze_chore` - Postpone chore by specified days
- `sh_chore_tracker.skip_chore` - Skip current instance, maintain schedule
- NO auto-completion, auto-snoozing, or auto-skipping capabilities

**Single Instance Management:**

- One active instance per chore maximum
- Overdue chores persist until manual acknowledgment
- No spawning multiple instances when overdue
- State transitions only via explicit service calls

**Start Date Management:**

- Start date defaults to current date (today)
- Start dates cannot be in the past
- If start date matches recurrence pattern, first occurrence is immediate
- If start date doesn't match pattern, calculate next valid occurrence
- Example: "Every Saturday starting Wednesday" → first Saturday after Wednesday

**Edge Case Handling:**

- **Monthly Overflow**: Use "smart last day" logic (target date if available, otherwise last day of month)
  - Example: "Every 31st" → Jan 31st, Feb 28th, Mar 31st, Apr 30th
- **Weekend Collisions**: Use strict calendar dates regardless of day-of-week
  - Calculated dates remain unchanged (Saturday stays Saturday)
- **Completion-Based Intervals**: Next due calculated from actual completion date

### Testing Requirements

Unit + Integration Testing:

- Unit tests for core logic (recurrence calculation, state management)
- Integration tests with HASS test framework
- Automated testing in CI/CD pipeline
- Manual testing in HASS DevContainer environment

### Technology Stack

- **Language:** Python 3.11+ (HASS requirement)
- **Framework:** Home Assistant Integration Framework
- **Config Management:** HASS config flow + YAML backup support
- **Data Storage:** HASS native storage API with JSON configuration
- **UI:** Native HASS frontend components only
- **Testing:** pytest with HASS testing utilities
- **Distribution:** HACS (Home Assistant Community Store)

### Development Environment

- **Primary:** HASS DevContainer for development and testing
- **IDE Integration:** VS Code with HASS extension and full debugging support
- **[CRITICAL] Debugging:** Full IDE debugging with breakpoints, variable inspection, real-time code changes, and symlink-based workflow
- **Safety:** Separate debug workspace with symlinks to prevent accidental commits to HASS core
- **Version Control:** Git with conventional commits and dedicated debugging branches

### 🚀 Debugging Architecture (Primary NFR)

**Debugging is a CRITICAL requirement for this integration development.**

#### Core Debugging Requirements:

- **Breakpoint Debugging:** Set breakpoints in VS Code and step through integration code during HASS execution
- **Variable Inspection:** Examine entity states, coordinator data, and service call parameters in real-time
- **Hot Code Reloading:** Make code changes and see results immediately without full HASS restart
- **Safe Workflow:** Prevent accidental commits to Home Assistant core repository
- **Integrated Testing:** Test config flows, service calls, and entity updates through HASS UI with full debug visibility

#### Debugging Implementation:

- **Symlink Architecture:** Source code in `/workspaces/ha-chore-tracker/` linked to HASS custom_components
- **VS Code Launch Config:** Direct Python debugging of Home Assistant with integration loaded
- **Branch Isolation:** Dedicated debugging branches separate from main development
- **Safety Scripts:** `DEBUG_SAFETY.md` and `debug_deploy.sh` to prevent repository confusion

#### Debugging Workflow:

1. Set breakpoints in source files (`/workspaces/ha-chore-tracker/custom_components/sh_chore_tracker/`)
2. Launch HASS via VS Code debugger (F5)
3. Use HASS UI to trigger integration functionality
4. Debug hits breakpoints in source files with full variable access
5. Make code changes and test iteratively

### Integration Architecture

- **Entity Types:** Custom sensor entities for each chore
- **Coordinator Pattern:** Single coordinator managing all chore states
- **Calendar Integration:** HASS Calendar platform implementation (Phase 2)
- **Person Integration:** Native HASS Person entity references
- **State Management:** HASS entity state attributes for all chore data

### Deployment & Distribution

- **HACS Installation:** Standard HACS custom integration
- **Configuration:** Config flow with YAML fallback
- **Updates:** HACS automatic update notifications
- **Documentation:** README + HASS developer docs format

## User Story Summary

**📁 [View Detailed User Stories →](user-stories/README.md)**

The following table provides an overview of all user stories. Click any story link to view detailed acceptance criteria, technical implementation, and cross-references.

| Epic                                     | Story ID                                                                 | Name                             | Status      | Effort | File Link                                                               |
| ---------------------------------------- | ------------------------------------------------------------------------ | -------------------------------- | ----------- | ------ | ----------------------------------------------------------------------- |
| **Epic 1: Integration Foundation**       |                                                                          |                                  |             |        |                                                                         |
| 1                                        | [1.1](user-stories/epic-1/story-1.1-integration-infrastructure-setup.md) | Integration Infrastructure Setup | ✅ Complete | 3 pts  | [📄](user-stories/epic-1/story-1.1-integration-infrastructure-setup.md) |
| 1                                        | [1.2](user-stories/epic-1/story-1.2-basic-chore-entity-creation.md)      | Basic Chore Entity Creation      | ✅ Complete | 5 pts  | [📄](user-stories/epic-1/story-1.2-basic-chore-entity-creation.md)      |
| 1                                        | [1.3](user-stories/epic-1/story-1.3-entity-state-management.md)          | Entity State Management          | ✅ Complete | 4 pts  | [📄](user-stories/epic-1/story-1.3-entity-state-management.md)          |
| **Epic 2: Advanced Chore Lifecycle**     |                                                                          |                                  |             |        |                                                                         |
| 2                                        | [2.1](user-stories/epic-2/story-2.1-flexible-recurrence-patterns.md)     | Flexible Recurrence Patterns     | ✅ Complete | 8 pts  | [📄](user-stories/epic-2/story-2.1-flexible-recurrence-patterns.md)     |
| 2                                        | [2.2](user-stories/epic-2/story-2.2-mark-complete-functionality.md)      | Mark Complete Functionality      | ✅ Complete | 5 pts  | [📄](user-stories/epic-2/story-2.2-mark-complete-functionality.md)      |
| 2                                        | [2.3](user-stories/epic-2/story-2.3-snooze-functionality.md)             | Snooze Functionality             | ✅ Complete | 4 pts  | [📄](user-stories/epic-2/story-2.3-snooze-functionality.md)             |
| 2                                        | [2.4](user-stories/epic-2/story-2.4-skip-instance-functionality.md)      | Skip Instance Functionality      | ✅ Complete | 4 pts  | [📄](user-stories/epic-2/story-2.4-skip-instance-functionality.md)      |
| 2                                        | [2.5](user-stories/epic-2/story-2.5-restore-functionality.md)            | Restore Functionality            | ✅ Complete | 3 pts  | [📄](user-stories/epic-2/story-2.5-restore-functionality.md)            |
| 2                                        | [2.6](user-stories/epic-2/story-2.6-data-persistence.md)                 | Data Persistence                 | ✅ Complete | 5 pts  | [📄](user-stories/epic-2/story-2.6-data-persistence.md)                 |
| **Epic 3: Person Assignment & Advanced** |                                                                          |                                  |             |        |                                                                         |
| 3                                        | [3.1](user-stories/epic-3/story-3.1-person-assignment-integration.md)    | Person Assignment Integration    | 🎯 Planned  | 6 pts  | [📄](user-stories/epic-3/story-3.1-person-assignment-integration.md)    |
| 3                                        | [3.2](user-stories/epic-3/story-3.2-chore-reassignment.md)               | Chore Reassignment               | 🎯 Planned  | 4 pts  | [📄](user-stories/epic-3/story-3.2-chore-reassignment.md)               |
| 3                                        | [3.3](user-stories/epic-3/story-3.3-chore-edit-and-delete.md)            | Chore Edit and Delete            | 🎯 Planned  | 5 pts  | [📄](user-stories/epic-3/story-3.3-chore-edit-and-delete.md)            |

**Progress Summary**: 9/12 stories complete (75%) | 41/56 story points complete (73%)

## Epic Status Summary

### ✅ Epic 1: Integration Foundation - COMPLETE
**Status**: ✅ **COMPLETED** - October 13, 2025
**Implementation**: Helper integration with entity-level configuration, DataUpdateCoordinator pattern, comprehensive config flow with selector-based UI, legacy data migration support.

### ✅ Epic 2: Advanced Chore Lifecycle Management - COMPLETE
**Status**: ✅ **COMPLETED** - October 13, 2025
**Implementation**: RecurrenceEngine with 4 patterns (INTERVAL/WEEKLY/MONTHLY/YEARLY), DateCalculator utility, 5 service handlers (complete/snooze/skip/restore/reassign), 5 entity states, event system, comprehensive testing (67 unit tests).

### 🎯 Epic 3: Person Assignment & Advanced Features - PLANNED
**Status**: 📋 **PLANNED** - Requirements gathering needed
**Scope**: Calendar integration, multi-person assignments, advanced automation features.

## Epic List

**Epic 1: Foundation & Core Integration** ✅ COMPLETE - Establish HASS integration infrastructure and basic chore entity management

**Epic 2: Chore Lifecycle Management** ✅ COMPLETE - Implement complete chore workflow with recurrence and completion logic

**Epic 3: Person Assignment & Advanced Features** 🎯 PLANNED - Add person integration and enhanced functionality

## Epic 1: Foundation & Core Integration

**Epic Goal:** Establish a working HASS integration that can create and display basic chore entities, providing the foundation for all chore management functionality.

**Epic Description:** This epic delivers the fundamental HASS integration infrastructure including config flow setup, entity coordinator, and basic chore entity creation. Users will be able to install the integration, create simple chores, and see them as HASS entities.

### Story 1.1: Integration Infrastructure Setup

As a HASS user,
I want to install the chore tracker integration through HASS,
so that I can begin managing chores within my home automation system.

**Acceptance Criteria:**

- Integration appears in HASS integrations list
- Config flow guides through initial setup
- Integration loads without errors in HASS logs
- Basic integration entity appears in developer tools
- Integration follows HASS integration structure standards
- HACS installation compatibility verified

### Story 1.2: Basic Chore Entity Creation

As a HASS user,
I want to create a simple chore entity with a name and basic recurrence,
so that I can start tracking household tasks.

**Acceptance Criteria:**

- Can create chore through config flow
- Chore appears as entity in HASS entities list
- Entity displays chore name and basic status
- Entity state reflects current chore status (pending/complete)
- Entity has unique ID for HASS management
- Basic recurrence pattern can be configured

### Story 1.3: Entity State Management

As a HASS user,
I want chore entities to display relevant information (due date, days until due),
so that I can see chore status at a glance.

**Acceptance Criteria:**

- Entity attributes include next_due_date
- Entity attributes include days_until_due (negative for overdue)
- Entity state updates when chore becomes overdue
- All attributes visible in developer tools
- Entity state changes trigger HASS events for automation
- State persistence across HASS restarts

## Epic 2: Chore Lifecycle Management

**Epic Goal:** Provide complete chore workflow including flexible recurrence patterns, completion actions, and state persistence across HASS restarts.

**Epic Description:** This epic implements the core chore management workflow that users interact with daily. It includes advanced recurrence patterns, completion/snooze actions, and reliable data persistence. Users will have a fully functional chore tracking system.

### Story 2.1: Flexible Recurrence Patterns

As a HASS user,
I want to set up chores with both fixed schedules ("every Saturday") and interval-based schedules ("30 days after completion"),
so that I can handle different types of household tasks appropriately.

**Acceptance Criteria:**

- Support daily, weekly, monthly, yearly fixed schedules
- Support interval-based scheduling (X days/weeks/months after completion)
- Support specific day scheduling (every Monday, last Friday of month)
- Recurrence configuration available in chore creation/edit
- Next due date calculated correctly for all pattern types
- Edge cases handled (leap years, month boundaries, weekends)

### Story 2.2: Mark Complete Functionality

As a HASS user,
I want to mark chores as complete,
so that the system updates the next due date and resets the chore cycle.

**Acceptance Criteria:**

- Service call available to mark chore complete
- Entity state updates to "complete" status
- Next due date calculated based on recurrence pattern
- Completion timestamp recorded
- Entity attributes updated immediately
- HASS event fired for automation triggers

### Story 2.3: Snooze Functionality

As a HASS user,
I want to snooze chores for a specified number of days,
so that I can postpone tasks when needed without losing track of them.

**Acceptance Criteria:**

- Service call available to snooze chore with day count parameter
- Next due date pushed forward by specified days
- Entity state shows "snoozed" status
- Snooze expiration automatically returns to normal scheduling
- Multiple snoozes supported on same chore
- Default snooze duration configurable

### Story 2.4: Skip Instance Functionality

As a HASS user,
I want to skip this specific instance of a chore,
so that I can move to the next scheduled occurrence without affecting the regular pattern.

**Acceptance Criteria:**

- Service call available to skip current chore instance
- Next due date calculated based on original recurrence pattern (not completion-based)
- Entity state shows "skipped" temporarily then returns to "pending" for next instance
- Skip action records timestamp and reason (optional)
- Skipped instances appear in completion history for tracking
- Skip event fired for automation triggers

### Story 2.5: Unskip Instance Functionality

As a HASS user,
I want to unskip a chore instance if it's still within the time window,
so that I can reinstate a mistakenly skipped chore.

**Acceptance Criteria:**

- Service call available to unskip recent chore instance
- Unskip only allowed within configurable time window (default: 24 hours)
- Unskip restores original due date and "pending" status
- Previous skip record marked as "unskipped" in history
- Unskip not allowed if next instance is already overdue
- Unskip event fired for automation triggers

### Story 2.6: Data Persistence

As a HASS user,
I want my chore data to persist across HASS restarts,
so that I don't lose my chore tracking setup when the system reboots.

**Acceptance Criteria:**

- All chore data saved to HASS storage
- Entity states restored after restart
- Recurrence schedules continue correctly after restart
- No data loss during HASS updates or restarts
- Configuration survives integration reloads
- Backup/restore compatibility with HASS snapshots

## Epic 3: Person Assignment & Advanced Features

**Epic Goal:** Enable person assignments using HASS Person entities and provide enhanced chore management capabilities.

**Epic Description:** This epic adds person assignment functionality and management features that enhance the basic chore tracking system. Users can assign responsibilities and manage their chore setup more effectively.

### Story 3.1: Person Assignment Integration

As a HASS user,
I want to assign chores to specific people using HASS Person entities,
so that household members have clear responsibility for tasks.

**Acceptance Criteria:**

- Chore creation/edit includes person assignment dropdown
- Dropdown populated with available HASS Person entities
- Entity attribute shows assigned person name and ID
- Unassigned chores supported (personal tasks)
- Person entity changes reflected in chore assignments
- Person-based filtering possible for automations

### Story 3.2: Chore Reassignment

As a HASS user,
I want to reassign chores to different people,
so that I can adjust responsibilities as needed.

**Acceptance Criteria:**

- Service call available to reassign chore to new person
- Entity attribute updated with new person assignment
- Change history tracked for accountability
- Reassignment event fired for automation triggers
- UI supports easy reassignment through standard HASS controls
- Bulk reassignment supported for multiple chores

### Story 3.3: Chore Edit and Delete

As a HASS user,
I want to edit or delete existing chores,
so that I can maintain my chore list as needs change.

**Acceptance Criteria:**

- Edit chore functionality through config flow
- All chore properties editable (name, recurrence, person)
- Delete chore removes entity and all associated data
- Confirmation required for delete operations
- Edit preserves completion history where appropriate
- Deleted chores clean up all HASS references

## Future Enhancements (Post-MVP)

### Phase 2 Features

- **Chore Groups/Categories:** Organize chores into rooms or categories (Home, Bedroom, Kitchen)
- **Chore SubActions:** Multi-step chores with intermediate checkpoints that maintain single chore lifecycle but track progress steps
  - _Use Case:_ Monthly water softener maintenance: "Check salt level" → "Refill salt" → Complete
  - _Benefits:_ Single chore entity, intermediate progress tracking, complete audit trail
  - _Implementation:_ SubAction log with timestamps, progress percentage, optional notes
- **Advanced Templates:** Pre-built chore templates for common household tasks
- **Enhanced Notifications:** Customizable reminder timing and escalation
- **Analytics Dashboard:** Completion rates, trends, and household participation metrics

### SubActions Feature Details

**Concept:** Allow chores to have predefined intermediate steps that can be logged without completing the main chore.

**Example Workflow:**

1. **Chore:** "Monthly Water Softener Maintenance" (due monthly)
2. **SubActions:**
   - "Check salt level" (can log midway through month)
   - "Refill salt" (final action that completes the chore)
3. **User Experience:**
   - Log "Checked salt level - 50% full" on day 15
   - Log "Refilled salt" on day 30 → chore completes, next due date calculated
4. **Entity Attributes:**
   - `subaction_progress`: "1/2 steps completed"
   - `last_subaction`: "Check salt level (2025-10-15)"
   - `subaction_history`: Complete log of all intermediate steps

**Technical Implementation:**

- SubActions defined in chore configuration
- SubAction logging service: `sh_chore_tracker.log_subaction`
- Entity attributes track progress without changing due dates
- Complete chore only when final SubAction logged or explicit completion

## Next Steps

### Architect Handoff

This PRD provides comprehensive requirements for the HASS sh-chore-tracker Integration. Please review thoroughly and create the technical architecture document, focusing on:

1. **HASS Integration Architecture:** Entity coordinator patterns, platform implementations
2. **Data Model Design:** Chore entity structure, state management, persistence strategy
3. **Recurrence Engine:** Algorithm design for flexible scheduling patterns
4. **API Design:** Service calls, entity attributes, event structure
5. **Development Environment:** DevContainer setup, testing framework, CI/CD pipeline

The architect should validate technical assumptions and may suggest refinements to the PRD based on HASS framework capabilities and constraints.
