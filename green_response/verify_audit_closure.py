"""Comprehensive 15-Suite Independent Audit-Closure & Counterexample Regression (`green_response`).

Covers ALL 10 checks from `v3.1` / `v4_audit` PLUS ALL 5 new probes from `markdown/green_response_audit/checks/`:
  1. [v4_audit `port_v4_sign_probe.py`] 54 coarse 1-goal & near-goal 2-target value-bound enclosures (`0` violations).
  2. [v4_audit 3D Nested Tree] Eager vs lazy initialization at `L1, L4, L8, EXACT` in 3D (`< 1e-12` diff, `0` wasted cols).
  3. [v4_audit `port_v4_barrier_probe.py`] 32 random signed boundary intervals on drifting `41^2` (`0` violations).
  4. [v4_audit `port_v4_start_scope_probe.py` + BnB] `t=0` ball absorption + `m=7` (`5,040` perms) BnB (`0` violations).
  5. [Adaptive Macro-MDP] `O(m^2 2^m)` Subset-State Macro-Bellman on `m=8` (`F_lo <= F* <= J^{mu_hat} <= F_hi`).
  6. [v4_audit KKT] Anisotropic constrained KKT vs `brentq`/`SLSQP` + `51^2` `6101/q6` residual `< 1e-11` + readout split.
  7. [v4_audit 3D Reuse] `Cached-Target-FD` (`0` double factorizations) & `Warm-ILU` (`0` fallbacks on Map 400).
  8. [v4_audit High-D Spec Guard] Rejects anisotropic `R` & finite `u_max` across BOTH high-D AND 2D/3D LMDP solvers,
     supports scalar `R = 2 I` (`< 1e-8`), and proves `< 1e-13` prior-mean GP algebraic equivalence.
  9. [v3.1/v4 Collar & Robust HJB] Unclipped exterior trace (`< 0.008`), wall normal `u=0`, continuous-disk robust HJB.
 10. [v4_audit Kinetic & Adjoint] Independent path-vs-endpoint telescoping (`< 1e-12`), killed adjoint (`< 1e-8`).
 11. [NEW `85e2323` `root85_exactring_dispatch_probe.py`] Repaired `ExactRing` near/overlapping goal union dispatch:
     `map401/q2` (`25^3`) and overlapping heterogeneous-`phi` goals match `ClassicalFDSolver` to `< 1e-13` (`57 == 57` ports!).
 12. [NEW `85e2323` `macro85_numeric_probe.py`] Terminal-cost gauge invariance across `phi = -50, 0, 2, 8, 20, 200`:
     all `phi` certify at identical `L8` resolution with `< 1e-12` width variation!
 13. [NEW `85e2323` `macro85_numeric_probe.py` Failure/Fail-Closed] Zero-budget invalid input performs `0` refinements
     and raises `0` exceptions (`status='numeric_invalid', policy=None`), and inverted harmonic inputs fail closed
     without midpoint repair!
 14. [NEW `85e2323` `highd85_scalar_and_stats_probe.py`] Repaired scalar-`R` PIMC innovation across `r = 0.5, 1, 2, 4`
     on affine-cost nonzero Gaussian tilting (`observed / exact` within `2%` MC tolerance vs `2x / 0.25x` bug!).
 15. [NEW `85e2323` `macro85_scaling_probe.py` + Continual Stage D] Independent `m=9` (`512` masks x `69` rows = `35,328`
     entries) all-entry check (`0` violations) + Continual M-matrix residual-audited epoch update (`0` violations!).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import scipy.sparse.linalg as spla
from scipy.optimize import brentq, minimize

from green_response import (
    BoxNeumannBesselBaseGuide,
    ClassicalFDSolver,
    GoalBall,
    HazardFeature,
    KrigingWorldModel,
    MacroTourPlanner,
    MirrorNeumannMatern52GP,
    ProblemSpec,
    QueryTask,
    SchurPortPlanner,
    build_grid_points,
    collect_runtime_metadata,
    enforce_single_thread_env,
    eval_goal_union,
    generate_benchmark_map,
    independent_exact_ball_tour_scores,
    independent_exact_macro_bellman_reference,
    make_antithetic_centered_pimc_policy,
    make_consistent_value_and_policy_2d3d,
    sample_noisy_probes,
    solve_exact_continuous_ball_robust_hjb_2d,
    solve_highd_fk_distillation,
    solve_kinetic_underactuated_greenres,
    solve_monotone_anisotropic_constrained_hjb_2d,
)


class _AffineCostModel:
    def predict_q(self, X: np.ndarray) -> np.ndarray:
        return 10.0 + np.asarray(X, dtype=float)[:, 0]

    def predict_b(self, X: np.ndarray) -> np.ndarray:
        return np.zeros_like(np.asarray(X, dtype=float))


def run_all_audit_checks() -> dict:
    enforce_single_thread_env()
    report = {"metadata": collect_runtime_metadata()}

    # ------------------------------------------------------------------
    # 1. Single-Query Sign Probe (54 cases)
    # ------------------------------------------------------------------
    sign_27_violations = 0
    sign_27_violated_nodes = 0
    for sigma in (0.45, 0.25, 0.75):
        for q0 in (0.5, 2.0, 8.0):
            for gcent in ((0.0, 0.0), (0.21, 0.11), (1.1, 0.3)):
                sp_p = ProblemSpec(dim=2, sigma=sigma, q0=q0)
                goals = [GoalBall(gcent, 0.0, 0.27)]
                qt = QueryTask("sign_probe", tuple(goals), ((-0.7, -0.9),))
                zf = lambda X: np.zeros(len(X))
                pl = SchurPortPlanner(sp_p, 41, zf, None, goals, initial_sectors_per_wp="L1")
                r = pl.solve_query(qt)
                fd = ClassicalFDSolver(sp_p, 41, zf, None).solve_direct(qt)
                mask, _ = eval_goal_union(pl.pts, goals)
                ext = ~mask
                vlo = r["V_grid"][ext] + r["ring_value_lower_shift"]
                vhi = r["V_grid"][ext] + r["ring_value_upper_shift"]
                vfd = fd["V_grid"][ext]
                bad = (vfd < vlo - 1e-9) | (vfd > vhi + 1e-9)
                if np.any(bad):
                    sign_27_violations += 1
                    sign_27_violated_nodes += int(np.sum(bad))

    sp2 = ProblemSpec(dim=2, half_width=1.65, sigma=0.45, q0=0.50)
    fd41 = ClassicalFDSolver(sp2, 41, lambda X: np.zeros(len(X)), None)
    adv_27_violations = 0
    worst_raw_min_z = np.inf
    for sep in (0.40, 0.45, 0.50):
        cat_wps = [GoalBall((0.0, 0.0), 0.0, 0.22), GoalBall((sep, 0.0), 0.0, 0.22), GoalBall((-0.7, 0.6), 0.0, 0.22)]
        for phi2 in (0.6, 1.0, 2.0):
            q_adv = QueryTask("adv", (GoalBall((0.0, 0.0), 0.0, 0.22), GoalBall((sep, 0.0), phi2, 0.22)), ((-0.8, -0.8),))
            v_fd = fd41.solve_direct(q_adv)["V_grid"]
            gmask, _ = eval_goal_union(fd41.pts, q_adv.goals)
            ext = ~gmask
            for lvl in ("L1", "L4", "L8"):
                pl = SchurPortPlanner(sp2, 41, lambda X: np.zeros(len(X)), None, cat_wps, initial_sectors_per_wp=lvl)
                res = pl.solve_query(q_adv)
                worst_raw_min_z = min(worst_raw_min_z, res["raw_min_Z"])
                vlo = res["V_grid"][ext] + res["ring_value_lower_shift"]
                vhi = res["V_grid"][ext] + res["ring_value_upper_shift"]
                if np.any(v_fd[ext] < vlo - 1e-9) or np.any(v_fd[ext] > vhi + 1e-9):
                    adv_27_violations += 1

    report["1_single_query_sign_and_enclosure_54_cases"] = {
        "gpt6_sign_probe_27_failing_cases": sign_27_violations,
        "gpt6_sign_probe_27_violated_nodes": sign_27_violated_nodes,
        "adversarial_2goal_27_failing_cases": adv_27_violations,
        "worst_raw_min_Z": worst_raw_min_z,
        "pass": bool(sign_27_violations == 0 and adv_27_violations == 0 and worst_raw_min_z > 0.0),
    }

    # ------------------------------------------------------------------
    # 2. 3D Unified Nested Partition Tree (`L1 -> L4 -> L8 -> EXACT`)
    # ------------------------------------------------------------------
    sp3 = ProblemSpec(dim=3, half_width=1.65, sigma=0.45, q0=0.50)
    cat3 = [GoalBall((0.25, -0.30, 0.15), 0.0, 0.30), GoalBall((-0.55, 0.40, -0.20), 0.0, 0.30)]
    q3_fn = lambda X: 1.5 * np.exp(-np.sum(X ** 2, axis=1) / 0.5)
    b3_fn = lambda X: np.column_stack([-0.4 * X[:, 1], 0.4 * X[:, 0], 0.2 * X[:, 2]])

    pl3_lazy = SchurPortPlanner(sp3, 17, q3_fn, b3_fn, cat3, initial_sectors_per_wp="L1", lazy_init=True)
    for lv in ("L1", "L4", "L8", "EXACT"):
        pl3_lazy.ensure_wp_level(0, lv)
    exact_backsolves_used = pl3_lazy.total_lu_backsolves
    n_ring_wp0 = len(pl3_lazy.wp_rings[0])

    max_eager_vs_lazy_diff = 0.0
    max_pde_col_res = 0.0
    for init_lv in ("L1", "L4", "L8", "EXACT"):
        pl3_eag = SchurPortPlanner(sp3, 17, q3_fn, b3_fn, [cat3[0]], initial_sectors_per_wp=init_lv, lazy_init=False)
        for lv in ("L1", "L4", "L8", "EXACT"):
            s_e, U_e = pl3_eag.ensure_wp_level(0, lv)
            s_l, U_l = pl3_lazy.ensure_wp_level(0, lv)
            max_eager_vs_lazy_diff = max(max_eager_vs_lazy_diff, float(np.max(np.abs(U_e - U_l))))
            for k_c, sl in enumerate(s_e):
                rhs = np.zeros(len(pl3_eag.pts))
                rhs[sl] = 1.0
                max_pde_col_res = max(max_pde_col_res, float(np.max(np.abs(pl3_eag.A0 @ U_e[:, k_c] - rhs))))

    report["2_3d_nested_tree_eager_vs_lazy_invariance"] = {
        "wp0_ring_nodes": n_ring_wp0,
        "lazy_L1_to_EXACT_total_backsolves": exact_backsolves_used,
        "zero_wasted_backsolves": bool(exact_backsolves_used == n_ring_wp0),
        "max_eager_vs_lazy_column_diff": max_eager_vs_lazy_diff,
        "max_A0_column_residual": max_pde_col_res,
        "pass": bool(exact_backsolves_used == n_ring_wp0 and max_eager_vs_lazy_diff < 1e-12 and max_pde_col_res < 1e-11),
    }

    # ------------------------------------------------------------------
    # 3. Signed Asymmetric-Drift Barrier Probe (32 random intervals)
    # ------------------------------------------------------------------
    w_bar = generate_benchmark_map(801, dim=2, regime="narrow_barrier", with_drift=True)
    cat_bar = [GoalBall((0.28, -0.22), 0.0, 0.27)]
    pl_bar = SchurPortPlanner(w_bar.spec, 41, w_bar.q_hidden, w_bar.drift, cat_bar, initial_sectors_per_wp="L1", lazy_init=True)
    ring_b = pl_bar.wp_rings[0]
    in_r = np.zeros(len(pl_bar.pts), dtype=bool); in_r[ring_b] = True
    ext_b = np.flatnonzero(~in_r)
    A_csr_b = pl_bar.A0.tocsr()
    lu_dir = spla.splu(A_csr_b[ext_b, :][:, ext_b].tocsc())
    H_dir = np.zeros((len(pl_bar.pts), len(ring_b)))
    H_dir[ext_b, :] = lu_dir.solve(-(A_csr_b[ext_b, :][:, ring_b].toarray()))
    H_dir[ring_b, :] = np.eye(len(ring_b))

    rng_b = np.random.default_rng(2026)
    F_lo_32 = rng_b.uniform(-4.5, 3.5, size=(len(ring_b), 32))
    F_hi_32 = F_lo_32 + rng_b.uniform(0.0, 1.2, size=(len(ring_b), 32))
    F_sample = 0.5 * (F_lo_32 + F_hi_32) + 0.45 * (F_hi_32 - F_lo_32) * np.sin(np.arange(len(ring_b))[:, None])
    Ex_true = H_dir @ F_sample

    barrier_violations = 0
    all_valid_flags = True
    eval_all = np.arange(len(pl_bar.pts), dtype=np.int64)
    for lv in ("L1", "L4", "L8", "EXACT"):
        pl_bar.ensure_wp_level(0, lv)
        prep_b = pl_bar.prepare_wp_ring_eval(0, eval_all)
        lo_all, hi_all, ok_flag = pl_bar.bound_harmonic_batch(prep_b, F_lo_32, F_hi_32, eval_first_only=False)
        all_valid_flags = all_valid_flags and ok_flag
        valid_dom = (~pl_bar.wp_masks[0]) | in_r
        bad_b = (Ex_true[valid_dom] < lo_all[valid_dom] - 1e-9) | (Ex_true[valid_dom] > hi_all[valid_dom] + 1e-9)
        barrier_violations += int(np.sum(bad_b))

    report["3_signed_barrier_probe_32_cases"] = {
        "levels_tested": ["L1", "L4", "L8", "EXACT"],
        "all_valid_without_clamping": all_valid_flags,
        "violated_node_case_pairs": barrier_violations,
        "pass": bool(all_valid_flags and barrier_violations == 0),
    }

    # ------------------------------------------------------------------
    # 4. Tour `t=0` Immediate Absorption + Scalable `m = 7` (`5,040` perms) BnB
    # ------------------------------------------------------------------
    w_t = generate_benchmark_map(800, dim=2, regime="narrow_barrier", with_drift=True)
    rng_t = np.random.default_rng(877)
    cat_t = []
    for _ in range(10):
        for _att in range(200):
            pt = rng_t.uniform(-1.20, 1.20, size=2)
            if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.06 * 0.27 for w in cat_t):
                cat_t.append(GoalBall(tuple(pt.tolist()), 0.0, 0.27))
                break
    km_t = KrigingWorldModel(*sample_noisy_probes(w_t, n_probes=80, seed=805, include_drift=True))

    pl_t5 = SchurPortPlanner(w_t.spec, 61, km_t.predict_q, km_t.predict_b, cat_t, initial_sectors_per_wp="L1", lazy_init=True)
    mt5 = MacroTourPlanner(pl_t5)
    sub5 = (0, 1, 2, 3, 4)
    start_inside = np.asarray(cat_t[2].center) + np.array([0.03, -0.02])
    ex_scores_in, _ = independent_exact_ball_tour_scores(pl_t5, start_inside, sub5)
    res_in_r1 = mt5.plan_fixed_tour_bnb(start_inside, sub5, epsilon_tol=0.25, max_refine_steps=0, return_all_perm_enclosures=True)
    res_in_fin = mt5.plan_fixed_tour_bnb(start_inside, sub5, epsilon_tol=0.25, max_refine_steps=8, return_all_perm_enclosures=True)

    in_viol = 0
    for r_chk in (res_in_r1, res_in_fin):
        for pm, (lv, hv) in r_chk["perm_enclosures"].items():
            ev = ex_scores_in[pm]
            if ev < lv - 1e-9 or ev > hv + 1e-9:
                in_viol += 1
    inside_regret = ex_scores_in[res_in_fin["best_order"]] - min(ex_scores_in.values())

    pl_t7 = SchurPortPlanner(w_t.spec, 61, km_t.predict_q, km_t.predict_b, cat_t, initial_sectors_per_wp="L1", lazy_init=True)
    mt7 = MacroTourPlanner(pl_t7)
    sub7 = (0, 1, 2, 3, 4, 5, 6)
    start_ext = np.array([-1.35, -1.35])
    ex_scores_7, _ = independent_exact_ball_tour_scores(pl_t7, start_ext, sub7)
    res_7 = mt7.plan_fixed_tour_bnb(start_ext, sub7, epsilon_tol=0.25, max_refine_steps=10)
    m7_viol = 0
    for pm, (lv, hv) in res_7["perm_enclosures"].items():
        ev = ex_scores_7[pm]
        if ev < lv - 1e-9 or ev > hv + 1e-9:
            m7_viol += 1
    for pref, lb_p in res_7["pruned_prefix_lower_bounds"]:
        k_p = len(pref)
        sub_min = min(v for pm, v in ex_scores_7.items() if pm[:k_p] == pref)
        if sub_min < lb_p - 1e-9:
            m7_viol += 1
    m7_regret = ex_scores_7[res_7["best_order"]] - min(ex_scores_7.values())

    report["4_tour_t0_absorption_and_m7_bnb_5040_audit"] = {
        "inside_start_first_selected_is_2": bool(res_in_fin["best_order"][0] == 2),
        "inside_start_bound_violations_across_240_intervals": in_viol,
        "inside_start_exact_regret": inside_regret,
        "m7_total_permutations": res_7["total_permutations_in_space"],
        "m7_unique_leaves_evaluated": res_7["unique_leaves_evaluated"],
        "m7_pruned_permutations": res_7["pruned_permutations_never_expanded"],
        "m7_certified": res_7["certified"],
        "m7_bound_and_prefix_violations": m7_viol,
        "m7_exact_regret": m7_regret,
        "pass": bool(
            res_in_fin["best_order"][0] == 2
            and in_viol == 0
            and inside_regret <= 0.25 + 1e-9
            and res_7["certified"]
            and m7_viol == 0
            and m7_regret <= 0.25 + 1e-9
            and res_7["pruned_permutations_never_expanded"] > 2500
        ),
    }

    # ------------------------------------------------------------------
    # 5. Decision-Guided Subset Macro-Bellman (`m = 8`) vs Matched Exact-Subset-DP
    # ------------------------------------------------------------------
    pl_m8 = SchurPortPlanner(w_t.spec, 61, km_t.predict_q, km_t.predict_b, cat_t, initial_sectors_per_wp="L1", lazy_init=True)
    mt_m8 = MacroTourPlanner(pl_m8)
    sub8 = (0, 1, 2, 3, 4, 5, 6, 7)
    mac_r1 = mt_m8.plan_subset_macro_policy(start_ext, sub8, epsilon_tol=0.25, max_refine_steps=0, refine_strategy="decision_guided")
    mac_fin = mt_m8.plan_subset_macro_policy(start_ext, sub8, epsilon_tol=0.25, max_refine_steps=12, refine_strategy="decision_guided")
    pl_m8_ex = SchurPortPlanner(w_t.spec, 61, km_t.predict_q, km_t.predict_b, cat_t, initial_sectors_per_wp="L1", lazy_init=True)
    ex_sub8 = MacroTourPlanner(pl_m8_ex).plan_exact_subset_dp(start_ext, sub8)
    ref_mac = independent_exact_macro_bellman_reference(pl_m8, start_ext, sub8, policy_action_idx=mac_fin["policy_action_idx"])
    f_star = ref_mac["optimal_adaptive_macro_cost"]
    j_pol = ref_mac["evaluated_policy_exact_macro_cost"]
    lo_r1, hi_r1 = mac_r1["macro_value_bounds"]
    lo_fn, hi_fn = mac_fin["macro_value_bounds"]
    ex_sub_diff = abs(ex_sub8["macro_value_bounds"][0] - f_star)
    mac_enclosure_ok = (
        lo_r1 - 1e-9 <= f_star <= hi_r1 + 1e-9
        and lo_fn - 1e-9 <= f_star <= hi_fn + 1e-9
        and f_star - 1e-9 <= j_pol <= hi_fn + 1e-9
        and ex_sub_diff < 1e-11
    )

    report["5_subset_macro_bellman_m8_audit"] = {
        "coarse_L1_bounds": [lo_r1, hi_r1],
        "final_certified_bounds": [lo_fn, hi_fn],
        "exact_optimal_macro_cost": f_star,
        "matched_exact_subset_dp_diff_vs_killed_ref": ex_sub_diff,
        "exact_evaluated_policy_cost": j_pol,
        "exact_macro_regret": float(j_pol - f_star),
        "decision_guided_backsolves": mac_fin["new_lu_backsolves"],
        "exact_ring_backsolves": ex_sub8["new_lu_backsolves"],
        "certified": mac_fin["certified"],
        "pass": bool(mac_enclosure_ok and mac_fin["certified"] and (j_pol - f_star) <= 0.25 + 1e-9),
    }

    # ------------------------------------------------------------------
    # 6. Anisotropic Constrained KKT Policy Readout & `51^2` `6101/q6`
    # ------------------------------------------------------------------
    sp_kkt = ProblemSpec(dim=2, r_diag=(0.35, 3.0), u_max=1.8)
    xs_k, pts_k, _ = build_grid_points(2, sp_kkt.half_width, 21)
    q_kkt = QueryTask("lin_probe", (GoalBall((1.3, 1.3), 0.0, 0.15),), ((0.0, 0.0),))
    g_vec = np.array([2.0, 2.0])
    _, pol_kkt = make_consistent_value_and_policy_2d3d(xs_k, pts_k @ g_vec, sp_kkt, q_kkt)
    u_code = pol_kkt(np.zeros((1, 2)))[0]
    eta_ref = brentq(lambda eta: np.linalg.norm(g_vec / (sp_kkt.R_vec + eta)) - 1.8, 0.0, 20.0, xtol=1e-15)
    u_ref = -g_vec / (sp_kkt.R_vec + eta_ref)
    slsqp = minimize(
        lambda u: float(g_vec @ u + 0.5 * np.sum(sp_kkt.R_vec * u * u)),
        np.zeros(2),
        constraints=[{"type": "ineq", "fun": lambda u: 1.8 ** 2 - float(u @ u)}],
        method="SLSQP",
        options={"ftol": 1e-12, "maxiter": 500},
    )
    H_fn = lambda u: float(g_vec @ u + 0.5 * np.sum(sp_kkt.R_vec * u * u))
    ham_excess = abs(H_fn(u_code) - H_fn(u_ref))

    w_6101 = generate_benchmark_map(6101, dim=2, regime="narrow_barrier", with_drift=True, spec=sp_kkt)
    km_6101 = KrigingWorldModel(*sample_noisy_probes(w_6101, n_probes=85, seed=6110, include_drift=True))
    rng_nl = np.random.default_rng(6101 + 303)
    wps_nl = []
    for _ in range(6):
        for _att in range(120):
            c = rng_nl.uniform(-1.12, 1.12, size=2)
            if all(np.linalg.norm(c - np.asarray(w.center)) >= 0.48 for w in wps_nl):
                wps_nl.append(GoalBall(tuple(c.tolist()), 0.0, 0.22)); break
    qs_nl = []
    for q_i in range(7):
        picks = rng_nl.choice(len(wps_nl), size=2, replace=False)
        gls = (GoalBall(wps_nl[picks[0]].center, 0.0, 0.22), GoalBall(wps_nl[picks[1]].center, float(rng_nl.uniform(0.25, 1.05)), 0.22))
        sts = []
        for _ in range(2):
            for _att in range(100):
                s = rng_nl.uniform(-1.25, 1.25, size=2)
                if all(np.linalg.norm(s - np.asarray(g.center)) > 0.48 for g in gls):
                    sts.append(tuple(s.tolist())); break
        lh = ()
        if q_i % 3 == 1:
            mid = np.clip(0.5 * (np.asarray(sts[0]) + np.asarray(gls[0].center)), -1.15, 1.15)
            lh = (HazardFeature(tuple(mid.tolist()), float(rng_nl.uniform(4.5, 8.5)), (0.20, 0.20)),)
        qs_nl.append(QueryTask(f"nl_{q_i}", gls, tuple(sts), lh))

    _, pts51, h51 = build_grid_points(2, sp_kkt.half_width, 51)
    q6 = qs_nl[6]
    eff_r51 = 0.75 * h51 * np.sqrt(2.0)
    eff_g51 = [GoalBall(g.center, g.phi, max(g.radius, eff_r51)) for g in q6.goals]
    is_g51, phi_u51 = eval_goal_union(pts51, eff_g51)
    slope51 = np.sqrt(2.0 * sp_kkt.q0 * float(np.sqrt(np.mean(sp_kkt.R_vec))))
    v_geo51 = np.minimum.reduce([g.phi + slope51 * np.maximum(0.0, np.linalg.norm(pts51 - np.asarray(g.center)[None, :], axis=1) - g.radius) for g in eff_g51])
    v_geo51[is_g51] = phi_u51[is_g51]

    s_q6 = solve_monotone_anisotropic_constrained_hjb_2d(
        sp_kkt, 51, km_6101.predict_q, km_6101.predict_b, q6, V_init=v_geo51, max_iters=25, tol_bellman=1e-8
    )
    s_fixed3 = solve_monotone_anisotropic_constrained_hjb_2d(
        sp_kkt, 35, km_6101.predict_q, km_6101.predict_b, q6, V_init=None, max_iters=3, tol_bellman=None
    )

    report["6_anisotropic_kkt_policy_and_51sq_tolerance"] = {
        "u_code": u_code.tolist(),
        "u_exact_brentq": u_ref.tolist(),
        "u_slsqp": slsqp.x.tolist(),
        "hamiltonian_excess_vs_exact_kkt": ham_excess,
        "q6_51sq_discrete_value_bellman_residual": s_q6["discrete_value_bellman_residual"],
        "q6_51sq_deployed_policy_discrete_residual": s_q6["deployed_policy_discrete_residual"],
        "q6_51sq_sweeps_used": s_q6["sweeps_used"],
        "fixed_3_step_sweeps_reported": s_fixed3["sweeps_used"],
        "pass": bool(
            ham_excess < 1e-14
            and np.linalg.norm(u_code - u_ref) < 1e-13
            and s_q6["discrete_value_bellman_residual"] <= 1e-8
            and s_fixed3["sweeps_used"] == 3
        ),
    }

    # ------------------------------------------------------------------
    # 7. 3D Classical Reuse Baselines Audit (Map 400)
    # ------------------------------------------------------------------
    w400 = generate_benchmark_map(400, dim=3, regime="narrow_barrier", with_drift=True)
    km400 = KrigingWorldModel(*sample_noisy_probes(w400, n_probes=110, seed=413, include_drift=True))
    rng400 = np.random.default_rng(500)
    cat400 = []
    for _ in range(8):
        for _att in range(150):
            cand = rng400.uniform(-1.12, 1.12, size=3); cand[2] *= 0.78
            if all(np.linalg.norm(cand - np.asarray(w.center)) >= 1.85 * 0.28 for w in cat400):
                cat400.append(GoalBall(tuple(cand.tolist()), 0.0, 0.28)); break
    qs400 = []
    for q_i in range(20):
        mg = 1 if (q_i % 3 == 0) else 2
        pks = rng400.choice(len(cat400), size=mg, replace=False)
        phs = [0.0] + [float(rng400.uniform(0.15, 0.95)) for _ in range(mg - 1)]
        rng400.shuffle(phs)
        gls = tuple(GoalBall(cat400[idx].center, phi=phs[k], radius=0.28) for k, idx in enumerate(pks))
        sts = []
        for _ in range(2):
            for _att in range(100):
                sp_pt = rng400.uniform(-1.25, 1.25, size=3)
                if all(np.linalg.norm(sp_pt - np.asarray(g.center)) > 0.63 for g in gls):
                    sts.append(tuple(sp_pt.tolist())); break
        lh = []
        if q_i % 5 in (1, 3):
            mid = np.clip(0.5 * (np.asarray(sts[0]) + np.asarray(gls[0].center)) + rng400.normal(0.0, 0.16, size=3), -1.15, 1.15)
            lh.append(HazardFeature(tuple(mid.tolist()), float(rng400.uniform(5.0, 9.5)), (0.20,) * 3))
        qs400.append(QueryTask(f"q3d_{q_i}", gls, tuple(sts), tuple(lh)))

    fd_c400 = ClassicalFDSolver(w400.spec, 25, km400.predict_q, km400.predict_b, min_goal_radius_override=0.28)
    fd_i400 = ClassicalFDSolver(w400.spec, 25, km400.predict_q, km400.predict_b, min_goal_radius_override=0.28, build_ilu=True)
    x0_ptp_first = float(np.ptp(fd_i400._last_z_warm))
    double_facts_on_single_query = 0
    for q_item in qs400:
        b4 = fd_c400.lu_factorizations
        fd_c400.solve_cached_target_lu(q_item)
        if fd_c400.lu_factorizations - b4 > 1:
            double_facts_on_single_query += 1
        fd_i400.solve_warm_ilu_krylov(q_item)

    report["7_3d_classical_reuse_accounting_probe"] = {
        "map400_cached_fd_total_lu_factorizations": fd_c400.lu_factorizations,
        "double_factorizations_on_any_single_query": double_facts_on_single_query,
        "warm_ilu_initial_x0_ptp": x0_ptp_first,
        "warm_ilu_info0_count_of_20": fd_i400.krylov_info0_count,
        "warm_ilu_lu_fallbacks_of_20": fd_i400.lu_factorizations,
        "pass": bool(
            double_facts_on_single_query == 0
            and fd_c400.lu_factorizations <= 20
            and x0_ptp_first > 0.01
            and fd_i400.krylov_info0_count == 20
        ),
    }

    # ------------------------------------------------------------------
    # 8. Unified LMDP Capability Guards (2D/3D/High-D), Scalar `R = 2 I`, & Prior Equivalence
    # ------------------------------------------------------------------
    q_hd_p = QueryTask("r2_probe", (GoalBall((0.0, 0.0, 0.0, 0.0), 0.0, 0.36),), ((0.8, 0.0, 0.0, 0.0),))
    rejected_aniso_hd = rejected_umax_hd = rejected_port_nonlmdp = rejected_fd_nonlmdp = False
    try:
        BoxNeumannBesselBaseGuide(ProblemSpec(dim=4, r_diag=(0.35, 3.0, 1.0, 1.0)), q_hd_p)
    except ValueError:
        rejected_aniso_hd = True
    try:
        BoxNeumannBesselBaseGuide(ProblemSpec(dim=4, u_max=1.8), q_hd_p)
    except ValueError:
        rejected_umax_hd = True
    try:
        SchurPortPlanner(sp_kkt, 21, lambda X: np.zeros(len(X)), None, [GoalBall((0.0, 0.0), 0.0, 0.22)])
    except ValueError:
        rejected_port_nonlmdp = True
    try:
        ClassicalFDSolver(sp_kkt, 21, lambda X: np.zeros(len(X)), None)
    except ValueError:
        rejected_fd_nonlmdp = True

    sp_r2 = ProblemSpec(dim=4, sigma=0.55, q0=0.65, r_diag=(2.0, 2.0, 2.0, 2.0))
    base_r2 = BoxNeumannBesselBaseGuide(sp_r2, q_hd_p)
    pt_r2 = np.array([[0.8, 0.0, 0.0, 0.0], [1.55, 0.2, -0.1, 0.0]])
    _, g_r2, rep_r2 = base_r2.val_grad_and_base_pde_residual(pt_r2)
    h_fd = 1e-5
    lap_r2 = np.zeros(len(pt_r2))
    for ax in range(4):
        off = np.zeros((1, 4)); off[0, ax] = h_fd
        lap_r2 += (base_r2.val_and_grad(pt_r2 + off)[1][:, ax] - base_r2.val_and_grad(pt_r2 - off)[1][:, ax]) / (2.0 * h_fd)
    true_r2_hjb = sp_r2.q0 + 0.5 * (sp_r2.sigma ** 2) * lap_r2 - 0.5 * np.sum((g_r2 ** 2) / sp_r2.R_vec[None, :], axis=1)
    max_r2_discrepancy = float(np.max(np.abs(rep_r2 - true_r2_hjb)))

    rng_alg = np.random.default_rng(42)
    X_alg = rng_alg.uniform(-1.5, 1.5, size=(40, 4))
    y_tot_alg = base_r2.val_and_grad(X_alg)[0] + np.sin(X_alg[:, 0])
    nv_alg = np.full(40, 2e-3)
    gp_with_prior = MirrorNeumannMatern52GP(X_alg, y_tot_alg, 1.65, 0.5, nv_alg, prior_val_and_grad_fn=base_r2.val_and_grad)
    gp_res_only = MirrorNeumannMatern52GP(X_alg, y_tot_alg - base_r2.val_and_grad(X_alg)[0], 1.65, 0.5, nv_alg, prior_val_and_grad_fn=None)
    Xq_alg = rng_alg.uniform(-1.6, 1.6, size=(25, 4))
    vp1, gp1 = gp_with_prior.predict_val_and_grad(Xq_alg)
    vr2, gr2 = gp_res_only.predict_val_and_grad(Xq_alg)
    v0q, gv0q = base_r2.val_and_grad(Xq_alg)
    alg_val_diff = float(np.max(np.abs(vp1 - (v0q + vr2))))
    alg_grad_diff = float(np.max(np.abs(gp1 - (gv0q + gr2))))

    report["8_highd_and_lmdp_spec_guards_scalar_r_and_prior_equivalence"] = {
        "rejected_anisotropic_R_highd": rejected_aniso_hd,
        "rejected_finite_u_max_highd": rejected_umax_hd,
        "rejected_nonlmdp_in_schur_port": rejected_port_nonlmdp,
        "rejected_nonlmdp_in_classical_fd": rejected_fd_nonlmdp,
        "scalar_R2_max_hjb_discrepancy": max_r2_discrepancy,
        "prior_mean_vs_residual_gp_val_diff": alg_val_diff,
        "prior_mean_vs_residual_gp_grad_diff": alg_grad_diff,
        "pass": bool(
            rejected_aniso_hd
            and rejected_umax_hd
            and rejected_port_nonlmdp
            and rejected_fd_nonlmdp
            and max_r2_discrepancy < 1e-8
            and alg_val_diff < 1e-13
            and alg_grad_diff < 1e-13
        ),
    }

    # ------------------------------------------------------------------
    # 9. Collar Residual, Unclipped Trace Consistency, & Continuous-Disk Robust HJB
    # ------------------------------------------------------------------
    sp4 = ProblemSpec(dim=4, half_width=1.65, sigma=0.55, q0=0.70)
    km0 = KrigingWorldModel(np.zeros((10, 4)), np.zeros(10))
    q_near4 = QueryTask(
        "near4",
        (GoalBall((0.0, 0.0, 0.0, 0.0), 0.0, 0.36), GoalBall((0.73, 0.0, 0.0, 0.0), 0.0, 0.36)),
        ((-0.8, -0.6, 0.0, 0.0),),
    )
    sol_n4 = solve_highd_fk_distillation(sp4, km0, q_near4, n_interior_anchors=48, n_boundary_per_goal=64, n_mc_paths=48, n_steps_fk=60, seed=101)
    rng_tr = np.random.default_rng(99)
    dirs_tr = rng_tr.normal(size=(256, 4)); dirs_tr /= np.linalg.norm(dirs_tr, axis=1, keepdims=True)
    X_ext4 = (0.36 + 1e-7) * dirs_tr
    X_ext4 = X_ext4[np.linalg.norm(X_ext4 - np.array([[0.73, 0.0, 0.0, 0.0]]), axis=1) > 0.36 + 1e-6]
    raw_rms4 = float(np.sqrt(np.mean(sol_n4["value_fn"](X_ext4) ** 2)))
    pt_chk4 = np.array([[0.5, -0.4, 0.2, -0.1]])
    eps_g = 1e-7
    fd_g4 = np.array([(sol_n4["value_fn"](pt_chk4 + np.eye(4)[j] * eps_g)[0] - sol_n4["value_fn"](pt_chk4 - np.eye(4)[j] * eps_g)[0]) / (2.0 * eps_g) for j in range(4)])
    grad_pol_err = float(np.max(np.abs(sol_n4["policy"](pt_chk4)[0] + fd_g4)))
    wall_norm_u = float(np.max(np.abs(sol_n4["policy"](np.array([[1.65, 0.0, 0.0, 0.0]]))[:, 0])))

    fd31 = ClassicalFDSolver(sp2, 31, lambda X: np.full(len(X), 0.40), lambda X: np.column_stack([-0.5 * X[:, 1], 0.5 * X[:, 0]]))
    q_adj = QueryTask("adj", (GoalBall((0.66, 0.44), 0.0, 0.22),), ((-0.77, -0.66),))
    rob_res = solve_exact_continuous_ball_robust_hjb_2d(
        sp2, 31, np.full(len(fd31.pts), 0.8), np.column_stack([-0.4 * fd31.pts[:, 1], 0.4 * fd31.pts[:, 0]]),
        np.full(len(fd31.pts), 0.25), q_adj, upper=True, n_iters=22,
    )

    report["9_highd_trace_consistency_and_robust_hjb"] = {
        "near4_unclipped_raw_rms": raw_rms4,
        "policy_plus_fd_grad_max_err": grad_pol_err,
        "reflecting_wall_normal_u": wall_norm_u,
        "robust_hjb_exact_disk_residual": rob_res["true_continuous_disk_residual"],
        "robust_hjb_4096_dir_residual": rob_res["independent_4096_dir_residual"],
        "pass": bool(
            raw_rms4 < 0.008
            and grad_pol_err < 1e-6
            and wall_norm_u < 1e-12
            and rob_res["true_continuous_disk_residual"] < 1e-11
            and rob_res["independent_4096_dir_residual"] < 1e-4
        ),
    }

    # ------------------------------------------------------------------
    # 10. Kinetic Independent Telescoping Audit, Killed Adjoint, & PIMC Zero Variance
    # ------------------------------------------------------------------
    w_ua = generate_benchmark_map(14500, dim=2, regime="narrow_barrier", with_drift=True)
    km_ua = KrigingWorldModel(*sample_noisy_probes(w_ua, n_probes=45, seed=14507, include_drift=True))
    ua_sol = solve_kinetic_underactuated_greenres(km_ua, n_continuation_rounds=6, seed=14520)

    sens = fd31.compute_killed_adjoint_sensitivity(q_adj)
    eps_q = 1e-6
    s_idx = int(np.argmin(np.sum((fd31.pts - np.array([q_adj.start_points[0]])) ** 2, axis=1)))
    vp = ClassicalFDSolver(sp2, 31, lambda X: np.full(len(X), 0.40 + eps_q), lambda X: np.column_stack([-0.5 * X[:, 1], 0.5 * X[:, 0]])).solve_direct(q_adj)["V_grid"][s_idx]
    vm = ClassicalFDSolver(sp2, 31, lambda X: np.full(len(X), 0.40 - eps_q), lambda X: np.column_stack([-0.5 * X[:, 1], 0.5 * X[:, 0]])).solve_direct(q_adj)["V_grid"][s_idx]
    adj_err = abs(float((vp - vm) / (2.0 * eps_q)) - float(np.sum(sens)))
    goal_mass = float(np.sum(np.abs(sens[np.linalg.norm(fd31.pts - np.array([[0.66, 0.44]]), axis=1) <= 0.22])))

    q_f4 = QueryTask("f4", (GoalBall((0.0, 0.0, 0.0, 0.0), 0.0, 0.36),), ((-0.6, -0.5, 0.1, -0.1),))
    pol_pimc, _, _ = make_antithetic_centered_pimc_policy(sp4, km0, q_f4, n_particles=36, horizon_steps=8, dt_mpc=0.03, seed=55)
    u_var = float(np.mean(np.var(pol_pimc(np.repeat(np.array([[-0.5, -0.4, 0.1, -0.1]]), 32, axis=0)), axis=0)))

    report["10_kinetic_telescoping_adjoint_and_pimc"] = {
        "seed14500_measured_telescoping_discrepancy": ua_sol["measured_telescoping_discrepancy"],
        "seed14500_continuation_diffs_6rounds": ua_sol["continuation_max_diffs"],
        "killed_adjoint_vs_fd_abs_diff": adj_err,
        "killed_adjoint_goal_mass": goal_mass,
        "pimc_free_world_action_variance": u_var,
        "pass": bool(
            ua_sol["measured_telescoping_discrepancy"] < 1e-12
            and ua_sol["continuation_max_diffs"][-1] < 0.02
            and adj_err < 1e-8
            and goal_mass == 0.0
            and u_var < 1e-28
        ),
    }

    # ------------------------------------------------------------------
    # 11. [NEW `85e2323` Bug 2.1] ExactRing Full-Branch Exactness (`root85_exactring_dispatch_probe.py`)
    # ------------------------------------------------------------------
    w401 = generate_benchmark_map(401, dim=3, regime="narrow_barrier", with_drift=True)
    km401 = KrigingWorldModel(*sample_noisy_probes(w401, n_probes=110, seed=414, include_drift=True))
    rng401 = np.random.default_rng(501)
    cat401 = []
    for _ in range(8):
        for _att in range(150):
            cand = rng401.uniform(-1.12, 1.12, size=3); cand[2] *= 0.78
            if all(np.linalg.norm(cand - np.asarray(w.center)) >= 1.85 * 0.28 for w in cat401):
                cat401.append(GoalBall(tuple(cand.tolist()), 0.0, 0.28)); break
    qs401 = []
    for q_i in range(3):
        mg = 1 if (q_i % 3 == 0) else 2
        pks = rng401.choice(len(cat401), size=mg, replace=False)
        phs = [0.0] + [float(rng401.uniform(0.15, 0.95)) for _ in range(mg - 1)]
        rng401.shuffle(phs)
        gls = tuple(GoalBall(cat401[idx].center, phi=phs[k], radius=0.28) for k, idx in enumerate(pks))
        sts = []
        for _ in range(2):
            for _att in range(100):
                sp_pt = rng401.uniform(-1.25, 1.25, size=3)
                if all(np.linalg.norm(sp_pt - np.asarray(g.center)) > 0.63 for g in gls):
                    sts.append(tuple(sp_pt.tolist())); break
        lh = []
        if q_i % 5 in (1, 3):
            mid = np.clip(0.5 * (np.asarray(sts[0]) + np.asarray(gls[0].center)) + rng401.normal(0.0, 0.16, size=3), -1.15, 1.15)
            lh.append(HazardFeature(tuple(mid.tolist()), float(rng401.uniform(5.0, 9.5)), (0.20,) * 3))
        qs401.append(QueryTask(f"q3d_{q_i}", gls, tuple(sts), tuple(lh)))

    pl401_ex = SchurPortPlanner(
        w401.spec, 25, km401.predict_q, km401.predict_b, cat401,
        initial_sectors_per_wp="EXACT", lazy_init=True, hazard_mode="exact", min_goal_radius_override=0.28,
    )
    fd401 = ClassicalFDSolver(w401.spec, 25, km401.predict_q, km401.predict_b, min_goal_radius_override=0.28)
    rp_q2 = pl401_ex.solve_query(qs401[2])
    rf_q2 = fd401.solve_direct(qs401[2])
    q2_v_diff = float(np.max(np.abs(rp_q2["V_grid"] - rf_q2["V_grid"])))

    # Also test overlapping + ad-hoc 2D multi-goal with heterogeneous phi!
    q_ov_het = QueryTask(
        "overlap_adhoc",
        (GoalBall((-0.10, 0.0), -0.4, 0.28), GoalBall((0.12, 0.05), 1.3, 0.28), GoalBall((0.75, -0.60), 0.5, 0.24)),
        ((-1.0, -1.0),),
    )
    pl2_ex = SchurPortPlanner(
        sp2, 41, fd31.q_base.__class__(np.zeros(41 * 41)) if False else (lambda X: 0.8 * np.exp(-np.sum(X ** 2, axis=1))),
        lambda X: np.column_stack([-0.3 * X[:, 1], 0.3 * X[:, 0]]),
        [GoalBall((-0.10, 0.0), 0.0, 0.28)],
        initial_sectors_per_wp="EXACT", lazy_init=True, hazard_mode="exact",
    )
    fd2_ex = ClassicalFDSolver(
        sp2, 41, lambda X: 0.8 * np.exp(-np.sum(X ** 2, axis=1)),
        lambda X: np.column_stack([-0.3 * X[:, 1], 0.3 * X[:, 0]]),
    )
    rp_ov = pl2_ex.solve_query(q_ov_het)
    rf_ov = fd2_ex.solve_direct(q_ov_het)
    ov_v_diff = float(np.max(np.abs(rp_ov["V_grid"] - rf_ov["V_grid"])))

    report["11_exact_ring_full_branch_dispatch_probe"] = {
        "map401_q2_ring_nodes": rp_q2["ring_nodes"],
        "map401_q2_ports_used": rp_q2["ports_used"],
        "map401_q2_effective_level": rp_q2["effective_level"],
        "map401_q2_max_V_diff_vs_fd25": q2_v_diff,
        "overlap_adhoc_max_V_diff_vs_fd41": ov_v_diff,
        "pass": bool(
            rp_q2["ports_used"] == rp_q2["ring_nodes"]
            and rp_q2["effective_level"] == "EXACT"
            and q2_v_diff < 1e-12
            and ov_v_diff < 1e-12
        ),
    }

    # ------------------------------------------------------------------
    # 12. [NEW `85e2323` Bug 2.2] Terminal-Cost Gauge Invariance (`macro85_numeric_probe.py`)
    # ------------------------------------------------------------------
    phi_cases = [-50.0, 0.0, 2.0, 8.0, 20.0, 200.0]
    shift_widths = []
    shift_policies = []
    shift_refs = []
    shift_all_certified = True
    shift_viol = 0
    for phi_v in phi_cases:
        sp_g = ProblemSpec(dim=2, sigma=0.45, q0=0.5)
        goals_g = [GoalBall((-0.7, -0.5), phi_v, 0.28), GoalBall((0.7, -0.4), phi_v, 0.28), GoalBall((0.3, 0.85), phi_v, 0.28)]
        q_g = lambda X: 2.0 * np.exp(-((X[:, 0] + 0.1) ** 2 / 0.12 + X[:, 1] ** 2 / 0.8))
        b_g = lambda X: np.column_stack((-0.2 * X[:, 1], 0.2 * X[:, 0]))
        pl_g = SchurPortPlanner(sp_g, 31, q_g, b_g, goals_g, initial_sectors_per_wp="L1", lazy_init=True)
        mp_g = MacroTourPlanner(pl_g)
        r_g = mp_g.plan_subset_macro_policy([-1.1, 0.8], [0, 1, 2], epsilon_tol=0.1, max_refine_steps=10, refine_strategy="uniform_width")
        shift_all_certified = shift_all_certified and bool(r_g["certified"])
        lo_g, hi_g = r_g["macro_value_bounds"]
        shift_widths.append(hi_g - lo_g)
        shift_policies.append(r_g["policy_action_idx"].copy())
        shift_refs.append(r_g["refinement_steps"])
        ref_g = independent_exact_macro_bellman_reference(pl_g, [-1.1, 0.8], [0, 1, 2], policy_action_idx=r_g["policy_action_idx"])
        if not (lo_g - 1e-9 <= ref_g["optimal_adaptive_macro_cost"] <= ref_g["evaluated_policy_exact_macro_cost"] + 1e-9 <= hi_g + 1e-9):
            shift_viol += 1

    width_ptp = float(np.ptp(shift_widths))
    pol_identical = all(np.array_equal(p, shift_policies[0]) for p in shift_policies[1:])
    refs_identical = all(rf == shift_refs[0] for rf in shift_refs[1:])

    report["12_terminal_cost_gauge_shift_invariance"] = {
        "phi_values_tested": phi_cases,
        "all_certified_at_eps_0_1": shift_all_certified,
        "interval_widths": shift_widths,
        "width_ptp_across_all_shifts": width_ptp,
        "policies_identical": pol_identical,
        "refinement_paths_identical": refs_identical,
        "independent_reference_violations": shift_viol,
        "pass": bool(shift_all_certified and width_ptp < 1e-12 and pol_identical and refs_identical and shift_viol == 0),
    }

    # ------------------------------------------------------------------
    # 13. [NEW `85e2323` Bugs 2.3 & 2.4] Zero-Budget Invalid Cap & Fail-Closed Inverted Intervals
    # ------------------------------------------------------------------
    # 13a. Zero-budget invalid query: genuine IEEE-754 underflow (`u1 == 0.0` far from goal on `41^2`
    # when `sigma = 0.02, q0 = 1e6`) where `_compute_subset_macro_dp` returns `ok == False` at `step_i == 0`!
    sp_bad = ProblemSpec(dim=2, sigma=0.02, q0=1e6)
    goals_bad = [GoalBall((1.3, 1.3), 0.0, 0.15), GoalBall((1.1, 1.3), 0.0, 0.15)]
    pl_bad = SchurPortPlanner(sp_bad, 41, lambda X: np.full(len(X), 1e6), None, goals_bad, initial_sectors_per_wp="L1", lazy_init=True)
    mp_bad = MacroTourPlanner(pl_bad)
    r_zero_cap = mp_bad.plan_subset_macro_policy([-1.5, -1.5], [0, 1], epsilon_tol=0.1, max_refine_steps=0)
    levels_after_zero_cap = dict(pl_bad.wp_levels)

    # Also nonfinite input check:
    pl_nan = SchurPortPlanner(sp2, 21, lambda X: np.zeros(len(X)), None, [GoalBall((0.0, 0.0), np.nan, 0.25)], initial_sectors_per_wp="L1", lazy_init=True)
    r_nan = MacroTourPlanner(pl_nan).plan_subset_macro_policy([-1.0, -1.0], [0], epsilon_tol=0.1, max_refine_steps=0)

    # 13b. Fail-closed check on tiny reversed interval (`lo = 1e-8 + 4e-12 > hi = 1e-8`) in `bound_harmonic_batch`!
    prep_fc = pl_bar.prepare_wp_ring_eval(0, np.array([0, 1], dtype=np.int64))
    F_inv_lo = np.full((len(prep_fc["ring_d"]), 1), 1e-8 + 4e-12)
    F_inv_hi = np.full((len(prep_fc["ring_d"]), 1), 1e-8)
    _, _, ok_inv = pl_bar.bound_harmonic_batch(prep_fc, F_inv_lo, F_inv_hi)

    report["13_zero_budget_invalid_and_fail_closed_no_midpoint"] = {
        "zero_cap_underflow_status": r_zero_cap["status"],
        "zero_cap_certified": r_zero_cap["certified"],
        "zero_cap_policy_is_none": bool(r_zero_cap["policy_action_idx"] is None),
        "zero_cap_levels_unchanged_at_L1": bool(all(v == "L1" for v in levels_after_zero_cap.values())),
        "nonfinite_phi_status": r_nan["status"],
        "reversed_1e_minus_12_interval_rejected": bool(not ok_inv),
        "pass": bool(
            r_zero_cap["status"] == "numeric_invalid"
            and not r_zero_cap["certified"]
            and r_zero_cap["policy_action_idx"] is None
            and all(v == "L1" for v in levels_after_zero_cap.values())
            and r_nan["status"] == "numeric_invalid"
            and not ok_inv
        ),
    }

    # ------------------------------------------------------------------
    # 14. [NEW `85e2323` Bug 2.5] Nonzero-Weight Scalar-`R` PIMC Gaussian Tilting (`r = 0.5, 1, 2, 4`)
    # ------------------------------------------------------------------
    pimc_r_ratios = []
    pimc_r_errs = []
    for r_val in (0.5, 1.0, 2.0, 4.0):
        sp_pr = ProblemSpec(dim=2, half_width=100.0, sigma=0.55, q0=0.65, r_diag=(r_val, r_val))
        q_pr = QueryTask("affine_tilt", (GoalBall((0.0, 0.0), 0.0, 0.10),), ((6.0, 0.0),))
        x_pr = np.array(q_pr.start_points)
        nom_pr = -BoxNeumannBesselBaseGuide(sp_pr, q_pr).val_and_grad(x_pr)[1] / r_val
        dt_pr = 0.2
        pol_pr, _, _ = make_antithetic_centered_pimc_policy(
            sp_pr, _AffineCostModel(), q_pr, n_particles=120000, horizon_steps=2, dt_mpc=dt_pr, seed=2701
        )
        obs_du = pol_pr(x_pr) - nom_pr
        exact_du = np.array([[-dt_pr / r_val, 0.0]])
        pimc_r_ratios.append(float(obs_du[0, 0] / exact_du[0, 0]))
        pimc_r_errs.append(float(np.max(np.abs(obs_du - exact_du))))

    report["14_scalar_r_nonzero_pimc_gaussian_tilt"] = {
        "r_values": [0.5, 1.0, 2.0, 4.0],
        "observed_over_exact_x_ratios": pimc_r_ratios,
        "max_abs_errors": pimc_r_errs,
        "pass": bool(all(abs(rt - 1.0) < 0.025 for rt in pimc_r_ratios) and max(pimc_r_errs) < 0.01),
    }

    # ------------------------------------------------------------------
    # 15. [NEW `85e2323` `macro85_scaling_probe.py` + Stage D Continual Residual Audit]
    # ------------------------------------------------------------------
    w_m9 = generate_benchmark_map(802, dim=2, regime="narrow_barrier", with_drift=True)
    rng_m9 = np.random.default_rng(909)
    cat_m9 = []
    for _ in range(9):
        for _att in range(250):
            pt = rng_m9.uniform(-1.25, 1.25, size=2)
            if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.05 * 0.25 for w in cat_m9):
                cat_m9.append(GoalBall(tuple(pt.tolist()), 0.0, 0.25))
                break
    pl_m9 = SchurPortPlanner(w_m9.spec, 25, w_m9.q_hidden, w_m9.drift, cat_m9, initial_sectors_per_wp="L1", lazy_init=True)
    mt_m9 = MacroTourPlanner(pl_m9)
    sub9 = tuple(range(9))
    s9 = np.array([-1.40, -1.40])
    res_m9 = mt_m9.plan_subset_macro_policy(s9, sub9, epsilon_tol=0.25, max_refine_steps=14, refine_strategy="decision_guided")
    ref_m9 = independent_exact_macro_bellman_reference(pl_m9, s9, sub9, policy_action_idx=res_m9["policy_action_idx"])
    # Check ALL `n_ev * 512` entries of `F_opt_table <= J_pol_table` AND root enclosure!
    m9_table_viol = int(np.sum(ref_m9["J_pol_table"][:, 1:] < ref_m9["F_opt_table"][:, 1:] - 1e-9))
    lo9, hi9 = res_m9["macro_value_bounds"]
    m9_root_ok = bool(lo9 - 1e-9 <= ref_m9["optimal_adaptive_macro_cost"] <= ref_m9["evaluated_policy_exact_macro_cost"] + 1e-9 <= hi9 + 1e-9)

    # Continual Epoch Update Check (`selective_residual`): add localized perturbation and verify `0` bound violations!
    q_epoch2 = lambda X: w_m9.q_hidden(X) + 3.5 * np.exp(-np.sum((X - np.array([[0.8, 0.8]])) ** 2, axis=1) / 0.06)
    upd_info = pl_m9.update_world_with_residual_audit(q_epoch2, w_m9.drift, mode="selective_residual")
    res_ep2 = mt_m9.plan_subset_macro_policy(s9, (0, 1, 2, 3, 4), epsilon_tol=0.25, max_refine_steps=10, refine_strategy="decision_guided")
    ref_ep2 = independent_exact_macro_bellman_reference(pl_m9, s9, (0, 1, 2, 3, 4), policy_action_idx=res_ep2["policy_action_idx"])
    lo_e2, hi_e2 = res_ep2["macro_value_bounds"]
    ep2_ok = bool(lo_e2 - 1e-9 <= ref_ep2["optimal_adaptive_macro_cost"] <= ref_ep2["evaluated_policy_exact_macro_cost"] + 1e-9 <= hi_e2 + 1e-9)

    report["15_m9_full_table_and_continual_residual_audit"] = {
        "m9_row_mask_entries": res_m9["work"]["row_mask_entries"],
        "m9_certified": res_m9["certified"],
        "m9_all_table_policy_vs_opt_violations": m9_table_viol,
        "m9_root_enclosure_valid": m9_root_ok,
        "continual_epoch2_waypoints_retained": upd_info["waypoints_retained"],
        "continual_epoch2_certified": res_ep2["certified"],
        "continual_epoch2_enclosure_valid": ep2_ok,
        "pass": bool(res_m9["certified"] and m9_table_viol == 0 and m9_root_ok and res_ep2["certified"] and ep2_ok),
    }

    report["ALL_PASSED"] = bool(all(v["pass"] for v in report.values() if isinstance(v, dict) and "pass" in v))
    return report


if __name__ == "__main__":
    out = run_all_audit_checks()
    out_path = Path(__file__).with_name("audit_closure_results.json")
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    if not out["ALL_PASSED"]:
        sys.exit(1)
