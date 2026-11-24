"""
Rigorous Stress-Test Suite Probing the 3 Real Limitations of Direction 1A:
  Stress Test 1 — Pure On-Trajectory Online Episodic Learning (NO teleporting point probes!
                  Noisy stage cost + noisy macro-window drift increments along physically
                  traversed SDE episodes; tests both seen Q1 and unseen Q2/Q3/Q4 transfer).
  Stress Test 2 — Non-Convex U-Shaped Trap / Maze Wall Geometry:
                  (2A) 2D deep U-trap (exact + sparse probes + pure on-trajectory escape!)
                  (2B) 4D wall trap testing whether 1-round GreenResidual-1A suffers ESS
                       collapse and whether 2-round Iterative Guiding (u0 -> u1 -> u2) fixes it.
  Stress Test 3 — Breaking Cole-Hopf / LMDP Assumptions (True Model Mismatch!):
                  (3A) Unknown diffusion sigma (wrong fixed sigma vs online-estimated sigma_hat).
                  (3B) Anisotropic control cost R = diag(0.35, 3.0) + hard saturation ||u|| <= 1.8
                       (mathematically non-linearizable by Cole-Hopf!), benchmarked against
                       an EXACT Nonlinear-HJB Policy-Iteration Oracle on an 81x81 grid,
                       comparing naive Green-1A vs Green-1A + 3-step Linear PI Polish!
"""
from __future__ import annotations

import json
import os
import time
import warnings
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.interpolate import RegularGridInterpolator
from scipy.special import logsumexp
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from env_and_oracle import (
    StochasticControlEnv, QuerySpec, HazardBlob, ExactFDPDEOracle, build_default_benchmark
)
from methods import SemigroupGreenSolver, KrigingEnvironmentModel, fit_ordinary_kriging_V
from test_breakthrough_a_highd import HighDEnv, HighDQuery, HighDHazard, solve_highd_green_residual_1a


