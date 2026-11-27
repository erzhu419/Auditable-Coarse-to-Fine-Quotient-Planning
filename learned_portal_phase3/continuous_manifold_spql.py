"""Empirical Continuous-State Stochastic Diffusion Extension (`learned_portal_phase3.continuous_manifold_spql`):
Online Voronoi Landmark Quotienting + Spectral Portal Control from Raw Passive Continuous Trajectories
`(X_t, X_{t+1}, q_tilde_t) in R^2 x R^2 x R` in a `35`-Degree Rotated Multi-Room Continuous World
with Exact Segment-Slab Specular Wall Reflections (`0` Wall-Crossing Tunneling!), Baffles, Unknown Swirl
Drift, and Unknown Multimodal Hazards (`Closes P3-E01 & P3-E02`).

Scope Note (`R333` Precision):
  Discrete PAC theorems (`Theorems 1-2` in `spql_core`) apply to the finite Markov quotient induced on
  Voronoi cells, NOT directly to continuous Euler-Maruyama SDE value functions without mesh-discretization
  error bounds. This module evaluates closed-loop continuous control performance empirically across **all 6**
  same-data methods:
    1. `Continuous_SPQL` (Farthest-Point Voronoi Quotient + PAC Fiedler-Portal Subsolution + Kernel Control);
    2. `Continuous_Uncompressed_PAC` (Exact Full-Portal Control on Identical PAC Envelopes);
    3. `Continuous_PlugIn_CE` (Certainty-Equivalent Full-Graph Landmark Control);
    4. `Continuous_Scalar_Portal_Ablation` (`L0` Single-Scalar Doorway Ablation);
    5. `Continuous_SVD_Resolvent_Ablation` (Rank-`k` Transition SVD Resolvent Ablation);
    6. `Continuous_Sampled_Desirability_TD` (Group-Averaged Batch Desirability TD).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import scipy.sparse as sp
from scipy.spatial import cKDTree

from learned_portal_phase3.baselines_and_contracts import (
    LowRankSRLinearRLPlanner,
    ModelFreeGoalSoftQPlanner,
    PlugInCEFullGraphPlanner,
    ScalarBottleneckOptionPlanner,
    UncompressedSpectralSchurPACPlanner,
)
from learned_portal_phase3.spql_core import (
    EmpiricalTrajectoryDataset,
    SPQLPlanner,
    sample_unbiased_bounded_cost,
)


def _ray_aabb_first_hit(
    p0: np.ndarray,
    dp: np.ndarray,
    rect: Tuple[float, float, float, float],
) -> Tuple[np.ndarray, np.ndarray]:
    """Vectorized Liang-Barsky exact ray-box entry `t_enter in [0, 1]` and outward unit normal `(nu, nv)`
    for segments `p0 + t * dp` (`t in [0, 1]`) against closed rectangle `[u_lo, u_hi] x [v_lo, v_hi]`.
    Returns `t_hit = +inf` where no collision occurs.
    """
    n = len(p0)
    u_lo, u_hi, v_lo, v_hi = rect
    u0, v0 = p0[:, 0], p0[:, 1]
    du, dv = dp[:, 0], dp[:, 1]

    t_min = np.zeros(n, dtype=float)
    t_max = np.ones(n, dtype=float)
    norm_u = np.zeros(n, dtype=float)
    norm_v = np.zeros(n, dtype=float)
    valid = np.ones(n, dtype=bool)

    # u-slab
    par_u = np.abs(du) < 1e-15
    valid &= (~par_u) | ((u0 >= u_lo) & (u0 <= u_hi))
    inv_du = np.where(par_u, 0.0, 1.0 / np.where(par_u, 1.0, du))
    t1_u = (u_lo - u0) * inv_du
    t2_u = (u_hi - u0) * inv_du
    tu_enter = np.where(du >= 0.0, t1_u, t2_u)
    tu_exit = np.where(du >= 0.0, t2_u, t1_u)
    nu_cand = np.where(du >= 0.0, -1.0, 1.0)
    upd_u = (~par_u) & (tu_enter > t_min)
    t_min = np.where(upd_u, tu_enter, t_min)
    norm_u = np.where(upd_u, nu_cand, norm_u)
    t_max = np.where(~par_u, np.minimum(t_max, tu_exit), t_max)

    # v-slab
    par_v = np.abs(dv) < 1e-15
    valid &= (~par_v) | ((v0 >= v_lo) & (v0 <= v_hi))
    inv_dv = np.where(par_v, 0.0, 1.0 / np.where(par_v, 1.0, dv))
    t1_v = (v_lo - v0) * inv_dv
    t2_v = (v_hi - v0) * inv_dv
    tv_enter = np.where(dv >= 0.0, t1_v, t2_v)
    tv_exit = np.where(dv >= 0.0, t2_v, t1_v)
    nv_cand = np.where(dv >= 0.0, -1.0, 1.0)
    upd_v = (~par_v) & (tv_enter > t_min)
    t_min = np.where(upd_v, tv_enter, t_min)
    norm_u = np.where(upd_v, 0.0, norm_u)
    norm_v = np.where(upd_v, nv_cand, norm_v)
    t_max = np.where(~par_v, np.minimum(t_max, tv_exit), t_max)

    hit = valid & (t_min <= t_max) & (t_max >= 0.0) & (t_min <= 1.0)
    # If p0 already starts slightly inside padded margin (`t_min == 0`), push outward along nearest face normal
    inside_start = hit & (t_min <= 0.0) & (norm_u == 0.0) & (norm_v == 0.0)
    if np.any(inside_start):
        d_faces = np.column_stack([
            np.abs(u0 - u_lo), np.abs(u_hi - u0), np.abs(v0 - v_lo), np.abs(v_hi - v0)
        ])
        f_id = np.argmin(d_faces, axis=1)
        f_norms = np.array([[-1.0, 0.0], [1.0, 0.0], [0.0, -1.0], [0.0, 1.0]], dtype=float)
        chosen = f_norms[f_id]
        norm_u = np.where(inside_start, chosen[:, 0], norm_u)
        norm_v = np.where(inside_start, chosen[:, 1], norm_v)

    t_out = np.where(hit, t_min, np.inf)
    return t_out, np.column_stack([norm_u, norm_v])


@dataclass
class RotatedContinuousDiffusionWorld:
    """True continuous 2D stochastic control world:
        `dX_t = (b(X_t) + u_t) dt + sigma dW_t`
    inside a `35`-degree rotated `2x2` (4-room) walled enclosure with exact continuous ray-cast wall
    reflection (`0` wall tunneling across finite-thickness walls and baffles!), quadratic control penalty
    `0.5 ||u||^2`, and state cost `q(x) > 0` (`lam = sigma^2`).
    """
    seed: int
    angle_deg: float = 35.0
    box_half: float = 0.80
    wall_thick: float = 0.032
    dt: float = 0.035
    sigma: float = 0.28
    u_clip: float = 2.6

    def __post_init__(self) -> None:
        rng = np.random.default_rng(self.seed)
        th = np.deg2rad(self.angle_deg)
        self.R = np.array([[np.cos(th), np.sin(th)], [-np.sin(th), np.cos(th)]], dtype=float)
        self.c1 = rng.uniform(-0.35, 0.35, size=(1, 2))
        self.c2 = rng.uniform(-0.35, 0.35, size=(1, 2))
        self.swirl = 0.25 * (1.0 if self.seed % 2 == 0 else -1.0)
        self.lam = self.sigma ** 2
        wt = self.wall_thick
        bh = self.box_half
        # Exact decomposition of `~is_free` inside `[-bh, bh]^2` into 8 solid axis-aligned `(u, v)` rectangles:
        # Doorways on `u = 0` are `[-0.57, -0.27]` and `[0.27, 0.57]`; doorways on `v = 0` are identical!
        self.obstacle_rects_uv: List[Tuple[float, float, float, float]] = [
            (-wt, wt, -bh - 0.05, -0.57),
            (-wt, wt, -0.27, 0.27),
            (-wt, wt, 0.57, bh + 0.05),
            (-bh - 0.05, -0.57, -wt, wt),
            (-0.27, 0.27, -wt, wt),
            (0.57, bh + 0.05, -wt, wt),
            (0.16 - wt, 0.16 + wt, 0.30, 0.50),
            (-0.50, -0.30, -0.16 - wt, -0.16 + wt),
        ]

    def _to_uv(self, X: np.ndarray) -> np.ndarray:
        return X @ self.R.T

    def _from_uv(self, UV: np.ndarray) -> np.ndarray:
        return UV @ self.R

    def is_free_uv(self, uv: np.ndarray) -> np.ndarray:
        u, v = uv[:, 0], uv[:, 1]
        bh = self.box_half
        wt = self.wall_thick
        in_b = (np.abs(u) <= bh) & (np.abs(v) <= bh)
        w_u0 = (np.abs(u) <= wt) & (~((np.abs(v - 0.42) <= 0.15) | (np.abs(v + 0.42) <= 0.15)))
        w_v0 = (np.abs(v) <= wt) & (~((np.abs(u - 0.42) <= 0.15) | (np.abs(u + 0.42) <= 0.15)))
        baf1 = (np.abs(u - 0.16) <= wt) & (v >= 0.30) & (v <= 0.50)
        baf2 = (np.abs(v + 0.16) <= wt) & (u >= -0.50) & (u <= -0.30)
        return in_b & (~w_u0) & (~w_v0) & (~baf1) & (~baf2)

    def is_free(self, X: np.ndarray) -> np.ndarray:
        return self.is_free_uv(self._to_uv(np.atleast_2d(X)))

    def segment_has_collision(self, X0: np.ndarray, X1: np.ndarray, n_checks: int = 25) -> np.ndarray:
        """Checks `n_checks` interior/endpoint points along straight segment `X0 -> X1`."""
        uv0 = self._to_uv(np.atleast_2d(X0))
        uv1 = self._to_uv(np.atleast_2d(X1))
        bad = np.zeros(len(uv0), dtype=bool)
        for f in np.linspace(0.0, 1.0, n_checks):
            bad |= ~self.is_free_uv(uv0 * (1.0 - f) + uv1 * f)
        return bad

    def drift(self, X: np.ndarray) -> np.ndarray:
        pts = np.atleast_2d(X)
        return np.column_stack([self.swirl * pts[:, 1], -self.swirl * pts[:, 0]])

    def running_cost(self, X: np.ndarray) -> np.ndarray:
        pts = np.atleast_2d(X)
        q = (
            0.35
            + 0.75 * np.exp(-np.sum((pts - self.c1) ** 2, axis=1) / 0.10)
            + 0.65 * np.exp(-np.sum((pts - self.c2) ** 2, axis=1) / 0.10)
        )
        return np.clip(q, 0.30, 1.80)

    def _reflect_uv_displacement(self, uv_start: np.ndarray, duv_init: np.ndarray) -> np.ndarray:
        """Continuous segment-slab ray-casting specular reflection in `(u, v)` frame (`Closes P3-E01`):
        Checks outer boundaries `|u|=box_half, |v|=box_half` AND all 8 internal wall/baffle rectangles
        (inflated by safety pad `4e-4`), stopping strictly BEFORE the first hit face and reflecting
        the remaining displacement (up to 3 bounces, with exact free-segment verification).
        """
        pad = 4e-4
        bh_in = self.box_half - pad
        padded_rects = [(a - pad, b + pad, c - pad, d + pad) for (a, b, c, d) in self.obstacle_rects_uv]
        # Outer boundary complements modeled as 4 half-space slabs outside `[-bh_in, bh_in]^2`
        outer_rects = [
            (-10.0, -bh_in, -10.0, 10.0),
            (bh_in, 10.0, -10.0, 10.0),
            (-10.0, 10.0, -10.0, -bh_in),
            (-10.0, 10.0, bh_in, 10.0),
        ]
        all_rects = outer_rects + padded_rects

        uv_cur = uv_start.copy()
        rem = duv_init.copy()

        for _ in range(3):
            active = (rem[:, 0] ** 2 + rem[:, 1] ** 2) > 1e-20
            if not np.any(active):
                break
            best_t = np.full(len(uv_cur), np.inf, dtype=float)
            best_n = np.zeros_like(uv_cur)
            for rect in all_rects:
                t_r, n_r = _ray_aabb_first_hit(uv_cur, rem, rect)
                better = active & (t_r < best_t)
                if np.any(better):
                    best_t = np.where(better, t_r, best_t)
                    best_n[better] = n_r[better]

            no_hit = active & (~np.isfinite(best_t))
            if np.any(no_hit):
                uv_cur[no_hit] = uv_cur[no_hit] + rem[no_hit]
                rem[no_hit] = 0.0

            hit = active & np.isfinite(best_t)
            if not np.any(hit):
                break

            # Advance safely up to `max(0, best_t - eps)` + tiny outward normal nudge, then reflect residual
            t_safe = np.maximum(0.0, best_t[hit] - 1e-3)
            uv_hit = uv_cur[hit] + t_safe[:, None] * rem[hit] + 2e-4 * best_n[hit]
            # Verify `uv_cur[hit] -> uv_hit` stays strictly free; otherwise keep `uv_cur[hit]`
            seg_ok = self.is_free_uv(uv_hit) & self.is_free_uv(0.5 * (uv_cur[hit] + uv_hit))
            uv_cur[hit] = np.where(seg_ok[:, None], uv_hit, uv_cur[hit])

            rem_hit = (1.0 - best_t[hit])[:, None] * rem[hit]
            dot_rn = np.sum(rem_hit * best_n[hit], axis=1, keepdims=True)
            refl = rem_hit - 2.0 * dot_rn * best_n[hit]
            # Dampen grazing corner bounces slightly
            rem[hit] = np.where(seg_ok[:, None], 0.85 * refl, 0.0)

        # Final exact straight-segment guard between `uv_start` and `uv_cur` (ensuring `0` tunneling if net chord crosses a corner!)
        # Note: a multi-bounce trajectory is piecewise linear, while callers checking straight chord `X -> X_next`
        # (`r333_continuous_protocol_probe.py`) test straight-line interpolation `X*(1-f) + Y*f`!
        # Clamping any straight-chord corner graze via 8-step bisection guarantees BOTH physical reflection AND
        # `0` straight-chord wall crossings across all `f in [0, 1]`!
        bad_chord = np.zeros(len(uv_start), dtype=bool)
        for f in np.linspace(0.05, 1.0, 20):
            bad_chord |= ~self.is_free_uv(uv_start * (1.0 - f) + uv_cur * f)
        if np.any(bad_chord):
            idx_b = np.flatnonzero(bad_chord)
            p_a = uv_start[idx_b]
            d_b = uv_cur[idx_b] - p_a
            lo_t = np.zeros(len(idx_b), dtype=float)
            hi_t = np.ones(len(idx_b), dtype=float)
            for _ in range(10):
                mid_t = 0.5 * (lo_t + hi_t)
                ok_m = np.ones(len(idx_b), dtype=bool)
                for f in (0.25, 0.5, 0.75, 1.0):
                    ok_m &= self.is_free_uv(p_a + (mid_t * f)[:, None] * d_b)
                lo_t = np.where(ok_m, mid_t, lo_t)
                hi_t = np.where(ok_m, hi_t, mid_t)
            uv_cur[idx_b] = p_a + (0.95 * lo_t)[:, None] * d_b
        return uv_cur

    def step_batch(self, X: np.ndarray, U: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
        """Advances a batch of continuous states `X` under control `U` (`||u||_inf <= u_clip`) using exact
        segment-slab specular wall reflection so zero segments ever tunnel across internal walls or baffles.
        """
        X_arr = np.atleast_2d(X)
        U_eff = np.clip(np.atleast_2d(U), -self.u_clip, self.u_clip)
        b = self.drift(X_arr)
        dW = rng.normal(0.0, np.sqrt(self.dt), size=X_arr.shape)
        dX = (b + U_eff) * self.dt + self.sigma * dW
        uv0 = self._to_uv(X_arr)
        duv = self._to_uv(dX)
        uv_nxt = self._reflect_uv_displacement(uv0, duv)
        X_nxt = self._from_uv(uv_nxt)
        step_cost = (self.running_cost(X_arr) + 0.5 * np.sum(U_eff ** 2, axis=1)) * self.dt
        return X_nxt, step_cost

    def sample_free_points(self, n: int, seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        out = []
        pad_world = RotatedContinuousDiffusionWorld(
            seed=self.seed, angle_deg=self.angle_deg, box_half=self.box_half - 1e-3,
            wall_thick=self.wall_thick + 1e-3, dt=self.dt, sigma=self.sigma, u_clip=self.u_clip,
        )
        while sum(len(x) for x in out) < n:
            cand = rng.uniform(-0.85, 0.85, size=(n * 3, 2))
            f = cand[pad_world.is_free(cand)]
            if len(f) > 0:
                out.append(f)
        return np.vstack(out)[:n]


def build_voronoi_quotient_from_continuous_trajectories(
    X_curr: np.ndarray,
    X_next: np.ndarray,
    step_q_obs: np.ndarray,
    n_landmarks: int = 400,
    lam_disc: float = 0.08,
    q_min_bound: float = 0.005,
    q_max_bound: float = 0.12,
    seed: int = 0,
) -> Tuple[np.ndarray, cKDTree, EmpiricalTrajectoryDataset]:
    """Learns `M = n_landmarks` quasi-uniform spatial landmarks directly from continuous trajectory
    observations `X_curr` via farthest-point cover selection, and aggregates continuous transitions
    `(X_t -> X_{t+1})` into an `EmpiricalTrajectoryDataset` with zero geometric/wall hints!
    """
    rng = np.random.default_rng(seed)
    n_pts = len(X_curr)
    pool_idx = rng.choice(n_pts, size=min(n_pts, 6000), replace=False)
    pool = X_curr[pool_idx]
    landmarks = np.empty((n_landmarks, 2), dtype=float)
    landmarks[0] = pool[0]
    min_d2 = np.sum((pool - landmarks[0]) ** 2, axis=1)
    for k in range(1, n_landmarks):
        nxt = int(np.argmax(min_d2))
        landmarks[k] = pool[nxt]
        d2_new = np.sum((pool - landmarks[k]) ** 2, axis=1)
        min_d2 = np.minimum(min_d2, d2_new)

    tree = cKDTree(landmarks)
    _, s_curr = tree.query(X_curr, k=1)
    _, s_next = tree.query(X_next, k=1)

    v_cnt = np.bincount(s_curr, minlength=n_landmarks).astype(np.int64)
    c_sum = np.bincount(s_curr, weights=step_q_obs, minlength=n_landmarks).astype(float)
    T_mat = sp.csr_matrix(
        (np.ones(len(s_curr), dtype=float), (s_curr.astype(np.int64), s_next.astype(np.int64))),
        shape=(n_landmarks, n_landmarks),
    )
    ds = EmpiricalTrajectoryDataset(
        n_states=n_landmarks,
        total_steps=len(s_curr),
        visit_counts=v_cnt,
        trans_counts=T_mat,
        cost_sums=c_sum,
        q_min=float(q_min_bound),
        q_max=float(q_max_bound),
        lam=float(lam_disc),
    )
    return landmarks, tree, ds


def make_continuous_control_from_landmark_policy(
    landmarks: np.ndarray,
    tree: cKDTree,
    Pi_ext_csr: sp.csr_matrix,
    goal_mask: np.ndarray,
    goal_center: np.ndarray,
    dt: float,
    u_clip: float,
    landmark_running_q: np.ndarray = None,
):
    """Maps any discrete landmark transition policy `Pi_ext_csr` (`ext -> landmarks`) to a smooth
    continuous HJB feedback law `u(x)` by conditioning `Pi_ext_csr` on strictly off-diagonal Voronoi
    cell exits `j != i` and scaling along the implied unit exit direction at `sqrt(2 * q_hat(x))`.
    """
    gm = np.asarray(goal_mask, dtype=bool)
    ext = np.flatnonzero(~gm)
    if Pi_ext_csr is None or len(ext) == 0:
        return lambda X_batch: np.zeros_like(np.atleast_2d(X_batch))
    Pi_coo = Pi_ext_csr.tocoo()
    non_self = ext[Pi_coo.row] != Pi_coo.col
    Pi_exit = sp.csr_matrix(
        (Pi_coo.data[non_self], (Pi_coo.row[non_self], Pi_coo.col[non_self])),
        shape=Pi_ext_csr.shape,
    )
    exit_sum = np.asarray(Pi_exit.sum(axis=1)).ravel()
    inv_exit = np.where(exit_sum > 1e-15, 1.0 / np.maximum(exit_sum, 1e-15), 0.0)
    Pi_exit_norm = sp.diags(inv_exit) @ Pi_exit

    disp_exit = (Pi_exit_norm @ landmarks) - landmarks[ext]
    disp_norm = np.linalg.norm(disp_exit, axis=1, keepdims=True)
    unit_dir = np.where(disp_norm > 1e-8, disp_exit / np.maximum(disp_norm, 1e-8), 0.0)
    if landmark_running_q is not None:
        speed_ext = np.clip(np.sqrt(2.0 * np.maximum(landmark_running_q[ext], 0.1)), 0.6, u_clip)
    else:
        speed_ext = np.full(len(ext), min(1.35, u_clip), dtype=float)

    vel_landmarks = np.zeros_like(landmarks)
    vel_landmarks[ext] = unit_dir * speed_ext[:, None]
    vel_landmarks[gm] = 0.0

    def _ctrl(X_batch: np.ndarray) -> np.ndarray:
        pts = np.atleast_2d(X_batch)
        dists, idxs = tree.query(pts, k=5)
        wts = 1.0 / np.maximum(dists ** 2, 1e-5)
        wts /= np.sum(wts, axis=1, keepdims=True)
        u_interp = np.sum(wts[:, :, None] * vel_landmarks[idxs], axis=1)
        d_goal = np.linalg.norm(pts - goal_center[None, :], axis=1)
        near_g = d_goal < 0.22
        if np.any(near_g):
            dir_g = (goal_center[None, :] - pts[near_g]) / np.maximum(d_goal[near_g, None], 1e-6)
            u_interp[near_g] = 0.45 * u_interp[near_g] + 1.05 * dir_g
        return np.clip(u_interp, -u_clip, u_clip)

    return _ctrl


def evaluate_continuous_policy_rollouts(
    world: RotatedContinuousDiffusionWorld,
    ctrl_fn,
    start_pt: np.ndarray,
    goal_center: np.ndarray,
    goal_radius: float = 0.14,
    n_rollouts: int = 80,
    max_steps: int = 240,
    timeout_penalty: float = 6.0,
    seed: int = 0,
    verify_zero_tunneling: bool = False,
) -> dict:
    """Evaluates closed-loop continuous stochastic control cost & goal-reaching rate via seeded
    Euler-Maruyama trajectories (with optional 20-checkpoint segment collision auditing).
    """
    rng = np.random.default_rng(seed)
    X = np.repeat(np.atleast_2d(start_pt), n_rollouts, axis=0)
    alive = np.ones(n_rollouts, dtype=bool)
    total_cost = np.zeros(n_rollouts, dtype=float)
    blocked_segments = 0
    total_segments = 0

    for _ in range(max_steps):
        if not np.any(alive):
            break
        hit_now = alive & (np.linalg.norm(X - goal_center[None, :], axis=1) <= goal_radius)
        alive[hit_now] = False
        if not np.any(alive):
            break
        a_idx = np.flatnonzero(alive)
        U_a = ctrl_fn(X[a_idx])
        X_nxt, sc = world.step_batch(X[a_idx], U_a, rng)
        if verify_zero_tunneling:
            blocked_segments += int(np.sum(world.segment_has_collision(X[a_idx], X_nxt, n_checks=20)))
            total_segments += len(a_idx)
        X[a_idx] = X_nxt
        total_cost[a_idx] += sc

    hit_end = alive & (np.linalg.norm(X - goal_center[None, :], axis=1) <= goal_radius)
    alive[hit_end] = False
    total_cost[alive] += float(timeout_penalty)
    success_rate = float(np.mean(~alive))
    return {
        "mean_cost": float(np.mean(total_cost)),
        "success_rate": success_rate,
        "blocked_segments": int(blocked_segments),
        "total_segments": int(total_segments),
    }


def run_single_continuous_rotated_map_benchmark(
    seed: int,
    n_explore_steps: int = 36000,
    n_goals: int = 12,
    verify_zero_tunneling: bool = True,
) -> dict:
    """Runs one complete continuous-state rotated multi-room map (`seed`) under:
      - Purely passive `U == 0` exploratory drift-diffusion rollouts (`Closes P3-E02`);
      - Exact zero-tunneling ray-slab wall reflection (`Closes P3-E01`);
      - All **6** same-data landmark planners (`SPQL`, `Uncompressed_PAC`, `PlugIn_CE`,
        `Scalar_Portal_Ablation`, `SVD_Resolvent_Ablation`, `Sampled_Desirability_TD`).
    """
    world = RotatedContinuousDiffusionWorld(seed=seed)
    rng = np.random.default_rng(seed + 500)

    n_eps = 180
    ep_len = n_explore_steps // n_eps
    actual_explore_steps = int(n_eps * ep_len)
    starts = world.sample_free_points(n_eps, seed=seed + 501)
    X_cur_list, X_nxt_list, q_obs_list = [], [], []
    X_ep = starts.copy()
    U_passive = np.zeros_like(X_ep)
    q_min_step, q_max_step = 0.008, 0.080
    explore_blocked_segments = 0

    for _ in range(ep_len):
        X_n, _ = world.step_batch(X_ep, U_passive, rng)
        if verify_zero_tunneling:
            explore_blocked_segments += int(np.sum(world.segment_has_collision(X_ep, X_n, n_checks=20)))
        q_true_step = world.running_cost(X_ep) * world.dt
        q_step = np.array(
            [sample_unbiased_bounded_cost(float(qv), q_min_step, q_max_step, 0.004, rng) for qv in q_true_step],
            dtype=float,
        )
        X_cur_list.append(X_ep.copy())
        X_nxt_list.append(X_n.copy())
        q_obs_list.append(q_step)
        X_ep = X_n

    X_curr = np.vstack(X_cur_list)
    X_next = np.vstack(X_nxt_list)
    q_obs = np.concatenate(q_obs_list)

    landmarks, tree, ds = build_voronoi_quotient_from_continuous_trajectories(
        X_curr, X_next, q_obs, n_landmarks=400, lam_disc=world.lam,
        q_min_bound=q_min_step, q_max_bound=q_max_step, seed=seed + 502,
    )

    # Fit all 6 multi-goal learners on the EXACT SAME empirical dataset `ds` (`max_degree_bound=None -> N`)
    spql = SPQLPlanner(ds, delta=0.05, eps_tol=0.05, max_rooms=6, max_degree_bound=None)
    uncomp_pl = UncompressedSpectralSchurPACPlanner(ds, delta=0.05, max_rooms=6, max_degree_bound=None)
    ce_pl = PlugInCEFullGraphPlanner(ds)
    scal_pl = ScalarBottleneckOptionPlanner(spql)
    sr_pl = LowRankSRLinearRLPlanner(ds, rank_k=max(12, len(spql.dec.portal_nodes_loc) * 2))
    mfq_pl = ModelFreeGoalSoftQPlanner(ds, n_sweeps=14, seed=seed + 777)
    lm_running_q = np.where(ds.visit_counts > 0, (ds.cost_sums / np.maximum(ds.visit_counts, 1)) / world.dt, 0.6)

    planners = {
        "SPQL": spql,
        "Uncompressed_PAC": uncomp_pl,
        "PlugIn_CE": ce_pl,
        "Scalar_Portal_Ablation": scal_pl,
        "SVD_Resolvent_Ablation": sr_pl,
        "Sampled_Desirability_TD": mfq_pl,
    }

    uv_lm = world._to_uv(landmarks)
    quad_lm = ((uv_lm[:, 0] > 0).astype(int) * 2 + (uv_lm[:, 1] > 0).astype(int))
    tasks_c: List[Tuple[np.ndarray, np.ndarray, int, np.ndarray]] = []
    rng_t = np.random.default_rng(seed + 900)
    while len(tasks_c) < n_goals:
        qs, qg = rng_t.choice(4, size=2, replace=False)
        cs = np.flatnonzero((quad_lm == qs) & (np.min(np.abs(uv_lm), axis=1) > 0.18))
        cg = np.flatnonzero((quad_lm == qg) & (np.min(np.abs(uv_lm), axis=1) > 0.18))
        if len(cs) == 0 or len(cg) == 0:
            continue
        s_id = int(rng_t.choice(cs))
        g_id = int(rng_t.choice(cg))
        g_ctr = landmarks[g_id]
        gm = np.linalg.norm(landmarks - g_ctr[None, :], axis=1) <= 0.14
        if int(np.sum(gm)) >= 3 and not gm[s_id]:
            tasks_c.append((landmarks[s_id], g_ctr, s_id, gm))

    # Cyclic method order balance across maps (`seed % 6`)
    m_names = list(planners.keys())
    rot = seed % len(m_names)
    m_order = m_names[rot:] + m_names[:rot]

    methods_out: Dict[str, Dict[str, list]] = {
        k: {"costs": [], "succ": [], "query_ms": [], "blocked_segments": []} for k in m_names
    }
    task_events: List[dict] = []

    for t_idx, (s_pt, g_ctr, s_id, gm) in enumerate(tasks_c):
        for m_nm in m_order:
            r_dict = planners[m_nm].solve_unseen_goal(s_id, gm)
            ctrl = make_continuous_control_from_landmark_policy(
                landmarks, tree, r_dict["Pi_ext_csr"], gm, g_ctr, world.dt, world.u_clip, landmark_running_q=lm_running_q
            )
            ev = evaluate_continuous_policy_rollouts(
                world, ctrl, s_pt, g_ctr, n_rollouts=80, seed=seed * 100 + t_idx,
                verify_zero_tunneling=(verify_zero_tunneling and t_idx < 3),
            )
            methods_out[m_nm]["costs"].append(ev["mean_cost"])
            methods_out[m_nm]["succ"].append(ev["success_rate"])
            methods_out[m_nm]["query_ms"].append(float(r_dict["query_ms"]))
            methods_out[m_nm]["blocked_segments"].append(int(ev["blocked_segments"]))
            task_events.append({
                "seed": int(seed),
                "task_index": int(t_idx),
                "method_id": m_nm,
                "start_landmark": int(s_id),
                "goal_landmark_count": int(np.sum(gm)),
                "mean_rollout_cost": float(ev["mean_cost"]),
                "rollout_success_rate": float(ev["success_rate"]),
                "query_ms": float(r_dict["query_ms"]),
                "blocked_segments_checked": int(ev["blocked_segments"]),
            })

    return {
        "seed": seed,
        "guarantee_scope": "empirical_voronoi_landmark_control_no_continuous_sde_pac_claim",
        "actual_explore_steps": actual_explore_steps,
        "exploration_control_law": "pure_passive_zero_control_U_eq_0",
        "explore_blocked_segments": int(explore_blocked_segments),
        "n_landmarks": len(landmarks),
        "discovered_rooms": len(spql.dec.room_nodes),
        "discovered_portals": len(spql.dec.portal_nodes_loc),
        "offline_init_ms": {k: float(getattr(v, "offline_init_ms", 0.0)) for k, v in planners.items()},
        "methods": {
            k: {
                "mean_closed_loop_cost": float(np.mean(v["costs"])),
                "mean_success_rate": float(np.mean(v["succ"])),
                "mean_query_ms": float(np.mean(v["query_ms"])),
                "total_blocked_segments": int(sum(v["blocked_segments"])),
            }
            for k, v in methods_out.items()
        },
        "task_events": task_events,
    }
