"""Continuous-State Stochastic Diffusion Extension (`learned_portal_phase3.continuous_manifold_spql`):
Online Voronoi Landmark Quotienting + Spectral Portal Discovery from Raw Continuous Trajectories
`(X_t, X_{t+1}, q_tilde_t) in R^2 x R^2 x R` in a `35`-Degree Rotated Multi-Room Continuous World
with Reflective Internal Walls, Baffles, Unknown Swirl Drift, and Unknown Multimodal Hazards.

Evaluates Closed-Loop Continuous Stochastic Control Policies `u(x)` via True Continuous Euler-Maruyama
Monte Carlo Rollouts (with Specular Wall Reflections) Against:
  1. `Continuous_SPQL` (Online Farthest-Point Voronoi Quotient + PAC Fiedler-Portal Subsolution + Kernel Control);
  2. `Continuous_RBF_LinearRL` (Continuous RBF Successor Features + Rank-`k` SVD Readout);
  3. `Continuous_Scalar_EigenOptions` (Single Bottleneck Landmark Option per Discovered Doorway);
  4. `Continuous_Kernel_SoftQ` (Offline Hindsight-Relabeled Kernel Soft Value Iteration).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

from dataclasses import dataclass
import time
from typing import List, Tuple

import numpy as np
import scipy.sparse as sp
from scipy.spatial import cKDTree

from learned_portal_phase3.baselines_and_contracts import (
    LowRankSRLinearRLPlanner,
    ModelFreeGoalSoftQPlanner,
    ScalarBottleneckOptionPlanner,
)
from learned_portal_phase3.spql_core import EmpiricalTrajectoryDataset, SPQLPlanner


@dataclass
class RotatedContinuousDiffusionWorld:
    """True continuous 2D stochastic control world:
        `dX_t = (b(X_t) + u_t) dt + sigma dW_t`
    inside a `35`-degree rotated `2x2` (4-room) walled enclosure with asymmetric internal baffles,
    quadratic control penalty `0.5 ||u||^2`, and state cost `q(x) > 0` (`lam = sigma^2`).
    """
    seed: int
    angle_deg: float = 35.0
    box_half: float = 0.80
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

    def _to_uv(self, X: np.ndarray) -> np.ndarray:
        return X @ self.R.T

    def is_free(self, X: np.ndarray) -> np.ndarray:
        uv = self._to_uv(np.atleast_2d(X))
        u, v = uv[:, 0], uv[:, 1]
        in_b = (np.abs(u) <= self.box_half) & (np.abs(v) <= self.box_half)
        wt = 0.032
        # Cross walls `u = 0` and `v = 0` with wide doorways (`width = 0.30`) + partial baffles behind them
        w_u0 = (np.abs(u) <= wt) & (~((np.abs(v - 0.42) <= 0.15) | (np.abs(v + 0.42) <= 0.15)))
        w_v0 = (np.abs(v) <= wt) & (~((np.abs(u - 0.42) <= 0.15) | (np.abs(u + 0.42) <= 0.15)))
        baf1 = (np.abs(u - 0.16) <= wt) & (v >= 0.30) & (v <= 0.50)
        baf2 = (np.abs(v + 0.16) <= wt) & (u >= -0.50) & (u <= -0.30)
        return in_b & (~w_u0) & (~w_v0) & (~baf1) & (~baf2)

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

    def step_batch(self, X: np.ndarray, U: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
        """Advances a batch of continuous states `X` under control `U` (`||u|| <= u_clip`), rejecting/reflecting
        wall collisions so trajectories remain strictly inside the continuous free manifold.
        """
        U_eff = np.clip(U, -self.u_clip, self.u_clip)
        b = self.drift(X)
        dW = rng.normal(0.0, np.sqrt(self.dt), size=X.shape)
        X_cand = X + (b + U_eff) * self.dt + self.sigma * dW
        ok = self.is_free(X_cand)
        if not np.all(ok):
            # Try half-step / specular bounce fallback on blocked proposals
            bad = ~ok
            X_bounce = X[bad] - 0.35 * (X_cand[bad] - X[bad])
            ok_b = self.is_free(X_bounce)
            X_cand[bad] = np.where(ok_b[:, None], X_bounce, X[bad])
        step_cost = (self.running_cost(X) + 0.5 * np.sum(U_eff ** 2, axis=1)) * self.dt
        return X_cand, step_cost

    def sample_free_points(self, n: int, seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        out = []
        while sum(len(x) for x in out) < n:
            cand = rng.uniform(-0.85, 0.85, size=(n * 3, 2))
            f = cand[self.is_free(cand)]
            if len(f) > 0:
                out.append(f)
        return np.vstack(out)[:n]


def build_voronoi_quotient_from_continuous_trajectories(
    X_curr: np.ndarray,
    X_next: np.ndarray,
    step_q_obs: np.ndarray,
    n_landmarks: int = 420,
    lam_disc: float = 0.08,
    seed: int = 0,
) -> Tuple[np.ndarray, cKDTree, EmpiricalTrajectoryDataset]:
    """Learns `M = n_landmarks` quasi-uniform spatial landmarks directly from continuous trajectory
    observations `X_curr` via farthest-point cover selection, and aggregates continuous transitions
    `(X_t -> X_{t+1})` into an `EmpiricalTrajectoryDataset` with zero geometric/wall hints!
    """
    rng = np.random.default_rng(seed)
    n_pts = len(X_curr)
    # Subsample candidate pool for fast O(M * Pool) farthest-point landmark cover
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
        q_min=float(max(1e-4, np.min(step_q_obs) * 0.8)),
        q_max=float(np.max(step_q_obs) * 1.2),
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
    cell exits `j != i` (eliminating discrete self-loop laziness bias!) and scaling along the implied
    unit exit direction at local optimal HJB travel speed `sqrt(2 * q_hat(x))`!
    """
    gm = np.asarray(goal_mask, dtype=bool)
    ext = np.flatnonzero(~gm)
    # Remove self-loops `ext[r] == c` so exit direction reflects genuine cross-Voronoi steering!
    Pi_coo = Pi_ext_csr.tocoo()
    non_self = ext[Pi_coo.row] != Pi_coo.col
    Pi_exit = sp.csr_matrix(
        (Pi_coo.data[non_self], (Pi_coo.row[non_self], Pi_coo.col[non_self])),
        shape=Pi_ext_csr.shape,
    )
    exit_sum = np.asarray(Pi_exit.sum(axis=1)).ravel()
    inv_exit = np.where(exit_sum > 1e-15, 1.0 / np.maximum(exit_sum, 1e-15), 0.0)
    Pi_exit_norm = sp.diags(inv_exit) @ Pi_exit

    disp_exit = (Pi_exit_norm @ landmarks) - landmarks[ext]  # (|ext|, 2)
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
        # Near goal ball, pull smoothly toward continuous goal center
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
    n_rollouts: int = 96,
    max_steps: int = 240,
    timeout_penalty: float = 6.0,
    seed: int = 0,
) -> dict:
    """Evaluates true closed-loop continuous stochastic control cost & goal-reaching rate via
    antithetic/seeded Monte Carlo Euler-Maruyama trajectories.
    """
    rng = np.random.default_rng(seed)
    X = np.repeat(np.atleast_2d(start_pt), n_rollouts, axis=0)
    alive = np.ones(n_rollouts, dtype=bool)
    total_cost = np.zeros(n_rollouts, dtype=float)

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
        X[a_idx] = X_nxt
        total_cost[a_idx] += sc

    hit_end = alive & (np.linalg.norm(X - goal_center[None, :], axis=1) <= goal_radius)
    alive[hit_end] = False
    # Remaining alive trajectories failed to hit goal within horizon -> incur timeout penalty
    total_cost[alive] += float(timeout_penalty)
    success_rate = float(np.mean(~alive))
    return {
        "mean_cost": float(np.mean(total_cost)),
        "success_rate": success_rate,
    }


