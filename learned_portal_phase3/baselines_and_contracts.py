"""Strong Same-Data Baselines, Controlled Ablations, & 16-Gate PAC Counterexample Suite
(`learned_portal_phase3.baselines_and_contracts` — Repaired `v2` Closing `P3-P0-01..04` & `P3-E01..08`).

Comparators & Controlled Ablations Implemented on Identical Trajectory Datasets `D_n`:
  1. `PlugIn_CE_FullGraph` (`PlugInCEFullGraphPlanner`):
       Certainty-equivalent plug-in LMDP (`P_hat, q_hat`) with global sparse-LU Woodbury target capacitance.
  2. `Uncompressed_SpectralSchur_PAC` (`UncompressedSpectralSchurPACPlanner`):
       Pre-assembled full-portal `n_Gamma x n_Gamma` exact Schur solver on the EXACT SAME `(A_pes, A_opt)`
       time-uniform PAC envelopes (all-goal killed-portal exactness + unified post-policy query timing).
  3. `MatrixFree_SpectralSchur_PAC` (`MatrixFreeSpectralSchurPACPlanner`):
       Zero-assembly matrix-free Schur BiCGSTAB + Lyapunov-certified solver on the EXACT SAME `(A_pes, A_opt)`
       time-uniform PAC envelopes and room factorizations (closest-neighbor 3D Krylov control).
  4. `Scalar_L0_Portal_Ablation` (`ScalarBottleneckOptionPlanner`):
       Restricted 1-scalar-per-doorway (`L0`) portal ablation on the same discovered separator `Gamma_1..Gamma_P`,
       isolating the irreducible `Omega(1)` entry-dependent doorway aliasing gap.
  5. `TransitionSVD_Resolvent_Ablation` (`LowRankSRLinearRLPlanner`):
       Rank-`k` SVD transition-kernel resolvent approximation `(I - U_k S_k V_k^T)^{-1}` with Woodbury target
       conditioning, isolating orthogonal spectral sign violations (`neg_frac > 15%`).
  6. `Sampled_Desirability_TD` (`ModelFreeGoalSoftQPlanner`):
       Offline sampled desirability Bellman updates with exact per-minibatch state-grouped target averaging
       (`Closes P3-E04`: eliminates NumPy duplicate-index overwrite).

16 Deterministic & Statistical Contract Gates (`P3-C01` .. `P3-C16`):
  Embeds all original 10 gates PLUS all 6 `v13` independent audit counterexample probes (`4-state all-15-subset
  portal goals`, `392-state portal-goal exactness`, `2-look & multi-look predictable optional-stopping CP`,
  `boundary-unbiased bounded cost noise`, `zero continuous wall tunneling + group-mean TD`, and `tiny-probability
  proper support + fail-closed residual rejection`).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

import itertools
import math
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.stats import beta as sp_beta, binom as sp_binom

from learned_portal_phase3 import verify_phase1_and_phase2_untouched, verify_phase3_v1_archive_untouched
from learned_portal_phase3.spql_core import (
    EmpiricalTrajectoryDataset,
    SPQLPlanner,
    SpectralPortalDecomposition,
    UnknownDiscreteKLEnv,
    _SingleMMatrixPortalChannel,
    _recursive_fiedler_portal_tree,
    build_pac_mmatrix_pair,
    build_rotated_multiroom_2d_env,
    collect_exploration_trajectories,
    discover_spectral_portals_from_trajectories,
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
# 1. Strong Baselines & Controlled Ablations on Identical `EmpiricalTrajectoryDataset`
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
        self.init_lu_rhs = 0
        self.offline_init_ms = 1000.0 * (time.perf_counter() - t0)

    def resident_bytes(self) -> int:
        return int(
            self.lu.L.data.nbytes + self.lu.L.indices.nbytes + self.lu.L.indptr.nbytes
            + self.lu.U.data.nbytes + self.lu.U.indices.nbytes + self.lu.U.indptr.nbytes
        )

    def factor_bytes(self) -> int:
        return self.resident_bytes()

    def solve_unseen_goal(
        self, s0: int, goal_mask: np.ndarray, phi_goal: float = 0.0, materialize_policy: bool = True
    ) -> dict:
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        if bool(gm[s0]):
            q_ms = 1000.0 * (time.perf_counter() - t0)
            return {"query_ms": q_ms, "bounds_only_query_ms": q_ms, "pred_val": float(phi_goal), "Pi_ext_csr": None}
        ext = np.flatnonzero(~gm)
        g_idx = np.flatnonzero(gm)
        sub = self.A_hat_csr[ext, :][:, g_idx]
        ring = g_idx[np.asarray((sub < 0.0).sum(axis=0)).ravel() > 0]
        if len(ring) == 0:
            q_ms = 1000.0 * (time.perf_counter() - t0)
            return {"query_ms": q_ms, "bounds_only_query_ms": q_ms, "pred_val": float("inf"), "Pi_ext_csr": None}
        RHS = np.zeros((self.n_states, len(ring)), dtype=float)
        RHS[ring, np.arange(len(ring))] = 1.0
        U = self.lu.solve(RHS)
        try:
            alpha = np.linalg.solve(U[ring, :], np.ones(len(ring), dtype=float))
            z_hat = U @ alpha
        except np.linalg.LinAlgError:
            z_hat = np.zeros(self.n_states, dtype=float)
        z_hat[gm] = 1.0
        b_ms = 1000.0 * (time.perf_counter() - t0)
        v_hat = (float(phi_goal) - self.lam * float(np.log(z_hat[s0]))) if z_hat[s0] > 0.0 else float("inf")
        Pi_csr = _policy_csr_from_kernel_and_z(self.M_hat, z_hat, gm) if materialize_policy else None
        q_ms = 1000.0 * (time.perf_counter() - t0)
        return {
            "query_ms": q_ms,
            "bounds_only_query_ms": b_ms,
            "pred_val": v_hat,
            "z_hat": z_hat,
            "global_lu_rhs": int(len(ring)),
            "Pi_ext_csr": Pi_csr,
        }


class LowRankSRLinearRLPlanner:
    """`TransitionSVD_Resolvent_Ablation`:
    Rank-`k` Orthogonal SVD Transition-Kernel Resolvent Approximation (`M_hat approx U_k S_k V_k^T`,
    `(I - M_hat)^{-1} approx I + U_k (S_k^{-1} - V_k^T U_k)^{-1} V_k^T`) with Woodbury target conditioning.
    Isolates why orthogonal SVD modes violate desirability positivity (`neg_frac > 15%`).
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
        Core_inv = np.diag(1.0 / np.maximum(s, 1e-12)) - (Vt @ U)
        self.U_k = U
        self.GVt_k = np.linalg.pinv(Core_inv) @ Vt
        self.offline_init_ms = 1000.0 * (time.perf_counter() - t0)

    def solve_unseen_goal(self, s0: int, goal_mask: np.ndarray, phi_goal: float = 0.0) -> dict:
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        if bool(gm[s0]):
            return {"query_ms": 1000.0 * (time.perf_counter() - t0), "neg_frac": 0.0, "Pi_ext_csr": None}
        ext = np.flatnonzero(~gm)
        g_idx = np.flatnonzero(gm)
        ring = g_idx[np.asarray((self.A_hat_csr[ext, :][:, g_idx] < 0.0).sum(axis=0)).ravel() > 0]
        if len(ring) == 0:
            return {"query_ms": 1000.0 * (time.perf_counter() - t0), "neg_frac": 0.0, "Pi_ext_csr": None}
        GV_r = self.GVt_k[:, ring]
        C_sr = np.eye(len(ring), dtype=float) + self.U_k[ring, :] @ GV_r
        alpha = np.linalg.pinv(C_sr) @ np.ones(len(ring), dtype=float)
        z_raw = self.U_k @ (GV_r @ alpha)
        z_raw[ring] += alpha
        neg_frac = float(np.mean(z_raw[ext] <= 0.0))
        z_clipped = np.maximum(z_raw, 1e-12)
        z_clipped[gm] = 1.0
        Pi_csr = _policy_csr_from_kernel_and_z(self.M_hat, z_clipped, gm)
        q_ms = 1000.0 * (time.perf_counter() - t0)
        return {"query_ms": q_ms, "z_raw": z_raw, "neg_frac": neg_frac, "Pi_ext_csr": Pi_csr}


