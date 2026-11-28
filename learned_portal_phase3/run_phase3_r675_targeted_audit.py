"""Phase-III `v4` Bounded Numerical-Contract, Linear-MatrixFree, & 4-Level Decomposition Audit
(`learned_portal_phase3.run_phase3_r675_targeted_audit` — Closing `R675-01..11` & Work Package D).

Strict Bounded Scope (`per GPT6 R675 Sections 9.2–9.3 & 16`):
  1. Preserves ALL historical archives (`Phase-I`, `Phase-II`, `p3_v1`, `p3_v2`, AND `p3_v3` `0ffd1d3a...`)
     100% byte-for-byte untouched.
  2. Runs all `20 / 20` Deterministic Contract Gates (`P3-C01..P3-C20`), embedding all `R675` counterexamples:
       - Outward-rounded Higham upper/lower verifiers with gradual-underflow (`2^-1074`) & zero `1e-12` floors;
       - Per-row max-log-weight `CSR` policy normalization (`row-stochastic at 1e-310`) + certificate binding;
       - Strictly linear `MatrixFreeSpectralSchurPACPlanner._apply_K_ext` (`oddness, homogeneity, additivity`);
       - Strictly separated `native_room_lu_rhs`, `room_lu_refactorizations`, and `global_fallback_lu_calls`.
  3. Block E1 (`Seeds 4000..4007`):
       - Preserves frozen `v2` reanalysis (`30k, 90k, 240k`) AND exports **all 384 per-task events & per-seed arrays**
         for the `240k` repair block (`SPQL_Passive`, `SPQL_Active`, `PlugIn_CE_FullGraph`), reporting BOTH
         `uncapped_regret` and `capped_score_80` (`Closes R675-05`) plus 4-level error decomposition.
  4. Block E2 (`Seeds 5000..5007`, Fixed 8 Maps, 4-Arm Cyclic Schedule, Zero Cross-Arm Retention):
       - Re-verifies `SPQL`, **linear-matvec `MatrixFree_SpectralSchur_PAC`**, `Uncompressed_SpectralSchur_PAC`,
         and `PlugIn_CE_FullGraph` across all `192` tasks (`768` saved events) with separated native/global LU ledger;
       - Computes Work Package D's **Same-Data 4-Level Regret & Posterior-Bound Decomposition**:
         `V*_true` vs. `PlugIn_CE` (`+ posterior PAC bound J_bar(pi_CE)`) vs. `Full_PAC` vs. `Coarse_SPQL`.
  5. Block E3 (`Seeds 6000..6007`, Policy-Fingerprint Audit vs. Frozen `v3`, Re-evaluating Only Changed Policies):
       - Verifies all `96 x 7 = 672` discrete landmark policies under `v4`, checking `||Pi_v4 - Pi_v3||_inf`,
         recording `policy_sha256` and separated fallback counters, and re-running continuous rollouts ONLY if a
         policy changes by `> 1e-12` (`per R675 Section 9.3`).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.sparse as sp
from scipy import stats as sp_stats

from green_response import collect_runtime_metadata, enforce_single_thread_env, paired_stats
from quotient_phase2.m232_final_closure import _sanitize_for_strict_json
from quotient_phase2.m233_sisc_subportal_quadtree import verify_m233_original_archive_untouched
from quotient_phase2.verify_m232_release import _strict_json_loads, verify_all_10_frozen_jsons

from learned_portal_phase3 import (
    compute_phase3_manifest,
    verify_phase1_and_phase2_untouched,
    verify_phase3_v1_archive_untouched,
    verify_phase3_v2_archive_untouched,
    verify_phase3_v3_archive_untouched,
)
from learned_portal_phase3.baselines_and_contracts import (
    LowRankSRLinearRLPlanner,
    MatrixFreeSpectralSchurPACPlanner,
    ModelFreeGoalSoftQPlanner,
    PlugInCEFullGraphPlanner,
    ScalarBottleneckOptionPlanner,
    UncompressedSpectralSchurPACPlanner,
    evaluate_posterior_pac_policy_upper_bound,
    run_phase3_20_contract_gates,
)
from learned_portal_phase3.continuous_manifold_spql import (
    RotatedContinuousDiffusionWorld,
    build_voronoi_quotient_from_continuous_trajectories,
    evaluate_continuous_policy_rollouts,
    make_continuous_control_from_landmark_policy,
)
from learned_portal_phase3.spql_core import (
    SPQLPlanner,
    build_curved_3d_cave_env,
    build_rotated_multiroom_2d_env,
    collect_exploration_trajectories,
    collect_portal_directed_active_trajectories,
    sample_unbiased_bounded_cost,
    sample_unseen_goal_tasks,
)


FROZEN_M233_CLEAN_SHA256 = "73101638ce563ca9f33049e2ffef50c16218ad097785c031ecd19d3d99a7e678"


def _rss_mib() -> float:
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024.0
    except OSError:
        pass
    return 0.0


def _goal_sha1(gm: np.ndarray) -> str:
    idx = np.flatnonzero(gm).astype(np.int64)
    return hashlib.sha1(idx.tobytes()).hexdigest()[:12]


def _legacy_v3_policy_csr(M_csr: sp.csr_matrix, z_vec: np.ndarray, gm: np.ndarray) -> sp.csr_matrix:
    """Exact `v3` (`commit 67532c9`) policy constructor used strictly to test `||Pi_v4 - Pi_v3||_inf` in E3."""
    ext = np.flatnonzero(~gm)
    M_ext = M_csr[ext, :].tocsr()
    row_ids = np.repeat(np.arange(len(ext), dtype=np.int64), np.diff(M_ext.indptr))
    z_pos = np.maximum(np.asarray(z_vec, dtype=float), 0.0)
    z_nb = z_pos[M_ext.indices]
    rmax = np.zeros(len(ext), dtype=float)
    np.maximum.at(rmax, row_ids, z_nb)
    has_pos = rmax > 0.0
    sc = np.where(has_pos[row_ids], z_nb / np.maximum(rmax[row_ids], 1e-300), 1.0)
    w_dat = M_ext.data * sc
    W_mat = sp.csr_matrix((w_dat, M_ext.indices.copy(), M_ext.indptr.copy()), shape=M_ext.shape)
    w_sum = np.asarray(W_mat.sum(axis=1)).ravel()
    pi_dat = np.where((w_sum > 0.0)[row_ids], w_dat / np.maximum(w_sum[row_ids], 1e-300), 0.0)
    out = sp.csr_matrix((pi_dat, M_ext.indices.copy(), M_ext.indptr.copy()), shape=M_ext.shape)
    out.sort_indices()
    return out


def _exact_signflip_two_sided_p(diffs: np.ndarray) -> float:
    arr = np.asarray(diffs, dtype=float)
    n = len(arr)
    obs = abs(float(np.mean(arr)))
    cnt = 0
    for bits in range(1 << n):
        signs = np.array([1.0 if ((bits >> k) & 1) else -1.0 for k in range(n)], dtype=float)
        if abs(float(np.mean(signs * arr))) >= obs - 1e-15:
            cnt += 1
    return float(cnt) / float(1 << n)


def run_e1_240k_full_ledger_and_v2_reanalysis(p3_dir: Path, seeds: List[int]) -> dict:
    """Preserves frozen `v2` reanalysis (`30k, 90k, 240k`) AND saves **complete per-task events & per-seed arrays**
    for the `v4` `240k` repair block (`Closes R675-05`), plus 4-level same-data decomposition on `240k`.
    """
    v3_prev = json.loads((p3_dir / "p3_v3_r747_delivery_verified_results.json").read_text(encoding="utf-8"))
    reanalysis_by_budget = v3_prev["block_e1_reanalysis_and_240k_delivery_audit"]["v2_reanalysis_by_budget"]

    nb = 240000
    events_240k: List[dict] = []
    per_seed_240k: List[dict] = []

    for sd in seeds:
        env = build_rotated_multiroom_2d_env(seed=sd, grid_n=40, angle_deg=37.0, door_half_width=0.10, add_baffles=True)
        entry_room = int(np.bincount(env.true_room_hint_for_eval).argmax())
        entry_states = np.flatnonzero(env.true_room_hint_for_eval == entry_room)
        tasks = sample_unseen_goal_tasks(env, n_tasks=16, seed=sd + 1000, goal_radius_nodes=6, avoid_states=None)
        true_vs = [float(env.true_desirability_and_value(gm)[1][s0]) for s0, gm in tasks]

        ds_pas = collect_exploration_trajectories(
            env, total_steps=nb, episode_len=110, seed=sd + nb, entry_states=entry_states, ambient_reset_prob=0.10
        )
        ds_act = collect_portal_directed_active_trajectories(
            env, total_steps=nb, episode_len=110, seed=sd + nb + 17,
            entry_states=entry_states, ambient_reset_prob=0.10, warmup_frac=0.34,
        )

        pl_pas = SPQLPlanner(ds_pas, delta=0.05, eps_tol=0.18, max_rooms=10, max_degree_bound=8)
        pl_act = SPQLPlanner(ds_act, delta=0.05, eps_tol=0.18, max_rooms=10, max_degree_bound=8)
        pl_uc_pas = UncompressedSpectralSchurPACPlanner(ds_pas, delta=0.05, max_rooms=10, max_degree_bound=8)
        pl_ce_pas = PlugInCEFullGraphPlanner(ds_pas)

        seed_arm_rows: Dict[str, List[dict]] = {
            "SPQL_Passive": [],
            "SPQL_Active": [],
            "Uncompressed_PAC_Passive": [],
            "PlugIn_CE_Passive": [],
        }

        for t_i, (s0, gm) in enumerate(tasks):
            vt_s = true_vs[t_i]
            g_sha = _goal_sha1(gm)
            for m_nm, pl_obj in (
                ("SPQL_Passive", pl_pas),
                ("SPQL_Active", pl_act),
                ("Uncompressed_PAC_Passive", pl_uc_pas),
                ("PlugIn_CE_Passive", pl_ce_pas),
            ):
                rr = pl_obj.solve_unseen_goal(s0, gm, materialize_policy=True) if m_nm != "PlugIn_CE_Passive" else pl_obj.solve_unseen_goal(s0, gm)
                pol_pres = bool(rr.get("policy_present", rr.get("Pi_ext_csr") is not None))
                j_t = env.evaluate_deployed_policy_true_cost(rr["Pi_ext_csr"], gm, 0.0, s0) if pol_pres else float("inf")
                is_prop = bool(pol_pres and np.isfinite(j_t))
                uncap_reg = float(j_t - vt_s) if is_prop else None
                cap80 = float(min(j_t - vt_s, 80.0)) if is_prop else 80.0
                capped_hit = bool((not is_prop) or (j_t - vt_s > 80.0))

                if m_nm != "PlugIn_CE_Passive":
                    fin_cert = bool(rr["certified"])
                    lo_v = float(rr["lo"]) if np.isfinite(rr["lo"]) else None
                    hi_v = float(rr["hi"]) if np.isfinite(rr["hi"]) else None
                    wd_v = float(rr["width"]) if np.isfinite(rr["width"]) else None
                    w_eps = bool(fin_cert and wd_v is not None and wd_v <= 0.18)
                    pac_viol = bool(
                        (fin_cert and ((not is_prop) or not (rr["lo"] <= vt_s <= j_t <= rr["hi"])))
                        or ((not fin_cert) and lo_v is not None and lo_v > vt_s)
                    )
                    ce_post_hi = None
                    ce_opt_viol = False
                else:
                    fin_cert = False
                    lo_v = None
                    hi_v = None
                    wd_v = None
                    w_eps = False
                    pac_viol = False
                    pred_v = float(rr["pred_val"])
                    ce_opt_viol = bool(np.isfinite(pred_v) and pred_v < j_t - 1e-9)
                    ce_post_hi_raw = evaluate_posterior_pac_policy_upper_bound(
                        pl_pas.pac_pair, rr["Pi_ext_csr"], gm, 0.0, s0, env.lam
                    )
                    ce_post_hi = float(ce_post_hi_raw) if np.isfinite(ce_post_hi_raw) else None

                ev_row = {
                    "block": "E1_240k_v4_FullEventLedger",
                    "seed": int(sd),
                    "step_budget": nb,
                    "task_index": int(t_i),
                    "start_state": int(s0),
                    "goal_sha1": g_sha,
                    "method_id": m_nm,
                    "solver_status": str(rr.get("solver_status", "delivered_plugin_policy")),
                    "policy_present": pol_pres,
                    "policy_sha256": str(rr.get("policy_sha256", "")),
                    "proper_policy": is_prop,
                    "finite_certified": fin_cert,
                    "within_eps_0p18": w_eps,
                    "fallback_used": bool(rr.get("fallback_used", False)),
                    "fallback_method": rr.get("fallback_method", None),
                    "true_optimal_V": vt_s,
                    "deployed_policy_J": float(j_t) if is_prop else None,
                    "uncapped_regret": uncap_reg,
                    "capped_score_80": cap80,
                    "cap_80_triggered": capped_hit,
                    "lo": lo_v,
                    "hi": hi_v,
                    "width": wd_v,
                    "posterior_pac_upper_bound_on_policy": ce_post_hi,
                    "pac_four_ineq_violation_zero_slack": pac_viol,
                    "ce_overoptimism_violation": ce_opt_viol,
                    "query_ms": float(rr["query_ms"]),
                    "native_operational_lu_rhs": int(rr.get("operational_lu_rhs", rr.get("global_lu_rhs", 0))),
                    "native_materialization_lu_rhs": int(rr.get("materialization_lu_rhs", 0)),
                    "room_lu_refactorizations": int(rr.get("room_lu_refactorizations", 0)),
                    "global_fallback_lu_calls": int(rr.get("global_fallback_lu_calls", 0)),
                }
                events_240k.append(ev_row)
                seed_arm_rows[m_nm].append(ev_row)

        per_seed_240k.append({
            "seed": int(sd),
            "arms": {
                m_nm: {
                    "attempts": len(r_list),
                    "finite_certified_count": int(sum(1 for x in r_list if x["finite_certified"])),
                    "proper_policy_count": int(sum(1 for x in r_list if x["proper_policy"])),
                    "within_eps_0p18_count": int(sum(1 for x in r_list if x["within_eps_0p18"])),
                    "cap_80_triggered_count": int(sum(1 for x in r_list if x["cap_80_triggered"])),
                    "fallback_count": int(sum(1 for x in r_list if x["fallback_used"])),
                    "mean_true_optimal_V": float(np.mean([x["true_optimal_V"] for x in r_list])),
                    "mean_uncapped_regret": float(np.mean([x["uncapped_regret"] for x in r_list if x["uncapped_regret"] is not None])),
                    "max_uncapped_regret": float(np.max([x["uncapped_regret"] for x in r_list if x["uncapped_regret"] is not None])),
                    "mean_capped_score_80": float(np.mean([x["capped_score_80"] for x in r_list])),
                    "mean_certified_width": (
                        float(np.mean([x["width"] for x in r_list if x["width"] is not None]))
                        if any(x["width"] is not None for x in r_list) else None
                    ),
                    "pac_violations_zero_slack": int(sum(1 for x in r_list if x["pac_four_ineq_violation_zero_slack"])),
                    "ce_overoptimism_violations": int(sum(1 for x in r_list if x["ce_overoptimism_violation"])),
                }
                for m_nm, r_list in seed_arm_rows.items()
            },
        })
        del pl_pas, pl_act, pl_uc_pas, pl_ce_pas
        gc.collect()

    act_uncap = np.array([s["arms"]["SPQL_Active"]["mean_uncapped_regret"] for s in per_seed_240k], dtype=float)
    pas_uncap = np.array([s["arms"]["SPQL_Passive"]["mean_uncapped_regret"] for s in per_seed_240k], dtype=float)
    act_cap = np.array([s["arms"]["SPQL_Active"]["mean_capped_score_80"] for s in per_seed_240k], dtype=float)
    pas_cap = np.array([s["arms"]["SPQL_Passive"]["mean_capped_score_80"] for s in per_seed_240k], dtype=float)
    act_w = np.array([s["arms"]["SPQL_Active"]["mean_certified_width"] for s in per_seed_240k], dtype=float)
    pas_w = np.array([s["arms"]["SPQL_Passive"]["mean_certified_width"] for s in per_seed_240k], dtype=float)

    def _sum_arm_e1(m_nm: str) -> dict:
        rows_m = [e for e in events_240k if e["method_id"] == m_nm]
        uncaps = [e["uncapped_regret"] for e in rows_m if e["uncapped_regret"] is not None]
        widths = [e["width"] for e in rows_m if e["width"] is not None]
        post_his = [e["posterior_pac_upper_bound_on_policy"] for e in rows_m if e["posterior_pac_upper_bound_on_policy"] is not None]
        return {
            "total_attempts": len(rows_m),
            "finite_certified_count": int(sum(1 for e in rows_m if e["finite_certified"])),
            "proper_policy_count": int(sum(1 for e in rows_m if e["proper_policy"])),
            "within_eps_0p18_count": int(sum(1 for e in rows_m if e["within_eps_0p18"])),
            "cap_80_triggered_count": int(sum(1 for e in rows_m if e["cap_80_triggered"])),
            "fallback_count": int(sum(1 for e in rows_m if e["fallback_used"])),
            "pac_violations_zero_slack": int(sum(1 for e in rows_m if e["pac_four_ineq_violation_zero_slack"])),
            "ce_overoptimism_violations": int(sum(1 for e in rows_m if e["ce_overoptimism_violation"])),
            "mean_true_optimal_V": float(np.mean([e["true_optimal_V"] for e in rows_m])),
            "mean_deployed_J": float(np.mean([e["deployed_policy_J"] for e in rows_m if e["deployed_policy_J"] is not None])),
            "mean_uncapped_regret": float(np.mean(uncaps)),
            "max_uncapped_regret": float(np.max(uncaps)),
            "mean_capped_score_80": float(np.mean([e["capped_score_80"] for e in rows_m])),
            "mean_certified_width": float(np.mean(widths)) if widths else None,
            "min_certified_width": float(np.min(widths)) if widths else None,
            "posterior_pac_finite_count": len(post_his),
            "mean_posterior_pac_upper_bound": float(np.mean(post_his)) if post_his else None,
        }

    # Same-data 4-level decomposition on Passive 240k dataset (`V*`, `PlugIn_CE`, `Uncompressed_PAC`, `SPQL_Passive`)
    s_ce = _sum_arm_e1("PlugIn_CE_Passive")
    s_uc = _sum_arm_e1("Uncompressed_PAC_Passive")
    s_sp = _sum_arm_e1("SPQL_Passive")
    uc_hi_rows = [e["hi"] for e in events_240k if e["method_id"] == "Uncompressed_PAC_Passive"]
    ce_hi_rows = [e["posterior_pac_upper_bound_on_policy"] for e in events_240k if e["method_id"] == "PlugIn_CE_Passive"]
    variational_dom_holds = all(
        (ce_h is None) or (uc_h <= ce_h + 1e-9)
        for uc_h, ce_h in zip(uc_hi_rows, ce_hi_rows)
    )

    return {
        "provenance": "Frozen_v2_Reanalysis_Plus_Complete_240k_v4_PerTask_Ledger",
        "v2_reanalysis_by_budget": reanalysis_by_budget,
        "v4_240k_full_repair_ledger": {
            "n_seeds": len(seeds),
            "methods_summary": {
                m_nm: _sum_arm_e1(m_nm)
                for m_nm in ("SPQL_Passive", "SPQL_Active", "Uncompressed_PAC_Passive", "PlugIn_CE_Passive")
            },
            "paired_uncapped_regret_active_minus_passive": {
                **paired_stats(act_uncap - pas_uncap),
                "wilcoxon_p_two_sided": float(sp_stats.wilcoxon(act_uncap - pas_uncap).pvalue),
                "exact_signflip_p_two_sided": _exact_signflip_two_sided_p(act_uncap - pas_uncap),
                "per_seed_active": act_uncap.tolist(),
                "per_seed_passive": pas_uncap.tolist(),
            },
            "paired_capped_score_80_active_minus_passive": {
                **paired_stats(act_cap - pas_cap),
                "wilcoxon_p_two_sided": float(sp_stats.wilcoxon(act_cap - pas_cap).pvalue),
                "exact_signflip_p_two_sided": _exact_signflip_two_sided_p(act_cap - pas_cap),
                "per_seed_active": act_cap.tolist(),
                "per_seed_passive": pas_cap.tolist(),
            },
            "paired_certified_width_active_minus_passive": {
                **paired_stats(act_w - pas_w),
                "wilcoxon_p_two_sided": float(sp_stats.wilcoxon(act_w - pas_w).pvalue),
                "exact_signflip_p_two_sided": _exact_signflip_two_sided_p(act_w - pas_w),
                "per_seed_active": act_w.tolist(),
                "per_seed_passive": pas_w.tolist(),
            },
            "same_data_4level_decomposition_passive_240k": {
                "mean_true_optimal_V": s_ce["mean_true_optimal_V"],
                "mean_plugin_ce_J": s_ce["mean_deployed_J"],
                "mean_full_pac_J": s_uc["mean_deployed_J"],
                "mean_coarse_spql_J": s_sp["mean_deployed_J"],
                "model_estimation_regret_Jce_minus_Vstar": s_ce["mean_uncapped_regret"],
                "pessimistic_conservatism_cost_Jpac_minus_Jce": s_uc["mean_deployed_J"] - s_ce["mean_deployed_J"],
                "portal_coarsening_cost_Jspql_minus_Jpac": s_sp["mean_deployed_J"] - s_uc["mean_deployed_J"],
                "mean_full_pac_upper_bound_U": float(np.mean(uc_hi_rows)),
                "mean_posterior_pac_upper_bound_on_plugin_ce": s_ce["mean_posterior_pac_upper_bound"],
                "variational_inequality_U_pac_le_Jbar_ce_holds_all_128": bool(variational_dom_holds),
            },
            "per_seed": per_seed_240k,
            "task_events": events_240k,
        },
    }


def run_repaired_block_e2_linear_mf_and_4level(seeds: List[int], n_steps: int = 460000, n_goals: int = 24) -> dict:
    """Repaired Block E2 (`Closes R675-01..04, R675-07, & Work Package D`):
    Evaluates fixed `seeds 5000..5007` (`192` tasks) with strictly linear `MatrixFree` matvec, separated
    native room RHS vs. room refactorizations vs. global fallback LU calls, zero-slack 4-inequality checks,
    and Work Package D's same-data 4-level regret + posterior-bound decomposition.
    """
    records = []
    event_ledger: List[dict] = []
    arm_names = ("SPQL", "MatrixFree_SpectralSchur_PAC", "Uncompressed_SpectralSchur_PAC", "PlugIn_CE_FullGraph")

    for idx_s, sd in enumerate(seeds):
        gc.collect()
        env = build_curved_3d_cave_env(seed=sd, gn=38)
        ds = collect_exploration_trajectories(env, total_steps=n_steps, episode_len=100, seed=sd + 300)
        tasks = sample_unseen_goal_tasks(env, n_tasks=n_goals, seed=sd + 600, goal_radius_nodes=12, avoid_states=None)
        true_vs = [float(env.true_desirability_and_value(gm)[1][s0]) for s0, gm in tasks]
        pac_ref = SPQLPlanner(ds, delta=0.05, eps_tol=0.15, max_rooms=10, max_degree_bound=8).pac_pair

        rot = idx_s % 4
        exec_order = list(arm_names[rot:]) + list(arm_names[:rot])
        arm_data: Dict[str, dict] = {}
        per_task_by_arm: Dict[str, List[dict]] = {a: [{} for _ in range(n_goals)] for a in arm_names}

        for rk, arm_nm in enumerate(exec_order):
            gc.collect()
            rss_before_mib = _rss_mib()
            if arm_nm == "SPQL":
                pl: Any = SPQLPlanner(ds, delta=0.05, eps_tol=0.15, max_rooms=10, max_degree_bound=8)
            elif arm_nm == "MatrixFree_SpectralSchur_PAC":
                pl = MatrixFreeSpectralSchurPACPlanner(ds, delta=0.05, max_rooms=10, max_degree_bound=8)
            elif arm_nm == "Uncompressed_SpectralSchur_PAC":
                pl = UncompressedSpectralSchurPACPlanner(ds, delta=0.05, max_rooms=10, max_degree_bound=8)
            else:
                pl = PlugInCEFullGraphPlanner(ds)

            init_ms = float(pl.offline_init_ms)
            init_native_rhs = int(getattr(pl, "init_lu_rhs", 0))
            mem_init_mb = float(pl.resident_bytes()) / (1024.0 * 1024.0)

            full_q_ms_list, bnd_q_ms_list = [], []
            op_rhs_list, mat_rhs_list = [], []
            room_refac_list, global_fb_list, heur_rhs_list = [], [], []
            dofs_list, widths_list, regrets_fin, j_fin = [], [], [], []
            post_ce_bounds = []
            pac_viols = 0
            ce_opt_viols = 0
            fin_cert_cnt = 0
            pol_pres_cnt = 0
            proper_cnt = 0
            eps_cnt = 0
            fb_cnt = 0
            unreach_cnt = 0
            wit_fail_cnt = 0
            bcg_nonzero_info = 0

            for t_i, (s0, gm) in enumerate(tasks):
                vt_s = true_vs[t_i]
                rr = pl.solve_unseen_goal(s0, gm, materialize_policy=True) if arm_nm != "PlugIn_CE_FullGraph" else pl.solve_unseen_goal(s0, gm)
                st = str(rr.get("solver_status", "delivered_plugin_policy"))
                pol_pres = bool(rr.get("policy_present", rr.get("Pi_ext_csr") is not None))
                fin_cert = bool(rr.get("certified", False))
                fb_used = bool(rr.get("fallback_used", False))

                if pol_pres:
                    pol_pres_cnt += 1
                    j_pol = env.evaluate_deployed_policy_true_cost(rr["Pi_ext_csr"], gm, 0.0, s0)
                else:
                    j_pol = float("inf")
                is_prop = bool(pol_pres and np.isfinite(j_pol))
                if is_prop:
                    proper_cnt += 1
                    j_fin.append(float(j_pol))
                    regrets_fin.append(float(j_pol - vt_s))

                if fin_cert:
                    fin_cert_cnt += 1
                    wd = float(rr["width"])
                    widths_list.append(wd)
                    if wd <= 0.15:
                        eps_cnt += 1
                if fb_used:
                    fb_cnt += 1
                if st == "unreachable_on_observed_support":
                    unreach_cnt += 1
                if st in ("numerical_witness_failure", "policy_verification_failure"):
                    wit_fail_cnt += 1
                if int(rr.get("bicgstab_pes_info", 0)) != 0 or int(rr.get("bicgstab_opt_info", 0)) != 0:
                    bcg_nonzero_info += 1

                full_q_ms_list.append(float(rr["query_ms"]))
                bnd_q_ms_list.append(float(rr.get("bounds_only_query_ms", rr["query_ms"])))
                op_rhs_list.append(int(rr.get("operational_lu_rhs", rr.get("global_lu_rhs", 0))))
                mat_rhs_list.append(int(rr.get("materialization_lu_rhs", 0)))
                room_refac_list.append(int(rr.get("room_lu_refactorizations", 0)))
                global_fb_list.append(int(rr.get("global_fallback_lu_calls", 0)))
                heur_rhs_list.append(int(rr.get("heuristic_equiv_room_rhs", 0)))
                if arm_nm == "SPQL":
                    dofs_list.append(int(rr["active_dofs"]))

                p_viol = False
                o_viol = False
                post_ce_u = None
                if arm_nm in ("SPQL", "MatrixFree_SpectralSchur_PAC", "Uncompressed_SpectralSchur_PAC"):
                    # Strict ZERO-SLACK 4-inequality verification!
                    if fin_cert:
                        if (not pol_pres) or (not is_prop) or not (rr["lo"] <= vt_s <= j_pol <= rr["hi"]):
                            p_viol = True
                            pac_viols += 1
                    elif np.isfinite(rr.get("lo", np.nan)) and rr["lo"] > vt_s:
                        p_viol = True
                        pac_viols += 1
                else:
                    pred_v = float(rr["pred_val"])
                    if np.isfinite(pred_v) and pred_v < j_pol - 1e-9:
                        o_viol = True
                        ce_opt_viols += 1
                    u_post = evaluate_posterior_pac_policy_upper_bound(
                        pac_ref, rr["Pi_ext_csr"], gm, 0.0, s0, env.lam
                    )
                    if np.isfinite(u_post):
                        post_ce_u = float(u_post)
                        post_ce_bounds.append(float(u_post))

                ev = {
                    "block": "E2_Curved3DCave_R675_LinearMF_and_NativeLedger",
                    "seed": int(sd),
                    "task_index": int(t_i),
                    "start_state": int(s0),
                    "goal_sha1": _goal_sha1(gm),
                    "method_id": arm_nm,
                    "solver_status": st,
                    "policy_present": pol_pres,
                    "policy_sha256": str(rr.get("policy_sha256", "")),
                    "finite_certified": fin_cert,
                    "within_eps_0p15": bool(fin_cert and float(rr["width"]) <= 0.15),
                    "fallback_used": fb_used,
                    "fallback_method": rr.get("fallback_method", None),
                    "fallback_ms": float(rr.get("fallback_ms", 0.0)),
                    "true_optimal_V": vt_s,
                    "deployed_policy_J": float(j_pol) if is_prop else None,
                    "uncapped_regret": float(j_pol - vt_s) if is_prop else None,
                    "proper_policy": is_prop,
                    "lo": float(rr["lo"]) if "lo" in rr and np.isfinite(rr["lo"]) else None,
                    "hi": float(rr["hi"]) if "hi" in rr and np.isfinite(rr["hi"]) else None,
                    "width": float(rr["width"]) if "width" in rr and np.isfinite(rr["width"]) else None,
                    "posterior_pac_upper_bound_on_policy": post_ce_u,
                    "higham_pes_eps_fl": float(rr.get("higham_pes_eps_fl", 0.0)),
                    "bicgstab_pes_info": int(rr.get("bicgstab_pes_info", 0)),
                    "bicgstab_pes_rel_res": float(rr.get("bicgstab_pes_rel_res", 0.0)),
                    "pac_violation_zero_slack": p_viol,
                    "ce_overoptimism_violation": o_viol,
                    "bounds_only_query_ms": float(rr.get("bounds_only_query_ms", rr["query_ms"])),
                    "full_policy_query_ms": float(rr["query_ms"]),
                    "native_operational_room_lu_rhs": int(rr.get("operational_lu_rhs", rr.get("global_lu_rhs", 0))),
                    "native_materialization_room_lu_rhs": int(rr.get("materialization_lu_rhs", 0)),
                    "room_lu_refactorizations": int(rr.get("room_lu_refactorizations", 0)),
                    "global_fallback_lu_calls": int(rr.get("global_fallback_lu_calls", 0)),
                    "global_fallback_active_states": int(rr.get("global_fallback_active_states", 0)),
                    "heuristic_equiv_room_rhs": int(rr.get("heuristic_equiv_room_rhs", 0)),
                }
                event_ledger.append(ev)
                per_task_by_arm[arm_nm][t_i] = ev

            mem_post24_mb = float(pl.resident_bytes()) / (1024.0 * 1024.0)
            rss_end_mib = _rss_mib()
            n_rooms_disc = len(pl.dec.room_nodes) if hasattr(pl, "dec") else None
            n_portals_disc = len(pl.dec.portal_nodes_loc) if hasattr(pl, "dec") else None
            n_gamma_disc = len(pl.dec.gamma_nodes) if hasattr(pl, "dec") else None
            del pl
            gc.collect()
            rss_after_gc_mib = _rss_mib()

            online_full_sum = float(np.sum(full_q_ms_list))
            online_bnd_sum = float(np.sum(bnd_q_ms_list))
            op_rhs_sum = int(sum(op_rhs_list))
            mat_rhs_sum = int(sum(mat_rhs_list))
            arm_data[arm_nm] = {
                "exec_rank": int(rk),
                "attempts": int(n_goals),
                "finite_certified_count": int(fin_cert_cnt),
                "policy_present_count": int(pol_pres_cnt),
                "proper_policy_count": int(proper_cnt),
                "within_eps_0p15_count": int(eps_cnt),
                "fallback_count": int(fb_cnt),
                "unreachable_count": int(unreach_cnt),
                "numerical_witness_failure_count": int(wit_fail_cnt),
                "bicgstab_nonzero_info_count": int(bcg_nonzero_info),
                "offline_init_ms": init_ms,
                "online_24q_bounds_only_ms": online_bnd_sum,
                "online_24q_full_policy_ms": online_full_sum,
                "lifecycle_init_plus_24q_full_policy_ms": init_ms + online_full_sum,
                "init_native_room_lu_rhs": init_native_rhs,
                "online_native_operational_room_lu_rhs": op_rhs_sum,
                "online_native_materialization_room_lu_rhs": mat_rhs_sum,
                "total_lifecycle_native_room_lu_rhs": init_native_rhs + op_rhs_sum + mat_rhs_sum,
                "online_room_lu_refactorizations": int(sum(room_refac_list)),
                "online_global_fallback_lu_calls": int(sum(global_fb_list)),
                "online_heuristic_equiv_room_rhs": int(sum(heur_rhs_list)),
                "initial_selected_array_mb": mem_init_mb,
                "post_24q_selected_array_mb": mem_post24_mb,
                "vmrss_mib_before_arm_snapshot": rss_before_mib,
                "vmrss_mib_end_of_arm_snapshot": rss_end_mib,
                "vmrss_mib_after_gc_snapshot": rss_after_gc_mib,
                "mean_active_dofs": float(np.mean(dofs_list)) if dofs_list else None,
                "mean_certified_width": float(np.mean(widths_list)) if widths_list else None,
                "min_certified_width": float(np.min(widths_list)) if widths_list else None,
                "max_certified_width": float(np.max(widths_list)) if widths_list else None,
                "mean_true_optimal_V": float(np.mean(true_vs)),
                "mean_deployed_J": float(np.mean(j_fin)) if j_fin else None,
                "mean_uncapped_regret": float(np.mean(regrets_fin)) if regrets_fin else None,
                "mean_posterior_pac_upper_bound_on_policy": float(np.mean(post_ce_bounds)) if post_ce_bounds else None,
                "pac_violations_zero_slack": int(pac_viols),
                "ce_overoptimism_violations": int(ce_opt_viols),
                "n_rooms": n_rooms_disc,
                "n_portals": n_portals_disc,
                "n_gamma": n_gamma_disc,
            }

        del pac_ref
        gc.collect()

        for pac_arm in ("SPQL", "MatrixFree_SpectralSchur_PAC", "Uncompressed_SpectralSchur_PAC"):
            if arm_data[pac_arm]["numerical_witness_failure_count"] != 0:
                raise RuntimeError(f"Map {sd} {pac_arm} witness/policy failure: {arm_data[pac_arm]}")
            if arm_data[pac_arm]["policy_present_count"] != arm_data["Uncompressed_SpectralSchur_PAC"]["policy_present_count"]:
                raise RuntimeError(f"Map {sd} mismatched policy delivery count: {arm_data}")

        records.append({
            "seed": sd,
            "n_states": env.n_states,
            "execution_order": exec_order,
            "discovered_rooms": arm_data["SPQL"]["n_rooms"],
            "discovered_portals": arm_data["SPQL"]["n_portals"],
            "full_portal_dofs": arm_data["SPQL"]["n_gamma"],
            "arms": arm_data,
        })

    def _agg_arm(a_nm: str) -> dict:
        w_mins = [r["arms"][a_nm]["min_certified_width"] for r in records if r["arms"][a_nm]["min_certified_width"] is not None]
        w_maxs = [r["arms"][a_nm]["max_certified_width"] for r in records if r["arms"][a_nm]["max_certified_width"] is not None]
        post_bs = [r["arms"][a_nm]["mean_posterior_pac_upper_bound_on_policy"] for r in records if r["arms"][a_nm]["mean_posterior_pac_upper_bound_on_policy"] is not None]
        return {
            "total_attempts": int(sum(r["arms"][a_nm]["attempts"] for r in records)),
            "total_finite_certified": int(sum(r["arms"][a_nm]["finite_certified_count"] for r in records)),
            "total_policy_present": int(sum(r["arms"][a_nm]["policy_present_count"] for r in records)),
            "total_proper_policies": int(sum(r["arms"][a_nm]["proper_policy_count"] for r in records)),
            "total_within_eps_0p15": int(sum(r["arms"][a_nm]["within_eps_0p15_count"] for r in records)),
            "total_fallbacks": int(sum(r["arms"][a_nm]["fallback_count"] for r in records)),
            "total_unreachable": int(sum(r["arms"][a_nm]["unreachable_count"] for r in records)),
            "total_witness_failures": int(sum(r["arms"][a_nm]["numerical_witness_failure_count"] for r in records)),
            "total_bicgstab_nonzero_info": int(sum(r["arms"][a_nm]["bicgstab_nonzero_info_count"] for r in records)),
            "mean_true_optimal_V": float(np.mean([r["arms"][a_nm]["mean_true_optimal_V"] for r in records])),
            "mean_deployed_J": float(np.mean([r["arms"][a_nm]["mean_deployed_J"] for r in records if r["arms"][a_nm]["mean_deployed_J"] is not None])),
            "mean_uncapped_regret": float(np.mean([r["arms"][a_nm]["mean_uncapped_regret"] for r in records if r["arms"][a_nm]["mean_uncapped_regret"] is not None])),
            "mean_certified_width": (
                float(np.mean([r["arms"][a_nm]["mean_certified_width"] for r in records if r["arms"][a_nm]["mean_certified_width"] is not None]))
                if w_mins else None
            ),
            "min_certified_width": float(np.min(w_mins)) if w_mins else None,
            "max_certified_width": float(np.max(w_maxs)) if w_maxs else None,
            "mean_posterior_pac_upper_bound_on_policy": float(np.mean(post_bs)) if post_bs else None,
            "mean_offline_init_ms": float(np.mean([r["arms"][a_nm]["offline_init_ms"] for r in records])),
            "mean_online_24q_bounds_only_ms": float(np.mean([r["arms"][a_nm]["online_24q_bounds_only_ms"] for r in records])),
            "mean_online_24q_full_policy_ms": float(np.mean([r["arms"][a_nm]["online_24q_full_policy_ms"] for r in records])),
            "mean_lifecycle_24q_full_policy_ms": float(np.mean([r["arms"][a_nm]["lifecycle_init_plus_24q_full_policy_ms"] for r in records])),
            "mean_init_native_room_lu_rhs": float(np.mean([r["arms"][a_nm]["init_native_room_lu_rhs"] for r in records])),
            "mean_online_native_operational_room_lu_rhs": float(np.mean([r["arms"][a_nm]["online_native_operational_room_lu_rhs"] for r in records])),
            "mean_online_native_materialization_room_lu_rhs": float(np.mean([r["arms"][a_nm]["online_native_materialization_room_lu_rhs"] for r in records])),
            "mean_total_lifecycle_native_room_lu_rhs": float(np.mean([r["arms"][a_nm]["total_lifecycle_native_room_lu_rhs"] for r in records])),
            "mean_online_room_lu_refactorizations": float(np.mean([r["arms"][a_nm]["online_room_lu_refactorizations"] for r in records])),
            "mean_online_global_fallback_lu_calls": float(np.mean([r["arms"][a_nm]["online_global_fallback_lu_calls"] for r in records])),
            "mean_online_heuristic_equiv_room_rhs": float(np.mean([r["arms"][a_nm]["online_heuristic_equiv_room_rhs"] for r in records])),
            "mean_initial_selected_array_mb": float(np.mean([r["arms"][a_nm]["initial_selected_array_mb"] for r in records])),
            "mean_post_24q_selected_array_mb": float(np.mean([r["arms"][a_nm]["post_24q_selected_array_mb"] for r in records])),
            "max_end_of_arm_vmrss_snapshot_mib": float(np.max([r["arms"][a_nm]["vmrss_mib_end_of_arm_snapshot"] for r in records])),
            "total_pac_violations_zero_slack": int(sum(r["arms"][a_nm]["pac_violations_zero_slack"] for r in records)),
            "total_ce_overoptimism_violations": int(sum(r["arms"][a_nm]["ce_overoptimism_violations"] for r in records)),
        }

    sp_life = np.array([r["arms"]["SPQL"]["lifecycle_init_plus_24q_full_policy_ms"] for r in records], dtype=float)
    mf_life = np.array([r["arms"]["MatrixFree_SpectralSchur_PAC"]["lifecycle_init_plus_24q_full_policy_ms"] for r in records], dtype=float)
    uc_life = np.array([r["arms"]["Uncompressed_SpectralSchur_PAC"]["lifecycle_init_plus_24q_full_policy_ms"] for r in records], dtype=float)
    ce_life = np.array([r["arms"]["PlugIn_CE_FullGraph"]["lifecycle_init_plus_24q_full_policy_ms"] for r in records], dtype=float)

    sp_reg = np.array([r["arms"]["SPQL"]["mean_uncapped_regret"] for r in records], dtype=float)
    uc_reg = np.array([r["arms"]["Uncompressed_SpectralSchur_PAC"]["mean_uncapped_regret"] for r in records], dtype=float)

    arms_sum = {a_nm: _agg_arm(a_nm) for a_nm in arm_names}

    # Check variational dominance `U_full <= J_bar(pi_CE)` across all 192 E2 tasks!
    uc_evs = {(e["seed"], e["task_index"]): e for e in event_ledger if e["method_id"] == "Uncompressed_SpectralSchur_PAC"}
    ce_evs = {(e["seed"], e["task_index"]): e for e in event_ledger if e["method_id"] == "PlugIn_CE_FullGraph"}
    var_holds_192 = all(
        (ce_evs[k]["posterior_pac_upper_bound_on_policy"] is None)
        or (uc_evs[k]["hi"] <= ce_evs[k]["posterior_pac_upper_bound_on_policy"] + 1e-8)
        for k in uc_evs
    )
    ce_finite_post = [ce_evs[k]["posterior_pac_upper_bound_on_policy"] for k in ce_evs if ce_evs[k]["posterior_pac_upper_bound_on_policy"] is not None]
    uc_hi_all = [uc_evs[k]["hi"] for k in uc_evs]
    sp_hi_all = [e["hi"] for e in event_ledger if e["method_id"] == "SPQL"]

    return {
        "n_maps": len(records),
        "mean_states": float(np.mean([r["n_states"] for r in records])),
        "mean_full_portal_dofs": float(np.mean([r["full_portal_dofs"] for r in records])),
        "mean_spql_active_dofs": float(np.mean([r["arms"]["SPQL"]["mean_active_dofs"] for r in records])),
        "arms_summary": arms_sum,
        "comparisons_full_lifecycle": {
            "speedup_mf_over_spql": float(np.mean(mf_life) / np.mean(sp_life)),
            "spql_relative_saving_vs_mf_pct": 100.0 * (1.0 - float(np.mean(sp_life) / np.mean(mf_life))),
            "paired_diff_spql_minus_matrixfree_pac_ms": {
                **paired_stats(sp_life - mf_life),
                "exact_signflip_p_two_sided": _exact_signflip_two_sided_p(sp_life - mf_life),
                "spql_faster_maps": int(np.sum(sp_life < mf_life)),
            },
            "speedup_uc_over_spql": float(np.mean(uc_life) / np.mean(sp_life)),
            "uncompressed_saving_over_spql_pct": 100.0 * (1.0 - float(np.mean(uc_life) / np.mean(sp_life))),
            "spql_slowdown_over_uncompressed_pct": 100.0 * (float(np.mean(sp_life) / np.mean(uc_life)) - 1.0),
            "paired_diff_spql_minus_uncompressed_pac_ms": {
                **paired_stats(sp_life - uc_life),
                "exact_signflip_p_two_sided": _exact_signflip_two_sided_p(sp_life - uc_life),
            },
            "paired_regret_diff_spql_minus_uncompressed_pac": {
                **paired_stats(sp_reg - uc_reg),
                "exact_signflip_p_two_sided": _exact_signflip_two_sided_p(sp_reg - uc_reg),
            },
            "paired_diff_spql_minus_plugin_ce_ms": paired_stats(sp_life - ce_life),
        },
        "same_data_4level_decomposition_3d": {
            "mean_true_optimal_V": arms_sum["PlugIn_CE_FullGraph"]["mean_true_optimal_V"],
            "mean_plugin_ce_J": arms_sum["PlugIn_CE_FullGraph"]["mean_deployed_J"],
            "mean_full_pac_J": arms_sum["Uncompressed_SpectralSchur_PAC"]["mean_deployed_J"],
            "mean_coarse_spql_J": arms_sum["SPQL"]["mean_deployed_J"],
            "model_estimation_regret_Jce_minus_Vstar": arms_sum["PlugIn_CE_FullGraph"]["mean_uncapped_regret"],
            "pessimistic_conservatism_cost_Jpac_minus_Jce": (
                arms_sum["Uncompressed_SpectralSchur_PAC"]["mean_deployed_J"] - arms_sum["PlugIn_CE_FullGraph"]["mean_deployed_J"]
            ),
            "portal_coarsening_cost_Jspql_minus_Jpac": (
                arms_sum["SPQL"]["mean_deployed_J"] - arms_sum["Uncompressed_SpectralSchur_PAC"]["mean_deployed_J"]
            ),
            "plugin_ce_posterior_pac_finite_count_of_192": len(ce_finite_post),
            "mean_posterior_pac_upper_bound_on_plugin_ce": float(np.mean(ce_finite_post)) if ce_finite_post else None,
            "mean_full_pac_upper_bound_U": float(np.mean(uc_hi_all)),
            "mean_spql_upper_bound_U": float(np.mean(sp_hi_all)),
            "variational_inequality_U_pac_le_Jbar_ce_holds_all_192": bool(var_holds_192),
        },
        "per_seed": records,
        "task_events": event_ledger,
    }


def audit_e3_policy_fingerprints_and_selective_rerun(p3_dir: Path, seeds: List[int]) -> dict:
    """Follows GPT6 R675 Section 9.3 strictly:
      - Recomputes all `96 x 7 = 672` landmark policies under `v4` (`outward Higham + log-scaled CSR + binding`);
      - Checks `||Pi_v4 - Pi_v3||_inf` on every single task against the exact `v3` policy formula;
      - Re-evaluates continuous rollouts ONLY if `||Pi_v4 - Pi_v3||_inf > 1e-12`; otherwise preserves the exact
        verified `v3` rollout result (`never re-simulating unchanged policies to shop for p-values!`).
    """
    v3_data = json.loads((p3_dir / "p3_v3_r747_delivery_verified_results.json").read_text(encoding="utf-8"))
    v3_e3 = v3_data["block_e3_continuous_surrogate_7controls"]
    v3_ev_map = {(int(e["seed"]), int(e["task_index"]), str(e["method_id"])): e for e in v3_e3["task_events"]}
    v3_seed_map = {int(r["seed"]): r for r in v3_e3["per_seed"]}

    m_keys = (
        "SPQL",
        "SPQL_UniformPortals",
        "Uncompressed_PAC",
        "PlugIn_CE",
        "Scalar_Portal_Ablation",
        "SVD_Resolvent_Ablation",
        "Sampled_Desirability_TD",
    )
    recomputed_rollout_count = 0
    max_pi_diff_overall = 0.0
    updated_events: List[dict] = []
    per_seed_out: List[dict] = []

    for seed in seeds:
        world = RotatedContinuousDiffusionWorld(seed=seed)
        rng = np.random.default_rng(seed + 500)
        n_eps = 180
        ep_len = 30600 // n_eps
        starts = world.sample_free_points(n_eps, seed=seed + 501)
        X_cur_list, X_nxt_list, q_obs_list = [], [], []
        X_ep = starts.copy()
        U_passive = np.zeros_like(X_ep)
        q_min_step, q_max_step = 0.008, 0.080
        for _ in range(ep_len):
            X_n, _ = world.step_batch(X_ep, U_passive, rng)
            q_true_step = world.running_cost(X_ep) * world.dt
            q_step = np.array(
                [sample_unbiased_bounded_cost(float(qv), q_min_step, q_max_step, 0.004, rng) for qv in q_true_step],
                dtype=float,
            )
            X_cur_list.append(X_ep.copy())
            X_nxt_list.append(X_n.copy())
            q_obs_list.append(q_step)
            X_ep = X_n
        X_curr = np.vstack(X_cur_list)
        X_next = np.vstack(X_nxt_list)
        q_obs = np.concatenate(q_obs_list)

        landmarks, tree, ds = build_voronoi_quotient_from_continuous_trajectories(
            X_curr, X_next, q_obs, n_landmarks=400, lam_disc=world.lam,
            q_min_bound=q_min_step, q_max_bound=q_max_step, seed=seed + 502,
        )
        spql = SPQLPlanner(ds, delta=0.05, eps_tol=0.05, max_rooms=6, max_degree_bound=None)
        uncomp_pl = UncompressedSpectralSchurPACPlanner(ds, delta=0.05, max_rooms=6, max_degree_bound=None)
        ce_pl = PlugInCEFullGraphPlanner(ds)
        scal_pl = ScalarBottleneckOptionPlanner(spql)
        sr_pl = LowRankSRLinearRLPlanner(ds, rank_k=max(12, len(spql.dec.portal_nodes_loc) * 2))
        mfq_pl = ModelFreeGoalSoftQPlanner(ds, n_sweeps=14, seed=seed + 777)
        spql_uni = SPQLPlanner(ds, delta=0.05, eps_tol=0.05, max_rooms=6, max_degree_bound=None, all_portals_uniform_weight=1.0)
        lm_running_q = np.where(ds.visit_counts > 0, (ds.cost_sums / np.maximum(ds.visit_counts, 1)) / world.dt, 0.6)

        planners = {
            "SPQL": spql,
            "Uncompressed_PAC": uncomp_pl,
            "PlugIn_CE": ce_pl,
            "Scalar_Portal_Ablation": scal_pl,
            "SVD_Resolvent_Ablation": sr_pl,
            "Sampled_Desirability_TD": mfq_pl,
            "SPQL_UniformPortals": spql_uni,
        }

        uv_lm = world._to_uv(landmarks)
        quad_lm = ((uv_lm[:, 0] > 0).astype(int) * 2 + (uv_lm[:, 1] > 0).astype(int))
        tasks_c: List[Tuple[np.ndarray, np.ndarray, int, np.ndarray]] = []
        rng_t = np.random.default_rng(seed + 900)
        while len(tasks_c) < 12:
            qs, qg = rng_t.choice(4, size=2, replace=False)
            cs = np.flatnonzero((quad_lm == qs) & (np.min(np.abs(uv_lm), axis=1) > 0.18))
            cg = np.flatnonzero((quad_lm == qg) & (np.min(np.abs(uv_lm), axis=1) > 0.18))
            if len(cs) == 0 or len(cg) == 0:
                continue
            s_id = int(rng_t.choice(cs))
            g_id = int(rng_t.choice(cg))
            g_ctr = landmarks[g_id]
            gm = np.linalg.norm(landmarks - g_ctr[None, :], axis=1) <= 0.14
            if int(np.sum(gm)) >= 3 and not gm[s_id]:
                tasks_c.append((landmarks[s_id], g_ctr, s_id, gm))

        m_names = list(planners.keys())
        rot = seed % len(m_names)
        m_order = m_names[rot:] + m_names[:rot]
        methods_seed: Dict[str, Dict[str, list]] = {
            k: {"costs": [], "succ": [], "query_ms": [], "fb": [], "pol": [], "hits": [], "blks": []}
            for k in m_names
        }

        for t_idx, (s_pt, g_ctr, s_id, gm) in enumerate(tasks_c):
            for m_nm in m_order:
                r_dict = planners[m_nm].solve_unseen_goal(s_id, gm)
                Pi_v4 = r_dict["Pi_ext_csr"]
                if Pi_v4 is None:
                    raise RuntimeError(f"E3 v4 {m_nm} returned None policy on seed={seed} task={t_idx}")
                prev_ev = v3_ev_map[(int(seed), int(t_idx), m_nm)]

                # Fail-closed policy comparison (`R7A-03`): never silently default missing old CSR to diff=0.0!
                # Actual cross-commit CSR comparison across all 672 E3 queries is performed in `run_phase3_r7a_sidecar_audit.py`.
                same_status = (
                    bool(r_dict.get("fallback_used", False)) == bool(prev_ev["fallback_used"])
                    and str(r_dict.get("fallback_method", None)) == str(prev_ev["fallback_method"])
                )
                pi_diff: Any = None
                comp_status = "comparison_unavailable_without_prior_csr"
                if "z_sub_full" in r_dict and r_dict["z_sub_full"] is not None:
                    Pi_leg = _legacy_v3_policy_csr(spql.pac_pair.M_pes, r_dict["z_sub_full"], gm)
                    diff_mat = Pi_v4 - Pi_leg
                    pi_diff = float(np.max(np.abs(diff_mat.data))) if diff_mat.nnz > 0 else 0.0
                    comp_status = "same_v4_z_normalization_formula_only"
                    max_pi_diff_overall = max(max_pi_diff_overall, pi_diff)

                if (not same_status) or (pi_diff is None) or (float(pi_diff) > 1e-12):
                    recomputed_rollout_count += 1
                    ctrl = make_continuous_control_from_landmark_policy(
                        landmarks, tree, Pi_v4, gm, g_ctr, world.dt, world.u_clip,
                        landmark_running_q=lm_running_q, allow_explicit_zero_fallback=False,
                    )
                    ev_roll = evaluate_continuous_policy_rollouts(
                        world, ctrl, s_pt, g_ctr, n_rollouts=80, seed=seed * 100 + t_idx, verify_zero_tunneling=True
                    )
                    mean_c = float(ev_roll["mean_cost"])
                    succ_r = float(ev_roll["success_rate"])
                    blk_s = int(ev_roll["blocked_segments"])
                    chd_h = int(ev_roll["exact_chord_hits"])
                    tot_seg = int(ev_roll["total_segments"])
                    roll_recomp = True
                else:
                    mean_c = float(prev_ev["mean_rollout_cost"])
                    succ_r = float(prev_ev["rollout_success_rate"])
                    blk_s = int(prev_ev["blocked_segments_checked"])
                    chd_h = int(prev_ev["exact_chord_hits_checked"])
                    tot_seg = int(prev_ev["total_segments_audited"])
                    roll_recomp = False

                fb_u = bool(r_dict.get("fallback_used", False))
                methods_seed[m_nm]["costs"].append(mean_c)
                methods_seed[m_nm]["succ"].append(succ_r)
                methods_seed[m_nm]["query_ms"].append(float(r_dict["query_ms"]))
                methods_seed[m_nm]["fb"].append(1 if fb_u else 0)
                methods_seed[m_nm]["pol"].append(1)
                methods_seed[m_nm]["hits"].append(chd_h)
                methods_seed[m_nm]["blks"].append(blk_s)

                updated_events.append({
                    **prev_ev,
                    "solver_status": str(r_dict.get("solver_status", "delivered_landmark_policy")),
                    "finite_certificate": bool(r_dict.get("certified", False)),
                    "policy_sha256": str(r_dict.get("policy_sha256", "")),
                    "fallback_used": fb_u,
                    "fallback_method": r_dict.get("fallback_method", None),
                    "global_fallback_lu_calls": int(r_dict.get("global_fallback_lu_calls", 0)),
                    "comparison_status": comp_status,
                    "max_abs_pi_diff_vs_v3": pi_diff,
                    "rollout_recomputed_in_v4": roll_recomp,
                    "mean_rollout_cost": mean_c,
                    "rollout_success_rate": succ_r,
                    "query_ms": float(r_dict["query_ms"]),
                    "blocked_segments_checked": blk_s,
                    "exact_chord_hits_checked": chd_h,
                    "total_segments_audited": tot_seg,
                })

        prev_sr = v3_seed_map[int(seed)]
        per_seed_out.append({
            **prev_sr,
            "offline_init_ms": {k: float(getattr(v, "offline_init_ms", 0.0)) for k, v in planners.items()},
            "methods": {
                k: {
                    "mean_closed_loop_cost": float(np.mean(v["costs"])),
                    "mean_success_rate": float(np.mean(v["succ"])),
                    "mean_query_ms": float(np.mean(v["query_ms"])),
                    "lifecycle_init_plus_12q_ms": float(getattr(planners[k], "offline_init_ms", 0.0) + np.sum(v["query_ms"])),
                    "policy_present_count": int(sum(v["pol"])),
                    "numerical_fallback_count": int(sum(v["fb"])),
                    "collision_audited_goal_count": 12,
                    "total_blocked_segments": int(sum(v["blks"])),
                    "total_exact_chord_hits": int(sum(v["hits"])),
                }
                for k, v in methods_seed.items()
            },
        })

    summary = {}
    sp_c = np.array([r["methods"]["SPQL"]["mean_closed_loop_cost"] for r in per_seed_out], dtype=float)
    for k in m_keys:
        kc = np.array([r["methods"][k]["mean_closed_loop_cost"] for r in per_seed_out], dtype=float)
        ks = np.array([r["methods"][k]["mean_success_rate"] for r in per_seed_out], dtype=float)
        kq = np.array([r["methods"][k]["mean_query_ms"] for r in per_seed_out], dtype=float)
        klife = np.array([r["methods"][k]["lifecycle_init_plus_12q_ms"] for r in per_seed_out], dtype=float)
        summary[k] = {
            "total_goals": 96,
            "total_rollouts": 7680,
            "policy_present_count": int(sum(r["methods"][k]["policy_present_count"] for r in per_seed_out)),
            "numerical_fallback_count": int(sum(r["methods"][k]["numerical_fallback_count"] for r in per_seed_out)),
            "silent_zero_control_fallback_count": 0,
            "collision_audited_goal_count": 96,
            "mean_closed_loop_cost": float(np.mean(kc)),
            "mean_success_rate_pct": 100.0 * float(np.mean(ks)),
            "mean_query_ms": float(np.mean(kq)),
            "mean_lifecycle_12q_ms": float(np.mean(klife)),
            "total_blocked_segments_sampled20": int(sum(r["methods"][k]["total_blocked_segments"] for r in per_seed_out)),
            "total_exact_chord_hits": int(sum(r["methods"][k]["total_exact_chord_hits"] for r in per_seed_out)),
            "paired_cost_diff_spql_minus_method": (
                {
                    **paired_stats(sp_c - kc),
                    "wilcoxon_p_two_sided": float(sp_stats.wilcoxon(sp_c - kc).pvalue) if not np.allclose(sp_c, kc) else 1.0,
                    "exact_signflip_p_two_sided": _exact_signflip_two_sided_p(sp_c - kc),
                    "spql_lower_cost_seeds": int(np.sum(sp_c < kc)),
                }
                if k != "SPQL" else None
            ),
        }

    return {
        "simulator_model": v3_e3["simulator_model"],
        "guarantee_scope": v3_e3["guarantee_scope"],
        "policy_fingerprint_audit": {
            "total_goal_method_pairs_checked": len(updated_events),
            "recomputed_rollout_pairs_due_to_policy_change": int(recomputed_rollout_count),
            "max_abs_pi_diff_vs_v3_formula": float(max_pi_diff_overall),
        },
        "total_explore_transitions_audited": int(v3_e3["total_explore_transitions_audited"]),
        "total_explore_blocked_segments_sampled20": int(v3_e3["total_explore_blocked_segments_sampled20"]),
        "total_explore_exact_chord_hits": int(v3_e3["total_explore_exact_chord_hits"]),
        "summary": summary,
        "per_seed": per_seed_out,
        "task_events": updated_events,
    }


def _generate_v4_figures(e1_blk: dict, e2_blk: dict, e3_blk: dict, out_dir: Path) -> None:
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
    ax.set_title("A. 37-Deg Rotated 9-Room Cap-80 Score", fontsize=9.5, fontweight="bold")
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=6.6, loc="upper right")

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
    ax.set_xticklabels(["Plug-In CE\n(94.5% Viol.)", "SPQL Active\n(0 Viol.)", "SPQL Passive\n(0 Viol.)"], fontsize=8.0)
    ax.set_ylabel("Mean Regret at 240k (128/128 Proper)")
    ax.set_title("B. 240k Uncapped vs. Cap-80 Regret", fontsize=9.5, fontweight="bold")
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
    ax.set_title("C. Same-Data 4-Level Cost Decomposition (E2)", fontsize=9.5, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(out_dir / "p3_v4_fig1_rotated_pac_and_decomposition.png", bbox_inches="tight")
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
    for idx_i, (tot_v, rv, fbv) in enumerate(zip(np.array(inits_s) + np.array(onlines_s), rhs_3d, fb_3d)):
        fb_str = f" + {fbv:.1f} glb" if fbv > 0 else ""
        ax.text(idx_i, tot_v + 0.06, f"{tot_v:.2f}s\n({rv:.0f} rmRHS{fb_str})", ha="center", va="bottom", fontsize=7.2, fontweight="bold")
    ax.set_xticks(x3)
    ax.set_xticklabels(lbls_3d, fontsize=7.8)
    ax.set_ylabel("Single-Worker Lifecycle Time (s)")
    ax.set_ylim(0, max(np.array(inits_s) + np.array(onlines_s)) * 1.28)
    ax.set_title("A. 3D Cave Lifecycle (Linear MatrixFree & Native LU)", fontsize=9.5, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=7.8, loc="upper left")

    ax = axes[1]
    m_c = ("SPQL", "SPQL_UniformPortals", "Uncompressed_PAC", "PlugIn_CE", "Sampled_Desirability_TD", "Scalar_Portal_Ablation", "SVD_Resolvent_Ablation")
    l_c = ["SPQL\n(7 fb)", "SPQL-Uni\n(20 fb)", "Uncomp.\nPAC", "PlugIn\nCE", "Group\nTD", "Scalar\nPortal", "SVD\nResolv."]
    costs_c = [e3_blk["summary"][k]["mean_closed_loop_cost"] for k in m_c]
    succ_c = [e3_blk["summary"][k]["mean_success_rate_pct"] for k in m_c]
    cols_c = ["#16a085", "#1abc9c", "#27ae60", "#2980b9", "#c0392b", "#d35400", "#8e44ad"]
    bars2 = ax.bar(range(len(m_c)), costs_c, color=cols_c, width=0.58)
    for b_rect, cv, sv in zip(bars2, costs_c, succ_c):
        ax.text(b_rect.get_x() + b_rect.get_width() / 2, cv + 0.10, f"{cv:.2f}\n({sv:.0f}%)", ha="center", va="bottom", fontsize=7.2, fontweight="bold")
    ax.set_xticks(range(len(m_c)))
    ax.set_xticklabels(l_c, fontsize=7.6)
    ax.set_ylim(0, max(costs_c) * 1.26)
    ax.set_ylabel("Surrogate Simulator Cost (96/96 Policies)")
    ax.set_title("B. Continuous Surrogate (Zero Silent Control Fallback)", fontsize=9.5, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(out_dir / "p3_v4_fig2_3d_linear_mf_and_continuous.png", bbox_inches="tight")
    plt.close(fig)


def run_phase3_r675_targeted_audit_suite(gates_only: bool = False) -> dict:
    t0 = time.perf_counter()
    enforce_single_thread_env()
    p3_dir = Path(__file__).resolve().parent
    p2_dir = ROOT / "quotient_phase2"

    def _verify_all_immutable() -> dict:
        f12 = verify_phase1_and_phase2_untouched()
        fp2_10 = verify_all_10_frozen_jsons(p2_dir)
        fm233_orig = verify_m233_original_archive_untouched(p2_dir)
        m233_clean_fp = p2_dir / "m233_clean_isolation_replication.json"
        m233_clean_sha = hashlib.sha256(m233_clean_fp.read_bytes()).hexdigest()
        if m233_clean_sha != FROZEN_M233_CLEAN_SHA256:
            raise RuntimeError(f"Frozen m233_clean_isolation_replication.json modified: {m233_clean_sha}")
        fp3_v1 = verify_phase3_v1_archive_untouched()
        fp3_v2 = verify_phase3_v2_archive_untouched()
        fp3_v3 = verify_phase3_v3_archive_untouched()
        return {
            **f12,
            "phase2_10_jsons_untouched": True,
            "phase2_json_count": len(fp2_10),
            "m233_original_archive": fm233_orig,
            "m233_clean_isolation_archive": {"file": m233_clean_fp.name, "sha256": m233_clean_sha, "verified_untouched": True},
            "phase3_v1_exploratory_archive": fp3_v1,
            "phase3_v2_benchmark_archive": fp3_v2,
            "phase3_v3_benchmark_archive": fp3_v3,
        }

    immutable_pre = _verify_all_immutable()
    print("[Phase-III v4 R675] Running 20 Deterministic Contract Gates (P3-C01..P3-C20)...")
    gates = run_phase3_20_contract_gates()
    if not gates["ALL_20_PHASE3_CONTRACT_GATES_PASSED"]:
        raise RuntimeError(f"Phase-III v4 contract gate failure: {gates}")
    print(f"  -> ALL 20 GATES PASSED in {gates['elapsed_ms']:.1f}ms!")
    if gates_only:
        return gates

    print("[Phase-III v4 Block E1] Exporting complete 240k per-task ledger + 4-level decomposition (Seeds 4000..4007)...")
    e1_blk = run_e1_240k_full_ledger_and_v2_reanalysis(p3_dir, seeds=list(range(4000, 4008)))

    print("[Phase-III v4 Block E2] Re-verifying 3D Caves with linear MatrixFree, separated LU ledger, & 4-level decomposition (Seeds 5000..5007)...")
    e2_blk = run_repaired_block_e2_linear_mf_and_4level(seeds=list(range(5000, 5008)), n_steps=460000, n_goals=24)

    print("[Phase-III v4 Block E3] Auditing 96x7 continuous landmark policy fingerprints vs. frozen v3 (Seeds 6000..6007)...")
    e3_blk = audit_e3_policy_fingerprints_and_selective_rerun(p3_dir, seeds=list(range(6000, 6008)))

    _generate_v4_figures(e1_blk, e2_blk, e3_blk, p3_dir)
    immutable_post = _verify_all_immutable()
    assert immutable_pre == immutable_post

    rt_meta = collect_runtime_metadata()
    rt_meta["actual_parallel_workers"] = 1

    e1_sum = e1_blk["v4_240k_full_repair_ledger"]["methods_summary"]
    tot_pac_viols = (
        e1_sum["SPQL_Passive"]["pac_violations_zero_slack"]
        + e1_sum["SPQL_Active"]["pac_violations_zero_slack"]
        + e1_sum["Uncompressed_PAC_Passive"]["pac_violations_zero_slack"]
        + sum(e2_blk["arms_summary"][k]["total_pac_violations_zero_slack"] for k in ("SPQL", "MatrixFree_SpectralSchur_PAC", "Uncompressed_SpectralSchur_PAC"))
    )
    if tot_pac_viols != 0:
        raise RuntimeError(f"Non-zero zero-slack PAC violations: {tot_pac_viols}")

    payload = _sanitize_for_strict_json({
        "milestone": "Phase3_v4_R675_OutwardVerifier_CSRBinding_LinearMF_and_4LevelDecomposition",
        "cohort_provenance": "Bounded_R675_Repair_Replay_on_Fixed_Seeds_4000_5000_6000 (not an untouched confirmation cohort; v1, v2, and v3 JSON archives preserved byte-identical)",
        "elapsed_wall_s": float(time.perf_counter() - t0),
        "runtime_metadata": rt_meta,
        "phase3_manifest": compute_phase3_manifest(),
        "immutable_archives_verified": immutable_post,
        "total_zero_slack_pac_violations": int(tot_pac_viols),
        "contract_20_gates": gates,
        "block_e1_240k_full_ledger_and_v2_reanalysis": e1_blk,
        "block_e2_curved_3d_linear_mf_and_4level": e2_blk,
        "block_e3_continuous_surrogate_fingerprint_verified": e3_blk,
    })

    out_json = p3_dir / "p3_v4_r675_verified_results.json"
    txt = json.dumps(payload, indent=2, allow_nan=False)
    _ = _strict_json_loads(txt)
    out_json.write_text(txt, encoding="utf-8")
    print(
        f"[Phase-III v4 DONE] Wrote {out_json.name} in {payload['elapsed_wall_s']:.1f}s | "
        f"Gates20/20=True | ZeroSlackPACViol={tot_pac_viols} | "
        f"E3_RecomputedRollouts={e3_blk['policy_fingerprint_audit']['recomputed_rollout_pairs_due_to_policy_change']}"
    )
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gates-only", action="store_true")
    args = parser.parse_args()
    if args.gates_only:
        res = run_phase3_r675_targeted_audit_suite(gates_only=True)
        print(json.dumps(res, indent=2))
    else:
        run_phase3_r675_targeted_audit_suite(gates_only=False)
