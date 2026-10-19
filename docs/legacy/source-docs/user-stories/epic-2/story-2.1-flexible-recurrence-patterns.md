# Story 2.1: Flexible Recurrence Patterns

**Epic**: 2 - Advanced Chore Lifecycle Management
**Story ID**: 2.1
**Priority**: Critical
**Status**: 🔄 REFACTORING REQUIRED - Architectural Mismatch
**Estimated Effort**: 8 story points (+ 4 points refactoring)

## User Story

**As a** HASS user,
**I want to** set up chores with both fixed schedules ("every Saturday") and interval-based schedules ("30 days after completion") with smart start date handling,
**so that** I can handle different types of household tasks with predictable all-day event behavior.

## Acceptance Criteria

- [x] Support daily, weekly, monthly, yearly fixed schedules as all-day events
- [x] Support interval-based scheduling (X days/weeks/months/years after completion)
- [x] Support specific day scheduling (every Monday, last Friday of month)
- [x] Recurrence configuration available in chore creation/edit with start date selection
- [x] Next due date calculated correctly for all pattern types based on completion date
- [x] Start date defaults to today, cannot be in past
- [x] Immediate start when start date matches pattern, otherwise next valid occurrence
- [x] Smart last day logic for monthly overflow (31st → last day of month)
- [x] Strict calendar dates maintained (no automatic weekend shifting)
- [x] Edge cases handled (leap years, month boundaries, completion-based intervals)

## Technical Implementation Details

### Components Delivered

- **RecurrenceEngine** (741 lines): Comprehensive scheduling logic
- **4 Recurrence Patterns** (NEEDS REFACTORING):
  - INTERVAL: Every X days after completion ✅ (matches all-day event model)
  - ~~FIXED~~: **REMOVE** - conflicts with all-day event architecture
  - WEEKLY: Specific days of week (Mon,Fri) - **REMOVE TIME COMPONENT**
  - MONTHLY: Specific day of month (15th) - **REMOVE TIME COMPONENT**
  - **NEW**: YEARLY: Specific date (March 15th) - date-only
- **Enhanced Config Flow**: Pattern selection with conditional fields
- **Calendar Integration**: Smart calendar-based scheduling logic

### Advanced Features

- **String/List Input Handling**: Flexible day specification ("Mon,Wed,Fri" or ["Mon", "Wed", "Fri"])
- **All-Day Event Architecture**: No time parsing - all chores operate on calendar dates only
- **Smart Start Date Logic**: Immediate start if start date matches pattern, otherwise next valid occurrence
- **Edge Case Handling**: Month boundaries, leap years, smart last day for monthly overflow
- **Strict Calendar Logic**: Weekend collisions maintain calculated dates (no automatic shifting)
- **Human-Readable Descriptions**: Auto-generated pattern summaries

### Business Rules Implementation (All-Day Event Architecture)

- **Start Date Management**:
  - Default to today, prevent past dates
  - If start date = Saturday and pattern = "Every Saturday" → first occurrence is today
  - If start date = Wednesday and pattern = "Every Saturday" → first occurrence is next Saturday
- **Monthly Overflow**: "Every 31st" → Jan 31st, Feb 28th/29th, Mar 31st (smart last day)
- **Yearly Overflow**: "Every Feb 29th" → Feb 29th (leap years), Feb 28th (non-leap years)
- **Completion-Based Intervals**: Next due calculated from completion **date** regardless of completion time
- **Weekend Handling**: Calculated dates remain unchanged (strict calendar)
- **Date-Only Calculations**: ALL patterns return date objects, NO time components

### Architecture Comparison

#### ❌ **Current Implementation (Time-Based - WRONG)**

```python
# CONFLICTS with all-day event model
def _calculate_weekly_recurrence(config, completion_date):
    hour, minute = map(int, fixed_time.split(":"))  # ❌ TIME PARSING
    return next_date.replace(hour=hour, minute=minute)  # ❌ TIME SETTING
```

