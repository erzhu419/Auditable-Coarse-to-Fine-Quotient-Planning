"""Milestone M2.0 (`quotient_phase2.m20_contracts`):
Mathematical Object Separation (`U, H, Z, P`), Killed-Collar Lifting with Full Interface Feedback,
Operator-Verified Bilinear Primal-Dual (DWR) Functional Enclosures (`Hf` & `H1`), Non-Interchangeable
Full-Policy vs. Root-Action Certificates, Row-Stochastic `R H L` Sandwich & Lumpability Diagnostics,
and the 10-Counterexample Falsification Regression Suite (`P2A-01..05`, `P2B-01..04`, `P2C-01..02`).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import json
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

from green_response.core import collect_runtime_metadata, enforce_single_thread_env
from quotient_phase2 import compute_phase2_manifest


# ==============================================================================
# 1. Four-Object Separation & Killed Hitting Kernel Contract (`P2A-01`)
# ==============================================================================
def verify_killed_hitting_kernel_conditions(
    A_ii: sp.spmatrix | np.ndarray,
    B_ig: sp.spmatrix | np.ndarray,
    tol: float = 1e-12,
) -> dict:
    """Verifies sufficient M-matrix conditions guaranteeing `H = A_{II}^{-1} B >= 0` and `H 1 <= 1`:
      1. `A_{II}` has positive diagonal and non-positive off-diagonals (`<= tol`);
      2. `B >= -tol` entrywise;
      3. `A_{II} 1 - B 1 >= q_min_eff > 0` (`1 - H 1 = A_{II}^{-1}(A_{II} 1 - B 1) >= 0`).
    Explicitly distinguishes `KilledHittingKernel` from unbounded `GreenSourceResponse` (`A^{-1} E_Gamma`).
    """
    A_csr = sp.csr_matrix(A_ii, dtype=float)
    B_arr = B_ig.toarray() if sp.issparse(B_ig) else np.asarray(B_ig, dtype=float)
    if B_arr.ndim == 1:
        B_arr = B_arr[:, None]
    n_i, n_j = A_csr.shape
    if n_i != n_j or B_arr.shape[0] != n_i:
        return {"valid": False, "reason": "shape_mismatch", "min_row_excess": None, "inv_inf_ub": None}

    diag = A_csr.diagonal()
    if np.any(~np.isfinite(diag)) or np.any(diag <= tol):
        return {"valid": False, "reason": "nonpositive_diagonal", "min_row_excess": None, "inv_inf_ub": None}

    A_off = A_csr - sp.diags(diag, format="csr")
    max_off = float(A_off.max()) if A_off.nnz > 0 else 0.0
    if max_off > tol:
        return {"valid": False, "reason": "positive_off_diagonal_not_z_matrix", "min_row_excess": None, "inv_inf_ub": None}

    if np.any(~np.isfinite(B_arr)) or float(np.min(B_arr)) < -tol:
        return {"valid": False, "reason": "negative_boundary_rhs", "min_row_excess": None, "inv_inf_ub": None}

    a_row_sum = np.asarray(A_csr @ np.ones(n_i, dtype=float)).ravel()
    b_row_sum = np.sum(B_arr, axis=1)
    min_a_row = float(np.min(a_row_sum))
    row_excess = a_row_sum - b_row_sum
    min_excess = float(np.min(row_excess))

    if min_a_row <= tol:
        return {"valid": False, "reason": "nonpositive_A_row_sum", "min_row_excess": min_excess, "inv_inf_ub": None}

    submarkov_guaranteed = bool(min_excess >= -tol)
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
) -> Tuple[np.ndarray, np.ndarray, spla.SuperLU]:
    """Applies local principal M-matrix collar correction `A_{CC} dH_C = R_base[C, :]`, zero-extends to `I_b`,
    and evaluates the **exact full-exterior residual** `R_full = B_ig - A_{II} H_lifted` across ALL of `I_b`
    (retaining 100% interior-exterior feedback, closing `P2A-02`).
    When `H_base is None` (unseen target) and `(A_{II}, B_ig)` satisfies `verify_killed_hitting_kernel_conditions`,
    `0 <= H_lifted` and `H_lifted @ 1 <= 1` hold identically without clipping (`P2A-01`).
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
    # Mandatory interior back-substitution (`u_B = A_BB^{-1}(f_B - A_BC u_C)`):
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
    """Explicitly verifies `psi_trial >= 0` and `A_{II}^T psi_trial >= ell_rhs` componentwise (`P2A-05`).
    Rejects unverified analytical/exponential templates whenever any component violates `>= -tol`.
    """
    A_csr = sp.csr_matrix(A_ii, dtype=float)
    psi = np.asarray(psi_trial, dtype=float)
    ell = np.asarray(ell_rhs, dtype=float)
    slack = (A_csr.T @ psi) - ell
    min_psi = float(np.min(psi))
    min_slack = float(np.min(slack))
    valid = bool(np.all(np.isfinite(psi)) and np.all(np.isfinite(slack)) and min_psi >= -tol and min_slack >= -tol)
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
    """Prepares row-localized Bilinear Primal-Dual (DWR) functional bounds on `eval_ext_rows subset I_b`:
      - If `Psi_ext_cols is None` (`psi == 0` special case = Primal Uniform Auditor):
          `H_corr = H_tilde[eval_ext_rows, :]`, `alpha_row = inv_inf_ub * 1.0`.
      - If `Psi_ext_cols` (`shape = (|I_b|, |eval_ext_rows|)`) is provided:
          1. Computes exact current-operator adjoint residual `Delta_adj = E_eval - A_{II}^T @ Psi_ext_cols`;
          2. Sets `alpha_row[r] = inv_inf_ub * ||Delta_adj[:, r]||_1`;
          3. Sets `H_corr = H_tilde[eval_ext_rows, :] + Psi_ext_cols.T @ R_full`.
      - Stores BOTH `rho_row_sum = ||R_full @ 1||_inf` (for denominator `Z = H 1`) AND per-column
        `r_col_inf[j] = ||R_full[:, j]||_inf` (for arbitrary continuation `N_f = H (f - c 1)`, closing `P2A-03`).
    """
    r_col_inf = np.max(np.abs(R_full), axis=0)
    rho_1 = float(np.max(np.abs(np.sum(R_full, axis=1)))) if R_full.size > 0 else 0.0
    n_ev_ext = len(eval_ext_rows)

    if Psi_ext_cols is None or n_ev_ext == 0:
        H_corr = H_tilde[eval_ext_rows, :].copy()
        alpha_row = np.full(n_ev_ext, float(inv_inf_ub), dtype=float)
        max_delta_l1 = 1.0 if n_ev_ext > 0 else 0.0
    else:
        AT_Psi = A_ii_csr.T @ Psi_ext_cols
        # Subtract 1.0 at `(eval_ext_rows[k], k)` without allocating dense `|I_b| x |P|` identity if sparse,
        # here `AT_Psi` is dense `(|I_b|, n_ev_ext)`:
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
) -> Tuple[np.ndarray, np.ndarray, bool]:
    """Bounds `c0_b + P_b F_ring = -lam * log(Z_b) + (H_b F_ring) / Z_b` across batch columns `(m_ring, K)`
    covering BOTH numerator `H_b(F - mu)` AND denominator `Z_b = H_b 1` (`P2A-03` closed!).
    Uses monotonicity of the exact non-negative hitting measure `P_b^* >= 0`:
      - Lower bound evaluates fixed centered vector `g_lo = F_ring_lo - mu_lo`;
      - Upper bound evaluates fixed centered vector `g_hi = F_ring_hi - mu_hi` whenever `z_lo > 1e-15`
        and `F_ring_hi` is finite on all ring nodes; if `z_lo <= 1e-15` and `allow_extended_inf_upper=True`,
        returns valid finite `Q_lo` and `Q_hi = +inf` (allowing same-state dominated-branch pruning without
        ever certifying an unverified leg on the active policy tree!).
    """
    if F_ring_lo.ndim == 1:
        F_ring_lo = F_ring_lo[:, None]
        F_ring_hi = F_ring_hi[:, None]

    if np.any(np.isnan(F_ring_lo)) or np.any(np.isnan(F_ring_hi)) or np.any(F_ring_lo > F_ring_hi):
        return F_ring_lo, F_ring_hi, False

    H_corr = dwr_op["H_corr"]
    alpha = dwr_op["alpha_row"][:, None]
    r_col_inf = dwr_op["r_col_inf"]
    z_lo = dwr_op["z_lo_ext"][:, None]
    z_hi = dwr_op["z_hi_ext"][:, None]
    n_rows = H_corr.shape[0]
    n_cols = F_ring_lo.shape[1]

    if np.any(~np.isfinite(z_hi)) or np.any(z_hi <= 1e-285):
        return np.empty((n_rows, n_cols)), np.empty((n_rows, n_cols)), False

    pos_ok = z_lo > 1e-15
    if (not allow_extended_inf_upper) and (not np.all(pos_ok)):
        return np.empty((n_rows, n_cols)), np.empty((n_rows, n_cols)), False

    # 1. Lower bound (always finite since `F_ring_lo` and `-lam * log(z_hi)` are finite!)
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

    # 2. Upper bound (finite where `pos_ok` AND column `F_ring_hi` is all-finite, else `+inf`)
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

    valid = bool(np.all(np.isfinite(out_lo)) and np.all(out_lo <= out_hi + 1e-11))
    out_hi = np.maximum(out_lo, out_hi)
    return out_lo, out_hi, valid


