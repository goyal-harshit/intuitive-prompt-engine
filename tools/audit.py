"""Repository hygiene and verification CLI.

Usage (from the repo root):

    python tools/audit.py scan               # report junk/temp files, never deletes
    python tools/audit.py clean              # dry-run of what clean would delete
    python tools/audit.py clean --apply      # delete caches/coverage/temp artifacts
    python tools/audit.py clean --apply --all  # also delete rebuildable build output
    python tools/audit.py verify             # run every CI quality gate locally
    python tools/audit.py verify --repeat 3  # repeat pytest 3x to surface flaky tests

Safety model:
- ``clean`` never touches git-tracked files; tracked junk is reported for manual
  ``git rm`` + .gitignore fixes instead.
- Suspiciously named files (temp.py, final_copy.js, ...) are report-only: a human
  decides, the tool never deletes them.
- ``verify`` mirrors .github/workflows/ci.yml so a green local run predicts green CI.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Directories whose contents are never scanned. ``data`` holds runtime session
#: databases and generated images; ``.venv``/``node_modules`` are package trees.
EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "data"}

#: Directory names that are pure tool caches — always safe to delete.
CACHE_DIRS = {"__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"}

#: Coverage-report directories (pytest-cov html, vitest) — always safe to delete.
COVERAGE_DIRS = {"htmlcov", "coverage"}

#: Rebuildable build output — deleted only with ``clean --all``.
BUILD_DIRS = {"dist", "build"}

CACHE_FILE_GLOBS = ("*.pyc", "*.pyo")
COVERAGE_FILE_GLOBS = (".coverage", ".coverage.*", "coverage.xml")
TEMP_FILE_GLOBS = (
    "*.tmp", "*.temp", "*.bak", "*.swp", "*.swo", "*~",
    "*.orig", "*.rej", ".DS_Store", "Thumbs.db", "desktop.ini",
)

#: Filenames that suggest a forgotten scratch file. Word-boundary anchored so
#: legitimate names like ``template.py`` or ``newsfeed.ts`` do not match.
SUSPECT_NAME_RE = re.compile(
    r"(?i)(?:^|[\s_\-.])(?:temp|tmp|scratch|junk|untitled|wip|backup|old|copy|(?:final)+|new|test\d+)(?:$|[\s_\-.(])"
)
#: Legitimate names the suspect heuristic would otherwise flag.
SUSPECT_ALLOWLIST = {"template.py", "tmpfile.py"}


class Category(Enum):
    CACHE = "cache"
    COVERAGE = "coverage"
    TEMP = "temp"
    BUILD = "build"
    SUSPECT = "suspect"


#: Categories ``clean`` deletes by default; BUILD requires --all; SUSPECT never.
DEFAULT_CLEAN = {Category.CACHE, Category.COVERAGE, Category.TEMP}


@dataclass
class Finding:
    path: Path
    category: Category
    size: int
    tracked: bool


@dataclass
class ScanReport:
    findings: list[Finding] = field(default_factory=list)

    def by_category(self, category: Category) -> list[Finding]:
        return [f for f in self.findings if f.category is category]

    @property
    def deletable(self) -> list[Finding]:
        return [f for f in self.findings if f.category is not Category.SUSPECT and not f.tracked]


def matches_any(name: str, globs: tuple[str, ...]) -> bool:
    from fnmatch import fnmatch

    return any(fnmatch(name, g) for g in globs)


def is_suspect_name(name: str) -> bool:
    return name not in SUSPECT_ALLOWLIST and bool(SUSPECT_NAME_RE.search(Path(name).stem))


def classify(path: Path) -> Category | None:
    """Classify a single file or directory name; None means keep."""
    name = path.name
    if path.is_dir():
        if name in CACHE_DIRS:
            return Category.CACHE
        if name in COVERAGE_DIRS:
            return Category.COVERAGE
        if name in BUILD_DIRS:
            return Category.BUILD
        return None
    if matches_any(name, CACHE_FILE_GLOBS):
        return Category.CACHE
    if matches_any(name, COVERAGE_FILE_GLOBS):
        return Category.COVERAGE
    if matches_any(name, TEMP_FILE_GLOBS):
        return Category.TEMP
    if is_suspect_name(name):
        return Category.SUSPECT
    return None


def git_tracked_files(root: Path) -> set[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    return {root / p for p in out.decode().split("\0") if p}


def dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def scan(root: Path) -> ScanReport:
    """Walk the repo, classifying junk. Excluded dirs are skipped entirely."""
    tracked = git_tracked_files(root)
    report = ScanReport()

    def visit(directory: Path) -> None:
        for entry in sorted(directory.iterdir()):
            if entry.name in EXCLUDED_DIRS:
                continue
            category = classify(entry)
            if category is not None:
                is_tracked = entry in tracked or (
                    entry.is_dir() and any(t.is_relative_to(entry) for t in tracked)
                )
                size = dir_size(entry) if entry.is_dir() else entry.stat().st_size
                report.findings.append(Finding(entry, category, size, is_tracked))
                if entry.is_dir():
                    continue  # classified whole; don't descend
            elif entry.is_dir():
                visit(entry)

    visit(root)
    return report


def clean(root: Path, apply: bool, include_build: bool) -> int:
    """Delete deletable findings. Returns count removed (or would-remove)."""
    categories = DEFAULT_CLEAN | ({Category.BUILD} if include_build else set())
    targets = [f for f in scan(root).deletable if f.category in categories]
    verb = "Deleting" if apply else "Would delete"
    total = 0
    removed = 0
    failures: list[tuple[Path, OSError]] = []
    for f in targets:
        print(f"  {verb}: {f.path.relative_to(root)}  ({format_size(f.size)})")
        if not apply:
            total += f.size
            continue
        try:
            if f.path.is_dir():
                shutil.rmtree(f.path)
            else:
                f.path.unlink(missing_ok=True)
        except OSError as exc:  # locked file, permissions — skip and keep going
            failures.append((f.path, exc))
        else:
            total += f.size
            removed += 1
    action = "Freed" if apply else "Would free"
    count = removed if apply else len(targets)
    print(f"\n{action} {format_size(total)} across {count} item(s).")
    for failed_path, err in failures:
        print(f"  WARNING: could not delete {failed_path.relative_to(root)}: {err.strerror or err}")
    if not apply and targets:
        print("Dry-run only. Re-run with --apply to delete.")
    return removed if apply else len(targets)


def format_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{n} B"


def print_report(report: ScanReport, root: Path) -> None:
    if not report.findings:
        print("Clean: no junk, temp, or suspect files found.")
        return
    labels = {
        Category.CACHE: "Tool caches (safe to delete)",
        Category.COVERAGE: "Coverage artifacts (safe to delete)",
        Category.TEMP: "Temp/editor leftovers (safe to delete)",
        Category.BUILD: "Rebuildable build output (clean --all)",
        Category.SUSPECT: "Suspicious names (review manually — never auto-deleted)",
    }
    for category in Category:
        findings = report.by_category(category)
        if not findings:
            continue
        print(f"\n{labels[category]}:")
        for f in findings:
            flag = "  [TRACKED IN GIT — fix .gitignore, then git rm]" if f.tracked else ""
            print(f"  {f.path.relative_to(root)}  ({format_size(f.size)}){flag}")
    deletable = report.deletable
    total = sum(f.size for f in deletable)
    print(f"\n{len(deletable)} deletable item(s), {format_size(total)} reclaimable.")


# --------------------------------------------------------------------------- verify


@dataclass
class Step:
    name: str
    cmd: list[str]
    cwd: Path


@dataclass
class StepResult:
    step: Step
    ok: bool
    seconds: float


def build_steps(repeat: int, skip_frontend: bool) -> list[Step]:
    """Mirror .github/workflows/ci.yml. Pytest repeats to surface flaky tests."""
    py = sys.executable
    steps = [
        Step("ruff (lint)", [py, "-m", "ruff", "check", "."], REPO_ROOT),
        Step("mypy (types)", [py, "-m", "mypy"], REPO_ROOT),
    ]
    for i in range(repeat):
        suffix = f" [run {i + 1}/{repeat}]" if repeat > 1 else ""
        steps.append(Step(f"pytest + coverage{suffix}", [py, "-m", "pytest"], REPO_ROOT))
    frontend = REPO_ROOT / "frontend"
    if not skip_frontend and (frontend / "node_modules").is_dir():
        npm = shutil.which("npm")
        if npm:
            steps += [
                Step("eslint", [npm, "run", "lint"], frontend),
                Step("prettier --check", [npm, "run", "format:check"], frontend),
                Step("tsc + vite build", [npm, "run", "build"], frontend),
                Step("vitest", [npm, "test"], frontend),
            ]
    return steps


def run_step(step: Step) -> StepResult:
    start = time.monotonic()
    proc = subprocess.run(step.cmd, cwd=step.cwd)
    return StepResult(step, proc.returncode == 0, time.monotonic() - start)


def verify(repeat: int, skip_frontend: bool) -> int:
    steps = build_steps(repeat, skip_frontend)
    results: list[StepResult] = []
    for step in steps:
        print(f"\n=== {step.name} ===")
        results.append(run_step(step))

    print("\n=== hygiene scan ===")
    report = scan(REPO_ROOT)
    hygiene_ok = not any(f.tracked for f in report.findings)
    print_report(report, REPO_ROOT)

    print("\n" + "=" * 46)
    print("Verification summary")
    print("=" * 46)
    for r in results:
        mark = "PASS" if r.ok else "FAIL"
        print(f"  [{mark}] {r.step.name}  ({r.seconds:.1f}s)")
    print(f"  [{'PASS' if hygiene_ok else 'FAIL'}] hygiene (no tracked junk)")
    failed = [r for r in results if not r.ok]
    if failed or not hygiene_ok:
        print(f"\n{len(failed)} gate(s) failed.")
        return 1
    print("\nAll gates green.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="audit", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scan", help="report junk/temp/suspect files (read-only)")

    p_clean = sub.add_parser("clean", help="delete caches, coverage and temp artifacts")
    p_clean.add_argument("--apply", action="store_true", help="actually delete (default: dry-run)")
    p_clean.add_argument("--all", action="store_true", help="also delete rebuildable build output")

    p_verify = sub.add_parser("verify", help="run all CI quality gates locally")
    p_verify.add_argument("--repeat", type=int, default=1, help="pytest repetitions (flake check)")
    p_verify.add_argument("--skip-frontend", action="store_true", help="backend gates only")

    args = parser.parse_args(argv)
    if args.command == "scan":
        print_report(scan(REPO_ROOT), REPO_ROOT)
        return 0
    if args.command == "clean":
        clean(REPO_ROOT, apply=args.apply, include_build=args.all)
        return 0
    return verify(repeat=max(1, args.repeat), skip_frontend=args.skip_frontend)


if __name__ == "__main__":
    raise SystemExit(main())
