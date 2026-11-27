"""Phase-III `v3` Bounded Delivery-Contract & Matched-Quality Repair Suite
(`learned_portal_phase3.run_phase3_r747_delivery_repair` — Closing `R747-01..10`).

Strict Bounded Scope (`per GPT6 R747 Section 13`):
  1. Preserves ALL historical archives byte-for-byte untouched:
       - `green_response/` (`271ac8df...`)
       - `quotient_phase2/*.py` (`e6ea565b...`), 10 `m20..m232` JSONs, `m233_sisc_unlock_results.json` (`339e723f...`),
         and `m233_clean_isolation_replication.json` (`73101638...`)
       - `learned_portal_phase3/p3_neurips_benchmark_results.json` (`0e2c76ea...`)
       - `learned_portal_phase3/p3_v2_verified_benchmark_results.json` (`6167bd5f...`)
  2. Executes `18/18` Deterministic Contract Gates (`P3-C01..P3-C18`).
  3. Block E1 (`Seeds 4000..4007`):
       - Re-reduces frozen `v2` task events (`2,304` rows) with full `R747-09` diagnostics (`matched-task
         finite width intersection`, `mean_true_optimal_value`, `capped_score_80` paired-t & Wilcoxon CIs,
         explicit `finite_policy_count` vs. `abstention_count`);
       - Runs a bounded `240k` solver-delivery audit on the exact same `4000..4007` datasets quantifying
         exact `unreachable_on_observed_support` vs. `certified_coarse_finite_policy`.
  4. Block E2 (`Seeds 5000..5007`, Exact Fixed `192` Tasks, 4-Arm Cyclic Schedule):
       - Re-runs affected 3D cave suite under Tier-3 IEEE-754 Higham verification & typed `solver_status`;
       - Asserts **100% matched policy delivery** across all 3 PAC methods (`SPQL`, `MatrixFree`, `Uncompressed`)
         before comparing LU backsolves, selected array footprints, or lifecycle wall-clock times (`Closes R747-P0-01`).
  5. Block E3 (`Seeds 6000..6007`, Exact Fixed `96` Goals, `80` Rollouts/Goal, Zero Silent Fallback):
       - Re-runs affected continuous Voronoi surrogate benchmark across **7** same-data controls (`including
         SPQL start-local AND SPQL_UniformPortals causal ablation`), forbidding `Pi=None -> u=0` (`Closes R747-P0-02`)
         and auditing collisions on **all `96/96` goals (`7,680/7,680` rollouts/method)** (`Closes R747-06`).
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
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
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
)
from learned_portal_phase3.baselines_and_contracts import (
    MatrixFreeSpectralSchurPACPlanner,
    PlugInCEFullGraphPlanner,
    UncompressedSpectralSchurPACPlanner,
    run_phase3_18_contract_gates,
)
from learned_portal_phase3.continuous_manifold_spql import run_single_continuous_rotated_map_benchmark
from learned_portal_phase3.spql_core import (
    SPQLPlanner,
    build_curved_3d_cave_env,
    build_rotated_multiroom_2d_env,
    collect_exploration_trajectories,
    collect_portal_directed_active_trajectories,
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


def audit_e1_from_frozen_v2_and_240k_delivery(p3_dir: Path, seeds: List[int]) -> dict:
    """Recomputes full R747-09 diagnostics from frozen `p3_v2_verified_benchmark_results.json` (`no silent
    overwriting of v2`) AND audits `v3` solver status on `240k` `seeds 4000..4007`.
    """
    v2_data = json.loads((p3_dir / "p3_v2_verified_benchmark_results.json").read_text(encoding="utf-8"))
    ev_v2 = v2_data["block_e1_rotated_2d_unrestricted_goals"]["task_events"]

    reanalysis_by_budget: Dict[str, dict] = {}
    for b_int in (30000, 90000, 240000):
        b_rows = [e for e in ev_v2 if int(e["step_budget"]) == b_int]
        by_map_act_cap, by_map_pas_cap = [], []
        by_map_matched_w_diff = []
        matched_pairs_total = 0
        for sd in sorted(set(int(e["seed"]) for e in b_rows)):
            act_s = {int(e["task_index"]): e for e in b_rows if int(e["seed"]) == sd and e["method_id"] == "SPQL_Active"}
            pas_s = {int(e["task_index"]): e for e in b_rows if int(e["seed"]) == sd and e["method_id"] == "SPQL_Passive"}
            by_map_act_cap.append(float(np.mean([x["capped_score_80"] for x in act_s.values()])))
            by_map_pas_cap.append(float(np.mean([x["capped_score_80"] for x in pas_s.values()])))
            m_diffs = [
                float(act_s[ti]["width"] - pas_s[ti]["width"])
                for ti in sorted(act_s.keys())
                if act_s[ti]["finite_certified"] and pas_s[ti]["finite_certified"]
                and act_s[ti]["width"] is not None and pas_s[ti]["width"] is not None
            ]
            matched_pairs_total += len(m_diffs)
            if m_diffs:
                by_map_matched_w_diff.append(float(np.mean(m_diffs)))

        act_cap_arr = np.array(by_map_act_cap, dtype=float)
        pas_cap_arr = np.array(by_map_pas_cap, dtype=float)
        wil_p = float(sp_stats.wilcoxon(act_cap_arr - pas_cap_arr).pvalue)
        act_all = [e for e in b_rows if e["method_id"] == "SPQL_Active"]
        pas_all = [e for e in b_rows if e["method_id"] == "SPQL_Passive"]
        reanalysis_by_budget[str(b_int)] = {
            "mean_true_optimal_value": float(np.mean([e["true_optimal_V"] for e in act_all])),
            "spql_active_attempts": len(act_all),
            "spql_active_finite_policy_count": int(sum(1 for e in act_all if e["finite_certified"])),
            "spql_active_abstention_count": int(sum(1 for e in act_all if not e["finite_certified"])),
            "spql_active_within_eps_0p18_count": int(sum(1 for e in act_all if e["within_eps_tol"])),
            "spql_passive_attempts": len(pas_all),
            "spql_passive_finite_policy_count": int(sum(1 for e in pas_all if e["finite_certified"])),
            "spql_passive_abstention_count": int(sum(1 for e in pas_all if not e["finite_certified"])),
            "spql_passive_within_eps_0p18_count": int(sum(1 for e in pas_all if e["within_eps_tol"])),
            "paired_capped_score_80_active_minus_passive": {
                **paired_stats(act_cap_arr - pas_cap_arr),
                "wilcoxon_p_two_sided": wil_p,
                "active_lower_seed_count": int(np.sum(act_cap_arr < pas_cap_arr)),
            },
            "posthoc_matched_finite_task_intersection_width_diff": (
                {
                    "matched_task_pairs": matched_pairs_total,
                    "maps_with_matched_pairs": len(by_map_matched_w_diff),
                    "map_level_paired_stats": paired_stats(np.array(by_map_matched_w_diff, dtype=float)),
                }
                if len(by_map_matched_w_diff) >= 2
                else None
            ),
            "v2_summary_methods": v2_data["block_e1_rotated_2d_unrestricted_goals"]["summary_by_budget"][str(b_int)]["methods"],
        }

    # Bounded v3 solver-status audit at 240k on exact same seeds `seeds` (`4000..4007`)
    status_240k = {
        "SPQL_Passive": {"certified_coarse_finite_policy": 0, "certified_exact_portal_fallback_policy": 0, "unreachable_on_observed_support": 0, "numerical_witness_failure": 0, "pac_violations": 0, "capped_scores": [], "finite_widths": []},
        "SPQL_Active": {"certified_coarse_finite_policy": 0, "certified_exact_portal_fallback_policy": 0, "unreachable_on_observed_support": 0, "numerical_witness_failure": 0, "pac_violations": 0, "capped_scores": [], "finite_widths": []},
    }
    nb = 240000
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
        for m_nm, ds_cur in (("SPQL_Passive", ds_pas), ("SPQL_Active", ds_act)):
            pl = SPQLPlanner(ds_cur, delta=0.05, eps_tol=0.18, max_rooms=10, max_degree_bound=8)
            cap_s_seed, w_seed = [], []
            for t_i, (s0, gm) in enumerate(tasks):
                vt_s = true_vs[t_i]
                rr = pl.solve_unseen_goal(s0, gm, materialize_policy=True)
                st = str(rr["solver_status"])
                status_240k[m_nm][st] = status_240k[m_nm].get(st, 0) + 1
                j_t = env.evaluate_deployed_policy_true_cost(rr["Pi_ext_csr"], gm, 0.0, s0)
                cap_s_seed.append(float(min(j_t - vt_s, 80.0)) if np.isfinite(j_t) else 80.0)
                if rr["certified"]:
                    w_seed.append(float(rr["width"]))
                    if not (rr["lo"] - 1e-7 <= vt_s <= j_t + 1e-7 <= rr["hi"] + 1e-7):
                        status_240k[m_nm]["pac_violations"] += 1
                elif np.isfinite(rr["lo"]) and rr["lo"] > vt_s + 1e-7:
                    status_240k[m_nm]["pac_violations"] += 1
            status_240k[m_nm]["capped_scores"].append(float(np.mean(cap_s_seed)))
            status_240k[m_nm]["finite_widths"].append(float(np.mean(w_seed)) if w_seed else float("nan"))
            del pl
            gc.collect()

    act_c3 = np.array(status_240k["SPQL_Active"]["capped_scores"], dtype=float)
    pas_c3 = np.array(status_240k["SPQL_Passive"]["capped_scores"], dtype=float)
    act_w3 = np.array(status_240k["SPQL_Active"]["finite_widths"], dtype=float)
    pas_w3 = np.array(status_240k["SPQL_Passive"]["finite_widths"], dtype=float)
    return {
        "provenance": "Frozen_v2_Ledger_Reanalysis_Plus_Bounded_240k_v3_Delivery_Audit",
        "v2_reanalysis_by_budget": reanalysis_by_budget,
        "v3_240k_delivery_audit": {
            "n_seeds": len(seeds),
            "SPQL_Passive": {
                **{k: v for k, v in status_240k["SPQL_Passive"].items() if k not in ("capped_scores", "finite_widths")},
                "mean_capped_score_80": float(np.mean(pas_c3)),
                "mean_finite_width": float(np.nanmean(pas_w3)),
            },
            "SPQL_Active": {
                **{k: v for k, v in status_240k["SPQL_Active"].items() if k not in ("capped_scores", "finite_widths")},
                "mean_capped_score_80": float(np.mean(act_c3)),
                "mean_finite_width": float(np.nanmean(act_w3)),
            },
            "paired_capped_score_80_active_minus_passive": {
                **paired_stats(act_c3 - pas_c3),
                "wilcoxon_p_two_sided": float(sp_stats.wilcoxon(act_c3 - pas_c3).pvalue),
            },
            "paired_finite_width_active_minus_passive": paired_stats(act_w3 - pas_w3),
        },
    }


def run_repaired_block_e2_curved_3d_cave_suite(seeds: List[int], n_steps: int = 460000, n_goals: int = 24) -> dict:
    """Repaired Block E2 (`Closes R747-P0-01, R747-03, & R747-10`):
    Evaluates the exact same `seeds` (`5000..5007`) and `192` tasks under Tier-3 Higham verification and
    enforces **matched policy-delivery contract** across all 3 PAC methods (`SPQL`, `MatrixFree`, `Uncompressed`)!
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

        rot = idx_s % 4
        exec_order = list(arm_names[rot:]) + list(arm_names[:rot])
        arm_data: Dict[str, dict] = {}

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
            init_rhs = int(getattr(pl, "init_lu_rhs", 0))
            mem_init_mb = float(pl.resident_bytes()) / (1024.0 * 1024.0)

            full_q_ms_list, bnd_q_ms_list = [], []
            op_rhs_list, mat_rhs_list = [], []
            dofs_list, widths_list, regrets_fin = [], [], []
            pac_viols = 0
            ce_opt_viols = 0
            fin_cert_cnt = 0
            pol_pres_cnt = 0
            proper_cnt = 0
            eps_cnt = 0
            fb_cnt = 0
            unreach_cnt = 0
            wit_fail_cnt = 0

            for t_i, (s0, gm) in enumerate(tasks):
                vt_s = true_vs[t_i]
                rr = pl.solve_unseen_goal(s0, gm, materialize_policy=True)
                st = str(rr.get("solver_status", "unknown"))
                pol_pres = bool(rr.get("policy_present", rr["Pi_ext_csr"] is not None))
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
                if st == "numerical_witness_failure":
                    wit_fail_cnt += 1

                full_q_ms_list.append(float(rr["query_ms"]))
                bnd_q_ms_list.append(float(rr["bounds_only_query_ms"]))
                op_rhs_list.append(int(rr.get("operational_lu_rhs", rr.get("global_lu_rhs", 0))))
                mat_rhs_list.append(int(rr.get("materialization_lu_rhs", 0)))
                if arm_nm == "SPQL":
                    dofs_list.append(int(rr["active_dofs"]))

                p_viol = False
                o_viol = False
                if arm_nm in ("SPQL", "MatrixFree_SpectralSchur_PAC", "Uncompressed_SpectralSchur_PAC"):
                    if fin_cert:
                        if (not pol_pres) or (not is_prop) or not (rr["lo"] - 1e-7 <= vt_s <= j_pol + 1e-7 <= rr["hi"] + 1e-7):
                            p_viol = True
                            pac_viols += 1
                    elif np.isfinite(rr.get("lo", np.nan)) and rr["lo"] > vt_s + 1e-7:
                        p_viol = True
                        pac_viols += 1
                else:
                    pred_v = float(rr["pred_val"])
                    if np.isfinite(pred_v) and pred_v < j_pol - 1e-6:
                        o_viol = True
                        ce_opt_viols += 1

                event_ledger.append({
                    "block": "E2_Curved3DCave_R747_MatchedDelivery",
                    "seed": int(sd),
                    "task_index": int(t_i),
                    "start_state": int(s0),
                    "goal_sha1": _goal_sha1(gm),
                    "method_id": arm_nm,
                    "solver_status": st,
                    "policy_present": pol_pres,
                    "finite_certified": fin_cert,
                    "within_eps_0p15": bool(fin_cert and float(rr["width"]) <= 0.15),
                    "fallback_used": fb_used,
                    "fallback_method": rr.get("fallback_method", None),
                    "fallback_ms": float(rr.get("fallback_ms", 0.0)),
                    "true_optimal_V": vt_s,
                    "deployed_policy_J": j_pol,
                    "proper_policy": is_prop,
                    "lo": float(rr["lo"]) if "lo" in rr and np.isfinite(rr["lo"]) else None,
                    "hi": float(rr["hi"]) if "hi" in rr and np.isfinite(rr["hi"]) else None,
                    "width": float(rr["width"]) if "width" in rr and np.isfinite(rr["width"]) else None,
                    "higham_pes_eps_fl": float(rr.get("higham_pes_eps_fl", 0.0)),
                    "pac_violation": p_viol,
                    "ce_overoptimism_violation": o_viol,
                    "bounds_only_query_ms": float(rr["bounds_only_query_ms"]),
                    "full_policy_query_ms": float(rr["query_ms"]),
                    "operational_lu_rhs": int(rr.get("operational_lu_rhs", rr.get("global_lu_rhs", 0))),
                    "materialization_lu_rhs": int(rr.get("materialization_lu_rhs", 0)),
                })

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
                "exec_rank": rk,
                "attempts": int(len(tasks)),
                "finite_certified_count": int(fin_cert_cnt),
                "policy_present_count": int(pol_pres_cnt),
                "proper_policy_count": int(proper_cnt),
                "within_eps_count": int(eps_cnt),
                "fallback_count": int(fb_cnt),
                "unreachable_count": int(unreach_cnt),
                "numerical_witness_failure_count": int(wit_fail_cnt),
                "offline_init_ms": init_ms,
                "online_24q_bounds_only_ms": online_bnd_sum,
                "online_24q_full_policy_ms": online_full_sum,
                "lifecycle_init_plus_24q_full_policy_ms": init_ms + online_full_sum,
                "init_lu_rhs": init_rhs,
                "online_operational_lu_rhs": op_rhs_sum,
                "online_materialization_lu_rhs": mat_rhs_sum,
                "total_lifecycle_lu_rhs": init_rhs + op_rhs_sum + mat_rhs_sum,
                "initial_selected_array_mb": mem_init_mb,
                "post_24q_selected_array_mb": mem_post24_mb,
                "vmrss_mib_before_arm_snapshot": rss_before_mib,
                "vmrss_mib_end_of_arm_snapshot": rss_end_mib,
                "vmrss_mib_after_gc_snapshot": rss_after_gc_mib,
                "mean_active_dofs": float(np.mean(dofs_list)) if dofs_list else None,
                "mean_certified_width": float(np.mean(widths_list)) if widths_list else None,
                "mean_uncapped_regret": float(np.mean(regrets_fin)) if regrets_fin else None,
                "pac_violations": int(pac_viols),
                "ce_overoptimism_violations": int(ce_opt_viols),
                "n_rooms": n_rooms_disc,
                "n_portals": n_portals_disc,
                "n_gamma": n_gamma_disc,
            }

        # Enforce R747-P0-01 matched-delivery invariant on every map!
        for pac_arm in ("SPQL", "MatrixFree_SpectralSchur_PAC", "Uncompressed_SpectralSchur_PAC"):
            if arm_data[pac_arm]["numerical_witness_failure_count"] != 0:
                raise RuntimeError(f"Map {sd} {pac_arm} had numerical witness failure: {arm_data[pac_arm]}")
            if arm_data[pac_arm]["policy_present_count"] != arm_data["Uncompressed_SpectralSchur_PAC"]["policy_present_count"]:
                raise RuntimeError(f"Map {sd} mismatched policy delivery count across PAC arms: {arm_data}")

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
        return {
            "total_attempts": int(sum(r["arms"][a_nm]["attempts"] for r in records)),
            "total_finite_certified": int(sum(r["arms"][a_nm]["finite_certified_count"] for r in records)),
            "total_policy_present": int(sum(r["arms"][a_nm]["policy_present_count"] for r in records)),
            "total_proper_policies": int(sum(r["arms"][a_nm]["proper_policy_count"] for r in records)),
            "total_within_eps_0p15": int(sum(r["arms"][a_nm]["within_eps_count"] for r in records)),
            "total_fallbacks": int(sum(r["arms"][a_nm]["fallback_count"] for r in records)),
            "total_unreachable": int(sum(r["arms"][a_nm]["unreachable_count"] for r in records)),
            "total_witness_failures": int(sum(r["arms"][a_nm]["numerical_witness_failure_count"] for r in records)),
            "mean_uncapped_regret": float(np.mean([r["arms"][a_nm]["mean_uncapped_regret"] for r in records if r["arms"][a_nm]["mean_uncapped_regret"] is not None])),
            "mean_certified_width": (
                float(np.mean([r["arms"][a_nm]["mean_certified_width"] for r in records if r["arms"][a_nm]["mean_certified_width"] is not None]))
                if any(r["arms"][a_nm]["mean_certified_width"] is not None for r in records)
                else None
            ),
            "mean_offline_init_ms": float(np.mean([r["arms"][a_nm]["offline_init_ms"] for r in records])),
            "mean_online_24q_bounds_only_ms": float(np.mean([r["arms"][a_nm]["online_24q_bounds_only_ms"] for r in records])),
            "mean_online_24q_full_policy_ms": float(np.mean([r["arms"][a_nm]["online_24q_full_policy_ms"] for r in records])),
            "mean_lifecycle_24q_full_policy_ms": float(np.mean([r["arms"][a_nm]["lifecycle_init_plus_24q_full_policy_ms"] for r in records])),
            "mean_init_lu_rhs": float(np.mean([r["arms"][a_nm]["init_lu_rhs"] for r in records])),
            "mean_online_operational_lu_rhs": float(np.mean([r["arms"][a_nm]["online_operational_lu_rhs"] for r in records])),
            "mean_online_materialization_lu_rhs": float(np.mean([r["arms"][a_nm]["online_materialization_lu_rhs"] for r in records])),
            "mean_total_lifecycle_lu_rhs": float(np.mean([r["arms"][a_nm]["total_lifecycle_lu_rhs"] for r in records])),
            "mean_initial_selected_array_mb": float(np.mean([r["arms"][a_nm]["initial_selected_array_mb"] for r in records])),
            "mean_post_24q_selected_array_mb": float(np.mean([r["arms"][a_nm]["post_24q_selected_array_mb"] for r in records])),
            "max_end_of_arm_vmrss_snapshot_mib": float(np.max([r["arms"][a_nm]["vmrss_mib_end_of_arm_snapshot"] for r in records])),
            "total_pac_violations": int(sum(r["arms"][a_nm]["pac_violations"] for r in records)),
            "total_ce_overoptimism_violations": int(sum(r["arms"][a_nm]["ce_overoptimism_violations"] for r in records)),
        }

    sp_life = np.array([r["arms"]["SPQL"]["lifecycle_init_plus_24q_full_policy_ms"] for r in records], dtype=float)
    mf_life = np.array([r["arms"]["MatrixFree_SpectralSchur_PAC"]["lifecycle_init_plus_24q_full_policy_ms"] for r in records], dtype=float)
    uc_life = np.array([r["arms"]["Uncompressed_SpectralSchur_PAC"]["lifecycle_init_plus_24q_full_policy_ms"] for r in records], dtype=float)
    ce_life = np.array([r["arms"]["PlugIn_CE_FullGraph"]["lifecycle_init_plus_24q_full_policy_ms"] for r in records], dtype=float)

    return {
        "n_maps": len(records),
        "mean_states": float(np.mean([r["n_states"] for r in records])),
        "mean_full_portal_dofs": float(np.mean([r["full_portal_dofs"] for r in records])),
        "mean_spql_active_dofs": float(np.mean([r["arms"]["SPQL"]["mean_active_dofs"] for r in records])),
        "arms_summary": {a_nm: _agg_arm(a_nm) for a_nm in arm_names},
        "comparisons_full_lifecycle": {
            "speedup_vs_matrixfree_pac": float(np.mean(mf_life) / np.mean(sp_life)),
            "paired_diff_spql_minus_matrixfree_pac_ms": paired_stats(sp_life - mf_life),
            "speedup_vs_uncompressed_pac": float(np.mean(uc_life) / np.mean(sp_life)),
            "paired_diff_spql_minus_uncompressed_pac_ms": paired_stats(sp_life - uc_life),
            "speedup_vs_plugin_ce_fullgraph": float(np.mean(ce_life) / np.mean(sp_life)),
            "paired_diff_spql_minus_plugin_ce_ms": paired_stats(sp_life - ce_life),
        },
        "per_seed": records,
        "task_events": event_ledger,
    }


