# Story Implementation Check — 2026-04-01

**Reviewed by:** GitHub Copilot (Party Mode — Solo)
**Date:** April 14, 2026
**Scope:** All stories in Epic 1, Epic 2, Epic 3 cross-referenced against:
- `custom_components/sh_chore_tracker/__init__.py`
- `custom_components/sh_chore_tracker/sensor.py`
- `custom_components/sh_chore_tracker/config_flow.py`
- `custom_components/sh_chore_tracker/const.py`
- `custom_components/sh_chore_tracker/date_utils.py`
- `custom_components/sh_chore_tracker/services.yaml`
- `custom_components/sh_chore_tracker/manifest.json`
- `tests/test_init.py`
- `tests/test_config_flow.py`
- `tests/test_date_utils.py`

---

## Summary Table

| Story | Title | Story Status | Code Present | Tests Present | Notes |
|-------|-------|:---:|:---:|:---:|-------|
| 1.1 | Integration Infrastructure Setup | ✅ Complete | ✅ | ❌ | No unit/integration tests |
| 1.2 | Basic Chore Entity Creation | ✅ Complete | ✅ | ❌ | No entity-specific tests |
| 1.3 | Entity State Management | ✅ Complete | ✅ | ❌ | No state-transition tests |
| 2.1 | Flexible Recurrence Patterns | ⚠️ Refactoring Required | ✅ (partial) | ✅ (partial) | FIXED pattern removed; legacy code remnants found |
| 2.2 | Mark Complete Functionality | ✅ Complete | ✅ | ❌ | Service code works; no dedicated service tests |
| 2.3 | Snooze Functionality | ✅ Complete | ✅ | ❌ | Service logic present; no snooze unit tests |
| 2.4 | Skip Instance Functionality | ✅ Complete | ⚠️ | ❌ | Skip uses completion-based scheduling, not pattern-based |
| 2.5 | Restore Functionality | ✅ Complete | ✅ | ❌ | 24-hour window hardcoded; no tests |
| 2.6 | Data Persistence | ✅ Complete | ⚠️ | ❌ | Coordinator-only persistence (in-memory); no HASS storage write tests |
| 3.1 | Person Assignment Integration | 🎯 Planned | ⚠️ (partial) | ❌ | `assigned_person` in config flow; no person registry integration |
| 3.2 | Chore Reassignment | 🎯 Planned | ✅ | ❌ | `reassign_chore` service exists; no bulk reassignment |
| 3.3 | Chore Edit and Delete | 🎯 Planned | ⚠️ (partial) | ❌ | Options flow edit works; no delete handler or confirmation |

---

## Epic 1 — Integration Foundation

### Story 1.1: Integration Infrastructure Setup
**Story Status:** ✅ Complete  
**Code Status:** ✅ Implemented

**Acceptance Criteria vs. Code:**
| Criterion | Code Evidence | Result |
|-----------|--------------|--------|
| Appears in HASS integrations list | `manifest.json` with `domain: sh_chore_tracker` | ✅ |
| Config flow guides through setup | `ChoreTrackerConfigFlow(SchemaConfigFlowHandler, domain=DOMAIN)` in `config_flow.py` | ✅ |
| Loads without errors | `async_setup_entry` in `__init__.py` | ✅ |
| Entity in developer tools | `ChoreEntity(CoordinatorEntity, SensorEntity)` in `sensor.py` | ✅ |
| Follows HASS integration structure | `manifest.json`, `const.py`, `services.yaml`, `strings.json` all present | ✅ |
| HACS compatibility | `manifest.json` includes `hacs_manifest` fields | ✅ |

