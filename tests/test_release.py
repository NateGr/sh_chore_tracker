"""Exercise release versioning and fail-closed import checks without Home Assistant."""

import json
import subprocess
from pathlib import Path

import pytest

from scripts import release as release_module
from scripts.release import (
    MANIFEST,
    check_readiness,
    parse_version,
    prepare,
    recover,
    release_baseline,
    select_version,
    verify_release_metadata,
)


@pytest.mark.parametrize("version", ["0.0.0", "0.2.0", "12.34.56"])
def test_stable_version(version):
    assert parse_version(version) == tuple(int(part) for part in version.split("."))


@pytest.mark.parametrize(
    "version", ["v1.0.0", "1.0", "01.0.0", "1.0.0b1", "1.0.0\n", "1.0.0;echo bad", ""]
)
def test_invalid_version(version):
    with pytest.raises(ValueError):
        parse_version(version)


@pytest.mark.parametrize(
    ("bump", "expected"), [("patch", "1.2.4"), ("minor", "1.3.0"), ("major", "2.0.0")]
)
def test_version_bumps(bump, expected):
    assert select_version("1.2.3", bump) == expected


def test_explicit_version():
    assert select_version("0.2.0", "patch", "1.0.0") == "1.0.0"


@pytest.mark.parametrize("version", ["0.1.0", "0.2.0"])
def test_version_must_increase(version):
    with pytest.raises(ValueError, match="greater"):
        select_version("0.2.0", "patch", version)


def test_unknown_bump():
    with pytest.raises(ValueError, match="Unknown"):
        select_version("0.2.0", "automatic")


def test_release_baseline_uses_all_pages_and_ignores_unpublished_versions():
    pages = [
        [{"tag_name": "v0.3.0", "draft": False, "prerelease": False}],
        [
            {"tag_name": "v0.4.0", "draft": False, "prerelease": False},
            {"tag_name": "v9.0.0", "draft": True, "prerelease": False},
            {"tag_name": "v8.0.0", "draft": False, "prerelease": True},
            {"tag_name": "legacy", "draft": False, "prerelease": False},
        ],
    ]
    assert release_baseline("0.2.0", pages) == "0.4.0"
    assert release_baseline("1.0.0", pages) == "1.0.0"
    assert release_baseline("0.2.0", []) == "0.2.0"


def write_file(root: Path, relative: str, content: str):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def repository(tmp_path):
    write_file(tmp_path, "pyproject.toml", "[tool.smarthass]\nintegration-ready = false\n")
    return tmp_path


def test_scaffold_is_not_integration_ready(repository):
    assert check_readiness(repository) is False
    with pytest.raises(ValueError, match="not enabled"):
        check_readiness(repository, require_integration=True)


def test_partial_import_does_not_silently_skip_validation(repository):
    write_file(repository, MANIFEST.as_posix(), "{}")
    with pytest.raises(ValueError, match="not enabled"):
        check_readiness(repository)


@pytest.fixture
def imported_repository(repository):
    write_file(repository, "pyproject.toml", "[tool.smarthass]\nintegration-ready = true\n")
    manifest = {
        "domain": "chore_tracker",
        "name": "SmartHass Chore Tracker",
        "documentation": "https://github.com/NateGr/sh_chore_tracker",
        "issue_tracker": "https://github.com/NateGr/sh_chore_tracker/issues",
        "codeowners": ["@NateGr"],
        "version": "0.2.0",
    }
    write_file(repository, MANIFEST.as_posix(), json.dumps(manifest))
    write_file(repository, "custom_components/chore_tracker/__init__.py", "")
    write_file(repository, "custom_components/chore_tracker/brand/icon.png", "test fixture")
    write_file(repository, "tests/test_config_flow.py", "")
    write_file(
        repository,
        "requirements_test.txt",
        "pytest-homeassistant-custom-component==0.0.0\n",
    )
    write_file(
        repository,
        "hacs.json",
        json.dumps(
            {
                "name": "SmartHass Chore Tracker",
                "content_in_root": False,
                "homeassistant": "2026.3.0",
            }
        ),
    )
    return repository


def test_import_readiness(imported_repository):
    assert check_readiness(imported_repository, require_integration=True)


@pytest.mark.parametrize(
    "relative",
    [
        "custom_components/chore_tracker/__init__.py",
        "custom_components/chore_tracker/brand/icon.png",
        "tests/test_config_flow.py",
    ],
)
def test_missing_import_assets(imported_repository, relative):
    (imported_repository / relative).unlink()
    with pytest.raises(ValueError):
        check_readiness(imported_repository)


@pytest.mark.parametrize(
    "field", ["domain", "name", "documentation", "issue_tracker", "codeowners"]
)
def test_wrong_manifest_metadata(imported_repository, field):
    manifest_path = imported_repository / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[field] = "wrong"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        check_readiness(imported_repository)


