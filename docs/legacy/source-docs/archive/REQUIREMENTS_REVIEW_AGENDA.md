# Requirements Review & Gathering Session Agenda

**Purpose:** Validate current implementation against requirements, identify gaps, and gather requirements for Epic 3 and Epic 4

**Participants:** Product Owner, Development Team, Key Stakeholders/Users  
**Duration:** 2-3 hours (can be split into multiple sessions)  
**Prerequisites:** Review PROJECT_STATUS_AND_DOCUMENTATION_REVIEW.md

---

## Session 1: Current Implementation Review (45-60 minutes)

### Objective
Validate that Epic 1 and Epic 2 implementations meet original requirements and user needs.

### Agenda Items

#### 1.1 Demonstration of Current Features (20 minutes)

**Demo Checklist:**
- [ ] Show integration installation
- [ ] Show entity-level configuration (Entity Card → Settings → Configure)
- [ ] Demonstrate all 4 recurrence patterns:
  - [ ] INTERVAL: "Every 3 days after completion"
  - [ ] WEEKLY: "Every Monday and Friday"
  - [ ] MONTHLY: "15th of every month"
  - [ ] YEARLY: "March 15th every year"
- [ ] Demonstrate all 5 services:
  - [ ] complete_chore
  - [ ] snooze_chore
  - [ ] skip_chore (with 24hr restore window)
  - [ ] restore_chore
  - [ ] reassign_chore
- [ ] Show entity states: pending, complete, overdue, snoozed, skipped
- [ ] Show entity attributes in developer tools
- [ ] Show event firing (if possible in demo)

**Questions to Answer:**
- Is the demonstration clear and understandable?
- Are there any confusion points?
- Does the UX feel intuitive?

#### 1.2 Recurrence Patterns Validation (10 minutes)

**Discussion Questions:**

1. **Are the 4 patterns sufficient?**
   - [ ] INTERVAL - meeting needs?
   - [ ] WEEKLY - meeting needs?
   - [ ] MONTHLY - meeting needs?
   - [ ] YEARLY - actually needed? (rare use case?)

2. **Are there missing patterns?**
   - [ ] Need for "Every X days of the week" (e.g., every Tuesday and Thursday)?
   - [ ] Need for "Last X day of month" (e.g., last Friday of month)?
   - [ ] Need for "Every X weekday" (skip weekends automatically)?
   - [ ] Need for seasonal patterns (summer only, winter only)?

3. **Pattern Complexity**
   - [ ] Are patterns too simple?
   - [ ] Are patterns too complex?
   - [ ] Is the current complexity just right?

4. **All-Day Event Model**
   - [ ] Is date-only (no specific time) acceptable?
   - [ ] Are there use cases requiring specific times? (e.g., "Take medication at 8am")
   - [ ] Should time be optional or removed entirely?

**Action Items:**
- [ ] Document new pattern requirements (if any)
- [ ] Prioritize new patterns
- [ ] Validate all-day model decision

#### 1.3 Service Handlers Validation (10 minutes)

**Discussion Questions:**

1. **Are all 5 services being used?**
   - [ ] complete_chore - usage frequency?
   - [ ] snooze_chore - usage frequency?
   - [ ] skip_chore - usage frequency?
   - [ ] restore_chore - usage frequency?
   - [ ] reassign_chore - usage frequency?

2. **Are there missing services?**
   - [ ] Need for "undo complete" service?
   - [ ] Need for "start chore" or "in progress" service?
   - [ ] Need for "cancel" or "delete" chore service?
   - [ ] Need for "bulk operation" services?

3. **Service Parameters**
   - [ ] Is 24-hour restore window sufficient?
   - [ ] Should snooze have a maximum duration?
   - [ ] Should there be snooze presets (1 day, 3 days, 1 week)?

**Action Items:**
- [ ] Document new service requirements (if any)
- [ ] Validate 24-hour window decision
- [ ] Consider snooze presets

#### 1.4 Person Assignment Review (5 minutes)

**Discussion Questions:**

1. **Single Assignment**
   - [ ] Is single person assignment sufficient?
   - [ ] Need for multiple assignees (shared responsibility)?
   - [ ] Need for assignment rotation?

