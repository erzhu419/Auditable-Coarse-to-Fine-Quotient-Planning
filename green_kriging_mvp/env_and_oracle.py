"""
Continuous 2D Stochastic Control Benchmark + Exact Elliptic PDE Oracle for Direction 1A.

Dynamics:
    dx_t = (b(x_t) + u_t) dt + sigma dW_t,    x_t in R^2
Cost until hitting any goal disk B(g_j, r_g):
    J(x, u) = E[ int_0^tau (q_0 + q_hid(x_t) + q_dyn(x_t) + 0.5 ||u_t||^2) dt + phi(x_tau) ]
Cole-Hopf transform:
    Z(x) = exp(-V*(x) / sigma^2)
    (-0.5 * sigma^2 * Delta - b(x) . grad + q_tot(x) / sigma^2) Z(x) = 0
    Z(x) = exp(-phi_j / sigma^2) on B(g_j, r_g),  Z(inf) = 0
Optimal feedback control:
    u*(x) = -grad V*(x) = +sigma^2 * grad log Z(x)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.interpolate import RegularGridInterpolator


@dataclass
class HazardBlob:
    center: np.ndarray  # (2,)
    amplitude: float    # peak running cost >= 0
    width: float        # Gaussian std


@dataclass
class QuerySpec:
    name: str
    goals: List[Tuple[np.ndarray, float]]  # list of (center (2,), terminal_cost phi_j >= 0)
    extra_hazards: List[HazardBlob] = field(default_factory=list)  # known dynamic constraints
    start_points: List[np.ndarray] = field(default_factory=list)


@dataclass
class StochasticControlEnv:
    sigma: float = 0.45          # diffusion noise std
    q0: float = 0.60             # known baseline time cost
    r_goal: float = 0.14         # goal absorption disk radius
    box_limit: float = 1.6       # soft outer simulation clip (domain of interest [-1, 1]^2)
    hazards: List[HazardBlob] = field(default_factory=list)
    vortex_center: Optional[np.ndarray] = None
    vortex_strength: float = 0.0 # non-conservative rotational drift amplitude (Regime 2)
    vortex_width: float = 0.45

    @property
    def kappa(self) -> float:
        return float(np.sqrt(2.0 * self.q0) / (self.sigma ** 2))

    def q_hidden(self, X: np.ndarray) -> np.ndarray:
        """Unknown environment hazard running cost q_hid(x) >= 0. X: (..., 2)."""
        X = np.asarray(X, dtype=float)
        orig_shape = X.shape[:-1]
        pts = X.reshape(-1, 2)
        val = np.zeros(len(pts), dtype=float)
        for h in self.hazards:
            d2 = np.sum((pts - h.center[None, :]) ** 2, axis=1)
            val += h.amplitude * np.exp(-0.5 * d2 / (h.width ** 2))
        return val.reshape(orig_shape)

    def q_dynamic(self, X: np.ndarray, extra_hazards: List[HazardBlob]) -> np.ndarray:
        """Known query-specific extra hazard cost q_dyn(x) >= 0."""
        X = np.asarray(X, dtype=float)
        orig_shape = X.shape[:-1]
        pts = X.reshape(-1, 2)
        val = np.zeros(len(pts), dtype=float)
        for h in extra_hazards:
            d2 = np.sum((pts - h.center[None, :]) ** 2, axis=1)
            val += h.amplitude * np.exp(-0.5 * d2 / (h.width ** 2))
        return val.reshape(orig_shape)

    def drift(self, X: np.ndarray) -> np.ndarray:
        """Unknown non-conservative background drift b(x) (vortex field in Regime 2). X: (..., 2)."""
        X = np.asarray(X, dtype=float)
        orig_shape = X.shape
        pts = X.reshape(-1, 2)
        out = np.zeros_like(pts)
        if self.vortex_center is not None and abs(self.vortex_strength) > 0.0:
            rel = pts - self.vortex_center[None, :]
            r2 = np.sum(rel ** 2, axis=1)
            env = np.exp(-0.5 * r2 / (self.vortex_width ** 2))
            # Divergence-free rotational vortex: (-dy, dx)
            out[:, 0] = -self.vortex_strength * rel[:, 1] * env
            out[:, 1] = +self.vortex_strength * rel[:, 0] * env
        return out.reshape(orig_shape)

    def simulate_rollouts(
        self,
        policy_fn: Callable[[np.ndarray], np.ndarray],
        query: QuerySpec,
        n_per_start: int = 40,
        dt: float = 0.015,
        max_steps: int = 450,
        u_clip: float = 6.0,
        seed: int = 0,
    ) -> dict:
        """Run actual closed-loop Euler-Maruyama SDE rollouts and measure true cost."""
        rng = np.random.default_rng(seed)
        starts = np.repeat(np.asarray(query.start_points, dtype=float), n_per_start, axis=0)
        n_traj = len(starts)
        x = starts.copy()
        alive = np.ones(n_traj, dtype=bool)
        reached = np.zeros(n_traj, dtype=bool)
        total_cost = np.zeros(n_traj, dtype=float)
        hazard_cost = np.zeros(n_traj, dtype=float)
        ctrl_cost = np.zeros(n_traj, dtype=float)
        steps_taken = np.zeros(n_traj, dtype=int)

        sqrt_dt = np.sqrt(dt)
        goal_centers = np.array([g[0] for g in query.goals], dtype=float)
        goal_phis = np.array([g[1] for g in query.goals], dtype=float)

        for step in range(max_steps):
            if not np.any(alive):
                break
            idx = np.where(alive)[0]
            xa = x[idx]

            # Check goal hit
            dists = np.linalg.norm(xa[:, None, :] - goal_centers[None, :, :], axis=2)
            min_goal_idx = np.argmin(dists, axis=1)
            min_dist = dists[np.arange(len(idx)), min_goal_idx]
            hit = min_dist <= self.r_goal
            if np.any(hit):
                hit_global = idx[hit]
                total_cost[hit_global] += goal_phis[min_goal_idx[hit]]
                reached[hit_global] = True
                alive[hit_global] = False
                steps_taken[hit_global] = step
                idx = np.where(alive)[0]
                if len(idx) == 0:
                    break
                xa = x[idx]

            u = np.asarray(policy_fn(xa), dtype=float)
            u_norm = np.linalg.norm(u, axis=1, keepdims=True)
            u = np.where(u_norm > u_clip, u * (u_clip / np.maximum(u_norm, 1e-12)), u)

            qh = self.q_hidden(xa) + self.q_dynamic(xa, query.extra_hazards)
            uc = 0.5 * np.sum(u ** 2, axis=1)
            hazard_cost[idx] += qh * dt
            ctrl_cost[idx] += uc * dt
            total_cost[idx] += (self.q0 + qh + uc) * dt

            b = self.drift(xa)
            noise = rng.normal(0.0, 1.0, size=xa.shape)
            x_next = xa + (b + u) * dt + self.sigma * sqrt_dt * noise
            x_next = np.clip(x_next, -self.box_limit, self.box_limit)
            x[idx] = x_next

        # Penalty for unreached trajectories (remaining horizon cost)
        if np.any(alive):
            steps_taken[alive] = max_steps
            # Terminal distance penalty proportional to straight-line minimal cost
            xa = x[alive]
            d_min = np.min(np.linalg.norm(xa[:, None, :] - goal_centers[None, :, :], axis=2), axis=1)
            total_cost[alive] += 2.0 * d_min + 2.0

        return {
            "mean_cost": float(np.mean(total_cost)),
            "std_cost": float(np.std(total_cost) / np.sqrt(n_traj)),
            "mean_hazard": float(np.mean(hazard_cost)),
            "mean_ctrl": float(np.mean(ctrl_cost)),
            "reach_rate": float(np.mean(reached)),
            "mean_steps": float(np.mean(steps_taken)),
        }


class ExactFDPDEOracle:
    """High-resolution finite-difference solver for the exact Cole-Hopf linear PDE."""

    def __init__(self, env: StochasticControlEnv, grid_n: int = 121, half_width: float = 2.0):
        self.env = env
        self.grid_n = grid_n
        self.half_width = half_width
        self.xs = np.linspace(-half_width, half_width, grid_n)
        self.h = float(self.xs[1] - self.xs[0])

    def solve(self, query: QuerySpec) -> dict:
        n = self.grid_n
        h = self.h
        sig2 = self.env.sigma ** 2
        XX, YY = np.meshgrid(self.xs, self.xs, indexing="ij")
        pts = np.stack([XX.ravel(), YY.ravel()], axis=1)

        q_tot = (
            self.env.q0
            + self.env.q_hidden(pts)
            + self.env.q_dynamic(pts, query.extra_hazards)
        ).reshape(n, n)
        drift = self.env.drift(pts).reshape(n, n, 2)

        # Identify goal disk nodes (Dirichlet BC: Z = exp(-phi_j / sigma^2))
        is_goal = np.zeros((n, n), dtype=bool)
        goal_val = np.zeros((n, n), dtype=float)
        for g_center, phi_j in query.goals:
            dist = np.sqrt((XX - g_center[0]) ** 2 + (YY - g_center[1]) ** 2)
            mask = dist <= self.env.r_goal
            w_j = float(np.exp(-phi_j / sig2))
            # If overlapping goals, take max Z (min cost)
            goal_val[mask] = np.maximum(goal_val[mask], w_j)
            is_goal |= mask

        # Assemble sparse linear system for (-0.5*sig2*Delta - b.grad + q_tot/sig2) Z = 0
        # Upwind scheme for drift ensures M-matrix positivity!
        N = n * n
        rows, cols, vals = [], [], []
        rhs = np.zeros(N, dtype=float)
        c_diff = 0.5 * sig2 / (h * h)

        for i in range(n):
            for j in range(n):
                idx = i * n + j
                if is_goal[i, j]:
                    rows.append(idx)
                    cols.append(idx)
                    vals.append(1.0)
                    rhs[idx] = goal_val[i, j]
                    continue
                if i == 0 or i == n - 1 or j == 0 or j == n - 1:
                    # Far-field absorbing Z = 0 at +/- half_width (well outside [-1,1]^2)
                    rows.append(idx)
                    cols.append(idx)
                    vals.append(1.0)
                    rhs[idx] = 1e-12
                    continue

                bx, by = drift[i, j, 0], drift[i, j, 1]
                diag = 4.0 * c_diff + q_tot[i, j] / sig2
                w_xp = -c_diff
                w_xm = -c_diff
                w_yp = -c_diff
                w_ym = -c_diff

                # Upwind for -bx * dZ/dx - by * dZ/dy
                if bx >= 0:
                    diag += bx / h
                    w_xp -= bx / h
                else:
                    diag += (-bx) / h
                    w_xm -= (-bx) / h

                if by >= 0:
                    diag += by / h
                    w_yp -= by / h
                else:
                    diag += (-by) / h
                    w_ym -= (-by) / h

                rows.extend([idx, idx, idx, idx, idx])
                cols.extend([idx, (i + 1) * n + j, (i - 1) * n + j, i * n + (j + 1), i * n + (j - 1)])
                vals.extend([diag, w_xp, w_xm, w_yp, w_ym])

        A = sparse.csr_matrix((vals, (rows, cols)), shape=(N, N))
        Z = spsolve(A, rhs).reshape(n, n)
        Z = np.maximum(Z, 1e-300)
        V = -sig2 * np.log(Z)

        # Compute optimal control u* = -grad V on grid via central differences
        gx, gy = np.gradient(V, h, h)
        ux = -gx
        uy = -gy

        V_interp = RegularGridInterpolator((self.xs, self.xs), V, bounds_error=False, fill_value=None)
        ux_interp = RegularGridInterpolator((self.xs, self.xs), ux, bounds_error=False, fill_value=0.0)
        uy_interp = RegularGridInterpolator((self.xs, self.xs), uy, bounds_error=False, fill_value=0.0)

        def policy(X: np.ndarray) -> np.ndarray:
            X = np.atleast_2d(X)
            xc = np.clip(X, -self.half_width + h, self.half_width - h)
            return np.stack([ux_interp(xc), uy_interp(xc)], axis=1)

        def value_fn(X: np.ndarray) -> np.ndarray:
            X = np.atleast_2d(X)
            xc = np.clip(X, -self.half_width + h, self.half_width - h)
            return V_interp(xc)

        return {"Z": Z, "V": V, "policy": policy, "value_fn": value_fn, "xs": self.xs}


def build_default_benchmark(with_vortex: bool = False) -> Tuple[StochasticControlEnv, List[QuerySpec]]:
    """
    Create a genuinely non-trivial 2D environment where straight-line free-space Green
    policies slam directly into hidden high-cost hazards.
    """
    hazards = [
        HazardBlob(center=np.array([0.0, 0.15]), amplitude=10.0, width=0.24),
        HazardBlob(center=np.array([0.22, -0.30]), amplitude=9.0, width=0.22),
        HazardBlob(center=np.array([-0.38, -0.18]), amplitude=8.0, width=0.20),
    ]
    env = StochasticControlEnv(
        sigma=0.45,
        q0=0.60,
        r_goal=0.14,
        hazards=hazards,
        vortex_center=np.array([0.05, 0.0]) if with_vortex else None,
        vortex_strength=1.4 if with_vortex else 0.0,
        vortex_width=0.55,
    )

    starts = [
        np.array([-0.80, -0.70]),
        np.array([-0.80, 0.25]),
        np.array([-0.20, -0.80]),
        np.array([0.75, -0.75]),
    ]

    queries = [
        QuerySpec(
            name="Q1_seen_goal",
            goals=[(np.array([0.80, 0.70]), 0.0)],
            start_points=starts,
        ),
        QuerySpec(
            name="Q2_unseen_goal",
            goals=[(np.array([-0.75, 0.78]), 0.0)],
            start_points=[
                np.array([0.75, -0.65]),
                np.array([0.80, 0.35]),
                np.array([0.10, -0.75]),
                np.array([-0.75, -0.70]),
            ],
        ),
        QuerySpec(
            name="Q3_unseen_multigoal",
            goals=[(np.array([0.80, 0.70]), 0.0), (np.array([-0.75, 0.78]), 0.12)],
            start_points=[
                np.array([0.00, -0.82]),
                np.array([-0.50, -0.72]),
                np.array([0.55, -0.72]),
                np.array([0.00, -0.45]),
            ],
        ),
        QuerySpec(
            name="Q4_dynamic_constraint",
            goals=[(np.array([0.80, 0.70]), 0.0)],
            extra_hazards=[HazardBlob(center=np.array([-0.20, 0.58]), amplitude=12.0, width=0.20)],
            start_points=starts,
        ),
    ]
    return env, queries
