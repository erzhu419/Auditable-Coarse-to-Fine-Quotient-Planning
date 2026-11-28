"""Read the published SISC records or reproduce the frozen runners in a new directory."""

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys


PACKAGE = Path(__file__).resolve().parents[1]
PROJECT = PACKAGE.parent
CLEAN_ARCHIVE = "m233_clean_isolation_replication.json"
CLEAN_SHA256 = "73101638ce563ca9f33049e2ffef50c16218ad097785c031ecd19d3d99a7e678"


def check_campaign(path, published):
    sys.path.insert(0, str(PROJECT))
    from quotient_phase2.m233_sisc_subportal_quadtree import (
        PAIR2_SISC_ARMS, _build_expected_m233_roster, _strict_json_loads,
        compute_phase2_manifest, verify_event_roster_and_inequalities,
    )

    raw = path.read_bytes()
    if published and hashlib.sha256(raw).hexdigest() != CLEAN_SHA256:
        raise ValueError("Published clean campaign digest mismatch")
    data = _strict_json_loads(raw.decode("utf-8"))
    if compute_phase2_manifest() != data["phase2_manifest"]:
        raise ValueError("Phase-I or Phase-II source manifest mismatch")
    records = data["per_map_records"]
    events = [event for rows in records.values() for row in rows
              for key in ("pair_events", "cache_events", "events") for event in row.get(key, [])]
    expected, scheduled = _build_expected_m233_roster()
    audit = verify_event_roster_and_inequalities(events, expected, scheduled, eps_budget=0.25, slack=0.0)
    if not audit["ALL_INDEPENDENT_GATES_PASSED"]:
        raise ValueError(f"Zero-slack roster verification failed: {audit}")
    # The older roster verifier keys task identity by block; these two M2.3.3
    # blocks also share each query and reference across their five methods.
    for row in records["replay_47cubed"]:
        identities = {}
        for event in row["cache_events"] + row["pair_events"]:
            key = event["task_index"]
            identity = (event["start_state"], event["goal_signature_sha1"], event["reference_value"])
            if identities.setdefault(key, identity) != identity:
                raise ValueError(f"Cache/pair task mismatch for seed {row['seed']}, task {key}")
    geometric_tasks = {(e["seed"], e["grid_n"], e["operator_epoch"], e["start_state"], e["goal_signature_sha1"])
                       for e in events}
    print(f"Sources and roster verified. {len(events)} events, {len(geometric_tasks)} distinct geometric tasks, "
          f"{len(scheduled)} policy checks.")
    for block, rows in records.items():
        if "pair_arms" not in rows[0]:
            continue
        timed = [row for row in rows if row["singlelu_reference_total_ms"] is not None]
        print(f"{block}: {len(timed)}/{len(rows)} maps with a fresh SingleLU reference timing")
        for row in timed:
            pou = row["pair_arms"][PAIR2_SISC_ARMS[0]]["total_ms"]
            print(f"  seed {row['seed']}: PoU {pou:.1f} ms, SingleLU {row['singlelu_reference_total_ms']:.1f} ms")


def reproduce(mode, destination):
    # The historical drivers resolve input and output relative to their own module.
    # An exclusive directory keeps concurrent runs and the published evidence independent.
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    for package in (PROJECT / "green_response", PACKAGE):
        directory = destination / package.name
        directory.mkdir()
        for source in sorted(package.glob("*.py")):
            shutil.copy2(source, directory / source.name)
    directory = destination / PACKAGE.name
    for source in sorted(PACKAGE.glob("*.json")):
        if source.name not in (CLEAN_ARCHIVE, "m232_release_verification_report.json"):
            shutil.copy2(source, directory / source.name)
    driver = ["m233_sisc_subportal_quadtree.py", "--clean-isolation-replication"]
    if mode == "verify-m232":
        driver = ["verify_m232_release.py"]
    print(f"Running in {directory}", flush=True)
    subprocess.run([sys.executable, "-B", "-u", *driver], cwd=directory, check=True)
    if mode == "replicate":
        check_campaign(directory / CLEAN_ARCHIVE, published=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("check", help="verify the published roster and print matched reference timings")
    for command in ("replicate", "verify-m232"):
        modes.add_parser(command).add_argument("destination", type=Path, help="new run directory")
    args = parser.parse_args()
    if args.mode == "check":
        check_campaign(PACKAGE / CLEAN_ARCHIVE, published=True)
    else:
        if args.destination.exists():
            parser.error(f"Run directory already exists: {args.destination}")
        reproduce(args.mode, args.destination)
