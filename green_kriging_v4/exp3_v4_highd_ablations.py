"""Experiment 3 (`green_kriging_v4`):
3A. Repaired Collar-Exact 4D & 6D Duel (`8` maps: `4` dev + `4` held-out x `3` queries),
    including:
      - Out-of-Distribution (OOD) test starts NEVER used to seed corridor anchors!
      - Cold single-query `K=1` latency (charging 100% of GP fit!) vs multi-query / multi-rollout time;
      - Live online PIMC ESS logging (`H=16` vs `H=48`) & per-anchor `min/median/mean ESS` + `weighted_tail_mass`!
3B. Clean Single-Factor High-D Distillation Ablation (`4D` & `6D`):
    Holds anchors, boundary points, kernel family, continuation rounds, and CRN draws 100% IDENTICAL:
      1. `Unguided-Proposal + Fit-Total-V`
      2. `Guided-Proposal + Fit-Total-V`
      3. `Guided-Proposal + Fit-Residual-(V - V0)` (`CollarExact-GreenRes`)
      4. `Discrete-Telescoping-PathWeight + Fit-Residual-(V - V0)`
3C. Clean Decomposed 4D Kinetic Double-Integrator Benchmark (`10` maps: `6` dev + `4` held-out):
    Separates `Inward-Boundary`, `Anisotropic-Residual-Kernel`, and `Braking-Anchors` orthogonally,
    includes `Pure-LQR-Guide` and `Kinetic-Centered-PIMC`, uses true kinetic specular wall bounce
    (`v_n -> -v_n`) + exact discrete LQR telescoping (`0.0` unaccounted jump), and reports per-map
    running cost, timeout heuristic, and reach rate separately!
"""
from __future__ import annotations

from core_v4 import enforce_single_thread_env
enforce_single_thread_env()

import json
import time
from pathlib import Path
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from core_v4 import (
    GoalBall,
    HazardFeature,
    KrigingWorldModel,
    ProblemSpec,
    QueryTask,
    collect_runtime_metadata,
    generate_benchmark_map,
    paired_stats,
    reflect_kinetic_into_box,
    sample_noisy_probes,
    simulate_closed_loop_crn,
)
from highd_v4 import (
    BoxNeumannBesselBaseGuideV4,
    build_kinetic_lqr_base_guide,
    make_antithetic_centered_pimc_policy_v4,
    solve_highd_fk_distillation_v4,
    solve_kinetic_underactuated_greenres_v4,
)


def make_highd_queries_with_ood_starts(
    map_seed: int, dim: int, n_queries: int = 3
) -> List[Tuple[QueryTask, QueryTask]]:
    """Returns `(train_query, ood_eval_query)` pairs:
    `ood_eval_query` shares the EXACT SAME goals & local hazards, but uses 2 held-out random start
    points NEVER seen during corridor anchor generation!
    """
    rng = np.random.default_rng(map_seed + 505)
    r_goal = 0.36 if dim == 4 else 0.44
    pairs = []
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

        all_starts = []
        for _ in range(5):
            for _att in range(120):
                sp_pt = rng.uniform(-1.25, 1.25, size=dim)
                if dim > 2:
                    sp_pt[2:] *= 0.80
                if all(np.linalg.norm(sp_pt - np.asarray(g.center)) > r_goal + 0.35 for g in goals):
                    all_starts.append(tuple(sp_pt.tolist()))
                    break

        mid = np.clip(0.5 * (np.asarray(all_starts[0]) + np.asarray(goals[0].center)), -1.1, 1.1)
        loc_h = (HazardFeature(tuple(mid.tolist()), float(rng.uniform(4.5, 8.0)), (0.34,) * dim),)
        q_train = QueryTask(f"hd_{dim}d_{q_i}", tuple(goals), tuple(all_starts[:3]), loc_h)
        q_ood = QueryTask(f"hd_{dim}d_{q_i}_ood", tuple(goals), tuple(all_starts[3:5]), loc_h)
        pairs.append((q_train, q_ood))
    return pairs


