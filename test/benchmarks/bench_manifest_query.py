"""Manual NFR-C timing tool: query a 1,000-manifest dataset three times.

Requirement: NFR-C. Proposed acceptance (PENDING TEAM APPROVAL, not asserted
here): on a fixed CI runner with Python 3.13, after generating 1,000 synthetic
manifests, three *independent* CLI processes each finish in <= 2.0 s. Each
process's elapsed time includes interpreter/CLI startup, directory scan,
schema validation and output capture. This tool only produces evidence; the
real performance conclusion belongs to CI after the C implementation exists.

It is intentionally NOT collected by pytest (``test/benchmarks`` is outside the
configured ``testpaths`` root set used for the acceptance suite). Run it by hand:

    python test/benchmarks/bench_manifest_query.py \
        --results-dir /tmp/manifest_bench --count 1000

Processes are spawned with ``subprocess`` so startup cost is measured, not a
warm in-process call. Exit codes and expected-match counts are checked per run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = REPO_ROOT / "test" / "fixtures" / "run_manifests" / "gen_dataset.py"
PROPOSED_BUDGET_SECONDS = 2.0
RUNS = 3


def _query_argv(results_dir: Path, ticker: str) -> list[str]:
    """The CLI query command under measurement (contract under test).

    Reserves the command shape proposed for C. It does not exist yet; a
    measured run against the un-implemented product is expected to fail and is
    itself useful baseline evidence, not an NFR-C pass.
    """

    return [
        sys.executable,
        "-m",
        "cli.main",
        "manifest",
        "query",
        "--results-dir",
        str(results_dir),
        "--ticker",
        ticker,
        "--json",
    ]


def _expected_matches(results_dir: Path, ticker: str) -> int:
    count = 0
    for manifest in results_dir.rglob("run_manifest.json"):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("ticker") == ticker:
            count += 1
    return count


def _count_manifests(results_dir: Path) -> int:
    return sum(1 for _ in results_dir.rglob("run_manifest.json"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--ticker", default="AAPL")
    args = parser.parse_args(argv)

    if not any(args.results_dir.rglob("run_manifest.json")):
        subprocess.run(
            [sys.executable, str(GENERATOR), "--out", str(args.results_dir),
             "--count", str(args.count)],
            check=True,
            cwd=REPO_ROOT,
        )

    # The timing budget is defined for exactly --count manifests; refuse to
    # measure a differently sized dataset rather than report a misleading time.
    actual = _count_manifests(args.results_dir)
    if actual != args.count:
        print(
            f"ERROR: expected {args.count} manifests in {args.results_dir}, found {actual}. "
            "Regenerate the dataset or pass the matching --count before timing.",
            file=sys.stderr,
        )
        return 2

    expected = _expected_matches(args.results_dir, args.ticker)
    timings: list[float] = []
    all_ok = True
    for run in range(1, RUNS + 1):
        start = time.perf_counter()
        proc = subprocess.run(
            _query_argv(args.results_dir, args.ticker),
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
        match_ok = _reported_match_count(proc.stdout) == expected
        ok = proc.returncode == 0 and match_ok
        all_ok = all_ok and ok
        print(
            f"run {run}: exit={proc.returncode} elapsed={elapsed:.3f}s "
            f"expected_matches={expected} match_ok={match_ok} ok={ok}"
        )
        if proc.returncode != 0:
            print(f"  stderr: {proc.stderr.strip()[:300]}")

    slowest = max(timings)
    within = all(t <= PROPOSED_BUDGET_SECONDS for t in timings)
    print(
        f"slowest={slowest:.3f}s proposed_budget={PROPOSED_BUDGET_SECONDS}s "
        f"within_proposed={within} all_runs_ok={all_ok}"
    )
    print("NOTE: <=2.0s per run is a PROPOSED threshold pending team approval.")
    return 0 if (all_ok and within) else 1


def _reported_match_count(stdout: str) -> int:
    """Read the match count a JSON query prints, or -1 if unparseable."""
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return -1
    if isinstance(payload, dict):
        matches = payload.get("matches")
        if isinstance(matches, list):
            return len(matches)
        if isinstance(payload.get("count"), int):
            return payload["count"]
    if isinstance(payload, list):
        return len(payload)
    return -1


if __name__ == "__main__":
    raise SystemExit(main())
