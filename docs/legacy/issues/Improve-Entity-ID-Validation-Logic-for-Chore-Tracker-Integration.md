### Problem:
The current validation logic for checking if an entity belongs to the sh-chore-tracker requires `entity_id` to start with "sensor.chore_". While this constraint ensures consistency, it's too tightly coupled to the naming pattern, which:
1. Reduces flexibility if the naming conventions evolve.
2. Prevents integration with non-standard chore entities.

### Proposed Resolutions:
To address this issue, three options are proposed:
1. **Regex-Based Validation:** Use a more flexible regex pattern (e.g., allowing prefixes like "sensor.chore." or other consistent namespace).
2. **Dynamic Metadata Check:** Query dynamic metadata associated with the entity or coordinator to evaluate its validity instead of relying solely on its name.
3. **Configuration-Based Prefixes:** Introduce user-defined prefixes in configuration to support custom naming conventions.

### Resolution Chosen: Integration `platform` Field (2026-05-31) [CLOSED]

After deeper investigation of HASS internals, none of the three originally proposed options were selected. Instead, the HASS entity registry's built-in `platform` field was used.

**Why this approach:**

The entity registry (`homeassistant/helpers/entity_registry.py`) records a `platform` field on every `RegistryEntry`. This field holds the integration domain that created the entity — for example, `sh_chore_tracker`. This is the exact same field the `auto-entities` Lovelace card exposes as its `integration` filter. It is naming-convention-independent and is the authoritative source for integration membership in HASS.

**What changed in code:**

- `_find_chore_data()` in `custom_components/sh_chore_tracker/__init__.py` now validates `entry.platform == DOMAIN` before returning a coordinator. Any entity not owned by this integration returns `(None, None)`.
- The brittle `entity_id.startswith("sensor.chore_")` guard in `_handle_service_call()` was removed. `_find_chore_data()` is now the single validation point.
- `tests/test_services.py`: `TestFindChoreData` and `TestHandleServiceCallIntegrationValidation` classes added. Full suite: 129 tests pass.

**Why not the originally proposed options:**

| Option | Verdict |
|---|---|
| Regex-based validation | Still a naming-convention check — same root brittleness |
| Dynamic metadata / coordinator check | What `_find_chore_data` already did; didn't prevent spoofing by name |
| Configuration-based prefixes | Adds complexity without addressing the root cause |
| **`entry.platform == DOMAIN`** | ✅ Authoritative, zero naming dependency, consistent with HASS internals |

### Agent Instructions:
1. Analyze the impacted logic in `custom_components/sh_chore_tracker/__init__.py`, specifically `_handle_service_call()`.
2. Implement the chosen resolution option.
3. Add unit tests to validate entity ID checks with the updated logic.

### Task:
Modify validation logic for chore entities. Select one resolution option to decouple the dependency between entity IDs and static naming conventions.