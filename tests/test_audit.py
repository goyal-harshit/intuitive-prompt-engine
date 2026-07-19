"""Hygiene tooling: classification, suspect-name heuristic, and clean safety."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import audit  # noqa: E402  (tools/audit.py)
from audit import Category, classify, format_size, is_suspect_name, scan  # noqa: E402


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("module.pyc", Category.CACHE),
        (".coverage", Category.COVERAGE),
        ("coverage.xml", Category.COVERAGE),
        ("notes.bak", Category.TEMP),
        ("file.swp", Category.TEMP),
        (".DS_Store", Category.TEMP),
        ("temp.py", Category.SUSPECT),
        ("final_copy.js", Category.SUSPECT),
        ("test2.py", Category.SUSPECT),
    ],
)
def test_classify_files(tmp_path, name, expected):
    f = tmp_path / name
    f.write_text("x")
    assert classify(f) is expected


@pytest.mark.parametrize("name", ["main.py", "template.py", "newsfeed.ts", "testing.md", "olden.py"])
def test_legitimate_names_not_flagged(tmp_path, name):
    f = tmp_path / name
    f.write_text("x")
    assert classify(f) is None


@pytest.mark.parametrize(
    ("name", "suspect"),
    [
        ("finalfinal.py", True),
        ("app copy.js", True),
        ("old_backup.sql", True),
        ("wip.md", True),
        ("template.py", False),  # 'temp' inside a word must not match
        ("attempt.py", False),
        ("newton.py", False),
        ("contest1.py", False),  # 'test\\d' must be word-anchored
    ],
)
def test_suspect_name_boundaries(name, suspect):
    assert is_suspect_name(name) is suspect


def test_cache_dirs_classified(tmp_path):
    d = tmp_path / "__pycache__"
    d.mkdir()
    assert classify(d) is Category.CACHE
    b = tmp_path / "dist"
    b.mkdir()
    assert classify(b) is Category.BUILD


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('ok')")
    cache = tmp_path / "src" / "__pycache__"
    cache.mkdir()
    (cache / "main.cpython-310.pyc").write_bytes(b"\x00")
    (tmp_path / ".coverage").write_bytes(b"\x00" * 10)
    (tmp_path / "temp.py").write_text("scratch")
    return tmp_path


def test_scan_finds_and_categorizes(tmp_path, monkeypatch):
    root = _make_repo(tmp_path)
    monkeypatch.setattr(audit, "git_tracked_files", lambda _root: set())
    report = scan(root)
    categories = {f.category for f in report.findings}
    assert categories == {Category.CACHE, Category.COVERAGE, Category.SUSPECT}
    # main.py untouched by the scan's deletable view
    assert all(f.path.name != "main.py" for f in report.findings)


def test_clean_dry_run_deletes_nothing(tmp_path, monkeypatch):
    root = _make_repo(tmp_path)
    monkeypatch.setattr(audit, "git_tracked_files", lambda _root: set())
    audit.clean(root, apply=False, include_build=False)
    assert (root / ".coverage").exists()
    assert (root / "src" / "__pycache__").exists()


def test_clean_apply_removes_junk_keeps_suspects(tmp_path, monkeypatch):
    root = _make_repo(tmp_path)
    monkeypatch.setattr(audit, "git_tracked_files", lambda _root: set())
    audit.clean(root, apply=True, include_build=False)
    assert not (root / ".coverage").exists()
    assert not (root / "src" / "__pycache__").exists()
    # Suspect files are report-only and source files are never touched.
    assert (root / "temp.py").exists()
    assert (root / "src" / "main.py").exists()


def test_clean_never_deletes_tracked_files(tmp_path, monkeypatch):
    root = _make_repo(tmp_path)
    tracked = {root / ".coverage"}
    monkeypatch.setattr(audit, "git_tracked_files", lambda _root: tracked)
    audit.clean(root, apply=True, include_build=False)
    assert (root / ".coverage").exists()  # tracked → protected
    assert not (root / "src" / "__pycache__").exists()  # untracked → removed


def test_excluded_dirs_not_scanned(tmp_path, monkeypatch):
    root = _make_repo(tmp_path)
    venv_cache = root / ".venv" / "__pycache__"
    venv_cache.mkdir(parents=True)
    monkeypatch.setattr(audit, "git_tracked_files", lambda _root: set())
    report = scan(root)
    assert all(".venv" not in f.path.parts for f in report.findings)


def test_format_size():
    assert format_size(512) == "512 B"
    assert format_size(2048) == "2.0 KB"
    assert format_size(5 * 1024 * 1024) == "5.0 MB"


def test_cli_scan_smoke(capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(audit, "REPO_ROOT", _make_repo(tmp_path))
    monkeypatch.setattr(audit, "git_tracked_files", lambda _root: set())
    assert audit.main(["scan"]) == 0
    out = capsys.readouterr().out
    assert ".coverage" in out and "temp.py" in out
