"""
Closing the Last Two High-Value Research Gaps:
  Test 4 (Limitation 4):
    4D & 6D Stochastic Control with BOTH Unknown Hazards q_hid(x) AND Unknown
    Non-Conservative Rotational Vortex Drift b(x) + Calibrated High-D Elliptic/Feynman-Kac
    Uncertainty Envelope [V_lower, V_upper] (verified against high-precision true-env FK!).
  Test 5 (Limitation 2 — Hardest Part: Underactuated Second-Order Dynamics):
    4D Underactuated Inertial Double Integrator:
        dp_t = v_t dt
        dv_t = (-gamma * v_t + f_wind(p_t) + u_t) dt + sigma dW_t   (u_t in R^2, x_t in R^4!)
    Control enters ONLY through acceleration (rank-2 B in 4D state space, non-zero initial
    velocity!). Still satisfies exact Hypoelliptic Cole-Hopf Linearization!
    Compares Online-PIMC (True Env), Free-Space LQR, 4D Hypoelliptic PINN-HJB, and
    Underactuated GreenResidual-Kriging-1A (only N=30 noisy probes across Q1-Q3 zero-shot!).
"""
from __future__ import annotations

import json
import os
import time
import warnings
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple
import numpy as np
from scipy.linalg import solve_continuous_are
from scipy.special import kv, logsumexp
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
import torch
import torch.nn as nn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from test_breakthrough_a_highd import HighDHazard, HighDQuery, HighDEnv


# ===========================================================================
# TEST 4: 4D & 6D with Unknown Hazards + Unknown Non-Conservative Drift + Calibrated Envelope
# ===========================================================================
@dataclass
class HighDDriftEnv(HighDEnv):
    vortex_strength: float = 1.4
    vortex_width: float = 0.70

    def drift(self, X: np.ndarray) -> np.ndarray:
        """Non-conservative rotational vortex in (x0, x1) + coupled swirl in (x2, x3)."""
        X = np.atleast_2d(X)
        out = np.zeros_like(X)
        if abs(self.vortex_strength) > 0.0:
            r2 = np.sum(X ** 2, axis=1)
            env = np.exp(-0.5 * r2 / (self.vortex_width ** 2))
            # Divergence-free non-conservative rotation in planes (0,1) and (2,3)
            out[:, 0] = -self.vortex_strength * X[:, 1] * env
            out[:, 1] = +self.vortex_strength * X[:, 0] * env
            if self.dim >= 4:
                out[:, 2] = -0.8 * self.vortex_strength * X[:, 3] * env
                out[:, 3] = +0.8 * self.vortex_strength * X[:, 2] * env
        return out

    def simulate_rollouts(
        self, policy_fn, query: HighDQuery, n_per_start: int = 35,
        dt: float = 0.02, max_steps: int = 300, u_clip: float = 6.5, seed: int = 0,
    ) -> dict:
        rng = np.random.default_rng(seed)
        starts = np.repeat(np.asarray(query.starts, dtype=float), n_per_start, axis=0)
        x = starts.copy()
        alive = np.ones(len(x), dtype=bool)
        reached = np.zeros(len(x), dtype=bool)
        total_cost = np.zeros(len(x), dtype=float)
        hazard_cost = np.zeros(len(x), dtype=float)
        sqrt_dt = np.sqrt(dt)
        g_centers = np.array([g[0] for g in query.goals], dtype=float)
        g_phis = np.array([g[1] for g in query.goals], dtype=float)

        for _ in range(max_steps):
            if not np.any(alive):
                break
            idx = np.where(alive)[0]
            xa = x[idx]
            dists = np.linalg.norm(xa[:, None, :] - g_centers[None, :, :], axis=2)
            mi = np.argmin(dists, axis=1)
            hit = dists[np.arange(len(idx)), mi] <= self.r_goal
            if np.any(hit):
                hg = idx[hit]
                total_cost[hg] += g_phis[mi[hit]]
                reached[hg] = True
                alive[hg] = False
                idx = np.where(alive)[0]
                if len(idx) == 0:
                    break
                xa = x[idx]

            u = np.asarray(policy_fn(xa), dtype=float)
            un = np.linalg.norm(u, axis=1, keepdims=True)
            u = np.where(un > u_clip, u * (u_clip / np.maximum(un, 1e-12)), u)
            qh = self.q_hidden(xa)
            hazard_cost[idx] += qh * dt
            total_cost[idx] += (self.q0 + qh + 0.5 * np.sum(u ** 2, axis=1)) * dt
            b = self.drift(xa)
            x[idx] = np.clip(xa + (b + u) * dt + self.sigma * sqrt_dt * rng.normal(size=xa.shape), -self.box_limit, self.box_limit)

        if np.any(alive):
            xa = x[alive]
            d_min = np.min(np.linalg.norm(xa[:, None, :] - g_centers[None, :, :], axis=2), axis=1)
            total_cost[alive] += 2.2 * d_min + 2.5

        return {
            "mean_cost": float(np.mean(total_cost)),
            "mean_hazard": float(np.mean(hazard_cost)),
            "reach_rate": float(np.mean(reached)),
        }