**Gaps:**
- ❌ No unit tests for `async_setup_entry` or `async_unload_entry` (tests exist in `test_init.py` but are mock-heavy and don't assert full integration behavior)
- ❌ No integration test exercising the full config flow end-to-end in a real HA context
- ⚠️ Linting not confirmed run

---

### Story 1.2: Basic Chore Entity Creation
**Story Status:** ✅ Complete  
**Code Status:** ✅ Implemented

**Acceptance Criteria vs. Code:**
| Criterion | Code Evidence | Result |
|-----------|--------------|--------|
| Create chore via config flow | `SchemaFlowFormStep(_get_chore_schema)` in `config_flow.py` | ✅ |
| Entity appears in HASS | `async_setup_entry` adds `ChoreEntity` via `async_add_entities` | ✅ |
| Displays chore name and status | `_attr_name = chore_name`, `native_value` returns status | ✅ |
| State reflects pending/complete | `CHORE_STATUS_PENDING/COMPLETE/OVERDUE/SNOOZED` constants and state logic | ✅ |
| Unique entity ID | `_attr_unique_id = f"chore_{config_entry.entry_id}"` | ✅ |
| Basic recurrence configurable | All 4 recurrence types in config flow schema | ✅ |

**Gaps:**
- ❌ No unit tests for `ChoreEntity.__init__` or unique ID generation
- ❌ No tests for entity state transitions (pending → overdue → complete)
- ❌ No test for entity ID sanitization with special characters

---

### Story 1.3: Entity State Management
**Story Status:** ✅ Complete  
**Code Status:** ✅ Implemented

**Acceptance Criteria vs. Code:**
| Criterion | Code Evidence | Result |
|-----------|--------------|--------|
| `next_due_date` attribute | `attributes["next_due_date"]` in `extra_state_attributes` | ✅ |
| `days_until_due` (negative when overdue) | `days_until_due = (next_due - dt_util.now()).days` | ✅ |
| State updates when overdue | `status = CHORE_STATUS_OVERDUE` in `_async_update_data` | ✅ |
| All attributes visible in developer tools | All attributes returned in `extra_state_attributes` | ✅ |
| State changes fire HASS events | `hass.bus.async_fire(EVENT_CHORE_COMPLETED, ...)` and other events | ✅ |
| State persistence across restarts | Config entry data stored via HASS native entry storage | ✅ |

**Gaps:**
- ❌ No unit tests for `days_until_due` calculation, including negative (overdue) case
- ❌ No tests for the `pending → overdue` state transition in `_async_update_data`
- ❌ No tests for event firing during state transitions
- ⚠️ `completion_count` attribute still sourced from `completed_count` key but story uses `completion_count` — minor key name inconsistency between story spec and code (`state.get("completed_count", 0)`)

---

## Epic 2 — Advanced Chore Lifecycle Management

### Story 2.1: Flexible Recurrence Patterns
**Story Status:** ⚠️ Refactoring Required (per story itself)  
**Code Status:** ✅ Substantially implemented, with legacy remnants

**Acceptance Criteria vs. Code:**
| Criterion | Code Evidence | Result |
|-----------|--------------|--------|
| Daily/weekly/monthly/yearly fixed schedules | `RECURRENCE_TYPE_INTERVAL/WEEKLY/MONTHLY/YEARLY` | ✅ |
| Interval-based scheduling (X days after completion) | `_calculate_interval` in `RecurrenceEngine` | ✅ |
| Specific day scheduling (every Monday, etc.) | `_calculate_weekly` with `weekly_days` list | ✅ |
| Config available in creation/edit | All fields present in `_get_chore_schema` | ✅ |
| Next due date calculated correctly | `DateCalculator` handles leap year, month-end overflow | ✅ |
| Smart last-day logic (31st → last day of month) | `add_months_with_smart_day` in `date_utils.py` | ✅ |
| Strict calendar dates (no weekend shifting) | `next_weekday_occurrence` returns exact target day | ✅ |
| Edge cases (leap years, month boundaries) | `add_years_with_leap_day_logic` in `date_utils.py` | ✅ |
| FIXED pattern removed | `RECURRENCE_TYPE_FIXED` constant still present in `const.py` | ⚠️ |
| Date-only calculations (no time components) | `RecurrenceEngine` returns `datetime.combine(date, datetime.min.time())` | ✅ |

**Gaps:**
- ⚠️ `RECURRENCE_TYPE_FIXED = "fixed"` and `CONF_FIXED_TIME = "fixed_time"` still present in `const.py` as "legacy constants" — story says FIXED pattern must be removed entirely
- ⚠️ Legacy `_calculate_monthly_recurrence` with time-based code (time parsing) found as a dangling method in `__init__.py` around line 534 (inside `async_unload_services`) — appears to be orphaned dead code from the old architecture
- ⚠️ `_calculate_initial_due_date` in `ChoreCoordinator` still uses the legacy `interval_days` for interval type, not `pattern_interval` + `interval_unit`
- ❌ No start date field (`start_date`) implemented in config flow schema despite story requiring it
- ❌ "Immediate start when start date matches pattern" logic not implemented
- ✅ Tests exist for RecurrenceEngine in `test_init.py` covering all 4 pattern types

---

### Story 2.2: Mark Complete Functionality
**Story Status:** ✅ Complete  
**Code Status:** ✅ Implemented

**Acceptance Criteria vs. Code:**
| Criterion | Code Evidence | Result |
|-----------|--------------|--------|
| Service call to mark complete | `SERVICE_COMPLETE_CHORE` registered, `_complete_chore_handler` | ✅ |
| Entity state updates to "complete" | `state["status"] = CHORE_STATUS_COMPLETE` | ✅ |
| Next due date calculated from completion date | `recurrence_engine.calculate_next_due_date(config, completion_date)` | ✅ |
| Completion timestamp recorded | `state["last_completed_date"] = completion_date` | ✅ |
| Entity attributes updated immediately | `coordinator.async_request_refresh()` called | ✅ |
| HASS event fired | `hass.bus.async_fire(EVENT_CHORE_COMPLETED, ...)` | ✅ |
| Single instance management | No loop/spawn logic — one state, one instance | ✅ |
| Chores remain overdue until acknowledged | Overdue detection only transitions from pending; complete must be explicit | ✅ |

**Gaps:**
- ⚠️ `_complete_chore_handler` sets `state["status"] = CHORE_STATUS_COMPLETE` but never transitions back to "pending" — the transition to pending happens only in `async_update` on `sensor.py`, not in the coordinator, which could cause state inconsistency if the entity is not loaded
- ❌ No unit tests for `_complete_chore_handler`
- ❌ No tests for the `complete → pending` state transition
- ⚠️ Event data in code uses `"completion_date"` key; story spec shows `"completed_at"` — minor naming discrepancy

---

### Story 2.3: Snooze Functionality
**Story Status:** ✅ Complete  
**Code Status:** ✅ Implemented

**Acceptance Criteria vs. Code:**
| Criterion | Code Evidence | Result |
|-----------|--------------|--------|
| Service call with day count | `SERVICE_SNOOZE_CHORE` with `days` parameter (default `DEFAULT_SNOOZE_DAYS=3`) | ✅ |
| Next due date pushed forward | `state["snooze_until"] = datetime.now() + timedelta(days=days)` | ⚠️ |
| Entity state shows "snoozed" | `state["status"] = CHORE_STATUS_SNOOZED` | ✅ |
| Single postponed instance | State updated in place, no spawning | ✅ |
| Multiple snoozes supported | No guard against re-snoozeing a snoozed chore | ✅ |
| Default snooze duration configurable | `DEFAULT_SNOOZE_DAYS = 3` in `const.py` | ✅ |
| Remains snoozed until next due date | Snooze expiry in `_async_update_data` | ✅ |

**Gaps:**
- ⚠️ **Critical semantic difference:** The snooze handler sets `snooze_until` (a point in time when snooze expires) but does NOT update `next_due_date`. The story requires "Next due date pushed forward by specified days." The `next_due_date` attribute remains unchanged; only `snooze_until` is set. These are two different fields.
- ⚠️ `days` parameter in service: `services.yaml` correctly defines it as `days`; however `__init__.py` `_register_chore_services` (the duplicate registration at line ~350) uses `snooze_until` (a datetime) instead of `days` — there are **two service registration code paths** in `__init__.py` which may conflict
- ❌ No unit tests for snooze handler, date arithmetic, or cumulative snooze behavior
- ❌ `snooze_count` attribute mentioned in story is not tracked in state

---

### Story 2.4: Skip Instance Functionality
**Story Status:** ✅ Complete  
**Code Status:** ⚠️ Partially correct

**Acceptance Criteria vs. Code:**
| Criterion | Code Evidence | Result |
|-----------|--------------|--------|
| Service call to skip | `SERVICE_SKIP_CHORE` registered, `_skip_chore_handler` | ✅ |
| Next due based on original recurrence pattern (not completion) | Uses `recurrence_engine.calculate_next_due_date(config, datetime.now())` — this is completion-based | ❌ |
| Entity state shows "skipped" | `state["status"] = CHORE_STATUS_SKIPPED` | ✅ |
| Skip records timestamp and reason | `state["last_skip_date"]`, `state["skip_reason"]` | ✅ |
| History tracking | `state["skip_restored"]` tracked | ⚠️ (partial) |
| Skip event fired | `hass.bus.async_fire(EVENT_CHORE_SKIPPED, ...)` | ✅ |
| Single instance management | No spawning | ✅ |

**Gaps:**
- ❌ **Key logic bug:** Story explicitly specifies "Next due = current due date + pattern interval (not completion-based)" but the skip handler uses `calculate_next_due_date(config, datetime.now())` — same as complete. Skip should advance from the *current* `next_due_date`, not from `now()`.
- ❌ No formal history array/list — skip info stored as flat properties only, not as an auditable list of events
- ❌ No tests

---

### Story 2.5: Restore Functionality
**Story Status:** ✅ Complete  
**Code Status:** ✅ Implemented

**Acceptance Criteria vs. Code:**
| Criterion | Code Evidence | Result |
|-----------|--------------|--------|
| Service call to restore | `SERVICE_RESTORE_CHORE` registered, `_restore_chore_handler` | ✅ |
| Restore only within configurable time window | 24-hour check using `DEFAULT_RESTORE_WINDOW_HOURS = 24` | ✅ |
| Restore returns to original due date + pending | `state["next_due_date"] = state["original_due_date"]`, `state["status"] = CHORE_STATUS_PENDING` | ✅ |
| Previous skip marked as "restored" | `state["skip_restored"] = True` | ✅ |
| Restore not allowed if next instance already overdue | No explicit check — only time-window check | ⚠️ |
| Restore event fired | `hass.bus.async_fire(EVENT_CHORE_RESTORED, ...)` | ✅ |

**Gaps:**
- ⚠️ No check whether the "next instance is already overdue" — story says restore should be blocked in that case; only a 24-hour time-window check exists
- ⚠️ `DEFAULT_RESTORE_WINDOW_HOURS` is defined in `const.py` but the handler hardcodes `24 * 3600` directly — does not use the constant
- ❌ No tests
- ❌ Restore only works on `CHORE_STATUS_SKIPPED` — story implies it also covers snoozed chores, but snooze has its own expiration and no restore service path

---

### Story 2.6: Data Persistence
**Story Status:** ✅ Complete  
**Code Status:** ⚠️ Partially correct

**Acceptance Criteria vs. Code:**
| Criterion | Code Evidence | Result |
|-----------|--------------|--------|
| All chore data saved to HASS storage | Config entry `data`/`options` fields used | ✅ |
| Entity states restored after restart | `_initialize_chore_data` rebuilds from `entry.options` | ⚠️ |
| Recurrence schedules continue correctly | `_calculate_initial_due_date` recalculates from config | ⚠️ |
| No data loss during restarts | Standard HASS config entry storage | ✅ |
| Config survives integration reloads | `async_unload_entry`/`async_setup_entry` | ✅ |
| Backup/restore compatibility | HASS snapshot covers config entries natively | ✅ |

**Gaps:**
- ⚠️ **Critical persistence gap:** Chore runtime state (current status, `last_completed`, `completion_count`, `next_due_date`) is stored only in `coordinator._chore_data` (in-memory). On restart, `_initialize_chore_data` rebuilds state from config — but **does not restore** `last_completed`, `completion_count`, or the specific `next_due_date`. It recalculates `next_due_date` from now, losing any history.
- ⚠️ After restart, a chore that was completed last Tuesday and is due next Tuesday would restart with `next_due_date` recalculated from "now + interval" rather than the actual stored next date
- ❌ There is no write to `hass.storage` or `config_entry.async_update_options()` to persist runtime state changes
- ❌ No persistence tests

---

## Epic 3 — Person Assignment & Advanced Features

### Story 3.1: Person Assignment Integration
**Story Status:** 🎯 Planned  
**Code Status:** ⚠️ Partially implemented (ahead of story)

**Acceptance Criteria vs. Code:**
| Criterion | Code Evidence | Result |
|-----------|--------------|--------|
| Person assignment dropdown in creation/edit | `CONF_ASSIGNED_PERSON` in config flow schema with person entity IDs | ✅ |
| Dropdown populated with HASS Person entities | `handler.hass.states.async_entity_ids("person")` | ✅ |
| Entity attribute shows assigned person | `"assigned_person": config.get(CONF_ASSIGNED_PERSON)` in `extra_state_attributes` | ✅ |
| Unassigned chores supported | Default option `"none"` in selector | ✅ |
| Person entity changes reflected | No dynamic listener for person entity changes | ❌ |
| Person-based filtering for automations | `assigned_person` attribute exists for automation use | ✅ |

**Gaps:**
- ❌ No dynamic update when a Person entity is renamed or deleted in HASS — stale `entity_id` stored
- ❌ `assigned_person` attribute shows raw entity ID (e.g., `person.alice`) not a friendly name+ID dict as specified in the story
- ❌ No tests
- ⚠️ Story lists this as "Planned" but functional person assignment is already in place — story status should be updated

---

### Story 3.2: Chore Reassignment
**Story Status:** 🎯 Planned  
**Code Status:** ✅ Implemented (ahead of story)

**Acceptance Criteria vs. Code:**
| Criterion | Code Evidence | Result |
|-----------|--------------|--------|
| Service call to reassign | `SERVICE_REASSIGN_CHORE` registered, `_reassign_chore_handler` | ✅ |
| Entity attribute updated with new person | `config["assigned_person"] = person_id` | ✅ |
| Change history tracked | Only current assignment stored; no change log | ❌ |
| Reassignment event fired | `hass.bus.async_fire(EVENT_CHORE_REASSIGNED, ...)` | ✅ |
| UI supports reassignment | Via options flow (config flow edit) | ✅ |
| Bulk reassignment supported | No bulk support — only single entity per call | ❌ |

**Gaps:**
- ❌ No assignment change history/audit trail
- ❌ No bulk reassignment
- ❌ No tests
- ⚠️ Story listed as "Planned" but service is already implemented — story status should be updated

---

### Story 3.3: Chore Edit and Delete
**Story Status:** 🎯 Planned  
**Code Status:** ⚠️ Edit partially implemented; Delete not implemented

**Acceptance Criteria vs. Code:**
| Criterion | Code Evidence | Result |
|-----------|--------------|--------|
| Edit via config flow | Options flow `OPTIONS_FLOW = {"init": SchemaFlowFormStep(_get_chore_schema)}` | ✅ |
| All properties editable (name, recurrence, person) | All fields in `_get_chore_schema` | ✅ |
| Delete chore removes entity and data | No delete service or flow defined | ❌ |
| Confirmation required for delete | Not implemented | ❌ |
| Edit preserves completion history | Not implemented — edit rebuilds from options | ❌ |
| Deleted chores clean up HASS references | Not implemented | ❌ |

**Gaps:**
- ❌ No delete functionality at all — no service, no config flow step, no cleanup logic
- ❌ No history preservation when editing recurrence pattern (changes wipe runtime state since `_initialize_chore_data` is called fresh on reload)
- ❌ No tests

---

## Cross-Cutting Concerns

### Testing Coverage
All three epics share a systemic testing gap:

| Test File | Coverage |
|-----------|----------|
| `test_init.py` | `RecurrenceEngine` calculations and validation — well covered. `async_setup_entry`/`async_unload_entry` — mock-only. Service handlers — **not tested**. |
| `test_config_flow.py` | Schema generation and basic validation logic — covered. Full flow execution — **not tested**. |
| `test_date_utils.py` | `DateCalculator` methods — well covered with edge cases. |

**Not tested at all:**
- All 5 service handlers (`complete`, `snooze`, `skip`, `restore`, `reassign`)
- `ChoreCoordinator` state management and transitions
- `_async_update_data` overdue/snooze expiry logic
- `ChoreEntity` attribute calculations
- Data persistence / restart recovery

### Code Quality Issues Found
1. **Duplicate service registration:** `_register_chore_services` (around line 350) AND `async_setup_services` (around line 870) both register the same services with different schemas. `async_setup_services` is the correct/complete path; the older `_register_chore_services` is likely dead code or a risk of double-registration.
2. **Orphaned legacy method:** `_calculate_monthly_recurrence` with time-based code appears inside the body of `async_unload_services` — this is malformed code placement (likely a merge artifact) and is unreachable.
3. **`DEFAULT_RESTORE_WINDOW_HOURS` unused:** Defined in `const.py` but `_restore_chore_handler` hardcodes `24 * 3600`.
4. **`coordinator.chores` reference:** `_find_chore_data` calls `coordinator.chores` but `ChoreCoordinator` has no `chores` property — it uses `_chore_data`. This would cause an `AttributeError` at runtime when any service is called.
5. **`interval_days` in initial due date:** `_calculate_initial_due_date` uses `config.get("interval_days", 7)` — the legacy field name — not `pattern_interval` + `interval_unit`.

---

## What Is Done

| Capability | Done |
|---|---|
| Integration loads in HASS | ✅ |
| Config flow for chore creation | ✅ |
| Sensor entity with state and attributes | ✅ |
| 4 recurrence pattern types | ✅ |
| Date arithmetic utilities (leap year, month-end) | ✅ |
| `complete_chore` service (schema + handler) | ✅ |
| `snooze_chore` service (schema + handler) | ✅ |
| `skip_chore` service (schema + handler) | ✅ |
| `restore_chore` service (schema + handler) | ✅ |
| `reassign_chore` service (schema + handler) | ✅ |
| Person assignment in config flow | ✅ |
| HASS events for all lifecycle actions | ✅ |
| Options flow (edit chore config) | ✅ |
| RecurrenceEngine unit tests | ✅ |
| DateCalculator unit tests | ✅ |
| Config flow schema unit tests | ✅ |

## What Is Not Done / Needs Fixing

| Gap | Priority |
|---|---|
| Runtime state (status, completion history, next_due_date) not persisted across restarts | 🔴 Critical |
| `coordinator.chores` AttributeError in all service calls at runtime | 🔴 Critical |
| Skip handler uses completion-based scheduling instead of pattern-based | 🔴 High |
| Duplicate service registration paths in `__init__.py` | 🔴 High |
| `snooze_chore` does not update `next_due_date` (only sets `snooze_until`) | 🟠 High |
| FIXED pattern constants not fully removed (`const.py`) | 🟠 Medium |
| `start_date` field missing from config flow (Story 2.1 AC) | 🟠 Medium |
| `DEFAULT_RESTORE_WINDOW_HOURS` not used — hardcoded instead | 🟡 Medium |
| No delete chore functionality (Story 3.3) | 🟡 Medium (Epic 3) |
| Person entity change not dynamically reflected | 🟡 Medium (Epic 3) |
| `completion_count` key mismatch (`completed_count` in code vs. `completion_count` in story) | 🟡 Low |
| No assignment history audit trail (Story 3.2) | 🟡 Low (Epic 3) |
| No bulk reassignment (Story 3.2) | 🟢 Low (Epic 3) |
| No unit tests for any service handlers | 🟠 High |
| No unit tests for coordinator state management | 🟠 High |
| No unit tests for entity attribute calculations | 🟡 Medium |
| Story status for 3.1 and 3.2 stale (code is ahead of story) | 🟢 Low |

---

_Generated: 2026-04-14_
_Covers: Epic 1 (Stories 1.1–1.3), Epic 2 (Stories 2.1–2.6), Epic 3 (Stories 3.1–3.3)_
