# Story 3.4: Config Flow Translatable Labels

**Epic**: Epic 3 — Person Assignment & Advanced Features
**Status**: 🎯 Planned
**Effort**: 2 story points
**Priority**: Low

## User Story

**As a** non-English Home Assistant user,
**I want** all config flow dropdowns to display labels in my language,
**so that** I can configure chores without needing to understand English technical terms.

## Background

The config flow currently uses hardcoded English strings as option labels in all SelectSelector dropdowns (recurrence type, interval unit, weekdays, months). These are not passed through HA's translation system and therefore cannot be localized.

The field name labels (`chore_name`, `pattern_interval`, etc.) are already translatable via `strings.json` `data` keys. This story extends that coverage to selector option values.

## Acceptance Criteria

- [ ] All recurrence type option labels are resolved from translation keys, not hardcoded
- [ ] All interval unit option labels are resolved from translation keys
- [ ] All weekday option labels are resolved from translation keys
- [ ] All month option labels are resolved from translation keys
- [ ] `strings.json` contains a `selector` section with all option label keys
- [ ] `translations/en.json` provides English baseline for all new keys
- [ ] No hardcoded English option label strings remain in `config_flow.py`
- [ ] Existing behavior and option values are unchanged (only labels change)

## Technical Notes

HA's SchemaConfigFlowHandler resolves selector option labels through the `strings.json` translation system when options are defined without explicit `label` keys and translation keys are provided in the `selector` section of the strings file.

Reference pattern used in HA core integrations:

```json
"selector": {
  "recurrence_type": {
    "options": {
      "interval": "Every X units after completion",
      "weekly": "Weekly on specific days"
    }
  }
}
```

This story should be done as a single atomic change — update all four selectors together to keep the translation file consistent.

## Out of Scope

- Adding translations for languages other than English (en.json baseline only)
- Any behavioral changes to the config flow
- Changes to option `value` keys (only labels)
