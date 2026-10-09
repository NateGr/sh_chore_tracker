# SmartHass Chore Tracker

A Home Assistant custom integration for tracking household chores.

This repository is being prepared as the public successor to
[ha-chore-tracker](https://github.com/NateGr/ha-chore-tracker). The integration
code has not been imported yet. There is no installable release here currently.

## Installation

Once the first release is published:

### HACS

1. Add `https://github.com/NateGr/sh_chore_tracker` as a custom repository in HACS,
   with type **Integration**.
2. Install **SmartHass Chore Tracker** and restart Home Assistant.
3. Add the integration through **Settings > Devices & services**.

### Manual

Download a published release's source archive from
[Releases](https://github.com/NateGr/sh_chore_tracker/releases), then copy
`custom_components/chore_tracker` into your Home Assistant configuration's
`custom_components` directory and restart Home Assistant.

The minimum supported Home Assistant version will be published after the imported
integration has been tested. Repository tooling currently uses Python 3.13 in CI;
this is not a Home Assistant compatibility claim.

## Existing Users

The integration domain remains `chore_tracker`. Do not delete existing Home
Assistant integration entries or install both repositories at the same time.
Tested migration instructions will be published before the old repository is
retired. Back up Home Assistant before switching repositories.

## Contributing And Support

- [Contributing](CONTRIBUTING.md): local setup, checks, and pull requests.
- [Maintainer guide](docs/maintainer.md): releases, GitHub setup, and migration.
- [Issues](https://github.com/NateGr/sh_chore_tracker/issues): bugs and suggestions.
- [Security policy](.github/SECURITY.md): privately report vulnerabilities.

Distributed under the [MIT license](LICENSE).