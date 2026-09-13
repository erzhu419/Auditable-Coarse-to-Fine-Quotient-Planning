"""Frozen V41 horizon-layered intervention, reusing retained V40 controls."""
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
from acfqp.science.rate_distortion_layered_v41 import fit_layered_abstraction, layer_inventory, stable_legal_policy
from acfqp.science.controlled_predictive_2048_v1 import PUBLIC_DEVELOPMENT_BOARDS

BETAS = (6., 7., 8., 9., 10.)
AUTHOR_COMMIT = "0d3b6f7e1cd63f8df8056bd35a0c82934390cefd"


def default_json(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, default=default_json, allow_nan=False) + "\n")


def solve(backup, count, scale):
    u = np.zeros(count)
    for step in range(1, 20001):
        next_u = backup(u)
        if np.max(np.abs(next_u - u)) / scale <= 1e-12:
            return next_u, step
        u = next_u
    raise RuntimeError("Fixed point did not converge within the frozen limit")


def evaluate_q(adapter, original, q, scale=1.):
    before = perf_counter()
    q = np.asarray(q) / scale
    policy = stable_legal_policy(adapter, q)
    predicted = q.reshape(adapter.legal_mask.shape)[np.arange(adapter.mdp.num_states), policy]
    readout_seconds = perf_counter() - before
    before = perf_counter()
    actual = target.evaluate_original_policy(adapter, policy)
    state_values = np.asarray(actual["tabular_state_values"])
    source_values = np.asarray(original["tabular_state_values"])
    selected = np.arange(adapter.mdp.num_states)
    residual = np.max(np.abs(state_values - adapter.mdp.rewards[selected, policy] - adapter.mdp.gamma * adapter.mdp.transitions[selected, policy] @ state_values))
    if residual > 1e-12:
        raise ValueError("Original finite evaluation disagrees with tabular policy equation")
    root_prediction = float(np.mean(predicted[list(adapter.root_states)]))
    return {
        "policy": policy, "root_value": actual["mean_root_value"],
        "root_regret": original["mean_root_value"] - actual["mean_root_value"],
        "predicted_root_value": root_prediction,
        "root_bias": root_prediction - actual["mean_root_value"],
        "relative_absolute_root_bias": abs(root_prediction - actual["mean_root_value"]) / max(abs(original["mean_root_value"]), 1e-12),
        "state_values": state_values, "predicted_state_values": predicted,
        "maximum_state_regret": float(np.max(source_values - state_values)),
        "maximum_absolute_state_bias": float(np.max(np.abs(predicted - state_values))),
        "legal_q_error_inf": float(np.max(np.abs(q[adapter.valid_pair_indices] - original["legal_q"]))),
        "terminal_prediction": float(predicted[adapter.terminal_state]),
        "readout_seconds": readout_seconds, "independent_evaluation_seconds": perf_counter() - before,
    }


def policy_difference(adapter, left, right):
    changed = np.flatnonzero(np.asarray(left["policy"]) != np.asarray(right["policy"]))
    return {"changed_states": changed, "root_value_change": right["root_value"] - left["root_value"],
            "maximum_state_value_change": float(np.max(np.abs(np.asarray(right["state_values"]) - left["state_values"])))}


def load_controls(adapter, original, prior, archive, stem, ab):
    scale = prior["reward_and_distance_scale"]
    with np.load(archive / f"{stem}.snapshot.npz", allow_pickle=False) as saved:
        e = saved["encoder"]
        decoder = saved["decoder"]
        u = saved["fixed_u"]
        clamped_u = saved["clamped_u"]
        frozen_u = saved["u"]
    # This object only restores the retained author grounding operation.
    restored = ab.StateActionAbstraction(beta=10., encoder=e, decoder=decoder,
                                        posterior=np.empty((0, 0)), full_encoder=e, full_decoder=decoder)
    flat_q = ab.ground_state_action_abstract_q(restored, u)
    clamped_q = ab.ground_state_action_abstract_q(restored, clamped_u).reshape(adapter.legal_mask.shape)
    clamped_q[adapter.terminal_state] = 0.
    frozen_q = ab.ground_state_action_abstract_q(restored, frozen_u)
    # Detect wrong retained inputs before making a new readout comparison.
    old = prior["converged"]
    strict_policy = target.greedy_legal_policy(adapter, flat_q / scale)
    if not np.array_equal(strict_policy, old["policy"]):
        raise ValueError("V40 saved endpoint does not reproduce its original policy")
    predicted = np.mean(np.max(np.where(adapter.legal_mask, (flat_q / scale).reshape(adapter.legal_mask.shape), -np.inf), axis=1)[list(adapter.root_states)])
    if abs(predicted - old["predicted_root_value"]) > 1e-12:
        raise ValueError("V40 saved endpoint prediction differs")
    controls = {"flat": evaluate_q(adapter, original, flat_q, scale),
                "clamp": evaluate_q(adapter, original, clamped_q.reshape(-1), scale),
                "flat_adaptive_snapshot": evaluate_q(adapter, original, frozen_q, scale)}
    for name, old_name in (("flat", "converged"), ("clamp", "terminal_clamp"), ("flat_adaptive_snapshot", "frozen_snapshot")):
        controls[name]["changes_from_v40_strict_argmax"] = {
            "changed_states": np.flatnonzero(np.asarray(controls[name]["policy"]) != prior[old_name]["policy"]),
            "root_value_change": controls[name]["root_value"] - prior[old_name]["root_value"],
        }
    controls["flat"]["v40_operator_plus_readout_and_u_bytes"] = prior["operator_inventory"]["operator_plus_legal_readout_array_bytes"] + u.nbytes
    return controls