2. **Assignment Features**
   - [ ] Need for assignment rules (auto-assign based on criteria)?
   - [ ] Need for assignment history?
   - [ ] Need for workload balancing?

**Action Items:**
- [ ] Document multi-assignee requirements
- [ ] Consider for Epic 3

#### 1.5 State Management Review (5 minutes)

**Discussion Questions:**

1. **Are 5 states sufficient?**
   - [ ] pending
   - [ ] complete
   - [ ] overdue
   - [ ] snoozed
   - [ ] skipped

2. **Missing States?**
   - [ ] Need for "in_progress" state?
   - [ ] Need for "blocked" state (waiting on something)?
   - [ ] Need for "cancelled" state?

3. **State Behavior**
   - [ ] Should "complete" be temporary or permanent?
   - [ ] How long should completion history be retained?
   - [ ] Are automatic state transitions (snooze expiration, overdue detection) acceptable?

**Action Items:**
- [ ] Document new state requirements
- [ ] Define state retention policy

#### 1.6 Open Issues and Pain Points (10 minutes)

**Discussion:**

1. **Current Issues**
   - What's not working as expected?
   - What's confusing?
   - What's missing?

2. **User Experience**
   - Is configuration easy?
   - Are service calls intuitive?
   - Is status visibility clear?

3. **Performance**
   - Any performance issues?
   - Coordinator refresh rate acceptable?
   - Large chore list handling?

**Action Items:**
- [ ] Document all issues raised
- [ ] Prioritize issues for fixing

---

## Session 2: Epic 3 Requirements Gathering (45-60 minutes)

### Objective
Define requirements for Epic 3: Smart Automation features (Person Assignment, Calendar, Notifications)

### Agenda Items

#### 2.1 Person Assignment Enhancements (15 minutes)

**Current State:**
- Single person assignment per chore
- Manual reassignment via service

**Requirements to Discuss:**

1. **Multi-Person Assignment**
   - [ ] Should chores support multiple assignees?
   - [ ] Use cases: Shared responsibility (e.g., "Clean kitchen" - anyone can do it)
   - [ ] UI for selecting multiple people
   - [ ] How to handle completion with multiple assignees?

2. **Assignment Rotation**
   - [ ] Should chores auto-rotate between people?
   - [ ] Use cases: Fair distribution (e.g., "Take out trash" rotates weekly)
   - [ ] Rotation patterns:
     - [ ] Round-robin (A → B → C → A)
     - [ ] Weighted (A gets 2 chores for every 1 B gets)
     - [ ] Skill-based (certain people for certain chores)
   - [ ] Configuration: UI for defining rotation

3. **Assignment Rules**
   - [ ] Should assignment happen automatically based on rules?
   - [ ] Use cases:
     - [ ] Assign to person with least chores
     - [ ] Assign based on person availability
     - [ ] Assign based on location (person at home)
   - [ ] Configuration: Rule builder UI

4. **Assignment History**
   - [ ] Track who completed what chores?
   - [ ] Display assignment history in entity attributes?
   - [ ] Analytics on person workload?

**Priority Questions:**
- [ ] Which features are must-have for v1?
- [ ] Which can wait for future versions?

**Action Items:**
- [ ] Define must-have assignment features
- [ ] Design rotation configuration
- [ ] Design rule builder (if needed)

#### 2.2 Calendar Integration (15 minutes)

**Current State:**
- No calendar integration
- Chores only visible as sensor entities

**Requirements to Discuss:**

1. **Calendar Entity**
   - [ ] Should chores appear in Home Assistant calendar?
   - [ ] Benefits: Visual timeline, integration with other calendars
   - [ ] Challenges: One config entry per chore (need aggregation)

2. **Calendar View**
   - [ ] What should appear on calendar?
     - [ ] Due dates?
     - [ ] Completion dates?
     - [ ] Snoozed dates?
   - [ ] How far in advance should events show?
   - [ ] Color coding by status?

3. **Aggregation Service**
   - [ ] How to aggregate all chore entities into single calendar?
   - [ ] Technical approach: Separate calendar integration?
   - [ ] Performance considerations with many chores

4. **Calendar Actions**
   - [ ] Complete chore from calendar?
   - [ ] Snooze from calendar?
   - [ ] Create new chore from calendar?

