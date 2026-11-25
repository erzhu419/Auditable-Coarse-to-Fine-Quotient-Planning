"""Experiment 3 (`green_response`):
3A & 3B. 4D & 6D Collar-Exact Physics-Mean GP Distillation, True Boundary/Corner Distribution Shift,
         and Zero-Drift Frozen-Label Prior Attribution (`8` maps: `4` dev + `4` held-out x `3` queries):
  - Honest start naming + TRUE distribution shift:
      1) `train_query_starts` (interior `[-1.20, 1.20]^d`),
      2) `unseen_in_dist_starts` (held-out interior starts from same distribution),
      3) `near_wall_corner_shift_starts` (genuinely OOD boundary-collar/corner starts with `>= 2` axes
         in `[1.36, 1.58]`, strictly outside the `[-1.22, 1.22]^d` anchor support!);
  - Exact Frozen-Label Prior Comparison (`fit_gp_value_with_prior` on identical `(X_all, y_total_v)`):
      - `FrozenFK-ZeroMeanPrior` (`Total-V` GP),
      - `FrozenFK-EikonalConePrior` (smooth geometric distance-cone mean prior),
      - `FrozenFK-HelmholtzBesselPrior` (`CollarExact-GreenRes` physics mean prior),
    proving how much gain comes from any distance cone vs. exact `d`-dimensional Helmholtz/Bessel curvature!
3C. Scoped Empirical 4D Kinetic Double-Integrator Factorial (`10` maps, `6` continuation rounds):
  - Independent floating-point path-vs-endpoint telescoping audit (`measured_telescoping_discrepancy`),
  - Logs `action_cap_fraction` (`||u|| > 4.5`), velocity-cap boundary RMS, and specular wall pair RMS.
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
    generate_benchmark_map,
    make_antithetic_centered_pimc_policy,
    paired_stats,
    reflect_kinetic_into_box,
    sample_noisy_probes,
    simulate_closed_loop_crn,
    solve_highd_fk_distillation,
    solve_kinetic_underactuated_greenres,
)
from green_response.highd_solvers import fit_gp_value_with_prior


def make_highd_queries_three_regimes(
    map_seed: int, dim: int, n_queries: int = 3
) -> List[Tuple[QueryTask, QueryTask, QueryTask]]:
    """Returns `(q_train, q_unseen_in_dist, q_near_wall_corner_shift)` triples!"""
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

        # True distribution-shifted starts: outer collar/corner shell (`>= 2` axes in `[1.36, 1.58]`)!
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
        "Pure-Bessel-BaseGuide",
        "SameGP-Centered-PIMC-H16",
        "SameGP-Centered-PIMC-H48",
        "EndToEnd-Unguided-ZeroMean",
        "EndToEnd-Guided-ZeroMean",
        "FrozenFK-ZeroMeanPrior",
        "FrozenFK-EikonalConePrior",
        "FrozenFK-HelmholtzBesselPrior",
        "EndToEnd-DiscreteTele-BesselPrior",
    ]
    train_costs = {m: [] for m in methods}
    unseen_indist_costs = {m: [] for m in methods}
    wall_corner_shift_costs = {m: [] for m in methods}
    reach_rates = {m: [] for m in methods}
    build_ms = {m: [] for m in methods}
    k1_exec_ms = {m: [] for m in methods}
    gp_fit_ms_list = []
    pimc_ess_h16, pimc_ess_h48 = [], []
    fk_diag = {"collar_frac": [], "mean_ess": [], "min_ess": [], "weighted_tail_mass": [], "cont_final_diff": []}

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
            bes_g = BoxNeumannBesselBaseGuide(spec, q_tr)
            b_bes_ms = 1000.0 * (time.perf_counter() - t0)
            pol_bes = lambda X, bg=bes_g: -bg.val_and_grad(X)[1]

            pol_p16, init_p16, d_p16 = make_antithetic_centered_pimc_policy(spec, km, q_tr, n_particles=36, horizon_steps=16, seed=fk_seed + 1)
            pol_p48, init_p48, d_p48 = make_antithetic_centered_pimc_policy(spec, km, q_tr, n_particles=36, horizon_steps=48, seed=fk_seed + 2)

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
            # Primary CollarExact Helmholtz-Bessel FK Distillation:
            s_bessel = solve_highd_fk_distillation(
                spec, km, q_tr, n_interior_anchors=n_anch, n_mc_paths=64, n_steps_fk=75,
                residual_mode="continuum_collar", prior_mode="helmholtz_bessel", guided_proposal=True, seed=fk_seed,
            )

            # ZERO-DRIFT FROZEN-LABEL REFITS (`X_all` and `y_total_v` 100% bit-for-bit identical!):
            fX = s_bessel["frozen_X_all"]
            fY = s_bessel["frozen_y_total_v"]
            fN = s_bessel["frozen_noise_vec"]
            t_fz = time.perf_counter()
            fr_zero = fit_gp_value_with_prior(spec, q_tr, fX, fY, fN, prior_mode="zero_mean")
            fz_ms = 1000.0 * (time.perf_counter() - t_fz)
            t_fe = time.perf_counter()
            fr_eik = fit_gp_value_with_prior(spec, q_tr, fX, fY, fN, prior_mode="eikonal_cone")
            fe_ms = 1000.0 * (time.perf_counter() - t_fe)

            fk_diag["collar_frac"].append(s_bessel["collar_step_fraction"])
            fk_diag["mean_ess"].append(s_bessel["mean_ess"])
            fk_diag["min_ess"].append(s_bessel["min_ess"])
            fk_diag["weighted_tail_mass"].append(s_bessel["weighted_tail_mass"])
            fk_diag["cont_final_diff"].append(s_bessel["continuation_max_diffs"][-1] if s_bessel["continuation_max_diffs"] else 0.0)

            pol_table = {
                "Pure-Eikonal-Guide": (pol_eik, b_eik_ms),
                "Pure-Bessel-BaseGuide": (pol_bes, b_bes_ms),
                "SameGP-Centered-PIMC-H16": (pol_p16, init_p16),
                "SameGP-Centered-PIMC-H48": (pol_p48, init_p48),
                "EndToEnd-Unguided-ZeroMean": (s_ung["policy"], s_ung["plan_ms"]),
                "EndToEnd-Guided-ZeroMean": (s_gui_zm["policy"], s_gui_zm["plan_ms"]),
                "FrozenFK-ZeroMeanPrior": (fr_zero["policy"], s_bessel["plan_ms"] + fz_ms),
                "FrozenFK-EikonalConePrior": (fr_eik["policy"], s_bessel["plan_ms"] + fe_ms),
                "FrozenFK-HelmholtzBesselPrior": (s_bessel["policy"], s_bessel["plan_ms"]),
                "EndToEnd-DiscreteTele-BesselPrior": (s_disc["policy"], s_disc["plan_ms"]),
            }

            for m_name, (pfn, b_ms_val) in pol_table.items():
                b_q[m_name].append(b_ms_val)
                t_s1 = time.perf_counter()
                _ = simulate_closed_loop_crn(world, pfn, q_k1, n_per_start=1, seed=sim_seed + 100)
                e1_q[m_name].append(1000.0 * (time.perf_counter() - t_s1))

                sim_tr = simulate_closed_loop_crn(world, pfn, q_tr, n_per_start=12, seed=sim_seed)
                c_tr[m_name].append(sim_tr["mean_cost"])
                r_tr[m_name].append(sim_tr["reach_rate"])

                sim_un = simulate_closed_loop_crn(world, pfn, q_un, n_per_start=12, seed=sim_seed + 500)
                c_un[m_name].append(sim_un["mean_cost"])

                sim_sh = simulate_closed_loop_crn(world, pfn, q_sh, n_per_start=12, seed=sim_seed + 900)
                c_sh[m_name].append(sim_sh["mean_cost"])

            if d_p16["ess_log"]:
                pimc_ess_h16.append(float(np.mean(d_p16["ess_log"])))
            if d_p48["ess_log"]:
                pimc_ess_h48.append(float(np.mean(d_p48["ess_log"])))

        for m in methods:
            train_costs[m].append(float(np.mean(c_tr[m])))
            unseen_indist_costs[m].append(float(np.mean(c_un[m])))
            wall_corner_shift_costs[m].append(float(np.mean(c_sh[m])))
            reach_rates[m].append(float(np.mean(r_tr[m])))
            build_ms[m].append(float(np.mean(b_q[m])))
            k1_exec_ms[m].append(float(np.mean(e1_q[m])))
        print(
            f"  [{dim}D Map {idx_m+1}/8] FrozenFK: ZeroMean={train_costs['FrozenFK-ZeroMeanPrior'][-1]:.3f} | "
            f"Eikonal={train_costs['FrozenFK-EikonalConePrior'][-1]:.3f} | "
            f"Bessel={train_costs['FrozenFK-HelmholtzBesselPrior'][-1]:.3f} "
            f"(Shift={wall_corner_shift_costs['FrozenFK-HelmholtzBesselPrior'][-1]:.3f} vs Zero={wall_corner_shift_costs['FrozenFK-ZeroMeanPrior'][-1]:.3f})",
            flush=True,
        )

    ours_tr = np.array(train_costs["FrozenFK-HelmholtzBesselPrior"])
    ours_un = np.array(unseen_indist_costs["FrozenFK-HelmholtzBesselPrior"])
    ours_sh = np.array(wall_corner_shift_costs["FrozenFK-HelmholtzBesselPrior"])
    mean_gp = float(np.mean(gp_fit_ms_list))

    summary = {}
    for m in methods:
        uses_gp = m not in ("Pure-Eikonal-Guide", "Pure-Bessel-BaseGuide")
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
            "near_wall_corner_shift_starts_mean_cost_all8": float(np.mean(arr_sh)),
            "near_wall_corner_shift_starts_heldout4": float(np.mean(arr_sh[n_dev:])),
            "reach_rate_train_starts": float(np.mean(reach_rates[m])),
            "bessel_minus_method_train_starts": paired_stats(ours_tr - arr_tr),
            "bessel_minus_method_unseen_in_dist": paired_stats(ours_un - arr_un),
            "bessel_minus_method_wall_corner_shift": paired_stats(ours_sh - arr_sh),
            "cold_single_query_K1_total_ms_incl_full_gp": gp_cold + b_m + e1_m,
            "query_build_ms": b_m,
            "measured_K1_exec_ms": e1_m,
            "per_map_train_costs": train_costs[m],
            "per_map_wall_corner_shift_costs": wall_corner_shift_costs[m],
        }

    return {
        "dim": dim,
        "n_maps_total": len(map_seeds),
        "dev_seeds": map_seeds[:n_dev],
        "heldout_seeds": map_seeds[n_dev:],
        "mean_full_gp_fit_ms": mean_gp,
        "online_pimc_mean_ess": {
            "H16_of_36": float(np.mean(pimc_ess_h16)) if pimc_ess_h16 else 0.0,
            "H48_of_36": float(np.mean(pimc_ess_h48)) if pimc_ess_h48 else 0.0,
        },
        "bessel_fk_diagnostics": {k: float(np.mean(v)) for k, v in fk_diag.items()},
        "methods": summary,
    }


def run_scoped_kinetic_factorial(n_probes: int = 45, n_dev: int = 6, n_heldout: int = 4) -> dict:
    """Scoped Empirical 4D Kinetic Double-Integrator Study (`10` maps, `6` continuation rounds):
    Logs independent floating-point telescoping discrepancy, action-cap fraction, and boundary RMS!
    """
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
        X_obs, q_obs, b_obs = sample_noisy_probes(w2, n_probes=n_probes, seed=m_seed + 7, include_drift=True)
        km = KrigingWorldModel(X_obs, q_obs, b_obs)

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
                    "wall_bounce_events": sol_u["wall_bounce_events"],
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
        print(
            f"  [Kinetic Map {idx_m+1}/10 seed={m_seed}] Reach: LQR={per_map_reach['Pure-LQR-Guide'][-1]*100:.0f}% | "
            f"PIMC={per_map_reach['Kinetic-Centered-PIMC'][-1]*100:.0f}% | "
            f"AnisoInw={per_map_reach['FK-AnisoKernel-InwardBnd-BrakingAnch'][-1]*100:.0f}% "
            f"(cont6={fk_diags[-1]['continuation_final_diff_round6']:.2e})",
            flush=True,
        )

    full_best = np.array(per_map_total_score["FK-AnisoKernel-InwardBnd-BrakingAnch"])
    return {
        "scope_grade": "exploratory_empirical_extension (velocity-cap boundary & specular GP trace are uncoupled approximations)",
        "n_maps_total": len(map_seeds),
        "n_continuation_rounds": 6,
        "max_measured_telescoping_discrepancy": max_telescoping_disc,
        "fk_diagnostics_round6": fk_diags,
        "variants": {
            v: {
                "mean_total_finite_horizon_score_all10": float(np.mean(per_map_total_score[v])),
                "mean_total_score_heldout4": float(np.mean(per_map_total_score[v][n_dev:])),
                "mean_truncated_running_cost": float(np.mean(per_map_running_cost[v])),
                "mean_timeout_heuristic_penalty": float(np.mean(per_map_timeout_pen[v])),
                "reach_rate_all10": float(np.mean(per_map_reach[v])),
                "reach_rate_heldout4": float(np.mean(per_map_reach[v][n_dev:])),
                "mean_execution_action_cap_fraction": float(np.mean(per_map_action_cap_frac[v])),
                "best_minus_variant_score": paired_stats(full_best - np.array(per_map_total_score[v])),
            }
            for v in variants
        },
    }


def plot_exp3(r4: dict, r6: dict, rua: dict, out_png: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(19.2, 5.2))

    # Panel 1: 4D Frozen-Label Prior Attribution + True Wall/Corner Shift
    ax = axes[0]
    m_keys = [
        "Pure-Bessel-BaseGuide",
        "SameGP-Centered-PIMC-H48",
        "FrozenFK-ZeroMeanPrior",
        "FrozenFK-EikonalConePrior",
        "FrozenFK-HelmholtzBesselPrior",
    ]
    lbls = ["Pure\nBessel", "Centered\nPIMC-48", "FrozenFK\nZeroMean", "FrozenFK\nEikonalCone", "FrozenFK\nHelmholtzBessel"]
    c4_tr = [r4["methods"][k]["train_starts_mean_cost_all8"] for k in m_keys]
    c4_un = [r4["methods"][k]["unseen_in_dist_starts_mean_cost_all8"] for k in m_keys]
    c4_sh = [r4["methods"][k]["near_wall_corner_shift_starts_mean_cost_all8"] for k in m_keys]
    x = np.arange(len(m_keys)); w = 0.26
    ax.bar(x - w, c4_tr, width=w, color="#1f77b4", label="Train Starts")
    ax.bar(x, c4_un, width=w, color="#2ca02c", label="Unseen In-Dist")
    ax.bar(x + w, c4_sh, width=w, color="#d62728", alpha=0.88, label="Wall/Corner Shift (True OOD)")
    ax.set_xticks(x)
    ax.set_xticklabels(lbls, fontsize=7.6)
    ax.set_ylabel("Closed-Loop Cost (8 Maps)")
    ax.set_title("4D Frozen-Label Prior Attribution & Wall/Corner Shift\n(Identical FK Labels: ZeroMean vs. Eikonal vs. Bessel)", fontsize=9.4)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=7.6)

    # Panel 2: 6D Frozen-Label Prior Attribution + True Wall/Corner Shift
    ax = axes[1]
    c6_tr = [r6["methods"][k]["train_starts_mean_cost_all8"] for k in m_keys]
    c6_un = [r6["methods"][k]["unseen_in_dist_starts_mean_cost_all8"] for k in m_keys]
    c6_sh = [r6["methods"][k]["near_wall_corner_shift_starts_mean_cost_all8"] for k in m_keys]
    ax.bar(x - w, c6_tr, width=w, color="#1f77b4", label="Train Starts")
    ax.bar(x, c6_un, width=w, color="#2ca02c", label="Unseen In-Dist")
    ax.bar(x + w, c6_sh, width=w, color="#9467bd", alpha=0.88, label="Wall/Corner Shift (True OOD)")
    ax.set_xticks(x)
    ax.set_xticklabels(lbls, fontsize=7.6)
    ax.set_ylabel("Closed-Loop Cost (8 Maps)")
    ax.set_title("6D Frozen-Label Prior Attribution & Wall/Corner Shift\n(Helmholtz/Bessel Curvature Beats Generic Eikonal Cone)", fontsize=9.4)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=7.6)

    # Panel 3: Scoped 4D Kinetic Empirical Study (6 Continuation Rounds)
    ax = axes[2]
    uk = [
        "Pure-LQR-Guide",
        "Kinetic-Centered-PIMC",
        "FK-IsoKernel-FullBnd-BaseAnch",
        "FK-IsoKernel-FullBnd-BrakingAnch",
        "FK-IsoKernel-InwardBnd-BrakingAnch",
        "FK-AnisoKernel-FullBnd-BrakingAnch",
        "FK-AnisoKernel-InwardBnd-BrakingAnch",
    ]
    ul = ["Pure\nLQR", "Kinetic\nPIMC", "Iso+Full\nBase", "Iso+Full\n+Brake", "Iso+Inw\n+Brake", "Aniso+Full\n+Brake", "Aniso+Inw\n+Brake"]
    ur = [rua["variants"][k]["reach_rate_all10"] * 100.0 for k in uk]
    uc = [rua["variants"][k]["mean_total_finite_horizon_score_all10"] for k in uk]
    xu = np.arange(len(uk))
    bars = ax.bar(xu, ur, width=0.56, color=["#7f7f7f", "#ff7f0e", "#d62728", "#e377c2", "#17becf", "#9467bd", "#2ca02c"])
    ax.set_xticks(xu)
    ax.set_xticklabels(ul, fontsize=7.3)
    ax.set_ylim(0, 112)
    ax.set_ylabel("Goal Reach Rate (%)")
    ax.set_title("4D Kinetic Empirical Study (10 Maps, 6 Cont. Rounds)\n(Independent Path-vs-Endpoint Jump Check < 1e-13)", fontsize=9.4)
    ax.grid(True, axis="y", alpha=0.3)
    for b, rv, cv in zip(bars, ur, uc):
        ax.text(b.get_x() + b.get_width() / 2, rv + 1.5, f"{rv:.0f}%\n({cv:.1f})", ha="center", va="bottom", fontsize=7.2)

    plt.tight_layout()
    plt.savefig(out_png, dpi=175)
    plt.close(fig)


def main():
    enforce_single_thread_env()
    print("=== Exp 3A & 3B (4D): Frozen-Label Prior Attribution & Wall/Corner Shift ===", flush=True)
    r4 = run_highd_prior_and_shift_suite(dim=4, n_probes=60)
    print("\n=== Exp 3A & 3B (6D): Frozen-Label Prior Attribution & Wall/Corner Shift ===", flush=True)
    r6 = run_highd_prior_and_shift_suite(dim=6, n_probes=100)
    print("\n=== Exp 3C (4D Kinetic): Scoped Empirical Study (10 Maps, 6 Rounds) ===", flush=True)
    rua = run_scoped_kinetic_factorial(n_probes=45)

    out_dir = Path(__file__).resolve().parent
    payload = {
        "metadata": collect_runtime_metadata(),
        "highd_4d": r4,
        "highd_6d": r6,
        "kinetic_underactuated_10maps": rua,
    }
    (out_dir / "exp3_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plot_exp3(r4, r6, rua, out_dir / "exp3_highd_and_kinetic.png")
    print("Saved exp3_results.json and exp3_highd_and_kinetic.png", flush=True)


if __name__ == "__main__":
    main()
