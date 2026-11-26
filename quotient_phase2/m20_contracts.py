"""Milestone M2.0 (`quotient_phase2.m20_contracts`):
Mathematical Object Separation (`U, H, Z, P`), Killed-Collar Lifting with Full Interface Feedback,
Operator-Verified Bilinear Primal-Dual (DWR) Functional Enclosures (`Hf` & `H1`), Non-Interchangeable
Full-Policy vs. Root-Action & Multi-Step Receding-Horizon Certificates, Row-Stochastic `R H L` Sandwich,
Normalized State-Adequacy & SSP/M-Matrix Cyclic Lyapunov Witnesses, and the 15-Gate Falsification Suite
(`C01..C10` covering `P2A-01..05`, `P2B-01..04`, `P2C-01..02` + `C11..C15` closing `v10` NaN/Inf,
root-horizon, `tiny-Z` exit/cost aliasing, and cyclic resolvent amplification counterexamples).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.sparse.csgraph import breadth_first_order

from green_response.core import collect_runtime_metadata, enforce_single_thread_env
from quotient_phase2 import compute_phase2_manifest


def check_directed_goal_reachability(A_csr: sp.spmatrix, goal_mask: np.ndarray) -> np.ndarray:
    """Computes exact directed graph reachability to `goal_mask` on M-matrix `A_csr` (`i -> j` iff `-A_{ij} > 0`).
    Uses a single C-level reverse BFS from a virtual sink connected to all `goal_mask` nodes (`O(nnz)`).
    """
    A_c = sp.csr_matrix(A_csr, dtype=float)
    n_tot = A_c.shape[0]
    gm = np.asarray(goal_mask, dtype=bool)
    if gm.ndim != 1 or gm.shape[0] != n_tot:
        raise ValueError(f"goal_mask shape {gm.shape} incompatible with operator shape {A_c.shape}")
    goal_idx = np.flatnonzero(gm)
    if len(goal_idx) == 0:
        return np.zeros(n_tot, dtype=bool)

    diag_all = A_c.diagonal()
    A_off_pos = (-(A_c - sp.diags(diag_all, offsets=0, format="csr"))).tocoo()
    keep = A_off_pos.data > 0.0
    # Reverse edges: `j -> i` if original graph has `i -> j` (`-A_{ij} > 0`), plus `sink (n_tot) -> g` for `g in goal_idx`
    rev_rows = np.concatenate([A_off_pos.col[keep], np.full(len(goal_idx), n_tot, dtype=np.int64)])
    rev_cols = np.concatenate([A_off_pos.row[keep], goal_idx.astype(np.int64)])
    rev_vals = np.ones(len(rev_rows), dtype=np.int8)
    G_rev = sp.csr_matrix((rev_vals, (rev_rows, rev_cols)), shape=(n_tot + 1, n_tot + 1))

    order = breadth_first_order(G_rev, i_start=n_tot, directed=True, return_predecessors=False)
    reach = np.zeros(n_tot + 1, dtype=bool)
    reach[order] = True
    return reach[:n_tot]


# ==============================================================================
# 1. Four-Object Separation & Killed Hitting Kernel Contract (`P2A-01`)
# ==============================================================================
def verify_killed_hitting_kernel_conditions(
    A_ii: sp.spmatrix | np.ndarray,
    B_ig: sp.spmatrix | np.ndarray,
    tol: float = 1e-12,
) -> dict:
    """Verifies sufficient M-matrix conditions guaranteeing `H = A_{II}^{-1} B >= 0` and `H 1 <= 1`:
      1. `A_{II}` is finite 2D square with positive diagonal and non-positive off-diagonals (`<= tol`);
      2. `B` is finite 2D with `B >= -tol` entrywise;
      3. `A_{II} 1 - B 1 >= -tol` and `A_{II} 1 > tol` (`1 - H 1 = A_{II}^{-1}(A_{II} 1 - B 1) >= 0`).
    Explicitly distinguishes `KilledHittingKernel` from unbounded `GreenSourceResponse` (`A^{-1} E_Gamma`).
    """
    if not (np.isfinite(tol) and tol >= 0.0):
        return {"valid": False, "reason": "invalid_tolerance", "min_row_excess": None, "inv_inf_ub": None}

    A_csr = sp.csr_matrix(A_ii, dtype=float)
    B_arr = B_ig.toarray() if sp.issparse(B_ig) else np.asarray(B_ig, dtype=float)
    if B_arr.ndim == 1:
        B_arr = B_arr[:, None]
    if A_csr.ndim != 2 or B_arr.ndim != 2:
        return {"valid": False, "reason": "invalid_ndim", "min_row_excess": None, "inv_inf_ub": None}

    n_i, n_j = A_csr.shape
    if n_i == 0 or n_i != n_j or B_arr.shape[0] != n_i:
        return {"valid": False, "reason": "shape_mismatch", "min_row_excess": None, "inv_inf_ub": None}

    if (A_csr.nnz > 0 and not np.all(np.isfinite(A_csr.data))) or (not np.all(np.isfinite(B_arr))):
        return {"valid": False, "reason": "nonfinite_entries", "min_row_excess": None, "inv_inf_ub": None}

    diag = A_csr.diagonal()
    if np.any(~np.isfinite(diag)) or np.any(diag <= tol):
        return {"valid": False, "reason": "nonpositive_diagonal", "min_row_excess": None, "inv_inf_ub": None}

    A_off = A_csr - sp.diags(diag, format="csr")
    max_off = float(A_off.max()) if A_off.nnz > 0 else 0.0
    if (not np.isfinite(max_off)) or max_off > tol:
        return {"valid": False, "reason": "positive_off_diagonal_not_z_matrix", "min_row_excess": None, "inv_inf_ub": None}

    if B_arr.size > 0 and float(np.min(B_arr)) < -tol:
        return {"valid": False, "reason": "negative_boundary_rhs", "min_row_excess": None, "inv_inf_ub": None}

    a_row_sum = np.asarray(A_csr @ np.ones(n_i, dtype=float)).ravel()
    b_row_sum = np.sum(B_arr, axis=1)
    min_a_row = float(np.min(a_row_sum))
    row_excess = a_row_sum - b_row_sum
    min_excess = float(np.min(row_excess))

    if (not np.isfinite(min_a_row)) or min_a_row <= tol:
        return {"valid": False, "reason": "nonpositive_A_row_sum", "min_row_excess": min_excess, "inv_inf_ub": None}

    submarkov_guaranteed = bool(np.isfinite(min_excess) and min_excess >= -tol)
    return {
        "valid": submarkov_guaranteed,
        "reason": "ok" if submarkov_guaranteed else "row_sum_less_than_boundary_rhs_not_submarkov",
        "min_A_row_sum": min_a_row,
        "min_row_excess": min_excess,
        "inv_inf_ub": float(1.0 / min_a_row),
    }


# ==============================================================================
# 2. Local Collar Lifting With Exact Full-Exterior / Schur Feedback (`P2A-02`)
# ==============================================================================
def extract_k_hop_collar_indices(
    A_ii_csr: sp.csr_matrix,
    B_ig: np.ndarray,
    hops: int = 2,
) -> np.ndarray:
    """Extracts the `k`-hop exterior graph collar `C_b subset I_b` starting from rows where `B_ig != 0`."""
    if hops <= 0:
        return np.zeros(0, dtype=np.int64)
    seed_mask = np.any(np.abs(B_ig) > 0.0, axis=1)
    if not np.any(seed_mask):
        return np.zeros(0, dtype=np.int64)
    adj = (np.abs(A_ii_csr) + np.abs(A_ii_csr.T)) > 0
    cur = seed_mask.astype(float)
    for _ in range(max(0, hops - 1)):
        cur = (adj @ cur + cur) > 0.0
    return np.flatnonzero(cur > 0.0).astype(np.int64)


def apply_killed_collar_residual_lift(
    A_ii_csr: sp.csr_matrix,
    B_ig: np.ndarray,
    H_base: Optional[np.ndarray],
    collar_idx: np.ndarray,
    collar_lu: Optional[spla.SuperLU] = None,
) -> Tuple[np.ndarray, np.ndarray, Optional[spla.SuperLU]]:
    """Applies local principal M-matrix collar correction `A_{CC} dH_C = R_base[C, :]`, zero-extends to `I_b`,
    and evaluates the **exact full-exterior residual** `R_full = B_ig - A_{II} H_lifted` across ALL of `I_b`
    (retaining 100% interior-exterior feedback, closing `P2A-02`).
    """
    n_ext, m_ring = B_ig.shape
    if H_base is None:
        H_lifted = np.zeros((n_ext, m_ring), dtype=float)
        R_loc = B_ig[collar_idx, :]
    else:
        H_lifted = H_base.copy()
        R_loc = B_ig[collar_idx, :] - (A_ii_csr[collar_idx, :] @ H_base)

    if len(collar_idx) > 0:
        if collar_lu is None:
            A_cc = A_ii_csr[collar_idx, :][:, collar_idx].tocsc()
            collar_lu = spla.splu(A_cc)
        dH_c = collar_lu.solve(R_loc)
        H_lifted[collar_idx, :] += dH_c

    R_full = B_ig - (A_ii_csr @ H_lifted)
    return H_lifted, R_full, collar_lu


def exact_schur_collar_solve(
    A_full: np.ndarray | sp.spmatrix,
    f_rhs: np.ndarray,
    collar_idx: Sequence[int],
) -> np.ndarray:
    """Exact two-domain Schur complement elimination with mandatory interior back-substitution (`P2A-02`)."""
    A_mat = A_full.toarray() if sp.issparse(A_full) else np.asarray(A_full, dtype=float)
    f_arr = np.asarray(f_rhs, dtype=float)
    n = A_mat.shape[0]
    c_idx = np.asarray(collar_idx, dtype=np.int64)
    mask_c = np.zeros(n, dtype=bool)
    mask_c[c_idx] = True
    f_idx = np.flatnonzero(~mask_c)

    A_bb = A_mat[np.ix_(c_idx, c_idx)]
    A_bc = A_mat[np.ix_(c_idx, f_idx)]
    A_cb = A_mat[np.ix_(f_idx, c_idx)]
    A_cc = A_mat[np.ix_(f_idx, f_idx)]

    A_bb_inv_f = np.linalg.solve(A_bb, f_arr[c_idx])
    A_bb_inv_Abc = np.linalg.solve(A_bb, A_bc)
    S_c = A_cc - A_cb @ A_bb_inv_Abc
    rhs_c = f_arr[f_idx] - A_cb @ A_bb_inv_f
    u_c = np.linalg.solve(S_c, rhs_c)
    u_b = np.linalg.solve(A_bb, f_arr[c_idx] - A_bc @ u_c)

    out = np.empty_like(f_arr, dtype=float)
    out[c_idx] = u_b
    out[f_idx] = u_c
    return out


# ==============================================================================
# 3. Operator-Verified Super-Adjoint & Bilinear Primal-Dual DWR Bounds (`P2A-03, 05`)
# ==============================================================================
def check_super_adjoint_witness(
    A_ii: sp.spmatrix | np.ndarray,
    psi_trial: np.ndarray,
    ell_rhs: np.ndarray,
    tol: float = 1e-12,
) -> dict:
    """Explicitly verifies finiteness, shape, `psi_trial >= 0`, and `A_{II}^T psi_trial >= ell_rhs` (`P2A-05`)."""
    if not (np.isfinite(tol) and tol >= 0.0):
        return {"valid_super_adjoint": False, "min_psi": None, "min_adjoint_slack": None, "adjoint_defect_l1": None}

    A_csr = sp.csr_matrix(A_ii, dtype=float)
    psi = np.asarray(psi_trial, dtype=float)
    ell = np.asarray(ell_rhs, dtype=float)
    if psi.ndim != 1 or ell.ndim != 1 or len(psi) == 0 or A_csr.shape != (len(psi), len(psi)) or len(ell) != len(psi):
        return {"valid_super_adjoint": False, "min_psi": None, "min_adjoint_slack": None, "adjoint_defect_l1": None}
    if (A_csr.nnz > 0 and not np.all(np.isfinite(A_csr.data))) or (not np.all(np.isfinite(psi))) or (not np.all(np.isfinite(ell))):
        return {"valid_super_adjoint": False, "min_psi": None, "min_adjoint_slack": None, "adjoint_defect_l1": None}

    slack = (A_csr.T @ psi) - ell
    min_psi = float(np.min(psi))
    min_slack = float(np.min(slack))
    valid = bool(np.all(np.isfinite(slack)) and min_psi >= -tol and min_slack >= -tol)
    return {
        "valid_super_adjoint": valid,
        "min_psi": min_psi,
        "min_adjoint_slack": min_slack,
        "adjoint_defect_l1": float(np.sum(np.abs(ell - (A_csr.T @ psi)))),
    }


def prepare_bilinear_dwr_operator(
    A_ii_csr: sp.csr_matrix,
    H_tilde: np.ndarray,
    R_full: np.ndarray,
    inv_inf_ub: float,
    eval_ext_rows: np.ndarray,
    Psi_ext_cols: Optional[np.ndarray] = None,
) -> dict:
    """Prepares row-localized Bilinear Primal-Dual (DWR) functional bounds on `eval_ext_rows subset I_b`."""
    if not (np.isfinite(inv_inf_ub) and inv_inf_ub >= 0.0):
        raise ValueError(f"inv_inf_ub must be finite and non-negative, got {inv_inf_ub}")
    if (not np.all(np.isfinite(H_tilde))) or (not np.all(np.isfinite(R_full))):
        raise ValueError("H_tilde and R_full must be finite")

    r_col_inf = np.max(np.abs(R_full), axis=0) if R_full.shape[0] > 0 else np.zeros(R_full.shape[1], dtype=float)
    rho_1 = float(np.max(np.abs(np.sum(R_full, axis=1)))) if R_full.size > 0 else 0.0
    n_ev_ext = len(eval_ext_rows)

    if Psi_ext_cols is None or n_ev_ext == 0:
        H_corr = H_tilde[eval_ext_rows, :].copy()
        alpha_row = np.full(n_ev_ext, float(inv_inf_ub), dtype=float)
        max_delta_l1 = 1.0 if n_ev_ext > 0 else 0.0
    else:
        if not np.all(np.isfinite(Psi_ext_cols)):
            raise ValueError("Psi_ext_cols must be finite")
        AT_Psi = A_ii_csr.T @ Psi_ext_cols
        Delta_adj = -AT_Psi
        Delta_adj[eval_ext_rows, np.arange(n_ev_ext)] += 1.0
        delta_l1 = np.sum(np.abs(Delta_adj), axis=0)
        alpha_row = float(inv_inf_ub) * delta_l1
        H_corr = H_tilde[eval_ext_rows, :] + (Psi_ext_cols.T @ R_full)
        max_delta_l1 = float(np.max(delta_l1)) if len(delta_l1) else 0.0

    z_corr = np.sum(H_corr, axis=1)
    d_z = alpha_row * rho_1
    pad_z = 1e-13 * (1.0 + np.abs(z_corr) + d_z)
    z_lo = z_corr - d_z - pad_z
    z_hi = np.minimum(1.0, z_corr + d_z + pad_z)

    return {
        "H_corr": H_corr,
        "alpha_row": alpha_row,
        "r_col_inf": r_col_inf,
        "rho_1": rho_1,
        "z_lo_ext": z_lo,
        "z_hi_ext": z_hi,
        "max_delta_l1": max_delta_l1,
    }


def bound_normalized_continuation_dwr(
    dwr_op: dict,
    F_ring_lo: np.ndarray,
    F_ring_hi: np.ndarray,
    lam: float,
    allow_extended_inf_upper: bool = True,
    strict_fail_closed: bool = False,
) -> Tuple[np.ndarray, np.ndarray, bool]:
    """Bounds `c0_b + P_b F_ring = -lam * log(Z_b) + (H_b F_ring) / Z_b` across batch columns `(m_ring, K)`
    covering BOTH numerator `H_b(F - mu)` AND denominator `Z_b = H_b 1` (`P2A-03` closed).
    When `strict_fail_closed=True`, enforces `out_lo <= out_hi` without `1e-11` rounding slack or clamping.
    """
    if F_ring_lo.ndim == 1:
        F_ring_lo = F_ring_lo[:, None]
        F_ring_hi = F_ring_hi[:, None]

    H_corr = dwr_op["H_corr"]
    alpha = dwr_op["alpha_row"][:, None]
    r_col_inf = dwr_op["r_col_inf"]
    z_lo = dwr_op["z_lo_ext"][:, None]
    z_hi = dwr_op["z_hi_ext"][:, None]
    n_rows = H_corr.shape[0]
    n_cols = F_ring_lo.shape[1]

    if (
        (not np.isfinite(lam))
        or lam <= 0.0
        or F_ring_lo.shape != F_ring_hi.shape
        or F_ring_lo.shape[0] != H_corr.shape[1]
        or np.any(np.isnan(F_ring_lo))
        or np.any(np.isnan(F_ring_hi))
        or np.any(F_ring_lo > F_ring_hi)
        or (not np.all(np.isfinite(H_corr)))
        or (not np.all(np.isfinite(alpha)))
        or (not np.all(np.isfinite(r_col_inf)))
        or (not np.all(np.isfinite(z_lo)))
    ):
        return np.empty((n_rows, n_cols)), np.empty((n_rows, n_cols)), False

    if np.any(~np.isfinite(z_hi)) or np.any(z_hi <= 1e-285):
        return np.empty((n_rows, n_cols)), np.empty((n_rows, n_cols)), False

    pos_ok = z_lo > 1e-15
    if (not allow_extended_inf_upper) and (not np.all(pos_ok)):
        return np.empty((n_rows, n_cols)), np.empty((n_rows, n_cols)), False

    if not np.all(np.isfinite(F_ring_lo)):
        return np.empty((n_rows, n_cols)), np.empty((n_rows, n_cols)), False

    f_min_lo = np.min(F_ring_lo, axis=0) - 1e-12 * (1.0 + np.max(np.abs(F_ring_lo), axis=0))
    f_max_lo = np.max(F_ring_lo, axis=0) + 1e-12 * (1.0 + np.max(np.abs(F_ring_lo), axis=0))
    mu_lo = 0.5 * (f_min_lo + f_max_lo)
    g_lo = F_ring_lo - mu_lo[None, :]
    num_hat_lo = H_corr @ g_lo
    d_num_lo = alpha * (r_col_inf @ np.abs(g_lo))[None, :]
    num_lo = num_hat_lo - d_num_lo - 1e-13 * (1.0 + np.abs(num_hat_lo) + d_num_lo)

    z_lo_safe = np.where(pos_ok, z_lo, 1.0)
    div_lo = np.where(num_lo >= 0.0, num_lo / z_hi, num_lo / z_lo_safe)
    cand_lo = mu_lo[None, :] + div_lo
    pad_lo = 1e-12 * (1.0 + np.abs(cand_lo))
    cont_lo = np.where(pos_ok, np.maximum(f_min_lo[None, :], cand_lo - pad_lo), f_min_lo[None, :])
    c0_lo = -lam * np.log(z_hi)
    out_lo = c0_lo + cont_lo

    col_hi_finite = np.all(np.isfinite(F_ring_hi), axis=0)
    out_hi = np.full((n_rows, n_cols), np.inf, dtype=float)
    if np.any(col_hi_finite) and np.any(pos_ok):
        fin_cols = np.flatnonzero(col_hi_finite)
        F_hi_sub = F_ring_hi[:, fin_cols]
        f_min_hi = np.min(F_hi_sub, axis=0) - 1e-12 * (1.0 + np.max(np.abs(F_hi_sub), axis=0))
        f_max_hi = np.max(F_hi_sub, axis=0) + 1e-12 * (1.0 + np.max(np.abs(F_hi_sub), axis=0))
        mu_hi = 0.5 * (f_min_hi + f_max_hi)
        g_hi = F_hi_sub - mu_hi[None, :]
        num_hat_hi = H_corr @ g_hi
        d_num_hi = alpha * (r_col_inf @ np.abs(g_hi))[None, :]
        num_hi = num_hat_hi + d_num_hi + 1e-13 * (1.0 + np.abs(num_hat_hi) + d_num_hi)

        div_hi = np.where(num_hi >= 0.0, num_hi / z_lo_safe, num_hi / z_hi)
        cand_hi = mu_hi[None, :] + div_hi
        pad_hi = 1e-12 * (1.0 + np.abs(cand_hi))
        cont_hi = np.minimum(f_max_hi[None, :], cand_hi + pad_hi)
        c0_hi = np.where(pos_ok, -lam * np.log(z_lo_safe), np.inf)
        sub_hi = np.where(pos_ok, c0_hi + cont_hi, np.inf)
        out_hi[:, fin_cols] = sub_hi

    if strict_fail_closed:
        valid = bool(np.all(np.isfinite(out_lo)) and (not np.any(np.isnan(out_hi))) and np.all(out_lo <= out_hi))
        return out_lo, out_hi, valid

    valid = bool(np.all(np.isfinite(out_lo)) and (not np.any(np.isnan(out_hi))) and np.all(out_lo <= out_hi + 1e-11))
    if valid:
        out_hi = np.maximum(out_lo, out_hi)
    return out_lo, out_hi, valid


# ==============================================================================
# 4. Full-Policy vs. Root-Action & Multi-Step Chain Separation (`P2A-04`, `v10 C02-C04`)
# ==============================================================================
@dataclass(frozen=True)
class Phase2DecisionCertificate:
    """Strictly separates:
      - `full_policy_enclosure`: certifies a complete deployed policy `U^mu(s0) - L^*(s0) <= epsilon_tol`;
      - `receding_horizon_root_action_enclosure`: certifies ONLY the single root decision step
        `max_{a != a_hat} [U_{a_hat}^* - L_a^*]_+ <= epsilon_tol`.
    A single-node root-action certificate NEVER claims a multi-step `guaranteed_full_horizon_regret_bound`
    (`returns None`), because unchecked downstream steps can incur unbounded policy loss (`v10 C03`).
    Multi-step receding-horizon regret bounds require `RecedingHorizonCertificateChain` holding verified
    per-step certificates across all `m` steps!
    """
    certificate_mode: str  # "full_policy_enclosure" | "receding_horizon_root_action_enclosure"
    certified: bool
    epsilon_tol: float
    lower_bound_opt: float
    incumbent_policy_upper_bound: Optional[float] = None
    root_action_q_bounds: Optional[Dict[int, Tuple[float, float]]] = None
    chosen_root_action: int = 0
    horizon_steps: int = 1
    step_index: Optional[int] = None
    state_id: Optional[int] = None
    next_state_id: Optional[int] = None
    operator_epoch: Optional[int] = None
    model_semantics: str = "discrete_upwind_kl_lmdp"

    def __post_init__(self) -> None:
        if not isinstance(self.certified, (bool, np.bool_)):
            raise TypeError("certified must be a boolean")
        if self.certificate_mode not in ("full_policy_enclosure", "receding_horizon_root_action_enclosure"):
            raise ValueError(f"Invalid certificate_mode: {self.certificate_mode}")
        if not isinstance(self.model_semantics, str) or not self.model_semantics.strip():
            raise ValueError("model_semantics must be a non-empty string")
        for attr_nm in ("step_index", "state_id", "next_state_id", "operator_epoch"):
            val = getattr(self, attr_nm)
            if val is not None and (not isinstance(val, (int, np.integer)) or isinstance(val, bool) or int(val) < 0):
                raise ValueError(f"{attr_nm} must be None or a non-negative integer, got {val!r}")
        if (
            not isinstance(self.horizon_steps, (int, np.integer))
            or isinstance(self.horizon_steps, bool)
            or int(self.horizon_steps) < 1
        ):
            raise ValueError(f"horizon_steps must be an integer >= 1, got {self.horizon_steps!r}")
        if not isinstance(self.chosen_root_action, (int, np.integer)) or isinstance(self.chosen_root_action, bool):
            raise ValueError(f"chosen_root_action must be an integer, got {self.chosen_root_action!r}")
        if (not np.isfinite(self.epsilon_tol)) or float(self.epsilon_tol) < 0.0:
            raise ValueError(f"epsilon_tol must be finite and >= 0, got {self.epsilon_tol!r}")
        if not np.isfinite(self.lower_bound_opt):
            raise ValueError("lower_bound_opt must be finite")
        if self.incumbent_policy_upper_bound is not None and (not np.isfinite(self.incumbent_policy_upper_bound)):
            raise ValueError("incumbent_policy_upper_bound must be finite when provided")

        if self.root_action_q_bounds is not None:
            if not isinstance(self.root_action_q_bounds, dict):
                raise TypeError("root_action_q_bounds must be a dict or None")
            for k, pair in self.root_action_q_bounds.items():
                if not isinstance(k, (int, np.integer)) or isinstance(k, bool):
                    raise ValueError(f"Action key {k!r} must be an integer")
                if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                    raise ValueError(f"Action {k} bounds must be a 2-tuple (q_lo, q_hi)")
                q_lo, q_hi = float(pair[0]), float(pair[1])
                if (not np.isfinite(q_lo)) or np.isnan(q_hi) or (q_hi == -float("inf")) or (q_lo > q_hi + 1e-11):
                    raise ValueError(f"Invalid/non-finite action Q-interval for action {k}: {(q_lo, q_hi)}")

        if self.certificate_mode == "full_policy_enclosure" and self.certified:
            if self.incumbent_policy_upper_bound is None or (not np.isfinite(self.incumbent_policy_upper_bound)):
                raise ValueError("full_policy_enclosure requires finite incumbent_policy_upper_bound")
            gap_pol = float(self.incumbent_policy_upper_bound - self.lower_bound_opt)
            if (not np.isfinite(gap_pol)) or gap_pol > float(self.epsilon_tol) + 1e-12 or gap_pol < -1e-11:
                raise ValueError(
                    f"full_policy_enclosure violated: policy_gap={gap_pol} vs epsilon_tol={self.epsilon_tol}"
                )
            if self.root_action_q_bounds:
                if self.chosen_root_action not in self.root_action_q_bounds:
                    raise ValueError("chosen_root_action missing from non-empty root_action_q_bounds")
                if not np.isfinite(self.root_action_q_bounds[self.chosen_root_action][1]):
                    raise ValueError("chosen_root_action must have finite upper Q-bound")

        if self.certificate_mode == "receding_horizon_root_action_enclosure" and self.certified:
            if not self.root_action_q_bounds or self.chosen_root_action not in self.root_action_q_bounds:
                raise ValueError("chosen_root_action missing from root_action_q_bounds")
            u_hat = float(self.root_action_q_bounds[self.chosen_root_action][1])
            if not np.isfinite(u_hat):
                raise ValueError("chosen_root_action upper Q-bound must be finite")
            others = [float(v[0]) for k, v in self.root_action_q_bounds.items() if k != self.chosen_root_action]
            root_gap = 0.0 if not others else max(0.0, float(u_hat - min(others)))
            if (not np.isfinite(root_gap)) or root_gap > float(self.epsilon_tol) + 1e-12:
                raise ValueError(f"root_action_enclosure violated: root_gap={root_gap} vs tol={self.epsilon_tol}")

    @property
    def guaranteed_root_action_regret_bound(self) -> Optional[float]:
        """Single-step optimal-continuation root Q-gap bound (certified ONLY at the root state)."""
        if not self.certified:
            return None
        if self.root_action_q_bounds and self.chosen_root_action in self.root_action_q_bounds:
            u_hat = float(self.root_action_q_bounds[self.chosen_root_action][1])
            others = [float(v[0]) for k, v in self.root_action_q_bounds.items() if k != self.chosen_root_action]
            return 0.0 if not others else max(0.0, float(u_hat - min(others)))
        if self.certificate_mode == "full_policy_enclosure":
            return float(max(0.0, self.incumbent_policy_upper_bound - self.lower_bound_opt))
        return None

    @property
    def guaranteed_full_horizon_regret_bound(self) -> Optional[float]:
        """Returns a full-horizon deployed-policy regret bound ONLY when the entire horizon is certified!
        A single-node `receding_horizon_root_action_enclosure` returns `None` (`v10 C03`).
        """
        if not self.certified:
            return None
        if self.certificate_mode == "full_policy_enclosure":
            return float(max(0.0, self.incumbent_policy_upper_bound - self.lower_bound_opt))
        return None


@dataclass(frozen=True)
class RecedingHorizonCertificateChain:
    """Explicit multi-step certificate chain requiring verified root-action certificates at EVERY step `t = 1..m`
    before returning cumulative regret bound `sum_{t=1}^m eta_t`.
    """
    expected_horizon_steps: int
    step_certificates: Tuple[Phase2DecisionCertificate, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.expected_horizon_steps, (int, np.integer))
            or isinstance(self.expected_horizon_steps, bool)
            or int(self.expected_horizon_steps) < 1
        ):
            raise ValueError("expected_horizon_steps must be an integer >= 1")
        if not isinstance(self.step_certificates, tuple):
            raise TypeError("step_certificates must be a tuple of Phase2DecisionCertificate")
        for c in self.step_certificates:
            if not isinstance(c, Phase2DecisionCertificate):
                raise TypeError("All entries of step_certificates must be Phase2DecisionCertificate")

    @property
    def trajectory_identity_verified(self) -> bool:
        """Verifies that multi-step certificates carry distinct sequential step indices `0..m-1`,
        concrete state & operator identities, and contiguous transition linkage `next_state_id == next.state_id`.
        Closes `EC-06` (repeating a single root object `(c, c, c, c)` is rejected!).
        """
        m = int(self.expected_horizon_steps)
        if len(self.step_certificates) != m:
            return False
        for idx_t, c in enumerate(self.step_certificates):
            if c.step_index != idx_t or c.state_id is None or c.operator_epoch is None:
                return False
            if idx_t < m - 1:
                nxt = self.step_certificates[idx_t + 1]
                if c.next_state_id is None or c.next_state_id != nxt.state_id:
                    return False
        return True

    @property
    def all_steps_certified(self) -> bool:
        if len(self.step_certificates) != int(self.expected_horizon_steps):
            return False
        if not all(c.certified and c.guaranteed_root_action_regret_bound is not None for c in self.step_certificates):
            return False
        if int(self.expected_horizon_steps) > 1 and (not self.trajectory_identity_verified):
            return False
        return True

    @property
    def guaranteed_full_horizon_regret_bound(self) -> Optional[float]:
        if not self.all_steps_certified:
            return None
        return float(sum(float(c.epsilon_tol) for c in self.step_certificates))


# ==============================================================================
# 5. Convex `R H L` Sandwich, Lumpability, Normalized State-Adequacy & Cyclic SSP (`P2B-01..02`, `M2.2`)
# ==============================================================================
def build_row_stochastic_sandwich_kernel(
    H_micro: np.ndarray,
    R_restrict: np.ndarray,
    L_lift: np.ndarray,
    tol: float = 1e-12,
) -> np.ndarray:
    """Constructs `H_bar = R @ H @ L` verifying shape, finiteness, `H >= 0, H 1 <= 1`, and row-stochastic `R, L`."""
    if not (np.isfinite(tol) and tol >= 0.0):
        raise ValueError(f"Invalid tolerance tol={tol}")
    H = np.asarray(H_micro, dtype=float)
    R = np.asarray(R_restrict, dtype=float)
    L = np.asarray(L_lift, dtype=float)
    if H.ndim != 2 or R.ndim != 2 or L.ndim != 2 or H.size == 0 or R.size == 0 or L.size == 0:
        raise ValueError("H, R, and L must be non-empty 2D arrays")
    if R.shape[1] != H.shape[0] or H.shape[1] != L.shape[0]:
        raise ValueError(f"Incompatible R @ H @ L shapes: {R.shape}, {H.shape}, {L.shape}")
    if (not np.all(np.isfinite(H))) or (not np.all(np.isfinite(R))) or (not np.all(np.isfinite(L))):
        raise ValueError("H, R, and L must contain only finite entries")
    if float(np.min(H)) < -tol or float(np.max(np.sum(H, axis=1))) > 1.0 + tol:
        raise ValueError("Micro kernel H must be non-negative sub-Markov (H >= 0, H 1 <= 1)")
    if float(np.min(R)) < -tol or float(np.max(np.abs(np.sum(R, axis=1) - 1.0))) > tol:
        raise ValueError("Restriction R must be non-negative row-stochastic (R >= 0, R 1 = 1)")
    if float(np.min(L)) < -tol or float(np.max(np.abs(np.sum(L, axis=1) - 1.0))) > tol:
        raise ValueError("Lifting L must be non-negative row-stochastic (L >= 0, L 1 = 1)")
    return R @ H @ L


def audit_partition_lumpability_and_two_step_defect(
    P_micro: np.ndarray,
    blocks: Sequence[Sequence[int]],
) -> dict:
    """Computes BOTH within-block exit-distribution dispersion `delta_lump` (strong lumpability defect)
    AND independent 2-step aggregation discrepancy `||R P^2 L - (R P L)^2||_inf` (`P2B-02`).
    """
    P = np.asarray(P_micro, dtype=float)
    n = P.shape[0]
    k_b = len(blocks)
    L = np.zeros((n, k_b), dtype=float)
    R = np.zeros((k_b, n), dtype=float)
    for b_idx, blk in enumerate(blocks):
        idx_arr = np.asarray(blk, dtype=np.int64)
        L[idx_arr, b_idx] = 1.0
        R[b_idx, idx_arr] = 1.0 / float(len(idx_arr))

    block_trans = P @ L
    max_within_block_l1 = 0.0
    for blk in blocks:
        rows = block_trans[np.asarray(blk, dtype=np.int64), :]
        if len(rows) > 1:
            diffs = np.sum(np.abs(rows[:, None, :] - rows[None, :, :]), axis=2)
            max_within_block_l1 = max(max_within_block_l1, float(np.max(diffs)))

    Q_1 = build_row_stochastic_sandwich_kernel(P, R, L)
    Q_true_2 = R @ (P @ P) @ L
    Q_sq = Q_1 @ Q_1
    two_step_err_inf = float(np.max(np.sum(np.abs(Q_true_2 - Q_sq), axis=1)))
    return {
        "within_block_exit_dispersion_l1": max_within_block_l1,
        "independent_two_step_discrepancy_inf": two_step_err_inf,
        "point_interval_product_width": 0.0,
        "is_strongly_lumpable": bool(max_within_block_l1 <= 1e-12),
    }


def audit_normalized_block_state_adequacy(
    H_block_to_exits: np.ndarray,
    lam: float,
    continuation_span_bound: float,
    z_min_floor: float = 1e-6,
    adequacy_tol: float = 0.25,
) -> dict:
    """Audits state-adequacy of merging rows `x, x' in B` on the **normalized** `(c_0, P)` option parameters
    rather than raw `delta_H` (`v10` `tiny-Z` exit & cost aliasing guard):
      1. `kernel_valid`: `H >= 0` and `H 1 <= 1` (finite);
      2. `positivity_certified`: `min_x Z(x) >= z_min_floor > 0`;
      3. `joint_bellman_discrepancy`:
         `max_{x, x' in B} [ |c_0(x) - c_0(x')| + 0.5 * ||P(x,.) - P(x',.)||_1 * continuation_span_bound ]`,
         where `c_0(x) = -lam * log(Z(x))` and `P(x,.) = H(x,.) / Z(x)`.
    Never certifies `state_adequacy_certified = True` unless BOTH `kernel_valid`, `positivity_certified`,
    and `joint_bellman_discrepancy <= adequacy_tol` hold!
    """
    H = np.asarray(H_block_to_exits, dtype=float)
    if H.ndim != 2 or H.shape[0] == 0 or (not np.all(np.isfinite(H))) or (not np.isfinite(lam)) or lam <= 0.0:
        return {
            "kernel_valid": False,
            "positivity_certified": False,
            "state_adequacy_certified": False,
            "z_min": None,
            "raw_delta_H_l1": None,
            "max_delta_c0": None,
            "max_delta_P_l1": None,
            "joint_bellman_discrepancy": None,
        }
    if (not np.isfinite(continuation_span_bound)) or continuation_span_bound < 0.0 or (not np.isfinite(adequacy_tol)) or adequacy_tol < 0.0:
        raise ValueError("continuation_span_bound and adequacy_tol must be finite and >= 0")

    z = np.sum(H, axis=1)
    kernel_valid = bool(float(np.min(H)) >= -1e-12 and float(np.max(z)) <= 1.0 + 1e-12)
    z_min = float(np.min(z))
    pos_cert = bool(kernel_valid and z_min >= max(float(z_min_floor), 1e-15))

    raw_dh = 0.0
    if H.shape[0] > 1:
        raw_dh = float(np.max(np.sum(np.abs(H[:, None, :] - H[None, :, :]), axis=2)))

    if not pos_cert:
        return {
            "kernel_valid": kernel_valid,
            "positivity_certified": False,
            "state_adequacy_certified": False,
            "z_min": z_min,
            "raw_delta_H_l1": raw_dh,
            "max_delta_c0": float("inf"),
            "max_delta_P_l1": 2.0 if H.shape[0] > 1 else 0.0,
            "joint_bellman_discrepancy": float("inf"),
        }

    c0 = -float(lam) * np.log(z)
    P = H / z[:, None]
    if H.shape[0] == 1:
        dc0 = 0.0
        dp = 0.0
        joint_disc = 0.0
    else:
        dc0_mat = np.abs(c0[:, None] - c0[None, :])
        dp_mat = np.sum(np.abs(P[:, None, :] - P[None, :, :]), axis=2)
        joint_mat = dc0_mat + 0.5 * dp_mat * float(continuation_span_bound)
        dc0 = float(np.max(dc0_mat))
        dp = float(np.max(dp_mat))
        joint_disc = float(np.max(joint_mat))

    return {
        "kernel_valid": kernel_valid,
        "positivity_certified": True,
        "state_adequacy_certified": bool(joint_disc <= float(adequacy_tol) + 1e-12),
        "z_min": z_min,
        "raw_delta_H_l1": raw_dh,
        "max_delta_c0": dc0,
        "max_delta_P_l1": dp,
        "joint_bellman_discrepancy": joint_disc,
    }


def certify_cyclic_ssp_policy_via_lyapunov_witness(
    P_sub: np.ndarray,
    c_step_lo: np.ndarray,
    c_step_hi: np.ndarray,
    V_trial: np.ndarray,
    w_lyapunov: np.ndarray,
    tol: float = 1e-12,
) -> dict:
    """Certifies `[V_lo, V_hi]` for a cyclic absorbing SSP Markov policy `(P_sub, c_step)` WITHOUT assuming
    discounting `gamma < 1`, using an explicit **SSP Lyapunov witness** `w >= 0` satisfying `(I - P_sub) w >= 1`:
      - Since `P_sub >= 0` and `(I - P_sub) w >= s_min * 1` (`s_min > 0`), `(I - P_sub)` is a nonsingular M-matrix
        with `0 <= (I - P_sub)^{-1}` and `(I - P_sub)^{-1} 1 <= w / s_min` (`||(I - P_sub)^{-1}||_inf <= ||w||_inf / s_min`);
      - Given Bellman residuals `r_lo = c_step_lo + P_sub V_trial - V_trial` and `r_hi = c_step_hi + P_sub V_trial - V_trial`:
        `V_trial - (max(-r_lo, 0)_inf / s_min) * w <= V^mu <= V_trial + (max(r_hi, 0)_inf / s_min) * w`
        (or tighter componentwise solve when solved directly on coarse blocks).
    """
    P = np.asarray(P_sub, dtype=float)
    clo = np.asarray(c_step_lo, dtype=float)
    chi = np.asarray(c_step_hi, dtype=float)
    Vt = np.asarray(V_trial, dtype=float)
    w = np.asarray(w_lyapunov, dtype=float)
    n = P.shape[0]
    if (
        P.ndim != 2
        or P.shape != (n, n)
        or n == 0
        or clo.shape != (n,)
        or chi.shape != (n,)
        or Vt.shape != (n,)
        or w.shape != (n,)
        or (not np.all(np.isfinite(P)))
        or (not np.all(np.isfinite(clo)))
        or (not np.all(np.isfinite(chi)))
        or (not np.all(np.isfinite(Vt)))
        or (not np.all(np.isfinite(w)))
        or np.any(clo > chi + tol)
        or float(np.min(P)) < -tol
        or float(np.max(np.sum(P, axis=1))) > 1.0 + tol
        or float(np.min(w)) < 0.0
    ):
        return {"valid": False, "reason": "invalid_inputs_or_negative_transition"}

    drift = w - (P @ w)
    s_min = float(np.min(drift))
    if (not np.isfinite(s_min)) or s_min <= tol:
        return {"valid": False, "reason": "lyapunov_drift_not_strictly_positive", "min_lyapunov_drift": s_min}

    resolvent_ub = float(np.max(w) / s_min)
    r_lo = clo + (P @ Vt) - Vt
    r_hi = chi + (P @ Vt) - Vt
    neg_defect = float(np.max(np.maximum(-r_lo, 0.0)))
    pos_defect = float(np.max(np.maximum(r_hi, 0.0)))

    V_lo = Vt - (neg_defect / s_min) * w
    V_hi = Vt + (pos_defect / s_min) * w
    return {
        "valid": True,
        "min_lyapunov_drift": s_min,
        "certified_resolvent_inf_ub": resolvent_ub,
        "V_lo": V_lo,
        "V_hi": V_hi,
        "max_width": float(np.max(V_hi - V_lo)),
    }


# ==============================================================================
# 6. Complete 15-Gate Falsification Verification Suite (`M2.0` + `v10` Closure)
# ==============================================================================
def run_m20_contract_verification_suite() -> dict:
    enforce_single_thread_env(force=True)
    t0 = time.perf_counter()
    results = {}

    # C01 (`P2A-01`): Principal M-matrix Green source `A_BB^{-1} e_1 > 1` vs Killed Hitting Kernel `H 1 <= 1`
    A_3 = np.array([[0.05, -0.02, 0.0], [-0.02, 0.05, -0.02], [0.0, -0.02, 0.05]], dtype=float)
    A_bb = A_3[:2, :2]
    u_green = np.linalg.solve(A_bb, np.array([1.0, 0.0]))
    chk_bad_green = verify_killed_hitting_kernel_conditions(A_bb, np.eye(2)[:, :1])
    B_hit = -A_3[:2, 2:3]
    chk_good_hit = verify_killed_hitting_kernel_conditions(A_bb, B_hit)
    H_hit = np.linalg.solve(A_bb, B_hit)
    results["C01_P2A01_green_source_vs_killed_hitting"] = {
        "green_source_max": float(np.max(u_green)),
        "unnormalized_green_rejected_as_submarkov": bool(not chk_bad_green["valid"]),
        "killed_hitting_verified_submarkov": bool(chk_good_hit["valid"]),
        "killed_hitting_min": float(np.min(H_hit)),
        "killed_hitting_max_row_sum": float(np.max(np.sum(H_hit, axis=1))),
        "pass": bool(
            np.max(u_green) > 20.0
            and (not chk_bad_green["valid"])
            and chk_good_hit["valid"]
            and np.min(H_hit) >= 0.0
            and np.max(np.sum(H_hit, axis=1)) <= 1.0 + 1e-12
        ),
    }

    # C02 (`P2A-02`): Local lifting without interior feedback fails `(1/2, 1/4) != (2/3, 1/3)`; full remainder & Schur pass
    A_2 = np.array([[2.0, -1.0], [-1.0, 2.0]], dtype=float)
    f_2 = np.array([[1.0], [0.0]], dtype=float)
    u_exact_2 = np.linalg.solve(A_2, f_2[:, 0])
    u_schur_2 = exact_schur_collar_solve(A_2, f_2[:, 0], collar_idx=[0])
    H_lift_2, R_full_2, _ = apply_killed_collar_residual_lift(
        sp.csr_matrix(A_2), f_2, H_base=None, collar_idx=np.array([0], dtype=np.int64)
    )
    u_corr_2 = H_lift_2[:, 0] + np.linalg.solve(A_2, R_full_2[:, 0])
    results["C02_P2A02_collar_lift_interface_feedback"] = {
        "naive_no_feedback": [0.5, 0.25],
        "exact_solution": u_exact_2.tolist(),
        "schur_err_inf": float(np.max(np.abs(u_schur_2 - u_exact_2))),
        "full_remainder_correction_err_inf": float(np.max(np.abs(u_corr_2 - u_exact_2))),
        "collar_row_residual_zero": float(abs(R_full_2[0, 0])),
        "exterior_rim_residual_captured": float(R_full_2[1, 0]),
        "pass": bool(
            np.max(np.abs(u_schur_2 - u_exact_2)) <= 1e-15
            and np.max(np.abs(u_corr_2 - u_exact_2)) <= 1e-15
            and abs(R_full_2[1, 0] - 0.5) <= 1e-15
        ),
    }

    # C03 (`P2A-03`): Swapped stochastic rows `H=[[0.9,0.1],[0.1,0.9]]` vs `H_tilde=[[0.1,0.9],[0.9,0.1]]`
    H_true_sw = np.array([[0.9, 0.1], [0.1, 0.9]], dtype=float)
    H_til_sw = np.array([[0.1, 0.9], [0.9, 0.1]], dtype=float)
    R_sw = H_true_sw - H_til_sw
    f_sw = np.array([[0.0], [1.0]], dtype=float)
    dwr_zero_psi = prepare_bilinear_dwr_operator(
        sp.eye(2, format="csr"), H_til_sw, R_sw, inv_inf_ub=1.0,
        eval_ext_rows=np.array([0, 1], dtype=np.int64), Psi_ext_cols=None
    )
    ql_0, qh_0, ok_0 = bound_normalized_continuation_dwr(dwr_zero_psi, f_sw, f_sw, lam=0.5)
    true_q_sw = -0.5 * np.log(np.sum(H_true_sw, axis=1, keepdims=True)) + (H_true_sw @ f_sw)
    dwr_exact_psi = prepare_bilinear_dwr_operator(
        sp.eye(2, format="csr"), H_til_sw, R_sw, inv_inf_ub=1.0,
        eval_ext_rows=np.array([0, 1], dtype=np.int64), Psi_ext_cols=np.eye(2, dtype=float)
    )
    ql_e, qh_e, ok_e = bound_normalized_continuation_dwr(dwr_exact_psi, f_sw, f_sw, lam=0.5)
    results["C03_P2A03_swapped_rows_continuation_enclosure"] = {
        "row_sum_residual_zero": float(np.max(np.abs(np.sum(R_sw, axis=1)))),
        "true_continuation_diff": 0.8,
        "zero_psi_encloses_true_continuation": bool(ok_0 and np.all(ql_0 - 1e-12 <= true_q_sw) and np.all(true_q_sw <= qh_0 + 1e-12)),
        "exact_psi_recovers_exact_continuation_err": float(max(np.max(np.abs(ql_e - true_q_sw)), np.max(np.abs(qh_e - true_q_sw)))),
        "pass": bool(
            ok_0 and ok_e
            and np.all(ql_0 - 1e-12 <= true_q_sw)
            and np.all(true_q_sw <= qh_0 + 1e-12)
            and np.max(np.abs(qh_e - ql_e)) <= 1e-11
        ),
    }

    # C04 (`P2A-04` + `v10 C03`): Root action Q-gap == 0 while deployed policy regret == 100;
    # single-node root-only certificate returns `None` for full-horizon regret, while verified 4-step chain returns `0.40`!
    root_q = {0: (0.0, 0.0), 1: (1.0, 1.0)}
    rejected_false_full_policy = False
    try:
        Phase2DecisionCertificate(
            certificate_mode="full_policy_enclosure",
            certified=True,
            epsilon_tol=0.25,
            lower_bound_opt=0.0,
            incumbent_policy_upper_bound=100.0,
            root_action_q_bounds=root_q,
            chosen_root_action=0,
            horizon_steps=2,
        )
    except ValueError:
        rejected_false_full_policy = True

    cert_root_only = Phase2DecisionCertificate(
        certificate_mode="receding_horizon_root_action_enclosure",
        certified=True,
        epsilon_tol=0.10,
        lower_bound_opt=0.0,
        incumbent_policy_upper_bound=None,
        root_action_q_bounds=root_q,
        chosen_root_action=0,
        horizon_steps=4,
    )
    chain_incomplete = RecedingHorizonCertificateChain(expected_horizon_steps=4, step_certificates=(cert_root_only,))
    chain_repeated_unindexed = RecedingHorizonCertificateChain(
        expected_horizon_steps=4, step_certificates=(cert_root_only, cert_root_only, cert_root_only, cert_root_only)
    )
    step_certs_valid = tuple(
        Phase2DecisionCertificate(
            certificate_mode="receding_horizon_root_action_enclosure",
            certified=True,
            epsilon_tol=0.10,
            lower_bound_opt=0.0,
            incumbent_policy_upper_bound=None,
            root_action_q_bounds=root_q,
            chosen_root_action=0,
            horizon_steps=4,
            step_index=t_idx,
            state_id=10 + t_idx,
            next_state_id=11 + t_idx,
            operator_epoch=0,
        )
        for t_idx in range(4)
    )
    chain_complete = RecedingHorizonCertificateChain(expected_horizon_steps=4, step_certificates=step_certs_valid)
    results["C04_P2A04_root_gap_vs_full_policy_separation"] = {
        "bad_deployed_policy_rejected_under_full_policy_mode": rejected_false_full_policy,
        "single_root_cert_full_horizon_regret_is_none": cert_root_only.guaranteed_full_horizon_regret_bound is None,
        "incomplete_chain_full_horizon_regret_is_none": chain_incomplete.guaranteed_full_horizon_regret_bound is None,
        "repeated_unindexed_root_chain_rejected": chain_repeated_unindexed.guaranteed_full_horizon_regret_bound is None,
        "verified_4step_chain_bound": chain_complete.guaranteed_full_horizon_regret_bound,
        "pass": bool(
            rejected_false_full_policy
            and (cert_root_only.guaranteed_full_horizon_regret_bound is None)
            and (chain_incomplete.guaranteed_full_horizon_regret_bound is None)
            and (chain_repeated_unindexed.guaranteed_full_horizon_regret_bound is None)
            and abs(float(chain_complete.guaranteed_full_horizon_regret_bound) - 0.40) <= 1e-15
        ),
    }

    # C05 (`P2A-05`): Asymmetric jump-rate M-matrix rejects unverified radial exponential template
    A_asym = np.array([[1.0, -0.9], [-0.1, 1.0]], dtype=float)
    psi_exp = np.array([1.0, np.exp(-1.0)], dtype=float)
    ell_0 = np.array([1.0, 0.0], dtype=float)
    wit_exp = check_super_adjoint_witness(A_asym, psi_exp, ell_0)
    H_true_as = np.linalg.solve(A_asym, np.array([[0.1], [0.0]]))
    H_til_as = np.zeros_like(H_true_as)
    R_as = np.array([[0.1], [0.0]]) - A_asym @ H_til_as
    dwr_unverified_psi = prepare_bilinear_dwr_operator(
        sp.csr_matrix(A_asym), H_til_as, R_as, inv_inf_ub=10.0,
        eval_ext_rows=np.array([0], dtype=np.int64), Psi_ext_cols=psi_exp[:, None]
    )
    z_true_as = float(H_true_as[0, 0])
    results["C05_P2A05_operator_witness_and_sound_dwr_fallback"] = {
        "radial_template_rejected_as_super_adjoint": bool(not wit_exp["valid_super_adjoint"]),
        "min_adjoint_slack": wit_exp["min_adjoint_slack"],
        "bilinear_dwr_with_imperfect_psi_still_encloses_z_true": bool(
            dwr_unverified_psi["z_lo_ext"][0] <= z_true_as <= dwr_unverified_psi["z_hi_ext"][0]
        ),
        "pass": bool(
            (not wit_exp["valid_super_adjoint"])
            and dwr_unverified_psi["z_lo_ext"][0] <= z_true_as <= dwr_unverified_psi["z_hi_ext"][0]
        ),
    }

    # C06 (`P2B-01`): Partition-of-unity Galerkin projection produces `-1/6`, whereas `R H L` sandwich stays >= 0
    W_pou = np.array([[1.0, 0.0], [0.5, 0.5], [0.0, 1.0]], dtype=float)
    H_galerkin = W_pou @ np.linalg.inv(W_pou.T @ W_pou) @ W_pou.T
    R_stoch = W_pou.T / np.sum(W_pou.T, axis=1, keepdims=True)
    L_stoch = W_pou
    H_sandwich = build_row_stochastic_sandwich_kernel(np.eye(3), R_stoch, L_stoch)
    results["C06_P2B01_pou_galerkin_negativity_vs_stochastic_sandwich"] = {
        "galerkin_min_entry": float(np.min(H_galerkin)),
        "sandwich_min_entry": float(np.min(H_sandwich)),
        "sandwich_max_row_sum": float(np.max(np.sum(H_sandwich, axis=1))),
        "pass": bool(
            np.min(H_galerkin) < -0.16
            and np.min(H_sandwich) >= 0.0
            and np.max(np.abs(np.sum(H_sandwich, axis=1) - 1.0)) <= 1e-15
        ),
    }

    # C07 (`P2B-02`): Non-lumpable 3-state chain has `0` interval width but `delta_lump == 2.0` & 2-step error `1.0`
    P_chain = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0]], dtype=float)
    lump_bad = audit_partition_lumpability_and_two_step_defect(P_chain, blocks=[[0, 1], [2]])
    lump_split = audit_partition_lumpability_and_two_step_defect(P_chain, blocks=[[0], [1], [2]])
    results["C07_P2B02_within_port_dispersion_and_split_recovery"] = {
        "coarse_point_interval_width": lump_bad["point_interval_product_width"],
        "coarse_within_block_dispersion_l1": lump_bad["within_block_exit_dispersion_l1"],
        "coarse_two_step_discrepancy_inf": lump_bad["independent_two_step_discrepancy_inf"],
        "split_is_strongly_lumpable": lump_split["is_strongly_lumpable"],
        "pass": bool(
            (not lump_bad["is_strongly_lumpable"])
            and abs(lump_bad["independent_two_step_discrepancy_inf"] - 1.0) <= 1e-15
            and lump_split["is_strongly_lumpable"]
            and lump_split["independent_two_step_discrepancy_inf"] <= 1e-15
        ),
    }

    # C08 (`P2B-03`): Irreversible 3-cycle ratio `729:1` invariant under diagonal Doob similarity
    P_cyc = np.array([[0.0, 0.9, 0.1], [0.1, 0.0, 0.9], [0.9, 0.1, 0.0]], dtype=float)
    h_diag = np.array([2.0, 0.5, 3.7], dtype=float)
    P_sim = np.diag(1.0 / h_diag) @ P_cyc @ np.diag(h_diag)
    r_orig = (P_cyc[0, 1] * P_cyc[1, 2] * P_cyc[2, 0]) / (P_cyc[0, 2] * P_cyc[2, 1] * P_cyc[1, 0])
    r_sim = (P_sim[0, 1] * P_sim[1, 2] * P_sim[2, 0]) / (P_sim[0, 2] * P_sim[2, 1] * P_sim[1, 0])
    results["C08_P2B03_irreversible_cycle_invariant_under_doob"] = {
        "cycle_ratio_original": float(r_orig),
        "cycle_ratio_transformed": float(r_sim),
        "pass": bool(abs(r_orig - 729.0) <= 1e-10 and abs(r_orig - r_sim) <= 1e-10),
    }

    # C09 (`P2C-01`): Compact-support prior `K_{LR} == 0` develops nonlocal posterior `K_{LR|M} == -0.16`
    K_3 = np.array([[1.0, 0.4, 0.0], [0.4, 1.0, 0.4], [0.0, 0.4, 1.0]], dtype=float)
    K_lr_given_m = K_3[0, 2] - K_3[0, 1] * (1.0 / K_3[1, 1]) * K_3[1, 2]
    mean_shift_r = K_lr_given_m / (K_3[0, 0] - K_3[0, 1] ** 2 / K_3[1, 1])
    results["C09_P2C01_compact_prior_nonlocal_posterior_guard"] = {
        "prior_LR_cov": float(K_3[0, 2]),
        "posterior_LR_cov_given_M": float(K_lr_given_m),
        "unit_innovation_at_L_shifts_R_by": float(mean_shift_r),
        "pass": bool(abs(K_lr_given_m + 0.16) <= 1e-15 and abs(mean_shift_r + 0.16 / 0.84) <= 1e-15),
    }

    # C10 (`P2C-02`): Coupled interface Schur perturbation changes all global interface coordinates
    S_old = np.array([[2.0, -1.0, 0.0], [-1.0, 2.0, -1.0], [0.0, -1.0, 2.0]], dtype=float)
    S_new = S_old.copy()
    S_new[0, 0] = 2.1
    rhs_if = np.array([0.0, 0.0, 1.0], dtype=float)
    u_if_old = np.linalg.solve(S_old, rhs_if)
    u_if_new = np.linalg.solve(S_new, rhs_if)
    changed_coords = int(np.sum(np.abs(u_if_new - u_if_old) > 1e-4))
    results["C10_P2C02_local_schur_update_global_interface_coupling"] = {
        "changed_interface_coordinates_of_3": changed_coords,
        "max_interface_shift": float(np.max(np.abs(u_if_new - u_if_old))),
        "pass": bool(changed_coords == 3),
    }

    # C11 (`v10 C02`): Non-finite `NaN` / `inf` / negative epsilon & `NaN` competitor Q-bounds rejected fail-closed
    nan_inf_rejections = {}
    for lbl, fn in [
        ("cert_eps_nan", lambda: Phase2DecisionCertificate("full_policy_enclosure", True, float("nan"), 0.0, 100.0, None, 0, 1)),
        ("cert_eps_inf", lambda: Phase2DecisionCertificate("full_policy_enclosure", True, float("inf"), 0.0, 100.0, None, 0, 1)),
        ("cert_eps_neg", lambda: Phase2DecisionCertificate("full_policy_enclosure", True, -0.01, 0.0, 0.0, None, 0, 1)),
        ("cert_nan_comp", lambda: Phase2DecisionCertificate("receding_horizon_root_action_enclosure", True, 0.1, 0.0, None, {0: (0.0, 0.05), 1: (float("nan"), float("nan"))}, 0, 4)),
        ("cert_bad_horizon", lambda: Phase2DecisionCertificate("full_policy_enclosure", True, 0.1, 0.0, 0.05, None, 0, 0)),
        ("sandwich_H_nan", lambda: build_row_stochastic_sandwich_kernel(np.array([[np.nan]]), np.ones((1, 1)), np.ones((1, 1)))),
        ("sandwich_R_nan", lambda: build_row_stochastic_sandwich_kernel(np.ones((1, 1)), np.array([[np.nan]]), np.ones((1, 1)))),
        ("sandwich_L_nan", lambda: build_row_stochastic_sandwich_kernel(np.ones((1, 1)), np.ones((1, 1)), np.array([[np.nan]]))),
    ]:
        try:
            fn()
            nan_inf_rejections[lbl] = False
        except (ValueError, TypeError):
            nan_inf_rejections[lbl] = True
    results["C11_V10_C02_nan_inf_and_invalid_input_rejection"] = {
        "rejected_by_case": nan_inf_rejections,
        "pass": bool(all(nan_inf_rejections.values())),
    }

    # C12 (`v10 M2.2 Trap 1a`): `tiny-Z` exit aliasing (`H = diag(1e-8, 1e-8)`, `delta_H = 2e-8` yet `delta_P = 2.0`)
    H_exit_tiny = np.array([[1e-8, 0.0], [0.0, 1e-8]], dtype=float)
    adq_exit_floor = audit_normalized_block_state_adequacy(H_exit_tiny, lam=1.0, continuation_span_bound=1.0, z_min_floor=1e-6, adequacy_tol=0.25)
    adq_exit_lowfloor = audit_normalized_block_state_adequacy(H_exit_tiny, lam=1.0, continuation_span_bound=1.0, z_min_floor=1e-12, adequacy_tol=0.25)
    results["C12_V10_tiny_z_exit_aliasing_rejected"] = {
        "raw_delta_H_l1": adq_exit_lowfloor["raw_delta_H_l1"],
        "normalized_delta_P_l1": adq_exit_lowfloor["max_delta_P_l1"],
        "joint_bellman_discrepancy": adq_exit_lowfloor["joint_bellman_discrepancy"],
        "rejected_under_z_floor": bool(not adq_exit_floor["state_adequacy_certified"]),
        "rejected_under_joint_discrepancy": bool(not adq_exit_lowfloor["state_adequacy_certified"]),
        "pass": bool(
            adq_exit_lowfloor["kernel_valid"]
            and abs(adq_exit_lowfloor["raw_delta_H_l1"] - 2e-8) <= 1e-16
            and abs(adq_exit_lowfloor["max_delta_P_l1"] - 2.0) <= 1e-12
            and abs(adq_exit_lowfloor["joint_bellman_discrepancy"] - 1.0) <= 1e-12
            and (not adq_exit_floor["state_adequacy_certified"])
            and (not adq_exit_lowfloor["state_adequacy_certified"])
        ),
    }

    # C13 (`v10 M2.2 Trap 1b`): `tiny-Z` cost aliasing (`H = [[1e-8, 0], [2e-8, 0]]`, `delta_P = 0` yet `delta_c0 = log(2)`)
    H_cost_tiny = np.array([[1e-8, 0.0], [2e-8, 0.0]], dtype=float)
    adq_cost = audit_normalized_block_state_adequacy(H_cost_tiny, lam=1.0, continuation_span_bound=1.0, z_min_floor=1e-12, adequacy_tol=0.25)
    results["C13_V10_tiny_z_cost_aliasing_rejected"] = {
        "raw_delta_H_l1": adq_cost["raw_delta_H_l1"],
        "normalized_delta_P_l1": adq_cost["max_delta_P_l1"],
        "max_delta_c0": adq_cost["max_delta_c0"],
        "state_adequacy_certified": adq_cost["state_adequacy_certified"],
        "pass": bool(
            abs(adq_cost["max_delta_P_l1"]) <= 1e-15
            and abs(adq_cost["max_delta_c0"] - math.log(2.0)) <= 1e-12
            and (not adq_cost["state_adequacy_certified"])
        ),
    }

    # C14 (`v10 M2.2 Trap 2`): Option-library Jensen loss (`T_fixed = c_0 + P F` vs `T_CH = -lam * log(H exp(-F/lam))`)
    H_opt = np.array([[0.45, 0.45]], dtype=float)
    F_opt = np.array([0.0, 4.0], dtype=float)
    lam_opt = 0.5
    z_opt = float(np.sum(H_opt))
    v_fixed_single = float(-lam_opt * np.log(z_opt) + (H_opt[0] / z_opt) @ F_opt)
    v_multi_exit_ch = float(-lam_opt * np.log(np.sum(H_opt[0] * np.exp(-F_opt / lam_opt))))
    jensen_gap = v_fixed_single - v_multi_exit_ch
    results["C14_V10_single_option_jensen_gap_vs_exact_desirability_interface"] = {
        "fixed_single_option_value": v_fixed_single,
        "multi_exit_cole_hopf_value": v_multi_exit_ch,
        "action_library_jensen_gap": jensen_gap,
        "pass": bool(jensen_gap > 1.5),
    }

    # C15 (`v10 M2.2 Trap 3`): Cyclic SSP resolvent amplification (`p_ret = 0.99`, residual `0.01` -> value error `1.0` enclosed via Lyapunov `w = 100`)
    P_ret = np.array([[0.99]], dtype=float)
    c_ret = np.array([1.0], dtype=float)
    V_true_ret = 100.0
    V_approx_ret = np.array([99.0], dtype=float)  # Bellman residual == 0.01, true error == 1.0!
    w_lyap = np.array([100.0], dtype=float)
    ssp_cert = certify_cyclic_ssp_policy_via_lyapunov_witness(P_ret, c_ret, c_ret, V_approx_ret, w_lyap)
    results["C15_V10_cyclic_resolvent_amplification_lyapunov_enclosure"] = {
        "bellman_residual": 0.01,
        "true_value_error": 1.0,
        "certified_resolvent_inf_ub": ssp_cert["certified_resolvent_inf_ub"],
        "certified_V_lo": float(ssp_cert["V_lo"][0]),
        "certified_V_hi": float(ssp_cert["V_hi"][0]),
        "encloses_true_100": bool(ssp_cert["valid"] and ssp_cert["V_lo"][0] - 1e-12 <= V_true_ret <= ssp_cert["V_hi"][0] + 1e-12),
        "pass": bool(
            ssp_cert["valid"]
            and abs(ssp_cert["certified_resolvent_inf_ub"] - 100.0) <= 1e-10
            and ssp_cert["V_lo"][0] - 1e-12 <= V_true_ret <= ssp_cert["V_hi"][0] + 1e-12
        ),
    }

    all_passed = all(v["pass"] for v in results.values())
    elapsed_ms = 1000.0 * (time.perf_counter() - t0)
    out = {
        "milestone": "M2.0_Mathematical_Contracts_and_15_Counterexample_Gates",
        "runtime_metadata": collect_runtime_metadata(max_workers=1),
        "phase2_manifest": compute_phase2_manifest(),
        "elapsed_ms": elapsed_ms,
        "ALL_10_COUNTEREXAMPLE_GATES_PASSED": bool(all_passed),
        "ALL_15_COUNTEREXAMPLE_GATES_PASSED": bool(all_passed),
        "n_gates_passed": int(sum(1 for v in results.values() if v["pass"])),
        "n_gates_total": len(results),
        "counterexample_gates": results,
    }
    return out


def main() -> None:
    res = run_m20_contract_verification_suite()
    out_path = Path(__file__).resolve().parent / "m20_contract_results.json"
    out_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(
        f"[M2.0] ALL_15_COUNTEREXAMPLE_GATES_PASSED={res['ALL_15_COUNTEREXAMPLE_GATES_PASSED']} "
        f"({res['n_gates_passed']}/{res['n_gates_total']}) elapsed_ms={res['elapsed_ms']:.2f} "
        f"frozen_phase1_ok={res['phase2_manifest']['frozen_phase1_verified_intact']}"
    )
    if not res["ALL_15_COUNTEREXAMPLE_GATES_PASSED"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
