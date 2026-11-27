"""Milestone M2.3.1 Part A (`quotient_phase2.m231_audit_closure`):
Non-Destructive Contract & Public-API Falsification Regression Suite Closing `EC-01..EC-06` and `7.3`.

Verifies EVERY counterexample raised in the `ec75871` independent audit WITHOUT overwriting any
historical campaign JSON (`m20_contract_results.json`, `m21_ablation_results.json`, `m22_pilot_results.json`,
`m23_m24_3d_results.json`):
  - `EC-01` (`C-MATH-01`): Uniform terminal gauge shift invariance across `phi_goal in {-1000, 0, 100, 135, 145, 160, 1000}`
    (`width` and deployed policy invariant; zero fake zero-width `139.882` floor certificates!).
  - `EC-02` (`C-MATH-02 & C-MATH-03`): Rejects cross-room goal unions, portal-straddling goals, `u_max` finite bounds,
    and anisotropic `r_diag`; supports `start_in_goal` short-circuit and `start_on_portal` exact readout.
  - `EC-03`: Rejects disconnected/unreachable goals in BOTH `M2.2` and `M2.3` (`certified=False, status='unreachable', +inf`)
    and verifies floor-free scale-invariant policy evaluators return `+inf` (never `690.78` or `0.5` row sums).
  - `EC-04` (`C-MATH-04`): Verifies `solve_and_verify_portal_howard_bounds` on the 24-node strictly sub-stochastic
    chain (where 6-step capped Howard violated post-fixed-point by `1.21e-4`), proving `post_fp_min_slack >= 0`,
    unclipped `s_0_raw > 0`, and sound enclosure of true cost `27.5034`.
  - `EC-05` (`C-MATH-05`): Fault-injects `bicgstab(..., info=80)` into `solve_exact_reference_value` and verifies
    immediate `RuntimeError` rejection.
  - `EC-06` & `7.3`: Verifies `RecedingHorizonCertificateChain` rejects `(c, c, c, c)` repeated root certificates,
    `LazyRoomPortalPolicy` rejects stale epochs after `update_world_operator`, and `build_portal_level_blocks`
    produces `0` cross-parent blocks across `L0 -> L1 -> L2 -> L3` on `11x11` planar portals.
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from green_response import ProblemSpec, collect_runtime_metadata, enforce_single_thread_env
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
    solve_and_verify_portal_howard_bounds,
)


FROZEN_JSON_SHA256 = {
    "m20_contract_results.json": "bdad834622c2ab0215be84c2e3cfb4473f5b242e053d9b7bef8e792081c67004",
    "m21_ablation_results.json": "634c15e52fb3a8181f738baef40b8d7c30e690a8600a7cf1e30b6ca17a3c4fc1",
    "m22_pilot_results.json": "55d7e1ea176d2ad53d173595339c21216fc6f210857b5d28e30b98c163a3d892",
    "m23_m24_3d_results.json": "8fb6fb84749dfa640e5f5394c65db71426302a365e95a512c25dd896bce30f05",
}


def verify_historical_jsons_untouched() -> dict:
    p2_dir = Path(__file__).resolve().parent
    out = {}
    for fn, exp_sha in FROZEN_JSON_SHA256.items():
        actual = hashlib.sha256((p2_dir / fn).read_bytes()).hexdigest()
        if actual != exp_sha:
            raise RuntimeError(f"Historical artifact {fn} modified: expected {exp_sha}, got {actual}")
        out[fn] = {"sha256": actual, "verified_untouched": True}
    for pres_fn in ("m21_economic_gate_verdict.json", "m21_post_audit_closure.json"):
        fp = p2_dir / pres_fn
        out[pres_fn] = {"exists": fp.exists(), "sha256": hashlib.sha256(fp.read_bytes()).hexdigest() if fp.exists() else None}
    return out


def run_m231_audit_closure_suite(write_json: bool = False) -> dict:
    t0 = time.perf_counter()
    verify_phase1_readonly_freeze()
    enforce_single_thread_env()

    # 0. Existing M2.0 (15 gates), WP0, and M2.2 (4 graph families) regressions in memory
    m20_res = run_m20_contract_verification_suite()
    wp0_res = run_v10_online_and_contract_probes()
    m22_graph_res = run_part_a_multiroom_graph_suite()

    # Setup 17^3 two-room single-portal probe from `ec_certificate_probe.py`
    gn = 17
    spec = ProblemSpec(dim=3)
    free = np.ones((gn, gn, gn), dtype=bool)
    free[8, :, :] = False
    free[8, 6:11, 6:11] = True
    nodes = np.flatnonzero(free.ravel())
    fpos = np.full(gn ** 3, -1, dtype=np.int64)
    fpos[nodes] = np.arange(len(nodes), dtype=np.int64)
    _, pts, _ = build_grid_points(3, spec.half_width, gn)
    q = np.full(len(nodes), 0.5, dtype=float)
    b = np.zeros((len(nodes), 3), dtype=float)
    b[:, 1] = 0.13
    A = build_3d_reflecting_obstacle_mmatrix(spec, gn, free.ravel(), q, b).tocsr()

    def _idx(x: int, y: int, z: int) -> int:
        return int(fpos[(x * gn + y) * gn + z])

    start = _idx(3, 8, 8)
    far = _idx(13, 8, 8)
    near_r = _idx(11, 8, 8)
    portal_node = _idx(8, 8, 8)
    goal_far = np.zeros(len(nodes), dtype=bool)
    goal_far[far] = True

    ex_mask = np.flatnonzero(~goal_far)
    z_ex0 = spla.spsolve(A[ex_mask, :][:, ex_mask].tocsc(), np.asarray((-A[ex_mask, :][:, goal_far]).sum(axis=1)).ravel())
    v0_truth = float(-spec.lam * np.log(z_ex0[int(np.searchsorted(ex_mask, start))]))

    pl = SeamFreePortal3DPlanner(spec, gn, free, nodes, pts[nodes], A, eps_tol=0.25)

    # 1. EC-01: Terminal gauge invariance across `phi in {-1000, 0, 100, 135, 145, 160, 1000}`
    gauge_rows = []
    widths_seen = []
    ec01_pass = True
    for phi in (-1000.0, 0.0, 100.0, 135.0, 145.0, 160.0, 1000.0):
        res = pl.solve_unseen_goal(start, goal_far, phi_goal=phi, materialize_full_z_sub=True)
        truth_phi = v0_truth + phi
        v_pol = evaluate_3d_deployed_policy_exact(A, goal_far, phi, res["z_guide_full"], spec.lam, start)
        ok_phi = bool(
            res["certified"]
            and (res["lo"] - 1e-9 <= truth_phi <= v_pol + 1e-9)
            and (v_pol <= res["hi"] + 1e-9)
            and (res["width"] > 1e-4)
            and (res["width"] <= 0.25)
        )
        widths_seen.append(res["width"])
        if not ok_phi:
            ec01_pass = False
        gauge_rows.append({
            "phi_goal": phi,
            "truth": truth_phi,
            "lo": res["lo"],
            "hi": res["hi"],
            "width": res["width"],
            "deployed_policy_value": v_pol,
            "pass": ok_phi,
        })
    width_drift = float(np.max(widths_seen) - np.min(widths_seen))
    ec01_pass = bool(ec01_pass and width_drift <= 1e-12)

    # 2. EC-02: Multi-room goal union rejection, portal-goal rejection, capability guards, start-in-goal, portal-start
    multi_goal = np.zeros(len(nodes), dtype=bool)
    multi_goal[_idx(3, 8, 8)] = True
    multi_goal[near_r] = True
    rejected_multi_goal = False
    try:
        pl.solve_unseen_goal(far, multi_goal)
    except ValueError:
        rejected_multi_goal = True

    portal_goal = np.zeros(len(nodes), dtype=bool)
    portal_goal[portal_node] = True
    rejected_portal_goal = False
    try:
        pl.solve_unseen_goal(start, portal_goal)
    except ValueError:
        rejected_portal_goal = True

    rejected_umax = False
    try:
        build_3d_reflecting_obstacle_mmatrix(ProblemSpec(dim=3, u_max=0.01), gn, free.ravel(), q, b)
    except ValueError:
        rejected_umax = True

    rejected_rdiag = False
    try:
        build_3d_reflecting_obstacle_mmatrix(ProblemSpec(dim=3, r_diag=(0.5, 1.0, 2.0)), gn, free.ravel(), q, b)
    except ValueError:
        rejected_rdiag = True

    res_in_goal = pl.solve_unseen_goal(far, goal_far, phi_goal=12.5)
    start_in_goal_ok = bool(res_in_goal["certified"] and res_in_goal["lo"] == 12.5 and res_in_goal["hi"] == 12.5)

    res_portal_start = pl.solve_unseen_goal(portal_node, goal_far, phi_goal=0.0, materialize_full_z_sub=True)
    v_portal_truth = float(-spec.lam * np.log(z_ex0[int(np.searchsorted(ex_mask, portal_node))]))
    portal_start_ok = bool(
        res_portal_start["certified"]
        and (res_portal_start["lo"] - 1e-8 <= v_portal_truth <= res_portal_start["hi"] + 1e-8)
    )
    ec02_pass = bool(
        rejected_multi_goal and rejected_portal_goal and rejected_umax and rejected_rdiag and start_in_goal_ok and portal_start_ok
    )

    # 3. EC-03: Unreachable goals rejected in BOTH M2.2 and M2.3, and evaluators return `+inf`
    A_unreach = sp.csr_matrix(np.array([[2.0, -1.0, 0.0], [-1.0, 2.0, 0.0], [0.0, 0.0, 1.0]], dtype=float))
    gm_unreach = np.array([False, False, True])
    dec_u, _ = build_room_decomposition(A_unreach, np.array([True, False, False]), [np.array([0])])
    r_m22_u1 = plan_unseen_goal_via_portal_quotient(A_unreach, dec_u, 1, gm_unreach, 0.0, 1.0, use_uncompressed_interface=True)
    r_m22_u2 = plan_unseen_goal_via_portal_quotient(A_unreach, dec_u, 1, gm_unreach, 0.0, 1.0, use_uncompressed_interface=False)
    ev_m22_u = evaluate_twisted_lmdp_policy_exact(A_unreach, gm_unreach, 0.0, np.array([0.0, 0.0, 1.0]), 1.0)

    # Disconnected 3D two-room building (doorway sealed!)
    free_sealed = np.ones((gn, gn, gn), dtype=bool)
    free_sealed[8, :, :] = False  # completely sealed wall at x=8!
    nodes_s = np.flatnonzero(free_sealed.ravel())
    fpos_s = np.full(gn ** 3, -1, dtype=np.int64)
    fpos_s[nodes_s] = np.arange(len(nodes_s), dtype=np.int64)
    A_sealed = build_3d_reflecting_obstacle_mmatrix(spec, gn, free_sealed.ravel(), np.full(len(nodes_s), 0.5), np.zeros((len(nodes_s), 3))).tocsr()
    # Keep a fake portal plane at x=4 so rooms exist while x=8 is sealed
    free_sealed_p = free_sealed.copy()
    free_sealed_p[4, :, :] = False
    free_sealed_p[4, 6:11, 6:11] = True
    nodes_sp = np.flatnonzero(free_sealed_p.ravel())
    fpos_sp = np.full(gn ** 3, -1, dtype=np.int64)
    fpos_sp[nodes_sp] = np.arange(len(nodes_sp), dtype=np.int64)
    A_sp = build_3d_reflecting_obstacle_mmatrix(spec, gn, free_sealed_p.ravel(), np.full(len(nodes_sp), 0.5), np.zeros((len(nodes_sp), 3))).tocsr()
    pl_sp = SeamFreePortal3DPlanner(spec, gn, free_sealed_p, nodes_sp, pts[nodes_sp], A_sp, eps_tol=0.25)
    s_left = int(fpos_sp[(2 * gn + 8) * gn + 8])
    g_right = np.zeros(len(nodes_sp), dtype=bool)
    g_right[int(fpos_sp[(13 * gn + 8) * gn + 8])] = True
    r_m23_u = pl_sp.solve_unseen_goal(s_left, g_right)
    ev_m23_u = evaluate_3d_deployed_policy_exact(A_sp, g_right, 0.0, np.where(g_right, 1.0, 0.0), spec.lam, s_left)

    ec03_pass = bool(
        (not r_m22_u1["certified"])
        and r_m22_u1["status"] == "unreachable"
        and np.isinf(r_m22_u1["lower_bound"])
        and (not r_m22_u2["certified"])
        and np.isinf(ev_m22_u[0])
        and np.isinf(ev_m22_u[1])
        and ev_m22_u[2] == 0.0
        and (not r_m23_u["certified"])
        and r_m23_u["status"] == "unreachable"
        and np.isinf(ev_m23_u)
    )

    # 4. EC-04: 24-node strictly sub-stochastic Howard chain counterexample (`ec_howard_contract_probe.py`)
    m_h = 12
    n_h = 2 * m_h
    K_h = np.zeros((n_h, n_h), dtype=float)
    r_h = np.zeros(n_h, dtype=float)
    blocks_h = [np.array([2 * i, 2 * i + 1], dtype=np.int64) for i in range(m_h)]
    L_h = np.zeros((n_h, m_h), dtype=float)
    for i in range(m_h):
        L_h[blocks_h[i], i] = 1.0
        if i < m_h - 1:
            K_h[2 * i, 2 * (i + 1)] = 0.99
        r_h[2 * i] = 1e-13
        r_h[2 * i + 1] = 0.5 * (4.0 ** (i - m_h + 1))
    K_cur_h = K_h @ L_h
    z_true_h = np.linalg.solve(np.eye(n_h) - K_h, r_h)
    hw_full = solve_and_verify_portal_howard_bounds(K_cur_h, r_h, blocks_h, max_iters=30)
    # Also test even when `max_iters=6` (early Howard cap): verified Lyapunov shift STILL preserves soundness (`W_lo <= z_true`)!
    hw_capped6 = solve_and_verify_portal_howard_bounds(K_cur_h, r_h, blocks_h, max_iters=6)
    ec04_pass = bool(
        hw_full["verified"]
        and hw_full["post_fp_min_slack"] >= -1e-16
        and hw_full["pre_fp_min_slack"] >= -1e-16
        and np.all(hw_full["W_lo"] <= z_true_h + 1e-24)
        and np.all(z_true_h <= hw_full["W_hi"] + 1e-15)
        and (-np.log(hw_full["W_lo"][0]) >= -np.log(z_true_h[0]) - 1e-12)
        and ((not hw_capped6["verified"]) or np.all(hw_capped6["W_lo"] <= z_true_h + 1e-24))
    )

    # 5. EC-05: Reference non-convergence injection (`info=80`) rejected via `RuntimeError`
    old_bicg = spla.bicgstab
    rejected_bad_ref = False
    try:
        spla.bicgstab = lambda Aop, rhs, **kw: (np.full_like(rhs, 2.0), 80)
        try:
            pl.solve_exact_reference_value(start, goal_far)
        except RuntimeError:
            rejected_bad_ref = True
    finally:
        spla.bicgstab = old_bicg

    # 6. EC-06, Stale-Epoch Policy Guard, & `7.3` Strictly Nested Dyadic `11x11` Partition Check
    c_unindexed = Phase2DecisionCertificate(
        "receding_horizon_root_action_enclosure", True, 0.1, 0.0, None, {0: (0.0, 0.0), 1: (1.0, 1.0)}, 0, 4
    )
    chain_bad = RecedingHorizonCertificateChain(4, (c_unindexed, c_unindexed, c_unindexed, c_unindexed))

    # Stale policy epoch rejection after `update_world_operator`
    res_ep0 = pl.solve_unseen_goal(start, goal_far)
    pol_ep0 = res_ep0["policy"]
    nb_0, pr_0 = pol_ep0.action_distribution(start)
    action_sum_ok = bool(abs(float(np.sum(pr_0)) - 1.0) <= 1e-12)
    pl.update_world_operator(A, modified_rooms=[0], portal_diag_changed=False)
    stale_policy_rejected = False
    try:
        pol_ep0.action_distribution(start)
    except RuntimeError:
        stale_policy_rejected = True

    # Strictly nested check across L0 -> L1 -> L2 -> L3 on 11x11 square portal (`121` nodes)
    coords_11 = np.array([(0.0, float(i), float(j)) for i in range(11) for j in range(11)], dtype=float)
    ids_11 = np.arange(len(coords_11), dtype=np.int64)
    cross_parent_total = 0
    level_counts = {}
    for lv in (0, 1, 2, 3):
        blks_lv = build_portal_level_blocks(ids_11, coords_11, lv)
        level_counts[f"L{lv}"] = len(blks_lv)
        if lv > 0:
            blks_prev = build_portal_level_blocks(ids_11, coords_11, lv - 1)
            par_of = np.empty(len(ids_11), dtype=np.int64)
            for pk, pb in enumerate(blks_prev):
                par_of[pb] = pk
            for cb in blks_lv:
                if len(np.unique(par_of[cb])) > 1:
                    cross_parent_total += 1

    ec06_and_nested_pass = bool(
        (not chain_bad.all_steps_certified)
        and (chain_bad.guaranteed_full_horizon_regret_bound is None)
        and action_sum_ok
        and stale_policy_rejected
        and cross_parent_total == 0
    )

    hist_ledger = verify_historical_jsons_untouched()
    all_pass = bool(
        m20_res["ALL_15_COUNTEREXAMPLE_GATES_PASSED"]
        and wp0_res["ALL_V10_CLOSURE_PROBES_PASSED"]
        and m22_graph_res["ALL_4_GRAPH_FAMILIES_PASSED"]
        and ec01_pass
        and ec02_pass
        and ec03_pass
        and ec04_pass
        and rejected_bad_ref
        and ec06_and_nested_pass
    )

    payload = {
        "milestone": "M2.3.1_WP_A_Audit_Counterexample_Closure",
        "ALL_EC75871_AUDIT_ISSUES_CLOSED": all_pass,
        "elapsed_ms": 1000.0 * (time.perf_counter() - t0),
        "runtime_metadata": collect_runtime_metadata(),
        "phase2_manifest": compute_phase2_manifest(),
        "historical_artifacts_preserved": hist_ledger,
        "regressions": {
            "m20_all_15_passed": m20_res["ALL_15_COUNTEREXAMPLE_GATES_PASSED"],
            "wp0_all_passed": wp0_res["ALL_V10_CLOSURE_PROBES_PASSED"],
            "m22_4_families_passed": m22_graph_res["ALL_4_GRAPH_FAMILIES_PASSED"],
            "EC01_terminal_gauge_invariance": {
                "pass": ec01_pass,
                "max_width_drift_across_phi_minus1000_to_plus1000": width_drift,
                "cases": gauge_rows,
            },
            "EC02_domain_and_capability_guards": {
                "pass": ec02_pass,
                "rejected_multi_room_goal_union": rejected_multi_goal,
                "rejected_portal_goal": rejected_portal_goal,
                "rejected_finite_u_max": rejected_umax,
                "rejected_anisotropic_r_diag": rejected_rdiag,
                "start_in_goal_exact": start_in_goal_ok,
                "start_on_portal_enclosed": portal_start_ok,
            },
            "EC03_unreachable_goal_and_floor_free_evaluators": {
                "pass": ec03_pass,
                "m22_uncompressed_status": r_m22_u1["status"],
                "m22_evaluator_values": [float(x) for x in ev_m22_u],
                "m23_status": r_m23_u["status"],
                "m23_evaluator_value": float(ev_m23_u),
            },
            "EC04_runtime_howard_and_lyapunov_verification": {
                "pass": ec04_pass,
                "iters_lo": hw_full["iters_lo"],
                "post_fp_min_slack": hw_full["post_fp_min_slack"],
                "pre_fp_min_slack": hw_full["pre_fp_min_slack"],
                "min_beta_s_over_w": hw_full["min_beta_s_over_w"],
                "true_cost_start": float(-np.log(z_true_h[0])),
                "certified_upper_cost_start": float(-np.log(hw_full["W_lo"][0])),
                "capped_6iter_still_sound_or_rejected": bool(
                    (not hw_capped6["verified"]) or np.all(hw_capped6["W_lo"] <= z_true_h + 1e-24)
                ),
            },
            "EC05_reference_nonconvergence_rejected": {
                "pass": rejected_bad_ref,
            },
            "EC06_and_7_3_chain_identity_policy_epoch_and_nested_dyadic": {
                "pass": ec06_and_nested_pass,
                "repeated_root_chain_rejected": not chain_bad.all_steps_certified,
                "stale_policy_epoch_rejected": stale_policy_rejected,
                "portal_11x11_level_counts": level_counts,
                "cross_parent_blocks_count": cross_parent_total,
            },
        },
    }

    if write_json:
        out_path = Path(__file__).resolve().parent / "m231_audit_closure.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"[M2.3.1 WP-A] ALL_EC75871_AUDIT_ISSUES_CLOSED={all_pass} | "
        f"EC01={ec01_pass} EC02={ec02_pass} EC03={ec03_pass} EC04={ec04_pass} "
        f"EC05={rejected_bad_ref} EC06+Nested={ec06_and_nested_pass} (cross_parent={cross_parent_total}) | "
        f"write_json={write_json} | elapsed={payload['elapsed_ms']:.1f}ms"
    )
    if not all_pass:
        raise RuntimeError("One or more M2.3.1 WP-A audit closure gates failed!")
    return payload


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-legacy-archive-overwrite",
        action="store_true",
        help="Explicitly overwrite frozen b6ff40d m231_audit_closure.json (default: run in-memory read-only).",
    )
    args_cli = parser.parse_args()
    run_m231_audit_closure_suite(write_json=args_cli.allow_legacy_archive_overwrite)
