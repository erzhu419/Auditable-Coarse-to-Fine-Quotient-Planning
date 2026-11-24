"""4D / 6D & Underactuated Unified Base-Green + Exact Residual + Continuation FK Distillation
and Strong Same-GP Online PIMC Baselines (v2).

Fixes all high-dimensional issues identified in the v1 audit:
1. Capacitary multi-goal collocation weights for analytical d-D Bessel Green base V0(x),
   plus exact boundary residual anchors `DeltaV(x_Gamma) = phi_actual(x_Gamma) - V0(x_Gamma)`.
2. Unified exact PDE residual formula `r0(x)` for arbitrary smooth base guide V0(x)
   (covering both isotropic 4D/6D and 4D underactuated inertial double integrator).
3. Two-pass continuation bootstrap `DeltaV_boot(X_T)` for paths surviving past horizon T,
   with explicit logging of `survivor_fraction` and `mean_ess`.
4. Apples-to-apples comparison against `Same-GP + Unguided-PIMC` and `Same-GP + BaseGuided-PIMC`
   with full wall-clock breakdown (`gp_fit_ms + plan_ms + rollout_ms`).
"""
from __future__ import annotations

import time
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np
from scipy.linalg import solve_continuous_are, cho_factor, cho_solve
from scipy.optimize import nnls
from scipy.special import kv
from scipy.stats import qmc

from core_spec_and_gp import (
    GoalBall,
    HazardBump,
    KrigingWorldModel,
    ProblemSpec,
    QueryTask,
    eval_bumps,
    reflect_into_box,
)


