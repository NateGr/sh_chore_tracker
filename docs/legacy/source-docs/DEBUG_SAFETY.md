# 🛡️ COMPREHENSIVE DEBUGGING GUIDE

> **PRIMARY NFR**: Debugging is a CRITICAL requirement. This integration is architected for debugging-first development.

## ✅ Safe Debugging Setup

### Current Configuration:

- **Source Code**: `/workspaces/ha-chore-tracker/` (YOUR repo)
- **Home Assistant**: `/workspaces/home-assistant/` (CORE repo)
- **Debugging**: Symlink from HA → Your repo (safe!)

### 🚀 Current Debugging Capabilities

**Full VS Code Debugging Setup**:

- ✅ **Breakpoint Debugging**: Set breakpoints in source files, debug through HASS execution
- ✅ **Variable Inspection**: Examine coordinator data, entity states, service parameters in real-time
- ✅ **Hot Code Reloading**: Edit code and test immediately via symlink architecture
- ✅ **Safe Workflow**: Symlink prevents accidental commits to HASS core repository
- ✅ **Hub Integration Testing**: Debug the hub setup and chore subentry flows through the HASS UI
- ✅ **Config Flow Debugging**: Step through the hub ConfigFlow and chore ConfigSubentryFlow
- ✅ **Service Call Debugging**: Debug complete_chore, snooze_chore service handlers
- ✅ **Entity State Debugging**: Monitor ChoreEntity state transitions and attribute updates

### 🎯 How Debugging Works:

1. **Edit files** in `/workspaces/ha-chore-tracker/custom_components/sh_chore_tracker/`
2. **Set breakpoints** in VS Code on your source files
3. **Use Home Assistant UI** to trigger code execution
4. **Breakpoints hit** in your source files ✅
5. **All commits** stay in your repo only ✅

## ♻️ Rebuild-Safe Repo Workflows

If a dev container rebuild resets your working tree, this is where the "commit or stash first" pain comes from. Use one of the approaches below to keep your integration changes safe.

### Approach A (Recommended): Sibling Repo + Symlink

Keep the integration in a separate sibling repo and link it into Home Assistant's `config/custom_components` path.

Why this works:

- Changes are isolated from Home Assistant core history.
- Fast debug loop with breakpoints and live code updates.
- Cleanest day-to-day workflow for custom integration development.

Example:

```bash
# Clone once inside the dev container workspace
cd /workspaces
git clone https://github.com/NateGr/ha-chore-tracker.git

# Link integration into Home Assistant custom components
ln -sf /workspaces/ha-chore-tracker/custom_components/sh_chore_tracker \
			 /workspaces/home-assistant/config/custom_components/sh_chore_tracker

# Verify link target
ls -la /workspaces/home-assistant/config/custom_components/sh_chore_tracker
```

### Approach B: Persistent Mount for Integration Source

Store the integration source in a bind mount or named volume that survives container rebuilds, then keep the same symlink pattern.

Why this works:

- Rebuilding container image does not delete source files.
- No forced stash/commit cycle just to rebuild.

Example devcontainer mount idea:

```json
"mounts": [
	"source=${localWorkspaceFolder}/../ha-chore-tracker,target=/workspaces/ha-chore-tracker,type=bind"
]
```

Then recreate symlink as in Approach A.

### Approach C: WIP Snapshot Before Rebuild

If you cannot change mounts yet, snapshot quickly before rebuild and restore after.

Option 1: WIP commit (preferred over stash for traceability)

```bash
cd /workspaces/ha-chore-tracker
git add -A
git commit -m "wip: snapshot before devcontainer rebuild"
# Optional: push to a WIP branch for backup
git push origin HEAD
```

Option 2: stash workflow

```bash
cd /workspaces/ha-chore-tracker
git stash push -u -m "pre-rebuild $(date +%F-%H%M)"

# After rebuild
git stash list
git stash pop
```

### Quick Decision Guide

- Use Approach A for normal daily development.
- Add Approach B when rebuilds are frequent.
- Use Approach C as a fallback or temporary safety net.

## ⚠️ SAFETY REMINDERS:

### ✅ DO:

- Work in `/workspaces/ha-chore-tracker/`
- Set breakpoints in your source files
- Commit changes to your repo
- Use `git status` to verify you're in the right repo

### ❌ DON'T:

