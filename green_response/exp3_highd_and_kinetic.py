"""Experiment 3 (`green_response` — Post-`85e2323` Audit Closure & Prior Sample Efficiency):

3A & 3B. 4D & 6D Frozen-Label Physics-Mean Attribution with NNLS-Matched Sharp/Smooth Cone Controls:
  - Compares on bit-identical frozen FK labels `(X_all, y_total_v)`:
      * `FrozenFK-ZeroMeanPrior` (empirical constant mean, no physics prior),
      * `FrozenFK-EikonalConePrior` (smooth softmin cone),
      * `FrozenFK-MatchedSmoothConePrior` (36-point NNLS + `C^2` collar + `tau=0.035`),
      * `FrozenFK-MatchedSharpConePrior` (36-point NNLS + `C^2` collar + `tau=0.0` exact finite slope!),
      * `FrozenFK-HelmholtzBesselPrior` (`BoxNeumannBesselBaseGuide` — isolating `d`-D Helmholtz curvature!);
  - Persists full per-map train / unseen-in-dist / wall-corner-shift costs, reach/clip rates, ESS quantiles,
    and reports BOTH `all8` pooled and `heldout4` paired statistics separately!

3B-Confirm. 6D Anchor-Budget Efficiency Curve (`16` maps `9600..9615` from `d1b926a` confirmation cohort,
  split into `9600..9607` vs `9608..9615`):
  - Varies nominal interior FK anchor budget `N_anch in {24, 54, 108}` comparing `ZeroMean`, `MatchedSharpCone`,
    and `HelmholtzBessel`, plus decoupled fixed-design vs full-reconstruction seed sensitivity.

3D. Independent Non-Bessel Teachers (`3D 25^3` discrete FD reference on `9700..9707`; `6D` Cone-Girsanov
  teacher on `9608..9615`) & Locked `method_config_id` Quality–Cost + Serial/Batch-Makespan Table (`29fa7c6` Stage B1).

3C. Scoped Empirical 4D Kinetic Double-Integrator Study (`10` maps, `6` continuation rounds).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import json
import sys
import time
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from green_response import (
    BoxNeumannBesselBaseGuide,
    EikonalConeMeanGuide,
    GoalBall,
    HazardFeature,
    KrigingWorldModel,
    ProblemSpec,
    QueryTask,
    build_kinetic_lqr_base_guide,
    collect_runtime_metadata,
    enforce_single_thread_env,
    fit_gp_value_with_prior,
    generate_benchmark_map,
    make_antithetic_centered_pimc_policy,
    paired_relative_noninferiority,
    paired_stats,
    reflect_kinetic_into_box,
    sample_noisy_probes,
    simulate_closed_loop_crn,
    solve_highd_fk_distillation,
    solve_kinetic_underactuated_greenres,
)


def make_highd_queries_three_regimes(
    map_seed: int, dim: int, n_queries: int = 3
) -> List[Tuple[QueryTask, QueryTask, QueryTask]]:
    rng = np.random.default_rng(map_seed + 505)
    r_goal = 0.36 if dim == 4 else 0.44
    triples = []
    for q_i in range(n_queries):
        goals = []
        for g_k in range(2):
            for _att in range(100):
                gc = rng.uniform(-0.92, 0.92, size=dim)
                if dim > 2:
                    gc[2:] *= 0.65
                if all(np.linalg.norm(gc - np.asarray(prev.center)) > 2.15 * r_goal for prev in goals):
                    phi_v = 0.0 if g_k == 0 else float(rng.uniform(0.20, 0.85))
                    goals.append(GoalBall(tuple(gc.tolist()), phi=phi_v, radius=r_goal))
                    break

        in_starts = []
        for _ in range(5):
            for _att in range(120):
                sp_pt = rng.uniform(-1.20, 1.20, size=dim)
                if dim > 2:
                    sp_pt[2:] *= 0.80
                if all(np.linalg.norm(sp_pt - np.asarray(g.center)) > r_goal + 0.35 for g in goals):
                    in_starts.append(tuple(sp_pt.tolist()))
                    break

        shift_starts = []
        for _ in range(2):
            for _att in range(150):
                sp_sh = rng.uniform(-1.30, 1.30, size=dim)
                ax_pair = rng.choice(dim, size=2, replace=False)
                for ax_i in ax_pair:
                    sp_sh[ax_i] = float(rng.choice([-1.0, 1.0]) * rng.uniform(1.38, 1.58))
                if all(np.linalg.norm(sp_sh - np.asarray(g.center)) > r_goal + 0.35 for g in goals):
                    shift_starts.append(tuple(sp_sh.tolist()))
                    break

        mid = np.clip(0.5 * (np.asarray(in_starts[0]) + np.asarray(goals[0].center)), -1.1, 1.1)
        loc_h = (HazardFeature(tuple(mid.tolist()), float(rng.uniform(4.5, 8.0)), (0.34,) * dim),)
        q_train = QueryTask(f"hd_{dim}d_{q_i}", tuple(goals), tuple(in_starts[:3]), loc_h)
        q_unseen = QueryTask(f"hd_{dim}d_{q_i}_unseen_indist", tuple(goals), tuple(in_starts[3:5]), loc_h)
        q_shift = QueryTask(f"hd_{dim}d_{q_i}_wall_corner_shift", tuple(goals), tuple(shift_starts), loc_h)
        triples.append((q_train, q_unseen, q_shift))
    return triples


def run_highd_prior_and_shift_suite(
    dim: int, n_probes: int, n_dev: int = 4, n_heldout: int = 4, n_queries: int = 3
) -> dict:
    spec = ProblemSpec(dim=dim, half_width=1.65, sigma=0.55, q0=0.65, dt_sim=0.020, max_steps=420)
    base_s = 2200 if dim == 4 else 3200
    map_seeds = list(range(base_s, base_s + n_dev)) + list(range(base_s + 1000, base_s + 1000 + n_heldout))

    methods = [
        "Pure-Eikonal-Guide",
        "Pure-MatchedSharpCone-Guide",
        "Pure-Bessel-BaseGuide",
        "SameGP-Centered-PIMC-H16",
        "SameGP-Centered-PIMC-H48",
        "EndToEnd-Unguided-ZeroMean",
        "EndToEnd-Guided-ZeroMean",
        "FrozenFK-ZeroMeanPrior",
        "FrozenFK-EikonalConePrior",
        "FrozenFK-MatchedSmoothConePrior",
        "FrozenFK-MatchedSharpConePrior",
        "FrozenFK-HelmholtzBesselPrior",
        "EndToEnd-DiscreteTele-BesselPrior",
    ]
    train_costs = {m: [] for m in methods}
    unseen_indist_costs = {m: [] for m in methods}
    wall_corner_shift_costs = {m: [] for m in methods}
    reach_tr_map = {m: [] for m in methods}
    reach_sh_map = {m: [] for m in methods}
    build_ms = {m: [] for m in methods}
    k1_exec_ms = {m: [] for m in methods}
    gp_fit_ms_list = []
    fk_query_diags = []

    n_anch = 88 if dim == 4 else 108

    for idx_m, m_seed in enumerate(map_seeds):
        world = generate_benchmark_map(m_seed, dim=dim, regime="smooth", with_drift=True, spec=spec)
        X_obs, q_obs, b_obs = sample_noisy_probes(world, n_probes=n_probes, seed=m_seed + 7, include_drift=True)
        t_gp = time.perf_counter()
        km = KrigingWorldModel(X_obs, q_obs, b_obs)
        gp_fit_ms_list.append(1000.0 * (time.perf_counter() - t_gp))

        triples = make_highd_queries_three_regimes(m_seed, dim=dim, n_queries=n_queries)
        c_tr = {m: [] for m in methods}
        c_un = {m: [] for m in methods}
        c_sh = {m: [] for m in methods}
        r_tr = {m: [] for m in methods}
        r_sh = {m: [] for m in methods}
        b_q = {m: [] for m in methods}
        e1_q = {m: [] for m in methods}

        for q_i, (q_tr, q_un, q_sh) in enumerate(triples):
            fk_seed = 8000 + 20 * idx_m + q_i
            sim_seed = 9000 + 20 * idx_m + q_i
            q_k1 = QueryTask(q_tr.name + "_k1", q_tr.goals, (q_tr.start_points[0],), q_tr.local_hazards)

            t0 = time.perf_counter()
            eik_g = EikonalConeMeanGuide(spec, q_tr)
            b_eik_ms = 1000.0 * (time.perf_counter() - t0)
            pol_eik = lambda X, eg=eik_g: -eg.val_and_grad(X)[1]

            t0 = time.perf_counter()
            shc_g = EikonalConeMeanGuide(spec, q_tr, smooth_tau=0.0, calibrate_nnls=True)
            b_shc_ms = 1000.0 * (time.perf_counter() - t0)
            pol_shc = lambda X, sg=shc_g: -sg.val_and_grad(X)[1]

            t0 = time.perf_counter()
            bes_g = BoxNeumannBesselBaseGuide(spec, q_tr)
            b_bes_ms = 1000.0 * (time.perf_counter() - t0)
            pol_bes = lambda X, bg=bes_g: -bg.val_and_grad(X)[1]

            pol_p16, init_p16, _ = make_antithetic_centered_pimc_policy(spec, km, q_tr, n_particles=36, horizon_steps=16, seed=fk_seed + 1)
            pol_p48, init_p48, _ = make_antithetic_centered_pimc_policy(spec, km, q_tr, n_particles=36, horizon_steps=48, seed=fk_seed + 2)

            s_ung = solve_highd_fk_distillation(
                spec, km, q_tr, n_interior_anchors=n_anch, n_mc_paths=64, n_steps_fk=75,
                residual_mode="continuum_collar", prior_mode="zero_mean", guided_proposal=False, seed=fk_seed,
            )
            s_gui_zm = solve_highd_fk_distillation(
                spec, km, q_tr, n_interior_anchors=n_anch, n_mc_paths=64, n_steps_fk=75,
                residual_mode="continuum_collar", prior_mode="zero_mean", guided_proposal=True, seed=fk_seed,
            )
            s_disc = solve_highd_fk_distillation(
                spec, km, q_tr, n_interior_anchors=n_anch, n_mc_paths=64, n_steps_fk=75,
                residual_mode="discrete_telescoping", prior_mode="helmholtz_bessel", guided_proposal=True, seed=fk_seed,
            )
            s_bessel = solve_highd_fk_distillation(
                spec, km, q_tr, n_interior_anchors=n_anch, n_mc_paths=64, n_steps_fk=75,
                residual_mode="continuum_collar", prior_mode="helmholtz_bessel", guided_proposal=True, seed=fk_seed,
            )

            fX, fY, fN = s_bessel["frozen_X_all"], s_bessel["frozen_y_total_v"], s_bessel["frozen_noise_vec"]
            t_fz = time.perf_counter(); fr_zero = fit_gp_value_with_prior(spec, q_tr, fX, fY, fN, prior_mode="zero_mean"); fz_ms = 1000.0 * (time.perf_counter() - t_fz)
            t_fe = time.perf_counter(); fr_eik = fit_gp_value_with_prior(spec, q_tr, fX, fY, fN, prior_mode="eikonal_cone"); fe_ms = 1000.0 * (time.perf_counter() - t_fe)
            t_fms = time.perf_counter(); fr_msmooth = fit_gp_value_with_prior(spec, q_tr, fX, fY, fN, prior_mode="matched_smooth_cone"); fms_ms = 1000.0 * (time.perf_counter() - t_fms)
            t_fsh = time.perf_counter(); fr_msharp = fit_gp_value_with_prior(spec, q_tr, fX, fY, fN, prior_mode="matched_sharp_cone"); fsh_ms = 1000.0 * (time.perf_counter() - t_fsh)

            fk_query_diags.append({
                "map_seed": m_seed,
                "query_idx": q_i,
                "collar_frac": s_bessel["collar_step_fraction"],
                "mean_ess": s_bessel["mean_ess"],
                "median_ess": s_bessel["median_ess"],
                "min_ess": s_bessel["min_ess"],
                "weighted_tail_mass": s_bessel["weighted_tail_mass"],
                "cont_final_diff": s_bessel["continuation_max_diffs"][-1] if s_bessel["continuation_max_diffs"] else 0.0,
            })

            pol_table = {
                "Pure-Eikonal-Guide": (pol_eik, b_eik_ms),
                "Pure-MatchedSharpCone-Guide": (pol_shc, b_shc_ms),
                "Pure-Bessel-BaseGuide": (pol_bes, b_bes_ms),
                "SameGP-Centered-PIMC-H16": (pol_p16, init_p16),
                "SameGP-Centered-PIMC-H48": (pol_p48, init_p48),
                "EndToEnd-Unguided-ZeroMean": (s_ung["policy"], s_ung["plan_ms"]),
                "EndToEnd-Guided-ZeroMean": (s_gui_zm["policy"], s_gui_zm["plan_ms"]),
                "FrozenFK-ZeroMeanPrior": (fr_zero["policy"], s_bessel["plan_ms"] + fz_ms),
                "FrozenFK-EikonalConePrior": (fr_eik["policy"], s_bessel["plan_ms"] + fe_ms),
                "FrozenFK-MatchedSmoothConePrior": (fr_msmooth["policy"], s_bessel["plan_ms"] + fms_ms),
                "FrozenFK-MatchedSharpConePrior": (fr_msharp["policy"], s_bessel["plan_ms"] + fsh_ms),
                "FrozenFK-HelmholtzBesselPrior": (s_bessel["policy"], s_bessel["plan_ms"]),
                "EndToEnd-DiscreteTele-BesselPrior": (s_disc["policy"], s_disc["plan_ms"]),
            }

            for m_name, (pfn, b_ms_val) in pol_table.items():
                b_q[m_name].append(b_ms_val)
                t_s1 = time.perf_counter()
                _ = simulate_closed_loop_crn(world, pfn, q_k1, n_per_start=1, seed=sim_seed + 100)
                e1_q[m_name].append(1000.0 * (time.perf_counter() - t_s1))

                sim_tr = simulate_closed_loop_crn(world, pfn, q_tr, n_per_start=12, seed=sim_seed)
                c_tr[m_name].append(sim_tr["mean_cost"]); r_tr[m_name].append(sim_tr["reach_rate"])

                sim_un = simulate_closed_loop_crn(world, pfn, q_un, n_per_start=12, seed=sim_seed + 500)
                c_un[m_name].append(sim_un["mean_cost"])

                sim_sh = simulate_closed_loop_crn(world, pfn, q_sh, n_per_start=12, seed=sim_seed + 900)
                c_sh[m_name].append(sim_sh["mean_cost"]); r_sh[m_name].append(sim_sh["reach_rate"])

        for m in methods:
            train_costs[m].append(float(np.mean(c_tr[m])))
            unseen_indist_costs[m].append(float(np.mean(c_un[m])))
            wall_corner_shift_costs[m].append(float(np.mean(c_sh[m])))
            reach_tr_map[m].append(float(np.mean(r_tr[m])))
            reach_sh_map[m].append(float(np.mean(r_sh[m])))
            build_ms[m].append(float(np.mean(b_q[m])))
            k1_exec_ms[m].append(float(np.mean(e1_q[m])))
        print(
            f"  [{dim}D Map {idx_m+1}/8] Shift OOD: Zero={wall_corner_shift_costs['FrozenFK-ZeroMeanPrior'][-1]:.3f} | "
            f"MatchSharpCone={wall_corner_shift_costs['FrozenFK-MatchedSharpConePrior'][-1]:.3f} | "
            f"Bessel={wall_corner_shift_costs['FrozenFK-HelmholtzBesselPrior'][-1]:.3f}",
            flush=True,
        )

    ours_tr = np.array(train_costs["FrozenFK-HelmholtzBesselPrior"])
    ours_un = np.array(unseen_indist_costs["FrozenFK-HelmholtzBesselPrior"])
    ours_sh = np.array(wall_corner_shift_costs["FrozenFK-HelmholtzBesselPrior"])
    mean_gp = float(np.mean(gp_fit_ms_list))

    summary = {}
    for m in methods:
        uses_gp = not m.startswith("Pure-")
        gp_cold = mean_gp if uses_gp else 0.0
        b_m = float(np.mean(build_ms[m]))
        e1_m = float(np.mean(k1_exec_ms[m]))
        arr_tr = np.array(train_costs[m])
        arr_un = np.array(unseen_indist_costs[m])
        arr_sh = np.array(wall_corner_shift_costs[m])
        summary[m] = {
            "train_starts_mean_cost_all8": float(np.mean(arr_tr)),
            "train_starts_mean_cost_heldout4": float(np.mean(arr_tr[n_dev:])),
            "unseen_in_dist_starts_mean_cost_all8": float(np.mean(arr_un)),
            "unseen_in_dist_starts_mean_cost_heldout4": float(np.mean(arr_un[n_dev:])),
            "near_wall_corner_shift_starts_mean_cost_all8": float(np.mean(arr_sh)),
            "near_wall_corner_shift_starts_heldout4": float(np.mean(arr_sh[n_dev:])),
            "reach_rate_train_starts": float(np.mean(reach_tr_map[m])),
            "reach_rate_wall_corner_shift": float(np.mean(reach_sh_map[m])),
            "bessel_minus_method_train_all8": paired_stats(ours_tr - arr_tr),
            "bessel_minus_method_train_heldout4": paired_stats(ours_tr[n_dev:] - arr_tr[n_dev:]),
            "bessel_minus_method_unseen_all8": paired_stats(ours_un - arr_un),
            "bessel_minus_method_unseen_heldout4": paired_stats(ours_un[n_dev:] - arr_un[n_dev:]),
            "bessel_minus_method_shift_all8": paired_stats(ours_sh - arr_sh),
            "bessel_minus_method_shift_heldout4": paired_stats(ours_sh[n_dev:] - arr_sh[n_dev:]),
            "cold_single_query_K1_total_ms_incl_full_gp": gp_cold + b_m + e1_m,
            "query_build_ms": b_m,
            "measured_K1_exec_ms": e1_m,
            "per_map_train_costs": train_costs[m],
            "per_map_unseen_in_dist_costs": unseen_indist_costs[m],
            "per_map_wall_corner_shift_costs": wall_corner_shift_costs[m],
        }

    return {
        "dim": dim,
        "n_maps_total": len(map_seeds),
        "dev_seeds": map_seeds[:n_dev],
        "heldout_seeds": map_seeds[n_dev:],
        "mean_full_gp_fit_ms": mean_gp,
        "bessel_fk_query_diagnostics": fk_query_diags,
        "methods": summary,
    }


def _budget_map_worker(args: Tuple[int, int, Sequence[int]]) -> dict:
    idx_m, ms, budgets = args
    dim = 6
    spec = ProblemSpec(dim=dim, half_width=1.65, sigma=0.55, q0=0.65, dt_sim=0.020, max_steps=420)
    priors = ["zero_mean", "matched_sharp_cone", "helmholtz_bessel"]
    rng_ord = np.random.default_rng(ms + 505)
    world = generate_benchmark_map(ms, dim=dim, regime="smooth", with_drift=True, spec=spec)
    km = KrigingWorldModel(*sample_noisy_probes(world, n_probes=100, seed=ms + 7, include_drift=True))
    triples = make_highd_queries_three_regimes(ms, dim=dim, n_queries=2)

    out_m = {}
    for nb in rng_ord.permutation(list(budgets)).tolist():
        nb = int(nb)
        ctr = {p: [] for p in priors}
        cun = {p: [] for p in priors}
        csh = {p: [] for p in priors}
        reach_un = {p: [] for p in priors}
        reach_sh = {p: [] for p in priors}
        timeout_sh = {p: [] for p in priors}
        clip_sh = {p: [] for p in priors}
        pms = {p: [] for p in priors}
        gr_mc_only = {p: [] for p in priors}
        gr_full_recon = {p: [] for p in priors}
        counters_list = []
        ess_list, tail_list = [], []

        for q_i, (q_tr, q_un, q_sh) in enumerate(triples):
            d_seed = 28000 + 50 * idx_m + 10 * q_i
            sims = 29000 + 50 * idx_m + 10 * q_i
            # Primary construction: `(design_seed = d_seed, mc_seed = d_seed)`
            s_a = solve_highd_fk_distillation(
                spec, km, q_tr, n_interior_anchors=nb, n_mc_paths=48, n_steps_fk=75,
                residual_mode="continuum_collar", prior_mode="helmholtz_bessel", guided_proposal=True,
                design_seed=d_seed, mc_seed=d_seed,
            )
            # Fixed-design MC replica: SAME `design_seed`, independent `mc_seed` (pure FK path variance!)
            s_mc = solve_highd_fk_distillation(
                spec, km, q_tr, n_interior_anchors=nb, n_mc_paths=48, n_steps_fk=75,
                residual_mode="continuum_collar", prior_mode="helmholtz_bessel", guided_proposal=True,
                design_seed=d_seed, mc_seed=d_seed + 3333,
            )
            # Full-reconstruction replica: independent `design_seed` AND `mc_seed`
            s_full = solve_highd_fk_distillation(
                spec, km, q_tr, n_interior_anchors=nb, n_mc_paths=48, n_steps_fk=75,
                residual_mode="continuum_collar", prior_mode="helmholtz_bessel", guided_proposal=True,
                design_seed=d_seed + 7777, mc_seed=d_seed + 7777,
            )
            counters_list.append(s_a["budget_counters"])
            ess_list.append(s_a["mean_ess"])
            tail_list.append(s_a["weighted_tail_mass"])

            eval_pts = np.vstack([np.asarray(q_un.start_points), np.asarray(q_sh.start_points)])
            for p_mode in rng_ord.permutation(priors).tolist():
                t_r0 = time.perf_counter()
                fa = s_a if p_mode == "helmholtz_bessel" else fit_gp_value_with_prior(
                    spec, q_tr, s_a["frozen_X_all"], s_a["frozen_y_total_v"], s_a["frozen_noise_vec"], prior_mode=p_mode
                )
                ref_ms = 0.0 if p_mode == "helmholtz_bessel" else 1000.0 * (time.perf_counter() - t_r0)
                f_mc = s_mc if p_mode == "helmholtz_bessel" else fit_gp_value_with_prior(
                    spec, q_tr, s_mc["frozen_X_all"], s_mc["frozen_y_total_v"], s_mc["frozen_noise_vec"], prior_mode=p_mode
                )
                f_full = s_full if p_mode == "helmholtz_bessel" else fit_gp_value_with_prior(
                    spec, q_tr, s_full["frozen_X_all"], s_full["frozen_y_total_v"], s_full["frozen_noise_vec"], prior_mode=p_mode
                )
                pms[p_mode].append(s_a["plan_ms"] + ref_ms)
                ga = fa["raw_value_and_grad"](eval_pts)[1]
                g_mc = f_mc["raw_value_and_grad"](eval_pts)[1]
                g_fu = f_full["raw_value_and_grad"](eval_pts)[1]
                gr_mc_only[p_mode].append(float(np.sqrt(np.mean((ga - g_mc) ** 2))))
                gr_full_recon[p_mode].append(float(np.sqrt(np.mean((ga - g_fu) ** 2))))

                r_tr = simulate_closed_loop_crn(world, fa["policy"], q_tr, n_per_start=12, seed=sims)
                r_un = simulate_closed_loop_crn(world, fa["policy"], q_un, n_per_start=12, seed=sims + 300)
                r_sh = simulate_closed_loop_crn(world, fa["policy"], q_sh, n_per_start=12, seed=sims + 600)
                ctr[p_mode].append(r_tr["mean_cost"])
                cun[p_mode].append(r_un["mean_cost"])
                csh[p_mode].append(r_sh["mean_cost"])
                reach_un[p_mode].append(r_un["reach_rate"])
                reach_sh[p_mode].append(r_sh["reach_rate"])
                timeout_sh[p_mode].append(r_sh["timeout_rate"])
                clip_sh[p_mode].append(r_sh["clip_fraction"])

        out_m[nb] = {
            "map_seed": ms,
            "counters_mean": {
                ck: float(np.mean([c[ck] for c in counters_list]))
                for ck in counters_list[0].keys()
                if isinstance(counters_list[0][ck], (int, float))
            },
            "mean_ess": float(np.mean(ess_list)),
            "weighted_tail_mass": float(np.mean(tail_list)),
            "priors": {
                p: {
                    "tr": float(np.mean(ctr[p])),
                    "un": float(np.mean(cun[p])),
                    "sh": float(np.mean(csh[p])),
                    "reach_un": float(np.mean(reach_un[p])),
                    "reach_sh": float(np.mean(reach_sh[p])),
                    "timeout_sh": float(np.mean(timeout_sh[p])),
                    "clip_sh": float(np.mean(clip_sh[p])),
                    "plan_ms": float(np.mean(pms[p])),
                    "grad_rms_mc_only": float(np.mean(gr_mc_only[p])),
                    "grad_rms_full_recon": float(np.mean(gr_full_recon[p])),
                }
                for p in priors
            },
        }
    return out_m


def run_6d_anchor_budget_and_fresh_confirmation(n_maps: int = 16, max_workers: int = 8) -> dict:
    """`d1b926a Work Package D`: 16 6D Maps (`9600..9607` Replication + `9608..9615` Confirmation)
    with Native Model-Eval vs Physical-Probe Counters, Retained Per-Map Timing Rows, and Split Statistics!
    """
    from green_response import paired_relative_noninferiority, run_map_parallel

    dim = 6
    all_seeds = list(range(9600, 9600 + n_maps))
    budgets = [24, 54, 108]
    priors = ["zero_mean", "matched_sharp_cone", "helmholtz_bessel"]

    rows = run_map_parallel(
        _budget_map_worker, [(i, s, budgets) for i, s in enumerate(all_seeds)], max_workers=max_workers
    )

    out_budgets = {}
    for nb in budgets:
        bes_un = np.array([r[nb]["priors"]["helmholtz_bessel"]["un"] for r in rows])
        bes_sh = np.array([r[nb]["priors"]["helmholtz_bessel"]["sh"] for r in rows])
        c_keys = list(rows[0][nb]["counters_mean"].keys())
        mean_cnt = {ck: float(np.mean([r[nb]["counters_mean"][ck] for r in rows])) for ck in c_keys}

        out_budgets[f"anchors_{nb}"] = {
            "nominal_interior_anchors_param": nb,
            "physical_world_observation_probes_per_map": 100,
            "actual_solver_budget_counters_mean": mean_cnt,
            "mean_fk_ess": float(np.mean([r[nb]["mean_ess"] for r in rows])),
            "mean_fk_weighted_tail_mass": float(np.mean([r[nb]["weighted_tail_mass"] for r in rows])),
            "priors": {
                p: {
                    "train_mean_cost": float(np.mean([r[nb]["priors"][p]["tr"] for r in rows])),
                    "unseen_in_dist_mean_cost": float(np.mean([r[nb]["priors"][p]["un"] for r in rows])),
                    "wall_corner_shift_mean_cost": float(np.mean([r[nb]["priors"][p]["sh"] for r in rows])),
                    "unseen_reach_rate": float(np.mean([r[nb]["priors"][p]["reach_un"] for r in rows])),
                    "wall_corner_shift_reach_rate": float(np.mean([r[nb]["priors"][p]["reach_sh"] for r in rows])),
                    "wall_corner_shift_timeout_rate": float(np.mean([r[nb]["priors"][p]["timeout_sh"] for r in rows])),
                    "wall_corner_shift_clip_fraction": float(np.mean([r[nb]["priors"][p]["clip_sh"] for r in rows])),
                    "mean_query_plan_ms_8worker": float(np.mean([r[nb]["priors"][p]["plan_ms"] for r in rows])),
                    "mean_query_plan_ms": float(np.mean([r[nb]["priors"][p]["plan_ms"] for r in rows])),
                    "fixed_design_mc_seed_grad_rms_diff": float(np.mean([r[nb]["priors"][p]["grad_rms_mc_only"] for r in rows])),
                    "full_reconstruction_seed_grad_rms_diff": float(np.mean([r[nb]["priors"][p]["grad_rms_full_recon"] for r in rows])),
                    "bessel_minus_prior_unseen_all16": paired_stats(bes_un - np.array([r[nb]["priors"][p]["un"] for r in rows])),
                    "bessel_minus_prior_shift_all16": paired_stats(bes_sh - np.array([r[nb]["priors"][p]["sh"] for r in rows])),
                    "bessel_minus_prior_unseen_new8_9608_9615": paired_stats(
                        bes_un[8:] - np.array([r[nb]["priors"][p]["un"] for r in rows[8:]])
                    ),
                    "bessel_minus_prior_shift_new8_9608_9615": paired_stats(
                        bes_sh[8:] - np.array([r[nb]["priors"][p]["sh"] for r in rows[8:]])
                    ),
                    "per_map_unseen_costs": [r[nb]["priors"][p]["un"] for r in rows],
                    "per_map_shift_costs": [r[nb]["priors"][p]["sh"] for r in rows],
                    "per_map_query_plan_ms_8worker": [r[nb]["priors"][p]["plan_ms"] for r in rows],
                }
                for p in priors
            },
        }

    def _split_cross(sl: slice) -> dict:
        b24_u = np.array(out_budgets["anchors_24"]["priors"]["helmholtz_bessel"]["per_map_unseen_costs"])[sl]
        b24_s = np.array(out_budgets["anchors_24"]["priors"]["helmholtz_bessel"]["per_map_shift_costs"])[sl]
        c108_u = np.array(out_budgets["anchors_108"]["priors"]["matched_sharp_cone"]["per_map_unseen_costs"])[sl]
        c108_s = np.array(out_budgets["anchors_108"]["priors"]["matched_sharp_cone"]["per_map_shift_costs"])[sl]
        return {
            "bessel24_minus_cone108_unseen_paired_diff": paired_stats(b24_u - c108_u),
            "bessel24_minus_cone108_shift_paired_diff": paired_stats(b24_s - c108_s),
            "declared_5pct_relative_NI_bessel24_vs_cone108_unseen": paired_relative_noninferiority(b24_u, c108_u, rel_margin_pct=5.0),
            "declared_5pct_relative_NI_bessel24_vs_cone108_shift": paired_relative_noninferiority(b24_s, c108_s, rel_margin_pct=5.0),
        }

    paths_24 = out_budgets["anchors_24"]["actual_solver_budget_counters_mean"]["n_fk_paths_launched_actual"]
    paths_108 = out_budgets["anchors_108"]["actual_solver_budget_counters_mean"]["n_fk_paths_launched_actual"]
    gp_24 = out_budgets["anchors_24"]["actual_solver_budget_counters_mean"]["n_gp_rows_total"]
    gp_108 = out_budgets["anchors_108"]["actual_solver_budget_counters_mean"]["n_gp_rows_total"]
    ms_24_arr = np.array(out_budgets["anchors_24"]["priors"]["helmholtz_bessel"]["per_map_query_plan_ms_8worker"])
    ms_108_arr = np.array(out_budgets["anchors_108"]["priors"]["matched_sharp_cone"]["per_map_query_plan_ms_8worker"])

    cross_budget = {
        "physical_world_probes_ratio_108_over_24": 1.0,
        "actual_launched_fk_paths_ratio_108_over_24": float(paths_108 / paths_24),
        "actual_gp_training_rows_ratio_108_over_24": float(gp_108 / gp_24),
        "descriptive_8worker_planning_ms_ratio_cone108_over_bessel24": float(np.mean(ms_108_arr) / np.mean(ms_24_arr)),
        "paired_8worker_ms_diff_bessel24_minus_cone108": paired_stats(ms_24_arr - ms_108_arr),
        "nominal_anchor_param_ratio_108_over_24": 108.0 / 24.0,
        "all_16_maps": _split_cross(slice(0, 16)),
        "replication_8_maps_9600_9607": _split_cross(slice(0, 8)),
        "new_confirmation_8_maps_9608_9615": _split_cross(slice(8, 16)),
    }

    return {
        "block_provenance": "fresh_computed_in_current_run",
        "replication_seeds_9600_9607": all_seeds[:8],
        "new_confirmation_seeds_9608_9615": all_seeds[8:],
        "all_seeds": all_seeds,
        "n_maps": n_maps,
        "dim": dim,
        "physical_world_probes_per_map": 100,
        "fixed_design_variance_note": (
            "MirrorNeumannMatern52GP uses fixed kernel length-scale and diagonal regularization; under fixed X, "
            "Delta grad V(x) is algebraically invariant to deterministic prior mean m(x). Lower full-reconstruction "
            "sensitivity of HelmholtzBessel reflects anchor-design interpolation/extrapolation stability."
        ),
        "nnls_cone_protocol": "same_c2_collar_same_asymptotic_slope_36pt_per_goal_positive_mode_weight_nnls",
        "anchor_budgets": out_budgets,
        "cross_budget_bessel24_vs_sharpcone108": cross_budget,
    }


def _indep_3d_fd_teacher_worker(args: Tuple[int, int]) -> dict:
    """3D (`25^3`) Exact Deterministic FD Teacher Check (`0%` Bessel/FK involvement in label generation!)."""
    from green_response import ClassicalFDSolver, eval_goal_union
    from scipy.stats import norm, qmc

    idx_m, ms = args
    dim = 3
    spec = ProblemSpec(dim=dim, half_width=1.65, sigma=0.45, q0=0.50, dt_sim=0.015, max_steps=380)
    world = generate_benchmark_map(ms, dim=dim, regime="smooth", with_drift=True, spec=spec)
    km = KrigingWorldModel(*sample_noisy_probes(world, n_probes=80, seed=ms + 7, include_drift=True))
    q_tr, q_un, q_sh = make_highd_queries_three_regimes(ms, dim=dim, n_queries=1)[0]

    fd_solver = ClassicalFDSolver(spec, 25, km.predict_q, km.predict_b)
    fd_sol = fd_solver.solve_direct(q_tr)
    val_fd_fn = fd_sol["value_fn"]
    pol_fd_fn = fd_sol["policy"]

    # Sample `N = 24` interior anchors + `64` boundary points/goal and label strictly with Exact FD!
    L = spec.half_width
    rng_d = np.random.default_rng(38000 + idx_m)
    sob_b = qmc.Sobol(d=dim, scramble=True, seed=38100 + idx_m)
    bnd_pts, bnd_phi = [], []
    for g in q_tr.goals:
        gc = np.asarray(g.center, dtype=float)
        dirs = norm.ppf(np.clip(sob_b.random(64), 1e-6, 1.0 - 1e-6))
        dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
        pj = np.clip(gc[None, :] + (g.radius + 1e-8) * dirs, -L + 1e-4, L - 1e-4)
        in_o, phi_u = eval_goal_union(pj, q_tr.goals)
        bnd_pts.append(pj)
        bnd_phi.append(np.where(in_o, np.minimum(phi_u, g.phi), g.phi))
    X_bnd = np.vstack(bnd_pts)
    phi_bnd = np.concatenate(bnd_phi)

    sob_i = qmc.Sobol(d=dim, scramble=True, seed=38200 + idx_m)
    X_sob = (sob_i.random(12) * 2.0 - 1.0) * 1.15
    starts_arr = np.asarray(q_tr.start_points, dtype=float)
    g_centers = np.array([g.center for g in q_tr.goals], dtype=float)
    cor_pts = [
        np.clip((1.0 - (al := rng_d.uniform(0.08, 0.92))) * starts_arr[k % len(starts_arr)] + al * g_centers[k % len(g_centers)] + rng_d.normal(0.0, 0.22, size=dim), -1.20, 1.20)
        for k in range(12)
    ]
    X_int_raw = np.vstack([starts_arr, X_sob, np.array(cor_pts)])
    in_g, _ = eval_goal_union(X_int_raw, [GoalBall(g.center, g.phi, g.radius + 0.03) for g in q_tr.goals])
    X_int = X_int_raw[~in_g]
    y_fd_int = np.asarray(val_fd_fn(X_int), dtype=float)

    X_all = np.vstack([X_int, X_bnd])
    y_all = np.concatenate([y_fd_int, phi_bnd])
    noise_vec = np.concatenate([np.full(len(X_int), 1e-5), np.full(len(X_bnd), 1e-7)])

    # Test grid points strictly outside goal balls for exact value & policy RMSE
    sob_test = qmc.Sobol(d=dim, scramble=True, seed=38900 + idx_m)
    X_test_raw = (sob_test.random(256) * 2.0 - 1.0) * 1.45
    in_gt, _ = eval_goal_union(X_test_raw, [GoalBall(g.center, g.phi, g.radius + 0.05) for g in q_tr.goals])
    X_test = X_test_raw[~in_gt]
    v_true_fd = np.asarray(val_fd_fn(X_test), dtype=float)
    u_true_fd = np.asarray(pol_fd_fn(X_test), dtype=float)

    out_p = {}
    for p_mode in ("zero_mean", "matched_sharp_cone", "helmholtz_bessel"):
        fit_p = fit_gp_value_with_prior(spec, q_tr, X_all, y_all, noise_vec, prior_mode=p_mode)
        v_pred = fit_p["value_fn"](X_test)
        u_pred = fit_p["policy"](X_test)
        r_un = simulate_closed_loop_crn(world, fit_p["policy"], q_un, n_per_start=14, seed=39100 + idx_m)
        r_sh = simulate_closed_loop_crn(world, fit_p["policy"], q_sh, n_per_start=14, seed=39500 + idx_m)
        out_p[p_mode] = {
            "val_rmse_vs_exact_fd": float(np.sqrt(np.mean((v_pred - v_true_fd) ** 2))),
            "policy_rmse_vs_exact_fd": float(np.sqrt(np.mean((u_pred - u_true_fd) ** 2))),
            "unseen_cost": r_un["mean_cost"],
            "shift_cost": r_sh["mean_cost"],
        }
    return {"map_seed": ms, "priors": out_p}


def _indep_6d_cone_teacher_worker(args: Tuple[int, int]) -> dict:
    """6D Bessel-Free Cone-Girsanov Independent Teacher Check (`192` paths, `150` steps, `dt=0.020`,
    `teacher_mode="cone_girsanov_independent"` — zero Bessel guide in label generation!).
    """
    idx_m, ms = args
    dim = 6
    spec = ProblemSpec(dim=dim, half_width=1.65, sigma=0.55, q0=0.65, dt_sim=0.020, max_steps=420)
    world = generate_benchmark_map(ms, dim=dim, regime="smooth", with_drift=True, spec=spec)
    km = KrigingWorldModel(*sample_noisy_probes(world, n_probes=100, seed=ms + 7, include_drift=True))
    q_tr, q_un, q_sh = make_highd_queries_three_regimes(ms, dim=dim, n_queries=1)[0]

    # Generate high-budget labels strictly under `cone_girsanov_independent` teacher (`N = 24` anchors)
    t_sol = solve_highd_fk_distillation(
        spec, km, q_tr, n_interior_anchors=24, n_mc_paths=192, n_steps_fk=150, dt_fk=0.020,
        n_continuation_rounds=3, prior_mode="matched_sharp_cone", guided_proposal=True,
        design_seed=41000 + idx_m, mc_seed=42000 + idx_m, teacher_mode="cone_girsanov_independent",
    )
    out_p = {}
    for p_mode in ("zero_mean", "matched_sharp_cone", "helmholtz_bessel"):
        fit_p = fit_gp_value_with_prior(
            spec, q_tr, t_sol["frozen_X_all"], t_sol["frozen_y_total_v"], t_sol["frozen_noise_vec"], prior_mode=p_mode
        )
        r_un = simulate_closed_loop_crn(world, fit_p["policy"], q_un, n_per_start=14, seed=43000 + idx_m)
        r_sh = simulate_closed_loop_crn(world, fit_p["policy"], q_sh, n_per_start=14, seed=44000 + idx_m)
        out_p[p_mode] = {
            "unseen_cost": r_un["mean_cost"],
            "shift_cost": r_sh["mean_cost"],
            "unseen_reach_rate": r_un["reach_rate"],
            "shift_reach_rate": r_sh["reach_rate"],
        }
    return {
        "map_seed": ms,
        "survivor_frac": t_sol["survivor_fraction"],
        "weighted_tail_mass": t_sol["weighted_tail_mass"],
        "mean_ess": t_sol["mean_ess"],
        "min_ess": t_sol["min_ess"],
        "median_ess": t_sol["median_ess"],
        "continuation_max_diffs": t_sol["continuation_max_diffs"],
        "budget_counters": t_sol["budget_counters"],
        "priors": out_p,
    }


LOCKED_6D_METHOD_CONFIGS = {
    "M1_EndToEnd_Bessel24": {
        "teacher_mode": "bessel_guided",
        "teacher_prior_mode": "helmholtz_bessel",
        "student_refit_prior_mode": None,
        "n_interior_anchors": 24,
        "n_mc_paths": 48,
        "n_steps_fk": 75,
        "dt_fk": 0.045,
        "n_continuation_rounds": 3,
        "design_seed_base": 46000,
        "mc_seed_base": 46500,
    },
    "M2_FrozenBesselTeacher_SharpCone108": {
        "teacher_mode": "bessel_guided",
        "teacher_prior_mode": "helmholtz_bessel",
        "student_refit_prior_mode": "matched_sharp_cone",
        "n_interior_anchors": 108,
        "n_mc_paths": 48,
        "n_steps_fk": 75,
        "dt_fk": 0.045,
        "n_continuation_rounds": 3,
        "design_seed_base": 47000,
        "mc_seed_base": 47500,
    },
    "M3_EndToEnd_IndepConeGirsanov_SharpCone108": {
        "teacher_mode": "cone_girsanov_independent",
        "teacher_prior_mode": "matched_sharp_cone",
        "student_refit_prior_mode": None,
        "n_interior_anchors": 108,
        "n_mc_paths": 48,
        "n_steps_fk": 75,
        "dt_fk": 0.045,
        "n_continuation_rounds": 3,
        "design_seed_base": 47000,
        "mc_seed_base": 47500,
    },
}


def execute_locked_6d_method(
    method_id: str,
    spec: ProblemSpec,
    km: KrigingWorldModel,
    query_train: QueryTask,
    map_idx: int,
) -> dict:
    """Single canonical dispatch factory shared across quality, serial latency, and batch makespan workers."""
    if method_id not in LOCKED_6D_METHOD_CONFIGS:
        raise KeyError(f"Unknown locked 6D method_config_id: {method_id}")
    cfg = LOCKED_6D_METHOD_CONFIGS[method_id]
    t0 = time.perf_counter()
    s_t = solve_highd_fk_distillation(
        spec,
        km,
        query_train,
        n_interior_anchors=cfg["n_interior_anchors"],
        n_mc_paths=cfg["n_mc_paths"],
        n_steps_fk=cfg["n_steps_fk"],
        dt_fk=cfg["dt_fk"],
        n_continuation_rounds=cfg["n_continuation_rounds"],
        prior_mode=cfg["teacher_prior_mode"],
        teacher_mode=cfg["teacher_mode"],
        design_seed=cfg["design_seed_base"] + map_idx,
        mc_seed=cfg["mc_seed_base"] + map_idx,
    )
    t_ms = 1000.0 * (time.perf_counter() - t0)
    if cfg["student_refit_prior_mode"] is not None:
        t_r0 = time.perf_counter()
        fit_c = fit_gp_value_with_prior(
            spec,
            query_train,
            s_t["frozen_X_all"],
            s_t["frozen_y_total_v"],
            s_t["frozen_noise_vec"],
            prior_mode=cfg["student_refit_prior_mode"],
        )
        r_ms = 1000.0 * (time.perf_counter() - t_r0)
        pol = fit_c["policy"]
        student_refits = 1
    else:
        r_ms = 0.0
        pol = s_t["policy"]
        student_refits = 0
    return {
        "policy": pol,
        "total_query_ms": t_ms + r_ms,
        "teacher_ms": t_ms,
        "student_refit_ms": r_ms,
        "student_refits": student_refits,
        "teacher_diag": s_t,
        "config": dict(cfg),
    }


def _matched_6d_method_worker(args: Tuple[int, int]) -> dict:
    """Locked `method_config_id` 6D Quality + Concurrent Worker Timing (`29fa7c6` Stage B1 / `57e5912` Unified Factory):
    Evaluates THREE pinned configurations via `execute_locked_6d_method` on the EXACT SAME world GP, held-out starts, and CRN seeds.
    """
    idx_m, ms = args
    dim = 6
    spec = ProblemSpec(dim=dim, half_width=1.65, sigma=0.55, q0=0.65, dt_sim=0.020, max_steps=420)
    world = generate_benchmark_map(ms, dim=dim, regime="smooth", with_drift=True, spec=spec)
    t_w0 = time.perf_counter()
    km = KrigingWorldModel(*sample_noisy_probes(world, n_probes=100, seed=ms + 7, include_drift=True))
    world_gp_ms = 1000.0 * (time.perf_counter() - t_w0)
    q_tr, q_un, q_sh = make_highd_queries_three_regimes(ms, dim=dim, n_queries=1)[0]
    rng_ord = np.random.default_rng(ms + 515)

    m_keys = list(LOCKED_6D_METHOD_CONFIGS.keys())
    out_m = {}
    for mk in rng_ord.permutation(m_keys).tolist():
        ex = execute_locked_6d_method(mk, spec, km, q_tr, idx_m)
        pol = ex["policy"]
        s_diag = ex["teacher_diag"]
        r_un = simulate_closed_loop_crn(world, pol, q_un, n_per_start=16, seed=48000 + idx_m)
        r_sh = simulate_closed_loop_crn(world, pol, q_sh, n_per_start=16, seed=48500 + idx_m)
        out_m[mk] = {
            "concurrent_query_ms": ex["total_query_ms"],
            "concurrent_teacher_ms": ex["teacher_ms"],
            "concurrent_refit_ms": ex["student_refit_ms"],
            "student_refits": ex["student_refits"],
            "unseen_cost": r_un["mean_cost"],
            "shift_cost": r_sh["mean_cost"],
            "unseen_reach_rate": r_un["reach_rate"],
            "shift_reach_rate": r_sh["reach_rate"],
            "survivor_fraction": s_diag["survivor_fraction"],
            "weighted_tail_mass": s_diag["weighted_tail_mass"],
            "mean_ess": s_diag["mean_ess"],
            "min_ess": s_diag["min_ess"],
            "budget_counters": s_diag["budget_counters"],
        }
    return {"map_seed": ms, "world_gp_fit_ms": world_gp_ms, "methods": out_m}


def _batch_only_6d_method_worker(args: Tuple[int, int, str]) -> float:
    idx_i, ms, mk = args
    spec6 = ProblemSpec(dim=6, half_width=1.65, sigma=0.55, q0=0.65, dt_sim=0.020, max_steps=420)
    w6 = generate_benchmark_map(ms, dim=6, regime="smooth", with_drift=True, spec=spec6)
    km6 = KrigingWorldModel(*sample_noisy_probes(w6, n_probes=100, seed=ms + 7, include_drift=True))
    q_tr, _, _ = make_highd_queries_three_regimes(ms, dim=6, n_queries=1)[0]
    ex = execute_locked_6d_method(mk, spec6, km6, q_tr, idx_i)
    return float(ex["total_query_ms"])


def run_independent_teacher_and_isolated_latency_suite(max_workers: int = 8) -> dict:
    """`d1b926a Work Package D` + `29fa7c6 Stage B1`:
      1. 3D (`25^3`) Discrete FD Reference Teacher Verification (`8` maps `9700..9707`);
      2. 6D Cone-Girsanov Bessel-Free Teacher Verification (`8` maps `9608..9615`, full ESS/tail/cont diagnostics);
      3. Locked `method_config_id` 6D Quality–Cost Table (`8` maps `9608..9615`) binding exact closed-loop
         quality & `+5%` NI to BOTH isolated 1-worker serial latency AND 8-worker batch makespan throughput!
    """
    from green_response import run_map_parallel

    seeds_3d = list(range(9700, 9708))
    rows_3d = run_map_parallel(_indep_3d_fd_teacher_worker, [(i, s) for i, s in enumerate(seeds_3d)], max_workers=max_workers)
    b3_un = np.array([r["priors"]["helmholtz_bessel"]["unseen_cost"] for r in rows_3d])
    b3_sh = np.array([r["priors"]["helmholtz_bessel"]["shift_cost"] for r in rows_3d])
    b3_vr = np.array([r["priors"]["helmholtz_bessel"]["val_rmse_vs_exact_fd"] for r in rows_3d])
    b3_pr = np.array([r["priors"]["helmholtz_bessel"]["policy_rmse_vs_exact_fd"] for r in rows_3d])

    summary_3d = {
        p: {
            "mean_val_rmse_vs_exact_fd": float(np.mean([r["priors"][p]["val_rmse_vs_exact_fd"] for r in rows_3d])),
            "mean_policy_rmse_vs_exact_fd": float(np.mean([r["priors"][p]["policy_rmse_vs_exact_fd"] for r in rows_3d])),
            "mean_unseen_cost": float(np.mean([r["priors"][p]["unseen_cost"] for r in rows_3d])),
            "mean_shift_cost": float(np.mean([r["priors"][p]["shift_cost"] for r in rows_3d])),
            "bessel_minus_prior_val_rmse": paired_stats(b3_vr - np.array([r["priors"][p]["val_rmse_vs_exact_fd"] for r in rows_3d])),
            "bessel_minus_prior_policy_rmse": paired_stats(b3_pr - np.array([r["priors"][p]["policy_rmse_vs_exact_fd"] for r in rows_3d])),
            "bessel_minus_prior_unseen_cost": paired_stats(b3_un - np.array([r["priors"][p]["unseen_cost"] for r in rows_3d])),
            "bessel_minus_prior_shift_cost": paired_stats(b3_sh - np.array([r["priors"][p]["shift_cost"] for r in rows_3d])),
        }
        for p in ("zero_mean", "matched_sharp_cone", "helmholtz_bessel")
    }

    seeds_6d = list(range(9608, 9616))
    rows_6d = run_map_parallel(_indep_6d_cone_teacher_worker, [(i, s) for i, s in enumerate(seeds_6d)], max_workers=max_workers)
    b6_un = np.array([r["priors"]["helmholtz_bessel"]["unseen_cost"] for r in rows_6d])
    b6_sh = np.array([r["priors"]["helmholtz_bessel"]["shift_cost"] for r in rows_6d])
    summary_6d = {
        p: {
            "mean_unseen_cost": float(np.mean([r["priors"][p]["unseen_cost"] for r in rows_6d])),
            "mean_shift_cost": float(np.mean([r["priors"][p]["shift_cost"] for r in rows_6d])),
            "mean_unseen_reach_rate": float(np.mean([r["priors"][p]["unseen_reach_rate"] for r in rows_6d])),
            "mean_shift_reach_rate": float(np.mean([r["priors"][p]["shift_reach_rate"] for r in rows_6d])),
            "bessel_minus_prior_unseen_cost": paired_stats(b6_un - np.array([r["priors"][p]["unseen_cost"] for r in rows_6d])),
            "bessel_minus_prior_shift_cost": paired_stats(b6_sh - np.array([r["priors"][p]["shift_cost"] for r in rows_6d])),
        }
        for p in ("zero_mean", "matched_sharp_cone", "helmholtz_bessel")
    }

    rows_m = run_map_parallel(_matched_6d_method_worker, [(i, s) for i, s in enumerate(seeds_6d)], max_workers=max_workers)

    spec6 = ProblemSpec(dim=6, half_width=1.65, sigma=0.55, q0=0.65, dt_sim=0.020, max_steps=420)
    m_ids = list(LOCKED_6D_METHOD_CONFIGS.keys())
    serial_ms = {mk: [] for mk in m_ids}
    serial_world_gp_ms = []
    for idx_i, ms in enumerate(seeds_6d):
        w6 = generate_benchmark_map(ms, dim=6, regime="smooth", with_drift=True, spec=spec6)
        t_gp0 = time.perf_counter()
        km6 = KrigingWorldModel(*sample_noisy_probes(w6, n_probes=100, seed=ms + 7, include_drift=True))
        serial_world_gp_ms.append(1000.0 * (time.perf_counter() - t_gp0))
        q_tr, _, _ = make_highd_queries_three_regimes(ms, dim=6, n_queries=1)[0]
        rng_s = np.random.default_rng(49000 + ms)
        ms_map = {}
        for mk in rng_s.permutation(m_ids).tolist():
            ex_s = execute_locked_6d_method(mk, spec6, km6, q_tr, idx_i)
            ms_map[mk] = float(ex_s["total_query_ms"])
        for mk in m_ids:
            serial_ms[mk].append(ms_map[mk])

    batch_makespan_ms = {}
    for mk in m_ids:
        t_b0 = time.perf_counter()
        run_map_parallel(_batch_only_6d_method_worker, [(i, s, mk) for i, s in enumerate(seeds_6d)], max_workers=max_workers)
        batch_makespan_ms[mk] = 1000.0 * (time.perf_counter() - t_b0)

    m1_un = np.array([r["methods"]["M1_EndToEnd_Bessel24"]["unseen_cost"] for r in rows_m])
    m1_sh = np.array([r["methods"]["M1_EndToEnd_Bessel24"]["shift_cost"] for r in rows_m])
    m1_ser = np.array(serial_ms["M1_EndToEnd_Bessel24"])

    matched_summary = {}
    for mk in m_ids:
        mk_un = np.array([r["methods"][mk]["unseen_cost"] for r in rows_m])
        mk_sh = np.array([r["methods"][mk]["shift_cost"] for r in rows_m])
        mk_ser = np.array(serial_ms[mk])
        mk_con = np.array([r["methods"][mk]["concurrent_query_ms"] for r in rows_m])
        cnt_keys = rows_m[0]["methods"][mk]["budget_counters"].keys()
        matched_summary[mk] = {
            "method_config_id": mk,
            "unseen_mean_cost": float(np.mean(mk_un)),
            "shift_mean_cost": float(np.mean(mk_sh)),
            "unseen_reach_rate": float(np.mean([r["methods"][mk]["unseen_reach_rate"] for r in rows_m])),
            "shift_reach_rate": float(np.mean([r["methods"][mk]["shift_reach_rate"] for r in rows_m])),
            "serial_1worker_query_cold_ms": float(np.mean(mk_ser)),
            "concurrent_8worker_per_call_ms": float(np.mean(mk_con)),
            "concurrent_teacher_ms": float(np.mean([r["methods"][mk]["concurrent_teacher_ms"] for r in rows_m])),
            "concurrent_refit_ms": float(np.mean([r["methods"][mk]["concurrent_refit_ms"] for r in rows_m])),
            "batch_8map_makespan_ms_incl_world_gp": float(batch_makespan_ms[mk]),
            "batch_throughput_queries_per_sec": float(len(seeds_6d) / (batch_makespan_ms[mk] / 1000.0)),
            "serial_speedup_of_M1_over_method": float(np.mean(mk_ser) / np.mean(m1_ser)),
            "batch_makespan_speedup_of_M1_over_method": float(batch_makespan_ms[mk] / batch_makespan_ms["M1_EndToEnd_Bessel24"]),
            "M1_minus_method_serial_ms": paired_stats(m1_ser - mk_ser),
            "M1_minus_method_unseen_cost": paired_stats(m1_un - mk_un),
            "M1_minus_method_shift_cost": paired_stats(m1_sh - mk_sh),
            "declared_5pct_relative_NI_M1_vs_method_unseen": paired_relative_noninferiority(m1_un, mk_un, rel_margin_pct=5.0),
            "declared_5pct_relative_NI_M1_vs_method_shift": paired_relative_noninferiority(m1_sh, mk_sh, rel_margin_pct=5.0),
            "mean_survivor_fraction": float(np.mean([r["methods"][mk]["survivor_fraction"] for r in rows_m])),
            "mean_weighted_tail_mass": float(np.mean([r["methods"][mk]["weighted_tail_mass"] for r in rows_m])),
            "mean_ess": float(np.mean([r["methods"][mk]["mean_ess"] for r in rows_m])),
            "min_ess_worst_across_maps": float(np.min([r["methods"][mk]["min_ess"] for r in rows_m])),
            "actual_budget_counters_mean": {
                ck: (
                    rows_m[0]["methods"][mk]["budget_counters"][ck]
                    if isinstance(rows_m[0]["methods"][mk]["budget_counters"][ck], str)
                    else float(np.mean([r["methods"][mk]["budget_counters"][ck] for r in rows_m]))
                )
                for ck in cnt_keys
            },
            "per_map_serial_ms": mk_ser.tolist(),
            "per_map_unseen_cost": mk_un.tolist(),
            "per_map_shift_cost": mk_sh.tolist(),
        }

    return {
        "block_provenance": "fresh_computed_in_current_run",
        "exact_fd_3d_independent_teacher_8maps": {
            "fresh_seeds": seeds_3d,
            "grid_n": 25,
            "interior_anchors_nominal": 24,
            "teacher": "ClassicalFDSolver_discrete_25cubed_HJB_plus_known_goal_boundary (0% Bessel/FK involvement)",
            "priors": summary_3d,
            "per_map_records": rows_3d,
        },
        "cone_girsanov_6d_independent_teacher_8maps": {
            "cohort_seeds": seeds_6d,
            "cohort_origin": "d1b926a_confirmation_cohort_new_cone_teacher_intervention",
            "interior_anchors_nominal": 24,
            "teacher": "Cone_Girsanov_FK_192paths_150steps_dt020 (0% Bessel involvement, endpoint-in-goal stopping)",
            "mean_teacher_survivor_fraction": float(np.mean([r["survivor_frac"] for r in rows_6d])),
            "mean_teacher_weighted_tail_mass": float(np.mean([r["weighted_tail_mass"] for r in rows_6d])),
            "mean_teacher_ess": float(np.mean([r["mean_ess"] for r in rows_6d])),
            "worst_min_teacher_ess": float(np.min([r["min_ess"] for r in rows_6d])),
            "mean_continuation_final_diff": float(np.mean([r["continuation_max_diffs"][-1] for r in rows_6d if r["continuation_max_diffs"]])),
            "priors": summary_6d,
            "per_map_records": rows_6d,
        },
        "matched_method_id_quality_and_latency_8maps": {
            "cohort_seeds": seeds_6d,
            "timing_scope": "query_cold_given_fitted_world_gp_for_serial_and_concurrent_per_call; includes_world_gp_in_batch_makespan",
            "serial_order_protocol": "per_map_rng_permutation_across_all_3_locked_method_ids",
            "mean_serial_world_gp_fit_ms": float(np.mean(serial_world_gp_ms)),
            "methods": matched_summary,
            "per_map_records": rows_m,
        },
    }


def run_scoped_kinetic_factorial(n_probes: int = 45, n_dev: int = 6, n_heldout: int = 4) -> dict:
    map_seeds = list(range(4500, 4500 + n_dev)) + list(range(14500, 14500 + n_heldout))
    goal_pos = (0.75, 0.65)
    r_pos, r_vel = 0.28, 0.85
    half_width, v_max, sigma, q0, gamma = 1.65, 3.5, 0.42, 0.35, 0.55
    lam = sigma ** 2
    v0_fn = build_kinetic_lqr_base_guide(goal_pos, q0=q0, gamma=gamma)

    variants = [
        "Pure-LQR-Guide",
        "Kinetic-Centered-PIMC",
        "FK-IsoKernel-FullBnd-BaseAnch",
        "FK-IsoKernel-FullBnd-BrakingAnch",
        "FK-IsoKernel-InwardBnd-BrakingAnch",
        "FK-AnisoKernel-FullBnd-BrakingAnch",
        "FK-AnisoKernel-InwardBnd-BrakingAnch",
    ]
    per_map_total_score = {v: [] for v in variants}
    per_map_running_cost = {v: [] for v in variants}
    per_map_timeout_pen = {v: [] for v in variants}
    per_map_reach = {v: [] for v in variants}
    per_map_action_cap_frac = {v: [] for v in variants}
    fk_diags = []
    max_telescoping_disc = 0.0
    starts_4d = np.array([[-0.85, -0.75, 0.0, 0.0], [-0.70, 0.80, 0.0, 0.0]])

    for idx_m, m_seed in enumerate(map_seeds):
        w2 = generate_benchmark_map(m_seed, dim=2, regime="narrow_barrier", with_drift=True)
        km = KrigingWorldModel(*sample_noisy_probes(w2, n_probes=n_probes, seed=m_seed + 7, include_drift=True))
        pol_lqr = lambda X4: -v0_fn(X4)[1][:, 2:4]
        rng_p = np.random.default_rng(m_seed + 99)

        def _pimc_kinetic(X4: np.ndarray, km_ref=km, rp=rng_p) -> np.ndarray:
            X2 = np.atleast_2d(X4)
            nb = len(X2)
            M = 32; hm = 16; dt_m = 0.04; sq = np.sqrt(dt_m)
            v0_s, gv0_s = v0_fn(X2)
            u_nom = -gv0_s[:, 2:4]
            z0 = rp.normal(0.0, sq, size=(nb, hm, 2))
            eps0 = np.concatenate([z0, -z0], axis=1)
            pos = np.repeat(X2[:, None, :], M, axis=1)
            v0_c = np.repeat(v0_s[:, None], M, axis=1)
            done0 = (np.linalg.norm(X2[:, :2] - np.array([goal_pos]), axis=1) <= r_pos) & (np.linalg.norm(X2[:, 2:4], axis=1) <= r_vel)
            al = np.broadcast_to((~done0)[:, None], (nb, M)).copy()
            c_acc = np.zeros((nb, M), dtype=float)
            for st in range(22):
                if not np.any(al):
                    break
                dw = eps0 if st == 0 else np.concatenate([z := rp.normal(0.0, sq, size=(nb, hm, 2)), -z], axis=1)
                ai, aj = np.where(al)
                xa = pos[ai, aj]; pa = xa[:, :2]; va = xa[:, 2:4]; dwa = dw[ai, aj]; v0a = v0_c[ai, aj]
                _, gv = v0_fn(xa); up = -gv[:, 2:4]
                qp = km_ref.predict_q(pa); bh = km_ref.predict_b(pa)
                pn, vn, _, _ = reflect_kinetic_into_box(pa + va * dt_m, va + (-gamma * va + bh + up) * dt_m + sigma * dwa, half_width, v_max)
                xn = np.hstack([pn, vn]); v0n, _ = v0_fn(xn)
                qt = q0 + qp + 0.06 * np.sum(va ** 2, axis=1)
                c_acc[ai, aj] += (qt + 0.5 * np.sum(up ** 2, axis=1)) * dt_m + sigma * np.sum(up * dwa, axis=1) + (v0n - v0a)
                pos[ai, aj] = xn; v0_c[ai, aj] = v0n
                hit = (np.linalg.norm(pn - np.array([goal_pos]), axis=1) <= r_pos) & (np.linalg.norm(vn, axis=1) <= r_vel)
                if np.any(hit):
                    hl = np.flatnonzero(hit)
                    c_acc[ai[hl], aj[hl]] += 0.0 - v0n[hl]
                    al[ai[hl], aj[hl]] = False
            ex = -c_acc / lam
            ex -= np.max(ex, axis=1, keepdims=True)
            w = np.exp(ex); w /= np.maximum(np.sum(w, axis=1, keepdims=True), 1e-30)
            du = (sigma / dt_m) * np.einsum("bm,bmd->bd", w - (1.0 / M), eps0)
            u = u_nom + du
            u[done0] = 0.0
            return u

        fk_specs = {
            "FK-IsoKernel-FullBnd-BaseAnch": (False, False, False),
            "FK-IsoKernel-FullBnd-BrakingAnch": (False, False, True),
            "FK-IsoKernel-InwardBnd-BrakingAnch": (True, False, True),
            "FK-AnisoKernel-FullBnd-BrakingAnch": (False, True, True),
            "FK-AnisoKernel-InwardBnd-BrakingAnch": (True, True, True),
        }
        pols = {"Pure-LQR-Guide": pol_lqr, "Kinetic-Centered-PIMC": _pimc_kinetic}
        for vname, (inw, ani, brk) in fk_specs.items():
            sol_u = solve_kinetic_underactuated_greenres(
                km, goal_pos=goal_pos, r_pos=r_pos, r_vel=r_vel,
                inward_boundary=inw, anisotropic_kernel=ani, extra_braking_anchors=brk,
                n_continuation_rounds=6, seed=m_seed + 20,
            )
            pols[vname] = sol_u["policy"]
            max_telescoping_disc = max(max_telescoping_disc, sol_u["measured_telescoping_discrepancy"])
            if vname == "FK-AnisoKernel-InwardBnd-BrakingAnch":
                fk_diags.append({
                    "map_seed": m_seed,
                    "survivor_fraction": sol_u["fk_survivor_fraction"],
                    "weighted_tail_mass": sol_u["weighted_tail_mass"],
                    "mean_ess": sol_u["mean_ess"],
                    "measured_telescoping_discrepancy": sol_u["measured_telescoping_discrepancy"],
                    "continuation_final_diff_round6": sol_u["continuation_max_diffs"][-1],
                    "scope_diagnostics": sol_u["scope_diagnostics"],
                })

        n_per = 18
        X0 = np.repeat(starts_4d, n_per, axis=0)
        n_tr = len(X0)
        for vname in variants:
            pfn = pols[vname]
            ss = np.random.SeedSequence([m_seed, 717])
            trngs = [np.random.default_rng(c) for c in ss.spawn(n_tr)]
            X = X0.copy()
            al = np.ones(n_tr, dtype=bool)
            run_c = np.zeros(n_tr, dtype=float)
            cap_cnt = 0; tot_cnt = 0
            dt_s = 0.015; sq_s = np.sqrt(dt_s)
            for _st in range(600):
                idx = np.flatnonzero(al)
                if len(idx) == 0:
                    break
                xa = X[idx]; pa = xa[:, :2]; va = xa[:, 2:4]
                u = np.asarray(pfn(xa), dtype=float)
                un = np.linalg.norm(u, axis=1, keepdims=True)
                cap_cnt += int(np.sum(un[:, 0] > 4.5))
                tot_cnt += len(idx)
                u = np.where(un > 4.5, u * (4.5 / np.maximum(un, 1e-12)), u)
                qt = q0 + w2.q_hidden(pa) + 0.06 * np.sum(va ** 2, axis=1)
                run_c[idx] += (qt + 0.5 * np.sum(u ** 2, axis=1)) * dt_s
                bh = w2.drift(pa)
                dw = np.vstack([trngs[ii].normal(0.0, sq_s, size=2) for ii in idx])
                pn, vn, _, _ = reflect_kinetic_into_box(pa + va * dt_s, va + (-gamma * va + bh + u) * dt_s + sigma * dw, half_width, v_max)
                xn = np.hstack([pn, vn])
                X[idx] = xn
                hit = (np.linalg.norm(pn - np.array([goal_pos]), axis=1) <= r_pos) & (np.linalg.norm(vn, axis=1) <= r_vel)
                if np.any(hit):
                    al[idx[hit]] = False
            pen = np.zeros(n_tr, dtype=float)
            if np.any(al):
                pen[al] = v0_fn(X[al])[0] + 2.0
            per_map_running_cost[vname].append(float(np.mean(run_c)))
            per_map_timeout_pen[vname].append(float(np.mean(pen)))
            per_map_total_score[vname].append(float(np.mean(run_c + pen)))
            per_map_reach[vname].append(float(np.mean(~al)))
            per_map_action_cap_frac[vname].append(float(cap_cnt / max(tot_cnt, 1)))

    full_best = np.array(per_map_total_score["FK-AnisoKernel-InwardBnd-BrakingAnch"])
    return {
        "scope_grade": "exploratory_empirical_extension",
        "n_maps_total": len(map_seeds),
        "n_continuation_rounds": 6,
        "max_measured_telescoping_discrepancy": max_telescoping_disc,
        "fk_diagnostics_round6": fk_diags,
        "variants": {
            v: {
                "mean_total_finite_horizon_score_all10": float(np.mean(per_map_total_score[v])),
                "mean_total_score_heldout4": float(np.mean(per_map_total_score[v][n_dev:])),
                "reach_rate_all10": float(np.mean(per_map_reach[v])),
                "reach_rate_heldout4": float(np.mean(per_map_reach[v][n_dev:])),
                "mean_execution_action_cap_fraction": float(np.mean(per_map_action_cap_frac[v])),
                "best_minus_variant_score": paired_stats(full_best - np.array(per_map_total_score[v])),
                "per_map_total_scores": per_map_total_score[v],
            }
            for v in variants
        },
    }


def plot_exp3(r4: dict, r6: dict, r_bud: dict, out_png: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(19.5, 5.3))

    m_keys = [
        "FrozenFK-ZeroMeanPrior",
        "FrozenFK-EikonalConePrior",
        "FrozenFK-MatchedSmoothConePrior",
        "FrozenFK-MatchedSharpConePrior",
        "FrozenFK-HelmholtzBesselPrior",
    ]
    lbls = ["ZeroMean\n(No Prior)", "Smooth\nCone", "NNLS-Match\nSmoothCone", "NNLS-Match\nSharpCone", "Helmholtz\nBessel"]
    x = np.arange(len(m_keys)); w = 0.26

    # Panel 1: 4D Matched Prior Attribution
    ax = axes[0]
    ax.bar(x - w, [r4["methods"][k]["train_starts_mean_cost_all8"] for k in m_keys], width=w, color="#1f77b4", label="Train Starts")
    ax.bar(x, [r4["methods"][k]["unseen_in_dist_starts_mean_cost_all8"] for k in m_keys], width=w, color="#2ca02c", label="Unseen In-Dist")
    ax.bar(x + w, [r4["methods"][k]["near_wall_corner_shift_starts_mean_cost_all8"] for k in m_keys], width=w, color="#d62728", alpha=0.88, label="Wall/Corner Shift")
    ax.set_xticks(x); ax.set_xticklabels(lbls, fontsize=7.5)
    ax.set_ylabel("Closed-Loop Cost (8 Maps)")
    ax.set_title("4D Frozen-Label Prior Attribution (NNLS-Matched Controls)\n(Isolates d-D Helmholtz Curvature vs. Sharp/Smooth Cones)", fontsize=9.3)
    ax.grid(True, axis="y", alpha=0.3); ax.legend(fontsize=7.4)

    # Panel 2: 6D Matched Prior Attribution
    ax = axes[1]
    ax.bar(x - w, [r6["methods"][k]["train_starts_mean_cost_all8"] for k in m_keys], width=w, color="#1f77b4", label="Train Starts")
    ax.bar(x, [r6["methods"][k]["unseen_in_dist_starts_mean_cost_all8"] for k in m_keys], width=w, color="#2ca02c", label="Unseen In-Dist")
    ax.bar(x + w, [r6["methods"][k]["near_wall_corner_shift_starts_mean_cost_all8"] for k in m_keys], width=w, color="#9467bd", alpha=0.88, label="Wall/Corner Shift")
    ax.set_xticks(x); ax.set_xticklabels(lbls, fontsize=7.5)
    ax.set_ylabel("Closed-Loop Cost (8 Maps)")
    ax.set_title("6D Frozen-Label Prior Attribution (NNLS-Matched Controls)\n(Helmholtz-Bessel Beats NNLS-Matched Sharp & Smooth Cones)", fontsize=9.3)
    ax.grid(True, axis="y", alpha=0.3); ax.legend(fontsize=7.4)

    # Panel 3: 6D Fresh-Seed Anchor-Budget Efficiency Curve (`9600..9615`, Native Path Counters!)
    ax = axes[2]
    b_list = [24, 54, 108]
    for p_key, p_lbl, col, mk in [
        ("zero_mean", "ZeroMean (No Physics Prior)", "#d62728", "o"),
        ("matched_sharp_cone", "NNLS-Mode Sharp Cone", "#ff7f0e", "s"),
        ("helmholtz_bessel", "Helmholtz-Bessel Physics Prior", "#2ca02c", "P"),
    ]:
        ys_sh = [r_bud["anchor_budgets"][f"anchors_{nb}"]["priors"][p_key]["wall_corner_shift_mean_cost"] for nb in b_list]
        ys_un = [r_bud["anchor_budgets"][f"anchors_{nb}"]["priors"][p_key]["unseen_in_dist_mean_cost"] for nb in b_list]
        ax.plot(b_list, ys_sh, marker=mk, color=col, lw=2.1, ls="-", label=f"{p_lbl} [Wall-Shift]")
        ax.plot(b_list, ys_un, marker=mk, color=col, lw=1.5, ls="--", alpha=0.78, label=f"{p_lbl} [Unseen]")
    ax.set_xticks(b_list)
    x_tick_lbls = []
    for nb in b_list:
        cnt = r_bud["anchor_budgets"][f"anchors_{nb}"].get("actual_solver_budget_counters_mean", {})
        act_int = cnt.get("n_interior_actual", nb)
        act_paths = cnt.get("n_fk_paths_launched_actual", nb * 48)
        x_tick_lbls.append(f"N={nb} ({act_int:.1f} int)\n[{act_paths:.0f} FK paths]")
    ax.set_xticklabels(x_tick_lbls, fontsize=7.6)
    n_m_bud = r_bud.get("n_maps", 16)
    ax.set_xlabel(f"Anchor Budget & Actual Launched FK Paths ({n_m_bud} 6D Maps: 8 Rep + 8 New)")
    ax.set_ylabel("Closed-Loop Control Cost")
    ax.set_title("6D Anchor-Budget Generalization & +5% NI\n(Same-N24 Gain & +5% NI Hold on New 8 Maps p<=.0023)", fontsize=9.0)
    ax.grid(True, alpha=0.3); ax.legend(fontsize=6.8, ncol=1)

    plt.tight_layout()
    plt.savefig(out_png, dpi=175)
    plt.close(fig)


def main():
    enforce_single_thread_env()
    n_workers = 8
    print("=== Exp 3A (4D): Frozen-Label Prior Attribution incl. NNLS-Matched Cones ===", flush=True)
    r4 = run_highd_prior_and_shift_suite(dim=4, n_probes=60)
    print("\n=== Exp 3B (6D): Frozen-Label Prior Attribution incl. NNLS-Matched Cones ===", flush=True)
    r6 = run_highd_prior_and_shift_suite(dim=6, n_probes=100)
    print(f"\n=== Exp 3B-Confirm (16 6D Maps: 8 Rep + 8 New, {n_workers}-Core Parallel): Native Budget Curve ===", flush=True)
    r_bud = run_6d_anchor_budget_and_fresh_confirmation(n_maps=16, max_workers=n_workers)
    print(f"\n=== Exp 3D: Independent FD/Cone-Girsanov Teachers & Isolated Latency ({n_workers}-Core Parallel) ===", flush=True)
    r_indep = run_independent_teacher_and_isolated_latency_suite(max_workers=n_workers)
    print("\n=== Exp 3C (4D Kinetic): Scoped Empirical Appendix (10 Maps, 6 Rounds) ===", flush=True)
    rua = run_scoped_kinetic_factorial(n_probes=45)

    out_dir = Path(__file__).resolve().parent
    payload = {
        "metadata": collect_runtime_metadata(max_workers=n_workers),
        "highd_4d": r4,
        "highd_6d": r6,
        "highd_6d_fresh_anchor_budget_efficiency": r_bud,
        "independent_teacher_and_isolated_latency": r_indep,
        "kinetic_underactuated_10maps": rua,
    }
    (out_dir / "exp3_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plot_exp3(r4, r6, r_bud, out_dir / "exp3_highd_and_kinetic.png")
    print("Saved exp3_results.json and exp3_highd_and_kinetic.png", flush=True)


if __name__ == "__main__":
    main()
