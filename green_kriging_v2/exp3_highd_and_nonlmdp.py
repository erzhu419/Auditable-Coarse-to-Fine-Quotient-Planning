"""Battle 3 & 4 (v2):
- Battle 3A: 4D & 6D Unified Base-Green + Continuation Residual vs Same-GP Online PIMC (8 Maps).
- Battle 3B: 4D Underactuated Double Integrator with Unified Exact r0 & Boundary Residual (8 Maps).
- Battle 4: Corrected Monotone KKT Non-LMDP Benchmark (Anisotropic R + Euclidean Ball u_max, 10 Maps).
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
from scipy.stats import qmc

from core_spec_and_gp import (
    GoalBall,
    GroundTruthWorld,
    HazardBump,
    KrigingWorldModel,
    ProblemSpec,
    QueryTask,
    eval_bumps,
    generate_random_map,
    reflect_into_box,
    sample_noisy_probes,
    simulate_closed_loop_crn,
    solve_anisotropic_ball_qp,
)
from solvers_2d3d import (
    ReusableGreenOperator2D3D,
    solve_monotone_anisotropic_constrained_hjb_2d,
)
from solvers_highd import (
    AnalyticMatern52ResidualGP,
    CapacitaryBesselBaseGuide,
    UnifiedUnderactuatedLQRGuide4D,
    make_same_gp_online_pimc_policy,
    solve_unified_highd_green_residual,
)


def paired_ci95(diffs: Sequence[float]) -> Tuple[float, float]:
    arr = np.asarray(diffs, dtype=float)
    m = float(np.mean(arr))
    se = float(np.std(arr, ddof=1) / np.sqrt(len(arr))) if len(arr) > 1 else 0.0
    return m, 1.96 * se


def run_battle3a_highd(dim: int, n_maps: int = 8, n_probes: int = 65) -> dict:
    methods = [
        "Pure-Base-Guide",
        "SameGP-Unguided-PIMC",
        "SameGP-BaseGuided-PIMC",
        "SameGP-Unified-GreenRes",
    ]
    map_costs: Dict[str, List[float]] = {m: [] for m in methods}
    map_reach: Dict[str, List[float]] = {m: [] for m in methods}
    map_plan_ms: Dict[str, List[float]] = {m: [] for m in methods}
    map_roll_ms: Dict[str, List[float]] = {m: [] for m in methods}
    gp_ms_list = []
    surv_list = []
    ess_list = []

    spec = ProblemSpec(dim=dim, half_width=1.65, sigma=0.55, q0=0.65, dt_sim=0.020, max_steps=420)

    for m_i in range(n_maps):
        map_seed = (2000 if dim == 4 else 3000) + m_i
        world, queries = generate_random_map(map_seed, dim=dim, with_drift=True, n_queries=3, spec=spec)
        X_obs, q_obs, b_obs = sample_noisy_probes(world, n_probes=n_probes, seed=map_seed + 7, probe_box=1.20, include_drift=True)
        km = KrigingWorldModel(X_obs, q_obs, b_obs)
        gp_ms_list.append(km.fit_ms)

        c_acc = {m: [] for m in methods}
        r_acc = {m: [] for m in methods}
        p_acc = {m: [] for m in methods}
        rl_acc = {m: [] for m in methods}

        for qi, q in enumerate(queries):
            crn_seed = 7000 + 10 * m_i + qi
            n_per_s = 15  # 3 starts x 15 = 45 CRN rollouts per query

            # 1. Pure Base Guide
            t0 = time.perf_counter()
            base = CapacitaryBesselBaseGuide(spec, q)
            p_ms = 1000.0 * (time.perf_counter() - t0)
            sim = simulate_closed_loop_crn(world, lambda X, _b=base: -_b.val_and_grad(X)[1], q, n_per_start=n_per_s, seed=crn_seed)
            c_acc["Pure-Base-Guide"].append(sim["mean_cost"]); r_acc["Pure-Base-Guide"].append(sim["reach_rate"])
            p_acc["Pure-Base-Guide"].append(p_ms); rl_acc["Pure-Base-Guide"].append(sim["rollout_ms"])

            # 2. Same-GP + Unguided Online PIMC
            pol_ug = make_same_gp_online_pimc_policy(spec, km, q, guided=False, n_particles=36, horizon_steps=14, seed=crn_seed + 1)
            sim_ug = simulate_closed_loop_crn(world, pol_ug, q, n_per_start=n_per_s, seed=crn_seed)
            c_acc["SameGP-Unguided-PIMC"].append(sim_ug["mean_cost"]); r_acc["SameGP-Unguided-PIMC"].append(sim_ug["reach_rate"])
            p_acc["SameGP-Unguided-PIMC"].append(0.0); rl_acc["SameGP-Unguided-PIMC"].append(sim_ug["rollout_ms"])

            # 3. Same-GP + BaseGuided Online PIMC
            pol_bg = make_same_gp_online_pimc_policy(spec, km, q, guided=True, n_particles=36, horizon_steps=14, seed=crn_seed + 2)
            sim_bg = simulate_closed_loop_crn(world, pol_bg, q, n_per_start=n_per_s, seed=crn_seed)
            c_acc["SameGP-BaseGuided-PIMC"].append(sim_bg["mean_cost"]); r_acc["SameGP-BaseGuided-PIMC"].append(sim_bg["reach_rate"])
            p_acc["SameGP-BaseGuided-PIMC"].append(0.0); rl_acc["SameGP-BaseGuided-PIMC"].append(sim_bg["rollout_ms"])

            # 4. Same-GP + Unified Green-Residual Distillation (Ours)
            sol_gr = solve_unified_highd_green_residual(
                spec, km, q,
                n_interior_anchors=88 if dim == 4 else 108,
                n_mc_paths=64,
                n_steps_fk=75,
                dt_fk=0.045,
                seed=crn_seed + 3,
            )
            sim_gr = simulate_closed_loop_crn(world, sol_gr["policy"], q, n_per_start=n_per_s, seed=crn_seed)
            c_acc["SameGP-Unified-GreenRes"].append(sim_gr["mean_cost"]); r_acc["SameGP-Unified-GreenRes"].append(sim_gr["reach_rate"])
            p_acc["SameGP-Unified-GreenRes"].append(sol_gr["plan_ms"]); rl_acc["SameGP-Unified-GreenRes"].append(sim_gr["rollout_ms"])
            surv_list.append(sol_gr["survivor_fraction"])
            ess_list.append(sol_gr["mean_ess"])

        for m in methods:
            map_costs[m].append(float(np.mean(c_acc[m])))
            map_reach[m].append(float(np.mean(r_acc[m])))
            map_plan_ms[m].append(float(np.mean(p_acc[m])))
            map_roll_ms[m].append(float(np.mean(rl_acc[m])))
        print(f"    [{dim}D map {m_i+1}/{n_maps}] GuidedPIMC={map_costs['SameGP-BaseGuided-PIMC'][-1]:.2f} ({map_roll_ms['SameGP-BaseGuided-PIMC'][-1]:.0f}ms) | Ours={map_costs['SameGP-Unified-GreenRes'][-1]:.2f} (plan={map_plan_ms['SameGP-Unified-GreenRes'][-1]:.0f}ms, roll={map_roll_ms['SameGP-Unified-GreenRes'][-1]:.0f}ms)", flush=True)

    ours_arr = np.array(map_costs["SameGP-Unified-GreenRes"])
    summary = {
        "dim": dim,
        "n_maps": n_maps,
        "n_probes": n_probes,
        "mean_gp_fit_ms": float(np.mean(gp_ms_list)),
        "mean_fk_survivor_fraction": float(np.mean(surv_list)),
        "mean_fk_ess_out_of_64": float(np.mean(ess_list)),
        "methods": {},
    }
    mean_gp = float(np.mean(gp_ms_list))
    for m in methods:
        pl = float(np.mean(map_plan_ms[m]))
        rl = float(np.mean(map_roll_ms[m]))
        dm, ci = paired_ci95(ours_arr - np.array(map_costs[m]))
        summary["methods"][m] = {
            "mean_cost": float(np.mean(map_costs[m])),
            "reach_rate": float(np.mean(map_reach[m])),
            "plan_ms_per_query": pl,
            "rollout_ms_45traj": rl,
            "total_ms_per_query_incl_amortized_gp": mean_gp / 3.0 + pl + rl,
            "ours_minus_method_cost": {"mean": dm, "ci95": ci},
            "per_map_costs": map_costs[m],
        }
    return summary


def run_battle3b_underactuated_4d(n_maps: int = 8, n_probes: int = 36) -> dict:
    """4D Inertial Double Integrator (Rank-2 control on velocity, position-dependent hazards & wind;
    explicitly declared structural assumption: unknown q(p), f_wind(p) depend on 2D position p, while
    planning & value residual live in full 4D phase space (p, v)!).
    """
    methods = ["Free-LQR", "SameGP-LQRGuided-PIMC", "SameGP-Unified-Underactuated-GreenRes"]
    map_costs = {m: [] for m in methods}
    map_reach = {m: [] for m in methods}
    map_plan_ms = {m: [] for m in methods}
    map_roll_ms = {m: [] for m in methods}

    gamma = 0.65
    sigma = 0.42
    lam = sigma ** 2
    q0 = 0.50
    r_goal = 0.24
    c_vel = 0.15

    for m_i in range(n_maps):
        map_seed = 4100 + m_i
        # Generate 2D physical world for unknown q(p) and wind f(p)
        w2d, _ = generate_random_map(map_seed, dim=2, with_drift=True, n_queries=1)
        X_obs, q_obs, b_obs = sample_noisy_probes(w2d, n_probes=n_probes, seed=map_seed + 5, probe_box=1.25, include_drift=True)
        km2d = KrigingWorldModel(X_obs, q_obs, b_obs)

        # 3 queries with non-zero initial velocity pointing toward center!
        queries = [
            QueryTask("UQ1", (GoalBall((0.80, 0.75), 0.0, r_goal),), ((-0.80, -0.75, 0.55, 0.50), (-0.75, 0.70, 0.45, -0.35))),
            QueryTask("UQ2", (GoalBall((-0.78, 0.78), 0.0, r_goal),), ((0.80, -0.75, -0.50, 0.50), (0.75, 0.70, -0.45, 0.0))),
            QueryTask("UQ3", (GoalBall((0.80, 0.72), 0.0, r_goal), GoalBall((-0.75, 0.75), 0.18, r_goal)), ((0.0, -0.88, 0.0, 0.65), (-0.70, -0.70, 0.45, 0.45))),
        ]

        def _sim_underactuated(pol_fn, q_task: QueryTask, seed_sim: int) -> Tuple[float, float, float]:
            starts = np.repeat(np.array(q_task.start_points, dtype=float), 20, axis=0)
            n_tr = len(starts)
            dt = 0.015
            sqrt_dt = np.sqrt(dt)
            ss = np.random.SeedSequence([seed_sim, 404])
            dW = np.array([np.random.default_rng(c).normal(0.0, sqrt_dt, size=(380, 2)) for c in ss.spawn(n_tr)])
            x = starts.copy()
            alive = np.ones(n_tr, dtype=bool)
            reached = np.zeros(n_tr, dtype=bool)
            costs = np.zeros(n_tr, dtype=float)
            g_c = np.array([g.center for g in q_task.goals])
            g_p = np.array([g.phi for g in q_task.goals])

            t0 = time.perf_counter()
            for st in range(380):
                idx = np.flatnonzero(alive)
                if len(idx) == 0:
                    break
                xa = x[idx]
                pa = xa[:, 0:2]; va = xa[:, 2:4]
                dm = np.linalg.norm(pa[:, None, :] - g_c[None, :, :], axis=2)
                hit = dm <= r_goal
                any_h = np.any(hit, axis=1)
                if np.any(any_h):
                    hl = np.flatnonzero(any_h)
                    best_phi = np.min(np.where(hit[hl], g_p[None, :], np.inf), axis=1)
                    costs[idx[hl]] += best_phi + c_vel * np.sum(va[hl] ** 2, axis=1)
                    reached[idx[hl]] = True
                    alive[idx[hl]] = False
                    idx = np.flatnonzero(alive)
                    if len(idx) == 0:
                        break
                    xa = x[idx]; pa = xa[:, 0:2]; va = xa[:, 2:4]

                u = np.asarray(pol_fn(xa), dtype=float)
                un = np.linalg.norm(u, axis=1, keepdims=True)
                u = np.where(un > 20.0, u * (20.0 / np.maximum(un, 1e-12)), u)
                qt = q0 + w2d.q_hidden(pa)
                costs[idx] += (qt + 0.5 * np.sum(u ** 2, axis=1)) * dt
                fw = w2d.drift(pa)
                p_next = reflect_into_box(pa + va * dt, 1.65)
                v_next = np.clip(va + (-gamma * va + fw + u) * dt + sigma * dW[idx, st, :], -3.0, 3.0)
                x[idx] = np.hstack([p_next, v_next])
            rl_ms = 1000.0 * (time.perf_counter() - t0)
            if np.any(alive):
                guide_tmp = UnifiedUnderactuatedLQRGuide4D(gamma, sigma, q0, q_task.goals, c_vel)
                v_rem, _, _ = guide_tmp.val_grad_and_trvv(x[alive])
                costs[alive] += v_rem
            return float(np.mean(costs)), float(np.mean(reached)), rl_ms

        c_q = {m: [] for m in methods}
        r_q = {m: [] for m in methods}
        p_q = {m: [] for m in methods}
        rl_q = {m: [] for m in methods}

        for qi, q_task in enumerate(queries):
            s_seed = 8100 + 10 * m_i + qi
            guide = UnifiedUnderactuatedLQRGuide4D(gamma, sigma, q0, q_task.goals, c_vel)

            # 1. Free LQR
            c1, r1, rl1 = _sim_underactuated(lambda X, _g=guide: -_g.val_grad_and_trvv(X)[1][:, 2:4], q_task, s_seed)
            c_q["Free-LQR"].append(c1); r_q["Free-LQR"].append(r1); p_q["Free-LQR"].append(0.1); rl_q["Free-LQR"].append(rl1)

            # 2. Same-GP + LQR-Guided Online PIMC
            rng_p = np.random.default_rng(s_seed + 1)
            g_c = np.array([g.center for g in q_task.goals])

            def _pimc_u(X4, _g=guide, _km=km2d, _gc=g_c, _rng=rng_p):
                X4 = np.atleast_2d(X4)
                nb = len(X4); M = 36; dt_m = 0.04; sq = np.sqrt(dt_m)
                _, gv0_0, _ = _g.val_grad_and_trvv(X4)
                u0_start = -gv0_0[:, 2:4]
                eps0 = _rng.normal(0.0, sq, size=(nb, M, 2))
                pos4 = np.repeat(X4[:, None, :], M, axis=1)
                al = np.ones((nb, M), dtype=bool)
                acc = np.zeros((nb, M))
                for st in range(15):
                    ai, aj = np.where(al)
                    if len(ai) == 0: break
                    cur = pos4[ai, aj]
                    p_cur = cur[:, 0:2]; v_cur = cur[:, 2:4]
                    if st == 0:
                        u_pr = np.repeat(u0_start[:, None, :], M, axis=1)[ai, aj]
                        nz = eps0[ai, aj]
                    else:
                        _, gv_s, _ = _g.val_grad_and_trvv(cur)
                        u_pr = -gv_s[:, 2:4]
                        nz = _rng.normal(0.0, sq, size=(len(ai), 2))
                    qh, _ = _km.predict_q(p_cur, return_std=False)
                    bh = _km.predict_b(p_cur, return_std=False)
                    r_st = _g.exact_pde_residual_r0(cur, qh, bh, np.zeros(len(ai)))
                    acc[ai, aj] += r_st * dt_m
                    pn = reflect_into_box(p_cur + v_cur * dt_m, 1.65)
                    vn = np.clip(v_cur + (-gamma * v_cur + bh + u_pr) * dt_m + sigma * nz, -3.0, 3.0)
                    nxt = np.hstack([pn, vn])
                    pos4[ai, aj] = nxt
                    dm = np.linalg.norm(pn[:, None, :] - _gc[None, :, :], axis=2)
                    hit = dm <= r_goal
                    ah = np.any(hit, axis=1)
                    if np.any(ah):
                        hl = np.flatnonzero(ah)
                        gi = np.argmin(dm[hl], axis=1)
                        acc[ai[hl], aj[hl]] += _g.terminal_residual(nxt[hl], gi)
                        al[ai[hl], aj[hl]] = False
                ex = -acc / lam
                mx = np.max(ex, axis=1, keepdims=True)
                w = np.exp(ex - mx)
                w /= np.maximum(np.sum(w, axis=1, keepdims=True), 1e-30)
                return u0_start + (sigma / dt_m) * np.einsum("bm,bmd->bd", w, eps0)

            c2, r2, rl2 = _sim_underactuated(_pimc_u, q_task, s_seed)
            c_q["SameGP-LQRGuided-PIMC"].append(c2); r_q["SameGP-LQRGuided-PIMC"].append(r2)
            p_q["SameGP-LQRGuided-PIMC"].append(0.0); rl_q["SameGP-LQRGuided-PIMC"].append(rl2)

            # 3. Same-GP + Unified Underactuated Green-Residual (Ours: exact r0 + exact boundary residual + 2-pass continuation!)
            t0 = time.perf_counter()
            rng_f = np.random.default_rng(s_seed + 2)
            # Boundary anchors in 4D (p on goal circle, v sampled in [-1.2, 1.2]^2)
            bnd_list, bnd_y = [], []
            for j in range(len(q_task.goals)):
                ang = rng_f.uniform(0, 2 * np.pi, size=24)
                p_b = g_c[j][None, :] + r_goal * np.column_stack([np.cos(ang), np.sin(ang)])
                v_b = rng_f.uniform(-1.1, 1.1, size=(24, 2))
                xb = np.hstack([p_b, v_b])
                bnd_list.append(xb)
                bnd_y.append(guide.terminal_residual(xb, np.full(24, j, dtype=int)))
            X_bnd = np.vstack(bnd_list); y_bnd = np.concatenate(bnd_y)

            sob = qmc.Sobol(d=4, scramble=True, seed=s_seed)
            u_raw = sob.random(96) * 2.0 - 1.0
            X_int = np.column_stack([u_raw[:, 0:2] * 1.15, u_raw[:, 2:4] * 1.25])
            X_int = np.vstack([np.array(q_task.start_points), X_int])
            keep = np.all(np.linalg.norm(X_int[:, None, 0:2] - g_c[None, :, :], axis=2) > r_goal + 0.04, axis=1)
            X_int = X_int[keep]

            M_fk = 64; dt_fk = 0.04; sq_fk = np.sqrt(dt_fk)
            pos4 = np.repeat(X_int[:, None, :], M_fk, axis=1)
            al = np.ones((len(X_int), M_fk), dtype=bool)
            acc_r = np.zeros((len(X_int), M_fk))
            term_res = np.zeros((len(X_int), M_fk))
            for _st in range(70):
                ai, aj = np.where(al)
                if len(ai) == 0: break
                cur = pos4[ai, aj]
                p_cur = cur[:, 0:2]; v_cur = cur[:, 2:4]
                dm = np.linalg.norm(p_cur[:, None, :] - g_c[None, :, :], axis=2)
                hit = dm <= r_goal
                ah = np.any(hit, axis=1)
                if np.any(ah):
                    hl = np.flatnonzero(ah)
                    gi = np.argmin(dm[hl], axis=1)
                    term_res[ai[hl], aj[hl]] = guide.terminal_residual(cur[hl], gi)
                    al[ai[hl], aj[hl]] = False
                    km_mask = ~ah
                    ai = ai[km_mask]; aj = aj[km_mask]
                    if len(ai) == 0: break
                    cur = pos4[ai, aj]; p_cur = cur[:, 0:2]; v_cur = cur[:, 2:4]
                _, gv, _ = guide.val_grad_and_trvv(cur)
                u0 = -gv[:, 2:4]
                qh, _ = km2d.predict_q(p_cur, return_std=False)
                bh = km2d.predict_b(p_cur, return_std=False)
                acc_r[ai, aj] += guide.exact_pde_residual_r0(cur, qh, bh, np.zeros(len(ai))) * dt_fk
                pn = reflect_into_box(p_cur + v_cur * dt_fk, 1.65)
                vn = np.clip(v_cur + (-gamma * v_cur + bh + u0) * dt_fk + sigma * rng_f.normal(0.0, sq_fk, size=v_cur.shape), -3.0, 3.0)
                pos4[ai, aj] = np.hstack([pn, vn])

            def _lme(emat):
                mx = np.max(emat, axis=1, keepdims=True)
                return -lam * (mx[:, 0] + np.log(np.maximum(np.mean(np.exp(emat - mx), axis=1), 1e-300)))

            dv1 = _lme(-(acc_r + np.where(al, 0.0, term_res)) / lam)
            gp1 = AnalyticMatern52ResidualGP(np.vstack([X_int, X_bnd]), np.concatenate([dv1, y_bnd]), length_scale=0.68, noise=3e-3)
            tail = np.zeros_like(term_res)
            ai, aj = np.where(al)
            if len(ai) > 0:
                tail[ai, aj] = gp1.predict_val_and_grad(pos4[ai, aj])[0]
            dv2 = _lme(-(acc_r + np.where(al, tail, term_res)) / lam)
            gp2 = AnalyticMatern52ResidualGP(np.vstack([X_int, X_bnd]), np.concatenate([dv2, y_bnd]), length_scale=0.68, noise=3e-3)
            p_ms = 1000.0 * (time.perf_counter() - t0)

            def _ours_pol(X4, _g=guide, _gp=gp2):
                _, gv0, _ = _g.val_grad_and_trvv(X4)
                _, gdv = _gp.predict_val_and_grad(X4)
                return -(gv0[:, 2:4] + gdv[:, 2:4])

            c3, r3, rl3 = _sim_underactuated(_ours_pol, q_task, s_seed)
            c_q["SameGP-Unified-Underactuated-GreenRes"].append(c3); r_q["SameGP-Unified-Underactuated-GreenRes"].append(r3)
            p_q["SameGP-Unified-Underactuated-GreenRes"].append(p_ms); rl_q["SameGP-Unified-Underactuated-GreenRes"].append(rl3)

        for m in methods:
            map_costs[m].append(float(np.mean(c_q[m])))
            map_reach[m].append(float(np.mean(r_q[m])))
            map_plan_ms[m].append(float(np.mean(p_q[m])))
            map_roll_ms[m].append(float(np.mean(rl_q[m])))

    ours_arr = np.array(map_costs["SameGP-Unified-Underactuated-GreenRes"])
    return {
        "n_maps": n_maps,
        "structural_note": "4D phase space (p, v) with rank-2 velocity control; unknown hazard q(p) and rotational wind f(p) live on 2D position subspace.",
        "methods": {
            m: {
                "mean_cost": float(np.mean(map_costs[m])),
                "reach_rate": float(np.mean(map_reach[m])),
                "plan_ms": float(np.mean(map_plan_ms[m])),
                "rollout_ms": float(np.mean(map_roll_ms[m])),
                "ours_minus_method_cost": dict(zip(["mean", "ci95"], paired_ci95(ours_arr - np.array(map_costs[m])))),
            }
            for m in methods
        },
    }


def run_battle4_corrected_non_lmdp(n_maps: int = 10, n_probes: int = 35) -> dict:
    """Corrected Non-LMDP Benchmark (Anisotropic R = diag(0.35, 3.0) + Euclidean ball ||u||_2 <= 1.8 + Vortex Drift)
    using exact KKT `u = -(R + eta I)^{-1} g` and strictly monotone separated-upwind Howard PI!
    """
    methods = [
        "GroundTruth-Monotone-KKT-HJB-81",
        "SameGP-Monotone-KKT-HJB-51",
        "SameGP-Naive-Isotropic-Green",
        "SameGP-0Step-KKT-Green",
        "SameGP-Green-WarmStart-3Step-KKT-Polish",
    ]
    map_costs = {m: [] for m in methods}
    map_plan_ms = {m: [] for m in methods}
    R_diag = (0.35, 3.0)
    u_max = 1.8

    for m_i in range(n_maps):
        map_seed = 5100 + m_i
        spec_nl = ProblemSpec(dim=2, half_width=1.65, sigma=0.45, q0=0.50, r_diag=R_diag, u_max=u_max)
        world, queries = generate_random_map(map_seed, dim=2, with_drift=True, n_queries=3, spec=spec_nl)
        X_obs, q_obs, b_obs = sample_noisy_probes(world, n_probes=n_probes, seed=map_seed + 11, include_drift=True)
        km = KrigingWorldModel(X_obs, q_obs, b_obs)
        q_fn = lambda X, _k=km: _k.predict_q(X, return_std=False)[0]
        b_fn = lambda X, _k=km: _k.predict_b(X, return_std=False)

        # Build reusable isotropic Cole-Hopf Green operator once per map
        spec_iso = ProblemSpec(dim=2, half_width=1.65, sigma=0.45, q0=0.50)
        gr_iso = ReusableGreenOperator2D3D(spec_iso, 35, q_fn, b_fn)

        c_q = {m: [] for m in methods}
        p_q = {m: [] for m in methods}

        for qi, q in enumerate(queries):
            s_seed = 9200 + 10 * m_i + qi
            # 1. Ground-truth high-res 81x81 Monotone KKT HJB reference
            gt_hjb = solve_monotone_anisotropic_constrained_hjb_2d(spec_nl, 81, world.q_hidden, world.drift, q, n_iters=16)
            c_q["GroundTruth-Monotone-KKT-HJB-81"].append(simulate_closed_loop_crn(world, gt_hjb["policy"], q, n_per_start=30, seed=s_seed)["mean_cost"])
            p_q["GroundTruth-Monotone-KKT-HJB-81"].append(gt_hjb["solve_ms"])

            # 2. Same-GP full 51x51 Monotone KKT HJB from zero init
            gp_hjb = solve_monotone_anisotropic_constrained_hjb_2d(spec_nl, 51, q_fn, b_fn, q, n_iters=14)
            c_q["SameGP-Monotone-KKT-HJB-51"].append(simulate_closed_loop_crn(world, gp_hjb["policy"], q, n_per_start=30, seed=s_seed)["mean_cost"])
            p_q["SameGP-Monotone-KKT-HJB-51"].append(gp_hjb["solve_ms"])

            # 3. Same-GP Naive Isotropic Green (ignores R_diag, radially clipped by simulator)
            sol_iso = gr_iso.solve_port_reduced(q, rich_modes=True)
            c_q["SameGP-Naive-Isotropic-Green"].append(simulate_closed_loop_crn(world, sol_iso["policy"], q, n_per_start=30, seed=s_seed)["mean_cost"])
            p_q["SameGP-Naive-Isotropic-Green"].append(sol_iso["solve_ms"])

            # 4. Same-GP 0-Step KKT-Projected Green (exact KKT applied to grad V_green!)
            t0 = time.perf_counter()
            sol_iso2 = gr_iso.solve_port_reduced(q, rich_modes=True)
            # Note: for isotropic Green, policy_iso(X) = -grad V_green(X) => grad V_green(X) = -policy_iso(X)!
            pol_0kkt = lambda X, _p=sol_iso2["policy"]: solve_anisotropic_ball_qp(-_p(X), np.array(R_diag), u_max)
            ms_0 = 1000.0 * (time.perf_counter() - t0)
            c_q["SameGP-0Step-KKT-Green"].append(simulate_closed_loop_crn(world, pol_0kkt, q, n_per_start=30, seed=s_seed)["mean_cost"])
            p_q["SameGP-0Step-KKT-Green"].append(ms_0)

            # 5. Same-GP Green Warm-Start + 3-Step Monotone KKT Polish on 35x35 grid
            t0 = time.perf_counter()
            u_warm = pol_0kkt(gr_iso.pts)
            pol_3pi = solve_monotone_anisotropic_constrained_hjb_2d(spec_nl, 35, q_fn, b_fn, q, n_iters=3, u_init_grid=u_warm)
            ms_3 = sol_iso2["solve_ms"] + pol_3pi["solve_ms"]
            c_q["SameGP-Green-WarmStart-3Step-KKT-Polish"].append(simulate_closed_loop_crn(world, pol_3pi["policy"], q, n_per_start=30, seed=s_seed)["mean_cost"])
            p_q["SameGP-Green-WarmStart-3Step-KKT-Polish"].append(ms_3)

        for m in methods:
            map_costs[m].append(float(np.mean(c_q[m])))
            map_plan_ms[m].append(float(np.mean(p_q[m])))

    gt_arr = np.array(map_costs["GroundTruth-Monotone-KKT-HJB-81"])
    sgp_arr = np.array(map_costs["SameGP-Monotone-KKT-HJB-51"])
    out = {"n_maps": n_maps, "r_diag": list(R_diag), "u_max": u_max, "methods": {}}
    for m in methods:
        arr = np.array(map_costs[m])
        rel_gt = 100.0 * (float(np.mean(arr)) - float(np.mean(gt_arr))) / float(np.mean(gt_arr))
        rel_sgp = 100.0 * (float(np.mean(arr)) - float(np.mean(sgp_arr))) / float(np.mean(sgp_arr))
        dm_sgp, ci_sgp = paired_ci95(arr - sgp_arr)
        out["methods"][m] = {
            "mean_cost": float(np.mean(arr)),
            "mean_solve_ms": float(np.mean(map_plan_ms[m])),
            "rel_gap_vs_gt_hjb_pct": rel_gt,
            "rel_gap_vs_same_gp_hjb_pct": rel_sgp,
            "paired_diff_vs_same_gp_hjb": {"mean": dm_sgp, "ci95": ci_sgp},
            "per_map_costs": map_costs[m],
        }
    return out


def plot_battle3_and_4(b4d: dict, b6d: dict, bua: dict, bnl: dict, out_png: Path):
    fig, axes = plt.subplots(1, 3, figsize=(16.8, 4.9))

    # Panel 1: 4D & 6D Cost vs Total Time (Plan + 45-Traj Execution + Amortized GP)
    for d_lbl, bdata, marker in [("4D", b4d, "o"), ("6D", b6d, "s")]:
        for m, col, short in [
            ("Pure-Base-Guide", "#7f7f7f", f"{d_lbl} Pure Base"),
            ("SameGP-Unguided-PIMC", "#d62728", f"{d_lbl} Same-GP Unguided PIMC"),
            ("SameGP-BaseGuided-PIMC", "#ff7f0e", f"{d_lbl} Same-GP Guided PIMC"),
            ("SameGP-Unified-GreenRes", "#1f77b4", f"{d_lbl} Unified GreenRes (Ours)"),
        ]:
            t_tot = bdata["methods"][m]["total_ms_per_query_incl_amortized_gp"]
            cost = bdata["methods"][m]["mean_cost"]
            axes[0].scatter(t_tot, cost, s=95, color=col, marker=marker, label=short)
    axes[0].set_xscale("log")
    axes[0].set_xlabel("Total Time per Query: Amortized GP + Plan + 45 Rollouts (ms, log)")
    axes[0].set_ylabel("Mean Closed-Loop Cost (8 Random Maps)")
    axes[0].set_title("4D & 6D High-D Duel (Same-GP Fair Accounting)")
    axes[0].grid(True, alpha=0.3, which="both")
    axes[0].legend(fontsize=7.3, ncol=2)

    # Panel 2: 4D Underactuated Inertial Double Integrator
    ua_names = ["Free-LQR", "SameGP-LQRGuided-PIMC", "SameGP-Unified-Underactuated-GreenRes"]
    ua_lbls = ["Free-Space\nLQR", "Same-GP +\nGuided PIMC", "Unified GreenRes\n(Exact r0, Ours)"]
    ua_costs = [bua["methods"][m]["mean_cost"] for m in ua_names]
    ua_tot = [bua["methods"][m]["plan_ms"] + bua["methods"][m]["rollout_ms"] for m in ua_names]
    bars2 = axes[1].bar(np.arange(3), ua_costs, width=0.52, color=["#7f7f7f", "#ff7f0e", "#1f77b4"])
    axes[1].set_xticks(np.arange(3))
    axes[1].set_xticklabels(ua_lbls, fontsize=8.8)
    axes[1].set_ylabel("Closed-Loop Cost (8 Random Maps)")
    axes[1].set_title("4D Underactuated Inertial System (Exact r0 & Bnd)")
    axes[1].grid(True, axis="y", alpha=0.3)
    for b, c, tms in zip(bars2, ua_costs, ua_tot):
        axes[1].text(b.get_x() + b.get_width() / 2, b.get_height() + 0.15, f"{c:.2f}\n({tms:.0f} ms)", ha="center", va="bottom", fontsize=8.3)
    axes[1].set_ylim(0, max(ua_costs) * 1.24)

    # Panel 3: Corrected Monotone KKT Non-LMDP Benchmark
    nl_names = [
        "SameGP-Naive-Isotropic-Green",
        "SameGP-0Step-KKT-Green",
        "SameGP-Green-WarmStart-3Step-KKT-Polish",
        "SameGP-Monotone-KKT-HJB-51",
        "GroundTruth-Monotone-KKT-HJB-81",
    ]
    nl_lbls = ["Naive Iso\nGreen", "0-Step KKT\nGreen", "Green + 3-Step\nKKT Polish", "Same-GP Full\nKKT-HJB (51²)", "GroundTruth\nKKT-HJB (81²)"]
    nl_c = [bnl["methods"][m]["mean_cost"] for m in nl_names]
    nl_ms = [bnl["methods"][m]["mean_solve_ms"] for m in nl_names]
    bars3 = axes[2].bar(np.arange(len(nl_names)), nl_c, width=0.56, color=["#d62728", "#9467bd", "#1f77b4", "#ff7f0e", "#2ca02c"])
    axes[2].set_xticks(np.arange(len(nl_names)))
    axes[2].set_xticklabels(nl_lbls, fontsize=8.0)
    axes[2].set_ylabel("Closed-Loop Cost (10 Random Maps)")
    axes[2].set_title("Corrected Non-LMDP KKT Benchmark (R=[0.35,3], ||u||≤1.8)")
    axes[2].grid(True, axis="y", alpha=0.3)
    for b, c, tms in zip(bars3, nl_c, nl_ms):
        axes[2].text(b.get_x() + b.get_width() / 2, b.get_height() + 0.10, f"{c:.2f}\n({tms:.0f}ms)", ha="center", va="bottom", fontsize=7.8)
    axes[2].set_ylim(0, max(nl_c) * 1.25)

    plt.tight_layout()
    plt.savefig(out_png, dpi=170)
    plt.close(fig)


def main():
    print("=== Battle 3A: 4D High-D Same-GP Duel (8 random maps x 3 queries) ===")
    b4d = run_battle3a_highd(dim=4, n_maps=8, n_probes=60)
    for k, v in b4d["methods"].items():
        print(f"  4D {k:28s} | Cost={v['mean_cost']:.3f} | Reach={v['reach_rate']*100:.1f}% | Plan={v['plan_ms_per_query']:.0f}ms | Rollout={v['rollout_ms_45traj']:.0f}ms | Total={v['total_ms_per_query_incl_amortized_gp']:.0f}ms")
    print(f"  4D FK Survivor={b4d['mean_fk_survivor_fraction']*100:.2f}%, ESS={b4d['mean_fk_ess_out_of_64']:.1f}/64")

    print("\n=== Battle 3A: 6D High-D Same-GP Duel (8 random maps x 3 queries) ===")
    b6d = run_battle3a_highd(dim=6, n_maps=8, n_probes=100)
    for k, v in b6d["methods"].items():
        print(f"  6D {k:28s} | Cost={v['mean_cost']:.3f} | Reach={v['reach_rate']*100:.1f}% | Plan={v['plan_ms_per_query']:.0f}ms | Rollout={v['rollout_ms_45traj']:.0f}ms | Total={v['total_ms_per_query_incl_amortized_gp']:.0f}ms")
    print(f"  6D FK Survivor={b6d['mean_fk_survivor_fraction']*100:.2f}%, ESS={b6d['mean_fk_ess_out_of_64']:.1f}/64")

    print("\n=== Battle 3B: 4D Underactuated Inertial Double Integrator (8 random maps) ===")
    bua = run_battle3b_underactuated_4d(n_maps=8, n_probes=36)
    for k, v in bua["methods"].items():
        print(f"  UA4D {k:38s} | Cost={v['mean_cost']:.3f} | Reach={v['reach_rate']*100:.1f}% | Plan={v['plan_ms']:.0f}ms | Rollout={v['rollout_ms']:.0f}ms")

    print("\n=== Battle 4: Corrected Monotone KKT Non-LMDP Benchmark (10 random maps) ===")
    bnl = run_battle4_corrected_non_lmdp(n_maps=10, n_probes=35)
    for k, v in bnl["methods"].items():
        print(f"  NL {k:40s} | Cost={v['mean_cost']:.3f} ({v['rel_gap_vs_gt_hjb_pct']:+.2f}% vs GT, {v['rel_gap_vs_same_gp_hjb_pct']:+.2f}% vs SameGP-HJB) | Solve={v['mean_solve_ms']:.1f}ms")

    out_dir = Path(__file__).resolve().parent
    res = {"highd_4d": b4d, "highd_6d": b6d, "underactuated_4d": bua, "corrected_non_lmdp_2d": bnl}
    (out_dir / "battle3_and_4_results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    plot_battle3_and_4(b4d, b6d, bua, bnl, out_dir / "battle3_highd_and_nonlmdp.png")
    print("Saved battle3_and_4_results.json and battle3_highd_and_nonlmdp.png")


if __name__ == "__main__":
    main()
