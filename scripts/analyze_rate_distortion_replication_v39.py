"""Assess the two retained author DoorKey entrypoints, without refitting."""
from __future__ import annotations

import argparse
from collections import deque
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

AUTHOR_COMMIT = "0d3b6f7e1cd63f8df8056bd35a0c82934390cefd"


def independent_doorkey_optimum(mdp):
    """Shortest paths give exact values for this deterministic terminal reward MDP."""
    p, r = mdp.transitions, mdp.rewards
    successor = np.argmax(p, axis=2)
    terminal = mdp.state_labels.index(("terminal",))
    if not np.allclose(p.sum(axis=2), 1.0) or not np.allclose(p.max(axis=2), 1.0):
        raise ValueError("DoorKey shortest-path evaluation requires deterministic rows")
    if not np.all((r == 0) | ((r == 1) & (successor == terminal))):
        raise ValueError("DoorKey reward convention changed")
    reverse = [[] for _ in range(mdp.num_states)]
    for s in range(mdp.num_states):
        for t in successor[s]:
            reverse[int(t)].append(s)
    distances = {terminal: 0}
    queue = deque([terminal])
    while queue:
        t = queue.popleft()
        for s in reverse[t]:
            if s not in distances:
                distances[s] = distances[t] + 1
                queue.append(s)
    values = np.zeros(mdp.num_states)
    for s, distance in distances.items():
        if s != terminal:
            values[s] = mdp.gamma ** (distance - 1)
    backed = np.max(r + mdp.gamma * values[successor], axis=1)
    residual = float(np.max(np.abs(backed - values)))
    if residual > 1e-12:
        raise ValueError("Independent shortest-path values violate the Bellman equation")
    return float(values.mean()), residual


def assess(path, optimum, *, independent_fit):
    summary = json.loads((path / "summary.json").read_text())
    with (path / "traces.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    adaptive = [r for r in rows if r["method_type"] == "adaptive"]
    base = [r for r in rows if r["method_type"] == "base"]
    if abs(float(base[-1]["policy_return"]) - optimum) > 1e-12:
        raise ValueError("Author base return disagrees with independent shortest-path optimum")
    first = next((r for r in adaptive if abs(float(r["policy_return"]) - optimum) <= 1e-8), None)
    checkpoint = None
    if first is not None:
        checkpoint = {k: float(first[k]) for k in (
            "sweep", "beta", "active_abstracts", "bellman_backup_units", "policy_return"
        )}
        # Only independent deterministic fits have identical inputs at the same
        # beta in the fixed and adaptive families. Never use this for warm starts.
        if independent_fit:
            family = next(r for r in summary["fixed_family_table"] if r["beta"] == checkpoint["beta"])
            pairs = summary["config"]["num_state_action_pairs"]
            checkpoint.update({
                "information_fraction": 2 ** family["mutual_information"] / pairs,
                "state_information_fraction": 2 ** family["bar_state_information"] / summary["config"]["num_states"],
                "action_information_fraction": 2 ** family["bar_conditional_action_information"] / summary["config"]["num_actions"],
                "information_provenance": "same beta, identical deterministic independent fit inputs in both families",
            })
    fixed = []
    for family in summary["fixed_family_table"]:
        matching = [r for r in rows if r["method_type"] == "fixed" and float(r["beta"]) == family["beta"]]
        fixed.append({
            "beta": family["beta"],
            "final_return": float(matching[-1]["policy_return"]),
            "active_codes": family["effective_abstract_pairs"],
            "information_fraction": 2 ** family["mutual_information"] / summary["config"]["num_state_action_pairs"],
        })
    information_fraction = checkpoint.get("information_fraction") if checkpoint else None
    return {
        "source_directory": str(path),
        "config": summary["config"],
        "adaptive_final_return": float(adaptive[-1]["policy_return"]),
        "adaptive_final_return_fraction": float(adaptive[-1]["policy_return"]) / optimum,
        "adaptive_best_return": max(float(r["policy_return"]) for r in adaptive),
        "adaptive_optimal_checkpoint_exists": first is not None,
        "first_optimal_adaptive": checkpoint,
        "paper_joint_information_rounding_match": information_fraction is not None and 0.1325 <= information_fraction < 0.1335,
        "paper_state_component_rounding_match": checkpoint is not None and "state_information_fraction" in checkpoint and 0.3725 <= checkpoint["state_information_fraction"] < 0.3735,
        "paper_action_component_rounding_match": checkpoint is not None and "action_information_fraction" in checkpoint and 0.3565 <= checkpoint["action_information_fraction"] < 0.3575,
        "fixed_family": fixed,
        "trace_rows": len(rows),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=Path("/home/erzhu419/mine_code/acfqp-rate-distortion-reference-v39-source"))
    parser.add_argument("--results-root", type=Path, default=Path("reports/rate_distortion_v39"))
    args = parser.parse_args()
    commit = subprocess.check_output(["git", "-C", str(args.source_dir), "rev-parse", "HEAD"], text=True).strip()
    if commit != AUTHOR_COMMIT:
        raise ValueError("Unexpected author source revision")
    if subprocess.check_output(["git", "-C", str(args.source_dir), "diff", "HEAD", "--"], text=True):
        raise ValueError("Author tracked source was modified")
    sys.path.insert(0, str(args.source_dir / "code"))
    from exp3_doorkey.doorkey_mdp import build_doorkey_mdp
    mdp = build_doorkey_mdp(grid_size=5, gamma=0.95, goal_reward=1)
    optimum, residual = independent_doorkey_optimum(mdp)
    result = {
        "author_commit": commit,
        "independent_optimal_return": optimum,
        "independent_bellman_residual": residual,
        "primary_sequential": assess(args.results_root / "doorkey", optimum, independent_fit=False),
        "readme_independent_diagnostic": assess(args.results_root / "release_entrypoint/doorkey", optimum, independent_fit=True),
        "conclusion": "README entrypoint reproduces optimal return and joint information fraction; default sequential path does not. Information components differ from paper rounding.",
        "cost_boundary": "Author backup units omit full concrete backups and stage probes; wall times include fitting and evaluation, not isolated deployment timings.",
    }
    for arm, log_path in (("primary_sequential", args.results_root / "doorkey"), ("readme_independent_diagnostic", args.results_root / "release_entrypoint")):
        result[arm]["stderr_bytes"] = (log_path / "stderr.log").stat().st_size
        result[arm]["wall_time"] = (log_path / "wall-time.txt").read_text().strip()
    output = args.results_root / "replication_analysis.json"
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(output), "independent_optimum": optimum, "bellman_residual": residual, "conclusion": result["conclusion"]}))


if __name__ == "__main__":
    main()
