"""Milestone M2.3.1 Parts B, C, & D (`quotient_phase2.m231_fair_ablation`):
Adjacent-Baseline Attribution, Cyclic Position-Balanced Execution Schedule, Executable Policy
Delivery Accounting, and Cache Invalidation Ablation.

Scientific Design & Guarantee Tiers (Updated in `M2.3.2` for `B6-01..B6-05` Closure):
  1. Preserves all historical JSON artifacts (`m20`, `m21`, `m22`, `m23_m24`, and `b6ff40d`'s
     `m231_fair_ablation_results.json`) 100% byte-untouched.
  2. Separates Guarantee Tiers Explicitly (`B6-03`):
       - `M231_Portal_*` & `MatrixFree_ExactSchur_Krylov`: `float64_toleranced_model_enclosure`
         (`epsilon_tol = 0.25` discrete KL-LMDP sub-/supersolution verified at runtime in IEEE-754 float64);
       - `SingleLU_GoalCapacitance`: `high_accuracy_numerical_reference` (direct global sparse LU +
         Woodbury capacitance verified via both global and componentwise relative residuals, without
         masquerading a fixed numerical pad as an outward-rounded interval enclosure);
       - `Verified_Global_WarmILU`: `uniform_mmatrix_enclosure` when self-certified by global residual,
         otherwise `fallback_to_high_accuracy_numerical_reference` (`with internal Krylov stage diagnostic
         recorded strictly as krylov_stage_diagnostic_inside_verified_pipeline_ms`, `B6-04`).
  3. Cache Ablation Arms Keep Intra-Query Memoization Enabled (`use_portal_cache=True`, `B6-02`),
     differing strictly at query boundaries (`CacheOn` vs `StructureOnly/L0Only` vs `CacheOff/QueryCold`).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse
import gc
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from green_response import ProblemSpec, collect_runtime_metadata, enforce_single_thread_env, paired_stats
from quotient_phase2 import compute_phase2_manifest, verify_phase1_readonly_freeze
from quotient_phase2.m20_contracts import Phase2DecisionCertificate, check_directed_goal_reachability
from quotient_phase2.m23_m24_3d_portal_scale import (
    LazyRoomPortalPolicy,
    SeamFreePortal3DPlanner,
    build_3d_reflecting_obstacle_mmatrix,
    evaluate_3d_deployed_policy_exact,
    extract_directed_goal_ring_in_room,
    generate_3d_multiroom_world,
    solve_and_verify_portal_howard_bounds,
)
from quotient_phase2.m231_audit_closure import verify_historical_jsons_untouched


# ==============================================================================
# 1. Mechanistically Adjacent Same-Quality 3D Baselines
# ==============================================================================
@dataclass
class FullGridGuidePolicy:
    """Callable discrete KL-LMDP controller backed by a full-grid desirability vector `z_unit`."""
    A_csr: sp.csr_matrix
    operator_epoch: int
    goal_signature: Tuple[int, ...]
    z_unit: np.ndarray

    def action_distribution(self, state_f: int) -> Tuple[np.ndarray, np.ndarray]:
        s = int(state_f)
        if s in self.goal_signature:
            return np.array([s], dtype=np.int64), np.array([1.0], dtype=float)
        row = self.A_csr.getrow(s)
        mask = (row.indices != s) & (row.data < 0.0)
        nb = row.indices[mask]
        mw = -row.data[mask]
        zb = self.z_unit[nb]
        zmx = float(np.max(zb))
        w = mw * (zb / zmx) if zmx > 0.0 else mw
        return nb, w / float(np.sum(w))


def verify_direct_desirability_solution(
    A_csr: sp.csr_matrix,
    gm: np.ndarray,
    z_unit: np.ndarray,
    s_f: int,
    rel_tol: float = 1e-7,
) -> Tuple[bool, float, float]:
    """Verifies strict exterior positivity and BOTH global AND componentwise relative residuals
    `max_{i in ext} |(A z)_i| / max(A_{ii} |z_i|, b_i, 1e-300) <= rel_tol` (`Closes B6-03` perturbation probe).
    """
    ext = np.flatnonzero(~gm)
    if len(ext) == 0:
        return True, 0.0, 0.0
    if (not np.all(np.isfinite(z_unit))) or np.any(z_unit[ext] <= 0.0) or float(z_unit[s_f]) <= 0.0:
        return False, float("inf"), float("inf")
    res_ext = np.abs((A_csr @ z_unit)[ext])
    b_ext = np.asarray(np.abs(A_csr[ext, :][:, gm].sum(axis=1))).ravel()
    rhs_norm = max(1.0, float(np.max(b_ext)))
    glob_res = float(np.max(res_ext)) / rhs_norm
    diag_ext = np.abs(A_csr.diagonal()[ext]) * np.abs(z_unit[ext])
    denom_comp = np.maximum(np.maximum(diag_ext, b_ext), 1e-300)
    comp_rel_res = float(np.max(res_ext / denom_comp))
    ok = bool(glob_res <= 1e-9 and comp_rel_res <= rel_tol)
    return ok, glob_res, comp_rel_res


class SingleLUGoalCapacitance3DPlanner:
    """Classical global factor reuse (`SingleLU + target-ring Woodbury capacitance`):
      - Offline: ONE global `splu(A_csc)` on the full `N`-node 3D grid;
      - Online per unseen goal: solves `|ring_G|` (`~26`) global triangular systems `U = lu.solve(E_ring)`,
        inverts the `|ring_G| x |ring_G|` capacitance matrix `U[ring_G, :]`, and delivers the high-accuracy
        numerical reference `z_unit = U @ (U[ring_G, :]^{-1} 1)` (`guarantee_tier = "high_accuracy_numerical_reference"`,
        NOT an outward-rounded interval certificate; `Closes B6-03`).
    """

    def __init__(self, spec: ProblemSpec, A_csc: sp.csc_matrix, A_csr: sp.csr_matrix, eps_tol: float = 0.25) -> None:
        spec.validate_cole_hopf_lmdp("SingleLUGoalCapacitance3DPlanner")
        self.lam = float(spec.lam)
        self.eps_tol = float(eps_tol)
        self.n_f = A_csr.shape[0]
        self.operator_epoch = 0
        t0 = time.perf_counter()
        self.A_csr = A_csr
        self.lu = spla.splu(A_csc)
        self.offline_init_ms = 1000.0 * (time.perf_counter() - t0)

    def factor_bytes(self) -> int:
        return int(
            self.lu.L.data.nbytes + self.lu.L.indices.nbytes + self.lu.L.indptr.nbytes
            + self.lu.U.data.nbytes + self.lu.U.indices.nbytes + self.lu.U.indptr.nbytes
        )

    def update_world_operator(self, A_new_csc: sp.csc_matrix, A_new_csr: sp.csr_matrix) -> float:
        t0 = time.perf_counter()
        self.operator_epoch += 1
        self.A_csr = A_new_csr
        self.lu = spla.splu(A_new_csc)
        return 1000.0 * (time.perf_counter() - t0)

    def solve_unseen_goal(self, s_f: int, goal_mask: np.ndarray, phi_goal: float = 0.0) -> dict:
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        g_f = np.flatnonzero(gm)
        phi_f = float(phi_goal)
        if bool(gm[s_f]):
            pol = FullGridGuidePolicy(self.A_csr, self.operator_epoch, tuple(int(x) for x in g_f), np.ones(self.n_f, dtype=float))
            _ = pol.action_distribution(s_f)
            return {
                "query_ms": 1000.0 * (time.perf_counter() - t0),
                "guarantee_tier": "exact_start_in_goal",
                "status": "start_in_goal",
                "reference_valid": True,
                "lo": phi_f,
                "hi": phi_f,
                "value": phi_f,
                "width": 0.0,
                "certified": True,
                "certificate": None,
                "policy": pol,
                "z_unit": pol.z_unit,
            }

        if not bool(check_directed_goal_reachability(self.A_csr, gm)[s_f]):
            return {
                "query_ms": 1000.0 * (time.perf_counter() - t0),
                "guarantee_tier": "unreachable",
                "status": "unreachable",
                "reference_valid": False,
                "lo": float("inf"),
                "hi": float("inf"),
                "value": float("inf"),
                "width": float("inf"),
                "certified": False,
                "certificate": None,
                "policy": None,
                "z_unit": None,
            }

        ext = np.flatnonzero(~gm)
        ring = g_f[np.asarray((self.A_csr[ext, :][:, g_f] < 0.0).sum(axis=0)).ravel() > 0]
        rhs = np.zeros((self.n_f, len(ring)), dtype=float)
        rhs[ring, np.arange(len(ring))] = 1.0
        U = self.lu.solve(rhs)
        coef = np.linalg.solve(U[ring, :], np.ones(len(ring), dtype=float))
        z_unit = U @ coef
        z_unit[gm] = 1.0

        ok_ref, glob_res, comp_rel_res = verify_direct_desirability_solution(self.A_csr, gm, z_unit, s_f, rel_tol=1e-7)
        if not ok_ref:
            val_bad = (phi_f + float(-self.lam * np.log(float(z_unit[s_f])))) if (np.isfinite(z_unit[s_f]) and float(z_unit[s_f]) > 0.0) else float("nan")
            return {
                "query_ms": 1000.0 * (time.perf_counter() - t0),
                "guarantee_tier": "unverified_direct_solve",
                "status": "failed_componentwise_relative_residual",
                "reference_valid": False,
                "lo": -float("inf"),
                "hi": float("inf"),
                "value": val_bad,
                "width": float("inf"),
                "certified": False,
                "certificate": None,
                "policy": None,
                "z_unit": z_unit,
                "global_residual": glob_res,
                "componentwise_relative_residual": comp_rel_res,
            }

        val = phi_f + float(-self.lam * np.log(float(z_unit[s_f])))
        pol = FullGridGuidePolicy(self.A_csr, self.operator_epoch, tuple(int(x) for x in g_f), np.maximum(z_unit, 0.0))
        _ = pol.action_distribution(s_f)
        q_ms = 1000.0 * (time.perf_counter() - t0)
        return {
            "query_ms": q_ms,
            "guarantee_tier": "high_accuracy_numerical_reference",
            "status": "ok_numerical_reference",
            "reference_valid": True,
            "lo": None,
            "hi": None,
            "value": val,
            "width": None,
            "certified": False,
            "certificate": None,
            "policy": pol,
            "z_unit": z_unit,
            "ring_size": int(len(ring)),
            "global_residual": glob_res,
            "componentwise_relative_residual": comp_rel_res,
        }


class MatrixFreeExactSchurKrylov3DPlanner:
    """Same zero-hint room decomposition, same 27 room LUs, and same verified L0 Lyapunov gauge `w_lyap`
    as `SeamFreePortal3DPlanner`, solving the full `n_g`-node portal equation `(I - P_tilde) u = r_hat / w_lyap`
    directly via matrix-free `BiCGSTAB` + verified defect closure (`NO L1..L3 coarse portal refinement!`).
    Cleanly isolates the contribution of adaptive `L1..L3` portal coarsening & caching from local Schur + gauge!
    """

    def __init__(
        self,
        spec: ProblemSpec,
        gn: int,
        free_3d: np.ndarray,
        free_nodes: np.ndarray,
        pts_f: np.ndarray,
        A_csr: sp.csr_matrix,
        eps_tol: float = 0.25,
    ) -> None:
        self.base = SeamFreePortal3DPlanner(
            spec=spec, gn=gn, free_3d=free_3d, free_nodes=free_nodes, pts_f=pts_f, A_csr=A_csr, eps_tol=eps_tol, coarse_l0_only=True, use_portal_cache=True
        )
        self.offline_init_ms = self.base.offline_init_ms
        self.lam = self.base.lam
        self.eps_tol = self.base.eps_tol

    def update_world_operator(self, A_new_csr: sp.csr_matrix, modified_rooms: Sequence[int], portal_diag_changed: bool) -> dict:
        return self.base.update_world_operator(A_new_csr, modified_rooms, portal_diag_changed)

    def solve_unseen_goal(self, s_f: int, goal_mask: np.ndarray, phi_goal: float = 0.0) -> dict:
        t0 = time.perf_counter()
        b_pl = self.base
        s_i, gm, g_f, phi_f = b_pl._validate_query_inputs(s_f, goal_mask, phi_goal)
        goal_sig = tuple(int(x) for x in g_f)
        solves_0 = b_pl.local_lu_solve_calls

        if bool(gm[s_i]) or (not bool(check_directed_goal_reachability(b_pl.A_csr, gm)[s_i])):
            return b_pl.solve_unseen_goal(s_i, gm, phi_goal=phi_f)

        c_g = int(b_pl.room_of_f[g_f[0]])
        rn_g = b_pl.room_nodes[c_g]
        tl_g = b_pl.room_tl[c_g]
        c_s = int(b_pl.room_of_f[s_i])

        in_g_loc, ring_r = extract_directed_goal_ring_in_room(b_pl.A_csr, gm, rn_g, b_pl.gamma_f[tl_g])

        RHS_rg = np.zeros((len(rn_g), len(ring_r)), dtype=float)
        RHS_rg[ring_r, np.arange(len(ring_r))] = 1.0
        U_rg = b_pl.hq_lus[c_g].solve(RHS_rg)
        b_pl.local_lu_solve_calls += int(len(ring_r))
        K_inv = np.linalg.inv(U_rg[ring_r, :])

        NegAgr_U_full = np.zeros((b_pl.n_g, len(ring_r)), dtype=float)
        NegAgr_U_full[tl_g, :] = b_pl.room_NegAgr[c_g] @ U_rg
        Smooth_U = b_pl.lu_Agg.solve(NegAgr_U_full)

        h_goal_r = U_rg @ (K_inv @ np.ones(len(ring_r), dtype=float))
        r_gam = np.zeros(b_pl.n_g, dtype=float)
        r_gam[tl_g] = np.maximum(b_pl.room_NegAgr[c_g] @ h_goal_r, 0.0)
        r_hat = np.maximum(b_pl.lu_Agg.solve(r_gam), 0.0)

        if c_s >= 0:
            rn_s = b_pl.room_nodes[c_s]
            tl_s = b_pl.room_tl[c_s]
            pos_s = int(np.searchsorted(rn_s, s_i))
            e_s = np.zeros(len(rn_s), dtype=float)
            e_s[pos_s] = 1.0
            lam_s = b_pl.hq_lus[c_s].solve(e_s, trans="T")
            b_pl.local_lu_solve_calls += 1
            if c_s == c_g:
                RHS_adj = np.zeros(len(rn_s), dtype=float)
                RHS_adj[ring_r] = K_inv.T @ U_rg[pos_s, :]
                lam_s = lam_s - b_pl.hq_lus[c_s].solve(RHS_adj, trans="T")
                b_pl.local_lu_solve_calls += 1
            h_s_tl = np.maximum(np.asarray(b_pl.room_Arg[c_s].T @ lam_s).ravel(), 0.0)
            z_dir = float(h_goal_r[pos_s]) if c_s == c_g else 0.0
        else:
            g_idx_s = int(np.searchsorted(b_pl.gamma_f, s_i))
            tl_s = np.array([g_idx_s], dtype=np.int64)
            h_s_tl = np.array([1.0], dtype=float)
            z_dir = 0.0

        # L0 Lyapunov gauge only (`m = n_portals = 51`)
        blks_0, K_0_list = [], []
        for p_id in range(b_pl.n_portals):
            bp, Kp, y_by_c = b_pl._ensure_portal_level(p_id, 0)
            if c_g in y_by_c:
                Kp = np.maximum(Kp - Smooth_U @ (K_inv @ y_by_c[c_g][ring_r, :]), 0.0)
            blks_0.extend(bp)
            K_0_list.append(Kp)
        K0 = np.hstack(K_0_list)
        hw0 = solve_and_verify_portal_howard_bounds(K0, r_hat, blks_0, k_neg_roundoff_ub=b_pl.max_k_neg_roundoff, max_iters=30)
        W_lo = hw0["W_lo"] * (1.0 - 1e-12)
        W_hi = hw0["W_hi"] * (1.0 + 1e-12)
        w_lyap = hw0["w_lyap"]
        s_0_raw = hw0["s_0_raw"]
        hw_ok = bool(hw0["verified"])

        z_lo_s = z_dir + float(h_s_tl @ W_lo[tl_s])
        z_hi_s = z_dir + float(h_s_tl @ W_hi[tl_s])
        lo_c = (phi_f - self.lam * float(np.log(z_hi_s))) if (hw_ok and z_hi_s > 0.0) else -float("inf")
        hi_c = (phi_f - self.lam * float(np.log(z_lo_s))) if (hw_ok and z_lo_s > 0.0) else float("inf")

        matvecs = 0
        if hw_ok and (hi_c - lo_c > self.eps_tol):
            def _apply_K_lin(vec_g: np.ndarray) -> np.ndarray:
                nonlocal matvecs
                matvecs += 1
                NegM_v = np.zeros(b_pl.n_g, dtype=float)
                for c in range(b_pl.n_rooms):
                    tl_c = b_pl.room_tl[c]
                    v_sub = vec_g[tl_c]
                    if not np.any(v_sub):
                        continue
                    yc = b_pl.hq_lus[c].solve(b_pl.room_Arg[c] @ v_sub)
                    b_pl.local_lu_solve_calls += 1
                    if c == c_g:
                        yc = yc - U_rg @ (K_inv @ yc[ring_r])
                    NegM_v[tl_c] += b_pl.room_NegAgr[c] @ yc
                return b_pl.lu_Agg.solve(NegM_v)

            Lin_sc = spla.LinearOperator(
                (b_pl.n_g, b_pl.n_g),
                matvec=lambda u: np.asarray(u, dtype=float) - (_apply_K_lin(w_lyap * np.asarray(u, dtype=float)) / w_lyap),
                dtype=float,
            )
            u_cur = (0.5 * (W_lo + W_hi)) / w_lyap
            rhs_sc = r_hat / w_lyap
            W_lo_0, W_hi_0 = W_lo, W_hi
            for rtol_s, mx_s in ((2.5e-3, 6), (1.0e-4, 10), (2.0e-6, 16), (1.0e-9, 50)):
                u_cur, _ = spla.bicgstab(Lin_sc, rhs_sc, x0=u_cur, rtol=rtol_s, atol=1e-14, maxiter=mx_s)
                if not np.all(np.isfinite(u_cur)):
                    hw_ok = False
                    break
                z_til = np.maximum(u_cur * w_lyap, 0.0)
                d_til = (_apply_K_lin(z_til) + r_hat) - z_til
                eta_m = float(np.max(np.maximum(-d_til, 0.0) / s_0_raw)) * (1.0 + 1e-10)
                eta_p = float(np.max(np.maximum(d_til, 0.0) / s_0_raw)) * (1.0 + 1e-10)
                u_lo_b = np.maximum(W_lo_0, z_til - eta_m * w_lyap)
                u_hi_b = np.minimum(W_hi_0, z_til + eta_p * w_lyap)
                if np.any(u_lo_b <= 0.0) or np.any(u_lo_b > u_hi_b):
                    hw_ok = False
                    break
                W_lo_c = (_apply_K_lin(u_lo_b) + r_hat) * (1.0 - 1e-12)
                W_hi_c = (_apply_K_lin(u_hi_b) + r_hat) * (1.0 + 1e-12)
                if np.all(W_lo_c > 0.0) and np.all(W_lo_c <= W_hi_c) and np.all(W_lo_c >= u_lo_b * (1.0 - 2e-12)):
                    W_lo, W_hi = W_lo_c, W_hi_c
                    z_lo_s = z_dir + float(h_s_tl @ W_lo[tl_s])
                    z_hi_s = z_dir + float(h_s_tl @ W_hi[tl_s])
                    lo_c = phi_f - self.lam * float(np.log(z_hi_s))
                    hi_c = phi_f - self.lam * float(np.log(z_lo_s))
                    if hi_c - lo_c <= self.eps_tol:
                        break
                else:
                    hw_ok = False
                    break

        is_cert = bool(hw_ok and np.isfinite(lo_c) and np.isfinite(hi_c) and (hi_c >= lo_c) and (hi_c - lo_c <= self.eps_tol + 1e-12))
        cert = Phase2DecisionCertificate("full_policy_enclosure", is_cert, self.eps_tol, lo_c, hi_c, None, 0, 1, state_id=s_i, operator_epoch=b_pl.operator_epoch) if is_cert else None
        pol = LazyRoomPortalPolicy(b_pl, b_pl.operator_epoch, goal_sig, phi_f, c_g, in_g_loc, ring_r, U_rg, K_inv, h_goal_r, W_lo) if is_cert else None
        if pol is not None:
            _ = pol.action_distribution(s_i)
        q_ms = 1000.0 * (time.perf_counter() - t0)
        op_rhs = int(b_pl.local_lu_solve_calls - solves_0)
        return {
            "query_ms": q_ms,
            "guarantee_tier": "float64_toleranced_model_enclosure" if is_cert else "uncertified",
            "status": "ok" if is_cert else "numeric_or_width_unclosed",
            "lo": lo_c,
            "hi": hi_c,
            "width": float(hi_c - lo_c) if is_cert else float("inf"),
            "certified": is_cert,
            "certificate": cert,
            "policy": pol,
            "portal_matvecs": matvecs,
            "operational_local_lu_rhs_solves": op_rhs,
            "evaluation_materialization_rhs_solves": 0,
            "local_lu_solves": op_rhs,
        }


class VerifiedGlobalWarmILU3DPlanner:
    """Quality-gated global `Warm-ILU-BiCGSTAB` (`Closes Audit Section 6.1`):
      - Runs global `spilu` + warm-started `BiCGSTAB(rtol=1e-11, atol=1e-15)` (`recording raw unverified
        Warm-ILU wall-clock & value error on the exact same solve!`), then checks rigorous global M-matrix
        residual bounds `||A_{II}^{-1}||_inf <= lam / q_min` (`z_sub = z_kry - dz > 0`).
      - Whenever unscaled global Krylov fails `full_policy_enclosure` (`because min_x z*(x) << (lam/q_min)||r||_inf`
        across 27-room 3D buildings), lazily factors ONE cached global `splu(A_csc)` per operator epoch and
        resolves the goal via exact Woodbury capacitance (giving this baseline the strongest possible global
        direct fallback rather than repeated from-scratch `spsolve`s, with 100% of fallback costs billed!).
    """

    def __init__(self, spec: ProblemSpec, q_min_val: float, A_csc: sp.csc_matrix, A_csr: sp.csr_matrix, eps_tol: float = 0.25) -> None:
        spec.validate_cole_hopf_lmdp("VerifiedGlobalWarmILU3DPlanner")
        self.lam = float(spec.lam)
        self.inv_inf_ub = self.lam / float(q_min_val)
        self.eps_tol = float(eps_tol)
        self.n_f = A_csr.shape[0]
        self.operator_epoch = 0
        self.z_prev: Optional[np.ndarray] = None
        self._fallback_lu: Optional[spla.SuperLU] = None
        t0 = time.perf_counter()
        self.A_csc = A_csc
        self.A_csr = A_csr
        self.ilu = spla.spilu(A_csc, drop_tol=1e-3, fill_factor=6.0)
        self.offline_init_ms = 1000.0 * (time.perf_counter() - t0)

    def update_world_operator(self, A_new_csc: sp.csc_matrix, A_new_csr: sp.csr_matrix, q_min_val: float) -> float:
        t0 = time.perf_counter()
        self.operator_epoch += 1
        self.inv_inf_ub = self.lam / float(q_min_val)
        self.A_csc = A_new_csc
        self.A_csr = A_new_csr
        self._fallback_lu = None
        self.ilu = spla.spilu(A_new_csc, drop_tol=1e-3, fill_factor=6.0)
        return 1000.0 * (time.perf_counter() - t0)

    def solve_unseen_goal(self, s_f: int, goal_mask: np.ndarray, phi_goal: float = 0.0) -> dict:
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        g_f = np.flatnonzero(gm)
        goal_sig = tuple(int(x) for x in g_f)
        phi_f = float(phi_goal)
        ext = np.flatnonzero(~gm)
        s_pos = int(np.searchsorted(ext, s_f))
        A_ii = self.A_csr[ext, :][:, ext]
        rhs = np.asarray((-self.A_csr[ext, :][:, gm]).sum(axis=1)).ravel()

        def _mv(v_sub: np.ndarray) -> np.ndarray:
            fv = np.zeros(self.n_f, dtype=float)
            fv[ext] = np.asarray(v_sub, dtype=float)
            return self.ilu.solve(fv)[ext]

        M_op = spla.LinearOperator(A_ii.shape, matvec=_mv, dtype=float)
        x_cur = self.z_prev[ext] if self.z_prev is not None else None
        zk, info = spla.bicgstab(A_ii, rhs, x0=x_cur, rtol=1e-11, atol=1e-15, maxiter=800, M=M_op)
        if info != 0:
            zk, info = spla.bicgstab(A_ii, rhs, rtol=1e-11, atol=1e-15, maxiter=1500, M=M_op)

        z_raw_full = np.ones(self.n_f, dtype=float)
        z_raw_full[ext] = np.maximum(zk, 0.0)
        _ = FullGridGuidePolicy(self.A_csr, self.operator_epoch, goal_sig, z_raw_full).action_distribution(s_f)
        raw_unverified_query_ms = 1000.0 * (time.perf_counter() - t0)
        raw_rtol11_val = (
            (phi_f - self.lam * float(np.log(float(zk[s_pos]))))
            if (np.isfinite(zk[s_pos]) and float(zk[s_pos]) > 0.0)
            else float("inf")
        )

        certified_by_krylov = False
        pointwise_s0_certified = False
        used_exact_fallback = False

        if info == 0 and np.all(np.isfinite(zk)):
            res_inf = float(np.max(np.abs(rhs - (A_ii @ zk))))
            dz = self.inv_inf_ub * res_inf * (1.0 + 1e-11)
            if float(zk[s_pos]) - dz > 0.0:
                lo_pt = phi_f - self.lam * float(np.log(float(zk[s_pos]) + dz))
                hi_pt = phi_f - self.lam * float(np.log(float(zk[s_pos]) - dz))
                if hi_pt - lo_pt <= self.eps_tol:
                    pointwise_s0_certified = True
            z_sub_ext = zk - dz
            z_sup_ext = zk + dz
            if np.all(z_sub_ext > 0.0):
                lo_c = phi_f - self.lam * float(np.log(float(z_sup_ext[s_pos])))
                hi_c = phi_f - self.lam * float(np.log(float(z_sub_ext[s_pos])))
                if hi_c - lo_c <= self.eps_tol:
                    certified_by_krylov = True
                    z_dep = np.ones(self.n_f, dtype=float)
                    z_dep[ext] = z_sub_ext
                    self.z_prev = z_dep

        if not certified_by_krylov:
            used_exact_fallback = True
            if self._fallback_lu is None:
                self._fallback_lu = spla.splu(self.A_csc)
            ring = g_f[np.asarray((self.A_csr[ext, :][:, g_f] < 0.0).sum(axis=0)).ravel() > 0]
            rhs_cap = np.zeros((self.n_f, len(ring)), dtype=float)
            rhs_cap[ring, np.arange(len(ring))] = 1.0
            U_cap = self._fallback_lu.solve(rhs_cap)
            coef_cap = np.linalg.solve(U_cap[ring, :], np.ones(len(ring), dtype=float))
            z_dep = U_cap @ coef_cap
            z_dep[gm] = 1.0
            ok_fb, _, _ = verify_direct_desirability_solution(self.A_csr, gm, z_dep, s_f, rel_tol=1e-7)
            if not ok_fb:
                raise RuntimeError("VerifiedGlobalWarmILU3DPlanner direct fallback failed componentwise relative residual check")
            val_ex = phi_f - self.lam * float(np.log(float(z_dep[s_f])))
            lo_c, hi_c = None, None
            z_dep = np.maximum(z_dep, 0.0)
            self.z_prev = z_dep
            cert = None
        else:
            cert = Phase2DecisionCertificate("full_policy_enclosure", True, self.eps_tol, lo_c, hi_c, None, 0, 1, state_id=int(s_f), operator_epoch=self.operator_epoch)
            val_ex = 0.5 * (lo_c + hi_c)

        pol = FullGridGuidePolicy(self.A_csr, self.operator_epoch, goal_sig, z_dep)
        _ = pol.action_distribution(s_f)
        q_ms = 1000.0 * (time.perf_counter() - t0)
        return {
            "query_ms": q_ms,
            "krylov_stage_diagnostic_inside_verified_pipeline_ms": raw_unverified_query_ms,
            "raw_unverified_query_ms": raw_unverified_query_ms,
            "guarantee_tier": "uniform_mmatrix_enclosure" if certified_by_krylov else "fallback_to_high_accuracy_numerical_reference",
            "lo": lo_c,
            "hi": hi_c,
            "value": val_ex,
            "width": (hi_c - lo_c) if (lo_c is not None and hi_c is not None) else None,
            "certified": bool(certified_by_krylov),
            "reference_fallback_valid": True,
            "certified_without_direct_fallback": certified_by_krylov,
            "pointwise_s0_certified_by_krylov": pointwise_s0_certified,
            "used_exact_fallback": used_exact_fallback,
            "raw_rtol11_value": raw_rtol11_val,
            "certificate": cert,
            "policy": pol,
            "z_unit": z_dep,
        }


# ==============================================================================
# 2. Balanced Randomized Per-Map Worker (`WP-B` + `WP-C` Cache Causal Study)
# ==============================================================================
ARMS_ORDER = (
    "M231_Portal_CacheOn",
    "M231_Portal_StructureOnly",
    "M231_Portal_CacheOff_Cold",
    "MatrixFree_ExactSchur_Krylov",
    "SingleLU_GoalCapacitance",
    "Verified_Global_WarmILU",
)

CORE4_ARMS_ORDER = (
    "M231_Portal_CacheOn",
    "MatrixFree_ExactSchur_Krylov",
    "SingleLU_GoalCapacitance",
    "Verified_Global_WarmILU",
)


def _portal_memory_ledger(pl: SeamFreePortal3DPlanner) -> dict:
    entries = list(pl.portal_cache.values())
    return {
        "portal_level_cache_entries": int(len(entries)),
        "stored_basis_columns": int(sum(len(x[0]) for x in entries)),
        "K_cache_bytes": int(sum(x[1].nbytes for x in entries)),
        "room_Y_cache_bytes": int(sum(y.nbytes for x in entries for y in x[2].values())),
        "local_LU_factor_bytes": int(
            sum(lu.L.data.nbytes + lu.L.indices.nbytes + lu.L.indptr.nbytes + lu.U.data.nbytes + lu.U.indices.nbytes + lu.U.indptr.nbytes for lu in pl.hq_lus)
        ),
    }


def _run_fair_map_worker(args: Tuple[int, int, int, int, bool]) -> dict:
    """Runs one 3D map (`seed`, `gn`, `K=n_tasks`, `map_idx`, `include_cold_cache_arms`) in Latin-square balanced arm order!"""
    seed, gn, n_tasks, map_idx, include_cold_cache_arms = args
    enforce_single_thread_env()

    world = generate_3d_multiroom_world(seed=seed, gn=gn, spec=ProblemSpec(dim=3), n_tasks=n_tasks, fit_gp_world=True)
    spec = world["spec"]
    lam = float(spec.lam)
    free_3d = world["free_3d"]
    free_mask = world["free_mask"]
    free_nodes = world["free_nodes"]
    pts_f = world["pts_f"]
    q_f = world["q_f"]
    b_f = world["b_f"]
    tasks = world["tasks"]
    q_min_val = float(np.min(q_f))

    t_op0 = time.perf_counter()
    A_csc = build_3d_reflecting_obstacle_mmatrix(spec, gn, free_mask, q_f, b_f)
    A_csr = A_csc.tocsr()
    operator_assembly_ms = 1000.0 * (time.perf_counter() - t_op0)

    # Balanced cyclic Latin-square shift of arm execution order across maps!
    active_arms = ARMS_ORDER if include_cold_cache_arms else CORE4_ARMS_ORDER
    n_arms = len(active_arms)
    perm_arms = [active_arms[(map_idx + k) % n_arms] for k in range(n_arms)]
    arm_results: Dict[str, dict] = {}
    singlelu_exact_values: Optional[List[float]] = None
    m231_deployed_guides: Optional[List[np.ndarray]] = None

    for exec_rank, arm_name in enumerate(perm_arms):
        gc.collect()
        if arm_name in ("M231_Portal_CacheOn", "M231_Portal_StructureOnly", "M231_Portal_CacheOff_Cold"):
            # Keep intra-query memoization enabled (`use_portal_cache=True`) across ALL 3 arms (`Closes B6-02`)!
            pl = SeamFreePortal3DPlanner(
                spec=spec, gn=gn, free_3d=free_3d, free_nodes=free_nodes, pts_f=pts_f, A_csr=A_csr, eps_tol=0.25, use_portal_cache=True
            )
            init_ms = pl.offline_init_ms
            q_ms_list, eager_ms_list, active_dofs, lu_solves, widths = [], [], [], [], []
            defect_cnt = 0
            cert_cnt = 0
            lo_list, hi_list = [], []
            guides_tmp: List[np.ndarray] = []

            n_pol_eval = (n_tasks if gn <= 35 else (min(12, n_tasks) if gn <= 47 else min(6, n_tasks))) if arm_name == "M231_Portal_CacheOn" else 0
            mat_flag = (arm_name == "M231_Portal_CacheOn")
            op_rhs_solves, eval_rhs_solves = [], []
            for t_i, (s_f, gm_k) in enumerate(tasks):
                if t_i > 0:
                    if arm_name == "M231_Portal_StructureOnly":
                        for k_del in [k for k in pl.portal_cache.keys() if k[1] > 0]:
                            del pl.portal_cache[k_del]
                    elif arm_name == "M231_Portal_CacheOff_Cold":
                        pl.portal_cache.clear()
                res = pl.solve_unseen_goal(s_f, gm_k, phi_goal=0.0, materialize_full_z_sub=mat_flag)
                q_ms_list.append(res["query_ms"])
                eager_ms_list.append(res["eager_materialize_ms"])
                active_dofs.append(res["active_dofs"])
                op_rhs_solves.append(res["operational_local_lu_rhs_solves"])
                eval_rhs_solves.append(res["evaluation_materialization_rhs_solves"])
                lu_solves.append(res["local_lu_solves"])
                widths.append(res["width"])
                lo_list.append(res["lo"])
                hi_list.append(res["hi"])
                if res["used_defect_closure"]:
                    defect_cnt += 1
                if res["certified"]:
                    cert_cnt += 1
                if t_i < n_pol_eval and res["z_guide_full"] is not None:
                    guides_tmp.append(res["z_guide_full"])
                del res

            mem_info = _portal_memory_ledger(pl)
            if arm_name == "M231_Portal_CacheOn":
                m231_deployed_guides = guides_tmp
            cum_prefix = list(np.cumsum([init_ms] + q_ms_list)[1:])
            arm_results[arm_name] = {
                "exec_order_rank": exec_rank,
                "init_ms": init_ms,
                "total_lazy_policy_ms": init_ms + float(np.sum(q_ms_list)),
                "total_eager_full_grid_ms": init_ms + float(np.sum(q_ms_list)) + float(np.sum(eager_ms_list)),
                "mean_query_ms": float(np.mean(q_ms_list)),
                "mean_eager_materialize_ms": float(np.mean(eager_ms_list)),
                "first6_query_ms": float(np.mean(q_ms_list[:6])),
                "last6_query_ms": float(np.mean(q_ms_list[-6:])),
                "prefix_cumulative_ms": [float(x) for x in cum_prefix],
                "mean_active_coarse_dofs": float(np.mean(active_dofs)),
                "full_interface_dofs": int(pl.n_g),
                "defect_closure_count": int(defect_cnt),
                "total_operational_local_lu_rhs_solves": int(np.sum(op_rhs_solves)),
                "total_evaluation_materialization_rhs_solves": int(np.sum(eval_rhs_solves)),
                "total_local_lu_solves": int(np.sum(lu_solves)),
                "certified_count": int(cert_cnt),
                "mean_width": float(np.mean(widths)),
                "max_width": float(np.max(widths)),
                "lo_list": lo_list,
                "hi_list": hi_list,
                "memory_ledger": mem_info,
            }
            del pl

        elif arm_name == "MatrixFree_ExactSchur_Krylov":
            pl_mf = MatrixFreeExactSchurKrylov3DPlanner(
                spec=spec, gn=gn, free_3d=free_3d, free_nodes=free_nodes, pts_f=pts_f, A_csr=A_csr, eps_tol=0.25
            )
            init_ms = pl_mf.offline_init_ms
            q_ms_list, matvecs_l, lu_solves, lo_list, hi_list = [], [], [], [], []
            cert_cnt = 0
            for s_f, gm_k in tasks:
                res = pl_mf.solve_unseen_goal(s_f, gm_k, phi_goal=0.0)
                q_ms_list.append(res["query_ms"])
                matvecs_l.append(res["portal_matvecs"])
                lu_solves.append(res["local_lu_solves"])
                lo_list.append(res["lo"])
                hi_list.append(res["hi"])
                if res["certified"]:
                    cert_cnt += 1
                del res
            cum_prefix = list(np.cumsum([init_ms] + q_ms_list)[1:])
            arm_results[arm_name] = {
                "exec_order_rank": exec_rank,
                "init_ms": init_ms,
                "total_lazy_policy_ms": init_ms + float(np.sum(q_ms_list)),
                "mean_query_ms": float(np.mean(q_ms_list)),
                "prefix_cumulative_ms": [float(x) for x in cum_prefix],
                "mean_portal_matvecs": float(np.mean(matvecs_l)),
                "total_operational_local_lu_rhs_solves": int(np.sum(lu_solves)),
                "total_local_lu_solves": int(np.sum(lu_solves)),
                "certified_count": int(cert_cnt),
                "lo_list": lo_list,
                "hi_list": hi_list,
            }
            del pl_mf

        elif arm_name == "SingleLU_GoalCapacitance":
            pl_slu = SingleLUGoalCapacitance3DPlanner(spec=spec, A_csc=A_csc, A_csr=A_csr, eps_tol=0.25)
            init_ms = pl_slu.offline_init_ms
            f_bytes = pl_slu.factor_bytes()
            q_ms_list, vals_ex, lo_list, hi_list = [], [], [], []
            cert_cnt = 0
            for s_f, gm_k in tasks:
                res = pl_slu.solve_unseen_goal(s_f, gm_k, phi_goal=0.0)
                q_ms_list.append(res["query_ms"])
                vals_ex.append(res["value"])
                lo_list.append(res["lo"])
                hi_list.append(res["hi"])
                if res["certified"]:
                    cert_cnt += 1
                del res
            singlelu_exact_values = vals_ex
            cum_prefix = list(np.cumsum([init_ms] + q_ms_list)[1:])
            arm_results[arm_name] = {
                "exec_order_rank": exec_rank,
                "init_ms": init_ms,
                "total_lazy_policy_ms": init_ms + float(np.sum(q_ms_list)),
                "mean_query_ms": float(np.mean(q_ms_list)),
                "prefix_cumulative_ms": [float(x) for x in cum_prefix],
                "global_lu_factor_bytes": f_bytes,
                "certified_count": int(cert_cnt),
                "lo_list": lo_list,
                "hi_list": hi_list,
            }
            del pl_slu

        elif arm_name == "Verified_Global_WarmILU":
            pl_wilu = VerifiedGlobalWarmILU3DPlanner(spec=spec, q_min_val=q_min_val, A_csc=A_csc, A_csr=A_csr, eps_tol=0.25)
            init_ms = pl_wilu.offline_init_ms
            q_ms_list, raw_q_ms_list, lo_list, hi_list, raw_vals = [], [], [], [], []
            kry_cert_cnt = 0
            pt_cert_cnt = 0
            fb_cnt = 0
            for s_f, gm_k in tasks:
                res = pl_wilu.solve_unseen_goal(s_f, gm_k, phi_goal=0.0)
                q_ms_list.append(res["query_ms"])
                raw_q_ms_list.append(res["raw_unverified_query_ms"])
                lo_list.append(res["lo"])
                hi_list.append(res["hi"])
                raw_vals.append(res["raw_rtol11_value"])
                if res["certified_without_direct_fallback"]:
                    kry_cert_cnt += 1
                if res["pointwise_s0_certified_by_krylov"]:
                    pt_cert_cnt += 1
                if res["used_exact_fallback"]:
                    fb_cnt += 1
                del res
            cum_prefix = list(np.cumsum([init_ms] + q_ms_list)[1:])
            arm_results[arm_name] = {
                "exec_order_rank": exec_rank,
                "init_ms": init_ms,
                "total_lazy_policy_ms": init_ms + float(np.sum(q_ms_list)),
                "unverified_warm_ilu_total_ms": init_ms + float(np.sum(raw_q_ms_list)),
                "mean_query_ms": float(np.mean(q_ms_list)),
                "unverified_warm_ilu_mean_query_ms": float(np.mean(raw_q_ms_list)),
                "prefix_cumulative_ms": [float(x) for x in cum_prefix],
                "krylov_self_certified_count": int(kry_cert_cnt),
                "pointwise_s0_certified_by_krylov_count": int(pt_cert_cnt),
                "direct_fallback_count": int(fb_cnt),
                "certified_count": int(kry_cert_cnt),
                "verified_or_valid_reference_count": int(kry_cert_cnt + fb_cnt),
                "raw_rtol11_values": raw_vals,
                "lo_list": lo_list,
                "hi_list": hi_list,
            }
            del pl_wilu

    # Reversed-order task sequence causal control on `35^3 / 47^3` (`rules out early-vs-late task difficulty bias!`)
    rev_control = None
    if gn <= 47 and include_cold_cache_arms:
        pl_rev = SeamFreePortal3DPlanner(
            spec=spec, gn=gn, free_3d=free_3d, free_nodes=free_nodes, pts_f=pts_f, A_csr=A_csr, eps_tol=0.25, use_portal_cache=True
        )
        rev_q = [pl_rev.solve_unseen_goal(s_f, gm_k)["query_ms"] for s_f, gm_k in reversed(tasks)]
        rev_control = {
            "reversed_first6_query_ms": float(np.mean(rev_q[:6])),
            "reversed_last6_query_ms": float(np.mean(rev_q[-6:])),
            "reversed_total_ms": pl_rev.offline_init_ms + float(np.sum(rev_q)),
        }
        del pl_rev

    # Independent Audit against `SingleLU_GoalCapacitance` (`high_accuracy_numerical_reference`)
    assert singlelu_exact_values is not None
    v_ex = np.array(singlelu_exact_values, dtype=float)
    m231_his_saved: Optional[np.ndarray] = None
    for arm_name, a_d in arm_results.items():
        lo_raw = a_d.pop("lo_list")
        hi_raw = a_d.pop("hi_list")
        if arm_name == "M231_Portal_CacheOn":
            m231_his_saved = np.array(hi_raw, dtype=float)
        if arm_name == "SingleLU_GoalCapacitance":
            a_d["independent_reference_violations"] = int(np.sum(~np.isfinite(v_ex)))
        elif arm_name == "Verified_Global_WarmILU":
            viols = 0
            for idx_q, (lv, hv) in enumerate(zip(lo_raw, hi_raw)):
                if lv is not None and hv is not None:
                    if v_ex[idx_q] < lv - 1e-7 or v_ex[idx_q] > hv + 1e-7 or (hv - lv) > 0.25 + 1e-6:
                        viols += 1
            a_d["independent_reference_violations"] = viols
        else:
            los = np.array(lo_raw, dtype=float)
            his = np.array(hi_raw, dtype=float)
            viols = int(np.sum((v_ex < los - 1e-7) | (v_ex > his + 1e-7) | ((his - los) > 0.25 + 1e-6)))
            a_d["independent_reference_violations"] = viols
        if "raw_rtol11_values" in a_d:
            rv = np.array(a_d.pop("raw_rtol11_values"), dtype=float)
            a_d["unverified_rtol11_errors_gt_025"] = int(np.sum(np.abs(rv - v_ex) > 0.25))
            a_d["unverified_rtol11_max_abs_err"] = float(np.max(np.abs(rv - v_ex)))

    # Independent Deployed Discrete KL-LMDP Policy Evaluations on `M231_Portal_CacheOn` (`verifying L <= V* <= J <= U`)
    pol_viols = 0
    pol_regrets: List[float] = []
    max_sub_res = 0.0
    if m231_deployed_guides and m231_his_saved is not None:
        m231_d = arm_results["M231_Portal_CacheOn"]
        for t_i, z_g in enumerate(m231_deployed_guides):
            s_f, gm_k = tasks[t_i]
            ext_all = np.flatnonzero(~gm_k)
            max_sub_res = max(max_sub_res, float(np.max((A_csr @ z_g)[ext_all])))
            vp = evaluate_3d_deployed_policy_exact(A_csr, gm_k, 0.0, z_g, lam, s_f)
            reg = max(0.0, vp - singlelu_exact_values[t_i])
            pol_regrets.append(reg)
            if reg > 0.25 + 1e-6 or vp < singlelu_exact_values[t_i] - 1e-6 or vp > float(m231_his_saved[t_i]) + 1e-6:
                pol_viols += 1
        m231_d["deployed_policy_evaluated_count"] = int(len(m231_deployed_guides))
        m231_d["deployed_policy_violations"] = int(pol_viols)
        m231_d["deployed_policy_mean_regret"] = float(np.mean(pol_regrets))
        m231_d["deployed_policy_max_regret"] = float(np.max(pol_regrets))
        m231_d["max_global_subsolution_residual"] = max_sub_res

    return {
        "seed": seed,
        "gn": gn,
        "n_tasks": n_tasks,
        "n_free_dofs": int(len(free_nodes)),
        "shared_gp_fit_ms": float(world["gp_fit_ms"]),
        "shared_operator_assembly_ms": operator_assembly_ms,
        "execution_order": perm_arms,
        "reversed_order_cache_control": rev_control,
        "arms": arm_results,
    }


def _run_continual_fair_worker(args: Tuple[int, int, int, int]) -> dict:
    """Continual `known_support_synthetic_local_operator_updates` (`47^3`, `1` Init + `5` Updates x `6` Tasks)
    comparing `M231_Portal_CacheOn`, `MatrixFree_ExactSchur_Krylov`, `SingleLU_GoalCapacitance`, and `Verified_Global_WarmILU`,
    explicitly charging BOTH `operator_rebuild_ms` AND solver update/query time!
    """
    seed, gn, n_epochs, tasks_per_ep = args
    enforce_single_thread_env()
    tot_tasks = (1 + n_epochs) * tasks_per_ep
    world = generate_3d_multiroom_world(seed=seed, gn=gn, spec=ProblemSpec(dim=3), n_tasks=tot_tasks, fit_gp_world=False)
    spec = world["spec"]
    free_3d = world["free_3d"]
    free_mask = world["free_mask"]
    free_nodes = world["free_nodes"]
    pts_f = world["pts_f"]
    q_cur = world["q_f"].copy()
    b_cur = world["b_f"].copy()
    tasks_all = world["tasks"]

    t_a0 = time.perf_counter()
    A0_csc = build_3d_reflecting_obstacle_mmatrix(spec, gn, free_mask, q_cur, b_cur)
    A0_csr = A0_csc.tocsr()
    op_init_ms = 1000.0 * (time.perf_counter() - t_a0)

    p_m231 = SeamFreePortal3DPlanner(spec, gn, free_3d, free_nodes, pts_f, A0_csr, eps_tol=0.25, use_portal_cache=True)
    p_mf = MatrixFreeExactSchurKrylov3DPlanner(spec, gn, free_3d, free_nodes, pts_f, A0_csr, eps_tol=0.25)
    p_slu = SingleLUGoalCapacitance3DPlanner(spec, A0_csc, A0_csr, eps_tol=0.25)
    p_wilu = VerifiedGlobalWarmILU3DPlanner(spec, float(np.min(q_cur)), A0_csc, A0_csr, eps_tol=0.25)

    totals = {
        "shared_operator_rebuild_marginal_ms": 0.0,
        "M231_Portal_CacheOn": {"life_ms": op_init_ms + p_m231.offline_init_ms, "marg_ms": 0.0, "viols": 0, "retained_l1_l3_entries": []},
        "MatrixFree_ExactSchur_Krylov": {"life_ms": op_init_ms + p_mf.offline_init_ms, "marg_ms": 0.0, "viols": 0},
        "SingleLU_GoalCapacitance": {"life_ms": op_init_ms + p_slu.offline_init_ms, "marg_ms": 0.0, "viols": 0},
        "Verified_Global_WarmILU": {"life_ms": op_init_ms + p_wilu.offline_init_ms, "marg_ms": 0.0, "viols": 0, "fallbacks": 0},
    }

    rng_ep = np.random.default_rng(seed + 810000)
    for ep in range(1 + n_epochs):
        if ep > 0:
            mod_rooms = [int(c) for c in rng_ep.choice(p_m231.n_rooms, size=2, replace=False)]
            for c in mod_rooms:
                rn_c = p_m231.room_nodes[c]
                ctr_c = np.mean(pts_f[rn_c], axis=0, keepdims=True)
                bump = float(rng_ep.uniform(0.18, 0.42)) * np.exp(-np.sum((pts_f[rn_c] - ctr_c) ** 2, axis=1) / 0.12)
                q_cur[rn_c] = np.clip(q_cur[rn_c] + bump, 0.05, 6.0)
                b_cur[rn_c, :] += rng_ep.normal(0.0, 0.05, size=(1, 3))

            t_rb = time.perf_counter()
            A_csc_t = build_3d_reflecting_obstacle_mmatrix(spec, gn, free_mask, q_cur, b_cur)
            A_csr_t = A_csc_t.tocsr()
            rb_ms = 1000.0 * (time.perf_counter() - t_rb)
            totals["shared_operator_rebuild_marginal_ms"] += rb_ms

            u_m231 = p_m231.update_world_operator(A_csr_t, mod_rooms, portal_diag_changed=False)
            totals["M231_Portal_CacheOn"]["life_ms"] += rb_ms + u_m231["update_ms"]
            totals["M231_Portal_CacheOn"]["marg_ms"] += rb_ms + u_m231["update_ms"]
            totals["M231_Portal_CacheOn"]["retained_l1_l3_entries"].append(u_m231["retained_cache_entries"])

            u_mf = p_mf.update_world_operator(A_csr_t, mod_rooms, portal_diag_changed=False)
            totals["MatrixFree_ExactSchur_Krylov"]["life_ms"] += rb_ms + u_mf["update_ms"]
            totals["MatrixFree_ExactSchur_Krylov"]["marg_ms"] += rb_ms + u_mf["update_ms"]

            dt_slu = p_slu.update_world_operator(A_csc_t, A_csr_t)
            totals["SingleLU_GoalCapacitance"]["life_ms"] += rb_ms + dt_slu
            totals["SingleLU_GoalCapacitance"]["marg_ms"] += rb_ms + dt_slu

            dt_wilu = p_wilu.update_world_operator(A_csc_t, A_csr_t, float(np.min(q_cur)))
            totals["Verified_Global_WarmILU"]["life_ms"] += rb_ms + dt_wilu
            totals["Verified_Global_WarmILU"]["marg_ms"] += rb_ms + dt_wilu

        ep_tasks = tasks_all[ep * tasks_per_ep : (ep + 1) * tasks_per_ep]
        for s_f, gm_k in ep_tasks:
            r_slu = p_slu.solve_unseen_goal(s_f, gm_k)
            v_ex = r_slu["value"]
            totals["SingleLU_GoalCapacitance"]["life_ms"] += r_slu["query_ms"]
            if ep > 0:
                totals["SingleLU_GoalCapacitance"]["marg_ms"] += r_slu["query_ms"]

            for nm, pl_obj in (
                ("M231_Portal_CacheOn", p_m231),
                ("MatrixFree_ExactSchur_Krylov", p_mf),
                ("Verified_Global_WarmILU", p_wilu),
            ):
                rr = pl_obj.solve_unseen_goal(s_f, gm_k)
                totals[nm]["life_ms"] += rr["query_ms"]
                if ep > 0:
                    totals[nm]["marg_ms"] += rr["query_ms"]
                if nm == "Verified_Global_WarmILU" and rr["used_exact_fallback"]:
                    totals[nm]["fallbacks"] += 1
                    if (not rr.get("reference_fallback_valid", False)) or abs(float(rr["value"]) - v_ex) > 1e-7:
                        totals[nm]["viols"] += 1
                else:
                    if (not rr["certified"]) or v_ex < rr["lo"] - 1e-7 or v_ex > rr["hi"] + 1e-7 or rr["width"] > 0.25 + 1e-6:
                        totals[nm]["viols"] += 1
                del rr

    return {"seed": seed, "gn": gn, "stream": "known_support_synthetic_local_operator_updates", "totals": totals}


# ==============================================================================
# 3. Cohort Aggregation, Four-Denominator Accounting, & Summary Figure
# ==============================================================================
def _summarize_fair_cohort(rows: List[dict], label: str, max_workers_used: int) -> dict:
    n_maps = len(rows)
    n_tasks = int(rows[0]["n_tasks"])
    tot_tasks = n_maps * n_tasks
    gp_arr = np.array([r["shared_gp_fit_ms"] for r in rows], dtype=float)
    op_arr = np.array([r["shared_operator_assembly_ms"] for r in rows], dtype=float)
    prefix_arr = gp_arr + op_arr

    m231_arr = np.array([r["arms"]["M231_Portal_CacheOn"]["total_lazy_policy_ms"] for r in rows], dtype=float)
    m231_eager_arr = np.array([r["arms"]["M231_Portal_CacheOn"]["total_eager_full_grid_ms"] for r in rows], dtype=float)
    present_arms = [ak for ak in ARMS_ORDER if ak in rows[0]["arms"]]
    arms_summary = {}
    for arm_name in present_arms:
        t_arr = np.array([r["arms"][arm_name]["total_lazy_policy_ms"] for r in rows], dtype=float)
        t_full_arr = t_arr + prefix_arr
        init_arr = np.array([r["arms"][arm_name]["init_ms"] for r in rows], dtype=float)
        q_arr = np.array([r["arms"][arm_name]["mean_query_ms"] for r in rows], dtype=float)
        pref_mat = np.array([r["arms"][arm_name]["prefix_cumulative_ms"] for r in rows], dtype=float)
        viols = int(sum(r["arms"][arm_name]["independent_reference_violations"] for r in rows))
        cert_cnt = int(sum(r["arms"][arm_name]["certified_count"] for r in rows))

        entry = {
            "planner_only_mean_ms": float(np.mean(t_arr)),
            "end_to_end_incl_gp_and_assembly_mean_ms": float(np.mean(t_full_arr)),
            "init_mean_ms": float(np.mean(init_arr)),
            "query_mean_ms": float(np.mean(q_arr)),
            "prefix_cumulative_mean_ms": [float(x) for x in np.mean(pref_mat, axis=0)],
            "speedup_of_M231_CacheOn_vs_arm_planner_only": float(np.mean(t_arr) / np.mean(m231_arr)),
            "speedup_of_M231_CacheOn_eager_full_grid_vs_arm": float(np.mean(t_arr) / np.mean(m231_eager_arr)),
            "speedup_of_M231_CacheOn_vs_arm_end_to_end": float(np.mean(t_full_arr) / np.mean(m231_arr + prefix_arr)),
            "paired_diff_M231_minus_arm_ms": paired_stats(m231_arr - t_arr) if arm_name != "M231_Portal_CacheOn" and n_maps >= 2 else None,
            "certificate_conditions_verified_count": cert_cnt,
            "optimal_value_reference_checked_count": tot_tasks,
            "independent_reference_violations": viols,
        }
        if arm_name == "M231_Portal_CacheOn":
            entry["eager_full_grid_planner_mean_ms"] = float(np.mean(m231_eager_arr))
            entry["mean_eager_materialize_ms"] = float(np.mean([r["arms"][arm_name]["mean_eager_materialize_ms"] for r in rows]))
            entry["first6_query_mean_ms"] = float(np.mean([r["arms"][arm_name]["first6_query_ms"] for r in rows]))
            entry["last6_query_mean_ms"] = float(np.mean([r["arms"][arm_name]["last6_query_ms"] for r in rows]))
            entry["mean_active_coarse_dofs"] = float(np.mean([r["arms"][arm_name]["mean_active_coarse_dofs"] for r in rows]))
            entry["full_interface_dofs"] = int(rows[0]["arms"][arm_name]["full_interface_dofs"])
            entry["defect_closure_task_count"] = int(sum(r["arms"][arm_name]["defect_closure_count"] for r in rows))
            entry["defect_closure_rate"] = float(entry["defect_closure_task_count"] / tot_tasks)
            entry["mean_local_lu_solves_per_map"] = float(np.mean([r["arms"][arm_name]["total_local_lu_solves"] for r in rows]))
            entry["deployed_policy_evaluated_count"] = int(sum(r["arms"][arm_name].get("deployed_policy_evaluated_count", 0) for r in rows))
            entry["deployed_policy_violations"] = int(sum(r["arms"][arm_name].get("deployed_policy_violations", 0) for r in rows))
            entry["deployed_policy_max_regret"] = float(max(r["arms"][arm_name].get("deployed_policy_max_regret", 0.0) for r in rows))
            entry["continuous_or_real_world_evaluated_count"] = 0
            entry["mean_end_memory_bytes"] = {
                mk: float(np.mean([r["arms"][arm_name]["memory_ledger"][mk] for r in rows]))
                for mk in rows[0]["arms"][arm_name]["memory_ledger"].keys()
            }
        if arm_name == "SingleLU_GoalCapacitance":
            entry["mean_global_lu_factor_bytes"] = float(np.mean([r["arms"][arm_name]["global_lu_factor_bytes"] for r in rows]))
        if arm_name == "Verified_Global_WarmILU":
            unv_arr = np.array([r["arms"][arm_name]["unverified_warm_ilu_total_ms"] for r in rows], dtype=float)
            entry["unverified_warm_ilu_planner_mean_ms"] = float(np.mean(unv_arr))
            entry["speedup_of_M231_CacheOn_vs_unverified_warm_ilu"] = float(np.mean(unv_arr) / np.mean(m231_arr))
            entry["paired_diff_M231_minus_unverified_warm_ilu_ms"] = paired_stats(m231_arr - unv_arr) if n_maps >= 2 else None
            entry["krylov_self_certified_count"] = int(sum(r["arms"][arm_name]["krylov_self_certified_count"] for r in rows))
            entry["pointwise_s0_certified_by_krylov_count"] = int(sum(r["arms"][arm_name]["pointwise_s0_certified_by_krylov_count"] for r in rows))
            entry["direct_fallback_count"] = int(sum(r["arms"][arm_name]["direct_fallback_count"] for r in rows))
            entry["unverified_rtol11_errors_gt_025"] = int(sum(r["arms"][arm_name]["unverified_rtol11_errors_gt_025"] for r in rows))
            entry["unverified_rtol11_max_abs_err"] = float(max(r["arms"][arm_name]["unverified_rtol11_max_abs_err"] for r in rows))
        arms_summary[arm_name] = entry

    rev_rows = [r["reversed_order_cache_control"] for r in rows if r["reversed_order_cache_control"] is not None]
    rev_sum = (
        {
            "reversed_first6_query_mean_ms": float(np.mean([x["reversed_first6_query_ms"] for x in rev_rows])),
            "reversed_last6_query_mean_ms": float(np.mean([x["reversed_last6_query_ms"] for x in rev_rows])),
            "reversed_total_mean_ms": float(np.mean([x["reversed_total_ms"] for x in rev_rows])),
        }
        if rev_rows
        else None
    )

    return {
        "cohort_label": label,
        "gn": int(rows[0]["gn"]),
        "n_maps": n_maps,
        "tasks_per_map": n_tasks,
        "total_tasks": tot_tasks,
        "actual_parallel_workers": max_workers_used,
        "mean_free_dofs": float(np.mean([r["n_free_dofs"] for r in rows])),
        "shared_gp_fit_mean_ms": float(np.mean(gp_arr)),
        "shared_operator_assembly_mean_ms": float(np.mean(op_arr)),
        "reversed_order_cache_control": rev_sum,
        "arms": arms_summary,
        "per_map": rows,
    }


def _summarize_continual_fair(rows: List[dict], max_workers_used: int) -> dict:
    arm_names = ("M231_Portal_CacheOn", "MatrixFree_ExactSchur_Krylov", "SingleLU_GoalCapacitance", "Verified_Global_WarmILU")
    m231_m = np.array([r["totals"]["M231_Portal_CacheOn"]["marg_ms"] for r in rows], dtype=float)
    m231_l = np.array([r["totals"]["M231_Portal_CacheOn"]["life_ms"] for r in rows], dtype=float)
    arms_out = {}
    for nm in arm_names:
        l_arr = np.array([r["totals"][nm]["life_ms"] for r in rows], dtype=float)
        m_arr = np.array([r["totals"][nm]["marg_ms"] for r in rows], dtype=float)
        arms_out[nm] = {
            "lifecycle_incl_operator_rebuild_mean_ms": float(np.mean(l_arr)),
            "post_init_marginal_incl_operator_rebuild_mean_ms": float(np.mean(m_arr)),
            "marginal_speedup_of_M231_vs_arm": float(np.mean(m_arr) / np.mean(m231_m)),
            "lifecycle_speedup_of_M231_vs_arm": float(np.mean(l_arr) / np.mean(m231_l)),
            "paired_marginal_diff_M231_minus_arm_ms": paired_stats(m231_m - m_arr) if nm != "M231_Portal_CacheOn" and len(rows) >= 2 else None,
            "independent_reference_violations": int(sum(r["totals"][nm]["viols"] for r in rows)),
        }
    arms_out["M231_Portal_CacheOn"]["mean_retained_l1_l3_portal_level_entries"] = float(
        np.mean([np.mean(r["totals"]["M231_Portal_CacheOn"]["retained_l1_l3_entries"]) for r in rows])
    )
    arms_out["Verified_Global_WarmILU"]["total_direct_fallbacks"] = int(
        sum(r["totals"]["Verified_Global_WarmILU"]["fallbacks"] for r in rows)
    )
    return {
        "stream_name": "known_support_synthetic_local_operator_updates",
        "gn": int(rows[0]["gn"]),
        "n_maps": len(rows),
        "actual_parallel_workers": max_workers_used,
        "shared_operator_rebuild_marginal_mean_ms": float(np.mean([r["totals"]["shared_operator_rebuild_marginal_ms"] for r in rows])),
        "arms": arms_out,
        "per_map": rows,
    }


def _plot_m231_summary(cohorts: List[dict], cont_sum: dict, fig_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14.2, 9.8), dpi=160)

    # Panel A: Same-Quality End-to-End Planner Comparison (`100%` Measured, Zero Extrapolation!)
    ax = axes[0, 0]
    x = np.arange(len(cohorts))
    w = 0.19
    lbls = [f"{c['cohort_label']}\n({int(round(c['mean_free_dofs']/1000))}k DOF)" for c in cohorts]
    for idx_b, (arm_k, arm_lbl, col) in enumerate((
        ("Verified_Global_WarmILU", "Verified Warm-ILU (eps<=0.25)", "#2980b9"),
        ("SingleLU_GoalCapacitance", "SingleLU + Goal Capacitance", "#7f8c8d"),
        ("MatrixFree_ExactSchur_Krylov", "MatrixFree Exact Schur Krylov", "#e67e22"),
        ("M231_Portal_CacheOn", "M2.3.1 Dyadic Portal (CacheOn)", "#27ae60"),
    )):
        ys = [c["arms"][arm_k]["planner_only_mean_ms"] / 1000.0 for c in cohorts]
        ax.bar(x + (idx_b - 1.5) * w, ys, width=w, label=arm_lbl, color=col)
    ax.set_xticks(x)
    ax.set_xticklabels(lbls, fontsize=8.3)
    ax.set_ylabel("Measured Total Wall-Clock for K=24 Goals (s)")
    ax.set_title("A. Same-Quality Adjacent Baselines (100% Measured, Balanced Order)")
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend(fontsize=8.0)

    # Panel B: Causal Cache Amortization Curve `C(k)` (`CacheOn` vs `StructureOnly` vs `CacheOff_Cold` vs `MatrixFree`)
    ax = axes[0, 1]
    cache_cohorts = [c for c in cohorts if "M231_Portal_CacheOff_Cold" in c["arms"]]
    c_target = cache_cohorts[-1] if cache_cohorts else cohorts[-1]
    ks = np.arange(1, c_target["tasks_per_map"] + 1)
    for arm_k, arm_lbl, style, col in (
        ("M231_Portal_CacheOff_Cold", "Portal CacheOff (Cold L0..L3)", "--", "#c0392b"),
        ("M231_Portal_StructureOnly", "Portal StructureOnly (Reset L1..L3)", "-.", "#d35400"),
        ("MatrixFree_ExactSchur_Krylov", "MatrixFree Exact Schur Krylov", ":", "#2980b9"),
        ("M231_Portal_CacheOn", "M2.3.1 Portal CacheOn (Persistent)", "-", "#27ae60"),
    ):
        if arm_k in c_target["arms"]:
            curve = np.array(c_target["arms"][arm_k]["prefix_cumulative_mean_ms"]) / 1000.0
            ax.plot(ks, curve, style, linewidth=2.2, label=arm_lbl, color=col)
    ax.set_xlabel("Streaming Unseen Goal Index k (1..24)")
    ax.set_ylabel("Cumulative Wall-Clock C(k) incl. Init (s)")
    ax.set_title(f"B. Causal Cache Control on {c_target['cohort_label']}")
    ax.grid(True, alpha=0.28)
    ax.legend(fontsize=8.0)

    # Panel C: Coarse vs. Full-Interface Defect-Closure Rate & LU Solves (`Honest Dimension Accounting`)
    ax = axes[1, 0]
    c_dofs = [c["arms"]["M231_Portal_CacheOn"]["mean_active_coarse_dofs"] for c in cohorts]
    def_rates = [100.0 * c["arms"]["M231_Portal_CacheOn"]["defect_closure_rate"] for c in cohorts]
    ax.bar(x - 0.16, c_dofs, width=0.30, color="#16a085", label="Mean Active Coarse DOFs (Dyadic L0..L3)")
    ax.set_xticks(x)
    ax.set_xticklabels(lbls, fontsize=8.3)
    ax.set_ylabel("Active Coarse Quotient DOFs", color="#16a085")
    ax2 = ax.twinx()
    ax2.bar(x + 0.16, def_rates, width=0.30, color="#8e44ad", alpha=0.78, label="% Queries Needing Full-Interface Closure")
    ax2.set_ylabel("Full-Interface Defect Closure Rate (%)", color="#8e44ad")
    ax2.set_ylim(0, 100)
    ax.set_title("C. Coarse Quotient DOFs vs. Full-Interface Closure Rate")
    ax.grid(True, axis="y", alpha=0.25)

    # Panel D: Continual Known-Support Local Operator Updates (`47^3`, Operator Rebuild Charged!)
    ax = axes[1, 1]
    c_arms = ("Verified_Global_WarmILU", "SingleLU_GoalCapacitance", "MatrixFree_ExactSchur_Krylov", "M231_Portal_CacheOn")
    c_names = ["Verified\nWarm-ILU", "SingleLU +\nCapacitance", "MatrixFree\nSchur Krylov", "M2.3.1 Portal\nCacheOn"]
    c_cols = ["#2980b9", "#7f8c8d", "#e67e22", "#27ae60"]
    c_vals = [cont_sum["arms"][ak]["post_init_marginal_incl_operator_rebuild_mean_ms"] / 1000.0 for ak in c_arms]
    bars = ax.bar(np.arange(len(c_arms)), c_vals, width=0.52, color=c_cols)
    for b_rect, v_s in zip(bars, c_vals):
        ax.text(b_rect.get_x() + b_rect.get_width() / 2.0, v_s + 0.4, f"{v_s:.1f}s", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    ax.set_xticks(np.arange(len(c_arms)))
    ax.set_xticklabels(c_names, fontsize=8.5)
    ax.set_ylabel("Post-Init Marginal Cost Across 5 Updates (s)")
    ax.set_title("D. Known-Support Local Operator Updates (47^3, Rebuild Charged)")
    ax.grid(True, axis="y", alpha=0.28)

    plt.tight_layout()
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)


def _run_pool(fn, jobs: list, max_workers: int) -> list:
    if max_workers <= 1 or len(jobs) <= 1:
        return [fn(jb) for jb in jobs]
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(fn, jobs))


def run_m231_fair_campaign(self_test: bool = False) -> dict:
    verify_phase1_readonly_freeze()
    hist_ledger = verify_historical_jsons_untouched()
    enforce_single_thread_env()
    t_start = time.perf_counter()

    if self_test:
        r0 = _run_fair_map_worker((61000, 35, 6, 0, True))
        for ak, av in r0["arms"].items():
            assert av["independent_reference_violations"] == 0, f"Violation in {ak}: {av}"
            assert av.get("deployed_policy_violations", 0) == 0, f"Policy violation in {ak}: {av}"
        rc = _run_continual_fair_worker((61000, 35, 2, 3))
        for ak in ("M231_Portal_CacheOn", "MatrixFree_ExactSchur_Krylov", "SingleLU_GoalCapacitance", "Verified_Global_WarmILU"):
            assert rc["totals"][ak]["viols"] == 0, f"Continual violation in {ak}: {rc['totals'][ak]}"
        print(
            f"[M2.3.1 SELF-TEST PASS] 35^3 K=6: "
            f"CacheOn={r0['arms']['M231_Portal_CacheOn']['total_lazy_policy_ms']:.1f}ms | "
            f"StructOnly={r0['arms']['M231_Portal_StructureOnly']['total_lazy_policy_ms']:.1f}ms | "
            f"CacheOff={r0['arms']['M231_Portal_CacheOff_Cold']['total_lazy_policy_ms']:.1f}ms | "
            f"MatFreeSchur={r0['arms']['MatrixFree_ExactSchur_Krylov']['total_lazy_policy_ms']:.1f}ms | "
            f"SingleLU={r0['arms']['SingleLU_GoalCapacitance']['total_lazy_policy_ms']:.1f}ms | "
            f"VerWarmILU={r0['arms']['Verified_Global_WarmILU']['total_lazy_policy_ms']:.1f}ms "
            f"(UnvWarmILU={r0['arms']['Verified_Global_WarmILU']['unverified_warm_ilu_total_ms']:.1f}ms) | 0 violations!"
        )
        return {"self_test_passed": True, "sample_map": r0, "sample_continual": rc}

    K_goals = 24
    # Strictly separated Dev `61000..61005` + Brand-New Untouched Fresh `63000..63005` across `35^3 -> 47^3 -> 59^3` (`100%` Measured, Zero Extrapolation!)
    cohort_specs = [
        ("Dev_35cubed", list(range(61000, 61006)), 35, 3, True),
        ("Fresh63k_35cubed", list(range(63000, 63006)), 35, 3, True),
        ("Fresh63k_47cubed", list(range(63000, 63006)), 47, 3, True),
        ("Fresh63k_59cubed", list(range(63000, 63006)), 59, 3, False),
    ]

    cohort_summaries: List[dict] = []
    for c_lbl, seeds, gn_c, mw_c, incl_cold in cohort_specs:
        print(f"[M2.3.1-B/C] Running {c_lbl} ({len(seeds)} maps, K={K_goals}, balanced order, cold_arms={incl_cold}, workers={mw_c})...")
        jobs = [(s, gn_c, K_goals, idx_m, incl_cold) for idx_m, s in enumerate(seeds)]
        rows = _run_pool(_run_fair_map_worker, jobs, max_workers=mw_c)
        c_sum = _summarize_fair_cohort(rows, c_lbl, max_workers_used=mw_c)
        cohort_summaries.append(c_sum)
        a_on = c_sum["arms"]["M231_Portal_CacheOn"]
        a_mf = c_sum["arms"]["MatrixFree_ExactSchur_Krylov"]
        a_sl = c_sum["arms"]["SingleLU_GoalCapacitance"]
        a_wi = c_sum["arms"]["Verified_Global_WarmILU"]
        so_txt = ""
        if "M231_Portal_StructureOnly" in c_sum["arms"]:
            a_so = c_sum["arms"]["M231_Portal_StructureOnly"]
            so_txt = f"StructOnly={a_so['planner_only_mean_ms']:.1f}ms ({a_so['speedup_of_M231_CacheOn_vs_arm_planner_only']:.2f}x) | "
        print(
            f"  -> {c_lbl}: CacheOn={a_on['planner_only_mean_ms']:.1f}ms (eager={a_on['eager_full_grid_planner_mean_ms']:.1f}ms, def={100*a_on['defect_closure_rate']:.1f}%) | "
            f"{so_txt}"
            f"MatFreeSchur={a_mf['planner_only_mean_ms']:.1f}ms ({a_mf['speedup_of_M231_CacheOn_vs_arm_planner_only']:.2f}x, p={a_mf['paired_diff_M231_minus_arm_ms']['p_two_sided']:.3g}) | "
            f"SingleLU={a_sl['planner_only_mean_ms']:.1f}ms ({a_sl['speedup_of_M231_CacheOn_vs_arm_planner_only']:.2f}x, p={a_sl['paired_diff_M231_minus_arm_ms']['p_two_sided']:.3g}) | "
            f"VerWarmILU={a_wi['planner_only_mean_ms']:.1f}ms ({a_wi['speedup_of_M231_CacheOn_vs_arm_planner_only']:.2f}x; Unv={a_wi['unverified_warm_ilu_planner_mean_ms']:.1f}ms, {a_wi['speedup_of_M231_CacheOn_vs_unverified_warm_ilu']:.2f}x; unv_err>0.25={a_wi['unverified_rtol11_errors_gt_025']}/{c_sum['total_tasks']})"
        )
        gc.collect()

    print("[M2.3.1-Continual] Running Known-Support Synthetic Local Operator Updates on Brand-New 63000..63005 (47^3, 5 Updates x 6 Tasks)...")
    cont_rows = _run_pool(_run_continual_fair_worker, [(s, 47, 5, 6) for s in range(63000, 63006)], max_workers=3)
    cont_sum = _summarize_continual_fair(cont_rows, max_workers_used=3)
    for ak, av in cont_sum["arms"].items():
        print(
            f"  -> Continual 47^3 {ak}: Marg={av['post_init_marginal_incl_operator_rebuild_mean_ms']:.1f}ms "
            f"({av['marginal_speedup_of_M231_vs_arm']:.2f}x) | viols={av['independent_reference_violations']}"
        )

    out_dir = Path(__file__).resolve().parent
    fig_path = out_dir / "m231_fair_ablation_summary.png"
    _plot_m231_summary(cohort_summaries, cont_sum, fig_path)

    tot_viols = sum(
        av["independent_reference_violations"] + av.get("deployed_policy_violations", 0)
        for cs in cohort_summaries
        for av in cs["arms"].values()
    ) + sum(av["independent_reference_violations"] for av in cont_sum["arms"].values())

    rt_meta = collect_runtime_metadata()
    rt_meta["per_stage_parallel_workers"] = {
        "Dev_35cubed": 3,
        "Fresh63k_35cubed": 3,
        "Fresh63k_47cubed": 3,
        "Fresh63k_59cubed": 3,
        "Continual_47cubed": 3,
    }

    payload = {
        "milestone": "M2.3.1_Same_Quality_Adjacent_Baselines_and_Cache_Causal_Closure",
        "elapsed_wall_s": float(time.perf_counter() - t_start),
        "runtime_metadata": rt_meta,
        "phase2_manifest": compute_phase2_manifest(),
        "historical_artifacts_preserved": verify_historical_jsons_untouched(),
        "global_verification_ledger": {
            "ALL_ARMS_MATCHED_EPSILON_025_WITH_ZERO_VIOLATIONS": bool(tot_viols == 0),
            "total_violations_across_all_arms_and_streams": int(tot_viols),
            "independent_reference_solver": "SingleLU_GoalCapacitance (exact full-grid Woodbury solve)",
            "m231_portal_cache_on_audit_counts": {
                "certificate_conditions_verified_count": int(
                    sum(cs["arms"]["M231_Portal_CacheOn"]["certificate_conditions_verified_count"] for cs in cohort_summaries)
                    + 6 * 36
                ),
                "optimal_value_reference_checked_count": int(
                    sum(cs["arms"]["M231_Portal_CacheOn"]["optimal_value_reference_checked_count"] for cs in cohort_summaries)
                    + 6 * 36
                ),
                "deployed_policy_evaluated_count": int(
                    sum(cs["arms"]["M231_Portal_CacheOn"]["deployed_policy_evaluated_count"] for cs in cohort_summaries)
                ),
                "continuous_or_real_world_evaluated_count": 0,
            },
        },
        "cohorts": {cs["cohort_label"]: cs for cs in cohort_summaries},
        "continual_known_support_47cubed": cont_sum,
    }

    json_path = out_dir / "m231_fair_ablation_results.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[DONE] Wrote {json_path.name} & {fig_path.name} in {payload['elapsed_wall_s']:.1f}s | total_viols={tot_viols}")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--allow-legacy-archive-overwrite",
        action="store_true",
        help="Explicitly permit overwriting the frozen b6ff40d m231_fair_ablation_results.json archive (to reproduce exact b6ff40d semantics, checkout commit b6ff40d).",
    )
    args_cli = parser.parse_args()
    if (not args_cli.self_test) and (not args_cli.allow_legacy_archive_overwrite):
        raise SystemExit(
            "[ARCHIVE GUARD C232-05] m231_fair_ablation_results.json is frozen at commit b6ff40d "
            "(sha256=f844a1028ec72ca7e0c26f77106b65d4a497636451bc5cf69bf241339410dba / f844a102...). "
            "Use `quotient_phase2/verify_m232_release.py` for current M2.3.2 release verification, `--self-test` for smoke checks, "
            "or `git checkout b6ff40d` to reproduce historical M2.3.1."
        )
    run_m231_fair_campaign(self_test=args_cli.self_test)