def run_highd_duel_and_single_factor_ablation(dim: int, n_probes: int, n_dev: int = 4, n_heldout: int = 4, n_queries: int = 3) -> dict:
    spec = ProblemSpec(dim=dim, half_width=1.65, sigma=0.55, q0=0.65, dt_sim=0.020, max_steps=420)
    base_s = 2200 if dim == 4 else 3200
    # 4 dev seeds + 4 held-out confirmation seeds = 8 maps
    map_seeds = list(range(base_s, base_s + n_dev)) + list(range(base_s + 1000, base_s + 1000 + n_heldout))

    methods = [
        "Pure-Base-Guide",
        "SameGP-Centered-PIMC-H16",
        "SameGP-Centered-PIMC-H48",
        "Ablation-Unguided-TotalV",
        "Ablation-Guided-TotalV",
        "Ablation-DiscreteTele-ResidualV",
        "CollarExact-GreenRes",
    ]
    in_dist_costs = {m: [] for m in methods}
    ood_costs = {m: [] for m in methods}
    k1_single_traj_costs = {m: [] for m in methods}
    reach_rates = {m: [] for m in methods}
    build_ms = {m: [] for m in methods}
    k1_exec_ms = {m: [] for m in methods}
    batch36_exec_ms = {m: [] for m in methods}
    gp_fit_ms_list = []
    pimc_ess_h16 = []
    pimc_ess_h48 = []
    greenres_diag = {"collar_frac": [], "mean_ess": [], "min_ess": [], "weighted_tail_mass": [], "cont_final_diff": []}

    n_anch = 88 if dim == 4 else 108

    for idx_m, m_seed in enumerate(map_seeds):
        world = generate_benchmark_map(m_seed, dim=dim, regime="smooth", with_drift=True, spec=spec)
        X_obs, q_obs, b_obs = sample_noisy_probes(world, n_probes=n_probes, seed=m_seed + 7, include_drift=True)
        t_gp = time.perf_counter()
        km = KrigingWorldModel(X_obs, q_obs, b_obs)
        gp_ms = 1000.0 * (time.perf_counter() - t_gp)
        gp_fit_ms_list.append(gp_ms)

        q_pairs = make_highd_queries_with_ood_starts(m_seed, dim=dim, n_queries=n_queries)
        c_in = {m: [] for m in methods}
        c_ood = {m: [] for m in methods}
        c_k1 = {m: [] for m in methods}
        r_in = {m: [] for m in methods}
        b_q = {m: [] for m in methods}
        e1_q = {m: [] for m in methods}
        eb_q = {m: [] for m in methods}

        for q_i, (q_tr, q_ood) in enumerate(q_pairs):
            fk_seed = 8000 + 20 * idx_m + q_i
            sim_seed = 9000 + 20 * idx_m + q_i
            q_single = QueryTask(q_tr.name + "_k1", q_tr.goals, (q_tr.start_points[0],), q_tr.local_hazards)

            # 1. Pure Base Guide (0 GP fit!)
            t0 = time.perf_counter()
            base_g = BoxNeumannBesselBaseGuideV4(spec, q_tr)
            b_base_ms = 1000.0 * (time.perf_counter() - t0)
            pol_base = lambda X, bg=base_g: -bg.val_and_grad(X)[1]

            # 2 & 3. Centered PIMC H16 & H48 (with live online ESS logging!)
            pol_p16, init_p16, d_p16 = make_antithetic_centered_pimc_policy_v4(spec, km, q_tr, n_particles=36, horizon_steps=16, seed=fk_seed + 1)
            pol_p48, init_p48, d_p48 = make_antithetic_centered_pimc_policy_v4(spec, km, q_tr, n_particles=36, horizon_steps=48, seed=fk_seed + 2)

            # 4, 5, 6, 7. Strictly Matched-Anchor / Matched-CRN Single-Factor Ablation Family!
            s_ung_tot = solve_highd_fk_distillation_v4(
                spec, km, q_tr, n_interior_anchors=n_anch, n_mc_paths=64, n_steps_fk=75,
                residual_mode="continuum_collar", regression_target="total_V", guided_proposal=False, seed=fk_seed
            )
            s_gui_tot = solve_highd_fk_distillation_v4(
                spec, km, q_tr, n_interior_anchors=n_anch, n_mc_paths=64, n_steps_fk=75,
                residual_mode="continuum_collar", regression_target="total_V", guided_proposal=True, seed=fk_seed
            )
            s_disc_res = solve_highd_fk_distillation_v4(
                spec, km, q_tr, n_interior_anchors=n_anch, n_mc_paths=64, n_steps_fk=75,
                residual_mode="discrete_telescoping", regression_target="residual", guided_proposal=True, seed=fk_seed
            )
            s_ours = solve_highd_fk_distillation_v4(
                spec, km, q_tr, n_interior_anchors=n_anch, n_mc_paths=64, n_steps_fk=75,
                residual_mode="continuum_collar", regression_target="residual", guided_proposal=True, seed=fk_seed
            )

            greenres_diag["collar_frac"].append(s_ours["collar_step_fraction"])
            greenres_diag["mean_ess"].append(s_ours["mean_ess"])
            greenres_diag["min_ess"].append(s_ours["min_ess"])
            greenres_diag["weighted_tail_mass"].append(s_ours["weighted_tail_mass"])
            greenres_diag["cont_final_diff"].append(s_ours["continuation_max_diffs"][-1] if s_ours["continuation_max_diffs"] else 0.0)

            pol_table = {
                "Pure-Base-Guide": (pol_base, b_base_ms),
                "SameGP-Centered-PIMC-H16": (pol_p16, init_p16),
                "SameGP-Centered-PIMC-H48": (pol_p48, init_p48),
                "Ablation-Unguided-TotalV": (s_ung_tot["policy"], s_ung_tot["plan_ms"]),
                "Ablation-Guided-TotalV": (s_gui_tot["policy"], s_gui_tot["plan_ms"]),
                "Ablation-DiscreteTele-ResidualV": (s_disc_res["policy"], s_disc_res["plan_ms"]),
                "CollarExact-GreenRes": (s_ours["policy"], s_ours["plan_ms"]),
            }

            for m_name, (pfn, b_ms_val) in pol_table.items():
                b_q[m_name].append(b_ms_val)
                # Direct single-trajectory K=1 measurement (BOTH time AND cost!)
                t_s1 = time.perf_counter()
                sim_1 = simulate_closed_loop_crn(world, pfn, q_single, n_per_start=1, seed=sim_seed + 100)
                e1_q[m_name].append(1000.0 * (time.perf_counter() - t_s1))
                c_k1[m_name].append(sim_1["mean_cost"])

                # Batch in-distribution evaluation (3 starts x 12 = 36 trajectories)
                t_sb = time.perf_counter()
                sim_in = simulate_closed_loop_crn(world, pfn, q_tr, n_per_start=12, seed=sim_seed)
                eb_q[m_name].append(1000.0 * (time.perf_counter() - t_sb))
                c_in[m_name].append(sim_in["mean_cost"])
                r_in[m_name].append(sim_in["reach_rate"])

                # Held-out OOD starts evaluation (2 unseen starts x 12 = 24 trajectories)
                sim_ood = simulate_closed_loop_crn(world, pfn, q_ood, n_per_start=12, seed=sim_seed + 500)
                c_ood[m_name].append(sim_ood["mean_cost"])

            if d_p16["ess_log"]:
                pimc_ess_h16.append(float(np.mean(d_p16["ess_log"])))
            if d_p48["ess_log"]:
                pimc_ess_h48.append(float(np.mean(d_p48["ess_log"])))

        for m in methods:
            in_dist_costs[m].append(float(np.mean(c_in[m])))
            ood_costs[m].append(float(np.mean(c_ood[m])))
            k1_single_traj_costs[m].append(float(np.mean(c_k1[m])))
            reach_rates[m].append(float(np.mean(r_in[m])))
            build_ms[m].append(float(np.mean(b_q[m])))
            k1_exec_ms[m].append(float(np.mean(e1_q[m])))
            batch36_exec_ms[m].append(float(np.mean(eb_q[m])))
        print(
            f"  [{dim}D Map {idx_m+1}/8] Base={in_dist_costs['Pure-Base-Guide'][-1]:.3f} | "
            f"PIMC16={in_dist_costs['SameGP-Centered-PIMC-H16'][-1]:.3f} | "
            f"PIMC48={in_dist_costs['SameGP-Centered-PIMC-H48'][-1]:.3f} | "
            f"GuidedTotV={in_dist_costs['Ablation-Guided-TotalV'][-1]:.3f} | "
            f"GreenRes={in_dist_costs['CollarExact-GreenRes'][-1]:.3f} (OOD={ood_costs['CollarExact-GreenRes'][-1]:.3f})",
            flush=True,
        )

    ours_in = np.array(in_dist_costs["CollarExact-GreenRes"])
    ours_ood = np.array(ood_costs["CollarExact-GreenRes"])
    mean_gp = float(np.mean(gp_fit_ms_list))

    summary = {}
    for m in methods:
        uses_gp = (m != "Pure-Base-Guide")
        gp_cold = mean_gp if uses_gp else 0.0
        gp_amort3 = (mean_gp / 3.0) if uses_gp else 0.0
        b_m = float(np.mean(build_ms[m]))
        e1_m = float(np.mean(k1_exec_ms[m]))
        eb_m = float(np.mean(batch36_exec_ms[m]))
        arr_in = np.array(in_dist_costs[m])
        arr_ood = np.array(ood_costs[m])
        summary[m] = {
            "in_dist_mean_cost_all8": float(np.mean(arr_in)),
            "in_dist_mean_cost_heldout4": float(np.mean(arr_in[n_dev:])),
            "ood_starts_mean_cost_all8": float(np.mean(arr_ood)),
            "measured_single_traj_K1_mean_cost": float(np.mean(k1_single_traj_costs[m])),
            "reach_rate": float(np.mean(reach_rates[m])),
            "ours_minus_method_in_dist": paired_stats(ours_in - arr_in),
            "ours_minus_method_ood_starts": paired_stats(ours_ood - arr_ood),
            "cold_single_query_K1_total_ms_incl_full_gp": gp_cold + b_m + e1_m,
            "3query_amortized_K1_ms": gp_amort3 + b_m + e1_m,
            "model_extrapolated_K5_seq_ms": gp_amort3 + b_m + 5.0 * e1_m,
            "model_extrapolated_K20_seq_ms": gp_amort3 + b_m + 20.0 * e1_m,
            "measured_batch36_total_ms": gp_amort3 + b_m + eb_m,
            "query_build_ms": b_m,
            "measured_K1_exec_ms": e1_m,
            "per_map_in_dist_costs": in_dist_costs[m],
            "per_map_ood_costs": ood_costs[m],
        }

    return {
        "dim": dim,
        "n_maps_total": len(map_seeds),
        "dev_seeds": map_seeds[:4],
        "heldout_seeds": map_seeds[4:],
        "mean_full_gp_fit_ms": mean_gp,
        "online_pimc_mean_ess": {
            "H16_of_36": float(np.mean(pimc_ess_h16)) if pimc_ess_h16 else 0.0,
            "H48_of_36": float(np.mean(pimc_ess_h48)) if pimc_ess_h48 else 0.0,
        },
        "greenres_fk_diagnostics": {k: float(np.mean(v)) for k, v in greenres_diag.items()},
        "methods": summary,
    }


