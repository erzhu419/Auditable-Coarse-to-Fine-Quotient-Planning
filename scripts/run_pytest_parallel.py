#!/usr/bin/env python3
"""Run pytest modules concurrently without an external xdist dependency.

The repository's expensive fixtures are module-local.  One subprocess per
test module preserves each fixture's single-build semantics while allowing
independent historical Gates to run in parallel.  By default, immutable
content-ID properties are memoized within each subprocess; ``--fresh-ids``
disables that exact test-only optimization for a release Gate.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time


SUMMARY_ITEM_PATTERN = re.compile(
    r"(?P<count>\d+) "
    r"(?P<kind>passed|failed|skipped|error|errors|xfailed|xpassed)"
)
SUMMARY_LINE_PATTERN = re.compile(r"\bin \d+(?:\.\d+)?s(?: \(.+\))?$")
ID_CACHE_PATTERN = re.compile(
    r"acfqp_exact_content_id_memoization_v1: "
    r"(?P<status>fresh \(.+\)|"
    r"(?P<properties>\d+) properties, "
    r"(?P<hits>\d+) exact hits, "
    r"(?P<misses>\d+) first evaluations)"
)
TIMING_CACHE_RELATIVE_PATH = Path(
    ".pytest_cache/acfqp_parallel_module_timings_v1.json"
)
PARALLEL_TEMP_ROOT_VARIABLE = "ACFQP_PARALLEL_TEMP_ROOT"


@dataclass(frozen=True)
class ModuleResult:
    path: Path
    returncode: int
    duration_seconds: float
    output: str
    counts: tuple[tuple[str, int], ...]
    id_cache_summary: str | None


def _discover(paths: tuple[str, ...], root: Path) -> tuple[Path, ...]:
    selected: set[Path] = set()
    inputs = paths or ("tests",)
    for raw_path in inputs:
        candidate = (root / raw_path).resolve()
        if candidate.is_dir():
            selected.update(candidate.rglob("test_*.py"))
        elif candidate.is_file() and candidate.name.startswith("test_"):
            selected.add(candidate)
        else:
            raise SystemExit(f"not a pytest module or directory: {raw_path}")
    return tuple(sorted(selected))


def _parse_counts(output: str) -> tuple[tuple[str, int], ...]:
    for line in reversed(output.splitlines()):
        if not SUMMARY_LINE_PATTERN.search(line):
            continue
        totals: dict[str, int] = {}
        for match in SUMMARY_ITEM_PATTERN.finditer(line):
            kind = match.group("kind")
            totals[kind] = totals.get(kind, 0) + int(
                match.group("count")
            )
        if totals:
            return tuple(sorted(totals.items()))
    return ()


def _parse_id_cache_summary(output: str) -> str | None:
    match = ID_CACHE_PATTERN.search(output)
    if match is None:
        return None
    status = match.group("status")
    if status.startswith("fresh "):
        return "fresh IDs"
    return (
        f"{int(match.group('hits')):,} ID hits/"
        f"{int(match.group('misses')):,} first"
    )


def _read_timing_cache(root: Path) -> dict[str, float]:
    path = root / TIMING_CACHE_RELATIVE_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    if type(payload) is not dict:
        return {}
    timings: dict[str, float] = {}
    for key, value in payload.items():
        if (
            type(key) is str
            and type(value) in (int, float)
            and value >= 0
        ):
            timings[key] = float(value)
    return timings


def _write_timing_cache(
    root: Path, timings: dict[str, float]
) -> None:
    path = root / TIMING_CACHE_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(timings, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _run_module(
    path: Path,
    *,
    root: Path,
    temporary_root: Path,
    python: str,
    pytest_args: tuple[str, ...],
    fresh_ids: bool,
) -> ModuleResult:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    module_temporary_directory = tempfile.mkdtemp(
        prefix=f"{path.stem}-",
        dir=temporary_root,
    )
    environment["TMPDIR"] = module_temporary_directory
    environment["TEMP"] = module_temporary_directory
    environment["TMP"] = module_temporary_directory
    started = time.monotonic()
    try:
        completed = subprocess.run(
            (
                python,
                "-m",
                "pytest",
                "-q",
                "-s",
                "-p",
                "no:cacheprovider",
                *(
                    ()
                    if fresh_ids
                    else ("-p", "tests.acfqp_exact_id_cache_v1")
                ),
                *pytest_args,
                str(path.relative_to(root)),
            ),
            cwd=root,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    finally:
        shutil.rmtree(module_temporary_directory, ignore_errors=True)
    duration = time.monotonic() - started
    return ModuleResult(
        path,
        completed.returncode,
        duration,
        completed.stdout,
        _parse_counts(completed.stdout),
        _parse_id_cache_summary(completed.stdout),
    )


def _parallel_temporary_root(root: Path) -> Path:
    """Resolve one explicit private base or a repository-local default."""

    configured = os.environ.get(PARALLEL_TEMP_ROOT_VARIABLE)
    candidate = (
        Path(configured)
        if configured is not None
        else root / ".tmp" / "parallel-pytest"
    )
    if not candidate.is_absolute() or candidate.is_symlink():
        raise SystemExit("parallel pytest temp root must be absolute and unlinked")
    candidate.mkdir(parents=True, exist_ok=True)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise SystemExit("parallel pytest temp root cannot be resolved") from error
    if resolved != candidate:
        raise SystemExit("parallel pytest temp root changed under resolution")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths",
        nargs="*",
        help="test modules or directories; defaults to tests/",
    )
    parser.add_argument(
        "-j",
        "--workers",
        type=int,
        default=4,
        help="concurrent pytest module processes (default: 4)",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used by every worker",
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="additional pytest argument; may be repeated",
    )
    parser.add_argument(
        "--no-timing-cache",
        action="store_true",
        help="do not read or update historical module timings",
    )
    parser.add_argument(
        "--fresh-ids",
        action="store_true",
        help=(
            "recompute every content ID access; use for the formal fresh "
            "release Gate"
        ),
    )
    parser.add_argument(
        "--shard-count",
        type=int,
        default=1,
        help="number of deterministic module shards (default: 1)",
    )
    parser.add_argument(
        "--shard-index",
        type=int,
        default=0,
        help="zero-based shard selected by this process (default: 0)",
    )
    args = parser.parse_args(argv)
    if args.workers <= 0:
        parser.error("--workers must be positive")
    if args.shard_count <= 0:
        parser.error("--shard-count must be positive")
    if not 0 <= args.shard_index < args.shard_count:
        parser.error("--shard-index must be in [0, shard-count)")

    root = Path(__file__).resolve().parents[1]
    temporary_root = _parallel_temporary_root(root)
    modules = _discover(tuple(args.paths), root)
    if not modules:
        parser.error("no test modules discovered")
    timing_cache = (
        {}
        if args.no_timing_cache
        else _read_timing_cache(root)
    )
    predicted_seconds = {
        path: timing_cache.get(
            str(path.relative_to(root)),
            path.stat().st_size / 1000,
        )
        for path in modules
    }
    ordered_modules = sorted(
        modules,
        key=lambda path: (-predicted_seconds[path], str(path)),
    )
    shards: list[list[Path]] = [
        [] for _ in range(args.shard_count)
    ]
    shard_loads = [0.0] * args.shard_count
    for module in ordered_modules:
        target = min(
            range(args.shard_count),
            key=lambda index: (shard_loads[index], index),
        )
        shards[target].append(module)
        shard_loads[target] += predicted_seconds[module]
    modules = tuple(shards[args.shard_index])
    if not modules:
        parser.error("selected shard contains no test modules")

    print(
        f"parallel pytest: {len(modules)} modules, "
        f"{args.workers} workers, shard "
        f"{args.shard_index + 1}/{args.shard_count}",
        flush=True,
    )
    started = time.monotonic()
    results: list[ModuleResult] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                _run_module,
                path,
                root=root,
                temporary_root=temporary_root,
                python=args.python,
                pytest_args=tuple(args.pytest_arg),
                fresh_ids=args.fresh_ids,
            ): path
            for path in modules
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            label = "PASS" if result.returncode == 0 else "FAIL"
            count_text = ", ".join(
                f"{value} {kind}" for kind, value in result.counts
            )
            print(
                f"[{label}] {result.path.relative_to(root)} "
                f"{result.duration_seconds:.1f}s"
                + (f" ({count_text})" if count_text else "")
                + (
                    f" [{result.id_cache_summary}]"
                    if result.id_cache_summary
                    else ""
                ),
                flush=True,
            )
            if result.returncode != 0:
                print(result.output, flush=True)

    totals: dict[str, int] = {}
    for result in results:
        timing_cache[str(result.path.relative_to(root))] = (
            result.duration_seconds
        )
        for kind, count in result.counts:
            totals[kind] = totals.get(kind, 0) + count
    if not args.no_timing_cache:
        _write_timing_cache(root, timing_cache)
    failed_modules = tuple(
        sorted(
            result.path.relative_to(root)
            for result in results
            if result.returncode != 0
        )
    )
    elapsed = time.monotonic() - started
    summary = ", ".join(
        f"{count} {kind}" for kind, count in sorted(totals.items())
    )
    print(
        f"completed in {elapsed:.1f}s"
        + (f": {summary}" if summary else ""),
        flush=True,
    )
    if failed_modules:
        print(
            "failed modules: "
            + ", ".join(str(path) for path in failed_modules),
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