#### ✅ **Required Implementation (Date-Only - CORRECT)**

```python
# ALIGNS with all-day event model
def _calculate_weekly_recurrence(config, completion_date):
    # Calculate next occurrence of target weekday
    return next_date  # ✅ DATE ONLY, no time component
```

### Refactored Recurrence Pattern Details

#### **1. INTERVAL (Enhanced) ✅**

- **Config**: `pattern_interval` + `interval_unit` (days/weeks/months/years)
- **Examples**: "Every 3 days", "Every 2 weeks", "Every 6 months", "Every 2 years" after completion
- **Calculation**: `completion_date + timedelta(pattern_interval * unit_multiplier)`

#### **2. ~~FIXED~~ (REMOVE ENTIRELY) ❌**

- **Reason**: Time-based concept conflicts with all-day event architecture
- **Replacement**: Users can achieve similar with WEEKLY patterns

#### **3. WEEKLY (Enhanced with Frequency) 🔄**

- **Config**: `pattern_interval` (1-52, defaults to 1) + `weekly_days` (list of weekday names)
- **Examples**: "Every Monday", "Every 2 weeks on Tuesday and Friday", "Every 4 weeks on Weekend"
- **Calculation**: Find next occurrence of target weekday(s), then add (pattern_interval-1) weeks

#### **4. MONTHLY (Enhanced with Frequency) 🔄**

- **Config**: `pattern_interval` (1-60, defaults to 1) + `monthly_day` (1-31)
- **Examples**: "Every 15th", "Every 3 months on 1st", "Every 6 months on 31st" (with smart last day)
- **Calculation**: Next month with target day, then add (pattern_interval-1) months, apply smart last day logic

#### **5. YEARLY (NEW PATTERN with Frequency) ➕**

- **Config**: `pattern_interval` (1-10, defaults to 1) + `yearly_month` (1-12) + `yearly_day` (1-31)
- **Examples**: "Every March 15th", "Every 2 years on December 25th", "Every 5 years on February 29th"
- **Calculation**: Next year with target month/day, then add (pattern_interval-1) years, handle leap year edge cases

## Data Dictionary - Unified Pattern Architecture

### **Core Fields (All Patterns)**

```yaml
recurrence_type:
  type: enum
  values: ["interval", "weekly", "monthly", "yearly"]
  required: true

pattern_interval:
  type: integer
  required: true
  default: 1
  validation: varies by pattern type
  ui_label: "Frequency"

start_date:
  type: date
  required: false
  default: today
  validation: >= current_date
```

### **Pattern-Specific Fields**

#### **INTERVAL Pattern**

```yaml
interval_unit:
  type: enum
  values: ["days", "weeks", "months", "years"]
  required: true

# Validation Rules:
pattern_interval: 1-999 (all units)
```

#### **WEEKLY Pattern**

```yaml
weekly_days:
  type: array
  values:
    [
      "monday",
      "tuesday",
      "wednesday",
      "thursday",
      "friday",
      "saturday",
      "sunday",
    ]
  required: true
  min_items: 1

# Validation Rules:
pattern_interval: 1-52 (weeks)
```

#### **MONTHLY Pattern**

```yaml
monthly_day:
  type: integer
  range: 1-31
  required: true

# Validation Rules:
pattern_interval: 1-60 (months)
```

#### **YEARLY Pattern**

```yaml
yearly_month:
  type: integer
  range: 1-12
  required: true

yearly_day:
  type: integer
  range: 1-31
  required: true

# Validation Rules:
pattern_interval: 1-10 (years)
```

### **Config Flow Implementation**

```yaml
# Simple number input - easiest to implement
frequency_field:
  type: number
  schema: vol.All(vol.Coerce(int), vol.Range(min=1, max=validation_limit))
  default: 1
  label: "Frequency"
```

### **Example Configurations**