# ===========================================================================
# STRESS TEST 1: Pure On-Trajectory Episodic Learning (NO Teleporting Probes!)
# ===========================================================================
def collect_on_trajectory_episode(
    env: StochasticControlEnv,
    policy_fn,
    query: QuerySpec,
    start: np.ndarray,
    dt: float = 0.015,
    max_steps: int = 360,
    window: int = 8,
    q_noise_std: float = 0.5,
    explore_eps: float = 0.35,
    rng: np.random.Generator = None,
):
    """
    Physically roll out ONE noisy SDE episode from `start`.
    Returns macro-windowed noisy (x_mid, q_obs, b_obs, V_mc_obs, raw_increments)
    strictly along the visited trajectory (NO off-trajectory teleporting!).
    """
    x = start.copy()
    g_centers = np.array([g[0] for g in query.goals], dtype=float)
    g_phis = np.array([g[1] for g in query.goals], dtype=float)
    sqrt_dt = np.sqrt(dt)

    xs_hist, us_hist, step_costs, q_noisy_hist = [], [], [], []
    reached = False
    term_cost = 0.0

    for step in range(max_steps):
        dists = np.linalg.norm(x[None, :] - g_centers, axis=1)
        mi = int(np.argmin(dists))
        if dists[mi] <= env.r_goal:
            reached = True
            term_cost = float(g_phis[mi])
            break

        u_pol = policy_fn(x[None, :])[0]
        # Mild exploration jitter during training episodes so agent doesn't repeat identical track
        u = u_pol + rng.normal(0.0, explore_eps, size=2)
        un = np.linalg.norm(u)
        if un > 6.0:
            u = u * (6.0 / un)

        qh_true = float(env.q_hidden(x[None, :])[0])
        qh_obs = max(0.0, qh_true + float(rng.normal(0.0, q_noise_std)))
        step_c = (env.q0 + qh_true + 0.5 * float(np.sum(u ** 2))) * dt

        xs_hist.append(x.copy())
        us_hist.append(u.copy())
        step_costs.append(step_c)
        q_noisy_hist.append(qh_obs)

        b_true = env.drift(x[None, :])[0]
        x = np.clip(x + (b_true + u) * dt + env.sigma * sqrt_dt * rng.normal(size=2), -env.box_limit, env.box_limit)

    if not reached:
        d_min = float(np.min(np.linalg.norm(x[None, :] - g_centers, axis=1)))
        term_cost = 2.0 * d_min + 2.0

    xs_hist.append(x.copy())
    T = len(us_hist)
    if T < window:
        return np.zeros((0, 2)), np.zeros(0), np.zeros((0, 2)), np.zeros(0), np.zeros((0, 2))

    # Compute Monte Carlo return-to-go at each visited step (for Ordinary-Kriging-V baseline!)
    rtg = np.zeros(T, dtype=float)
    running = term_cost
    for t in range(T - 1, -1, -1):
        running += step_costs[t]
        rtg[t] = running

    # Extract non-overlapping macro-window samples (reduces drift estimation variance by sqrt(window)
    # and avoids huge redundant GP matrices from 300 correlated steps!)
    X_pts, q_pts, b_pts, v_pts = [], [], [], []
    # Also collect raw single-step residuals for online sigma estimation
    raw_res = []
    for t in range(0, T - window + 1, window):
        x_mid = xs_hist[t + window // 2]
        q_avg = float(np.mean(q_noisy_hist[t : t + window]))
        # Macro drift estimate: (x_{t+W} - x_t - sum u_k dt) / (W dt)
        disp = xs_hist[t + window] - xs_hist[t]
        u_sum = np.sum(us_hist[t : t + window], axis=0) * dt
        b_est = (disp - u_sum) / (window * dt)
        X_pts.append(x_mid)
        q_pts.append(q_avg)
        b_pts.append(b_est)
        v_pts.append(rtg[t + window // 2])
    for t in range(T):
        raw_res.append((xs_hist[t + 1] - xs_hist[t]) - us_hist[t] * dt)

    return (
        np.asarray(X_pts, dtype=float),
        np.asarray(q_pts, dtype=float),
        np.asarray(b_pts, dtype=float),
        np.asarray(v_pts, dtype=float),
        np.asarray(raw_res, dtype=float),
    )


def run_stress_test_1_ontrajectory():
    print(f"\n{'='*88}\nSTRESS TEST 1 — PURE ON-TRAJECTORY ONLINE EPISODIC LEARNING (NO TELEPORT PROBES)\n{'='*88}")
    out = {}
    for regime_name, with_vortex in [("R1_OnTraj_Hazards", False), ("R2_OnTraj_HazardsPlusVortex", True)]:
        env, queries = build_default_benchmark(with_vortex=with_vortex)
        oracle = ExactFDPDEOracle(env, grid_n=101, half_width=2.0)
        solver = SemigroupGreenSolver(env, grid_n=25, half_width=1.65)
        or_costs = {q.name: env.simulate_rollouts(oracle.solve(q)["policy"], q, n_per_start=40, seed=100)["mean_cost"] for q in queries}
        op_free = solver.build_environment_operator(lambda X: np.zeros(len(np.atleast_2d(X))))
        free_costs = {q.name: env.simulate_rollouts(solver.solve_query(op_free, q)["policy"], q, n_per_start=40, seed=100)["mean_cost"] for q in queries}
        print(f"\n[{regime_name}] Oracle Avg={np.mean(list(or_costs.values())):.3f} | Pure-Free-Green Avg={np.mean(list(free_costs.values())):.3f}")

        out[regime_name] = {"oracle_avg": float(np.mean(list(or_costs.values()))), "free_avg": float(np.mean(list(free_costs.values()))), "checkpoints": {}}
        seeds = (0, 1, 2)
        checkpoints = (4, 8, 16)  # episodes run strictly on Q1!

        agg_1a = {ep: {q.name: [] for q in queries} for ep in checkpoints}
        agg_1a_adapt = {ep: [] for ep in checkpoints}  # Q2 after 2 physical episodes on Q2!
        agg_ok = {ep: {q.name: [] for q in queries} for ep in checkpoints}
        pts_counts = {ep: [] for ep in checkpoints}

        for sd in seeds:
            rng = np.random.default_rng(1200 + 37 * sd)
            X_all, q_all, b_all, v_all = [], [], [], []
            cur_pol_q1 = solver.solve_query(op_free, queries[0])["policy"]
            fk_ep = None

            for ep in range(1, max(checkpoints) + 1):
                st = queries[0].start_points[(ep - 1) % len(queries[0].start_points)]
                exp_eps = 0.65 if ep <= 4 else (0.35 if ep <= 8 else 0.18)
                Xp, qp, bp, vp, _ = collect_on_trajectory_episode(
                    env, cur_pol_q1, queries[0], st, window=10, explore_eps=exp_eps, rng=rng
                )
                if len(Xp) > 0:
                    X_all.append(Xp); q_all.append(qp); b_all.append(bp); v_all.append(vp)

                X_cat = np.vstack(X_all)
                q_cat = np.concatenate(q_all)
                b_cat = np.vstack(b_all) if with_vortex else None
                v_cat = np.concatenate(v_all)

                if len(X_cat) > 100:
                    idx_sub = rng.choice(len(X_cat), size=100, replace=False)
                    X_fit, q_fit, v_fit = X_cat[idx_sub], q_cat[idx_sub], v_cat[idx_sub]
                    b_fit = b_cat[idx_sub] if b_cat is not None else None
                else:
                    X_fit, q_fit, b_fit, v_fit = X_cat, q_cat, b_cat, v_cat

                reopt = (ep in checkpoints) or (ep % 4 == 1) or (fk_ep is None)
                km = KrigingEnvironmentModel(X_fit, q_fit, b_fit, fixed_kernels=None if reopt else fk_ep)
                if reopt:
                    fk_ep = km.get_fitted_kernels()
                drift_fn = km.predict_drift if with_vortex else None
                op_1a = solver.build_environment_operator(lambda X, _k=km: np.maximum(0.0, _k.predict_q(X)[0]), drift_fn=drift_fn)
                cur_pol_q1 = solver.solve_query(op_1a, queries[0])["policy"]

                if ep in checkpoints:
                    pts_counts[ep].append(len(X_cat))
                    ok_v = fit_ordinary_kriging_V(X_fit, v_fit)
                    for q in queries:
                        m1a = env.simulate_rollouts(solver.solve_query(op_1a, q)["policy"], q, n_per_start=30, seed=300 + sd)
                        mok = env.simulate_rollouts(ok_v["policy"], q, n_per_start=30, seed=300 + sd)
                        agg_1a[ep][q.name].append(m1a["mean_cost"])
                        agg_ok[ep][q.name].append(mok["mean_cost"])

                    # Honest check: if unseen Q2 gets just 2 online physical episodes to fill its own blind spots
                    X2, q2, b2 = [X_fit], [q_fit], ([b_fit] if with_vortex else None)
                    pol_q2 = solver.solve_query(op_1a, queries[1])["policy"]
                    for k2 in range(2):
                        Xp2, qp2, bp2, _, _ = collect_on_trajectory_episode(
                            env, pol_q2, queries[1], queries[1].start_points[k2], window=10, explore_eps=0.35, rng=rng
                        )
                        if len(Xp2) > 0:
                            X2.append(Xp2); q2.append(qp2)
                            if with_vortex: b2.append(bp2)
                    km2 = KrigingEnvironmentModel(np.vstack(X2), np.concatenate(q2), np.vstack(b2) if with_vortex else None, fixed_kernels=fk_ep)
                    op2 = solver.build_environment_operator(
                        lambda X, _k=km2: np.maximum(0.0, _k.predict_q(X)[0]),
                        drift_fn=km2.predict_drift if with_vortex else None,
                    )
                    m_q2a = env.simulate_rollouts(solver.solve_query(op2, queries[1])["policy"], queries[1], n_per_start=30, seed=300 + sd)
                    agg_1a_adapt[ep].append(m_q2a["mean_cost"])

        for ep in checkpoints:
            c1a = {q.name: float(np.mean(agg_1a[ep][q.name])) for q in queries}
            cok = {q.name: float(np.mean(agg_ok[ep][q.name])) for q in queries}
            q2_ad = float(np.mean(agg_1a_adapt[ep]))
            out[regime_name]["checkpoints"][str(ep)] = {
                "avg_raw_macro_pts": float(np.mean(pts_counts[ep])),
                "1A_zero_shot": c1a, "1A_avg": float(np.mean(list(c1a.values()))),
                "1A_Q2_plus2ep": q2_ad,
                "OK_V": cok, "OK_avg": float(np.mean(list(cok.values()))),
            }
            print(
                f"  After {ep:2d} Q1-episodes ({np.mean(pts_counts[ep]):5.1f} macro-pts) | "
                f"1A(0-shot): Q1={c1a['Q1_seen_goal']:.2f} Q2={c1a['Q2_unseen_goal']:.2f}(+2ep->{q2_ad:.2f}) "
                f"Q3={c1a['Q3_unseen_multigoal']:.2f} Q4={c1a['Q4_dynamic_constraint']:.2f} [Avg={np.mean(list(c1a.values())):.2f}] | "
                f"OK-V: Q1={cok['Q1_seen_goal']:.2f} Q2={cok['Q2_unseen_goal']:.2f} [Avg={np.mean(list(cok.values())):.2f}]"
            )
    return out


# ===========================================================================
# STRESS TEST 2: Non-Convex U-Shaped Maze Wall (2D + 4D Iterative Guiding)
# ===========================================================================
class UMazeEnv2D(StochasticControlEnv):
    """Deep U-shaped non-convex barrier opening AWAY from the goal (classic local-min trap!)."""

    def q_hidden(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        x, y = X[:, 0], X[:, 1]
        # U-shaped pocket: top bar y=0.22 for x in [-0.55, 0.55],
        # left arm x=-0.55 for y in [-0.45, 0.22], right arm x=+0.55 for y in [-0.45, 0.22]
        # Start at (0, -0.15) inside pocket, Goal at (0, 0.78) above the top bar!
        def seg_dist2(px, py, x1, y1, x2, y2):
            vx, vy = x2 - x1, y2 - y1
            l2 = vx * vx + vy * vy
            t = np.clip(((px - x1) * vx + (py - y1) * vy) / l2, 0.0, 1.0)
            return (px - (x1 + t * vx)) ** 2 + (py - (y1 + t * vy)) ** 2

        d2_top = seg_dist2(x, y, -0.52, 0.24, 0.52, 0.24)
        d2_left = seg_dist2(x, y, -0.52, -0.42, -0.52, 0.24)
        d2_right = seg_dist2(x, y, 0.52, -0.42, 0.52, 0.24)
        d2_min = np.minimum(d2_top, np.minimum(d2_left, d2_right))
        return 22.0 * np.exp(-0.5 * d2_min / (0.11 ** 2))


def solve_4d_iterative_green_residual(
    env: HighDEnv, q_fn, query: HighDQuery, n_rounds: int = 2, n_anchors: int = 96, n_fk_paths: int = 64, seed: int = 0
) -> dict:
    """
    Tests 1-round (free-space u_0*) vs 2-round Iterative Guiding (u_0* -> u_1* -> u_2*)
    behind a large 4D wall to directly diagnose & fix high-D importance-sampling ESS collapse!
    """
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    d = env.dim
    sig2 = env.sigma ** 2
    g_centers = np.array([g[0] for g in query.goals], dtype=float)

    # Start with exact free-space guiding policy u_guide = u_0*
    cur_guide = lambda X: env.free_green_exact_V_and_u(X, query)[1]
    res = None
    ess_per_round = []

    for rd in range(n_rounds):
        # Build anchors along current guided paths + transverse spread + global box
        anchors = []
        for st in query.starts:
            x = st.copy()
            for k in range(30):
                anchors.append(x + rng.normal(0.0, 0.30, size=d))
                u = cur_guide(x[None, :])[0]
                un = np.linalg.norm(u)
                if un > 5.0: u = u * (5.0 / un)
                x = np.clip(x + u * 0.05, -1.25, 1.25)
                if np.min(np.linalg.norm(x[None, :] - g_centers, axis=1)) <= env.r_goal:
                    break
        anchors.extend(list(rng.uniform(-1.1, 1.1, size=(40, d))))
        X_int = np.clip(np.asarray(anchors, dtype=float), -1.25, 1.25)
        mask = np.ones(len(X_int), dtype=bool)
        for gc, _ in query.goals:
            mask &= np.linalg.norm(X_int - gc[None, :], axis=1) > env.r_goal + 0.04
        X_int = X_int[mask][:n_anchors]

        bc = []
        for gc, _ in query.goals:
            dirs = rng.normal(size=(8, d)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
            bc.append(gc[None, :] + env.r_goal * dirs)
        X_bc = np.vstack(bc)

        # Girsanov importance sampling under cur_guide:
        # Let du = u_guide - u_0*. Exact Radon-Nikodym weight relative to u_0* adds:
        #   + 0.5*||du||^2 dt + du . (sigma dW)  into the exponent!
        M = len(X_int)
        pos = np.repeat(X_int[:, None, :], n_fk_paths, axis=1)
        acc = np.zeros((M, n_fk_paths), dtype=float)
        alive = np.ones((M, n_fk_paths), dtype=bool)
        dt_fk = 0.045
        sqrt_dt = np.sqrt(dt_fk)

        for _ in range(44):
            if not np.any(alive):
                break
            ai, aj = np.where(alive)
            pa = pos[ai, aj]
            _, u0 = env.free_green_exact_V_and_u(pa, query)
            un0 = np.linalg.norm(u0, axis=1, keepdims=True)
            u0 = np.where(un0 > 5.0, u0 * (5.0 / np.maximum(un0, 1e-12)), u0)
            if rd == 0:
                ug = u0
                du = np.zeros_like(u0)
            else:
                ug = cur_guide(pa)
                ung = np.linalg.norm(ug, axis=1, keepdims=True)
                ug = np.where(ung > 5.0, ug * (5.0 / np.maximum(ung, 1e-12)), ug)
                du = ug - u0

            dW = rng.normal(size=pa.shape) * sqrt_dt
            qh = np.maximum(0.0, np.asarray(q_fn(pa), dtype=float))
            # Exact Girsanov path exponent for Delta_V = V - V_0:
            #   int (q_hid + 0.5 ||du||^2) dt + int (du . sigma dW)
            step_exp = (qh + 0.5 * np.sum(du ** 2, axis=1)) * dt_fk + env.sigma * np.sum(du * dW, axis=1)
            acc[ai, aj] += step_exp

            p_next = pa + ug * dt_fk + env.sigma * dW
            pos[ai, aj] = p_next
            hit = np.min(np.linalg.norm(p_next[:, None, :] - g_centers[None, :, :], axis=2), axis=1) <= env.r_goal
            if np.any(hit):
                alive[ai[hit], aj[hit]] = False

        log_w = -acc / sig2
        lse = logsumexp(log_w, axis=1, keepdims=True)
        w = np.exp(log_w - lse)
        ess = float(np.median(1.0 / np.sum(w ** 2, axis=1)))
        ess_per_round.append(ess)

        dV_int = np.maximum(0.0, -sig2 * (lse[:, 0] - np.log(n_fk_paths)))
        X_fit = np.vstack([X_int, X_bc])
        y_fit = np.concatenate([dV_int, np.zeros(len(X_bc))])

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            k_res = ConstantKernel(3.0, (0.05, 80.0)) * Matern(length_scale=0.60, length_scale_bounds=(0.2, 2.5), nu=2.5) + WhiteKernel(noise_level=0.05, noise_level_bounds=(1e-4, 2.0))
            gp = GaussianProcessRegressor(kernel=k_res, n_restarts_optimizer=1, normalize_y=False, random_state=seed + rd)
            gp.fit(X_fit, y_fit)

        X_tr = gp.X_train_
        alpha_gp = gp.alpha_
        c_var = float(gp.kernel_.k1.k1.constant_value)
        ell = float(gp.kernel_.k1.k2.length_scale)
        s5 = np.sqrt(5.0) / ell

        def _make_pol(_X_tr=X_tr, _a=alpha_gp, _c=c_var, _ell=ell, _s5=s5):
            def pol(X):
                X = np.atleast_2d(X)
                _, u0x = env.free_green_exact_V_and_u(X, query)
                diff = X[:, None, :] - _X_tr[None, :, :]
                r = np.sqrt(np.sum(diff ** 2, axis=2) + 1e-18)
                sr = _s5 * r
                coeff = -(5.0 / (3.0 * _ell * _ell)) * _c * (1.0 + sr) * np.exp(-sr)
                gdV = np.einsum("nm,nmd->nd", coeff * _a[None, :], diff)
                return u0x - gdV
            return pol

        cur_guide = _make_pol()
        res = {"policy": cur_guide, "ess_per_round": ess_per_round, "solve_ms": (time.perf_counter() - t0) * 1000.0}
    return res


def run_stress_test_2_umaze():
    print(f"\n{'='*88}\nSTRESS TEST 2 — NON-CONVEX U-SHAPED TRAP / WALL GEOMETRY (2D + 4D)\n{'='*88}")
    # 2A: 2D U-shaped trap
    env_u = UMazeEnv2D(sigma=0.38, q0=0.55, r_goal=0.14)
    q_u = QuerySpec(
        name="U_Maze_Escape",
        goals=[(np.array([0.0, 0.80]), 0.0)],
        start_points=[np.array([0.0, -0.10]), np.array([-0.22, 0.0]), np.array([0.22, 0.0])],
    )
    oracle_u = ExactFDPDEOracle(env_u, grid_n=101, half_width=2.0).solve(q_u)
    solver_u = SemigroupGreenSolver(env_u, grid_n=29, half_width=1.65)
    op_exact = solver_u.build_environment_operator(env_u.q_hidden)
    op_free = solver_u.build_environment_operator(lambda X: np.zeros(len(np.atleast_2d(X))))

    m_or = env_u.simulate_rollouts(oracle_u["policy"], q_u, n_per_start=50, seed=100)
    m_ex = env_u.simulate_rollouts(solver_u.solve_query(op_exact, q_u)["policy"], q_u, n_per_start=50, seed=100)
    m_fr = env_u.simulate_rollouts(solver_u.solve_query(op_free, q_u)["policy"], q_u, n_per_start=50, seed=100)

    print("--- 2A: 2D Deep U-Trap (Start INSIDE pocket, Goal ABOVE wall!) ---")
    print(f"  Exact FD Oracle         | Cost={m_or['mean_cost']:5.2f} | Haz={m_or['mean_hazard']:5.2f} | Reach={100*m_or['reach_rate']:5.1f}%")
    print(f"  Exact-Green-1A (29x29)  | Cost={m_ex['mean_cost']:5.2f} | Haz={m_ex['mean_hazard']:5.2f} | Reach={100*m_ex['reach_rate']:5.1f}%")
    print(f"  Pure-Free-Green         | Cost={m_fr['mean_cost']:5.2f} | Haz={m_fr['mean_hazard']:5.2f} | Reach={100*m_fr['reach_rate']:5.1f}%")

    # Sparse probes N=40, N=80 on UNKNOWN U-wall
    out_2a = {"oracle": m_or, "exact_1a": m_ex, "free": m_fr, "learned": {}}
    vis_pol_80 = None
    vis_X80 = None
    for N in (40, 80):
        cs, hs, rs = [], [], []
        for sd in (0, 1, 2):
            rng = np.random.default_rng(3000 + sd * 17 + N)
            X_obs = rng.uniform(-1.05, 1.05, size=(N, 2))
            q_obs = np.maximum(0.0, env_u.q_hidden(X_obs) + rng.normal(0.0, 0.5, size=N))
            km = KrigingEnvironmentModel(X_obs, q_obs)
            op_l = solver_u.build_environment_operator(lambda X, _k=km: np.maximum(0.0, _k.predict_q(X)[0]))
            res_l = solver_u.solve_query(op_l, q_u)
            m = env_u.simulate_rollouts(res_l["policy"], q_u, n_per_start=45, seed=200 + sd)
            cs.append(m["mean_cost"]); hs.append(m["mean_hazard"]); rs.append(m["reach_rate"])
            if N == 80 and sd == 0:
                vis_pol_80 = res_l["policy"]; vis_X80 = X_obs
        out_2a["learned"][f"probes_{N}"] = {"cost": float(np.mean(cs)), "hazard": float(np.mean(hs)), "reach": float(np.mean(rs))}
        print(f"  Green-Kriging-1A (N={N}) | Cost={np.mean(cs):5.2f} | Haz={np.mean(hs):5.2f} | Reach={100*np.mean(rs):5.1f}%")

    # Pure ON-TRAJECTORY U-trap escape (agent starts blind inside U-pocket, walks into wall, learns to back out!)
    cs_ot, hs_ot, rs_ot = [], [], []
    vis_pol_ot = None
    for sd in (0, 1, 2):
        rng = np.random.default_rng(3500 + sd * 19)
        X_all, q_all = [], []
        pol = solver_u.solve_query(op_free, q_u)["policy"]
        fk_u = None
        for ep in range(1, 13):
            st = q_u.start_points[(ep - 1) % len(q_u.start_points)]
            Xp, qp, _, _, _ = collect_on_trajectory_episode(env_u, pol, q_u, st, window=8, explore_eps=0.55 if ep <= 6 else 0.25, rng=rng)
            if len(Xp) > 0:
                X_all.append(Xp); q_all.append(qp)
            Xc = np.vstack(X_all); qc = np.concatenate(q_all)
            if len(Xc) > 100:
                idx = rng.choice(len(Xc), 100, replace=False)
                Xc, qc = Xc[idx], qc[idx]
            reopt = (ep in (1, 4, 8, 12)) or (fk_u is None)
            km = KrigingEnvironmentModel(Xc, qc, fixed_kernels=None if reopt else fk_u)
            if reopt: fk_u = km.get_fitted_kernels()
            op_l = solver_u.build_environment_operator(lambda X, _k=km: np.maximum(0.0, _k.predict_q(X)[0]))
            pol = solver_u.solve_query(op_l, q_u)["policy"]
        m = env_u.simulate_rollouts(pol, q_u, n_per_start=40, seed=200 + sd)
        cs_ot.append(m["mean_cost"]); hs_ot.append(m["mean_hazard"]); rs_ot.append(m["reach_rate"])
        if sd == 0:
            vis_pol_ot = pol
    out_2a["learned"]["on_traj_12ep"] = {"cost": float(np.mean(cs_ot)), "hazard": float(np.mean(hs_ot)), "reach": float(np.mean(rs_ot))}
    print(f"  On-Traj 1A (12 blind ep)| Cost={np.mean(cs_ot):5.2f} | Haz={np.mean(hs_ot):5.2f} | Reach={100*np.mean(rs_ot):5.1f}%")

    # 2B: 4D Wide Non-Convex Wall Trap — testing 1-round vs 2-round Iterative Guiding ESS!
    print("\n--- 2B: 4D Wide Wall Trap (Testing 1-Round vs 2-Round Iterative Guiding ESS!) ---")
    c_wall = [
        HighDHazard(center=np.array([0.0, 0.15, 0.0, 0.0]), amplitude=24.0, width=0.45),
        HighDHazard(center=np.array([-0.55, 0.15, 0.0, 0.0]), amplitude=22.0, width=0.42),
        HighDHazard(center=np.array([0.55, 0.15, 0.0, 0.0]), amplitude=22.0, width=0.42),
    ]
    env_4w = HighDEnv(dim=4, sigma=0.55, q0=0.65, r_goal=0.36, hazards=c_wall)
    q_4w = HighDQuery(
        "4D_Wall_Trap",
        goals=[(np.array([0.0, 0.85, 0.0, 0.0]), 0.0)],
        starts=[np.array([0.0, -0.65, 0.0, 0.0]), np.array([-0.3, -0.55, 0.1, -0.1]), np.array([0.3, -0.55, -0.1, 0.1])],
    )
    m_4f = env_4w.simulate_rollouts(lambda X: env_4w.free_green_exact_V_and_u(X, q_4w)[1], q_4w, n_per_start=40, seed=100)
    r1 = solve_4d_iterative_green_residual(env_4w, env_4w.q_hidden, q_4w, n_rounds=1, seed=0)
    m_4r1 = env_4w.simulate_rollouts(r1["policy"], q_4w, n_per_start=40, seed=100)
    r2 = solve_4d_iterative_green_residual(env_4w, env_4w.q_hidden, q_4w, n_rounds=2, seed=0)
    m_4r2 = env_4w.simulate_rollouts(r2["policy"], q_4w, n_per_start=40, seed=100)

    print(f"  4D Pure-Free-Green      | Cost={m_4f['mean_cost']:5.2f} | Haz={m_4f['mean_hazard']:5.2f} | Reach={100*m_4f['reach_rate']:5.1f}%")
    print(f"  4D 1-Round GreenRes-1A  | Cost={m_4r1['mean_cost']:5.2f} | Haz={m_4r1['mean_hazard']:5.2f} | Reach={100*m_4r1['reach_rate']:5.1f}% | med_ESS={r1['ess_per_round']}")
    print(f"  4D 2-Round Iterative-1A | Cost={m_4r2['mean_cost']:5.2f} | Haz={m_4r2['mean_hazard']:5.2f} | Reach={100*m_4r2['reach_rate']:5.1f}% | med_ESS={r2['ess_per_round']}")

    return {"2D_UMaze": out_2a, "4D_Wall": {"free": m_4f, "round1": {**m_4r1, "ess": r1["ess_per_round"]}, "round2": {**m_4r2, "ess": r2["ess_per_round"]}}}, {
        "env_u": env_u, "q_u": q_u, "or_pol": oracle_u["policy"], "free_pol": solver_u.solve_query(op_free, q_u)["policy"],
        "pol_80": vis_pol_80, "pol_ot": vis_pol_ot, "X80": vis_X80,
    }


# ===========================================================================
# STRESS TEST 3: Breaking Cole-Hopf / LMDP Assumptions (True Model Mismatch!)
# ===========================================================================
def solve_exact_nonlinear_hjb_pi(
    env: StochasticControlEnv,
    query: QuerySpec,
    R_diag: np.ndarray,
    u_max: float,
    grid_n: int = 81,
    half_width: float = 1.8,
    n_pi: int = 12,
) -> dict:
    """
    Exact Howard Policy Iteration solver for the NON-LINEARIZABLE HJB PDE:
      min_{||u|| <= u_max} { q_tot(x) + 0.5*(r_x*u_x^2 + r_y*u_y^2) + u.grad V + 0.5*sig^2*Delta V } = 0
    Used as the true exact Oracle for Stress Test 3B!
    """
    n = grid_n
    xs = np.linspace(-half_width, half_width, n)
    h = float(xs[1] - xs[0])
    sig2 = env.sigma ** 2
    XX, YY = np.meshgrid(xs, xs, indexing="ij")
    pts = np.stack([XX.ravel(), YY.ravel()], axis=1)
    q_tot = (env.q0 + env.q_hidden(pts) + env.q_dynamic(pts, query.extra_hazards)).reshape(n, n)

    is_goal = np.zeros((n, n), dtype=bool)
    goal_phi = np.zeros((n, n), dtype=float)
    for gc, phi_j in query.goals:
        m = np.sqrt((XX - gc[0]) ** 2 + (YY - gc[1]) ** 2) <= env.r_goal
        goal_phi[m] = phi_j
        is_goal |= m

    # Initialize control pointing toward nearest goal
    g0 = query.goals[0][0]
    dx0, dy0 = g0[0] - XX, g0[1] - YY
    d0 = np.maximum(np.sqrt(dx0 ** 2 + dy0 ** 2), 1e-6)
    ux = 0.8 * u_max * dx0 / d0
    uy = 0.8 * u_max * dy0 / d0
    rx, ry = float(R_diag[0]), float(R_diag[1])
    c_diff = 0.5 * sig2 / (h * h)
    N = n * n

    V = np.zeros((n, n), dtype=float)
    for _ in range(n_pi):
        rows, cols, vals = [], [], []
        rhs = np.zeros(N, dtype=float)
        for i in range(n):
            for j in range(n):
                idx = i * n + j
                if is_goal[i, j]:
                    rows.append(idx); cols.append(idx); vals.append(1.0)
                    rhs[idx] = goal_phi[i, j]
                    continue
                if i == 0 or i == n - 1 or j == 0 or j == n - 1:
                    rows.append(idx); cols.append(idx); vals.append(1.0)
                    rhs[idx] = 8.0
                    continue
                vx, vy = ux[i, j], uy[i, j]
                diag = 4.0 * c_diff
                wxp = wxm = wyp = wym = -c_diff
                # Solve (-0.5*sig2*Delta - u.grad) V = q_tot + 0.5*(rx*vx^2 + ry*vy^2)
                if vx >= 0:
                    diag += vx / h; wxp -= vx / h
                else:
                    diag += (-vx) / h; wxm -= (-vx) / h
                if vy >= 0:
                    diag += vy / h; wyp -= vy / h
                else:
                    diag += (-vy) / h; wym -= (-vy) / h
                rows.extend([idx, idx, idx, idx, idx])
                cols.extend([idx, (i + 1) * n + j, (i - 1) * n + j, i * n + (j + 1), i * n + (j - 1)])
                vals.extend([diag, wxp, wxm, wyp, wym])
                rhs[idx] = q_tot[i, j] + 0.5 * (rx * vx * vx + ry * vy * vy)

        V = spsolve(sparse.csr_matrix((vals, (rows, cols)), shape=(N, N)), rhs).reshape(n, n)
        gx, gy = np.gradient(V, h, h)
        # Exact optimal constrained control: u = argmin_{||u||<=u_max} (0.5*u^T R u + u.g)
        ux_new = -gx / rx
        uy_new = -gy / ry
        un = np.sqrt(ux_new ** 2 + uy_new ** 2)
        scale = np.where(un > u_max, u_max / np.maximum(un, 1e-12), 1.0)
        ux = ux_new * scale
        uy = uy_new * scale

    ux_itp = RegularGridInterpolator((xs, xs), ux, bounds_error=False, fill_value=0.0)
    uy_itp = RegularGridInterpolator((xs, xs), uy, bounds_error=False, fill_value=0.0)
    V_itp = RegularGridInterpolator((xs, xs), V, bounds_error=False, fill_value=None)

    def pol(X):
        X = np.atleast_2d(X)
        xc = np.clip(X, -half_width + h, half_width - h)
        return np.stack([ux_itp(xc), uy_itp(xc)], axis=1)

    return {"policy": pol, "value_fn": lambda X: V_itp(np.clip(np.atleast_2d(X), -half_width + h, half_width - h)), "V": V}


def simulate_anisotropic_rollouts(
    env: StochasticControlEnv, policy_fn, query: QuerySpec, R_diag: np.ndarray, u_max: float,
    n_per_start: int = 50, dt: float = 0.015, max_steps: int = 450, seed: int = 100,
) -> dict:
    rng = np.random.default_rng(seed)
    starts = np.repeat(np.asarray(query.start_points, dtype=float), n_per_start, axis=0)
    x = starts.copy()
    alive = np.ones(len(x), dtype=bool)
    reached = np.zeros(len(x), dtype=bool)
    cost = np.zeros(len(x), dtype=float)
    sqrt_dt = np.sqrt(dt)
    g_centers = np.array([g[0] for g in query.goals], dtype=float)
    g_phis = np.array([g[1] for g in query.goals], dtype=float)
    rx, ry = float(R_diag[0]), float(R_diag[1])

    for _ in range(max_steps):
        if not np.any(alive): break
        idx = np.where(alive)[0]
        xa = x[idx]
        dists = np.linalg.norm(xa[:, None, :] - g_centers[None, :, :], axis=2)
        mi = np.argmin(dists, axis=1)
        hit = dists[np.arange(len(idx)), mi] <= env.r_goal
        if np.any(hit):
            hg = idx[hit]
            cost[hg] += g_phis[mi[hit]]
            reached[hg] = True; alive[hg] = False
            idx = np.where(alive)[0]
            if len(idx) == 0: break
            xa = x[idx]

        u = np.asarray(policy_fn(xa), dtype=float)
        un = np.linalg.norm(u, axis=1, keepdims=True)
        u = np.where(un > u_max, u * (u_max / np.maximum(un, 1e-12)), u)
        qh = env.q_hidden(xa) + env.q_dynamic(xa, query.extra_hazards)
        uc = 0.5 * (rx * u[:, 0] ** 2 + ry * u[:, 1] ** 2)
        cost[idx] += (env.q0 + qh + uc) * dt
        x[idx] = np.clip(xa + u * dt + env.sigma * sqrt_dt * rng.normal(size=xa.shape), -env.box_limit, env.box_limit)

    if np.any(alive):
        xa = x[alive]
        d_min = np.min(np.linalg.norm(xa[:, None, :] - g_centers[None, :, :], axis=2), axis=1)
        cost[alive] += 3.0 * d_min + 2.5
    return {"mean_cost": float(np.mean(cost)), "reach_rate": float(np.mean(reached))}


def green_1a_with_linear_pi_polish(
    env: StochasticControlEnv,
    km: KrigingEnvironmentModel,
    query: QuerySpec,
    R_diag: np.ndarray,
    u_max: float,
    n_polish: int = 4,
) -> dict:
    """
    Hybrid Non-LMDP Solver (takes ~25 ms!):
      1. Warm-start from Cole-Hopf Semigroup Green-Kriging-1A (global, avoids local minima).
      2. Run `n_polish` linear Policy-Iteration sweeps on the SAME coarse 25x25 grid using the
         Kriging hazard mu_q and exact non-LMDP cost (R_diag + hard saturation u_max)!
    """
    t0 = time.perf_counter()
    # Step 1: Cole-Hopf Green-1A warm start
    solver = SemigroupGreenSolver(env, grid_n=25, half_width=1.65)
    op = solver.build_environment_operator(lambda X: np.maximum(0.0, km.predict_q(X)[0]))
    res0 = solver.solve_query(op, query)

    # Step 2: 4 fast linear Policy-Iteration sweeps on the 25x25 lattice (M=625!)
    n = 25
    xs = np.linspace(-1.65, 1.65, n)
    h = float(xs[1] - xs[0])
    sig2 = env.sigma ** 2
    XX, YY = np.meshgrid(xs, xs, indexing="ij")
    pts = np.stack([XX.ravel(), YY.ravel()], axis=1)
    q_hat = (env.q0 + np.maximum(0.0, km.predict_q(pts)[0]) + env.q_dynamic(pts, query.extra_hazards)).reshape(n, n)

    is_goal = np.zeros((n, n), dtype=bool)
    goal_phi = np.zeros((n, n), dtype=float)
    for gc, phi_j in query.goals:
        m = np.sqrt((XX - gc[0]) ** 2 + (YY - gc[1]) ** 2) <= max(env.r_goal, 0.85 * h)
        goal_phi[m] = phi_j
        is_goal |= m

    # Warm-start control from Green-1A rescaled by R^{-1} and clipped to u_max
    rx, ry = float(R_diag[0]), float(R_diag[1])
    u0_grid = res0["policy"](pts).reshape(n, n, 2)
    ux = u0_grid[:, :, 0] / rx
    uy = u0_grid[:, :, 1] / ry
    un = np.sqrt(ux ** 2 + uy ** 2)
    sc = np.where(un > u_max, u_max / np.maximum(un, 1e-12), 1.0)
    ux *= sc; uy *= sc

    c_diff = 0.5 * sig2 / (h * h)
    N = n * n
    for _ in range(n_polish):
        rows, cols, vals = [], [], []
        rhs = np.zeros(N, dtype=float)
        for i in range(n):
            for j in range(n):
                idx = i * n + j
                if is_goal[i, j]:
                    rows.append(idx); cols.append(idx); vals.append(1.0); rhs[idx] = goal_phi[i, j]; continue
                if i == 0 or i == n - 1 or j == 0 or j == n - 1:
                    rows.append(idx); cols.append(idx); vals.append(1.0); rhs[idx] = 8.0; continue
                vx, vy = ux[i, j], uy[i, j]
                diag = 4.0 * c_diff
                wxp = wxm = wyp = wym = -c_diff
                if vx >= 0: diag += vx / h; wxp -= vx / h
                else: diag += (-vx) / h; wxm -= (-vx) / h
                if vy >= 0: diag += vy / h; wyp -= vy / h
                else: diag += (-vy) / h; wym -= (-vy) / h
                rows.extend([idx, idx, idx, idx, idx])
                cols.extend([idx, (i + 1) * n + j, (i - 1) * n + j, i * n + (j + 1), i * n + (j - 1)])
                vals.extend([diag, wxp, wxm, wyp, wym])
                rhs[idx] = q_hat[i, j] + 0.5 * (rx * vx * vx + ry * vy * vy)
        V = spsolve(sparse.csr_matrix((vals, (rows, cols)), shape=(N, N)), rhs).reshape(n, n)
        gx, gy = np.gradient(V, h, h)
        ux_n, uy_n = -gx / rx, -gy / ry
        un = np.sqrt(ux_n ** 2 + uy_n ** 2)
        sc = np.where(un > u_max, u_max / np.maximum(un, 1e-12), 1.0)
        ux, uy = ux_n * sc, uy_n * sc

    ms = (time.perf_counter() - t0) * 1000.0
    ux_itp = RegularGridInterpolator((xs, xs), ux, bounds_error=False, fill_value=0.0)
    uy_itp = RegularGridInterpolator((xs, xs), uy, bounds_error=False, fill_value=0.0)
    return {"policy": lambda X: np.stack([ux_itp(np.clip(np.atleast_2d(X), -1.5, 1.5)), uy_itp(np.clip(np.atleast_2d(X), -1.5, 1.5))], axis=1), "solve_ms": ms}


def run_stress_test_3_mismatch():
    print(f"\n{'='*88}\nSTRESS TEST 3 — BREAKING COLE-HOPF / LMDP ASSUMPTIONS (TRUE MODEL MISMATCH)\n{'='*88}")
    # 3A: Unknown diffusion sigma_true = 0.72 vs wrong fixed sigma = 0.25 vs online estimated sigma_hat!
    print("\n--- 3A: Unknown Diffusion Noise sigma (true=0.72, wrong assumption=0.25 vs online-estimated) ---")
    env_true, queries = build_default_benchmark(with_vortex=False)
    env_true.sigma = 0.72
    or_3a = {q.name: env_true.simulate_rollouts(ExactFDPDEOracle(env_true, grid_n=101, half_width=2.0).solve(q)["policy"], q, n_per_start=50, seed=100)["mean_cost"] for q in queries}

    rng = np.random.default_rng(4242)
    # Estimate sigma_hat from just 3 short noisy episodes (quadratic variation of increments!)
    op_f0 = SemigroupGreenSolver(StochasticControlEnv(sigma=0.45, q0=env_true.q0, r_goal=env_true.r_goal), grid_n=21).build_environment_operator(lambda X: np.zeros(len(np.atleast_2d(X))))
    raw_all = []
    for k in range(3):
        _, _, _, _, raw = collect_on_trajectory_episode(env_true, SemigroupGreenSolver(StochasticControlEnv(sigma=0.45, q0=env_true.q0, r_goal=env_true.r_goal), grid_n=21).solve_query(op_f0, queries[0])["policy"], queries[0], queries[0].start_points[k], rng=rng)
        raw_all.append(raw)
    raw_cat = np.vstack(raw_all)
    # Quadratic variation: E[||dx - u dt||^2] = 2 * sigma^2 * dt  (minus tiny drift^2*dt^2)
    sigma_hat = float(np.sqrt(np.mean(np.sum(raw_cat ** 2, axis=1)) / (2.0 * 0.015)))

    X30 = rng.uniform(-1.05, 1.05, size=(30, 2))
    q30 = np.maximum(0.0, env_true.q_hidden(X30) + rng.normal(0.0, 0.5, size=30))
    km30 = KrigingEnvironmentModel(X30, q30)

    out_3a = {"sigma_true": 0.72, "sigma_hat": sigma_hat, "oracle_avg": float(np.mean(list(or_3a.values())))}
    for lbl, sig_val in [("Wrong Fixed sigma=0.25", 0.25), (f"Online-Estimated sigma={sigma_hat:.3f}", sigma_hat), ("True sigma=0.72", 0.72)]:
        e_mod = StochasticControlEnv(sigma=sig_val, q0=env_true.q0, r_goal=env_true.r_goal)
        slv = SemigroupGreenSolver(e_mod, grid_n=25, half_width=1.65)
        op = slv.build_environment_operator(lambda X: np.maximum(0.0, km30.predict_q(X)[0]))
        cs = [env_true.simulate_rollouts(slv.solve_query(op, q)["policy"], q, n_per_start=50, seed=100)["mean_cost"] for q in queries]
        out_3a[lbl] = float(np.mean(cs))
        print(f"  {lbl:34s} | AvgCost={np.mean(cs):.3f} (Oracle={out_3a['oracle_avg']:.3f}, gap={100*(np.mean(cs)-out_3a['oracle_avg'])/out_3a['oracle_avg']:+.1f}%)")

    # 3B: TRUE NON-LMDP MISMATCH: Anisotropic R = diag(0.35, 3.0) + Hard Saturation ||u|| <= 1.8!
    print("\n--- 3B: True Non-LMDP Mismatch: Anisotropic R=diag(0.35, 3.0) + Hard Clip ||u||<=1.8 ---")
    env_nl, queries_nl = build_default_benchmark(with_vortex=False)
    R_diag = np.array([0.35, 3.0])  # vertical motion 8.6x more expensive than horizontal!
    u_max = 1.8

    rng2 = np.random.default_rng(5151)
    X30b = rng2.uniform(-1.05, 1.05, size=(30, 2))
    q30b = np.maximum(0.0, env_nl.q_hidden(X30b) + rng2.normal(0.0, 0.5, size=30))
    km30b = KrigingEnvironmentModel(X30b, q30b)

    slv_nl = SemigroupGreenSolver(env_nl, grid_n=25, half_width=1.65)
    op_free_nl = slv_nl.build_environment_operator(lambda X: np.zeros(len(np.atleast_2d(X))))
    op_naive_nl = slv_nl.build_environment_operator(lambda X: np.maximum(0.0, km30b.predict_q(X)[0]))

    res_3b = {m: [] for m in ["Exact-Nonlinear-HJB-Oracle", "Pure-Free-Green", "Naive-Isotropic-Green-1A (N=30)", "R-Scaled-Green-1A (N=30)", "Green-1A + 4-step PI Polish (N=30)"]}
    polish_ms = []
    vis_3b = {}

    for qi, q in enumerate(queries_nl):
        or_nl = solve_exact_nonlinear_hjb_pi(env_nl, q, R_diag, u_max, grid_n=81)
        m_or = simulate_anisotropic_rollouts(env_nl, or_nl["policy"], q, R_diag, u_max)
        m_fr = simulate_anisotropic_rollouts(env_nl, slv_nl.solve_query(op_free_nl, q)["policy"], q, R_diag, u_max)
        pol_naive = slv_nl.solve_query(op_naive_nl, q)["policy"]
        m_nv = simulate_anisotropic_rollouts(env_nl, pol_naive, q, R_diag, u_max)
        # Simple R^{-1} scaling of Green-1A gradient (still 13ms!)
        pol_rsc = lambda X, _p=pol_naive: _p(X) / R_diag[None, :]
        m_rs = simulate_anisotropic_rollouts(env_nl, pol_rsc, q, R_diag, u_max)
        # Green-1A + 4-step Linear Policy-Iteration Polish (~25ms!)
        pol_pi = green_1a_with_linear_pi_polish(env_nl, km30b, q, R_diag, u_max, n_polish=4)
        polish_ms.append(pol_pi["solve_ms"])
        m_pi = simulate_anisotropic_rollouts(env_nl, pol_pi["policy"], q, R_diag, u_max)

        res_3b["Exact-Nonlinear-HJB-Oracle"].append(m_or["mean_cost"])
        res_3b["Pure-Free-Green"].append(m_fr["mean_cost"])
        res_3b["Naive-Isotropic-Green-1A (N=30)"].append(m_nv["mean_cost"])
        res_3b["R-Scaled-Green-1A (N=30)"].append(m_rs["mean_cost"])
        res_3b["Green-1A + 4-step PI Polish (N=30)"].append(m_pi["mean_cost"])
        if qi == 0:
            vis_3b = {"env": env_nl, "query": q, "or": or_nl["policy"], "naive": pol_naive, "polish": pol_pi["policy"], "u_max": u_max}

    or_avg_nl = float(np.mean(res_3b["Exact-Nonlinear-HJB-Oracle"]))
    out_3b = {"polish_ms": float(np.mean(polish_ms)), "methods": {}}
    for k, vals in res_3b.items():
        avg = float(np.mean(vals))
        gap = 100.0 * (avg - or_avg_nl) / or_avg_nl
        out_3b["methods"][k] = {"avg_cost": avg, "per_query": vals, "gap_pct": gap}
        extra = f" | solve={np.mean(polish_ms):.1f}ms" if "Polish" in k else ""
        print(f"  {k:38s} | Q1-Q4 Avg={avg:5.2f} ({gap:+5.1f}% vs Exact Nonlinear HJB){extra}")

    return {"3A_unknown_sigma": out_3a, "3B_anisotropic_saturated": out_3b}, vis_3b


def make_stress_plot(vis_2a: dict, vis_3b: dict, out_png: str):
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.9), dpi=130)
    gx = np.linspace(-1.1, 1.1, 70)
    XX, YY = np.meshgrid(gx, gx, indexing="ij")
    grid_pts = np.stack([XX.ravel(), YY.ravel()], axis=1)

    # Panel 1 & 2: 2D U-Maze escape (Probes N=80 vs Pure On-Trajectory 12 blind episodes)
    env_u, q_u = vis_2a["env_u"], vis_2a["q_u"]
    qh_u = env_u.q_hidden(grid_pts).reshape(XX.shape)
    for ax, title, pol, show_pts in [
        (axes[0], "Stress 2A: Unknown U-Maze (Green-1A, N=80 probes)", vis_2a["pol_80"], True),
        (axes[1], "Stress 2A: Unknown U-Maze (On-Trajectory 12 blind ep)", vis_2a["pol_ot"], False),
    ]:
        ax.contourf(XX, YY, qh_u, levels=18, cmap="Reds", alpha=0.82)
        gc = q_u.goals[0][0]
        ax.add_patch(plt.Circle(gc, env_u.r_goal, facecolor="none", edgecolor="lime", lw=2.2, zorder=6))
        ax.scatter([gc[0]], [gc[1]], c="green", s=70, marker="*", zorder=7)
        if show_pts and vis_2a["X80"] is not None:
            ax.scatter(vis_2a["X80"][:, 0], vis_2a["X80"][:, 1], c="black", s=12, marker="x", alpha=0.6, zorder=5)
        for st in q_u.start_points:
            for p_fn, col, ls_s, lbl in [
                (vis_2a["free_pol"], "gray", ":", "Pure-Free-Green"),
                (vis_2a["or_pol"], "blue", "--", "Exact Oracle"),
                (pol, "cyan", "-", "Green-Kriging-1A"),
            ]:
                path = [st.copy()]; x = st.copy()
                for _ in range(300):
                    if np.linalg.norm(x - gc) <= env_u.r_goal: break
                    u = p_fn(x[None, :])[0]
                    un = np.linalg.norm(u)
                    if un > 6.0: u = u * (6.0 / un)
                    x = np.clip(x + u * 0.015, -1.25, 1.25); path.append(x.copy())
                P = np.array(path)
                ax.plot(P[:, 0], P[:, 1], color=col, linestyle=ls_s, lw=2.1, label=lbl if np.allclose(st, q_u.start_points[0]) else None)
        ax.set_xlim(-1.1, 1.1); ax.set_ylim(-1.1, 1.1); ax.set_title(title, fontsize=9.5)
        ax.legend(loc="lower right", fontsize=7.5)

    # Panel 3: Stress 3B Anisotropic Non-LMDP (Naive Green-1A vs Green-1A + PI Polish vs Nonlinear HJB Oracle)
    ax3 = axes[2]
    env_nl, q_nl = vis_3b["env"], vis_3b["query"]
    qh_nl = env_nl.q_hidden(grid_pts).reshape(XX.shape)
    ax3.contourf(XX, YY, qh_nl, levels=18, cmap="Reds", alpha=0.80)
    gc = q_nl.goals[0][0]
    ax3.add_patch(plt.Circle(gc, env_nl.r_goal, facecolor="none", edgecolor="lime", lw=2.2, zorder=6))
    ax3.scatter([gc[0]], [gc[1]], c="green", s=70, marker="*", zorder=7)
    for st in q_nl.start_points[:3]:
        for p_fn, col, ls_s, lbl in [
            (vis_3b["or"], "blue", "--", "Exact Nonlinear HJB"),
            (vis_3b["naive"], "orange", ":", "Naive Isotropic 1A"),
            (vis_3b["polish"], "cyan", "-", "1A + 4-step PI Polish"),
        ]:
            path = [st.copy()]; x = st.copy()
            for _ in range(340):
                if np.linalg.norm(x - gc) <= env_nl.r_goal: break
                u = p_fn(x[None, :])[0]
                un = np.linalg.norm(u)
                if un > vis_3b["u_max"]: u = u * (vis_3b["u_max"] / un)
                x = np.clip(x + u * 0.015, -1.25, 1.25); path.append(x.copy())
            P = np.array(path)
            ax3.plot(P[:, 0], P[:, 1], color=col, linestyle=ls_s, lw=2.1, label=lbl if np.allclose(st, q_nl.start_points[0]) else None)
    ax3.set_xlim(-1.1, 1.1); ax3.set_ylim(-1.1, 1.1)
    ax3.set_title("Stress 3B: Non-LMDP R=diag(0.35, 3.0), ||u||<=1.8", fontsize=9.5)
    ax3.legend(loc="lower right", fontsize=7.5)

    plt.tight_layout()
    plt.savefig(out_png)
    plt.close(fig)


if __name__ == "__main__":
    t0 = time.perf_counter()
    s1 = run_stress_test_1_ontrajectory()
    s2, vis_2a = run_stress_test_2_umaze()
    s3, vis_3b = run_stress_test_3_mismatch()

    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, "stress_boundaries_results.json"), "w", encoding="utf-8") as f:
        json.dump({"stress1_ontrajectory": s1, "stress2_umaze": s2, "stress3_mismatch": s3}, f, indent=2)
    png_path = os.path.join(out_dir, "stress_boundaries.png")
    make_stress_plot(vis_2a, vis_3b, png_path)
    print(f"\nAll 3 boundary stress tests finished in {time.perf_counter() - t0:.1f}s. Saved plot to {png_path}")
