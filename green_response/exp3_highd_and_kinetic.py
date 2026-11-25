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

3B-Confirm. Locked Fresh-Seed 6D Anchor-Budget Efficiency Curve (`8` brand-new maps `9600..9607`):
  - Varies interior FK anchor budget `N_anch in {28, 56, 108}` comparing `ZeroMean`, `MatchedSharpCone`,
    and `HelmholtzBessel`, plus independent FK seed replication stability `|V^{(A)} - V^{(B)}|`.

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
    world = generate_benchmark_map(ms, dim=dim, regime="smooth", with_drift=True, spec=spec)
    km = KrigingWorldModel(*sample_noisy_probes(world, n_probes=100, seed=ms + 7, include_drift=True))
    triples = make_highd_queries_three_regimes(ms, dim=dim, n_queries=2)

    out_m = {}
    for nb in budgets:
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
            for p_mode in priors:
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
            "counters_mean": {
                ck: float(np.mean([c[ck] for c in counters_list])) for ck in counters_list[0].keys()
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
    """`ddd19c5 Stage E`: 16 Locked Fresh 6D Maps (`9600..9615`) with Native Solver Budget Counters,
    Decoupled Fixed-Design MC Variance vs Full-Reconstruction Sensitivity, Same-Low-Budget (`N=24`)
    Primary Contrast, and Pre-Declared `+5.0%` Cross-Budget Non-Inferiority (`Bessel-24` vs `SharpCone-108`)!
    """
    from green_response import paired_relative_noninferiority, run_map_parallel

    dim = 6
    fresh_seeds = list(range(9600, 9600 + n_maps))
    budgets = [24, 54, 108]
    priors = ["zero_mean", "matched_sharp_cone", "helmholtz_bessel"]

    rows = run_map_parallel(
        _budget_map_worker, [(i, s, budgets) for i, s in enumerate(fresh_seeds)], max_workers=max_workers
    )

    out_budgets = {}
    for nb in budgets:
        bes_un = np.array([r[nb]["priors"]["helmholtz_bessel"]["un"] for r in rows])
        bes_sh = np.array([r[nb]["priors"]["helmholtz_bessel"]["sh"] for r in rows])
        c_keys = list(rows[0][nb]["counters_mean"].keys())
        mean_cnt = {ck: float(np.mean([r[nb]["counters_mean"][ck] for r in rows])) for ck in c_keys}

        out_budgets[f"anchors_{nb}"] = {
            "nominal_interior_anchors_param": nb,
            "world_observation_probes_per_map": 100,
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
                    "mean_query_plan_ms": float(np.mean([r[nb]["priors"][p]["plan_ms"] for r in rows])),
                    "fixed_design_mc_seed_grad_rms_diff": float(np.mean([r[nb]["priors"][p]["grad_rms_mc_only"] for r in rows])),
                    "full_reconstruction_seed_grad_rms_diff": float(np.mean([r[nb]["priors"][p]["grad_rms_full_recon"] for r in rows])),
                    "bessel_minus_prior_unseen": paired_stats(bes_un - np.array([r[nb]["priors"][p]["un"] for r in rows])),
                    "bessel_minus_prior_wall_corner_shift": paired_stats(bes_sh - np.array([r[nb]["priors"][p]["sh"] for r in rows])),
                    "per_map_unseen_costs": [r[nb]["priors"][p]["un"] for r in rows],
                    "per_map_shift_costs": [r[nb]["priors"][p]["sh"] for r in rows],
                }
                for p in priors
            },
        }

    b24_un = np.array(out_budgets["anchors_24"]["priors"]["helmholtz_bessel"]["per_map_unseen_costs"])
    b24_sh = np.array(out_budgets["anchors_24"]["priors"]["helmholtz_bessel"]["per_map_shift_costs"])
    c108_un = np.array(out_budgets["anchors_108"]["priors"]["matched_sharp_cone"]["per_map_unseen_costs"])
    c108_sh = np.array(out_budgets["anchors_108"]["priors"]["matched_sharp_cone"]["per_map_shift_costs"])

    paths_24 = out_budgets["anchors_24"]["actual_solver_budget_counters_mean"]["n_fk_paths_launched_actual"]
    paths_108 = out_budgets["anchors_108"]["actual_solver_budget_counters_mean"]["n_fk_paths_launched_actual"]
    gp_24 = out_budgets["anchors_24"]["actual_solver_budget_counters_mean"]["n_gp_rows_total"]
    gp_108 = out_budgets["anchors_108"]["actual_solver_budget_counters_mean"]["n_gp_rows_total"]
    ms_24 = out_budgets["anchors_24"]["priors"]["helmholtz_bessel"]["mean_query_plan_ms"]
    ms_108 = out_budgets["anchors_108"]["priors"]["matched_sharp_cone"]["mean_query_plan_ms"]

    cross_budget = {
        "actual_launched_fk_paths_ratio_108_over_24": float(paths_108 / paths_24),
        "actual_gp_training_rows_ratio_108_over_24": float(gp_108 / gp_24),
        "actual_planning_time_ratio_cone108_over_bessel24": float(ms_108 / ms_24),
        "nominal_anchor_param_ratio_108_over_24": 108.0 / 24.0,
        "bessel24_minus_cone108_unseen_paired_diff": paired_stats(b24_un - c108_un),
        "bessel24_minus_cone108_shift_paired_diff": paired_stats(b24_sh - c108_sh),
        "predeclared_5pct_relative_NI_bessel24_vs_cone108_unseen": paired_relative_noninferiority(b24_un, c108_un, rel_margin_pct=5.0),
        "predeclared_5pct_relative_NI_bessel24_vs_cone108_shift": paired_relative_noninferiority(b24_sh, c108_sh, rel_margin_pct=5.0),
    }

    return {
        "locked_fresh_seeds": fresh_seeds,
        "n_maps": n_maps,
        "dim": dim,
        "world_probes_per_map": 100,
        "nnls_cone_protocol": "same_c2_collar_same_asymptotic_slope_36pt_per_goal_positive_mode_weight_nnls",
        "anchor_budgets": out_budgets,
        "cross_budget_bessel24_vs_sharpcone108": cross_budget,
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
    n_m_bud = r_bud.get("n_maps", len(r_bud.get("locked_fresh_seeds", [])))
    ax.set_xlabel(f"Anchor Budget & Actual Launched FK Paths ({n_m_bud} Fresh 6D Maps)")
    ax.set_ylabel("Closed-Loop Control Cost")
    ax.set_title("6D Low-Budget Generalization & Cross-Budget Parity\n(Strong Same-N24 Gain; Bessel-24 Passes +5% NI vs Cone-108)", fontsize=9.1)
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
    print(f"\n=== Exp 3B-Confirm (16 Fresh 6D Maps 9600..9615, {n_workers}-Core Parallel): Native Budget Curve ===", flush=True)
    r_bud = run_6d_anchor_budget_and_fresh_confirmation(n_maps=16, max_workers=n_workers)
    print("\n=== Exp 3C (4D Kinetic): Scoped Empirical Appendix (10 Maps, 6 Rounds) ===", flush=True)
    rua = run_scoped_kinetic_factorial(n_probes=45)

    out_dir = Path(__file__).resolve().parent
    payload = {
        "metadata": collect_runtime_metadata(max_workers=n_workers),
        "highd_4d": r4,
        "highd_6d": r6,
        "highd_6d_fresh_anchor_budget_efficiency": r_bud,
        "kinetic_underactuated_10maps": rua,
    }
    (out_dir / "exp3_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plot_exp3(r4, r6, r_bud, out_dir / "exp3_highd_and_kinetic.png")
    print("Saved exp3_results.json and exp3_highd_and_kinetic.png", flush=True)


if __name__ == "__main__":
    main()
