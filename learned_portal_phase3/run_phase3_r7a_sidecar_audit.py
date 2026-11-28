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
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.sparse as sp

from green_response import collect_runtime_metadata, enforce_single_thread_env
from quotient_phase2.m232_final_closure import _sanitize_for_strict_json
from quotient_phase2.m233_sisc_subportal_quadtree import verify_m233_original_archive_untouched
from quotient_phase2.verify_m232_release import _strict_json_loads, verify_all_10_frozen_jsons

from learned_portal_phase3 import (
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
    SPQLPlanner,
    build_curved_3d_cave_env,
    build_rotated_multiroom_2d_env,
    collect_exploration_trajectories,
    sample_unseen_goal_tasks,
)


FROZEN_M233_CLEAN_SHA256 = "73101638ce563ca9f33049e2ffef50c16218ad097785c031ecd19d3d99a7e678"
OLD_V3_COMMIT = "67532c91d6c43a32d0f4d0277ad28cd059e5a28b"


_E3_DUMP_WORKER_CODE = r"""
import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import scipy.sparse as sp

repo_dir = Path(sys.argv[1]).resolve()
out_dir = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(repo_dir))

from learned_portal_phase3.spql_core import SPQLPlanner, sample_unbiased_bounded_cost
from learned_portal_phase3.baselines_and_contracts import (
    LowRankSRLinearRLPlanner,
    ModelFreeGoalSoftQPlanner,
    PlugInCEFullGraphPlanner,
    ScalarBottleneckOptionPlanner,
    UncompressedSpectralSchurPACPlanner,
)
from learned_portal_phase3.continuous_manifold_spql import (
    RotatedContinuousDiffusionWorld,
    build_voronoi_quotient_from_continuous_trajectories,
)

def canon_csr_sha256(mat: sp.csr_matrix) -> str:
    c = mat.copy()
    c.sort_indices()
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(c.indptr, dtype="<i8").tobytes())
    h.update(np.ascontiguousarray(c.indices, dtype="<i8").tobytes())
    h.update(np.ascontiguousarray(c.data, dtype="<f8").tobytes())
    return h.hexdigest()

for seed in range(6000, 6008):
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
        q_step = np.array([sample_unbiased_bounded_cost(float(qv), q_min_step, q_max_step, 0.004, rng) for qv in q_true_step], dtype=float)
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
    tasks_c = []
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
            tasks_c.append((s_id, gm))

    m_names = list(planners.keys())
    rot = seed % len(m_names)
    m_order = m_names[rot:] + m_names[:rot]
    arrays = {"X_curr": X_curr, "X_next": X_next, "q_obs": q_obs, "landmarks": landmarks}
    ev_meta = []
    for t_idx, (s_id, gm) in enumerate(tasks_c):
        g_sha = hashlib.sha256(np.flatnonzero(gm).astype("<i8").tobytes()).hexdigest()
        for m_nm in m_order:
            rr = planners[m_nm].solve_unseen_goal(s_id, gm)
            Pi = rr["Pi_ext_csr"].copy()
            Pi.sort_indices()
            key = f"t{t_idx}_{m_nm}"
            arrays[f"{key}_data"] = Pi.data
            arrays[f"{key}_indices"] = Pi.indices
            arrays[f"{key}_indptr"] = Pi.indptr
            arrays[f"{key}_shape"] = np.array(Pi.shape, dtype=np.int64)
            ev_meta.append({
                "task_index": int(t_idx),
                "method_id": m_nm,
                "goal_sha256": g_sha,
                "canonical_raw_csr_sha256": canon_csr_sha256(Pi),
                "fallback_used": bool(rr.get("fallback_used", False)),
                "fallback_method": rr.get("fallback_method", None),
                "has_z_sub_full": bool("z_sub_full" in rr and rr["z_sub_full"] is not None),
            })
    arrays["event_json"] = np.array(json.dumps(ev_meta))
    np.savez(out_dir / f"seed_{seed}.npz", **arrays)
"""


