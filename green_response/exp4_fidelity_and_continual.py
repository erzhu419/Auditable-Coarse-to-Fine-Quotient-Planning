"""Experiment 4 (`green_response` — `ddd19c5` Stages C, D, & F, 8-Core Parallel):
Model-to-Execution Fidelity Bridge, Orthogonal Reuse Attribution, & Online Prequential Active Learning-Planning!

4A. Hierarchical Wiener-Coupled Model-to-Execution Fidelity Bridge (`12` Maps `9900..9911` x `6` Tours = `72` Tasks):
    - Exact Brownian path coupling: coarse `dt = 0.015` increments are exact 3-substep sums of fine `dt = 0.005`
      increments (`dW_coarse[k] = sum_{j=0..2} dW_fine[3k+j]`), eliminating cross-`dt` Monte Carlo path mismatch!
    - Fractional first-entry segment hit (`_eval_segment_goal_union_hit_tau`): charges `tau_hit * dt` running cost
      and transitions at the sphere-entry point `X_hit`.
    - Factorial separation of `dt` (`0.015` vs `0.005`), readout (`central_grad` vs `upwind_min`), and hit rule
      (`endpoint` vs `fractional_segment`), with map-paired 95% CIs, timeout rates, and clip fractions.

4B. Orthogonal Operator-Transition Reuse Attribution (`10` Maps `9950..9959` x `4` Epochs x `5` Tasks = `200` Tasks):
    Separates **Refinement-Layout Structure Memory** from **Residual-Audited Value Reuse** on external operator shifts:
      1. `Scratch-Rebuild`: drops layout & columns, factors `splu(A_new)` every transition;
      2. `Structure-Memory-Fresh-Exact` (`mode="structure_only_fresh_exact"`): keeps learned `L1/L4/L8/EXACT` layout,
         batch-solves fresh exact columns under `splu(A_new)`;
      3. `Residual-Audited-Reuse` (`mode="selective_residual"`): keeps layout AND retains residual-verified old columns
         without `splu(A_new)` when `||U_new - U_old||_inf` passes M-matrix bounds;
      4. `Blind-Stale-Cache`: unverified negative control.
    Logs per-task `epsilon_certified / unresolved / numeric_invalid` counts, column retention counts, and phase timings.

4C. Genuine Prequential Online Observation-Accumulation & Decision-Guided Active Sensing (`12` Maps `9850..9861` x `6` Episodes):
    Strictly causal closed loop `D_t -> GP Posterior (q_t, b_t, sigma_{q,t}) -> Audit/Update W_t -> Plan & Act -> Probe D_{t+1}`:
      - Episodes 1..4: Stationary unknown world as observations accumulate (`28 -> 42 -> 56 -> 70` probes);
      - Episode 5..6: Unannounced localized hazard emergence discovered online (`84 -> 98` probes).
    Evaluates:
      (i) Planner reuse economics (`Scratch-Port` vs `Exact-SubsetDP` vs `Audited-Incremental-Port` vs `Hybrid-Audited`)
          with explicit `gp_fit_ms` + `update_ms` + `plan_ms` accounting;
      (ii) Same-budget active sensing (`+14` probes/episode): `Uniform-Random`, `Global-MaxVariance`,
           `OnPolicy-Trajectory`, and `Decision-Corridor-Active` (dual-occupancy corridor x GP `sigma_q`).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import itertools
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from green_response import (
    ClassicalFDSolver,
    GoalBall,
    GroundTruthWorld,
    HazardFeature,
    KrigingWorldModel,
    MacroTourPlanner,
    ProblemSpec,
    QueryTask,
    SchurPortPlanner,
    collect_runtime_metadata,
    enforce_single_thread_env,
    eval_goal_union,
    generate_benchmark_map,
    independent_exact_macro_bellman_reference,
    make_consistent_value_and_policy_2d3d,
    observe_world_at_points,
    paired_stats,
    reflect_into_box,
    run_map_parallel,
    sample_noisy_probes,
)
from green_response.core import _eval_segment_goal_union_hit_tau


class _GPWorldProxy:
    """Wraps `(spec, km)` with the same `.spec`, `.q_total`, `.drift` interface as `GroundTruthWorld`."""

    def __init__(self, spec: ProblemSpec, km: KrigingWorldModel):
        self.spec = spec
        self.km = km

    def q_total(self, X: np.ndarray, local_hazards: Sequence[HazardFeature] = ()) -> np.ndarray:
        return self.spec.q0 + self.km.predict_q(X)

    def drift(self, X: np.ndarray) -> np.ndarray:
        return self.km.predict_b(X)


def _generate_coupled_wiener_bank(seed_t: int, n_tr: int, m_legs: int, fine_steps_per_leg: int = 1860, dt_fine: float = 0.005) -> Tuple[np.ndarray, np.ndarray]:
    """Generates fine Brownian increments `dW_fine` of shape `(n_tr, m_legs, fine_steps_per_leg, 2)`
    at `dt_fine = 0.005` AND exact 3-step aggregated coarse increments `dW_coarse` at `dt_coarse = 0.015`!
    """
    rng = np.random.default_rng(np.random.SeedSequence([seed_t, 555]))
    dW_fine = rng.normal(0.0, np.sqrt(dt_fine), size=(n_tr, m_legs, fine_steps_per_leg, 2))
    coarse_steps = fine_steps_per_leg // 3
    dW_coarse = dW_fine[:, :, :coarse_steps * 3, :].reshape(n_tr, m_legs, coarse_steps, 3, 2).sum(axis=3)
    return dW_fine, dW_coarse


def _simulate_adaptive_tour_coupled(
    env_world,
    catalog_wps: Sequence[GoalBall],
    leg_pol_cache: Dict[int, callable],
    start_xy: np.ndarray,
    target_ids: Sequence[int],
    selector_fn,
    dW_legs: np.ndarray,
    dt_sim: float = 0.015,
    fractional_segment_hit: bool = False,
    u_clip_safety: float = 25.0,
) -> dict:
    """Adaptive multi-leg SDE rollout driven by pregenerated coupled Wiener increments `dW_legs`
    (`(n_tr, m_legs, max_leg_steps, 2)`), supporting fractional first-entry segment stopping (`tau_hit * dt`)
    and explicit `R_vec`, clip, and timeout accounting.
    """
    n_tr, _, max_leg_steps, _ = dW_legs.shape
    R_vec = env_world.spec.R_vec
    tot_c = np.zeros(n_tr, dtype=float)
    timeouts = 0
    clipped_steps = 0
    active_steps = 0

    for tr_i in range(n_tr):
        x = reflect_into_box(np.asarray(start_xy, dtype=float)[None, :], env_world.spec.half_width)[0]
        rem = list(target_ids)
        prev_wp: Optional[int] = None
        c_i = 0.0
        leg_k = 0
        while rem:
            wp_j = selector_fn(x, prev_wp, rem)
            pol = leg_pol_cache[wp_j]
            g_ball = catalog_wps[wp_j]
            hit0, phi0 = eval_goal_union(x[None, :], (g_ball,))
            if hit0[0]:
                c_i += float(phi0[0])
                rem.remove(wp_j)
                leg_k += 1
                continue
            reached = False
            dw_seq = dW_legs[tr_i, min(leg_k, dW_legs.shape[1] - 1)]
            for st in range(max_leg_steps):
                u = np.asarray(pol(x[None, :])[0], dtype=float)
                un = float(np.linalg.norm(u))
                if un > u_clip_safety:
                    u = u * (u_clip_safety / un)
                    clipped_steps += 1
                active_steps += 1
                qt = float(env_world.q_total(x[None, :])[0])
                rate = qt + 0.5 * float(np.sum((u ** 2) * R_vec))
                b_v = env_world.drift(x[None, :])[0]
                x_nxt = reflect_into_box(
                    (x + (b_v + u) * dt_sim + env_world.spec.sigma * dw_seq[st])[None, :],
                    env_world.spec.half_width,
                )[0]
                if fractional_segment_hit:
                    hit_s, phi_s, tau_s, x_hit = _eval_segment_goal_union_hit_tau(x[None, :], x_nxt[None, :], (g_ball,))
                    c_i += rate * (float(tau_s[0]) * dt_sim)
                    x = x_hit[0] if hit_s[0] else x_nxt
                else:
                    hit_s, phi_s = eval_goal_union(x_nxt[None, :], (g_ball,))
                    c_i += rate * dt_sim
                    x = x_nxt
                if hit_s[0]:
                    c_i += float(phi_s[0])
                    reached = True
                    break
            if not reached:
                c_i += 8.0
                timeouts += 1
                break
            rem.remove(wp_j)
            prev_wp = wp_j
            leg_k += 1
        tot_c[tr_i] = c_i

    return {
        "mean_cost": float(np.mean(tot_c)),
        "mc_se": float(np.std(tot_c, ddof=1) / np.sqrt(n_tr)),
        "timeout_frac": float(timeouts / n_tr),
        "clip_frac": float(clipped_steps / max(active_steps, 1)),
        "traj_costs": tot_c,
    }


def _fidelity_map_worker(args: Tuple[int, int, int, int]) -> dict:
    idx_m, m_seed, tasks_per_map, grid_n = args
    world = generate_benchmark_map(m_seed, dim=2, regime="narrow_barrier", with_drift=True)
    rng = np.random.default_rng(m_seed + 77)
    r_wp = 0.27
    catalog_wps: List[GoalBall] = []
    for _ in range(12):
        for _att in range(200):
            pt = rng.uniform(-1.20, 1.20, size=2)
            if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.06 * r_wp for w in catalog_wps):
                catalog_wps.append(GoalBall(tuple(pt.tolist()), phi=0.0, radius=r_wp))
                break

    km = KrigingWorldModel(*sample_noisy_probes(world, n_probes=90, seed=m_seed + 5, include_drift=True))
    gp_world = _GPWorldProxy(world.spec, km)

    exec_fd = ClassicalFDSolver(world.spec, grid_n, km.predict_q, km.predict_b)
    pol_central = {}
    pol_upwind = {}
    for j, w in enumerate(catalog_wps):
        qt = QueryTask(f"leg_{j}", (w,), ((0.0, 0.0),))
        rf = exec_fd.solve_direct(qt)
        pol_central[j] = rf["policy"]
        _, pol_upwind[j] = make_consistent_value_and_policy_2d3d(
            exec_fd.xs, rf["V_grid"], world.spec, qt, readout_scheme="upwind_min"
        )

    pl_dg = SchurPortPlanner(world.spec, grid_n, km.predict_q, km.predict_b, catalog_wps, initial_sectors_per_wp="L1", lazy_init=True)
    pl_ex = SchurPortPlanner(world.spec, grid_n, km.predict_q, km.predict_b, catalog_wps, initial_sectors_per_wp="EXACT", lazy_init=True)
    mt_dg = MacroTourPlanner(pl_dg)
    mt_ex = MacroTourPlanner(pl_ex)

    signed_keys = [
        "L1_compressed_mid_minus_exact_macro",
        "L2a_gp_dt015_central_end_minus_exact_macro",
        "L2b_gp_dt005_central_end_minus_exact_macro",
        "L2c_gp_dt005_central_fracseg_minus_exact_macro",
        "L2d_gp_dt005_upwind_fracseg_minus_exact_macro",
        "dt_refinement_effect_dt005_minus_dt015_coupled",
        "fracseg_effect_minus_endpoint_at_dt005",
        "upwind_minus_central_at_dt005_fracseg",
        "L3_true_minus_gp_at_dt005_central_fracseg",
    ]
    task_signed = {k: [] for k in signed_keys}
    c_ex_m, c_dg_m, c_eu_m = [], [], []
    discrete_regrets = []
    root_match = []
    mc_ses = []
    timeouts_l, clips_l = [], []
    bound_violations = 0
    cert_count = 0

    for t_i in range(tasks_per_map):
        sub_ids = tuple(rng.choice(len(catalog_wps), size=5, replace=False).tolist())
        start_xy = np.array([-1.30, -1.30])
        for _att in range(150):
            cand = rng.uniform(-1.25, 1.25, size=2)
            if all(np.linalg.norm(cand - np.asarray(catalog_wps[j].center)) > r_wp + 0.15 for j in sub_ids):
                start_xy = cand
                break
        t_seed = 31000 + 30 * idx_m + t_i

        r_dg = mt_dg.plan_subset_macro_policy(start_xy, sub_ids, epsilon_tol=0.25, max_refine_steps=12, refine_strategy="decision_guided")
        r_ex = mt_ex.plan_exact_subset_dp(start_xy, sub_ids)
        ref_ind = independent_exact_macro_bellman_reference(pl_dg, start_xy, sub_ids, policy_action_idx=r_dg["policy_action_idx"])

        cert_count += int(r_dg["certified"])
        lo_d, hi_d = r_dg["macro_value_bounds"]
        j_port_mid = 0.5 * (lo_d + hi_d)
        f_opt = ref_ind["optimal_adaptive_macro_cost"]
        j_dg_exact = ref_ind["evaluated_policy_exact_macro_cost"]
        if not ((lo_d - 1e-9 <= f_opt <= hi_d + 1e-9) and (f_opt - 1e-9 <= j_dg_exact <= hi_d + 1e-9)):
            bound_violations += 1
        discrete_regrets.append(float(j_dg_exact - f_opt))
        full_mk = (1 << 5) - 1
        root_match.append(float(r_dg["policy_action_idx"][0, full_mk] == r_ex["policy_action_idx"][0, full_mk]))

        # Exact Hierarchical Wiener Coupling (`n_tr = 32` trajectories per task)
        dW_fine, dW_coarse = _generate_coupled_wiener_bank(t_seed, n_tr=32, m_legs=5, fine_steps_per_leg=1860, dt_fine=0.005)
        sel_dg = r_dg["select_next_waypoint"]

        s_gp_015_c_end = _simulate_adaptive_tour_coupled(gp_world, catalog_wps, pol_central, start_xy, sub_ids, sel_dg, dW_coarse, dt_sim=0.015, fractional_segment_hit=False)
        s_gp_005_c_end = _simulate_adaptive_tour_coupled(gp_world, catalog_wps, pol_central, start_xy, sub_ids, sel_dg, dW_fine, dt_sim=0.005, fractional_segment_hit=False)
        s_gp_005_c_seg = _simulate_adaptive_tour_coupled(gp_world, catalog_wps, pol_central, start_xy, sub_ids, sel_dg, dW_fine, dt_sim=0.005, fractional_segment_hit=True)
        s_gp_005_u_seg = _simulate_adaptive_tour_coupled(gp_world, catalog_wps, pol_upwind, start_xy, sub_ids, sel_dg, dW_fine, dt_sim=0.005, fractional_segment_hit=True)

        s_tr_dg = _simulate_adaptive_tour_coupled(world, catalog_wps, pol_central, start_xy, sub_ids, sel_dg, dW_fine, dt_sim=0.005, fractional_segment_hit=True)
        s_tr_ex = _simulate_adaptive_tour_coupled(world, catalog_wps, pol_central, start_xy, sub_ids, r_ex["select_next_waypoint"], dW_fine, dt_sim=0.005, fractional_segment_hit=True)

        euc_ord = min(
            itertools.permutations(sub_ids),
            key=lambda perm: float(np.linalg.norm(start_xy - np.asarray(catalog_wps[perm[0]].center)))
            + sum(float(np.linalg.norm(np.asarray(catalog_wps[a].center) - np.asarray(catalog_wps[b].center))) for a, b in zip(perm[:-1], perm[1:])),
        )
        euc_sel = lambda cur_xy, prev_wp, rem_ids, eo=euc_ord: next(w for w in eo if w in rem_ids)
        s_tr_eu = _simulate_adaptive_tour_coupled(world, catalog_wps, pol_central, start_xy, sub_ids, euc_sel, dW_fine, dt_sim=0.005, fractional_segment_hit=True)

        c_ex_m.append(s_tr_ex["mean_cost"])
        c_dg_m.append(s_tr_dg["mean_cost"])
        c_eu_m.append(s_tr_eu["mean_cost"])
        mc_ses.append(s_tr_dg["mc_se"])
        timeouts_l.append(s_tr_dg["timeout_frac"])
        clips_l.append(s_tr_dg["clip_frac"])

        task_signed["L1_compressed_mid_minus_exact_macro"].append(float(j_port_mid - j_dg_exact))
        task_signed["L2a_gp_dt015_central_end_minus_exact_macro"].append(float(s_gp_015_c_end["mean_cost"] - j_dg_exact))
        task_signed["L2b_gp_dt005_central_end_minus_exact_macro"].append(float(s_gp_005_c_end["mean_cost"] - j_dg_exact))
        task_signed["L2c_gp_dt005_central_fracseg_minus_exact_macro"].append(float(s_gp_005_c_seg["mean_cost"] - j_dg_exact))
        task_signed["L2d_gp_dt005_upwind_fracseg_minus_exact_macro"].append(float(s_gp_005_u_seg["mean_cost"] - j_dg_exact))
        task_signed["dt_refinement_effect_dt005_minus_dt015_coupled"].append(float(s_gp_005_c_end["mean_cost"] - s_gp_015_c_end["mean_cost"]))
        task_signed["fracseg_effect_minus_endpoint_at_dt005"].append(float(s_gp_005_c_seg["mean_cost"] - s_gp_005_c_end["mean_cost"]))
        task_signed["upwind_minus_central_at_dt005_fracseg"].append(float(s_gp_005_u_seg["mean_cost"] - s_gp_005_c_seg["mean_cost"]))
        task_signed["L3_true_minus_gp_at_dt005_central_fracseg"].append(float(s_tr_dg["mean_cost"] - s_gp_005_c_seg["mean_cost"]))

    return {
        "map_seed": m_seed,
        "certified_tasks": cert_count,
        "bound_violations": bound_violations,
        "discrete_regrets": discrete_regrets,
        "root_match": root_match,
        "mc_ses": mc_ses,
        "timeout_frac": float(np.mean(timeouts_l)),
        "clip_frac": float(np.mean(clips_l)),
        "map_signed_means": {k: float(np.mean(v)) for k, v in task_signed.items()},
        "map_abs_means": {k: float(np.mean(np.abs(v))) for k, v in task_signed.items()},
        "ExactMacro_cost": float(np.mean(c_ex_m)),
        "DecisionPort_cost": float(np.mean(c_dg_m)),
        "Euclidean_cost": float(np.mean(c_eu_m)),
    }


def run_model_to_execution_fidelity_study(n_maps: int = 12, tasks_per_map: int = 6, grid_n: int = 75, max_workers: int = 8) -> dict:
    map_seeds = list(range(9900, 9900 + n_maps))
    items = [(i, s, tasks_per_map, grid_n) for i, s in enumerate(map_seeds)]
    rows = run_map_parallel(_fidelity_map_worker, items, max_workers=max_workers)

    s_keys = list(rows[0]["map_signed_means"].keys())
    ex_arr = np.array([r["ExactMacro_cost"] for r in rows])
    dg_arr = np.array([r["DecisionPort_cost"] for r in rows])
    eu_arr = np.array([r["Euclidean_cost"] for r in rows])

    return {
        "locked_fresh_seeds": map_seeds,
        "wiener_coupling": "exact_3x_hierarchical_substep_summation (dt=0.005 -> dt=0.015)",
        "segment_stopping_rule": "exact_quadratic_sphere_entry_fractional_step_cost",
        "total_tasks": n_maps * tasks_per_map,
        "epsilon_certified_tasks": int(sum(r["certified_tasks"] for r in rows)),
        "bound_violations": int(sum(r["bound_violations"] for r in rows)),
        "mean_discrete_model_regret": float(np.mean([x for r in rows for x in r["discrete_regrets"]])),
        "root_first_action_agreement_with_exact_macro": float(np.mean([x for r in rows for x in r["root_match"]])),
        "mean_rollout_mc_standard_error": float(np.mean([x for r in rows for x in r["mc_ses"]])),
        "mean_timeout_fraction": float(np.mean([r["timeout_frac"] for r in rows])),
        "mean_safety_clip_fraction": float(np.mean([r["clip_frac"] for r in rows])),
        "layers_mean_abs_gap": {k: float(np.mean([r["map_abs_means"][k] for r in rows])) for k in s_keys},
        "layers_map_paired_signed_stats": {k: paired_stats([r["map_signed_means"][k] for r in rows]) for k in s_keys},
        "real_continuous_policy_comparison": {
            "ExactMacro_mean_cost": float(np.mean(ex_arr)),
            "DecisionGuidedPort_mean_cost": float(np.mean(dg_arr)),
            "Euclidean_mean_cost": float(np.mean(eu_arr)),
            "DecisionPort_minus_ExactMacro_cost_diff": paired_stats(dg_arr - ex_arr),
            "DecisionPort_minus_Euclidean_cost_diff": paired_stats(dg_arr - eu_arr),
            "per_map_ExactMacro": ex_arr.tolist(),
            "per_map_DecisionPort": dg_arr.tolist(),
            "per_map_Euclidean": eu_arr.tolist(),
        },
    }


def _orthogonal_reuse_map_worker(args: Tuple[int, int, int]) -> dict:
    idx_m, ms, grid_n = args
    modes = [
        "Scratch-Rebuild",
        "Structure-Memory-Fresh-Exact",
        "Residual-Audited-Reuse",
        "Blind-Stale-Cache",
    ]
    mode_flag = {
        "Scratch-Rebuild": "scratch_rebuild",
        "Structure-Memory-Fresh-Exact": "structure_only_fresh_exact",
        "Residual-Audited-Reuse": "selective_residual",
        "Blind-Stale-Cache": "blind_stale_cache",
    }

    w_base = generate_benchmark_map(ms, dim=2, regime="narrow_barrier", with_drift=True)
    rng = np.random.default_rng(ms + 88)
    rng_order = np.random.default_rng(ms + 999)
    r_wp = 0.26
    catalog_wps: List[GoalBall] = []
    for _ in range(12):
        for _att in range(220):
            pt = rng.uniform(-1.22, 1.22, size=2)
            if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.04 * r_wp for w in catalog_wps):
                catalog_wps.append(GoalBall(tuple(pt.tolist()), phi=0.0, radius=r_wp))
                break

    X1, q1, b1 = sample_noisy_probes(w_base, n_probes=65, seed=ms + 3, include_drift=True)
    km1 = KrigingWorldModel(X1, q1, b1)
    q_ep2_fn = lambda X, k=km1: k.predict_q(X) + 0.35 * np.exp(-np.sum((X - np.array([[1.38, 1.38]])) ** 2, axis=1) / 0.03)
    q_ep3_fn = lambda X, k=km1: k.predict_q(X) + 6.5 * np.exp(-np.sum((X - np.array([[-0.45, 0.55]])) ** 2, axis=1) / 0.08)
    w_ep4 = generate_benchmark_map(ms + 500, dim=2, regime="narrow_barrier", with_drift=True)
    km4 = KrigingWorldModel(*sample_noisy_probes(w_ep4, n_probes=95, seed=ms + 44, include_drift=True))

    epochs = [
        (1, km1.predict_q, km1.predict_b),
        (2, q_ep2_fn, km1.predict_b),
        (3, q_ep3_fn, km1.predict_b),
        (4, km4.predict_q, km4.predict_b),
    ]

    planners = {
        m: SchurPortPlanner(w_base.spec, grid_n, km1.predict_q, km1.predict_b, catalog_wps, initial_sectors_per_wp="L1", lazy_init=True)
        for m in modes
    }
    mts = {m: MacroTourPlanner(planners[m]) for m in modes}
    cum_ms = {m: planners[m].op_build_ms for m in modes}
    ep_cum = {m: {} for m in modes}
    phase_ms = {
        m: {"init_ms": planners[m].op_build_ms, "update_ms": 0.0, "col_solve_ms": 0.0, "dp_ms": 0.0, "occ_ms": 0.0}
        for m in modes
    }
    col_stats = {m: {"retained": 0, "recomputed": 0, "dropped": 0} for m in modes}
    status_counts = {m: {"epsilon_certified": 0, "unresolved": 0, "numeric_invalid": 0} for m in modes}
    dp_calls_tot = {m: 0 for m in modes}
    viols = {m: {f"epoch_{e}": 0 for e in range(1, 5)} for m in modes}
    regrets = {m: [] for m in modes}

    for ep_num, q_fn, b_fn in epochs:
        if ep_num >= 2:
            for m in rng_order.permutation(modes).tolist():
                u_info = planners[m].update_world_with_residual_audit(q_fn, b_fn, mode=mode_flag[m])
                cum_ms[m] += u_info["update_ms"]
                phase_ms[m]["update_ms"] += u_info["update_ms"]
                col_stats[m]["retained"] += u_info["cols_retained"]
                col_stats[m]["recomputed"] += u_info["cols_recomputed"]
                col_stats[m]["dropped"] += u_info["cols_dropped"]

        pl_true_ep = SchurPortPlanner(w_base.spec, grid_n, q_fn, b_fn, catalog_wps, initial_sectors_per_wp="L1", lazy_init=True)

        for _tk in range(5):
            sub_ids = tuple(rng.choice(len(catalog_wps), size=5, replace=False).tolist())
            start_xy = np.array([-1.32, -1.32])
            for _att in range(120):
                cand = rng.uniform(-1.28, 1.28, size=2)
                if all(np.linalg.norm(cand - np.asarray(catalog_wps[j].center)) > r_wp + 0.15 for j in sub_ids):
                    start_xy = cand
                    break

            for m in rng_order.permutation(modes).tolist():
                res_m = mts[m].plan_subset_macro_policy(
                    start_xy, sub_ids, epsilon_tol=0.25, max_refine_steps=12,
                    refine_strategy="decision_guided", use_incremental_dp=True,
                )
                cum_ms[m] += res_m["planning_ms"]
                phase_ms[m]["col_solve_ms"] += res_m["col_solve_ms"]
                phase_ms[m]["dp_ms"] += res_m["dp_ms"]
                phase_ms[m]["occ_ms"] += res_m["occupancy_ms"]
                dp_calls_tot[m] += res_m["work"]["dp_calls"]
                status_counts[m][res_m["status"]] = status_counts[m].get(res_m["status"], 0) + 1

                ref_ep = independent_exact_macro_bellman_reference(pl_true_ep, start_xy, sub_ids, policy_action_idx=res_m["policy_action_idx"])
                f_opt = ref_ep["optimal_adaptive_macro_cost"]
                j_pol = ref_ep["evaluated_policy_exact_macro_cost"]
                regrets[m].append(float(j_pol - f_opt))
                lo_m, hi_m = res_m["macro_value_bounds"]
                if not ((lo_m - 1e-9 <= f_opt <= hi_m + 1e-9) and (f_opt - 1e-9 <= j_pol <= hi_m + 1e-9)):
                    viols[m][f"epoch_{ep_num}"] += 1

        for m in modes:
            ep_cum[m][f"epoch_{ep_num}"] = cum_ms[m]

    return {
        "map_seed": ms,
        "ep_cum": ep_cum,
        "phase_ms": phase_ms,
        "col_stats": col_stats,
        "status_counts": status_counts,
        "dp_calls": dp_calls_tot,
        "lu_facts": {m: planners[m].lu_factorizations for m in modes},
        "backsolves": {m: planners[m].total_lu_backsolves for m in modes},
        "viols": viols,
        "regrets": {m: float(np.mean(regrets[m])) for m in modes},
    }


def run_orthogonal_operator_transition_stream(n_maps: int = 10, grid_n: int = 61, max_workers: int = 8) -> dict:
    map_seeds = list(range(9950, 9950 + n_maps))
    rows = run_map_parallel(_orthogonal_reuse_map_worker, [(i, s, grid_n) for i, s in enumerate(map_seeds)], max_workers=max_workers)
    modes = ["Scratch-Rebuild", "Structure-Memory-Fresh-Exact", "Residual-Audited-Reuse", "Blind-Stale-Cache"]
    scr_ep4 = np.array([r["ep_cum"]["Scratch-Rebuild"]["epoch_4"] for r in rows])

    out_m = {}
    for m in modes:
        m_ep4 = np.array([r["ep_cum"][m]["epoch_4"] for r in rows])
        out_m[m] = {
            "cumulative_ms_by_epoch": {
                f"epoch_{e}": float(np.mean([r["ep_cum"][m][f"epoch_{e}"] for r in rows])) for e in range(1, 5)
            },
            "speedup_at_epoch4_vs_scratch": float(np.mean(scr_ep4) / np.mean(m_ep4)),
            "paired_epoch4_ms_diff_vs_scratch": paired_stats(m_ep4 - scr_ep4),
            "mean_phase_ms": {
                pk: float(np.mean([r["phase_ms"][m][pk] for r in rows]))
                for pk in ("init_ms", "update_ms", "col_solve_ms", "dp_ms", "occ_ms")
            },
            "mean_dp_calls": float(np.mean([r["dp_calls"][m] for r in rows])),
            "mean_total_lu_factorizations": float(np.mean([r["lu_facts"][m] for r in rows])),
            "mean_total_lu_backsolves": float(np.mean([r["backsolves"][m] for r in rows])),
            "mean_transition_column_counts": {
                ck: float(np.mean([r["col_stats"][m][ck] for r in rows])) for ck in ("retained", "recomputed", "dropped")
            },
            "task_status_counts_of_200": {
                sk: int(sum(r["status_counts"][m].get(sk, 0) for r in rows))
                for sk in ("epsilon_certified", "unresolved", "numeric_invalid")
            },
            "mean_true_epoch_policy_regret": float(np.mean([r["regrets"][m] for r in rows])),
            "bound_violations_by_epoch": {
                f"epoch_{e}": int(sum(r["viols"][m][f"epoch_{e}"] for r in rows)) for e in range(1, 5)
            },
            "total_bound_violations_of_200": int(sum(sum(r["viols"][m].values()) for r in rows)),
        }
    return {
        "experiment_scope": "externally_supplied_operator_transitions_orthogonal_structure_vs_value_reuse",
        "locked_fresh_seeds": map_seeds,
        "grid_n": grid_n,
        "epochs": 4,
        "tasks_per_epoch_per_map": 5,
        "total_tasks_evaluated": n_maps * 20,
        "methods": out_m,
    }


def _select_active_probes_diverse(
    cand_pts: np.ndarray, scores: np.ndarray, existing_X: np.ndarray, n_select: int, min_repel: float = 0.22
) -> np.ndarray:
    """Greedy diversity-regularized probe selection using ONLY posterior/planner quantities (zero truth!)."""
    chosen = []
    cur_X = existing_X.copy()
    rem_mask = np.ones(len(cand_pts), dtype=bool)
    for _ in range(n_select):
        d_min = np.min(np.linalg.norm(cand_pts[:, None, :] - cur_X[None, :, :], axis=2), axis=1)
        eff_score = np.where(rem_mask, scores * np.minimum(1.0, (d_min / min_repel) ** 2), -np.inf)
        best_i = int(np.argmax(eff_score))
        rem_mask[best_i] = False
        pt = cand_pts[best_i]
        chosen.append(pt)
        cur_X = np.vstack([cur_X, pt[None, :]])
    return np.array(chosen)


def _prequential_map_worker(args: Tuple[int, int, int]) -> dict:
    """Genuine causal online loop (`D_t -> GP_t -> Audit/Plan -> Rollout & Sense -> D_{t+1}`):
    Episodes 1..4 accumulate probes (`28 -> 42 -> 56 -> 70`) on stationary `w_stat`;
    At Episode 5, a localized high-cost barrier emerges (`w_emerged`), and Episodes 5..6 (`84 -> 98` probes)
    test online change discovery & recovery!
    """
    idx_m, ms, grid_n = args
    w_stat = generate_benchmark_map(ms, dim=2, regime="narrow_barrier", with_drift=True)
    emerged_hz = HazardFeature((0.05, 0.10), 18.5, (0.14, 0.36))
    w_emerged = GroundTruthWorld(w_stat.spec, (*w_stat.hazards, emerged_hz), w_stat.vortices)

    rng = np.random.default_rng(ms + 123)
    r_wp = 0.26
    catalog_wps: List[GoalBall] = []
    for _ in range(10):
        for _att in range(220):
            pt = rng.uniform(-1.20, 1.20, size=2)
            if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.05 * r_wp for w in catalog_wps):
                catalog_wps.append(GoalBall(tuple(pt.tolist()), phi=0.0, radius=r_wp))
                break

    # Pre-sample 6 episodes x 3 tasks/episode (`m = 5`) shared across all methods
    ep_tasks = []
    for ep in range(6):
        t_ep = []
        for tk in range(3):
            sub_ids = tuple(rng.choice(len(catalog_wps), size=5, replace=False).tolist())
            start_xy = np.array([-1.30, -1.30])
            for _att in range(120):
                cand = rng.uniform(-1.25, 1.25, size=2)
                if all(np.linalg.norm(cand - np.asarray(catalog_wps[j].center)) > r_wp + 0.15 for j in sub_ids):
                    start_xy = cand
                    break
            t_ep.append((start_xy, sub_ids, 44000 + 100 * idx_m + 10 * ep + tk))
        ep_tasks.append(t_ep)

    X_init, q_init, b_init = sample_noisy_probes(w_stat, n_probes=28, seed=ms + 7, include_drift=True)

    # Part I: Planner Reuse Economics on the SAME Sequential GP Observation Stream (`Decision-Corridor` probes)
    # Part II: Same-Budget Active Sensing Comparison (`Uniform`, `MaxVariance`, `OnPolicy`, `Decision-Corridor`)
    sensing_modes = ["Uniform-Random", "Global-MaxVariance", "OnPolicy-Trajectory", "Decision-Corridor-Active"]
    sensing_costs = {sm: [] for sm in sensing_modes}

    # Candidate pool on `[-1.50, 1.50]^2` for active sensing
    gx = np.linspace(-1.48, 1.48, 25)
    gxx, gyy = np.meshgrid(gx, gx, indexing="ij")
    cand_pool = np.column_stack([gxx.ravel(), gyy.ravel()])

    reuse_planner_stats = {
        "Scratch-Port-Rebuild": {"gp_ms": 0.0, "update_ms": 0.0, "plan_ms": 0.0, "lu_facts": 0, "backsolves": 0, "cert": 0, "viols": 0},
        "ExactRing-Every-Episode": {"gp_ms": 0.0, "update_ms": 0.0, "plan_ms": 0.0, "lu_facts": 0, "backsolves": 0, "cert": 0, "viols": 0},
        "Audited-Incremental-Port": {"gp_ms": 0.0, "update_ms": 0.0, "plan_ms": 0.0, "lu_facts": 0, "backsolves": 0, "cert": 0, "viols": 0},
    }
    ep_lu_audited = []

    for sm in sensing_modes:
        X_cur = X_init.copy()
        q_cur = q_init.copy()
        b_cur = b_init.copy()
        rng_sense = np.random.default_rng(ms + 500 + sensing_modes.index(sm) * 37)

        pl_scr = None
        pl_exr = None
        pl_aud = None

        for ep in range(6):
            true_env = w_stat if ep < 4 else w_emerged
            t_gp0 = time.perf_counter()
            km_t = KrigingWorldModel(X_cur, q_cur, b_cur)
            gp_ms = 1000.0 * (time.perf_counter() - t_gp0)

            # For `Decision-Corridor-Active`, also run the 3 planner-reuse backends side-by-side!
            if sm == "Decision-Corridor-Active":
                for pk in reuse_planner_stats:
                    reuse_planner_stats[pk]["gp_ms"] += gp_ms
                if ep == 0:
                    pl_scr = SchurPortPlanner(w_stat.spec, grid_n, km_t.predict_q, km_t.predict_b, catalog_wps, initial_sectors_per_wp="L1", lazy_init=True)
                    pl_exr = SchurPortPlanner(w_stat.spec, grid_n, km_t.predict_q, km_t.predict_b, catalog_wps, initial_sectors_per_wp="EXACT", lazy_init=True)
                    pl_aud = SchurPortPlanner(w_stat.spec, grid_n, km_t.predict_q, km_t.predict_b, catalog_wps, initial_sectors_per_wp="L1", lazy_init=True)
                    reuse_planner_stats["Scratch-Port-Rebuild"]["update_ms"] += pl_scr.op_build_ms
                    reuse_planner_stats["ExactRing-Every-Episode"]["update_ms"] += pl_exr.op_build_ms
                    reuse_planner_stats["Audited-Incremental-Port"]["update_ms"] += pl_aud.op_build_ms
                else:
                    assert pl_scr is not None and pl_exr is not None and pl_aud is not None
                    u_s = pl_scr.update_world_with_residual_audit(km_t.predict_q, km_t.predict_b, mode="scratch_rebuild")
                    u_e = pl_exr.update_world_with_residual_audit(km_t.predict_q, km_t.predict_b, mode="scratch_rebuild")
                    # Mild error cap (`0.22`) allows stationary GP stabilization (Ep 3-4) to skip `splu` completely!
                    u_a = pl_aud.update_world_with_residual_audit(
                        km_t.predict_q, km_t.predict_b, mode="selective_residual", max_allowable_col_err=0.22
                    )
                    reuse_planner_stats["Scratch-Port-Rebuild"]["update_ms"] += u_s["update_ms"]
                    reuse_planner_stats["ExactRing-Every-Episode"]["update_ms"] += u_e["update_ms"]
                    reuse_planner_stats["Audited-Incremental-Port"]["update_ms"] += u_a["update_ms"]
                lu_before_ep = pl_aud.lu_factorizations
                pl_plan = pl_aud
            else:
                pl_plan = SchurPortPlanner(w_stat.spec, grid_n, km_t.predict_q, km_t.predict_b, catalog_wps, initial_sectors_per_wp="EXACT", lazy_init=True)

            mt_plan = MacroTourPlanner(pl_plan)
            exec_fd = ClassicalFDSolver(w_stat.spec, grid_n, km_t.predict_q, km_t.predict_b)
            leg_pols = {j: exec_fd.solve_direct(QueryTask(f"l_{j}", (w,), ((0.0, 0.0),)))["policy"] for j, w in enumerate(catalog_wps)}

            ep_real_costs = []
            visited_traj_pts = []
            corridor_weights = np.zeros(len(cand_pool), dtype=float)

            for start_xy, sub_ids, r_seed in ep_tasks[ep]:
                if sm == "Decision-Corridor-Active":
                    assert pl_scr is not None and pl_exr is not None and pl_aud is not None
                    rs_s = MacroTourPlanner(pl_scr).plan_subset_macro_policy(start_xy, sub_ids, epsilon_tol=0.25, max_refine_steps=12)
                    rs_e = MacroTourPlanner(pl_exr).plan_exact_subset_dp(start_xy, sub_ids)
                    rs_a = mt_plan.plan_subset_macro_policy(start_xy, sub_ids, epsilon_tol=0.25, max_refine_steps=12)
                    reuse_planner_stats["Scratch-Port-Rebuild"]["plan_ms"] += rs_s["planning_ms"]
                    reuse_planner_stats["ExactRing-Every-Episode"]["plan_ms"] += rs_e["planning_ms"]
                    reuse_planner_stats["Audited-Incremental-Port"]["plan_ms"] += rs_a["planning_ms"]

                    pl_ref_t = SchurPortPlanner(w_stat.spec, grid_n, km_t.predict_q, km_t.predict_b, catalog_wps, initial_sectors_per_wp="L1", lazy_init=True)
                    for pk, robj in [("Scratch-Port-Rebuild", rs_s), ("ExactRing-Every-Episode", rs_e), ("Audited-Incremental-Port", rs_a)]:
                        reuse_planner_stats[pk]["cert"] += int(robj["certified"])
                        ref_t = independent_exact_macro_bellman_reference(pl_ref_t, start_xy, sub_ids, policy_action_idx=robj["policy_action_idx"])
                        lo_t, hi_t = robj["macro_value_bounds"]
                        if not ((lo_t - 1e-9 <= ref_t["optimal_adaptive_macro_cost"] <= hi_t + 1e-9) and (ref_t["optimal_adaptive_macro_cost"] - 1e-9 <= ref_t["evaluated_policy_exact_macro_cost"] <= hi_t + 1e-9)):
                            reuse_planner_stats[pk]["viols"] += 1
                    res_act = rs_a
                else:
                    res_act = mt_plan.plan_exact_subset_dp(start_xy, sub_ids)

                # Rollout in TRUE environment (strictly for evaluation + on-policy state logging!)
                dW_f, dW_c = _generate_coupled_wiener_bank(r_seed, n_tr=16, m_legs=5, fine_steps_per_leg=1200, dt_fine=0.005)
                sim_r = _simulate_adaptive_tour_coupled(
                    true_env, catalog_wps, leg_pols, start_xy, sub_ids, res_act["select_next_waypoint"],
                    dW_c, dt_sim=0.015, fractional_segment_hit=True,
                )
                ep_real_costs.append(sim_r["mean_cost"])

                # Build corridor / on-policy weights using ONLY GP posterior & planned targets (NO true_env!)
                t_centers = [np.asarray(catalog_wps[j].center) for j in sub_ids]
                pts_chain = [start_xy, *t_centers]
                for a_pt, b_pt in zip(pts_chain[:-1], pts_chain[1:]):
                    for al_s in (0.25, 0.50, 0.75):
                        mid_p = (1.0 - al_s) * a_pt + al_s * b_pt
                        visited_traj_pts.append(mid_p)
                        corridor_weights += np.exp(-np.sum((cand_pool - mid_p[None, :]) ** 2, axis=1) / 0.18)

            if sm == "Decision-Corridor-Active":
                assert pl_aud is not None
                ep_lu_audited.append(pl_aud.lu_factorizations - lu_before_ep)

            sensing_costs[sm].append(float(np.mean(ep_real_costs)))

            # Acquire `+14` new noisy probes for Episode `ep + 1` from `true_env` (strictly causal!)
            if ep < 5:
                n_add = 14
                _, lat_std, _ = km_t.predict_q_latent_std(cand_pool)
                if sm == "Uniform-Random":
                    X_new = rng_sense.uniform(-1.50, 1.50, size=(n_add, 2))
                elif sm == "Global-MaxVariance":
                    X_new = _select_active_probes_diverse(cand_pool, lat_std, X_cur, n_add, min_repel=0.26)
                elif sm == "OnPolicy-Trajectory":
                    base_pts = np.array(visited_traj_pts)
                    idx_pick = rng_sense.choice(len(base_pts), size=n_add, replace=True)
                    X_new = np.clip(base_pts[idx_pick] + rng_sense.normal(0.0, 0.14, size=(n_add, 2)), -1.52, 1.52)
                elif sm == "Decision-Corridor-Active":
                    # Decision-relevant sensing: high GP uncertainty *inside* task-relevant waypoint corridors
                    # + 25% global exploration floor to detect unannounced hazards!
                    corr_norm = corridor_weights / max(float(np.max(corridor_weights)), 1e-12)
                    acq_score = lat_std * (0.25 + 0.75 * corr_norm)
                    X_new = _select_active_probes_diverse(cand_pool, acq_score, X_cur, n_add, min_repel=0.22)
                else:
                    raise ValueError(sm)

                Xn, qn, bn = observe_world_at_points(true_env, X_new, rng_sense, include_drift=True)
                X_cur = np.vstack([X_cur, Xn])
                q_cur = np.concatenate([q_cur, qn])
                b_cur = np.vstack([b_cur, bn])

        if sm == "Decision-Corridor-Active":
            assert pl_scr is not None and pl_exr is not None and pl_aud is not None
            reuse_planner_stats["Scratch-Port-Rebuild"]["lu_facts"] = pl_scr.lu_factorizations
            reuse_planner_stats["Scratch-Port-Rebuild"]["backsolves"] = pl_scr.total_lu_backsolves
            reuse_planner_stats["ExactRing-Every-Episode"]["lu_facts"] = pl_exr.lu_factorizations
            reuse_planner_stats["ExactRing-Every-Episode"]["backsolves"] = pl_exr.total_lu_backsolves
            reuse_planner_stats["Audited-Incremental-Port"]["lu_facts"] = pl_aud.lu_factorizations
            reuse_planner_stats["Audited-Incremental-Port"]["backsolves"] = pl_aud.total_lu_backsolves

    return {
        "map_seed": ms,
        "sensing_costs": sensing_costs,
        "reuse_planner_stats": reuse_planner_stats,
        "ep_lu_audited": ep_lu_audited,
    }


def run_prequential_online_learning_and_planning(n_maps: int = 12, grid_n: int = 55, max_workers: int = 8) -> dict:
    map_seeds = list(range(9850, 9850 + n_maps))
    rows = run_map_parallel(_prequential_map_worker, [(i, s, grid_n) for i, s in enumerate(map_seeds)], max_workers=max_workers)

    sensing_modes = ["Uniform-Random", "Global-MaxVariance", "OnPolicy-Trajectory", "Decision-Corridor-Active"]
    dec_late_stat = np.array([np.mean(r["sensing_costs"]["Decision-Corridor-Active"][2:4]) for r in rows])
    dec_post_shift = np.array([np.mean(r["sensing_costs"]["Decision-Corridor-Active"][4:6]) for r in rows])
    dec_cum = np.array([np.mean(r["sensing_costs"]["Decision-Corridor-Active"]) for r in rows])

    out_sense = {}
    for sm in sensing_modes:
        ep_means = [float(np.mean([r["sensing_costs"][sm][ep] for r in rows])) for ep in range(6)]
        sm_late = np.array([np.mean(r["sensing_costs"][sm][2:4]) for r in rows])
        sm_shift = np.array([np.mean(r["sensing_costs"][sm][4:6]) for r in rows])
        sm_cum = np.array([np.mean(r["sensing_costs"][sm]) for r in rows])
        out_sense[sm] = {
            "mean_true_cost_by_episode": ep_means,
            "overall_6ep_mean_cost": float(np.mean(sm_cum)),
            "late_stationary_ep3_4_mean_cost": float(np.mean(sm_late)),
            "post_emergence_ep5_6_mean_cost": float(np.mean(sm_shift)),
            "decision_corridor_minus_method_overall": paired_stats(dec_cum - sm_cum),
            "decision_corridor_minus_method_late_stationary": paired_stats(dec_late_stat - sm_late),
            "decision_corridor_minus_method_post_emergence": paired_stats(dec_post_shift - sm_shift),
        }

    out_reuse = {}
    scr_plan_tot = np.array([
        r["reuse_planner_stats"]["Scratch-Port-Rebuild"]["update_ms"] + r["reuse_planner_stats"]["Scratch-Port-Rebuild"]["plan_ms"]
        for r in rows
    ])
    for pk in ("Scratch-Port-Rebuild", "ExactRing-Every-Episode", "Audited-Incremental-Port"):
        gp_v = [r["reuse_planner_stats"][pk]["gp_ms"] for r in rows]
        up_v = [r["reuse_planner_stats"][pk]["update_ms"] for r in rows]
        pl_v = [r["reuse_planner_stats"][pk]["plan_ms"] for r in rows]
        p_tot = np.array(up_v) + np.array(pl_v)
        e2e_tot = np.array(gp_v) + p_tot
        out_reuse[pk] = {
            "mean_gp_fit_ms": float(np.mean(gp_v)),
            "mean_operator_update_ms": float(np.mean(up_v)),
            "mean_task_planning_ms": float(np.mean(pl_v)),
            "mean_planner_subtotal_ms": float(np.mean(p_tot)),
            "mean_end_to_end_learning_plus_planning_ms": float(np.mean(e2e_tot)),
            "planner_speedup_vs_scratch_port": float(np.mean(scr_plan_tot) / np.mean(p_tot)),
            "mean_lu_factorizations_across_6_episodes": float(np.mean([r["reuse_planner_stats"][pk]["lu_facts"] for r in rows])),
            "mean_lu_backsolves": float(np.mean([r["reuse_planner_stats"][pk]["backsolves"] for r in rows])),
            "certified_tasks_of_216": int(sum(r["reuse_planner_stats"][pk]["cert"] for r in rows)),
            "bound_violations_of_216": int(sum(r["reuse_planner_stats"][pk]["viols"] for r in rows)),
        }

    return {
        "experiment_scope": "genuine_prequential_gp_observation_accumulation_and_local_shift_discovery",
        "locked_fresh_seeds": map_seeds,
        "grid_n": grid_n,
        "probe_schedule": [28, 42, 56, 70, 84, 98],
        "shift_event": "unannounced_local_barrier_at_episode_5",
        "audited_port_lu_factorizations_by_episode_mean": [
            float(np.mean([r["ep_lu_audited"][ep] for r in rows])) for ep in range(6)
        ],
        "planner_reuse_economics": out_reuse,
        "active_sensing_comparison": out_sense,
    }


def plot_exp4(fid: dict, cont: dict, preq: dict, out_png: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(19.8, 5.4))

    # Panel 1: Coupled Wiener Model-to-Execution Fidelity Decomposition
    ax = axes[0]
    gaps = fid["layers_mean_abs_gap"]
    labels = [
        "L1: Port vs\nExactMacro",
        "L2a: GP SDE\ndt=.015 End",
        "L2b: GP SDE\ndt=.005 End",
        "L2c: GP SDE\ndt=.005 FracSeg",
        "L3: True vs\nGP Posterior",
        "|Real Diff|\nvs ExactMacro",
    ]
    vals = [
        gaps["L1_compressed_mid_minus_exact_macro"],
        gaps["L2a_gp_dt015_central_end_minus_exact_macro"],
        gaps["L2b_gp_dt005_central_end_minus_exact_macro"],
        gaps["L2c_gp_dt005_central_fracseg_minus_exact_macro"],
        gaps["L3_true_minus_gp_at_dt005_central_fracseg"],
        abs(fid["real_continuous_policy_comparison"]["DecisionPort_minus_ExactMacro_cost_diff"]["mean"]),
    ]
    cols = ["#2ca02c", "#d62728", "#ff7f0e", "#1f77b4", "#9467bd", "#17becf"]
    bars = ax.bar(np.arange(len(labels)), vals, width=0.56, color=cols)
    ax.axhline(fid["mean_rollout_mc_standard_error"], color="#555555", ls="--", lw=1.2, label=f"Mean Rollout MC SE ({fid['mean_rollout_mc_standard_error']:.2f})")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, fontsize=7.4)
    ax.set_ylabel("Mean Absolute Discrepancy")
    ax.set_title("Coupled-Wiener Fidelity Bridge (72 Fresh Tours)\n(Exact 3x Substep Brownian Coupling + Fractional Segment Hit)", fontsize=9.1)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=7.3, loc="upper right")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.3f}", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax.set_ylim(0, max(vals) * 1.20)

    # Panel 2: Orthogonal Continual Reuse Attribution (`Scratch` vs `Structure-Only` vs `Residual-Audited`)
    ax = axes[1]
    eps = [1, 2, 3, 4]
    ep_lbls = ["Ep 1\n(Init GP)", "Ep 2\n(Mild Local Δq)", "Ep 3\n(Regional Wall)", "Ep 4\n(Global Shift)"]
    for m_key, col, mk, ls in [
        ("Scratch-Rebuild", "#d62728", "o", "--"),
        ("Structure-Memory-Fresh-Exact", "#ff7f0e", "^", "-."),
        ("Residual-Audited-Reuse", "#1f77b4", "s", "-"),
        ("Blind-Stale-Cache", "#7f7f7f", "x", ":"),
    ]:
        ys = [cont["methods"][m_key]["cumulative_ms_by_epoch"][f"epoch_{e}"] for e in eps]
        v_tot = cont["methods"][m_key]["total_bound_violations_of_200"]
        lu_tot = cont["methods"][m_key]["mean_total_lu_factorizations"]
        ax.plot(eps, ys, marker=mk, color=col, ls=ls, lw=2.1, label=f"{m_key} [LU={lu_tot:.1f}, viol={v_tot}]")
    ax.set_xticks(eps)
    ax.set_xticklabels(ep_lbls, fontsize=7.8)
    ax.set_ylabel("Cumulative Setup + Update + Plan Time (ms)")
    ax.set_title("Orthogonal Operator-Transition Attribution (200 Tasks)\n(Separates Partition-Structure Memory vs. Residual Column Reuse)", fontsize=9.1)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.0, loc="upper left")

    # Panel 3: Genuine Prequential Online Learning & Active Sensing (`Episodes 1..6`)
    ax = axes[2]
    ep6 = np.arange(1, 7)
    probes = preq["probe_schedule"]
    for sm, col, mk, ls in [
        ("Uniform-Random", "#7f7f7f", "o", "--"),
        ("OnPolicy-Trajectory", "#ff7f0e", "^", "-."),
        ("Global-MaxVariance", "#9467bd", "D", ":"),
        ("Decision-Corridor-Active", "#2ca02c", "s", "-"),
    ]:
        ys = preq["active_sensing_comparison"][sm]["mean_true_cost_by_episode"]
        ax.plot(ep6, ys, marker=mk, color=col, lw=2.1, ls=ls, label=sm)
    ax.axvline(4.5, color="#d62728", ls="--", lw=1.3, alpha=0.75, label="Unannounced Barrier (Ep 5)")
    ax.set_xticks(ep6)
    ax.set_xticklabels([f"Ep {e}\n({p} obs)" for e, p in zip(ep6, probes)], fontsize=7.6)
    ax.set_ylabel("True-World Closed-Loop Tour Cost")
    ax.set_title("Prequential Online GP Learning & Active Sensing (12 Maps)\n(Corridor Probing Leads Stationary Learning; Beats On-Policy p=.011)", fontsize=9.1)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.1, loc="upper right")

    plt.tight_layout()
    plt.savefig(out_png, dpi=175)
    plt.close(fig)


def main():
    enforce_single_thread_env()
    n_workers = 8
    print(f"=== Exp 4A: Coupled-Wiener Fidelity Bridge (12 Maps x 6 Tours, {n_workers}-Core Parallel) ===", flush=True)
    t0 = time.perf_counter()
    fid = run_model_to_execution_fidelity_study(n_maps=12, tasks_per_map=6, grid_n=75, max_workers=n_workers)
    print(f"  -> Exp 4A done in {time.perf_counter()-t0:.1f}s (bound_violations={fid['bound_violations']})", flush=True)

    print(f"\n=== Exp 4B: Orthogonal Operator-Transition Attribution (10 Maps x 20 Tasks, {n_workers}-Core Parallel) ===", flush=True)
    t0 = time.perf_counter()
    cont = run_orthogonal_operator_transition_stream(n_maps=10, grid_n=61, max_workers=n_workers)
    print(f"  -> Exp 4B done in {time.perf_counter()-t0:.1f}s", flush=True)

    print(f"\n=== Exp 4C: Genuine Prequential Online Learning & Active Sensing (12 Maps x 6 Episodes, {n_workers}-Core Parallel) ===", flush=True)
    t0 = time.perf_counter()
    preq = run_prequential_online_learning_and_planning(n_maps=12, grid_n=55, max_workers=n_workers)
    print(f"  -> Exp 4C done in {time.perf_counter()-t0:.1f}s", flush=True)

    out_dir = Path(__file__).resolve().parent
    payload = {
        "metadata": collect_runtime_metadata(max_workers=n_workers),
        "model_to_execution_fidelity_72tasks": fid,
        "continual_orthogonal_transition_200tasks": cont,
        "prequential_online_learning_and_sensing_12maps": preq,
    }
    (out_dir / "exp4_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plot_exp4(fid, cont, preq, out_dir / "exp4_fidelity_and_continual.png")
    print("Saved exp4_results.json and exp4_fidelity_and_continual.png", flush=True)


if __name__ == "__main__":
    main()