5. **External Calendar Sync**
   - [ ] Should chores sync to Google Calendar, iCal, etc.?
   - [ ] One-way or two-way sync?
   - [ ] Use cases: Mobile notifications, family sharing

**Priority Questions:**
- [ ] Is calendar integration essential?
- [ ] Which calendar features are most important?

**Action Items:**
- [ ] Define calendar requirements
- [ ] Research aggregation approaches
- [ ] Design calendar entity structure

#### 2.3 Notification System (15 minutes)

**Current State:**
- No built-in notifications
- Users can create automations using events

**Requirements to Discuss:**

1. **Notification Triggers**
   - [ ] When should notifications be sent?
     - [ ] Chore due today?
     - [ ] Chore overdue?
     - [ ] Chore completed?
     - [ ] Chore assigned/reassigned?
     - [ ] Reminder X days before due?
   - [ ] Configurable triggers per chore?

2. **Notification Channels**
   - [ ] Where should notifications go?
     - [ ] Home Assistant persistent notifications?
     - [ ] Mobile app push notifications?
     - [ ] Email?
     - [ ] SMS?
     - [ ] Slack/Discord/other?
   - [ ] Per-person notification preferences?

3. **Notification Content**
   - [ ] What information to include?
     - [ ] Chore name?
     - [ ] Due date?
     - [ ] Assigned person?
     - [ ] Priority/urgency?
   - [ ] Action buttons (complete, snooze, skip)?