# ==============================================================================
# 4. Full-Policy vs. Root-Action Certificate Separation (`P2A-04`)
# ==============================================================================
@dataclass(frozen=True)
class Phase2DecisionCertificate:
    """Strictly separates `full_policy_enclosure` (`U^mu(s0) - min_a L_a^*(s0) <= eps`) from
    `receding_horizon_root_action_enclosure` (`max_{a != a_hat} [U_{a_hat}^* - L_a^*]_+ <= eta`,
    with `m`-step horizon bound `m * eta`). Forbids substituting root-action gap for full-policy certification!
    """
    certificate_mode: str  # "full_policy_enclosure" | "receding_horizon_root_action_enclosure"
    certified: bool
    epsilon_tol: float
    lower_bound_opt: float
    incumbent_policy_upper_bound: Optional[float]
    root_action_q_bounds: Dict[int, Tuple[float, float]]
    chosen_root_action: int
    horizon_steps: int = 1

    def __post_init__(self) -> None:
        if self.certificate_mode not in ("full_policy_enclosure", "receding_horizon_root_action_enclosure"):
            raise ValueError(f"Invalid certificate_mode: {self.certificate_mode}")
        if not np.isfinite(self.lower_bound_opt):
            raise ValueError("lower_bound_opt must be finite")
        if self.certificate_mode == "full_policy_enclosure" and self.certified:
            if self.incumbent_policy_upper_bound is None or not np.isfinite(self.incumbent_policy_upper_bound):
                raise ValueError("full_policy_enclosure requires finite incumbent_policy_upper_bound")
            gap_pol = float(self.incumbent_policy_upper_bound - self.lower_bound_opt)
            if gap_pol > self.epsilon_tol + 1e-12 or gap_pol < -1e-11:
                raise ValueError(
                    f"full_policy_enclosure violated: policy_gap={gap_pol} vs epsilon_tol={self.epsilon_tol}"
                )
        if self.certificate_mode == "receding_horizon_root_action_enclosure" and self.certified:
            if self.chosen_root_action not in self.root_action_q_bounds:
                raise ValueError("chosen_root_action missing from root_action_q_bounds")
            u_hat = self.root_action_q_bounds[self.chosen_root_action][1]
            others = [v[0] for k, v in self.root_action_q_bounds.items() if k != self.chosen_root_action]
            root_gap = 0.0 if not others else max(0.0, float(u_hat - min(others)))
            if not np.isfinite(u_hat) or root_gap > self.epsilon_tol + 1e-12:
                raise ValueError(f"root_action_enclosure violated: root_gap={root_gap} vs tol={self.epsilon_tol}")

    @property
    def guaranteed_full_horizon_regret_bound(self) -> Optional[float]:
        if not self.certified:
            return None
        if self.certificate_mode == "full_policy_enclosure":
            return float(max(0.0, self.incumbent_policy_upper_bound - self.lower_bound_opt))
        # Receding-horizon step-eta only implies `m * eta` cumulative bound (`P2A-04`)!
        return float(self.horizon_steps * self.epsilon_tol)