TransitionSVDResolventAblation = LowRankSRLinearRLPlanner


class ScalarBottleneckOptionPlanner:
    """`Scalar_L0_Portal_Ablation`:
    Uses the EXACT SAME discovered separator doorways `Gamma_1..Gamma_P` and PAC channel, but restricts each
    exterior doorway to a SINGLE scalar aggregate (`1` DOF per doorway, piecewise-constant target on `E_Gamma`),
    isolating the irreducible `Omega(1)` entry-dependent doorway aliasing gap against `SPQL`'s Fiedler tree.
    """

    def __init__(self, spql_ref: SPQLPlanner) -> None:
        self.spql = spql_ref
        self.offline_init_ms = 0.0

    def solve_unseen_goal(self, s0: int, goal_mask: np.ndarray, phi_goal: float = 0.0) -> dict:
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        if bool(gm[s0]):
            return {"query_ms": 1000.0 * (time.perf_counter() - t0), "Pi_ext_csr": None}
        ch = self.spql.pes_chan
        ctx = ch.prepare_goal_context(s0, gm)
        # Group exterior portal nodes by portal id `pid` (1 scalar per non-goal portal!)
        ext_mask = ~ctx["g_gam_mask"]
        p_blks: List[np.ndarray] = []
        cols_p: List[np.ndarray] = []
        if not ctx["has_portal_goal"]:
            l0_keys = [(pid, 0, 0) for pid in range(len(self.spql.dec.portal_nodes_loc))]
            p_blks = [self.spql.dec.qt_blocks[ck] for ck in l0_keys]
            cols_p = [ch.get_goal_col(ctx, ck) for ck in l0_keys]
        else:
            cut_ext = ch.build_initial_exterior_cut(ctx)
            by_pid: Dict[int, List[Tuple[int, int, int]]] = {}
            for ck in cut_ext:
                by_pid.setdefault(ck[0], []).append(ck)
            for pid, ck_list in sorted(by_pid.items()):
                p_loc_ext = self.spql.dec.portal_nodes_loc[pid][ext_mask[self.spql.dec.portal_nodes_loc[pid]]]
                if len(p_loc_ext) > 0:
                    p_blks.append(p_loc_ext)
                    cols_p.append(np.sum([ch.get_goal_col(ctx, ck) for ck in ck_list], axis=0))

        Lv_bar = np.ones(ch.n_g, dtype=float)
        if len(p_blks) > 0:
            K0 = np.column_stack(cols_p)
            Sys_bar = np.eye(len(p_blks), dtype=float)
            for j, bl in enumerate(p_blks):
                Sys_bar[j, :] -= np.mean(K0[bl, :], axis=0)
            rhs_bar = np.array([float(np.mean(ctx["r_hat"][bl])) for bl in p_blks], dtype=float)
            v_bar = np.linalg.solve(Sys_bar, rhs_bar)
            Lv_bar[ctx["ext_gam_idx"]] = 0.0
            for j, bl in enumerate(p_blks):
                Lv_bar[bl] = max(float(v_bar[j]), 1e-15)
        z_ext, _ = ch.materialize_full_extension(ctx, Lv_bar)
        Pi_csr = self.spql.build_deployed_policy_csr(z_ext, gm)
        q_ms = 1000.0 * (time.perf_counter() - t0)
        return {"query_ms": q_ms, "Pi_ext_csr": Pi_csr}


ScalarL0PortalAblation = ScalarBottleneckOptionPlanner


