"""Experiment 4 (`green_response` — `d1b926a` Work Packages A, B, & C, 8-Core Parallel):
Coupled-Wiener Fidelity Bridge, Cache Net-Benefit Crossover, & Unconfounded Online World-Model Learning!

4A. Coupled-Wiener Model-to-Execution Fidelity Bridge (`12` Benchmark Maps `9900..9911` x `6` Tours = `72` Tasks):
    - Exact 3-substep Brownian path coupling (`dW_coarse[k] = sum_{j=0..2} dW_fine[3k+j]`).
    - Exact piecewise-reflected polyline sphere-entry stopping (`_eval_reflected_step_goal_union_hit_tau`,
      eliminating wall-bounce chord false-hits and missed pre-reflection hits; explicitly distinguished
      from continuous Brownian-bridge first passage).
    - Retains per-arm `timeout_frac`, `clip_frac`, `completion_rate`, and full `per_map_records`.

4B. Orthogonal Reuse Attribution (`200` Tasks on `9950..9959`) & Net-Benefit Crossover (`8` Fresh Maps `10200..10207`):
    - Retains full `per_map_records` in the 4-epoch orthogonal transition stream (enabling paired CIs
      between `Residual-Audited-Reuse` and `Structure-Memory-Fresh-Exact`).
    - Adds a 2x2 factorial crossover (`Cold-Partial-Catalog` vs `Warm-Full-Catalog` x `2D 61^2` vs `3D 21^3`
      under mild local perturbation, `K = 6` post-transition tasks/map), charging complete lifecycle time
      `T_total = T_update + T_deferred_LU_and_cols + T_DP + T_occ + T_router`.

4C. Unconfounded 5-Arm Online World-Model Learning & Held-Out Future Transfer (`16` Fresh Maps `10100..10115`):
    - ALL 5 arms execute the EXACT SAME `ExactRing + Subset-DP` planner (residual cache disabled),
      same low-level FD controller family, same initial `28` noisy observations (`0.0` Ep-1 cost confound!),
      same `+14` probe budget (`28 -> 98` across 6 checkpoints), and same `min_repel = 0.24`:
        1. `Frozen-GP-28` (no-learning counterfactual control);
        2. `Uniform-Random` (14 random coordinate probes/ep);
        3. `Global-MaxVariance` (14 posterior uncertainty probes/ep);
        4. `True-OnPolicy-Trajectory` (14 probes subsampled strictly from realized closed-loop `(x_t)` rollout states!);
        5. `Green-Frechet-Active` (target-order-invariant exact discrete Green adjoint sensitivity `dJ/dq` +
           action-gap sensitivity `d(Delta Q)/dq` projected through GP posterior variance reduction, with an
           explicit `11` decision + `3` global-sentinel hard quota).
    - Evaluates at every checkpoint on a FIXED HELD-OUT FUTURE TASK BANK (`6` disjoint `m = 5` tours/map
      with coupled CRN noise, never seen by any acquisition rule!), reporting held-out cumulative cost,
      complete-tour completion rate, timeout/clip fractions, acquisition compute time, and full `per_map_records`.
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
    holm_bonferroni_adjust,
    independent_exact_macro_bellman_reference,
    make_consistent_value_and_policy_2d3d,
    observe_world_at_points,
    paired_relative_noninferiority,
    paired_stats,
    reflect_into_box,
    run_map_parallel,
    sample_noisy_probes,
)
from green_response.core import _eval_reflected_step_goal_union_hit_tau, _eval_segment_goal_union_hit_tau


class _GPWorldProxy:
    """Wraps `(spec, km)` with the same `.spec`, `.q_total`, `.drift` interface as `GroundTruthWorld`."""

    def __init__(self, spec: ProblemSpec, km: KrigingWorldModel):
        self.spec = spec
        self.km = km

    def q_total(self, X: np.ndarray, local_hazards: Sequence[HazardFeature] = ()) -> np.ndarray:
        return self.spec.q0 + self.km.predict_q(X)

    def drift(self, X: np.ndarray) -> np.ndarray:
        return self.km.predict_b(X)


def _generate_coupled_wiener_bank(
    seed_t: int, n_tr: int, m_legs: int, fine_steps_per_leg: int = 1860, dt_fine: float = 0.005
) -> Tuple[np.ndarray, np.ndarray]:
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
    record_visited_states: bool = False,
    visit_log_stride: int = 3,
) -> dict:
    """Vectorized-by-leg adaptive multi-leg SDE rollout (`10x` faster while preserving exact per-trajectory
    `dW_legs[tr_i, leg_k, st]` innovations, exact piecewise-reflected polyline sphere-entry stopping when
    `fractional_segment_hit=True`, per-tour completion/timeout/clip tracking, and deterministic trajectory-major
    `visited_states` logging!).
    """
    n_tr, max_legs_bank, max_leg_steps, dim = dW_legs.shape
    L = float(env_world.spec.half_width)
    R_vec = env_world.spec.R_vec
    tot_c = np.zeros(n_tr, dtype=float)
    timed_out = np.zeros(n_tr, dtype=bool)
    clipped_steps = 0
    active_steps = 0
    X_cur = np.repeat(reflect_into_box(np.asarray(start_xy, dtype=float)[None, :], L), n_tr, axis=0)
    vis_by_tr: List[List[np.ndarray]] = [[X_cur[i].copy()] if record_visited_states else [] for i in range(n_tr)]
    rem_by_tr: List[List[int]] = [list(target_ids) for _ in range(n_tr)]
    prev_wp_by_tr: List[Optional[int]] = [None for _ in range(n_tr)]

    m_total = len(target_ids)
    for leg_k in range(m_total):
        active_trs = [i for i in range(n_tr) if (not timed_out[i]) and len(rem_by_tr[i]) > 0]
        if not active_trs:
            break
        wp_groups: Dict[int, List[int]] = {}
        for tr_i in active_trs:
            wp_j = int(selector_fn(X_cur[tr_i], prev_wp_by_tr[tr_i], rem_by_tr[tr_i]))
            wp_groups.setdefault(wp_j, []).append(tr_i)

        dw_leg_idx = min(leg_k, max_legs_bank - 1)
        for wp_j in sorted(wp_groups.keys()):
            grp = np.array(wp_groups[wp_j], dtype=np.int64)
            pol = leg_pol_cache[wp_j]
            g_ball = catalog_wps[wp_j]

            hit0, phi0 = eval_goal_union(X_cur[grp], (g_ball,))
            if np.any(hit0):
                for tr_done, ph_val in zip(grp[hit0].tolist(), phi0[hit0].tolist()):
                    tot_c[tr_done] += float(ph_val)
                    rem_by_tr[tr_done].remove(wp_j)

            alive_grp = grp[~hit0]
            for st in range(max_leg_steps):
                if len(alive_grp) == 0:
                    break
                xa = X_cur[alive_grp]
                u = np.asarray(pol(xa), dtype=float)
                un = np.linalg.norm(u, axis=1)
                over = un > u_clip_safety
                if np.any(over):
                    u[over] = u[over] * (u_clip_safety / un[over])[:, None]
                    clipped_steps += int(np.sum(over))
                active_steps += len(alive_grp)

                qt = np.asarray(env_world.q_total(xa), dtype=float)
                rate = qt + 0.5 * np.sum((u ** 2) * R_vec[None, :], axis=1)
                bv = np.asarray(env_world.drift(xa), dtype=float)
                dwa = dW_legs[alive_grp, dw_leg_idx, st, :]
                x_raw = xa + (bv + u) * dt_sim + env_world.spec.sigma * dwa

                if fractional_segment_hit:
                    hit_s, phi_s, tau_s, x_pos, _ = _eval_reflected_step_goal_union_hit_tau(
                        xa, x_raw, L, (g_ball,)
                    )
                    tot_c[alive_grp] += rate * (tau_s * dt_sim)
                    X_cur[alive_grp] = x_pos
                else:
                    x_nxt = reflect_into_box(x_raw, L)
                    hit_s, phi_s = eval_goal_union(x_nxt, (g_ball,))
                    tot_c[alive_grp] += rate * dt_sim
                    X_cur[alive_grp] = x_nxt

                if record_visited_states:
                    log_stride_now = (st % visit_log_stride == 0)
                    for loc_k, tr_id in enumerate(alive_grp.tolist()):
                        if log_stride_now or bool(hit_s[loc_k]):
                            vis_by_tr[tr_id].append(X_cur[tr_id].copy())

                if np.any(hit_s):
                    for tr_hit, ph_val in zip(alive_grp[hit_s].tolist(), phi_s[hit_s].tolist()):
                        tot_c[tr_hit] += float(ph_val)
                        rem_by_tr[tr_hit].remove(wp_j)
                        prev_wp_by_tr[tr_hit] = wp_j
                    alive_grp = alive_grp[~hit_s]

            if len(alive_grp) > 0:
                for tr_fail in alive_grp.tolist():
                    tot_c[tr_fail] += 8.0
                    timed_out[tr_fail] = True

    timeouts = int(np.sum(timed_out))
    out = {
        "mean_cost": float(np.mean(tot_c)),
        "mc_se": float(np.std(tot_c, ddof=1) / np.sqrt(n_tr)),
        "completion_rate": float(1.0 - timeouts / n_tr),
        "timeout_frac": float(timeouts / n_tr),
        "clip_frac": float(clipped_steps / max(active_steps, 1)),
        "traj_costs": tot_c,
    }
    if record_visited_states:
        flat_vis = [pt for tr_l in vis_by_tr for pt in tr_l]
        out["visited_states"] = np.array(flat_vis, dtype=float) if flat_vis else np.empty((0, dim))
    return out


# ==============================================================================
# Exp 4A: Coupled-Wiener Fidelity Bridge (Piecewise-Reflected Polyline Hit)
# ==============================================================================
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
    arm_diag = {
        k: {"cost": [], "timeout": [], "clip": [], "completion": []}
        for k in ("ExactMacro", "DecisionPort", "Euclidean", "GP_dt015_end", "GP_dt005_end", "GP_dt005_refseg", "GP_dt005_upwind")
    }
    discrete_regrets = []
    root_match = []
    mc_ses = []
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

        for ak, sim_o in [
            ("ExactMacro", s_tr_ex),
            ("DecisionPort", s_tr_dg),
            ("Euclidean", s_tr_eu),
            ("GP_dt015_end", s_gp_015_c_end),
            ("GP_dt005_end", s_gp_005_c_end),
            ("GP_dt005_refseg", s_gp_005_c_seg),
            ("GP_dt005_upwind", s_gp_005_u_seg),
        ]:
            arm_diag[ak]["cost"].append(sim_o["mean_cost"])
            arm_diag[ak]["timeout"].append(sim_o["timeout_frac"])
            arm_diag[ak]["clip"].append(sim_o["clip_frac"])
            arm_diag[ak]["completion"].append(sim_o["completion_rate"])

        mc_ses.append(s_tr_dg["mc_se"])
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
        "mean_discrete_regret": float(np.mean(discrete_regrets)),
        "mean_root_match": float(np.mean(root_match)),
        "mean_mc_se": float(np.mean(mc_ses)),
        "arm_summary": {
            ak: {mk: float(np.mean(mv)) for mk, mv in av.items()} for ak, av in arm_diag.items()
        },
        "map_signed_means": {k: float(np.mean(v)) for k, v in task_signed.items()},
        "map_abs_means": {k: float(np.mean(np.abs(v))) for k, v in task_signed.items()},
    }


def run_model_to_execution_fidelity_study(n_maps: int = 12, tasks_per_map: int = 6, grid_n: int = 75, max_workers: int = 8) -> dict:
    map_seeds = list(range(9900, 9900 + n_maps))
    rows = run_map_parallel(_fidelity_map_worker, [(i, s, tasks_per_map, grid_n) for i, s in enumerate(map_seeds)], max_workers=max_workers)
    s_keys = list(rows[0]["map_signed_means"].keys())
    ex_arr = np.array([r["arm_summary"]["ExactMacro"]["cost"] for r in rows])
    dg_arr = np.array([r["arm_summary"]["DecisionPort"]["cost"] for r in rows])
    eu_arr = np.array([r["arm_summary"]["Euclidean"]["cost"] for r in rows])

    return {
        "block_provenance": "fresh_computed_in_current_run",
        "seed_role": "regression_benchmark_seeds_9900_9911",
        "benchmark_seeds": map_seeds,
        "wiener_coupling": "exact_3x_hierarchical_substep_summation (dt=0.005 -> dt=0.015)",
        "segment_stopping_rule": "exact_piecewise_reflected_polyline_sphere_entry_not_brownian_bridge",
        "finite_horizon_penalty_note": "Unreached legs after max_leg_steps incur +8.0 penalty and terminate remaining tour goals.",
        "total_tasks": n_maps * tasks_per_map,
        "epsilon_certified_tasks": int(sum(r["certified_tasks"] for r in rows)),
        "bound_violations": int(sum(r["bound_violations"] for r in rows)),
        "mean_discrete_model_regret": float(np.mean([r["mean_discrete_regret"] for r in rows])),
        "root_first_action_agreement_with_exact_macro": float(np.mean([r["mean_root_match"] for r in rows])),
        "mean_rollout_mc_standard_error": float(np.mean([r["mean_mc_se"] for r in rows])),
        "per_arm_execution_diagnostics": {
            ak: {
                mk: float(np.mean([r["arm_summary"][ak][mk] for r in rows]))
                for mk in ("cost", "completion", "timeout", "clip")
            }
            for ak in rows[0]["arm_summary"].keys()
        },
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
        "per_map_records": rows,
    }


# ==============================================================================
# Exp 4B: Orthogonal Transition Stream + Warm/Cold Cache Net-Benefit Crossover
# ==============================================================================
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


def _cache_crossover_worker(args: Tuple[int, int]) -> dict:
    """Work Package C: Crosses `Cache Warmth` (`Warm-All-WPs` vs `Cold-Unseen-WPs`) x `Operator Scale`
    (`2D 61^2` vs `3D 21^3`) under a mild local GP update (`K = 6` post-update tasks/map), charging
    the FULL post-update lifecycle time `T_update + T_deferred_LU_cols + T_DP + T_occ + T_router`!
    """
    idx_m, ms = args
    methods = ["Scratch-Rebuild", "Structure-Memory-Fresh-Exact", "Residual-Audited-Reuse", "ExactRing-Rebuild"]
    rng_ord = np.random.default_rng(ms + 707)
    out_regimes = {}

    for reg_name, dim, gn, warm_all in [
        ("2D-61sq-ColdPartial", 2, 61, False),
        ("2D-61sq-WarmAll", 2, 61, True),
        ("3D-21cubed-ColdPartial", 3, 21, False),
        ("3D-21cubed-WarmAll", 3, 21, True),
    ]:
        world = generate_benchmark_map(ms, dim=dim, regime="narrow_barrier" if dim == 2 else "smooth", with_drift=True)
        rng = np.random.default_rng(ms + 111 * dim)
        r_wp = 0.28
        n_cat = 8 if warm_all else 12
        catalog_wps: List[GoalBall] = []
        for _ in range(n_cat):
            for _att in range(250):
                pt = rng.uniform(-1.15, 1.15, size=dim)
                if dim == 3:
                    pt[2] *= 0.65
                if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.05 * r_wp for w in catalog_wps):
                    catalog_wps.append(GoalBall(tuple(pt.tolist()), phi=0.0, radius=r_wp))
                    break

        X1, q1, b1 = sample_noisy_probes(world, n_probes=70 if dim == 2 else 85, seed=ms + 9, include_drift=True)
        km1 = KrigingWorldModel(X1, q1, b1)
        bump_c = np.full((1, dim), 1.32)
        q2_fn = lambda X, k=km1, bc=bump_c: k.predict_q(X) + 0.18 * np.exp(-np.sum((X - bc) ** 2, axis=1) / 0.04)

        planners = {}
        for m in methods:
            init_lv = "EXACT" if m == "ExactRing-Rebuild" else "L1"
            pl = SchurPortPlanner(world.spec, gn, km1.predict_q, km1.predict_b, catalog_wps, initial_sectors_per_wp=init_lv, lazy_init=True)
            mt0 = MacroTourPlanner(pl)
            if warm_all:
                # Warm up ALL catalog waypoints on pre-update tasks so no unseen waypoints remain!
                for w_start in (0, 3):
                    sub_w = tuple(range(w_start, min(w_start + 5, len(catalog_wps))))
                    s_w = np.full(dim, -1.25)
                    if m == "ExactRing-Rebuild":
                        mt0.plan_exact_subset_dp(s_w, sub_w)
                    else:
                        mt0.plan_subset_macro_policy(s_w, sub_w, epsilon_tol=0.25, max_refine_steps=10)
            else:
                # Warm up only half the catalog (`0..4`), leaving `5..11` cold/unvisited!
                s_w = np.full(dim, -1.25)
                if m == "ExactRing-Rebuild":
                    mt0.plan_exact_subset_dp(s_w, (0, 1, 2, 3, 4))
                else:
                    mt0.plan_subset_macro_policy(s_w, (0, 1, 2, 3, 4), epsilon_tol=0.25, max_refine_steps=10)
            planners[m] = pl

        post_tasks = []
        for _tk in range(6):
            sub_ids = tuple(rng.choice(len(catalog_wps), size=5, replace=False).tolist())
            s_xy = np.full(dim, -1.28)
            for _att in range(120):
                cand = rng.uniform(-1.22, 1.22, size=dim)
                if all(np.linalg.norm(cand - np.asarray(catalog_wps[j].center)) > r_wp + 0.14 for j in sub_ids):
                    s_xy = cand
                    break
            post_tasks.append((s_xy, sub_ids))

        lu_before = {m: planners[m].lu_factorizations for m in methods}
        bs_before = {m: planners[m].total_lu_backsolves for m in methods}
        stats_r = {
            m: {"update_ms": 0.0, "col_solve_ms": 0.0, "dp_ms": 0.0, "total_lifecycle_ms": 0.0, "cert": 0, "viols": 0}
            for m in methods
        }

        for m in rng_ord.permutation(methods).tolist():
            mode_u = (
                "scratch_rebuild" if m in ("Scratch-Rebuild", "ExactRing-Rebuild")
                else ("structure_only_fresh_exact" if m == "Structure-Memory-Fresh-Exact" else "selective_residual")
            )
            u_inf = planners[m].update_world_with_residual_audit(q2_fn, km1.predict_b, mode=mode_u)
            stats_r[m]["update_ms"] += u_inf["update_ms"]
            stats_r[m]["total_lifecycle_ms"] += u_inf["update_ms"]

        pl_ref = SchurPortPlanner(world.spec, gn, q2_fn, km1.predict_b, catalog_wps, initial_sectors_per_wp="EXACT", lazy_init=True)
        for s_xy, sub_ids in post_tasks:
            for m in rng_ord.permutation(methods).tolist():
                mt_m = MacroTourPlanner(planners[m])
                if m == "ExactRing-Rebuild":
                    res_m = mt_m.plan_exact_subset_dp(s_xy, sub_ids)
                else:
                    res_m = mt_m.plan_subset_macro_policy(s_xy, sub_ids, epsilon_tol=0.25, max_refine_steps=12, use_incremental_dp=True)
                stats_r[m]["col_solve_ms"] += res_m.get("col_solve_ms", 0.0)
                stats_r[m]["dp_ms"] += res_m.get("dp_ms", 0.0)
                stats_r[m]["total_lifecycle_ms"] += res_m["planning_ms"]
                stats_r[m]["cert"] += int(res_m["certified"])
                ref_c = independent_exact_macro_bellman_reference(pl_ref, s_xy, sub_ids, policy_action_idx=res_m["policy_action_idx"])
                lo_c, hi_c = res_m["macro_value_bounds"]
                if not ((lo_c - 1e-9 <= ref_c["optimal_adaptive_macro_cost"] <= hi_c + 1e-9) and (ref_c["optimal_adaptive_macro_cost"] - 1e-9 <= ref_c["evaluated_policy_exact_macro_cost"] <= hi_c + 1e-9)):
                    stats_r[m]["viols"] += 1

        for m in methods:
            stats_r[m]["post_update_lus"] = int(planners[m].lu_factorizations - lu_before[m])
            stats_r[m]["post_update_backsolves"] = int(planners[m].total_lu_backsolves - bs_before[m])
        out_regimes[reg_name] = stats_r

    return {"map_seed": ms, "regimes": out_regimes}


def run_orthogonal_operator_transition_stream(n_maps: int = 10, grid_n: int = 61, max_workers: int = 8) -> dict:
    map_seeds = list(range(9950, 9950 + n_maps))
    rows = run_map_parallel(_orthogonal_reuse_map_worker, [(i, s, grid_n) for i, s in enumerate(map_seeds)], max_workers=max_workers)
    modes = ["Scratch-Rebuild", "Structure-Memory-Fresh-Exact", "Residual-Audited-Reuse", "Blind-Stale-Cache"]
    scr_ep4 = np.array([r["ep_cum"]["Scratch-Rebuild"]["epoch_4"] for r in rows])
    str_ep4 = np.array([r["ep_cum"]["Structure-Memory-Fresh-Exact"]["epoch_4"] for r in rows])

    out_m = {}
    for m in modes:
        m_ep4 = np.array([r["ep_cum"][m]["epoch_4"] for r in rows])
        out_m[m] = {
            "cumulative_ms_by_epoch": {
                f"epoch_{e}": float(np.mean([r["ep_cum"][m][f"epoch_{e}"] for r in rows])) for e in range(1, 5)
            },
            "speedup_at_epoch4_vs_scratch": float(np.mean(scr_ep4) / np.mean(m_ep4)),
            "paired_epoch4_ms_diff_vs_scratch": paired_stats(m_ep4 - scr_ep4),
            "paired_epoch4_ms_diff_vs_structure_only": paired_stats(m_ep4 - str_ep4),
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
            "per_map_epoch4_ms": m_ep4.tolist(),
        }

    # Run Work Package C 2x2 Cache Warmth x Scale Crossover (`8` fresh maps `10200..10207`)
    cross_seeds = list(range(10200, 10208))
    cross_rows = run_map_parallel(_cache_crossover_worker, [(i, s) for i, s in enumerate(cross_seeds)], max_workers=max_workers)
    cross_summary = {}
    for reg_name in cross_rows[0]["regimes"].keys():
        str_arr = np.array([r["regimes"][reg_name]["Structure-Memory-Fresh-Exact"]["total_lifecycle_ms"] for r in cross_rows])
        ex_arr = np.array([r["regimes"][reg_name]["ExactRing-Rebuild"]["total_lifecycle_ms"] for r in cross_rows])
        reg_m = {}
        for m in ("Scratch-Rebuild", "Structure-Memory-Fresh-Exact", "Residual-Audited-Reuse", "ExactRing-Rebuild"):
            m_arr = np.array([r["regimes"][reg_name][m]["total_lifecycle_ms"] for r in cross_rows])
            reg_m[m] = {
                "mean_total_lifecycle_ms": float(np.mean(m_arr)),
                "mean_update_ms": float(np.mean([r["regimes"][reg_name][m]["update_ms"] for r in cross_rows])),
                "mean_deferred_col_solve_ms": float(np.mean([r["regimes"][reg_name][m]["col_solve_ms"] for r in cross_rows])),
                "mean_dp_ms": float(np.mean([r["regimes"][reg_name][m]["dp_ms"] for r in cross_rows])),
                "mean_post_update_lus": float(np.mean([r["regimes"][reg_name][m]["post_update_lus"] for r in cross_rows])),
                "mean_post_update_backsolves": float(np.mean([r["regimes"][reg_name][m]["post_update_backsolves"] for r in cross_rows])),
                "certified_tasks_of_48": int(sum(r["regimes"][reg_name][m]["cert"] for r in cross_rows)),
                "bound_violations_of_48": int(sum(r["regimes"][reg_name][m]["viols"] for r in cross_rows)),
                "speedup_vs_structure_only": float(np.mean(str_arr) / np.mean(m_arr)),
                "paired_ms_diff_vs_structure_only": paired_stats(m_arr - str_arr),
                "paired_ms_diff_vs_exact_rebuild": paired_stats(m_arr - ex_arr),
                "per_map_total_lifecycle_ms": m_arr.tolist(),
            }
        cross_summary[reg_name] = reg_m

    return {
        "block_provenance": "fresh_computed_in_current_run",
        "experiment_scope": "externally_supplied_operator_transitions_orthogonal_structure_vs_value_reuse",
        "benchmark_seeds": map_seeds,
        "grid_n": grid_n,
        "epochs": 4,
        "tasks_per_epoch_per_map": 5,
        "total_tasks_evaluated": n_maps * 20,
        "methods": out_m,
        "per_map_records": rows,
        "synthetic_local_bump_crossover_8maps": {
            "perturbation_type": "deterministic_corner_gaussian_bump_no_gp_refit (0.18 * exp(-||X - 1.32||^2 / 0.04))",
            "scope_note": "Controlled post-update operator perturbation stress test; WarmAll uses n_cat=8 vs ColdPartial n_cat=12.",
            "fresh_seeds": cross_seeds,
            "post_update_tasks_per_map": 6,
            "regimes": cross_summary,
            "per_map_records": cross_rows,
        },
    }


def _real_gp_update_lifecycle_worker(args: Tuple[int, int]) -> dict:
    """`29fa7c6 Stage B2` — Genuine `+16` Physical-Observation GP Posterior Update Lifecycle:
    Fixes a SINGLE `12`-waypoint catalog, initial physical observations `(X_old, q_old, b_old) -> km1`,
    `+16` newly acquired noisy physical observations `(X_add, q_add, b_add) -> km2` (refitted GP!),
    and an IDENTICAL post-update `K = 12` future tour stream (`K in {1, 4, 12}` cumulative slices).
    `ColdPrefix` (`2` warmup tasks on `0..4`) vs `WarmPrefix` (`6` warmup tasks covering `0..11`)
    isolates cache warmth strictly as a single factor, recording BOTH:
      1. `post_update_marginal_ms[K] = T_gp2 + T_update + T_post_queries(K)` (given existing pre-update cache);
      2. `from_zero_full_lifecycle_ms[K] = T_gp1 + T_init + T_warmup + T_gp2 + T_update + T_post_queries(K)`!
    """
    import hashlib
    idx_m, ms = args
    methods = ["Scratch-Rebuild", "Structure-Memory-Fresh-Exact", "Residual-Audited-Reuse", "ExactRing-Rebuild"]
    rng_ord = np.random.default_rng(ms + 818)
    out_dims = {}

    for dim_label, dim, gn, n_init_obs in [
        ("2D-61sq", 2, 61, 64),
        ("3D-21cubed", 3, 21, 80),
    ]:
        world = generate_benchmark_map(ms, dim=dim, regime="narrow_barrier" if dim == 2 else "smooth", with_drift=True)
        rng_cat = np.random.default_rng(ms + 222 * dim)
        r_wp = 0.28
        catalog_wps: List[GoalBall] = []
        for _ in range(12):
            for _att in range(250):
                pt = rng_cat.uniform(-1.15, 1.15, size=dim)
                if dim == 3:
                    pt[2] *= 0.65
                if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.02 * r_wp for w in catalog_wps):
                    catalog_wps.append(GoalBall(tuple(pt.tolist()), phi=0.0, radius=r_wp))
                    break

        # 1. Initial world GP `km1`
        X_old, q_old, b_old = sample_noisy_probes(world, n_probes=n_init_obs, seed=ms + 11 * dim, include_drift=True)
        t_gp1_0 = time.perf_counter()
        km1 = KrigingWorldModel(X_old, q_old, b_old)
        t_gp1_ms = 1000.0 * (time.perf_counter() - t_gp1_0)

        # 2. Select `16` real conditional max-variance coordinates & observe noisy `(q_add, b_add)` from `world`, then refit `km2`!
        sob_grid = np.random.default_rng(ms + 333 * dim).uniform(-1.45, 1.45, size=(512, dim))
        X_add = km1.select_sequential_conditional_maxvar_probes(sob_grid, X_old, 16, min_repel=0.25)
        obs_rng = np.random.default_rng(np.random.SeedSequence([ms, dim, 9901]))
        X_add, q_add, b_add = observe_world_at_points(world, X_add, obs_rng, include_drift=True)
        X_new = np.vstack([X_old, X_add])
        q_new = np.concatenate([q_old, q_add])
        b_new = np.vstack([b_old, b_add])

        t_gp2_0 = time.perf_counter()
        km2 = KrigingWorldModel(X_new, q_new, b_new)
        t_gp2_ms = 1000.0 * (time.perf_counter() - t_gp2_0)

        # Operator change diagnostics on grid
        pl_ref2 = SchurPortPlanner(world.spec, gn, km2.predict_q, km2.predict_b, catalog_wps, initial_sectors_per_wp="EXACT", lazy_init=True)
        dq_linf = float(np.max(np.abs(km2.predict_q(pl_ref2.pts) - km1.predict_q(pl_ref2.pts))))
        db_linf = float(np.max(np.abs(km2.predict_b(pl_ref2.pts) - km1.predict_b(pl_ref2.pts))))
        x_add_sha = hashlib.sha256(np.round(X_add, 10).tobytes()).hexdigest()[:16]

        # Fixed shared `K = 12` post-update future task stream (identical across ColdPrefix and WarmPrefix!)
        rng_tasks = np.random.default_rng(ms + 444 * dim)
        post_tasks = []
        for _tk in range(12):
            sub_ids = tuple(rng_tasks.choice(len(catalog_wps), size=5, replace=False).tolist())
            s_xy = np.full(dim, -1.28)
            for _att in range(120):
                cand = rng_tasks.uniform(-1.22, 1.22, size=dim)
                if all(np.linalg.norm(cand - np.asarray(catalog_wps[j].center)) > r_wp + 0.14 for j in sub_ids):
                    s_xy = cand
                    break
            post_tasks.append((s_xy, sub_ids))

        warmup_cold = [
            (np.full(dim, -1.25), (0, 1, 2, 3, 4)),
            (np.full(dim, 1.25), (0, 1, 2, 3, 4)),
        ]
        warmup_warm = [
            (np.full(dim, -1.25), (0, 1, 2, 3, 4)),
            (np.full(dim, 1.25), (3, 4, 5, 6, 7)),
            (np.array([-1.20, 1.20] + ([0.0] if dim == 3 else [])), (7, 8, 9, 10, 11)),
            (np.array([1.20, -1.20] + ([0.0] if dim == 3 else [])), (0, 2, 5, 8, 11)),
            (np.zeros(dim, dtype=float), (1, 4, 6, 9, 10)),
            (np.full(dim, -0.95), (2, 3, 6, 7, 11)),
        ]

        for prefix_name, warm_tasks in [("ColdPrefix", warmup_cold), ("WarmPrefix", warmup_warm)]:
            reg_key = f"{dim_label}-{prefix_name}"
            planners = {}
            st_m = {
                m: {
                    "gp1_ms": t_gp1_ms,
                    "init_ms": 0.0,
                    "warmup_ms": 0.0,
                    "gp2_ms": t_gp2_ms,
                    "update_ms": 0.0,
                    "col_solve_ms_by_K": {},
                    "dp_ms_by_K": {},
                    "post_queries_ms_by_K": {},
                    "post_update_marginal_ms_by_K": {},
                    "from_zero_full_lifecycle_ms_by_K": {},
                    "post_update_lus": 0,
                    "post_update_backsolves": 0,
                    "cols_retained": 0,
                    "cert_of_12": 0,
                    "viols_of_12": 0,
                }
                for m in methods
            }

            for m in rng_ord.permutation(methods).tolist():
                init_lv = "EXACT" if m == "ExactRing-Rebuild" else "L1"
                t_i0 = time.perf_counter()
                pl = SchurPortPlanner(world.spec, gn, km1.predict_q, km1.predict_b, catalog_wps, initial_sectors_per_wp=init_lv, lazy_init=True)
                st_m[m]["init_ms"] = 1000.0 * (time.perf_counter() - t_i0)
                mt0 = MacroTourPlanner(pl)
                t_w0 = time.perf_counter()
                for s_w, sub_w in warm_tasks:
                    if m == "ExactRing-Rebuild":
                        mt0.plan_exact_subset_dp(s_w, sub_w)
                    else:
                        mt0.plan_subset_macro_policy(s_w, sub_w, epsilon_tol=0.25, max_refine_steps=10, use_incremental_dp=True)
                st_m[m]["warmup_ms"] = 1000.0 * (time.perf_counter() - t_w0)
                planners[m] = pl

            lu_before = {m: planners[m].lu_factorizations for m in methods}
            bs_before = {m: planners[m].total_lu_backsolves for m in methods}

            for m in rng_ord.permutation(methods).tolist():
                mode_u = (
                    "scratch_rebuild" if m in ("Scratch-Rebuild", "ExactRing-Rebuild")
                    else ("structure_only_fresh_exact" if m == "Structure-Memory-Fresh-Exact" else "selective_residual")
                )
                u_inf = planners[m].update_world_with_residual_audit(km2.predict_q, km2.predict_b, mode=mode_u)
                st_m[m]["update_ms"] = float(u_inf["update_ms"])
                st_m[m]["cols_retained"] = int(u_inf.get("columns_retained", 0))

            cum_q = {m: 0.0 for m in methods}
            cum_col = {m: 0.0 for m in methods}
            cum_dp = {m: 0.0 for m in methods}
            for k_idx, (s_xy, sub_ids) in enumerate(post_tasks, start=1):
                for m in rng_ord.permutation(methods).tolist():
                    mt_m = MacroTourPlanner(planners[m])
                    if m == "ExactRing-Rebuild":
                        res_m = mt_m.plan_exact_subset_dp(s_xy, sub_ids)
                    else:
                        res_m = mt_m.plan_subset_macro_policy(s_xy, sub_ids, epsilon_tol=0.25, max_refine_steps=12, use_incremental_dp=True)
                    cum_q[m] += float(res_m["planning_ms"])
                    cum_col[m] += float(res_m.get("col_solve_ms", 0.0))
                    cum_dp[m] += float(res_m.get("dp_ms", 0.0))
                    st_m[m]["cert_of_12"] += int(res_m["certified"])
                    ref_c = independent_exact_macro_bellman_reference(pl_ref2, s_xy, sub_ids, policy_action_idx=res_m["policy_action_idx"])
                    lo_c, hi_c = res_m["macro_value_bounds"]
                    if not ((lo_c - 1e-9 <= ref_c["optimal_adaptive_macro_cost"] <= hi_c + 1e-9) and (ref_c["optimal_adaptive_macro_cost"] - 1e-9 <= ref_c["evaluated_policy_exact_macro_cost"] <= hi_c + 1e-9)):
                        st_m[m]["viols_of_12"] += 1

                if k_idx in (1, 4, 12):
                    ks = f"K_{k_idx}"
                    for m in methods:
                        st_m[m]["col_solve_ms_by_K"][ks] = cum_col[m]
                        st_m[m]["dp_ms_by_K"][ks] = cum_dp[m]
                        st_m[m]["post_queries_ms_by_K"][ks] = cum_q[m]
                        marg = st_m[m]["gp2_ms"] + st_m[m]["update_ms"] + cum_q[m]
                        full_z = st_m[m]["gp1_ms"] + st_m[m]["init_ms"] + st_m[m]["warmup_ms"] + marg
                        st_m[m]["post_update_marginal_ms_by_K"][ks] = marg
                        st_m[m]["from_zero_full_lifecycle_ms_by_K"][ks] = full_z

            for m in methods:
                st_m[m]["post_update_lus"] = int(planners[m].lu_factorizations - lu_before[m])
                st_m[m]["post_update_backsolves"] = int(planners[m].total_lu_backsolves - bs_before[m])

            out_dims[reg_key] = {
                "n_obs_old": int(len(X_old)),
                "n_obs_added_real": 16,
                "n_obs_new": int(len(X_new)),
                "added_probes_sha256_16": x_add_sha,
                "dq_linf_grid": dq_linf,
                "db_linf_grid": db_linf,
                "methods": st_m,
            }

    return {"map_seed": ms, "regimes": out_dims}


def run_real_gp_update_lifecycle_benchmark(n_maps: int = 12, max_workers: int = 8) -> dict:
    seeds = list(range(10250, 10250 + n_maps))
    rows = run_map_parallel(_real_gp_update_lifecycle_worker, [(i, s) for i, s in enumerate(seeds)], max_workers=max_workers)
    methods = ["Scratch-Rebuild", "Structure-Memory-Fresh-Exact", "Residual-Audited-Reuse", "ExactRing-Rebuild"]
    regimes_out = {}
    for rk in rows[0]["regimes"].keys():
        str_m12 = np.array([r["regimes"][rk]["methods"]["Structure-Memory-Fresh-Exact"]["post_update_marginal_ms_by_K"]["K_12"] for r in rows])
        ex_m12 = np.array([r["regimes"][rk]["methods"]["ExactRing-Rebuild"]["post_update_marginal_ms_by_K"]["K_12"] for r in rows])
        str_z12 = np.array([r["regimes"][rk]["methods"]["Structure-Memory-Fresh-Exact"]["from_zero_full_lifecycle_ms_by_K"]["K_12"] for r in rows])
        ex_z12 = np.array([r["regimes"][rk]["methods"]["ExactRing-Rebuild"]["from_zero_full_lifecycle_ms_by_K"]["K_12"] for r in rows])

        m_sum = {}
        for m in methods:
            m_marg12 = np.array([r["regimes"][rk]["methods"][m]["post_update_marginal_ms_by_K"]["K_12"] for r in rows])
            m_zero12 = np.array([r["regimes"][rk]["methods"][m]["from_zero_full_lifecycle_ms_by_K"]["K_12"] for r in rows])
            m_sum[m] = {
                "mean_gp1_ms": float(np.mean([r["regimes"][rk]["methods"][m]["gp1_ms"] for r in rows])),
                "mean_init_ms": float(np.mean([r["regimes"][rk]["methods"][m]["init_ms"] for r in rows])),
                "mean_warmup_ms": float(np.mean([r["regimes"][rk]["methods"][m]["warmup_ms"] for r in rows])),
                "mean_gp2_refit_ms": float(np.mean([r["regimes"][rk]["methods"][m]["gp2_ms"] for r in rows])),
                "mean_update_ms": float(np.mean([r["regimes"][rk]["methods"][m]["update_ms"] for r in rows])),
                "post_update_marginal_ms_by_K": {
                    ks: float(np.mean([r["regimes"][rk]["methods"][m]["post_update_marginal_ms_by_K"][ks] for r in rows]))
                    for ks in ("K_1", "K_4", "K_12")
                },
                "from_zero_full_lifecycle_ms_by_K": {
                    ks: float(np.mean([r["regimes"][rk]["methods"][m]["from_zero_full_lifecycle_ms_by_K"][ks] for r in rows]))
                    for ks in ("K_1", "K_4", "K_12")
                },
                "col_solve_ms_at_K12": float(np.mean([r["regimes"][rk]["methods"][m]["col_solve_ms_by_K"]["K_12"] for r in rows])),
                "dp_ms_at_K12": float(np.mean([r["regimes"][rk]["methods"][m]["dp_ms_by_K"]["K_12"] for r in rows])),
                "mean_post_update_lus": float(np.mean([r["regimes"][rk]["methods"][m]["post_update_lus"] for r in rows])),
                "mean_post_update_backsolves": float(np.mean([r["regimes"][rk]["methods"][m]["post_update_backsolves"] for r in rows])),
                "mean_cols_retained": float(np.mean([r["regimes"][rk]["methods"][m]["cols_retained"] for r in rows])),
                "certified_tasks_of_144": int(sum(r["regimes"][rk]["methods"][m]["cert_of_12"] for r in rows)),
                "bound_violations_of_144": int(sum(r["regimes"][rk]["methods"][m]["viols_of_12"] for r in rows)),
                "paired_marginal_K12_diff_vs_structure_only": paired_stats(m_marg12 - str_m12),
                "paired_marginal_K12_diff_vs_exact_rebuild": paired_stats(m_marg12 - ex_m12),
                "paired_from_zero_K12_diff_vs_structure_only": paired_stats(m_zero12 - str_z12),
                "paired_from_zero_K12_diff_vs_exact_rebuild": paired_stats(m_zero12 - ex_z12),
            }
        regimes_out[rk] = {
            "mean_dq_linf_after_16_real_obs": float(np.mean([r["regimes"][rk]["dq_linf_grid"] for r in rows])),
            "mean_db_linf_after_16_real_obs": float(np.mean([r["regimes"][rk]["db_linf_grid"] for r in rows])),
            "methods": m_sum,
        }

    return {
        "block_provenance": "fresh_computed_in_current_run",
        "experiment_scope": "genuine_16_real_world_observations_and_gp_refit_single_factor_warm_vs_cold_lifecycle",
        "fresh_seeds": seeds,
        "n_maps": n_maps,
        "catalog_waypoints_fixed": 12,
        "post_update_horizons": [1, 4, 12],
        "regimes": regimes_out,
        "per_map_records": rows,
    }


# ==============================================================================
# Exp 4C: Unconfounded 5-Arm Online World-Model Learning & Held-Out Transfer
# ==============================================================================
def _select_active_probes_diverse(
    cand_pts: np.ndarray, scores: np.ndarray, existing_X: np.ndarray, n_select: int, min_repel: float = 0.24
) -> np.ndarray:
    """Greedy diversity-regularized coordinate selection using ONLY posterior/planner quantities."""
    chosen = []
    cur_X = existing_X.copy()
    rem_mask = np.ones(len(cand_pts), dtype=bool)
    for _ in range(n_select):
        if not np.any(rem_mask):
            break
        d_min = np.min(np.linalg.norm(cand_pts[:, None, :] - cur_X[None, :, :], axis=2), axis=1)
        eff_score = np.where(rem_mask, scores * np.minimum(1.0, (d_min / min_repel) ** 2), -np.inf)
        best_i = int(np.argmax(eff_score))
        rem_mask[best_i] = False
        pt = cand_pts[best_i]
        chosen.append(pt)
        cur_X = np.vstack([cur_X, pt[None, :]])
    return np.array(chosen)


def _unconfounded_learning_map_worker(args: Tuple[int, int, int]) -> dict:
    """Work Package B (`16` Brand-New Locked Maps `10100..10115`):
    ALL 5 arms share the EXACT SAME `ExactRing + Subset-DP` planner, same `ClassicalFDSolver` leg
    controllers, same initial `28` observations (`0.0` Ep-1 discrepancy!), same `+14` probe budget,
    and same `min_repel = 0.24`, evaluated at every checkpoint on a FIXED HELD-OUT FUTURE TASK BANK
    (`6` disjoint `m = 5` tours/map with coupled CRN noise, never seen by any acquisition rule!).
    """
    idx_m, ms, grid_n = args
    world = generate_benchmark_map(ms, dim=2, regime="narrow_barrier", with_drift=True)
    rng = np.random.default_rng(ms + 211)
    r_wp = 0.26
    catalog_wps: List[GoalBall] = []
    for _ in range(10):
        for _att in range(250):
            pt = rng.uniform(-1.22, 1.22, size=2)
            if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.05 * r_wp for w in catalog_wps):
                catalog_wps.append(GoalBall(tuple(pt.tolist()), phi=0.0, radius=r_wp))
                break

    def _sample_tour_task(seed_val: int) -> Tuple[np.ndarray, Tuple[int, ...], int]:
        sub_ids = tuple(rng.choice(len(catalog_wps), size=5, replace=False).tolist())
        start_xy = np.array([-1.30, -1.30])
        for _att in range(150):
            cand = rng.uniform(-1.25, 1.25, size=2)
            if all(np.linalg.norm(cand - np.asarray(catalog_wps[j].center)) > r_wp + 0.15 for j in sub_ids):
                start_xy = cand
                break
        return start_xy, sub_ids, seed_val

    # 1. Online execution task stream (`5` acquisition episodes x `3` tasks/ep; Ep 6 is final eval checkpoint)
    online_stream = [
        [_sample_tour_task(51000 + 200 * idx_m + 20 * ep + tk) for tk in range(3)]
        for ep in range(6)
    ]
    # 2. Strictly disjoint FIXED HELD-OUT FUTURE EVALUATION BANK (`6` tasks/map, pregenerated CRN noise!)
    heldout_bank = []
    for hk in range(6):
        s_h, sub_h, sd_h = _sample_tour_task(61000 + 200 * idx_m + hk)
        _, dW_c_h = _generate_coupled_wiener_bank(sd_h, n_tr=16, m_legs=5, fine_steps_per_leg=1260, dt_fine=0.005)
        heldout_bank.append((s_h, sub_h, dW_c_h))

    X_init, q_init, b_init = sample_noisy_probes(world, n_probes=28, seed=ms + 7, include_drift=True)

    gx = np.linspace(-1.48, 1.48, 25)
    gxx, gyy = np.meshgrid(gx, gx, indexing="ij")
    cand_pool = np.column_stack([gxx.ravel(), gyy.ravel()])
    min_repel = 0.24

    arms = [
        "Frozen-GP-28",
        "Uniform-Random",
        "Global-MaxVariance",
        "True-OnPolicy-Trajectory",
        "Green-Frechet-Active",
    ]
    arm_out = {}

    # Evaluate shared Episode-1 model ONCE to guarantee exact `0.0` Ep-1 starting identity across all 5 arms
    # (and verify that executing from `X_init` produces identical Ep-1 checkpoint values!).
    for arm in arms:
        X_cur = X_init.copy()
        q_cur = q_init.copy()
        b_cur = b_init.copy()
        # Use identical sensor RNG advancement per episode across active arms for channel parity
        rng_acq = np.random.default_rng(ms + 900 + arms.index(arm) * 41)

        heldout_cost_ep = []
        heldout_comp_ep = []
        heldout_timeout_ep = []
        heldout_clip_ep = []
        online_cost_ep = []
        online_comp_ep = []
        acq_ms_ep = []
        gp_plan_ms_ep = []
        all_onpolicy_from_logged_states = True

        cached_frozen = None

        for ep in range(6):
            if arm == "Frozen-GP-28" and cached_frozen is not None:
                km_t, pl_plan, mt_plan, leg_pols, gp_p_ms = cached_frozen
                gp_plan_ms_ep.append(0.0)
            else:
                t_gp0 = time.perf_counter()
                km_t = KrigingWorldModel(X_cur, q_cur, b_cur)
                pl_plan = SchurPortPlanner(
                    world.spec, grid_n, km_t.predict_q, km_t.predict_b, catalog_wps,
                    initial_sectors_per_wp="EXACT", lazy_init=True,
                )
                mt_plan = MacroTourPlanner(pl_plan)
                exec_fd = ClassicalFDSolver(world.spec, grid_n, km_t.predict_q, km_t.predict_b)
                leg_pols = {
                    j: exec_fd.solve_direct(QueryTask(f"l_{j}", (w,), ((0.0, 0.0),)))["policy"]
                    for j, w in enumerate(catalog_wps)
                }
                gp_p_ms = 1000.0 * (time.perf_counter() - t_gp0)
                gp_plan_ms_ep.append(gp_p_ms)
                if arm == "Frozen-GP-28":
                    cached_frozen = (km_t, pl_plan, mt_plan, leg_pols, gp_p_ms)

            # A. Evaluate on FIXED HELD-OUT FUTURE TASK BANK (never used for acquisition!)
            h_costs, h_comps, h_tos, h_clips = [], [], [], []
            for s_h, sub_h, dW_c_h in heldout_bank:
                t_p0 = time.perf_counter()
                res_h = mt_plan.plan_exact_subset_dp(s_h, sub_h)
                gp_plan_ms_ep[-1] += 1000.0 * (time.perf_counter() - t_p0)
                sim_h = _simulate_adaptive_tour_coupled(
                    world, catalog_wps, leg_pols, s_h, sub_h, res_h["select_next_waypoint"],
                    dW_c_h, dt_sim=0.015, fractional_segment_hit=True, record_visited_states=False,
                )
                h_costs.append(sim_h["mean_cost"])
                h_comps.append(sim_h["completion_rate"])
                h_tos.append(sim_h["timeout_frac"])
                h_clips.append(sim_h["clip_frac"])

            heldout_cost_ep.append(float(np.mean(h_costs)))
            heldout_comp_ep.append(float(np.mean(h_comps)))
            heldout_timeout_ep.append(float(np.mean(h_tos)))
            heldout_clip_ep.append(float(np.mean(h_clips)))

            # B. Execute ONLINE STREAM tasks (records realized trajectory states for `True-OnPolicy-Trajectory`)
            o_costs, o_comps = [], []
            realized_states_ep: List[np.ndarray] = []
            need_states = (arm == "True-OnPolicy-Trajectory" and ep < 5)
            for s_o, sub_o, sd_o in online_stream[ep]:
                res_o = mt_plan.plan_exact_subset_dp(s_o, sub_o)
                _, dW_c_o = _generate_coupled_wiener_bank(sd_o, n_tr=12, m_legs=5, fine_steps_per_leg=1260, dt_fine=0.005)
                sim_o = _simulate_adaptive_tour_coupled(
                    world, catalog_wps, leg_pols, s_o, sub_o, res_o["select_next_waypoint"],
                    dW_c_o, dt_sim=0.015, fractional_segment_hit=True, record_visited_states=need_states,
                )
                o_costs.append(sim_o["mean_cost"])
                o_comps.append(sim_o["completion_rate"])
                if need_states and len(sim_o["visited_states"]) > 0:
                    realized_states_ep.append(sim_o["visited_states"])
            online_cost_ep.append(float(np.mean(o_costs)))
            online_comp_ep.append(float(np.mean(o_comps)))

            # C. Acquire `+14` noisy observations for Episode `ep + 1` (strictly causal!)
            if ep < 5:
                t_acq0 = time.perf_counter()
                n_add = 14
                if arm == "Frozen-GP-28":
                    acq_ms_ep.append(0.0)
                    continue
                elif arm == "Uniform-Random":
                    L_probe = world.spec.half_width - 0.12
                    X_new = rng_acq.uniform(-L_probe, L_probe, size=(n_add, 2))
                elif arm == "Global-MaxVariance":
                    _, lat_std_q, _ = km_t.predict_q_latent_std(cand_pool)
                    X_new = _select_active_probes_diverse(cand_pool, lat_std_q, X_cur, n_add, min_repel=min_repel)
                elif arm == "True-OnPolicy-Trajectory":
                    traj_cloud = np.vstack(realized_states_ep)
                    # Permute logged trajectory states deterministically, then diversity-subsample 14 ACTUAL visited states!
                    perm_idx = rng_acq.permutation(len(traj_cloud))
                    traj_perm = traj_cloud[perm_idx]
                    _, lat_std_tr, _ = km_t.predict_q_latent_std(traj_perm)
                    X_new = _select_active_probes_diverse(
                        traj_perm, 1.0 + lat_std_tr, X_cur, n_add, min_repel=min_repel
                    )
                    # Verify every selected coordinate is literally an element of `traj_cloud`!
                    cloud_set = {tuple(np.round(pt, 12)) for pt in traj_cloud}
                    if not all(tuple(np.round(pt, 12)) in cloud_set for pt in X_new):
                        all_onpolicy_from_logged_states = False
                elif arm == "Green-Frechet-Active":
                    # Target-permutation-invariant discrete Green adjoint sensitivity on ONLINE tasks ONLY:
                    vr_total = np.zeros(len(cand_pool), dtype=float)
                    for s_o, sub_o, _ in online_stream[ep]:
                        sens = mt_plan.compute_exact_macro_q_sensitivities(s_o, sub_o)
                        g_opt = sens["grad_q_optimal"]
                        bif_w = float(np.exp(-max(0.0, sens["action_gap"]) / 0.60))
                        g_gap = bif_w * sens["grad_q_top_gap"]
                        vr_mat = km_t.project_q_linear_functional_variance_reduction(
                            cand_pool, pl_plan.pts, np.column_stack([g_opt, g_gap])
                        )
                        vr_total += vr_mat[:, 0] + 1.5 * vr_mat[:, 1]
                    # Explicit hard quota: `11` Green-Frechet decision probes + `3` Global-MaxVariance sentinel probes!
                    X_dec = _select_active_probes_diverse(cand_pool, vr_total, X_cur, 11, min_repel=min_repel)
                    _, lat_std_q, _ = km_t.predict_q_latent_std(cand_pool)
                    X_sen = _select_active_probes_diverse(
                        cand_pool, lat_std_q, np.vstack([X_cur, X_dec]), 3, min_repel=min_repel
                    )
                    X_new = np.vstack([X_dec, X_sen])
                else:
                    raise ValueError(arm)

                acq_ms_ep.append(1000.0 * (time.perf_counter() - t_acq0))
                obs_rng = np.random.default_rng(np.random.SeedSequence([ms, ep, 8808]))
                Xn, qn, bn = observe_world_at_points(world, X_new, obs_rng, include_drift=True)
                X_cur = np.vstack([X_cur, Xn])
                q_cur = np.concatenate([q_cur, qn])
                b_cur = np.vstack([b_cur, bn])

        arm_out[arm] = {
            "heldout_cost_by_ep": heldout_cost_ep,
            "heldout_post_acq_ep2_6_mean_cost": float(np.mean(heldout_cost_ep[1:])),
            "heldout_final_ep6_cost": float(heldout_cost_ep[-1]),
            "heldout_completion_by_ep": heldout_comp_ep,
            "heldout_post_acq_completion_rate": float(np.mean(heldout_comp_ep[1:])),
            "heldout_mean_timeout_frac": float(np.mean(heldout_timeout_ep)),
            "heldout_mean_clip_frac": float(np.mean(heldout_clip_ep)),
            "online_stream_cost_by_ep": online_cost_ep,
            "online_post_acq_ep2_6_mean_cost": float(np.mean(online_cost_ep[1:])),
            "online_completion_rate": float(np.mean(online_comp_ep)),
            "mean_acquisition_ms": float(np.sum(acq_ms_ep)),
            "mean_gp_plus_exact_plan_ms": float(np.sum(gp_plan_ms_ep)),
            "all_onpolicy_probes_verified_visited_states": bool(all_onpolicy_from_logged_states),
        }

    return {"map_seed": ms, "arms": arm_out}


def run_unconfounded_online_learning_and_transfer(n_maps: int = 16, grid_n: int = 55, max_workers: int = 8) -> dict:
    fresh_seeds = list(range(10100, 10100 + n_maps))
    rows = run_map_parallel(
        _unconfounded_learning_map_worker, [(i, s, grid_n) for i, s in enumerate(fresh_seeds)], max_workers=max_workers
    )
    arms = [
        "Frozen-GP-28",
        "Uniform-Random",
        "Global-MaxVariance",
        "True-OnPolicy-Trajectory",
        "Green-Frechet-Active",
    ]
    gf_post = np.array([r["arms"]["Green-Frechet-Active"]["heldout_post_acq_ep2_6_mean_cost"] for r in rows])
    gf_ep6 = np.array([r["arms"]["Green-Frechet-Active"]["heldout_final_ep6_cost"] for r in rows])
    gf_onl = np.array([r["arms"]["Green-Frechet-Active"]["online_post_acq_ep2_6_mean_cost"] for r in rows])
    frz_post = np.array([r["arms"]["Frozen-GP-28"]["heldout_post_acq_ep2_6_mean_cost"] for r in rows])

    ep1_vals = {
        a: float(np.mean([r["arms"][a]["heldout_cost_by_ep"][0] for r in rows])) for a in arms
    }
    ep1_max_spread = float(max(ep1_vals.values()) - min(ep1_vals.values()))

    summary_arms = {}
    for a in arms:
        a_post = np.array([r["arms"][a]["heldout_post_acq_ep2_6_mean_cost"] for r in rows])
        a_ep6 = np.array([r["arms"][a]["heldout_final_ep6_cost"] for r in rows])
        a_onl = np.array([r["arms"][a]["online_post_acq_ep2_6_mean_cost"] for r in rows])
        summary_arms[a] = {
            "heldout_mean_cost_by_episode": [
                float(np.mean([r["arms"][a]["heldout_cost_by_ep"][ep] for r in rows])) for ep in range(6)
            ],
            "heldout_completion_rate_by_episode": [
                float(np.mean([r["arms"][a]["heldout_completion_by_ep"][ep] for r in rows])) for ep in range(6)
            ],
            "primary_heldout_post_acq_ep2_6_mean_cost": float(np.mean(a_post)),
            "heldout_final_ep6_mean_cost": float(np.mean(a_ep6)),
            "heldout_post_acq_completion_rate": float(np.mean([r["arms"][a]["heldout_post_acq_completion_rate"] for r in rows])),
            "heldout_mean_timeout_frac": float(np.mean([r["arms"][a]["heldout_mean_timeout_frac"] for r in rows])),
            "heldout_mean_clip_frac": float(np.mean([r["arms"][a]["heldout_mean_clip_frac"] for r in rows])),
            "online_stream_mean_cost_by_episode": [
                float(np.mean([r["arms"][a]["online_stream_cost_by_ep"][ep] for r in rows])) for ep in range(6)
            ],
            "online_post_acq_ep2_6_mean_cost": float(np.mean(a_onl)),
            "online_completion_rate": float(np.mean([r["arms"][a]["online_completion_rate"] for r in rows])),
            "mean_cumulative_acquisition_ms": float(np.mean([r["arms"][a]["mean_acquisition_ms"] for r in rows])),
            "mean_cumulative_gp_plus_exact_plan_ms": float(np.mean([r["arms"][a]["mean_gp_plus_exact_plan_ms"] for r in rows])),
            "method_minus_frozen_gp_heldout_ep2_6": paired_stats(a_post - frz_post),
            "green_frechet_minus_method_heldout_ep2_6": paired_stats(gf_post - a_post),
            "green_frechet_minus_method_heldout_ep6": paired_stats(gf_ep6 - a_ep6),
            "green_frechet_minus_method_online_ep2_6": paired_stats(gf_onl - a_onl),
            "per_map_heldout_post_acq_ep2_6_cost": a_post.tolist(),
            "per_map_heldout_ep6_cost": a_ep6.tolist(),
        }

    onpol_verified = all(r["arms"]["True-OnPolicy-Trajectory"]["all_onpolicy_probes_verified_visited_states"] for r in rows)

    return {
        "block_provenance": "fresh_computed_in_current_run",
        "experiment_scope": "unconfounded_same_exact_planner_coordinate_query_vs_realized_onpolicy_heldout_transfer",
        "access_protocol": (
            "Coordinate-observation oracle (`q_noisy, b_noisy`) with equal `+14` probe budget/episode; "
            "True-OnPolicy-Trajectory restricts queries strictly to realized `(x_t)` states logged during "
            "online SDE execution; Green-Frechet-Active reserves 11 Green-sensitivity + 3 Global-MaxVariance probes."
        ),
        "new_confirmation_seeds": fresh_seeds,
        "n_maps": n_maps,
        "grid_n": grid_n,
        "unified_planner_backend": "ExactRing + Subset-DP (residual cache disabled across all 5 arms)",
        "repulsion_radius_shared": min_repel if (min_repel := 0.24) else 0.24,
        "probe_schedule": [28, 42, 56, 70, 84, 98],
        "episode1_max_cost_spread_across_all_5_arms": ep1_max_spread,
        "all_onpolicy_probes_verified_realized_rollout_states": bool(onpol_verified),
        "primary_estimand": "heldout_post_acq_ep2_6_mean_cost (paired across n=16 maps)",
        "predeclared_primary_contrasts": {
            "GreenFrechet_minus_TrueOnPolicy_heldout_ep2_6": summary_arms["True-OnPolicy-Trajectory"]["green_frechet_minus_method_heldout_ep2_6"],
            "GreenFrechet_minus_GlobalMaxVariance_heldout_ep2_6": summary_arms["Global-MaxVariance"]["green_frechet_minus_method_heldout_ep2_6"],
        },
        "arms": summary_arms,
        "per_map_records": rows,
    }


def _decisive_isolated_voi_map_worker(args: Tuple[int, int, str, int]) -> dict:
    """`29fa7c6 Stage C/D` — Strictly Isolated Operational-vs-Eval Online World-Model Learning:
      - `pl_operational` / `mt_operational` is NEVER touched by `heldout_bank` (`pl_eval` is a separate instance!);
      - Per-map arm execution order is randomized (`rng_arm_ord.permutation`) to eliminate cache/load order bias;
      - Compares 6 arms under identical `ExactRing + Subset-DP` and `min_repel = 0.24`:
          1. `Frozen-GP-28`
          2. `Global-CondMaxVar-14` (sequential Schur-complement conditional variance)
          3. `True-OnPolicy-14` (14 diversity-filtered realized `(x_t)` visited states)
          4. `True-OnPolicy-11+Sentinel-3` (11 realized `(x_t)` visited states + 3 conditioned global sentinels!)
          5. `Green-ValueOnly-Cond-11+3` (11 ReLU-masked `(q,b)` value-gradient conditional probes + 3 sentinels)
          6. `Green-KG-VoI-11+3` (11 ReLU-masked `(q,b)` multi-branch Knowledge-Gradient VoI conditional probes + 3 sentinels)
    """
    import hashlib
    idx_m, ms, regime_name, grid_n = args
    world = generate_benchmark_map(ms, dim=2, regime=regime_name, with_drift=True)
    rng = np.random.default_rng(ms + 211)
    r_wp = 0.25
    catalog_wps: List[GoalBall] = []
    if regime_name == "competing_corridor":
        # Place 5 waypoints on each side of the domain so multi-goal tours cross the twin-gate ridge repeatedly
        for side_idx in range(10):
            for _att in range(250):
                pt = rng.uniform(-1.24, 1.24, size=2)
                if side_idx < 5:
                    pt[0] = rng.uniform(-1.24, -0.42)
                else:
                    pt[0] = rng.uniform(0.42, 1.24)
                if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.04 * r_wp for w in catalog_wps):
                    catalog_wps.append(GoalBall(tuple(pt.tolist()), phi=0.0, radius=r_wp))
                    break
    else:
        for _ in range(10):
            for _att in range(250):
                pt = rng.uniform(-1.22, 1.22, size=2)
                if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.05 * r_wp for w in catalog_wps):
                    catalog_wps.append(GoalBall(tuple(pt.tolist()), phi=0.0, radius=r_wp))
                    break

    def _sample_tour_task(seed_val: int) -> Tuple[np.ndarray, Tuple[int, ...], int]:
        sub_ids = tuple(rng.choice(len(catalog_wps), size=5, replace=False).tolist())
        start_xy = np.array([-1.30, -1.30])
        for _att in range(150):
            cand = rng.uniform(-1.25, 1.25, size=2)
            if all(np.linalg.norm(cand - np.asarray(catalog_wps[j].center)) > r_wp + 0.15 for j in sub_ids):
                start_xy = cand
                break
        return start_xy, sub_ids, seed_val

    online_stream = [
        [_sample_tour_task(71000 + 200 * idx_m + 20 * ep + tk) for tk in range(3)]
        for ep in range(6)
    ]
    online_dW_bank = [
        [
            _generate_coupled_wiener_bank(sd_o, n_tr=10, m_legs=5, fine_steps_per_leg=1260, dt_fine=0.005)[1]
            for (_, _, sd_o) in online_stream[ep]
        ]
        for ep in range(6)
    ]
    heldout_bank = []
    for hk in range(6):
        s_h, sub_h, sd_h = _sample_tour_task(81000 + 200 * idx_m + hk)
        _, dW_c_h = _generate_coupled_wiener_bank(sd_h, n_tr=14, m_legs=5, fine_steps_per_leg=1260, dt_fine=0.005)
        heldout_bank.append((s_h, sub_h, dW_c_h))

    X_init, q_init, b_init = sample_noisy_probes(world, n_probes=28, seed=ms + 7, include_drift=True)
    gx = np.linspace(-1.48, 1.48, 25)
    gxx, gyy = np.meshgrid(gx, gx, indexing="ij")
    cand_pool = np.column_stack([gxx.ravel(), gyy.ravel()])
    min_repel = 0.24

    arms = [
        "Frozen-GP-28",
        "Global-CondMaxVar-14",
        "True-OnPolicy-14",
        "True-OnPolicy-11+Sentinel-3",
        "Green-ValueOnly-Cond-11+3",
        "Green-KG-VoI-11+3",
    ]
    rng_arm_ord = np.random.default_rng(ms + 606)
    arm_out = {}

    for arm in rng_arm_ord.permutation(arms).tolist():
        X_cur = X_init.copy()
        q_cur = q_init.copy()
        b_cur = b_init.copy()
        rng_acq = np.random.default_rng(ms + 900 + arms.index(arm) * 41)

        heldout_cost_ep, heldout_comp_ep, heldout_to_ep, heldout_clip_ep = [], [], [], []
        online_cost_ep, online_comp_ep = [], []
        op_gp_fit_ms_ep, op_online_plan_ms_ep, op_acq_ms_ep, eval_only_ms_ep = [], [], [], []
        probe_sha_ep = []
        root_gaps_logged = []
        relu_fracs_logged = []
        all_onpolicy_verified = True
        cached_frozen_models = None

        for ep in range(6):
            if arm == "Frozen-GP-28" and cached_frozen_models is not None:
                km_t, leg_pols = cached_frozen_models
                op_gp_fit_ms_ep.append(0.0)
            else:
                t_gp0 = time.perf_counter()
                km_t = KrigingWorldModel(X_cur, q_cur, b_cur)
                exec_fd = ClassicalFDSolver(world.spec, grid_n, km_t.predict_q, km_t.predict_b)
                leg_pols = {
                    j: exec_fd.solve_direct(QueryTask(f"l_{j}", (w,), ((0.0, 0.0),)))["policy"]
                    for j, w in enumerate(catalog_wps)
                }
                op_gp_fit_ms_ep.append(1000.0 * (time.perf_counter() - t_gp0))
                if arm == "Frozen-GP-28":
                    cached_frozen_models = (km_t, leg_pols)

            # 1. OPERATIONAL PLANNER & ONLINE EXECUTION FIRST (strictly isolated from held-out evaluation!)
            t_op0 = time.perf_counter()
            pl_op = SchurPortPlanner(
                world.spec, grid_n, km_t.predict_q, km_t.predict_b, catalog_wps,
                initial_sectors_per_wp="EXACT", lazy_init=True,
            )
            mt_op = MacroTourPlanner(pl_op)
            op_online_plan_ms_ep.append(1000.0 * (time.perf_counter() - t_op0))

            o_costs, o_comps = [], []
            realized_states_ep: List[np.ndarray] = []
            need_states = (arm in ("True-OnPolicy-14", "True-OnPolicy-11+Sentinel-3")) and (ep < 5)
            for tk_i, (s_o, sub_o, _) in enumerate(online_stream[ep]):
                t_po = time.perf_counter()
                res_o = mt_op.plan_exact_subset_dp(s_o, sub_o)
                op_online_plan_ms_ep[-1] += 1000.0 * (time.perf_counter() - t_po)
                sim_o = _simulate_adaptive_tour_coupled(
                    world, catalog_wps, leg_pols, s_o, sub_o, res_o["select_next_waypoint"],
                    online_dW_bank[ep][tk_i], dt_sim=0.015, fractional_segment_hit=True, record_visited_states=need_states,
                )
                o_costs.append(sim_o["mean_cost"])
                o_comps.append(sim_o["completion_rate"])
                if need_states and len(sim_o["visited_states"]) > 0:
                    realized_states_ep.append(sim_o["visited_states"])
            online_cost_ep.append(float(np.mean(o_costs)))
            online_comp_ep.append(float(np.mean(o_comps)))

            # 2. CAUSAL ACQUISITION ON `pl_op` / `mt_op` BEFORE ANY HELD-OUT EVALUATION RUNS!
            if ep < 5:
                t_acq0 = time.perf_counter()
                if arm == "Frozen-GP-28":
                    op_acq_ms_ep.append(0.0)
                    X_new = None
                elif arm == "Global-CondMaxVar-14":
                    X_new = km_t.select_sequential_conditional_maxvar_probes(cand_pool, X_cur, 14, min_repel=min_repel)
                elif arm == "True-OnPolicy-14":
                    traj_cloud = np.vstack(realized_states_ep)
                    traj_perm = traj_cloud[rng_acq.permutation(len(traj_cloud))]
                    _, lat_std_tr, _ = km_t.predict_q_latent_std(traj_perm)
                    X_new = _select_active_probes_diverse(traj_perm, 1.0 + lat_std_tr, X_cur, 14, min_repel=min_repel)
                    cloud_set = {tuple(np.round(pt, 12)) for pt in traj_cloud}
                    if not all(tuple(np.round(pt, 12)) in cloud_set for pt in X_new):
                        all_onpolicy_verified = False
                elif arm == "True-OnPolicy-11+Sentinel-3":
                    traj_cloud = np.vstack(realized_states_ep)
                    traj_perm = traj_cloud[rng_acq.permutation(len(traj_cloud))]
                    _, lat_std_tr, _ = km_t.predict_q_latent_std(traj_perm)
                    X_onp = _select_active_probes_diverse(traj_perm, 1.0 + lat_std_tr, X_cur, 11, min_repel=min_repel)
                    cloud_set = {tuple(np.round(pt, 12)) for pt in traj_cloud}
                    if not all(tuple(np.round(pt, 12)) in cloud_set for pt in X_onp):
                        all_onpolicy_verified = False
                    X_sen = km_t.select_sequential_conditional_maxvar_probes(
                        cand_pool, np.vstack([X_cur, X_onp]), 3, min_repel=min_repel
                    )
                    X_new = np.vstack([X_onp, X_sen])
                elif arm in ("Green-ValueOnly-Cond-11+3", "Green-KG-VoI-11+3"):
                    sens_list = []
                    for s_o, sub_o, _ in online_stream[ep]:
                        s_dict = mt_op.compute_exact_macro_q_sensitivities(
                            s_o, sub_o, max_alt_branches=3 if arm == "Green-KG-VoI-11+3" else 0, include_drift_grad=True
                        )
                        root_gaps_logged.append(float(s_dict["action_gap"]))
                        if arm == "Green-ValueOnly-Cond-11+3":
                            s_dict = dict(s_dict)
                            s_dict["alt_branches"] = []
                        sens_list.append(s_dict)
                    X_new, kg_diag = km_t.select_sequential_kg_voi_probes(
                        cand_pool,
                        pl_op.pts,
                        sens_list,
                        X_cur,
                        n_decision=11,
                        n_sentinel=3,
                        min_repel=min_repel,
                        val_reg_weight=1.0 if arm == "Green-ValueOnly-Cond-11+3" else 0.15,
                    )
                    relu_fracs_logged.append(float(kg_diag["active_q_relu_fraction"]))
                else:
                    raise ValueError(arm)

                if X_new is not None:
                    op_acq_ms_ep.append(1000.0 * (time.perf_counter() - t_acq0))
                    probe_sha_ep.append(hashlib.sha256(np.round(X_new, 10).tobytes()).hexdigest()[:12])

            # 3. SEPARATE EVALUATION PLANNER `pl_eval` FOR HELD-OUT FUTURE BANK (zero operational side effects!)
            t_ev0 = time.perf_counter()
            pl_eval = SchurPortPlanner(
                world.spec, grid_n, km_t.predict_q, km_t.predict_b, catalog_wps,
                initial_sectors_per_wp="EXACT", lazy_init=True,
            )
            mt_eval = MacroTourPlanner(pl_eval)
            h_costs, h_comps, h_tos, h_clips = [], [], [], []
            for s_h, sub_h, dW_c_h in heldout_bank:
                res_h = mt_eval.plan_exact_subset_dp(s_h, sub_h)
                sim_h = _simulate_adaptive_tour_coupled(
                    world, catalog_wps, leg_pols, s_h, sub_h, res_h["select_next_waypoint"],
                    dW_c_h, dt_sim=0.015, fractional_segment_hit=True, record_visited_states=False,
                )
                h_costs.append(sim_h["mean_cost"])
                h_comps.append(sim_h["completion_rate"])
                h_tos.append(sim_h["timeout_frac"])
                h_clips.append(sim_h["clip_frac"])
            eval_only_ms_ep.append(1000.0 * (time.perf_counter() - t_ev0))

            heldout_cost_ep.append(float(np.mean(h_costs)))
            heldout_comp_ep.append(float(np.mean(h_comps)))
            heldout_to_ep.append(float(np.mean(h_tos)))
            heldout_clip_ep.append(float(np.mean(h_clips)))

            # 4. Observe world at `X_new` to advance `(X_cur, q_cur, b_cur)` to Episode `ep + 1`
            if ep < 5 and X_new is not None:
                obs_rng = np.random.default_rng(np.random.SeedSequence([ms, ep, 9109]))
                Xn, qn, bn = observe_world_at_points(world, X_new, obs_rng, include_drift=True)
                X_cur = np.vstack([X_cur, Xn])
                q_cur = np.concatenate([q_cur, qn])
                b_cur = np.vstack([b_cur, bn])

        arm_out[arm] = {
            "heldout_cost_by_ep": heldout_cost_ep,
            "heldout_post_acq_ep2_6_mean_cost": float(np.mean(heldout_cost_ep[1:])),
            "heldout_final_ep6_cost": float(heldout_cost_ep[-1]),
            "heldout_completion_by_ep": heldout_comp_ep,
            "heldout_post_acq_completion_rate": float(np.mean(heldout_comp_ep[1:])),
            "heldout_mean_timeout_frac": float(np.mean(heldout_to_ep)),
            "heldout_mean_clip_frac": float(np.mean(heldout_clip_ep)),
            "online_stream_cost_by_ep": online_cost_ep,
            "online_post_acq_ep2_6_mean_cost": float(np.mean(online_cost_ep[1:])),
            "online_completion_rate": float(np.mean(online_comp_ep)),
            "operational_gp_and_ctrl_ms": float(np.sum(op_gp_fit_ms_ep)),
            "operational_online_plan_ms": float(np.sum(op_online_plan_ms_ep)),
            "operational_acquisition_ms": float(np.sum(op_acq_ms_ep)),
            "operational_total_ms": float(np.sum(op_gp_fit_ms_ep) + np.sum(op_online_plan_ms_ep) + np.sum(op_acq_ms_ep)),
            "evaluation_only_ms": float(np.sum(eval_only_ms_ep)),
            "selected_probe_sha256_by_ep": probe_sha_ep,
            "all_onpolicy_probes_verified_visited_states": bool(all_onpolicy_verified),
            "mean_online_root_action_gap": float(np.mean(root_gaps_logged)) if root_gaps_logged else None,
            "near_tie_online_task_fraction_lt_0_35": float(np.mean(np.array(root_gaps_logged) < 0.35)) if root_gaps_logged else None,
            "mean_active_q_relu_fraction": float(np.mean(relu_fracs_logged)) if relu_fracs_logged else None,
        }

    return {"map_seed": ms, "regime": regime_name, "arms": arm_out}


def _summarize_voi_cohort(rows: List[dict], regime_label: str, seeds: List[int], grid_n: int) -> dict:
    arms = [
        "Frozen-GP-28",
        "Global-CondMaxVar-14",
        "True-OnPolicy-14",
        "True-OnPolicy-11+Sentinel-3",
        "Green-ValueOnly-Cond-11+3",
        "Green-KG-VoI-11+3",
    ]
    kg_post = np.array([r["arms"]["Green-KG-VoI-11+3"]["heldout_post_acq_ep2_6_mean_cost"] for r in rows])
    kg_ep6 = np.array([r["arms"]["Green-KG-VoI-11+3"]["heldout_final_ep6_cost"] for r in rows])
    frz_post = np.array([r["arms"]["Frozen-GP-28"]["heldout_post_acq_ep2_6_mean_cost"] for r in rows])
    onps_post = np.array([r["arms"]["True-OnPolicy-11+Sentinel-3"]["heldout_post_acq_ep2_6_mean_cost"] for r in rows])

    ep1_vals = [float(np.mean([r["arms"][a]["heldout_cost_by_ep"][0] for r in rows])) for a in arms]
    ep1_spread = float(max(ep1_vals) - min(ep1_vals))

    summary_arms = {}
    for a in arms:
        a_post = np.array([r["arms"][a]["heldout_post_acq_ep2_6_mean_cost"] for r in rows])
        a_ep6 = np.array([r["arms"][a]["heldout_final_ep6_cost"] for r in rows])
        summary_arms[a] = {
            "heldout_mean_cost_by_episode": [
                float(np.mean([r["arms"][a]["heldout_cost_by_ep"][ep] for r in rows])) for ep in range(6)
            ],
            "primary_heldout_post_acq_ep2_6_mean_cost": float(np.mean(a_post)),
            "heldout_final_ep6_mean_cost": float(np.mean(a_ep6)),
            "heldout_post_acq_completion_rate": float(np.mean([r["arms"][a]["heldout_post_acq_completion_rate"] for r in rows])),
            "heldout_mean_timeout_frac": float(np.mean([r["arms"][a]["heldout_mean_timeout_frac"] for r in rows])),
            "heldout_mean_clip_frac": float(np.mean([r["arms"][a]["heldout_mean_clip_frac"] for r in rows])),
            "online_post_acq_ep2_6_mean_cost": float(np.mean([r["arms"][a]["online_post_acq_ep2_6_mean_cost"] for r in rows])),
            "mean_operational_gp_and_ctrl_ms": float(np.mean([r["arms"][a]["operational_gp_and_ctrl_ms"] for r in rows])),
            "mean_operational_online_plan_ms": float(np.mean([r["arms"][a]["operational_online_plan_ms"] for r in rows])),
            "mean_operational_acquisition_ms": float(np.mean([r["arms"][a]["operational_acquisition_ms"] for r in rows])),
            "mean_operational_total_ms": float(np.mean([r["arms"][a]["operational_total_ms"] for r in rows])),
            "method_minus_frozen_gp_heldout_ep2_6": paired_stats(a_post - frz_post),
            "green_kg_voi_minus_method_heldout_ep2_6": paired_stats(kg_post - a_post),
            "green_kg_voi_minus_method_heldout_ep6": paired_stats(kg_ep6 - a_ep6),
            "per_map_heldout_post_acq_ep2_6_cost": a_post.tolist(),
        }

    fam_contrasts = {
        "KGVoI_minus_OnPolicy11Sentinel3": summary_arms["True-OnPolicy-11+Sentinel-3"]["green_kg_voi_minus_method_heldout_ep2_6"],
        "KGVoI_minus_OnPolicy14": summary_arms["True-OnPolicy-14"]["green_kg_voi_minus_method_heldout_ep2_6"],
        "KGVoI_minus_GlobalCondMaxVar14": summary_arms["Global-CondMaxVar-14"]["green_kg_voi_minus_method_heldout_ep2_6"],
    }
    holm_res = holm_bonferroni_adjust({k: v["p_two_sided"] for k, v in fam_contrasts.items()})
    onp_sentinel_ni_1_5pct = paired_relative_noninferiority(onps_post, kg_post, rel_margin_pct=1.5)

    return {
        "regime": regime_label,
        "fresh_seeds": seeds,
        "n_maps": len(rows),
        "grid_n": grid_n,
        "episode1_max_cost_spread_across_all_6_arms": ep1_spread,
        "all_onpolicy_probes_verified_visited_states": bool(
            all(
                r["arms"]["True-OnPolicy-14"]["all_onpolicy_probes_verified_visited_states"]
                and r["arms"]["True-OnPolicy-11+Sentinel-3"]["all_onpolicy_probes_verified_visited_states"]
                for r in rows
            )
        ),
        "mean_online_root_action_gap": float(np.mean([r["arms"]["Green-KG-VoI-11+3"]["mean_online_root_action_gap"] for r in rows])),
        "near_tie_online_task_fraction_lt_0_35": float(np.mean([r["arms"]["Green-KG-VoI-11+3"]["near_tie_online_task_fraction_lt_0_35"] for r in rows])),
        "mean_active_q_relu_fraction": float(np.mean([r["arms"]["Green-KG-VoI-11+3"]["mean_active_q_relu_fraction"] for r in rows])),
        "predeclared_family_contrasts_ep2_6": fam_contrasts,
        "holm_bonferroni_family_adjustment": holm_res,
        "declared_1_5pct_relative_NI_OnPolicy11Sentinel3_vs_GreenKGVoI": onp_sentinel_ni_1_5pct,
        "arms": summary_arms,
        "per_map_records": rows,
    }


def run_decisive_isolated_online_voi_study(n_maps_per_regime: int = 16, grid_n: int = 51, max_workers: int = 8) -> dict:
    std_seeds = list(range(10300, 10300 + n_maps_per_regime))
    comp_seeds = list(range(10400, 10400 + n_maps_per_regime))
    rows_std = run_map_parallel(
        _decisive_isolated_voi_map_worker,
        [(i, s, "narrow_barrier", grid_n) for i, s in enumerate(std_seeds)],
        max_workers=max_workers,
    )
    rows_comp = run_map_parallel(
        _decisive_isolated_voi_map_worker,
        [(i, s, "competing_corridor", grid_n) for i, s in enumerate(comp_seeds)],
        max_workers=max_workers,
    )
    sum_std = _summarize_voi_cohort(rows_std, "narrow_barrier", std_seeds, grid_n)
    sum_comp = _summarize_voi_cohort(rows_comp, "competing_corridor", comp_seeds, grid_n)
    sum_pooled = _summarize_voi_cohort(rows_std + rows_comp, "pooled_both_regimes_32maps", std_seeds + comp_seeds, grid_n)
    return {
        "block_provenance": "fresh_computed_in_current_run",
        "experiment_scope": "strict_eval_isolated_same_exact_planner_coordinate_oracle_kg_voi_vs_onpolicy_sentinel_dual_regime",
        "planner_isolation_contract": "pl_eval is physically separate from pl_operational; held-out tasks share same known catalog (new task instances).",
        "standard_narrow_barrier_16maps": sum_std,
        "competing_corridor_bifurcation_16maps": sum_comp,
        "pooled_32maps": sum_pooled,
    }


def plot_exp4(fid: dict, real_gp_lc: dict, voi_study: dict, out_png: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(20.4, 5.6))

    # Panel 1: Coupled-Wiener Fidelity Bridge (Piecewise-Reflected Polyline Hit)
    ax = axes[0]
    gaps = fid["layers_mean_abs_gap"]
    labels = [
        "L1: Port vs\nExactMacro",
        "L2a: GP SDE\ndt=.015 End",
        "L2b: GP SDE\ndt=.005 End",
        "L2c: GP SDE\ndt=.005 RefSeg",
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
    ax.set_title("Coupled-Wiener Fidelity Bridge (72 Tours)\n(Exact 3x Brownian Coupling + Piecewise-Reflected Hit)", fontsize=9.0)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=7.2, loc="upper right")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.3f}", ha="center", va="bottom", fontsize=7.4, fontweight="bold")
    ax.set_ylim(0, max(vals) * 1.20)

    # Panel 2: Genuine `+16` Physical-Observation GP Refit Lifecycle (`12` Maps `10250..10261`, `K = 12` Post-Update Tasks)
    ax = axes[1]
    reg_r = real_gp_lc["regimes"]
    reg_keys = ["2D-61sq-ColdPrefix", "2D-61sq-WarmPrefix", "3D-21cubed-ColdPrefix", "3D-21cubed-WarmPrefix"]
    reg_lbls = ["2D 61²\nCold-Prefix", "2D 61²\nWarm-Prefix", "3D 21³\nCold-Prefix", "3D 21³\nWarm-Prefix"]
    x = np.arange(len(reg_keys))
    w = 0.20
    for off, m_key, lbl, col in [
        (-1.5 * w, "Scratch-Rebuild", "Scratch Port Rebuild", "#d62728"),
        (-0.5 * w, "Structure-Memory-Fresh-Exact", "Structure-Only Fresh", "#ff7f0e"),
        (0.5 * w, "Residual-Audited-Reuse", "Residual-Audited Reuse", "#1f77b4"),
        (1.5 * w, "ExactRing-Rebuild", "ExactRing Rebuild (Default)", "#333333"),
    ]:
        ys = [reg_r[rk]["methods"][m_key]["post_update_marginal_ms_by_K"]["K_12"] for rk in reg_keys]
        ax.bar(x + off, ys, width=w, color=col, label=lbl)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(reg_lbls, fontsize=7.7)
    ax.set_ylabel("Post-Update Lifecycle: GP2 + Update + 12 Tasks (ms, log)")
    p_3dw_str_ex = reg_r["3D-21cubed-WarmPrefix"]["methods"]["Structure-Memory-Fresh-Exact"]["paired_marginal_K12_diff_vs_exact_rebuild"]["p_two_sided"]
    p_3dw_res_str = reg_r["3D-21cubed-WarmPrefix"]["methods"]["Residual-Audited-Reuse"]["paired_marginal_K12_diff_vs_structure_only"]["p_two_sided"]
    ax.set_title(
        f"Real +16 GP-Obs Refit Lifecycle (12 Maps, Fixed 12-WP Cat, K=12)\n(3D Warm: Struct vs Exact p={p_3dw_str_ex:.3g}; Resid vs Struct p={p_3dw_res_str:.3g})",
        fontsize=8.6,
    )
    ax.grid(True, axis="y", which="both", alpha=0.3)
    ax.legend(fontsize=6.8, loc="upper left")

    # Panel 3: Decisive Isolated VoI Study (`16` Standard + `16` Competing-Corridor Maps)
    ax = axes[2]
    std_s = voi_study["standard_narrow_barrier_16maps"]
    cmp_s = voi_study["competing_corridor_bifurcation_16maps"]
    arm_order = [
        ("Frozen-GP-28", "Frozen-GP\n(28 obs)", "#aa3333"),
        ("Global-CondMaxVar-14", "Global\nCondMaxVar", "#9467bd"),
        ("True-OnPolicy-14", "True\nOnPolicy-14", "#ff7f0e"),
        ("True-OnPolicy-11+Sentinel-3", "OnPolicy-11\n+Sentinel-3", "#1f77b4"),
        ("Green-ValueOnly-Cond-11+3", "Green-Val\nCond-11+3", "#17becf"),
        ("Green-KG-VoI-11+3", "Green-KG-VoI\nCond-11+3", "#2ca02c"),
    ]
    xa = np.arange(len(arm_order))
    wb = 0.36
    y_std = [std_s["arms"][ak]["primary_heldout_post_acq_ep2_6_mean_cost"] for ak, _, _ in arm_order]
    y_cmp = [cmp_s["arms"][ak]["primary_heldout_post_acq_ep2_6_mean_cost"] for ak, _, _ in arm_order]
    ax.bar(xa - wb / 2, y_std, width=wb, color="#4c78a8", alpha=0.90, label="Standard Barrier (16 Maps)")
    ax.bar(xa + wb / 2, y_cmp, width=wb, color="#f58518", alpha=0.90, label="Competing Corridor (16 Maps)")
    ax.set_xticks(xa)
    ax.set_xticklabels([lbl for _, lbl, _ in arm_order], fontsize=7.1)
    ymin = min(min(y_std), min(y_cmp))
    ymax = max(max(y_std), max(y_cmp))
    ax.set_ylim(max(0.0, ymin - 0.8), ymax + 0.65)
    ax.set_ylabel("Held-Out Future Tour Bank Cost (Ep 2–6 Mean)")
    p_std_hm = std_s["holm_bonferroni_family_adjustment"]["KGVoI_minus_OnPolicy11Sentinel3"]["p_holm"]
    p_cmp_hm = cmp_s["holm_bonferroni_family_adjustment"]["KGVoI_minus_OnPolicy11Sentinel3"]["p_holm"]
    ax.set_title(
        f"Eval-Isolated Active Sensing (32 Fresh Maps, Holm-Adjusted)\n(KG-VoI vs OnPolicy+Sent Holm p: Std={p_std_hm:.3f}, Comp={p_cmp_hm:.3f})",
        fontsize=8.6,
    )
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=7.2, loc="upper right")

    plt.tight_layout()
    plt.savefig(out_png, dpi=175)
    plt.close(fig)


def main():
    enforce_single_thread_env()
    n_workers = 8
    out_dir = Path(__file__).resolve().parent
    old_p = out_dir / "exp4_results.json"
    old_data = json.loads(old_p.read_text(encoding="utf-8")) if old_p.exists() else {}

    if "model_to_execution_fidelity_72tasks" in old_data:
        fid = old_data["model_to_execution_fidelity_72tasks"]
        fid["block_provenance"] = "inherited_from_commit_29fa7c6"
        print("Reusing verified Exp 4A (72-tour fidelity bridge) from 29fa7c6.", flush=True)
    else:
        fid = run_model_to_execution_fidelity_study(n_maps=12, tasks_per_map=6, grid_n=75, max_workers=n_workers)

    if "continual_orthogonal_transition_200tasks" in old_data:
        cont = old_data["continual_orthogonal_transition_200tasks"]
        cont["block_provenance"] = "inherited_from_commit_29fa7c6_relabeled_synthetic_bump"
        if "warm_vs_cold_net_benefit_crossover_8maps" in cont:
            syn_blk = cont.pop("warm_vs_cold_net_benefit_crossover_8maps")
            syn_blk["perturbation_type"] = "deterministic_corner_gaussian_bump_no_gp_refit"
            syn_blk["scope_note"] = "Controlled synthetic operator perturbation stress test (not real GP observation refit)."
            cont["synthetic_local_bump_crossover_8maps"] = syn_blk
        print("Retained & honestly relabeled Exp 4B synthetic perturbation block from 29fa7c6.", flush=True)
    else:
        cont = run_orthogonal_operator_transition_stream(n_maps=10, grid_n=61, max_workers=n_workers)

    prev_learn = old_data.get("unconfounded_online_learning_and_transfer_16maps")
    if prev_learn is not None:
        prev_learn["block_provenance"] = "inherited_from_commit_29fa7c6_dev_baseline"

    print(f"\n=== Stage B2: Genuine +16 GP-Obs Refit Lifecycle (12 Maps 10250..10261, {n_workers}-Core Parallel) ===", flush=True)
    t0 = time.perf_counter()
    real_gp_lc = run_real_gp_update_lifecycle_benchmark(n_maps=12, max_workers=n_workers)
    print(f"  -> Stage B2 done in {time.perf_counter()-t0:.1f}s", flush=True)

    print(f"\n=== Stage C/D: Eval-Isolated KG-VoI Dual-Regime Decisive Study (32 Fresh Maps, {n_workers}-Core Parallel) ===", flush=True)
    t0 = time.perf_counter()
    voi_study = run_decisive_isolated_online_voi_study(n_maps_per_regime=16, grid_n=51, max_workers=n_workers)
    print(
        f"  -> Stage C/D done in {time.perf_counter()-t0:.1f}s "
        f"(Std Ep1 spread={voi_study['standard_narrow_barrier_16maps']['episode1_max_cost_spread_across_all_6_arms']:.2e}, "
        f"Comp Ep1 spread={voi_study['competing_corridor_bifurcation_16maps']['episode1_max_cost_spread_across_all_6_arms']:.2e})",
        flush=True,
    )

    payload = {
        "metadata": collect_runtime_metadata(max_workers=n_workers),
        "model_to_execution_fidelity_72tasks": fid,
        "continual_orthogonal_transition_200tasks": cont,
        "real_gp_update_lifecycle_12maps": real_gp_lc,
        "decisive_isolated_voi_dual_regime_32maps": voi_study,
    }
    if prev_learn is not None:
        payload["historical_v29_online_baseline_16maps"] = prev_learn

    (out_dir / "exp4_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plot_exp4(fid, real_gp_lc, voi_study, out_dir / "exp4_fidelity_and_continual.png")
    print("Saved exp4_results.json and exp4_fidelity_and_continual.png", flush=True)


if __name__ == "__main__":
    main()
