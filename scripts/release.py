"""Validate repository readiness and select stable release versions."""

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("custom_components/chore_tracker/manifest.json")
VERSION_PATTERN = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def parse_version(value: str) -> tuple[int, int, int]:
    if not VERSION_PATTERN.fullmatch(value):
        raise ValueError(f"Expected stable version X.Y.Z without a v prefix: {value!r}")
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def select_version(current: str, bump: str, override: str = "") -> str:
    major, minor, patch = parse_version(current)
    if override:
        if parse_version(override) <= (major, minor, patch):
            raise ValueError("New version must be greater than the release baseline.")
        return override
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unknown version bump: {bump}")


def release_baseline(current: str, pages: list) -> str:
    versions = [parse_version(current)]
    for page in pages:
        for release in page:
            if release["draft"] or release["prerelease"]:
                continue
            tag = release["tag_name"].removeprefix("v")
            try:
                versions.append(parse_version(tag))
            except ValueError:
                continue
    return ".".join(str(part) for part in max(versions))


def git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=root, text=True, encoding="utf-8"
    ).strip()


def prepare(root: Path, pages: list, bump: str, override: str) -> dict[str, str]:
    check_readiness(root, require_integration=True)
    manifest_path = root / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = select_version(release_baseline(manifest["version"], pages), bump, override)
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/tags/v{version}"], cwd=root
    )
    if result.returncode != 1:
        raise ValueError(f"Tag v{version} already exists or tag lookup failed.")
    manifest["version"] = version
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"version": version}


def verify_release_metadata(previous: dict, candidate: dict, version: str) -> None:
    if candidate.get("version") != version:
        raise ValueError("Release manifest version does not match the requested tag.")
    if parse_version(version) <= parse_version(previous["version"]):
        raise ValueError("Release commit does not increase the manifest version.")
    previous = previous.copy()
    previous["version"] = version
    if previous != candidate:
        raise ValueError("Release commit must change only manifest.version.")


def recover(root: Path, version: str) -> dict[str, str]:
    parse_version(version)
    if git(root, "cat-file", "-t", f"refs/tags/v{version}") != "tag":
        raise ValueError("Recovery requires an annotated release tag.")
    candidate = git(root, "rev-parse", f"refs/tags/v{version}^{{commit}}")
    git(root, "merge-base", "--is-ancestor", candidate, "origin/main")
    parents = git(root, "rev-list", "--parents", "-n", "1", candidate).split()
    if len(parents) != 2:
        raise ValueError("Expected a release commit with exactly one parent.")
    message = git(root, "show", "-s", "--format=%B", candidate)
    if f"SmartHass-Release: {version}" not in message.splitlines():
        raise ValueError("Tag does not point to a recognized release commit.")
    files = git(root, "diff", "--name-only", parents[1], candidate).splitlines()
    if files != [MANIFEST.as_posix()]:
        raise ValueError("Release commit must change only the integration manifest.")
    previous = json.loads(git(root, "show", f"{parents[1]}:{MANIFEST.as_posix()}"))
    manifest = json.loads(git(root, "show", f"{candidate}:{MANIFEST.as_posix()}"))
    verify_release_metadata(previous, manifest, version)
    return {"version": version, "candidate": candidate}


def check_readiness(root: Path, *, require_integration: bool = False) -> bool:
    configuration = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    ready = configuration["tool"]["smarthass"]["integration-ready"]
    if not isinstance(ready, bool):
        raise ValueError("integration-ready must be a TOML boolean.")
    integration = root / MANIFEST.parent
    if not ready:
        if require_integration or integration.exists():
            raise ValueError(
                "Integration is not enabled. Import source/tests, verify HA dependencies "
                "and metadata, then set tool.smarthass.integration-ready = true."
            )
        return False
    if not (integration / "__init__.py").is_file():
        raise ValueError("Missing imported integration __init__.py.")
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    expected = {
        "domain": "chore_tracker",
        "name": "SmartHass Chore Tracker",
        "documentation": "https://github.com/NateGr/sh_chore_tracker",
        "issue_tracker": "https://github.com/NateGr/sh_chore_tracker/issues",
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"manifest.{key} must be {value!r}.")
    parse_version(manifest["version"])
    if "@NateGr" not in manifest.get("codeowners", []):
        raise ValueError("manifest.codeowners must include @NateGr.")
    if not (integration / "brand/icon.png").is_file():
        raise ValueError("Missing integration brand/icon.png required for HACS.")
    hacs = json.loads((root / "hacs.json").read_text(encoding="utf-8"))
    if hacs.get("name") != expected["name"] or hacs.get("content_in_root") is not False:
        raise ValueError("HACS metadata must match the integration name and layout.")
    if not hacs.get("homeassistant"):
        raise ValueError("Set hacs.homeassistant to the verified minimum HA version.")
    if hacs.get("zip_release") or "filename" in hacs:
        raise ValueError("Use tagged repository files, not custom HACS ZIP releases.")
    tests = list((root / "tests").rglob("test_*.py"))
    if not any(path.name != "test_release.py" for path in tests):
        raise ValueError("Import integration tests; release-helper tests alone are insufficient.")
    requirements = (root / "requirements_test.txt").read_text(encoding="utf-8")
    if not re.search(r"^pytest-homeassistant-custom-component==\S+", requirements, re.MULTILINE):
        raise ValueError("Pin a verified pytest-homeassistant-custom-component dependency.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "prepare", "recover"])
    parser.add_argument("--require-integration", action="store_true")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="patch")
    parser.add_argument("--version", default="")
    parser.add_argument("--releases", type=Path)
    arguments = parser.parse_args()
    try:
        if arguments.command == "check":
            ready = check_readiness(ROOT, require_integration=arguments.require_integration)
            values = {"integration-ready": str(ready).lower()}
            print(
                "Integration validation enabled."
                if ready
                else "Scaffold only; integration not imported."
            )
        elif arguments.command == "recover":
            values = recover(ROOT, arguments.version)
        else:
            if arguments.releases is None:
                raise ValueError("prepare requires --releases with paginated GitHub release JSON.")
            pages = json.loads(arguments.releases.read_text(encoding="utf-8"))
            values = prepare(ROOT, pages, arguments.bump, arguments.version)
    except (KeyError, OSError, TypeError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Release preflight failed: {error}\n")
    print(json.dumps(values))
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            for key, value in values.items():
                stream.write(f"{key}={value}\n")


if __name__ == "__main__":
    sys.exit(main())
