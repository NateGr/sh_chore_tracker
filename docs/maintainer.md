# Maintainer Guide

## Current State

The repository scaffold and release helper are ready. The hub integration package,
tests, and branding have been imported and adapted to the `chore_tracker` domain.
The Home Assistant test dependency, supported-version baseline, migration behavior,
and branding license still need verification. `tool.smarthass.integration-ready`
in `pyproject.toml` remains deliberately `false`; releases, including dry runs,
refuse to proceed until validation is complete.

The source repository's docs, user stories, and backlog snapshots are preserved
in the [legacy archive](legacy/README.md). They span several architectures and
should be triaged against the current hub code before being treated as active work.

## Import Checklist

1. Audit the imported `custom_components/chore_tracker`, tests, runtime assets,
  useful user docs, and attribution. Do not copy the source `.git`, development
  HA configuration, editor tasks, agent/tooling directories, or release
  automation into the operational tree. Historical docs and backlogs belong in
  `docs/legacy/` and are not active release requirements.
2. Preserve `chore_tracker`, entity unique IDs, config-entry identity/version,
   service names, and storage keys. Update the manifest display name to
   `SmartHass Chore Tracker`, documentation to
   `https://github.com/NateGr/sh_chore_tracker`, issue tracker to that URL plus
   `/issues`, and include `@NateGr` in codeowners. Retain the actual current
   version and required runtime metadata.
3. Review imported tests before changing behavior. Select a compatible Python,
   Home Assistant, and `pytest-homeassistant-custom-component` combination;
   add a verified exact plugin pin to `requirements_test.txt`. Adjust pytest and
   coverage pins together if needed. Enable only the asyncio/HA fixtures the
   imported tests actually need. Do not infer compatibility from old docs.
4. If the supported Python changes, update both setup-python steps and the Ruff
   target in `pyproject.toml`, plus the contributor instructions. Set
   `homeassistant` in `hacs.json` to the tested minimum and document it in README.
5. Add a licensed `custom_components/chore_tracker/brand/icon.png`. Keep all
   runtime integration files inside the integration directory. No custom ZIP
   release is needed.
6. Set `tool.smarthass.integration-ready = true`. Run the contributor checks,
   `python scripts/release.py check --require-integration`, and the complete
   imported test suite. The flag is an explicit maintainer assertion, not proof
   that its dependency pins or minimum HA version have been tested.
7. Remove the README's pending-import notice only when it is accurate to do so.
   Retain any useful legacy changelog as historical documentation; GitHub release
   notes are the source of new release history.

## GitHub Setup

Commit and push the scaffold when ready. Hosting settings are not configured by
these files. Do not enable required checks until the workflow has run and GitHub
offers the correct check name.

### Repository

Use `main` as the default branch. Add a description and topics such as
`home-assistant`, `hacs`, `custom-component`, and `python`. Enable Issues, squash
merges, and automatic deletion of merged branches. Disable unused wiki/projects.
Do not auto-merge dependency updates.

#### Security settings status

- [x] Dependency graph enabled.
- [x] Dependabot vulnerability reporting enabled.
- [ ] Check whether Dependabot security updates are available and enable them
  if appropriate; review update PRs rather than enabling auto-merge.
- [ ] Private vulnerability reporting was not visible in repository settings;
  revisit after confirming plan/organization availability.
- [ ] Secret scanning and push protection were not available in repository
  settings; revisit after confirming plan/organization availability.

### Release App

1. Register a dedicated GitHub App, with webhooks disabled unless needed. Grant
   repository **Contents: read and write**, plus required metadata read access.
   Do not grant administration or workflow-modification permissions.
2. Install it only on `NateGr/sh_chore_tracker`.
3. Create a GitHub environment named `release`, restricted to the branch `main`
   using selected deployment branches. Do not permit arbitrary branches or tags.
   No extra required reviewer is needed for the routine one-button release.
4. Add environment variable `RELEASE_APP_CLIENT_ID` and environment secret
   `RELEASE_APP_PRIVATE_KEY`. Enter the private key directly in GitHub; never
   commit it or paste it into issues or an assistant conversation.

The workflow mints a repository-scoped installation token only after validation,
uses it for the release commit/tag push, and revokes it on job completion. The
publish job uses the built-in token and does not check out or run repository code.
PR CI has no release environment or write token.

### Rulesets

