"""Unified ProblemSpec, Post-Step Absorption CRN Simulator, Latent-Noise-Separated GP,
and Smooth / Narrow-Barrier Procedural Map Suites (green_kriging_v3).

Remediates all protocol & world-model issues identified in `green_kriging_v2_review`:
1. Post-update goal absorption check on every step (including final step `max_steps - 1`).
2. Separation of GP latent epistemic uncertainty `predict_latent_std` from `WhiteKernel` sensor noise.
3. Order-invariant goal union helper `eval_goal_union`.
4. Two map families (`smooth` vs `narrow_barrier`) to honestly test where coarse FD suffices vs
   where fine-operator Schur-Port strictly dominates the quality-time Pareto frontier.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np
from scipy.linalg import cho_solve
from scipy.optimize import brentq
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel


@dataclass(frozen=True)
class GoalBall:
    center: Tuple[float, ...]
    phi: float = 0.0
    radius: float = 0.22


@dataclass(frozen=True)
class HazardFeature:
    """Supports both isotropic Gaussian bumps and rotated anisotropic thin barrier ridges."""
    center: Tuple[float, ...]
    amplitude: float
    widths: Tuple[float, ...]  # per-principal-axis widths
    angle_2d: float = 0.0      # rotation angle in (x0, x1) plane


@dataclass(frozen=True)
class QueryTask:
    name: str
    goals: Tuple[GoalBall, ...]
    start_points: Tuple[Tuple[float, ...], ...]
    local_hazards: Tuple[HazardFeature, ...] = ()


@dataclass(frozen=True)
class ProblemSpec:
    dim: int = 2
    half_width: float = 1.65
    sigma: float = 0.45
    q0: float = 0.50
    r_diag: Optional[Tuple[float, ...]] = None
    u_max: Optional[float] = None
    u_numerical_cap: float = 25.0
    dt_sim: float = 0.012
    max_steps: int = 950

    @property
    def lam(self) -> float:
        return self.sigma ** 2

    def R_vec(self) -> np.ndarray:
        if self.r_diag is None:
            return np.ones(self.dim, dtype=float)
        return np.asarray(self.r_diag, dtype=float)


def reflect_into_box(x: np.ndarray, half_width: float) -> np.ndarray:
    """Exact specular reflection into [-L, L]^d."""
    L = half_width
    span = 2.0 * L
    y = np.mod(x + L, 2.0 * span)
    y = np.where(y > span, 2.0 * span - y, y)
    return y - L


def eval_goal_union(X: np.ndarray, goals: Sequence[GoalBall]) -> Tuple[np.ndarray, np.ndarray]:
    """Order-invariant goal stopping check:
    Returns `(in_any_goal [N], phi_union [N])` where `phi_union(x) = min_{j: x in Gamma_j} phi_j`.
    Invariant to any permutation of `goals`!
    """
    X2 = np.atleast_2d(np.asarray(X, dtype=float))
    n = len(X2)
    in_any = np.zeros(n, dtype=bool)
    phi_u = np.full(n, np.inf, dtype=float)
    for g in goals:
        gc = np.asarray(g.center, dtype=float)[None, :]
        hit = np.linalg.norm(X2 - gc, axis=1) <= g.radius
        in_any |= hit
        phi_u = np.where(hit, np.minimum(phi_u, g.phi), phi_u)
    return in_any, phi_u


def solve_anisotropic_ball_qp(g: np.ndarray, R_diag: np.ndarray, u_max: Optional[float]) -> np.ndarray:
    """Exact KKT solver for `argmin_{||u||_2 <= u_max} (0.5 u^T diag(R) u + g^T u)`."""
    single = (g.ndim == 1)
    G = np.atleast_2d(np.asarray(g, dtype=float))
    R = np.asarray(R_diag, dtype=float)[None, :]
    u_unc = -G / R
    if u_max is None:
        return u_unc[0] if single else u_unc

    norms = np.linalg.norm(u_unc, axis=1)
    out = u_unc.copy()
    over = np.flatnonzero(norms > u_max)
    if len(over) > 0:
        r1 = np.asarray(R_diag, dtype=float)
        r_min = float(np.min(r1))
        for idx in over:
            gi = G[idx]
            gnorm = float(np.linalg.norm(gi))
            eta_hi = max(gnorm / u_max - r_min, 1e-12) * 1.0001 + 1e-9
            eta = brentq(lambda e: float(np.linalg.norm(gi / (r1 + e))) - u_max, 0.0, eta_hi, xtol=1e-12, rtol=1e-12)
            out[idx] = -gi / (r1 + eta)
    return out[0] if single else out


def eval_hazard_features(X: np.ndarray, features: Sequence[HazardFeature]) -> np.ndarray:
    X2 = np.atleast_2d(np.asarray(X, dtype=float))
    if not features:
        return np.zeros(len(X2), dtype=float)
    q = np.zeros(len(X2), dtype=float)
    for f in features:
        c = np.asarray(f.center, dtype=float)[None, :]
        dx = X2 - c
        if abs(f.angle_2d) > 1e-12 and X2.shape[1] >= 2:
            ca, sa = np.cos(f.angle_2d), np.sin(f.angle_2d)
            x0 = ca * dx[:, 0] + sa * dx[:, 1]
            x1 = -sa * dx[:, 0] + ca * dx[:, 1]
            dx = dx.copy()
            dx[:, 0] = x0
            dx[:, 1] = x1
        w = np.asarray(f.widths, dtype=float)[None, :]
        mahal2 = np.sum((dx / w) ** 2, axis=1)
        q += f.amplitude * np.exp(-0.5 * mahal2)
    return q


class GroundTruthWorld:
    def __init__(
        self,
        spec: ProblemSpec,
        hazards: Sequence[HazardFeature],
        vortices: Sequence[Tuple[np.ndarray, float, float, int, int]] = (),
    ):
        self.spec = spec
        self.hazards = tuple(hazards)
        self.vortices = tuple(vortices)

    def q_hidden(self, X: np.ndarray) -> np.ndarray:
        return eval_hazard_features(X, self.hazards)

    def q_total(self, X: np.ndarray, query: Optional[QueryTask] = None) -> np.ndarray:
        X2 = np.atleast_2d(X)
        q = self.spec.q0 + self.q_hidden(X2)
        if query is not None and query.local_hazards:
            q = q + eval_hazard_features(X2, query.local_hazards)
        return q

    def drift(self, X: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(X)
        b = np.zeros_like(X2, dtype=float)
        for center, strength, width, ax_a, ax_b in self.vortices:
            c = np.asarray(center, dtype=float)[None, :]
            diff = X2 - c
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
    terminal_heuristic_fn: Optional[Callable[[np.ndarray], np.ndarray]] = None,
) -> dict:
    """Closed-loop SDE evaluation with:
    1. Trajectory-indexed pre-generated Common Random Numbers (CRN).
    2. Initial-state AND post-transition goal absorption check on EVERY step (including final step).
    3. Explicit recording of `clip_fraction`, `reflection_count`, `timeout_rate`, and timing.
    """
    spec = world.spec
    starts = np.repeat(np.asarray(query.start_points, dtype=float), n_per_start, axis=0)
    n_traj = len(starts)
    dt = spec.dt_sim
    sqrt_dt = np.sqrt(dt)
    R_vec = spec.R_vec()

    ss = np.random.SeedSequence([seed, n_traj, spec.dim])
    dW = np.empty((n_traj, spec.max_steps, spec.dim), dtype=float)
    for m, child in enumerate(ss.spawn(n_traj)):
        dW[m] = np.random.default_rng(child).normal(0.0, sqrt_dt, size=(spec.max_steps, spec.dim))

    x = starts.copy()
    alive = np.ones(n_traj, dtype=bool)
    reached = np.zeros(n_traj, dtype=bool)
    costs = np.zeros(n_traj, dtype=float)
    haz_acc = np.zeros(n_traj, dtype=float)
    ctrl_acc = np.zeros(n_traj, dtype=float)
    steps_taken = np.zeros(n_traj, dtype=int)
    clipped_steps = 0
    reflection_events = 0
    total_ctrl_evals = 0

    t0 = time.perf_counter()
    # Initial t=0 absorption check
    hit0, phi0 = eval_goal_union(x, query.goals)
    if np.any(hit0):
        costs[hit0] += phi0[hit0]
        reached[hit0] = True
        alive[hit0] = False

    for step in range(spec.max_steps):
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
        haz_acc[idx] += (qt - spec.q0) * dt
        ctrl_acc[idx] += uc * dt
        steps_taken[idx] += 1

        drift_val = world.drift(xa)
        x_raw = xa + (drift_val + u) * dt + spec.sigma * dW[idx, step, :]
        reflection_events += int(np.sum(np.any(np.abs(x_raw) > spec.half_width, axis=1)))
        x_next = reflect_into_box(x_raw, spec.half_width)
        x[idx] = x_next

        # Post-step absorption check (covers step == max_steps - 1 cleanly!)
        hit_post, phi_post = eval_goal_union(x_next, query.goals)
        if np.any(hit_post):
            hg = idx[hit_post]
            costs[hg] += phi_post[hit_post]
            reached[hg] = True
            alive[hg] = False

    still_alive = np.flatnonzero(alive)
    if len(still_alive) > 0:
        if terminal_heuristic_fn is not None:
            costs[still_alive] += terminal_heuristic_fn(x[still_alive])
        else:
            # Explicitly documented finite-horizon terminal penalty heuristic (not claimed as a lower bound)
            g_centers = np.array([g.center for g in query.goals], dtype=float)
            g_radii = np.array([g.radius for g in query.goals], dtype=float)
            dists = np.linalg.norm(x[still_alive][:, None, :] - g_centers[None, :, :], axis=2)
            d_min = np.min(np.maximum(0.0, dists - g_radii[None, :]), axis=1)
            costs[still_alive] += 2.0 * d_min + 1.5
    rollout_ms = 1000.0 * (time.perf_counter() - t0)

    return {
        "mean_cost": float(np.mean(costs)),
        "se_cost": float(np.std(costs, ddof=1) / np.sqrt(n_traj)) if n_traj > 1 else 0.0,
        "per_traj_costs": costs,
        "reach_rate": float(np.mean(reached)),
        "timeout_rate": float(np.mean(alive)),
        "mean_hazard_cost": float(np.mean(haz_acc)),
        "mean_ctrl_cost": float(np.mean(ctrl_acc)),
        "mean_steps": float(np.mean(steps_taken)),
        "clip_fraction": float(clipped_steps / max(total_ctrl_evals, 1)),
        "reflection_events": reflection_events,
        "rollout_ms": rollout_ms,
    }


class KrigingWorldModel:
    """Shared GP posterior with:
    1. Zero-overhead exact BLAS Matérn-5/2 mean evaluation (`predict_q`, `predict_b`).
    2. Explicit separation of latent epistemic std (`predict_q_latent_std`) vs observation noise!
    """

    def __init__(
        self,
        X_obs: np.ndarray,
        q_obs: np.ndarray,
        b_obs: Optional[np.ndarray] = None,
        length_scale_bounds: Tuple[float, float] = (0.10, 1.6),
    ):
        t0 = time.perf_counter()
        self.X_obs = np.atleast_2d(np.asarray(X_obs, dtype=float))
        self.dim = self.X_obs.shape[1]
        self.q_obs = np.asarray(q_obs, dtype=float)

        kq = ConstantKernel(4.0, (0.05, 250.0)) * Matern(
            length_scale=np.full(self.dim, 0.32),
            length_scale_bounds=length_scale_bounds,
            nu=2.5,
        ) + WhiteKernel(noise_level=0.16, noise_level_bounds=(1e-4, 4.0))
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
                ) + WhiteKernel(noise_level=0.03, noise_level_bounds=(1e-4, 1.0))
                gpd = GaussianProcessRegressor(kernel=kb, normalize_y=True, n_restarts_optimizer=1, random_state=d + 1)
                gpd.fit(self.X_obs, B[:, d])
                self.gp_b.append(gpd)

        self._fast_q = self._extract_fast_params(self.gp_q)
        self._fast_b = [self._extract_fast_params(gpd) for gpd in self.gp_b]
        self.fit_ms = 1000.0 * (time.perf_counter() - t0)

    @staticmethod
    def _extract_fast_params(gp: GaussianProcessRegressor) -> tuple:
        c_val = float(gp.kernel_.k1.k1.constant_value)
        ell = np.atleast_1d(np.asarray(gp.kernel_.k1.k2.length_scale, dtype=float))
        noise_val = float(gp.kernel_.k2.noise_level)
        y_mean = float(np.squeeze(gp._y_train_mean))
        y_std = float(np.squeeze(gp._y_train_std))
        alpha_eff = np.asarray(gp.alpha_, dtype=float).ravel() * (c_val * y_std)
        X_scaled = np.asarray(gp.X_train_, dtype=float) / ell[None, :]
        x_sq = np.sum(X_scaled ** 2, axis=1)
        return ell, X_scaled, x_sq, alpha_eff, y_mean, c_val, y_std, noise_val, gp.L_

    @staticmethod
    def _eval_kernel_matrix_scaled(Xq_sc: np.ndarray, X_tr_sc: np.ndarray, x_tr_sq: np.ndarray) -> np.ndarray:
        d2 = np.maximum(0.0, np.sum(Xq_sc ** 2, axis=1, keepdims=True) + x_tr_sq[None, :] - 2.0 * (Xq_sc @ X_tr_sc.T))
        s = np.sqrt(5.0 * d2)
        return (1.0 + s + (5.0 / 3.0) * d2) * np.exp(-s)

    def predict_q(self, X: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(np.asarray(X, dtype=float))
        ell, X_tr_sc, x_tr_sq, alpha_eff, y_mean, *_ = self._fast_q
        K = self._eval_kernel_matrix_scaled(X2 / ell[None, :], X_tr_sc, x_tr_sq)
        return np.maximum(0.0, y_mean + K @ alpha_eff)

    def predict_q_latent_std(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        """Returns `(mu_q, latent_epistemic_std, obs_noise_std)` — strictly excluding WhiteKernel noise!"""
        X2 = np.atleast_2d(np.asarray(X, dtype=float))
        ell, X_tr_sc, x_tr_sq, alpha_eff, y_mean, c_val, y_std, noise_val, L_chol = self._fast_q
        K_unit = self._eval_kernel_matrix_scaled(X2 / ell[None, :], X_tr_sc, x_tr_sq)
        mu = np.maximum(0.0, y_mean + K_unit @ alpha_eff)
        # In normalized y units: k_latent(x, x) = c_val, k_latent(x, X_tr) = c_val * K_unit
        K_lat = c_val * K_unit  # (Nq, Ntr)
        v = cho_solve((L_chol, True), K_lat.T)  # (Ntr, Nq)
        var_norm = np.maximum(0.0, c_val - np.sum(K_lat.T * v, axis=0))
        latent_std = y_std * np.sqrt(var_norm)
        obs_noise_std = y_std * np.sqrt(noise_val)
        return mu, latent_std, obs_noise_std

    def predict_b(self, X: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(np.asarray(X, dtype=float))
        if not self.has_drift:
            return np.zeros_like(X2, dtype=float)
        cols = []
        for p in self._fast_b:
            ell, X_tr_sc, x_tr_sq, alpha_eff, y_mean, *_ = p
            K = self._eval_kernel_matrix_scaled(X2 / ell[None, :], X_tr_sc, x_tr_sq)
            cols.append(y_mean + K @ alpha_eff)
        return np.column_stack(cols)


def sample_noisy_probes(
    world: GroundTruthWorld,
    n_probes: int,
    seed: int,
    probe_box: float = 1.28,
    q_noise_std: float = 0.35,
    b_noise_std: float = 0.12,
    include_drift: bool = True,
) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    rng = np.random.default_rng(seed)
    X = rng.uniform(-probe_box, probe_box, size=(n_probes, world.spec.dim))
    q_obs = np.maximum(0.0, world.q_hidden(X) + rng.normal(0.0, q_noise_std, size=n_probes))
    b_obs = None
    if include_drift and len(world.vortices) > 0:
        b_obs = world.drift(X) + rng.normal(0.0, b_noise_std, size=(n_probes, world.spec.dim))
    return X, q_obs, b_obs


def generate_benchmark_map(
    map_seed: int,
    dim: int = 2,
    regime: str = "smooth",
    with_drift: bool = True,
    spec: Optional[ProblemSpec] = None,
) -> GroundTruthWorld:
    """Generates procedural world in two distinct geometric regimes:
    - `smooth`: Broad isotropic hazard hills (`width ~ 0.22..0.38`) + vortex wind.
    - `narrow_barrier`: Slotted thin high-cost barrier walls (`thickness ~ 0.065`, `length ~ 0.55`)
      with narrow gaps + localized hazards + vortex wind (tests fine-geometry retention!).
    """
    if spec is None:
        spec = ProblemSpec(
            dim=dim,
            half_width=1.65,
            sigma=0.45 if dim <= 3 else 0.55,
            q0=0.50 if dim <= 3 else 0.65,
        )
    rng = np.random.default_rng(map_seed)
    hazards: List[HazardFeature] = []

    if regime == "smooth":
        n_bumps = int(rng.integers(4, 7))
        for _ in range(n_bumps):
            c = rng.uniform(-0.85, 0.85, size=dim)
            amp = float(rng.uniform(6.0, 14.0))
            w = float(rng.uniform(0.22, 0.36) if dim == 2 else rng.uniform(0.30, 0.48))
            hazards.append(HazardFeature(tuple(c.tolist()), amp, tuple([w] * dim), 0.0))
    elif regime == "narrow_barrier":
        # Two slotted thin barrier segments leaving narrow passages + 2 local pockets
        ang1 = float(rng.uniform(-0.7, 0.7))
        gap_offset = float(rng.choice([-1.0, 1.0]) * rng.uniform(0.32, 0.48))
        n_vec = np.array([-np.sin(ang1), np.cos(ang1)])
        t_vec = np.array([np.cos(ang1), np.sin(ang1)])
        for sgn in (-1.0, 1.0):
            c2 = sgn * (0.52 * t_vec) + 0.15 * gap_offset * n_vec
            c_full = np.zeros(dim)
            c_full[:2] = c2
            widths = [0.46, 0.062] + ([0.65] * (dim - 2))
            hazards.append(HazardFeature(tuple(c_full.tolist()), 42.0, tuple(widths), ang1))
        for _ in range(2):
            c = rng.uniform(-0.85, 0.85, size=dim)
            w = 0.16 if dim == 2 else 0.24
            hazards.append(HazardFeature(tuple(c.tolist()), float(rng.uniform(14.0, 22.0)), tuple([w] * dim), 0.0))
    else:
        raise ValueError(f"Unknown regime={regime}")

    vortices = []
    if with_drift:
        n_v = 1 if dim <= 3 else 2
        for vi in range(n_v):
            vc = rng.uniform(-0.40, 0.40, size=dim)
            vstr = float(rng.choice([-1.0, 1.0]) * rng.uniform(0.65, 1.10))
            vwid = float(rng.uniform(0.70, 1.05))
            vortices.append((vc, vstr, vwid, (2 * vi) % dim, (2 * vi + 1) % dim))

    return GroundTruthWorld(spec, hazards, vortices)
