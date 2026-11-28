"""Phase-III `R7A` Bounded Provenance, Cross-Commit E3 Policy Comparison, CE `pred_val`,
& Bauer Row-Stochastic Simplex Diagnostic Sidecar (`learned_portal_phase3.run_phase3_r7a_sidecar_audit`).

Follows GPT6 `green_kriging_v14` (`R7A-01..07` & Decision C Step 1) strictly:
  - Preserves ALL 47 historical archives (`Phase-I`, `Phase-II`, `p3_v1`, `p3_v2`, `p3_v3`, AND `p3_v4` `798a9e2b...`)
    100% byte-for-byte untouched, and runs ZERO new benchmark campaigns or continuous trajectory rollouts.
  - Runs all `21 / 21` Deterministic Contract Gates (`P3-C01..P3-C21`).
  - Reconstructs all `672 / 672` actual frozen `67532c9` (`v3`) vs. current (`v4.1`) `E3` `CSR` policies in an isolated
    `git archive` checkout (`Closes R7A-03`), recording `old_raw_csr_sha256`, `new_raw_csr_sha256`, `max_abs_entry_diff`,
    `matrix_infinity_norm_diff`, `same_fallback`, and fail-closed comparison status (`zero continuous rollouts`).
  - Exports all `320` `PlugIn_CE` task events (`128` in `E1 240k` + `192` in `E2 460k`) with explicit `pred_val`,
    `deployed_policy_J`, `optimism_shortfall_J_minus_pred`, `threshold_1e_9`, and separated `native_room_lu_rhs = 0`
    vs. `global_lu_rhs` (`Closes R7A-05 & R7A-06`).
  - Quantifies on the EXACT fixed `E1 240k` (`128` tasks) and `E2 460k` (`192` tasks) datasets and policies the gap
    between the coordinatewise sub-Markov surrogate upper bound `J_bar_{M_pes}(pi)` and Bauer's exact row-stochastic
    simplex worst case under BOTH `unknown_support_dmax8` and `known_observed_support` (`Decision C Step 1`).
  - Renders updated figures `p3_v4_r7a_fig1_rotated_pac_and_decomposition.png` and
    `p3_v4_r7a_fig2_3d_linear_mf_and_continuous.png` (`fixing Panel 1A/1B version/event labels and Panel 2A "258 global RHS"`).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from green_response import collect_runtime_metadata, enforce_single_thread_env
from quotient_phase2.m232_final_closure import _sanitize_for_strict_json
from quotient_phase2.m233_sisc_subportal_quadtree import verify_m233_original_archive_untouched
from quotient_phase2.verify_m232_release import _strict_json_loads, verify_all_10_frozen_jsons

from learned_portal_phase3 import (
    phase3_output_directory,
    compute_phase3_manifest,
    verify_phase1_and_phase2_untouched,
    verify_phase3_v1_archive_untouched,
    verify_phase3_v2_archive_untouched,
    verify_phase3_v3_archive_untouched,
    verify_phase3_v4_archive_untouched,
)
from learned_portal_phase3.baselines_and_contracts import (
    PlugInCEFullGraphPlanner,
    UncompressedSpectralSchurPACPlanner,
    evaluate_posterior_pac_policy_upper_bound,
    evaluate_row_stochastic_simplex_posterior_diagnostic,
    run_phase3_21_contract_gates,
)
from learned_portal_phase3.spql_core import (
    build_curved_3d_cave_env,
    build_rotated_multiroom_2d_env,
    collect_exploration_trajectories,
    sample_unseen_goal_tasks,
)


FROZEN_M233_CLEAN_SHA256 = "73101638ce563ca9f33049e2ffef50c16218ad097785c031ecd19d3d99a7e678"

from learned_portal_phase3.run_phase3_r675_targeted_audit import _goal_sha1
from learned_portal_phase3.e3_policy_comparison import run_actual_cross_commit_e3_policy_comparison


# SHA-256 of sorted relative path + ":" + file SHA-256 + newline at 5be3f35.
FROZEN_47_MANIFEST_SHA256 = "388f57c5e253d1144b6c4f12192cf488b861bc846e9ea74708a2be678b655c69"
FROZEN_ARCHIVE_NAMES = {
    "green_response": (
        "audit_closure_results.json",
        "exp1_results.json",
        "exp2_results.json",
        "exp3_results.json",
        "exp4_acquisition_tapes.json",
        "exp4_results.json",
        "exp5_results.json",
    ),
    "quotient_phase2": (
        "m20_contract_results.json",
        "m21_ablation_results.json",
        "m21_economic_gate_verdict.json",
        "m21_post_audit_closure.json",
        "m22_pilot_results.json",
        "m231_audit_closure.json",
        "m231_fair_ablation_results.json",
        "m232_contract_and_ring_closure.json",
        "m232_release_verification_report.json",
        "m232_targeted_replay_results.json",
        "m233_clean_isolation_replication.json",
        "m233_sisc_unlock_results.json",
        "m23_m24_3d_results.json",
    ),
    "learned_portal_phase3": (
        "p3_neurips_benchmark_results.json", "p3_v2_verified_benchmark_results.json",
        "p3_v3_r747_delivery_verified_results.json", "p3_v4_r675_verified_results.json",
    ),
}


def _verify_frozen_roster(root):
    paths = [path for name in ("green_response", "quotient_phase2") for path in (root / name).glob("*.py")]
    paths.extend(root / name / file for name, files in FROZEN_ARCHIVE_NAMES.items() for file in files)
    hashes = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(paths)}
    digest = hashlib.sha256("".join(f"{name}:{sha}\n" for name, sha in hashes.items()).encode()).hexdigest()
    if len(hashes) != 47 or digest != FROZEN_47_MANIFEST_SHA256:
        raise ValueError(f"Frozen 47-file manifest mismatch: {len(hashes)} files, {digest}")
    return {"sha256": digest, "files": hashes, "count": len(hashes)}


def _verified_ce_event(block, seed, task, env, solution, start, goal_mask, reference):
    goal_sha = _goal_sha1(goal_mask)
    if (start, goal_sha) != (reference["start_state"], reference["goal_sha1"]):
        raise ValueError(f"{block} task identity mismatch at {(seed, task)}")
    policy = solution["Pi_ext_csr"]
    if policy is None or not reference["proper_policy"]:
        raise ValueError(f"{block} missing proper CE policy at {(seed, task)}")
    archived_j = float(reference["deployed_policy_J"])
    actual_j = float(env.evaluate_deployed_policy_true_cost(policy, goal_mask, 0.0, start))
    pred = float(solution["pred_val"])
    if not np.isfinite([pred, actual_j, archived_j]).all() or not np.isclose(
        actual_j, archived_j, rtol=1e-10, atol=1e-9
    ):
        raise ValueError(f"{block} deployed CE cost mismatch at {(seed, task)}: {actual_j} vs {archived_j}")
    violation = pred < actual_j - 1e-9
    if violation != reference["ce_overoptimism_violation"]:
        raise ValueError(f"{block} CE optimism flag mismatch at {(seed, task)}")
    return {
        "block": block, "seed": seed, "task_index": task, "start_state": start, "goal_sha1": goal_sha,
        "pred_val": pred, "deployed_policy_J": actual_j, "archived_deployed_policy_J": archived_j,
        "optimism_shortfall_J_minus_pred": actual_j - pred, "violation_threshold": 1e-9,
        "ce_self_underestimation_violation": violation,
        "native_room_lu_rhs": int(solution.get("operational_lu_rhs", 0)),
        "global_lu_rhs": int(solution["global_lu_rhs"]),
    }


def _event_accounting(data):
    e1 = data["block_e1_240k_full_ledger_and_v2_reanalysis"]["v4_240k_full_repair_ledger"]["task_events"]
    e2 = data["block_e2_curved_3d_linear_mf_and_4level"]["task_events"]
    e3 = data["block_e3_continuous_surrogate_fingerprint_verified"]["task_events"]
    methods = (
        ("SPQL_Passive", "SPQL_Active", "Uncompressed_PAC_Passive", "PlugIn_CE_Passive"),
        ("SPQL", "MatrixFree_SpectralSchur_PAC", "Uncompressed_SpectralSchur_PAC", "PlugIn_CE_FullGraph"),
        ("SPQL", "SPQL_UniformPortals", "Uncompressed_PAC", "PlugIn_CE", "Sampled_Desirability_TD",
         "Scalar_Portal_Ablation", "SVD_Resolvent_Ablation"),
    )
    for rows, arms, first_seed, n_tasks in zip((e1, e2, e3), methods, (4000, 5000, 6000), (16, 24, 12)):
        keys = {(r["seed"], r["task_index"], r["method_id"]) for r in rows}
        expected = {(sd, t, arm) for sd in range(first_seed, first_seed + 8)
                    for t in range(n_tasks) for arm in arms}
        if len(rows) != len(keys) or keys != expected:
            raise ValueError(f"Missing, duplicate or unexpected method events in block starting at {first_seed}")

    pac_counts = []
    violations = within = finite = ce_count = 0
    for rows, ce, eps, eps_key, viol_key in (
        (e1, methods[0][-1], 0.18, "within_eps_0p18", "pac_four_ineq_violation_zero_slack"),
        (e2, methods[1][-1], 0.15, "within_eps_0p15", "pac_violation_zero_slack"),
    ):
        pac = [r for r in rows if r["method_id"] != ce]
        ce_count += len(rows) - len(pac)
        pac_counts.append(len(pac))
        for r in pac:
            if not r["finite_certified"]:
                violation = r["lo"] is not None and r["lo"] > r["true_optimal_V"]
                if violation != r[viol_key] or r[eps_key]:
                    raise ValueError("Nonfinite PAC event flags disagree with its lower bound")
                violations += int(violation)
                continue
            lo, opt, cost, hi, width = (r[k] for k in ("lo", "true_optimal_V", "deployed_policy_J", "hi", "width"))
            if not r["policy_present"] or not r["proper_policy"] or None in (lo, opt, cost, hi, width):
                raise ValueError("Finite PAC event missing policy or value")
            if not np.isfinite([lo, opt, cost, hi, width]).all() or not np.isclose(width, hi-lo, rtol=1e-12, atol=1e-12):
                raise ValueError("Invalid finite PAC event width")
            violation = not (lo <= opt <= cost <= hi)
            if violation != r[viol_key] or ((hi-lo) <= eps) != r[eps_key]:
                raise ValueError("Saved PAC flag disagrees with the numerical values")
            violations += int(violation)
            within += int((hi-lo) <= eps)
            finite += 1
    return {
        "total_saved_method_events_in_v4": len(e1)+len(e2)+len(e3),
        "discrete_pac_attempts": sum(pac_counts), "discrete_pac_four_inequality_events": finite,
        "discrete_pac_e1_events": pac_counts[0], "discrete_pac_e2_events": pac_counts[1],
        "discrete_pac_nonfinite_attempts": sum(pac_counts) - finite,
        "discrete_pac_zero_slack_violations": violations, "discrete_pac_within_requested_eps_count": within,
        "uncertified_plugin_ce_control_events": ce_count, "tier4_empirical_continuous_surrogate_events": len(e3),
    }


def _simplex_event(seed, task, pair, ce_policy, pac_policy, pac_hi, gm, s0, lam):
    ce_coord = evaluate_posterior_pac_policy_upper_bound(pair, ce_policy, gm, 0.0, s0, lam)
    ce_unk_simp = evaluate_row_stochastic_simplex_posterior_diagnostic(
        pair, ce_policy, gm, 0.0, s0, lam, known_observed_support=False, max_degree_bound=8
    )
    ce_obs_simp = evaluate_row_stochastic_simplex_posterior_diagnostic(
        pair, ce_policy, gm, 0.0, s0, lam, known_observed_support=True, max_degree_bound=8
    )
    uc_coord = evaluate_posterior_pac_policy_upper_bound(pair, pac_policy, gm, 0.0, s0, lam)
    uc_obs_simp = evaluate_row_stochastic_simplex_posterior_diagnostic(
        pair, pac_policy, gm, 0.0, s0, lam, known_observed_support=True, max_degree_bound=8
    )
    values = (ce_coord, ce_unk_simp, ce_obs_simp, uc_coord, uc_obs_simp, pac_hi)
    if not np.isfinite(values).all():
        raise ValueError(f"Non-finite posterior diagnostic at {(seed, task)}")
    # Each support restriction shrinks a nested set; allow sparse-solve roundoff.
    for tight, loose in ((ce_obs_simp, ce_unk_simp), (ce_unk_simp, ce_coord), (uc_obs_simp, uc_coord)):
        if tight > loose and not np.isclose(tight, loose, rtol=1e-10, atol=1e-9):
            raise ValueError(f"Posterior support ordering failed at {(seed, task)}")
    return {
        "seed": seed, "task_index": task, "goal_sha1": _goal_sha1(gm),
        "ce_coord_surrogate_U": ce_coord,
        "ce_unknown_support_dmax8_simplex_U": ce_unk_simp,
        "ce_known_observed_support_simplex_U": ce_obs_simp,
        "full_pac_tier3_hi": pac_hi,
        "full_pac_coord_surrogate_U": uc_coord,
        "full_pac_known_observed_support_simplex_U": uc_obs_simp,
    }


def run_ce_pred_val_and_simplex_gap_sidecar(v4_data: dict) -> dict:
    """Exports all `320` CE `pred_val` records + separated `global_lu_rhs` (`Closes R7A-05 & R7A-06`),
    AND quantifies on the fixed `E1 240k` and `E2 460k` datasets the exact gap between coordinatewise
    surrogate bounds and Bauer row-stochastic simplex bounds (`Decision C Step 1`).
    """
    v4_e1 = v4_data["block_e1_240k_full_ledger_and_v2_reanalysis"]["v4_240k_full_repair_ledger"]["task_events"]
    v4_e2 = v4_data["block_e2_curved_3d_linear_mf_and_4level"]["task_events"]
    e1_ce_ref = {(int(e["seed"]), int(e["task_index"])): e for e in v4_e1 if e["method_id"] == "PlugIn_CE_Passive"}
    e2_ce_ref = {(int(e["seed"]), int(e["task_index"])): e for e in v4_e2 if e["method_id"] == "PlugIn_CE_FullGraph"}

    ce_e1_rows: list[dict] = []
    simplex_e1_rows: list[dict] = []
    for sd in range(4000, 4008):
        print(f"  E1 map {sd}", flush=True)
        env = build_rotated_multiroom_2d_env(seed=sd, grid_n=40, angle_deg=37.0, door_half_width=0.10, add_baffles=True)
        entry_room = int(np.bincount(env.true_room_hint_for_eval).argmax())
        entry_states = np.flatnonzero(env.true_room_hint_for_eval == entry_room)
        tasks = sample_unseen_goal_tasks(env, n_tasks=16, seed=sd + 1000, goal_radius_nodes=6, avoid_states=None)
        ds_pas = collect_exploration_trajectories(
            env, total_steps=240000, episode_len=110, seed=sd + 240000, entry_states=entry_states, ambient_reset_prob=0.10
        )
        pl_ce = PlugInCEFullGraphPlanner(ds_pas)
        pl_uc = UncompressedSpectralSchurPACPlanner(ds_pas, delta=0.05, max_rooms=10, max_degree_bound=8)
        for t_i, (s0, gm) in enumerate(tasks):
            rc = pl_ce.solve_unseen_goal(s0, gm)
            ru = pl_uc.solve_unseen_goal(s0, gm, materialize_policy=True)
            ref = e1_ce_ref[(sd, t_i)]
            ce_e1_rows.append(_verified_ce_event("E1_240k_Passive", sd, t_i, env, rc, s0, gm, ref))
            simplex_e1_rows.append(_simplex_event(sd, t_i, pl_uc.pac_pair, rc["Pi_ext_csr"],
                                                 ru["Pi_ext_csr"], ru["hi"], gm, s0, env.lam))

    ce_e2_rows: list[dict] = []
    simplex_e2_rows: list[dict] = []
    for sd in range(5000, 5008):
        print(f"  E2 map {sd}", flush=True)
        env = build_curved_3d_cave_env(seed=sd, gn=38)
        ds = collect_exploration_trajectories(env, total_steps=460000, episode_len=100, seed=sd + 300)
        tasks = sample_unseen_goal_tasks(env, n_tasks=24, seed=sd + 600, goal_radius_nodes=12, avoid_states=None)
        pl_ce = PlugInCEFullGraphPlanner(ds)
        pl_uc = UncompressedSpectralSchurPACPlanner(ds, delta=0.05, max_rooms=10, max_degree_bound=8)
        for t_i, (s0, gm) in enumerate(tasks):
            rc = pl_ce.solve_unseen_goal(s0, gm)
            ru = pl_uc.solve_unseen_goal(s0, gm, materialize_policy=True)
            ref = e2_ce_ref[(sd, t_i)]
            ce_e2_rows.append(_verified_ce_event("E2_460k_Curved3DCave", sd, t_i, env, rc, s0, gm, ref))
            simplex_e2_rows.append(_simplex_event(sd, t_i, pl_uc.pac_pair, rc["Pi_ext_csr"],
                                                 ru["Pi_ext_csr"], ru["hi"], gm, s0, env.lam))

    def _sum_simplex(rows: list[dict]) -> dict:
        return {
            "guarantee_tier": "float64_numerical_diagnostic",
            "n_tasks": len(rows),
            "task_events": rows,
            "mean_ce_coord_surrogate_U": float(np.mean([r["ce_coord_surrogate_U"] for r in rows])),
            "mean_ce_unknown_support_dmax8_simplex_U": float(np.mean([r["ce_unknown_support_dmax8_simplex_U"] for r in rows])),
            "mean_ce_known_observed_support_simplex_U": float(np.mean([r["ce_known_observed_support_simplex_U"] for r in rows])),
            "mean_full_pac_coord_surrogate_U": float(np.mean([r["full_pac_coord_surrogate_U"] for r in rows])),
            "mean_full_pac_known_observed_support_simplex_U": float(np.mean([r["full_pac_known_observed_support_simplex_U"] for r in rows])),
            "count_ce_obs_simplex_tighter_than_full_pac_surrogate": int(
                sum(1 for r in rows if r["ce_known_observed_support_simplex_U"] < r["full_pac_coord_surrogate_U"])
            ),
        }

    return {
        "ce_pred_val_audit": {
            "e1_240k_count": len(ce_e1_rows),
            "e1_recomputed_self_underestimation_count": int(sum(1 for r in ce_e1_rows if r["ce_self_underestimation_violation"])),
            "e1_mean_pred_val": float(np.mean([r["pred_val"] for r in ce_e1_rows])),
            "e1_mean_deployed_J": float(np.mean([r["deployed_policy_J"] for r in ce_e1_rows])),
            "e1_mean_global_lu_rhs": float(np.mean([r["global_lu_rhs"] for r in ce_e1_rows]) * 16.0),
            "e2_460k_count": len(ce_e2_rows),
            "e2_recomputed_self_underestimation_count": int(sum(1 for r in ce_e2_rows if r["ce_self_underestimation_violation"])),
            "e2_mean_pred_val": float(np.mean([r["pred_val"] for r in ce_e2_rows])),
            "e2_mean_deployed_J": float(np.mean([r["deployed_policy_J"] for r in ce_e2_rows])),
            "e2_mean_native_room_lu_rhs": float(sum(r["native_room_lu_rhs"] for r in ce_e2_rows) / 8),
            "e2_mean_global_lu_rhs_per_map": float(sum(r["global_lu_rhs"] for r in ce_e2_rows) / 8.0),
            "max_abs_rebuilt_minus_archived_J": max(abs(r["deployed_policy_J"] - r["archived_deployed_policy_J"])
                                                    for r in ce_e1_rows + ce_e2_rows),
            "e1_events": ce_e1_rows,
            "e2_events": ce_e2_rows,
        },
        "decision_c_simplex_vs_surrogate_diagnostic": {
            "e1_240k_passive": _sum_simplex(simplex_e1_rows),
            "e2_460k_3d": _sum_simplex(simplex_e2_rows),
        },
    }


def _render_r7a_figures(v4_data: dict, ce_audit: dict, out_dir: Path) -> None:
    e1_blk = v4_data["block_e1_240k_full_ledger_and_v2_reanalysis"]
    e2_blk = v4_data["block_e2_curved_3d_linear_mf_and_4level"]
    e3_blk = v4_data["block_e3_continuous_surrogate_fingerprint_verified"]
    re_b = e1_blk["v2_reanalysis_by_budget"]
    dec_3d = e2_blk["same_data_4level_decomposition_3d"]
    budgets = [30000, 90000, 240000]
    x_lbl = ["30k", "90k", "240k"]

    fig, axes = plt.subplots(1, 3, figsize=(15.8, 4.6), dpi=180)
    ax = axes[0]
    for m_k, lbl, st, col in (
        ("SPQL_Active", "SPQL Active (PAC + Binary Fiedler)", "-o", "#16a085"),
        ("SPQL_Passive", "SPQL Passive (PAC + Binary Fiedler)", "-s", "#27ae60"),
        ("PlugIn_CE_FullGraph", "Plug-In CE (Uncertified LU)", "--^", "#2980b9"),
        ("Scalar_L0_Portal_Ablation", "Scalar L0 Portal Ablation", "-.d", "#d35400"),
        ("TransitionSVD_Resolvent_Ablation", "Transition SVD Resolvent Abl.", ":v", "#8e44ad"),
        ("Sampled_Desirability_TD", "Sampled Desirability TD", ":x", "#c0392b"),
    ):
        ys = [re_b[str(b)]["v2_summary_methods"][m_k]["mean_capped_score_80"] for b in budgets]
        ax.plot(range(len(budgets)), ys, st, linewidth=2.1, markersize=6, color=col, label=lbl)
    ax.set_xticks(range(len(budgets)))
    ax.set_xticklabels(x_lbl)
    ax.set_xlabel("Exploration Trajectory Budget $N_{\\mathrm{step}}$")
    ax.set_ylabel("Mean Cap-80 Regret Score")
    ax.set_title("A. Rotated 9-Room Cap-80 Sweep (Frozen v2)", fontsize=9.3, fontweight="bold")
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=6.5, loc="lower left")

    ax = axes[1]
    v4_240 = e1_blk["v4_240k_full_repair_ledger"]["methods_summary"]
    bars_x = np.arange(3)
    uncap_vals = [
        v4_240["PlugIn_CE_Passive"]["mean_uncapped_regret"],
        v4_240["SPQL_Active"]["mean_uncapped_regret"],
        v4_240["SPQL_Passive"]["mean_uncapped_regret"],
    ]
    cap_vals = [
        v4_240["PlugIn_CE_Passive"]["mean_capped_score_80"],
        v4_240["SPQL_Active"]["mean_capped_score_80"],
        v4_240["SPQL_Passive"]["mean_capped_score_80"],
    ]
    ax.bar(bars_x - 0.17, uncap_vals, width=0.32, color="#16a085", label="Uncapped Regret (240k v4)")
    ax.bar(bars_x + 0.17, cap_vals, width=0.32, color="#2980b9", label="Cap-80 Score (240k v4)")
    ax.set_xticks(bars_x)
    ce_rate = ce_audit["e1_recomputed_self_underestimation_count"] / ce_audit["e1_240k_count"]
    def pac_label(arm):
        events = [e for e in e1_blk["v4_240k_full_repair_ledger"]["task_events"] if e["method_id"] == arm]
        return f"{arm.replace('_', ' ')}\n({np.mean([e['pac_four_ineq_violation_zero_slack'] for e in events]):.0%} PAC Env. Viol.)"
    ax.set_xticklabels(
        [f"Plug-In CE\n({ce_rate:.1%} Self-Underest.)", pac_label("SPQL_Active"), pac_label("SPQL_Passive")],
        fontsize=7.6,
    )
    ax.set_ylabel("Mean Regret at 240k (128/128 Proper)")
    ax.set_title("B. 240k Uncapped vs. Cap-80 (v4 Full Ledger)", fontsize=9.3, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=7.4)

    ax = axes[2]
    lv_names = ["True Opt\n$V^*$", "Plug-In CE\n$J(\\hat{\\pi}_{CE})$", "Full PAC\n$J(\\hat{\\pi}_{PAC})$", "Coarse SPQL\n$J(\\hat{\\pi}_{SPQL})$"]
    lv_vals = [
        dec_3d["mean_true_optimal_V"],
        dec_3d["mean_plugin_ce_J"],
        dec_3d["mean_full_pac_J"],
        dec_3d["mean_coarse_spql_J"],
    ]
    lv_cols = ["#34495e", "#2980b9", "#8e44ad", "#16a085"]
    b_dec = ax.bar(range(4), lv_vals, color=lv_cols, width=0.52)
    for rect, v in zip(b_dec, lv_vals):
        ax.text(rect.get_x() + rect.get_width() / 2, v + 0.9, f"{v:.2f}", ha="center", va="bottom", fontsize=7.8, fontweight="bold")
    ax.set_xticks(range(4))
    ax.set_xticklabels(lv_names, fontsize=7.8)
    ax.set_ylim(0, max(lv_vals) * 1.22)
    ax.set_ylabel("Mean 3D Cave Deployed Cost (192 Tasks)")
    ax.set_title("C. Same-Data 4-Level Cost Decomposition (E2 v4)", fontsize=9.3, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(out_dir / "p3_v4_r7a_fig1_rotated_pac_and_decomposition.png", bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(14.2, 4.8), dpi=180)
    ax = axes[0]
    arms_3d = ("PlugIn_CE_FullGraph", "Uncompressed_SpectralSchur_PAC", "MatrixFree_SpectralSchur_PAC", "SPQL")
    lbls_3d = ["Plug-In CE\n(192/192 Pol)", "Uncomp. PAC\n(192/192 Pol)", "Linear MF PAC\n(192/192 Pol)", "SPQL (Ours)\n(192/192 Pol)"]
    inits_s = [e2_blk["arms_summary"][k]["mean_offline_init_ms"] / 1000.0 for k in arms_3d]
    onlines_s = [e2_blk["arms_summary"][k]["mean_online_24q_full_policy_ms"] / 1000.0 for k in arms_3d]
    rhs_3d = [e2_blk["arms_summary"][k]["mean_total_lifecycle_native_room_lu_rhs"] for k in arms_3d]
    fb_3d = [e2_blk["arms_summary"][k]["mean_online_global_fallback_lu_calls"] for k in arms_3d]
    x3 = np.arange(len(arms_3d))
    ax.bar(x3, inits_s, width=0.5, color="#95a5a6", label="Offline Init (s)")
    ax.bar(x3, onlines_s, bottom=inits_s, width=0.5, color=["#2980b9", "#8e44ad", "#d35400", "#16a085"], label="24 Matched Full-Policy Queries (s)")
    for idx_i, (k_nm, tot_v, rv, fbv) in enumerate(zip(arms_3d, np.array(inits_s) + np.array(onlines_s), rhs_3d, fb_3d)):
        if k_nm == "PlugIn_CE_FullGraph":
            rhs_lbl = f"({ce_audit['e2_mean_global_lu_rhs_per_map']:.0f} global RHS)"
        else:
            fb_str = f" + {fbv:.1f} glb" if fbv > 0 else ""
            rhs_lbl = f"({rv:.0f} rmRHS{fb_str})"
        ax.text(idx_i, tot_v + 0.25, f"{tot_v:.2f}s\n{rhs_lbl}", ha="center", va="bottom", fontsize=7.2, fontweight="bold")
    ax.set_xticks(x3)
    ax.set_xticklabels(lbls_3d, fontsize=7.8)
    ax.set_ylabel("Single-Worker Lifecycle Time (s)")
    ax.set_ylim(0, max(np.array(inits_s) + np.array(onlines_s)) * 1.28)
    ax.set_title("A. 3D Cave Lifecycle (Linear MatrixFree & Separated LU)", fontsize=9.3, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=7.8, loc="upper left")

    ax = axes[1]
    m_c = ("SPQL", "SPQL_UniformPortals", "Uncompressed_PAC", "PlugIn_CE", "Sampled_Desirability_TD", "Scalar_Portal_Ablation", "SVD_Resolvent_Ablation")
    l_c = ["SPQL\n(7 num fb)", "SPQL-Uni\n(20 num fb)", "Uncomp.\nPAC", "PlugIn\nCE", "Group\nTD", "Scalar\nPortal", "SVD\nResolv."]
    costs_c = [e3_blk["summary"][k]["mean_closed_loop_cost"] for k in m_c]
    succ_c = [e3_blk["summary"][k]["mean_success_rate_pct"] for k in m_c]
    cols_c = ["#16a085", "#1abc9c", "#27ae60", "#2980b9", "#c0392b", "#d35400", "#8e44ad"]
    bars2 = ax.bar(range(len(m_c)), costs_c, color=cols_c, width=0.58)
    for b_rect, cv, sv in zip(bars2, costs_c, succ_c):
        ax.text(b_rect.get_x() + b_rect.get_width() / 2, cv + 0.12, f"{cv:.2f}\n({sv:.0f}%)", ha="center", va="bottom", fontsize=7.2, fontweight="bold")
    ax.set_xticks(range(len(m_c)))
    ax.set_xticklabels(l_c, fontsize=7.6)
    ax.set_ylim(0, max(costs_c) * 1.26)
    ax.set_ylabel("Empirical Surrogate Cost (96/96 Policies)")
    ax.set_title("B. Tier-4 Continuous Surrogate (Zero Silent u=0 Fallback)", fontsize=9.3, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(out_dir / "p3_v4_r7a_fig2_3d_linear_mf_and_continuous.png", bbox_inches="tight")
    plt.close(fig)


def run_r7a_sidecar_audit(gates_only: bool = False, output_dir: Path | None = None) -> dict:
    t0 = time.perf_counter()
    enforce_single_thread_env()
    p3_dir = Path(__file__).resolve().parent
    p2_dir = ROOT / "quotient_phase2"

    def _verify_all_47_frozen() -> dict:
        f12 = verify_phase1_and_phase2_untouched()
        fp2_10 = verify_all_10_frozen_jsons(p2_dir)
        fm233_orig = verify_m233_original_archive_untouched(p2_dir)
        m233_clean_fp = p2_dir / "m233_clean_isolation_replication.json"
        m233_clean_sha = hashlib.sha256(m233_clean_fp.read_bytes()).hexdigest()
        if m233_clean_sha != FROZEN_M233_CLEAN_SHA256:
            raise RuntimeError(f"Frozen m233_clean_isolation_replication.json modified: {m233_clean_sha}")
        return {
            **f12,
            "frozen_roster": _verify_frozen_roster(ROOT),
            "phase2_10_jsons_untouched": True,
            "phase2_json_count": len(fp2_10),
            "m233_original_archive": fm233_orig,
            "m233_clean_isolation_archive": {"file": m233_clean_fp.name, "sha256": m233_clean_sha, "verified_untouched": True},
            "phase3_v1_archive": verify_phase3_v1_archive_untouched(),
            "phase3_v2_archive": verify_phase3_v2_archive_untouched(),
            "phase3_v3_archive": verify_phase3_v3_archive_untouched(),
            "phase3_v4_archive": verify_phase3_v4_archive_untouched(),
        }

    out_dir = phase3_output_directory("r7a", output_dir)
    pre_freeze = _verify_all_47_frozen()
    source = compute_phase3_manifest()
    print("[Phase-III R7A] Running 21 Deterministic Contract Gates (P3-C01..P3-C21)...")
    gates = run_phase3_21_contract_gates()
    if not gates["ALL_21_PHASE3_CONTRACT_GATES_PASSED"]:
        raise RuntimeError(f"Contract gate failure: {gates}")
    print(f"  -> ALL 21 GATES PASSED in {gates['elapsed_ms']:.1f}ms!")
    if gates_only:
        return gates

    v4_data = json.loads((p3_dir / "p3_v4_r675_verified_results.json").read_text(encoding="utf-8"))

    accounting = _event_accounting(v4_data)
    print("[Phase-III R7A] Reconstructing all 672 actual frozen 67532c9 vs. current E3 CSR policies (zero rollouts)...")
    e3_cross = run_actual_cross_commit_e3_policy_comparison()

    print("[Phase-III R7A] Exporting 320 CE pred_val records + Decision-C Bauer simplex vs. coordinatewise diagnostic...")
    if e3_cross["new_snapshot_phase3_py_sha256"] != source["phase3_per_file_sha256"]:
        raise RuntimeError("Working source differs from the E3 reconstruction snapshot")
    ce_and_simplex = run_ce_pred_val_and_simplex_gap_sidecar(v4_data)

    post_freeze = _verify_all_47_frozen()
    if pre_freeze != post_freeze:
        raise RuntimeError("Archive manifests changed during the audit")

    if source != compute_phase3_manifest():
        raise RuntimeError("Working source changed while replaying the frozen tasks")
    _render_r7a_figures(v4_data, ce_and_simplex["ce_pred_val_audit"], out_dir)
    rt_meta = collect_runtime_metadata()
    rt_meta["actual_parallel_workers"] = 1

    payload = _sanitize_for_strict_json({
        "milestone": "Phase3_R7A_CrossCommitCSR_CEPredVal_and_SimplexDiagnostic_Sidecar",
        "scope": "Non-destructive audit & diagnostic sidecar on frozen v4 seeds (0 benchmark timing edits, 0 continuous rollout reruns, 47/47 frozen archives untouched)",
        "elapsed_wall_s": float(time.perf_counter() - t0),
        "runtime_metadata": rt_meta,
        "phase3_manifest": source,
        "immutable_47_archives_verified": post_freeze,
        "event_denominator_accounting": accounting,
        "contract_21_gates": gates,
        "e3_actual_cross_commit_672_policy_audit": e3_cross,
        **ce_and_simplex,
    })

    out_fp = out_dir / "p3_v4_r7a_sidecar_diagnostics.json"
    txt = json.dumps(payload, indent=2, allow_nan=False)
    _ = _strict_json_loads(txt)
    out_fp.write_text(txt, encoding="utf-8")
    print(
        f"[Phase-III R7A DONE] Wrote {out_fp.name} in {payload['elapsed_wall_s']:.1f}s | "
        f"Gates21/21=True | E3_672_MaxInfDiff={e3_cross['max_matrix_infinity_norm_diff']:.3e}"
    )
    return payload


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gates-only", action="store_true")
    ap.add_argument("--output-dir", type=Path, help="Directory for the reproduced JSON and figures")
    args = ap.parse_args()
    res = run_r7a_sidecar_audit(gates_only=args.gates_only, output_dir=args.output_dir)
    if args.gates_only:
        print(json.dumps(res, indent=2))