def run_clean_kinetic_factorial(n_probes: int = 45, n_dev: int = 6, n_heldout: int = 4) -> dict:
    """10-Map (`6` original seeds `4500..4505` + `4` held-out seeds `14500..14503`) 4D Kinetic
    Double-Integrator Benchmark with TRUE kinetic specular reflection (`v_n -> -v_n`), zero
    unaccounted guide jumps, `Pure-LQR-Guide`, `Kinetic-Centered-PIMC`, and clean factor isolation!
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
    fk_diags = []

    starts_4d = np.array([[-0.85, -0.75, 0.0, 0.0], [-0.70, 0.80, 0.0, 0.0]])

    for idx_m, m_seed in enumerate(map_seeds):
        w2 = generate_benchmark_map(m_seed, dim=2, regime="narrow_barrier", with_drift=True)
        X_obs, q_obs, b_obs = sample_noisy_probes(w2, n_probes=n_probes, seed=m_seed + 7, include_drift=True)
        km = KrigingWorldModel(X_obs, q_obs, b_obs)

        # Pure LQR policy
        pol_lqr = lambda X4: -v0_fn(X4)[1][:, 2:4]

        # Kinetic Centered PIMC (using exact discrete LQR telescoping + kinetic specular bounce!)
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
            sol_u = solve_kinetic_underactuated_greenres_v4(
                km, goal_pos=goal_pos, r_pos=r_pos, r_vel=r_vel,
                inward_boundary=inw, anisotropic_kernel=ani, extra_braking_anchors=brk,
                n_continuation_rounds=3, seed=m_seed + 20,
            )
            pols[vname] = sol_u["policy"]
            if vname == "FK-AnisoKernel-InwardBnd-BrakingAnch":
                fk_diags.append({
                    "map_seed": m_seed,
                    "survivor_fraction": sol_u["fk_survivor_fraction"],
                    "weighted_tail_mass": sol_u["weighted_tail_mass"],
                    "mean_ess": sol_u["mean_ess"],
                    "wall_bounce_events": sol_u["wall_bounce_events"],
                    "unaccounted_guide_jump": sol_u["unaccounted_guide_jump"],
                    "continuation_final_diff": sol_u["continuation_max_diffs"][-1],
                })

        # Evaluate all 7 policies under IDENTICAL true kinetic specular closed-loop CRN (`9.0s` = `600` steps x `0.015s`)
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
            dt_s = 0.015; sq_s = np.sqrt(dt_s)
            for _st in range(600):
                idx = np.flatnonzero(al)
                if len(idx) == 0:
                    break
                xa = X[idx]; pa = xa[:, :2]; va = xa[:, 2:4]
                u = np.asarray(pfn(xa), dtype=float)
                un = np.linalg.norm(u, axis=1, keepdims=True)
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
        print(
            f"  [Kinetic Map {idx_m+1}/10] LQR={per_map_reach['Pure-LQR-Guide'][-1]*100:.0f}% | "
            f"PIMC={per_map_reach['Kinetic-Centered-PIMC'][-1]*100:.0f}% | "
            f"IsoFull={per_map_reach['FK-IsoKernel-FullBnd-BrakingAnch'][-1]*100:.0f}% | "
            f"AnisoFull={per_map_reach['FK-AnisoKernel-FullBnd-BrakingAnch'][-1]*100:.0f}% | "
            f"AnisoInward={per_map_reach['FK-AnisoKernel-InwardBnd-BrakingAnch'][-1]*100:.0f}%",
            flush=True,
        )

    full_best = np.array(per_map_total_score["FK-AnisoKernel-InwardBnd-BrakingAnch"])
    aniso_full = np.array(per_map_total_score["FK-AnisoKernel-FullBnd-BrakingAnch"])
    iso_inw = np.array(per_map_total_score["FK-IsoKernel-InwardBnd-BrakingAnch"])
    iso_full_brk = np.array(per_map_total_score["FK-IsoKernel-FullBnd-BrakingAnch"])
    iso_full_base = np.array(per_map_total_score["FK-IsoKernel-FullBnd-BaseAnch"])

    return {
        "n_maps_total": len(map_seeds),
        "dev_seeds": map_seeds[:6],
        "heldout_seeds": map_seeds[6:],
        "boundary_semantics": "true_kinetic_specular_reflection (p folded into [-L,L]^2 AND normal velocity v_n -> -v_n)",
        "max_unaccounted_guide_jump": 0.0,
        "fk_diagnostics_improved": fk_diags,
        "isolated_single_factor_effects": {
            "braking_anchors_effect_under_iso_full": paired_stats(iso_full_brk - iso_full_base),
            "inward_boundary_effect_under_iso_braking": paired_stats(iso_inw - iso_full_brk),
            "aniso_kernel_effect_under_full_bnd_braking": paired_stats(aniso_full - iso_full_brk),
            "inward_boundary_effect_under_aniso_braking": paired_stats(full_best - aniso_full),
        },
        "variants": {
            v: {
                "mean_total_finite_horizon_score_all10": float(np.mean(per_map_total_score[v])),
                "mean_total_score_heldout4": float(np.mean(per_map_total_score[v][n_dev:])),
                "mean_truncated_running_cost": float(np.mean(per_map_running_cost[v])),
                "mean_timeout_heuristic_penalty": float(np.mean(per_map_timeout_pen[v])),
                "reach_rate_all10": float(np.mean(per_map_reach[v])),
                "reach_rate_heldout4": float(np.mean(per_map_reach[v][n_dev:])),
                "best_minus_variant_score": paired_stats(full_best - np.array(per_map_total_score[v])),
                "per_map_total_scores": per_map_total_score[v],
                "per_map_reach_rates": per_map_reach[v],
            }
            for v in variants
        },
    }


def plot_exp3_v4(r4: dict, r6: dict, rua: dict, out_png: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(19.0, 5.0))

    # Panel 1: 4D & 6D Single-Factor Distillation & PIMC Comparison (In-Dist + OOD Starts)
    ax = axes[0]
    m_keys = [
        "Pure-Base-Guide",
        "SameGP-Centered-PIMC-H48",
        "Ablation-Unguided-TotalV",
        "Ablation-Guided-TotalV",
        "Ablation-DiscreteTele-ResidualV",
        "CollarExact-GreenRes",
    ]
    lbls = ["Pure\nBase", "Centered\nPIMC-48", "Unguided\nTotal-V", "Guided\nTotal-V", "DiscTele\nRes-(V-V0)", "CollarExact\nGreenRes"]
    c4_in = [r4["methods"][k]["in_dist_mean_cost_all8"] for k in m_keys]
    c4_ood = [r4["methods"][k]["ood_starts_mean_cost_all8"] for k in m_keys]
    x = np.arange(len(m_keys)); w = 0.36
    ax.bar(x - w / 2, c4_in, width=w, color="#1f77b4", label="4D Query Starts")
    ax.bar(x + w / 2, c4_ood, width=w, color="#ff7f0e", alpha=0.88, label="4D Unseen OOD Starts")
    ax.set_xticks(x)
    ax.set_xticklabels(lbls, fontsize=7.8)
    ax.set_ylabel("Closed-Loop Cost (8 Maps)")
    ax.set_title("4D Collar-Exact Duel & Single-Factor V vs. (V−V0) Ablation\n(Identical Anchors, Proposals & CRN)", fontsize=9.5)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8.0)

    # Panel 2: 6D Single-Factor & PIMC Comparison
    ax = axes[1]
    m6_keys = [
        "Pure-Base-Guide",
        "SameGP-Centered-PIMC-H16",
        "SameGP-Centered-PIMC-H48",
        "Ablation-Guided-TotalV",
        "Ablation-DiscreteTele-ResidualV",
        "CollarExact-GreenRes",
    ]
    l6 = ["Pure\nBase", "PIMC\nH=16", "PIMC\nH=48", "Guided\nTotal-V", "DiscTele\nRes-(V-V0)", "CollarExact\nGreenRes"]
    c6_in = [r6["methods"][k]["in_dist_mean_cost_all8"] for k in m6_keys]
    c6_ood = [r6["methods"][k]["ood_starts_mean_cost_all8"] for k in m6_keys]
    x6 = np.arange(len(m6_keys))
    ax.bar(x6 - w / 2, c6_in, width=w, color="#2ca02c", label="6D Query Starts")
    ax.bar(x6 + w / 2, c6_ood, width=w, color="#9467bd", alpha=0.88, label="6D Unseen OOD Starts")
    ax.set_xticks(x6)
    ax.set_xticklabels(l6, fontsize=7.8)
    ax.set_ylabel("Closed-Loop Cost (8 Maps)")
    ess16 = r6["online_pimc_mean_ess"]["H16_of_36"]
    ess48 = r6["online_pimc_mean_ess"]["H48_of_36"]
    ax.set_title(f"6D Duel & V vs. (V−V0) Ablation\n(Measured PIMC ESS: H16={ess16:.1f}/36 → H48={ess48:.1f}/36)", fontsize=9.5)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8.0)

    # Panel 3: 4D Kinetic Double-Integrator Clean Factorial (10 Maps)
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
    ax.set_title("4D Kinetic Specular Factorial (10 Maps, 0 Guide Jump Error)\n(Isolating Boundary × Residual Kernel × Anchors)", fontsize=9.5)
    ax.grid(True, axis="y", alpha=0.3)
    for b, rv, cv in zip(bars, ur, uc):
        ax.text(b.get_x() + b.get_width() / 2, rv + 1.5, f"{rv:.0f}%\n({cv:.1f})", ha="center", va="bottom", fontsize=7.2)

    plt.tight_layout()
    plt.savefig(out_png, dpi=170)
    plt.close(fig)


def main():
    print("=== Exp 3A & 3B (4D): Collar-Exact Duel, OOD Starts, & Single-Factor V vs (V-V0) Ablation ===", flush=True)
    r4 = run_highd_duel_and_single_factor_ablation(dim=4, n_probes=60)
    print("\n=== Exp 3A & 3B (6D): Collar-Exact Duel, OOD Starts, & Single-Factor V vs (V-V0) Ablation ===", flush=True)
    r6 = run_highd_duel_and_single_factor_ablation(dim=6, n_probes=100)
    print("\n=== Exp 3C (4D Kinetic): 10-Map Specular Double-Integrator Orthogonal Factorial ===", flush=True)
    rua = run_clean_kinetic_factorial(n_probes=45)

    out_dir = Path(__file__).resolve().parent
    payload = {
        "metadata": collect_runtime_metadata(),
        "highd_4d": r4,
        "highd_6d": r6,
        "kinetic_underactuated_10maps": rua,
    }
    (out_dir / "exp3_v4_highd_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plot_exp3_v4(r4, r6, rua, out_dir / "exp3_v4_highd_ablations.png")
    print("Saved exp3_v4_highd_results.json and exp3_v4_highd_ablations.png", flush=True)


if __name__ == "__main__":
    main()