- Edit files in `/workspaces/home-assistant/custom_components/`
- Commit anything in the Home Assistant workspace
- Remove the safety symlink during development

### 🔍 Safety Check Commands:

```bash
# Verify you're in the right directory
pwd  # Should show: /workspaces/ha-chore-tracker

# Check git repo
git remote -v  # Should show: NateGr/ha-chore-tracker.git

# Verify symlink
ls -la /workspaces/home-assistant/custom_components/sh_chore_tracker
# Should show: -> /workspaces/ha-chore-tracker/...
```

### 🚨 If You Accidentally Work in Wrong Directory:

```bash
# Check what repo you're in
git remote -v

# If it shows home-assistant (WRONG):
cd /workspaces/ha-chore-tracker  # Go to YOUR repo
git status  # Verify no unexpected changes

# If it shows ha-chore-tracker (CORRECT):
# You're good! Continue working.
```

---

## 🚀 ADVANCED DEBUGGING WORKFLOWS

### Config Flow Debugging

```python
# Set breakpoints in config_flow.py at:
async def async_step_user(self, user_input=None):
# Debug: Entity creation through HASS UI

async def async_config_entry_title(self, options):
# Debug: Entry title generation

def _get_chore_schema(hass=None, defaults=None):
# Debug: Schema generation with person entity discovery
```

### Service Handler Debugging

```python
# Set breakpoints in __init__.py at:
async def complete_chore_handler(call):
# Debug: Service call processing

async def snooze_chore_handler(call):
# Debug: Snooze logic and next due date calculation

# Test via: Developer Tools → Services → sh_chore_tracker.complete_chore
```

### Entity State Debugging

```python
# Set breakpoints in sensor.py at:
async def async_update(self):
# Debug: Entity state refresh

@property
def native_value(self):
# Debug: Status value calculation

@property
def extra_state_attributes(self):
# Debug: Rich attribute population (days_until_due, etc.)
```

### Chore Subentry Testing Workflow

1. **Add Hub**: Settings → Devices & Services → Add Integration → Chore Tracker
2. **Set Breakpoint**: Place in the hub `async_step_user()` in config_flow.py
3. **Configure**: Create the first chore, then add more through chore subentries
4. **Edit Chore**: Reconfigure a chore from the hub's subentry controls
5. **Set Breakpoint**: Place in `ChoreTrackerChoreSubentryFlow.async_step_reconfigure()`
6. **Test Services**: Developer Tools → Services → sh_chore_tracker.\*
7. **Debug Live**: Step through service handlers and entity updates

## 📊 DEBUGGING SUCCESS METRICS (NFR Validation)

### Primary NFR Checkpoints:

- ✅ **Breakpoint Hit Rate**: 100% of set breakpoints trigger during testing
- ✅ **Variable Access**: Full read/write access to all integration state
- ✅ **Code Change Response**: <5 seconds from edit to test execution
- ✅ **Safety Score**: Zero accidental commits to wrong repository
- ✅ **Integration Testing**: All config flows, services, entities debuggable via HASS UI

### Debugging Test Cases:

1. **Config Flow**: Create chore through UI with breakpoints
2. **Service Calls**: Execute complete_chore with variable inspection
3. **Entity Updates**: Monitor state transitions during operations
4. **Error Handling**: Test invalid inputs with debug visibility
5. **Performance**: Profile coordinator updates and entity refresh

## 🎯 Current Architecture: Household Hub

One hub entry owns chore subentries, a shared coordinator, and household aggregate entities.

---

## 🔧 DEBUGGING QUICK REFERENCE

### Essential Breakpoint Locations:

- `config_flow.py:async_step_user()` - Entity creation
- `__init__.py:complete_chore_handler()` - Service processing
- `sensor.py:native_value` - State calculation
- `sensor.py:extra_state_attributes` - Attribute population

### VS Code Debugging Commands:

- **F5**: Start debugging (launch HASS)
- **F9**: Toggle breakpoint
- **F10**: Step over
- **F11**: Step into
- **Shift+F11**: Step out
- **Ctrl+Shift+F5**: Restart debugging

### HASS Testing Commands:

- **Developer Tools → Services**: Test service calls
- **Developer Tools → States**: Monitor entity states
- **Settings → Devices & Services**: Integration management
- **Settings → Entities**: Entity configuration