```json
// Every 3 days after completion
{"recurrence_type": "interval", "pattern_interval": 3, "interval_unit": "days"}

// Every 2 weeks on Monday and Friday
{"recurrence_type": "weekly", "pattern_interval": 2, "weekly_days": ["monday", "friday"]}

// Every 6 months on the 15th
{"recurrence_type": "monthly", "pattern_interval": 6, "monthly_day": 15}

// Every 2 years on March 15th
{"recurrence_type": "yearly", "pattern_interval": 2, "yearly_month": 3, "yearly_day": 15}
```

## Architectural Decision: Functional Composition Approach

### **Decision**: Use functional composition with strategy pattern

**Rationale**: Date calculations are pure functions with no shared state - perfect for functional approaches

### **Architecture Benefits:**

- ✅ **Extensibility**: Adding new patterns = add function + register in dictionary
- ✅ **Testability**: Each calculation function independently testable
- ✅ **Simplicity**: No inheritance hierarchy or complex OO patterns
- ✅ **Performance**: No method dispatch overhead
- ✅ **Debugging**: Easy to trace through pure function calls

### **Adding New Calculations (Future Extensions):**

```python
# Example: Adding quarterly pattern later
def _calculate_quarterly(self, config: Dict, completion_date: date) -> date:
    """Every quarter on specific day."""
    target_day = config.get('quarterly_day', 1)
    return self.date_calc.add_months_with_smart_day(completion_date, 3, target_day)

# Simple registration - no inheritance needed
self._calculators['quarterly'] = self._calculate_quarterly
```

### **File Structure:**

```
recurrence/
├── engine.py           # Main RecurrenceEngine with strategy dictionary
├── date_utils.py       # DateCalculator utility class
└── constants.py        # WEEKDAY_MAP, validation constants
```

## Definition of Done

### ❌ **Requirements Met - ARCHITECTURAL MISMATCH IDENTIFIED**

- ❌ **CRITICAL**: Current implementation uses TIME-BASED patterns, conflicts with all-day event architecture
- ❌ **REFACTORING REQUIRED**: Remove all time components from WEEKLY, MONTHLY patterns
- ❌ **PATTERN REMOVAL**: FIXED pattern must be eliminated (time-based concept)
- ❌ **NEW PATTERN**: YEARLY pattern missing from implementation

### ✅ **Coding Standards & Project Structure**

- ✅ RecurrenceEngine well-structured (741 lines, clear separation)
- ✅ Config flow conditional fields properly implemented
- ⚠️ **PARTIAL** - Complex recurrence logic could use more inline documentation

### ❌ **Testing**

- ❌ **MISSING** - No unit tests for RecurrenceEngine pattern calculations
- ❌ **MISSING** - No tests for edge cases (leap years, month boundaries)
- ❌ **MISSING** - No tests for config flow pattern selection

### ✅ **Functionality & Verification**

- ✅ Manually verified (all patterns working, edge cases tested)
- ✅ Integration with entity state system confirmed

### ⚠️ **Story Administration**

- ✅ Story requirements documented thoroughly
- ⚠️ **PARTIAL** - Complex implementation decisions not formally documented

### ✅ **Dependencies, Build & Configuration**

- ✅ Integration builds successfully with recurrence patterns
- ⚠️ **NEED TO VERIFY** - No linting run on RecurrenceEngine code

### ⚠️ **Documentation**

- ⚠️ **PARTIAL** - RecurrenceEngine needs comprehensive API documentation
- ⚠️ **PARTIAL** - Pattern calculation algorithms need detailed comments

## � **CRITICAL: Refactoring Tasks Required**

### **IMMEDIATE - Architectural Alignment (4 story points)**

1. **Remove Time Components from RecurrenceEngine**:

   - Strip all `fixed_time`, `hour`, `minute` parsing logic
   - Update `_calculate_weekly_recurrence` to return dates only
   - Update `_calculate_monthly_recurrence` to return dates only
   - Remove `next_date.replace(hour=hour, minute=minute)` calls

