# Contributing

Fork the repository, create a branch from `main`, make your change, and open a
pull request. Keep changes focused; update tests and user-facing documentation
when behavior changes. Conventional commits and release preparation are not
required from contributors.

## Local Setup

Use Python 3.14.x (CI pins 3.14.2) with Home Assistant 2026.9.0. This does not
claim compatibility with future Python minor versions. The test requirements pin Home Assistant to the
minimum supported version in `hacs.json`. A running Home Assistant server is
not required; tests use Home Assistant's installed Python package and mocked
instances where needed.

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
python -m pytest tests/ --cov=scripts --cov=custom_components/sh_chore_tracker --cov-report=term-missing
```

Use `python -m ruff format --exclude '*.md' .` to apply formatting. Review any automatic lint fixes
before committing. CI also measures coverage for
`custom_components/sh_chore_tracker`.

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