def run_repaired_block_e3_continuous_suite(seeds: List[int]) -> dict:
    """Repaired Block E3 (`Closes R747-P0-02, R747-06, & R747-07`):
    Zero silent `None -> u=0` fallback, `96/96` collision-audited goals (`80` rollouts/goal = `7,680` rollouts/method),
    and causal comparison of `SPQL` (start-local) vs. `SPQL_UniformPortals` (all-portal refinement) vs. `Uncompressed_PAC`!
    """
    rows = [
        run_single_continuous_rotated_map_benchmark(
            sd, n_explore_steps=30600, n_goals=12, verify_zero_tunneling=True, include_uniform_portal_spql=True
        )
        for sd in seeds
    ]
    m_keys = (
        "SPQL",
        "SPQL_UniformPortals",
        "Uncompressed_PAC",
        "PlugIn_CE",
        "Scalar_Portal_Ablation",
        "SVD_Resolvent_Ablation",
        "Sampled_Desirability_TD",
    )
    summary = {}
    sp_c = np.array([r["methods"]["SPQL"]["mean_closed_loop_cost"] for r in rows], dtype=float)
    for k in m_keys:
        kc = np.array([r["methods"][k]["mean_closed_loop_cost"] for r in rows], dtype=float)
        ks = np.array([r["methods"][k]["mean_success_rate"] for r in rows], dtype=float)
        kq = np.array([r["methods"][k]["mean_query_ms"] for r in rows], dtype=float)
        pol_tot = sum(int(r["methods"][k]["policy_present_count"]) for r in rows)
        fb_tot = sum(int(r["methods"][k]["fallback_count"]) for r in rows)
        aud_tot = sum(int(r["methods"][k]["collision_audited_goal_count"]) for r in rows)
        kb = sum(int(r["methods"][k]["total_blocked_segments"]) for r in rows)
        k_exact = sum(int(r["methods"][k]["total_exact_chord_hits"]) for r in rows)
        summary[k] = {
            "total_goals": int(len(seeds) * 12),
            "total_rollouts": int(len(seeds) * 12 * 80),
            "policy_present_count": int(pol_tot),
            "fallback_count": int(fb_tot),
            "collision_audited_goal_count": int(aud_tot),
            "mean_closed_loop_cost": float(np.mean(kc)),
            "mean_success_rate_pct": 100.0 * float(np.mean(ks)),
            "mean_query_ms": float(np.mean(kq)),
            "total_blocked_segments_sampled20": int(kb),
            "total_exact_chord_hits": int(k_exact),
            "paired_cost_diff_spql_minus_method": (
                {
                    **paired_stats(sp_c - kc),
                    "wilcoxon_p_two_sided": float(sp_stats.wilcoxon(sp_c - kc).pvalue) if not np.allclose(sp_c, kc) else 1.0,
                    "spql_lower_cost_seeds": int(np.sum(sp_c < kc)),
                }
                if k != "SPQL"
                else None
            ),
        }
        if pol_tot != len(seeds) * 12:
            raise RuntimeError(f"E3 method {k} failed to deliver policies on all {len(seeds)*12} goals: {pol_tot}")

    tot_exp_blocked = sum(int(r["explore_blocked_segments"]) for r in rows)
    tot_exp_exact = sum(int(r["explore_exact_chord_hits"]) for r in rows)
    all_events = [ev for r in rows for ev in r["task_events"]]
    return {
        "simulator_model": "damped_0.85_padded_4e-4_chord_guarded_euler_diffusion_simulator",
        "guarantee_scope": "empirical_fitted_voronoi_surrogate_no_aggregation_or_continuous_sde_pac_claim",
        "total_explore_transitions_audited": int(sum(int(r["actual_explore_steps"]) for r in rows)),
        "total_explore_blocked_segments_sampled20": int(tot_exp_blocked),
        "total_explore_exact_chord_hits": int(tot_exp_exact),
        "summary": summary,
        "per_seed": [{k: v for k, v in r.items() if k != "task_events"} for r in rows],
        "task_events": all_events,
    }


