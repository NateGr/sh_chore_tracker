# 🚀 DEBUGGING REQUIREMENTS - PRIMARY NFR

> **CRITICAL**: Debugging support is the **PRIMARY Non-Functional Requirement** for this integration. All architecture, development workflows, and repository structure decisions prioritize debugging capabilities.

## NFR-001: DEBUGGING-FIRST ARCHITECTURE (CRITICAL)

**Requirement**: The integration must support full debugging with breakpoints, variable inspection, and real-time code changes in VS Code.

### Acceptance Criteria:

#### ✅ Breakpoint Debugging
- [ ] Set breakpoints in source files (`/workspaces/ha-chore-tracker/custom_components/sh_chore_tracker/*.py`)
- [ ] Breakpoints trigger during HASS execution when integration functionality is used
- [ ] Full call stack visibility during breakpoint pauses
- [ ] Step through code (F10, F11, Shift+F11) with complete source access

#### ✅ Variable Inspection
- [ ] Real-time examination of coordinator data structures
- [ ] Entity state and attribute inspection during updates
- [ ] Service call parameter debugging
- [ ] Config flow user input and validation debugging
- [ ] Integration configuration and runtime_data access

#### ✅ Hot Code Reloading
- [ ] Edit source code and test changes within 5 seconds
- [ ] Symlink architecture reflects code changes immediately
- [ ] No HASS restart required for most integration code changes
- [ ] Configuration changes take effect on integration reload

#### ✅ Safety & Isolation
- [ ] Source code repository completely separate from HASS core
- [ ] Zero risk of accidental commits to Home Assistant repository
- [ ] Git operations confined to integration repository only
- [ ] Clear documentation of safe debugging workflows

#### ✅ Integration UI Testing
- [ ] Config flow debugging through HASS UI (Settings → Add Integration)
- [ ] Entity configuration debugging (entity → Settings → Configure)
- [ ] Service call debugging (Developer Tools → Services)
- [ ] Entity state debugging (Developer Tools → States)

## NFR-002: DEBUGGING WORKFLOW SUPPORT

### Development Environment Requirements:

#### VS Code Debugging Integration
```json
{
  "type": "python",
  "request": "launch",
  "program": "-m homeassistant",
  "args": ["--config", "/config", "--debug"],
  "console": "integratedTerminal"
}
```

#### Repository Structure
```
/workspaces/
├── ha-chore-tracker/                    # SOURCE (your repo)
│   └── custom_components/sh_chore_tracker/ # Integration source code
└── home-assistant/                      # HASS CORE (separate repo)
    └── custom_components/
        └── sh_chore_tracker -> /workspaces/ha-chore-tracker/custom_components/sh_chore_tracker
```

#### Safety Scripts
- `DEBUG_SAFETY.md`: Comprehensive safety guide
- `debug_deploy.sh`: Automated safe debugging setup
- Branch isolation: use a dedicated development branch for hub-architecture work

### Testing & Validation Workflows:

#### Config Flow Testing
1. Set breakpoint in `config_flow.py:async_step_user()`
2. Use HASS UI: Settings → Devices & Services → Add Integration
3. Fill out form, observe breakpoint trigger
4. Inspect `user_input` parameter and schema validation
5. Step through entity creation and config entry setup

#### Service Handler Testing
1. Set breakpoint in `__init__.py:complete_chore_handler()`
2. Use HASS UI: Developer Tools → Services → sh_chore_tracker.complete_chore
3. Execute service call, observe breakpoint trigger
4. Inspect service call data and entity state changes
5. Step through coordinator updates and entity attribute calculation

#### Entity State Testing
1. Set breakpoint in `sensor.py:native_value` property
2. Trigger entity update (service call, coordinator refresh, etc.)
3. Observe breakpoint trigger during state calculation
4. Inspect entity data, coordinator state, and attribute generation
5. Validate state transitions and attribute accuracy

## NFR-003: DEBUGGING PERFORMANCE REQUIREMENTS

### Response Time Requirements:
- **Code Change to Test**: < 5 seconds from edit to execution
- **Breakpoint Hit**: < 2 seconds from UI action to breakpoint trigger
- **Variable Inspection**: < 1 second response time for variable access
- **Hot Reload**: < 3 seconds for code changes to take effect

### Reliability Requirements:
- **Breakpoint Hit Rate**: 100% success rate for properly set breakpoints
- **Debugging Stability**: Zero debugger crashes during normal development
- **Safety Success**: 100% prevention of accidental HASS core commits
- **Symlink Integrity**: 100% uptime of symlink-based code access

## NFR-004: DEBUGGING DOCUMENTATION REQUIREMENTS

### Required Documentation:
- **Setup Guide**: Complete debugging environment setup instructions
- **Safety Guide**: Repository isolation and accident prevention
- **Workflow Guide**: Step-by-step debugging workflows for common scenarios
- **Troubleshooting**: Common debugging issues and resolution steps
- **Quick Reference**: Essential breakpoint locations and VS Code commands

### Documentation Standards:
- **Clarity**: Accessible to developers unfamiliar with HASS debugging
- **Completeness**: Cover all debugging scenarios (config flow, services, entities)
- **Safety Focus**: Emphasize repository safety in all workflows
- **Examples**: Concrete code examples with breakpoint locations

## �� DEBUGGING SUCCESS METRICS

### Primary Success Criteria:
1. **100% Breakpoint Success**: All set breakpoints trigger during testing
2. **< 5 Second Code Changes**: Edit-to-test cycle under 5 seconds
3. **Zero Safety Incidents**: No accidental commits to wrong repository
4. **Full UI Coverage**: All HASS UI interactions debuggable with breakpoints
5. **Complete State Access**: 100% visibility into integration state during debugging

### Validation Test Cases:

#### Test Case 1: Config Flow Debugging
**Scenario**: Create new chore through HASS UI with debugging
**Steps**: Set breakpoints → Use Add Integration UI → Verify breakpoint hits → Inspect variables
**Success**: Breakpoint triggers, full variable access, successful entity creation

#### Test Case 2: Service Call Debugging
**Scenario**: Execute complete_chore service with debugging
**Steps**: Set breakpoints → Use Developer Tools → Execute service → Step through handler
**Success**: Service debugging works, entity state changes visible, coordinator updates tracked

#### Test Case 3: Hot Code Reloading
**Scenario**: Modify entity attribute calculation and test immediately
**Steps**: Edit sensor.py → Set breakpoint → Trigger entity update → Verify changes
**Success**: Changes take effect within 5 seconds, debugging works with new code

#### Test Case 4: Safety Validation
**Scenario**: Verify no accidental commits to HASS core
**Steps**: Work in debugging environment → Check git remotes → Verify commit destinations
**Success**: All commits go to integration repo only, zero HASS core modifications

## 📋 DEBUGGING CHECKLIST

Before declaring debugging NFR complete, verify:

- [ ] **Breakpoints**: Set and trigger breakpoints in all integration files
- [ ] **Variables**: Inspect coordinator data, entity state, service parameters
- [ ] **Hot Reload**: Edit code and test changes within 5 seconds
- [ ] **Safety**: Verify git operations target correct repository
- [ ] **UI Integration**: Debug config flow, entity configuration, service calls
- [ ] **Documentation**: Complete debugging guides available
- [ ] **Performance**: Meet all timing requirements for debugging operations
- [ ] **Reliability**: 100% success rate for debugging workflows

---

**CRITICAL REMINDER**: This NFR supersedes all other requirements. Any architectural decision that compromises debugging capabilities must be rejected or redesigned to maintain full debugging support.
