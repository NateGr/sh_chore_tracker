# Maintainer Guide

## Supported Baseline

The integration supports fresh installations and existing version-3 household
hubs on Home Assistant 2026.9.0 or newer. Older helper/per-chore layouts and
unsupported entry versions are rejected without rewriting or deleting data.
Preserve the `sh_chore_tracker` domain, entry version, stable chore IDs, storage
keys, and persisted runtime state when changing the implementation.

CI uses Ubuntu 24.04 and Python 3.14.2 with isolated fixture environments for
the minimum Home Assistant 2026.9.0 and latest fixture-supported 2026.10.4.
The fixture plugin currently trails the latest stable Home Assistant 2026.11.3;
the weekly update monitor reports this gap rather than claiming stable has
been tested. Dependabot proposes updates to the latest fixture environment.
When changing the minimum, keep setup-python, Ruff, test requirements, HACS
metadata, and user documentation aligned. Shared CI and release validation
runs mypy and requires at least 80% integration-only line coverage in each
environment.

Runtime files belong in `custom_components/sh_chore_tracker`. HACS uses tagged
repository files; no custom ZIP release is needed. GitHub release notes record
release changes and any compatibility limitations.

## Validation

Follow the [contributor checks](../CONTRIBUTING.md) and run:

```bash
python scripts/release.py check --require-integration
```

Keep `tool.smarthass.integration-ready = true` only while integration tests and
metadata checks pass. This flag is not proof of live installation, licensing,
or hosted permissions. Test clean installation and version-3 hub replacement,
reload, and restart on a disposable Home Assistant instance. Back up existing
configuration and storage before making live changes.

## GitHub Setup

Configure hosting settings separately from the repository files. Verify the
actual CI check name in GitHub before making it required.

### Repository

Use `main` as the default branch. Add a description and topics such as
`home-assistant`, `hacs`, `custom-component`, and `python`. Enable Issues, squash
merges, and automatic deletion of merged branches. Disable unused wiki/projects.
Do not auto-merge dependency updates.

Review dependency alerts, private vulnerability reporting, secret scanning,
and push protection according to the repository's plan and visibility. Follow
the [security policy](../.github/SECURITY.md) for vulnerability reports.

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

To validate a feature branch before merging, select that branch and **dry-run**
in the Release workflow. It creates and validates a local candidate based on
that branch, without using the protected release environment or its App
credentials. It does not test the push or publication paths. Non-dry runs and
recovery are restricted to `main`.

If `main` advances while validation runs, the push is rejected. Rerun against
the new commit. The workflow never rebases validated code or force-pushes.

### Prereleases

Select **prerelease** to publish a test version. Choose a bump or provide a
stable target such as `0.5.3` without an `rc` suffix. The workflow automatically
numbers candidates from existing tags, for example `0.5.3rc1` and `0.5.3rc2`.
The target must be greater than the stable release baseline.

The workflow validates a separate version-only candidate, pushes only its
annotated tag, and publishes a GitHub prerelease without updating `main` or the
latest stable release. Testers can enable **Pre-release** for the repository in
HACS; the prerelease must be newer than their installed stable version to be
offered. A subsequent stable release follows the normal version selection and
publication path. Use **dry-run** to test either mode without publishing.

### Recovery

If **Validate and tag** succeeded but **Publish** failed, use **Re-run failed
jobs** on that workflow run. This retries publication of the recorded tag/SHA
without creating another version.

Alternatively, dispatch Release with **recover-version** set to the existing
version, leaving **version** empty. For a prerelease, use the full version, for
example `0.5.3rc1`; the workflow determines the release type from that version.
The helper verifies that the stable release commit, or the parent of the tag-only
prerelease commit, belongs to `main`. It also checks for a recognized
version-only release commit and matching manifest, then validates the tagged
code and retries publication. An existing release of the expected type returns
its URL without duplication; a conflicting draft or release type fails. Do not
delete or move tags.

Do not use a fresh default patch release to recover a publishing failure: that
would create another version. Missing App credentials, failed checks, duplicate
tags, and invalid versions stop the release rather than weakening the gates.

## Release Verification

Before publishing, verify a clean checkout, the full pinned Linux test suite,
hassfest, public HACS validation, and a release dry run. Confirm required checks
block a failing PR and the release App has only its intended bypass privileges.
A dry run does not exercise App token creation or the production push.

Review licensing, release content, and Git history for secrets or household
data. Rotate exposed credentials; deleting a file does not erase Git history.
Keep operational release records and credentials outside the public tree.

Exercise invalid-version rejection, stale-main rejection, tag collisions, and
publication recovery in a controlled context without moving published tags.
After publication, verify the release/tag SHA and tagged HACS/manual installation.
For existing version-3 hubs, confirm entity identity, chores, assignments, counts,
due dates, and completion history survive. Do not delete integration entries or
storage merely to switch repositories, or install two copies of the domain.