4. **Notification Customization**
   - [ ] Should users customize notification templates?
   - [ ] Different notifications for different chores?
   - [ ] Quiet hours (don't notify at night)?

5. **Notification Frequency**
   - [ ] Daily digest vs real-time?
   - [ ] Reminder escalation (daily → hourly if overdue)?
   - [ ] Snooze notifications?

**Priority Questions:**
- [ ] Built-in notifications vs user automations?
- [ ] Which triggers are most important?
- [ ] Which channels to support first?

**Action Items:**
- [ ] Define notification requirements
- [ ] Choose notification approach (built-in vs automation)
- [ ] Design notification configuration

---

## Session 3: Epic 4 Requirements Gathering (30-45 minutes)

### Objective
Define requirements for Epic 4: Analytics & Reporting features

### Agenda Items

#### 3.1 Completion Analytics (10 minutes)

**Current State:**
- completion_count attribute per chore
- No aggregated analytics

**Requirements to Discuss:**

1. **Metrics to Track**
   - [ ] Total chores completed (household)
   - [ ] Chores completed per person
   - [ ] Completion rate (completed vs missed)
   - [ ] Average time between chore instances
   - [ ] Streak tracking (consecutive completions)
   - [ ] Most/least completed chores

2. **Time Periods**
   - [ ] Daily summaries?
   - [ ] Weekly summaries?
   - [ ] Monthly summaries?
   - [ ] Custom date ranges?

3. **Visualization**
   - [ ] Dashboard cards for metrics?
   - [ ] Charts/graphs?
   - [ ] Leaderboards (gamification)?

**Action Items:**
- [ ] Define must-have metrics
- [ ] Design analytics dashboard

#### 3.2 Performance Tracking (10 minutes)

**Current State:**
- No performance metrics

**Requirements to Discuss:**

1. **Individual Performance**
   - [ ] Track completion rate per person
   - [ ] Track on-time vs late completions
   - [ ] Track time taken (if tracking start/end times)

2. **Household Performance**
   - [ ] Overall completion rate
   - [ ] Chores falling behind
   - [ ] Workload distribution fairness

3. **Chore-Specific Performance**
   - [ ] Which chores get skipped most?
   - [ ] Which chores get snoozed most?
   - [ ] Which chores are consistently late?

**Action Items:**
- [ ] Define performance metrics
- [ ] Design performance dashboards

#### 3.3 Historical Data & Insights (10 minutes)

**Current State:**
- No long-term historical data
- Data only in coordinator (may be lost on restart?)

**Requirements to Discuss:**

1. **Data Retention**
   - [ ] How long to keep historical data?
   - [ ] Where to store (database, files)?
   - [ ] Export/backup functionality?

2. **Insights Generation**
   - [ ] Automatic insights (e.g., "Bob completes 30% more chores on weekends")?
   - [ ] Trend analysis (completion rate going up/down)?
   - [ ] Anomaly detection (someone stopped doing chores)?

3. **Predictions**
   - [ ] Predict when chore will be completed?
   - [ ] Predict who will complete it?
   - [ ] AI/ML integration?

**Action Items:**
- [ ] Define data retention policy
- [ ] Design insights features
- [ ] Consider ML/AI integration

---

## Session 4: Architecture & Technical Review (30 minutes)

### Objective
Validate architectural decisions and plan for extensibility

### Agenda Items

#### 4.1 Helper Integration Pattern (10 minutes)

**Current State:**
- Helper integration (one config entry per chore)
- Entity-level configuration
- Simplified single-chore coordinator

**Discussion:**

1. **Advantages of Helper Pattern**
   - [ ] Native entity-level configuration UX
   - [ ] Simplified architecture
   - [ ] Easier debugging

2. **Limitations for Epic 3/4**
   - [ ] How will calendar aggregation work?
   - [ ] How will cross-chore analytics work?
   - [ ] Is a coordinator service needed?

3. **Alternative Architectures**
   - [ ] Should we reconsider device integration? (dev branch)
   - [ ] Hybrid approach?
   - [ ] Aggregation service pattern?

**Action Items:**
- [ ] Validate helper integration for Epic 3/4
- [ ] Design aggregation service if needed

#### 4.2 All-Day Event Model (5 minutes)

**Current State:**
- Date-only calculations (no time components for state)
- Optional time for weekly/monthly/yearly patterns

**Discussion:**

1. **Is All-Day Model Correct?**
   - [ ] Does it meet user needs?
   - [ ] Are there use cases requiring time-based scheduling?
   - [ ] Should time be added back for state calculations?

2. **Impact on Features**
   - [ ] Notifications: When to send if no specific time?
   - [ ] Calendar: All-day events or timed events?
   - [ ] Automation: Time-based triggers needed?

**Action Items:**
- [ ] Validate all-day model
- [ ] Define time requirements if needed

#### 4.3 Data Model Evolution (10 minutes)

**Current State:**
- Configuration in config entry
- State in coordinator
- No long-term persistence

**Discussion:**

1. **Data Extensibility**
   - [ ] Is current schema extensible?
   - [ ] Can we add new fields without breaking changes?
   - [ ] Migration strategy for schema changes?

2. **Data Persistence**
   - [ ] Is coordinator storage sufficient?
   - [ ] Need for database integration?
   - [ ] Backup and restore requirements?

3. **Performance & Scalability**
   - [ ] How many chores can system handle?
   - [ ] Performance with 50+ chores?
   - [ ] Performance with 100+ chores?
   - [ ] Optimization strategies?

**Action Items:**
- [ ] Define data model versioning
- [ ] Plan persistence strategy
- [ ] Test scalability limits

#### 4.4 Testing & Quality (5 minutes)

**Current State:**
- 67 unit tests (100% passing)
- Not tested in live Home Assistant

**Discussion:**

1. **Test Coverage**
   - [ ] Is 67 unit tests sufficient?
   - [ ] Need for integration tests?
   - [ ] Need for end-to-end tests?

2. **Testing Strategy**
   - [ ] Live instance testing plan
   - [ ] Beta testing program?
   - [ ] User acceptance testing?

3. **Quality Gates**
   - [ ] CI/CD integration?
   - [ ] Automated testing?
   - [ ] Code review process?

**Action Items:**
- [ ] Create live testing plan
- [ ] Define quality gates for releases

---

## Session 5: Prioritization & Roadmap (30 minutes)

### Objective
Prioritize features and create product roadmap

### Agenda Items

#### 5.1 Feature Prioritization (15 minutes)

**Method:** MoSCoW (Must have, Should have, Could have, Won't have)

**Epic 3 Features:**
- [ ] Categorize each Epic 3 feature
- [ ] Identify must-haves for v1.0
- [ ] Identify nice-to-haves for v1.1+

**Epic 4 Features:**
- [ ] Categorize each Epic 4 feature
- [ ] Identify must-haves
- [ ] Identify nice-to-haves

**New Features (from sessions):**
- [ ] Categorize any new features discovered
- [ ] Add to backlog

#### 5.2 Roadmap Planning (15 minutes)

**Proposed Roadmap:**

1. **v1.0 (Current)** - Testing & Documentation
   - Complete documentation updates
   - Live instance validation
   - Bug fixes from testing

2. **v1.1** - Epic 3 Foundation
   - Must-have person assignment features
   - Basic calendar integration
   - Simple notification system

3. **v1.2** - Epic 3 Completion
   - Advanced assignment (rotation, rules)
   - Full calendar features
   - Advanced notifications

4. **v2.0** - Epic 4 Foundation
   - Basic analytics
   - Performance tracking
   - Historical data

5. **v2.1+** - Epic 4 Advanced
   - Advanced insights
   - Predictions/ML
   - Custom dashboards

**Questions:**
- [ ] Does this roadmap make sense?
- [ ] Are versions sized appropriately?
- [ ] Any features to move between versions?

**Action Items:**
- [ ] Finalize roadmap
- [ ] Estimate effort for each version
- [ ] Set target dates

---

## Session 6: Action Items & Next Steps (15 minutes)

### Objective
Capture all action items and assign owners

### Review All Action Items

Go through each session and compile all action items:

- [ ] Review Session 1 action items
- [ ] Review Session 2 action items
- [ ] Review Session 3 action items
- [ ] Review Session 4 action items
- [ ] Review Session 5 action items

### Assign Owners and Deadlines

For each action item:
- [ ] Assign owner
- [ ] Set deadline
- [ ] Identify dependencies

### Communication Plan

- [ ] How will decisions be communicated?
- [ ] How will requirements be documented?
- [ ] Next review meeting date?

---

## Appendices

### Appendix A: Pre-Session Materials

**Send to Participants Before Meeting:**
- [ ] PROJECT_STATUS_AND_DOCUMENTATION_REVIEW.md
- [ ] Current README.md
- [ ] Demo video (if available)
- [ ] Key questions for each session

### Appendix B: Question Templates

#### For Product Owner

1. What are the top 3 pain points users experience with current chore management?
2. What features would provide the most value to users?
3. How do users currently handle chores without this integration?
4. What competing solutions exist? What do they do well?

#### For Developers

1. What architectural constraints should we be aware of?
2. What are the most challenging features to implement?
3. What technical debt exists that should be addressed?
4. What are the scalability limits?

#### For Users/Stakeholders

1. How would you use this integration in your daily life?
2. What features are missing that would make it more useful?
3. What features are confusing or difficult to use?
4. Would you recommend this to others? Why or why not?

### Appendix C: Decision Log Template

For each major decision, document:

**Decision:** [Brief title]  
**Date:** [Date]  
**Participants:** [Who was involved]  
**Context:** [Why this decision was needed]  
**Options Considered:** [List alternatives]  
**Decision Made:** [What was decided]  
**Rationale:** [Why this was chosen]  
**Consequences:** [Impact of this decision]  
**Action Items:** [What needs to be done]

### Appendix D: Requirements Template

For each new requirement, document:

**Requirement ID:** REQ-XXX  
**Epic:** [Epic 3 or Epic 4]  
**Title:** [Brief title]  
**Description:** [Detailed description]  
**User Story:** As a [user], I want [feature] so that [benefit]  
**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

**Priority:** [Must/Should/Could/Won't]  
**Effort Estimate:** [Story points or hours]  
**Dependencies:** [Other requirements or features]  
**Notes:** [Additional context]

---

## Post-Session Deliverables

After completing all sessions:

1. **Requirements Document**
   - [ ] All new requirements documented
   - [ ] All decisions logged
   - [ ] All action items compiled

2. **Updated PRD**
   - [ ] Epic 3 requirements added
   - [ ] Epic 4 requirements added
   - [ ] Roadmap updated

3. **User Stories**
   - [ ] New user stories created for Epic 3
   - [ ] New user stories created for Epic 4
   - [ ] Story dependencies mapped

4. **Architecture Decision Records**
   - [ ] Key decisions documented
   - [ ] Technical approach defined
   - [ ] Risks identified

5. **Communication**
   - [ ] Summary sent to all participants
   - [ ] Decisions communicated to broader team
   - [ ] Next steps clearly defined

---

**Document Version:** 1.0  
**Created:** January 5, 2026  
**Purpose:** Structure requirements review and gathering sessions  
**Next Review:** After Session 1 completion
