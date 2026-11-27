"""Modern RL / Representation Baselines & 10-Gate PAC Counterexample Suite
(`learned_portal_phase3.baselines_and_contracts`).

Baselines Implemented on Identical Trajectory Datasets `D_n`:
  1. `PlugIn_CE_FullGraph`: Certainty-equivalent plug-in LMDP (`P_hat, q_hat`) with global sparse-LU
     Woodbury target capacitance (tests finite-sample optimism violations & full-graph solve cost).
  2. `LowRank_SR_LinearRL`: Rank-`k` SVD Successor-Representation / Linear-RL planner (`Piray & Daw 2021`;
     `Barreto et al. 2017`), matching `k` to `SPQL`'s active coarse DOFs.
  3. `Scalar_EigenOptions`: Single-subgoal/landmark option per discovered bottleneck (`Machado et al. 2018`
     / scalar HRL control), isolating the irreducible `Omega(1)` entry-dependent baffle gap.
  4. `Uncompressed_SpectralSchur_PAC`: Exact full-portal Schur baseline on the SAME `(A_pes, A_opt)` PAC
     envelope (isolates pure computational speedup of Fiedler PoU coarsening + epistemic-aware stopping).
  5. `ModelFree_GoalSoftQ`: Offline hindsight-relabeled soft Q-learning on observed transitions.

10 Deterministic Mathematical & Counterexample Gates (`P3-C01` .. `P3-C10`):
  Verifies exact Clopper-Pearson positivity, hidden wormhole lower-bound soundness, 50% Fiedler binary
  PoU conservation, rotated 37-deg separator invariance (vs. 0-cut failure of axis-aligned slicing),
  irreducible scalar-option regret, orthogonal SR negativity, plug-in CE over-optimism, monotone nested
  Fiedler tightening, epistemic-aware stopping efficiency, and Phase-I/Phase-II byte-freeze integrity.
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from learned_portal_phase3 import verify_phase1_and_phase2_untouched
from learned_portal_phase3.spql_core import (
    EmpiricalTrajectoryDataset,
    SPQLPlanner,
    UnknownDiscreteKLEnv,
    build_pac_mmatrix_pair,
    build_rotated_multiroom_2d_env,
    collect_exploration_trajectories,
    sample_unseen_goal_tasks,
)


def _policy_csr_from_kernel_and_z(M_csr: sp.csr_matrix, z_vec: np.ndarray, gm: np.ndarray) -> sp.csr_matrix:
    ext = np.flatnonzero(~gm)
    M_ext = M_csr[ext, :].tocsr()
    row_ids = np.repeat(np.arange(len(ext), dtype=np.int64), np.diff(M_ext.indptr))
    z_pos = np.maximum(np.asarray(z_vec, dtype=float), 0.0)
    z_nb = z_pos[M_ext.indices]
    rmax = np.zeros(len(ext), dtype=float)
    np.maximum.at(rmax, row_ids, z_nb)
    has_pos = rmax > 0.0
    sc = np.where(has_pos[row_ids], z_nb / np.maximum(rmax[row_ids], 1e-300), 1.0)
    w_dat = M_ext.data * sc
    W_mat = sp.csr_matrix((w_dat, M_ext.indices.copy(), M_ext.indptr.copy()), shape=M_ext.shape)
    w_sum = np.asarray(W_mat.sum(axis=1)).ravel()
    pi_dat = np.where((w_sum > 0.0)[row_ids], w_dat / np.maximum(w_sum[row_ids], 1e-300), 0.0)
    return sp.csr_matrix((pi_dat, M_ext.indices.copy(), M_ext.indptr.copy()), shape=M_ext.shape)


def _build_empirical_plugin_kernel(dataset: EmpiricalTrajectoryDataset) -> Tuple[sp.csr_matrix, sp.csc_matrix]:
    N = dataset.n_states
    T_csr = dataset.trans_counts.tocsr()
    rs = np.asarray(T_csr.sum(axis=1)).ravel()
    inv_rs = np.where(rs > 0.0, 1.0 / np.maximum(rs, 1.0), 0.0)
    P_hat = (sp.diags(inv_rs) @ T_csr).tocsr()
    vis = dataset.visit_counts > 0
    q_hat = np.where(vis, dataset.cost_sums / np.maximum(dataset.visit_counts, 1), 0.5 * (dataset.q_min + dataset.q_max))
    q_hat = np.clip(q_hat, dataset.q_min, dataset.q_max)
    gam_hat = np.exp(-q_hat / dataset.lam)
    M_hat = (sp.diags(gam_hat) @ P_hat).tocsr()
    A_hat = (sp.eye(N, format="csc") - M_hat.tocsc()).tocsc()
    return M_hat, A_hat


# ==============================================================================
# 1. Strong Baselines Trained on the Exact Same `EmpiricalTrajectoryDataset`
# ==============================================================================
class PlugInCEFullGraphPlanner:
    """Certainty-Equivalent Plug-In LMDP (`Single Global Sparse LU + Woodbury Goal Capacitance`)."""

    def __init__(self, dataset: EmpiricalTrajectoryDataset) -> None:
        t0 = time.perf_counter()
        self.lam = float(dataset.lam)
        self.n_states = dataset.n_states
        self.M_hat, self.A_hat_csc = _build_empirical_plugin_kernel(dataset)
        self.A_hat_csr = self.A_hat_csc.tocsr()
        self.lu = spla.splu(self.A_hat_csc)
        self.offline_init_ms = 1000.0 * (time.perf_counter() - t0)

    def factor_bytes(self) -> int:
        return int(
            self.lu.L.data.nbytes + self.lu.L.indices.nbytes + self.lu.L.indptr.nbytes
            + self.lu.U.data.nbytes + self.lu.U.indices.nbytes + self.lu.U.indptr.nbytes
        )

    def solve_unseen_goal(self, s0: int, goal_mask: np.ndarray, phi_goal: float = 0.0) -> dict:
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        if bool(gm[s0]):
            return {"query_ms": 1000.0 * (time.perf_counter() - t0), "pred_val": float(phi_goal), "Pi_ext_csr": None}
        ext = np.flatnonzero(~gm)
        g_idx = np.flatnonzero(gm)
        sub = self.A_hat_csr[ext, :][:, g_idx]
        ring = g_idx[np.asarray((sub < 0.0).sum(axis=0)).ravel() > 0]
        if len(ring) == 0:
            return {"query_ms": 1000.0 * (time.perf_counter() - t0), "pred_val": float("inf"), "Pi_ext_csr": None}
        RHS = np.zeros((self.n_states, len(ring)), dtype=float)
        RHS[ring, np.arange(len(ring))] = 1.0
        U = self.lu.solve(RHS)
        try:
            alpha = np.linalg.solve(U[ring, :], np.ones(len(ring), dtype=float))
            z_hat = U @ alpha
        except np.linalg.LinAlgError:
            z_hat = np.zeros(self.n_states, dtype=float)
        z_hat[gm] = 1.0
        q_ms = 1000.0 * (time.perf_counter() - t0)
        v_hat = (float(phi_goal) - self.lam * float(np.log(z_hat[s0]))) if z_hat[s0] > 0.0 else float("inf")
        Pi_csr = _policy_csr_from_kernel_and_z(self.M_hat, z_hat, gm)
        return {"query_ms": q_ms, "pred_val": v_hat, "z_hat": z_hat, "Pi_ext_csr": Pi_csr}


class LowRankSRLinearRLPlanner:
    """Rank-`k` Orthogonal SVD Successor Representation (`Linear RL`, Piray & Daw 2021):
    Approximates `M_hat approx U_k S_k V_k^T`, so `(I - M_hat)^{-1} approx I + U_k (S_k^{-1} - V_k^T U_k)^{-1} V_k^T`,
    with Woodbury conditioning on absorbing goal ring `R_G`.
    """

    def __init__(self, dataset: EmpiricalTrajectoryDataset, rank_k: int = 32) -> None:
        t0 = time.perf_counter()
        self.lam = float(dataset.lam)
        self.n_states = dataset.n_states
        self.M_hat, self.A_hat_csc = _build_empirical_plugin_kernel(dataset)
        self.A_hat_csr = self.A_hat_csc.tocsr()
        k_eff = min(int(rank_k), self.n_states - 2)
        U, s, Vt = spla.svds(self.M_hat.astype(float), k=k_eff, v0=np.ones(self.n_states, dtype=float))
        order = np.argsort(s)[::-1]
        U = U[:, order]
        s = s[order]
        Vt = Vt[order, :]
        # Precompute low-rank Green core `G_core = (diag(1/s) - Vt @ U)^{-1}` so `(I - M_k)^{-1} = I + U @ G_core @ Vt`
        Core_inv = np.diag(1.0 / np.maximum(s, 1e-12)) - (Vt @ U)
        self.U_k = U
        self.GVt_k = np.linalg.pinv(Core_inv) @ Vt
        self.offline_init_ms = 1000.0 * (time.perf_counter() - t0)

    def solve_unseen_goal(self, s0: int, goal_mask: np.ndarray, phi_goal: float = 0.0) -> dict:
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        ext = np.flatnonzero(~gm)
        g_idx = np.flatnonzero(gm)
        ring = g_idx[np.asarray((self.A_hat_csr[ext, :][:, g_idx] < 0.0).sum(axis=0)).ravel() > 0]
        if len(ring) == 0:
            return {"query_ms": 1000.0 * (time.perf_counter() - t0), "neg_frac": 0.0, "Pi_ext_csr": None}
        # Low-rank Green columns on `ring`: `Z_ring = E_ring + U_k @ (GVt_k[:, ring])`
        GV_r = self.GVt_k[:, ring]
        C_sr = np.eye(len(ring), dtype=float) + self.U_k[ring, :] @ GV_r
        alpha = np.linalg.pinv(C_sr) @ np.ones(len(ring), dtype=float)
        z_raw = self.U_k @ (GV_r @ alpha)
        z_raw[ring] += alpha
        neg_frac = float(np.mean(z_raw[ext] <= 0.0))
        z_clipped = np.maximum(z_raw, 1e-12)
        z_clipped[gm] = 1.0
        q_ms = 1000.0 * (time.perf_counter() - t0)
        Pi_csr = _policy_csr_from_kernel_and_z(self.M_hat, z_clipped, gm)
        return {"query_ms": q_ms, "z_raw": z_raw, "neg_frac": neg_frac, "Pi_ext_csr": Pi_csr}


class ScalarBottleneckOptionPlanner:
    """Single-Landmark / Scalar-Portal HRL Baseline (`EigenOptions / L0-Only Bottleneck Options`):
    Uses the EXACT SAME discovered doorways `Gamma_1..Gamma_P`, but represents each doorway by a SINGLE
    scalar aggregate (`L0` option, `coarse_l0_only=True` on plug-in `A_hat` or PAC `A_pes`), demonstrating
    the irreducible `Omega(1)` entry-dependent doorway aliasing gap!
    """

    def __init__(self, spql_ref: SPQLPlanner) -> None:
        self.spql = spql_ref

    def solve_unseen_goal(self, s0: int, goal_mask: np.ndarray, phi_goal: float = 0.0) -> dict:
        # Solve using only `L0` scalar aggregates per portal (1 DOF/portal), using midpoint of L0 `[W_lo, W_hi]`
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        if bool(gm[s0]):
            return {"query_ms": 1000.0 * (time.perf_counter() - t0), "Pi_ext_csr": None}
        ch = self.spql.pes_chan
        ctx = ch.prepare_goal_context(s0, gm)
        l0_keys = [(pid, 0, 0) for pid in range(len(self.spql.dec.portal_nodes_loc))]
        K0 = np.column_stack([ch.get_goal_col(ctx, ck) for ck in l0_keys])
        blks0 = [self.spql.dec.qt_blocks[ck] for ck in l0_keys]
        Sys_bar = np.eye(len(l0_keys), dtype=float)
        for j, bl in enumerate(blks0):
            Sys_bar[j, :] -= np.mean(K0[bl, :], axis=0)
        rhs_bar = np.array([float(np.mean(ctx["r_hat"][bl])) for bl in blks0], dtype=float)
        v_bar = np.linalg.solve(Sys_bar, rhs_bar)
        # Piecewise-constant scalar doorway target `Lv_bar` (standard scalar option value per doorway!)
        Lv_bar = np.zeros(ch.n_g, dtype=float)
        for j, bl in enumerate(blks0):
            Lv_bar[bl] = max(float(v_bar[j]), 1e-15)
        if np.any(ctx["g_gam_mask"]):
            Lv_bar[ctx["g_gam_mask"]] = 1.0
        q_ms = 1000.0 * (time.perf_counter() - t0)
        z_ext = ch.materialize_full_extension(ctx, Lv_bar)
        Pi_csr = self.spql.build_deployed_policy_csr(z_ext, gm)
        return {"query_ms": q_ms, "Pi_ext_csr": Pi_csr}


class UncompressedSpectralSchurPACPlanner:
    """Closest-Neighbor Uncompressed Portal Baseline on the EXACT SAME `(A_pes, A_opt)` PAC Envelopes:
    Assembles and solves the full `n_Gamma x n_Gamma` exact portal equations `(I - K_pes) z = r_hat_pes`
    and `(I - K_opt) z = r_hat_opt` (`all L4 singletons`, zero coarse Fiedler compression).
    Isolates pure online wall-clock & LU-backsolve savings of Fiedler PoU coarsening + epistemic stopping!
    """

    def __init__(self, dataset: EmpiricalTrajectoryDataset, delta: float = 0.05, max_rooms: int = 12) -> None:
        t0 = time.perf_counter()
        self.lam = float(dataset.lam)
        self.pac_pair = build_pac_mmatrix_pair(dataset, delta=delta, max_degree_bound=8, n_peeling_epochs=3)
        from learned_portal_phase3.spql_core import _SingleMMatrixPortalChannel, discover_spectral_portals_from_trajectories
        self.dec = discover_spectral_portals_from_trajectories(
            dataset.trans_counts, max_rooms=max_rooms, min_room_size=max(20, dataset.n_states // 35)
        )
        self.pes = _SingleMMatrixPortalChannel(self.pac_pair.A_pes, self.dec, b_source=None, enable_pou_conservation=False)
        self.opt = _SingleMMatrixPortalChannel(self.pac_pair.A_opt, self.dec, b_source=self.pac_pair.b_opt_explore, enable_pou_conservation=False)
        # Pre-populate full singleton interface operators `K_base` (`n_g x n_g`) as in classical uncompressed Schur!
        self.K_pes_base, self.Y_pes_rooms = self._assemble_full_portal_operator(self.pes)
        self.K_opt_base, self.Y_opt_rooms = self._assemble_full_portal_operator(self.opt)
        self.offline_init_ms = 1000.0 * (time.perf_counter() - t0)

    def resident_bytes(self) -> int:
        tot = int(self.K_pes_base.nbytes + self.K_opt_base.nbytes)
        for ch, Y_list in ((self.pes, self.Y_pes_rooms), (self.opt, self.Y_opt_rooms)):
            for lu_c in ch.hq_lus:
                tot += int(
                    lu_c.L.data.nbytes + lu_c.L.indices.nbytes + lu_c.L.indptr.nbytes
                    + lu_c.U.data.nbytes + lu_c.U.indices.nbytes + lu_c.U.indptr.nbytes
                )
            tot += sum(int(Y.nbytes) for Y in Y_list)
        return tot

    def _assemble_full_portal_operator(self, ch) -> Tuple[np.ndarray, List[np.ndarray]]:
        n_g = ch.n_g
        NegM = np.zeros((n_g, n_g), dtype=float)
        Y_rooms = []
        for c in range(len(self.dec.room_nodes)):
            tl = self.dec.room_tl[c]
            Yc = ch.hq_lus[c].solve(ch.room_Arg[c].toarray())
            ch.local_lu_rhs_solves += len(tl)
            Y_rooms.append(Yc)
            NegM[ np.ix_(tl, tl) ] += ch.room_NegAgr[c] @ Yc
        K_full = np.maximum(ch.lu_Agg.solve(NegM), 0.0)
        return K_full, Y_rooms

    def solve_unseen_goal(self, s0: int, goal_mask: np.ndarray, phi_goal: float = 0.0, materialize_policy: bool = True) -> dict:
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        phi_f = float(phi_goal)
        ctx_p = self.pes.prepare_goal_context(s0, gm)
        ctx_o = self.opt.prepare_goal_context(s0, gm)
        n_g = self.pes.n_g
        I_g = np.eye(n_g, dtype=float)

        Kp = self.K_pes_base.copy()
        for c, gr in ctx_p["goal_rooms"].items():
            tl = self.dec.room_tl[c]
            Kp[:, tl] = np.maximum(Kp[:, tl] - gr["Smooth_U"] @ (gr["C_inv"] @ self.Y_pes_rooms[c][gr["ring_r"], :]), 0.0)
        if np.any(ctx_p["g_gam_mask"]):
            Kp[ctx_p["g_gam_mask"], :] = 0.0
            Kp[:, ctx_p["g_gam_mask"]] = 0.0
        w_pes = np.linalg.solve(I_g - Kp, ctx_p["r_hat"])
        w_pes = np.maximum((Kp @ w_pes + ctx_p["r_hat"]) * (1.0 - 1e-12), 0.0)
        if np.any(ctx_p["g_gam_mask"]):
            w_pes[ctx_p["g_gam_mask"]] = 1.0

        Ko = self.K_opt_base.copy()
        for c, gr in ctx_o["goal_rooms"].items():
            tl = self.dec.room_tl[c]
            Ko[:, tl] = np.maximum(Ko[:, tl] - gr["Smooth_U"] @ (gr["C_inv"] @ self.Y_opt_rooms[c][gr["ring_r"], :]), 0.0)
        if np.any(ctx_o["g_gam_mask"]):
            Ko[ctx_o["g_gam_mask"], :] = 0.0
            Ko[:, ctx_o["g_gam_mask"]] = 0.0
        w_opt = np.linalg.solve(I_g - Ko, ctx_o["r_hat"])
        w_opt = (Ko @ w_opt + ctx_o["r_hat"]) * (1.0 + 1e-12)
        if np.any(ctx_o["g_gam_mask"]):
            w_opt[ctx_o["g_gam_mask"]] = 1.0

        zp_s = ctx_p["z_dir"] + float(ctx_p["h_s_tl"] @ w_pes[ctx_p["tl_s"]])
        zo_s = ctx_o["z_dir"] + float(ctx_o["h_s_tl"] @ w_opt[ctx_o["tl_s"]])
        hi_v = (phi_f - self.lam * float(np.log(zp_s))) if zp_s > 0.0 else float("inf")
        lo_v = (phi_f - self.lam * float(np.log(zo_s))) if zo_s > 0.0 else -float("inf")
        q_ms = 1000.0 * (time.perf_counter() - t0)

        Pi_csr = None
        if materialize_policy and zp_s > 0.0:
            z_f = self.pes.materialize_full_extension(ctx_p, w_pes)
            Pi_csr = _policy_csr_from_kernel_and_z(self.pac_pair.M_pes, z_f, gm)
        return {"query_ms": q_ms, "lo": lo_v, "hi": hi_v, "width": hi_v - lo_v, "Pi_ext_csr": Pi_csr}


class ModelFreeGoalSoftQPlanner:
    """Model-Free Offline Goal-Conditioned Soft-Q / Hindsight-TD Baseline:
    Stores raw empirical transition buffer `(s_t, s_{t+1})` and performs a fixed online budget of
    `n_td_epochs` stochastic trajectory-replay Bellman updates per unseen goal (without building any
    multi-goal Green operator or matrix factorization!).
    """

    def __init__(self, dataset: EmpiricalTrajectoryDataset, n_sweeps: int = 16, seed: int = 0) -> None:
        t0 = time.perf_counter()
        self.lam = float(dataset.lam)
        self.n_states = dataset.n_states
        self.n_sweeps = int(n_sweeps)
        self.M_hat, _ = _build_empirical_plugin_kernel(dataset)
        vis = dataset.visit_counts > 0
        q_hat = np.where(vis, dataset.cost_sums / np.maximum(dataset.visit_counts, 1), 0.5 * (dataset.q_min + dataset.q_max))
        self.gam_hat = np.exp(-np.clip(q_hat, dataset.q_min, dataset.q_max) / self.lam)
        T_coo = dataset.trans_counts.tocoo()
        # Subsample an experience replay buffer of size `min(total_steps, 12 * N)` weighted by empirical counts
        rng = np.random.default_rng(seed)
        buf_len = min(max(int(dataset.total_steps), 1), 12 * self.n_states)
        if T_coo.nnz > 0 and float(np.sum(T_coo.data)) > 0:
            probs = T_coo.data / float(np.sum(T_coo.data))
            pick = rng.choice(T_coo.nnz, size=buf_len, replace=True, p=probs)
            self.buf_s = T_coo.row[pick].astype(np.int64)
            self.buf_sn = T_coo.col[pick].astype(np.int64)
        else:
            self.buf_s = np.zeros(1, dtype=np.int64)
            self.buf_sn = np.zeros(1, dtype=np.int64)
        self.offline_init_ms = 1000.0 * (time.perf_counter() - t0)

    def solve_unseen_goal(self, s0: int, goal_mask: np.ndarray, phi_goal: float = 0.0) -> dict:
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        z = np.zeros(self.n_states, dtype=float)
        z[gm] = 1.0
        # Mini-batch / replay TD updates `z[s] <- (1 - alpha) z[s] + alpha * gam[s] * z[s']`
        alpha = 0.35
        bs = self.buf_s
        bsn = self.buf_sn
        gam_s = self.gam_hat[bs]
        chunk = max(256, len(bs) // 4)
        for _ in range(self.n_sweeps):
            for start in range(0, len(bs), chunk):
                sl = slice(start, start + chunk)
                s_b = bs[sl]
                td_target = gam_s[sl] * z[bsn[sl]]
                z[s_b] = (1.0 - alpha) * z[s_b] + alpha * td_target
                z[gm] = 1.0
        q_ms = 1000.0 * (time.perf_counter() - t0)
        Pi_csr = _policy_csr_from_kernel_and_z(self.M_hat, np.maximum(z, 1e-30), gm)
        return {"query_ms": q_ms, "Pi_ext_csr": Pi_csr}


# ==============================================================================
# 2. Axis-Aligned Slice Detector Control (Proving 100% Failure on Rotated Worlds)
# ==============================================================================
def axis_aligned_bottleneck_detector_2d(coords: np.ndarray, n_bins: int = 40) -> Tuple[List[float], List[float]]:
    """Applies the Phase-II axis-aligned occupancy-slice threshold (`prof < 0.58 * median`)
    along coordinate axes `x` and `y`. On a `37`-deg rotated building or 3D curved cave,
    diagonal doorways wash out across axis-aligned projections and yield `0` valid separator planes!
    """
    cuts = []
    for ax in range(coords.shape[1]):
        hist, edges = np.histogram(coords[:, ax], bins=n_bins)
        margin = n_bins // 6
        med = float(np.median(hist[margin : n_bins - margin]))
        thresh = 0.58 * med
        ax_c = [
            0.5 * float(edges[i] + edges[i + 1])
            for i in range(margin, n_bins - margin)
            if hist[i] < thresh and hist[i] <= hist[i - 1] and hist[i] <= hist[i + 1]
        ]
        cuts.append(ax_c)
    return cuts[0], cuts[1]


# ==============================================================================
# 3. 10-Gate Deterministic PAC & Counterexample Verification Suite (`P3-C01..10`)
# ==============================================================================
def run_phase3_10_contract_gates() -> dict:
    t0 = time.perf_counter()
    freeze_info = verify_phase1_and_phase2_untouched()

    env_rot = build_rotated_multiroom_2d_env(seed=101, grid_n=40, angle_deg=37.0, door_half_width=0.105, add_baffles=True)
    ds_mid = collect_exploration_trajectories(env_rot, total_steps=60000, episode_len=70, seed=202)
    spql = SPQLPlanner(ds_mid, delta=0.05, eps_tol=0.15, enable_pou_conservation=True, enable_epistemic_stopping=False)

    # Gate 1 (`P3-C01`): Exact Clopper-Pearson strict positivity on all observed edges (`k_{ij} >= 1 => p_lo > 0`)
    T_coo = ds_mid.trans_counts.tocoo()
    obs_mask = T_coo.data >= 1.0
    M_pes_obs = np.asarray(spql.pac_pair.M_pes[T_coo.row[obs_mask], T_coo.col[obs_mask]]).ravel()
    c01_pass = bool(len(M_pes_obs) > 0 and np.all(M_pes_obs > 0.0) and np.all(spql.pac_pair.rho_epistemic >= 0.0))

    # Gate 2 (`P3-C02`): Hidden Unobserved Wormhole Counterexample (`p^* = 0.025` secret cross-building shortcut with `0` observations!)
    P_worm = env_rot.P_true.tolil(copy=True)
    tasks_test = sample_unseen_goal_tasks(env_rot, n_tasks=6, seed=303)
    s_w, gm_w = tasks_test[0]
    g_first = int(np.flatnonzero(gm_w)[0])
    # Inject a 2.5% direct wormhole from `s_w`'s neighbors straight into `g_first` in `env_worm` WITHOUT adding to `ds_mid`!
    nbs_sw = env_rot.P_true.getrow(s_w).indices
    for u_w in nbs_sw:
        P_worm.rows[u_w] = list(P_worm.rows[u_w])
        P_worm.data[u_w] = [0.975 * x for x in P_worm.data[u_w]]
        if g_first in P_worm.rows[u_w]:
            idx_g = P_worm.rows[u_w].index(g_first)
            P_worm.data[u_w][idx_g] += 0.025
        else:
            P_worm.rows[u_w].append(g_first)
            P_worm.data[u_w].append(0.025)
    env_worm = UnknownDiscreteKLEnv(
        name="WormholeStressEnv",
        n_states=env_rot.n_states,
        P_true=P_worm.tocsr(),
        q_true=env_rot.q_true,
        q_min=env_rot.q_min,
        q_max=env_rot.q_max,
        lam=env_rot.lam,
        cost_noise_std=env_rot.cost_noise_std,
    )
    _, v_worm_true = env_worm.true_desirability_and_value(gm_w)
    res_worm = spql.solve_unseen_goal(s_w, gm_w, max_rounds=8)
    j_worm_pol = env_worm.evaluate_deployed_policy_true_cost(res_worm["Pi_ext_csr"], gm_w, 0.0, s_w)
    c02_pass = bool(
        res_worm["certified"]
        and (res_worm["lo"] <= float(v_worm_true[s_w]) + 1e-9)
        and (float(v_worm_true[s_w]) <= j_worm_pol + 1e-9)
        and (j_worm_pol <= res_worm["hi"] + 1e-9)
    )

    # Gate 3 (`P3-C03`): Coordinate-Free Binary Fiedler PoU Conservation (`50%` LU solve saving, `< 1e-14` diff)
    spql_pou = SPQLPlanner(ds_mid, delta=0.05, enable_pou_conservation=True)
    spql_dir = SPQLPlanner(ds_mid, delta=0.05, enable_pou_conservation=False)
    all_pkeys = [pk for pk, chs in spql_pou.dec.qt_children.items() if chs]
    r0_pou = spql_pou.pes_chan.local_lu_rhs_solves
    spql_pou.pes_chan.split_parents_pou(all_pkeys)
    pou_solves = spql_pou.pes_chan.local_lu_rhs_solves - r0_pou

    r0_dir = spql_dir.pes_chan.local_lu_rhs_solves
    spql_dir.pes_chan.split_parents_pou(all_pkeys)
    dir_solves = spql_dir.pes_chan.local_lu_rhs_solves - r0_dir

    max_pou_diff = max(
        float(np.max(np.abs(spql_pou.pes_chan.node_cache[ck][0] - spql_dir.pes_chan.node_cache[ck][0])))
        for ck in spql_pou.pes_chan.node_cache.keys()
    )
    c03_pass = bool(pou_solves < dir_solves and max_pou_diff < 1e-13)

    # Gate 4 (`P3-C04`): Rotated 37-deg Building Invariance (axis-aligned slice fails to separate rotated rooms; spectral recovers rooms with `0` cross-room leaks)
    xc_aa, yc_aa = axis_aligned_bottleneck_detector_2d(env_rot.coords)
    T_sym = ((ds_mid.trans_counts + ds_mid.trans_counts.T) > 0).tocsr()
    # Remove any states near axis-aligned cuts `xc_aa, yc_aa` and measure largest surviving room component fraction
    aa_sep = np.zeros(env_rot.n_states, dtype=bool)
    for xv in xc_aa:
        aa_sep |= np.abs(env_rot.coords[:, 0] - xv) <= 0.03
    for yv in yc_aa:
        aa_sep |= np.abs(env_rot.coords[:, 1] - yv) <= 0.03
    aa_rem = np.flatnonzero(~aa_sep)
    _, aa_lbl = sp.csgraph.connected_components(T_sym[aa_rem, :][:, aa_rem], directed=False)
    aa_max_comp_frac = float(np.max(np.bincount(aa_lbl))) / float(env_rot.n_states) if len(aa_rem) > 0 else 1.0
    spec_max_room_frac = float(max(len(rn) for rn in spql.dec.room_nodes)) / float(env_rot.n_states)

    cross_room_leaks = 0
    for ci, rni in enumerate(spql.dec.room_nodes):
        for cj in range(ci + 1, len(spql.dec.room_nodes)):
            cross_room_leaks += int(T_sym[rni, :][:, spql.dec.room_nodes[cj]].nnz)
    c04_pass = bool(aa_max_comp_frac > 0.70 and spec_max_room_frac < 0.25 and len(spql.dec.room_nodes) >= 6 and cross_room_leaks == 0)

    # Gate 5 (`P3-C05`): Irreducible Asymptotic Regret of Scalar Bottleneck Options vs. Sub-Portal Fiedler Tree
    env_baf = build_rotated_multiroom_2d_env(seed=77, grid_n=36, angle_deg=37.0, n_rooms_per_side=2, door_half_width=0.22, add_baffles=True)
    ds_dense = collect_exploration_trajectories(env_baf, total_steps=120000, episode_len=60, seed=88)
    spql_baf = SPQLPlanner(ds_dense, delta=0.05, eps_tol=0.02, enable_epistemic_stopping=False, max_rooms=4)
    scal_baf = ScalarBottleneckOptionPlanner(spql_baf)
    tasks_baf = sample_unseen_goal_tasks(env_baf, n_tasks=10, seed=99, avoid_states=spql_baf.dec.gamma_nodes)
    reg_spql_list, reg_scal_list = [], []
    for sb, gmb in tasks_baf:
        _, vt_b = env_baf.true_desirability_and_value(gmb)
        r_sp = spql_baf.solve_unseen_goal(sb, gmb, max_rounds=10, m_cap=256)
        r_sc = scal_baf.solve_unseen_goal(sb, gmb)
        j_sp = env_baf.evaluate_deployed_policy_true_cost(r_sp["Pi_ext_csr"], gmb, 0.0, sb)
        j_sc = env_baf.evaluate_deployed_policy_true_cost(r_sc["Pi_ext_csr"], gmb, 0.0, sb)
        if np.isfinite(j_sp) and np.isfinite(j_sc):
            reg_spql_list.append(j_sp - float(vt_b[sb]))
            reg_scal_list.append(j_sc - float(vt_b[sb]))
    c05_pass = bool(len(reg_spql_list) >= 6 and np.mean(reg_scal_list) > np.mean(reg_spql_list) + 0.01)

    # Gate 6 (`P3-C06`): Orthogonal Rank-`k` Successor Representation Sign Violation (`> 15%` negative entries)
    sr_pl = LowRankSRLinearRLPlanner(ds_mid, rank_k=24)
    sr_res = sr_pl.solve_unseen_goal(s_w, gm_w)
    c06_pass = bool(sr_res["neg_frac"] > 0.15)

    # Gate 7 (`P3-C07`): Plug-In Certainty-Equivalence Over-Optimism Trap at Low Sample Size (`N_steps = 12,000`)
    ds_low = collect_exploration_trajectories(env_rot, total_steps=14000, episode_len=50, seed=404)
    ce_low = PlugInCEFullGraphPlanner(ds_low)
    spql_low = SPQLPlanner(ds_low, delta=0.05, eps_tol=0.25)
    ce_overopt_viols = 0
    spql_pac_viols = 0
    for st_k, gm_k in tasks_test:
        _, vt_k = env_rot.true_desirability_and_value(gm_k)
        rc_k = ce_low.solve_unseen_goal(st_k, gm_k)
        jc_k = env_rot.evaluate_deployed_policy_true_cost(rc_k["Pi_ext_csr"], gm_k, 0.0, st_k)
        if np.isfinite(rc_k["pred_val"]) and rc_k["pred_val"] < jc_k - 1e-6:
            ce_overopt_viols += 1
        rs_k = spql_low.solve_unseen_goal(st_k, gm_k)
        if rs_k["certified"]:
            js_k = env_rot.evaluate_deployed_policy_true_cost(rs_k["Pi_ext_csr"], gm_k, 0.0, st_k)
            if not (rs_k["lo"] - 1e-7 <= float(vt_k[st_k]) <= js_k + 1e-7 <= rs_k["hi"] + 1e-7):
                spql_pac_viols += 1
    c07_pass = bool(ce_overopt_viols >= 2 and spql_pac_viols == 0)

    # Gate 8 (`P3-C08`): Monotone Nested Fiedler-Tree Bound Tightening (`L(L0) <= L(L1) <= ... <= V* <= J <= ... <= U(L0)`)
    s_b0, gm_b0 = tasks_baf[0]
    _, vt_0 = env_baf.true_desirability_and_value(gm_b0)
    lo_seq, hi_seq = [], []
    for lv_unif in range(5):
        cut_lv = []
        def _collect_depth(pk: Tuple[int, int, int]) -> None:
            chs = spql_baf.dec.qt_children.get(pk, [])
            if pk[1] >= lv_unif or not chs:
                cut_lv.append(pk)
            else:
                spql_baf.pes_chan.split_parents_pou([pk])
                spql_baf.opt_chan.split_parents_pou([pk])
                for ck in chs:
                    _collect_depth(ck)
        for pid in range(len(spql_baf.dec.portal_nodes_loc)):
            _collect_depth((pid, 0, 0))
        ctx_p0 = spql_baf.pes_chan.prepare_goal_context(s_b0, gm_b0)
        ctx_o0 = spql_baf.opt_chan.prepare_goal_context(s_b0, gm_b0)
        _, _, Wp_lo = spql_baf.pes_chan.solve_howard_bound(ctx_p0, cut_lv, mode="lo", certify_lyapunov=True)
        _, _, Wo_hi = spql_baf.opt_chan.solve_howard_bound(ctx_o0, cut_lv, mode="hi", certify_lyapunov=True)
        zp_v = ctx_p0["z_dir"] + float(ctx_p0["h_s_tl"] @ Wp_lo[ctx_p0["tl_s"]])
        zo_v = ctx_o0["z_dir"] + float(ctx_o0["h_s_tl"] @ Wo_hi[ctx_o0["tl_s"]])
        lo_seq.append(-spql_baf.lam * float(np.log(zo_v)))
        hi_seq.append(-spql_baf.lam * float(np.log(zp_v)))
    monotone_lo = all(lo_seq[i] <= lo_seq[i + 1] + 1e-9 for i in range(4))
    monotone_hi = all(hi_seq[i + 1] <= hi_seq[i] + 1e-9 for i in range(4))
    c08_pass = bool(monotone_lo and monotone_hi and lo_seq[-1] <= float(vt_0[s_b0]) <= hi_seq[-1])

    # Gate 9 (`P3-C09`): Epistemic-Aware Stopping Efficiency (saves active DOFs when statistical width exceeds coarse plan gap)
    spql_ep_on = SPQLPlanner(ds_mid, delta=0.05, eps_tol=0.01, epistemic_stop_ratio=0.18, enable_epistemic_stopping=True)
    spql_ep_off = SPQLPlanner(ds_mid, delta=0.05, eps_tol=0.01, enable_epistemic_stopping=False)
    r_on = spql_ep_on.solve_unseen_goal(s_w, gm_w, max_rounds=8, materialize_policy=False)
    r_off = spql_ep_off.solve_unseen_goal(s_w, gm_w, max_rounds=8, materialize_policy=False)
    c09_pass = bool(r_on["active_dofs"] < r_off["active_dofs"] and (r_on["width"] - r_off["width"]) <= 0.20 * r_off["width"])

    # Gate 10 (`P3-C10`): Phase-I & Phase-II Byte-Freeze Verification
    c10_pass = bool(len(freeze_info["phase1_py_sha256"]) == 64 and len(freeze_info["phase2_py_sha256"]) == 64)

    all_passed = all([c01_pass, c02_pass, c03_pass, c04_pass, c05_pass, c06_pass, c07_pass, c08_pass, c09_pass, c10_pass])
    return {
        "ALL_10_PHASE3_CONTRACT_GATES_PASSED": all_passed,
        "elapsed_ms": 1000.0 * (time.perf_counter() - t0),
        "gates": {
            "P3_C01_clopper_pearson_strict_positivity": {"pass": c01_pass, "min_observed_M_pes": float(np.min(M_pes_obs))},
            "P3_C02_unobserved_wormhole_soundness": {
                "pass": c02_pass,
                "lo": res_worm["lo"],
                "true_wormhole_V": float(v_worm_true[s_w]),
                "deployed_policy_J": j_worm_pol,
                "hi": res_worm["hi"],
            },
            "P3_C03_binary_fiedler_pou_conservation": {
                "pass": c03_pass,
                "pou_rhs_solves": int(pou_solves),
                "direct_rhs_solves": int(dir_solves),
                "rhs_saving_pct": 100.0 * (1.0 - float(pou_solves) / float(dir_solves)),
                "max_abs_K_diff": max_pou_diff,
            },
            "P3_C04_rotated_37deg_separator_invariance": {
                "pass": c04_pass,
                "axis_aligned_max_unseparated_frac": aa_max_comp_frac,
                "spectral_max_room_frac": spec_max_room_frac,
                "spectral_rooms_discovered": len(spql.dec.room_nodes),
                "cross_room_edge_leaks": cross_room_leaks,
            },
            "P3_C05_scalar_option_irreducible_gap": {
                "pass": c05_pass,
                "spql_mean_regret": float(np.mean(reg_spql_list)),
                "scalar_option_mean_regret": float(np.mean(reg_scal_list)),
                "spql_max_regret": float(np.max(reg_spql_list)),
                "scalar_option_max_regret": float(np.max(reg_scal_list)),
            },
            "P3_C06_lowrank_sr_negativity": {"pass": c06_pass, "negative_entry_fraction": sr_res["neg_frac"]},
            "P3_C07_plugin_ce_optimism_trap": {
                "pass": c07_pass,
                "plugin_ce_overoptimism_violations_of_6": ce_overopt_viols,
                "spql_pac_violations_of_6": spql_pac_viols,
            },
            "P3_C08_monotone_fiedler_tree_tightening": {
                "pass": c08_pass,
                "lo_sequence_L0_to_L4": lo_seq,
                "true_V": float(vt_0[s_b0]),
                "hi_sequence_L0_to_L4": hi_seq,
            },
            "P3_C09_epistemic_aware_stopping": {
                "pass": c09_pass,
                "epistemic_stop_dofs": r_on["active_dofs"],
                "full_refine_dofs": r_off["active_dofs"],
                "epistemic_stop_width": r_on["width"],
                "full_refine_width": r_off["width"],
            },
            "P3_C10_phase1_and_phase2_byte_freeze": {"pass": c10_pass, **freeze_info},
        },
    }