class UncompressedSpectralSchurPACPlanner:
    """Pre-Assembled Full-Portal Exact Schur Baseline on Identical `(A_pes, A_opt)` Time-Uniform PAC Envelopes:
    Pre-populates the full `n_Gamma x n_Gamma` singleton room-to-portal responses at offline init and solves
    exact killed-portal equations on `E_Gamma = Gamma - G` per query (stopping `query_ms` AFTER policy
    materialization when `materialize_policy=True`, matching `SPQL` identically!).
    """

    def __init__(
        self,
        dataset: EmpiricalTrajectoryDataset,
        delta: float = 0.05,
        max_rooms: int = 12,
        max_degree_bound: Optional[int] = None,
    ) -> None:
        t0 = time.perf_counter()
        self.lam = float(dataset.lam)
        self.pac_pair = build_pac_mmatrix_pair(dataset, delta=delta, max_degree_bound=max_degree_bound)
        self.dec = discover_spectral_portals_from_trajectories(
            dataset.trans_counts, max_rooms=max_rooms, min_room_size=max(20, dataset.n_states // 35)
        )
        self.pes = _SingleMMatrixPortalChannel(self.pac_pair.A_pes, self.dec, b_source=None, enable_pou_conservation=False)
        self.opt = _SingleMMatrixPortalChannel(self.pac_pair.A_opt, self.dec, b_source=self.pac_pair.b_opt_explore, enable_pou_conservation=False)
        # Clear L0 cache and assemble full singleton operators (`classical pre-assembled Schur`)
        self.pes.node_cache.clear()
        self.opt.node_cache.clear()
        self.pes.local_lu_rhs_solves = 0
        self.opt.local_lu_rhs_solves = int(sum(1 for _ in self.dec.room_nodes if self.opt.has_source))
        self.K_pes_base, self.NegM_pes_base, self.Y_pes_rooms = self._assemble_full_portal_operator(self.pes)
        self.K_opt_base, self.NegM_opt_base, self.Y_opt_rooms = self._assemble_full_portal_operator(self.opt)
        self.init_lu_rhs = int(self.pes.local_lu_rhs_solves + self.opt.local_lu_rhs_solves)
        self.offline_init_ms = 1000.0 * (time.perf_counter() - t0)

    def resident_bytes(self) -> int:
        tot = int(
            self.K_pes_base.nbytes + self.K_opt_base.nbytes
            + self.NegM_pes_base.nbytes + self.NegM_opt_base.nbytes
        )
        for ch, Y_list in ((self.pes, self.Y_pes_rooms), (self.opt, self.Y_opt_rooms)):
            tot += int(
                ch.lu_Agg.L.data.nbytes + ch.lu_Agg.L.indices.nbytes + ch.lu_Agg.L.indptr.nbytes
                + ch.lu_Agg.U.data.nbytes + ch.lu_Agg.U.indices.nbytes + ch.lu_Agg.U.indptr.nbytes
            )
            for lu_c in ch.hq_lus:
                tot += int(
                    lu_c.L.data.nbytes + lu_c.L.indices.nbytes + lu_c.L.indptr.nbytes
                    + lu_c.U.data.nbytes + lu_c.U.indices.nbytes + lu_c.U.indptr.nbytes
                )
            tot += sum(int(Y.nbytes) for Y in Y_list)
        return tot

    def _assemble_full_portal_operator(self, ch: _SingleMMatrixPortalChannel) -> Tuple[np.ndarray, np.ndarray, List[np.ndarray]]:
        n_g = ch.n_g
        NegM = np.zeros((n_g, n_g), dtype=float)
        Y_rooms = []
        for c in range(len(self.dec.room_nodes)):
            tl = self.dec.room_tl[c]
            Yc = ch.hq_lus[c].solve(ch.room_Arg[c].toarray())
            ch.local_lu_rhs_solves += len(tl)
            Y_rooms.append(Yc)
            NegM[np.ix_(tl, tl)] += ch.room_NegAgr[c] @ Yc
        K_full = np.maximum(ch.lu_Agg.solve(NegM), 0.0)
        return K_full, NegM, Y_rooms

    def _solve_channel_singleton(
        self,
        ch: _SingleMMatrixPortalChannel,
        ctx: dict,
        K_base: np.ndarray,
        NegM_base: np.ndarray,
        Y_rooms: List[np.ndarray],
        outward_sign: float,
    ) -> np.ndarray:
        n_g = ch.n_g
        ext_idx = ctx["ext_gam_idx"]
        if len(ext_idx) == 0:
            return np.ones(n_g, dtype=float)
        if (not ctx["has_portal_goal"]) and (not ctx["has_full_goal_room"]):
            K_eff = K_base.copy()
            for c, gr in ctx["goal_rooms"].items():
                tl = self.dec.room_tl[c]
                K_eff[:, tl] = np.maximum(K_eff[:, tl] - gr["Smooth_U"] @ (gr["C_inv"] @ Y_rooms[c][gr["ring_r"], :]), 0.0)
            w = np.linalg.solve(np.eye(n_g, dtype=float) - K_eff, ctx["r_hat"])
            w = np.maximum((K_eff @ w + ctx["r_hat"]) * (1.0 + outward_sign * 1e-12), 0.0)
            return w
        NegM_eff = NegM_base.copy()
        for c in ctx["full_goal_rooms"]:
            tl = self.dec.room_tl[c]
            NegM_eff[np.ix_(tl, tl)] -= ch.room_NegAgr[c] @ Y_rooms[c]
        for c, gr in ctx["goal_rooms"].items():
            tl = self.dec.room_tl[c]
            NegM_eff[np.ix_(tl, tl)] -= gr["NegAgr_U_local"] @ (gr["C_inv"] @ Y_rooms[c][gr["ring_r"], :])
        NegM_ext = NegM_eff[np.ix_(ext_idx, ext_idx)]
        if ctx["has_portal_goal"]:
            K_ext = np.maximum(ctx["lu_Agg_ext"].solve(NegM_ext), 0.0)
        else:
            K_full_g = np.maximum(ch.lu_Agg.solve(NegM_eff), 0.0)
            K_ext = K_full_g[np.ix_(ext_idx, ext_idx)]
        r_ext = ctx["r_hat"][ext_idx]
        w_ext = np.linalg.solve(np.eye(len(ext_idx), dtype=float) - K_ext, r_ext)
        w_ext = np.maximum((K_ext @ w_ext + r_ext) * (1.0 + outward_sign * 1e-12), 0.0)
        w_out = np.ones(n_g, dtype=float)
        w_out[ext_idx] = w_ext
        return w_out

    def solve_unseen_goal(self, s0: int, goal_mask: np.ndarray, phi_goal: float = 0.0, materialize_policy: bool = True) -> dict:
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        phi_f = float(phi_goal)
        if bool(gm[s0]):
            q_ms = 1000.0 * (time.perf_counter() - t0)
            return {
                "query_ms": q_ms, "bounds_only_query_ms": q_ms, "lo": phi_f, "hi": phi_f, "width": 0.0,
                "operational_lu_rhs": 0, "materialization_lu_rhs": 0, "total_query_lu_rhs": 0, "Pi_ext_csr": None,
            }
        rhs0 = self.pes.local_lu_rhs_solves + self.opt.local_lu_rhs_solves
        ctx_p = self.pes.prepare_goal_context(s0, gm)
        ctx_o = self.opt.prepare_goal_context(s0, gm)

        w_pes = self._solve_channel_singleton(self.pes, ctx_p, self.K_pes_base, self.NegM_pes_base, self.Y_pes_rooms, -1.0)
        w_opt = self._solve_channel_singleton(self.opt, ctx_o, self.K_opt_base, self.NegM_opt_base, self.Y_opt_rooms, +1.0)

        zp_s = ctx_p["z_dir"] + float(ctx_p["h_s_tl"] @ w_pes[ctx_p["tl_s"]])
        zo_s = ctx_o["z_dir"] + float(ctx_o["h_s_tl"] @ w_opt[ctx_o["tl_s"]])
        hi_v = (phi_f - self.lam * float(np.log(zp_s))) if zp_s > 0.0 else float("inf")
        lo_v = (phi_f - self.lam * float(np.log(zo_s))) if zo_s > 0.0 else -float("inf")
        op_rhs = (self.pes.local_lu_rhs_solves + self.opt.local_lu_rhs_solves) - rhs0
        b_ms = 1000.0 * (time.perf_counter() - t0)

        Pi_csr = None
        rhs_m0 = self.pes.local_lu_rhs_solves + self.opt.local_lu_rhs_solves
        if materialize_policy and zp_s > 0.0 and np.isfinite(hi_v):
            z_f, _ = self.pes.materialize_full_extension(ctx_p, w_pes)
            Pi_csr = _policy_csr_from_kernel_and_z(self.pac_pair.M_pes, z_f, gm)
        mat_rhs = (self.pes.local_lu_rhs_solves + self.opt.local_lu_rhs_solves) - rhs_m0
        q_ms = 1000.0 * (time.perf_counter() - t0)
        return {
            "query_ms": q_ms,
            "bounds_only_query_ms": b_ms,
            "certified": bool(np.isfinite(lo_v) and np.isfinite(hi_v) and hi_v >= lo_v),
            "lo": lo_v,
            "hi": hi_v,
            "width": hi_v - lo_v,
            "operational_lu_rhs": int(op_rhs),
            "materialization_lu_rhs": int(mat_rhs),
            "total_query_lu_rhs": int(op_rhs + mat_rhs),
            "Pi_ext_csr": Pi_csr,
        }


class MatrixFreeSpectralSchurPACPlanner:
    """Zero-Assembly Matrix-Free Exact Schur Krylov PAC Baseline (`MatrixFree_SpectralSchur_PAC`):
    Shares the EXACT SAME `(A_pes, A_opt)` time-uniform PAC envelopes, spectral rooms, and room `SuperLU`
    factors as `SPQL` (`plus L0 Lyapunov witness`), solving `(I - K_{E_Gamma}) w = r_hat` matrix-free via
    `BiCGSTAB` + cooperative Lyapunov defect closure (zero upfront `n_Gamma`-column Schur assembly!).
    """

    def __init__(
        self,
        dataset: EmpiricalTrajectoryDataset,
        delta: float = 0.05,
        max_rooms: int = 12,
        max_degree_bound: Optional[int] = None,
    ) -> None:
        t0 = time.perf_counter()
        self.lam = float(dataset.lam)
        self.pac_pair = build_pac_mmatrix_pair(dataset, delta=delta, max_degree_bound=max_degree_bound)
        self.dec = discover_spectral_portals_from_trajectories(
            dataset.trans_counts, max_rooms=max_rooms, min_room_size=max(20, dataset.n_states // 35)
        )
        self.pes = _SingleMMatrixPortalChannel(self.pac_pair.A_pes, self.dec, b_source=None, enable_pou_conservation=False)
        self.opt = _SingleMMatrixPortalChannel(self.pac_pair.A_opt, self.dec, b_source=self.pac_pair.b_opt_explore, enable_pou_conservation=False)
        self.init_lu_rhs = int(self.pes.init_lu_rhs_solves + self.opt.init_lu_rhs_solves)
        self.offline_init_ms = 1000.0 * (time.perf_counter() - t0)

    def resident_bytes(self) -> int:
        tot = 0
        for ch in (self.pes, self.opt):
            tot += int(
                ch.lu_Agg.L.data.nbytes + ch.lu_Agg.L.indices.nbytes + ch.lu_Agg.L.indptr.nbytes
                + ch.lu_Agg.U.data.nbytes + ch.lu_Agg.U.indices.nbytes + ch.lu_Agg.U.indptr.nbytes
            )
            for lu_c in ch.hq_lus:
                tot += int(
                    lu_c.L.data.nbytes + lu_c.L.indices.nbytes + lu_c.L.indptr.nbytes
                    + lu_c.U.data.nbytes + lu_c.U.indices.nbytes + lu_c.U.indptr.nbytes
                )
            for k_col, nm_col, y_map in ch.node_cache.values():
                tot += int(k_col.nbytes) + int(nm_col.nbytes) + sum(int(yc.nbytes) for yc in y_map.values())
        return tot

    def _apply_K_ext(self, ch: _SingleMMatrixPortalChannel, ctx: dict, v_ext: np.ndarray) -> np.ndarray:
        ext_idx = ctx["ext_gam_idx"]
        w_full = np.zeros(ch.n_g, dtype=float)
        w_full[ext_idx] = v_ext
        neg_m = np.zeros(ch.n_g, dtype=float)
        for c, rn in enumerate(self.dec.room_nodes):
            if c in ctx["full_goal_rooms"]:
                continue
            tl_c = self.dec.room_tl[c]
            yc = ch.hq_lus[c].solve(ch.room_Arg[c] @ w_full[tl_c])
            ch.local_lu_rhs_solves += 1
            if c in ctx["goal_rooms"]:
                gr = ctx["goal_rooms"][c]
                yc = yc - gr["U_rg"] @ (gr["C_inv"] @ yc[gr["ring_r"]])
            neg_m[tl_c] += ch.room_NegAgr[c] @ yc
        if ctx["has_portal_goal"]:
            return np.maximum(ctx["lu_Agg_ext"].solve(neg_m[ext_idx]), 0.0)
        return np.maximum(ch.lu_Agg.solve(neg_m)[ext_idx], 0.0)

    def _solve_krylov_certified(self, ch: _SingleMMatrixPortalChannel, ctx: dict, mode: str) -> np.ndarray:
        ext_idx = ctx["ext_gam_idx"]
        if len(ext_idx) == 0:
            return np.ones(ch.n_g, dtype=float)
        cut0 = ch.build_initial_exterior_cut(ctx)
        K0, v0, W0, _ = ch.solve_howard_bound(ctx, cut0, mode=mode, certify_lyapunov=True)
        blks0 = [self.dec.qt_blocks[ck] for ck in cut0]
        src_ly = np.maximum(0.5 * W0, 1e-6)
        x_mx = np.array([bl[int(np.argmax(W0[bl]))] for bl in blks0], dtype=np.int64)
        v_ly = np.linalg.solve(np.eye(len(cut0)) - K0[x_mx, :], src_ly[x_mx])
        w_ly = np.zeros(ch.n_g, dtype=float)
        for j, bl in enumerate(blks0):
            w_ly[bl] = float(v_ly[j])
        xi_ext = (w_ly - (K0 @ v_ly))[ext_idx]
        xi_ext = np.maximum(xi_ext, 1e-12)
        w_ly_ext = np.maximum(w_ly[ext_idx], 1e-12)

        r_ext = ctx["r_hat"][ext_idx]
        n_e = len(ext_idx)
        lin_op = spla.LinearOperator(
            (n_e, n_e),
            matvec=lambda u: u - self._apply_K_ext(ch, ctx, u * w_ly_ext) / w_ly_ext,
            dtype=float,
        )
        u_init = W0[ext_idx] / w_ly_ext
        u_sol, _ = spla.bicgstab(lin_op, r_ext / w_ly_ext, x0=u_init, rtol=1e-7, atol=0.0, maxiter=35)
        z_tilde = np.maximum(u_sol * w_ly_ext, 0.0)
        Kz = self._apply_K_ext(ch, ctx, z_tilde)
        defect = (Kz + r_ext) - z_tilde
        w_out = np.ones(ch.n_g, dtype=float)
        if mode == "lo":
            eta = float(np.max(np.maximum(-defect, 0.0) / xi_ext)) * (1.0 + 1e-9)
            u_base = np.maximum(W0[ext_idx], z_tilde - eta * w_ly_ext)
            w_out[ext_idx] = np.maximum((self._apply_K_ext(ch, ctx, u_base) + r_ext) * (1.0 - 1e-12), 0.0)
        else:
            eta = float(np.max(np.maximum(defect, 0.0) / xi_ext)) * (1.0 + 1e-9)
            u_base = np.minimum(W0[ext_idx], z_tilde + eta * w_ly_ext)
            w_out[ext_idx] = np.maximum((self._apply_K_ext(ch, ctx, u_base) + r_ext) * (1.0 + 1e-12), 0.0)
        return w_out

    def solve_unseen_goal(self, s0: int, goal_mask: np.ndarray, phi_goal: float = 0.0, materialize_policy: bool = True) -> dict:
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        phi_f = float(phi_goal)
        if bool(gm[s0]):
            q_ms = 1000.0 * (time.perf_counter() - t0)
            return {
                "query_ms": q_ms, "bounds_only_query_ms": q_ms, "certified": True, "lo": phi_f, "hi": phi_f,
                "width": 0.0, "operational_lu_rhs": 0, "materialization_lu_rhs": 0, "total_query_lu_rhs": 0, "Pi_ext_csr": None,
            }
        rhs0 = self.pes.local_lu_rhs_solves + self.opt.local_lu_rhs_solves
        ctx_p = self.pes.prepare_goal_context(s0, gm)
        ctx_o = self.opt.prepare_goal_context(s0, gm)
        w_pes = self._solve_krylov_certified(self.pes, ctx_p, mode="lo")
        w_opt = self._solve_krylov_certified(self.opt, ctx_o, mode="hi")
        zp_s = ctx_p["z_dir"] + float(ctx_p["h_s_tl"] @ w_pes[ctx_p["tl_s"]])
        zo_s = ctx_o["z_dir"] + float(ctx_o["h_s_tl"] @ w_opt[ctx_o["tl_s"]])
        hi_v = (phi_f - self.lam * float(np.log(zp_s))) if zp_s > 0.0 else float("inf")
        lo_v = (phi_f - self.lam * float(np.log(zo_s))) if zo_s > 0.0 else -float("inf")
        op_rhs = (self.pes.local_lu_rhs_solves + self.opt.local_lu_rhs_solves) - rhs0
        b_ms = 1000.0 * (time.perf_counter() - t0)

        Pi_csr = None
        rhs_m0 = self.pes.local_lu_rhs_solves + self.opt.local_lu_rhs_solves
        if materialize_policy and zp_s > 0.0 and np.isfinite(hi_v):
            z_f, _ = self.pes.materialize_full_extension(ctx_p, w_pes)
            Pi_csr = _policy_csr_from_kernel_and_z(self.pac_pair.M_pes, z_f, gm)
        mat_rhs = (self.pes.local_lu_rhs_solves + self.opt.local_lu_rhs_solves) - rhs_m0
        q_ms = 1000.0 * (time.perf_counter() - t0)
        return {
            "query_ms": q_ms,
            "bounds_only_query_ms": b_ms,
            "certified": bool(np.isfinite(lo_v) and np.isfinite(hi_v) and hi_v >= lo_v),
            "lo": lo_v,
            "hi": hi_v,
            "width": hi_v - lo_v,
            "operational_lu_rhs": int(op_rhs),
            "materialization_lu_rhs": int(mat_rhs),
            "total_query_lu_rhs": int(op_rhs + mat_rhs),
            "Pi_ext_csr": Pi_csr,
        }


class ModelFreeGoalSoftQPlanner:
    """`Sampled_Desirability_TD`:
    Offline sampled desirability Bellman updates with **exact per-minibatch state-grouped averaging**
    (`Closes P3-E04`: `np.bincount` averages all sampled targets per unique state in each mini-batch
    instead of letting duplicate indices overwrite earlier updates!).
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

    @staticmethod
    def group_mean_batch_td_step(z: np.ndarray, s_b: np.ndarray, targets: np.ndarray, alpha: float) -> None:
        """In-place duplicate-safe group-mean TD update: `z[s] <- (1 - alpha) z[s] + alpha * mean_{k: s_k = s} targets[k]`."""
        cnt_b = np.bincount(s_b, minlength=len(z))
        upd_m = cnt_b > 0
        if np.any(upd_m):
            sum_b = np.bincount(s_b, weights=targets, minlength=len(z))
            z[upd_m] = (1.0 - alpha) * z[upd_m] + alpha * (sum_b[upd_m] / cnt_b[upd_m])

    def solve_unseen_goal(self, s0: int, goal_mask: np.ndarray, phi_goal: float = 0.0) -> dict:
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        if bool(gm[s0]):
            return {"query_ms": 1000.0 * (time.perf_counter() - t0), "Pi_ext_csr": None}
        z = np.zeros(self.n_states, dtype=float)
        z[gm] = 1.0
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
                self.group_mean_batch_td_step(z, s_b, td_target, alpha)
                z[gm] = 1.0
        Pi_csr = _policy_csr_from_kernel_and_z(self.M_hat, np.maximum(z, 1e-30), gm)
        q_ms = 1000.0 * (time.perf_counter() - t0)
        return {"query_ms": q_ms, "Pi_ext_csr": Pi_csr}


SampledDesirabilityTDPlanner = ModelFreeGoalSoftQPlanner


# ==============================================================================
# 2. Axis-Aligned Slice Detector Control (Proving 100% Failure on Rotated Worlds)
# ==============================================================================
def axis_aligned_bottleneck_detector_2d(coords: np.ndarray, n_bins: int = 40) -> Tuple[List[float], List[float]]:
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
# 3. 16-Gate Deterministic & Counterexample Verification Suite (`P3-C01..16`)
# ==============================================================================
def run_phase3_16_contract_gates() -> dict:
    t0 = time.perf_counter()
    freeze_info = verify_phase1_and_phase2_untouched()
    v1_freeze_info = verify_phase3_v1_archive_untouched()

    env_rot = build_rotated_multiroom_2d_env(seed=101, grid_n=40, angle_deg=37.0, door_half_width=0.105, add_baffles=True)
    ds_mid = collect_exploration_trajectories(env_rot, total_steps=60000, episode_len=70, seed=202)
    spql = SPQLPlanner(ds_mid, delta=0.05, eps_tol=0.15, max_degree_bound=8, enable_pou_conservation=True, enable_epistemic_stopping=False)

    # Gate 1 (`P3-C01`): Clopper-Pearson strict positivity on observed moderate-count edges + ZERO 1e-15 upward floor
    T_coo = ds_mid.trans_counts.tocoo()
    obs_mask = T_coo.data >= 1.0
    M_pes_obs = np.asarray(spql.pac_pair.M_pes[T_coo.row[obs_mask], T_coo.col[obs_mask]]).ravel()
    # Test ultra-rare p^* = 1e-16 edge observed once in m = 10^8 steps: no artificial 1e-15 floor violates p^*!
    ds_rare_floor = EmpiricalTrajectoryDataset(
        n_states=2, total_steps=10**8, visit_counts=np.array([10**8, 1], dtype=np.int64),
        trans_counts=sp.csr_matrix([[10**8 - 1, 1], [1, 0]], dtype=float),
        cost_sums=np.array([10**7, 0.1], dtype=float), q_min=0.1, q_max=0.1, lam=1.0,
    )
    pa_rf = build_pac_mmatrix_pair(ds_rare_floor, delta=0.05, max_degree_bound=2)
    p_lo_rare = float(pa_rf.M_pes[0, 1]) / math.exp(-0.1)
    c01_pass = bool(
        len(M_pes_obs) > 0 and np.all(M_pes_obs > 0.0) and np.all(spql.pac_pair.rho_epistemic >= 0.0)
        and (0.0 <= p_lo_rare < 1e-15)
    )

    # Gate 2 (`P3-C02`): Hidden Unobserved Wormhole Counterexample (`p^* = 0.025` secret cross-building shortcut with `0` observations!)
    P_worm = env_rot.P_true.tolil(copy=True)
    tasks_test = sample_unseen_goal_tasks(env_rot, n_tasks=6, seed=303)
    s_w, gm_w = tasks_test[0]
    g_first = int(np.flatnonzero(gm_w)[0])
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
        name="WormholeStressEnv", n_states=env_rot.n_states, P_true=P_worm.tocsr(),
        q_true=env_rot.q_true, q_min=env_rot.q_min, q_max=env_rot.q_max, lam=env_rot.lam, cost_noise_std=env_rot.cost_noise_std,
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

    # Gate 3 (`P3-C03`): Strictly Binary Fiedler Tree & Universal Exact `50.0%` Child-Column PoU Conservation (`Closes P3-E06`)
    spql_pou = SPQLPlanner(ds_mid, delta=0.05, max_degree_bound=8, enable_pou_conservation=True)
    spql_dir = SPQLPlanner(ds_mid, delta=0.05, max_degree_bound=8, enable_pou_conservation=False)
    all_pkeys = [pk for pk, chs in spql_pou.dec.qt_children.items() if chs]
    max_ch_rot = max(len(spql_pou.dec.qt_children[pk]) for pk in all_pkeys)
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
    # Exact reproduction of GPT6's 64-node path portal probe (`r333_tree_and_coverage_probe.py`)
    n64 = 64
    w64 = sp.diags([np.ones(n64 - 1), np.ones(n64 - 1)], [-1, 1], shape=(n64, n64), format="csr")
    bl64, ch64 = _recursive_fiedler_portal_tree(np.arange(n64), w64)
    ks64 = [len(v) for v in ch64.values() if v]
    saved_frac_64 = float(len(ks64)) / float(sum(ks64))
    leaf_singletons_64 = sum(1 for k, v in ch64.items() if len(v) == 0 and len(bl64[k]) == 1)
    c03_pass = bool(
        max_ch_rot == 2
        and pou_solves * 2 == dir_solves
        and max_pou_diff < 1e-13
        and max(ks64) == 2
        and abs(saved_frac_64 - 0.5) < 1e-15
        and leaf_singletons_64 == 64
    )

    # Gate 4 (`P3-C04`): Rotated 37-deg Building Invariance
    xc_aa, yc_aa = axis_aligned_bottleneck_detector_2d(env_rot.coords)
    T_sym = ((ds_mid.trans_counts + ds_mid.trans_counts.T) > 0).tocsr()
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

    # Gate 5 (`P3-C05`): Irreducible Doorway Aliasing Gap of `Scalar_L0_Portal_Ablation`
    env_baf = build_rotated_multiroom_2d_env(seed=77, grid_n=36, angle_deg=37.0, n_rooms_per_side=2, door_half_width=0.22, add_baffles=True)
    ds_dense = collect_exploration_trajectories(env_baf, total_steps=120000, episode_len=60, seed=88)
    spql_baf = SPQLPlanner(ds_dense, delta=0.05, eps_tol=0.02, max_degree_bound=8, enable_epistemic_stopping=False, max_rooms=4)
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

    # Gate 6 (`P3-C06`): Orthogonal `TransitionSVD_Resolvent_Ablation` Sign Violation (`> 15%` negative entries)
    sr_pl = LowRankSRLinearRLPlanner(ds_mid, rank_k=24)
    sr_res = sr_pl.solve_unseen_goal(s_w, gm_w)
    c06_pass = bool(sr_res["neg_frac"] > 0.15)

    # Gate 7 (`P3-C07`): Finite-Sample `PlugIn_CE` Over-Optimism Trap (`pred_val < J^{mu_CE}`) vs. `0` SPQL Violations
    ds_low = collect_exploration_trajectories(env_rot, total_steps=14000, episode_len=50, seed=404)
    ce_low = PlugInCEFullGraphPlanner(ds_low)
    spql_low = SPQLPlanner(ds_low, delta=0.05, eps_tol=0.25, max_degree_bound=8)
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

    # Gate 8 (`P3-C08`): Monotone Nested Fiedler-Tree Bound Tightening Across All Binary Levels `L0 .. L_max`
    s_b0, gm_b0 = tasks_baf[0]
    _, vt_0 = env_baf.true_desirability_and_value(gm_b0)
    max_lv_baf = max(pk[1] for pk in spql_baf.dec.qt_blocks.keys())
    lo_seq, hi_seq = [], []
    for lv_unif in range(max_lv_baf + 1):
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
        _, _, Wp_lo, ok_p = spql_baf.pes_chan.solve_howard_bound(ctx_p0, cut_lv, mode="lo", certify_lyapunov=True)
        _, _, Wo_hi, ok_o = spql_baf.opt_chan.solve_howard_bound(ctx_o0, cut_lv, mode="hi", certify_lyapunov=True)
        assert ok_p and ok_o
        zp_v = ctx_p0["z_dir"] + float(ctx_p0["h_s_tl"] @ Wp_lo[ctx_p0["tl_s"]])
        zo_v = ctx_o0["z_dir"] + float(ctx_o0["h_s_tl"] @ Wo_hi[ctx_o0["tl_s"]])
        lo_seq.append(-spql_baf.lam * float(np.log(zo_v)))
        hi_seq.append(-spql_baf.lam * float(np.log(zp_v)))
    monotone_lo = all(lo_seq[i] <= lo_seq[i + 1] + 1e-9 for i in range(len(lo_seq) - 1))
    monotone_hi = all(hi_seq[i + 1] <= hi_seq[i] + 1e-9 for i in range(len(hi_seq) - 1))
    c08_pass = bool(monotone_lo and monotone_hi and lo_seq[-1] <= float(vt_0[s_b0]) <= hi_seq[-1])

    # Gate 9 (`P3-C09`): Relative Coarse-Refinement Stopping Efficiency
    spql_ep_on = SPQLPlanner(ds_mid, delta=0.05, eps_tol=0.01, max_degree_bound=8, epistemic_stop_ratio=0.18, enable_epistemic_stopping=True)
    spql_ep_off = SPQLPlanner(ds_mid, delta=0.05, eps_tol=0.01, max_degree_bound=8, enable_epistemic_stopping=False)
    r_on = spql_ep_on.solve_unseen_goal(s_w, gm_w, max_rounds=8, materialize_policy=False)
    r_off = spql_ep_off.solve_unseen_goal(s_w, gm_w, max_rounds=8, materialize_policy=False)
    c09_pass = bool(r_on["active_dofs"] < r_off["active_dofs"] and (r_on["width"] - r_off["width"]) <= 0.20 * r_off["width"])

    # Gate 10 (`P3-C10`): Phase-I, Phase-II, & Exploratory Phase-III v1 Archive Freeze Verification
    c10_pass = bool(
        len(freeze_info["phase1_py_sha256"]) == 64
        and len(freeze_info["phase2_py_sha256"]) == 64
        and bool(v1_freeze_info["verified_untouched"])
    )

    # Gate 11 (`P3-C11`, `Closes P3-P0-01a`): Exhaustive 4-State All-15-Subset Goal Proof (`incl. r333_small_portal_goal.py`)
    P4 = sp.csr_matrix([[0, 1, 0, 0], [0.5, 0, 0.5, 0], [0, 0.5, 0, 0.5], [0, 0, 1, 0]], dtype=float)
    gam4 = math.exp(-0.5)
    A4 = (sp.eye(4, format="csr") - gam4 * P4).tocsr()
    D4 = SpectralPortalDecomposition(
        4, np.array([1, 2]), [np.array([0]), np.array([3])], np.array([0, -1, -1, 1]),
        [np.array([0]), np.array([1])], [[0], [1]], [[0], [1]], [np.array([0]), np.array([1])],
        [np.array([0, -1]), np.array([-1, 0])], {(0, 0, 0): np.array([0]), (1, 0, 0): np.array([1])},
        {(0, 0, 0): [], (1, 0, 0): []}, 0.0, 0.0,
    )
    ch4 = _SingleMMatrixPortalChannel(A4, D4)
    max_err_4 = 0.0
    max_res_4 = -np.inf
    pairs_checked_4 = 0
    for bits in itertools.product((False, True), repeat=4):
        if not any(bits):
            continue
        gm4 = np.array(bits, dtype=bool)
        ext4 = np.flatnonzero(~gm4)
        if len(ext4) == 0:
            continue
        z4_exact = np.ones(4, dtype=float)
        z4_exact[ext4] = spla.spsolve(A4[ext4, :][:, ext4].tocsc(), -np.asarray(A4[ext4, :][:, gm4].sum(axis=1)).ravel())
        for s4 in ext4:
            ctx4 = ch4.prepare_goal_context(int(s4), gm4)
            cut4 = ch4.build_initial_exterior_cut(ctx4)
            _, _, W4_lo, ok4_lo = ch4.solve_howard_bound(ctx4, cut4, mode="lo", certify_lyapunov=True)
            _, _, W4_hi, ok4_hi = ch4.solve_howard_bound(ctx4, cut4, mode="hi", certify_lyapunov=True)
            z4_lo, _ = ch4.materialize_full_extension(ctx4, W4_lo)
            z4_hi, _ = ch4.materialize_full_extension(ctx4, W4_hi)
            res4 = float(np.max((A4 @ z4_lo)[ext4]))
            max_res_4 = max(max_res_4, res4)
            # Singleton portals -> W4_lo and W4_hi match z4_exact up to 1e-12 Lyapunov safety factor!
            err4 = float(np.max(np.abs(0.5 * (z4_lo + z4_hi) - z4_exact)))
            max_err_4 = max(max_err_4, err4)
            assert ok4_lo and ok4_hi and np.all(z4_lo <= z4_exact + 1e-13) and np.all(z4_exact <= z4_hi + 1e-13)
            pairs_checked_4 += 1
    c11_pass = bool(pairs_checked_4 == 28 and max_err_4 < 1e-11 and max_res_4 <= 1e-12)

    # Gate 12 (`P3-C12`, `Closes P3-P0-01b`): Exact Reproduction of 392-State Portal-Goal Counterexample + 12 Unrestricted Goals
    orig_28 = build_rotated_multiroom_2d_env(seed=101, grid_n=28, n_rooms_per_side=2, door_half_width=0.18, add_baffles=True)
    N28 = orig_28.n_states
    rng28 = np.random.default_rng(777)
    T28 = orig_28.P_true.copy()
    m28 = 10**7
    for i in range(N28):
        sl = slice(T28.indptr[i], T28.indptr[i + 1])
        T28.data[sl] = rng28.multinomial(m28, T28.data[sl])
    T28.eliminate_zeros()
    P28 = T28 / float(m28)
    q28 = np.ones(N28, dtype=float) * 0.1
    lam28 = 0.5
    ds28 = EmpiricalTrajectoryDataset(N28, N28 * m28, np.full(N28, m28, dtype=np.int64), T28, q28 * m28, 0.1, 0.1, lam28)
    pl28 = SPQLPlanner(ds28, eps_tol=0.001, max_degree_bound=8, enable_epistemic_stopping=False, max_rooms=8)

    def _indep_eval_28(s_q: int, gm_q: np.ndarray, rr_q: dict) -> Tuple[bool, float, float, float]:
        ext_q = np.flatnonzero(~gm_q)
        ex_i = int(np.searchsorted(ext_q, s_q))
        M28 = sp.diags(np.exp(-q28 / lam28)) @ P28
        B_sys = sp.eye(len(ext_q), format="csc") - M28[ext_q, :][:, ext_q].tocsc()
        b_rhs = np.asarray(M28[ext_q, :][:, gm_q].sum(axis=1)).ravel()
        z_ex = spla.spsolve(B_sys, b_rhs)
        v_ex = float(-lam28 * np.log(z_ex[ex_i]))
        Pi_q = rr_q["Pi_ext_csr"]
        coo_q = Pi_q.tocoo()
        pvals_q = np.asarray(P28[ext_q[coo_q.row], coo_q.col]).ravel()
        kl_q = np.bincount(coo_q.row, weights=coo_q.data * np.log(coo_q.data / pvals_q), minlength=len(ext_q))
        c_q = q28[ext_q] + lam28 * kl_q
        Bp_q = sp.eye(len(ext_q), format="csc") - Pi_q[:, ext_q].tocsc()
        jp_q = spla.spsolve(Bp_q, c_q)
        J_ex = float(jp_q[ex_i])
        pes_res_max = float(np.max(np.asarray(pl28.pac_pair.A_pes @ rr_q["z_sub_full"]).ravel()[ext_q]))
        ok_4 = bool(rr_q["certified"] and (rr_q["lo"] <= v_ex <= J_ex <= rr_q["hi"]) and (pes_res_max <= 1e-10))
        return ok_4, v_ex, J_ex, pes_res_max

    gm_236 = np.zeros(N28, dtype=bool)
    gm_236[236] = True
    rr_236 = pl28.solve_unseen_goal(344, gm_236, max_rounds=12, m_cap=512)
    ok_236, v_236, J_236, res_236 = _indep_eval_28(344, gm_236, rr_236)

    # Also test 12 unrestricted portal-straddling & multi-room goals on `pl28`
    all_unrest_ok = ok_236
    for idx_u in range(12):
        gm_u = np.zeros(N28, dtype=bool)
        # Include 2 portal nodes + 3 interior nodes
        p_pick = pl28.dec.gamma_nodes[(idx_u * 3) % len(pl28.dec.gamma_nodes)]
        p_pick2 = pl28.dec.gamma_nodes[(idx_u * 3 + 1) % len(pl28.dec.gamma_nodes)]
        gm_u[[int(p_pick), int(p_pick2), int((idx_u * 29) % N28)]] = True
        s_u = int((344 + idx_u * 17) % N28)
        if gm_u[s_u]:
            s_u = int(np.flatnonzero(~gm_u)[0])
        rr_u = pl28.solve_unseen_goal(s_u, gm_u, max_rounds=10, m_cap=512)
        ok_u, _, _, _ = _indep_eval_28(s_u, gm_u, rr_u)
        all_unrest_ok = all_unrest_ok and ok_u
    c12_pass = bool(all_unrest_ok and bool(236 in pl28.dec.gamma_nodes))

    # Gate 13 (`P3-C13`, `Closes P3-P0-02`): Exact 2-Look & 29-Look Optional-Stopping Coverage + Degree Guard
    alpha_0 = 0.00625
    p_bern = 0.5
    n1, n2 = 100, 1000
    a1 = alpha_0 / (n1 * (n1 + 1.0))
    a2 = alpha_0 / (n2 * (n2 + 1.0))
    k1_crit = int(sp_binom.isf(a1, n1, p_bern)) + 1
    k2_crit = int(sp_binom.isf(a2, n2, p_bern)) + 1
    first_fail = float(sp_binom.sf(k1_crit - 1, n1, p_bern))
    second_fail = sum(
        float(sp_binom.pmf(k, n1, p_bern) * sp_binom.sf(k2_crit - k - 1, n2 - n1, p_bern))
        for k in range(k1_crit)
    )
    two_look_union_prob = first_fail + second_fail
    # 29-look dyadic schedule MC (`20,000` replicates) under repaired `alpha_0 / (n * (n + 1))`
    rng_mc = np.random.default_rng(316218)
    reps_mc = 20000
    cnts_mc = np.zeros(reps_mc, dtype=np.int64)
    crossed_mc = np.zeros(reps_mc, dtype=bool)
    prev_n = 0
    for n_lk in [100 * (2**k) for k in range(29)]:
        cnts_mc += rng_mc.binomial(n_lk - prev_n, p_bern, size=reps_mc)
        a_lk = alpha_0 / (float(n_lk) * (float(n_lk) + 1.0))
        crit_lk = int(sp_binom.isf(a_lk, n_lk, p_bern)) + 1
        crossed_mc |= cnts_mc >= crit_lk
        prev_n = n_lk
    mc_cross_rate = float(np.mean(crossed_mc))
    # Also verify invalid `max_degree_bound=1` raises ValueError when observed degree is 2
    deg_guard_rejected = False
    try:
        _ = build_pac_mmatrix_pair(ds_rare_floor, delta=0.05, max_degree_bound=1)
    except ValueError:
        deg_guard_rejected = True
    c13_pass = bool(two_look_union_prob <= alpha_0 and mc_cross_rate <= alpha_0 and deg_guard_rejected)

    # Gate 14 (`P3-C14`, `Closes P3-P0-03`): Exact Boundary-Unbiased Cost Noise (`q_true = q_min = 0.1`)
    env_bnd = UnknownDiscreteKLEnv(
        "boundary-cost-test", 2, sp.csr_matrix([[0, 1], [1, 0]], dtype=float),
        np.ones(2, dtype=float) * 0.1, 0.1, 1.1, 1.0, 0.1,
    )
    ds_bnd = collect_exploration_trajectories(
        env_bnd, 40000, episode_len=40000, entry_states=np.array([0]), ambient_reset_prob=0.0, seed=1029
    )
    pa_bnd = build_pac_mmatrix_pair(ds_bnd, delta=0.05, max_degree_bound=1)
    z_opt_bnd = (float(pa_bnd.M_opt[0, 1]) + float(pa_bnd.b_opt_explore[0])) / (1.0 - float(pa_bnd.M_opt[0, 0]))
    z_pes_bnd = float(pa_bnd.M_pes[0, 1]) / (1.0 - float(pa_bnd.M_pes[0, 0]))
    lo_bnd = -math.log(z_opt_bnd * (1.0 + 1e-12))
    hi_bnd = -math.log(z_pes_bnd * (1.0 - 1e-12))
    c14_pass = bool(np.all(pa_bnd.q_lo <= env_bnd.q_true) and np.all(env_bnd.q_true <= pa_bnd.q_hi) and (lo_bnd <= 0.1 <= hi_bnd))

    # Gate 15 (`P3-C15`, `Closes P3-E01 & P3-E04`): Deterministic Zero Continuous Wall Tunneling + Group-Mean Batch TD
    from learned_portal_phase3.continuous_manifold_spql import RotatedContinuousDiffusionWorld

    class _ZeroRNG:
        def normal(self, *args, **kwargs):
            return np.zeros(kwargs["size"], dtype=float)

    w_det = RotatedContinuousDiffusionWorld(seed=3000)
    pt_a = np.array([[-0.045, 0.15]]) @ w_det.R
    pt_b = np.array([[0.045, 0.15]]) @ w_det.R
    u_det = (pt_b - pt_a) / w_det.dt - w_det.drift(pt_a)
    pt_step, _ = w_det.step_batch(pt_a, u_det, _ZeroRNG())
    tunnel_blocked = bool(w_det.segment_has_collision(pt_a, pt_step, n_checks=25)[0])

    # Random batch stress test: 500 aggressive controls toward walls -> 0 blocked segments!
    rng_w = np.random.default_rng(909)
    pts_w = w_det.sample_free_points(500, seed=910)
    U_w = rng_w.uniform(-w_det.u_clip, w_det.u_clip, size=pts_w.shape)
    pts_w_nxt, _ = w_det.step_batch(pts_w, U_w, rng_w)
    batch_blocked = int(np.sum(w_det.segment_has_collision(pts_w, pts_w_nxt, n_checks=25)))

    z_td_test = np.zeros(1, dtype=float)
    ModelFreeGoalSoftQPlanner.group_mean_batch_td_step(
        z_td_test, np.array([0, 0], dtype=np.int64), np.array([1.0, 2.0], dtype=float), alpha=0.35
    )
    c15_pass = bool((not tunnel_blocked) and (batch_blocked == 0) and abs(float(z_td_test[0]) - 0.525) < 1e-15)

    # Gate 16 (`P3-C16`, `Closes P3-E05 & P3-E07`): Tiny-Probability Proper Policy Support + Fail-Closed Residual Guard
    env_tiny = UnknownDiscreteKLEnv(
        "tiny-prob-proper", 3,
        sp.csr_matrix([[1.0 - 1e-12, 1e-12, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, 1.0]], dtype=float),
        np.array([0.1, 0.1, 0.1]), 0.1, 0.1, 1.0, 0.0,
    )
    # Policy at state 0 puts 1e-12 (< 1e-11 old threshold!) on 0->1 and 1 - 1e-12 on self-loop 0->0 -> proper!
    Pi_tiny = sp.csr_matrix([[1.0 - 1e-12, 1e-12, 0.0], [0.0, 0.0, 1.0]], dtype=float)
    j_tiny = env_tiny.evaluate_deployed_policy_true_cost(Pi_tiny, np.array([False, False, True]), 0.0, 0)
    # Also verify full-policy query_ms >= bounds_only_query_ms
    c16_pass = bool(np.isfinite(j_tiny) and j_tiny > 1e10 and (res_worm["query_ms"] >= res_worm["bounds_only_query_ms"]))

    all_16 = all([
        c01_pass, c02_pass, c03_pass, c04_pass, c05_pass, c06_pass, c07_pass, c08_pass,
        c09_pass, c10_pass, c11_pass, c12_pass, c13_pass, c14_pass, c15_pass, c16_pass,
    ])
    return {
        "ALL_16_PHASE3_CONTRACT_GATES_PASSED": all_16,
        "ALL_10_PHASE3_CONTRACT_GATES_PASSED": all_16,
        "elapsed_ms": 1000.0 * (time.perf_counter() - t0),
        "gates": {
            "P3_C01_clopper_pearson_positivity_and_zero_floor": {
                "pass": c01_pass, "min_observed_M_pes": float(np.min(M_pes_obs)), "rare_edge_p_lo": p_lo_rare,
            },
            "P3_C02_unobserved_wormhole_soundness": {
                "pass": c02_pass, "lo": res_worm["lo"], "true_wormhole_V": float(v_worm_true[s_w]),
                "deployed_policy_J": j_worm_pol, "hi": res_worm["hi"],
            },
            "P3_C03_strict_binary_fiedler_50pct_pou_conservation": {
                "pass": c03_pass, "max_children_rotated2d": max_ch_rot, "pou_rhs_solves": int(pou_solves),
                "direct_rhs_solves": int(dir_solves), "rhs_saving_pct": 100.0 * (1.0 - float(pou_solves) / float(dir_solves)),
                "path64_max_children": max(ks64), "path64_saved_fraction": saved_frac_64, "max_abs_K_diff": max_pou_diff,
            },
            "P3_C04_rotated_37deg_separator_invariance": {
                "pass": c04_pass, "axis_aligned_max_unseparated_frac": aa_max_comp_frac,
                "spectral_max_room_frac": spec_max_room_frac, "spectral_rooms_discovered": len(spql.dec.room_nodes),
                "cross_room_edge_leaks": cross_room_leaks,
            },
            "P3_C05_scalar_portal_ablation_irreducible_gap": {
                "pass": c05_pass, "spql_mean_regret": float(np.mean(reg_spql_list)),
                "scalar_ablation_mean_regret": float(np.mean(reg_scal_list)),
            },
            "P3_C06_transition_svd_resolvent_negativity": {"pass": c06_pass, "negative_entry_fraction": sr_res["neg_frac"]},
            "P3_C07_plugin_ce_optimism_trap": {
                "pass": c07_pass, "plugin_ce_overoptimism_violations_of_6": ce_overopt_viols, "spql_pac_violations_of_6": spql_pac_viols,
            },
            "P3_C08_monotone_fiedler_tree_tightening": {
                "pass": c08_pass, "levels_checked": len(lo_seq), "lo_L0_to_Lmax": lo_seq, "true_V": float(vt_0[s_b0]), "hi_L0_to_Lmax": hi_seq,
            },
            "P3_C09_relative_coarse_stopping": {
                "pass": c09_pass, "stop_dofs": r_on["active_dofs"], "full_dofs": r_off["active_dofs"],
                "stop_width": r_on["width"], "full_width": r_off["width"],
            },
            "P3_C10_phase1_phase2_and_v1_archive_freeze": {"pass": c10_pass, **freeze_info, "p3_v1_archive": v1_freeze_info},
            "P3_C11_exhaustive_4state_all_15_goal_subsets": {
                "pass": c11_pass, "pairs_checked": pairs_checked_4, "max_midpoint_abs_err": max_err_4, "max_subsolution_res": max_res_4,
            },
            "P3_C12_392state_portal_goal_exact_certificate": {
                "pass": c12_pass, "goal_236_is_portal": bool(236 in pl28.dec.gamma_nodes),
                "lo_236": rr_236["lo"], "V_236": v_236, "J_236": J_236, "hi_236": rr_236["hi"], "max_pes_res_236": res_236,
            },
            "P3_C13_predictable_optional_stopping_confidence": {
                "pass": c13_pass, "nominal_alpha": alpha_0, "two_look_exact_crossing_prob": two_look_union_prob,
                "dyadic_29look_mc_crossing_prob": mc_cross_rate, "degree_guard_rejected": deg_guard_rejected,
            },
            "P3_C14_boundary_unbiased_bounded_cost_noise": {
                "pass": c14_pass, "lo": lo_bnd, "true_V": 0.1, "hi": hi_bnd, "q_lo": pa_bnd.q_lo.tolist(), "q_hi": pa_bnd.q_hi.tolist(),
            },
            "P3_C15_zero_continuous_wall_tunneling_and_group_td": {
                "pass": c15_pass, "deterministic_tunneling_blocked": tunnel_blocked, "random_500_blocked_segments": batch_blocked,
                "duplicate_state_group_td_value": float(z_td_test[0]),
            },
            "P3_C16_tiny_prob_proper_support_and_full_timing": {
                "pass": c16_pass, "tiny_prob_1e12_exact_cost": j_tiny,
                "bounds_only_ms": res_worm["bounds_only_query_ms"], "full_policy_ms": res_worm["query_ms"],
            },
        },
    }


run_phase3_10_contract_gates = run_phase3_16_contract_gates
