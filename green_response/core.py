"""Unified Core Specification, Capability Guards, Reflection Mechanics, Same-GP Kriging,
and Scale-Equivariant Paired Non-Inferiority Statistics (`green_response.core`).
"""
from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np
import scipy
import sklearn
from scipy.spatial.distance import cdist
from scipy.stats import t as student_t
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel


def enforce_single_thread_env() -> dict:
    """Pins BLAS/OpenMP thread environment variables to 1 when unset."""
    keys = (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    )
    for k in keys:
        os.environ.setdefault(k, "1")
    return {k: os.environ.get(k, "") for k in keys}


def collect_runtime_metadata() -> dict:
    pool_info = None
    try:
        from threadpoolctl import threadpool_info  # type: ignore
        pool_info = threadpool_info()
    except Exception:
        pool_info = "threadpoolctl_unavailable"
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "sklearn_version": sklearn.__version__,
        "thread_env": {
            k: os.environ.get(k, "unset")
            for k in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        },
        "active_threadpools": pool_info,
    }


@dataclass(frozen=True)
class GoalBall:
    center: Tuple[float, ...]
    phi: float = 0.0
    radius: float = 0.22


@dataclass(frozen=True)
class HazardFeature:
    center: Tuple[float, ...]
    amplitude: float
    sigma_vec: Tuple[float, ...]


@dataclass(frozen=True)
class QueryTask:
    name: str
    goals: Tuple[GoalBall, ...]
    start_points: Tuple[Tuple[float, ...], ...]
    local_hazards: Tuple[HazardFeature, ...] = ()


@dataclass(frozen=True)
class ProblemSpec:
    dim: int
    half_width: float = 1.65
    sigma: float = 0.45
    q0: float = 0.50
    r_diag: Optional[Tuple[float, ...]] = None
    u_max: Optional[float] = None
    dt_sim: float = 0.015
    max_steps: int = 380

    @property
    def R_vec(self) -> np.ndarray:
        if self.r_diag is None:
            return np.ones(self.dim, dtype=float)
        arr = np.asarray(self.r_diag, dtype=float)
        if arr.shape != (self.dim,):
            raise ValueError(f"r_diag length {arr.shape} does not match dim={self.dim}")
        if np.any(arr <= 0.0):
            raise ValueError("All entries of r_diag must be strictly positive.")
        return arr

    @property
    def is_isotropic_r(self) -> bool:
        if self.r_diag is None:
            return True
        rv = self.R_vec
        return bool(float(np.max(rv) - np.min(rv)) <= 1e-12 * max(1.0, float(np.max(rv))))

    @property
    def scalar_r(self) -> float:
        if not self.is_isotropic_r:
            raise ValueError(
                f"ProblemSpec has anisotropic r_diag={self.r_diag}; scalar_r is undefined."
            )
        return 1.0 if self.r_diag is None else float(self.r_diag[0])

    @property
    def lam(self) -> float:
        if not self.is_isotropic_r:
            return (self.sigma ** 2) * float(np.exp(np.mean(np.log(self.R_vec))))
        return (self.sigma ** 2) * self.scalar_r

    def validate_cole_hopf_lmdp(self, solver_name: str, allow_scalar_r: bool = True) -> float:
        """Explicit solver domain guard rejecting unsupported finite `u_max` or anisotropic `R`."""
        if self.u_max is not None:
            raise ValueError(
                f"{solver_name} requires unconstrained control (u_max=None), got u_max={self.u_max}."
            )
        if not self.is_isotropic_r:
            raise ValueError(
                f"{solver_name} requires isotropic R = r * I for Cole-Hopf LMDP reduction, got r_diag={self.r_diag}."
            )
        r_val = self.scalar_r
        if not allow_scalar_r and abs(r_val - 1.0) > 1e-12:
            raise ValueError(
                f"{solver_name} requires unit control weight R = I, got r={r_val}."
            )
        return r_val

    def as_isotropic_unconstrained_surrogate(self) -> "ProblemSpec":
        """Explicitly constructs the geometric-mean isotropic unconstrained LMDP surrogate (`u_max=None`,
        `R = r_bar * I` with `r_bar = exp(mean(log(R_vec)))`, preserving `lam`) for warm-start initialization
        of non-LMDP solvers without misrepresenting surrogate outputs as exact solutions of `self`.
        """
        r_bar = float(np.exp(np.mean(np.log(self.R_vec))))
        return ProblemSpec(
            dim=self.dim,
            half_width=self.half_width,
            sigma=self.sigma,
            q0=self.q0,
            r_diag=(r_bar,) * self.dim,
            u_max=None,
            dt_sim=self.dt_sim,
            max_steps=self.max_steps,
        )