@pytest.mark.parametrize(
    "changes",
    [
        {"homeassistant": ""},
        {"zip_release": True},
        {"filename": "chore_tracker.zip"},
        {"name": "wrong"},
        {"content_in_root": True},
    ],
)
def test_wrong_hacs_metadata(imported_repository, changes):
    path = imported_repository / "hacs.json"
    hacs = json.loads(path.read_text(encoding="utf-8"))
    hacs.update(changes)
    path.write_text(json.dumps(hacs), encoding="utf-8")
    with pytest.raises(ValueError):
        check_readiness(imported_repository)


def test_missing_ha_test_dependency(imported_repository):
    write_file(imported_repository, "requirements_test.txt", "pytest==9.1.1\n")
    with pytest.raises(ValueError, match="Pin a verified"):
        check_readiness(imported_repository)


def test_readiness_requires_boolean(repository):
    write_file(repository, "pyproject.toml", '[tool.smarthass]\nintegration-ready = "yes"\n')
    with pytest.raises(ValueError, match="boolean"):
        check_readiness(repository)


def run_git(root, *arguments):
    return subprocess.check_output(["git", *arguments], cwd=root, text=True).strip()


@pytest.fixture
def git_repository(imported_repository):
    run_git(imported_repository, "init", "--initial-branch=main")
    run_git(imported_repository, "config", "user.name", "Release tests")
    run_git(imported_repository, "config", "user.email", "release-tests@example.invalid")
    run_git(imported_repository, "config", "commit.gpgsign", "false")
    run_git(imported_repository, "add", ".")
    run_git(imported_repository, "commit", "-m", "Imported integration")
    return imported_repository


def test_prepare_updates_only_version(git_repository):
    previous = json.loads((git_repository / MANIFEST).read_text(encoding="utf-8"))
    assert prepare(git_repository, [], "patch", "") == {"version": "0.2.1"}
    candidate = json.loads((git_repository / MANIFEST).read_text(encoding="utf-8"))
    verify_release_metadata(previous, candidate, "0.2.1")
    assert run_git(git_repository, "diff", "--name-only") == MANIFEST.as_posix()


def test_prepare_rejects_existing_tag(git_repository):
    run_git(git_repository, "tag", "v0.2.1")
    with pytest.raises(ValueError, match="already exists"):
        prepare(git_repository, [], "patch", "")