def run_actual_cross_commit_e3_policy_comparison() -> dict:
    """Reconstructs all `672` actual `E3` `CSR` policies from commit `67532c9` vs. current working tree
    in isolated subprocesses (`zero continuous rollouts!`, `Closes R7A-03`).
    """
    with tempfile.TemporaryDirectory(prefix="r7a_e3_cmp_") as tmp:
        tmp_p = Path(tmp)
        old_repo = tmp_p / "old_repo"
        old_out = tmp_p / "old_out"
        new_out = tmp_p / "new_out"
        worker_py = tmp_p / "worker_e3_dump.py"
        old_repo.mkdir()
        old_out.mkdir()
        new_out.mkdir()
        worker_py.write_text(_E3_DUMP_WORKER_CODE, encoding="utf-8")

        # Extract strictly the 3 needed packages from frozen commit `67532c9`
        tar_proc = subprocess.Popen(
            ["git", "archive", OLD_V3_COMMIT, "green_response", "quotient_phase2", "learned_portal_phase3"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
        )
        subprocess.run(["tar", "-x", "-C", str(old_repo)], stdin=tar_proc.stdout, check=True)
        if tar_proc.wait() != 0:
            raise RuntimeError(f"git archive {OLD_V3_COMMIT} failed")

        subprocess.run([sys.executable, "-B", str(worker_py), str(old_repo), str(old_out)], check=True)
        subprocess.run([sys.executable, "-B", str(worker_py), str(ROOT), str(new_out)], check=True)

        rows: List[dict] = []
        input_checks: List[dict] = []
        for seed in range(6000, 6008):
            with np.load(old_out / f"seed_{seed}.npz", allow_pickle=False) as A, \
                 np.load(new_out / f"seed_{seed}.npz", allow_pickle=False) as B:
                eq = {
                    "seed": seed,
                    **{k: bool(np.array_equal(A[k], B[k])) for k in ("X_curr", "X_next", "q_obs", "landmarks")},
                }
                if not all(eq[k] for k in ("X_curr", "X_next", "q_obs", "landmarks")):
                    raise RuntimeError(f"E3 input mismatch on seed {seed}: {eq}")
                input_checks.append(eq)
                old_m = {(r["task_index"], r["method_id"]): r for r in json.loads(str(A["event_json"]))}
                new_m = {(r["task_index"], r["method_id"]): r for r in json.loads(str(B["event_json"]))}
                for (ti, m_nm), oa in sorted(old_m.items()):
                    nb = new_m[(ti, m_nm)]
                    k = f"t{ti}_{m_nm}"
                    pa = sp.csr_matrix((A[f"{k}_data"], A[f"{k}_indices"], A[f"{k}_indptr"]), shape=tuple(A[f"{k}_shape"]))
                    pb = sp.csr_matrix((B[f"{k}_data"], B[f"{k}_indices"], B[f"{k}_indptr"]), shape=tuple(B[f"{k}_shape"]))
                    diff = pa - pb
                    max_entry = float(np.max(np.abs(diff.data))) if diff.nnz > 0 else 0.0
                    row_l1 = float(np.max(np.asarray(np.abs(diff).sum(axis=1)).ravel()))
                    rows.append({
                        "seed": int(seed),
                        "task_index": int(ti),
                        "method_id": str(m_nm),
                        "comparison_status": "verified_actual_cross_commit_csr",
                        "max_abs_entry_diff": max_entry,
                        "matrix_infinity_norm_diff": row_l1,
                        "old_raw_csr_sha256": oa["canonical_raw_csr_sha256"],
                        "new_raw_csr_sha256": nb["canonical_raw_csr_sha256"],
                        "same_raw_csr_hash": bool(oa["canonical_raw_csr_sha256"] == nb["canonical_raw_csr_sha256"]),
                        "same_goal": bool(oa["goal_sha256"] == nb["goal_sha256"]),
                        "same_fallback": bool((oa["fallback_used"], oa["fallback_method"]) == (nb["fallback_used"], nb["fallback_method"])),
                        "v4_has_z_sub_full": bool(nb["has_z_sub_full"]),
                    })

        return {
            "old_commit": OLD_V3_COMMIT,
            "comparison_scope": "actual_cross_commit_csr_reconstruction_all_672_queries_zero_rollout_reruns",
            "equivalence_semantics": "numerical_tolerance_equivalence_le_1e-12_not_bitwise_csr_identity",
            "comparison_count": len(rows),
            "input_data_bitwise_equal_all_8_seeds": all(all(x[k] for k in ("X_curr", "X_next", "q_obs", "landmarks")) for x in input_checks),
            "same_fallback_count": int(sum(1 for r in rows if r["same_fallback"])),
            "bitwise_hash_equal_count": int(sum(1 for r in rows if r["same_raw_csr_hash"])),
            "exceeds_entrywise_1e12_count": int(sum(1 for r in rows if r["max_abs_entry_diff"] > 1e-12)),
            "exceeds_rowwise_1e12_count": int(sum(1 for r in rows if r["matrix_infinity_norm_diff"] > 1e-12)),
            "max_abs_entry_diff": float(max(r["max_abs_entry_diff"] for r in rows)),
            "max_matrix_infinity_norm_diff": float(max(r["matrix_infinity_norm_diff"] for r in rows)),
            "events": rows,
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

    ce_e1_rows: List[dict] = []
    simplex_e1_rows: List[dict] = []
    for sd in range(4000, 4008):
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
            j_ce = float(ref["deployed_policy_J"])
            pred_v = float(rc["pred_val"])
            viol_recomp = bool(np.isfinite(pred_v) and pred_v < j_ce - 1e-9)
            if viol_recomp != bool(ref["ce_overoptimism_violation"]):
                raise RuntimeError(f"E1 CE violation mismatch on ({sd}, {t_i})")
            ce_e1_rows.append({
                "block": "E1_240k_Passive",
                "seed": int(sd),
                "task_index": int(t_i),
                "start_state": int(s0),
                "pred_val": pred_v,
                "deployed_policy_J": j_ce,
                "optimism_shortfall_J_minus_pred": j_ce - pred_v,
                "violation_threshold": 1e-9,
                "ce_self_underestimation_violation": viol_recomp,
                "native_room_lu_rhs": 0,
                "global_lu_rhs": int(rc["global_lu_rhs"]),
            })
            ce_coord = evaluate_posterior_pac_policy_upper_bound(pl_uc.pac_pair, rc["Pi_ext_csr"], gm, 0.0, s0, env.lam)
            ce_unk_simp = evaluate_row_stochastic_simplex_posterior_diagnostic(
                pl_uc.pac_pair, rc["Pi_ext_csr"], gm, 0.0, s0, env.lam, known_observed_support=False, max_degree_bound=8
            )
            ce_obs_simp = evaluate_row_stochastic_simplex_posterior_diagnostic(
                pl_uc.pac_pair, rc["Pi_ext_csr"], gm, 0.0, s0, env.lam, known_observed_support=True, max_degree_bound=8
            )
            uc_coord = evaluate_posterior_pac_policy_upper_bound(pl_uc.pac_pair, ru["Pi_ext_csr"], gm, 0.0, s0, env.lam)
            uc_obs_simp = evaluate_row_stochastic_simplex_posterior_diagnostic(
                pl_uc.pac_pair, ru["Pi_ext_csr"], gm, 0.0, s0, env.lam, known_observed_support=True, max_degree_bound=8
            )
            simplex_e1_rows.append({
                "seed": int(sd), "task_index": int(t_i),
                "ce_coord_surrogate_U": ce_coord,
                "ce_unknown_support_dmax8_simplex_U": ce_unk_simp,
                "ce_known_observed_support_simplex_U": ce_obs_simp,
                "full_pac_tier3_hi": float(ru["hi"]),
                "full_pac_coord_surrogate_U": uc_coord,
                "full_pac_known_observed_support_simplex_U": uc_obs_simp,
            })

    ce_e2_rows: List[dict] = []
    simplex_e2_rows: List[dict] = []
    for sd in range(5000, 5008):
        env = build_curved_3d_cave_env(seed=sd, gn=38)
        ds = collect_exploration_trajectories(env, total_steps=460000, episode_len=100, seed=sd + 300)
        tasks = sample_unseen_goal_tasks(env, n_tasks=24, seed=sd + 600, goal_radius_nodes=12, avoid_states=None)
        pl_ce = PlugInCEFullGraphPlanner(ds)
        pl_uc = UncompressedSpectralSchurPACPlanner(ds, delta=0.05, max_rooms=10, max_degree_bound=8)
        for t_i, (s0, gm) in enumerate(tasks):
            rc = pl_ce.solve_unseen_goal(s0, gm)
            ru = pl_uc.solve_unseen_goal(s0, gm, materialize_policy=True)
            ref = e2_ce_ref[(sd, t_i)]
            j_ce = float(ref["deployed_policy_J"])
            pred_v = float(rc["pred_val"])
            viol_recomp = bool(np.isfinite(pred_v) and pred_v < j_ce - 1e-9)
            if viol_recomp != bool(ref["ce_overoptimism_violation"]):
                raise RuntimeError(f"E2 CE violation mismatch on ({sd}, {t_i})")
            ce_e2_rows.append({
                "block": "E2_460k_Curved3DCave",
                "seed": int(sd),
                "task_index": int(t_i),
                "start_state": int(s0),
                "pred_val": pred_v,
                "deployed_policy_J": j_ce,
                "optimism_shortfall_J_minus_pred": j_ce - pred_v,
                "violation_threshold": 1e-9,
                "ce_self_underestimation_violation": viol_recomp,
                "native_room_lu_rhs": 0,
                "global_lu_rhs": int(rc["global_lu_rhs"]),
            })
            ce_coord = evaluate_posterior_pac_policy_upper_bound(pl_uc.pac_pair, rc["Pi_ext_csr"], gm, 0.0, s0, env.lam)
            ce_unk_simp = evaluate_row_stochastic_simplex_posterior_diagnostic(
                pl_uc.pac_pair, rc["Pi_ext_csr"], gm, 0.0, s0, env.lam, known_observed_support=False, max_degree_bound=8
            )
            ce_obs_simp = evaluate_row_stochastic_simplex_posterior_diagnostic(
                pl_uc.pac_pair, rc["Pi_ext_csr"], gm, 0.0, s0, env.lam, known_observed_support=True, max_degree_bound=8
            )
            uc_coord = evaluate_posterior_pac_policy_upper_bound(pl_uc.pac_pair, ru["Pi_ext_csr"], gm, 0.0, s0, env.lam)
            uc_obs_simp = evaluate_row_stochastic_simplex_posterior_diagnostic(
                pl_uc.pac_pair, ru["Pi_ext_csr"], gm, 0.0, s0, env.lam, known_observed_support=True, max_degree_bound=8
            )
            simplex_e2_rows.append({
                "seed": int(sd), "task_index": int(t_i),
                "ce_coord_surrogate_U": ce_coord,
                "ce_unknown_support_dmax8_simplex_U": ce_unk_simp,
                "ce_known_observed_support_simplex_U": ce_obs_simp,
                "full_pac_tier3_hi": float(ru["hi"]),
                "full_pac_coord_surrogate_U": uc_coord,
                "full_pac_known_observed_support_simplex_U": uc_obs_simp,
            })

    def _sum_simplex(rows: List[dict]) -> dict:
        return {
            "guarantee_tier": "high_precision_numerical_diagnostic_not_tier3_interval_verified",
            "n_tasks": len(rows),
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
            "e2_mean_native_room_lu_rhs": 0.0,
            "e2_mean_global_lu_rhs_per_map": float(sum(r["global_lu_rhs"] for r in ce_e2_rows) / 8.0),
            "e1_events": ce_e1_rows,
            "e2_events": ce_e2_rows,
        },
        "decision_c_simplex_vs_surrogate_diagnostic": {
            "e1_240k_passive": _sum_simplex(simplex_e1_rows),
            "e2_460k_3d": _sum_simplex(simplex_e2_rows),
        },
    }


def _render_r7a_figures(v4_data: dict, out_dir: Path) -> None:
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
    ax.set_xticklabels(
        ["Plug-In CE\n(94.5% Self-Underest.)", "SPQL Active\n(0% PAC Env. Viol.)", "SPQL Passive\n(0% PAC Env. Viol.)"],
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
            rhs_lbl = f"({rv:.0f} global RHS)"
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


def run_r7a_sidecar_audit(gates_only: bool = False) -> dict:
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
            "phase2_10_jsons_untouched": True,
            "phase2_json_count": len(fp2_10),
            "m233_original_archive": fm233_orig,
            "m233_clean_isolation_archive": {"file": m233_clean_fp.name, "sha256": m233_clean_sha, "verified_untouched": True},
            "phase3_v1_archive": verify_phase3_v1_archive_untouched(),
            "phase3_v2_archive": verify_phase3_v2_archive_untouched(),
            "phase3_v3_archive": verify_phase3_v3_archive_untouched(),
            "phase3_v4_archive": verify_phase3_v4_archive_untouched(),
        }

    pre_freeze = _verify_all_47_frozen()
    print("[Phase-III R7A] Running 21 Deterministic Contract Gates (P3-C01..P3-C21)...")
    gates = run_phase3_21_contract_gates()
    if not gates["ALL_21_PHASE3_CONTRACT_GATES_PASSED"]:
        raise RuntimeError(f"Contract gate failure: {gates}")
    print(f"  -> ALL 21 GATES PASSED in {gates['elapsed_ms']:.1f}ms!")
    if gates_only:
        return gates

    v4_data = json.loads((p3_dir / "p3_v4_r675_verified_results.json").read_text(encoding="utf-8"))

    print("[Phase-III R7A] Reconstructing all 672 actual frozen 67532c9 vs. current E3 CSR policies (zero rollouts)...")
    e3_cross = run_actual_cross_commit_e3_policy_comparison()

    print("[Phase-III R7A] Exporting 320 CE pred_val records + Decision-C Bauer simplex vs. coordinatewise diagnostic...")
    ce_and_simplex = run_ce_pred_val_and_simplex_gap_sidecar(v4_data)

    _render_r7a_figures(v4_data, p3_dir)
    post_freeze = _verify_all_47_frozen()
    assert pre_freeze == post_freeze

    rt_meta = collect_runtime_metadata()
    rt_meta["actual_parallel_workers"] = 1

    payload = _sanitize_for_strict_json({
        "milestone": "Phase3_R7A_CrossCommitCSR_CEPredVal_and_SimplexDiagnostic_Sidecar",
        "scope": "Non-destructive audit & diagnostic sidecar on frozen v4 seeds (0 benchmark timing edits, 0 continuous rollout reruns, 47/47 frozen archives untouched)",
        "elapsed_wall_s": float(time.perf_counter() - t0),
        "runtime_metadata": rt_meta,
        "phase3_manifest": compute_phase3_manifest(),
        "immutable_47_archives_verified": post_freeze,
        "event_denominator_accounting": {
            "total_saved_method_events_in_v4": 1952,
            "discrete_pac_four_inequality_events": 960,
            "discrete_pac_e1_events": 384,
            "discrete_pac_e2_events": 576,
            "discrete_pac_zero_slack_violations": 0,
            "discrete_pac_within_requested_eps_count": 0,
            "uncertified_plugin_ce_control_events": 320,
            "tier4_empirical_continuous_surrogate_events": 672,
        },
        "contract_21_gates": gates,
        "e3_actual_cross_commit_672_policy_audit": e3_cross,
        **ce_and_simplex,
    })

    out_fp = p3_dir / "p3_v4_r7a_sidecar_diagnostics.json"
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
    args = ap.parse_args()
    res = run_r7a_sidecar_audit(gates_only=args.gates_only)
    if args.gates_only:
        print(json.dumps(res, indent=2))