@dataclass
class IntervalCertificate:
    """Lightweight typed certificate result (`status`, `scope`, `bounds`, `policy`, `reason`, `work`)
    supporting both attribute access and dict-style lookup for backward compatibility.
    """
    status: str  # "epsilon_certified" | "unresolved" | "numeric_invalid" | "heuristic"
    certified: bool
    certificate_scope: str
    epsilon_tol: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    stop_reason: str = ""
    work: Optional[dict] = None
    extras: Optional[dict] = None

    def to_dict(self) -> dict:
        base = {
            "status": self.status,
            "certified": bool(self.certified),
            "certificate_scope": self.certificate_scope,
            "epsilon_tol": float(self.epsilon_tol),
            "lower_bound": None if self.lower_bound is None else float(self.lower_bound),
            "upper_bound": None if self.upper_bound is None else float(self.upper_bound),
            "stop_reason": self.stop_reason,
            "work": {} if self.work is None else dict(self.work),
        }
        if self.extras:
            base.update(self.extras)
        return base

    def __getitem__(self, key: str):
        d = self.to_dict()
        return d[key]

    def get(self, key: str, default=None):
        return self.to_dict().get(key, default)

    def keys(self):
        return self.to_dict().keys()

    def __contains__(self, key: str) -> bool:
        return key in self.to_dict()


def reflect_into_box(X: np.ndarray, half_width: float) -> np.ndarray:
    """Exact specular reflection on `[-L, L]^d` with period `4L`."""
    L = float(half_width)
    period = 4.0 * L
    u = np.mod(X + L, period)
    return np.where(u <= 2.0 * L, u - L, 3.0 * L - u)