class HighDKrigingModel:
    """Fits Matérn-5/2 Kriging posteriors on high-D noisy hazard q_hid and d-D drift b."""

    def __init__(self, X_obs: np.ndarray, q_obs: np.ndarray, b_obs: np.ndarray):
        self.d = X_obs.shape[1]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            kq = ConstantKernel(5.0, (0.1, 80.0)) * Matern(length_scale=0.65, length_scale_bounds=(0.2, 2.5), nu=2.5) + WhiteKernel(noise_level=0.25, noise_level_bounds=(1e-4, 5.0))
            self.gp_q = GaussianProcessRegressor(kernel=kq, n_restarts_optimizer=1, normalize_y=False, random_state=0).fit(X_obs, q_obs)
            self.gp_b = []
            for j in range(self.d):
                kb = ConstantKernel(0.8, (0.01, 10.0)) * Matern(length_scale=0.75, length_scale_bounds=(0.2, 3.0), nu=2.5) + WhiteKernel(noise_level=0.05, noise_level_bounds=(1e-4, 2.0))
                self.gp_b.append(GaussianProcessRegressor(kernel=kb, n_restarts_optimizer=1, normalize_y=False, random_state=j).fit(X_obs, b_obs[:, j]))

    def predict_q(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        mu, std = self.gp_q.predict(np.atleast_2d(X), return_std=True)
        return mu, std

    def predict_b(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        X = np.atleast_2d(X)
        mus, vars_ = [], []
        for gp in self.gp_b:
            m, s = gp.predict(X, return_std=True)
            mus.append(m)
            vars_.append(s ** 2)
        return np.stack(mus, axis=1), np.sqrt(np.sum(vars_, axis=0))  # (N, d), (N,) norm std


def eval_fk_delta_V_with_drift(
    env: HighDDriftEnv,
    X_pts: np.ndarray,
    q_fn: Callable[[np.ndarray], np.ndarray],
    b_fn: Callable[[np.ndarray], np.ndarray],
    query: HighDQuery,
    n_fk_paths: int = 72,
    fk_steps: int = 44,
    dt_fk: float = 0.045,
    seed: int = 0,
) -> np.ndarray:
    """
    Exact Control-Variate Feynman-Kac formula for Delta_V(x) = V*(x) - V_0^{(d)}(x)
    under non-conservative drift b(x) and hazard q(x):
      dX_t = (u_0*(X_t) + b(X_t)) dt + sigma dW_t,
      Y(x) = E[ exp( -int_0^tau (q(X_t) - b(X_t) . u_0*(X_t)) dt / sig^2 ) ],
      Delta_V(x) = -sig^2 log Y(x).  (Can be negative if tailwind helps!)
    """
    rng = np.random.default_rng(seed)
    X_pts = np.atleast_2d(X_pts)
    M, d = X_pts.shape
    sig2 = env.sigma ** 2
    g_centers = np.array([g[0] for g in query.goals], dtype=float)

    pos = np.repeat(X_pts[:, None, :], n_fk_paths, axis=1)  # (M, K, d)
    acc = np.zeros((M, n_fk_paths), dtype=float)
    alive = np.ones((M, n_fk_paths), dtype=bool)
    sqrt_dt = np.sqrt(dt_fk)

    for _ in range(fk_steps):
        if not np.any(alive):
            break
        ai, aj = np.where(alive)
        pa = pos[ai, aj]
        _, u0 = env.free_green_exact_V_and_u(pa, query)
        un = np.linalg.norm(u0, axis=1, keepdims=True)
        u0_c = np.where(un > 5.0, u0 * (5.0 / np.maximum(un, 1e-12)), u0)

        qh = np.maximum(0.0, np.asarray(q_fn(pa), dtype=float))
        bh = np.asarray(b_fn(pa), dtype=float)
        # Exact multiplicative perturbation stage cost: q_hid - b . u_0*
        q_eff = qh - np.sum(bh * u0_c, axis=1)
        acc[ai, aj] += q_eff * dt_fk

        p_next = pa + (u0_c + bh) * dt_fk + env.sigma * sqrt_dt * rng.normal(size=pa.shape)
        pos[ai, aj] = p_next
        hit = np.min(np.linalg.norm(p_next[:, None, :] - g_centers[None, :, :], axis=2), axis=1) <= env.r_goal
        if np.any(hit):
            alive[ai[hit], aj[hit]] = False

    log_Y = logsumexp(-acc / sig2, axis=1) - np.log(n_fk_paths)
    return -sig2 * log_Y


def solve_highd_drift_1a_with_envelope(
    env: HighDDriftEnv,
    km: HighDKrigingModel,
    query: HighDQuery,
    beta_sim: float = 2.6,
    n_anchors: int = 90,
    seed: int = 0,
) -> dict:
    """
    Fits smooth Kriging residual for nominal Delta_V (and closed-form policy u*(x))
    PLUS computes calibrated high-D Elliptic/FK bounds [V_lower, V_upper] using
    BOTH hazard std_q AND adversarial/helpful drift std_b!
    """
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    d = env.dim

    # Build corridor + global anchors + goal BC anchors
    anchors = []
    per_pair = max(4, int(0.70 * n_anchors) // (len(query.starts) * len(query.goals)))
    for st in query.starts:
        for gc, _ in query.goals:
            ts = rng.uniform(0.0, 0.92, size=(per_pair, 1))
            base = (1.0 - ts) * st[None, :] + ts * gc[None, :]
            anchors.append(np.clip(base + rng.normal(0.0, 0.42, size=(per_pair, d)), -1.2, 1.2))
    anchors.append(rng.uniform(-1.05, 1.05, size=(max(20, n_anchors - sum(len(a) for a in anchors)), d)))
    X_int = np.vstack(anchors)
    mask = np.ones(len(X_int), dtype=bool)
    for gc, _ in query.goals:
        mask &= np.linalg.norm(X_int - gc[None, :], axis=1) > env.r_goal + 0.05
    X_int = X_int[mask][:n_anchors]

    bc = []
    for gc, _ in query.goals:
        dirs = rng.normal(size=(8, d)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
        bc.append(gc[None, :] + env.r_goal * dirs)
    X_bc = np.vstack(bc)

    q_mean_fn = lambda X: np.maximum(0.0, km.predict_q(X)[0])
    b_mean_fn = lambda X: km.predict_b(X)[0]

    dV_nom = eval_fk_delta_V_with_drift(env, X_int, q_mean_fn, b_mean_fn, query, n_fk_paths=64, seed=seed)
    X_fit = np.vstack([X_int, X_bc])
    y_fit = np.concatenate([dV_nom, np.zeros(len(X_bc))])

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        k_res = ConstantKernel(2.0, (0.05, 50.0)) * Matern(length_scale=0.65, length_scale_bounds=(0.2, 2.5), nu=2.5) + WhiteKernel(noise_level=0.05, noise_level_bounds=(1e-4, 2.0))
        gp_res = GaussianProcessRegressor(kernel=k_res, n_restarts_optimizer=1, normalize_y=False, random_state=seed).fit(X_fit, y_fit)

    solve_ms = (time.perf_counter() - t0) * 1000.0
    X_tr = gp_res.X_train_
    alpha_gp = gp_res.alpha_
    c_var = float(gp_res.kernel_.k1.k1.constant_value)
    ell = float(gp_res.kernel_.k1.k2.length_scale)
    s5 = np.sqrt(5.0) / ell

    def eval_dV_and_grad(X: np.ndarray):
        X = np.atleast_2d(X)
        diff = X[:, None, :] - X_tr[None, :, :]
        r = np.sqrt(np.sum(diff ** 2, axis=2) + 1e-18)
        sr = s5 * r
        exp_sr = np.exp(-sr)
        K = c_var * (1.0 + sr + (sr ** 2) / 3.0) * exp_sr
        dV = K @ alpha_gp
        coeff = -(5.0 / (3.0 * ell * ell)) * c_var * (1.0 + sr) * exp_sr
        gdV = np.einsum("nm,nmd->nd", coeff * alpha_gp[None, :], diff)
        return dV, gdV

    def policy(X: np.ndarray) -> np.ndarray:
        _, u0 = env.free_green_exact_V_and_u(X, query)
        _, gdV = eval_dV_and_grad(X)
        return u0 - gdV

    def value_fn(X: np.ndarray) -> np.ndarray:
        V0, _ = env.free_green_exact_V_and_u(X, query)
        dV, _ = eval_dV_and_grad(X)
        return V0 + dV

    # High-D calibrated envelope evaluator (at any test points X_eval):
    # Combines hazard UCB/LCB AND adversarial/helpful drift comparison along u_nom!
    def eval_envelope(X_eval: np.ndarray, mc_slack: float = 0.25) -> Tuple[np.ndarray, np.ndarray]:
        V0, _ = env.free_green_exact_V_and_u(X_eval, query)

        def q_ucb(X):
            m, s = km.predict_q(X)
            return np.maximum(0.0, m + beta_sim * s)

        def q_lcb(X):
            m, s = km.predict_q(X)
            return np.maximum(0.0, m - beta_sim * s)

        def b_adv(X):
            bm, sb = km.predict_b(X)
            u_x = policy(X)
            dir_g = u_x / np.maximum(np.linalg.norm(u_x, axis=1, keepdims=True), 1e-4)
            return bm - (beta_sim * sb)[:, None] * dir_g

        def b_help(X):
            bm, sb = km.predict_b(X)
            u_x = policy(X)
            dir_g = u_x / np.maximum(np.linalg.norm(u_x, axis=1, keepdims=True), 1e-4)
            return bm + (beta_sim * sb)[:, None] * dir_g

        dV_hi = eval_fk_delta_V_with_drift(env, X_eval, q_ucb, b_adv, query, n_fk_paths=96, seed=seed + 77)
        dV_lo = eval_fk_delta_V_with_drift(env, X_eval, q_lcb, b_help, query, n_fk_paths=96, seed=seed + 77)
        return np.maximum(0.0, V0 + dV_lo - mc_slack), V0 + dV_hi + mc_slack

    return {"policy": policy, "value_fn": value_fn, "eval_envelope": eval_envelope, "solve_ms": solve_ms}


def run_test_4_highd_drift_and_envelope():
    print(f"\n{'='*90}\nTEST 4 (CLOSING LIMITATION 4) — 4D & 6D UNKNOWN HAZARDS + NON-CONSERVATIVE DRIFT + ENVELOPE\n{'='*90}")
    out = {}
    for dim, budgets in [(4, (45, 90)), (6, (75, 140))]:
        c1 = np.zeros(dim); c1[0] = 0.0; c1[1] = 0.08
        c2 = np.zeros(dim); c2[0] = 0.18; c2[1] = -0.22; c2[2] = 0.15
        w_haz = 0.55 if dim == 4 else 0.72
        env = HighDDriftEnv(
            dim=dim, sigma=0.55, q0=0.70, r_goal=0.36 if dim == 4 else 0.48,
            hazards=[HighDHazard(c1, 14.0, w_haz), HighDHazard(c2, 12.0, w_haz)],
            vortex_strength=1.4, vortex_width=0.75,
        )
        g1 = np.zeros(dim); g1[0] = 0.72; g1[1] = 0.68; g1[2] = 0.25
        g2 = np.zeros(dim); g2[0] = -0.72; g2[1] = 0.68; g2[2] = -0.25
        s1 = np.zeros(dim); s1[0] = -0.70; s1[1] = -0.65; s1[2] = -0.20
        s2 = np.zeros(dim); s2[0] = -0.65; s2[1] = 0.15; s2[2] = 0.35
        s3 = np.zeros(dim); s3[0] = 0.65; s3[1] = -0.68; s3[2] = 0.20
        sq2 = [np.array([0.70, -0.62, 0.25] + [0.0]*(dim-3)), np.array([0.65, 0.20, -0.30] + [0.0]*(dim-3)), np.array([-0.55, -0.68, -0.20] + [0.0]*(dim-3))]
        sq3 = [np.array([0.0, -0.75, 0.0] + [0.0]*(dim-3)), np.array([-0.40, -0.68, -0.20] + [0.0]*(dim-3)), np.array([0.42, -0.68, 0.20] + [0.0]*(dim-3))]
        queries = [
            HighDQuery("Q1_seen", [(g1, 0.0)], [s1, s2, s3]),
            HighDQuery("Q2_unseen", [(g2, 0.0)], sq2),
            HighDQuery("Q3_multigoal", [(g1, 0.0), (g2, 0.10)], sq3),
        ]

        # High-precision true-environment FK reference V* on 50 test points per query + Exact-1A rollout reference
        rng_ev = np.random.default_rng(888 + dim)
        eval_pts_by_q, v_true_by_q = {}, {}
        free_costs, exact_costs = [], []
        for qi, q in enumerate(queries):
            pts = rng_ev.uniform(-0.85, 0.85, size=(70, dim))
            m = np.ones(len(pts), dtype=bool)
            for gc, _ in q.goals:
                m &= np.linalg.norm(pts - gc[None, :], axis=1) > env.r_goal + 0.15
            pts = pts[m][:50]
            eval_pts_by_q[q.name] = pts
            V0_e, _ = env.free_green_exact_V_and_u(pts, q)
            dV_t = eval_fk_delta_V_with_drift(env, pts, env.q_hidden, env.drift, q, n_fk_paths=256, seed=999 + qi)
            v_true_by_q[q.name] = V0_e + dV_t

            # Pure free green rollout
            mf = env.simulate_rollouts(lambda X, _q=q: env.free_green_exact_V_and_u(X, _q)[1], q, n_per_start=35, seed=100)
            free_costs.append(mf["mean_cost"])

            # True-env GreenResidual-1A with exact q & exact drift
            # Create dummy exact km wrapper via solve_with_exact
            dV_tr = eval_fk_delta_V_with_drift(env, pts, env.q_hidden, env.drift, q, n_fk_paths=64, seed=42 + qi)
            # Fit exact residual quickly using true q and true drift
            rng_ex = np.random.default_rng(42 + qi)
            X_ex = np.vstack([pts, np.vstack([gc[None, :] + env.r_goal * (rng_ex.normal(size=(8, dim)) / np.linalg.norm(rng_ex.normal(size=(8, dim)), axis=1, keepdims=True)) for gc, _ in q.goals])])
            # Evaluate on corridor anchors for clean true-env baseline
            anc = []
            for st in q.starts:
                for gc, _ in q.goals:
                    ts = rng_ex.uniform(0.0, 0.9, size=(12, 1))
                    anc.append(np.clip((1-ts)*st[None,:] + ts*gc[None,:] + rng_ex.normal(0, 0.4, size=(12, dim)), -1.2, 1.2))
            X_a = np.vstack(anc)
            ma = np.ones(len(X_a), dtype=bool)
            for gc, _ in q.goals: ma &= np.linalg.norm(X_a - gc[None, :], axis=1) > env.r_goal + 0.05
            X_a = X_a[ma][:90]
            dV_a = eval_fk_delta_V_with_drift(env, X_a, env.q_hidden, env.drift, q, n_fk_paths=64, seed=42 + qi)
            bc_e = []
            for gc, _ in q.goals:
                dr = rng_ex.normal(size=(8, dim)); dr /= np.linalg.norm(dr, axis=1, keepdims=True)
                bc_e.append(gc[None, :] + env.r_goal * dr)
            X_bc_e = np.vstack(bc_e)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ConvergenceWarning)
                gp_e = GaussianProcessRegressor(kernel=ConstantKernel(2.0,(0.05,50.0))*Matern(0.65,(0.2,2.5),nu=2.5)+WhiteKernel(0.05,(1e-4,2.0)), n_restarts_optimizer=1, normalize_y=False, random_state=0).fit(np.vstack([X_a, X_bc_e]), np.concatenate([dV_a, np.zeros(len(X_bc_e))]))
            Xt, al, cv, el = gp_e.X_train_, gp_e.alpha_, float(gp_e.kernel_.k1.k1.constant_value), float(gp_e.kernel_.k1.k2.length_scale)
            s5e = np.sqrt(5.0)/el
            def _ex_pol(X, _q=q, _Xt=Xt, _al=al, _cv=cv, _el=el, _s5=s5e):
                X = np.atleast_2d(X)
                _, u0 = env.free_green_exact_V_and_u(X, _q)
                df = X[:, None, :] - _Xt[None, :, :]
                r = np.sqrt(np.sum(df**2, axis=2) + 1e-18); sr = _s5*r
                gd = np.einsum("nm,nmd->nd", (-(5.0/(3.0*_el*_el))*_cv*(1.0+sr)*np.exp(-sr))*_al[None,:], df)
                return u0 - gd
            me = env.simulate_rollouts(_ex_pol, q, n_per_start=35, seed=100)
            exact_costs.append(me["mean_cost"])

        print(f"\n[{dim}D + Non-Conservative Vortex Drift] Exact-1A Avg={np.mean(exact_costs):.2f} | Pure-Free-Green Avg={np.mean(free_costs):.2f}")
        out[f"{dim}D"] = {"exact_1a_avg": float(np.mean(exact_costs)), "free_avg": float(np.mean(free_costs)), "budgets": {}}

        for N in budgets:
            costs_s, reaches_s, covs_s, widths_s, maes_s, ms_s = [], [], [], [], [], []
            for sd in (0, 1):
                rng = np.random.default_rng(600 + 31 * sd + 100 * dim + N)
                X_obs = rng.uniform(-1.1, 1.1, size=(N, dim))
                q_obs = np.maximum(0.0, env.q_hidden(X_obs) + rng.normal(0.0, 0.5, size=N))
                b_obs = env.drift(X_obs) + rng.normal(0.0, 0.2, size=(N, dim))
                km = HighDKrigingModel(X_obs, q_obs, b_obs)

                for qi, q in enumerate(queries):
                    res = solve_highd_drift_1a_with_envelope(env, km, q, beta_sim=2.6, n_anchors=90, seed=sd + 10 * qi)
                    m = env.simulate_rollouts(res["policy"], q, n_per_start=35, seed=300 + sd)
                    v_lo, v_hi = res["eval_envelope"](eval_pts_by_q[q.name], mc_slack=0.35)
                    v_t = v_true_by_q[q.name]
                    v_m = res["value_fn"](eval_pts_by_q[q.name])
                    costs_s.append(m["mean_cost"]); reaches_s.append(m["reach_rate"])
                    covs_s.append(float(np.mean((v_t >= v_lo) & (v_t <= v_hi))))
                    widths_s.append(float(np.mean(v_hi - v_lo)))
                    maes_s.append(float(np.mean(np.abs(v_m - v_t))))
                    ms_s.append(res["solve_ms"])

            out[f"{dim}D"]["budgets"][str(N)] = {
                "avg_cost": float(np.mean(costs_s)), "avg_reach": float(np.mean(reaches_s)),
                "envelope_coverage": float(np.mean(covs_s)), "envelope_width": float(np.mean(widths_s)),
                "mae_vs_true": float(np.mean(maes_s)), "solve_ms": float(np.mean(ms_s)),
            }
            print(
                f"  N={N:3d} | GreenResidual-1A AvgCost={np.mean(costs_s):5.2f} (Reach={100*np.mean(reaches_s):5.1f}%, {np.mean(ms_s):6.0f}ms) | "
                f"Envelope Coverage={100*np.mean(covs_s):5.1f}%, Width={np.mean(widths_s):.2f}, MAE={np.mean(maes_s):.2f}"
            )
    return out


# ===========================================================================
# TEST 5 (CLOSING HARDEST PART OF LIMITATION 2):
#   4D UNDERACTUATED SECOND-ORDER DOUBLE INTEGRATOR (dp = v dt, dv = (-gamma*v + f_wind + u)dt + sig dW)
# ===========================================================================
@dataclass
class UnderactuatedQuery:
    name: str
    goals: List[Tuple[np.ndarray, float]]   # (goal position p_g (2,), terminal cost phi_j)
    starts: List[np.ndarray]                # 4D start states (px, py, vx, vy) with NON-ZERO initial momentum!


class UnderactuatedDoubleIntegrator4D:
    """
    4D underactuated inertial robot/drone:
      state  x = [px, py, vx, vy] in R^4
      action u = [ax, ay] in R^2  (acceleration ONLY; ZERO direct position control!)
      dp = v dt
      dv = (-gamma * v + f_wind(p) + u) dt + sigma dW_t
    """

    def __init__(self, gamma: float = 0.85, sigma: float = 0.45, q0: float = 0.65, r_goal: float = 0.18):
        self.gamma = gamma
        self.sigma = sigma
        self.q0 = q0
        self.r_goal = r_goal
        # Hidden obstacles in 2D physical space + non-conservative rotational wind force!
        self.hazards = [
            (np.array([0.0, 0.12]), 14.0, 0.25),
            (np.array([0.24, -0.28]), 12.0, 0.22),
            (np.array([-0.38, -0.15]), 11.0, 0.21),
        ]
        # Exact continuous-time LQR for free-space damped double integrator:
        #   A = [[0, 1], [0, -gamma]], B = [[0], [1]], Q_lqr = diag(2.2, 0.35), R_lqr = 1.0
        A1 = np.array([[0.0, 1.0], [0.0, -gamma]])
        B1 = np.array([[0.0], [1.0]])
        Q1 = np.diag([2.2, 0.35])
        R1 = np.array([[1.0]])
        P1 = solve_continuous_are(A1, B1, Q1, R1)
        K1 = B1.T @ P1  # [kp, kv]
        self.P1 = P1
        self.kp = float(K1[0, 0])
        self.kv = float(K1[0, 1])

    def q_hidden(self, P: np.ndarray) -> np.ndarray:
        P = np.atleast_2d(P)
        val = np.zeros(len(P), dtype=float)
        for c, amp, w in self.hazards:
            val += amp * np.exp(-0.5 * np.sum((P - c[None, :]) ** 2, axis=1) / (w ** 2))
        return val

    def f_wind(self, P: np.ndarray) -> np.ndarray:
        P = np.atleast_2d(P)
        r2 = np.sum(P ** 2, axis=1)
        env = np.exp(-0.5 * r2 / (0.55 ** 2))
        return np.stack([-1.2 * P[:, 1] * env, +1.2 * P[:, 0] * env], axis=1)

    def lqr_base_V_and_u(self, X: np.ndarray, query: UnderactuatedQuery) -> Tuple[np.ndarray, np.ndarray]:
        """Exact smooth multi-goal LQR baseline value V_lqr(p,v) and acceleration u_lqr(p,v) = -grad_v V_lqr."""
        X = np.atleast_2d(X)
        p, v = X[:, :2], X[:, 2:]
        sig2 = self.sigma ** 2
        P11, P12, P22 = float(self.P1[0, 0]), float(self.P1[0, 1]), float(self.P1[1, 1])

        Vs, gvs = [], []
        for pg, phi_j in query.goals:
            dp = p - pg[None, :]
            # V_j(p,v) = phi_j + 0.5*(P11 ||dp||^2 + 2*P12 dp.v + P22 ||v||^2)
            Vj = phi_j + 0.5 * (P11 * np.sum(dp ** 2, axis=1) + 2.0 * P12 * np.sum(dp * v, axis=1) + P22 * np.sum(v ** 2, axis=1))
            gvj = P12 * dp + P22 * v  # grad_v V_j
            Vs.append(Vj)
            gvs.append(gvj)

        if len(Vs) == 1:
            return Vs[0], -gvs[0]

        V_stack = np.stack(Vs, axis=1)     # (N, K)
        gv_stack = np.stack(gvs, axis=1)   # (N, K, 2)
        # Soft-min composition in Cole-Hopf space!
        log_w = -V_stack / sig2
        lse = logsumexp(log_w, axis=1, keepdims=True)
        w = np.exp(log_w - lse)            # (N, K)
        V_soft = -sig2 * lse[:, 0]
        gv_soft = np.sum(w[:, :, None] * gv_stack, axis=1)
        return V_soft, -gv_soft

    def simulate_rollouts(
        self, policy_fn, query: UnderactuatedQuery, n_per_start: int = 35,
        dt: float = 0.02, max_steps: int = 320, u_clip: float = 6.5, seed: int = 0,
    ) -> dict:
        rng = np.random.default_rng(seed)
        starts = np.repeat(np.asarray(query.starts, dtype=float), n_per_start, axis=0)
        x = starts.copy()  # (N, 4)
        alive = np.ones(len(x), dtype=bool)
        reached = np.zeros(len(x), dtype=bool)
        total_cost = np.zeros(len(x), dtype=float)
        hazard_cost = np.zeros(len(x), dtype=float)
        sqrt_dt = np.sqrt(dt)
        g_centers = np.array([g[0] for g in query.goals], dtype=float)
        g_phis = np.array([g[1] for g in query.goals], dtype=float)

        for _ in range(max_steps):
            if not np.any(alive): break
            idx = np.where(alive)[0]
            xa = x[idx]
            pa, va = xa[:, :2], xa[:, 2:]
            dists = np.linalg.norm(pa[:, None, :] - g_centers[None, :, :], axis=2)
            mi = np.argmin(dists, axis=1)
            hit = dists[np.arange(len(idx)), mi] <= self.r_goal
            if np.any(hit):
                hg = idx[hit]
                # Terminal cost includes goal phi + small residual kinetic energy
                total_cost[hg] += g_phis[mi[hit]] + 0.15 * np.sum(va[hit] ** 2, axis=1)
                reached[hg] = True; alive[hg] = False
                idx = np.where(alive)[0]
                if len(idx) == 0: break
                xa = x[idx]; pa, va = xa[:, :2], xa[:, 2:]

            u = np.asarray(policy_fn(xa), dtype=float)  # (Na, 2) acceleration ONLY!
            un = np.linalg.norm(u, axis=1, keepdims=True)
            u = np.where(un > u_clip, u * (u_clip / np.maximum(un, 1e-12)), u)

            qh = self.q_hidden(pa)
            hazard_cost[idx] += qh * dt
            total_cost[idx] += (self.q0 + qh + 0.5 * np.sum(u ** 2, axis=1)) * dt

            fw = self.f_wind(pa)
            p_next = np.clip(pa + va * dt, -1.65, 1.65)
            v_next = np.clip(va + (-self.gamma * va + fw + u) * dt + self.sigma * sqrt_dt * rng.normal(size=va.shape), -3.5, 3.5)
            x[idx, :2] = p_next
            x[idx, 2:] = v_next

        if np.any(alive):
            xa = x[alive]
            d_min = np.min(np.linalg.norm(xa[:, None, :2] - g_centers[None, :, :], axis=2), axis=1)
            total_cost[alive] += 2.5 * d_min + 3.0

        return {
            "mean_cost": float(np.mean(total_cost)),
            "mean_hazard": float(np.mean(hazard_cost)),
            "reach_rate": float(np.mean(reached)),
        }


def solve_underactuated_1a(
    env: UnderactuatedDoubleIntegrator4D,
    q_fn: Callable[[np.ndarray], np.ndarray],
    wind_fn: Callable[[np.ndarray], np.ndarray],
    query: UnderactuatedQuery,
    n_anchors: int = 110,
    n_fk_paths: int = 64,
    fk_steps: int = 55,
    dt_fk: float = 0.045,
    seed: int = 0,
) -> dict:
    """
    Hypoelliptic Cole-Hopf GreenResidual-1A for 4D underactuated double integrator:
      V*(p,v) = V_LQR(p,v) + Delta_V(p,v),
      u*(p,v) = u_LQR(p,v) - grad_v Delta_V_hat(p,v)  [gradient ONLY w.r.t. velocity v!].
    Computes exact Girsanov path-integral V*(p,v) along LQR-guided 4D trajectories inside
    the learned 2D Kriging environment (q_hat, f_wind_hat), then fits a 4D Matérn-5/2 GP
    residual on Delta_V(p,v) = V*(p,v) - V_LQR(p,v).
    """
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    sig2 = env.sigma ** 2
    g_centers = np.array([g[0] for g in query.goals], dtype=float)
    g_phis = np.array([g[1] for g in query.goals], dtype=float)

    # 1. Generate 4D phase-space anchors (p, v) along LQR corridor tubes + random phase states
    anchors = []
    for st in query.starts:
        # Simulate 4 noisy LQR-guided trajectories to populate reachable phase-space tube
        for _ in range(4):
            x = st.copy()
            for step in range(32):
                anchors.append(x + np.concatenate([rng.normal(0, 0.25, 2), rng.normal(0, 0.45, 2)]))
                _, u = env.lqr_base_V_and_u(x[None, :], query)
                p_n = np.clip(x[:2] + x[2:] * 0.06, -1.25, 1.25)
                v_n = np.clip(x[2:] + (-env.gamma * x[2:] + u[0]) * 0.06 + rng.normal(0, 0.2, 2), -2.2, 2.2)
                x = np.concatenate([p_n, v_n])
                if np.min(np.linalg.norm(p_n[None, :] - g_centers, axis=1)) <= env.r_goal:
                    break
    X_int = np.asarray(anchors, dtype=float)
    mask = np.ones(len(X_int), dtype=bool)
    for gc, _ in query.goals:
        mask &= np.linalg.norm(X_int[:, :2] - gc[None, :], axis=1) > env.r_goal + 0.04
    X_int = X_int[mask]
    if len(X_int) > n_anchors:
        X_int = X_int[rng.choice(len(X_int), n_anchors, replace=False)]

    # Exact goal boundary anchors where Delta_V = 0 (at goals with low velocity)
    bc = []
    for gc, _ in query.goals:
        for _ in range(10):
            ang = rng.uniform(0, 2 * np.pi)
            p_b = gc + env.r_goal * np.array([np.cos(ang), np.sin(ang)])
            v_b = rng.normal(0, 0.4, size=2)
            bc.append(np.concatenate([p_b, v_b]))
    X_bc = np.asarray(bc, dtype=float)

    # 2. Exact Hypoelliptic Girsanov Path-Integral evaluation of V*(p, v) under u_guide = u_LQR
    M = len(X_int)
    pos = np.repeat(X_int[:, None, :2], n_fk_paths, axis=1)  # (M, K, 2)
    vel = np.repeat(X_int[:, None, 2:], n_fk_paths, axis=1)  # (M, K, 2)
    acc = np.zeros((M, n_fk_paths), dtype=float)
    alive = np.ones((M, n_fk_paths), dtype=bool)
    sqrt_dt = np.sqrt(dt_fk)

    for _ in range(fk_steps):
        if not np.any(alive): break
        ai, aj = np.where(alive)
        pa = pos[ai, aj]
        va = vel[ai, aj]
        xa = np.hstack([pa, va])
        _, ug = env.lqr_base_V_and_u(xa, query)
        un = np.linalg.norm(ug, axis=1, keepdims=True)
        ug = np.where(un > 5.5, ug * (5.5 / np.maximum(un, 1e-12)), ug)

        qh = np.maximum(0.0, np.asarray(q_fn(pa), dtype=float))
        fw = np.asarray(wind_fn(pa), dtype=float)
        dW = rng.normal(size=va.shape) * sqrt_dt

        # Exact Girsanov path exponent for hypoelliptic SDE:
        #   int (q0 + q_hid + 0.5 ||u_g||^2) dt + sigma * int (u_g . dW)
        step_exp = (env.q0 + qh + 0.5 * np.sum(ug ** 2, axis=1)) * dt_fk + env.sigma * np.sum(ug * dW, axis=1)
        acc[ai, aj] += step_exp

        p_next = pa + va * dt_fk
        v_next = np.clip(va + (-env.gamma * va + fw + ug) * dt_fk + env.sigma * dW, -3.5, 3.5)
        pos[ai, aj] = p_next
        vel[ai, aj] = v_next

        dists = np.linalg.norm(p_next[:, None, :] - g_centers[None, :, :], axis=2)
        mi = np.argmin(dists, axis=1)
        hit = dists[np.arange(len(ai)), mi] <= env.r_goal
        if np.any(hit):
            acc[ai[hit], aj[hit]] += g_phis[mi[hit]] + 0.15 * np.sum(v_next[hit] ** 2, axis=1)
            alive[ai[hit], aj[hit]] = False

    # Terminal LQR anchor for any particles still in flight
    if np.any(alive):
        ai, aj = np.where(alive)
        V_rem, _ = env.lqr_base_V_and_u(np.hstack([pos[ai, aj], vel[ai, aj]]), query)
        acc[ai, aj] += V_rem

    V_fk = -sig2 * (logsumexp(-acc / sig2, axis=1) - np.log(n_fk_paths))
    V_lqr_int, _ = env.lqr_base_V_and_u(X_int, query)
    dV_int = V_fk - V_lqr_int

    X_fit = np.vstack([X_int, X_bc])
    y_fit = np.concatenate([dV_int, np.zeros(len(X_bc))])

    # 3. Fit anisotropic 4D Matérn-5/2 GP residual (separate length scales for p vs v!)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        k_res = (
            ConstantKernel(2.5, (0.05, 60.0))
            * Matern(length_scale=[0.45, 0.45, 0.90, 0.90], length_scale_bounds=(0.18, 3.0), nu=2.5)
            + WhiteKernel(noise_level=0.08, noise_level_bounds=(1e-4, 2.0))
        )
        gp_res = GaussianProcessRegressor(kernel=k_res, n_restarts_optimizer=1, normalize_y=False, random_state=seed).fit(X_fit, y_fit)

    solve_ms = (time.perf_counter() - t0) * 1000.0
    X_tr = gp_res.X_train_
    alpha_gp = gp_res.alpha_
    c_var = float(gp_res.kernel_.k1.k1.constant_value)
    ells = np.asarray(gp_res.kernel_.k1.k2.length_scale, dtype=float)  # (4,)
    s5 = np.sqrt(5.0)

    def policy(X: np.ndarray) -> np.ndarray:
        """Closed-form underactuated acceleration u*(p,v) = u_LQR(p,v) - grad_v Delta_V(p,v)!"""
        X = np.atleast_2d(X)
        _, u_lqr = env.lqr_base_V_and_u(X, query)
        diff = X[:, None, :] - X_tr[None, :, :]          # (N, M, 4)
        scaled = diff / ells[None, None, :]              # (N, M, 4)
        r = np.sqrt(np.sum(scaled ** 2, axis=2) + 1e-18) # (N, M)
        sr = s5 * r
        coeff = -(5.0 / 3.0) * c_var * (1.0 + sr) * np.exp(-sr)  # (N, M)
        # Derivative ONLY w.r.t. velocity dims (2, 3)!
        diff_v = diff[:, :, 2:] / (ells[2:] ** 2)[None, None, :]
        grad_v_dV = np.einsum("nm,nmd->nd", coeff * alpha_gp[None, :], diff_v)
        return u_lqr - grad_v_dV

    return {"policy": policy, "solve_ms": solve_ms}


def make_underactuated_pimc_oracle(env: UnderactuatedDoubleIntegrator4D, query: UnderactuatedQuery, n_rollouts: int = 80, H: int = 26, dt_p: float = 0.045):
    sig2 = env.sigma ** 2
    g_centers = np.array([g[0] for g in query.goals], dtype=float)
    g_phis = np.array([g[1] for g in query.goals], dtype=float)
    rng = np.random.default_rng(777)

    def policy(X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        N = len(X)
        _, u_base = env.lqr_base_V_and_u(X, query)
        eps0 = rng.normal(0.0, env.sigma / np.sqrt(dt_p), size=(N, n_rollouts, 2))
        pos = np.repeat(X[:, None, :2], n_rollouts, axis=1)
        vel = np.repeat(X[:, None, 2:], n_rollouts, axis=1)
        cost = np.zeros((N, n_rollouts), dtype=float)
        done = np.zeros((N, n_rollouts), dtype=bool)

        for t in range(H):
            nt = eps0 if t == 0 else rng.normal(0.0, env.sigma / np.sqrt(dt_p), size=(N, n_rollouts, 2))
            _, un = env.lqr_base_V_and_u(np.concatenate([pos, vel], axis=2).reshape(-1, 4), query)
            un = un.reshape(N, n_rollouts, 2)
            qh = env.q_hidden(pos.reshape(-1, 2)).reshape(N, n_rollouts)
            fw = env.f_wind(pos.reshape(-1, 2)).reshape(N, n_rollouts, 2)
            step_c = (env.q0 + qh + 0.5 * np.sum(un ** 2, axis=2) + np.sum(un * nt, axis=2)) * dt_p
            cost += np.where(done, 0.0, step_c)
            p_n = pos + vel * dt_p
            v_n = np.clip(vel + (-env.gamma * vel + fw + un + nt) * dt_p, -3.5, 3.5)
            pos = np.where(done[:, :, None], pos, p_n)
            vel = np.where(done[:, :, None], vel, v_n)
            dists = np.linalg.norm(pos[:, :, None, :] - g_centers[None, None, :, :], axis=3)
            mi = np.argmin(dists, axis=2)
            md = np.take_along_axis(dists, mi[:, :, None], axis=2)[:, :, 0]
            hit = (~done) & (md <= env.r_goal)
            if np.any(hit):
                cost += np.where(hit, g_phis[mi] + 0.15 * np.sum(vel ** 2, axis=2), 0.0)
                done |= hit

        Vt, _ = env.lqr_base_V_and_u(np.concatenate([pos, vel], axis=2).reshape(-1, 4), query)
        cost += np.where(done, 0.0, Vt.reshape(N, n_rollouts))
        lw = -cost / sig2
        w = np.exp(lw - logsumexp(lw, axis=1, keepdims=True))
        return u_base + np.sum(w[:, :, None] * eps0, axis=1)

    return policy


class _MLP4D(nn.Module):
    def __init__(self, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(4, hidden), nn.Tanh(), nn.Linear(hidden, hidden), nn.Tanh(), nn.Linear(hidden, hidden), nn.Tanh(), nn.Linear(hidden, 1))
    def forward(self, x): return self.net(x).squeeze(-1)


def fit_hypoelliptic_pinn_4d(env: UnderactuatedDoubleIntegrator4D, q_fn, wind_fn, query: UnderactuatedQuery, epochs: int = 320, seed: int = 0) -> dict:
    """4D PyTorch PINN solving the hypoelliptic underactuated HJB PDE."""
    t0 = time.perf_counter()
    torch.manual_seed(seed); rng = np.random.default_rng(seed)
    P_c = rng.uniform(-1.2, 1.2, size=(360, 2))
    V_c = rng.uniform(-1.6, 1.6, size=(360, 2))
    X_col_np = np.hstack([P_c, V_c])
    q_col = torch.tensor(env.q0 + np.maximum(0.0, q_fn(P_c)), dtype=torch.float32)
    fw_col = torch.tensor(wind_fn(P_c), dtype=torch.float32)

    bc_x, bc_y = [], []
    for gc, phi_j in query.goals:
        ang = rng.uniform(0, 2*np.pi, size=32)
        pb = gc[None, :] + env.r_goal * np.stack([np.cos(ang), np.sin(ang)], axis=1)
        vb = rng.normal(0, 0.5, size=(32, 2))
        bc_x.append(np.hstack([pb, vb]))
        bc_y.append(phi_j + 0.15 * np.sum(vb ** 2, axis=1))
    X_bc = torch.tensor(np.vstack(bc_x), dtype=torch.float32)
    V_bc = torch.tensor(np.concatenate(bc_y), dtype=torch.float32)

    X_far_np = np.hstack([rng.uniform(-1.4, 1.4, size=(48, 2)), rng.uniform(-1.5, 1.5, size=(48, 2))])
    V_far_np, _ = env.lqr_base_V_and_u(X_far_np, query)
    X_far = torch.tensor(X_far_np, dtype=torch.float32)
    V_far = torch.tensor(V_far_np, dtype=torch.float32)

    X_col = torch.tensor(X_col_np, dtype=torch.float32, requires_grad=True)
    model = _MLP4D(64)
    opt = torch.optim.Adam(model.parameters(), lr=4e-3)
    sig2 = float(env.sigma ** 2)

    for _ in range(epochs):
        opt.zero_grad()
        V = model(X_col)
        g = torch.autograd.grad(V.sum(), X_col, create_graph=True)[0]  # [gp_x, gp_y, gv_x, gv_y]
        gp, gv = g[:, :2], g[:, 2:]
        d2vx = torch.autograd.grad(gv[:, 0].sum(), X_col, create_graph=True)[0][:, 2]
        d2vy = torch.autograd.grad(gv[:, 1].sum(), X_col, create_graph=True)[0][:, 3]
        v_in = X_col[:, 2:]
        # Exact hypoelliptic HJB: q - 0.5||gv||^2 + v.gp + (-gamma*v + f_wind).gv + 0.5*sig2*(d2vx + d2vy) = 0
        res = q_col - 0.5 * torch.sum(gv ** 2, dim=1) + torch.sum(v_in * gp, dim=1) + torch.sum((-env.gamma * v_in + fw_col) * gv, dim=1) + 0.5 * sig2 * (d2vx + d2vy)
        loss = torch.mean(res ** 2) + 20.0 * torch.mean((model(X_bc) - V_bc) ** 2) + 0.5 * torch.mean((model(X_far) - V_far) ** 2)
        loss.backward(); opt.step()

    ms = (time.perf_counter() - t0) * 1000.0
    model.eval()
    def pol(X):
        xt = torch.tensor(np.atleast_2d(X), dtype=torch.float32, requires_grad=True)
        g = torch.autograd.grad(model(xt).sum(), xt)[0]
        return (-g[:, 2:]).detach().numpy()
    return {"policy": pol, "solve_ms": ms}


def run_test_5_underactuated_4d():
    print(f"\n{'='*90}\nTEST 5 (CLOSING LIMITATION 2) — 4D UNDERACTUATED SECOND-ORDER DOUBLE INTEGRATOR (rank-2 B)\n{'='*90}")
    env = UnderactuatedDoubleIntegrator4D(gamma=0.85, sigma=0.45, q0=0.65, r_goal=0.18)
    # Non-zero initial velocities aiming straight toward the hidden hazards (must brake & bank!)
    queries = [
        UnderactuatedQuery("Q1_seen", [(np.array([0.78, 0.72]), 0.0)], [
            np.array([-0.75, -0.65, +0.9, +0.8]),   # flying straight toward center hazard!
            np.array([-0.75, 0.25, +1.0, +0.2]),
            np.array([0.70, -0.70, -0.4, +0.9]),
        ]),
        UnderactuatedQuery("Q2_unseen", [(np.array([-0.72, 0.75]), 0.0)], [
            np.array([0.72, -0.65, -0.9, +0.8]),
            np.array([0.75, 0.30, -1.0, +0.2]),
            np.array([-0.68, -0.70, +0.4, +0.9]),
        ]),
        UnderactuatedQuery("Q3_multigoal", [(np.array([0.78, 0.72]), 0.0), (np.array([-0.72, 0.75]), 0.12)], [
            np.array([0.0, -0.78, 0.0, +1.1]),      # launching straight into center hazard!
            np.array([-0.45, -0.70, +0.4, +0.9]),
            np.array([0.48, -0.70, -0.4, +0.9]),
        ]),
    ]

    # Reference baselines (true env)
    print("--- TRUE-ENV REFERENCES ---")
    ref = {}
    for lbl, kind in [("Online-PIMC (True 4D Inertial)", "pimc"), ("Exact-Underactuated-1A (True q,wind)", "ex"), ("Free-Space LQR (Ignores q,wind)", "lqr")]:
        cs, hs, rs, ts = [], [], [], []
        for qi, q in enumerate(queries):
            if kind == "pimc":
                pol = make_underactuated_pimc_oracle(env, q)
                t0 = time.perf_counter()
                m = env.simulate_rollouts(pol, q, n_per_start=20, seed=100)
                ms = (time.perf_counter() - t0) * 1000.0
            elif kind == "ex":
                r = solve_underactuated_1a(env, env.q_hidden, env.f_wind, q, seed=42 + qi)
                ms = r["solve_ms"]
                m = env.simulate_rollouts(r["policy"], q, n_per_start=40, seed=100)
            else:
                ms = 0.1
                m = env.simulate_rollouts(lambda X, _q=q: env.lqr_base_V_and_u(X, _q)[1], q, n_per_start=40, seed=100)
            cs.append(m["mean_cost"]); hs.append(m["mean_hazard"]); rs.append(m["reach_rate"]); ts.append(ms)
        ref[lbl] = {"avg_cost": float(np.mean(cs)), "per_q": cs, "avg_haz": float(np.mean(hs)), "avg_reach": float(np.mean(rs)), "avg_ms": float(np.mean(ts))}
        print(f"  {lbl:38s} | Q1={cs[0]:5.2f} Q2={cs[1]:5.2f} Q3={cs[2]:5.2f} | Avg={np.mean(cs):5.2f} (Reach={100*np.mean(rs):5.1f}%, haz={np.mean(hs):.2f}, t={np.mean(ts):6.0f}ms)")

    # Learned from ONLY N=35 noisy 2D physical-space probes (for both q_hid and f_wind!)
    print("--- LEARNED FROM ONLY N=35 NOISY 2D PROBES (2 seeds) ---")
    agg = {m: {q.name: {"cost": [], "haz": [], "reach": [], "ms": []} for q in queries} for m in ["4D Hypoelliptic PINN-HJB (retrained)", "Underactuated GreenRes-1A (Ours)"]}
    vis_pol = None
    vis_X = None

    for sd in (0, 1):
        rng = np.random.default_rng(7700 + 31 * sd)
        X_obs = rng.uniform(-1.05, 1.05, size=(35, 2))
        q_obs = np.maximum(0.0, env.q_hidden(X_obs) + rng.normal(0.0, 0.5, size=35))
        w_obs = env.f_wind(X_obs) + rng.normal(0.0, 0.2, size=(35, 2))
        km = HighDKrigingModel(X_obs, q_obs, w_obs)
        qf = lambda P, _k=km: np.maximum(0.0, _k.predict_q(P)[0])
        wf = lambda P, _k=km: _k.predict_b(P)[0]

        for qi, q in enumerate(queries):
            pinn = fit_hypoelliptic_pinn_4d(env, qf, wf, q, epochs=320, seed=sd + 10 * qi)
            mp = env.simulate_rollouts(pinn["policy"], q, n_per_start=35, seed=300 + sd)
            agg["4D Hypoelliptic PINN-HJB (retrained)"][q.name]["cost"].append(mp["mean_cost"])
            agg["4D Hypoelliptic PINN-HJB (retrained)"][q.name]["haz"].append(mp["mean_hazard"])
            agg["4D Hypoelliptic PINN-HJB (retrained)"][q.name]["reach"].append(mp["reach_rate"])
            agg["4D Hypoelliptic PINN-HJB (retrained)"][q.name]["ms"].append(pinn["solve_ms"])

            gr = solve_underactuated_1a(env, qf, wf, q, seed=100 + sd + 10 * qi)
            mg = env.simulate_rollouts(gr["policy"], q, n_per_start=35, seed=300 + sd)
            agg["Underactuated GreenRes-1A (Ours)"][q.name]["cost"].append(mg["mean_cost"])
            agg["Underactuated GreenRes-1A (Ours)"][q.name]["haz"].append(mg["mean_hazard"])
            agg["Underactuated GreenRes-1A (Ours)"][q.name]["reach"].append(mg["reach_rate"])
            agg["Underactuated GreenRes-1A (Ours)"][q.name]["ms"].append(gr["solve_ms"])
            if sd == 0 and qi == 2:
                vis_pol = gr["policy"]; vis_X = X_obs

    learned_out = {}
    for m_name, qd in agg.items():
        cs = [float(np.mean(qd[q.name]["cost"])) for q in queries]
        hs = [float(np.mean(qd[q.name]["haz"])) for q in queries]
        rs = [float(np.mean(qd[q.name]["reach"])) for q in queries]
        ms = [float(np.mean(qd[q.name]["ms"])) for q in queries]
        learned_out[m_name] = {"per_q": cs, "avg_cost": float(np.mean(cs)), "avg_haz": float(np.mean(hs)), "avg_reach": float(np.mean(rs)), "avg_ms": float(np.mean(ms))}
        print(f"  {m_name:38s} | Q1={cs[0]:5.2f} Q2={cs[1]:5.2f} Q3={cs[2]:5.2f} | Avg={np.mean(cs):5.2f} (Reach={100*np.mean(rs):5.1f}%, haz={np.mean(hs):.2f}, t={np.mean(ms):6.0f}ms)")

    # Plot 4D underactuated braking & banking trajectories on unseen Q3 multi-goal!
    if vis_pol is not None:
        out_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "underactuated_4d_multigoal.png")
        fig, ax = plt.subplots(figsize=(6.0, 5.4), dpi=130)
        gx = np.linspace(-1.1, 1.1, 65); XX, YY = np.meshgrid(gx, gx, indexing="ij")
        pts2 = np.stack([XX.ravel(), YY.ravel()], axis=1)
        ax.contourf(XX, YY, env.q_hidden(pts2).reshape(XX.shape), levels=18, cmap="Reds", alpha=0.78)
        # Wind quiver
        qgx = np.linspace(-1.0, 1.0, 11); QX, QY = np.meshgrid(qgx, qgx, indexing="ij")
        fw_q = env.f_wind(np.stack([QX.ravel(), QY.ravel()], axis=1)).reshape(11, 11, 2)
        ax.quiver(QX, QY, fw_q[:, :, 0], fw_q[:, :, 1], color="navy", alpha=0.35, scale=18)
        q3 = queries[2]
        for gc, _ in q3.goals:
            ax.add_patch(plt.Circle(gc, env.r_goal, facecolor="none", edgecolor="lime", lw=2.2, zorder=6))
            ax.scatter([gc[0]], [gc[1]], c="green", s=70, marker="*", zorder=7)
        ax.scatter(vis_X[:, 0], vis_X[:, 1], c="black", s=16, marker="x", alpha=0.65, label="N=35 2D probes", zorder=5)
        for st in q3.starts:
            # Show initial velocity vector!
            ax.arrow(st[0], st[1], 0.18*st[2], 0.18*st[3], head_width=0.04, color="gold", zorder=9)
            for p_fn, col, ls_s, lbl in [
                (lambda X: env.lqr_base_V_and_u(X, q3)[1], "gray", "--", "Free-Space LQR (Ignores Hazards)"),
                (vis_pol, "cyan", "-", "Underactuated 1A (N=35, Zero-Shot)"),
            ]:
                x = st.copy(); path = [x[:2].copy()]
                for _ in range(280):
                    if min(np.linalg.norm(x[:2] - gc) for gc, _ in q3.goals) <= env.r_goal: break
                    u = p_fn(x[None, :])[0]; un = np.linalg.norm(u)
                    if un > 6.5: u = u * (6.5 / un)
                    pn = np.clip(x[:2] + x[2:] * 0.02, -1.3, 1.3)
                    vn = np.clip(x[2:] + (-env.gamma * x[2:] + env.f_wind(x[:2][None, :])[0] + u) * 0.02, -3.5, 3.5)
                    x = np.concatenate([pn, vn]); path.append(pn.copy())
                P = np.array(path)
                ax.plot(P[:, 0], P[:, 1], color=col, linestyle=ls_s, lw=2.3, label=lbl if np.allclose(st, q3.starts[0]) else None)
        ax.set_xlim(-1.1, 1.1); ax.set_ylim(-1.1, 1.1)
        ax.set_title("4D Underactuated Inertial Robot (Unseen Q3 Multi-Goal)\nYellow arrows = initial velocity aimed at hazards")
        ax.legend(loc="lower right", fontsize=8); plt.tight_layout()
        plt.savefig(out_png); plt.close(fig)
        print(f"Saved 4D underactuated plot to {out_png}")

    return {"reference": ref, "learned": learned_out}


if __name__ == "__main__":
    t0 = time.perf_counter()
    res4 = run_test_4_highd_drift_and_envelope()
    res5 = run_test_5_underactuated_4d()
    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, "test4_test5_results.json"), "w", encoding="utf-8") as f:
        json.dump({"test4_highd_drift_envelope": res4, "test5_underactuated_4d": res5}, f, indent=2)
    print(f"\nTests 4 & 5 completed in {time.perf_counter() - t0:.1f}s.")