def run_single_continuous_rotated_map_benchmark(seed: int, n_explore_steps: int = 36000, n_goals: int = 12) -> dict:
    """Runs one complete continuous-state rotated multi-room map (`seed`) comparing `Continuous_SPQL`
    against `Continuous_RBF_LinearRL`, `Continuous_Scalar_EigenOptions`, and `Continuous_Kernel_SoftQ`.
    """
    world = RotatedContinuousDiffusionWorld(seed=seed)
    rng = np.random.default_rng(seed + 500)

    # 1. Collect purely continuous reward-free Brownian/exploratory rollouts `(X_t, X_{t+1}, step_q_t)`
    n_eps = 180
    ep_len = n_explore_steps // n_eps
    starts = world.sample_free_points(n_eps, seed=seed + 501)
    X_cur_list, X_nxt_list, q_obs_list = [], [], []
    X_ep = starts.copy()
    for _ in range(ep_len):
        U_zero = rng.normal(0.0, 0.35, size=X_ep.shape)
        X_n, _ = world.step_batch(X_ep, U_zero, rng)
        q_step = np.clip(world.running_cost(X_ep) * world.dt + rng.normal(0.0, 0.005, size=len(X_ep)), 0.005, 0.12)
        X_cur_list.append(X_ep.copy())
        X_nxt_list.append(X_n.copy())
        q_obs_list.append(q_step)
        X_ep = X_n

    X_curr = np.vstack(X_cur_list)
    X_next = np.vstack(X_nxt_list)
    q_obs = np.concatenate(q_obs_list)

    landmarks, tree, ds = build_voronoi_quotient_from_continuous_trajectories(
        X_curr, X_next, q_obs, n_landmarks=400, lam_disc=world.lam, seed=seed + 502
    )

    # 2. Fit all 4 multi-goal learners on the EXACT SAME empirical dataset
    spql = SPQLPlanner(ds, delta=0.05, eps_tol=0.05, max_rooms=6)
    sr_pl = LowRankSRLinearRLPlanner(ds, rank_k=max(12, len(spql.dec.portal_nodes_loc) * 2))
    scal_pl = ScalarBottleneckOptionPlanner(spql)
    mfq_pl = ModelFreeGoalSoftQPlanner(ds, n_sweeps=14, seed=seed + 777)
    lm_running_q = np.where(ds.visit_counts > 0, (ds.cost_sums / np.maximum(ds.visit_counts, 1)) / world.dt, 0.6)

    # 3. Sample `n_goals` unseen cross-quadrant continuous `(start_pt, goal_center)` tasks
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

    methods_out = {k: {"costs": [], "succ": [], "query_ms": []} for k in ("SPQL", "RBF_LinearRL", "Scalar_EigenOptions", "Kernel_SoftQ")}
    for t_idx, (s_pt, g_ctr, s_id, gm) in enumerate(tasks_c):
        r_sp = spql.solve_unseen_goal(s_id, gm)
        r_sr = sr_pl.solve_unseen_goal(s_id, gm)
        r_sc = scal_pl.solve_unseen_goal(s_id, gm)
        r_fq = mfq_pl.solve_unseen_goal(s_id, gm)

        for m_nm, r_dict in (("SPQL", r_sp), ("RBF_LinearRL", r_sr), ("Scalar_EigenOptions", r_sc), ("Kernel_SoftQ", r_fq)):
            ctrl = make_continuous_control_from_landmark_policy(
                landmarks, tree, r_dict["Pi_ext_csr"], gm, g_ctr, world.dt, world.u_clip, landmark_running_q=lm_running_q
            )
            ev = evaluate_continuous_policy_rollouts(world, ctrl, s_pt, g_ctr, n_rollouts=80, seed=seed * 100 + t_idx)
            methods_out[m_nm]["costs"].append(ev["mean_cost"])
            methods_out[m_nm]["succ"].append(ev["success_rate"])
            methods_out[m_nm]["query_ms"].append(float(r_dict["query_ms"]))

    return {
        "seed": seed,
        "n_landmarks": len(landmarks),
        "discovered_rooms": len(spql.dec.room_nodes),
        "discovered_portals": len(spql.dec.portal_nodes_loc),
        "methods": {
            k: {
                "mean_closed_loop_cost": float(np.mean(v["costs"])),
                "mean_success_rate": float(np.mean(v["succ"])),
                "mean_query_ms": float(np.mean(v["query_ms"])),
            }
            for k, v in methods_out.items()
        },
    }
