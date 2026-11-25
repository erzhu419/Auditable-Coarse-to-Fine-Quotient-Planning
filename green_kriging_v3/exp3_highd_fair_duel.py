"""Experiment 3 (green_kriging_v3): High-D 4D/6D Fair Duel vs Antithetic Centered Long-Horizon PIMC,
Deployment Reuse Curve `T(K)`, and 4D Underactuated Reach-Rate Attribution Diagnostic.

Addresses every high-dimensional review point from `green_kriging_v2_review` Sections 6, 7, 8, 10:
1. Upgrades PIMC baseline to Antithetic + Mean-Centered Control-Variate PIMC (zero spurious
   zero-residual noise!), tested at BOTH short (`H=16`) and matched long (`H=50`) horizons.
2. Adds `Same-GP + Plain-MC Value Distillation` to isolate the Bessel base guide contribution.
3. Explicitly measures genuine `K=1` single-trajectory execution latency AND `K = 5, 20, 45`
   amortization curves `T(K)` (with zero GP fit charge on `Pure-Base`).
4. Runs a clean factor-by-factor attribution diagnostic on the 4D Underactuated reach-rate gap.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import cho_factor, cho_solve, solve_continuous_are
from scipy.stats import qmc

from core_v3 import (
    GoalBall,
    KrigingWorldModel,
    ProblemSpec,
    QueryTask,
    eval_goal_union,
    generate_benchmark_map,
    reflect_into_box,
    sample_noisy_probes,
    simulate_closed_loop_crn,
)
from exp1_pareto_and_adaptive_tour import paired_student_ci95
from highd_v3 import (
    BoxNeumannBesselBaseGuide,
    make_antithetic_centered_pimc_policy,
    solve_plain_mc_value_distillation,
    solve_reflected_telescoping_greenres,
)


def make_highd_queries(map_seed: int, dim: int, n_queries: int = 3) -> List[QueryTask]:
    rng = np.random.default_rng(map_seed + 600)
    r_goal = 0.36
    queries = []
    for k in range(n_queries):
        n_g = 2 if k == 2 else 1
        goals = []
        for gj in range(n_g):
            for _att in range(50):
                gc = rng.uniform(-1.00, 1.00, size=dim)
                gc[2:] *= 0.65
                if all(np.linalg.norm(gc - np.asarray(p.center)) >= 2.25 * r_goal for p in goals):
                    goals.append(GoalBall(tuple(gc.tolist()), phi=0.0 if gj == 0 else 0.20, radius=r_goal))
                    break
        starts = []
        for _s in range(3):
            for _att in range(50):
                st = rng.uniform(-1.05, 1.05, size=dim)
                st[2:] *= 0.65
                if all(np.linalg.norm(st - np.asarray(g.center)) >= 2.5 * r_goal + 0.30 for g in goals):
                    starts.append(tuple(st.tolist()))
                    break
        queries.append(QueryTask(f"HD{dim}_M{map_seed}_Q{k+1}", tuple(goals), tuple(starts)))
    return queries


def run_highd_duel(dim: int, n_maps: int = 8, n_probes: int = 65) -> dict:
    methods = [
        "Pure-Base-Guide",
        "SameGP-PlainMC-Distill",
        "SameGP-Centered-PIMC-H16",
        "SameGP-Centered-PIMC-H48",
        "SameGP-Reflected-GreenRes",
    ]
    map_costs: Dict[str, List[float]] = {m: [] for m in methods}
    map_reach: Dict[str, List[float]] = {m: [] for m in methods}
    map_clips: Dict[str, List[float]] = {m: [] for m in methods}
    map_plan_ms: Dict[str, List[float]] = {m: [] for m in methods}
    map_exec1_ms: Dict[str, List[float]] = {m: [] for m in methods}
    map_exec45_ms: Dict[str, List[float]] = {m: [] for m in methods}
    gp_ms_list = []

    spec = ProblemSpec(dim=dim, half_width=1.65, sigma=0.55, q0=0.65, dt_sim=0.020, max_steps=420)

    for m_i in range(n_maps):
        map_seed = (2200 if dim == 4 else 3200) + m_i
        world = generate_benchmark_map(map_seed, dim=dim, regime="smooth", with_drift=True, spec=spec)
        queries = make_highd_queries(map_seed, dim=dim, n_queries=3)
        X_obs, q_obs, b_obs = sample_noisy_probes(world, n_probes=n_probes, seed=map_seed + 7, include_drift=True)
        km = KrigingWorldModel(X_obs, q_obs, b_obs)
        gp_ms_list.append(km.fit_ms)

        c_q = {m: [] for m in methods}
        r_q = {m: [] for m in methods}
        cl_q = {m: [] for m in methods}
        pl_q = {m: [] for m in methods}
        e1_q = {m: [] for m in methods}
        e45_q = {m: [] for m in methods}

        for qi, q in enumerate(queries):
            crn_s = 8000 + 20 * m_i + qi
            q_single_start = QueryTask(q.name + "_k1", q.goals, (q.start_points[0],), q.local_hazards)

            # 1. Pure Base Guide (ZERO GP charge!)
            t0 = time.perf_counter()
            base = BoxNeumannBesselBaseGuide(spec, q)
            b_init_ms = 1000.0 * (time.perf_counter() - t0)
            pol_b = lambda X, _b=base: -_b.val_and_grad(X)[1]
            s1_b = simulate_closed_loop_crn(world, pol_b, q_single_start, n_per_start=1, seed=crn_s)
            s45_b = simulate_closed_loop_crn(world, pol_b, q, n_per_start=15, seed=crn_s)
            c_q["Pure-Base-Guide"].append(s45_b["mean_cost"]); r_q["Pure-Base-Guide"].append(s45_b["reach_rate"])
            cl_q["Pure-Base-Guide"].append(s45_b["clip_fraction"]); pl_q["Pure-Base-Guide"].append(b_init_ms)
            e1_q["Pure-Base-Guide"].append(s1_b["rollout_ms"]); e45_q["Pure-Base-Guide"].append(s45_b["rollout_ms"])

            # 2. Same-GP Plain-MC Value Distillation (no Bessel control variate)
            sol_mc = solve_plain_mc_value_distillation(spec, km, q, n_interior_anchors=88 if dim == 4 else 108, n_mc_paths=64, n_steps_fk=75, seed=crn_s + 1)
            s1_mc = simulate_closed_loop_crn(world, sol_mc["policy"], q_single_start, n_per_start=1, seed=crn_s)
            s45_mc = simulate_closed_loop_crn(world, sol_mc["policy"], q, n_per_start=15, seed=crn_s)
            c_q["SameGP-PlainMC-Distill"].append(s45_mc["mean_cost"]); r_q["SameGP-PlainMC-Distill"].append(s45_mc["reach_rate"])
            cl_q["SameGP-PlainMC-Distill"].append(s45_mc["clip_fraction"]); pl_q["SameGP-PlainMC-Distill"].append(sol_mc["plan_ms"])
            e1_q["SameGP-PlainMC-Distill"].append(s1_mc["rollout_ms"]); e45_q["SameGP-PlainMC-Distill"].append(s45_mc["rollout_ms"])

            # 3. Same-GP Antithetic Centered PIMC (H=16)
            pol_p16, p16_init = make_antithetic_centered_pimc_policy(spec, km, q, n_particles=36, horizon_steps=16, seed=crn_s + 2)
            s1_p16 = simulate_closed_loop_crn(world, pol_p16, q_single_start, n_per_start=1, seed=crn_s)
            s45_p16 = simulate_closed_loop_crn(world, pol_p16, q, n_per_start=15, seed=crn_s)
            c_q["SameGP-Centered-PIMC-H16"].append(s45_p16["mean_cost"]); r_q["SameGP-Centered-PIMC-H16"].append(s45_p16["reach_rate"])
            cl_q["SameGP-Centered-PIMC-H16"].append(s45_p16["clip_fraction"]); pl_q["SameGP-Centered-PIMC-H16"].append(p16_init)
            e1_q["SameGP-Centered-PIMC-H16"].append(s1_p16["rollout_ms"]); e45_q["SameGP-Centered-PIMC-H16"].append(s45_p16["rollout_ms"])

            # 4. Same-GP Antithetic Centered PIMC (Long Horizon H=48)
            pol_p48, p48_init = make_antithetic_centered_pimc_policy(spec, km, q, n_particles=36, horizon_steps=48, seed=crn_s + 3)
            s1_p48 = simulate_closed_loop_crn(world, pol_p48, q_single_start, n_per_start=1, seed=crn_s)
            s45_p48 = simulate_closed_loop_crn(world, pol_p48, q, n_per_start=15, seed=crn_s)
            c_q["SameGP-Centered-PIMC-H48"].append(s45_p48["mean_cost"]); r_q["SameGP-Centered-PIMC-H48"].append(s45_p48["reach_rate"])
            cl_q["SameGP-Centered-PIMC-H48"].append(s45_p48["clip_fraction"]); pl_q["SameGP-Centered-PIMC-H48"].append(p48_init)
            e1_q["SameGP-Centered-PIMC-H48"].append(s1_p48["rollout_ms"]); e45_q["SameGP-Centered-PIMC-H48"].append(s45_p48["rollout_ms"])

            # 5. Same-GP Reflected GreenRes (Ours)
            sol_gr = solve_reflected_telescoping_greenres(spec, km, q, n_interior_anchors=88 if dim == 4 else 108, n_mc_paths=64, n_steps_fk=75, seed=crn_s + 4)
            s1_gr = simulate_closed_loop_crn(world, sol_gr["policy"], q_single_start, n_per_start=1, seed=crn_s)
            s45_gr = simulate_closed_loop_crn(world, sol_gr["policy"], q, n_per_start=15, seed=crn_s)
            c_q["SameGP-Reflected-GreenRes"].append(s45_gr["mean_cost"]); r_q["SameGP-Reflected-GreenRes"].append(s45_gr["reach_rate"])
            cl_q["SameGP-Reflected-GreenRes"].append(s45_gr["clip_fraction"]); pl_q["SameGP-Reflected-GreenRes"].append(sol_gr["plan_ms"])
            e1_q["SameGP-Reflected-GreenRes"].append(s1_gr["rollout_ms"]); e45_q["SameGP-Reflected-GreenRes"].append(s45_gr["rollout_ms"])

        for m in methods:
            map_costs[m].append(float(np.mean(c_q[m])))
            map_reach[m].append(float(np.mean(r_q[m])))
            map_clips[m].append(float(np.mean(cl_q[m])))
            map_plan_ms[m].append(float(np.mean(pl_q[m])))
            map_exec1_ms[m].append(float(np.mean(e1_q[m])))
            map_exec45_ms[m].append(float(np.mean(e45_q[m])))

        print(
            f"  [{dim}D map {m_i+1}/{n_maps}] Base={map_costs['Pure-Base-Guide'][-1]:.3f} | "
            f"PIMC16={map_costs['SameGP-Centered-PIMC-H16'][-1]:.3f} | "
            f"PIMC48={map_costs['SameGP-Centered-PIMC-H48'][-1]:.3f} | "
            f"GreenRes={map_costs['SameGP-Reflected-GreenRes'][-1]:.3f} (K1_exec={map_exec1_ms['SameGP-Reflected-GreenRes'][-1]:.1f}ms vs PIMC48={map_exec1_ms['SameGP-Centered-PIMC-H48'][-1]:.0f}ms)",
            flush=True,
        )

    ours_arr = np.array(map_costs["SameGP-Reflected-GreenRes"])
    gp_mean = float(np.mean(gp_ms_list))
    summary = {"dim": dim, "n_maps": n_maps, "n_probes": n_probes, "mean_gp_fit_ms": gp_mean, "methods": {}}

    for m in methods:
        arr = np.array(map_costs[m])
        dm, ci = paired_student_ci95(ours_arr - arr)
        gp_charge = 0.0 if m == "Pure-Base-Guide" else gp_mean / 3.0
        pl = float(np.mean(map_plan_ms[m]))
        e1 = float(np.mean(map_exec1_ms[m]))
        e45 = float(np.mean(map_exec45_ms[m]))
        summary["methods"][m] = {
            "mean_cost": float(np.mean(arr)),
            "reach_rate": float(np.mean(map_reach[m])),
            "clip_fraction": float(np.mean(map_clips[m])),
            "ours_minus_method_cost": {"mean": dm, "student_t_ci95": ci},
            "gp_amortized_ms": gp_charge,
            "query_build_ms": pl,
            "single_traj_exec_ms": e1,
            "batch45_exec_ms": e45,
            "amortized_T_K1_sequential_ms": gp_charge + pl + e1,
            "amortized_T_K5_sequential_ms": gp_charge + pl + 5.0 * e1,
            "amortized_T_K20_sequential_ms": gp_charge + pl + 20.0 * e1,
            "amortized_T_batch45_ms": gp_charge + pl + e45,
            "per_map_costs": map_costs[m],
        }
    return summary


def run_underactuated_attribution_diagnostic(n_maps: int = 6, n_probes: int = 40) -> dict:
    """Factor-by-factor diagnosis of v2's `64.9% vs 77.3%` reach-rate gap on 4D Underactuated Inertial Control:
      - Factor 1: v2 short simulation cutoff (`T_sim = 5.7s`, where inertial braking trajectories were still decelerating)
                  vs generous `T_sim = 9.0s` (`600` steps) + post-step absorption check!
      - Factor 2: Isotropic residual kernel (`ell = 0.68`) without inward-velocity boundary distinction
                  vs Anisotropic phase-space kernel (`ell_p = 0.42, ell_v = 0.90`) + collar braking anchors
                  applied ONLY to inward-moving goal boundary states (`(p - g) . v < 0`)!
    """
    gamma = 0.65; sigma = 0.42; lam = sigma ** 2; q0 = 0.50; r_goal = 0.24; c_vel = 0.15
    A_lin = np.array([[0, 0, 1, 0], [0, 0, 0, 1], [0, 0, -gamma, 0], [0, 0, 0, -gamma]], dtype=float)
    G_mat = np.array([[0, 0], [0, 0], [1, 0], [0, 1]], dtype=float)
    P_lqr = solve_continuous_are(A_lin, G_mat, np.diag([1.6, 1.6, 0.25, 0.25]), np.eye(2))
    tr_Pvv = float(P_lqr[2, 2] + P_lqr[3, 3])

    configs = [
        "Centered-LQRGuided-PIMC",
        "GreenRes-Iso-ShortSim(v2-like)",
        "GreenRes-Iso-LongSim(9s)",
        "GreenRes-AnisoInwardBnd-LongSim(9s)",
    ]
    map_costs = {c: [] for c in configs}
    map_reach = {c: [] for c in configs}
    map_vel_clips = {c: [] for c in configs}

    for m_i in range(n_maps):
        map_seed = 4500 + m_i
        w2d = generate_benchmark_map(map_seed, dim=2, regime="smooth", with_drift=True)
        X_obs, q_obs, b_obs = sample_noisy_probes(w2d, n_probes=n_probes, seed=map_seed + 3, include_drift=True)
        km2d = KrigingWorldModel(X_obs, q_obs, b_obs)
        gc = np.array([0.78, 0.72])
        starts = np.array([[-0.80, -0.75, 0.55, 0.50], [-0.75, 0.68, 0.45, -0.35]])

        def _v0_and_grad(X4: np.ndarray):
            dx = X4 - np.array([[gc[0], gc[1], 0.0, 0.0]])
            Pd = dx @ P_lqr
            return 0.5 * np.sum(dx * Pd, axis=1), Pd

        def _r0_ua(X4: np.ndarray, qh: np.ndarray, fw: np.ndarray) -> np.ndarray:
            _, gv = _v0_and_grad(X4)
            v = X4[:, 2:4]
            return q0 + qh + np.sum(v * gv[:, 0:2], axis=1) + np.sum((-gamma * v + fw) * gv[:, 2:4], axis=1) + 0.5 * (sigma ** 2) * tr_Pvv - 0.5 * np.sum(gv[:, 2:4] ** 2, axis=1)

        def _fit_ua_greenres(aniso_inward: bool, seed_f: int):
            rng = np.random.default_rng(seed_f)
            ang = rng.uniform(0, 2 * np.pi, size=48)
            n_out = np.column_stack([np.cos(ang), np.sin(ang)])
            p_b = gc[None, :] + r_goal * n_out
            v_b = rng.uniform(-1.1, 1.1, size=(48, 2))
            if aniso_inward:
                # Kinematic entry condition: trajectory approaching goal from outside satisfies `(p - g) . v < 0`!
                dot_nv = np.sum(n_out * v_b, axis=1)
                v_b = np.where((dot_nv >= 0)[:, None], v_b - (dot_nv[:, None] + 0.25) * n_out, v_b)
            X_bnd = np.hstack([p_b, v_b])
            v0_b, _ = _v0_and_grad(X_bnd)
            y_bnd = c_vel * np.sum(v_b ** 2, axis=1) - v0_b

            sob = qmc.Sobol(d=4, scramble=True, seed=seed_f)
            ur = sob.random(104) * 2.0 - 1.0
            X_int = np.column_stack([ur[:, 0:2] * 1.15, ur[:, 2:4] * 1.30])
            if aniso_inward:
                # Add 24 braking-collar anchors around goal!
                ang_c = rng.uniform(0, 2 * np.pi, size=24)
                rad_c = rng.uniform(r_goal + 0.05, r_goal + 0.35, size=24)
                pc = gc[None, :] + rad_c[:, None] * np.column_stack([np.cos(ang_c), np.sin(ang_c)])
                vc = rng.uniform(-1.2, 1.2, size=(24, 2))
                X_int = np.vstack([starts, X_int, np.hstack([pc, vc])])
            else:
                X_int = np.vstack([starts, X_int])
            X_int = X_int[np.linalg.norm(X_int[:, 0:2] - gc[None, :], axis=1) > r_goal + 0.03]

            M_fk = 64; hm = 32; dt_f = 0.04; sq = np.sqrt(dt_f)
            pos4 = np.repeat(X_int[:, None, :], M_fk, axis=1)
            al = np.ones((len(X_int), M_fk), dtype=bool)
            acc = np.zeros((len(X_int), M_fk))
            tres = np.zeros((len(X_int), M_fk))
            for _st in range(75):
                if not np.any(al): break
                zh = rng.normal(0.0, sq, size=(len(X_int), hm, 2))
                dw = np.concatenate([zh, -zh], axis=1)
                ai, aj = np.where(al)
                cur = pos4[ai, aj]; p_c = cur[:, 0:2]; v_c = cur[:, 2:4]
                _, gv = _v0_and_grad(cur)
                u0 = -gv[:, 2:4]
                qh = km2d.predict_q(p_c); bh = km2d.predict_b(p_c)
                acc[ai, aj] += _r0_ua(cur, qh, bh) * dt_f
                pn = reflect_into_box(p_c + v_c * dt_f, 1.65)
                vn = np.clip(v_c + (-gamma * v_c + bh + u0) * dt_f + sigma * dw[ai, aj], -3.5, 3.5)
                nxt = np.hstack([pn, vn])
                pos4[ai, aj] = nxt
                hit = np.linalg.norm(pn - gc[None, :], axis=1) <= r_goal
                if np.any(hit):
                    hl = np.flatnonzero(hit)
                    v0_h, _ = _v0_and_grad(nxt[hl])
                    tres[ai[hl], aj[hl]] = c_vel * np.sum(vn[hl] ** 2, axis=1) - v0_h
                    al[ai[hl], aj[hl]] = False

            ell_vec = np.array([0.42, 0.42, 0.90, 0.90]) if aniso_inward else np.full(4, 0.68)
            X_all = np.vstack([X_int, X_bnd])
            nv = np.concatenate([np.full(len(X_int), 3e-3), np.full(len(X_bnd), 1e-5)])

            def _fit_ard_gp(y_vals: np.ndarray):
                ym = float(np.mean(y_vals)); ys = float(max(np.std(y_vals - ym), 1e-6))
                Xs = X_all / ell_vec[None, :]
                diff = Xs[:, None, :] - Xs[None, :, :]
                s = np.sqrt(5.0 * np.sum(diff ** 2, axis=2))
                K = (1.0 + s + (s ** 2) / 3.0) * np.exp(-s)
                K[np.diag_indices_from(K)] += nv
                c_f, lw = cho_factor(K, lower=True)
                al_w = cho_solve((c_f, lw), (y_vals - ym) / ys) * ys

                def _pred(Xq: np.ndarray):
                    Xqs = np.atleast_2d(Xq) / ell_vec[None, :]
                    df = Xqs[:, None, :] - Xs[None, :, :]
                    sq_r = np.sqrt(5.0 * np.sum(df ** 2, axis=2))
                    es = np.exp(-sq_r)
                    val = ym + ((1.0 + sq_r + (sq_r ** 2) / 3.0) * es) @ al_w
                    cf = -(5.0 / 3.0) * (1.0 + sq_r) * es * al_w[None, :]
                    grad = np.einsum("ij,ijd->id", cf, df) / ell_vec[None, :]
                    return val, grad
                return _pred

            def _lme(em):
                mx = np.max(em, axis=1, keepdims=True)
                return -lam * (mx[:, 0] + np.log(np.maximum(np.mean(np.exp(em - mx), axis=1), 1e-300)))

            gp1 = _fit_ard_gp(np.concatenate([_lme(-(acc + np.where(al, 0.0, tres)) / lam), y_bnd]))
            tl = np.zeros_like(tres)
            ai, aj = np.where(al)
            if len(ai) > 0:
                tl[ai, aj] = gp1(pos4[ai, aj])[0]
            gp2 = _fit_ard_gp(np.concatenate([_lme(-(acc + np.where(al, tl, tres)) / lam), y_bnd]))
            return lambda X4: -(_v0_and_grad(X4)[1][:, 2:4] + gp2(X4)[1][:, 2:4])

        pol_iso = _fit_ua_greenres(aniso_inward=False, seed_f=map_seed + 20)
        pol_ani = _fit_ua_greenres(aniso_inward=True, seed_f=map_seed + 20)

        rng_p = np.random.default_rng(map_seed + 30)
        def _centered_pimc_ua(X4: np.ndarray):
            X4 = np.atleast_2d(X4); nb = len(X4); hm = 18; M = 36; dt_m = 0.04; sq = np.sqrt(dt_m)
            _, gv0 = _v0_and_grad(X4); u0_s = -gv0[:, 2:4]
            z0 = rng_p.normal(0.0, sq, size=(nb, hm, 2))
            eps0 = np.concatenate([z0, -z0], axis=1)
            pos4 = np.repeat(X4[:, None, :], M, axis=1); al = np.ones((nb, M), dtype=bool); acc = np.zeros((nb, M))
            for st in range(18):
                if not np.any(al): break
                dw = eps0 if st == 0 else np.concatenate([z := rng_p.normal(0.0, sq, size=(nb, hm, 2)), -z], axis=1)
                ai, aj = np.where(al); cur = pos4[ai, aj]; p_c = cur[:, 0:2]; v_c = cur[:, 2:4]
                _, gvs = _v0_and_grad(cur); up = -gvs[:, 2:4]
                qh = km2d.predict_q(p_c); bh = km2d.predict_b(p_c)
                acc[ai, aj] += _r0_ua(cur, qh, bh) * dt_m
                pn = reflect_into_box(p_c + v_c * dt_m, 1.65)
                vn = np.clip(v_c + (-gamma * v_c + bh + up) * dt_m + sigma * dw[ai, aj], -3.5, 3.5)
                nxt = np.hstack([pn, vn]); pos4[ai, aj] = nxt
                hit = np.linalg.norm(pn - gc[None, :], axis=1) <= r_goal
                if np.any(hit):
                    hl = np.flatnonzero(hit); v0_h, _ = _v0_and_grad(nxt[hl])
                    acc[ai[hl], aj[hl]] += c_vel * np.sum(vn[hl] ** 2, axis=1) - v0_h
                    al[ai[hl], aj[hl]] = False
            ex = -acc / lam; mx = np.max(ex, axis=1, keepdims=True); w = np.exp(ex - mx)
            w /= np.maximum(np.sum(w, axis=1, keepdims=True), 1e-30)
            return u0_s + (sigma / dt_m) * np.einsum("bm,bmd->bd", w - 1.0 / M, eps0)

        def _roll_ua(pol_fn, max_steps_sim: int) -> Tuple[float, float, float]:
            st_rep = np.repeat(starts, 18, axis=0); n_tr = len(st_rep); dt = 0.015; sq = np.sqrt(dt)
            ss = np.random.SeedSequence([map_seed, 909])
            dW = np.array([np.random.default_rng(c).normal(0.0, sq, size=(600, 2)) for c in ss.spawn(n_tr)])
            x = st_rep.copy(); al = np.ones(n_tr, dtype=bool); rch = np.zeros(n_tr, dtype=bool); cs = np.zeros(n_tr)
            v_clips = 0; tot_ev = 0
            for s_i in range(max_steps_sim):
                idx = np.flatnonzero(al)
                if len(idx) == 0: break
                xa = x[idx]; pa = xa[:, 0:2]; va = xa[:, 2:4]
                u = pol_fn(xa); un = np.linalg.norm(u, axis=1, keepdims=True)
                u = np.where(un > 20.0, u * (20.0 / np.maximum(un, 1e-12)), u)
                cs[idx] += (q0 + w2d.q_hidden(pa) + 0.5 * np.sum(u ** 2, axis=1)) * dt
                pn = reflect_into_box(pa + va * dt, 1.65)
                vr = va + (-gamma * va + w2d.drift(pa) + u) * dt + sigma * dW[idx, s_i, :]
                v_clips += int(np.sum(np.any(np.abs(vr) > 3.5, axis=1))); tot_ev += len(idx)
                vn = np.clip(vr, -3.5, 3.5)
                x[idx] = np.hstack([pn, vn])
                hit = np.linalg.norm(pn - gc[None, :], axis=1) <= r_goal
                if np.any(hit):
                    hg = idx[hit]
                    cs[hg] += c_vel * np.sum(vn[hit] ** 2, axis=1)
                    rch[hg] = True; al[hg] = False
            if np.any(al):
                cs[al] += _v0_and_grad(x[al])[0] + 2.0
            return float(np.mean(cs)), float(np.mean(rch)), float(v_clips / max(tot_ev, 1))

        for cname, pfn, msteps in [
            ("Centered-LQRGuided-PIMC", _centered_pimc_ua, 600),
            ("GreenRes-Iso-ShortSim(v2-like)", pol_iso, 380),
            ("GreenRes-Iso-LongSim(9s)", pol_iso, 600),
            ("GreenRes-AnisoInwardBnd-LongSim(9s)", pol_ani, 600),
        ]:
            c_v, r_v, vc_v = _roll_ua(pfn, msteps)
            map_costs[cname].append(c_v); map_reach[cname].append(r_v); map_vel_clips[cname].append(vc_v)

    return {
        "n_maps": n_maps,
        "configs": {
            c: {
                "mean_cost": float(np.mean(map_costs[c])),
                "reach_rate": float(np.mean(map_reach[c])),
                "vel_clip_fraction": float(np.mean(map_vel_clips[c])),
            }
            for c in configs
        },
    }


def plot_exp3(d4: dict, d6: dict, ua: dict, out_png: Path):
    fig, axes = plt.subplots(1, 3, figsize=(17.2, 4.8))
    ks = [1, 5, 20]
    k_keys = ["amortized_T_K1_sequential_ms", "amortized_T_K5_sequential_ms", "amortized_T_K20_sequential_ms"]

    for ax, data, d_lbl in [(axes[0], d4, "4D"), (axes[1], d6, "6D")]:
        for m, col, ls, lbl in [
            ("SameGP-Centered-PIMC-H16", "#ff7f0e", "--", f"{d_lbl} Centered PIMC (H=16, Cost={data['methods']['SameGP-Centered-PIMC-H16']['mean_cost']:.2f})"),
            ("SameGP-Centered-PIMC-H48", "#d62728", "-", f"{d_lbl} Centered PIMC (H=48, Cost={data['methods']['SameGP-Centered-PIMC-H48']['mean_cost']:.2f})"),
            ("SameGP-PlainMC-Distill", "#9467bd", ":", f"{d_lbl} Plain-MC Distill (Cost={data['methods']['SameGP-PlainMC-Distill']['mean_cost']:.2f})"),
            ("SameGP-Reflected-GreenRes", "#1f77b4", "-", f"{d_lbl} Reflected GreenRes (Cost={data['methods']['SameGP-Reflected-GreenRes']['mean_cost']:.2f})"),
        ]:
            ts = [data["methods"][m][kk] for kk in k_keys]
            ax.plot(ks, ts, marker="o", color=col, ls=ls, lw=2.1, label=lbl)
        ax.set_yscale("log")
        ax.set_xticks(ks)
        ax.set_xlabel("Sequential Deployments K on Same Query")
        ax.set_ylabel("Cumulative Wall-Clock Time T(K) (ms, log)")
        ax.set_title(f"{d_lbl} Amortization Curve vs Centered PIMC (8 Maps)")
        ax.grid(True, alpha=0.3, which="both")
        ax.legend(fontsize=7.4)

    ua_keys = list(ua["configs"].keys())
    ua_lbls = ["Centered\nPIMC (9s)", "Iso GreenRes\n(5.7s Cutoff)", "Iso GreenRes\n(9.0s Sim)", "Aniso+Inward\nGreenRes (9s)"]
    rchs = [100.0 * ua["configs"][k]["reach_rate"] for k in ua_keys]
    csts = [ua["configs"][k]["mean_cost"] for k in ua_keys]
    bars = axes[2].bar(np.arange(4), rchs, width=0.52, color=["#ff7f0e", "#d62728", "#9467bd", "#1f77b4"])
    axes[2].set_xticks(np.arange(4))
    axes[2].set_xticklabels(ua_lbls, fontsize=8.2)
    axes[2].set_ylabel("Goal Reach Rate (%)")
    axes[2].set_ylim(0, 114)
    axes[2].set_title("4D Underactuated Reach-Rate Attribution (6 Maps)")
    axes[2].grid(True, axis="y", alpha=0.3)
    for b, r_v, c_v in zip(bars, rchs, csts):
        axes[2].text(b.get_x() + b.get_width() / 2, r_v + 1.5, f"{r_v:.1f}%\n(Cost={c_v:.1f})", ha="center", va="bottom", fontsize=8.0)

    plt.tight_layout()
    plt.savefig(out_png, dpi=170)
    plt.close(fig)


def main():
    print("=== Exp 3A-1: 4D Fair Duel vs Antithetic Centered PIMC (8 maps x 3 queries) ===", flush=True)
    d4 = run_highd_duel(dim=4, n_maps=8, n_probes=60)
    print("\n=== Exp 3A-2: 6D Fair Duel vs Antithetic Centered PIMC (8 maps x 3 queries) ===", flush=True)
    d6 = run_highd_duel(dim=6, n_maps=8, n_probes=100)
    print("\n=== Exp 3B: 4D Underactuated Reach-Rate Attribution Diagnostic (6 maps) ===", flush=True)
    ua = run_underactuated_attribution_diagnostic(n_maps=6, n_probes=40)
    for k, v in ua["configs"].items():
        print(f"  UA {k:38s} | Reach={v['reach_rate']*100:.1f}% | Cost={v['mean_cost']:.3f} | VelClip={v['vel_clip_fraction']*100:.2f}%", flush=True)

    out_dir = Path(__file__).resolve().parent
    res = {"highd_4d": d4, "highd_6d": d6, "underactuated_attribution": ua}
    (out_dir / "exp3_highd_fair_results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    plot_exp3(d4, d6, ua, out_dir / "exp3_highd_fair_duel.png")
    print("Saved exp3_highd_fair_results.json and exp3_highd_fair_duel.png", flush=True)


if __name__ == "__main__":
    main()
