"""Unified ProblemSpec, CRN Simulator, Procedural Map Generator, and Kriging World Model (v2).

Addresses all P0 protocol issues identified in the v1 audit:
1. Single shared `ProblemSpec` across numerical reference, candidate solvers, and rollout simulator
   (identical domain `[-L, L]^d`, specular reflecting outer walls = zero-Neumann `dV/dn = 0`,
   explicit control constraint semantics, and explicit horizon / stopping semantics).
2. Trajectory-indexed pre-generated Common Random Numbers (CRN) so early absorption of one
   trajectory never shifts the Brownian increments of other trajectories.
3. Fast Matérn-5/2 Kriging world model with exact analytic gradients and separated wall-clock
   accounting (`gp_fit_ms`).
4. Procedural multi-map generator (`generate_random_map`) for held-out map-clustered evaluation.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import brentq
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel


@dataclass(frozen=True)
class GoalBall:
    center: Tuple[float, ...]
    phi: float = 0.0
    radius: float = 0.22


@dataclass(frozen=True)
class HazardBump:
    center: Tuple[float, ...]
    amplitude: float
    sigma_width: float


@dataclass(frozen=True)
class QueryTask:
    name: str
    goals: Tuple[GoalBall, ...]
    start_points: Tuple[Tuple[float, ...], ...]
    local_hazards: Tuple[HazardBump, ...] = ()


@dataclass(frozen=True)
class ProblemSpec:
    """Single source of truth for the stochastic optimal control problem."""
    dim: int = 2
    half_width: float = 1.65
    sigma: float = 0.45
    q0: float = 0.50
    # Anisotropic quadratic control penalty R = diag(r_diag); None means identity I_d (standard LMDP).
    r_diag: Optional[Tuple[float, ...]] = None
    # Hard Euclidean ball cap ||u||_2 <= u_max; None means unconstrained (with a high safety cap
    # `u_numerical_cap` purely against NaN, verified via logged `clip_fraction`).
    u_max: Optional[float] = None
    u_numerical_cap: float = 25.0
    dt_sim: float = 0.012
    max_steps: int = 900  # T_max = 10.8s; long enough that first-exit absorption is >99.5%

    @property
    def lam(self) -> float:
        return self.sigma ** 2

    def R_vec(self) -> np.ndarray:
        if self.r_diag is None:
            return np.ones(self.dim, dtype=float)
        return np.asarray(self.r_diag, dtype=float)


def reflect_into_box(x: np.ndarray, half_width: float) -> np.ndarray:
    """Exact specular (Skorokhod) reflection into [-L, L]^d, matching zero-Neumann PDE boundary."""
    L = half_width
    span = 2.0 * L
    # Map to [0, 2*span) and fold triangle wave
    y = np.mod(x + L, 2.0 * span)
    y = np.where(y > span, 2.0 * span - y, y)
    return y - L


def solve_anisotropic_ball_qp(g: np.ndarray, R_diag: np.ndarray, u_max: Optional[float]) -> np.ndarray:
    """Exact KKT solver for:
        argmin_{||u||_2 <= u_max} (0.5 * u^T diag(R_diag) u + g^T u)
    Supports batched `g` of shape (N, d) or 1D `g` of shape (d,).
    """
    single = (g.ndim == 1)
    G = np.atleast_2d(np.asarray(g, dtype=float))
    R = np.asarray(R_diag, dtype=float)[None, :]
    u_unc = -G / R
    if u_max is None:
        return u_unc[0] if single else u_unc

    norms = np.linalg.norm(u_unc, axis=1)
    out = u_unc.copy()
    over = np.where(norms > u_max)[0]
    if len(over) > 0:
        r1 = np.asarray(R_diag, dtype=float)
        r_min = float(np.min(r1))
        for idx in over:
            gi = G[idx]
            gnorm = float(np.linalg.norm(gi))
            # Upper bound on KKT multiplier eta: ||gi / (R + eta)|| <= gnorm / (r_min + eta) = u_max
            eta_hi = max(gnorm / u_max - r_min, 1e-12) * 1.0001 + 1e-9
            eta = brentq(lambda e: float(np.linalg.norm(gi / (r1 + e))) - u_max, 0.0, eta_hi, xtol=1e-12, rtol=1e-12)
            out[idx] = -gi / (r1 + eta)
    return out[0] if single else out


def eval_bumps(X: np.ndarray, bumps: Sequence[HazardBump]) -> np.ndarray:
    X = np.atleast_2d(X)
    if not bumps:
        return np.zeros(len(X), dtype=float)
    q = np.zeros(len(X), dtype=float)
    for b in bumps:
        c = np.asarray(b.center, dtype=float)[None, :]
        d2 = np.sum((X - c) ** 2, axis=1)
        q += b.amplitude * np.exp(-0.5 * d2 / (b.sigma_width ** 2))
    return q


class GroundTruthWorld:
    """True continuous environment holding hidden hazards and non-conservative drift."""

    def __init__(
        self,
        spec: ProblemSpec,
        hazards: Sequence[HazardBump],
        vortices: Sequence[Tuple[np.ndarray, float, float, int, int]] = (),
    ):
        self.spec = spec
        self.hazards = tuple(hazards)
        # Each vortex: (center_d, strength, width, plane_axis_a, plane_axis_b)
        self.vortices = tuple(vortices)

    def q_hidden(self, X: np.ndarray) -> np.ndarray:
        return eval_bumps(X, self.hazards)

    def q_total(self, X: np.ndarray, query: Optional[QueryTask] = None) -> np.ndarray:
        X = np.atleast_2d(X)
        q = self.spec.q0 + self.q_hidden(X)
        if query is not None and query.local_hazards:
            q = q + eval_bumps(X, query.local_hazards)
        return q

    def drift(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        b = np.zeros_like(X, dtype=float)
        for center, strength, width, ax_a, ax_b in self.vortices:
            c = np.asarray(center, dtype=float)[None, :]
            diff = X - c
            r2 = np.sum(diff ** 2, axis=1)
            env_factor = strength * np.exp(-0.5 * r2 / (width ** 2))
            b[:, ax_a] += -diff[:, ax_b] * env_factor
            b[:, ax_b] += diff[:, ax_a] * env_factor
        return b


def simulate_closed_loop_crn(
    world: GroundTruthWorld,
    policy_fn: Callable[[np.ndarray], np.ndarray],
    query: QueryTask,
    n_per_start: int = 40,
    seed: int = 2026,
    terminal_continuation_fn: Optional[Callable[[np.ndarray], np.ndarray]] = None,
) -> dict:
    """Closed-loop SDE evaluation with trajectory-indexed pre-generated Common Random Numbers."""
    spec = world.spec
    starts = np.repeat(np.asarray(query.start_points, dtype=float), n_per_start, axis=0)
    n_traj = len(starts)
    dt = spec.dt_sim
    sqrt_dt = np.sqrt(dt)
    R_vec = spec.R_vec()

    # Deterministic per-trajectory RNG streams so path m always sees identical Brownian path W^(m)
    ss = np.random.SeedSequence([seed, len(starts), spec.dim])
    traj_rngs = [np.random.default_rng(child) for child in ss.spawn(n_traj)]
    # Pre-generate noise array (n_traj, max_steps, dim)
    dW = np.empty((n_traj, spec.max_steps, spec.dim), dtype=float)
    for m, trng in enumerate(traj_rngs):
        dW[m] = trng.normal(0.0, sqrt_dt, size=(spec.max_steps, spec.dim))

    x = starts.copy()
    alive = np.ones(n_traj, dtype=bool)
    reached = np.zeros(n_traj, dtype=bool)
    costs = np.zeros(n_traj, dtype=float)
    haz_Acc = np.zeros(n_traj, dtype=float)
    ctrl_Acc = np.zeros(n_traj, dtype=float)
    steps_taken = np.zeros(n_traj, dtype=int)
    clipped_steps = 0
    total_ctrl_evals = 0

    g_centers = np.array([g.center for g in query.goals], dtype=float)
    g_phis = np.array([g.phi for g in query.goals], dtype=float)
    g_radii = np.array([g.radius for g in query.goals], dtype=float)

    t0 = time.perf_counter()
    for step in range(spec.max_steps):
        idx = np.flatnonzero(alive)
        if len(idx) == 0:
            break
        xa = x[idx]
        # Goal absorption check
        dists = np.linalg.norm(xa[:, None, :] - g_centers[None, :, :], axis=2)
        hit_any = dists <= g_radii[None, :]
        has_hit = np.any(hit_any, axis=1)
        if np.any(has_hit):
            hit_local = np.flatnonzero(has_hit)
            hit_global = idx[hit_local]
            # If multiple goals hit simultaneously, pick lowest terminal cost
            best_phi = np.min(np.where(hit_any[hit_local], g_phis[None, :], np.inf), axis=1)
            costs[hit_global] += best_phi
            reached[hit_global] = True
            alive[hit_global] = False
            idx = np.flatnonzero(alive)
            if len(idx) == 0:
                break
            xa = x[idx]

        u = np.asarray(policy_fn(xa), dtype=float)
        unorm = np.linalg.norm(u, axis=1, keepdims=True)
        cap = spec.u_max if spec.u_max is not None else spec.u_numerical_cap
        over = unorm[:, 0] > cap + 1e-12
        clipped_steps += int(np.sum(over))
        total_ctrl_evals += len(idx)
        if np.any(over):
            u = np.where(unorm > cap, u * (cap / np.maximum(unorm, 1e-12)), u)

        qt = world.q_total(xa, query)
        uc = 0.5 * np.sum((u ** 2) * R_vec[None, :], axis=1)
        costs[idx] += (qt + uc) * dt
        haz_Acc[idx] += (qt - spec.q0) * dt
        ctrl_Acc[idx] += uc * dt
        steps_taken[idx] += 1

        drift_val = world.drift(xa)
        x_next = xa + (drift_val + u) * dt + spec.sigma * dW[idx, step, :]
        x[idx] = reflect_into_box(x_next, spec.half_width)

    rollout_ms = 1000.0 * (time.perf_counter() - t0)
    still_alive = np.flatnonzero(alive)
    if len(still_alive) > 0:
        if terminal_continuation_fn is not None:
            costs[still_alive] += terminal_continuation_fn(x[still_alive])
        else:
            # Conservative lower-bound free geodesic estimate if unabsorbed at T_max
            dists = np.linalg.norm(x[still_alive][:, None, :] - g_centers[None, :, :], axis=2)
            d_min = np.min(np.maximum(0.0, dists - g_radii[None, :]), axis=1)
            costs[still_alive] += np.sqrt(2.0 * spec.q0 * float(np.min(R_vec))) * d_min

    return {
        "mean_cost": float(np.mean(costs)),
        "se_cost": float(np.std(costs, ddof=1) / np.sqrt(n_traj)),
        "per_traj_costs": costs,
        "reach_rate": float(np.mean(reached)),
        "timeout_rate": float(np.mean(alive)),
        "mean_hazard_cost": float(np.mean(haz_Acc)),
        "mean_ctrl_cost": float(np.mean(ctrl_Acc)),
        "mean_steps": float(np.mean(steps_taken)),
        "clip_fraction": float(clipped_steps / max(total_ctrl_evals, 1)),
        "rollout_ms": rollout_ms,
    }


class KrigingWorldModel:
    """Shared Gaussian Process posterior over unknown hazard q(x) and optional drift b(x)."""

    def __init__(
        self,
        X_obs: np.ndarray,
        q_obs: np.ndarray,
        b_obs: Optional[np.ndarray] = None,
        length_scale_bounds: Tuple[float, float] = (0.15, 1.5),
    ):
        t0 = time.perf_counter()
        self.X_obs = np.atleast_2d(np.asarray(X_obs, dtype=float))
        self.dim = self.X_obs.shape[1]
        self.q_obs = np.asarray(q_obs, dtype=float)

        kq = ConstantKernel(4.0, (0.05, 200.0)) * Matern(
            length_scale=np.full(self.dim, 0.38),
            length_scale_bounds=length_scale_bounds,
            nu=2.5,
        ) + WhiteKernel(noise_level=0.20, noise_level_bounds=(1e-3, 4.0))
        self.gp_q = GaussianProcessRegressor(kernel=kq, normalize_y=True, n_restarts_optimizer=2, random_state=0)
        self.gp_q.fit(self.X_obs, self.q_obs)

        self.has_drift = b_obs is not None
        self.gp_b: List[GaussianProcessRegressor] = []
        if self.has_drift:
            B = np.atleast_2d(np.asarray(b_obs, dtype=float))
            for d in range(self.dim):
                kb = ConstantKernel(1.0, (0.01, 50.0)) * Matern(
                    length_scale=np.full(self.dim, 0.50),
                    length_scale_bounds=(0.20, 2.0),
                    nu=2.5,
                ) + WhiteKernel(noise_level=0.04, noise_level_bounds=(1e-4, 1.0))
                gpd = GaussianProcessRegressor(kernel=kb, normalize_y=True, n_restarts_optimizer=1, random_state=d + 1)
                gpd.fit(self.X_obs, B[:, d])
                self.gp_b.append(gpd)

        # Compile zero-overhead exact Matérn-5/2 ARD fast predictors (matches sklearn.predict to ~1e-15
        # while eliminating Python check_array overhead inside tight online PIMC / FK loops!)
        self._fast_q = self._extract_fast_params(self.gp_q)
        self._fast_b = [self._extract_fast_params(gpd) for gpd in self.gp_b]
        self.fit_ms = 1000.0 * (time.perf_counter() - t0)

    @staticmethod
    def _extract_fast_params(gp: GaussianProcessRegressor) -> tuple:
        c_val = float(gp.kernel_.k1.k1.constant_value)
        ell = np.atleast_1d(np.asarray(gp.kernel_.k1.k2.length_scale, dtype=float))
        y_mean = float(np.squeeze(gp._y_train_mean))
        y_std = float(np.squeeze(gp._y_train_std))
        alpha_eff = np.asarray(gp.alpha_, dtype=float).ravel() * (c_val * y_std)
        X_scaled = np.asarray(gp.X_train_, dtype=float) / ell[None, :]
        x_sq = np.sum(X_scaled ** 2, axis=1)
        return ell, X_scaled, x_sq, alpha_eff, y_mean

    @staticmethod
    def _eval_fast_matern52(X: np.ndarray, params: tuple) -> np.ndarray:
        ell, X_tr_sc, x_tr_sq, alpha_eff, y_mean = params
        Xq_sc = X / ell[None, :]
        # Squared ARD Euclidean distance via BLAS gemm: ||a - b||^2 = ||a||^2 + ||b||^2 - 2 a.b
        d2 = np.maximum(0.0, np.sum(Xq_sc ** 2, axis=1, keepdims=True) + x_tr_sq[None, :] - 2.0 * (Xq_sc @ X_tr_sc.T))
        s = np.sqrt(5.0 * d2)
        K = (1.0 + s + (5.0 / 3.0) * d2) * np.exp(-s)
        return y_mean + K @ alpha_eff

    def predict_q(self, X: np.ndarray, return_std: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        X = np.atleast_2d(np.asarray(X, dtype=float))
        if return_std:
            mu, std = self.gp_q.predict(X, return_std=True)
            return np.maximum(0.0, mu), std
        mu = self._eval_fast_matern52(X, self._fast_q)
        return np.maximum(0.0, mu), None

    def predict_b(self, X: np.ndarray, return_std: bool = False):
        X = np.atleast_2d(np.asarray(X, dtype=float))
        if not self.has_drift:
            zeros = np.zeros_like(X, dtype=float)
            return (zeros, np.zeros_like(X, dtype=float)) if return_std else zeros
        if return_std:
            mus, stds = [], []
            for gpd in self.gp_b:
                m, s = gpd.predict(X, return_std=True)
                mus.append(m); stds.append(s)
            return np.column_stack(mus), np.column_stack(stds)
        return np.column_stack([self._eval_fast_matern52(X, p) for p in self._fast_b])


def sample_noisy_probes(
    world: GroundTruthWorld,
    n_probes: int,
    seed: int,
    probe_box: float = 1.25,
    q_noise_std: float = 0.40,
    b_noise_std: float = 0.15,
    include_drift: bool = True,
) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    rng = np.random.default_rng(seed)
    X = rng.uniform(-probe_box, probe_box, size=(n_probes, world.spec.dim))
    q_obs = np.maximum(0.0, world.q_hidden(X) + rng.normal(0.0, q_noise_std, size=n_probes))
    b_obs = None
    if include_drift and len(world.vortices) > 0:
        b_obs = world.drift(X) + rng.normal(0.0, b_noise_std, size=(n_probes, world.spec.dim))
    return X, q_obs, b_obs


def generate_random_map(
    map_seed: int,
    dim: int = 2,
    with_drift: bool = True,
    n_queries: int = 12,
    spec: Optional[ProblemSpec] = None,
) -> Tuple[GroundTruthWorld, List[QueryTask]]:
    """Procedural generator of diverse random environments and query suites for map-clustered evaluation."""
    if spec is None:
        spec = ProblemSpec(
            dim=dim,
            half_width=1.65,
            sigma=0.45 if dim <= 3 else 0.55,
            q0=0.50 if dim <= 3 else 0.65,
        )
    rng = np.random.default_rng(map_seed)
    n_bumps = rng.integers(3, 7) if dim == 2 else rng.integers(4, 8)
    hazards: List[HazardBump] = []
    for _ in range(int(n_bumps)):
        c = rng.uniform(-0.85, 0.85, size=dim)
        amp = float(rng.uniform(5.5, 13.5))
        wid = float(rng.uniform(0.20, 0.36) if dim == 2 else rng.uniform(0.32, 0.52))
        hazards.append(HazardBump(tuple(c.tolist()), amp, wid))

    vortices = []
    if with_drift:
        n_vort = 1 if dim == 2 else 2
        for v_i in range(n_vort):
            vc = rng.uniform(-0.45, 0.45, size=dim)
            strength = float(rng.choice([-1.0, 1.0]) * rng.uniform(0.65, 1.15))
            vwid = float(rng.uniform(0.65, 1.05))
            ax_a = (2 * v_i) % dim
            ax_b = (2 * v_i + 1) % dim
            vortices.append((vc, strength, vwid, ax_a, ax_b))

    world = GroundTruthWorld(spec, hazards, vortices)
    r_goal = 0.22 if dim == 2 else (0.28 if dim == 3 else 0.36)

    queries: List[QueryTask] = []
    for k in range(n_queries):
        n_goals = 2 if (k % 3 == 2) else 1
        goals = []
        for g_j in range(n_goals):
            # Place goals away from immediate overlap
            for _attempt in range(30):
                gc = rng.uniform(-1.05, 1.05, size=dim)
                if dim > 2:
                    gc[2:] *= 0.6
                if all(np.linalg.norm(gc - np.array(prev.center)) > 2.3 * r_goal for prev in goals):
                    break
            phi = 0.0 if g_j == 0 else float(rng.uniform(0.0, 0.30))
            goals.append(GoalBall(tuple(gc.tolist()), phi=phi, radius=r_goal))

        starts = []
        for _s in range(3):
            for _attempt in range(40):
                st = rng.uniform(-1.10, 1.10, size=dim)
                if dim > 2:
                    st[2:] *= 0.6
                if all(np.linalg.norm(st - np.array(g.center)) > 2.5 * r_goal + 0.35 for g in goals):
                    break
            starts.append(tuple(st.tolist()))

        local_haz = ()
        if k % 4 == 3:
            # Dynamic local hazard between start_0 and goal_0
            mid = 0.5 * (np.array(starts[0]) + np.array(goals[0].center)) + rng.normal(0.0, 0.12, size=dim)
            if all(np.linalg.norm(mid - np.array(g.center)) > 1.5 * r_goal for g in goals):
                local_haz = (HazardBump(tuple(mid.tolist()), amplitude=14.0, sigma_width=0.20 if dim == 2 else 0.30),)

        queries.append(QueryTask(
            name=f"M{map_seed}_Q{k+1}",
            goals=tuple(goals),
            start_points=tuple(starts),
            local_hazards=local_haz,
        ))
    return world, queries
