"""Verify tested Home Assistant versions and report available fixture updates."""

import argparse
import json
import re
import sys
from importlib.metadata import version
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
LATEST_REQUIREMENTS = ROOT / "requirements" / "latest" / "requirements.txt"
PLUGIN = "pytest-homeassistant-custom-component"


def stable_version(value: str) -> tuple[int, int, int]:
    """Require an ordinary stable Home Assistant release."""
    if not re.fullmatch(r"\d{4}\.\d+\.\d+", value):
        raise ValueError(f"Expected a stable Home Assistant version, got {value!r}.")
    return tuple(int(part) for part in value.split("."))


def check_installed(mode: str, minimum: str, installed: str) -> None:
    minimum_version = stable_version(minimum)
    installed_version = stable_version(installed)
    if mode == "minimum" and installed_version != minimum_version:
        raise ValueError(f"Minimum environment has Home Assistant {installed}, expected {minimum}.")
    if mode == "latest" and installed_version < minimum_version:
        raise ValueError(f"Latest environment has Home Assistant {installed}, below {minimum}.")
    print(f"{mode.capitalize()} environment: Home Assistant {installed}")


def pypi_info(package: str) -> dict:
    with urlopen(f"https://pypi.org/pypi/{package}/json", timeout=30) as response:
        return json.load(response)["info"]


def check_updates(homeassistant: dict, plugin: dict, requirements: str) -> None:
    latest_ha = homeassistant["version"]
    stable_version(latest_ha)
    plugin_version = plugin["version"]
    pinned_ha = [
        match.group(1)
        for dependency in plugin["requires_dist"]
        if (match := re.fullmatch(r"homeassistant==([^\s;]+)", dependency, re.IGNORECASE))
    ]
    if len(pinned_ha) != 1:
        raise ValueError("Latest fixture plugin must pin exactly one Home Assistant version.")
    fixture_ha = pinned_ha[0]
    stable_version(fixture_ha)
    pins = re.findall(rf"^{re.escape(PLUGIN)}==(\S+)$", requirements, re.MULTILINE)
    if len(pins) != 1:
        raise ValueError("Latest requirements must pin exactly one fixture plugin version.")

    print(f"Latest stable Home Assistant: {latest_ha}")
    print(f"Latest fixture plugin: {plugin_version} (Home Assistant {fixture_ha})")
    print(f"Configured fixture plugin: {pins[0]}")
    problems = []
    if pins[0] != plugin_version:
        problems.append("The latest fixture plugin is not pinned; review the Dependabot update.")
    if stable_version(fixture_ha) != stable_version(latest_ha):
        problems.append("The latest fixture plugin does not test the latest stable Home Assistant.")
    if problems:
        raise ValueError(" ".join(problems))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("minimum", "latest", "updates"))
    args = parser.parse_args()
    try:
        if args.mode == "updates":
            check_updates(
                pypi_info("homeassistant"),
                pypi_info(PLUGIN),
                LATEST_REQUIREMENTS.read_text(encoding="utf-8"),
            )
        else:
            minimum = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))["homeassistant"]
            check_installed(args.mode, minimum, version("homeassistant"))
    except (ValueError, KeyError, OSError) as exc:
        print(f"Home Assistant compatibility check failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
