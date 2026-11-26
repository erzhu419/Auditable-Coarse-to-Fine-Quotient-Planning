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
    independent_exact_ball_operators,
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
    # 15. [UPGRADED `ddd19c5` Sec 4.1] True 4-Way Full-Table `m = 9` Envelope Check + Incremental-DP Identity
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
    res_m9 = mt_m9.plan_subset_macro_policy(
        s9, sub9, epsilon_tol=0.25, max_refine_steps=14, refine_strategy="decision_guided",
        use_incremental_dp=True, return_dp_tables=True,
    )
    # Also run from-scratch DP on an identical clone to verify IEEE-754 exactness of Incremental DP!
    pl_m9_scr = SchurPortPlanner(w_m9.spec, 25, w_m9.q_hidden, w_m9.drift, cat_m9, initial_sectors_per_wp="L1", lazy_init=True)
    res_m9_scr = MacroTourPlanner(pl_m9_scr).plan_subset_macro_policy(
        s9, sub9, epsilon_tol=0.25, max_refine_steps=14, refine_strategy="decision_guided",
        use_incremental_dp=False, return_dp_tables=True,
    )
    inc_vs_scr_max_diff = max(
        float(np.max(np.abs(res_m9["F_lo_table"] - res_m9_scr["F_lo_table"]))),
        float(np.max(np.abs(res_m9["F_hi_table"] - res_m9_scr["F_hi_table"]))),
    )
    ref_m9 = independent_exact_macro_bellman_reference(pl_m9, s9, sub9, policy_action_idx=res_m9["policy_action_idx"])

    # TRUE 4-WAY INEQUALITY CHECK across ALL `73 * 511` non-empty subset entries:
    # `F_lo_table <= F_opt_table <= J_pol_table <= F_hi_table`!
    F_lo_nz = res_m9["F_lo_table"][:, 1:]
    F_hi_nz = res_m9["F_hi_table"][:, 1:]
    F_opt_nz = ref_m9["F_opt_table"][:, 1:]
    J_pol_nz = ref_m9["J_pol_table"][:, 1:]
    m9_four_way_viol = int(np.sum(
        (F_opt_nz < F_lo_nz - 1e-9)
        | (J_pol_nz < F_opt_nz - 1e-9)
        | (J_pol_nz > F_hi_nz + 1e-9)
        | (F_lo_nz > F_hi_nz + 1e-12)
    ))
    lo9, hi9 = res_m9["macro_value_bounds"]
    m9_root_ok = bool(
        (lo9 - 1e-9 <= ref_m9["optimal_adaptive_macro_cost"] <= hi9 + 1e-9)
        and (ref_m9["optimal_adaptive_macro_cost"] - 1e-9 <= ref_m9["evaluated_policy_exact_macro_cost"] <= hi9 + 1e-9)
    )

    q_epoch2 = lambda X: w_m9.q_hidden(X) + 3.5 * np.exp(-np.sum((X - np.array([[0.8, 0.8]])) ** 2, axis=1) / 0.06)
    upd_info = pl_m9.update_world_with_residual_audit(q_epoch2, w_m9.drift, mode="selective_residual")
    res_ep2 = mt_m9.plan_subset_macro_policy(
        s9, (0, 1, 2, 3, 4), epsilon_tol=0.25, max_refine_steps=10, refine_strategy="decision_guided",
        return_dp_tables=True,
    )
    ref_ep2 = independent_exact_macro_bellman_reference(pl_m9, s9, (0, 1, 2, 3, 4), policy_action_idx=res_ep2["policy_action_idx"])
    ep2_four_way_viol = int(np.sum(
        (ref_ep2["F_opt_table"][:, 1:] < res_ep2["F_lo_table"][:, 1:] - 1e-9)
        | (ref_ep2["J_pol_table"][:, 1:] < ref_ep2["F_opt_table"][:, 1:] - 1e-9)
        | (ref_ep2["J_pol_table"][:, 1:] > res_ep2["F_hi_table"][:, 1:] + 1e-9)
    ))

    report["15_m9_full_table_and_continual_residual_audit"] = {
        "m9_row_mask_entries": res_m9["work"]["row_mask_entries"],
        "m9_nonempty_entries_checked": int(F_lo_nz.size),
        "m9_certified": res_m9["certified"],
        "m9_four_way_table_violations": m9_four_way_viol,
        "m9_incremental_vs_scratch_max_diff": inc_vs_scr_max_diff,
        "m9_root_enclosure_valid": m9_root_ok,
        "continual_epoch2_waypoints_retained": upd_info["waypoints_retained"],
        "continual_epoch2_certified": res_ep2["certified"],
        "continual_epoch2_four_way_table_violations": ep2_four_way_viol,
        "pass": bool(
            res_m9["certified"]
            and m9_four_way_viol == 0
            and inc_vs_scr_max_diff < 1e-13
            and m9_root_ok
            and res_ep2["certified"]
            and ep2_four_way_viol == 0
        ),
    }

    # ------------------------------------------------------------------
    # 16. [NEW `ddd19c5` P0 Bug 3.1] Cross-Waypoint Interleaved Epoch Contamination Probe (`ddd_continual_probe.py`)
    # ------------------------------------------------------------------
    sp_cw = ProblemSpec(dim=2, half_width=1.65, sigma=0.45, q0=0.5)
    gs_cw = [GoalBall((-0.6, 0.0), 0.0, 0.32), GoalBall((0.6, 0.0), 0.0, 0.32)]
    q0_cw = lambda X: np.zeros(len(X))
    q1_cw = lambda X: np.full(len(X), 0.001)
    q2_cw = lambda X: np.full(len(X), 0.003)

    cw_harmonic_viols = 0
    cw_macro_viols = 0
    cw_max_col_res = 0.0
    for order_ab in ((0, 1), (1, 0)):
        pl_cw = SchurPortPlanner(sp_cw, 25, q0_cw, None, gs_cw, initial_sectors_per_wp="L1", lazy_init=False)
        pl_cw.update_world_with_residual_audit(q1_cw, None, mode="selective_residual")
        pl_cw.ensure_wp_level(order_ab[0], "EXACT")
        pl_cw.ensure_wp_level(order_ab[1], "EXACT")
        for wid in (0, 1):
            ss_w, U_w = pl_cw._wp_tree[wid]["EXACT"]
            B_w = np.zeros_like(U_w)
            for j_c, s_c in enumerate(ss_w):
                B_w[s_c, j_c] = 1.0
            cw_max_col_res = max(cw_max_col_res, float(np.max(np.abs(pl_cw.A0 @ U_w - B_w))))

        prep_cw = pl_cw.prepare_wp_ring_eval(order_ab[1], np.arange(len(pl_cw.pts)))
        F_ones = np.ones((len(pl_cw.wp_rings[order_ab[1]]), 1))
        L_cw, H_cw, ok_cw = pl_cw.bound_harmonic_batch(prep_cw, F_ones, F_ones)
        ref_cw = SchurPortPlanner(sp_cw, 25, q1_cw, None, gs_cw, initial_sectors_per_wp="EXACT", lazy_init=True)
        r_ref_cw = ref_cw.solve_query(QueryTask("ref_cw", (gs_cw[order_ab[1]],), ((0.0, 0.0),)))
        ext_cw = ~pl_cw.wp_masks[order_ab[1]]
        cw_harmonic_viols += int(np.sum((r_ref_cw["Z"][ext_cw] < L_cw[ext_cw, 0] - 1e-10) | (r_ref_cw["Z"][ext_cw] > H_cw[ext_cw, 0] + 1e-10)))

        res_cw = MacroTourPlanner(pl_cw).plan_subset_macro_policy((0.0, -1.2), (0, 1), epsilon_tol=0.25, max_refine_steps=12)
        refm_cw = independent_exact_macro_bellman_reference(pl_cw, (0.0, -1.2), (0, 1), res_cw["policy_action_idx"])
        lo_cw, hi_cw = res_cw["macro_value_bounds"]
        f_cw = refm_cw["optimal_adaptive_macro_cost"]
        j_cw = refm_cw["evaluated_policy_exact_macro_cost"]
        if not ((lo_cw - 1e-9 <= f_cw <= hi_cw + 1e-9) and (f_cw - 1e-9 <= j_cw <= hi_cw + 1e-9)):
            cw_macro_viols += 1

        # Second consecutive update (`q1 -> q2`) with interleaved L4 -> EXACT
        pl_cw.update_world_with_residual_audit(q2_cw, None, mode="selective_residual")
        res_cw2 = MacroTourPlanner(pl_cw).plan_subset_macro_policy((0.0, -1.2), (0, 1), epsilon_tol=0.25, max_refine_steps=12)
        refm_cw2 = independent_exact_macro_bellman_reference(pl_cw, (0.0, -1.2), (0, 1), res_cw2["policy_action_idx"])
        lo_cw2, hi_cw2 = res_cw2["macro_value_bounds"]
        if not (lo_cw2 - 1e-9 <= refm_cw2["optimal_adaptive_macro_cost"] <= refm_cw2["evaluated_policy_exact_macro_cost"] + 1e-9 and refm_cw2["evaluated_policy_exact_macro_cost"] <= hi_cw2 + 1e-9):
            cw_macro_viols += 1

    report["16_cross_waypoint_epoch_contamination_probe"] = {
        "max_new_exact_column_residual": cw_max_col_res,
        "exterior_harmonic_violations": cw_harmonic_viols,
        "macro_certificate_violations": cw_macro_viols,
        "pass": bool(cw_max_col_res < 1e-12 and cw_harmonic_viols == 0 and cw_macro_viols == 0),
    }

    # ------------------------------------------------------------------
    # 17. [NEW `ddd19c5` P0 Bug 3.2] Single-Query Post-Update Residual Propagation Probe (`9^2`)
    # ------------------------------------------------------------------
    sp_sq = ProblemSpec(dim=2, half_width=1.0, sigma=0.45, q0=0.5)
    go_sq = GoalBall((0.0, 0.0), phi=0.0, radius=0.01)
    qt_sq = QueryTask("after_update", (go_sq,), ((-0.75, -0.75),))

    # Case A: GPT6's exact `q: 0.5 -> 0.501` counterexample (`80/81` violations in `ddd19c5` -> `0/81` now!)
    pl_sq = SchurPortPlanner(sp_sq, 9, q0_cw, None, [go_sq], initial_sectors_per_wp="L1", lazy_init=False, min_goal_radius_override=0.01)
    upd_sq = pl_sq.update_world_with_residual_audit(q1_cw, None, mode="selective_residual")
    r_sq = pl_sq.solve_query(qt_sq)
    fd_sq = ClassicalFDSolver(sp_sq, 9, q1_cw, None, min_goal_radius_override=0.01).solve_direct(qt_sq)
    lo_sq = r_sq["V_grid"] + r_sq["ring_value_lower_shift"]
    hi_sq = r_sq["V_grid"] + r_sq["ring_value_upper_shift"]
    sq_viols = int(np.sum((fd_sq["V_grid"] < lo_sq - 1e-10) | (fd_sq["V_grid"] > hi_sq + 1e-10)))

    # Case B: Mild perturbation (`dq = 1e-5`) where `raw_Z - delta_Z > 0` everywhere -> 0 LU refactor + valid residual scope!
    q_mild = lambda X: np.full(len(X), 1e-5)
    pl_sq_m = SchurPortPlanner(sp_sq, 9, q0_cw, None, [go_sq], initial_sectors_per_wp="L1", lazy_init=False, min_goal_radius_override=0.01)
    pl_sq_m.update_world_with_residual_audit(q_mild, None, mode="selective_residual")
    r_sq_m = pl_sq_m.solve_query(qt_sq)
    fd_sq_m = ClassicalFDSolver(sp_sq, 9, q_mild, None, min_goal_radius_override=0.01).solve_direct(qt_sq)
    lo_m_sq = r_sq_m["V_grid"] + r_sq_m["ring_value_lower_shift"]
    hi_m_sq = r_sq_m["V_grid"] + r_sq_m["ring_value_upper_shift"]
    sq_m_viols = int(np.sum((fd_sq_m["V_grid"] < lo_m_sq - 1e-10) | (fd_sq_m["V_grid"] > hi_m_sq + 1e-10)))

    # Case C: Post-update query WITH local hazard (`mh > 0`)
    hz_sq = (HazardFeature((0.25, 0.25), 2.5, (0.2, 0.2)),)
    qt_sq_hz = QueryTask("after_update_hz", (go_sq,), ((-0.75, -0.75),), local_hazards=hz_sq)
    pl_sq_hz = SchurPortPlanner(sp_sq, 9, q0_cw, None, [go_sq], initial_sectors_per_wp="L1", lazy_init=False, hazard_mode="exact", min_goal_radius_override=0.01)
    pl_sq_hz.update_world_with_residual_audit(q1_cw, None, mode="selective_residual")
    r_sq_hz = pl_sq_hz.solve_query(qt_sq_hz)
    fd_sq_hz = ClassicalFDSolver(sp_sq, 9, q1_cw, None, min_goal_radius_override=0.01).solve_direct(qt_sq_hz)
    lo_hz = r_sq_hz["V_grid"] + r_sq_hz["ring_value_lower_shift"]
    hi_hz = r_sq_hz["V_grid"] + r_sq_hz["ring_value_upper_shift"]
    sq_hz_viols = int(np.sum((fd_sq_hz["V_grid"] < lo_hz - 1e-10) | (fd_sq_hz["V_grid"] > hi_hz + 1e-10)))

    # Case D: GPT6 `d1_core_gamma_noop.py` (`25^2` off-center 12-node L1 ring, nonzero drift, no-op update)
    sp_noop = ProblemSpec(dim=2, half_width=1.0, sigma=0.622986099095231, q0=0.5)
    g_noop = GoalBall((0.1369616873214543, -0.2302132862361297), 0.16510223091108872, 0.21434073337766815)
    q_noop = lambda X: np.zeros(len(X))
    b_noop = lambda X: np.tile([-1.16033367473153, 0.7518485740806538], (len(X), 1))
    qt_noop = QueryTask("noop", (g_noop,), ((-0.8, -0.8),))
    pl_noop = SchurPortPlanner(sp_noop, 25, q_noop, b_noop, [g_noop], initial_sectors_per_wp="L1")
    r_noop0 = pl_noop.solve_query(qt_noop)
    pl_noop.update_world_with_residual_audit(q_noop, b_noop, mode="selective_residual")
    r_noop1 = pl_noop.solve_query(qt_noop)
    fd_noop = ClassicalFDSolver(sp_noop, 25, q_noop, b_noop).solve_direct(qt_noop)
    lo_noop = r_noop1["V_grid"] + r_noop1["ring_value_lower_shift"]
    hi_noop = r_noop1["V_grid"] + r_noop1["ring_value_upper_shift"]
    noop_viols = int(np.sum((fd_noop["V_grid"] < lo_noop - 1e-10) | (fd_noop["V_grid"] > hi_noop + 1e-10)))
    noop_shift_jump = max(
        abs(r_noop1["ring_value_lower_shift"] - r_noop0["ring_value_lower_shift"]),
        abs(r_noop1["ring_value_upper_shift"] - r_noop0["ring_value_upper_shift"]),
    )

    # Case E: GPT6 `d1_core_gamma_probe.py` (`40` random off-center multi-node L1/L4/L8 rings across 25^2/41^2/61^2)
    gamma_probe_viols = 0
    for sd_g in range(40):
        rng_g = np.random.default_rng(sd_g)
        c_g = tuple(rng_g.uniform(-0.5, 0.5, 2).tolist())
        rad_g = float(rng_g.uniform(0.2, 0.55))
        dr_g = rng_g.uniform(-1.2, 1.2, 2)
        ph_g = float(rng_g.uniform(-0.2, 0.2))
        sg_g = float(rng_g.uniform(0.35, 0.8))
        gn_g = (25, 41, 61)[sd_g % 3]
        lv_g = ("L1", "L4", "L8")[sd_g % 3]
        sp_g = ProblemSpec(dim=2, half_width=1.0, sigma=sg_g, q0=0.5)
        go_g = [GoalBall(c_g, ph_g, rad_g)]
        qt_g = QueryTask("gp", tuple(go_g), ((-0.8, -0.8),))
        bf_g = lambda X, d=dr_g: np.tile(d, (len(X), 1))
        pl_g = SchurPortPlanner(sp_g, gn_g, lambda X: np.zeros(len(X)), bf_g, go_g, initial_sectors_per_wp=lv_g)
        pl_g.update_world_with_residual_audit(lambda X: np.full(len(X), 1e-9), bf_g, mode="selective_residual")
        out_g = pl_g.solve_query(qt_g)
        fd_g = ClassicalFDSolver(sp_g, gn_g, lambda X: np.full(len(X), 1e-9), bf_g).solve_direct(qt_g)
        lo_g = out_g["V_grid"] + out_g["ring_value_lower_shift"]
        hi_g = out_g["V_grid"] + out_g["ring_value_upper_shift"]
        gamma_probe_viols += int(np.sum((fd_g["V_grid"] < lo_g - 1e-10) | (fd_g["V_grid"] > hi_g + 1e-10)))

    report["17_single_query_post_update_residual_enclosure"] = {
        "gpt6_dq1e3_violations_of_81": sq_viols,
        "mild_dq1e5_lu_skipped": bool(not pl_sq_m._lu_is_current),
        "mild_dq1e5_scope": r_sq_m["value_bound_scope"],
        "mild_dq1e5_violations_of_81": sq_m_viols,
        "post_update_hazard_query_violations_of_81": sq_hz_viols,
        "d1_noop_25sq_violations_of_625": noop_viols,
        "d1_noop_shift_continuity_diff": float(noop_shift_jump),
        "d1_40seed_multinode_L1_L4_L8_violations": gamma_probe_viols,
        "pass": bool(
            sq_viols == 0
            and (not pl_sq_m._lu_is_current)
            and r_sq_m["value_bound_scope"] == "residual_audited_discrete_operator"
            and sq_m_viols == 0
            and sq_hz_viols == 0
            and upd_sq["waypoints_retained"] == 1
            and noop_viols == 0
            and noop_shift_jump < 1e-9
            and gamma_probe_viols == 0
        ),
    }

    # ------------------------------------------------------------------
    # 18. [NEW `ddd19c5` P1 Bug 3.3 + `d1b926a` Policy Guard] Exact-Baseline Fail-Closed & Cert Guard
    # ------------------------------------------------------------------
    uf_rejected_all = True
    for q_big in (1e8, 1e12, 1e16, 1e20):
        sp_u = ProblemSpec(dim=2, sigma=0.45, q0=0.5)
        w_u = [GoalBall((1.35, 1.35), 0.0, 0.2), GoalBall((0.85, 0.85), 0.0, 0.2)]
        pl_u = SchurPortPlanner(sp_u, 25, lambda X, qb=q_big: qb * np.ones(len(X)), None, w_u, initial_sectors_per_wp="EXACT", lazy_init=True)
        mt_u = MacroTourPlanner(pl_u)
        r_ex_s = mt_u.plan_exact_subset_dp((-1.35, -1.35), [0, 1])
        r_ex_f = mt_u.plan_exact_fixed_tour((-1.35, -1.35), [0, 1])
        if not (
            r_ex_s["status"] == "numeric_invalid" and not r_ex_s["certified"]
            and r_ex_f["status"] == "numeric_invalid" and not r_ex_f["certified"]
        ):
            uf_rejected_all = False

    pl_nan = SchurPortPlanner(ProblemSpec(dim=2), 15, lambda X: np.zeros(len(X)), None, [GoalBall((0.8, 0.8), float("nan"), 0.3)], initial_sectors_per_wp="EXACT", lazy_init=True)
    r_nan_sub = MacroTourPlanner(pl_nan).plan_exact_subset_dp((-0.8, -0.8), [0])
    r_nan_fix = MacroTourPlanner(pl_nan).plan_exact_fixed_tour((-0.8, -0.8), [0])

    # Verify IntervalCertificate rejects forged `extras`, NaN bounds, AND missing policy on `certified=True`
    cert_guard_ok = True
    try:
        from .core import IntervalCertificate as _IC, _eval_reflected_step_goal_union_hit_tau
    except ImportError:
        from green_response.core import IntervalCertificate as _IC, _eval_reflected_step_goal_union_hit_tau
    for bad_kwargs in (
        dict(status="epsilon_certified", certified=True, certificate_scope="t", epsilon_tol=0.1, lower_bound=float("nan"), upper_bound=1.0, extras={"policy": lambda x: x}),
        dict(status="epsilon_certified", certified=True, certificate_scope="t", epsilon_tol=0.1, lower_bound=2.0, upper_bound=1.0, extras={"policy": lambda x: x}),
        dict(status="epsilon_certified", certified=True, certificate_scope="t", epsilon_tol=0.1, lower_bound=1.0, upper_bound=1.05, extras={"status": "heuristic", "policy": lambda x: x}),
        dict(status="epsilon_certified", certified=True, certificate_scope="t", epsilon_tol=0.1, lower_bound=1.0, upper_bound=1.05, extras={"policy_action_idx": None}),
        dict(status="epsilon_certified", certified=True, certificate_scope="t", epsilon_tol=0.1, lower_bound=1.0, upper_bound=1.05, extras={"policy": {}}),
        dict(status="epsilon_certified", certified=True, certificate_scope="t", epsilon_tol=0.1, lower_bound=1.0, upper_bound=1.05, extras={"best_order": ()}),
        dict(status="epsilon_certified", certified=True, certificate_scope="t", epsilon_tol=0.1, lower_bound=1.0, upper_bound=1.05, extras={"policy_action_idx": np.array([], dtype=int)}),
        dict(status="epsilon_certified", certified=True, certificate_scope="t", epsilon_tol=0.1, lower_bound=1.0, upper_bound=1.05),
        dict(status="epsilon_certified", certified=True, certificate_scope="t", epsilon_tol=0.1, lower_bound=1.0, upper_bound=1.05, extras={"other_field": 42}),
    ):
        try:
            _IC(**bad_kwargs)
            cert_guard_ok = False
        except ValueError:
            pass
    v_only_cert = _IC(status="epsilon_certified", certified=True, certificate_scope="t", epsilon_tol=0.1, lower_bound=1.0, upper_bound=1.05, allow_value_only=True).to_dict()
    p_val_cert = _IC(status="epsilon_certified", certified=True, certificate_scope="t", epsilon_tol=0.1, lower_bound=1.0, upper_bound=1.05, extras={"best_order": (0, 1)}).to_dict()
    cert_kind_ok = (v_only_cert["certificate_kind"] == "value_only_enclosure") and (p_val_cert["certificate_kind"] == "policy_and_value_enclosure")

    report["18_exact_baseline_fail_closed_and_cert_guard"] = {
        "underflow_all_rejected_as_numeric_invalid": uf_rejected_all,
        "nan_phi_subset_dp_status": r_nan_sub["status"],
        "nan_phi_fixed_tour_status": r_nan_fix["status"],
        "certificate_constructor_guards_enforced": cert_guard_ok,
        "certificate_kind_role_serialized": cert_kind_ok,
        "pass": bool(
            uf_rejected_all
            and r_nan_sub["status"] == "numeric_invalid" and not r_nan_sub["certified"]
            and r_nan_fix["status"] == "numeric_invalid" and not r_nan_fix["certified"]
            and cert_guard_ok
            and cert_kind_ok
        ),
    }

    # ------------------------------------------------------------------
    # 19. [NEW `d1b926a` P1] Stale-EXACT Route Work Descriptor & Hybrid LU Accounting Probe
    # ------------------------------------------------------------------
    sp_hx = ProblemSpec(dim=2, half_width=1.0, sigma=0.6, q0=0.5)
    gs_hx = [GoalBall((0.3, 0.2), 0.0, 0.25), GoalBall((-0.4, -0.2), 0.0, 0.25)]
    q_hx = lambda X: np.zeros(len(X))
    pl_hx = SchurPortPlanner(sp_hx, 25, q_hx, None, gs_hx, initial_sectors_per_wp="EXACT")
    pl_hx.update_world_with_residual_audit(q_hx, None, mode="selective_residual")
    pred_ex_bs = sum(pl_hx.marginal_backsolves_to_refine(w, "EXACT") for w in range(2))
    est_hx = pl_hx.estimate_current_exact_route_work([0, 1])

    # Hybrid should recognize residual-valid columns + missing LU and route to `incremental_decision_port_dp` with 0 new LUs!
    lu_hx0 = pl_hx.lu_factorizations
    out_hyb_hx = MacroTourPlanner(pl_hx).plan_economical_hybrid((-0.8, 0.8), [0, 1])
    hyb_lu_used = pl_hx.lu_factorizations - lu_hx0
    hyb_charges_router = abs(out_hyb_hx["planning_ms"] - (out_hyb_hx["inner_route_planning_ms"] + out_hyb_hx["router_ms"])) < 1e-9

    # Direct `plan_exact_subset_dp` must match `predicted_missing_exact_backsolves` (`29`) and `requires_new_lu` (`1`)!
    bs_ex0 = pl_hx.total_lu_backsolves
    lu_ex0 = pl_hx.lu_factorizations
    out_ex_hx = MacroTourPlanner(pl_hx).plan_exact_subset_dp((-0.8, 0.8), [0, 1])
    obs_ex_bs = pl_hx.total_lu_backsolves - bs_ex0
    obs_ex_lu = pl_hx.lu_factorizations - lu_ex0

    report["19_stale_exact_work_descriptor_and_hybrid_probe"] = {
        "predicted_missing_current_exact_backsolves": int(pred_ex_bs),
        "observed_exact_route_new_backsolves": int(obs_ex_bs),
        "predicted_requires_new_lu": bool(est_hx["requires_new_lu_factorization"]),
        "observed_exact_route_new_lu": int(obs_ex_lu),
        "hybrid_route_on_warm_residual_valid": out_hyb_hx["hybrid_selected_route"],
        "hybrid_new_lu_factorizations": int(hyb_lu_used),
        "hybrid_planning_ms_includes_router_ms": bool(hyb_charges_router),
        "pass": bool(
            pred_ex_bs > 0
            and pred_ex_bs == obs_ex_bs
            and est_hx["missing_current_exact_backsolves"] == obs_ex_bs
            and est_hx["requires_new_lu_factorization"] is True
            and obs_ex_lu == 1
            and out_hyb_hx["hybrid_selected_route"] == "incremental_decision_port_dp"
            and hyb_lu_used == 0
            and out_hyb_hx["certified"] is True
            and out_ex_hx["certified"] is True
            and hyb_charges_router
        ),
    }

    # ------------------------------------------------------------------
    # 20. [NEW `d1b926a` Work Packages A/B] Green-Adjoint Frechet FD Check, Target-Order Invariance, & Piecewise-Reflected Hit
    # ------------------------------------------------------------------
    sp_gf = ProblemSpec(dim=2, half_width=1.2, sigma=0.5, q0=0.5)
    gs_gf = [
        GoalBall((-0.45, 0.55), 0.1, 0.24),
        GoalBall((0.55, 0.40), -0.2, 0.24),
        GoalBall((0.40, -0.55), 0.0, 0.24),
        GoalBall((-0.50, -0.45), 0.15, 0.24),
    ]
    q_gf_base = np.linspace(0.1, 0.9, 17 * 17)
    b_gf = lambda X: np.column_stack([0.35 * X[:, 1], -0.35 * X[:, 0]])
    pl_gf = SchurPortPlanner(sp_gf, 17, lambda X: q_gf_base, b_gf, gs_gf, initial_sectors_per_wp="EXACT", lazy_init=True)
    mt_gf = MacroTourPlanner(pl_gf)
    sens_a = mt_gf.compute_exact_macro_q_sensitivities((-0.85, 0.05), [3, 1, 0, 2])
    sens_b = mt_gf.compute_exact_macro_q_sensitivities((-0.85, 0.05), [2, 0, 1, 3])
    perm_grad_diff = float(np.max(np.abs(sens_a["grad_q_optimal"] - sens_b["grad_q_optimal"])))
    perm_gap_diff = float(np.max(np.abs(sens_a["grad_q_top_gap"] - sens_b["grad_q_top_gap"])))

    # Finite-difference verification on BOTH `grad_q_optimal`, `grad_q_top_gap`, AND `grad_b_optimal`/`grad_b_top_gap`
    fd_errs = []
    fd_gap_errs = []
    eps_fd = 1e-6

    def _indep_killed_root_q(pl_obj, s_pt, ids_seq):
        ref_k = independent_exact_macro_bellman_reference(pl_obj, s_pt, ids_seq)
        s_nd = int(np.argmin(np.sum((pl_obj.pts - np.asarray(s_pt)) ** 2, axis=1)))
        _, off_k, val_k, P_k, _ = independent_exact_ball_operators(pl_obj, s_nd, ids_seq)
        F_k = ref_k["F_opt_table"]
        full_k = (1 << len(ids_seq)) - 1
        out_q = []
        for ii, bb in enumerate(ids_seq):
            rem_k = full_k ^ (1 << ii)
            cont_k = F_k[0, rem_k] if pl_obj.wp_masks[bb][s_nd] else P_k[bb][0] @ F_k[off_k[bb], rem_k]
            out_q.append(float(val_k[bb][0] + cont_k))
        return np.asarray(out_q, dtype=float)

    qr0 = _indep_killed_root_q(pl_gf, (-0.85, 0.05), [0, 1, 2, 3])
    ord0 = np.argsort(qr0, kind="mergesort")
    ia0, ib0 = int(ord0[0]), int(ord0[1])
    for nid_test in (40, 72, 110, 144, 185, 222):
        dq_vec = np.zeros_like(q_gf_base)
        dq_vec[nid_test] = eps_fd
        pl_p = SchurPortPlanner(sp_gf, 17, lambda X, v=q_gf_base + dq_vec: v, b_gf, gs_gf, initial_sectors_per_wp="EXACT", lazy_init=True)
        pl_m = SchurPortPlanner(sp_gf, 17, lambda X, v=q_gf_base - dq_vec: v, b_gf, gs_gf, initial_sectors_per_wp="EXACT", lazy_init=True)
        qp_v = _indep_killed_root_q(pl_p, (-0.85, 0.05), [0, 1, 2, 3])
        qm_v = _indep_killed_root_q(pl_m, (-0.85, 0.05), [0, 1, 2, 3])
        fd_errs.append(abs(float((np.min(qp_v) - np.min(qm_v)) / (2.0 * eps_fd)) - float(sens_a["grad_q_optimal"][nid_test])))
        fd_gap_errs.append(abs(float(((qp_v[ib0] - qp_v[ia0]) - (qm_v[ib0] - qm_v[ia0])) / (2.0 * eps_fd)) - float(sens_a["grad_q_top_gap"][nid_test])))
    max_frechet_fd_err = float(max(fd_errs))
    max_frechet_gap_fd_err = float(max(fd_gap_errs))

    # Drift sensitivity (`grad_b_optimal` and `grad_b_top_gap`) FD check along smooth interior drift perturbation
    b_base_arr = b_gf(pl_gf.pts)
    db_dir = np.column_stack([np.cos(0.17 * np.arange(len(pl_gf.pts))), np.sin(0.11 * np.arange(len(pl_gf.pts)))])
    # Mask out near-zero upwind kink nodes (`|b| <= 1e-4`) so directional derivative is strictly smooth
    db_dir[np.abs(b_base_arr) <= 1e-4] = 0.0
    pl_bp = SchurPortPlanner(sp_gf, 17, lambda X: q_gf_base, lambda X, v=b_base_arr + eps_fd * db_dir: v, gs_gf, initial_sectors_per_wp="EXACT", lazy_init=True)
    pl_bm = SchurPortPlanner(sp_gf, 17, lambda X: q_gf_base, lambda X, v=b_base_arr - eps_fd * db_dir: v, gs_gf, initial_sectors_per_wp="EXACT", lazy_init=True)
    qbp = _indep_killed_root_q(pl_bp, (-0.85, 0.05), [0, 1, 2, 3])
    qbm = _indep_killed_root_q(pl_bm, (-0.85, 0.05), [0, 1, 2, 3])
    fd_b_opt = float((np.min(qbp) - np.min(qbm)) / (2.0 * eps_fd))
    fd_b_gap = float(((qbp[ib0] - qbp[ia0]) - (qbm[ib0] - qbm[ia0])) / (2.0 * eps_fd))
    ad_b_opt = float(np.sum(sens_a["grad_b_optimal"] * db_dir))
    ad_b_gap = float(np.sum(sens_a["grad_b_top_gap"] * db_dir))
    drift_fd_max_err = float(max(abs(fd_b_opt - ad_b_opt), abs(fd_b_gap - ad_b_gap)))

    # GPT6 `v29_core_frechet_overlap.py` duplicate-eval-node composition regressions (`start_on_ring` & `overlapping_rings`)
    gs_dis3 = [GoalBall((-0.45, 0.55), 0.1, 0.24), GoalBall((0.55, 0.40), -0.2, 0.24), GoalBall((0.40, -0.55), 0.0, 0.24)]
    gs_ovl3 = [GoalBall((-0.15, 0.45), 0.1, 0.35), GoalBall((0.15, 0.45), -0.2, 0.35), GoalBall((0.40, -0.55), 0.0, 0.24)]
    dup_errs = []
    for gs_case, ring_start in ((gs_dis3, True), (gs_ovl3, False)):
        pl_c = SchurPortPlanner(sp_gf, 17, lambda X: q_gf_base, b_gf, gs_case, initial_sectors_per_wp="EXACT", lazy_init=True)
        st_c = pl_c.pts[pl_c.wp_rings[0][2]].copy() if ring_start else np.array([-0.85, 0.05])
        sens_c = MacroTourPlanner(pl_c).compute_exact_macro_q_sensitivities(st_c, [0, 1, 2])
        qrc = _indep_killed_root_q(pl_c, st_c, [0, 1, 2])
        oc = np.argsort(qrc, kind="mergesort")
        ca, cb = int(oc[0]), int(oc[1])
        for dir_c in (np.ones(17 * 17), np.sin(np.arange(17 * 17) * 0.13)):
            pl_cp = SchurPortPlanner(sp_gf, 17, lambda X, v=q_gf_base + eps_fd * dir_c: v, b_gf, gs_case, initial_sectors_per_wp="EXACT", lazy_init=True)
            pl_cm = SchurPortPlanner(sp_gf, 17, lambda X, v=q_gf_base - eps_fd * dir_c: v, b_gf, gs_case, initial_sectors_per_wp="EXACT", lazy_init=True)
            qcp = _indep_killed_root_q(pl_cp, st_c, [0, 1, 2])
            qcm = _indep_killed_root_q(pl_cm, st_c, [0, 1, 2])
            dup_errs.append(abs(float((np.min(qcp) - np.min(qcm)) / (2.0 * eps_fd)) - float(sens_c["grad_q_optimal"] @ dir_c)))
            dup_errs.append(abs(float(((qcp[cb] - qcp[ca]) - (qcm[cb] - qcm[ca])) / (2.0 * eps_fd)) - float(sens_c["grad_q_top_gap"] @ dir_c)))
    max_duplicate_node_fd_err = float(max(dup_errs))

    # Symmetric Bellman tie / active-branch metadata check (`v29_core_contract_checks.py`)
    pl_tie = SchurPortPlanner(sp_gf, 17, lambda X: np.full(len(X), 0.3), None, [GoalBall((-0.6, 0.0), 0.0, 0.24), GoalBall((0.6, 0.0), 0.0, 0.24)], initial_sectors_per_wp="EXACT", lazy_init=True)
    sens_tie = MacroTourPlanner(pl_tie).compute_exact_macro_q_sensitivities((0.0, 0.75), [0, 1])

    # GPT6 `reflection_segment_probe` (`false_chord_hit` & `missed_pre_reflection_hit`)
    st_ref = np.array([[0.9, 0.0]])
    raw_ref = np.array([[1.5, 0.4]])
    h_false, _, _, _, _ = _eval_reflected_step_goal_union_hit_tau(st_ref, raw_ref, 1.0, (GoalBall((0.8, 0.1), 0.0, 0.02),))
    h_pre, _, tau_pre, _, _ = _eval_reflected_step_goal_union_hit_tau(st_ref, raw_ref, 1.0, (GoalBall((0.96, 0.04), 0.0, 0.01),))

    report["20_green_frechet_invariance_and_piecewise_reflected_hit"] = {
        "target_permutation_grad_max_diff": perm_grad_diff,
        "target_permutation_gap_grad_max_diff": perm_gap_diff,
        "max_frechet_vs_central_fd_abs_err": max_frechet_fd_err,
        "max_gap_frechet_vs_central_fd_abs_err": max_frechet_gap_fd_err,
        "max_drift_b_frechet_vs_central_fd_abs_err": drift_fd_max_err,
        "max_duplicate_eval_node_fd_abs_err": max_duplicate_node_fd_err,
        "tie_derivative_kind": sens_tie["derivative_kind"],
        "symmetric_tie_detected": bool(sens_tie["tie_detected"]),
        "false_chord_hit_eliminated": bool(not h_false[0]),
        "pre_reflection_hit_detected": bool(h_pre[0]),
        "pre_reflection_hit_tau": float(tau_pre[0]),
        "pass": bool(
            perm_grad_diff == 0.0
            and perm_gap_diff == 0.0
            and max_frechet_fd_err < 1e-8
            and max_frechet_gap_fd_err < 1e-8
            and drift_fd_max_err < 1e-8
            and max_duplicate_node_fd_err < 1e-8
            and sens_tie["derivative_kind"] == "active_branch"
            and bool(sens_tie["tie_detected"]) is True
            and (not h_false[0])
            and bool(h_pre[0])
            and abs(float(tau_pre[0]) - (0.06 - 0.01) / np.hypot(0.6, 0.4)) < 0.03
        ),
    }

    # ------------------------------------------------------------------
    # 21. [NEW `29fa7c6` Closure] Sequential Rank-1 Schur Conditional Covariance Exactness & Eval-vs-Operational Isolation
    # ------------------------------------------------------------------
    w_cc = generate_benchmark_map(10300, dim=2, regime="competing_corridor", with_drift=True)
    X_cc, q_cc, b_cc = sample_noisy_probes(w_cc, n_probes=24, seed=10307, include_drift=True)
    km_cc = KrigingWorldModel(X_cc, q_cc, b_cc)
    gx_cc = np.linspace(-1.3, 1.3, 13)
    gxx_c, gyy_c = np.meshgrid(gx_cc, gx_cc, indexing="ij")
    cand_cc = np.column_stack([gxx_c.ravel(), gyy_c.ravel()])
    grid_cc = build_grid_points(2, w_cc.spec.half_width, 15)[1]
    w_func = np.column_stack([np.sin(0.2 * np.arange(len(grid_cc))), np.cos(0.15 * np.arange(len(grid_cc)))])
    C0_q, G0_q, nz0_q = km_cc._build_channel_posterior_cov_and_proj(km_cc._q_fast, cand_cc, grid_cc, w_func)
    sel_idx = 42
    dq0 = C0_q[sel_idx, sel_idx] + nz0_q
    C1_downdate = C0_q - np.outer(C0_q[:, sel_idx], C0_q[:, sel_idx]) / dq0
    G1_downdate = G0_q - np.outer(C0_q[:, sel_idx], G0_q[sel_idx, :]) / dq0

    # Exact fixed-hyperparameter block Cholesky reference with `cand_cc[sel_idx]` appended to `X_obs`
    # (including sklearn's default `alpha=1e-10` diagonal jitter on the original `X_obs` block!)
    st_q = km_cc._q_fast
    n0_obs = len(km_cc.X_obs)
    X_aug = np.vstack([km_cc.X_obs, cand_cc[sel_idx : sel_idx + 1]])
    K_aa = km_cc._eval_matern25_kernel_pair(X_aug, X_aug, st_q) + (nz0_q / (st_q["y_std"] ** 2)) * np.eye(len(X_aug))
    K_aa[:n0_obs, :n0_obs] += 1e-10 * np.eye(n0_obs)
    L_aug = np.linalg.cholesky(K_aa)
    from scipy.linalg import solve_triangular as _st_tri
    K_ca = km_cc._eval_matern25_kernel_pair(cand_cc, X_aug, st_q)
    K_ga = km_cc._eval_matern25_kernel_pair(grid_cc, X_aug, st_q)
    K_cc_raw = km_cc._eval_matern25_kernel_pair(cand_cc, cand_cc, st_q)
    K_cg_raw = km_cc._eval_matern25_kernel_pair(cand_cc, grid_cc, st_q)
    V_ca = _st_tri(L_aug, K_ca.T, lower=True, check_finite=False)
    V_ga = _st_tri(L_aug, K_ga.T, lower=True, check_finite=False)
    C1_exact = (st_q["y_std"] ** 2) * (K_cc_raw - (V_ca.T @ V_ca))
    G1_exact = (st_q["y_std"] ** 2) * ((K_cg_raw @ w_func) - (V_ca.T @ (V_ga @ w_func)))
    schur_cov_err = float(np.max(np.abs(C1_downdate - C1_exact)))
    schur_proj_err = float(np.max(np.abs(G1_downdate - G1_exact)))

    # Eval-vs-Operational isolation check: held-out evaluation on `pl_eval` must leave `pl_operational` state/counters untouched
    wps_iso = [GoalBall((-0.6, 0.5), 0.0, 0.26), GoalBall((0.6, 0.5), 0.0, 0.26), GoalBall((0.5, -0.6), 0.0, 0.26), GoalBall((-0.5, -0.6), 0.0, 0.26)]
    def _run_one_isolated_step(run_heldout_eval: bool):
        km_i = KrigingWorldModel(X_cc, q_cc, b_cc)
        pl_op = SchurPortPlanner(w_cc.spec, 21, km_i.predict_q, km_i.predict_b, wps_iso, initial_sectors_per_wp="EXACT", lazy_init=True)
        mt_op = MacroTourPlanner(pl_op)
        if run_heldout_eval:
            pl_ev = SchurPortPlanner(w_cc.spec, 21, km_i.predict_q, km_i.predict_b, wps_iso, initial_sectors_per_wp="EXACT", lazy_init=True)
            MacroTourPlanner(pl_ev).plan_exact_subset_dp((0.0, 0.9), (0, 1, 2, 3))
        mt_op.plan_exact_subset_dp((-0.9, 0.0), (0, 1, 2))
        sens_op = mt_op.compute_exact_macro_q_sensitivities((-0.9, 0.0), (0, 1, 2))
        X_sel, _ = km_i.select_sequential_kg_voi_probes(cand_cc, pl_op.pts, [sens_op], X_cc, n_decision=6, n_sentinel=2, min_repel=0.22)
        return X_sel, pl_op.lu_factorizations, pl_op.total_lu_backsolves

    X_with_ev, lu_w, bs_w = _run_one_isolated_step(True)
    X_no_ev, lu_n, bs_n = _run_one_isolated_step(False)
    eval_iso_probe_diff = float(np.max(np.abs(X_with_ev - X_no_ev)))

    report["21_conditional_cov_downdate_and_eval_isolation_audit"] = {
        "schur_rank1_cov_max_abs_err": schur_cov_err,
        "schur_rank1_proj_max_abs_err": schur_proj_err,
        "eval_deleted_probe_max_diff": eval_iso_probe_diff,
        "eval_deleted_lu_identical": bool(lu_w == lu_n),
        "eval_deleted_backsolves_identical": bool(bs_w == bs_n),
        "pass": bool(
            schur_cov_err < 1e-12
            and schur_proj_err < 1e-12
            and eval_iso_probe_diff == 0.0
            and lu_w == lu_n
            and bs_w == bs_n
        ),
    }

    # ------------------------------------------------------------------
    # 22. [NEW `57e5912` v5 Audit Closure] Zero-Drift Upwind Kink, True `max_alt_branches=0`,
    #     Off-Grid Pending Sentinel Conditioning, & Mandatory `cols_retained` Contract
    # ------------------------------------------------------------------
    # (A) Single-goal exact zero-drift counterexample (`v57_core_grad_probes.py`): no Bellman tie, upwind kink active
    gs_zd = [GoalBall((0.55, 0.40), 0.0, 0.24)]
    bv_zero = np.zeros((17 * 17, 2), dtype=float)
    pl_zd = SchurPortPlanner(sp_gf, 17, lambda X: q_gf_base, lambda X: bv_zero, gs_zd, initial_sectors_per_wp="EXACT", lazy_init=True)
    sens_zd = MacroTourPlanner(pl_zd).compute_exact_macro_q_sensitivities((-0.85, 0.05), [0], max_alt_branches=0)
    v0_zd = float(_indep_killed_root_q(pl_zd, (-0.85, 0.05), [0])[0])
    eps_zd = 1e-5
    zd_right_raw_errs = []
    zd_right_rich_errs = []
    zd_left_rich_errs = []
    zd_mid_rich_errs = []
    for ax_z in range(2):
        db_z = np.zeros_like(bv_zero)
        db_z[:, ax_z] = 1.0
        pl_zp1 = SchurPortPlanner(sp_gf, 17, lambda X: q_gf_base, lambda X, v=eps_zd * db_z: v, gs_zd, initial_sectors_per_wp="EXACT", lazy_init=True)
        pl_zp2 = SchurPortPlanner(sp_gf, 17, lambda X: q_gf_base, lambda X, v=0.5 * eps_zd * db_z: v, gs_zd, initial_sectors_per_wp="EXACT", lazy_init=True)
        pl_zm1 = SchurPortPlanner(sp_gf, 17, lambda X: q_gf_base, lambda X, v=-eps_zd * db_z: v, gs_zd, initial_sectors_per_wp="EXACT", lazy_init=True)
        pl_zm2 = SchurPortPlanner(sp_gf, 17, lambda X: q_gf_base, lambda X, v=-0.5 * eps_zd * db_z: v, gs_zd, initial_sectors_per_wp="EXACT", lazy_init=True)
        d_r1 = (float(_indep_killed_root_q(pl_zp1, (-0.85, 0.05), [0])[0]) - v0_zd) / eps_zd
        d_r2 = (float(_indep_killed_root_q(pl_zp2, (-0.85, 0.05), [0])[0]) - v0_zd) / (0.5 * eps_zd)
        d_l1 = (v0_zd - float(_indep_killed_root_q(pl_zm1, (-0.85, 0.05), [0])[0])) / eps_zd
        d_l2 = (v0_zd - float(_indep_killed_root_q(pl_zm2, (-0.85, 0.05), [0])[0])) / (0.5 * eps_zd)
        rich_r = 2.0 * d_r2 - d_r1
        rich_l = 2.0 * d_l2 - d_l1
        rich_m = 0.5 * (rich_r + rich_l)
        zd_right_raw_errs.append(abs(d_r2 - float(np.sum(sens_zd["grad_b_plus_optimal"] * db_z))))
        zd_right_rich_errs.append(abs(rich_r - float(np.sum(sens_zd["grad_b_plus_optimal"] * db_z))))
        zd_left_rich_errs.append(abs(rich_l - float(np.sum(sens_zd["grad_b_minus_optimal"] * db_z))))
        zd_mid_rich_errs.append(abs(rich_m - float(np.sum(sens_zd["grad_b_optimal"] * db_z))))
    # Also test mixed-sign directional derivative at `b == 0` via half-ray Richardson extrapolation
    db_mix = np.column_stack([np.sin(0.23 * np.arange(17 * 17)), np.cos(0.19 * np.arange(17 * 17))])
    pl_zmix1 = SchurPortPlanner(sp_gf, 17, lambda X: q_gf_base, lambda X, v=eps_zd * db_mix: v, gs_zd, initial_sectors_per_wp="EXACT", lazy_init=True)
    pl_zmix2 = SchurPortPlanner(sp_gf, 17, lambda X: q_gf_base, lambda X, v=0.5 * eps_zd * db_mix: v, gs_zd, initial_sectors_per_wp="EXACT", lazy_init=True)
    dm1 = (float(_indep_killed_root_q(pl_zmix1, (-0.85, 0.05), [0])[0]) - v0_zd) / eps_zd
    dm2 = (float(_indep_killed_root_q(pl_zmix2, (-0.85, 0.05), [0])[0]) - v0_zd) / (0.5 * eps_zd)
    fd_mix_rich = 2.0 * dm2 - dm1
    ad_mix = float(np.sum(np.where(db_mix >= 0.0, sens_zd["grad_b_plus_optimal"], sens_zd["grad_b_minus_optimal"]) * db_mix))
    zd_mix_err = abs(fd_mix_rich - ad_mix)
    strict_smooth_rejected = False
    try:
        MacroTourPlanner(pl_zd).compute_exact_macro_q_sensitivities((-0.85, 0.05), [0], zero_drift_mode="strict_smooth")
    except ValueError:
        strict_smooth_rejected = True

    # (B) True `max_alt_branches = 0` eliminates redundant transpose RHS columns while keeping ValueOnly selection identical
    sens_alt0 = MacroTourPlanner(pl_gf).compute_exact_macro_q_sensitivities((-0.85, 0.05), [0, 1, 2, 3], max_alt_branches=0)
    sens_alt1 = MacroTourPlanner(pl_gf).compute_exact_macro_q_sensitivities((-0.85, 0.05), [0, 1, 2, 3], max_alt_branches=1)
    alt0_grad_diff = float(
        max(
            np.max(np.abs(sens_alt0["grad_q_optimal"] - sens_alt1["grad_q_optimal"])),
            np.max(np.abs(sens_alt0["grad_b_optimal"] - sens_alt1["grad_b_optimal"])),
            abs(sens_alt0["action_gap"] - sens_alt1["action_gap"]),
        )
    )
    alt0_rhs_reduced = bool(sens_alt0["n_transpose_rhs_cols"] < sens_alt1["n_transpose_rhs_cols"])

    # (C) Off-grid `pending_X` sentinel conditioning vs exact augmented Cholesky + GPT6 3-candidate SPD counterexample
    from types import SimpleNamespace
    C_spd = np.array([[1.0, 0.99, 0.10], [0.99, 1.0, 0.10], [0.10, 0.10, 0.80]], dtype=float)
    cand_spd = np.array([[0.0, 0.0], [0.1, 0.0], [1.0, 0.0]], dtype=float)
    stub_spd = SimpleNamespace(dim=2, _q_fast={}, _b_fast=None, _build_channel_posterior_cov_and_proj=lambda *a: (C_spd.copy(), None, 0.01))
    sel_spd = KrigingWorldModel.select_sequential_conditional_maxvar_probes(
        stub_spd, cand_spd, np.array([[-2.0, -2.0]]), 1, min_repel=1e-6, pending_X=cand_spd[[0]]
    )
    spd_selected_idx = int(np.argmin(np.sum((cand_spd - sel_spd[0]) ** 2, axis=1)))

    # Off-grid pending_X block-Cholesky exactness on real `km_cc` across BOTH `q` and `b` channels
    X_pend_offgrid = np.array([[-0.37, 0.29], [0.44, -0.51], [0.12, 0.63]], dtype=float)
    Cp_q, Gp_q, nzp_q = km_cc._build_channel_posterior_cov_and_proj(km_cc._q_fast, cand_cc, grid_cc, w_func, pending_X=X_pend_offgrid)
    X_aug_p = np.vstack([km_cc.X_obs, X_pend_offgrid])
    K_aap = km_cc._eval_matern25_kernel_pair(X_aug_p, X_aug_p, st_q) + (nzp_q / (st_q["y_std"] ** 2)) * np.eye(len(X_aug_p))
    K_aap[:n0_obs, :n0_obs] += 1e-10 * np.eye(n0_obs)
    L_aug_p = np.linalg.cholesky(K_aap)
    V_cap = _st_tri(L_aug_p, km_cc._eval_matern25_kernel_pair(cand_cc, X_aug_p, st_q).T, lower=True, check_finite=False)
    V_gap = _st_tri(L_aug_p, km_cc._eval_matern25_kernel_pair(grid_cc, X_aug_p, st_q).T, lower=True, check_finite=False)
    Cp_exact = (st_q["y_std"] ** 2) * (K_cc_raw - (V_cap.T @ V_cap))
    Gp_exact = (st_q["y_std"] ** 2) * ((K_cg_raw @ w_func) - (V_cap.T @ (V_gap @ w_func)))
    pend_offgrid_cov_err = float(np.max(np.abs(Cp_q - Cp_exact)))
    pend_offgrid_proj_err = float(np.max(np.abs(Gp_q - Gp_exact)))

    # (D) Positive control on `cols_retained`: no-op / micro update MUST retain >0 native columns
    pl_pos = SchurPortPlanner(sp_gf, 17, lambda X: np.full(len(X), 0.4), None, [GoalBall((0.4, 0.2), 0.0, 0.28)], initial_sectors_per_wp="L1", lazy_init=False)
    upd_pos = pl_pos.update_world_with_residual_audit(lambda X: np.full(len(X), 0.4), None, mode="selective_residual")
    pos_cols_retained = int(upd_pos["cols_retained"])

    report["22_zero_drift_kink_pending_sentinel_and_retained_cols_audit"] = {
        "zero_drift_action_tie_detected": bool(sens_zd["action_tie_detected"]),
        "zero_drift_upwind_kink_detected": bool(sens_zd["upwind_drift_kink_detected"]),
        "zero_drift_kink_components": int(sens_zd["n_zero_drift_kink_components"]),
        "zero_drift_right_onesided_raw_fd_err_5e6": float(max(zd_right_raw_errs)),
        "zero_drift_right_richardson_fd_max_err": float(max(zd_right_rich_errs)),
        "zero_drift_left_richardson_fd_max_err": float(max(zd_left_rich_errs)),
        "zero_drift_clarke_midpoint_richardson_fd_max_err": float(max(zd_mid_rich_errs)),
        "zero_drift_mixed_dir_richardson_fd_err": float(zd_mix_err),
        "strict_smooth_mode_rejects_kink": bool(strict_smooth_rejected),
        "alt0_grad_and_gap_max_diff": alt0_grad_diff,
        "alt0_rhs_cols": int(sens_alt0["n_transpose_rhs_cols"]),
        "alt1_rhs_cols": int(sens_alt1["n_transpose_rhs_cols"]),
        "alt0_rhs_reduced": alt0_rhs_reduced,
        "spd_pending_counterexample_selected_idx": spd_selected_idx,
        "offgrid_pending_cov_max_abs_err": pend_offgrid_cov_err,
        "offgrid_pending_proj_max_abs_err": pend_offgrid_proj_err,
        "positive_control_cols_retained": pos_cols_retained,
        "pass": bool(
            (not sens_zd["action_tie_detected"])
            and bool(sens_zd["upwind_drift_kink_detected"])
            and int(sens_zd["n_zero_drift_kink_components"]) > 0
            and max(zd_right_rich_errs) < 1e-9
            and max(zd_left_rich_errs) < 1e-9
            and max(zd_mid_rich_errs) < 1e-9
            and zd_mix_err < 1e-9
            and strict_smooth_rejected
            and alt0_grad_diff == 0.0
            and alt0_rhs_reduced
            and spd_selected_idx == 2
            and pend_offgrid_cov_max_err < 1e-12 if (pend_offgrid_cov_max_err := pend_offgrid_cov_err) is not None else False
            and pend_offgrid_proj_err < 1e-12
            and pos_cols_retained >= 1
        ),
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
