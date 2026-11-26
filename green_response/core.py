"""Unified Core Specification, Capability Guards, Reflection Mechanics, Same-GP Kriging,
8-Core Process-Parallel Map Runner, and Scale-Equivariant Paired Statistics (`green_response.core`).
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import math
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple, TypeVar

import numpy as np
import scipy
import sklearn
from scipy.spatial.distance import cdist
from scipy.stats import norm, t as student_t
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel

T_In = TypeVar("T_In")
T_Out = TypeVar("T_Out")

_THREAD_ENV_KEYS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)


def enforce_single_thread_env(force: bool = False) -> dict:
    """Pins BLAS/OpenMP thread environment variables to 1 (avoiding intra-process lock contention)."""
    for k in _THREAD_ENV_KEYS:
        if force:
            os.environ[k] = "1"
        else:
            os.environ.setdefault(k, "1")
    try:
        from threadpoolctl import threadpool_limits  # type: ignore
        threadpool_limits(limits=1)
    except Exception:
        pass
    return {k: os.environ.get(k, "") for k in _THREAD_ENV_KEYS}


def _worker_init_single_thread() -> None:
    """Initializer for each worker process in `run_map_parallel`: strictly pins BLAS/OpenMP to 1 thread."""
    enforce_single_thread_env(force=True)


def run_map_parallel(
    worker_fn: Callable[[T_In], T_Out],
    items: Sequence[T_In],
    max_workers: int = 8,
) -> List[T_Out]:
    """Executes independent map/seed tasks across up to `max_workers` OS processes (default 8 cores)
    while pinning each worker's internal BLAS/OpenMP threadpool to 1 thread (eliminating nested
    intra-process thread oversubscription; OS process-level cache/memory bandwidth remains shared).
    Preserves input order.
    """
    item_list = list(items)
    if not item_list:
        return []
    n_eff = min(int(max_workers), len(item_list), os.cpu_count() or 8)
    if n_eff <= 1:
        enforce_single_thread_env(force=True)
        return [worker_fn(it) for it in item_list]
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=n_eff, initializer=_worker_init_single_thread
    ) as ex:
        return list(ex.map(worker_fn, item_list))


def compute_source_manifest() -> dict:
    """Computes an immutable SHA-256 manifest of all `green_response/*.py` sources plus Git status."""
    pkg_dir = Path(__file__).resolve().parent
    repo_dir = pkg_dir.parent
    per_file: Dict[str, str] = {}
    agg = hashlib.sha256()
    for py_path in sorted(pkg_dir.glob("*.py")):
        raw = py_path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        per_file[py_path.name] = digest
        agg.update(f"{py_path.name}:{digest}\n".encode("utf-8"))
    git_sha = "unknown"
    git_dirty = None
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_dir), text=True, stderr=subprocess.DEVNULL
        ).strip()
        st_out = subprocess.check_output(
            ["git", "status", "--porcelain", "green_response"],
            cwd=str(repo_dir),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        git_dirty = bool(len(st_out) > 0)
    except Exception:
        pass
    return {
        "git_head_sha": git_sha,
        "git_dirty_green_response": git_dirty,
        "package_py_sha256": agg.hexdigest(),
        "per_file_sha256": per_file,
    }


def collect_runtime_metadata(max_workers: int = 1) -> dict:
    pool_info = None
    try:
        from threadpoolctl import threadpool_info  # type: ignore
        pool_info = threadpool_info()
    except Exception:
        pool_info = "threadpoolctl_unavailable"
    src_manifest = compute_source_manifest()
    return {
        "git_head_sha": src_manifest["git_head_sha"],
        "git_dirty_green_response": src_manifest["git_dirty_green_response"],
        "package_py_sha256": src_manifest["package_py_sha256"],
        "source_manifest": src_manifest,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "configured_parallel_workers": int(max_workers),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "sklearn_version": sklearn.__version__,
        "thread_env": {k: os.environ.get(k, "unset") for k in _THREAD_ENV_KEYS},
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


_VALID_CERT_STATUSES = {"epsilon_certified", "unresolved", "numeric_invalid", "heuristic"}
_PROTECTED_CERT_KEYS = {
    "status",
    "certified",
    "certificate_kind",
    "certificate_scope",
    "epsilon_tol",
    "lower_bound",
    "upper_bound",
    "stop_reason",
    "operator_epoch",
    "work",
}


def _validate_typed_policy_entry(key: str, val: object) -> None:
    if val is None:
        raise ValueError(f"certified=True cannot have {key}=None.")
    if key == "policy_action_idx":
        if not (isinstance(val, np.ndarray) and val.size > 0 and np.issubdtype(val.dtype, np.integer)):
            raise ValueError(f"certified=True requires non-empty integer ndarray for policy_action_idx, got {type(val).__name__}.")
    elif key in ("select_next_waypoint", "policy"):
        if not callable(val):
            raise ValueError(f"certified=True requires callable for {key}, got {type(val).__name__}.")
    elif key == "best_order":
        if not (isinstance(val, (tuple, list)) and len(val) > 0 and all(isinstance(x, (int, np.integer)) for x in val)):
            raise ValueError(f"certified=True requires non-empty integer sequence for best_order, got {val!r}.")


@dataclass
class IntervalCertificate:
    """Fail-closed validated certificate contract (`ddd19c5` + `29fa7c6` Audit Closure):
      - Enforces finite ordered `[lower_bound, upper_bound]`, valid `status`, non-negative `operator_epoch`,
        explicit `certificate_kind` (`"policy_and_value_enclosure"` vs `"value_only_enclosure"`), and
        strictly typed actionable policy references whenever `certified=True` (unless `allow_value_only=True`);
      - Prevents `extras` from overwriting any validated core certificate field!
    """
    status: str  # "epsilon_certified" | "unresolved" | "numeric_invalid" | "heuristic"
    certified: bool
    certificate_scope: str
    epsilon_tol: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    stop_reason: str = ""
    operator_epoch: int = 0
    work: Optional[dict] = None
    extras: Optional[dict] = None
    allow_value_only: bool = False

    def __post_init__(self) -> None:
        if self.status not in _VALID_CERT_STATUSES:
            raise ValueError(f"Invalid certificate status: {self.status!r}")
        if not math.isfinite(float(self.epsilon_tol)) or float(self.epsilon_tol) < 0.0:
            raise ValueError(f"Invalid epsilon_tol: {self.epsilon_tol!r}")
        if int(self.operator_epoch) < 0:
            raise ValueError(f"Invalid negative operator_epoch: {self.operator_epoch!r}")
        self.operator_epoch = int(self.operator_epoch)
        self.certified = bool(self.certified)
        self.allow_value_only = bool(self.allow_value_only)

        if self.status == "numeric_invalid" and self.certified:
            raise ValueError("numeric_invalid certificate cannot have certified=True.")

        if self.lower_bound is not None or self.upper_bound is not None:
            if self.lower_bound is None or self.upper_bound is None:
                raise ValueError("lower_bound and upper_bound must both be finite floats or both None.")
            lo = float(self.lower_bound)
            hi = float(self.upper_bound)
            if not (math.isfinite(lo) and math.isfinite(hi)):
                raise ValueError(f"Non-finite certificate bounds: [{lo}, {hi}]")
            if lo > hi:
                raise ValueError(f"Inverted certificate bounds: [{lo}, {hi}]")
            self.lower_bound = lo
            self.upper_bound = hi

        if self.certified:
            if self.status != "epsilon_certified":
                raise ValueError(f"certified=True requires status='epsilon_certified', got {self.status!r}")
            if self.lower_bound is None or self.upper_bound is None:
                raise ValueError("certified=True requires finite lower_bound and upper_bound.")
            gap = self.upper_bound - self.lower_bound
            if gap > float(self.epsilon_tol) + 1e-12 * (1.0 + abs(self.upper_bound)):
                raise ValueError(
                    f"certified=True with gap={gap} exceeding epsilon_tol={self.epsilon_tol}."
                )
            policy_keys = ("policy_action_idx", "select_next_waypoint", "best_order", "policy")
            if not self.allow_value_only:
                if not self.extras or not any(k in self.extras for k in policy_keys):
                    raise ValueError(
                        "certified=True requires a non-null typed actionable policy reference in extras "
                        f"({policy_keys}) unless allow_value_only=True."
                    )
            if self.extras:
                for pk in policy_keys:
                    if pk in self.extras:
                        _validate_typed_policy_entry(pk, self.extras[pk])

        if self.extras:
            illegal_overlap = _PROTECTED_CERT_KEYS.intersection(self.extras.keys())
            if illegal_overlap:
                raise ValueError(
                    f"IntervalCertificate.extras cannot override protected core keys: {sorted(illegal_overlap)}"
                )

    @property
    def certificate_kind(self) -> str:
        return "value_only_enclosure" if self.allow_value_only else "policy_and_value_enclosure"

    def to_dict(self) -> dict:
        out = {} if self.extras is None else dict(self.extras)
        out.update({
            "status": self.status,
            "certified": bool(self.certified),
            "certificate_kind": self.certificate_kind,
            "certificate_scope": self.certificate_scope,
            "epsilon_tol": float(self.epsilon_tol),
            "lower_bound": None if self.lower_bound is None else float(self.lower_bound),
            "upper_bound": None if self.upper_bound is None else float(self.upper_bound),
            "stop_reason": self.stop_reason,
            "operator_epoch": int(self.operator_epoch),
            "work": {} if self.work is None else dict(self.work),
        })
        return out

    def __getitem__(self, key: str):
        return self.to_dict()[key]

    def get(self, key: str, default=None):
        return self.to_dict().get(key, default)

    def keys(self) -> Iterable[str]:
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
    elif regime == "competing_corridor":
        # Twin-gate / competing-pass ridge (`29fa7c6` bifurcation regime):
        # A central dividing barrier splits the domain into two competing passes (`pass_a` vs `pass_b`),
        # one genuinely clear and one holding a localized choke hazard (`sigma ~ 0.14`) that sparse
        # initial probes may miss or mis-smooth across passes!
        axis_cut = int(rng.integers(0, min(dim, 2)))
        other_ax = 1 - axis_cut
        ridge_pos = float(rng.uniform(-0.18, 0.18))
        for seg_pos in (-1.28, -0.02, 1.28):
            c_seg = np.zeros(dim, dtype=float)
            c_seg[axis_cut] = ridge_pos
            c_seg[other_ax] = seg_pos
            sig_seg = np.full(dim, 0.36, dtype=float)
            sig_seg[axis_cut] = 0.095
            sig_seg[other_ax] = 0.28
            hazards.append(HazardFeature(tuple(c_seg.tolist()), float(rng.uniform(16.0, 22.0)), tuple(sig_seg.tolist())))
        blocked_side = float(rng.choice([-1.0, 1.0]))
        c_choke = np.zeros(dim, dtype=float)
        c_choke[axis_cut] = ridge_pos + float(rng.uniform(-0.08, 0.08))
        c_choke[other_ax] = blocked_side * float(rng.uniform(0.58, 0.72))
        sig_choke = np.full(dim, 0.15, dtype=float)
        hazards.append(HazardFeature(tuple(c_choke.tolist()), float(rng.uniform(17.0, 24.0)), tuple(sig_choke.tolist())))
        for _ in range(2):
            c_bg = rng.uniform(-1.05, 1.05, size=dim)
            if abs(c_bg[other_ax] + blocked_side * 0.65) < 0.32 and abs(c_bg[axis_cut] - ridge_pos) < 0.35:
                c_bg[other_ax] *= -1.0  # keep the alternative pass genuinely clear
            sig_bg = rng.uniform(0.18, 0.28, size=dim)
            hazards.append(HazardFeature(tuple(c_bg.tolist()), float(rng.uniform(4.5, 8.5)), tuple(sig_bg.tolist())))
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


def observe_world_at_points(
    world: GroundTruthWorld,
    X: np.ndarray,
    rng: np.random.Generator,
    q_noise_std: float = 0.28,
    b_noise_std: float = 0.08,
    include_drift: bool = True,
) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """Evaluates noisy world probes at specified coordinates `X` (used for sequential active sensing)."""
    X_arr = np.atleast_2d(np.asarray(X, dtype=float))
    q_obs = np.maximum(0.0, world.q_hidden(X_arr) + rng.normal(0.0, q_noise_std, size=len(X_arr)))
    if not include_drift:
        return X_arr, q_obs, None
    b_obs = world.drift(X_arr) + rng.normal(0.0, b_noise_std, size=(len(X_arr), world.spec.dim))
    return X_arr, q_obs, b_obs


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
    return observe_world_at_points(
        world, X, rng, q_noise_std=q_noise_std, b_noise_std=b_noise_std, include_drift=include_drift
    )


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

    @staticmethod
    def _eval_matern25_kernel_pair(X_a: np.ndarray, X_b: np.ndarray, st: dict) -> np.ndarray:
        Xa_s = np.atleast_2d(X_a) / st["ell"][None, :]
        Xb_s = np.atleast_2d(X_b) / st["ell"][None, :]
        d = cdist(Xa_s, Xb_s, metric="euclidean")
        s = np.sqrt(5.0) * d
        return st["c_val"] * (1.0 + s + (s ** 2) / 3.0) * np.exp(-s)

    def predict_q_raw_latent_mean(self, X: np.ndarray) -> np.ndarray:
        K_star = self._eval_matern25_kernel(X, self._q_fast)
        return self._q_fast["y_mean"] + K_star @ self._q_fast["alpha_scaled"]

    def predict_q(self, X: np.ndarray) -> np.ndarray:
        return np.maximum(0.0, self.predict_q_raw_latent_mean(X))

    def predict_q_latent_std(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        from scipy.linalg import solve_triangular
        st = self._q_fast
        K_star = self._eval_matern25_kernel(X, st)
        mean = np.maximum(0.0, st["y_mean"] + K_star @ st["alpha_scaled"])
        V = solve_triangular(st["L"], K_star.T, lower=True, check_finite=False)
        lat_var = np.maximum(st["c_val"] - np.einsum("ij,ij->j", V, V), 0.0)
        lat_std = np.sqrt(lat_var) * st["y_std"]
        return mean, lat_std, float(st["obs_noise_std"])

    def _build_channel_posterior_cov_and_proj(
        self,
        st: dict,
        cand_pts: np.ndarray,
        grid_pts: Optional[np.ndarray] = None,
        W: Optional[np.ndarray] = None,
        pending_X: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, Optional[np.ndarray], float]:
        from scipy.linalg import solve_triangular
        K_cc = self._eval_matern25_kernel_pair(cand_pts, cand_pts, st)
        K_co = self._eval_matern25_kernel(cand_pts, st)
        V_c = solve_triangular(st["L"], K_co.T, lower=True, check_finite=False)
        y2 = float(st["y_std"] ** 2)
        C_cc = y2 * (K_cc - (V_c.T @ V_c))
        noise_var = float(st["obs_noise_std"] ** 2)

        has_proj = grid_pts is not None and W is not None and W.size > 0
        if has_proj:
            K_cg = self._eval_matern25_kernel_pair(cand_pts, grid_pts, st)
            K_go = self._eval_matern25_kernel(grid_pts, st)
            V_g = solve_triangular(st["L"], K_go.T, lower=True, check_finite=False)
            VW = V_g @ W
            G_cf: Optional[np.ndarray] = y2 * ((K_cg @ W) - (V_c.T @ VW))
        else:
            V_g = None
            VW = None
            G_cf = None

        if pending_X is not None and len(pending_X) > 0:
            pend_arr = np.atleast_2d(np.asarray(pending_X, dtype=float))
            K_pp = self._eval_matern25_kernel_pair(pend_arr, pend_arr, st)
            K_po = self._eval_matern25_kernel(pend_arr, st)
            V_p = solve_triangular(st["L"], K_po.T, lower=True, check_finite=False)
            S_pp = y2 * (K_pp - (V_p.T @ V_p))
            S_pp = 0.5 * (S_pp + S_pp.T)
            idx_p = np.arange(len(pend_arr))
            S_pp[idx_p, idx_p] = np.maximum(np.diag(S_pp), 0.0) + max(noise_var, 1e-12)
            L_p = np.linalg.cholesky(S_pp)

            K_cp = self._eval_matern25_kernel_pair(cand_pts, pend_arr, st)
            C_cp = y2 * (K_cp - (V_c.T @ V_p))
            U_cp_T = solve_triangular(L_p, C_cp.T, lower=True, check_finite=False)
            C_cc = C_cc - (U_cp_T.T @ U_cp_T)

            if has_proj and G_cf is not None and VW is not None:
                K_gp = self._eval_matern25_kernel_pair(grid_pts, pend_arr, st)
                G_pf = y2 * ((K_gp.T @ W) - (V_p.T @ VW))
                U_pf = solve_triangular(L_p, G_pf, lower=True, check_finite=False)
                G_cf = G_cf - (U_cp_T.T @ U_pf)

        idx_d = np.arange(len(cand_pts))
        C_cc[idx_d, idx_d] = np.maximum(C_cc[idx_d, idx_d], 0.0)
        return C_cc, G_cf, noise_var

    def select_sequential_conditional_maxvar_probes(
        self,
        cand_pts: np.ndarray,
        existing_X: np.ndarray,
        n_select: int,
        min_repel: float = 0.24,
        pending_X: Optional[np.ndarray] = None,
        include_drift_channels: bool = False,
        drift_std_weight: float = 0.25,
    ) -> np.ndarray:
        """Sequential Schur-complement conditional uncertainty selector with explicit distinction between:
          - `existing_X`: already-observed training points (used for geometric repulsion; already conditioned in `self.gp_*`),
          - `pending_X`: newly chosen but not-yet-fitted pending observation coordinates (arbitrary off-grid or on-grid
            points conditioned into `C_q` and `C_b` via exact block-Cholesky Schur complement BEFORE selecting probes,
            and also included in geometric repulsion),
          - `include_drift_channels`: when True, scores `std_cond(q) + drift_std_weight * sum_d std_cond(b_d)` to match
            the multi-channel sentinel objective used by Green active acquisition.
        """
        cand_arr = np.atleast_2d(np.asarray(cand_pts, dtype=float))
        if n_select <= 0 or len(cand_arr) == 0:
            return np.empty((0, self.dim), dtype=float)
        pend_arr = (
            np.atleast_2d(np.asarray(pending_X, dtype=float))
            if (pending_X is not None and len(pending_X) > 0)
            else None
        )
        try:
            C_q, _, nz_q = self._build_channel_posterior_cov_and_proj(self._q_fast, cand_arr, pending_X=pend_arr)
        except TypeError:
            # Backward-compatible fallback for unit-test stubs with 3-arg `_build_channel_posterior_cov_and_proj`
            C_q, _, nz_q = self._build_channel_posterior_cov_and_proj(self._q_fast, cand_arr)
            if pend_arr is not None:
                for p_pt in pend_arr:
                    d_p = np.linalg.norm(cand_arr - p_pt[None, :], axis=1)
                    j_p = int(np.argmin(d_p))
                    if d_p[j_p] <= 1e-10:
                        denom_p = max(float(C_q[j_p, j_p] + nz_q), 1e-12)
                        col_p = C_q[:, j_p]
                        C_q = C_q - np.outer(col_p, col_p) / denom_p

        b_covs = []
        if include_drift_channels and getattr(self, "_b_fast", None):
            for st_b in self._b_fast:
                C_b, _, nz_b = self._build_channel_posterior_cov_and_proj(st_b, cand_arr, pending_X=pend_arr)
                b_covs.append([C_b, nz_b])

        base_X = np.atleast_2d(np.asarray(existing_X, dtype=float)).copy()
        cur_X = np.vstack([base_X, pend_arr]) if pend_arr is not None else base_X
        rem_mask = np.ones(len(cand_arr), dtype=bool)
        if pend_arr is not None:
            d_to_pend = np.min(np.linalg.norm(cand_arr[:, None, :] - pend_arr[None, :, :], axis=2), axis=1)
            rem_mask &= d_to_pend > 1e-12
        idx_diag = np.arange(len(cand_arr))
        chosen = []
        for _ in range(n_select):
            if not np.any(rem_mask):
                break
            lat_std = np.sqrt(np.maximum(np.diag(C_q), 0.0))
            for C_b, _ in b_covs:
                lat_std = lat_std + drift_std_weight * np.sqrt(np.maximum(np.diag(C_b), 0.0))
            d_min = np.min(np.linalg.norm(cand_arr[:, None, :] - cur_X[None, :, :], axis=2), axis=1)
            rep_w = np.minimum(1.0, (d_min / max(min_repel, 1e-9)) ** 2)
            eff = np.where(rem_mask, lat_std * rep_w, -np.inf)
            best_i = int(np.argmax(eff))
            rem_mask[best_i] = False
            chosen.append(cand_arr[best_i])
            cur_X = np.vstack([cur_X, cand_arr[best_i : best_i + 1]])
            denom = max(float(C_q[best_i, best_i] + nz_q), 1e-12)
            col = C_q[:, best_i]
            C_q = C_q - np.outer(col, col) / denom
            C_q[idx_diag, idx_diag] = np.maximum(np.diag(C_q), 0.0)
            for ch in b_covs:
                C_b, nz_b = ch
                denom_b = max(float(C_b[best_i, best_i] + nz_b), 1e-12)
                col_b = C_b[:, best_i]
                C_b_new = C_b - np.outer(col_b, col_b) / denom_b
                C_b_new[idx_diag, idx_diag] = np.maximum(np.diag(C_b_new), 0.0)
                ch[0] = C_b_new
        return np.array(chosen, dtype=float) if chosen else np.empty((0, self.dim), dtype=float)

    def select_sequential_kg_voi_probes(
        self,
        cand_pts: np.ndarray,
        grid_pts: np.ndarray,
        task_sens_list: Sequence[dict],
        existing_X: np.ndarray,
        n_decision: int = 11,
        n_sentinel: int = 3,
        min_repel: float = 0.24,
        val_reg_weight: float = 0.15,
        include_drift_sensitivity: bool = True,
        condition_decision_probes: bool = True,
        sentinel_drift_weight: float = 0.25,
    ) -> Tuple[np.ndarray, dict]:
        """Goal-Oriented Local-Linearized `(q, b)` Green Response Acquisition Selector (`57e5912` Refined):
          - When `alt_branches` are empty (`max_alt_branches=0`, `Green-ValueOnly-Cond`), acts as a pure
            goal-oriented linear-functional posterior std-reduction rule (`acquisition_proxy_kind="value_only_linear_functional_std"`);
          - When `alt_branches` are non-empty, adds the **pairwise local-linear Knowledge-Gradient acquisition proxy**
            `sum_j [s_j phi(mu_j / s_j) - mu_j Phi(-mu_j)]` (`acquisition_proxy_kind="pairwise_local_linear_kg_proxy"`,
            explicitly scoped as a sum-of-pairwise Gaussian opportunity proxy under frozen batch means/branches,
            NOT exact correlated joint multi-alternative KG);
          - Supports clean 2x2 factorial toggles (`include_drift_sensitivity` x `condition_decision_probes`) while
            keeping the `n_sentinel` `(q, b)` sentinels strictly conditioned on all `n_decision` pending probes!
        """
        cand_arr = np.atleast_2d(np.asarray(cand_pts, dtype=float))
        mu_q_raw = self.predict_q_raw_latent_mean(grid_pts)
        q_chain_mask = (mu_q_raw > 0.0).astype(float)
        active_q_frac = float(np.mean(q_chain_mask))

        wq_cols: List[np.ndarray] = []
        wb_cols_by_ax: List[List[np.ndarray]] = [[] for _ in range(self.dim)]
        func_meta: List[Tuple[str, float]] = []  # ("opt", 0.0) or ("gap", gap_mu)

        for sens in task_sens_list:
            gq_opt = np.asarray(sens["grad_q_optimal"], dtype=float) * q_chain_mask
            wq_cols.append(gq_opt)
            gb_opt = sens.get("grad_b_optimal") if include_drift_sensitivity else None
            for ax in range(self.dim):
                wb_cols_by_ax[ax].append(
                    np.zeros(len(grid_pts), dtype=float) if gb_opt is None else np.asarray(gb_opt[:, ax], dtype=float)
                )
            func_meta.append(("opt", 0.0))

            alt_list = sens.get("alt_branches")
            if alt_list is None:
                if (
                    sens.get("runner_up_wp") != sens.get("incumbent_wp")
                    and sens.get("grad_q_top_gap") is not None
                ):
                    alt_list = [{
                        "gap": float(max(0.0, sens["action_gap"])),
                        "grad_q_gap": sens["grad_q_top_gap"],
                        "grad_b_gap": sens.get("grad_b_top_gap"),
                    }]
                else:
                    alt_list = []
            for br in alt_list:
                mu_gap = float(max(0.0, br["gap"]))
                wq_cols.append(np.asarray(br["grad_q_gap"], dtype=float) * q_chain_mask)
                gb_g = br.get("grad_b_gap") if include_drift_sensitivity else None
                for ax in range(self.dim):
                    wb_cols_by_ax[ax].append(
                        np.zeros(len(grid_pts), dtype=float) if gb_g is None else np.asarray(gb_g[:, ax], dtype=float)
                    )
                func_meta.append(("gap", mu_gap))

        W_q = np.column_stack(wq_cols) if wq_cols else np.zeros((len(grid_pts), 0), dtype=float)
        C_q, G_q, nz_q = self._build_channel_posterior_cov_and_proj(self._q_fast, cand_arr, grid_pts, W_q)

        b_channels = []
        if self._b_fast:
            for ax, st_b in enumerate(self._b_fast):
                if include_drift_sensitivity and wq_cols:
                    W_b_ax = np.column_stack(wb_cols_by_ax[ax])
                    C_b, G_b, nz_b = self._build_channel_posterior_cov_and_proj(st_b, cand_arr, grid_pts, W_b_ax)
                else:
                    C_b, G_b, nz_b = self._build_channel_posterior_cov_and_proj(st_b, cand_arr)
                b_channels.append([C_b, G_b, nz_b])

        opt_indices = [idx for idx, (kind, _) in enumerate(func_meta) if kind == "opt"]
        gap_entries = [(idx, mu_g) for idx, (kind, mu_g) in enumerate(func_meta) if kind == "gap"]

        cur_X = np.atleast_2d(np.asarray(existing_X, dtype=float)).copy()
        rem_mask = np.ones(len(cand_arr), dtype=bool)
        chosen_dec = []
        chosen_dec_idx: List[int] = []
        chosen_sen = []
        idx_diag = np.arange(len(cand_arr))

        def _downdate_all_channels(sel_i: int) -> None:
            nonlocal C_q, G_q
            dq = max(float(C_q[sel_i, sel_i] + nz_q), 1e-12)
            col_q = C_q[:, sel_i]
            if G_q is not None:
                G_q = G_q - np.outer(col_q, G_q[sel_i, :]) / dq
            C_q = C_q - np.outer(col_q, col_q) / dq
            C_q[idx_diag, idx_diag] = np.maximum(np.diag(C_q), 0.0)
            for ch in b_channels:
                C_b, G_b, nz_b = ch
                db = max(float(C_b[sel_i, sel_i] + nz_b), 1e-12)
                col_b = C_b[:, sel_i]
                if G_b is not None:
                    ch[1] = G_b - np.outer(col_b, G_b[sel_i, :]) / db
                C_b_new = C_b - np.outer(col_b, col_b) / db
                C_b_new[idx_diag, idx_diag] = np.maximum(np.diag(C_b_new), 0.0)
                ch[0] = C_b_new

        for _ in range(n_decision):
            if not np.any(rem_mask):
                break
            if G_q is None or G_q.shape[1] == 0:
                score_raw = np.sqrt(np.maximum(np.diag(C_q), 0.0))
            else:
                denom_q = np.maximum(np.diag(C_q) + nz_q, 1e-12)[:, None]
                var_red = (G_q ** 2) / denom_q
                if include_drift_sensitivity:
                    for C_b, G_b, nz_b in b_channels:
                        if G_b is not None:
                            denom_b = np.maximum(np.diag(C_b) + nz_b, 1e-12)[:, None]
                            var_red = var_red + (G_b ** 2) / denom_b

                score_raw = np.zeros(len(cand_arr), dtype=float)
                if opt_indices:
                    score_raw += val_reg_weight * np.sum(np.sqrt(np.maximum(var_red[:, opt_indices], 0.0)), axis=1)
                for g_idx, mu_g in gap_entries:
                    s_shift = np.sqrt(np.maximum(var_red[:, g_idx], 0.0))
                    pos_s = s_shift > 1e-12
                    if np.any(pos_s):
                        z = np.zeros_like(s_shift)
                        z[pos_s] = mu_g / s_shift[pos_s]
                        kg_vec = np.zeros_like(s_shift)
                        kg_vec[pos_s] = s_shift[pos_s] * norm.pdf(z[pos_s]) - mu_g * norm.cdf(-z[pos_s])
                        score_raw += np.maximum(kg_vec, 0.0)

            d_min = np.min(np.linalg.norm(cand_arr[:, None, :] - cur_X[None, :, :], axis=2), axis=1)
            rep_w = np.minimum(1.0, (d_min / max(min_repel, 1e-9)) ** 2)
            eff = np.where(rem_mask, score_raw * rep_w, -np.inf)
            best_i = int(np.argmax(eff))
            rem_mask[best_i] = False
            chosen_dec.append(cand_arr[best_i])
            chosen_dec_idx.append(best_i)
            cur_X = np.vstack([cur_X, cand_arr[best_i : best_i + 1]])
            if condition_decision_probes:
                _downdate_all_channels(best_i)

        # Even when decision probes are unconditioned (`condition_decision_probes=False`),
        # always condition the sentinel stage on ALL pending decision probes so sentinel behavior is unconfounded!
        if (not condition_decision_probes) and chosen_dec_idx:
            for sel_i in chosen_dec_idx:
                _downdate_all_channels(sel_i)

        for _ in range(n_sentinel):
            if not np.any(rem_mask):
                break
            cond_std = np.sqrt(np.maximum(np.diag(C_q), 0.0))
            for C_b, _, _ in b_channels:
                cond_std = cond_std + sentinel_drift_weight * np.sqrt(np.maximum(np.diag(C_b), 0.0))
            d_min = np.min(np.linalg.norm(cand_arr[:, None, :] - cur_X[None, :, :], axis=2), axis=1)
            rep_w = np.minimum(1.0, (d_min / max(min_repel, 1e-9)) ** 2)
            eff = np.where(rem_mask, cond_std * rep_w, -np.inf)
            best_i = int(np.argmax(eff))
            rem_mask[best_i] = False
            chosen_sen.append(cand_arr[best_i])
            cur_X = np.vstack([cur_X, cand_arr[best_i : best_i + 1]])
            _downdate_all_channels(best_i)

        all_pts = chosen_dec + chosen_sen
        return (
            np.array(all_pts, dtype=float) if all_pts else np.empty((0, self.dim), dtype=float),
            {
                "acquisition_proxy_kind": (
                    "pairwise_local_linear_kg_proxy" if gap_entries else "value_only_linear_functional_std"
                ),
                "active_q_relu_fraction": active_q_frac,
                "n_decision_selected": len(chosen_dec),
                "n_sentinel_selected": len(chosen_sen),
                "n_functionals_tracked": len(func_meta),
                "drift_sensitivity_included": bool(include_drift_sensitivity and len(b_channels) > 0),
                "decision_probes_conditioned": bool(condition_decision_probes),
                "drift_channels_in_sentinel": len(b_channels),
            },
        )

    def project_q_linear_functional_variance_reduction(
        self,
        cand_pts: np.ndarray,
        grid_pts: np.ndarray,
        weights_mat: np.ndarray,
        apply_q_relu_mask: bool = False,
    ) -> np.ndarray:
        """Exact closed-form 1-step Gaussian posterior variance reduction on `K` linear functionals
        `L_k = <w_k, q_latent(grid_pts)>` from observing a noisy probe `y(x) = q_latent(x) + eps`
        at each candidate point `x in cand_pts` (`shape = (len(cand_pts), K)`):
            `Delta Var(L_k | y(x)) = Cov_post(q(x), L_k)^2 / (Var_post(q(x)) + sigma_noise^2)`.
        """
        from scipy.linalg import solve_triangular
        st = self._q_fast
        W = np.atleast_2d(np.asarray(weights_mat, dtype=float))
        if W.shape[0] != len(grid_pts) and W.shape[1] == len(grid_pts):
            W = W.T
        if apply_q_relu_mask:
            W = W * (self.predict_q_raw_latent_mean(grid_pts) > 0.0)[:, None]
        K_cg = self._eval_matern25_kernel_pair(cand_pts, grid_pts, st)
        K_co = self._eval_matern25_kernel(cand_pts, st)
        K_go = self._eval_matern25_kernel(grid_pts, st)
        V_c = solve_triangular(st["L"], K_co.T, lower=True, check_finite=False)
        V_g = solve_triangular(st["L"], K_go.T, lower=True, check_finite=False)
        cov_mat = (st["y_std"] ** 2) * ((K_cg @ W) - (V_c.T @ (V_g @ W)))
        lat_var = np.maximum(st["c_val"] - np.einsum("ij,ij->j", V_c, V_c), 0.0) * (st["y_std"] ** 2)
        pred_obs_var = np.maximum(lat_var + (st["obs_noise_std"] ** 2), 1e-12)
        return (cov_mat ** 2) / pred_obs_var[:, None]

    def predict_b(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        if not self._b_fast:
            return np.zeros_like(X, dtype=float)
        cols = []
        for st in self._b_fast:
            K_star = self._eval_matern25_kernel(X, st)
            cols.append(st["y_mean"] + K_star @ st["alpha_scaled"])
        return np.column_stack(cols)


def _eval_segment_goal_union_hit_tau(
    X_prev: np.ndarray, X_next: np.ndarray, goals: Sequence[GoalBall]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Exact line-segment first-entry interpolation on `[X_prev, X_next]`:
    Returns `(in_any, phi_at_first_hit, tau_first_hit, X_at_first_hit)` where `tau_first_hit in [0, 1]`
    solves `||X_prev + tau*(X_next - X_prev) - c_j||_2 = r_j`, charging fractional step cost `tau * dt`
    and transitioning at the entry point!
    """
    X_prev = np.atleast_2d(X_prev)
    X_next = np.atleast_2d(X_next)
    n = X_prev.shape[0]
    dX = X_next - X_prev
    a = np.sum(dX ** 2, axis=1)

    best_tau = np.full(n, np.inf, dtype=float)
    best_phi = np.full(n, np.inf, dtype=float)

    for g in goals:
        c = np.asarray(g.center, dtype=float)[None, :]
        r2 = float(g.radius ** 2)
        f = X_prev - c
        f2 = np.sum(f ** 2, axis=1)
        inside0 = f2 <= r2
        if np.any(inside0):
            earlier0 = inside0 & (0.0 < best_tau - 1e-12)
            tie0 = inside0 & (np.abs(best_tau) <= 1e-12)
            best_tau = np.where(earlier0, 0.0, best_tau)
            best_phi = np.where(earlier0, g.phi, np.where(tie0, np.minimum(best_phi, g.phi), best_phi))

        b_half = np.sum(f * dX, axis=1)
        c_quad = f2 - r2
        disc = b_half ** 2 - a * c_quad
        valid_q = (~inside0) & (a > 1e-24) & (disc >= 0.0)
        if np.any(valid_q):
            sqrt_d = np.sqrt(np.maximum(disc, 0.0))
            t1 = (-b_half - sqrt_d) / np.maximum(a, 1e-24)
            hit_seg = valid_q & (t1 >= 0.0) & (t1 <= 1.0)
            if np.any(hit_seg):
                earlier = hit_seg & (t1 < best_tau - 1e-12)
                tie = hit_seg & (np.abs(t1 - best_tau) <= 1e-12)
                best_tau = np.where(earlier, t1, best_tau)
                best_phi = np.where(earlier, g.phi, np.where(tie, np.minimum(best_phi, g.phi), best_phi))

    # Fallback check on endpoint inclusion for numerical edge tangency
    hit_end, phi_end = eval_goal_union(X_next, goals)
    end_only = hit_end & (~np.isfinite(best_tau))
    if np.any(end_only):
        best_tau = np.where(end_only, 1.0, best_tau)
        best_phi = np.where(end_only, phi_end, best_phi)

    in_any = np.isfinite(best_tau)
    tau_out = np.where(in_any, np.clip(best_tau, 0.0, 1.0), 1.0)
    phi_out = np.where(in_any, best_phi, 0.0)
    X_hit = X_prev + tau_out[:, None] * dX
    return in_any, phi_out, tau_out, X_hit