class AnalyticMatern52ResidualGP:
    """Fast exact Matérn-5/2 GP with closed-form analytic value and gradient evaluation."""

    def __init__(self, X: np.ndarray, y: np.ndarray, length_scale: float = 0.55, noise: float = 1e-3):
        self.X = np.atleast_2d(np.asarray(X, dtype=float))
        self.y = np.asarray(y, dtype=float)
        self.y_mean = float(np.mean(self.y))
        yc = self.y - self.y_mean
        self.y_scale = float(max(np.std(yc), 1e-6))
        yn = yc / self.y_scale
        self.ell = float(length_scale)

        diff = self.X[:, None, :] - self.X[None, :, :]
        r = np.linalg.norm(diff, axis=2)
        s = np.sqrt(5.0) * r / self.ell
        K = (1.0 + s + (s ** 2) / 3.0) * np.exp(-s)
        K[np.diag_indices_from(K)] += noise
        c, low = cho_factor(K, lower=True)
        self.alpha = cho_solve((c, low), yn) * self.y_scale

    def predict_val_and_grad(self, Xq: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        Xq = np.atleast_2d(np.asarray(Xq, dtype=float))
        # diff: (Nq, Ntrain, d) = Xq[:, None, :] - X[None, :, :]
        diff = Xq[:, None, :] - self.X[None, :, :]
        r = np.linalg.norm(diff, axis=2)
        s = np.sqrt(5.0) * r / self.ell
        exp_s = np.exp(-s)
        k_mat = (1.0 + s + (s ** 2) / 3.0) * exp_s
        val = self.y_mean + k_mat @ self.alpha

        # Exact derivative of Matern-5/2 wrt Xq:
        # dk/dr = -(5 r / (3 ell^2)) * (1 + s) * exp(-s)  => (1/r) dk/dr = -(5 / (3 ell^2)) (1 + s) exp(-s)
        coeff = -(5.0 / (3.0 * self.ell ** 2)) * (1.0 + s) * exp_s
        weighted = coeff * self.alpha[None, :]  # (Nq, Ntrain)
        grad = np.einsum("ij,ijd->id", weighted, diff)
        return val, grad


class CapacitaryBesselBaseGuide:
    """Analytical d-D free-space Cole-Hopf Green base V0(x) = -lam * log Z0(x)
    with capacitary boundary collocation weights c_j >= 0 so nearby goals do not corrupt
    each other's Dirichlet terminal values.
    Since each radial mode satisfies 0.5*sigma^2 Lap psi_j - (q0/lam) psi_j = 0 identically,
    Z0 = sum_j c_j psi_j ALSO satisfies the exact free-space interior PDE with zero residual!
    """

    def __init__(self, spec: ProblemSpec, query: QueryTask):
        self.spec = spec
        self.query = query
        self.d = spec.dim
        self.nu = 0.5 * self.d - 1.0
        self.kappa = np.sqrt(2.0 * spec.q0) / (spec.sigma ** 2)
        self.g_centers = np.array([g.center for g in query.goals], dtype=float)
        self.g_phis = np.array([g.phi for g in query.goals], dtype=float)
        self.g_radii = np.array([g.radius for g in query.goals], dtype=float)
        self.base_denom = kv(self.nu, self.kappa * self.g_radii)

        # Solve capacitary collocation weights c_j >= 0 on spherical boundary points
        m_g = len(query.goals)
        if m_g == 1:
            self.weights = np.array([np.exp(-self.g_phis[0] / spec.lam)], dtype=float)
        else:
            rng = np.random.default_rng(17)
            coll_pts = []
            coll_rhs = []
            n_per_goal = 24
            for j in range(m_g):
                dirs = rng.normal(size=(n_per_goal, self.d))
                dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
                pts_j = self.g_centers[j][None, :] + self.g_radii[j] * dirs
                coll_pts.append(pts_j)
                coll_rhs.append(np.full(n_per_goal, np.exp(-self.g_phis[j] / spec.lam)))
            P_coll = np.vstack(coll_pts)
            w_coll = np.concatenate(coll_rhs)
            Psi_coll, _ = self._eval_modes_and_grads(P_coll)
            c_nnls, _ = nnls(Psi_coll, w_coll)
            if np.all(c_nnls <= 1e-14):
                c_nnls = np.exp(-self.g_phis / spec.lam)
            self.weights = np.maximum(c_nnls, 1e-12)

    def _eval_modes_and_grads(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        X = np.atleast_2d(X)
        n_pts = len(X)
        m_g = len(self.g_centers)
        Psi = np.empty((n_pts, m_g), dtype=float)
        dPsi = np.empty((n_pts, m_g, self.d), dtype=float)

        for j in range(m_g):
            diff = X - self.g_centers[j][None, :]
            r = np.linalg.norm(diff, axis=1)
            r_eff = np.maximum(r, self.g_radii[j])
            kr = self.kappa * r_eff
            kv_nu = kv(self.nu, kr)
            kv_nu1 = kv(self.nu + 1.0, kr)
            ratio_r = (r_eff / self.g_radii[j]) ** (-self.nu)
            psi_j = ratio_r * (kv_nu / self.base_denom[j])
            Psi[:, j] = psi_j

            # Exact radial derivative of r^{-nu} K_nu(kappa r) is -kappa * r^{-nu} K_{nu+1}(kappa r)!
            dpsi_dr = -self.kappa * ratio_r * (kv_nu1 / self.base_denom[j])
            outside = (r > self.g_radii[j] + 1e-12)[:, None]
            unit_vec = diff / np.maximum(r[:, None], 1e-12)
            dPsi[:, j, :] = np.where(outside, dpsi_dr[:, None] * unit_vec, 0.0)

        return Psi, dPsi

    def val_and_grad(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        X = np.atleast_2d(X)
        Psi, dPsi = self._eval_modes_and_grads(X)
        Z0 = np.maximum(Psi @ self.weights, 1e-300)
        grad_Z0 = np.einsum("nmd,m->nd", dPsi, self.weights)
        V0 = -self.spec.lam * np.log(Z0)
        grad_V0 = -self.spec.lam * (grad_Z0 / Z0[:, None])
        return V0, grad_V0

    def residual_r0(self, X: np.ndarray, q_hid_vec: np.ndarray, b_mat: np.ndarray, dyn_haz_vec: np.ndarray) -> np.ndarray:
        """Exact PDE residual of V0:
        Since 0.5*sig^2 Lap V0 - 0.5*||grad V0||^2 + q0 == 0 identically outside goals,
        r0(x) = q_hid(x) + q_dyn(x) + b(x) . grad V0(x)  (= q_pert - b . u0).
        """
        _, grad_V0 = self.val_and_grad(X)
        return q_hid_vec + dyn_haz_vec + np.sum(b_mat * grad_V0, axis=1)


def solve_unified_highd_green_residual(
    spec: ProblemSpec,
    km: KrigingWorldModel,
    query: QueryTask,
    n_interior_anchors: int = 88,
    n_boundary_per_goal: int = 18,
    n_mc_paths: int = 64,
    n_steps_fk: int = 75,
    dt_fk: float = 0.045,
    seed: int = 101,
) -> dict:
    """Unified Base-Green + Exact Residual r0 + Boundary Collocation + 2-Pass Continuation FK."""
    t0 = time.perf_counter()
    d = spec.dim
    lam = spec.lam
    L = spec.half_width
    base = CapacitaryBesselBaseGuide(spec, query)

    rng = np.random.default_rng(seed)
    g_centers = np.array([g.center for g in query.goals], dtype=float)
    g_phis = np.array([g.phi for g in query.goals], dtype=float)
    g_radii = np.array([g.radius for g in query.goals], dtype=float)

    # 1. Exact boundary anchors: DeltaV_Gamma = phi_actual - V0(x_Gamma)
    bnd_pts = []
    bnd_vals = []
    for j in range(len(query.goals)):
        dirs = rng.normal(size=(n_boundary_per_goal, d))
        dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
        pj = np.clip(g_centers[j][None, :] + g_radii[j] * dirs, -L + 0.02, L - 0.02)
        v0_j, _ = base.val_and_grad(pj)
        bnd_pts.append(pj)
        bnd_vals.append(np.full(len(pj), g_phis[j]) - v0_j)
    X_bnd = np.vstack(bnd_pts)
    y_bnd = np.concatenate(bnd_vals)

    # 2. Task-corridor + Sobol interior anchors (outside goals)
    sobol = qmc.Sobol(d=d, scramble=True, seed=seed)
    n_sob = n_interior_anchors // 2
    X_sob = (sobol.random(n_sob) * 2.0 - 1.0) * 1.15
    if d > 2:
        X_sob[:, 2:] *= 0.75

    cor_pts = []
    n_cor = n_interior_anchors - n_sob
    starts_arr = np.asarray(query.start_points, dtype=float)
    for k in range(n_cor):
        s_pt = starts_arr[k % len(starts_arr)]
        g_pt = g_centers[k % len(g_centers)]
        alpha = rng.uniform(0.05, 0.92)
        pt = (1.0 - alpha) * s_pt + alpha * g_pt + rng.normal(0.0, 0.28, size=d)
        cor_pts.append(np.clip(pt, -L + 0.05, L - 0.05))
    X_int_raw = np.vstack([starts_arr, X_sob, np.array(cor_pts)])
    dists_int = np.linalg.norm(X_int_raw[:, None, :] - g_centers[None, :, :], axis=2)
    keep = np.all(dists_int > g_radii[None, :] + 0.03, axis=1)
    X_int = X_int_raw[keep]
    n_int = len(X_int)

    # 3. Simulate guided SDE paths from interior anchors under (b_hat + u0)
    #    and record step-wise exact residual r0 along each path!
    sqrt_dt = np.sqrt(dt_fk)
    pos = np.repeat(X_int[:, None, :], n_mc_paths, axis=1)  # (n_int, M, d)
    alive = np.ones((n_int, n_mc_paths), dtype=bool)
    acc_r = np.zeros((n_int, n_mc_paths), dtype=float)
    term_bnd_res = np.zeros((n_int, n_mc_paths), dtype=float)

    for _st in range(n_steps_fk):
        ai, aj = np.where(alive)
        if len(ai) == 0:
            break
        pts_a = pos[ai, aj]
        # Check goal absorption
        d_mat = np.linalg.norm(pts_a[:, None, :] - g_centers[None, :, :], axis=2)
        hit = d_mat <= g_radii[None, :]
        any_hit = np.any(hit, axis=1)
        if np.any(any_hit):
            hl = np.flatnonzero(any_hit)
            best_phi = np.min(np.where(hit[hl], g_phis[None, :], np.inf), axis=1)
            v0_hit, _ = base.val_and_grad(pts_a[hl])
            term_bnd_res[ai[hl], aj[hl]] = best_phi - v0_hit
            alive[ai[hl], aj[hl]] = False
            keep_mask = ~any_hit
            ai = ai[keep_mask]; aj = aj[keep_mask]
            if len(ai) == 0:
                break
            pts_a = pos[ai, aj]

        _, grad_v0 = base.val_and_grad(pts_a)
        u0 = -grad_v0
        q_hat, _ = km.predict_q(pts_a, return_std=False)
        b_hat = km.predict_b(pts_a, return_std=False)
        q_dyn = eval_bumps(pts_a, query.local_hazards)
        # Exact PDE residual r0 = q_hat + q_dyn + b_hat . grad_v0
        r0_step = q_hat + q_dyn + np.sum(b_hat * grad_v0, axis=1)
        acc_r[ai, aj] += r0_step * dt_fk

        x_next = pts_a + (b_hat + u0) * dt_fk + spec.sigma * sqrt_dt * rng.normal(size=pts_a.shape)
        pos[ai, aj] = reflect_into_box(x_next, L)

    # Final hit check at T
    ai, aj = np.where(alive)
    if len(ai) > 0:
        pts_a = pos[ai, aj]
        d_mat = np.linalg.norm(pts_a[:, None, :] - g_centers[None, :, :], axis=2)
        hit = d_mat <= g_radii[None, :]
        any_hit = np.any(hit, axis=1)
        if np.any(any_hit):
            hl = np.flatnonzero(any_hit)
            best_phi = np.min(np.where(hit[hl], g_phis[None, :], np.inf), axis=1)
            v0_hit, _ = base.val_and_grad(pts_a[hl])
            term_bnd_res[ai[hl], aj[hl]] = best_phi - v0_hit
            alive[ai[hl], aj[hl]] = False

    survivor_frac = float(np.mean(alive))

    # Pass 1 FK estimate (survivor tail = 0 initially) -> fit bootstrap GP -> Pass 2 continuation!
    def _fk_log_mean_exp(exponent_mat: np.ndarray) -> Tuple[np.ndarray, float]:
        mx = np.max(exponent_mat, axis=1, keepdims=True)
        w = np.exp(exponent_mat - mx)
        ess = np.mean((np.sum(w, axis=1) ** 2) / np.maximum(np.sum(w ** 2, axis=1), 1e-30))
        log_y = mx[:, 0] + np.log(np.maximum(np.mean(w, axis=1), 1e-300))
        return -lam * log_y, float(ess)

    exp1 = -(acc_r + np.where(alive, 0.0, term_bnd_res)) / lam
    dv_pass1, _ = _fk_log_mean_exp(exp1)
    ell_gp = 0.58 if d <= 4 else 0.72
    gp_boot = AnalyticMatern52ResidualGP(
        np.vstack([X_int, X_bnd]),
        np.concatenate([dv_pass1, y_bnd]),
        length_scale=ell_gp,
        noise=2e-3,
    )

    # Pass 2: plug continuation bootstrap DeltaV_boot(X_T) into surviving paths!
    tail_cont = np.zeros_like(term_bnd_res)
    ai, aj = np.where(alive)
    if len(ai) > 0:
        cont_vals, _ = gp_boot.predict_val_and_grad(pos[ai, aj])
        tail_cont[ai, aj] = cont_vals
    exp2 = -(acc_r + np.where(alive, tail_cont, term_bnd_res)) / lam
    dv_pass2, mean_ess = _fk_log_mean_exp(exp2)

    gp_final = AnalyticMatern52ResidualGP(
        np.vstack([X_int, X_bnd]),
        np.concatenate([dv_pass2, y_bnd]),
        length_scale=ell_gp,
        noise=2e-3,
    )

    def value_fn(X: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(X)
        v0, _ = base.val_and_grad(X2)
        dv, _ = gp_final.predict_val_and_grad(X2)
        val = v0 + dv
        d_mat = np.linalg.norm(X2[:, None, :] - g_centers[None, :, :], axis=2)
        hit = d_mat <= g_radii[None, :]
        any_hit = np.any(hit, axis=1)
        if np.any(any_hit):
            val[any_hit] = np.min(np.where(hit[any_hit], g_phis[None, :], np.inf), axis=1)
        return val

    def policy_fn(X: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(X)
        _, gv0 = base.val_and_grad(X2)
        _, gdv = gp_final.predict_val_and_grad(X2)
        u = -(gv0 + gdv)
        d_mat = np.linalg.norm(X2[:, None, :] - g_centers[None, :, :], axis=2)
        any_hit = np.any(d_mat <= g_radii[None, :], axis=1)
        if np.any(any_hit):
            u[any_hit] = 0.0
        return u

    plan_ms = 1000.0 * (time.perf_counter() - t0)
    return {
        "value_fn": value_fn,
        "policy": policy_fn,
        "base": base,
        "plan_ms": plan_ms,
        "survivor_fraction": survivor_frac,
        "mean_ess": mean_ess,
        "n_paths_per_anchor": n_mc_paths,
        "fk_horizon_sec": n_steps_fk * dt_fk,
    }


def make_same_gp_online_pimc_policy(
    spec: ProblemSpec,
    km: KrigingWorldModel,
    query: QueryTask,
    guided: bool = True,
    n_particles: int = 40,
    horizon_steps: int = 16,
    dt_mpc: float = 0.045,
    seed: int = 777,
) -> Callable[[np.ndarray], np.ndarray]:
    """Strong High-D Same-GP Baseline:
    Online Path-Integral MPC operating on the EXACT SAME learned KrigingWorldModel `(q_hat, b_hat)`.
    - `guided=False`: Unguided Brownian PIMC + terminal distance heuristic.
    - `guided=True`: Uses our analytical CapacitaryBesselBaseGuide `u0` as proposal drift AND
      `V0(X_H)` as terminal value bootstrap (isolates online MC vs residual GP distillation!).
    """
    lam = spec.lam
    L = spec.half_width
    sqrt_dt = np.sqrt(dt_mpc)
    base = CapacitaryBesselBaseGuide(spec, query)
    g_centers = np.array([g.center for g in query.goals], dtype=float)
    g_phis = np.array([g.phi for g in query.goals], dtype=float)
    g_radii = np.array([g.radius for g in query.goals], dtype=float)
    rng = np.random.default_rng(seed)

    def policy_fn(X: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(X)
        n_b = len(X2)
        d = spec.dim
        # Check already in goal
        d0 = np.linalg.norm(X2[:, None, :] - g_centers[None, :, :], axis=2)
        done0 = np.any(d0 <= g_radii[None, :], axis=1)

        if guided:
            _, gv0_start = base.val_and_grad(X2)
            u_nom0 = -gv0_start
        else:
            u_nom0 = np.zeros_like(X2)

        eps0 = rng.normal(0.0, sqrt_dt, size=(n_b, n_particles, d))
        pos = np.repeat(X2[:, None, :], n_particles, axis=1)
        alive = np.broadcast_to((~done0)[:, None], (n_b, n_particles)).copy()
        cost_acc = np.zeros((n_b, n_particles), dtype=float)

        for st in range(horizon_steps):
            ai, aj = np.where(alive)
            if len(ai) == 0:
                break
            pts = pos[ai, aj]
            if st == 0:
                u_prop = np.repeat(u_nom0[:, None, :], n_particles, axis=1)[ai, aj]
                noise = eps0[ai, aj]
            else:
                if guided:
                    _, gv = base.val_and_grad(pts)
                    u_prop = -gv
                else:
                    u_prop = np.zeros_like(pts)
                noise = rng.normal(0.0, sqrt_dt, size=pts.shape)

            q_hat, _ = km.predict_q(pts, return_std=False)
            b_hat = km.predict_b(pts, return_std=False)
            q_dyn = eval_bumps(pts, query.local_hazards)

            if guided:
                # Exact residual cost along guided proposal!
                r_step = q_hat + q_dyn - np.sum(b_hat * u_prop, axis=1)
            else:
                r_step = spec.q0 + q_hat + q_dyn
            cost_acc[ai, aj] += r_step * dt_mpc

            x_next = reflect_into_box(pts + (b_hat + u_prop) * dt_mpc + spec.sigma * noise, L)
            pos[ai, aj] = x_next

            dm = np.linalg.norm(x_next[:, None, :] - g_centers[None, :, :], axis=2)
            hit = dm <= g_radii[None, :]
            any_hit = np.any(hit, axis=1)
            if np.any(any_hit):
                hl = np.flatnonzero(any_hit)
                best_phi = np.min(np.where(hit[hl], g_phis[None, :], np.inf), axis=1)
                if guided:
                    v0_h, _ = base.val_and_grad(x_next[hl])
                    cost_acc[ai[hl], aj[hl]] += best_phi - v0_h
                else:
                    cost_acc[ai[hl], aj[hl]] += best_phi
                alive[ai[hl], aj[hl]] = False

        # Terminal value for unabsorbed particles at lookahead horizon H
        ai, aj = np.where(alive)
        if len(ai) > 0:
            if not guided:
                v0_end, _ = base.val_and_grad(pos[ai, aj])
                cost_acc[ai, aj] += v0_end
            # For guided=True, V0 is already factored out via control variate!

        exps = -cost_acc / lam
        mx = np.max(exps, axis=1, keepdims=True)
        w = np.exp(exps - mx)
        w /= np.maximum(np.sum(w, axis=1, keepdims=True), 1e-30)
        # Path-integral control correction: u* = u_nom0 + (sigma / dt) * E_w[dW_0]
        du = (spec.sigma / dt_mpc) * np.einsum("bm,bmd->bd", w, eps0)
        u_out = u_nom0 + du
        u_out[done0] = 0.0
        return u_out

    return policy_fn


class UnifiedUnderactuatedLQRGuide4D:
    """Smooth analytical multi-goal LQR base guide V0(p, v) for 4D inertial double integrator:
        dp = v dt,   dv = (-gamma v + f_wind(p) + u) dt + sigma dW
    Provides exact V0, grad_p V0, grad_v V0, and exact tr(Hess_v V0) so the full HJB residual:
        r0(p, v) = q0 + q_hid(p) + q_dyn(p) + v . grad_p V0 + (-gamma v + f_wind(p)) . grad_v V0
                   + 0.5 * sigma^2 * tr(Hess_v V0) - 0.5 * ||grad_v V0||^2
    holds WITH ZERO APPROXIMATION for both single-goal and multi-goal queries!
    """

    def __init__(self, gamma: float, sigma: float, q0: float, goals: Sequence[GoalBall], c_vel_term: float = 0.15):
        self.gamma = float(gamma)
        self.sigma = float(sigma)
        self.lam = self.sigma ** 2
        self.q0 = float(q0)
        self.c_vel_term = float(c_vel_term)
        self.g_centers = np.array([g.center for g in goals], dtype=float)
        self.g_phis = np.array([g.phi for g in goals], dtype=float)
        self.g_radii = np.array([g.radius for g in goals], dtype=float)

        A_lin = np.array([
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, -self.gamma, 0.0],
            [0.0, 0.0, 0.0, -self.gamma],
        ])
        G = np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
        Q_lqr = np.diag([1.6, 1.6, 0.25, 0.25])
        self.P = solve_continuous_are(A_lin, G, Q_lqr, np.eye(2))
        self.tr_Pvv = float(self.P[2, 2] + self.P[3, 3])

    def val_grad_and_trvv(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        X4 = np.atleast_2d(np.asarray(X, dtype=float))
        n = len(X4)
        m_g = len(self.g_centers)
        V_modes = np.empty((n, m_g), dtype=float)
        G_modes = np.empty((n, m_g, 4), dtype=float)

        for j in range(m_g):
            xg = np.array([self.g_centers[j, 0], self.g_centers[j, 1], 0.0, 0.0])
            dx = X4 - xg[None, :]
            Pd = dx @ self.P
            V_modes[:, j] = self.g_phis[j] + 0.5 * np.sum(dx * Pd, axis=1)
            G_modes[:, j, :] = Pd

        if m_g == 1:
            return V_modes[:, 0], G_modes[:, 0, :], np.full(n, self.tr_Pvv)

        exps = -V_modes / self.lam
        mx = np.max(exps, axis=1, keepdims=True)
        w = np.exp(exps - mx)
        z_sum = np.sum(w, axis=1, keepdims=True)
        alpha = w / np.maximum(z_sum, 1e-300)
        V0 = -self.lam * (mx[:, 0] + np.log(np.maximum(z_sum[:, 0], 1e-300)))
        grad_V0 = np.einsum("nj,njd->nd", alpha, G_modes)
        gv_modes = G_modes[:, :, 2:4]
        gv_mean = grad_V0[:, 2:4]
        var_gv = np.sum(alpha * np.sum(gv_modes ** 2, axis=2), axis=1) - np.sum(gv_mean ** 2, axis=1)
        tr_vv = self.tr_Pvv - var_gv / self.lam
        return V0, grad_V0, tr_vv

    def terminal_residual(self, X_bnd: np.ndarray, goal_idx: np.ndarray) -> np.ndarray:
        """Exact boundary residual: (phi_j + c_vel * ||v||^2) - V0(p, v)."""
        X4 = np.atleast_2d(X_bnd)
        v_sq = np.sum(X4[:, 2:4] ** 2, axis=1)
        phi_actual = self.g_phis[goal_idx] + self.c_vel_term * v_sq
        v0, _, _ = self.val_grad_and_trvv(X4)
        return phi_actual - v0

    def exact_pde_residual_r0(self, X: np.ndarray, q_hid_2d: np.ndarray, f_wind_2d: np.ndarray, q_dyn_2d: np.ndarray) -> np.ndarray:
        X4 = np.atleast_2d(X)
        v = X4[:, 2:4]
        _, grad_V0, tr_vv = self.val_grad_and_trvv(X4)
        gp = grad_V0[:, 0:2]
        gv = grad_V0[:, 2:4]
        drift_v = -self.gamma * v + f_wind_2d
        return (
            self.q0 + q_hid_2d + q_dyn_2d
            + np.sum(v * gp, axis=1)
            + np.sum(drift_v * gv, axis=1)
            + 0.5 * (self.sigma ** 2) * tr_vv
            - 0.5 * np.sum(gv ** 2, axis=1)
        )