# ==============================================================================
# 5. Convex `R H L` Sandwich & Lumpability Dispersion Contracts (`P2B-01..02`)
# ==============================================================================
def build_row_stochastic_sandwich_kernel(
    H_micro: np.ndarray,
    R_restrict: np.ndarray,
    L_lift: np.ndarray,
    tol: float = 1e-12,
) -> np.ndarray:
    """Constructs `H_bar = R @ H @ L` verifying `H >= 0, H 1 <= 1` and row-stochastic `R, L` (`P2B-01`)."""
    H = np.asarray(H_micro, dtype=float)
    R = np.asarray(R_restrict, dtype=float)
    L = np.asarray(L_lift, dtype=float)
    if np.min(H) < -tol or np.max(np.sum(H, axis=1)) > 1.0 + tol:
        raise ValueError("Micro kernel H must be non-negative sub-Markov (H >= 0, H 1 <= 1)")
    if np.min(R) < -tol or np.max(np.abs(np.sum(R, axis=1) - 1.0)) > tol:
        raise ValueError("Restriction R must be non-negative row-stochastic (R >= 0, R 1 = 1)")
    if np.min(L) < -tol or np.max(np.abs(np.sum(L, axis=1) - 1.0)) > tol:
        raise ValueError("Lifting L must be non-negative row-stochastic (L >= 0, L 1 = 1)")
    return R @ H @ L


