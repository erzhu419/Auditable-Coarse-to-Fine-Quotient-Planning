"""Frozen exact-2048 transfer of the reproduced author's soft-pair mechanism."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from math import ceil
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from acfqp.science import rate_distortion_2048_v39 as target
from acfqp.science.controlled_predictive_2048_v1 import PUBLIC_DEVELOPMENT_BOARDS

FIXED_BETAS = (6., 7., 7.5, 8., 10.)
ADAPTIVE_BETAS = (6., 7., 8., 9., 10.)
AUTHOR_COMMIT = "0d3b6f7e1cd63f8df8056bd35a0c82934390cefd"


def run_condition(adapter, distance, original, scale, modules):
    ab, pl, ad = modules
    scaled = replace(adapter.mdp, rewards=adapter.mdp.rewards * scale)
    scaled_distance = distance * scale
    n = adapter.num_valid_pairs
    baseline_q = original["legal_q"][adapter.rect_to_valid_pair] * scale
    fitted, embedded, info = {}, {}, {}
    started = perf_counter()
    for beta in sorted(set(FIXED_BETAS + ADAPTIVE_BETAS)):
        fit_started = perf_counter()
        legal = target.fit_author_abstraction(adapter, scaled_distance, ab, beta=beta, num_abstract=n)
        fitted[beta] = legal
        embedded[beta] = target.embed_author_abstraction(adapter, legal, ab)
        information = ab.mutual_information(adapter.uniform_legal_prior, legal.encoder)
        info[beta] = {
            "beta": beta,
            "active_codes": legal.num_abstract,
            "active_code_fraction": legal.num_abstract / n,
            "information_bits": information,
            "information_fraction": 2 ** information / n,
            "abstraction_error": ab.compute_abstraction_error(adapter.uniform_legal_prior, legal.encoder, legal.decoder, scaled_distance, mode="average"),
            "fit_seconds": perf_counter() - fit_started,
            "legal_encoder_bytes": legal.encoder.nbytes,
            "rectangular_encoder_bytes": embedded[beta].encoder.nbytes,
        }
    fitting_seconds = perf_counter() - started
    evaluated = {}
    evaluation_seconds = 0.

    def evaluate(grounded, beta):
        nonlocal evaluation_seconds
        policy = target.greedy_legal_policy(adapter, grounded)
        key = tuple(int(a) for a in policy)
        if key not in evaluated:
            before = perf_counter()
            result = target.evaluate_original_policy(adapter, policy)
            # A different primitive transition/terminal interpretation would
            # invalidate transfer; compare with the completed tabular equation.
            state_values = np.asarray(result["tabular_state_values"])
            states = np.arange(adapter.mdp.num_states)
            backed = adapter.mdp.rewards[states, policy] + adapter.mdp.gamma * adapter.mdp.transitions[states, policy] @ state_values
            residual = float(np.max(np.abs(backed - state_values)))
            if residual > 1e-12:
                raise ValueError("Original policy values and rectangular model disagree")
            evaluated[key] = (result, residual)
            evaluation_seconds += perf_counter() - before
        result, residual = evaluated[key]
        root_value = float(result["mean_root_value"])
        optimum = float(original["mean_root_value"])
        regret = optimum - root_value
        row = {
            **info[beta],
            "root_value": root_value,
            "root_regret": regret,
            "root_return_fraction": root_value / optimum if optimum > 0 else None,
            "root_exact_optimal": abs(regret) <= 1e-10,
            "root_at_least_99pct": root_value >= .99 * optimum - 1e-10,
            "mean_tabular_value": float(result["mean_tabular_state_value"]),
            "mean_tabular_regret": float(original["mean_tabular_state_value"] - result["mean_tabular_state_value"]),
            "root_actions": [target.ACTION_LABELS[int(policy[s])] for s in adapter.root_states],
            "original_policy_bellman_residual": residual,
            "policy": list(key),
            "predicted_root_value_original_units": float(np.mean(np.max(np.where(adapter.legal_mask, grounded.reshape(adapter.legal_mask.shape), -np.inf), axis=1)[list(adapter.root_states)])) / scale,
        }
        row["joint_exact_root_and_information_reduction"] = row["root_exact_optimal"] and row["information_fraction"] < 1 - 1e-10
        row["joint_99pct_root_and_information_reduction"] = row["root_at_least_99pct"] and row["information_fraction"] < 1 - 1e-10
        return row

    fixed = []
    for beta in FIXED_BETAS:
        abstraction = embedded[beta]
        sweeps = ceil(100 * n / abstraction.num_abstract)
        q = np.zeros(abstraction.num_abstract)
        before = perf_counter()
        for _ in range(sweeps):
            q = pl.abstract_state_action_bellman_update(scaled, abstraction, q)
        grounded = ab.ground_state_action_abstract_q(abstraction, q)
        elapsed = perf_counter() - before
        fixed.append({**evaluate(grounded, beta), "planning_seconds": elapsed, "sweeps": sweeps, "author_backup_units": sweeps * abstraction.num_abstract})
    ladder = ad.AdaptiveLadder([embedded[b] for b in ADAPTIVE_BETAS], [info[b]["abstraction_error"] for b in ADAPTIVE_BETAS])
    max_sweeps = ceil(100 * n / min(a.num_abstract for a in ladder.abstractions))
    before = perf_counter()
    run = ad.run_adaptive_controller(scaled, ladder, baseline_q, 100 * n, max_sweeps, range(max_sweeps + 1))
    planning_seconds = perf_counter() - before
    first_optimal = None
    trace = []
    for snapshot in run.snapshots:
        evaluated_row = evaluate(snapshot.grounded_q, snapshot.beta)
        compact = {key: evaluated_row[key] for key in (
            "beta", "root_value", "root_regret", "root_exact_optimal", "information_fraction", "active_codes", "root_actions"
        )}
        compact.update(sweep=snapshot.sweep, author_backup_units=snapshot.bellman_backup_units)
        trace.append(compact)
        if first_optimal is None and evaluated_row["root_exact_optimal"]:
            first_optimal = compact
    final = run.final_snapshot
    return {
        "reward_and_distance_scale": scale,
        "fitting_seconds": fitting_seconds,
        "fixed": fixed,
        "adaptive_final": {**evaluate(final.grounded_q, final.beta), "planning_seconds": planning_seconds, "author_backup_units": final.bellman_backup_units},
        "adaptive_run_paid_author_backup_units": run.final_state.cumulative_backup_units,
        "adaptive_first_optimal": first_optimal,
        "adaptive_switch_betas": run.final_state.switch_betas,
        "adaptive_switch_updates": run.final_state.switch_updates,
        "adaptive_trace": trace,
        "unique_policies_evaluated": len(evaluated),
        "independent_evaluation_seconds": evaluation_seconds,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=Path("/home/erzhu419/mine_code/acfqp-rate-distortion-reference-v39-source"))
    parser.add_argument("--results-root", type=Path, default=Path("reports/rate_distortion_v39"))
    args = parser.parse_args()
    source = args.source_dir.resolve()
    if subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() != AUTHOR_COMMIT:
        raise ValueError("Unexpected author revision")
    if subprocess.check_output(["git", "-C", str(source), "diff", "HEAD", "--"], text=True):
        raise ValueError("Author source must remain unchanged")
    replication = json.loads((args.results_root / "replication_analysis.json").read_text())
    prior = replication["readme_independent_diagnostic"]
    if not prior["adaptive_optimal_checkpoint_exists"] or not prior["paper_joint_information_rounding_match"]:
        raise ValueError("Original benchmark mechanism has not been reproduced")
    output_dir = args.results_root / "transfer"
    output_dir.mkdir(exist_ok=True)
    if any(output_dir.glob("*.json")):
        raise FileExistsError("Retain existing transfer results; do not overwrite a completed/partial attempt")
    sys.path.insert(0, str(source / "code"))
    from core import abstraction as ab, planning as pl, adaptive as ad
    from exp4_sysadmin import sysadmin_mdp as metric
    all_cases = []
    for case in PUBLIC_DEVELOPMENT_BOARDS:
        started = perf_counter()
        print(f"[transfer] building {case}", flush=True)
        adapter = target.build_exact_2048_adapter(case, ab)
        construction_seconds = perf_counter() - started
        before = perf_counter()
        original = target.exact_original_solution(adapter)
        original_solve_seconds = perf_counter() - before
        before = perf_counter()
        author_values = pl.solve_optimal_values(adapter.mdp)
        author_ground_solve_seconds = perf_counter() - before
        if not np.allclose(author_values, original["tabular_state_values"], atol=1e-12, rtol=0):
            raise ValueError("Ground solver and original legal finite-horizon DP disagree")
        simple_baselines = {}
        for name, values in (("lexicographic", np.zeros(adapter.mdp.num_state_action_pairs)), ("immediate_reward_greedy", adapter.mdp.rewards.reshape(-1))):
            policy = target.greedy_legal_policy(adapter, values)
            evaluated = target.evaluate_original_policy(adapter, policy)
            simple_baselines[name] = {
                "root_value": evaluated["mean_root_value"],
                "mean_tabular_value": evaluated["mean_tabular_state_value"],
                "root_actions": [target.ACTION_LABELS[int(policy[s])] for s in adapter.root_states],
            }
        before = perf_counter()
        distance = target.author_fixed_point_distortion(adapter, metric, verbose=True)
        metric_seconds = perf_counter() - before
        maximum = float(np.max(distance))
        record = {
            "case": case, "inventory": adapter.inventory(), "closure_counts": adapter.closure.counts,
            "construction_seconds": construction_seconds, "metric_seconds": metric_seconds,
            "metric_maximum": maximum, "metric_state_tolerance": 1e-6,
            "original_solve_seconds": original_solve_seconds, "author_ground_solve_seconds": author_ground_solve_seconds,
            "exact_root_value": original["mean_root_value"], "exact_mean_tabular_value": original["mean_tabular_state_value"],
            "full_mdp_array_bytes": adapter.mdp.transitions.nbytes + adapter.mdp.rewards.nbytes,
            "legal_mask_and_mapping_array_bytes": adapter.legal_mask.nbytes + adapter.valid_pair_indices.nbytes + adapter.rect_to_valid_pair.nbytes,
            "simple_baselines": simple_baselines,
            "conditions": {},
        }
        for condition, scale in (("raw", 1.), ("doorkey_metric_units", 1.95 / maximum if maximum > 0 else 1.)):
            print(f"[transfer] {case} / {condition}, scale={scale:g}", flush=True)
            result = run_condition(adapter, distance, original, scale, (ab, pl, ad))
            record["conditions"][condition] = result
            print(json.dumps({"case": case, "condition": condition, "adaptive": {key: result["adaptive_final"][key] for key in ("root_value", "root_regret", "information_fraction", "active_codes")}}), flush=True)
        record["wall_seconds"] = perf_counter() - started
        (output_dir / f"{case}.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
        all_cases.append(record)
    compact = []
    for case in all_cases:
        for name, result in case["conditions"].items():
            compact.append({"case": case["case"], "units": name, "exact_root_value": case["exact_root_value"], **result["adaptive_final"]})
    (output_dir / "summary.json").write_text(json.dumps({
        "author_commit": AUTHOR_COMMIT, "cases": compact, "new_sampled_environment_draws": 0,
        "exact_enumeration_charged_in_case_files": True,
        "scope": "Exact known H2 models on all three public development boards; fixed legal-action completion; no learned transition estimation or cross-query reuse claim.",
        "cost_scope": "Full MDP remains available to author Q backups; information reduction and author units do not imply total cost or storage reduction.",
    }, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
