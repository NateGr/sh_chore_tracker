# Contributing

Fork the repository, create a branch from `main`, make your change, and open a
pull request. Keep changes focused; update tests and user-facing documentation
when behavior changes. Conventional commits and release preparation are not
required from contributors.

## Local Setup

Use Python 3.13 to match CI. The integration and its tests are imported, but the
Home Assistant test dependency and supported-version baseline are not yet
verified. A running Home Assistant server is not required for scaffold checks;
integration tests should use Linux, WSL2, or another supported HA development
environment.

Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements_test.txt
```

Linux or macOS:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements_test.txt
```

If PowerShell activation is unavailable, invoke
`.\.venv\Scripts\python.exe` instead of `python`; no execution-policy change is
needed. Native Windows supports the scaffold checks. Home Assistant integration
tests should use Linux, WSL2, or another supported Home Assistant development
environment once dependencies are selected.

## Checks

Run the same local checks used by CI:

```bash
python scripts/release.py check
python -m ruff check .
python -m ruff format --check .
python -m pytest tests/ --cov=scripts --cov-report=term-missing
```

Use `python -m ruff format .` to apply formatting. Review any automatic lint fixes
before committing. Once integration validation is enabled, add
`--cov=custom_components/chore_tracker` to the pytest command to match CI coverage.

CI also runs hassfest on imported integration files and HACS validation when the
repository is public. A green scaffold check does not mean the integration has
been tested. The readiness gate remains disabled until the maintainer completes
the import and validation checklist.

## Testing In Home Assistant

After import, copy `custom_components/chore_tracker` into a disposable Home
Assistant configuration's `custom_components` directory and restart it. Use
backups and a test instance, not production household data. Keep local Home
Assistant configuration, tokens, logs, and `.storage` files out of this repo.

## Pull Requests

Describe the problem, the change, and checks performed. Do not bump the
integration version for ordinary changes. Maintainers can merge multiple PRs
before releasing; the Release workflow handles versioning and publication.

For suspected vulnerabilities, follow the [security policy](.github/SECURITY.md)
instead of opening a public issue.