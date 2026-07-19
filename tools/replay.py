"""Session replay: inspect the append-only SQLite event log offline.

Usage (from the repo root):

    python tools/replay.py list
    python tools/replay.py show ses_1234abcd
    python tools/replay.py show ses_1234abcd --json
    python tools/replay.py show ses_1234abcd --speed 2.0   # paced playback

Reads the same database the app writes (``data/gesturegpt.db`` by default,
``DATA_DIR`` env respected) and never modifies it — safe to run against a
live backend. Useful for debugging gesture→intent fusion after the fact and
for reproducing demo sessions deterministically.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Make the backend importable when run as `python tools/replay.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.config import get_config  # noqa: E402
from backend.storage.repo import Repository  # noqa: E402


def _fmt_ts(ts: float | None) -> str:
    if ts is None:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _fmt_event(event: dict, t0: float) -> str:
    """One timeline row: +offset  KIND      details."""
    offset = f"+{event['ts'] - t0:7.2f}s"
    kind = event["kind"]
    if kind == "gesture":
        detail = f"{event['primitive']}  (conf {event['confidence']:.2f})"
    elif kind == "intent":
        detail = (
            f"{event['target']}.{event['attribute']} = {event['value']!r}"
            f"  (conf {event['confidence']:.2f})"
        )
    elif kind == "scene":
        n_objects = len(event["graph"].get("objects", []))
        detail = (
            f"revision {event['revision']}  completeness {event['completeness']:.2f}"
            f"  ({n_objects} objects)"
        )
    else:  # generation
        detail = (
            f"{event['image_id']} via {event['backend']}  {event['latency_ms']}ms"
            f"  prompt: {event['prompt'][:70]}"
        )
    return f"{offset}  {kind.upper():<10}  {detail}"


def cmd_list(repo: Repository) -> int:
    sessions = repo.list_sessions()
    if not sessions:
        print("no sessions recorded")
        return 0
    header = f"{'session':<14} {'started':<20} {'ended':<20} {'gest':>5} {'int':>5} {'scene':>5} {'gen':>4}"
    print(header)
    print("-" * len(header))
    for s in sessions:
        print(
            f"{s['id']:<14} {_fmt_ts(s['started_at']):<20} {_fmt_ts(s['ended_at']):<20} "
            f"{s['gestures']:>5} {s['intents']:>5} {s['snapshots']:>5} {s['generations']:>4}"
        )
    return 0


def cmd_show(repo: Repository, session_id: str, as_json: bool, speed: float) -> int:
    timeline = repo.session_timeline(session_id)
    if not timeline:
        print(f"no events for session {session_id!r} (does it exist? try: replay.py list)")
        return 1
    if as_json:
        print(json.dumps(timeline, indent=2))
        return 0
    t0 = timeline[0]["ts"]
    print(f"session {session_id} — {len(timeline)} events, starting {_fmt_ts(t0)}")
    prev_ts = t0
    for event in timeline:
        if speed > 0:
            time.sleep((event["ts"] - prev_ts) / speed)
            prev_ts = event["ts"]
        print(_fmt_event(event, t0))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="replay.py", description="Replay recorded GestureGPT sessions from the event log."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="database directory (default: the app's configured data_dir)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="list recorded sessions with event counts")
    show = sub.add_parser("show", help="print one session's merged event timeline")
    show.add_argument("session_id")
    show.add_argument("--json", action="store_true", help="machine-readable output")
    show.add_argument(
        "--speed",
        type=float,
        default=0.0,
        help="replay pacing multiplier (0 = instant, 1 = real time, 2 = double speed)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data_dir = args.data_dir or get_config().data_dir
    repo = Repository(data_dir)
    if args.command == "list":
        return cmd_list(repo)
    return cmd_show(repo, args.session_id, args.json, args.speed)


if __name__ == "__main__":
    raise SystemExit(main())
