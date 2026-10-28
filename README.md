# SmartHass Chore Tracker

SmartHass Chore Tracker is a Home Assistant custom integration for scheduling,
assigning, and tracking household chores. Create chores from Home Assistant's
configuration flow, monitor due dates from chore sensors, and manage chores with
dashboard controls, services, and automations.

Requires **Home Assistant 2025.1 or newer**.

## Features

- Schedule chores on interval, weekly, monthly, or yearly recurrence patterns.
- Assign chores to Home Assistant people and reassign them as responsibilities
  change.
- Track due dates, overdue chores, completion history, and household summaries.
- Complete, snooze, skip, restore, and reset chores using buttons or services.
- Automate chore workflows with Home Assistant events and service calls.

## Installation

### HACS

1. In HACS, open **Integrations** and select the menu in the upper-right corner.
2. Select **Custom repositories** and add
   `https://github.com/NateGr/sh_chore_tracker` with category **Integration**.
3. Find and install **SmartHass Chore Tracker**, then restart Home Assistant.

### Manual

1. Download the latest release from
   [Releases](https://github.com/NateGr/sh_chore_tracker/releases).
2. Copy `custom_components/chore_tracker` into your Home Assistant
   configuration's `custom_components` directory.
3. Restart Home Assistant.

## Setup

1. In Home Assistant, go to **Settings > Devices & services** and select
   **Add Integration**.
2. Search for **SmartHass Chore Tracker**.
3. Follow the guided flow to create the household hub and first chore. Add or
   edit additional chores from the hub's chore controls.

The integration creates a sensor for each chore and household summary sensors
for the nearest due chore and overdue chore count. Chore devices include buttons
for common actions. See the [configuration reference](docs/configuration-reference.md)
and [service reference](docs/service-reference.md) for scheduling options,
entity details, services, and automation examples.

## Upgrading

The integration domain is `chore_tracker`. Back up your Home Assistant
configuration before upgrading, and do not install copies of the integration
from multiple repositories at the same time.

## Contributing And Support

- [Contributing](CONTRIBUTING.md): local setup, checks, and pull requests.
- [Maintainer guide](docs/maintainer.md): releases, GitHub setup, and migration.
- [Issues](https://github.com/NateGr/sh_chore_tracker/issues): bugs and suggestions.
- [Security policy](.github/SECURITY.md): privately report vulnerabilities.

Distributed under the [MIT license](LICENSE).