@pytest.fixture
def released_repository(git_repository):
    prepare(git_repository, [], "patch", "")
    run_git(git_repository, "add", MANIFEST.as_posix())
    run_git(git_repository, "commit", "-m", "Release v0.2.1\n\nSmartHass-Release: 0.2.1")
    run_git(git_repository, "tag", "-a", "v0.2.1", "-m", "Release v0.2.1")
    run_git(git_repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    return git_repository


def test_recovery_uses_immutable_release_commit(released_repository):
    expected = run_git(released_repository, "rev-parse", "HEAD")
    assert recover(released_repository, "0.2.1") == {"version": "0.2.1", "candidate": expected}
    assert recover(released_repository, "0.2.1")["candidate"] == expected


def test_recovery_rejects_unrecognized_commit(git_repository):
    run_git(git_repository, "tag", "-a", "v0.2.0", "-m", "Old release")
    run_git(git_repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    with pytest.raises(ValueError):
        recover(git_repository, "0.2.0")


def test_recovery_rejects_lightweight_tag(released_repository):
    run_git(released_repository, "tag", "-d", "v0.2.1")
    run_git(released_repository, "tag", "v0.2.1")
    with pytest.raises(ValueError, match="annotated"):
        recover(released_repository, "0.2.1")


def test_recovery_rejects_commit_outside_main(released_repository):
    run_git(released_repository, "update-ref", "refs/remotes/origin/main", "HEAD^")
    with pytest.raises(subprocess.CalledProcessError):
        recover(released_repository, "0.2.1")


@pytest.mark.parametrize(
    ("previous", "candidate", "version"),
    [
        ({"version": "0.2.0"}, {"version": "0.2.2"}, "0.2.1"),
        ({"version": "0.2.1"}, {"version": "0.2.1"}, "0.2.1"),
        ({"version": "0.2.0", "domain": "chore_tracker"}, {"version": "0.2.1"}, "0.2.1"),
    ],
)
def test_recovery_rejects_invalid_metadata(previous, candidate, version):
    with pytest.raises(ValueError):
        verify_release_metadata(previous, candidate, version)


@pytest.mark.parametrize("defect", ["message", "extra-file", "other-metadata"])
def test_recovery_rejects_invalid_release_commits(git_repository, defect):
    prepare(git_repository, [], "patch", "")
    if defect == "extra-file":
        write_file(git_repository, "README.md", "Unexpected release content")
        run_git(git_repository, "add", "README.md")
    if defect == "other-metadata":
        manifest_path = git_repository / MANIFEST
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["name"] = "Unexpected rename"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    run_git(git_repository, "add", MANIFEST.as_posix())
    message = "Unknown commit" if defect == "message" else "SmartHass-Release: 0.2.1"
    run_git(git_repository, "commit", "-m", message)
    run_git(git_repository, "tag", "-a", "v0.2.1", "-m", "Release v0.2.1")
    run_git(git_repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    with pytest.raises(ValueError):
        recover(git_repository, "0.2.1")


def test_cli_outputs_scaffold_status(repository, monkeypatch, capsys):
    output = repository / "outputs.txt"
    monkeypatch.setattr(release_module, "ROOT", repository)
    monkeypatch.setattr("sys.argv", ["release.py", "check"])
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    release_module.main()
    assert "Scaffold only" in capsys.readouterr().out
    assert output.read_text(encoding="utf-8") == "integration-ready=false\n"


@pytest.mark.parametrize(
    "arguments",
    [
        ["check", "--require-integration"],
        ["prepare"],
        ["recover", "--version", "malformed"],
    ],
)
def test_cli_errors_fail_closed(repository, monkeypatch, capsys, arguments):
    monkeypatch.setattr(release_module, "ROOT", repository)
    monkeypatch.setattr("sys.argv", ["release.py", *arguments])
    with pytest.raises(SystemExit) as error:
        release_module.main()
    assert error.value.code == 1
    assert "Release preflight failed" in capsys.readouterr().err


def test_cli_prepares_version(git_repository, monkeypatch, tmp_path_factory):
    releases_path = tmp_path_factory.mktemp("release-input") / "releases.json"
    releases_path.write_text("[]", encoding="utf-8")
    output = releases_path.parent / "outputs.txt"
    monkeypatch.setattr(release_module, "ROOT", git_repository)
    monkeypatch.setattr("sys.argv", ["release.py", "prepare", "--releases", str(releases_path)])
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    release_module.main()
    assert output.read_text(encoding="utf-8") == "version=0.2.1\n"


def test_cli_recovers_version(released_repository, monkeypatch, tmp_path_factory):
    output = tmp_path_factory.mktemp("recovery-output") / "outputs.txt"
    monkeypatch.setattr(release_module, "ROOT", released_repository)
    monkeypatch.setattr("sys.argv", ["release.py", "recover", "--version", "0.2.1"])
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    release_module.main()
    assert "version=0.2.1\n" in output.read_text(encoding="utf-8")
    assert "candidate=" in output.read_text(encoding="utf-8")


@pytest.fixture
def remote_repository(git_repository, tmp_path_factory):
    remote = tmp_path_factory.mktemp("remote") / "repository.git"
    run_git(remote.parent, "init", "--bare", "--initial-branch=main", str(remote))
    run_git(git_repository, "remote", "add", "origin", str(remote))
    run_git(git_repository, "push", "-u", "origin", "main")
    return remote


def create_release_commit(root):
    prepare(root, [], "patch", "")
    run_git(root, "add", MANIFEST.as_posix())
    run_git(root, "commit", "-m", "Release v0.2.1\n\nSmartHass-Release: 0.2.1")
    run_git(root, "tag", "-a", "v0.2.1", "-m", "Release v0.2.1")
    return run_git(root, "rev-parse", "HEAD")


def atomic_push(root):
    run_git(root, "push", "--atomic", "origin", "HEAD:refs/heads/main", "refs/tags/v0.2.1")


def test_atomic_push_publishes_matching_refs(git_repository, remote_repository):
    candidate = create_release_commit(git_repository)
    atomic_push(git_repository)
    assert run_git(remote_repository, "rev-parse", "refs/heads/main") == candidate
    assert run_git(remote_repository, "rev-parse", "refs/tags/v0.2.1^{commit}") == candidate
    assert recover(git_repository, "0.2.1")["candidate"] == candidate


def test_atomic_push_does_not_push_tag_when_main_advances(
    git_repository, remote_repository, tmp_path_factory
):
    competitor = tmp_path_factory.mktemp("competitor") / "checkout"
    run_git(competitor.parent, "clone", str(remote_repository), str(competitor))
    run_git(competitor, "config", "user.name", "Concurrent merge")
    run_git(competitor, "config", "user.email", "merge@example.invalid")
    write_file(competitor, "README.md", "Concurrent PR merge")
    run_git(competitor, "add", "README.md")
    run_git(competitor, "-c", "commit.gpgsign=false", "commit", "-m", "Merge another PR")
    run_git(competitor, "push", "origin", "main")
    remote_main = run_git(remote_repository, "rev-parse", "refs/heads/main")
    create_release_commit(git_repository)
    with pytest.raises(subprocess.CalledProcessError):
        atomic_push(git_repository)
    assert run_git(remote_repository, "rev-parse", "refs/heads/main") == remote_main
    assert run_git(git_repository, "ls-remote", "origin", "refs/tags/v0.2.1") == ""


def test_atomic_push_does_not_push_main_when_tag_conflicts(git_repository, remote_repository):
    remote_main = run_git(remote_repository, "rev-parse", "refs/heads/main")
    run_git(remote_repository, "tag", "v0.2.1", remote_main)
    create_release_commit(git_repository)
    with pytest.raises(subprocess.CalledProcessError):
        atomic_push(git_repository)
    assert run_git(remote_repository, "rev-parse", "refs/heads/main") == remote_main
    assert run_git(remote_repository, "rev-parse", "refs/tags/v0.2.1^{commit}") == remote_main