def _eval_reflected_step_goal_union_hit_tau(
    X_prev: np.ndarray,
    X_raw_next: np.ndarray,
    half_width: float,
    goals: Sequence[GoalBall],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Exact piecewise-reflected polyline sphere-entry intersection on `[-L, L]^d` (`d1b926a Sec 6.1`):
    Splits any wall-bouncing Euler-Maruyama step `X_prev + tau * (X_raw_next - X_prev)` (`tau in [0, 1]`)
    at its exact specular wall-reflection breakpoints `(2*m + 1) * L` before testing sphere entry on each
    reflected straight sub-segment. (Note: exact for the discrete piecewise-reflected polyline, not
    continuous Brownian-bridge first-passage between `t` and `t + dt`.)
    Returns `(in_any, phi_hit, tau_hit, X_hit_or_final_reflected, X_final_reflected)`.
    """
    X_prev = np.atleast_2d(X_prev)
    X_raw_next = np.atleast_2d(X_raw_next)
    L = float(half_width)
    X_ref_end = reflect_into_box(X_raw_next, L)
    bounced = np.any(np.abs(X_raw_next) > L, axis=1)
    if not np.any(bounced):
        in_any, phi_out, tau_out, X_hit = _eval_segment_goal_union_hit_tau(X_prev, X_raw_next, goals)
        X_pos = np.where(in_any[:, None], X_hit, X_ref_end)
        return in_any, phi_out, tau_out, X_pos, X_ref_end

    n = len(X_prev)
    in_any = np.zeros(n, dtype=bool)
    phi_out = np.zeros(n, dtype=float)
    tau_out = np.ones(n, dtype=float)
    X_pos = X_ref_end.copy()

    interior_idx = np.flatnonzero(~bounced)
    if interior_idx.size > 0:
        h_i, p_i, t_i, x_i = _eval_segment_goal_union_hit_tau(X_prev[interior_idx], X_raw_next[interior_idx], goals)
        in_any[interior_idx] = h_i
        phi_out[interior_idx] = p_i
        tau_out[interior_idx] = t_i
        X_pos[interior_idx] = np.where(h_i[:, None], x_i, X_ref_end[interior_idx])

    for i in np.flatnonzero(bounced):
        p0 = X_prev[i]
        pr = X_raw_next[i]
        dx = pr - p0
        taus = [0.0, 1.0]
        for j in range(len(p0)):
            if abs(dx[j]) <= 1e-15:
                continue
            lo_v = min(p0[j], pr[j])
            hi_v = max(p0[j], pr[j])
            m_min = int(math.floor((lo_v + L) / (2.0 * L)))
            m_max = int(math.ceil((hi_v + L) / (2.0 * L)))
            for m_k in range(m_min, m_max + 1):
                wall_x = (2 * m_k - 1) * L
                if lo_v < wall_x < hi_v:
                    t_w = float((wall_x - p0[j]) / dx[j])
                    if 1e-12 < t_w < 1.0 - 1e-12:
                        taus.append(t_w)
        taus_s = sorted(taus)
        uniq_taus = [taus_s[0]]
        for tv in taus_s[1:]:
            if tv - uniq_taus[-1] > 1e-11:
                uniq_taus.append(tv)
        for t_a, t_b in zip(uniq_taus[:-1], uniq_taus[1:]):
            xa = reflect_into_box((p0 + t_a * dx)[None, :], L)
            xb = reflect_into_box((p0 + t_b * dx)[None, :], L)
            h_s, p_s, loc_tau, x_s = _eval_segment_goal_union_hit_tau(xa, xb, goals)
            if h_s[0]:
                in_any[i] = True
                phi_out[i] = float(p_s[0])
                tau_out[i] = float(t_a + float(loc_tau[0]) * (t_b - t_a))
                X_pos[i] = x_s[0]
                break
    return in_any, phi_out, tau_out, X_pos, X_ref_end


def _eval_segment_goal_union_hit(
    X_prev: np.ndarray, X_next: np.ndarray, goals: Sequence[GoalBall]
) -> Tuple[np.ndarray, np.ndarray]:
    in_any, phi_out, _, _ = _eval_segment_goal_union_hit_tau(X_prev, X_next, goals)
    return in_any, phi_out


def simulate_closed_loop_crn(
    world: GroundTruthWorld,
    policy_fn: Callable[[np.ndarray], np.ndarray],
    query: QueryTask,
    n_per_start: int = 16,
    seed: int = 2026,
    u_clip_safety: float = 25.0,
    dt_override: Optional[float] = None,
    substep_segment_hit: bool = False,
    dW_pregenerated: Optional[np.ndarray] = None,
    record_visited_states: bool = False,
) -> dict:
    """Closed-loop rollout with per-trajectory CRN streams, `t=0` immediate goal absorption,
    specular reflection, optional fractional-step segment hitting, and optional pregenerated Brownian
    increments `dW_pregenerated` of shape `(n_traj, max_steps, dim)` for exact coarse/fine Wiener coupling.
    """
    spec = world.spec
    dt = spec.dt_sim if dt_override is None else float(dt_override)
    max_steps = (
        dW_pregenerated.shape[1]
        if dW_pregenerated is not None
        else (spec.max_steps if dt_override is None else int(round(spec.max_steps * spec.dt_sim / dt)))
    )
    sqrt_dt = np.sqrt(dt)
    R_vec = spec.R_vec

    starts = np.repeat(np.asarray(query.start_points, dtype=float), n_per_start, axis=0)
    n_traj = starts.shape[0]
    X = reflect_into_box(starts.copy(), spec.half_width)

    traj_rngs = None
    if dW_pregenerated is None:
        ss = np.random.SeedSequence([seed, len(query.goals), int(abs(query.goals[0].center[0]) * 1000)])
        traj_rngs = [np.random.default_rng(s) for s in ss.spawn(n_traj)]

    hit0, phi0 = eval_goal_union(X, query.goals)
    alive = ~hit0
    running_cost = np.zeros(n_traj, dtype=float)
    terminal_cost = np.where(hit0, phi0, 0.0)
    steps_taken = np.zeros(n_traj, dtype=float)
    clipped_steps = 0
    total_active_steps = 0
    visited_chunks: List[np.ndarray] = [X[alive].copy()] if (record_visited_states and np.any(alive)) else []

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
        step_rate = q_val + ctrl_quad

        b_val = world.drift(X_act)
        if dW_pregenerated is not None:
            dW = dW_pregenerated[idx, _step, :]
        else:
            assert traj_rngs is not None
            dW = np.vstack([traj_rngs[i].normal(0.0, sqrt_dt, size=spec.dim) for i in idx])
        X_raw = X_act + (b_val + u) * dt + spec.sigma * dW

        if substep_segment_hit:
            hit_post, phi_post, tau_hit, X_pos, _ = _eval_reflected_step_goal_union_hit_tau(
                X_act, X_raw, spec.half_width, query.goals
            )
            running_cost[idx] += step_rate * (tau_hit * dt)
            X[idx] = X_pos
            steps_taken[idx] += tau_hit
        else:
            X_next = reflect_into_box(X_raw, spec.half_width)
            hit_post, phi_post = eval_goal_union(X_next, query.goals)
            running_cost[idx] += step_rate * dt
            X[idx] = X_next
            steps_taken[idx] += 1.0

        if record_visited_states:
            visited_chunks.append(X[idx].copy())

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
    out_dict = {
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
    if record_visited_states:
        out_dict["visited_states"] = np.vstack(visited_chunks) if visited_chunks else np.empty((0, spec.dim))
    return out_dict


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


def holm_bonferroni_adjust(p_values: Dict[str, float], alpha: float = 0.05) -> Dict[str, dict]:
    """Step-down Holm-Bonferroni family-wise error rate adjustment across a pre-declared contrast family."""
    items = sorted(((k, float(v)) for k, v in p_values.items()), key=lambda kv: kv[1])
    m = len(items)
    out: Dict[str, dict] = {}
    running_max = 0.0
    rejected_so_far = True
    for idx, (k, p_raw) in enumerate(items):
        p_adj = min(1.0, max(running_max, (m - idx) * p_raw))
        running_max = p_adj
        if p_adj >= alpha:
            rejected_so_far = False
        out[k] = {
            "p_nominal": p_raw,
            "p_holm": p_adj,
            "significant_familywise_0_05": bool(rejected_so_far and p_adj < alpha),
        }
    return out