- A `main` PR ruleset: require pull requests, successful **Validate** check from
  the **CI** workflow, up-to-date branches, and resolved conversations. Confirm
  the exact status-check name after the first CI run. Use zero required approving
  reviews so a solo maintainer can merge their own passing PRs.
- Add the release App to that ruleset's bypass list with **Always allow**. A
  pull-request-only bypass cannot push the automated release commit.
- A separate `main` safety ruleset: block force pushes and deletion, with no
  release-App bypass.
- A `v*` tag ruleset: block updates and deletion. Do not restrict tag creation in
  a way that blocks the release App. Published tags must remain immutable.

Ruleset bypass is a real privilege: GitHub cannot limit an App credential to one
workflow merely through the bypass list. Review changes to workflows and local
actions carefully, and keep the private key in the main-only release environment.
Pinned action wrappers can still execute upstream Docker images tagged latest or
main; hassfest/HACS updates therefore require awareness beyond SHA pins.

## Releasing

Merge any number of normal PRs first. Versions are not bumped in those PRs.

1. Open **Actions > Release > Run workflow**, selecting branch **main**.
2. Choose **patch** (default), **minor**, or **major**. An optional explicit
   stable `X.Y.Z` version overrides the bump; leave recovery empty.
3. Click **Run workflow**. There is no release PR or separate Publish button.

The workflow starts above the higher of the manifest version and all published
stable versions. It creates a local version-only commit, validates that exact
candidate, and atomically pushes the commit to `main` and an annotated `vX.Y.Z`
tag. It then publishes a GitHub release with generated notes. Add important
breaking-change or migration details to the notes when needed; ordinary
contributors need not maintain a duplicate changelog.

The workflow is manual-only: merging PRs, App-generated pushes, and tag events
never invoke another release. App pushes can invoke ordinary CI. The per-repo
release concurrency group prevents overlap; GitHub may replace an older pending
run if multiple additional requests are queued, so do not queue repeated clicks.

Select **dry-run** to validate the proposed release without creating remote refs
or a release. A private repo permits dry runs but skips HACS checks; production
publication requires public visibility and passing HACS validation.

If `main` advances while validation runs, the push is rejected. Rerun against
the new commit. The workflow never rebases validated code or force-pushes.

### Recovery

If **Validate and tag** succeeded but **Publish** failed, use **Re-run failed
jobs** on that workflow run. This retries publication of the recorded tag/SHA
without creating another version.

Alternatively, dispatch Release with **recover-version** set to the existing
version, leaving **version** empty. The helper verifies the tag belongs to `main`,
points to a recognized version-only release commit, and matches the manifest;
it then validates that tagged code and retries publication. An already published
stable release returns its URL without duplication. A conflicting draft or
prerelease fails instead of being silently promoted. Do not delete or move tags.

Do not use a fresh default patch release to recover a publishing failure: that
would create another version. Missing App credentials, failed checks, duplicate
tags, and invalid versions stop the release rather than weakening the gates.

## Public Cutover

- Audit copied files and this repo's history for secrets, household data, private
  URLs, destructive dev scripts, and licensing. Copying files instead of old Git
  history reduces accidental disclosure. Rotate any exposed secrets; ignoring or
  deleting them is not sufficient.
- Make the repository public only after that audit. Run CI with actual repository
  metadata and HACS checks enabled. HACS catalog inclusion is a separate optional
  submission; custom-repository installation does not require it.
- Run a dry release, then publish a version higher than the actual old release
  baseline. Check tagged HACS installation and manual installation in a disposable
  HA instance; no production household config should be used as a test sandbox.
- Back up an existing installation and test the repository switch. Do not delete
  HA integration entries or `.storage`. Do not leave both repositories managing
  `chore_tracker`. HACS removal may remove installed files: test its current
  behavior and reinstall from the new repo before restarting HA.
- Verify entities, configuration, chores, and completion history survive. Publish
  the exact tested migration steps; do not assume GitHub or HACS redirects them.
- Only then update old support/install links, migrate essential issues, disable
  old release automation, and archive the old repo read-only. If it remains
  private, notify existing users directly. Preserve useful historical releases.

## Verification Before First Release

Verify a clean checkout and full HA test baseline on supported Python/Linux,
actual fork and docs-only PR checks, a failed check blocking merge, a release dry
run, App bypass against the rulesets, and successful HACS install/upgrade.
Exercise invalid versions, stale-main rejection, duplicate tags, and publication
recovery. Local scaffold tests do not prove GitHub permissions or HA compatibility.