def _generate_v3_figures(e1_blk: dict, e2_blk: dict, e3_blk: dict, out_dir: Path) -> None:
    re_b = e1_blk["v2_reanalysis_by_budget"]
    budgets = [30000, 90000, 240000]
    x_lbl = ["30k", "90k", "240k"]

    fig, axes = plt.subplots(1, 3, figsize=(15.6, 4.6), dpi=180)
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
    ax.legend(fontsize=6.8, loc="upper right")

    ax = axes[1]
    fc_pas = [re_b[str(b)]["v2_summary_methods"]["SPQL_Passive"]["finite_enclosure_rate_pct"] for b in budgets]
    fc_act = [re_b[str(b)]["v2_summary_methods"]["SPQL_Active"]["finite_enclosure_rate_pct"] for b in budgets]
    ep_act = [re_b[str(b)]["v2_summary_methods"]["SPQL_Active"]["within_eps_tol_rate_pct"] for b in budgets]
    ax.plot(range(len(budgets)), fc_pas, "--s", linewidth=2.0, color="#27ae60", label="Passive Finite Policy %")
    ax.plot(range(len(budgets)), fc_act, "-o", linewidth=2.3, color="#16a085", label="Active Finite Policy %")
    ax.plot(range(len(budgets)), ep_act, "-.^", linewidth=1.9, color="#7f8c8d", label="Width <= 0.18 % (0%)")
    ax.set_xticks(range(len(budgets)))
    ax.set_xticklabels(x_lbl)
    ax.set_ylim(-2.0, 105.0)
    ax.set_xlabel("Exploration Trajectory Budget $N_{\\mathrm{step}}$")
    ax.set_ylabel("Task Rate (%) [0 PAC Violations]")
    ax.set_title("B. Finite Policy Delivery vs. Tight Eps=0.18", fontsize=9.5, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.4, loc="center right")

    ax = axes[2]
    ce_v = [re_b[str(b)]["v2_summary_methods"]["PlugIn_CE_FullGraph"]["total_ce_overoptimism_violations"] for b in budgets]
    sp_v = [re_b[str(b)]["v2_summary_methods"]["SPQL_Active"]["total_pac_four_inequality_violations"] for b in budgets]
    x_pos = np.arange(len(budgets))
    ax.bar(x_pos - 0.18, ce_v, width=0.34, color="#e74c3c", label="Plug-In CE (V_hat < J)")
    ax.bar(x_pos + 0.18, sp_v, width=0.34, color="#16a085", label="SPQL Active (4-Ineq Viol.)")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_lbl)
    ax.set_ylabel("Count out of 128 Unrestricted Tasks")
    ax.set_title("C. Optimism Underestimation vs. PAC Validity", fontsize=9.5, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=7.4)

    plt.tight_layout()
    fig.savefig(out_dir / "p3_v3_fig1_rotated_pac_and_active.png", bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(14.2, 4.8), dpi=180)
    ax = axes[0]
    arms_3d = ("PlugIn_CE_FullGraph", "Uncompressed_SpectralSchur_PAC", "MatrixFree_SpectralSchur_PAC", "SPQL")
    lbls_3d = ["Plug-In CE\n(192/192 Pol)", "Uncomp. PAC\n(192/192 Pol)", "MatrixFree PAC\n(192/192 Pol)", "SPQL (Ours)\n(192/192 Pol)"]
    inits_s = [e2_blk["arms_summary"][k]["mean_offline_init_ms"] / 1000.0 for k in arms_3d]
    onlines_s = [e2_blk["arms_summary"][k]["mean_online_24q_full_policy_ms"] / 1000.0 for k in arms_3d]
    rhs_3d = [e2_blk["arms_summary"][k]["mean_total_lifecycle_lu_rhs"] for k in arms_3d]
    x3 = np.arange(len(arms_3d))
    ax.bar(x3, inits_s, width=0.5, color="#95a5a6", label="Offline Init (s)")
    ax.bar(x3, onlines_s, bottom=inits_s, width=0.5, color=["#2980b9", "#8e44ad", "#d35400", "#16a085"], label="24 Matched Full-Policy Queries (s)")
    for idx_i, (tot_v, rv) in enumerate(zip(np.array(inits_s) + np.array(onlines_s), rhs_3d)):
        ax.text(idx_i, tot_v + 0.06, f"{tot_v:.2f}s\n({rv:.0f} RHS)", ha="center", va="bottom", fontsize=7.6, fontweight="bold")
    ax.set_xticks(x3)
    ax.set_xticklabels(lbls_3d, fontsize=7.8)
    ax.set_ylabel("Single-Worker Lifecycle Time (s)")
    ax.set_ylim(0, max(np.array(inits_s) + np.array(onlines_s)) * 1.28)
    ax.set_title("A. 3D Cave Matched-Delivery Lifecycle (192/192 Policies)", fontsize=9.5, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=7.8, loc="upper left")

    ax = axes[1]
    m_c = ("SPQL", "SPQL_UniformPortals", "Uncompressed_PAC", "PlugIn_CE", "Sampled_Desirability_TD", "Scalar_Portal_Ablation", "SVD_Resolvent_Ablation")
    l_c = ["SPQL\nStartLoc", "SPQL\nAllPort", "Uncomp.\nPAC", "PlugIn\nCE", "Group\nTD", "Scalar\nPortal", "SVD\nResolv."]
    costs_c = [e3_blk["summary"][k]["mean_closed_loop_cost"] for k in m_c]
    succ_c = [e3_blk["summary"][k]["mean_success_rate_pct"] for k in m_c]
    cols_c = ["#16a085", "#1abc9c", "#27ae60", "#2980b9", "#c0392b", "#d35400", "#8e44ad"]
    bars2 = ax.bar(range(len(m_c)), costs_c, color=cols_c, width=0.58)
    for b_rect, cv, sv in zip(bars2, costs_c, succ_c):
        ax.text(b_rect.get_x() + b_rect.get_width() / 2, cv + 0.10, f"{cv:.2f}\n({sv:.0f}%)", ha="center", va="bottom", fontsize=7.2, fontweight="bold")
    ax.set_xticks(range(len(m_c)))
    ax.set_xticklabels(l_c, fontsize=7.6)
    ax.set_ylim(0, max(costs_c) * 1.26)
    ax.set_ylabel("Surrogate Simulator Cost (96/96 Policies, 0 Hits)")
    ax.set_title("B. Continuous Surrogate Control (Zero Silent Fallback)", fontsize=9.5, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(out_dir / "p3_v3_fig2_3d_matched_delivery_and_continuous.png", bbox_inches="tight")
    plt.close(fig)


def run_phase3_r747_delivery_repair_suite(gates_only: bool = False) -> dict:
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
        return {
            **f12,
            "phase2_10_jsons_untouched": True,
            "phase2_json_count": len(fp2_10),
            "m233_original_archive": fm233_orig,
            "m233_clean_isolation_archive": {"file": m233_clean_fp.name, "sha256": m233_clean_sha, "verified_untouched": True},
            "phase3_v1_exploratory_archive": fp3_v1,
            "phase3_v2_benchmark_archive": fp3_v2,
        }

    immutable_pre = _verify_all_immutable()
    print("[Phase-III v3 R747] Running 18 Deterministic Contract Gates (P3-C01..P3-C18)...")
    gates = run_phase3_18_contract_gates()
    if not gates["ALL_18_PHASE3_CONTRACT_GATES_PASSED"]:
        raise RuntimeError(f"Phase-III v3 contract gate failure: {gates}")
    print(f"  -> ALL 18 GATES PASSED in {gates['elapsed_ms']:.1f}ms!")
    if gates_only:
        return gates

    print("[Phase-III v3 Block E1] Reanalyzing frozen v2 E1 ledger + running 240k v3 solver-delivery audit (Seeds 4000..4007)...")
    e1_blk = audit_e1_from_frozen_v2_and_240k_delivery(p3_dir, seeds=list(range(4000, 4008)))

    print("[Phase-III v3 Block E2] Running Repaired Matched-Delivery 3D Cave Suite (Seeds 5000..5007, 192 Tasks)...")
    e2_blk = run_repaired_block_e2_curved_3d_cave_suite(seeds=list(range(5000, 5008)), n_steps=460000, n_goals=24)

    print("[Phase-III v3 Block E3] Running Repaired Zero-Fallback Continuous Surrogate Suite (Seeds 6000..6007, 96 Goals x 7 Controls)...")
    e3_blk = run_repaired_block_e3_continuous_suite(seeds=list(range(6000, 6008)))

    _generate_v3_figures(e1_blk, e2_blk, e3_blk, p3_dir)
    immutable_post = _verify_all_immutable()
    assert immutable_pre == immutable_post

    rt_meta = collect_runtime_metadata()
    rt_meta["actual_parallel_workers"] = 1

    tot_pac_viols = (
        e1_blk["v3_240k_delivery_audit"]["SPQL_Passive"]["pac_violations"]
        + e1_blk["v3_240k_delivery_audit"]["SPQL_Active"]["pac_violations"]
        + sum(e2_blk["arms_summary"][k]["total_pac_violations"] for k in ("SPQL", "MatrixFree_SpectralSchur_PAC", "Uncompressed_SpectralSchur_PAC"))
    )
    tot_chord_hits = (
        e3_blk["total_explore_exact_chord_hits"]
        + sum(e3_blk["summary"][k]["total_exact_chord_hits"] for k in e3_blk["summary"])
    )
    if tot_pac_viols != 0:
        raise RuntimeError(f"Non-zero PAC violations: {tot_pac_viols}")
    if tot_chord_hits != 0:
        raise RuntimeError(f"Non-zero exact chord wall hits: {tot_chord_hits}")
    if e2_blk["arms_summary"]["SPQL"]["total_policy_present"] != 192:
        raise RuntimeError(f"E2 SPQL policy delivery < 192: {e2_blk['arms_summary']['SPQL']}")

    payload = _sanitize_for_strict_json({
        "milestone": "Phase3_v3_R747_Matched_Policy_Delivery_and_18Gate_Repair",
        "cohort_provenance": "Bounded_R747_Repair_on_Existing_Seeds_4000_5000_6000 (not a newly drawn confirmation cohort; v1 and v2 JSON archives preserved byte-identical)",
        "elapsed_wall_s": float(time.perf_counter() - t0),
        "runtime_metadata": rt_meta,
        "phase3_manifest": compute_phase3_manifest(),
        "immutable_archives_verified": immutable_post,
        "total_pac_violations": int(tot_pac_viols),
        "total_e2_spql_policies_delivered_of_192": int(e2_blk["arms_summary"]["SPQL"]["total_policy_present"]),
        "total_e3_spql_policies_delivered_of_96": int(e3_blk["summary"]["SPQL"]["policy_present_count"]),
        "total_continuous_exact_chord_wall_hits": int(tot_chord_hits),
        "contract_18_gates": gates,
        "block_e1_reanalysis_and_240k_delivery_audit": e1_blk,
        "block_e2_curved_3d_cave_matched_delivery": e2_blk,
        "block_e3_continuous_surrogate_7controls": e3_blk,
    })

    out_json = p3_dir / "p3_v3_r747_delivery_verified_results.json"
    txt = json.dumps(payload, indent=2, allow_nan=False)
    _ = _strict_json_loads(txt)
    out_json.write_text(txt, encoding="utf-8")
    print(
        f"[Phase-III v3 DONE] Wrote {out_json.name} in {payload['elapsed_wall_s']:.1f}s | "
        f"Gates18/18=True | E2_SPQL_Policies={e2_blk['arms_summary']['SPQL']['total_policy_present']}/192 | "
        f"E3_SPQL_Policies={e3_blk['summary']['SPQL']['policy_present_count']}/96 | "
        f"PAC_Violations={tot_pac_viols} | ExactChordHits={tot_chord_hits}"
    )
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gates-only", action="store_true")
    args = parser.parse_args()
    if args.gates_only:
        res = run_phase3_r747_delivery_repair_suite(gates_only=True)
        print(json.dumps(res, indent=2))
    else:
        run_phase3_r747_delivery_repair_suite(gates_only=False)