def run_condition(adapter, original, distance, scale, modules, prior, output, stem):
    ab, pl, ad = modules
    mdp = replace(adapter.mdp, rewards=adapter.mdp.rewards * scale)
    controls = load_controls(adapter, original, prior, ROOT / "reports/rate_distortion_v40", stem, ab)
    fitted, embedded, operators, beta_rows = {}, {}, {}, {}
    for beta in BETAS:
        before = perf_counter()
        legal = fit_layered_abstraction(adapter, distance * scale, ab, beta=beta)
        fit_seconds = perf_counter() - before
        structural = layer_inventory(adapter, legal)
        # These invariants are also checked on every production fit, so a bad
        # mapping cannot masquerade as a scientific failure of the method.
        layers = np.asarray([adapter.closure.model.layers[s] if s is not None else -1 for s in adapter.state_to_source])
        pair_layers = layers[adapter.valid_pair_indices // adapter.mdp.num_actions]
        crossing = legal.encoder * (pair_layers[:, None] != pair_layers[legal.decoder][None, :])
        terminal = np.flatnonzero(pair_layers[legal.decoder] == -1)
        if np.max(np.abs(crossing)) != 0. or terminal.size != 1:
            raise ValueError("Layer or independent terminal-code invariant failed")
        before = perf_counter()
        e = target.embed_author_abstraction(adapter, legal, ab)
        embedding_seconds = perf_counter() - before
        before = perf_counter()
        operator = compile_operator(adapter, legal, reward_scale=scale)
        compile_seconds = perf_counter() - before
        backup = lambda u: pl.abstract_state_action_bellman_update(mdp, e, u)
        before = perf_counter()
        u, steps = solve(backup, legal.num_abstract, scale)
        solve_seconds = perf_counter() - before
        before = perf_counter()
        grounded = ab.ground_state_action_abstract_q(e, u)
        grounding_seconds = perf_counter() - before
        result = evaluate_q(adapter, original, grounded, scale)
        probe = np.arange(legal.num_abstract, dtype=float) * scale
        probe[terminal] = 0.
        one = backup(probe)
        two = backup(one)
        three = backup(two)
        residual = float(np.max(np.abs(backup(u) - u)) / scale)
        bound_error = float(np.max(np.abs(three - two)) / scale)
        if bound_error > 1e-12 or any(float(v[terminal[0]]) != 0. for v in (one, two, three, u)):
            raise ValueError("Layered H2 backup created a false temporal continuation")
        information = ab.mutual_information(adapter.uniform_legal_prior, legal.encoder)
        beta_rows[beta] = {
            **result, "beta": beta, "active_codes": legal.num_abstract,
            "information_bits": information, "information_fraction": 2 ** information / adapter.num_valid_pairs,
            "abstraction_error": ab.compute_abstraction_error(adapter.uniform_legal_prior, legal.encoder, legal.decoder, distance * scale, mode="average"),
            "fit_seconds": fit_seconds, "compile_seconds": compile_seconds,
            "embedding_seconds": embedding_seconds, "grounding_seconds": grounding_seconds,
            "solve_seconds": solve_seconds, "solve_updates": steps,
            "original_unit_abstract_residual": residual, "two_step_check_error": bound_error,
            "layers": structural,
        }
        fitted[beta], embedded[beta], operators[beta] = legal, e, operator
        if beta == 10.:
            operator.save(output / f"{stem}.operator.npz")
            np.savez(output / f"{stem}.readout.npz", legal_encoder=legal.encoder,
                     legal_pair_indices=adapter.valid_pair_indices, u=u)
            np.savez(output / f"{stem}.snapshot.npz", u=u, expected_backup=backup(u))
            inventory = operator.inventory()
            readout_bytes = legal.encoder.nbytes + adapter.valid_pair_indices.nbytes
            beta_rows[beta]["deployment"] = {
                **inventory, "legal_readout_array_bytes": readout_bytes,
                "u_array_bytes": u.nbytes,
                "complete_numeric_array_bytes": inventory["array_bytes"] + readout_bytes + u.nbytes,
                "operator_and_readout_archive_bytes": sum((output / f"{stem}.{kind}.npz").stat().st_size for kind in ("operator", "readout")),
                "diagnostic_witness_archive_bytes": (output / f"{stem}.snapshot.npz").stat().st_size,
                "fixed_policy_cache_array_bytes": result["policy"].nbytes,
                "state_board_lookup_included": False,
            }
    ladder = ad.AdaptiveLadder([embedded[b] for b in BETAS], [beta_rows[b]["abstraction_error"] for b in BETAS])
    n = adapter.num_valid_pairs
    maximum_sweeps = ceil(100 * n / min(a.num_abstract for a in ladder.abstractions))
    before = perf_counter()
    run = ad.run_adaptive_controller(mdp, ladder, original["legal_q"][adapter.rect_to_valid_pair] * scale,
                                     100 * n, maximum_sweeps, range(maximum_sweeps + 1))
    adaptive_seconds = perf_counter() - before
    before = perf_counter()
    events, trace = [], []
    max_update_error, max_ground_error = 0., 0.
    for snap in run.snapshots:
        e = embedded[snap.beta]
        source_u = pl.abstract_state_action_bellman_update(mdp, e, snap.abstract_q)
        compiled_u = operators[snap.beta].backup(snap.abstract_q)
        left_q = ab.ground_state_action_abstract_q(e, source_u)
        right_q = ab.ground_state_action_abstract_q(e, compiled_u)
        max_update_error = max(max_update_error, float(np.max(np.abs(source_u - compiled_u)) / scale))
        max_ground_error = max(max_ground_error, float(np.max(np.abs(left_q - right_q)) / scale))
        left = stable_legal_policy(adapter, left_q, reward_scale=scale)
        right = stable_legal_policy(adapter, right_q, reward_scale=scale)
        if not np.array_equal(left, right):
            events.append({"sweep": snap.sweep, "beta": snap.beta,
                           **policy_difference(adapter, evaluate_q(adapter, original, left_q, scale), evaluate_q(adapter, original, right_q, scale))})
        if float(snap.grounded_q.reshape(adapter.legal_mask.shape)[adapter.terminal_state, -1]) != 0.:
            raise ValueError("Adaptive switch changed the terminal value")
        evaluated = evaluate_q(adapter, original, snap.grounded_q, scale)
        trace.append({"sweep": snap.sweep, "beta": snap.beta, "author_backup_units": snap.bellman_backup_units,
                      **{key: evaluated[key] for key in ("root_value", "root_regret", "root_bias")}})
    if max_update_error > 1e-12 or max_ground_error > 1e-12:
        raise ValueError("Compiled numerical error exceeds frozen tolerance")
    comparison_seconds = perf_counter() - before
    final = run.final_snapshot
    adaptive = evaluate_q(adapter, original, final.grounded_q, scale)
    return {
        "scale": scale, "controls": controls, "primary_beta": 10., "primary": beta_rows[10.],
        "all_fixed_betas": [beta_rows[b] for b in BETAS],
        "adaptive": {**adaptive, "beta": final.beta, "seconds": adaptive_seconds,
                     "snapshot_backup_units": final.bellman_backup_units,
                     "paid_backup_units": run.final_state.cumulative_backup_units,
                     "switch_betas": run.final_state.switch_betas, "trace": trace,
                     "comparison_to_flat_snapshot": policy_difference(adapter, controls["flat_adaptive_snapshot"], adaptive)},
        "compiled_comparison": {"snapshots": len(run.snapshots), "max_update_error": max_update_error,
                                "max_ground_error": max_ground_error, "action_disagreement_events": events},
        "experiment_costs": {"all_fits_seconds": sum(beta_rows[b]["fit_seconds"] for b in BETAS),
                             "all_embeddings_seconds": sum(beta_rows[b]["embedding_seconds"] for b in BETAS),
                             "all_groundings_seconds": sum(beta_rows[b]["grounding_seconds"] for b in BETAS),
                             "all_compiles_seconds": sum(beta_rows[b]["compile_seconds"] for b in BETAS),
                             "all_fixed_solves_seconds": sum(beta_rows[b]["solve_seconds"] for b in BETAS),
                             "adaptive_seconds": adaptive_seconds, "snapshot_checks_and_evaluation_seconds": comparison_seconds},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/rate_distortion_v41")
    args = parser.parse_args()
    source = ROOT.parent / "acfqp-rate-distortion-reference-v39-source"
    if subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() != AUTHOR_COMMIT:
        raise ValueError("Wrong author revision")
    if subprocess.check_output(["git", "-C", str(source), "diff", "HEAD", "--"], text=True):
        raise ValueError("Author source was modified")
    if args.output_dir.exists():
        raise FileExistsError("Retain V41 attempts; use a fresh output directory")
    args.output_dir.mkdir(parents=True)
    sys.path.insert(0, str(source / "code"))
    from core import abstraction as ab, planning as pl, adaptive as ad
    from exp4_sysadmin import sysadmin_mdp as metric
    started = perf_counter()
    filenames = []
    for case in PUBLIC_DEVELOPMENT_BOARDS:
        print(f"[V41] {case}", flush=True)
        before = perf_counter()
        adapter = target.build_exact_2048_adapter(case, ab)
        acquisition_seconds = perf_counter() - before
        before = perf_counter()
        original = target.exact_original_solution(adapter)
        original_truth_evaluation_seconds = perf_counter() - before
        before = perf_counter()
        exact_values = pl.solve_optimal_values(adapter.mdp)
        exact_q = pl.bellman_update(adapter.mdp, np.repeat(exact_values, adapter.mdp.num_actions))
        exact_solve_seconds = perf_counter() - before
        if np.max(np.abs(exact_q[adapter.valid_pair_indices] - original["legal_q"])) > 1e-12:
            raise ValueError("Exact tabular DP differs from original finite-horizon truth")
        exact = evaluate_q(adapter, original, exact_q)
        before = perf_counter()
        distance = target.author_fixed_point_distortion(adapter, metric)
        metric_seconds = perf_counter() - before
        np.savez(args.output_dir / f"{case}.distance.npz", distance=distance)
        previous = json.loads((ROOT / "reports/rate_distortion_v40" / f"{case}.json").read_text())
        record = {
            "case": case, "closure_counts": adapter.closure.counts,
            "costs": {"acquisition_seconds": acquisition_seconds, "metric_seconds": metric_seconds,
                      "exact_solve_seconds": exact_solve_seconds, "original_truth_evaluation_seconds": original_truth_evaluation_seconds},
            "exact_cost_scope": "Author tabular optimal-value DP plus Bellman Q and stable readout; independent original finite-horizon truth/evaluation is charged separately.",
            "exact_root_optimum": original["mean_root_value"], "exact_tie_policy": exact,
            "ground_model_array_bytes": adapter.mdp.transitions.nbytes + adapter.mdp.rewards.nbytes,
            "exact_policy_cache_array_bytes": exact["policy"].nbytes,
            "exact_policy_and_values_cache_array_bytes": exact["policy"].nbytes + exact["state_values"].nbytes,
            "exact_one_query_prepare_seconds": acquisition_seconds + exact_solve_seconds + exact["readout_seconds"],
            "conditions": {},
        }
        for units in ("raw", "doorkey_metric_units"):
            prior = previous["conditions"][units]
            result = run_condition(adapter, original, distance, prior["reward_and_distance_scale"],
                                   (ab, pl, ad), prior, args.output_dir, f"{case}.{units}")
            row = result["primary"]
            row["one_query_prepare_seconds"] = acquisition_seconds + metric_seconds + row["fit_seconds"] + row["embedding_seconds"] + row["compile_seconds"] + row["solve_seconds"] + row["grounding_seconds"] + row["readout_seconds"]
            record["conditions"][units] = result
            print(json.dumps({"case": case, "units": units, "primary_regret": row["root_regret"], "primary_bias": row["root_bias"], "complete_bytes": row["deployment"]["complete_numeric_array_bytes"]}), flush=True)
        path = args.output_dir / f"{case}.json"
        write_json(path, record)
        filenames.append(path.name)
    child = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/replay_rate_distortion_compiled_v40.py"), str(args.output_dir.resolve())], capture_output=True, check=True, text=True)
    write_json(args.output_dir / "summary.json", {
        "author_commit": AUTHOR_COMMIT, "case_files": filenames, "new_sampled_environment_draws": 0,
        "fresh_process_replay": json.loads(child.stdout), "wall_seconds": perf_counter() - started,
        "primary_beta": 10., "tie_tolerance_original_units": 1e-12,
        "scope": "Six public H2 conditions; one structural intervention, retained controls, newly specified tie readout. Array runtime has no original model dependency; preparation and evaluation use the exact model.",
    })
    print("[V41] complete", flush=True)


if __name__ == "__main__":
    main()
