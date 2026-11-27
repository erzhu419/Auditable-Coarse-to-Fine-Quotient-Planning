"""Milestone M2.3.2 Final Release Revision & Freeze Suite (`quotient_phase2.m232_final_closure`):
Closes All `b6ff40d` Audit Findings (`B6-01..B6-05`, `B6-D01..B6-D10`) Without Expanding Scope or
Overwriting Any Prior Frozen Artifact (`green_response`, `89761ff`, `ec75871`, or `b6ff40d`).

Deliverables (`100%` Standard RFC-8259 JSON with `allow_nan=False`):
  1. `m232_contract_and_ring_closure.json` (`WP-1` + `WP-2` Unit Counter Proofs):
       - Re-verifies `M2.0` (`15/15`), `WP0`, `M2.2` (`4/4`), and `EC-01..EC-06` + nested dyadic `11x11` (`0` warnings);
       - `B6-01`: Verifies shared `extract_directed_goal_ring_in_room` across `SeamFreePortal3DPlanner`,
         `solve_exact_reference_value`, and `MatrixFreeExactSchurKrylov3DPlanner` on `17^3` asymmetric-drift
         `interior_point`, `interior_3x3x3`, `portal_adjacent_slab_thickness{1,2,3}`, and `whole_goal_room`
         for `eps in {0.25, 0.01, 0.001}`, directly asserting all 4 inequalities `L <= V* <= J^{mu} <= U` & `U - L <= eps`;
       - Verifies `old_ring == new_ring` across ALL `792 / 792` official tasks (`0` changed rings);
       - `B6-02`: Verifies via LU solve counters that `CacheOn_Persistent`, `CacheL0Only`, and `QueryCold`
         all preserve intra-query memoization (`0` repeated solves within a query) while separating cross-query
         retention (`all levels` vs `L0 only` vs `none`);
       - `B6-03`: Verifies `SingleLUGoalCapacitance3DPlanner` carries `guarantee_tier = "high_accuracy_numerical_reference"`
         (`certified = False`) and rejects the 50-state `+1e-12` `PerturbedLU` fault injection via componentwise relative residual;
       - `B6-05`: Verifies `0` post-`query_ms` room backsolves on first & second root actions for BOTH `interior_start`
         AND `portal_start` across both `SeamFreePortal` and `MatrixFree`, plus immediate weakref GC release.
  2. `m232_targeted_replay_results.json` & `m232_targeted_replay_summary.png` (`WP-2` + `WP-3`, Strictly `workers = 1`):
       - Block A (`47^3` Fixed 3-Arm Cache Causal Ablation on `Replay 63000..63005`, `K = 24`, exact `2x` `3x3` Latin balance);
       - Block B (`47^3` & `59^3` Closest-Neighbor `Portal` vs `MatrixFree` on `Replay 63000..63005`, `K = 24`, exact `3 AB / 3 BA` balance);
       - Block C (`47^3` Continual `known_support_synthetic_local_operator_updates` `Portal` vs `MatrixFree`, `1+5` epochs, exact `3 AB / 3 BA` balance);
       - Saves per-task `(lo, hi, reference_value, policy_value)` records, reduces all counts/denominators from
         saved events (`0` hardcoded denominators), and explicitly records `relative_time_saving_pct = 100*(1 - T_cand/T_base)`
         and `engineering_20pct_time_saving_gate` (`PASS` vs `NOT_MET`).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse
import gc
import hashlib
import json
import sys
import time
import warnings
import weakref
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy import stats as sp_stats

from green_response import ProblemSpec, collect_runtime_metadata, enforce_single_thread_env, paired_stats
from green_response.port_solvers import build_grid_points
from quotient_phase2 import compute_phase2_manifest, verify_phase1_readonly_freeze
from quotient_phase2.m20_contracts import (
    Phase2DecisionCertificate,
    RecedingHorizonCertificateChain,
    run_m20_contract_verification_suite,
)
from quotient_phase2.m21_postprocess_closure import run_v10_online_and_contract_probes
from quotient_phase2.m22_portal_quotient_pilot import (
    build_room_decomposition,
    evaluate_twisted_lmdp_policy_exact,
    plan_unseen_goal_via_portal_quotient,
    run_part_a_multiroom_graph_suite,
)
from quotient_phase2.m23_m24_3d_portal_scale import (
    SeamFreePortal3DPlanner,
    build_3d_reflecting_obstacle_mmatrix,
    build_portal_level_blocks,
    evaluate_3d_deployed_policy_exact,
    extract_directed_goal_ring_in_room,
    generate_3d_multiroom_world,
    solve_and_verify_portal_howard_bounds,
)
from quotient_phase2.m231_audit_closure import run_m231_audit_closure_suite
from quotient_phase2.m231_fair_ablation import (
    MatrixFreeExactSchurKrylov3DPlanner,
    SingleLUGoalCapacitance3DPlanner,
    _portal_memory_ledger,
)


FROZEN_PRIOR_JSON_SHA256 = {
    "m20_contract_results.json": "bdad834622c2ab0215be84c2e3cfb4473f5b242e053d9b7bef8e792081c67004",
    "m21_ablation_results.json": "634c15e52fb3a8181f738baef40b8d7c30e690a8600a7cf1e30b6ca17a3c4fc1",
    "m21_economic_gate_verdict.json": "dca3212a6b34dda33952f58397c7d9ae3bade9058be083e98154d3f9d7b3a95b",
    "m21_post_audit_closure.json": "9b8d0db59265b0386dd3cf3812c1234aeb1e24aa782ca5b9d0fe20e3e2c967a1",
    "m22_pilot_results.json": "55d7e1ea176d2ad53d173595339c21216fc6f210857b5d28e30b98c163a3d892",
    "m23_m24_3d_results.json": "8fb6fb84749dfa640e5f5394c65db71426302a365e95a512c25dd896bce30f05",
    "m231_audit_closure.json": "4a0e2514a351ab7102dc9e54c6fce38dc9b5b8325ec8c277aa96aaa09257c4a9",
    "m231_fair_ablation_results.json": "f844a1028ec72ca7e0c26f77106b65d622412c8efb500fbe1e7f0869706cf003",
}


def verify_all_prior_artifacts_untouched() -> Dict[str, dict]:
    p2_dir = Path(__file__).resolve().parent
    out: Dict[str, dict] = {}
    for fn, exp_sha in FROZEN_PRIOR_JSON_SHA256.items():
        fp = p2_dir / fn
        if not fp.exists():
            raise RuntimeError(f"Missing frozen historical artifact: {fn}")
        actual = hashlib.sha256(fp.read_bytes()).hexdigest()
        if actual != exp_sha:
            raise RuntimeError(f"Frozen historical artifact {fn} modified: expected {exp_sha}, got {actual}")
        out[fn] = {"sha256": actual, "verified_untouched": True}
    return out


def _sanitize_for_strict_json(obj: Any) -> Any:
    """Recursively converts numpy scalars and non-finite floats so `json.dumps(..., allow_nan=False)` succeeds."""
    if isinstance(obj, dict):
        return {str(k): _sanitize_for_strict_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_strict_json(v) for v in obj]
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        fv = float(obj)
        if np.isnan(fv):
            return "NaN"
        if np.isposinf(fv):
            return "+Infinity"
        if np.isneginf(fv):
            return "-Infinity"
        return fv
    return obj


def _goal_hash(goal_mask: np.ndarray) -> str:
    idx = np.flatnonzero(goal_mask).astype(np.int64)
    return hashlib.sha1(idx.tobytes()).hexdigest()[:12]


def _one_sided_20pct_saving_p(cand_ms: np.ndarray, base_ms: np.ndarray) -> float:
    """Diagnostic one-sided paired t-test for `H1: E[T_cand - 0.80 * T_base] < 0` (`B6-D05`)."""
    d = np.asarray(cand_ms, dtype=float) - 0.80 * np.asarray(base_ms, dtype=float)
    n = len(d)
    if n < 2:
        return 1.0
    sd = float(np.std(d, ddof=1))
    if sd <= 0.0:
        return 0.0 if float(np.mean(d)) < 0.0 else 1.0
    t_stat = float(np.mean(d)) / (sd / np.sqrt(float(n)))
    return float(sp_stats.t.cdf(t_stat, df=n - 1))


def _sustained_crossing_k(c_cand: Sequence[float], c_base: Sequence[float]) -> Optional[int]:
    """Smallest `1`-based task index `k` from which `c_cand[j] <= c_base[j]` holds for all `j >= k-1` through `K`."""
    n = min(len(c_cand), len(c_base))
    for k0 in range(n):
        if all(float(c_cand[j]) <= float(c_base[j]) for j in range(k0, n)):
            return int(k0 + 1)
    return None


# ==============================================================================
# Part 1: Deterministic Contract, Goal-Ring (`B6-01`), Cache (`B6-02`), Pad (`B6-03`), & Readiness (`B6-05`) Suite
# ==============================================================================
def run_m232_contract_and_ring_closure(write_json: bool = False) -> dict:
    t0 = time.perf_counter()
    verify_phase1_readonly_freeze()
    prior_hashes = verify_all_prior_artifacts_untouched()
    enforce_single_thread_env()

    with warnings.catch_warnings():
        warnings.simplefilter("error")

        # 0. Prior suites (`M2.0` 15 gates, `WP0`, `M2.2` 4 graph families, AND full `M2.3.1 EC-01..EC-06 + 7.3`, `Closes C232-05`) in memory
        m231_ec_full = run_m231_audit_closure_suite(write_json=False)
        m20_res = run_m20_contract_verification_suite()
        wp0_res = run_v10_online_and_contract_probes()
        m22_res = run_part_a_multiroom_graph_suite()

        # Setup 17^3 asymmetric two-room single-portal world (`b_y = 0.13`)
        gn = 17
        spec = ProblemSpec(dim=3)
        free = np.ones((gn, gn, gn), dtype=bool)
        free[8, :, :] = False
        free[8, 6:11, 6:11] = True
        nodes = np.flatnonzero(free.ravel()).astype(np.int64)
        fpos = np.full(gn ** 3, -1, dtype=np.int64)
        fpos[nodes] = np.arange(len(nodes), dtype=np.int64)
        _, pts, _ = build_grid_points(3, spec.half_width, gn)
        q = np.full(len(nodes), 0.5, dtype=float)
        b = np.zeros((len(nodes), 3), dtype=float)
        b[:, 1] = 0.13
        A_csc = build_3d_reflecting_obstacle_mmatrix(spec, gn, free.ravel(), q, b)
        A_csr = A_csc.tocsr()

        def _idx(x: int, y: int, z: int) -> int:
            return int(fpos[(x * gn + y) * gn + z])

        s_left = _idx(3, 8, 8)
        p_door = _idx(8, 8, 8)
        g_far = _idx(13, 8, 8)

        pl_ref_probe = SeamFreePortal3DPlanner(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=0.25)

        # 1. Re-verify EC-01..EC-06 + Nested 11x11 in memory
        gm_pt = np.zeros(len(nodes), dtype=bool)
        gm_pt[g_far] = True
        ex_pt = np.flatnonzero(~gm_pt)
        z_pt_ex = spla.spsolve(A_csr[ex_pt, :][:, ex_pt].tocsc(), np.asarray((-A_csr[ex_pt, :][:, gm_pt]).sum(axis=1)).ravel())
        v0_pt = float(-spec.lam * np.log(z_pt_ex[int(np.searchsorted(ex_pt, s_left))]))
        widths_ec01 = []
        ec01_ok = True
        for phi in (-1000.0, 0.0, 100.0, 145.0, 160.0, 1000.0):
            rr_phi = pl_ref_probe.solve_unseen_goal(s_left, gm_pt, phi_goal=phi, materialize_full_z_sub=True)
            vp_phi = evaluate_3d_deployed_policy_exact(A_csr, gm_pt, phi, rr_phi["z_guide_full"], spec.lam, s_left)
            t_phi = v0_pt + phi
            widths_ec01.append(rr_phi["width"])
            if not (rr_phi["certified"] and rr_phi["lo"] - 1e-9 <= t_phi <= vp_phi + 1e-9 and vp_phi <= rr_phi["hi"] + 1e-9):
                ec01_ok = False
        ec01_ok = bool(ec01_ok and (max(widths_ec01) - min(widths_ec01) <= 1e-12))

        A_unr = sp.csr_matrix(np.array([[2.0, -1.0, 0.0], [-1.0, 2.0, 0.0], [0.0, 0.0, 1.0]], dtype=float))
        gm_unr = np.array([False, False, True])
        dec_u, _ = build_room_decomposition(A_unr, np.array([True, False, False]), [np.array([0])])
        r_m22_u = plan_unseen_goal_via_portal_quotient(A_unr, dec_u, 1, gm_unr, 0.0, 1.0, use_uncompressed_interface=False)
        ev_m22_u = evaluate_twisted_lmdp_policy_exact(A_unr, gm_unr, 0.0, np.array([0.0, 0.0, 1.0]), 1.0)
        c_unidx = Phase2DecisionCertificate("receding_horizon_root_action_enclosure", True, 0.1, 0.0, None, {0: (0.0, 0.0)}, 0, 4)
        chain_rep = RecedingHorizonCertificateChain(4, (c_unidx, c_unidx, c_unidx, c_unidx))
        coords_11 = np.array([(0.0, float(i), float(j)) for i in range(11) for j in range(11)], dtype=float)
        ids_11 = np.arange(len(coords_11), dtype=np.int64)
        cross_p = 0
        for lv in (1, 2, 3):
            b_prev = build_portal_level_blocks(ids_11, coords_11, lv - 1)
            par = np.empty(len(ids_11), dtype=np.int64)
            for pk, pb in enumerate(b_prev):
                par[pb] = pk
            for cb in build_portal_level_blocks(ids_11, coords_11, lv):
                if len(np.unique(par[cb])) > 1:
                    cross_p += 1
        prior_ec_all_ok = bool(
            m231_ec_full["ALL_EC75871_AUDIT_ISSUES_CLOSED"]
            and ec01_ok
            and (not r_m22_u["certified"])
            and np.isinf(ev_m22_u[0])
            and (not chain_rep.all_steps_certified)
            and cross_p == 0
        )

        # 2. B6-01: Complete Goal-Ring Support Suite (`interior_point`, `interior_3x3x3`, `portal_adjacent_slab_1..3`, `whole_goal_room`)
        goal_families: Dict[str, np.ndarray] = {"interior_point": gm_pt}
        g_333 = np.zeros((gn, gn, gn), dtype=bool)
        g_333[12:15, 7:10, 7:10] = True
        goal_families["interior_3x3x3"] = g_333.ravel()[nodes]
        for thick in (1, 2, 3):
            g_slab = np.zeros((gn, gn, gn), dtype=bool)
            g_slab[9 : 9 + thick, 6:11, 6:11] = True
            goal_families[f"portal_adjacent_slab_thickness{thick}"] = g_slab.ravel()[nodes]
        goal_families["whole_goal_room"] = (pl_ref_probe.room_of_f == pl_ref_probe.room_of_f[g_far])

        slu_17 = SingleLUGoalCapacitance3DPlanner(spec, A_csc, A_csr, eps_tol=0.001)
        b6_01_cases: List[dict] = []
        b6_01_pass = True

        for g_name, gm_case in goal_families.items():
            ext_c = np.flatnonzero(~gm_case)
            z_kill = np.ones(len(nodes), dtype=float)
            z_kill[ext_c] = spla.spsolve(A_csr[ext_c, :][:, ext_c].tocsc(), np.asarray((-A_csr[ext_c, :][:, gm_case]).sum(axis=1)).ravel())
            v_true = float(-spec.lam * np.log(z_kill[s_left]))
            r_slu_c = slu_17.solve_unseen_goal(s_left, gm_case)
            v_int_ref = pl_ref_probe.solve_exact_reference_value(s_left, gm_case)

            c_goal_id = int(pl_ref_probe.room_of_f[np.flatnonzero(gm_case)[0]])
            rn_goal = pl_ref_probe.room_nodes[c_goal_id]
            tl_goal = pl_ref_probe.room_tl[c_goal_id]
            _, ring_helper = extract_directed_goal_ring_in_room(A_csr, gm_case, rn_goal, pl_ref_probe.gamma_f[tl_goal])
            g_r_all = np.flatnonzero(gm_case[rn_goal]).astype(np.int64)
            ring_global = g_r_all[np.asarray((A_csr[ext_c, :][:, rn_goal[g_r_all]] < 0.0).sum(axis=0)).ravel() > 0]
            helper_matches_global = bool(np.array_equal(ring_helper, ring_global))
            ref_err = abs(v_int_ref - v_true)
            slu_err = abs(float(r_slu_c["value"]) - v_true)
            if (not helper_matches_global) or ref_err > 1e-10 or slu_err > 1e-11:
                b6_01_pass = False

            for eps_val in (0.25, 0.01, 0.001):
                for m_lbl, cls_p in (
                    ("SeamFreePortal3DPlanner", SeamFreePortal3DPlanner),
                    ("MatrixFreeExactSchurKrylov3DPlanner", MatrixFreeExactSchurKrylov3DPlanner),
                ):
                    pl_t = cls_p(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=eps_val)
                    rr_t = pl_t.solve_unseen_goal(s_left, gm_case)
                    z_pol = rr_t["policy"].materialize_full_grid_unit()
                    j_pol = evaluate_3d_deployed_policy_exact(A_csr, gm_case, 0.0, z_pol, spec.lam, s_left)
                    sub_res = float(np.max((A_csr @ z_pol)[ext_c]))
                    four_ok = bool(
                        rr_t["certified"]
                        and (rr_t["lo"] - 1e-9 <= v_true)
                        and (v_true <= j_pol + 1e-9)
                        and (j_pol <= rr_t["hi"] + 1e-9)
                        and (rr_t["hi"] - rr_t["lo"] <= eps_val + 1e-11)
                        and (j_pol - v_true <= eps_val + 1e-9)
                    )
                    if not four_ok:
                        b6_01_pass = False
                    b6_01_cases.append({
                        "goal_family": g_name,
                        "goal_nodes": int(np.sum(gm_case)),
                        "ring_nodes": int(len(ring_helper)),
                        "helper_matches_global_exterior_support": helper_matches_global,
                        "method": m_lbl,
                        "epsilon": eps_val,
                        "certified": bool(rr_t["certified"]),
                        "lo": float(rr_t["lo"]),
                        "true_optimal_V": v_true,
                        "deployed_policy_J": j_pol,
                        "hi": float(rr_t["hi"]),
                        "width": float(rr_t["width"]),
                        "actual_regret": float(j_pol - v_true),
                        "internal_ref_abs_err": ref_err,
                        "max_subsolution_residual": sub_res,
                        "four_inequalities_verified": four_ok,
                    })
                    del rr_t, pl_t

        # 3. Official 792-Task Ring Equivalence Verification (`0` tasks changed between old room-only ring and full ring!)
        official_ring_checked = 0
        official_ring_changed = 0
        official_cohorts = [
            ("Dev_35cubed", range(61000, 61006), 35, 24, True),
            ("Replay_35cubed", range(63000, 63006), 35, 24, True),
            ("Replay_47cubed", range(63000, 63006), 47, 24, True),
            ("Replay_59cubed", range(63000, 63006), 59, 24, True),
            ("Continual_47cubed", range(63000, 63006), 47, 36, False),
        ]
        # Note: `fit_gp_world=False` preserves the exact RNG sequence up to task generation? Wait: let's check!
        # In `generate_3d_multiroom_world`, `sample_noisy_probes` uses `seed + 500000` (separate RNG!), so `rng = default_rng(seed)`
        # generates the EXACT SAME free_3d, walls, doors, baffles, and `tasks` regardless of `fit_gp_world`!
        for _, sd_list, gn_chk, k_chk, _ in official_cohorts:
            for sd in sd_list:
                w_chk = generate_3d_multiroom_world(sd, gn_chk, ProblemSpec(dim=3), k_chk, fit_gp_world=False)
                A_chk = build_3d_reflecting_obstacle_mmatrix(w_chk["spec"], gn_chk, w_chk["free_mask"], w_chk["q_f"], w_chk["b_f"]).tocsr()
                # Discover rooms/portals identically
                from quotient_phase2.m23_m24_3d_portal_scale import discover_3d_bottleneck_planes_zero_hint
                from scipy.sparse.csgraph import connected_components
                xc, yc, zc = discover_3d_bottleneck_planes_zero_hint(w_chk["free_3d"])
                c_ijk = np.unravel_index(w_chk["free_nodes"], (gn_chk, gn_chk, gn_chk))
                gmask_f = np.isin(c_ijk[0], xc) | np.isin(c_ijk[1], yc) | np.isin(c_ijk[2], zc)
                gam_f = np.flatnonzero(gmask_f).astype(np.int64)
                int_f = np.flatnonzero(~gmask_f).astype(np.int64)
                n_rm, r_lb = connected_components((np.abs(A_chk[int_f, :][:, int_f]) + np.abs(A_chk[int_f, :][:, int_f].T)) > 0, directed=False)
                rm_of = np.full(len(w_chk["free_nodes"]), -1, dtype=np.int64)
                rm_nodes = []
                rm_tl = []
                for rc_i in range(n_rm):
                    rn_i = int_f[r_lb == rc_i]
                    rm_of[rn_i] = rc_i
                    rm_nodes.append(rn_i)
                    Arg_i = A_chk[rn_i, :][:, gam_f]
                    rm_tl.append(np.flatnonzero(np.asarray(np.abs(Arg_i).sum(axis=0)).ravel() > 0).astype(np.int64))
                for _, gm_tk in w_chk["tasks"]:
                    official_ring_checked += 1
                    cg_tk = int(rm_of[np.flatnonzero(gm_tk)[0]])
                    rn_tk = rm_nodes[cg_tk]
                    tl_tk = rm_tl[cg_tk]
                    in_g_tk = gm_tk[rn_tk]
                    ext_r_tk = np.flatnonzero(~in_g_tk)
                    g_r_tk = np.flatnonzero(in_g_tk).astype(np.int64)
                    A_rr_tk = A_chk[rn_tk, :][:, rn_tk]
                    old_ring_tk = g_r_tk[np.asarray(np.abs(A_rr_tk[ext_r_tk, :][:, g_r_tk]).sum(axis=0)).ravel() > 0]
                    _, new_ring_tk = extract_directed_goal_ring_in_room(A_chk, gm_tk, rn_tk, gam_f[tl_tk])
                    if not np.array_equal(old_ring_tk, new_ring_tk):
                        official_ring_changed += 1
        official_ring_compat_ok = bool(official_ring_checked == 792 and official_ring_changed == 0)

        # 4. B6-02: Cache Counter Probe (`intra-query memoization preserved; cross-query retention strictly separated`)
        gm_q2 = np.zeros(len(nodes), dtype=bool)
        gm_q2[_idx(12, 7, 8)] = True
        cache_probe_out: Dict[str, dict] = {}
        for mode_nm in ("CacheOn_Persistent", "CacheL0Only", "QueryCold"):
            pl_c = SeamFreePortal3DPlanner(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=0.005, use_portal_cache=True)
            # Intra-query repeated L0 read test (`must add 0 solves in ALL 3 modes!`)
            s_b0 = pl_c.local_lu_solve_calls
            _ = pl_c._ensure_portal_level(0, 0)
            intra_repeat_l0_solves = int(pl_c.local_lu_solve_calls - s_b0)
            q_solves = []
            entries_after = []
            for idx_q_c, gm_cur in enumerate((gm_pt, gm_q2)):
                if idx_q_c > 0:
                    if mode_nm == "CacheL0Only":
                        for kd in [k for k in pl_c.portal_cache.keys() if k[1] > 0]:
                            del pl_c.portal_cache[kd]
                    elif mode_nm == "QueryCold":
                        pl_c.portal_cache.clear()
                rc_q = pl_c.solve_unseen_goal(s_left, gm_cur)
                q_solves.append(int(rc_q["local_lu_solves"]))
                entries_after.append(int(len(pl_c.portal_cache)))
                del rc_q
            cache_probe_out[mode_nm] = {
                "intra_query_repeated_L0_solves": intra_repeat_l0_solves,
                "two_query_local_lu_solves": q_solves,
                "cache_entries_after_each_query": entries_after,
            }
            del pl_c
        b6_02_counter_ok = bool(
            all(v["intra_query_repeated_L0_solves"] == 0 for v in cache_probe_out.values())
            and (
                cache_probe_out["CacheOn_Persistent"]["two_query_local_lu_solves"][1]
                < cache_probe_out["CacheL0Only"]["two_query_local_lu_solves"][1]
                < cache_probe_out["QueryCold"]["two_query_local_lu_solves"][1]
            )
        )

        # 5. B6-03: 50-State Tridiagonal `+1e-12` PerturbedLU Fault-Injection Probe (`b6_reference_pad_probe.py`)
        n_tri = 50
        A_tri = sp.diags([-np.ones(n_tri - 1), np.full(n_tri, 3.0), -np.ones(n_tri - 1)], [-1, 0, 1], format="csc")
        gm_tri = np.zeros(n_tri, dtype=bool)
        gm_tri[-1] = True
        pl_tri = SingleLUGoalCapacitance3DPlanner(ProblemSpec(dim=3), A_tri, A_tri.tocsr())
        clean_tri = pl_tri.solve_unseen_goal(0, gm_tri)
        orig_lu_tri = pl_tri.lu

        class _PerturbedLU:
            def solve(self, *args, **kwargs):
                u = np.array(orig_lu_tri.solve(*args, **kwargs), copy=True)
                u[0] += 1e-12
                return u

        pl_tri.lu = _PerturbedLU()
        pert_tri = pl_tri.solve_unseen_goal(0, gm_tri)
        b6_03_ok = bool(
            clean_tri["reference_valid"]
            and (not clean_tri["certified"])
            and clean_tri["guarantee_tier"] == "high_accuracy_numerical_reference"
            and (not pert_tri["reference_valid"])
            and (not pert_tri["certified"])
            and pert_tri["status"] == "failed_componentwise_relative_residual"
        )

        # 6. B6-05: Portal-Start & Interior-Start Root-Action Readiness (`0` post-query room backsolves) + Weakref GC
        class _CountLU:
            def __init__(self, lu):
                self._lu = lu
                self.calls = 0

            def solve(self, *a, **kw):
                self.calls += 1
                return self._lu.solve(*a, **kw)

            def __getattr__(self, nm):
                return getattr(self._lu, nm)

        b6_05_out: Dict[str, dict] = {}
        b6_05_ok = True
        for m_nm, mk_fn in (
            ("SeamFreePortal3DPlanner", lambda: SeamFreePortal3DPlanner(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=0.25)),
            ("MatrixFreeExactSchurKrylov3DPlanner", lambda: MatrixFreeExactSchurKrylov3DPlanner(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=0.25)),
        ):
            pl_r = mk_fn()
            base_r = pl_r.base if hasattr(pl_r, "base") else pl_r
            base_r.hq_lus = [_CountLU(x) for x in base_r.hq_lus]
            sub_d = {}
            for st_lbl, st_node in (("interior_start", s_left), ("portal_start", p_door)):
                rr_st = pl_r.solve_unseen_goal(st_node, gm_pt)
                pol_st = rr_st["policy"]
                c0 = sum(x.calls for x in base_r.hq_lus)
                _, pr1 = pol_st.action_distribution(st_node)
                c1 = sum(x.calls for x in base_r.hq_lus)
                _, pr2 = pol_st.action_distribution(st_node)
                c2 = sum(x.calls for x in base_r.hq_lus)
                s1 = int(c1 - c0)
                s2 = int(c2 - c1)
                if s1 != 0 or s2 != 0 or abs(float(np.sum(pr1)) - 1.0) > 1e-12:
                    b6_05_ok = False
                sub_d[st_lbl] = {
                    "first_root_action_new_room_solves": s1,
                    "second_root_action_new_room_solves": s2,
                    "cached_rooms_at_return": sorted(int(x) for x in pol_st._room_z_cache.keys()),
                }
                del rr_st, pol_st
            wref = weakref.ref(base_r)
            del pl_r, base_r
            gc.collect()
            gc_freed = bool(wref() is None)
            if not gc_freed:
                b6_05_ok = False
            sub_d["weakref_freed_after_del"] = gc_freed
            b6_05_out[m_nm] = sub_d

    all_closed = bool(
        m20_res["ALL_15_COUNTEREXAMPLE_GATES_PASSED"]
        and wp0_res["ALL_V10_CLOSURE_PROBES_PASSED"]
        and m22_res["ALL_4_GRAPH_FAMILIES_PASSED"]
        and prior_ec_all_ok
        and b6_01_pass
        and official_ring_compat_ok
        and b6_02_counter_ok
        and b6_03_ok
        and b6_05_ok
    )

    payload = _sanitize_for_strict_json({
        "milestone": "M2.3.2_WP1_Contract_GoalRing_Cache_and_Readiness_Closure",
        "ALL_B6FF40D_CONTRACT_ISSUES_CLOSED": all_closed,
        "elapsed_ms": 1000.0 * (time.perf_counter() - t0),
        "runtime_metadata": collect_runtime_metadata(),
        "phase2_manifest": compute_phase2_manifest(),
        "prior_frozen_artifacts_verified": prior_hashes,
        "checks": {
            "m20_15_gates_passed": m20_res["ALL_15_COUNTEREXAMPLE_GATES_PASSED"],
            "wp0_passed": wp0_res["ALL_V10_CLOSURE_PROBES_PASSED"],
            "m22_4_graph_families_passed": m22_res["ALL_4_GRAPH_FAMILIES_PASSED"],
            "ec01_to_ec06_and_nested_dyadic_passed": prior_ec_all_ok,
            "B6_01_complete_goal_ring_support": {
                "pass": b6_01_pass,
                "total_family_method_eps_checks": len(b6_01_cases),
                "cases": b6_01_cases,
            },
            "official_792_task_ring_compatibility": {
                "pass": official_ring_compat_ok,
                "official_tasks_checked": official_ring_checked,
                "changed_ring_count": official_ring_changed,
            },
            "B6_02_cache_mode_counter_separation": {
                "pass": b6_02_counter_ok,
                "modes": cache_probe_out,
            },
            "B6_03_direct_reference_tier_and_perturbation_guard": {
                "pass": b6_03_ok,
                "clean_guarantee_tier": clean_tri["guarantee_tier"],
                "clean_certified_flag": clean_tri["certified"],
                "clean_comp_rel_res": clean_tri["componentwise_relative_residual"],
                "perturbed_reference_valid": pert_tri["reference_valid"],
                "perturbed_certified_flag": pert_tri["certified"],
                "perturbed_status": pert_tri["status"],
                "perturbed_global_residual": pert_tri["global_residual"],
                "perturbed_comp_rel_res": pert_tri["componentwise_relative_residual"],
            },
            "B6_05_portal_and_interior_root_readiness_and_gc": {
                "pass": b6_05_ok,
                "planners": b6_05_out,
            },
        },
    })

    if write_json:
        out_path = Path(__file__).resolve().parent / "m232_contract_and_ring_closure.json"
        out_path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    print(
        f"[M2.3.2 WP-1] ALL_B6FF40D_CONTRACT_ISSUES_CLOSED={all_closed} | "
        f"B6_01={b6_01_pass} (36/36) | Official792RingUnchanged={official_ring_compat_ok} ({official_ring_checked}/792) | "
        f"B6_02={b6_02_counter_ok} | B6_03={b6_03_ok} | B6_05={b6_05_ok} | write_json={write_json} | elapsed={payload['elapsed_ms']:.1f}ms"
    )
    if not all_closed:
        raise RuntimeError("M2.3.2 WP-1 contract closure check failed!")
    return payload


# ==============================================================================
# Part 2: Single-Worker (`workers = 1`) Exact-Balance Cache & Closest-Neighbor Replay
# ==============================================================================
CACHE3_MODES = ("CacheOn_Persistent", "CacheL0Only", "QueryCold")
PAIR2_ARMS = ("M231_Portal_CacheOn", "MatrixFree_ExactSchur_Krylov")


def _build_task_event(
    *,
    block_id: str,
    seed: int,
    gn: int,
    epoch: int,
    task_index: int,
    s_f: int,
    gm: np.ndarray,
    method_id: str,
    res: dict,
    v_ref: float,
    ref_valid: bool,
    j_pol: Optional[float],
) -> dict:
    lo = float(res["lo"])
    hi = float(res["hi"])
    is_fin = bool(np.isfinite(lo) and np.isfinite(hi) and np.isfinite(v_ref))
    cert = bool(res["certified"])
    val_ok = bool(cert and ref_valid and is_fin and (lo - 1e-7 <= v_ref <= hi + 1e-7) and (hi - lo <= 0.25 + 1e-6))
    pol_eval = j_pol is not None
    if pol_eval:
        jf = float(j_pol)
        four_ok = bool(
            val_ok
            and np.isfinite(jf)
            and (lo - 1e-7 <= v_ref)
            and (v_ref <= jf + 1e-6)
            and (jf <= hi + 1e-6)
            and (hi - lo <= 0.25 + 1e-6)
        )
    else:
        four_ok = None
    return {
        "block_id": block_id,
        "seed": int(seed),
        "grid_n": int(gn),
        "operator_epoch": int(epoch),
        "task_index": int(task_index),
        "start_state": int(s_f),
        "goal_signature_sha1": _goal_hash(gm),
        "method_id": method_id,
        "guarantee_tier": str(res["guarantee_tier"]),
        "status": str(res["status"]),
        "certified": cert,
        "epsilon": 0.25,
        "lo": lo,
        "hi": hi,
        "width": float(hi - lo),
        "reference_value": float(v_ref),
        "reference_valid": bool(ref_valid),
        "value_enclosure_satisfied": val_ok,
        "policy_evaluated": pol_eval,
        "policy_value": float(j_pol) if pol_eval else None,
        "four_inequalities_satisfied": four_ok,
        "query_ms": float(res["query_ms"]),
        "active_coarse_dofs": int(res.get("active_dofs", len(gm) * 0)),
        "used_defect_closure": bool(res.get("used_defect_closure", True)),
        "operational_local_lu_rhs_solves": int(res.get("operational_local_lu_rhs_solves", res.get("local_lu_solves", 0))),
        "evaluation_materialization_rhs_solves": int(res.get("evaluation_materialization_rhs_solves", 0)),
        "local_lu_solves": int(res.get("local_lu_solves", 0)),
    }


def _reduce_event_ledger(events: List[dict]) -> dict:
    """Computes all verification denominators and violations strictly by reducing over saved event rows (`B6-D08`)."""
    n_tot = len(events)
    n_cert = sum(1 for e in events if e["certified"])
    n_ref_ok = sum(1 for e in events if e["reference_valid"])
    n_val_ok = sum(1 for e in events if e["value_enclosure_satisfied"])
    n_val_viol = n_tot - n_val_ok
    pol_rows = [e for e in events if e["policy_evaluated"]]
    n_pol = len(pol_rows)
    n_four_ok = sum(1 for e in pol_rows if e["four_inequalities_satisfied"] is True)
    n_pol_viol = n_pol - n_four_ok
    max_reg = max((float(e["policy_value"]) - float(e["reference_value"]) for e in pol_rows), default=0.0)
    return {
        "total_task_events": n_tot,
        "certified_count": n_cert,
        "valid_reference_checked_count": n_ref_ok,
        "value_enclosure_satisfied_count": n_val_ok,
        "value_enclosure_violations": n_val_viol,
        "deployed_policy_evaluated_count": n_pol,
        "four_inequalities_satisfied_count": n_four_ok,
        "four_inequalities_violations": n_pol_viol,
        "max_deployed_regret": max(0.0, float(max_reg)),
        "continuous_or_real_world_evaluated_count": 0,
        "ALL_SAVED_EVENTS_SATISFIED": bool(n_tot > 0 and n_cert == n_tot and n_val_viol == 0 and n_pol_viol == 0),
    }


def _run_47_cache_and_pair_single_map(seed: int, map_idx: int, n_tasks: int) -> dict:
    """Runs `47^3` Replay map `seed` (`workers = 1`):
      - Block A: Exact `3x3` cyclic Latin-balanced 3-arm cache study (`CacheOn_Persistent`, `CacheL0Only`, `QueryCold`);
      - Block B: Exact `AB / BA` position-balanced closest-neighbor pair (`M231_Portal_CacheOn` vs `MatrixFree_ExactSchur_Krylov`);
      - Untimed Post-Pass: Independent `SingleLU` numerical reference + `12` deployed-policy evaluations per arm.
    """
    enforce_single_thread_env()
    gn = 47
    world = generate_3d_multiroom_world(seed=seed, gn=gn, spec=ProblemSpec(dim=3), n_tasks=n_tasks, fit_gp_world=True)
    spec = world["spec"]
    lam = float(spec.lam)
    free_3d = world["free_3d"]
    free_mask = world["free_mask"]
    free_nodes = world["free_nodes"]
    pts_f = world["pts_f"]
    tasks = world["tasks"]

    t_op = time.perf_counter()
    A_csc = build_3d_reflecting_obstacle_mmatrix(spec, gn, free_mask, world["q_f"], world["b_f"])
    A_csr = A_csc.tocsr()
    op_asm_ms = 1000.0 * (time.perf_counter() - t_op)

    # 1. Block A: 3-Arm Cache Causal Study (`exact 2x 3x3 Latin square across 6 maps`)
    cache_order = [CACHE3_MODES[(map_idx + k) % 3] for k in range(3)]
    cache_raw: Dict[str, dict] = {}
    for rk, c_mode in enumerate(cache_order):
        gc.collect()
        pl = SeamFreePortal3DPlanner(spec, gn, free_3d, free_nodes, pts_f, A_csr, eps_tol=0.25, use_portal_cache=True)
        init_ms = pl.offline_init_ms
        raw_rows = []
        guides_12: Dict[int, np.ndarray] = {}
        n_pol = min(12, n_tasks) if c_mode == "CacheOn_Persistent" else 0
        for t_i, (s_f, gm_k) in enumerate(tasks):
            if t_i > 0:
                if c_mode == "CacheL0Only":
                    for kd in [k for k in pl.portal_cache.keys() if k[1] > 0]:
                        del pl.portal_cache[kd]
                elif c_mode == "QueryCold":
                    pl.portal_cache.clear()
            rr = pl.solve_unseen_goal(s_f, gm_k, phi_goal=0.0, materialize_full_z_sub=(t_i < n_pol))
            if t_i < n_pol and rr["z_guide_full"] is not None:
                guides_12[t_i] = rr["z_guide_full"]
            raw_rows.append({
                "lo": rr["lo"],
                "hi": rr["hi"],
                "certified": rr["certified"],
                "guarantee_tier": rr["guarantee_tier"],
                "status": rr["status"],
                "query_ms": rr["query_ms"],
                "active_dofs": rr["active_dofs"],
                "used_defect_closure": rr["used_defect_closure"],
                "operational_local_lu_rhs_solves": rr["operational_local_lu_rhs_solves"],
                "evaluation_materialization_rhs_solves": rr["evaluation_materialization_rhs_solves"],
                "local_lu_solves": rr["local_lu_solves"],
            })
            del rr
        mem_led = _portal_memory_ledger(pl)
        del pl
        gc.collect()
        q_arr = [x["query_ms"] for x in raw_rows]
        cache_raw[c_mode] = {
            "exec_rank": rk,
            "init_ms": init_ms,
            "total_ms": init_ms + float(np.sum(q_arr)),
            "mean_query_ms": float(np.mean(q_arr)),
            "first6_query_ms": float(np.mean(q_arr[:6])),
            "last6_query_ms": float(np.mean(q_arr[-6:])),
            "prefix_cumulative_ms": [float(x) for x in np.cumsum([init_ms] + q_arr)[1:]],
            "total_operational_local_lu_rhs_solves": int(sum(x["operational_local_lu_rhs_solves"] for x in raw_rows)),
            "total_evaluation_materialization_rhs_solves": int(sum(x["evaluation_materialization_rhs_solves"] for x in raw_rows)),
            "total_local_lu_solves": int(sum(x["local_lu_solves"] for x in raw_rows)),
            "factor_plus_response_cache_bytes": mem_led,
            "_raw_rows": raw_rows,
            "_guides": guides_12,
        }

    # 2. Block B (`47^3`): Exact `AB / BA` Closest-Neighbor Head-to-Head (`Portal` vs `MatrixFree`)
    pair_order = list(PAIR2_ARMS) if (map_idx % 2 == 0) else list(reversed(PAIR2_ARMS))
    pair_raw: Dict[str, dict] = {}
    n_pol_pair = min(12, n_tasks)
    for rk, arm_nm in enumerate(pair_order):
        gc.collect()
        if arm_nm == "M231_Portal_CacheOn":
            pl_p = SeamFreePortal3DPlanner(spec, gn, free_3d, free_nodes, pts_f, A_csr, eps_tol=0.25, use_portal_cache=True)
            init_ms = pl_p.offline_init_ms
            raw_rows = []
            guides_p: Dict[int, np.ndarray] = {}
            for t_i, (s_f, gm_k) in enumerate(tasks):
                rr = pl_p.solve_unseen_goal(s_f, gm_k, phi_goal=0.0, materialize_full_z_sub=(t_i < n_pol_pair))
                if t_i < n_pol_pair and rr["z_guide_full"] is not None:
                    guides_p[t_i] = rr["z_guide_full"]
                raw_rows.append({
                    "lo": rr["lo"],
                    "hi": rr["hi"],
                    "certified": rr["certified"],
                    "guarantee_tier": rr["guarantee_tier"],
                    "status": rr["status"],
                    "query_ms": rr["query_ms"],
                    "eager_ms": rr["eager_materialize_ms"],
                    "active_dofs": rr["active_dofs"],
                    "used_defect_closure": rr["used_defect_closure"],
                    "operational_local_lu_rhs_solves": rr["operational_local_lu_rhs_solves"],
                    "evaluation_materialization_rhs_solves": rr["evaluation_materialization_rhs_solves"],
                    "local_lu_solves": rr["local_lu_solves"],
                })
                del rr
            del pl_p
            gc.collect()
        else:
            pl_mf = MatrixFreeExactSchurKrylov3DPlanner(spec, gn, free_3d, free_nodes, pts_f, A_csr, eps_tol=0.25)
            init_ms = pl_mf.offline_init_ms
            raw_rows = []
            guides_p = {}
            for t_i, (s_f, gm_k) in enumerate(tasks):
                rr = pl_mf.solve_unseen_goal(s_f, gm_k, phi_goal=0.0)
                if t_i < n_pol_pair and rr["policy"] is not None:
                    guides_p[t_i] = rr["policy"].materialize_full_grid_unit()
                raw_rows.append({
                    "lo": rr["lo"],
                    "hi": rr["hi"],
                    "certified": rr["certified"],
                    "guarantee_tier": rr["guarantee_tier"],
                    "status": rr["status"],
                    "query_ms": rr["query_ms"],
                    "eager_ms": 0.0,
                    "active_dofs": int(pl_mf.base.n_g),
                    "used_defect_closure": True,
                    "local_lu_solves": rr["local_lu_solves"],
                })
                del rr
            del pl_mf
            gc.collect()
        q_arr = [x["query_ms"] for x in raw_rows]
        pair_raw[arm_nm] = {
            "exec_rank": rk,
            "init_ms": init_ms,
            "total_ms": init_ms + float(np.sum(q_arr)),
            "mean_query_ms": float(np.mean(q_arr)),
            "prefix_cumulative_ms": [float(x) for x in np.cumsum([init_ms] + q_arr)[1:]],
            "defect_closure_count": int(sum(1 for x in raw_rows if x["used_defect_closure"])),
            "total_local_lu_solves": int(sum(x["local_lu_solves"] for x in raw_rows)),
            "_raw_rows": raw_rows,
            "_guides": guides_p,
        }

    # 3. Untimed Post-Pass: Independent `SingleLU` Reference + Deployed Policy Evaluation (`L <= V* <= J <= U`)
    gc.collect()
    slu = SingleLUGoalCapacitance3DPlanner(spec, A_csc, A_csr)
    ref_vals, ref_ok = [], []
    for s_f, gm_k in tasks:
        rs = slu.solve_unseen_goal(s_f, gm_k)
        ref_vals.append(float(rs["value"]))
        ref_ok.append(bool(rs["reference_valid"]))
        del rs
    slu_bytes = slu.factor_bytes()
    del slu
    gc.collect()

    cache_events: List[dict] = []
    for c_mode, cd in cache_raw.items():
        r_rows = cd.pop("_raw_rows")
        g_map = cd.pop("_guides")
        for t_i, rr_x in enumerate(r_rows):
            s_f, gm_k = tasks[t_i]
            jp = evaluate_3d_deployed_policy_exact(A_csr, gm_k, 0.0, g_map[t_i], lam, s_f) if t_i in g_map else None
            cache_events.append(_build_task_event(
                block_id="cache_ablation_47cubed",
                seed=seed,
                gn=gn,
                epoch=0,
                task_index=t_i,
                s_f=s_f,
                gm=gm_k,
                method_id=c_mode,
                res=rr_x,
                v_ref=ref_vals[t_i],
                ref_valid=ref_ok[t_i],
                j_pol=jp,
            ))

    pair_events: List[dict] = []
    for arm_nm, pd in pair_raw.items():
        r_rows = pd.pop("_raw_rows")
        g_map = pd.pop("_guides")
        for t_i, rr_x in enumerate(r_rows):
            s_f, gm_k = tasks[t_i]
            jp = evaluate_3d_deployed_policy_exact(A_csr, gm_k, 0.0, g_map[t_i], lam, s_f) if t_i in g_map else None
            pair_events.append(_build_task_event(
                block_id="pair_abba_47cubed",
                seed=seed,
                gn=gn,
                epoch=0,
                task_index=t_i,
                s_f=s_f,
                gm=gm_k,
                method_id=arm_nm,
                res=rr_x,
                v_ref=ref_vals[t_i],
                ref_valid=ref_ok[t_i],
                j_pol=jp,
            ))

    return {
        "seed": seed,
        "gn": gn,
        "n_free_dofs": int(len(free_nodes)),
        "shared_gp_fit_ms": float(world["gp_fit_ms"]),
        "shared_operator_assembly_ms": op_asm_ms,
        "singlelu_factor_bytes": slu_bytes,
        "cache_execution_order": cache_order,
        "cache_arms": cache_raw,
        "cache_events": cache_events,
        "pair_execution_order": pair_order,
        "pair_arms": pair_raw,
        "pair_events": pair_events,
    }


def _run_59_pair_single_map(seed: int, map_idx: int, n_tasks: int) -> dict:
    """Runs `59^3` Replay map `seed` (`workers = 1`, exact `3 AB / 3 BA` balance) + `SingleLU` & `6` policy evals/arm."""
    enforce_single_thread_env()
    gn = 59
    world = generate_3d_multiroom_world(seed=seed, gn=gn, spec=ProblemSpec(dim=3), n_tasks=n_tasks, fit_gp_world=True)
    spec = world["spec"]
    lam = float(spec.lam)
    free_3d = world["free_3d"]
    free_mask = world["free_mask"]
    free_nodes = world["free_nodes"]
    pts_f = world["pts_f"]
    tasks = world["tasks"]

    t_op = time.perf_counter()
    A_csc = build_3d_reflecting_obstacle_mmatrix(spec, gn, free_mask, world["q_f"], world["b_f"])
    A_csr = A_csc.tocsr()
    op_asm_ms = 1000.0 * (time.perf_counter() - t_op)

    pair_order = list(PAIR2_ARMS) if (map_idx % 2 == 0) else list(reversed(PAIR2_ARMS))
    pair_raw: Dict[str, dict] = {}
    n_pol = min(6, n_tasks)

    for rk, arm_nm in enumerate(pair_order):
        gc.collect()
        if arm_nm == "M231_Portal_CacheOn":
            pl_p = SeamFreePortal3DPlanner(spec, gn, free_3d, free_nodes, pts_f, A_csr, eps_tol=0.25, use_portal_cache=True)
            init_ms = pl_p.offline_init_ms
            raw_rows = []
            guides_p: Dict[int, np.ndarray] = {}
            for t_i, (s_f, gm_k) in enumerate(tasks):
                rr = pl_p.solve_unseen_goal(s_f, gm_k, phi_goal=0.0, materialize_full_z_sub=(t_i < n_pol))
                if t_i < n_pol and rr["z_guide_full"] is not None:
                    guides_p[t_i] = rr["z_guide_full"]
                raw_rows.append({
                    "lo": rr["lo"],
                    "hi": rr["hi"],
                    "certified": rr["certified"],
                    "guarantee_tier": rr["guarantee_tier"],
                    "status": rr["status"],
                    "query_ms": rr["query_ms"],
                    "active_dofs": rr["active_dofs"],
                    "used_defect_closure": rr["used_defect_closure"],
                    "operational_local_lu_rhs_solves": rr.get("operational_local_lu_rhs_solves", rr["local_lu_solves"]),
                    "evaluation_materialization_rhs_solves": rr.get("evaluation_materialization_rhs_solves", 0),
                    "local_lu_solves": rr["local_lu_solves"],
                })
                del rr
            mem_led = _portal_memory_ledger(pl_p)
            del pl_p
            gc.collect()
        else:
            pl_mf = MatrixFreeExactSchurKrylov3DPlanner(spec, gn, free_3d, free_nodes, pts_f, A_csr, eps_tol=0.25)
            init_ms = pl_mf.offline_init_ms
            raw_rows = []
            guides_p = {}
            for t_i, (s_f, gm_k) in enumerate(tasks):
                rr = pl_mf.solve_unseen_goal(s_f, gm_k, phi_goal=0.0)
                if t_i < n_pol and rr["policy"] is not None:
                    guides_p[t_i] = rr["policy"].materialize_full_grid_unit()
                raw_rows.append({
                    "lo": rr["lo"],
                    "hi": rr["hi"],
                    "certified": rr["certified"],
                    "guarantee_tier": rr["guarantee_tier"],
                    "status": rr["status"],
                    "query_ms": rr["query_ms"],
                    "active_dofs": int(pl_mf.base.n_g),
                    "used_defect_closure": True,
                    "local_lu_solves": rr["local_lu_solves"],
                })
                del rr
            mem_led = None
            del pl_mf
            gc.collect()

        q_arr = [x["query_ms"] for x in raw_rows]
        pair_raw[arm_nm] = {
            "exec_rank": rk,
            "init_ms": init_ms,
            "total_ms": init_ms + float(np.sum(q_arr)),
            "mean_query_ms": float(np.mean(q_arr)),
            "first6_query_ms": float(np.mean(q_arr[:6])),
            "last6_query_ms": float(np.mean(q_arr[-6:])),
            "prefix_cumulative_ms": [float(x) for x in np.cumsum([init_ms] + q_arr)[1:]],
            "defect_closure_count": int(sum(1 for x in raw_rows if x["used_defect_closure"])),
            "total_local_lu_solves": int(sum(x["local_lu_solves"] for x in raw_rows)),
            "factor_plus_response_cache_bytes": mem_led,
            "_raw_rows": raw_rows,
            "_guides": guides_p,
        }

    gc.collect()
    slu = SingleLUGoalCapacitance3DPlanner(spec, A_csc, A_csr)
    ref_vals, ref_ok = [], []
    for s_f, gm_k in tasks:
        rs = slu.solve_unseen_goal(s_f, gm_k)
        ref_vals.append(float(rs["value"]))
        ref_ok.append(bool(rs["reference_valid"]))
        del rs
    slu_bytes = slu.factor_bytes()
    del slu
    gc.collect()

    pair_events: List[dict] = []
    for arm_nm, pd in pair_raw.items():
        r_rows = pd.pop("_raw_rows")
        g_map = pd.pop("_guides")
        for t_i, rr_x in enumerate(r_rows):
            s_f, gm_k = tasks[t_i]
            jp = evaluate_3d_deployed_policy_exact(A_csr, gm_k, 0.0, g_map[t_i], lam, s_f) if t_i in g_map else None
            pair_events.append(_build_task_event(
                block_id="pair_abba_59cubed",
                seed=seed,
                gn=gn,
                epoch=0,
                task_index=t_i,
                s_f=s_f,
                gm=gm_k,
                method_id=arm_nm,
                res=rr_x,
                v_ref=ref_vals[t_i],
                ref_valid=ref_ok[t_i],
                j_pol=jp,
            ))

    return {
        "seed": seed,
        "gn": gn,
        "n_free_dofs": int(len(free_nodes)),
        "shared_gp_fit_ms": float(world["gp_fit_ms"]),
        "shared_operator_assembly_ms": op_asm_ms,
        "singlelu_factor_bytes": slu_bytes,
        "pair_execution_order": pair_order,
        "pair_arms": pair_raw,
        "pair_events": pair_events,
    }


def _run_continual_47_abba_single_map(seed: int, map_idx: int, n_epochs: int, tasks_per_ep: int) -> dict:
    """Runs `47^3` Continual `known_support_synthetic_local_operator_updates` (`workers = 1`, exact `3 AB / 3 BA` order):
    Each arm runs its entire `1 + n_epochs` stream without interleaved reference solves; post-timing pass computes
    independent `SingleLU` references across all `36` tasks AND `evaluate_3d_deployed_policy_exact` on task `0` of
    every epoch (`6` continual policy evaluations per map per arm!).
    """
    enforce_single_thread_env()
    gn = 47
    tot_tasks = (1 + n_epochs) * tasks_per_ep
    world = generate_3d_multiroom_world(seed=seed, gn=gn, spec=ProblemSpec(dim=3), n_tasks=tot_tasks, fit_gp_world=False)
    spec = world["spec"]
    lam = float(spec.lam)
    free_3d = world["free_3d"]
    free_mask = world["free_mask"]
    free_nodes = world["free_nodes"]
    pts_f = world["pts_f"]
    tasks_all = world["tasks"]

    # Pre-build deterministic operator trajectory `(A_0..A_5)` once (`measuring shared operator assembly/rebuild`)
    pl_tmp = SeamFreePortal3DPlanner(
        spec, gn, free_3d, free_nodes, pts_f,
        build_3d_reflecting_obstacle_mmatrix(spec, gn, free_mask, world["q_f"], world["b_f"]).tocsr(),
        eps_tol=0.25,
    )
    room_nodes_ref = [rn.copy() for rn in pl_tmp.room_nodes]
    n_rooms_ref = pl_tmp.n_rooms
    del pl_tmp
    gc.collect()

    q_cur = world["q_f"].copy()
    b_cur = world["b_f"].copy()
    t0_op = time.perf_counter()
    A0_csc = build_3d_reflecting_obstacle_mmatrix(spec, gn, free_mask, q_cur, b_cur)
    A0_csr = A0_csc.tocsr()
    op_init_ms = 1000.0 * (time.perf_counter() - t0_op)

    epoch_ops: List[Tuple[sp.csc_matrix, sp.csr_matrix, List[int], float]] = [(A0_csc, A0_csr, [], op_init_ms)]
    rng_ep = np.random.default_rng(seed + 810000)
    for _ in range(n_epochs):
        mod_rooms = [int(c) for c in rng_ep.choice(n_rooms_ref, size=2, replace=False)]
        for c in mod_rooms:
            rn_c = room_nodes_ref[c]
            ctr_c = np.mean(pts_f[rn_c], axis=0, keepdims=True)
            bump = float(rng_ep.uniform(0.18, 0.42)) * np.exp(-np.sum((pts_f[rn_c] - ctr_c) ** 2, axis=1) / 0.12)
            q_cur[rn_c] = np.clip(q_cur[rn_c] + bump, 0.05, 6.0)
            b_cur[rn_c, :] += rng_ep.normal(0.0, 0.05, size=(1, 3))
        t_rb = time.perf_counter()
        At_csc = build_3d_reflecting_obstacle_mmatrix(spec, gn, free_mask, q_cur, b_cur)
        At_csr = At_csc.tocsr()
        rb_ms = 1000.0 * (time.perf_counter() - t_rb)
        epoch_ops.append((At_csc, At_csr, mod_rooms, rb_ms))

    pair_order = list(PAIR2_ARMS) if (map_idx % 2 == 0) else list(reversed(PAIR2_ARMS))
    arm_streams: Dict[str, dict] = {}

    for rk, arm_nm in enumerate(pair_order):
        gc.collect()
        if arm_nm == "M231_Portal_CacheOn":
            pl_obj: Any = SeamFreePortal3DPlanner(spec, gn, free_3d, free_nodes, pts_f, epoch_ops[0][1], eps_tol=0.25, use_portal_cache=True)
            init_ms = pl_obj.offline_init_ms
        else:
            pl_obj = MatrixFreeExactSchurKrylov3DPlanner(spec, gn, free_3d, free_nodes, pts_f, epoch_ops[0][1], eps_tol=0.25)
            init_ms = pl_obj.offline_init_ms

        life_ms = op_init_ms + init_ms
        marg_ms = 0.0
        retained_l1_l3: List[int] = []
        raw_task_rows: List[Tuple[int, int, dict, Optional[np.ndarray]]] = []

        for ep_idx, (_, A_ep_csr, mod_r, rb_ms) in enumerate(epoch_ops):
            if ep_idx > 0:
                upd = pl_obj.update_world_operator(A_ep_csr, mod_r, portal_diag_changed=False)
                life_ms += rb_ms + upd["update_ms"]
                marg_ms += rb_ms + upd["update_ms"]
                retained_l1_l3.append(int(upd["retained_cache_entries"]))
            ep_slice = tasks_all[ep_idx * tasks_per_ep : (ep_idx + 1) * tasks_per_ep]
            for local_ti, (s_f, gm_k) in enumerate(ep_slice):
                g_ti = ep_idx * tasks_per_ep + local_ti
                eval_pol_here = (local_ti == 0)  # 1 deployed-policy eval per epoch (`6` per map!)
                if arm_nm == "M231_Portal_CacheOn":
                    rr = pl_obj.solve_unseen_goal(s_f, gm_k, phi_goal=0.0, materialize_full_z_sub=eval_pol_here)
                    z_pol = rr["z_guide_full"] if eval_pol_here else None
                else:
                    rr = pl_obj.solve_unseen_goal(s_f, gm_k, phi_goal=0.0)
                    z_pol = rr["policy"].materialize_full_grid_unit() if (eval_pol_here and rr["policy"] is not None) else None
                life_ms += rr["query_ms"]
                if ep_idx > 0:
                    marg_ms += rr["query_ms"]
                raw_task_rows.append((
                    ep_idx,
                    g_ti,
                    {
                        "lo": rr["lo"],
                        "hi": rr["hi"],
                        "certified": rr["certified"],
                        "guarantee_tier": rr["guarantee_tier"],
                        "status": rr["status"],
                        "query_ms": rr["query_ms"],
                        "active_dofs": rr.get("active_dofs", int(pl_obj.base.n_g) if hasattr(pl_obj, "base") else 0),
                        "used_defect_closure": rr.get("used_defect_closure", True),
                        "operational_local_lu_rhs_solves": rr.get("operational_local_lu_rhs_solves", rr.get("local_lu_solves", 0)),
                        "evaluation_materialization_rhs_solves": rr.get("evaluation_materialization_rhs_solves", 0),
                        "local_lu_solves": rr.get("local_lu_solves", 0),
                    },
                    z_pol,
                ))
                del rr

        del pl_obj
        gc.collect()
        arm_streams[arm_nm] = {
            "exec_rank": rk,
            "lifecycle_incl_rebuild_ms": life_ms,
            "post_init_marginal_incl_rebuild_ms": marg_ms,
            "mean_retained_l1_l3_entries": float(np.mean(retained_l1_l3)) if retained_l1_l3 else 0.0,
            "_raw_rows": raw_task_rows,
        }

    # Untimed Post-Pass: Independent `SingleLU` across all `1 + n_epochs` operators + continual policy evaluations
    ref_by_gti: Dict[int, Tuple[float, bool]] = {}
    for ep_idx, (A_ep_csc, A_ep_csr, _, _) in enumerate(epoch_ops):
        gc.collect()
        slu_ep = SingleLUGoalCapacitance3DPlanner(spec, A_ep_csc, A_ep_csr)
        ep_slice = tasks_all[ep_idx * tasks_per_ep : (ep_idx + 1) * tasks_per_ep]
        for local_ti, (s_f, gm_k) in enumerate(ep_slice):
            g_ti = ep_idx * tasks_per_ep + local_ti
            rs = slu_ep.solve_unseen_goal(s_f, gm_k)
            ref_by_gti[g_ti] = (float(rs["value"]), bool(rs["reference_valid"]))
            del rs
        del slu_ep

    cont_events: List[dict] = []
    for arm_nm, ad in arm_streams.items():
        r_rows = ad.pop("_raw_rows")
        for ep_idx, g_ti, rr_x, z_pol in r_rows:
            s_f, gm_k = tasks_all[g_ti]
            A_ep_csr = epoch_ops[ep_idx][1]
            v_ref, r_ok = ref_by_gti[g_ti]
            jp = evaluate_3d_deployed_policy_exact(A_ep_csr, gm_k, 0.0, z_pol, lam, s_f) if z_pol is not None else None
            cont_events.append(_build_task_event(
                block_id="continual_abba_47cubed",
                seed=seed,
                gn=gn,
                epoch=ep_idx,
                task_index=g_ti,
                s_f=s_f,
                gm=gm_k,
                method_id=arm_nm,
                res=rr_x,
                v_ref=v_ref,
                ref_valid=r_ok,
                j_pol=jp,
            ))

    return {
        "seed": seed,
        "gn": gn,
        "stream_name": "known_support_synthetic_local_operator_updates",
        "shared_operator_rebuild_marginal_ms": float(sum(x[3] for x in epoch_ops[1:])),
        "pair_execution_order": pair_order,
        "arms": arm_streams,
        "events": cont_events,
    }


def _summarize_pair_block(rows: List[dict], block_label: str, arms_key: str, events_key: str, time_key: str) -> dict:
    p_arr = np.array([r[arms_key]["M231_Portal_CacheOn"][time_key] for r in rows], dtype=float)
    mf_arr = np.array([r[arms_key]["MatrixFree_ExactSchur_Krylov"][time_key] for r in rows], dtype=float)
    p_mean = float(np.mean(p_arr))
    mf_mean = float(np.mean(mf_arr))
    speedup = mf_mean / p_mean
    saving_pct = 100.0 * (1.0 - (p_mean / mf_mean))
    p_diff = paired_stats(p_arr - mf_arr) if len(rows) >= 2 else None
    p_20 = _one_sided_20pct_saving_p(p_arr, mf_arr)

    all_events = [e for r in rows for e in r[events_key]]
    p_events = [e for e in all_events if e["method_id"] == "M231_Portal_CacheOn"]
    mf_events = [e for e in all_events if e["method_id"] == "MatrixFree_ExactSchur_Krylov"]

    crossings_per_seed = {}
    mean_crossing = None
    if "prefix_cumulative_ms" in rows[0][arms_key]["M231_Portal_CacheOn"]:
        p_pref = np.mean([r[arms_key]["M231_Portal_CacheOn"]["prefix_cumulative_ms"] for r in rows], axis=0)
        mf_pref = np.mean([r[arms_key]["MatrixFree_ExactSchur_Krylov"]["prefix_cumulative_ms"] for r in rows], axis=0)
        mean_crossing = _sustained_crossing_k(p_pref, mf_pref)
        for r in rows:
            crossings_per_seed[str(r["seed"])] = _sustained_crossing_k(
                r[arms_key]["M231_Portal_CacheOn"]["prefix_cumulative_ms"],
                r[arms_key]["MatrixFree_ExactSchur_Krylov"]["prefix_cumulative_ms"],
            )

    # Verify exact AB/BA position balance
    p_rank0 = sum(1 for r in rows if r["pair_execution_order"][0] == "M231_Portal_CacheOn")
    mf_rank0 = sum(1 for r in rows if r["pair_execution_order"][0] == "MatrixFree_ExactSchur_Krylov")

    return {
        "block_label": block_label,
        "cohort_provenance": "Replay_Cohort_63000_63005 (re-used post-patch verification seeds, NOT a fresh untouched draw)",
        "workers": 1,
        "execution_schedule": f"deterministic_AB_BA_balanced (Portal_first={p_rank0}, MatrixFree_first={mf_rank0})",
        "n_maps": len(rows),
        "portal_mean_ms": p_mean,
        "matrixfree_mean_ms": mf_mean,
        "speedup_ratio_matrixfree_over_portal": speedup,
        "relative_time_saving_pct": saving_pct,
        "paired_equal_time_diff_portal_minus_matrixfree_ms": p_diff,
        "diagnostic_one_sided_p_for_20pct_saving": p_20,
        "engineering_20pct_time_saving_gate": "PASS" if (saving_pct >= 20.0 and p_20 < 0.05) else "NOT_MET",
        "observed_cohort_mean_prefix_crossing_through_K24": mean_crossing,
        "per_seed_sustained_prefix_crossing_through_K24": crossings_per_seed if crossings_per_seed else None,
        "event_reduced_verification": {
            "M231_Portal_CacheOn": _reduce_event_ledger(p_events),
            "MatrixFree_ExactSchur_Krylov": _reduce_event_ledger(mf_events),
        },
    }


def _plot_m232_summary(cache_sum: dict, pair47: dict, pair59: dict, cont47: dict, rows47: List[dict], rows59: List[dict], fig_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.8, 9.6), dpi=160)

    # Panel A: Corrected 47^3 3-Arm Cache Causal Study (`Intra-Query Memoization ON Across All 3 Modes, Same-Block Curves ONLY, Closes C232-01`)
    ax = axes[0, 0]
    ks = np.arange(1, len(cache_sum["modes"]["CacheOn_Persistent"]["prefix_cumulative_mean_ms"]) + 1)
    for m_k, m_lbl, st, col in (
        ("QueryCold", "QueryCold (Intra-Query ON, Clear L0..L3 per Query)", "--", "#c0392b"),
        ("CacheL0Only", "CacheL0Only (Keep L0, Clear L1..L3 per Query)", "-.", "#d35400"),
        ("CacheOn_Persistent", "CacheOn_Persistent (Keep L0..L3 Across Queries)", "-", "#27ae60"),
    ):
        ys = np.array(cache_sum["modes"][m_k]["prefix_cumulative_mean_ms"], dtype=float) / 1000.0
        ax.plot(ks, ys, st, linewidth=2.3, label=m_lbl, color=col)
    ax.set_xlabel("Streaming Unseen Goal Index k (1..24)")
    ax.set_ylabel("Single-Worker Cumulative Time C(k) (s)")
    ax.set_title("A. Corrected 47^3 Cache Causal Ablation (Replay 63000..63005, 1 Worker)")
    ax.grid(True, alpha=0.28)
    ax.legend(fontsize=7.8)

    # Panel B: Closest-Neighbor Single-Worker AB/BA Head-to-Head (`Speedup & Relative Time Saving %`)
    ax = axes[0, 1]
    blks = [("Replay 47^3\n(K=24)", pair47), ("Replay 59^3\n(K=24)", pair59), ("Continual 47^3\n(Post-Init Marg)", cont47)]
    xb = np.arange(len(blks))
    w = 0.34
    p_s = [b[1]["portal_mean_ms"] / 1000.0 for b in blks]
    mf_s = [b[1]["matrixfree_mean_ms"] / 1000.0 for b in blks]
    ax.bar(xb - w / 2, mf_s, width=w, color="#e67e22", label="MatrixFree Exact Schur Krylov")
    bars_p = ax.bar(xb + w / 2, p_s, width=w, color="#27ae60", label="M2.3.2 Dyadic Portal (CacheOn)")
    for idx_i, (_, b_d) in enumerate(blks):
        sav = b_d["relative_time_saving_pct"]
        spd = b_d["speedup_ratio_matrixfree_over_portal"]
        ax.text(
            xb[idx_i],
            max(p_s[idx_i], mf_s[idx_i]) + 0.8,
            f"-{sav:.1f}% ({spd:.2f}x)",
            ha="center",
            va="bottom",
            fontsize=8.3,
            fontweight="bold",
        )
    ax.set_xticks(xb)
    ax.set_xticklabels([b[0] for b in blks], fontsize=8.5)
    ax.set_ylabel("Single-Worker Wall-Clock Time (s)")
    ax.set_title("B. Closest-Neighbor AB/BA Replay (20% Gate Honest Check)")
    ax.set_ylim(0, max(mf_s) * 1.18)
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend(fontsize=8.0)

    # Panel C: Per-Seed Sustained Crossing Index Distribution through K=24 (`47^3` & `59^3`)
    ax = axes[1, 0]
    seeds_str = [str(r["seed"]) for r in rows47]
    xs = np.arange(len(seeds_str))
    c47 = [pair47["per_seed_sustained_prefix_crossing_through_K24"][s] or 25 for s in seeds_str]
    c59 = [pair59["per_seed_sustained_prefix_crossing_through_K24"][s] or 25 for s in seeds_str]
    ax.bar(xs - 0.17, c47, width=0.32, color="#16a085", label=f"47^3 (Cohort Mean Crossing k={pair47['observed_cohort_mean_prefix_crossing_through_K24']})")
    ax.bar(xs + 0.17, c59, width=0.32, color="#8e44ad", label=f"59^3 (Cohort Mean Crossing k={pair59['observed_cohort_mean_prefix_crossing_through_K24']})")
    ax.set_xticks(xs)
    ax.set_xticklabels(seeds_str, fontsize=8.5)
    ax.set_xlabel("Replay Map Seed")
    ax.set_ylabel("Per-Map Sustained Crossing Index k (<=24; 25=None)")
    ax.set_ylim(0, 26)
    ax.set_title("C. Per-Map vs. Cohort-Mean Crossing Distribution Through K=24")
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend(fontsize=8.0)

    # Panel D: Event-Reduced Four-Inequality Verification (`L <= V* <= J <= U`) Regret Distribution
    ax = axes[1, 1]
    reg47 = [float(e["policy_value"]) - float(e["reference_value"]) for r in rows47 for e in r["pair_events"] if e["method_id"] == "M231_Portal_CacheOn" and e["policy_evaluated"]]
    reg59 = [float(e["policy_value"]) - float(e["reference_value"]) for r in rows59 for e in r["pair_events"] if e["method_id"] == "M231_Portal_CacheOn" and e["policy_evaluated"]]
    ax.boxplot([reg47, reg59], tick_labels=[f"47^3 (n={len(reg47)})", f"59^3 (n={len(reg59)})"])
    ax.axhline(0.25, color="#c0392b", linestyle="--", linewidth=1.5, label="Contract Budget eps=0.25")
    ax.set_ylabel("Exact Deployed Policy Regret J^{mu} - V*")
    ax.set_title("D. Saved Per-Task Deployed Regret (100% L <= V* <= J <= U)")
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend(fontsize=8.0)

    plt.tight_layout()
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)


def run_m232_full_closure(self_test: bool = False, write_json: bool = False) -> dict:
    wp1_payload = run_m232_contract_and_ring_closure(write_json=write_json and (not self_test))
    t_rep0 = time.perf_counter()

    if self_test:
        r47_st = _run_47_cache_and_pair_single_map(63000, 0, 4)
        rc_st = _run_continual_47_abba_single_map(63000, 0, 1, 2)
        led_c = _reduce_event_ledger(r47_st["cache_events"] + r47_st["pair_events"] + rc_st["events"])
        assert led_c["ALL_SAVED_EVENTS_SATISFIED"], f"Self-test event failure: {led_c}"
        print(
            f"[M2.3.2 SELF-TEST PASS] 47^3 K=4 1-worker: "
            f"CacheOn={r47_st['cache_arms']['CacheOn_Persistent']['total_ms']:.1f}ms | "
            f"CacheL0Only={r47_st['cache_arms']['CacheL0Only']['total_ms']:.1f}ms | "
            f"QueryCold={r47_st['cache_arms']['QueryCold']['total_ms']:.1f}ms | "
            f"AllEventsOK={led_c['ALL_SAVED_EVENTS_SATISFIED']} ({led_c['total_task_events']} events)"
        )
        return {"self_test_passed": True, "wp1": wp1_payload, "ledger": led_c}

    seeds_replay = list(range(63000, 63006))
    K_goals = 24

    print("[M2.3.2 WP-2/3A] Running 1-worker 47^3 Fixed 3-Arm Cache Causal Study + AB/BA Closest-Neighbor Replay (63000..63005, K=24)...")
    rows47 = [_run_47_cache_and_pair_single_map(sd, idx_m, K_goals) for idx_m, sd in enumerate(seeds_replay)]

    # Summarize 47^3 3-Arm Cache Study
    c_on_arr = np.array([r["cache_arms"]["CacheOn_Persistent"]["total_ms"] for r in rows47], dtype=float)
    modes_sum = {}
    all_cache_events = [e for r in rows47 for e in r["cache_events"]]
    for m_nm in CACHE3_MODES:
        m_arr = np.array([r["cache_arms"][m_nm]["total_ms"] for r in rows47], dtype=float)
        m_pref = np.mean([r["cache_arms"][m_nm]["prefix_cumulative_ms"] for r in rows47], axis=0)
        m_ev = [e for e in all_cache_events if e["method_id"] == m_nm]
        modes_sum[m_nm] = {
            "rank_counts_across_6_maps": [
                sum(1 for r in rows47 if r["cache_arms"][m_nm]["exec_rank"] == rk) for rk in range(3)
            ],
            "planner_only_mean_ms": float(np.mean(m_arr)),
            "mean_query_ms": float(np.mean([r["cache_arms"][m_nm]["mean_query_ms"] for r in rows47])),
            "first6_query_mean_ms": float(np.mean([r["cache_arms"][m_nm]["first6_query_ms"] for r in rows47])),
            "last6_query_mean_ms": float(np.mean([r["cache_arms"][m_nm]["last6_query_ms"] for r in rows47])),
            "prefix_cumulative_mean_ms": [float(x) for x in m_pref],
            "mean_local_lu_solves_per_map": float(np.mean([r["cache_arms"][m_nm]["total_local_lu_solves"] for r in rows47])),
            "speedup_of_CacheOn_vs_mode": float(np.mean(m_arr) / np.mean(c_on_arr)),
            "relative_time_saving_of_CacheOn_vs_mode_pct": float(100.0 * (1.0 - np.mean(c_on_arr) / np.mean(m_arr))),
            "paired_diff_CacheOn_minus_mode_ms": paired_stats(c_on_arr - m_arr) if m_nm != "CacheOn_Persistent" else None,
            "event_reduced_verification": _reduce_event_ledger(m_ev),
        }
    cache_sum = {
        "cohort_label": "Replay_47cubed_Fixed_Cache_Ablation",
        "workers": 1,
        "execution_schedule": "exact_2x_3x3_cyclic_Latin_square (each mode rank 0/1/2 twice)",
        "intra_query_memoization_enabled_all_modes": True,
        "modes": modes_sum,
    }
    pair47_sum = _summarize_pair_block(rows47, "Replay_47cubed_AB_BA_Pair", "pair_arms", "pair_events", "total_ms")
    print(
        f"  -> 47^3 Cache (1-worker): CacheOn={modes_sum['CacheOn_Persistent']['planner_only_mean_ms']:.1f}ms | "
        f"CacheL0Only={modes_sum['CacheL0Only']['planner_only_mean_ms']:.1f}ms ({modes_sum['CacheL0Only']['speedup_of_CacheOn_vs_mode']:.2f}x) | "
        f"QueryCold={modes_sum['QueryCold']['planner_only_mean_ms']:.1f}ms ({modes_sum['QueryCold']['speedup_of_CacheOn_vs_mode']:.2f}x)"
    )
    print(
        f"  -> 47^3 Pair AB/BA (1-worker): Portal={pair47_sum['portal_mean_ms']:.1f}ms vs MatrixFree={pair47_sum['matrixfree_mean_ms']:.1f}ms | "
        f"saving={pair47_sum['relative_time_saving_pct']:.2f}% ({pair47_sum['speedup_ratio_matrixfree_over_portal']:.2f}x, "
        f"p={pair47_sum['paired_equal_time_diff_portal_minus_matrixfree_ms']['p_two_sided']:.4g}, gate20={pair47_sum['engineering_20pct_time_saving_gate']})"
    )

    print("[M2.3.2 WP-3B] Running 1-worker 59^3 AB/BA Closest-Neighbor Replay (63000..63005, K=24)...")
    rows59 = [_run_59_pair_single_map(sd, idx_m, K_goals) for idx_m, sd in enumerate(seeds_replay)]
    pair59_sum = _summarize_pair_block(rows59, "Replay_59cubed_AB_BA_Pair", "pair_arms", "pair_events", "total_ms")
    print(
        f"  -> 59^3 Pair AB/BA (1-worker): Portal={pair59_sum['portal_mean_ms']:.1f}ms vs MatrixFree={pair59_sum['matrixfree_mean_ms']:.1f}ms | "
        f"saving={pair59_sum['relative_time_saving_pct']:.2f}% ({pair59_sum['speedup_ratio_matrixfree_over_portal']:.2f}x, "
        f"p={pair59_sum['paired_equal_time_diff_portal_minus_matrixfree_ms']['p_two_sided']:.4g}, gate20={pair59_sum['engineering_20pct_time_saving_gate']})"
    )

    print("[M2.3.2 WP-3C] Running 1-worker 47^3 Continual Known-Support Local Updates AB/BA Replay (63000..63005, 1+5 Epochs x 6 Tasks)...")
    rows_cont = [_run_continual_47_abba_single_map(sd, idx_m, 5, 6) for idx_m, sd in enumerate(seeds_replay)]
    cont47_marg_sum = _summarize_pair_block(rows_cont, "Replay_Continual_47cubed_Marginal_AB_BA", "arms", "events", "post_init_marginal_incl_rebuild_ms")
    cont47_life_sum = _summarize_pair_block(rows_cont, "Replay_Continual_47cubed_Lifecycle_AB_BA", "arms", "events", "lifecycle_incl_rebuild_ms")
    print(
        f"  -> Continual 47^3 AB/BA (1-worker): Marg Portal={cont47_marg_sum['portal_mean_ms']:.1f}ms vs MatrixFree={cont47_marg_sum['matrixfree_mean_ms']:.1f}ms | "
        f"saving={cont47_marg_sum['relative_time_saving_pct']:.2f}% ({cont47_marg_sum['speedup_ratio_matrixfree_over_portal']:.2f}x, "
        f"p={cont47_marg_sum['paired_equal_time_diff_portal_minus_matrixfree_ms']['p_two_sided']:.4g}, gate20={cont47_marg_sum['engineering_20pct_time_saving_gate']})"
    )

    out_dir = Path(__file__).resolve().parent
    fig_path = out_dir / "m232_targeted_replay_summary.png"
    _plot_m232_summary(cache_sum, pair47_sum, pair59_sum, cont47_marg_sum, rows47, rows59, fig_path)

    all_saved_events = (
        [e for r in rows47 for e in r["cache_events"]]
        + [e for r in rows47 for e in r["pair_events"]]
        + [e for r in rows59 for e in r["pair_events"]]
        + [e for r in rows_cont for e in r["events"]]
    )
    global_event_ledger = _reduce_event_ledger(all_saved_events)

    rt_meta = collect_runtime_metadata()
    rt_meta["actual_parallel_workers"] = 1

    replay_payload = _sanitize_for_strict_json({
        "milestone": "M2.3.2_WP2_WP3_Single_Worker_Balanced_Cache_and_Neighbor_Replay",
        "elapsed_wall_s": float(time.perf_counter() - t_rep0),
        "runtime_metadata": rt_meta,
        "phase2_manifest": compute_phase2_manifest(),
        "prior_frozen_artifacts_verified": verify_all_prior_artifacts_untouched(),
        "global_event_reduced_ledger": global_event_ledger,
        "cache_causal_ablation_47cubed": cache_sum,
        "closest_neighbor_abba_47cubed": pair47_sum,
        "closest_neighbor_abba_59cubed": pair59_sum,
        "continual_known_support_abba_47cubed": {
            "marginal": cont47_marg_sum,
            "lifecycle": cont47_life_sum,
            "mean_retained_l1_l3_portal_level_entries": float(
                np.mean([r["arms"]["M231_Portal_CacheOn"]["mean_retained_l1_l3_entries"] for r in rows_cont])
            ),
        },
        "per_map_records": {
            "replay_47cubed": rows47,
            "replay_59cubed": rows59,
            "continual_47cubed": rows_cont,
        },
    })

    json_path = out_dir / "m232_targeted_replay_results.json"
    json_path.write_text(json.dumps(replay_payload, indent=2, allow_nan=False), encoding="utf-8")
    print(
        f"[DONE] Wrote {json_path.name} & {fig_path.name} in {replay_payload['elapsed_wall_s']:.1f}s | "
        f"ALL_SAVED_EVENTS_SATISFIED={global_event_ledger['ALL_SAVED_EVENTS_SATISFIED']} "
        f"(events={global_event_ledger['total_task_events']}, pol_evals={global_event_ledger['deployed_policy_evaluated_count']})"
    )
    if not global_event_ledger["ALL_SAVED_EVENTS_SATISFIED"]:
        raise RuntimeError(f"Saved event ledger violation: {global_event_ledger}")
    return replay_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--contracts-only", action="store_true", help="Run WP-1 contract & goal-ring suite in memory (read-only unless --allow-frozen-ec3c58f-overwrite is also set).")
    parser.add_argument(
        "--allow-frozen-ec3c58f-overwrite",
        action="store_true",
        help="Explicitly allow overwriting frozen ec3c58f m232_*.json/png artifacts (default: read-only guard; use verify_m232_release.py for current release checks).",
    )
    args_cli = parser.parse_args()
    if args_cli.contracts_only:
        run_m232_contract_and_ring_closure(write_json=args_cli.allow_frozen_ec3c58f_overwrite)
    elif args_cli.self_test:
        run_m232_full_closure(self_test=True, write_json=False)
    else:
        if not args_cli.allow_frozen_ec3c58f_overwrite:
            raise SystemExit(
                "[ARCHIVE GUARD C232-05] m232_contract_and_ring_closure.json (06b44156...) and m232_targeted_replay_results.json (9979d61a...) "
                "are frozen at commit ec3c58f. Run `quotient_phase2/verify_m232_release.py` for zero-rerun release verification, "
                "`--contracts-only` for in-memory contract checks, or `--self-test` for smoke tests."
            )
        run_m232_full_closure(self_test=False, write_json=True)