def audit_partition_lumpability_and_two_step_defect(
    P_micro: np.ndarray,
    blocks: Sequence[Sequence[int]],
) -> dict:
    """Computes BOTH within-block exit-distribution dispersion `delta_lump` (strong lumpability defect)
    AND independent 2-step aggregation discrepancy `||R P^2 L - (R P L)^2||_inf`, cleanly separating
    Markovianity defect from interval product width (`P2B-02`).
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

    block_trans = P @ L  # (n, k_b): micro-state -> macro-block exit probabilities
    max_within_block_l1 = 0.0
    for blk in blocks:
        rows = block_trans[np.asarray(blk, dtype=np.int64), :]
        if len(rows) > 1:
            diffs = np.sum(np.abs(rows[:, None, :] - rows[None, :, :]), axis=2)
            max_within_block_l1 = max(max_within_block_l1, float(np.max(diffs)))

    Q_1 = build_row_stochastic_sandwich_kernel(P, R, L)
    Q_true_2 = R @ (P @ P) @ L
    Q_sq = Q_1 @ Q_1
    # Matrix operator infinity norm `||M||_inf = max_i sum_j |M_{ij}|`:
    two_step_err_inf = float(np.max(np.sum(np.abs(Q_true_2 - Q_sq), axis=1)))
    return {
        "within_block_exit_dispersion_l1": max_within_block_l1,
        "independent_two_step_discrepancy_inf": two_step_err_inf,
        "point_interval_product_width": 0.0,
        "is_strongly_lumpable": bool(max_within_block_l1 <= 1e-12),
    }


# ==============================================================================
# 6. Complete 10-Counterexample Verification Suite (`M2.0` Gate)
# ==============================================================================
def run_m20_contract_verification_suite() -> dict:
    enforce_single_thread_env(force=True)
    t0 = time.perf_counter()
    results = {}

    # C1 (`P2A-01`): Principal M-matrix Green source `A_BB^{-1} e_1 > 1` vs Killed Hitting Kernel `H 1 <= 1`
    A_3 = np.array([[0.05, -0.02, 0.0], [-0.02, 0.05, -0.02], [0.0, -0.02, 0.05]], dtype=float)
    A_bb = A_3[:2, :2]
    u_green = np.linalg.solve(A_bb, np.array([1.0, 0.0]))
    chk_bad_green = verify_killed_hitting_kernel_conditions(A_bb, np.eye(2)[:, :1])
    # Killed hitting kernel taking node 2 as absorbing Gamma (`I = {0, 1}`): `B = -A_{I, {2}} = [0, 0.02]^T`
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

    # C2 (`P2A-02`): Local lifting without interior feedback fails `(1/2, 1/4) != (2/3, 1/3)`; full remainder & Schur pass
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

    # C3 (`P2A-03`): Swapped stochastic rows `H=[[0.9,0.1],[0.1,0.9]]` vs `H_tilde=[[0.1,0.9],[0.9,0.1]]`
    H_true_sw = np.array([[0.9, 0.1], [0.1, 0.9]], dtype=float)
    H_til_sw = np.array([[0.1, 0.9], [0.9, 0.1]], dtype=float)
    R_sw = H_true_sw - H_til_sw  # `A_II = I_2`
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

    # C4 (`P2A-04`): Root action Q-gap == 0 while deployed policy regret == 100
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
    results["C04_P2A04_root_gap_vs_full_policy_separation"] = {
        "bad_deployed_policy_rejected_under_full_policy_mode": rejected_false_full_policy,
        "receding_horizon_4step_bound_scales_with_m": cert_root_only.guaranteed_full_horizon_regret_bound,
        "pass": bool(rejected_false_full_policy and abs(cert_root_only.guaranteed_full_horizon_regret_bound - 0.40) <= 1e-15),
    }

    # C5 (`P2A-05`): Asymmetric jump-rate M-matrix rejects unverified radial exponential template
    A_asym = np.array([[1.0, -0.9], [-0.1, 1.0]], dtype=float)
    psi_exp = np.array([1.0, np.exp(-1.0)], dtype=float)
    ell_0 = np.array([1.0, 0.0], dtype=float)
    wit_exp = check_super_adjoint_witness(A_asym, psi_exp, ell_0)
    # Bilinear DWR STILL produces valid sound enclosure even when given unverified `psi_exp` because it bills `||e_p - A^T psi||_1`!
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

    # C6 (`P2B-01`): Partition-of-unity Galerkin projection produces `-1/6`, whereas `R H L` sandwich stays >= 0
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

    # C7 (`P2B-02`): Non-lumpable 3-state chain has `0` interval width but `delta_lump == 2.0` & 2-step error `1.0`
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

    # C8 (`P2B-03`): Irreversible 3-cycle ratio `729:1` invariant under diagonal Doob similarity
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

    # C9 (`P2C-01`): Compact-support prior `K_{LR} == 0` develops nonlocal posterior `K_{LR|M} == -0.16`
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

    all_passed = all(v["pass"] for v in results.values())
    elapsed_ms = 1000.0 * (time.perf_counter() - t0)
    out = {
        "milestone": "M2.0_Mathematical_Contracts_and_10_Counterexample_Gates",
        "runtime_metadata": collect_runtime_metadata(max_workers=1),
        "phase2_manifest": compute_phase2_manifest(),
        "elapsed_ms": elapsed_ms,
        "ALL_10_COUNTEREXAMPLE_GATES_PASSED": bool(all_passed),
        "counterexample_gates": results,
    }
    return out


def main() -> None:
    res = run_m20_contract_verification_suite()
    out_path = Path(__file__).resolve().parent / "m20_contract_results.json"
    out_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(
        f"[M2.0] ALL_10_COUNTEREXAMPLE_GATES_PASSED={res['ALL_10_COUNTEREXAMPLE_GATES_PASSED']} "
        f"elapsed_ms={res['elapsed_ms']:.2f} frozen_phase1_ok={res['phase2_manifest']['frozen_phase1_verified_intact']}"
    )
    if not res["ALL_10_COUNTEREXAMPLE_GATES_PASSED"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
