# Contributing

Fork the repository, create a branch from `main`, make your change, and open a
pull request. Keep changes focused; update tests and user-facing documentation
when behavior changes. Conventional commits and release preparation are not
required from contributors.

## Local Setup

Use Python 3.14.x (CI pins 3.14.2). This does not claim compatibility with
future Python minor versions. The minimum test environment uses Home Assistant
2026.9.0 and fixture plugin 0.13.363; a separate latest fixture environment
uses plugin 0.13.375 and Home Assistant 2026.10.4. A running Home Assistant
server is not required; tests combine fixture-backed Home Assistant instances
with focused mocked unit tests.

Update the minimum Home Assistant pin, fixture plugin, and `hacs.json` together
only after verifying compatibility. Dependabot updates the latest fixture
environment separately; update the minimum stack intentionally.

Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements_test.txt
```

Linux or macOS:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements_test.txt
```

If PowerShell activation is unavailable, invoke
`.\.venv\Scripts\python.exe` instead of `python`; no execution-policy change is
needed. Use Linux, WSL2, or another supported Home Assistant development
environment to run the test suite.

## Checks

Run the same local checks used by CI:

```bash
python scripts/release.py check
python -m ruff check .
python -m ruff format --check --exclude '*.md' .
python -m mypy custom_components/sh_chore_tracker/ --ignore-missing-imports
python scripts/check_ha_compatibility.py minimum
python -m pytest tests/ --cov=scripts --cov=custom_components/sh_chore_tracker --cov-report=term-missing
python -m coverage report --include='*/custom_components/sh_chore_tracker/*' --fail-under=80
```

For the latest fixture stack, create a separate Python 3.14 virtual environment,
install `requirements/latest/requirements.txt`, and run:

```bash
python scripts/check_ha_compatibility.py latest
python -m pytest tests/ --cov=scripts --cov=custom_components/sh_chore_tracker --cov-report=term-missing
python -m coverage report --include='*/custom_components/sh_chore_tracker/*' --fail-under=80
```

`python scripts/check_ha_compatibility.py updates` queries PyPI and reports
whether the latest fixture plugin and latest stable Home Assistant match. The
weekly CI monitor runs this check and fails when the fixture lags stable or
the latest plugin has not been pinned.

Use `python -m ruff format --exclude '*.md' .` to apply formatting. Review any automatic lint fixes
before committing. CI enforces at least 80% line coverage for the integration
alone; release-helper coverage does not count toward that threshold. The mypy
check ignores missing third-party imports and does not check untyped function
bodies by default.

CI also runs hassfest on the integration and HACS validation when the repository
is public. Passing automated checks does not replace a live Home Assistant
upgrade test; use a disposable instance for migration validation.

## Testing In Home Assistant

After import, copy `custom_components/sh_chore_tracker` into a disposable Home
Assistant configuration's `custom_components` directory and restart it. Use
backups and a test instance, not production household data. Keep local Home
Assistant configuration, tokens, logs, and `.storage` files out of this repo.

## Pull Requests

Describe the problem, the change, and checks performed. Do not bump the
integration version for ordinary changes. Maintainers can merge multiple PRs
before releasing; the Release workflow handles versioning and publication.

For suspected vulnerabilities, follow the [security policy](.github/SECURITY.md)
instead of opening a public issue.