2. **Remove FIXED Pattern Type**:

   - Delete `_calculate_fixed_recurrence` method
   - Remove `RECURRENCE_TYPE_FIXED` from constants
   - Update config flow to remove FIXED option
   - Update validation logic

3. **Add YEARLY Pattern Type**:

   - Implement `_calculate_yearly_recurrence` method
   - Add `RECURRENCE_TYPE_YEARLY` constant
   - Add yearly config fields: `yearly_month`, `yearly_day`
   - Implement smart last day logic for yearly (Feb 29th handling)

4. **Update Config Flow**:

   - Remove time input fields from weekly/monthly patterns
   - Add yearly pattern option with month/day selection
   - Remove fixed_time configuration entirely
   - Update validation schema

5. **Implement Unified Pattern Architecture**:
   - Add `pattern_interval` field to ALL patterns (mandatory, defaults to 1)
   - Rename `interval_value` to `pattern_interval` for consistency
   - Update all pattern calculations to support frequency intervals
   - Examples: "Every 2 weeks on Monday", "Every 3 months on 15th", "Every 2 years on March 15th"

### **POST-REFACTORING - Testing & Documentation**

6. **Add RecurrenceEngine Unit Tests** - Test all 4 NEW pattern types with edge cases
7. **Test All-Day Event Logic** - Verify no time components in calculations
8. **Test Edge Case Handling** - Leap years, month boundaries, yearly patterns
9. **Test Config Flow Patterns** - Verify new pattern selection works
10. **Document RefactoredRecurrenceEngine API** - All-day event focused documentation

## 📋 **Refactoring Implementation Plan**

### **Architectural Approach: Functional Composition**

**Pattern**: Strategy pattern with functional composition and utility classes
**Benefits**: Easy to extend, simple to test, no inheritance complexity

```python
# Main approach - strategy dictionary with pure functions
class RecurrenceEngine:
    def __init__(self):
        self._calculators: Dict[str, Callable] = {
            'interval': self._calculate_interval,
            'weekly': self._calculate_weekly,
            'monthly': self._calculate_monthly,
            'yearly': self._calculate_yearly,
        }
        self.date_calc = DateCalculator()  # Utility for complex date arithmetic
```

### **Phase 1: Architecture Foundation & Remove Time Dependencies**

- [ ] Implement DateCalculator utility class for complex date arithmetic
- [ ] Create strategy dictionary for pattern calculators
- [ ] Strip time parsing from existing methods
- [ ] Update return values to date-only calculations
- [ ] Remove time-related configuration validation

### **Phase 2: Pattern Restructuring**

- [ ] Delete FIXED pattern entirely
- [ ] Implement YEARLY pattern with month/day config
- [ ] Enhance INTERVAL with units (days/weeks/months)

### **Phase 3: Config Flow Updates**

- [ ] Remove time input fields
- [ ] Add yearly pattern selection
- [ ] Add interval unit selection (days/weeks/months)
- [ ] Update conditional field logic

### **Phase 4: Testing & Validation**

- [ ] Comprehensive unit tests for all-day event patterns
- [ ] Edge case testing (leap years, monthly overflow, yearly patterns)
- [ ] Manual testing of config flow changes
- [ ] Performance validation with date-only calculations

## Related Stories

- **Depends on**: [Epic 1 complete](../epic-1/README.md) ([1.1](../epic-1/story-1.1-integration-infrastructure-setup.md), [1.2](../epic-1/story-1.2-basic-chore-entity-creation.md), [1.3](../epic-1/story-1.3-entity-state-management.md))
- **Enables**: [Story 2.2: Mark Complete Functionality](story-2.2-mark-complete-functionality.md)
- **Foundation for**: All remaining [Epic 2 stories](README.md)
- **Epic**: [Epic 2 Overview](README.md)
- **Previous Epic**: [Epic 1: Integration Foundation](../epic-1/README.md)

---

_Last Updated: 2025-10-11_
_Implementation Status: Complete and validated_
_Related Epic Status: Epic 2 - ✅ Complete_