def reflect_kinetic_into_box(
    p_raw: np.ndarray, v_raw: np.ndarray, half_width: float, v_max: float = 3.5
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """True kinetic specular wall reflection for `(p, v)` in `[-L, L]^d_p x [-v_max, v_max]^d_v`."""
    L = float(half_width)
    period = 4.0 * L
    u = np.mod(p_raw + L, period)
    odd_bounce = u > 2.0 * L
    p_ref = np.where(odd_bounce, 3.0 * L - u, u - L)
    wall_hit = np.any(np.abs(p_raw) > L, axis=1)
    v_bounced = np.where(odd_bounce, -v_raw, v_raw)
    vel_clipped = np.any(np.abs(v_bounced) > v_max, axis=1)
    v_ref = np.clip(v_bounced, -v_max, v_max)
    return p_ref, v_ref, wall_hit, vel_clipped


def eval_hazard_features(X: np.ndarray, features: Sequence[HazardFeature]) -> np.ndarray:
    X = np.atleast_2d(X)
    out = np.zeros(X.shape[0], dtype=float)
    for f in features:
        c = np.asarray(f.center, dtype=float)[None, :]
        s = np.asarray(f.sigma_vec, dtype=float)[None, :]
        out += f.amplitude * np.exp(-0.5 * np.sum(((X - c) / s) ** 2, axis=1))
    return out


def eval_goal_union(X: np.ndarray, goals: Sequence[GoalBall]) -> Tuple[np.ndarray, np.ndarray]:
    """Order-invariant goal union: `in_union(x) = OR_j (||x - g_j||_2 <= r_j)`,
    `phi_union(x) = min_{j : x in Gamma_j} phi_j`.
    """
    X = np.atleast_2d(X)
    n = X.shape[0]
    in_any = np.zeros(n, dtype=bool)
    phi_min = np.full(n, np.inf, dtype=float)
    for g in goals:
        c = np.asarray(g.center, dtype=float)[None, :]
        mask = np.sum((X - c) ** 2, axis=1) <= (g.radius ** 2)
        if np.any(mask):
            in_any |= mask
            phi_min[mask] = np.minimum(phi_min[mask], g.phi)
    phi_min[~in_any] = 0.0
    return in_any, phi_min


class GroundTruthWorld:
    def __init__(
        self,
        spec: ProblemSpec,
        hazards: Sequence[HazardFeature],
        vortices: Sequence[Tuple[np.ndarray, float, float]] = (),
    ):
        self.spec = spec
        self.hazards = tuple(hazards)
        self.vortices = tuple(vortices)

    def q_hidden(self, X: np.ndarray) -> np.ndarray:
        return eval_hazard_features(X, self.hazards)

    def q_total(self, X: np.ndarray, local_hazards: Sequence[HazardFeature] = ()) -> np.ndarray:
        return self.spec.q0 + self.q_hidden(X) + eval_hazard_features(X, local_hazards)

    def drift(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        b = np.zeros_like(X, dtype=float)
        if not self.vortices:
            return b
        for center, strength, width in self.vortices:
            c = np.asarray(center, dtype=float)[None, :]
            rel = X - c
            r2 = np.sum(rel[:, :2] ** 2, axis=1, keepdims=True)
            env = strength * np.exp(-0.5 * r2 / (width ** 2))
            b[:, 0:1] += -env * rel[:, 1:2]
            b[:, 1:2] += env * rel[:, 0:1]
        if X.shape[1] >= 4:
            b[:, 2] += 0.20 * np.sin(np.pi * X[:, 3] / self.spec.half_width)
            b[:, 3] += -0.20 * np.sin(np.pi * X[:, 2] / self.spec.half_width)
        return b


def generate_benchmark_map(
    map_seed: int,
    dim: int,
    regime: str = "smooth",
    with_drift: bool = True,
    spec: Optional[ProblemSpec] = None,
) -> GroundTruthWorld:
    rng = np.random.default_rng(map_seed)
    if spec is None:
        spec = ProblemSpec(
            dim=dim,
            half_width=1.65,
            sigma=0.45 if dim <= 3 else 0.55,
            q0=0.50 if dim <= 3 else 0.65,
            dt_sim=0.015 if dim <= 3 else 0.020,
            max_steps=400 if dim <= 3 else 420,
        )
    hazards: List[HazardFeature] = []
    if regime == "smooth":
        n_blobs = 5 if dim == 2 else (6 if dim == 3 else 7)
        for _ in range(n_blobs):
            center = rng.uniform(-0.92, 0.92, size=dim)
            if dim > 2:
                center[2:] *= 0.6
            amp = float(rng.uniform(4.5, 9.5))
            sig = rng.uniform(0.28, 0.48, size=dim)
            if dim > 3:
                sig[2:] = rng.uniform(0.50, 0.75, size=dim - 2)
            hazards.append(HazardFeature(tuple(center.tolist()), amp, tuple(sig.tolist())))
    elif regime == "narrow_barrier":
        n_walls = 3 if dim == 2 else 4
        for w_i in range(n_walls):
            center = rng.uniform(-0.75, 0.75, size=dim)
            thin_axis = w_i % min(dim, 3)
            sig = np.full(dim, 0.52, dtype=float)
            sig[thin_axis] = 0.095 if dim == 2 else 0.13
            amp = float(rng.uniform(13.0, 21.0))
            hazards.append(HazardFeature(tuple(center.tolist()), amp, tuple(sig.tolist())))
        for _ in range(3):
            center = rng.uniform(-1.0, 1.0, size=dim)
            sig = rng.uniform(0.20, 0.34, size=dim)
            hazards.append(HazardFeature(tuple(center.tolist()), float(rng.uniform(5.0, 9.0)), tuple(sig.tolist())))
    else:
        raise ValueError(f"Unknown regime: {regime}")

    vortices = []
    if with_drift:
        for _ in range(2):
            vc = rng.uniform(-0.65, 0.65, size=dim)
            strength = float(rng.choice([-1.0, 1.0]) * rng.uniform(0.55, 0.95))
            width = float(rng.uniform(0.60, 0.90))
            vortices.append((vc, strength, width))
    return GroundTruthWorld(spec=spec, hazards=hazards, vortices=vortices)


def sample_noisy_probes(
    world: GroundTruthWorld,
    n_probes: int,
    seed: int,
    q_noise_std: float = 0.28,
    b_noise_std: float = 0.08,
    include_drift: bool = True,
) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    rng = np.random.default_rng(seed)
    L = world.spec.half_width - 0.12
    X = rng.uniform(-L, L, size=(n_probes, world.spec.dim))
    q_obs = np.maximum(0.0, world.q_hidden(X) + rng.normal(0.0, q_noise_std, size=n_probes))
    if not include_drift:
        return X, q_obs, None
    b_obs = world.drift(X) + rng.normal(0.0, b_noise_std, size=(n_probes, world.spec.dim))
    return X, q_obs, b_obs


class KrigingWorldModel:
    """Same-GP Matérn-5/2 world model with fast BLAS mean evaluation and latent-vs-sensor std split."""

    def __init__(self, X_obs: np.ndarray, q_obs: np.ndarray, b_obs: Optional[np.ndarray] = None):
        self.X_obs = np.atleast_2d(np.asarray(X_obs, dtype=float))
        self.q_obs = np.asarray(q_obs, dtype=float)
        self.dim = self.X_obs.shape[1]

        kernel_q = ConstantKernel(2.0, (0.05, 80.0)) * Matern(
            length_scale=np.full(self.dim, 0.42),
            length_scale_bounds=(0.07, 2.5),
            nu=2.5,
        ) + WhiteKernel(noise_level=0.08, noise_level_bounds=(1e-4, 2.0))
        self.gp_q = GaussianProcessRegressor(kernel=kernel_q, normalize_y=True, n_restarts_optimizer=1, random_state=0)
        self.gp_q.fit(self.X_obs, self.q_obs)
        self._cache_fast_matern_params()

        self.b_gps: Optional[List[GaussianProcessRegressor]] = None
        self._b_fast: List[dict] = []
        if b_obs is not None:
            b_obs = np.asarray(b_obs, dtype=float)
            self.b_gps = []
            for k in range(self.dim):
                kb = ConstantKernel(0.5, (1e-3, 15.0)) * Matern(
                    length_scale=np.full(self.dim, 0.65),
                    length_scale_bounds=(0.15, 3.0),
                    nu=2.5,
                ) + WhiteKernel(noise_level=0.01, noise_level_bounds=(1e-4, 0.5))
                gp_k = GaussianProcessRegressor(kernel=kb, normalize_y=True, n_restarts_optimizer=0, random_state=k)
                gp_k.fit(self.X_obs, b_obs[:, k])
                self.b_gps.append(gp_k)
                self._b_fast.append(self._extract_matern25_struct(gp_k))

    def _extract_matern25_struct(self, gp: GaussianProcessRegressor) -> dict:
        k_prod = gp.kernel_.k1
        c_val = float(k_prod.k1.constant_value)
        ell = np.atleast_1d(np.asarray(k_prod.k2.length_scale, dtype=float))
        if ell.size == 1:
            ell = np.full(self.dim, float(ell[0]))
        noise_var = float(gp.kernel_.k2.noise_level)
        y_std = float(np.atleast_1d(gp._y_train_std)[0])
        y_mean = float(np.atleast_1d(gp._y_train_mean)[0])
        return {
            "c_val": c_val,
            "ell": ell,
            "X_scaled": self.X_obs / ell[None, :],
            "alpha_scaled": gp.alpha_ * y_std,
            "y_mean": y_mean,
            "y_std": y_std,
            "L": gp.L_,
            "obs_noise_std": np.sqrt(noise_var) * y_std,
        }

    def _cache_fast_matern_params(self) -> None:
        self._q_fast = self._extract_matern25_struct(self.gp_q)

    @staticmethod
    def _eval_matern25_kernel(X_q: np.ndarray, st: dict) -> np.ndarray:
        Xq_s = np.atleast_2d(X_q) / st["ell"][None, :]
        d = cdist(Xq_s, st["X_scaled"], metric="euclidean")
        s = np.sqrt(5.0) * d
        return st["c_val"] * (1.0 + s + (s ** 2) / 3.0) * np.exp(-s)

    def predict_q(self, X: np.ndarray) -> np.ndarray:
        K_star = self._eval_matern25_kernel(X, self._q_fast)
        mean = self._q_fast["y_mean"] + K_star @ self._q_fast["alpha_scaled"]
        return np.maximum(0.0, mean)

    def predict_q_latent_std(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        from scipy.linalg import solve_triangular
        st = self._q_fast
        K_star = self._eval_matern25_kernel(X, st)
        mean = np.maximum(0.0, st["y_mean"] + K_star @ st["alpha_scaled"])
        V = solve_triangular(st["L"], K_star.T, lower=True, check_finite=False)
        lat_var = np.maximum(st["c_val"] - np.einsum("ij,ij->j", V, V), 0.0)
        lat_std = np.sqrt(lat_var) * st["y_std"]
        return mean, lat_std, float(st["obs_noise_std"])

    def predict_b(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        if not self._b_fast:
            return np.zeros_like(X, dtype=float)
        cols = []
        for st in self._b_fast:
            K_star = self._eval_matern25_kernel(X, st)
            cols.append(st["y_mean"] + K_star @ st["alpha_scaled"])
        return np.column_stack(cols)


def _eval_segment_goal_union_hit(
    X_prev: np.ndarray, X_next: np.ndarray, goals: Sequence[GoalBall]
) -> Tuple[np.ndarray, np.ndarray]:
    """Checks continuous line-segment sphere intersection `min_{t in [0, 1]} ||X_prev + t*(X_next - X_prev) - c_j|| <= r_j`
    in addition to endpoint inclusion, reducing finite-`dt` boundary-crossing overshoot bias.
    """
    hit_end, phi_end = eval_goal_union(X_next, goals)
    dX = X_next - X_prev
    seg_len2 = np.sum(dX ** 2, axis=1)
    in_any = hit_end.copy()
    phi_min = np.where(hit_end, phi_end, np.inf)
    for g in goals:
        c = np.asarray(g.center, dtype=float)[None, :]
        rel = c - X_prev
        t_star = np.where(seg_len2 > 1e-24, np.clip(np.sum(rel * dX, axis=1) / np.maximum(seg_len2, 1e-24), 0.0, 1.0), 0.0)
        closest = X_prev + t_star[:, None] * dX
        mask = np.sum((closest - c) ** 2, axis=1) <= (g.radius ** 2)
        if np.any(mask):
            in_any |= mask
            phi_min[mask] = np.minimum(phi_min[mask], g.phi)
    phi_min[~in_any] = 0.0
    return in_any, phi_min


def simulate_closed_loop_crn(
    world: GroundTruthWorld,
    policy_fn: Callable[[np.ndarray], np.ndarray],
    query: QueryTask,
    n_per_start: int = 16,
    seed: int = 2026,
    u_clip_safety: float = 25.0,
    dt_override: Optional[float] = None,
    substep_segment_hit: bool = False,
) -> dict:
    """Closed-loop rollout with per-trajectory CRN streams, `t=0` immediate goal absorption,
    specular reflection, post-step (or segment) union absorption, and explicit cost/clip diagnostics.
    """
    spec = world.spec
    dt = spec.dt_sim if dt_override is None else float(dt_override)
    max_steps = spec.max_steps if dt_override is None else int(round(spec.max_steps * spec.dt_sim / dt))
    sqrt_dt = np.sqrt(dt)
    R_vec = spec.R_vec

    starts = np.repeat(np.asarray(query.start_points, dtype=float), n_per_start, axis=0)
    n_traj = starts.shape[0]
    X = reflect_into_box(starts.copy(), spec.half_width)

    ss = np.random.SeedSequence([seed, len(query.goals), int(abs(query.goals[0].center[0]) * 1000)])
    traj_rngs = [np.random.default_rng(s) for s in ss.spawn(n_traj)]

    hit0, phi0 = eval_goal_union(X, query.goals)
    alive = ~hit0
    running_cost = np.zeros(n_traj, dtype=float)
    terminal_cost = np.where(hit0, phi0, 0.0)
    steps_taken = np.zeros(n_traj, dtype=int)
    clipped_steps = 0
    total_active_steps = 0

    for _step in range(max_steps):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        X_act = X[idx]
        u = np.asarray(policy_fn(X_act), dtype=float)
        if spec.u_max is not None:
            unorm = np.linalg.norm(u, axis=1, keepdims=True)
            over = unorm[:, 0] > spec.u_max + 1e-9
            clipped_steps += int(np.sum(over))
            u = np.where(unorm > spec.u_max, u * (spec.u_max / np.maximum(unorm, 1e-12)), u)
        else:
            unorm = np.linalg.norm(u, axis=1, keepdims=True)
            over = unorm[:, 0] > u_clip_safety
            clipped_steps += int(np.sum(over))
            u = np.where(unorm > u_clip_safety, u * (u_clip_safety / np.maximum(unorm, 1e-12)), u)
        total_active_steps += idx.size

        q_val = world.q_total(X_act, query.local_hazards)
        ctrl_quad = 0.5 * np.sum((u ** 2) * R_vec[None, :], axis=1)
        running_cost[idx] += (q_val + ctrl_quad) * dt

        b_val = world.drift(X_act)
        dW = np.vstack([traj_rngs[i].normal(0.0, sqrt_dt, size=spec.dim) for i in idx])
        X_next = reflect_into_box(X_act + (b_val + u) * dt + spec.sigma * dW, spec.half_width)
        X[idx] = X_next
        steps_taken[idx] += 1

        if substep_segment_hit:
            hit_post, phi_post = _eval_segment_goal_union_hit(X_act, X_next, query.goals)
        else:
            hit_post, phi_post = eval_goal_union(X_next, query.goals)
        if np.any(hit_post):
            newly_done = idx[hit_post]
            terminal_cost[newly_done] += phi_post[hit_post]
            alive[newly_done] = False

    timeout_penalty = np.zeros(n_traj, dtype=float)
    if np.any(alive):
        min_goal_dist = np.min(
            np.column_stack([
                np.maximum(0.0, np.linalg.norm(X[alive] - np.asarray(g.center)[None, :], axis=1) - g.radius)
                for g in query.goals
            ]),
            axis=1,
        )
        timeout_penalty[alive] = 4.0 + 2.0 * min_goal_dist

    total_cost = running_cost + terminal_cost + timeout_penalty
    return {
        "mean_cost": float(np.mean(total_cost)),
        "mean_running_plus_terminal_cost": float(np.mean(running_cost + terminal_cost)),
        "mean_timeout_penalty": float(np.mean(timeout_penalty)),
        "std_cost": float(np.std(total_cost) / np.sqrt(n_traj)),
        "reach_rate": float(np.mean(~alive)),
        "timeout_rate": float(np.mean(alive)),
        "mean_steps": float(np.mean(steps_taken)),
        "clip_fraction": float(clipped_steps / max(total_active_steps, 1)),
        "traj_costs": total_cost,
    }


def paired_stats(diffs: Sequence[float], noninferiority_margin: Optional[float] = None) -> dict:
    """Map-paired mean, Student-t 95% CI `[lo, hi]`, two-sided p-value, and one-sided NI test."""
    arr = np.asarray(diffs, dtype=float)
    n = arr.size
    mean = float(np.mean(arr))
    if n <= 1:
        return {"n": int(n), "mean": mean, "ci95_half": 0.0, "ci95": [mean, mean], "p_two_sided": 1.0}
    se = float(np.std(arr, ddof=1) / np.sqrt(n))
    if se < 1e-16:
        p2 = 1.0 if abs(mean) < 1e-16 else 0.0
        out = {"n": int(n), "mean": mean, "ci95_half": 0.0, "ci95": [mean, mean], "p_two_sided": p2}
        if noninferiority_margin is not None:
            out["noninferiority_margin"] = float(noninferiority_margin)
            out["upper_95_one_sided"] = mean
            out["p_noninferior"] = 0.0 if mean < noninferiority_margin else 1.0
            out["noninferior_at_alpha_0_05"] = bool(mean < noninferiority_margin)
        return out
    t_crit = float(student_t.ppf(0.975, df=n - 1))
    half = t_crit * se
    t_stat = mean / se
    p_two = float(2.0 * student_t.sf(abs(t_stat), df=n - 1))
    out = {
        "n": int(n),
        "mean": mean,
        "ci95_half": half,
        "ci95": [mean - half, mean + half],
        "p_two_sided": p_two,
    }
    if noninferiority_margin is not None:
        t_ni = (mean - float(noninferiority_margin)) / se
        p_ni = float(student_t.cdf(t_ni, df=n - 1))
        out["noninferiority_margin"] = float(noninferiority_margin)
        out["upper_95_one_sided"] = float(mean + float(student_t.ppf(0.95, df=n - 1)) * se)
        out["p_noninferior"] = p_ni
        out["noninferior_at_alpha_0_05"] = bool(p_ni < 0.05)
    return out


def paired_relative_noninferiority(
    method_costs: Sequence[float],
    ref_costs: Sequence[float],
    rel_margin_pct: float = 3.5,
) -> dict:
    """Scale-equivariant per-map paired relative non-inferiority test (`GPT6 Audit Finding 5`):
      1. Linearized contrast `d_m = C_{method,m} - (1 + delta) * C_{ref,m}` tested against `< 0`;
      2. Direct per-map percentage excess `pct_m = 100 * (C_{method,m} / C_{ref,m} - 1)` tested against `< rel_margin_pct`.
    """
    cm = np.asarray(method_costs, dtype=float)
    cr = np.asarray(ref_costs, dtype=float)
    delta = float(rel_margin_pct) / 100.0
    contrast = cm - (1.0 + delta) * cr
    pct_excess = 100.0 * (cm / np.maximum(cr, 1e-12) - 1.0)
    lin_res = paired_stats(contrast, noninferiority_margin=0.0)
    pct_res = paired_stats(pct_excess, noninferiority_margin=float(rel_margin_pct))
    return {
        "rel_margin_pct": float(rel_margin_pct),
        "primary_estimand": "linearized_contrast_vs_0",
        "primary_p_noninferior": float(lin_res["p_noninferior"]),
        "primary_noninferior_at_alpha_0_05": bool(lin_res["noninferior_at_alpha_0_05"]),
        "linearized_contrast_vs_0": lin_res,
        "per_map_pct_excess": pct_res,
    }
