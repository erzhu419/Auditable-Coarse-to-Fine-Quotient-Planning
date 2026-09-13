"""Frozen V40: reconstruct V39, compile LFE, and diagnose value bias."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from acfqp.science import rate_distortion_2048_v39 as target
from acfqp.science.rate_distortion_compiled_v40 import compile_operator
from acfqp.science.rate_distortion_diagnosis_v40 import diagnose_roundtrip
from acfqp.science.controlled_predictive_2048_v1 import PUBLIC_DEVELOPMENT_BOARDS

BETAS = (6., 7., 8., 9., 10.)
AUTHOR_COMMIT = "0d3b6f7e1cd63f8df8056bd35a0c82934390cefd"


def json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=json_default) + "\n")


def converge(backup, initial):
    u = initial.copy()
    for iteration in range(1, 20001):
        next_u = backup(u)
        if np.max(np.abs(next_u - u)) <= 1e-12:
            return next_u, iteration, float(np.max(np.abs(backup(next_u) - next_u)))
        u = next_u
    raise RuntimeError("Frozen fixed-point iteration limit exceeded")


def policy_record(adapter, q, optimum):
    policy = target.greedy_legal_policy(adapter, q)
    result = target.evaluate_original_policy(adapter, policy)
    predicted = q.reshape(adapter.legal_mask.shape)[np.arange(adapter.mdp.num_states), policy]
    return {
        "policy": policy, "root_value": result["mean_root_value"],
        "root_regret": optimum - result["mean_root_value"],
        "predicted_root_value": float(np.mean(predicted[list(adapter.root_states)])),
        "mean_tabular_value": result["mean_tabular_state_value"],
        "terminal_predicted_value": float(predicted[adapter.terminal_state]),
    }


def compare_actions(adapter, left_q, right_q):
    left = target.greedy_legal_policy(adapter, left_q)
    right = target.greedy_legal_policy(adapter, right_q)
    states = np.flatnonzero(left != right)
    result = {"disagreeing_states": states.tolist(), "root_value_difference": 0., "max_state_value_difference": 0.}
    if states.size:
        a = target.evaluate_original_policy(adapter, left)
        b = target.evaluate_original_policy(adapter, right)
        result.update(
            root_value_difference=b["mean_root_value"] - a["mean_root_value"],
            max_state_value_difference=float(np.max(np.abs(np.asarray(b["tabular_state_values"]) - a["tabular_state_values"]))),
            left_selected_action_gaps=[float(left_q.reshape(adapter.legal_mask.shape)[s, left[s]] - left_q.reshape(adapter.legal_mask.shape)[s, right[s]]) for s in states],
        )
    return result


def benchmark(author_backup, compiled_backup, u):
    times = {"author": [], "compiled": []}
    functions = {"author": author_backup, "compiled": compiled_backup}
    for block in range(5):
        for name in (("author", "compiled") if block % 2 == 0 else ("compiled", "author")):
            before = perf_counter()
            for _ in range(200):
                functions[name](u)
            times[name].append((perf_counter() - before) / 200)
    return {name: {"seconds_per_backup_blocks": values, "median_seconds": float(np.median(values)), "minimum_seconds": min(values), "maximum_seconds": max(values)} for name, values in times.items()}


def run_condition(adapter, distance, original, scale, modules, prior, output, stem):
    ab, pl, ad = modules
    scaled = replace(adapter.mdp, rewards=adapter.mdp.rewards * scale)
    fitted, embedded, compiled, info = {}, {}, {}, {}
    costs = {"fitting_seconds": 0., "compiling_seconds": 0.}
    for beta in BETAS:
        before = perf_counter()
        fitted[beta] = target.fit_author_abstraction(adapter, distance * scale, ab, beta=beta, num_abstract=adapter.num_valid_pairs)
        embedded[beta] = target.embed_author_abstraction(adapter, fitted[beta], ab)
        legal = fitted[beta]
        info[beta] = {
            "information_bits": ab.mutual_information(adapter.uniform_legal_prior, legal.encoder),
            "abstraction_error": ab.compute_abstraction_error(adapter.uniform_legal_prior, legal.encoder, legal.decoder, distance * scale, mode="average"),
        }
        costs["fitting_seconds"] += perf_counter() - before
        before = perf_counter()
        compiled[beta] = compile_operator(adapter, legal, reward_scale=scale)
        info[beta]["compiling_seconds"] = perf_counter() - before
        costs["compiling_seconds"] += info[beta]["compiling_seconds"]
    ladder = ad.AdaptiveLadder([embedded[b] for b in BETAS], [info[b]["abstraction_error"] for b in BETAS])
    n = adapter.num_valid_pairs
    max_sweeps = ceil(100 * n / min(a.num_abstract for a in ladder.abstractions))
    before = perf_counter()
    run = ad.run_adaptive_controller(scaled, ladder, original["legal_q"][adapter.rect_to_valid_pair] * scale, 100 * n, max_sweeps, range(max_sweeps + 1))
    costs["trajectory_reconstruction_seconds"] = perf_counter() - before
    final = run.final_snapshot
    abstraction = embedded[final.beta]
    operator = compiled[final.beta]
    optimum = original["mean_root_value"]
    frozen = policy_record(adapter, final.grounded_q / scale, optimum)
    expected = prior["adaptive_final"]
    reproduction = {
        "policy_exact": np.array_equal(frozen["policy"], expected["policy"]),
        "beta_exact": final.beta == expected["beta"],
        "active_codes_exact": abstraction.num_abstract == expected["active_codes"],
        "root_value_error": abs(frozen["root_value"] - expected["root_value"]),
        "root_prediction_error": abs(frozen["predicted_root_value"] - expected["predicted_root_value_original_units"]),
        "information_error": abs(info[final.beta]["information_bits"] - expected["information_bits"]),
        "snapshot_units_exact": final.bellman_backup_units == expected["author_backup_units"],
        "paid_units_exact": run.final_state.cumulative_backup_units == prior["adaptive_run_paid_author_backup_units"],
    }
    if not all(v if key.endswith("exact") else v <= 1e-12 for key, v in reproduction.items()):
        raise ValueError(f"V39 endpoint reconstruction differs: {reproduction}")
    max_error, max_ground_error, action_events = 0., 0., []
    before = perf_counter()
    for snapshot in run.snapshots:
        e = embedded[snapshot.beta]
        actual = pl.abstract_state_action_bellman_update(scaled, e, snapshot.abstract_q)
        candidate = compiled[snapshot.beta].backup(snapshot.abstract_q)
        max_error = max(max_error, float(np.max(np.abs(actual - candidate))))
        left_q = ab.ground_state_action_abstract_q(e, actual)
        right_q = ab.ground_state_action_abstract_q(e, candidate)
        max_ground_error = max(max_ground_error, float(np.max(np.abs(left_q - right_q))))
        comparison = compare_actions(adapter, left_q, right_q)
        if comparison["disagreeing_states"]:
            action_events.append({"sweep": snapshot.sweep, "beta": snapshot.beta, **comparison})
    if max_error > 1e-12 or max_ground_error > 1e-12:
        raise ValueError("Compiled operator exceeds frozen numerical tolerance")
    costs["snapshot_comparison_seconds"] = perf_counter() - before
    layers = np.asarray([adapter.closure.model.layers[s] if s is not None else -1 for s in adapter.state_to_source])

    def diagnose(u):
        result = diagnose_roundtrip(adapter.mdp.transitions, adapter.mdp.rewards, adapter.mdp.gamma,
                                    abstraction.encoder, abstraction.decoder, u / scale,
                                    adapter.legal_mask, layers, adapter.root_states)
        result["remaining_abstract_iteration_error_bound"] = result["abstract_residual_inf"] / (1. - adapter.mdp.gamma)
        # Changing units before a dot product can perturb a numerical tie.
        # Preserve that distinction instead of silently attributing a different
        # policy's exact return to the frozen author readout.
        reference_q = ab.ground_state_action_abstract_q(abstraction, u) / scale
        diagnostic_q = abstraction.encoder @ (u / scale)
        result["comparison_to_author_readout"] = compare_actions(adapter, reference_q, diagnostic_q)
        return result

    before = perf_counter()
    author_backup = lambda u: pl.abstract_state_action_bellman_update(scaled, abstraction, u)
    author_u, author_steps, author_residual = converge(author_backup, final.abstract_q)
    compiled_u, compiled_steps, compiled_residual = converge(operator.backup, final.abstract_q)
    fixed_q = ab.ground_state_action_abstract_q(abstraction, author_u) / scale
    compiled_q = ab.ground_state_action_abstract_q(abstraction, compiled_u) / scale
    fixed_error = float(np.max(np.abs(author_u - compiled_u)))
    if fixed_error > 1e-10:
        raise ValueError("Compiled fixed points differ beyond contraction-amplified roundoff")
    frozen_diagnosis = diagnose(final.abstract_q)
    fixed_diagnosis = diagnose(author_u)

    def clamped_backup(u):
        q = ab.ground_state_action_abstract_q(abstraction, u).reshape(adapter.legal_mask.shape)
        q[adapter.terminal_state] = 0.
        return pl.bellman_update(scaled, q.reshape(-1))[abstraction.decoder]

    clamped_u, clamped_steps, clamped_residual = converge(clamped_backup, final.abstract_q)
    clamped_q = ab.ground_state_action_abstract_q(abstraction, clamped_u).reshape(adapter.legal_mask.shape)
    clamped_q[adapter.terminal_state] = 0.
    clamped_q = clamped_q.reshape(-1) / scale
    costs["fixed_points_and_diagnosis_seconds"] = perf_counter() - before
    # Save reconstructed E/u as well as the array-only runtime; no original P is
    # needed by the fresh-process witness replay.
    operator.save(output / f"{stem}.operator.npz")
    np.savez(output / f"{stem}.snapshot.npz", encoder=abstraction.encoder, decoder=abstraction.decoder,
             u=final.abstract_q, fixed_u=author_u, clamped_u=clamped_u,
             expected_backup=author_backup(final.abstract_q), legal_mask=adapter.legal_mask,
             state_layers=layers, root_states=adapter.root_states)
    before = perf_counter()
    timing = benchmark(author_backup, operator.backup, final.abstract_q)
    costs["benchmark_seconds"] = perf_counter() - before
    inventory = operator.inventory()
    inventory["legal_policy_readout_array_bytes"] = fitted[final.beta].encoder.nbytes + adapter.valid_pair_indices.nbytes
    inventory["operator_plus_legal_readout_array_bytes"] = inventory["array_bytes"] + inventory["legal_policy_readout_array_bytes"]
    inventory["full_ground_model_array_bytes"] = adapter.mdp.transitions.nbytes + adapter.mdp.rewards.nbytes
    inventory["state_board_lookup_included"] = False
    return {
        "reward_and_distance_scale": scale, "reconstruction": reproduction,
        "costs": costs, "final_beta_compile_seconds": info[final.beta]["compiling_seconds"],
        "operator_inventory": inventory, "timing": timing,
        "snapshot_comparison": {"snapshots": len(run.snapshots), "action_gap_units": "scaled rewards",
                                "max_operator_error": max_error,
                                "max_grounded_error": max_ground_error, "action_disagreement_events": action_events},
        "frozen_snapshot": frozen, "frozen_diagnosis": frozen_diagnosis,
        "converged": {**policy_record(adapter, fixed_q, optimum), "steps": author_steps,
                      "scaled_abstract_residual": author_residual, "diagnosis": fixed_diagnosis},
        "compiled_fixed_point": {"steps": compiled_steps, "scaled_abstract_residual": compiled_residual,
                                 "max_scaled_u_difference": fixed_error, **compare_actions(adapter, fixed_q, compiled_q)},
        "terminal_clamp": {**policy_record(adapter, clamped_q, optimum), "steps": clamped_steps,
                           "scaled_abstract_residual": clamped_residual,
                           "comparison_to_original_converged": compare_actions(adapter, fixed_q, clamped_q)},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=ROOT.parent / "acfqp-rate-distortion-reference-v39-source")
    parser.add_argument("--prior-dir", type=Path, default=ROOT / "reports/rate_distortion_v39/transfer")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/rate_distortion_v40")
    args = parser.parse_args()
    source = args.source_dir.resolve()
    if subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() != AUTHOR_COMMIT:
        raise ValueError("Unexpected author revision")
    if subprocess.check_output(["git", "-C", str(source), "diff", "HEAD", "--"], text=True):
        raise ValueError("Author source has changed")
    if args.output_dir.exists():
        raise FileExistsError("Keep existing V40 attempts; select a fresh output directory")
    args.output_dir.mkdir(parents=True)
    sys.path.insert(0, str(source / "code"))
    from core import abstraction as ab, planning as pl, adaptive as ad
    from exp4_sysadmin import sysadmin_mdp as metric
    started = perf_counter()
    records = []
    for case in PUBLIC_DEVELOPMENT_BOARDS:
        print(f"[V40] reconstructing {case}", flush=True)
        before = perf_counter()
        adapter = target.build_exact_2048_adapter(case, ab)
        construction_seconds = perf_counter() - before
        before = perf_counter()
        distance = target.author_fixed_point_distortion(adapter, metric)
        metric_seconds = perf_counter() - before
        before = perf_counter()
        original = target.exact_original_solution(adapter)
        exact_solve_seconds = perf_counter() - before
        prior = json.loads((args.prior_dir / f"{case}.json").read_text())
        record = {"case": case, "closure_counts": adapter.closure.counts,
                  "costs": {"construction_seconds": construction_seconds, "metric_seconds": metric_seconds,
                            "exact_solve_seconds": exact_solve_seconds},
                  "exact_root_value": original["mean_root_value"], "conditions": {}}
        for condition in ("raw", "doorkey_metric_units"):
            scale = prior["conditions"][condition]["reward_and_distance_scale"]
            result = run_condition(adapter, distance, original, scale, (ab, pl, ad), prior["conditions"][condition], args.output_dir, f"{case}.{condition}")
            record["conditions"][condition] = result
            print(json.dumps({"case": case, "condition": condition, "snapshot_bias": result["frozen_diagnosis"]["root_bias"],
                              "fixed_bias": result["converged"]["diagnosis"]["root_bias"], "clamped": result["terminal_clamp"]["predicted_root_value"]}, default=json_default), flush=True)
        write_json(args.output_dir / f"{case}.json", record)
        records.append(record)
    child = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/replay_rate_distortion_compiled_v40.py"), str(args.output_dir.resolve())], check=True, capture_output=True, text=True)
    independent = json.loads(child.stdout)
    write_json(args.output_dir / "summary.json", {
        "author_commit": AUTHOR_COMMIT, "new_sampled_environment_draws": 0,
        "reconstruction_is_new_independent_evidence": False, "conditions": 6,
        "fresh_process_replay": independent, "wall_seconds": perf_counter() - started,
        "case_files": [f"{record['case']}.json" for record in records],
        "scope": "Six existing public H2 exact-model conditions; same frozen E/g/beta for intervention. Compiled backups use no original P; reconstruction, reference runs and diagnosis retain it.",
    })
    print("[V40] complete", flush=True)


if __name__ == "__main__":
    main()
