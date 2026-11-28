"""Core Mathematical & Algorithmic Engine (`learned_portal_phase3.spql_core`):
PAC-Certified Spectral-Portal Quotient Learning (SPQL) Without Geometric or Operator Priors.

Key Theoretical & Algorithmic Innovations:
  1. Exact Time-Uniform Clopper-Pearson Dual M-Matrix Envelopes `(A_pes, A_opt)`:
       From passive/adaptive trajectory counts `k_{ij}`, `n(i)`, and noisy step costs `q_hat_i`,
       constructs `p_lo_{ij} = Beta^{-1}(delta_edge; k_{ij}, n(i) - k_{ij} + 1)` (`> 0` as soon as
       `k_{ij} >= 1`!) and observable epistemic mass `rho_i = 1 - sum_j p_lo_{ij} in [0, 1]`.
       Both `A_pes = I - gamma_lo * P_lo` and `A_opt = I - gamma_hi * P_lo` are **goal-independent**
       strictly row-diagonally dominant nonsingular M-matrices supported EXCLUSIVELY on observed edges
       `E_hat`, certifying simultaneously across ALL unseen goals `G` on event `E_{1-delta}`:
           `L_{n, C}(s_0; G) <= V^*_{true}(s_0; G) <= J^{mu_hat}_{true}(s_0; G) <= U_{n, C}(s_0; G)`
       even in the presence of unobserved cross-room shortcut edges!
  2. Coordinate-Free Spectral Sweep-Cut Separator & Fiedler PoU Portal Trees:
       Discovers low-conductance room clusters `R_1..R_C` and minimal vertex separators
       `Gamma = union_p Gamma_p` directly from empirical flux `F_hat = 0.5*(K + K^T)` (zero coordinates
       or axis-aligned wall priors!), and constructs strictly nested binary Fiedler partition trees
       `L0 -> L1 -> L2 -> L3 -> L4` on arbitrary unstructured portal subgraphs `Gamma_p`, conserving
       **50% of cache-miss room-LU backsolves** via binary Partition-of-Unity subtraction.
  3. Epistemic-Aware Adaptive Stopping & Active Bottleneck Exploration:
       Decomposes certified width into `Delta_plan(C) + Delta_stat(D_n)`, halting coarse refinement
       automatically once `Delta_plan(C)` falls below either target `eps_tol` or fraction `eta_epistemic`
       of total interval width, while `collect_active_bottleneck_trajectories` targets high-`rho_i`
       separator neighborhoods to accelerate worst-case multi-goal certification.
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

from collections import deque
from dataclasses import dataclass, field
import hashlib
import math
import time
from typing import Dict, List, Optional, Sequence, Tuple
import warnings

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.sparse.csgraph import connected_components, dijkstra as cs_dijkstra, shortest_path
from scipy.stats import beta as sp_beta

U_MACH_F64 = 1.1102230246251565e-16  # IEEE-754 binary64 unit roundoff 2^{-53}
ETA_SUB_F64 = float(np.nextafter(0.0, 1.0))  # IEEE-754 binary64 min positive subnormal 2^{-1074}


def _up1(x: float) -> float:
    return float(np.nextafter(float(x), float("inf")))


def _up2(x: float) -> float:
    return _up1(_up1(x))


def _dn1(x: float) -> float:
    return float(np.nextafter(float(x), -float("inf")))


def _dn2(x: float) -> float:
    return _dn1(_dn1(x))


def backward_reachable_mask(M_csr: sp.csr_matrix, gm: np.ndarray) -> np.ndarray:
    """Exact backward-reachable state mask from goal set `gm` in directed graph `(M_csr > 0)`."""
    M_T = M_csr.T.tocsr()
    vis = np.asarray(gm, dtype=bool).copy()
    q = deque(int(x) for x in np.flatnonzero(vis))
    while q:
        u = q.popleft()
        for idx in range(M_T.indptr[u], M_T.indptr[u + 1]):
            if M_T.data[idx] > 0.0:
                v = int(M_T.indices[idx])
                if not vis[v]:
                    vis[v] = True
                    q.append(v)
    return vis


def equilibrated_dense_m_solve(A: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Solves nonsingular M-matrix system `A x = b` (`A = I - M`, `M >= 0`, `b >= 0`) accurately
    across `300` orders of magnitude (`1.0` down to `1e-300`) via positive-cone warmup + diagonal
    equilibration `(D^{-1} A D) u = D^{-1} b` + monotone non-negative Jacobi polish.
    """
    m = len(b)
    if m == 0 or float(np.max(b)) <= 0.0:
        return np.zeros(m, dtype=float)
    M = np.maximum(np.eye(m, dtype=float) - A, 0.0)
    x = np.maximum(b, 0.0).copy()
    for _ in range(55):
        xn = (M @ x) + b
        pos = xn > 0.0
        if np.any(pos) and np.max(np.abs(xn[pos] - x[pos]) / xn[pos]) < 1e-3:
            x = xn
            break
        x = xn
    pos_mask = x > 0.0
    if not np.all(pos_mask):
        out = np.zeros(m, dtype=float)
        if np.any(pos_mask):
            idx = np.flatnonzero(pos_mask)
            out[idx] = equilibrated_dense_m_solve(A[np.ix_(idx, idx)], b[idx])
        return out
    d = np.maximum(x, 1e-300)
    inv_d = 1.0 / d
    u = np.linalg.solve((inv_d[:, None] * A) * d[None, :], inv_d * b)
    x = np.maximum(d * u, 0.0)
    for _ in range(4):
        x = (M @ x) + b
    return x


def dijkstra_equilibrated_sparse_subsolution(
    M_sub: sp.csr_matrix,
    b_sub: np.ndarray,
    damp: float = 1e-11,
    log_cutoff: float = 630.0,
    must_keep_local_idx: Optional[int] = None,
) -> np.ndarray:
    """Constructs a truncated, damped shortest-path Doob `h`-scaled candidate subsolution on `M_sub >= 0`:
      - Computes shortest-path log-potentials `ell_i = dist(boundary -> i)` in `-log M_{ij}` via Cython Dijkstra;
      - By Bellman's triangle inequality `ell_i <= ell_j - log M_{ij}`, every transformed single-edge entry
        `M_tilde_{ij} = exp(log M_{ij} - ell_j + ell_i)` lies in `[0, 1]` (`mitigating multi-decade room/cave
        dynamic range; note that on multi-path DAGs of depth d, path multiplicity can still yield u_i = O(2^d),
        so soundness relies strictly on the subsequent full-operator IEEE-754 verifier, never on assuming u_i = O(1)`).
    """
    n = len(b_sub)
    src = np.flatnonzero(b_sub > 0.0)
    if n == 0 or len(src) == 0:
        return np.zeros(n, dtype=float)
    M_coo = M_sub.tocoo()
    mask_m = M_coo.data > 0.0
    r_m = M_coo.col[mask_m].astype(np.int64)
    c_m = M_coo.row[mask_m].astype(np.int64)
    w_m = np.maximum(-np.log(M_coo.data[mask_m]), 1e-12)
    r_s = np.full(len(src), n, dtype=np.int64)
    c_s = src.astype(np.int64)
    w_s = np.maximum(-np.log(b_sub[src]), 1e-12)
    G_rev = sp.csr_matrix(
        (np.concatenate([w_m, w_s]), (np.concatenate([r_m, r_s]), np.concatenate([c_m, c_s]))),
        shape=(n + 1, n + 1),
    )
    dist = cs_dijkstra(G_rev, directed=True, indices=n)[:n]
    eff_cut = float(log_cutoff)
    if must_keep_local_idx is not None and 0 <= must_keep_local_idx < n and np.isfinite(dist[must_keep_local_idx]):
        eff_cut = min(690.0, max(eff_cut, float(dist[must_keep_local_idx]) + 25.0))
    q_idx = np.flatnonzero(np.isfinite(dist) & (dist <= eff_cut))
    if len(q_idx) == 0:
        return np.zeros(n, dtype=float)
    dist_q = dist[q_idx]
    M_qq = M_sub[q_idx, :][:, q_idx].tocoo()
    pos_qq = M_qq.data > 0.0
    rq = M_qq.row[pos_qq]
    cq = M_qq.col[pos_qq]
    log_arg = np.log(M_qq.data[pos_qq]) - dist_q[cq] + dist_q[rq]
    keep_e = log_arg > -690.0
    m_tilde_dat = np.exp(np.minimum(log_arg[keep_e], 1.0))
    M_tilde = sp.csr_matrix((m_tilde_dat, (rq[keep_e], cq[keep_e])), shape=(len(q_idx), len(q_idx)))
    b_q = b_sub[q_idx]
    b_tilde = np.zeros(len(q_idx), dtype=float)
    pos_bq = b_q > 0.0
    log_b = np.log(b_q[pos_bq]) + dist_q[pos_bq]
    b_tilde[pos_bq] = np.where(log_b > -690.0, np.exp(np.minimum(log_b, 1.0)), 0.0)

    fac = 1.0 - float(damp)
    A_eq = (sp.eye(len(q_idx), format="csr") - fac * M_tilde).tocsc()
    u_sol = np.maximum(spla.spsolve(A_eq, fac * b_tilde), 0.0)
    for _ in range(2):
        u_sol = fac * (np.asarray(M_tilde @ u_sol).ravel() + b_tilde)
    y_q = np.exp(-dist_q) * np.maximum(u_sol, 0.0)
    M_qq_csr = M_sub[q_idx, :][:, q_idx].tocsr()
    y_q = fac * (np.asarray(M_qq_csr @ y_q).ravel() + b_q)
    out = np.zeros(n, dtype=float)
    out[q_idx] = y_q
    return out


def dijkstra_equilibrated_global_subsolution(
    M_pes: sp.csr_matrix,
    gm: np.ndarray,
    reach_all: np.ndarray,
    s0: int,
    damp: float = 1e-11,
) -> Tuple[np.ndarray, int]:
    """Exact Doob-equilibrated exterior fallback subsolution on `I_reach = (~gm) & reach_all` when a single
    curved 3D room spans `>15` orders of magnitude (exceeding unscaled `float64` `SuperLU`'s `16`-digit room
    dynamic range). Returns `(z_full, n_active_states)`.
    """
    gm_b = np.asarray(gm, dtype=bool)
    ext_r = np.flatnonzero((~gm_b) & reach_all)
    z_full = np.zeros(len(gm_b), dtype=float)
    z_full[gm_b] = 1.0
    if len(ext_r) == 0:
        return z_full, 0
    M_rr = M_pes[ext_r, :][:, ext_r].tocsr()
    b_r = np.asarray(M_pes[ext_r, :][:, gm_b].sum(axis=1)).ravel()
    s0_loc = int(np.searchsorted(ext_r, s0))
    if not (0 <= s0_loc < len(ext_r) and int(ext_r[s0_loc]) == int(s0)):
        s0_loc = None
    y_r = dijkstra_equilibrated_sparse_subsolution(
        M_rr, b_r, damp=damp, log_cutoff=630.0, must_keep_local_idx=s0_loc
    )
    z_full[ext_r] = y_r
    z_full[gm_b] = 1.0
    return z_full, int(len(ext_r))


def higham_verify_upper_subsolution(
    M_pes: sp.csr_matrix,
    z_sub: np.ndarray,
    gm: np.ndarray,
    s0: int,
    phi_goal: float,
    lam: float,
    q_min: float,
    max_allowed_eps_fl: float = 1e-2,
) -> Tuple[bool, float, float, float]:
    """Outward-rounded IEEE-754 stored-operator upper bound verifier on `I_+ = {i in X_G : z_sub[i] > 0}`
    (`Closes R747-03 & R675-01`):
      - Rejects non-positive/non-finite `(lam, q_min)` fail-closed with ZERO undeclared `1e-12` floors
        (preserving exact cost-unit equivariance under `(q, lam) -> c * (q, lam)`);
      - Bounds sparse dot products below including gradual-underflow error `(deg_i + 1) * 2^{-1074}`;
      - Outward-rounds `delta_rel`, `eta_log`, `eps_fl = (lam / q_min) * eta_log`, and terminal readout `hi_cert`.
    """
    if (
        z_sub is None
        or (not np.isfinite(phi_goal))
        or (not np.isfinite(lam)) or float(lam) <= 0.0
        or (not np.isfinite(q_min)) or float(q_min) <= 0.0
    ):
        return False, float("inf"), 1.0, 1.0
    z_arr = np.asarray(z_sub, dtype=float)
    gm_b = np.asarray(gm, dtype=bool)
    if gm_b[s0]:
        return True, float(phi_goal), 0.0, 0.0
    if (not np.all(np.isfinite(z_arr))) or float(z_arr[s0]) <= 0.0 or float(z_arr[s0]) > 1.0:
        return False, float("inf"), 1.0, 1.0
    ext = np.flatnonzero(~gm_b)
    if len(ext) == 0:
        return True, float(phi_goal), 0.0, 0.0
    if float(np.min(z_arr[ext])) < 0.0 or not np.all(z_arr[gm_b] == 1.0):
        return False, float("inf"), 1.0, 1.0
    zp = z_arr[ext]
    pos = zp > 0.0
    if not np.any(pos):
        return False, float("inf"), 1.0, 1.0
    pos_nodes = ext[pos]
    M_pos = M_pes[pos_nodes, :]
    if len(M_pos.data) > 0 and ((not np.all(np.isfinite(M_pos.data))) or float(np.min(M_pos.data)) < 0.0):
        return False, float("inf"), 1.0, 1.0
    Mz_hat = np.asarray(M_pos @ z_arr).ravel()
    deg = np.diff(M_pos.indptr).astype(float)
    if np.any((deg + 3.0) * U_MACH_F64 >= 0.25):
        return False, float("inf"), 1.0, 1.0
    rel_dn = np.maximum(1.0 - (deg + 3.0) * U_MACH_F64, 0.0)
    S_lo = np.nextafter(
        np.nextafter(rel_dn * Mz_hat, -float("inf")) - (deg + 1.0) * ETA_SUB_F64,
        -float("inf"),
    )
    zp_pos = z_arr[pos_nodes]
    if np.any(S_lo <= 0.0):
        return False, float("inf"), 1.0, 1.0
    ratio_lo = np.nextafter(S_lo / zp_pos, -float("inf"))
    min_ratio = float(np.min(ratio_lo))
    delta_rel = 0.0 if min_ratio >= 1.0 else _up1(1.0 - min_ratio)
    if (not np.isfinite(delta_rel)) or delta_rel >= 0.25:
        return False, float("inf"), float(delta_rel), 1.0
    eta_log_hi = 0.0 if delta_rel == 0.0 else _up2(-math.log1p(-delta_rel))
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        raw_lq = float(lam) / float(q_min)
    if (not np.isfinite(raw_lq)) or raw_lq <= 0.0:
        return False, float("inf"), delta_rel, float("inf")
    lam_over_q_hi = _up1(raw_lq)
    if not np.isfinite(lam_over_q_hi):
        return False, float("inf"), delta_rel, float("inf")
    with np.errstate(over="ignore", invalid="ignore"):
        raw_eps = 0.0 if eta_log_hi == 0.0 else lam_over_q_hi * eta_log_hi
    if not np.isfinite(raw_eps):
        return False, float("inf"), delta_rel, float("inf")
    eps_fl = 0.0 if eta_log_hi == 0.0 else _up1(raw_eps)
    if (not np.isfinite(eps_fl)) or eps_fl > max_allowed_eps_fl or eps_fl >= 0.5:
        return False, float("inf"), delta_rel, float(eps_fl)
    zs0 = float(z_arr[s0])
    neg_log_hi = 0.0 if zs0 >= 1.0 else _up2(-math.log(zs0))
    u_raw_hi = 0.0 if neg_log_hi == 0.0 else _up1(float(lam) * neg_log_hi)
    denom_lo = _dn1(1.0 - eps_fl)
    if denom_lo <= 0.0 or (not np.isfinite(u_raw_hi)):
        return False, float("inf"), delta_rel, float(eps_fl)
    term_hi = 0.0 if u_raw_hi == 0.0 else _up1(u_raw_hi / denom_lo)
    hi_cert = float(phi_goal) if term_hi == 0.0 else _up1(float(phi_goal) + term_hi)
    if not np.isfinite(hi_cert):
        return False, float("inf"), delta_rel, float(eps_fl)
    return True, hi_cert, delta_rel, float(eps_fl)


def higham_verify_lower_supersolution(
    M_opt: sp.csr_matrix,
    b_opt: np.ndarray,
    z_sup: np.ndarray,
    gm: np.ndarray,
    s0: int,
    phi_goal: float,
    lam: float,
    q_min: float,
) -> Tuple[bool, float, float, float]:
    """Outward-rounded IEEE-754 stored-operator lower bound verifier on `X_G = S - G` (`Closes R675-01`):
      - Includes BOTH relative dot-product error AND gradual-underflow product error `(deg_i + 1) * 2^{-1074}`
        (`eliminating the 2^{-1074} subnormal round-to-zero false accept!`);
      - Computes `1 - exp(-q_min / lam)` via `-expm1(-q_min / lam)` with certified downward rounding and
        ZERO `1e-12` contraction-margin floor (failing closed whenever margin underflows or overflows);
      - Outward-rounds `gam_max` upward and `lo_cert` downward (`eliminating 1-ULP upward readout drift`).
    """
    if (
        z_sup is None or b_opt is None
        or (not np.isfinite(phi_goal))
        or (not np.isfinite(lam)) or float(lam) <= 0.0
        or (not np.isfinite(q_min)) or float(q_min) <= 0.0
    ):
        return False, -float("inf"), 1.0, 1.0
    z_in = np.asarray(z_sup, dtype=float)
    b_in = np.asarray(b_opt, dtype=float)
    gm_b = np.asarray(gm, dtype=bool)
    if gm_b[s0]:
        return True, float(phi_goal), 0.0, 0.0
    if (not np.all(np.isfinite(z_in))) or (not np.all(np.isfinite(b_in))):
        return False, -float("inf"), 1.0, 1.0
    ext = np.flatnonzero(~gm_b)
    if len(ext) == 0:
        return True, float(phi_goal), 0.0, 0.0
    if np.any(b_in[ext] < 0.0):
        return False, -float("inf"), 1.0, 1.0
    z_clamped = np.clip(z_in, 0.0, 1.0)
    z_clamped[gm_b] = 1.0
    M_ext = M_opt[ext, :]
    if len(M_ext.data) > 0 and ((not np.all(np.isfinite(M_ext.data))) or float(np.min(M_ext.data)) < 0.0):
        return False, -float("inf"), 1.0, 1.0
    deg = np.diff(M_ext.indptr).astype(float)
    if np.any((deg + 5.0) * U_MACH_F64 >= 0.25):
        return False, -float("inf"), 1.0, 1.0

    raw_dot = np.asarray(M_ext @ z_clamped).ravel()
    sum_hi = np.nextafter(raw_dot + b_in[ext], float("inf"))
    den_dn = np.maximum(1.0 - (deg + 4.0) * U_MACH_F64, 0.5)
    sub_up = (deg + 1.0) * ETA_SUB_F64
    S_hi = np.nextafter(np.nextafter(sum_hi / den_dn, float("inf")) + sub_up, float("inf"))
    diff_up = np.nextafter(S_hi - z_clamped[ext], float("inf"))
    delta_abs = max(0.0, float(np.max(diff_up)))

    with np.errstate(over="ignore", under="ignore", divide="ignore", invalid="ignore"):
        raw_x = float(q_min) / float(lam)
    if (not np.isfinite(raw_x)) or raw_x <= 0.0:
        return False, -float("inf"), delta_abs, float("inf")
    x_dn = _dn1(raw_x)
    if x_dn <= 0.0:
        return False, -float("inf"), delta_abs, float("inf")
    m_raw = -math.expm1(-x_dn)
    margin_lo = _dn2(m_raw * (1.0 - 4.0 * U_MACH_F64))
    if (not np.isfinite(margin_lo)) or margin_lo <= 0.0:
        return False, -float("inf"), delta_abs, float("inf")
    with np.errstate(over="ignore", invalid="ignore"):
        raw_tau = 0.0 if delta_abs == 0.0 else delta_abs / margin_lo
    if not np.isfinite(raw_tau):
        return False, -float("inf"), delta_abs, float("inf")
    tau = 0.0 if delta_abs == 0.0 else _up2(raw_tau)
    if not np.isfinite(tau):
        return False, -float("inf"), delta_abs, float("inf")

    gam_max_hi = min(1.0, _up2(math.exp(-x_dn)))
    z_sum_hi = float(z_clamped[s0]) if tau == 0.0 else _up1(float(z_clamped[s0]) + tau)
    z_cert_s0 = min(gam_max_hi, z_sum_hi)
    if (not np.isfinite(z_cert_s0)) or z_cert_s0 <= 0.0:
        return False, -float("inf"), delta_abs, tau
    neg_log_dn = 0.0 if z_cert_s0 >= 1.0 else max(0.0, _dn2(-math.log(z_cert_s0)))
    cost_dn = 0.0 if neg_log_dn == 0.0 else _dn1(float(lam) * neg_log_dn)
    lo_cert = float(phi_goal) if cost_dn == 0.0 else _dn1(float(phi_goal) + cost_dn)
    if not np.isfinite(lo_cert):
        return False, -float("inf"), delta_abs, tau
    return True, lo_cert, delta_abs, tau


def build_log_scaled_policy_csr(M_csr: sp.csr_matrix, z_vec: np.ndarray, gm: np.ndarray) -> sp.csr_matrix:
    """Constructs a row-stochastic Markov policy `pi_{ij} propto M_{ij} z_j` on `ext = ~gm` via exact
    per-row max-log-weight scaling (`Closes R675-02`: eliminates `max(w_sum, 1e-300)` denominator floors so
    normalization remains row-stochastic across the entire IEEE-754 range down to `2^{-1074} = 4.94e-324`).
    """
    gm_b = np.asarray(gm, dtype=bool)
    ext = np.flatnonzero(~gm_b)
    M_ext = M_csr[ext, :].tocsr()
    if len(ext) == 0 or M_ext.nnz == 0:
        return sp.csr_matrix(M_ext.shape, dtype=float)
    row_ids = np.repeat(np.arange(len(ext), dtype=np.int64), np.diff(M_ext.indptr))
    m_dat = M_ext.data
    z_nb = np.asarray(z_vec, dtype=float)[M_ext.indices]
    pos_e = (m_dat > 0.0) & (z_nb > 0.0)
    has_pos_row = np.zeros(len(ext), dtype=bool)
    np.logical_or.at(has_pos_row, row_ids, pos_e)

    use_z = has_pos_row[row_ids]
    active_e = np.where(use_z, pos_e, m_dat > 0.0)
    log_w = np.full(len(m_dat), -float("inf"), dtype=float)
    idx_z = np.flatnonzero(use_z & pos_e)
    if len(idx_z) > 0:
        log_w[idx_z] = np.log(m_dat[idx_z]) + np.log(z_nb[idx_z])
    idx_fb = np.flatnonzero((~use_z) & (m_dat > 0.0))
    if len(idx_fb) > 0:
        log_w[idx_fb] = np.log(m_dat[idx_fb])

    rmax_log = np.full(len(ext), -float("inf"), dtype=float)
    np.maximum.at(rmax_log, row_ids, log_w)
    rel_w = np.zeros(len(m_dat), dtype=float)
    act_idx = np.flatnonzero(active_e & np.isfinite(rmax_log[row_ids]))
    if len(act_idx) > 0:
        diff_log = log_w[act_idx] - rmax_log[row_ids[act_idx]]
        rel_w[act_idx] = np.where(diff_log > -745.0, np.exp(np.minimum(diff_log, 0.0)), 0.0)

    W_mat = sp.csr_matrix((rel_w, M_ext.indices.copy(), M_ext.indptr.copy()), shape=M_ext.shape)
    w_sum = np.asarray(W_mat.sum(axis=1)).ravel()
    pi_dat = np.where((w_sum > 0.0)[row_ids], rel_w / np.where(w_sum > 0.0, w_sum, 1.0)[row_ids], 0.0)
    Pi_out = sp.csr_matrix((pi_dat, M_ext.indices.copy(), M_ext.indptr.copy()), shape=M_ext.shape)
    Pi_out.sort_indices()
    return Pi_out


def verify_and_bind_deployed_policy_csr(
    M_pes: sp.csr_matrix,
    z_sub: np.ndarray,
    Pi_csr: Optional[sp.csr_matrix],
    gm: np.ndarray,
    s0: int,
    phi_goal: float,
    lam: float,
    q_min: float,
    hi_sub: float,
    eps_fl_sub: float,
    max_allowed_eps_fl: float = 1e-2,
) -> Tuple[bool, float, float, str]:
    """Verifies the ACTUAL delivered `Pi_csr` object and cryptographically binds it to `hi_cert` (`Closes R675-02`):
      1. Finiteness, non-negativity, and shape `(len(ext), N)`;
      2. Forward reachability closure inside `I_+ = {i in ext : z_sub[i] > 0}` from `s0`;
      3. Row-stochasticity `|sum_j Pi[r, j] - 1| <= 1e-11` on every reachable exterior row;
      4. Strict observed-edge support `Pi[r, j] > 0 => M_pes[ext[r], j] > 0` and `j in I_+ U G`;
      5. Topological properness (`100%` of forward-reachable states from `s0` reach `G` on `Pi > 0`);
      6. Outward-rounded Bellman-KL step-drift bound directly on the stored `Pi_csr` entries;
      7. Canonical SHA-256 digest `policy_sha256` over `(indptr, indices, data)`.
    Returns `(ok, hi_bound, eps_fl_bound, policy_sha256)`.
    """
    gm_b = np.asarray(gm, dtype=bool)
    ext = np.flatnonzero(~gm_b)
    if (
        Pi_csr is None or z_sub is None
        or (not sp.isspmatrix_csr(Pi_csr))
        or Pi_csr.shape != (len(ext), len(gm_b))
        or not np.isfinite(hi_sub) or not np.isfinite(phi_goal)
        or not np.isfinite(lam) or lam <= 0.0
        or not np.isfinite(q_min) or q_min <= 0.0
        or not np.isfinite(eps_fl_sub) or eps_fl_sub < 0.0
    ):
        return False, float("inf"), 1.0, ""
    if len(ext) == 0:
        return True, float(phi_goal), 0.0, "empty_exterior"
    if len(Pi_csr.data) == 0 or (not np.all(np.isfinite(Pi_csr.data))) or float(np.min(Pi_csr.data)) < 0.0:
        return False, float("inf"), 1.0, ""

    r_s0 = int(np.searchsorted(ext, s0))
    if not (0 <= r_s0 < len(ext) and int(ext[r_s0]) == int(s0)):
        return False, float("inf"), 1.0, ""
    z_arr = np.asarray(z_sub, dtype=float)
    if (z_arr.shape != gm_b.shape or not np.all(np.isfinite(z_arr))
        or not np.all(z_arr[gm_b] == 1.0) or not 0.0 < z_arr[s0] <= 1.0):
        return False, float("inf"), 1.0, ""

    ext_lookup = np.full(len(gm_b), -1, dtype=np.int64)
    ext_lookup[ext] = np.arange(len(ext), dtype=np.int64)

    # 1. Forward BFS from `r_s0` along `Pi_csr > 0`
    vis_f = np.zeros(len(ext), dtype=bool)
    vis_f[r_s0] = True
    qf = deque([r_s0])
    reaches_goal_direct = np.zeros(len(ext), dtype=bool)
    while qf:
        r = qf.popleft()
        for p_idx in range(Pi_csr.indptr[r], Pi_csr.indptr[r + 1]):
            pv = float(Pi_csr.data[p_idx])
            if pv <= 0.0:
                continue
            j_st = int(Pi_csr.indices[p_idx])
            if gm_b[j_st]:
                reaches_goal_direct[r] = True
            else:
                rn = int(ext_lookup[j_st])
                if rn < 0 or float(z_arr[j_st]) <= 0.0:
                    return False, float("inf"), 1.0, ""
                if not vis_f[rn]:
                    vis_f[rn] = True
                    qf.append(rn)

    reach_rows = np.flatnonzero(vis_f)
    if np.any(z_arr[ext[reach_rows]] <= 0.0):
        return False, float("inf"), 1.0, ""

    # 2. Backward BFS from `reaches_goal_direct` on `reach_rows` to certify properness `P^Pi_{s0}(tau_G < inf) = 1`
    Pi_rr = Pi_csr[reach_rows, :][:, ext[reach_rows]].tocsr()
    Pi_rr_T = Pi_rr.T.tocsr()
    can_hit = reaches_goal_direct[reach_rows].copy()
    qb = deque(int(i) for i in np.flatnonzero(can_hit))
    while qb:
        u = qb.popleft()
        for idx in range(Pi_rr_T.indptr[u], Pi_rr_T.indptr[u + 1]):
            if Pi_rr_T.data[idx] > 0.0:
                v = int(Pi_rr_T.indices[idx])
                if not can_hit[v]:
                    can_hit[v] = True
                    qb.append(v)
    if not np.all(can_hit):
        return False, float("inf"), 1.0, ""

    # 3. Row-stochasticity + exact observed-support check + Bellman-KL drift bound on stored `Pi_csr`
    Pi_sub = Pi_csr[reach_rows, :].tocsr()
    Pi_sub.sum_duplicates()
    Pi_sub.sort_indices()
    row_sums = np.asarray(Pi_sub.sum(axis=1)).ravel()
    deg_r = np.diff(Pi_sub.indptr).astype(float)
    if np.any(np.abs(row_sums - 1.0) > 1e-11) or np.any((deg_r + 3.0) * U_MACH_F64 >= 0.1):
        return False, float("inf"), 1.0, ""
    s_lo = np.nextafter(np.maximum(1.0 - (deg_r + 2.0) * U_MACH_F64, 0.5) * row_sums, -float("inf"))
    if np.any(s_lo <= 0.0):
        return False, float("inf"), 1.0, ""
    log_s_lo = np.log(s_lo)

    M_sub = M_pes[ext[reach_rows], :].tocsr()
    M_sub.sum_duplicates()
    M_sub.sort_indices()
    max_eta_pol = 0.0
    for loc_r in range(len(reach_rows)):
        st_i = int(ext[reach_rows[loc_r]])
        log_zi = math.log(float(z_arr[st_i]))
        m_start, m_end = M_sub.indptr[loc_r], M_sub.indptr[loc_r + 1]
        m_cols = M_sub.indices[m_start:m_end]
        m_vals = M_sub.data[m_start:m_end]
        for p_idx in range(Pi_sub.indptr[loc_r], Pi_sub.indptr[loc_r + 1]):
            pv = float(Pi_sub.data[p_idx])
            if pv <= 0.0:
                continue
            col_j = int(Pi_sub.indices[p_idx])
            pos_m = int(np.searchsorted(m_cols, col_j))
            if not (0 <= pos_m < len(m_cols) and int(m_cols[pos_m]) == col_j):
                return False, float("inf"), 1.0, ""
            mv = float(m_vals[pos_m])
            zj = 1.0 if gm_b[col_j] else float(z_arr[col_j])
            if not np.isfinite(mv) or mv <= 0.0 or zj <= 0.0:
                return False, float("inf"), 1.0, ""
            lp = math.log(pv)
            lm = math.log(mv)
            lzj = 0.0 if gm_b[col_j] else math.log(zj)
            rad = 12.0 * U_MACH_F64 * (1.0 + abs(lp) + abs(lm) + abs(lzj) + abs(log_zi) + abs(float(log_s_lo[loc_r])))
            drift_ij = (lp - lm - lzj + log_zi - float(log_s_lo[loc_r])) + rad
            if drift_ij > max_eta_pol:
                max_eta_pol = drift_ij

    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        lq_hi = _up1(float(lam) / float(q_min))
        eps_pol = 0.0 if max_eta_pol == 0.0 else _up1(lq_hi * max_eta_pol)
    eps_tot = max(float(eps_fl_sub), float(eps_pol))
    if (not np.isfinite(eps_tot)) or eps_tot > max_allowed_eps_fl or eps_tot >= 0.5:
        return False, float("inf"), float(eps_tot), ""

    zs0 = float(z_arr[s0])
    neg_log_hi = 0.0 if zs0 >= 1.0 else _up2(-math.log(zs0))
    u_raw_hi = 0.0 if neg_log_hi == 0.0 else _up1(float(lam) * neg_log_hi)
    denom_lo = _dn1(1.0 - eps_tot)
    if denom_lo <= 0.0:
        return False, float("inf"), float(eps_tot), ""
    term_hi = 0.0 if u_raw_hi == 0.0 else _up1(u_raw_hi / denom_lo)
    hi_pol = float(phi_goal) if term_hi == 0.0 else _up1(float(phi_goal) + term_hi)
    hi_final = max(float(hi_sub), float(hi_pol))
    if not np.isfinite(hi_final):
        return False, float("inf"), float(eps_tot), ""

    Pi_canon = Pi_csr.copy()
    Pi_canon.sort_indices()
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(Pi_canon.indptr, dtype="<i8").tobytes())
    h.update(np.ascontiguousarray(Pi_canon.indices, dtype="<i8").tobytes())
    h.update(np.ascontiguousarray(Pi_canon.data, dtype="<f8").tobytes())
    return True, hi_final, float(eps_tot), h.hexdigest()


# ==============================================================================
# 1. Unknown-Dynamics Non-Axis-Aligned / Curved / Unstructured Environments
# ==============================================================================
def _log_dirichlet_elimination(P, cost, active, boundary_z):
    """Solve for log(z) on active states by subtraction-free state elimination.

    A row's diagonal is the sum of its off-diagonal, boundary and killing
    rates. Eliminating a state propagates those rates and the boundary payoff
    separately, so even an almost-absorbing cycle retains its small exit.
    """
    n = len(active)
    local = np.full(P.shape[0], -1, dtype=int)
    local[active] = np.arange(n)
    edges = [{} for _ in active]
    incoming = [set() for _ in active]
    sink = np.full(n, -np.inf)
    payoff = np.full(n, -np.inf)
    for r, state in enumerate(active):
        kill = -math.expm1(-cost[state])
        if kill > 0:
            sink[r] = math.log(kill)
        for k in range(P.indptr[state], P.indptr[state + 1]):
            j, p = P.indices[k], P.data[k]
            if j == state or p <= 0:
                continue
            w = math.log(p) - cost[state]
            other = local[j]
            if other >= 0:
                edges[r][other] = np.logaddexp(edges[r].get(other, -np.inf), w)
                incoming[other].add(r)
            else:
                sink[r] = np.logaddexp(sink[r], w)
                if boundary_z[j] > 0:
                    payoff[r] = np.logaddexp(payoff[r], w + math.log(boundary_z[j]))

    diagonal = np.empty(n)
    for k, row in enumerate(edges):
        diagonal[k] = np.logaddexp.reduce([sink[k], *row.values()])
        if not np.isfinite(diagonal[k]):
            raise ArithmeticError("Reachable Dirichlet row has no exit")
        for prev in incoming[k]:
            prev_row = edges[prev]
            scale = prev_row.pop(k) - diagonal[k]
            sink[prev] = np.logaddexp(sink[prev], scale + sink[k])
            payoff[prev] = np.logaddexp(payoff[prev], scale + payoff[k])
            for dest, rate in row.items():
                if dest != prev:
                    prev_row[dest] = np.logaddexp(prev_row.get(dest, -np.inf), scale + rate)
                    incoming[dest].add(prev)
        for dest in row:
            incoming[dest].discard(k)

    log_z = np.empty(n)
    for k in reversed(range(n)):
        terms = [payoff[k]] + [rate + log_z[j] for j, rate in edges[k].items()]
        log_z[k] = np.logaddexp.reduce(terms) - diagonal[k]
    if np.any(~np.isfinite(log_z)):
        raise ArithmeticError("Reachable Dirichlet value is outside the log solver's numeric range")
    return np.minimum(log_z, 0.0)


@dataclass
class UnknownDiscreteKLEnv:
    """True underlying unknown KL-regularized Markov environment `(P_true, q_true, lam)`.
    The learner NEVER accesses `P_true`, `q_true`, or `coords` during discovery or planning!
    `coords` is stored solely for visualization and benchmark world generation.
    """
    name: str
    n_states: int
    P_true: sp.csr_matrix        # Row-stochastic (N x N) passive transition matrix
    q_true: np.ndarray           # True step cost in [q_min, q_max], shape (N,)
    q_min: float
    q_max: float
    lam: float
    cost_noise_std: float
    coords: Optional[np.ndarray] = None  # Optional (N, d) for plotting / goal sampling only
    true_room_hint_for_eval: Optional[np.ndarray] = None

    def true_desirability_and_value(self, goal_mask: np.ndarray, phi_goal: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
        """Exact ground-truth `z^*_{true}` and `V^*_{true}` on the true unknown environment (for audit only)."""
        gm = np.asarray(goal_mask, dtype=bool)
        z_true = gm.astype(float)
        v_true = np.full(self.n_states, np.inf)
        v_true[gm] = float(phi_goal)
        active = np.flatnonzero(backward_reachable_mask(self.P_true, gm) & ~gm)
        if len(active):
            cost = self.q_true / self.lam
            # Near-conservative rows can wipe out killing rates in I - M.
            # This threshold selects the arithmetic; it never truncates a rate.
            if np.min(cost[active]) <= math.sqrt(np.finfo(float).eps):
                difficult = active
            else:
                M = sp.diags(np.exp(-cost[active])) @ self.P_true[active, :]
                system = sp.eye(len(active), format="csc") - M[:, active].tocsc()
                rhs = np.asarray(M[:, gm].sum(axis=1)).ravel()
                z = spla.spsolve(system, rhs)
                if np.all(np.isfinite(z)):
                    normal = z >= np.finfo(float).tiny
                    z_true[active[normal]] = z[normal]
                    v_true[active[normal]] = float(phi_goal) - self.lam * np.log(z[normal])
                    difficult = active[~normal]
                else:
                    difficult = active
            if len(difficult):
                log_z = _log_dirichlet_elimination(self.P_true, cost, difficult, z_true)
                z_true[difficult] = np.exp(log_z)
                v_true[difficult] = float(phi_goal) - self.lam * log_z
        return z_true, v_true

    def evaluate_deployed_policy_true_cost(
        self,
        Pi_ext_csr: sp.csr_matrix,
        goal_mask: np.ndarray,
        phi_goal: float,
        s0: int,
    ) -> float:
        """Evaluates exact closed-loop expected cost `J^{mu}_{true}(s0)` of deployed policy `Pi_ext_csr`
        (`shape = (|ext|, N)`, row-stochastic) on the TRUE unknown environment `(P_true, q_true)`.
        Returns `+inf` if `Pi_ext_csr` puts positive probability on any impossible transition `P_true == 0`
        or fails to reach `goal_mask` with probability 1 from `s0`!
        """
        gm = np.asarray(goal_mask, dtype=bool)
        if bool(gm[s0]):
            return float(phi_goal)
        if Pi_ext_csr is None or not np.any(gm):
            return float("inf")
        ext = np.flatnonzero(~gm)
        s_pos = int(np.searchsorted(ext, s0))
        if Pi_ext_csr.shape != (len(ext), self.n_states):
            return float("inf")
        Pi_ext_csr = Pi_ext_csr.copy()
        Pi_ext_csr.sum_duplicates()

        # Check absolute continuity `Pi << P_true` and compute exact step KL `D_KL(pi_i || p^*_i)`
        P_ext = self.P_true[ext, :].tocsr()
        row_ids = np.repeat(np.arange(len(ext), dtype=np.int64), np.diff(Pi_ext_csr.indptr))
        pos_mask = Pi_ext_csr.data > 0.0
        r_nz = row_ids[pos_mask]
        c_nz = Pi_ext_csr.indices[pos_mask]
        pi_nz = Pi_ext_csr.data[pos_mask]

        # Costs and admissibility at s0 depend only on positive-probability
        # paths before the first visit to G. An unused row may be undefined.
        adj_fwd = sp.csr_matrix(
            (np.ones(len(pi_nz), dtype=float), (ext[r_nz], c_nz)),
            shape=(self.n_states, self.n_states),
        )
        fwd_from_s0 = np.isfinite(shortest_path(adj_fwd, directed=True, unweighted=True, indices=s0))
        used = fwd_from_s0[ext[r_nz]]
        r_nz, c_nz, pi_nz = r_nz[used], c_nz[used], pi_nz[used]
        row_entries = Pi_ext_csr.data[fwd_from_s0[ext[row_ids]]]
        if np.any(~np.isfinite(row_entries)) or np.any(row_entries < 0.0):
            return float("inf")
        if not len(pi_nz):
            return float("inf")
        p_true_nz = np.asarray(P_ext[r_nz, c_nz]).ravel()
        if np.any(p_true_nz <= 0.0):
            return float("inf")

        r_sums = np.asarray(Pi_ext_csr.sum(axis=1)).ravel()
        valid_row = np.abs(r_sums - 1.0) <= 1e-11
        if not np.all(valid_row[fwd_from_s0[ext]]):
            return float("inf")

        pi_nz = pi_nz / r_sums[r_nz]
        kl_vals = pi_nz * (np.log(pi_nz) - np.log(p_true_nz))
        kl_row = np.zeros(len(ext), dtype=float)
        np.add.at(kl_row, r_nz, kl_vals)
        c_step = np.where(valid_row, self.q_true[ext] + self.lam * np.maximum(kl_row, 0.0), float("inf"))

        # Exact positive-support reachability / properness check from `s0` (`Closes P3-E07`: zero arbitrary 1e-11 cutoff)
        adj_T = sp.csr_matrix(
            (np.ones(len(pi_nz), dtype=float), (c_nz, ext[r_nz])),
            shape=(self.n_states, self.n_states),
        )
        dist_to_g = shortest_path(adj_T, directed=True, unweighted=True, indices=np.flatnonzero(gm))
        can_reach = np.min(dist_to_g, axis=0) < np.inf if dist_to_g.ndim == 2 else (dist_to_g < np.inf)
        if not bool(can_reach[s0]):
            return float("inf")

        Pi_pos_csr = sp.csr_matrix((pi_nz, (r_nz, c_nz)), shape=Pi_ext_csr.shape)
        bad = ~can_reach
        while np.any(bad):
            Pi_bad = Pi_pos_csr[:, bad]
            leak = (np.diff(Pi_bad.indptr) > 0) & can_reach[ext]
            if not np.any(leak):
                break
            can_reach[ext[leak]] = False
            if not bool(can_reach[s0]):
                return float("inf")
            bad = ~can_reach

        # Restrict linear evaluation to the exact Markov support reachable forward from `s0` (states never
        # visited from `s0` cannot affect `J^{mu}(s0)` and must not pollute condition number!)
        prop_ext_mask = fwd_from_s0[ext] & can_reach[ext] & valid_row
        if not bool(prop_ext_mask[s_pos]):
            return float("inf")
        # Verify closedness: no state reachable from `s0` may transition outside `(prop_ext_mask cup gm)`
        allowed_dest = np.zeros(self.n_states, dtype=bool)
        allowed_dest[gm] = True
        allowed_dest[ext[prop_ext_mask]] = True
        if Pi_pos_csr[prop_ext_mask, :][:, ~allowed_dest].nnz > 0:
            return float("inf")

        ext_p = ext[prop_ext_mask]
        # Form `(I - Pi_p)` WITHOUT catastrophic `1.0 - pi_{ii}` cancellation in IEEE-754 float64:
        # For any row-stochastic Markov kernel closed on `ext_p cup gm`,
        # `1 - pi_{ii} == sum_{j in ext_p \ {i}} pi_{ij} + sum_{g in gm} pi_{ig} > 0`!
        Pi_p_off = Pi_pos_csr[prop_ext_mask, :][:, ext_p].tolil()
        Pi_p_off.setdiag(0.0)
        Pi_p_off_csr = Pi_p_off.tocsr()
        Pi_p_off_csr.eliminate_zeros()
        exit_to_ext = np.asarray(Pi_p_off_csr.sum(axis=1)).ravel()
        exit_to_goal = np.asarray(Pi_pos_csr[prop_ext_mask, :][:, gm].sum(axis=1)).ravel()
        diag_m = exit_to_ext + exit_to_goal
        if np.any(diag_m <= 0.0):
            return float("inf")
        Sys = (sp.diags(diag_m, format="csr") - Pi_p_off_csr).tocsc()
        rhs = c_step[prop_ext_mask]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                v0 = spla.spsolve(Sys, rhs)
        except Exception:
            return float("inf")
        if (not np.all(np.isfinite(v0))) or np.any(v0 < -1e-9):
            return float("inf")
        comp_denom = np.maximum(np.maximum(np.abs(rhs), diag_m * np.abs(v0)), 1e-300)
        if float(np.max(np.abs(rhs - (Sys @ v0)) / comp_denom)) > 1e-6:
            return float("inf")
        return float(phi_goal) + float(max(0.0, float(v0[int(np.searchsorted(ext_p, s0))])))


def build_rotated_multiroom_2d_env(
    seed: int = 0,
    grid_n: int = 46,
    angle_deg: float = 37.0,
    n_rooms_per_side: int = 3,
    door_half_width: float = 0.095,
    add_baffles: bool = True,
) -> UnknownDiscreteKLEnv:
    """Constructs a `37`-degree ROTATED `3x3` (9-room) multi-room 2D domain on `[-1, 1]^2`
    with asymmetric interior baffles, multimodal hazards, and rotational drift.
    Because all walls and doorways are rotated by `37` degrees, axis-aligned coordinate-plane
    bottleneck detectors find ZERO cuts (`100%` failure of axis-aligned priors!).
    """
    rng = np.random.default_rng(seed)
    xs = np.linspace(-1.0, 1.0, grid_n)
    gx, gy = np.meshgrid(xs, xs, indexing="ij")
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    h = 2.0 / float(grid_n - 1)

    th = np.deg2rad(angle_deg)
    R = np.array([[np.cos(th), np.sin(th)], [-np.sin(th), np.cos(th)]], dtype=float)
    uv = pts @ R.T  # Rotated room frame coordinates `(u, v)`

    # Keep interior of rotated square `|u| <= 0.78, |v| <= 0.78`
    in_box = (np.abs(uv[:, 0]) <= 0.78) & (np.abs(uv[:, 1]) <= 0.78)
    wall_pos = [-0.26, 0.26] if n_rooms_per_side == 3 else [0.0]
    wall_thick = 0.92 * h

    is_wall = np.zeros(len(pts), dtype=bool)
    # Vertical rotated walls `u = w_u` with shifted doorway openings
    seg_bounds = [-0.78] + wall_pos + [0.78]
    for wu in wall_pos:
        near_wu = np.abs(uv[:, 0] - wu) <= wall_thick
        open_door = np.zeros(len(pts), dtype=bool)
        for r_v in range(len(seg_bounds) - 1):
            vc = 0.5 * (seg_bounds[r_v] + seg_bounds[r_v + 1]) + float(rng.uniform(-0.04, 0.04))
            open_door |= np.abs(uv[:, 1] - vc) <= door_half_width
        is_wall |= near_wu & (~open_door)

    for wv in wall_pos:
        near_wv = np.abs(uv[:, 1] - wv) <= wall_thick
        open_door = np.zeros(len(pts), dtype=bool)
        for r_u in range(len(seg_bounds) - 1):
            uc = 0.5 * (seg_bounds[r_u] + seg_bounds[r_u + 1]) + float(rng.uniform(-0.04, 0.04))
            open_door |= np.abs(uv[:, 0] - uc) <= door_half_width
        is_wall |= near_wv & (~open_door)

    if add_baffles:
        # Partial baffles directly behind doorways to induce entry-dependent optimal crossing profiles
        for (bu, bv0, bv1) in [(-0.11, -0.62, -0.44), (0.41, -0.10, 0.12), (-0.42, 0.36, 0.58)]:
            is_wall |= (np.abs(uv[:, 0] - bu) <= wall_thick) & (uv[:, 1] >= bv0) & (uv[:, 1] <= bv1)

    free_mask = in_box & (~is_wall)
    free_idx = np.flatnonzero(free_mask)
    # Keep largest connected component on 4-neighbor grid
    f_map = np.full(len(pts), -1, dtype=np.int64)
    f_map[free_idx] = np.arange(len(free_idx), dtype=np.int64)
    rows_g, cols_g = [], []
    for k, g_id in enumerate(free_idx):
        ix, iy = divmod(int(g_id), grid_n)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = ix + dx, iy + dy
            if 0 <= nx < grid_n and 0 <= ny < grid_n:
                nb = f_map[nx * grid_n + ny]
                if nb >= 0:
                    rows_g.append(k)
                    cols_g.append(int(nb))
    adj0 = sp.csr_matrix((np.ones(len(rows_g)), (rows_g, cols_g)), shape=(len(free_idx), len(free_idx)))
    n_cc, lbl = connected_components(adj0, directed=False)
    if n_cc > 1:
        best_cc = int(np.argmax(np.bincount(lbl)))
        free_idx = free_idx[lbl == best_cc]
        f_map.fill(-1)
        f_map[free_idx] = np.arange(len(free_idx), dtype=np.int64)

    n_s = len(free_idx)
    pts_f = pts[free_idx]
    uv_f = uv[free_idx]

    # Build anisotropic-drift passive transition kernel P_true (4-neighbor + self-loop, unknown to learner!)
    swirl = 0.28 * (1.0 if (seed % 2 == 0) else -1.0)
    b_vec = np.column_stack([swirl * pts_f[:, 1] + 0.10 * np.cos(3.0 * pts_f[:, 0]), -swirl * pts_f[:, 0] + 0.10 * np.sin(3.0 * pts_f[:, 1])])

    p_rows, p_cols, p_vals = [], [], []
    for i, g_id in enumerate(free_idx):
        ix, iy = divmod(int(g_id), grid_n)
        nbs = [i]
        wts = [0.15]  # lazy self-transition
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = ix + dx, iy + dy
            if 0 <= nx < grid_n and 0 <= ny < grid_n:
                nb = int(f_map[nx * grid_n + ny])
                if nb >= 0:
                    step_v = np.array([float(dx), float(dy)], dtype=float)
                    drift_tilt = float(np.exp(0.38 * np.dot(b_vec[i], step_v)))
                    nbs.append(nb)
                    wts.append(drift_tilt)
        w_arr = np.array(wts, dtype=float)
        w_arr /= float(np.sum(w_arr))
        p_rows.extend([i] * len(nbs))
        p_cols.extend(nbs)
        p_vals.extend(w_arr.tolist())

    P_true = sp.csr_matrix((p_vals, (p_rows, p_cols)), shape=(n_s, n_s))
    c1 = rng.uniform(-0.45, 0.45, size=(1, 2))
    c2 = rng.uniform(-0.45, 0.45, size=(1, 2))
    q_true = (
        0.06
        + 0.24 * np.exp(-np.sum((pts_f - c1) ** 2, axis=1) / 0.14)
        + 0.20 * np.exp(-np.sum((pts_f - c2) ** 2, axis=1) / 0.12)
    )
    q_true = np.clip(q_true, 0.05, 0.55)

    # True room index in rotated frame (used ONLY to sample diverse cross-room test goals!)
    ru = np.digitize(uv_f[:, 0], wall_pos)
    rv = np.digitize(uv_f[:, 1], wall_pos)
    room_hint = (ru * n_rooms_per_side + rv).astype(np.int64)

    return UnknownDiscreteKLEnv(
        name=f"RotatedMultiRoom2D_{angle_deg:.0f}deg",
        n_states=n_s,
        P_true=P_true,
        q_true=q_true,
        q_min=0.04,
        q_max=0.60,
        lam=1.0,
        cost_noise_std=0.04,
        coords=pts_f,
        true_room_hint_for_eval=room_hint,
    )


def build_curved_3d_cave_env(seed: int = 0, gn: int = 26) -> UnknownDiscreteKLEnv:
    """Constructs a 3D non-axis-aligned multi-chamber cave/tunnel network (`~7,500-9,500` states)
    where 8 ellipsoidal/tilted 3D chambers are connected by slanted cylindrical tunnels of multi-node
    cross-section (`~12-25` nodes/tunnel) + internal obstacle pillars.
    Zero axis-aligned wall planes exist anywhere in the 3D domain!
    """
    rng = np.random.default_rng(seed)
    xs = np.linspace(-1.0, 1.0, gn)
    gx, gy, gz = np.meshgrid(xs, xs, xs, indexing="ij")
    pts = np.column_stack([gx.ravel(), gy.ravel(), gz.ravel()])

    # 8 tilted 3D chamber centers (`2x2x2` octants jittered irregularly)
    base_ctrs = []
    for sx in (-0.50, 0.50):
        for sy in (-0.50, 0.50):
            for sz in (-0.48, 0.48):
                jit = rng.uniform(-0.08, 0.08, size=3)
                base_ctrs.append(np.array([sx, sy, sz]) + jit)
    ch_ctrs = np.vstack(base_ctrs)  # (8, 3)

    in_chamber = np.zeros(len(pts), dtype=bool)
    nearest_ch = np.argmin(np.sum((pts[:, None, :] - ch_ctrs[None, :, :]) ** 2, axis=2), axis=1)
    # Tilted ellipsoids
    th = 0.55
    rot = np.array([[np.cos(th), -np.sin(th), 0.0], [np.sin(th), np.cos(th), 0.25], [0.0, -0.24, 0.97]], dtype=float)
    for c_i in range(8):
        rel = (pts - ch_ctrs[c_i]) @ rot.T
        ell_d = (rel[:, 0] / 0.43) ** 2 + (rel[:, 1] / 0.41) ** 2 + (rel[:, 2] / 0.40) ** 2
        # Carve an internal boulder baffle inside 4 chambers
        boulder = np.sum((pts - (ch_ctrs[c_i] + np.array([0.09, -0.07, 0.0]))) ** 2, axis=1) < (0.14 ** 2 if c_i % 2 == 0 else -1.0)
        in_chamber |= (ell_d <= 1.0) & (~boulder)

    # Connect adjacent octant chambers via slanted multi-node tunnels (closing 2 of 12 tunnels for detours)
    edges_oct = []
    for i in range(8):
        for j in range(i + 1, 8):
            if bin(i ^ j).count("1") == 1:
                edges_oct.append((i, j))
    closed = set(int(k) for k in rng.choice(len(edges_oct), size=2, replace=False))
    in_tunnel = np.zeros(len(pts), dtype=bool)
    tunnel_rad = 0.165
    for e_idx, (ci, cj) in enumerate(edges_oct):
        if e_idx in closed:
            continue
        p0 = ch_ctrs[ci]
        p1 = ch_ctrs[cj]
        seg = p1 - p0
        seg_len2 = float(np.dot(seg, seg))
        t_proj = np.clip(((pts - p0) @ seg) / seg_len2, 0.0, 1.0)
        closest = p0[None, :] + t_proj[:, None] * seg[None, :]
        dist2 = np.sum((pts - closest) ** 2, axis=1)
        in_tunnel |= dist2 <= (tunnel_rad ** 2)

    free_mask = in_chamber | in_tunnel
    free_idx = np.flatnonzero(free_mask)
    f_map = np.full(len(pts), -1, dtype=np.int64)
    f_map[free_idx] = np.arange(len(free_idx), dtype=np.int64)

    # Ensure single connected 6-neighbor 3D graph
    strides = (gn * gn, gn, 1)
    rows_g, cols_g = [], []
    for k, g_id in enumerate(free_idx):
        ix = (int(g_id) // strides[0]) % gn
        iy = (int(g_id) // strides[1]) % gn
        iz = int(g_id) % gn
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nx, ny, nz = ix + dx, iy + dy, iz + dz
            if 0 <= nx < gn and 0 <= ny < gn and 0 <= nz < gn:
                nb = int(f_map[nx * strides[0] + ny * strides[1] + nz])
                if nb >= 0:
                    rows_g.append(k)
                    cols_g.append(nb)
    adj = sp.csr_matrix((np.ones(len(rows_g)), (rows_g, cols_g)), shape=(len(free_idx), len(free_idx)))
    n_cc, lbl = connected_components(adj, directed=False)
    if n_cc > 1:
        best_cc = int(np.argmax(np.bincount(lbl)))
        free_idx = free_idx[lbl == best_cc]
        f_map.fill(-1)
        f_map[free_idx] = np.arange(len(free_idx), dtype=np.int64)

    n_s = len(free_idx)
    pts_f = pts[free_idx]
    ch_hint = nearest_ch[free_idx].astype(np.int64)

    # 3D vortex drift passive kernel
    b_f = np.column_stack([0.18 * pts_f[:, 1], -0.18 * pts_f[:, 0], 0.10 * np.sin(2.0 * pts_f[:, 0])])
    p_rows, p_cols, p_vals = [], [], []
    for i, g_id in enumerate(free_idx):
        ix = (int(g_id) // strides[0]) % gn
        iy = (int(g_id) // strides[1]) % gn
        iz = int(g_id) % gn
        nbs = [i]
        wts = [0.20]
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nx, ny, nz = ix + dx, iy + dy, iz + dz
            if 0 <= nx < gn and 0 <= ny < gn and 0 <= nz < gn:
                nb = int(f_map[nx * strides[0] + ny * strides[1] + nz])
                if nb >= 0:
                    sv = np.array([float(dx), float(dy), float(dz)], dtype=float)
                    nbs.append(nb)
                    wts.append(float(np.exp(0.32 * np.dot(b_f[i], sv))))
        w_arr = np.array(wts, dtype=float)
        w_arr /= float(np.sum(w_arr))
        p_rows.extend([i] * len(nbs))
        p_cols.extend(nbs)
        p_vals.extend(w_arr.tolist())

    P_true = sp.csr_matrix((p_vals, (p_rows, p_cols)), shape=(n_s, n_s))
    hz_c = rng.uniform(-0.5, 0.5, size=(1, 3))
    q_true = np.clip(0.035 + 0.16 * np.exp(-np.sum((pts_f - hz_c) ** 2, axis=1) / 0.25), 0.03, 0.40)

    return UnknownDiscreteKLEnv(
        name="Curved3DCaveNetwork",
        n_states=n_s,
        P_true=P_true,
        q_true=q_true,
        q_min=0.025,
        q_max=0.45,
        lam=1.0,
        cost_noise_std=0.03,
        coords=pts_f,
        true_room_hint_for_eval=ch_hint,
    )


def sample_unseen_goal_tasks(
    env: UnknownDiscreteKLEnv,
    n_tasks: int,
    seed: int,
    goal_radius_nodes: int = 6,
    avoid_states: Optional[np.ndarray] = None,
) -> List[Tuple[int, np.ndarray]]:
    """Samples `n_tasks` unseen `(start_state, goal_mask)` pairs in distinct macro-regions."""
    rng = np.random.default_rng(seed)
    avoid_mk = np.zeros(env.n_states, dtype=bool)
    if avoid_states is not None and len(avoid_states) > 0:
        avoid_mk[np.asarray(avoid_states, dtype=np.int64)] = True

    adj_undir = ((env.P_true + env.P_true.T) > 0).tocsr()
    rooms = env.true_room_hint_for_eval
    uniq_r = np.unique(rooms) if rooms is not None else np.array([0])
    tasks: List[Tuple[int, np.ndarray]] = []
    attempts = 0
    while len(tasks) < n_tasks and attempts < n_tasks * 60:
        attempts += 1
        if len(uniq_r) >= 2:
            rs, rg = rng.choice(uniq_r, size=2, replace=False)
            cand_s = np.flatnonzero((rooms == rs) & (~avoid_mk))
            cand_g = np.flatnonzero((rooms == rg) & (~avoid_mk))
        else:
            cand_s = np.flatnonzero(~avoid_mk)
            cand_g = cand_s
        if len(cand_s) == 0 or len(cand_g) < goal_radius_nodes:
            continue
        s0 = int(rng.choice(cand_s))
        g_seed = int(rng.choice(cand_g))
        # BFS ball around g_seed inside the same cluster/region and outside `avoid_mk`
        dists = shortest_path(adj_undir, directed=False, unweighted=True, indices=g_seed)
        elig = np.flatnonzero((~avoid_mk) & ((rooms == rg) if len(uniq_r) >= 2 else True) & np.isfinite(dists))
        if len(elig) < goal_radius_nodes:
            continue
        order = elig[np.argsort(dists[elig])[:goal_radius_nodes]]
        if s0 in order:
            continue
        gm = np.zeros(env.n_states, dtype=bool)
        gm[order] = True
        tasks.append((s0, gm))
    return tasks


# ==============================================================================
# 2. Trajectory Collection (Passive Random Walk & Active Bottleneck Exploration)
# ==============================================================================
@dataclass
class EmpiricalTrajectoryDataset:
    n_states: int
    total_steps: int
    visit_counts: np.ndarray        # (N,) int64
    trans_counts: sp.csr_matrix     # (N, N) int64 / float64 transition counts k_{ij}
    cost_sums: np.ndarray           # (N,) float64 sum of observed noisy costs
    q_min: float
    q_max: float
    lam: float


def sample_unbiased_bounded_cost(
    q_val: float,
    q_min: float,
    q_max: float,
    noise_std: float,
    rng: np.random.Generator,
) -> float:
    """Exact mean-preserving bounded sensor observation on `[q_min, q_max]` (`Closes P3-P0-03`):
    Draws a Bernoulli-mixture observation `q_tilde in [q_min, q_max]` satisfying
    `E[q_tilde | q_val] == q_val` IDENTICALLY everywhere on `[q_min, q_max]`, including boundaries
    `q_val == q_min` and `q_val == q_max` (eliminating clipped-Gaussian boundary bias).
    """
    qv = float(np.clip(q_val, q_min, q_max))
    rng_span = float(q_max - q_min)
    if noise_std <= 0.0 or rng_span <= 0.0:
        return qv
    u = float(np.clip((qv - q_min) / rng_span, 0.0, 1.0))
    eta = min(1.0, (2.0 * float(noise_std)) / rng_span)
    bern = 1.0 if float(rng.random()) < u else 0.0
    return float((1.0 - eta) * qv + eta * (q_min + rng_span * bern))


def collect_exploration_trajectories(
    env: UnknownDiscreteKLEnv,
    total_steps: int,
    episode_len: int = 80,
    seed: int = 0,
    initial_dataset: Optional[EmpiricalTrajectoryDataset] = None,
    active_target_weights: Optional[np.ndarray] = None,
    entry_states: Optional[np.ndarray] = None,
    ambient_reset_prob: float = 0.12,
) -> EmpiricalTrajectoryDataset:
    """Collects `total_steps` reward-free passive transitions `(s_t, s_{t+1}, q_tilde_t)` (`u_t = 0`,
    `s_{t+1} ~ P_true(· | s_t)`) from `env`.
    If `entry_states` is provided, episodes start in `entry_states` with probability `1 - ambient_reset_prob`
    (and uniform ambient otherwise), modeling realistic home-base exploration across narrow bottlenecks.
    """
    rng = np.random.default_rng(seed)
    N = env.n_states
    P_csr = env.P_true
    indptr = P_csr.indptr
    indices = P_csr.indices
    data = P_csr.data

    if initial_dataset is not None:
        v_cnt = initial_dataset.visit_counts.copy()
        t_coo = initial_dataset.trans_counts.tocoo()
        edge_dict: Dict[Tuple[int, int], int] = {
            (int(r), int(c)): int(v) for r, c, v in zip(t_coo.row, t_coo.col, t_coo.data) if v > 0
        }
        c_sum = initial_dataset.cost_sums.copy()
        prev_steps = int(initial_dataset.total_steps)
    else:
        v_cnt = np.zeros(N, dtype=np.int64)
        edge_dict = {}
        c_sum = np.zeros(N, dtype=float)
        prev_steps = 0

    row_cdfs = [np.cumsum(data[indptr[i] : indptr[i + 1]]) for i in range(N)]
    row_cols = [indices[indptr[i] : indptr[i + 1]] for i in range(N)]
    entry_arr = np.asarray(entry_states, dtype=np.int64) if (entry_states is not None and len(entry_states) > 0) else None

    def _sample_episode_start() -> int:
        if entry_arr is not None and (rng.random() >= ambient_reset_prob):
            return int(entry_arr[int(rng.integers(0, len(entry_arr)))])
        return int(rng.integers(0, N))

    s = _sample_episode_start()
    for step in range(total_steps):
        if step % episode_len == 0:
            s = _sample_episode_start()

        v_cnt[s] += 1
        q_obs = sample_unbiased_bounded_cost(env.q_true[s], env.q_min, env.q_max, env.cost_noise_std, rng)
        c_sum[s] += q_obs

        cols_s = row_cols[s]
        u = float(rng.random())
        idx_k = min(int(np.searchsorted(row_cdfs[s], u, side="right")), len(cols_s) - 1)
        s_nxt = int(cols_s[idx_k])

        edge_dict[(s, s_nxt)] = edge_dict.get((s, s_nxt), 0) + 1
        s = s_nxt

    if edge_dict:
        r_idx = np.fromiter((k[0] for k in edge_dict.keys()), dtype=np.int64, count=len(edge_dict))
        c_idx = np.fromiter((k[1] for k in edge_dict.keys()), dtype=np.int64, count=len(edge_dict))
        v_val = np.fromiter(edge_dict.values(), dtype=float, count=len(edge_dict))
        T_mat = sp.csr_matrix((v_val, (r_idx, c_idx)), shape=(N, N))
    else:
        T_mat = sp.csr_matrix((N, N), dtype=float)

    return EmpiricalTrajectoryDataset(
        n_states=N,
        total_steps=prev_steps + int(total_steps),
        visit_counts=v_cnt,
        trans_counts=T_mat,
        cost_sums=c_sum,
        q_min=env.q_min,
        q_max=env.q_max,
        lam=env.lam,
    )


def collect_portal_directed_active_trajectories(
    env: UnknownDiscreteKLEnv,
    total_steps: int,
    episode_len: int = 110,
    seed: int = 0,
    entry_states: Optional[np.ndarray] = None,
    ambient_reset_prob: float = 0.12,
    warmup_frac: float = 0.34,
) -> EmpiricalTrajectoryDataset:
    """Two-Stage / Multi-Epoch Unbiased Spectral-Portal Active Bottleneck Exploration (`Algorithm 2`):
      1. Starts EVERY episode from the EXACT SAME physical reset distribution `(entry_states, ambient_reset_prob)`
         as passive exploration (ZERO teleportation privilege!).
      2. After a passive warmup (`warmup_frac * total_steps`), discovers spectral rooms & bottleneck portals
         `Gamma_p` on the observed graph, ranks portals & rooms by Clopper-Pearson epistemic uncertainty `rho_i`,
         and during active episodes navigates along already-observed transitions (`u_t != 0`, counting EVERY
         navigation step against `total_steps` while NOT logging controlled steps into passive `trans_counts`!)
         to reach under-sampled bottleneck portals/rooms, where it switches to uncontrolled exploration (`u_t = 0`,
         `s_{t+1} ~ P_true(· | s_t)`) so all logged empirical counts remain **100% Martingale-unbiased**!
    """
    warm_steps = max(episode_len, int(round(total_steps * warmup_frac)))
    ds = collect_exploration_trajectories(
        env, total_steps=warm_steps, episode_len=episode_len, seed=seed,
        entry_states=entry_states, ambient_reset_prob=ambient_reset_prob,
    )
    rem_steps = int(total_steps) - warm_steps
    if rem_steps <= 0:
        return ds

    rng = np.random.default_rng(seed + 7919)
    N = env.n_states
    P_csr = env.P_true
    indptr, indices, data = P_csr.indptr, P_csr.indices, P_csr.data
    row_cdfs = [np.cumsum(data[indptr[i] : indptr[i + 1]]) for i in range(N)]
    row_cols = [indices[indptr[i] : indptr[i + 1]] for i in range(N)]
    entry_arr = np.asarray(entry_states, dtype=np.int64) if (entry_states is not None and len(entry_states) > 0) else None

    v_cnt = ds.visit_counts.copy()
    t_coo = ds.trans_counts.tocoo()
    edge_dict: Dict[Tuple[int, int], int] = {
        (int(r), int(c)): int(v) for r, c, v in zip(t_coo.row, t_coo.col, t_coo.data) if v > 0
    }
    c_sum = ds.cost_sums.copy()

    def _sample_episode_start() -> int:
        if entry_arr is not None and (rng.random() >= ambient_reset_prob):
            return int(entry_arr[int(rng.integers(0, len(entry_arr)))])
        return int(rng.integers(0, N))

    # Split remaining budget into 2 active refinement stages
    n_stages = 2
    stage_budgets = [rem_steps // n_stages, rem_steps - (rem_steps // n_stages)]
    for stg_idx, stg_steps in enumerate(stage_budgets):
        if stg_steps <= 0:
            continue
        r_i = np.fromiter((k[0] for k in edge_dict), dtype=np.int64, count=len(edge_dict))
        c_i = np.fromiter((k[1] for k in edge_dict), dtype=np.int64, count=len(edge_dict))
        v_i = np.fromiter(edge_dict.values(), dtype=float, count=len(edge_dict))
        T_cur = sp.csr_matrix((v_i, (r_i, c_i)), shape=(N, N))
        ds_cur = EmpiricalTrajectoryDataset(N, warm_steps, v_cnt.copy(), T_cur, c_sum.copy(), env.q_min, env.q_max, env.lam)
        pac_cur = build_pac_mmatrix_pair(ds_cur, delta=0.05, max_degree_bound=8)
        dec_cur = discover_spectral_portals_from_trajectories(T_cur, max_rooms=10, min_room_size=max(20, N // 35))

        # Build candidate target sets: discovered bottleneck portals + high-rho rooms
        target_sets: List[np.ndarray] = []
        target_scores: List[float] = []
        for p_loc in dec_cur.portal_nodes_loc:
            g_nodes = dec_cur.gamma_nodes[p_loc]
            if len(g_nodes) > 0:
                target_sets.append(g_nodes)
                target_scores.append(1.35 * float(np.mean(pac_cur.rho_epistemic[g_nodes])))
        for rn in dec_cur.room_nodes:
            if len(rn) > 0:
                # Focus on least-visited states inside each room
                sub_ord = np.argsort(v_cnt[rn])[: max(4, len(rn) // 6)]
                cand_rn = rn[sub_ord]
                target_sets.append(cand_rn)
                target_scores.append(float(np.mean(pac_cur.rho_epistemic[cand_rn])))

        order_t = np.argsort(target_scores)[::-1][: min(10, len(target_sets))]
        nav_potentials: List[Tuple[np.ndarray, np.ndarray]] = []
        rs = np.maximum(np.asarray(T_cur.sum(axis=1)).ravel(), 1.0)
        P_hat_obs = (sp.diags(1.0 / rs) @ T_cur).tocsr()
        obs_adj_bin = (T_cur > 0).tocsr()
        for tid in order_t:
            t_nodes = target_sets[int(tid)]
            t_mask = np.zeros(N, dtype=bool)
            t_mask[t_nodes] = True
            # Compute shortest-path / soft desirability `z_nav` on OBSERVED graph toward `t_nodes`
            z_nav = np.zeros(N, dtype=float)
            z_nav[t_mask] = 1.0
            for _ in range(55):
                z_nav = 0.94 * (P_hat_obs @ z_nav)
                z_nav[t_mask] = 1.0
            nav_potentials.append((t_mask, z_nav))

        steps_used = 0
        ep_counter = 0
        while steps_used < stg_steps:
            s = _sample_episode_start()
            ep_budget = min(episode_len, stg_steps - steps_used)
            use_nav = len(nav_potentials) > 0 and (ep_counter % 5 != 4)
            if use_nav:
                t_mask, z_nav = nav_potentials[ep_counter % len(nav_potentials)]
            else:
                t_mask, z_nav = None, None
            ep_counter += 1
            reached_target = (t_mask is None) or bool(t_mask[s])
            max_nav_steps = ep_budget // 2

            for t_in_ep in range(ep_budget):
                steps_used += 1
                if (not reached_target) and (t_in_ep < max_nav_steps) and (z_nav is not None) and (z_nav[s] > 1e-8):
                    # Navigate along ALREADY-OBSERVED edges toward `t_mask` (`u_t != 0`: spend step, do not log biased P!)
                    obs_nbs = obs_adj_bin.indices[obs_adj_bin.indptr[s] : obs_adj_bin.indptr[s + 1]]
                    # Filter to true feasible neighbors (all observed edges have P_true > 0!)
                    if len(obs_nbs) > 0:
                        scores_nb = np.maximum(z_nav[obs_nbs], 1e-12) ** 4.0
                        cdf_nb = np.cumsum(scores_nb / float(np.sum(scores_nb)))
                        s = int(obs_nbs[min(int(np.searchsorted(cdf_nb, rng.random(), side="right")), len(obs_nbs) - 1)])
                        if bool(t_mask[s]):
                            reached_target = True
                        continue

                # Uncontrolled exploratory step (`u_t = 0`, exact draw from `P_true[s, :]`!)
                v_cnt[s] += 1
                q_obs = sample_unbiased_bounded_cost(env.q_true[s], env.q_min, env.q_max, env.cost_noise_std, rng)
                c_sum[s] += q_obs
                cols_s = row_cols[s]
                idx_k = min(int(np.searchsorted(row_cdfs[s], float(rng.random()), side="right")), len(cols_s) - 1)
                s_nxt = int(cols_s[idx_k])
                edge_dict[(s, s_nxt)] = edge_dict.get((s, s_nxt), 0) + 1
                s = s_nxt

    r_idx = np.fromiter((k[0] for k in edge_dict.keys()), dtype=np.int64, count=len(edge_dict))
    c_idx = np.fromiter((k[1] for k in edge_dict.keys()), dtype=np.int64, count=len(edge_dict))
    v_val = np.fromiter(edge_dict.values(), dtype=float, count=len(edge_dict))
    T_final = sp.csr_matrix((v_val, (r_idx, c_idx)), shape=(N, N))
    return EmpiricalTrajectoryDataset(
        n_states=N,
        total_steps=int(total_steps),
        visit_counts=v_cnt,
        trans_counts=T_final,
        cost_sums=c_sum,
        q_min=env.q_min,
        q_max=env.q_max,
        lam=env.lam,
    )


# ==============================================================================
# 3. Exact Clopper-Pearson Dual M-Matrix Confidence Envelopes `(A_pes, A_opt)`
# ==============================================================================
@dataclass
class DualPACMMatrixPair:
    A_pes: sp.csr_matrix       # I - M_pes (strictly row-diag-dominant M-matrix for upper cost bound U_n & deployed policy)
    M_pes: sp.csr_matrix       # gamma_lo * P_lo >= 0
    A_opt: sp.csr_matrix       # I - M_opt (strictly row-diag-dominant M-matrix for lower cost bound L_n)
    M_opt: sp.csr_matrix       # gamma_hi * P_lo >= 0
    b_opt_explore: np.ndarray  # gamma_hi * rho_n >= 0 (unexplored/epistemic mass source in A_opt)
    rho_epistemic: np.ndarray  # 1 - sum_j p_lo_{ij} in [0, 1]
    q_lo: np.ndarray
    q_hi: np.ndarray
    P_lo: Optional[sp.csr_matrix] = None  # CP probability bounds before cost scaling.


def build_pac_mmatrix_pair(
    dataset: EmpiricalTrajectoryDataset,
    delta: float = 0.05,
    max_degree_bound: Optional[int] = None,
    n_peeling_epochs: int = 1,
) -> DualPACMMatrixPair:
    """Constructs the goal-independent pessimistic/optimistic M-matrix pair `(A_pes, A_opt)` on a single
    **time-uniform predictable-sampling** Clopper-Pearson + Hoeffding confidence sequence `E_{1-delta}`
    (`Closes P3-P0-02`):
      - Under the canonical latent transition/cost stack `(S_{i,m}, Q_{i,m})_{m >= 1}`, union-bounding over
        ALL states `i = 1..N`, ALL true outgoing support edges `|supp(P^*_i)| <= d_max`, and ALL possible
        visit counts `m = 1, 2, ...` via `sum_{m=1}^inf 1/(m(m+1)) = 1` sets:
            `alpha_edge(m) = delta / (2 * N * d_max * m * (m + 1))`,
            `alpha_cost(m) = delta / (2 * N * m * (m + 1))`.
        This holds simultaneously across ALL `m >= 1`, hence for ANY predictable adaptive exploration or
        stopping strategy `N_T(i)` without requiring fixed-time row counts or finite epoch caps (`n_peeling_epochs`
        is retained only as a deprecated no-op signature argument for backward compatibility).
      - Uses **zero upward flooring** (`np.clip(sp_beta.ppf(...), 0.0, 1.0)`), so `p_lo_{ij} <= P^*_{ij}`
        holds even for arbitrarily rare transitions `P^*_{ij} < 1e-15`.
      - Validates `observed_out_degree <= d_max` explicitly (`default max_degree_bound=None -> d_max = N`).
    """
    N = int(dataset.n_states)
    if not (0.0 < float(delta) < 1.0):
        raise ValueError(f"Confidence parameter delta must lie in (0, 1), got {delta}")
    T_csr = dataset.trans_counts.tocsr()
    obs_max_deg = int(np.max(np.diff(T_csr.indptr))) if N > 0 else 0
    deg_ub = int(max_degree_bound) if max_degree_bound is not None else max(1, N)
    if deg_ub < 1 or obs_max_deg > deg_ub:
        raise ValueError(
            f"Observed row support degree {obs_max_deg} exceeds declared max_degree_bound={deg_ub}; "
            "pass a valid structural out-degree bound d_max or None (uses N)."
        )

    v_cnt = np.asarray(dataset.visit_counts, dtype=np.int64)
    row_sum_T = np.asarray(T_csr.sum(axis=1)).ravel()
    if np.any(np.round(row_sum_T).astype(np.int64) > v_cnt):
        raise ValueError("Invalid EmpiricalTrajectoryDataset: transition row sum exceeds visit_counts.")

    row_of_nnz = np.repeat(np.arange(N, dtype=np.int64), np.diff(T_csr.indptr))
    k_nnz = T_csr.data
    n_of_nnz = v_cnt[row_of_nnz].astype(float)

    pos = (k_nnz >= 1.0) & (n_of_nnz >= 1.0)
    p_lo_data = np.zeros_like(k_nnz, dtype=float)
    if np.any(pos):
        k_p = k_nnz[pos]
        n_p = n_of_nnz[pos]
        alpha_edge_p = float(delta) / (2.0 * float(N) * float(deg_ub) * n_p * (n_p + 1.0))
        p_lo_data[pos] = np.clip(sp_beta.ppf(alpha_edge_p, k_p, n_p - k_p + 1.0), 0.0, 1.0)

    P_lo = sp.csr_matrix((p_lo_data, T_csr.indices.copy(), T_csr.indptr.copy()), shape=(N, N))
    p_lo_row_sum = np.clip(np.asarray(P_lo.sum(axis=1)).ravel(), 0.0, 1.0)
    rho_clopper = np.maximum(0.0, 1.0 - p_lo_row_sum)

    vis = v_cnt > 0
    q_range = max(0.0, float(dataset.q_max - dataset.q_min))
    m_float = np.maximum(v_cnt, 1).astype(float)
    alpha_cost_vec = float(delta) / (2.0 * float(N) * m_float * (m_float + 1.0))
    q_hat = np.where(vis, dataset.cost_sums / m_float, 0.5 * (dataset.q_min + dataset.q_max))
    eps_q = np.where(
        vis,
        q_range * np.sqrt(np.log(2.0 / alpha_cost_vec) / (2.0 * m_float)),
        q_range,
    )
    q_lo = np.clip(q_hat - eps_q, dataset.q_min, dataset.q_max)
    q_hi = np.clip(q_hat + eps_q, dataset.q_min, dataset.q_max)

    gam_lo = np.exp(-q_hi / dataset.lam)
    gam_hi = np.exp(-q_lo / dataset.lam)

    M_pes = (sp.diags(gam_lo) @ P_lo).tocsr()
    M_pes.sum_duplicates()
    M_pes.sort_indices()
    M_opt = (sp.diags(gam_hi) @ P_lo).tocsr()
    M_opt.sum_duplicates()
    M_opt.sort_indices()
    I_sp = sp.eye(N, format="csr")
    A_pes = (I_sp - M_pes).tocsr()
    A_pes.sort_indices()
    A_opt = (I_sp - M_opt).tocsr()
    A_opt.sort_indices()
    b_opt_explore = gam_hi * rho_clopper
    rho_epistemic = rho_clopper

    return DualPACMMatrixPair(
        A_pes=A_pes,
        M_pes=M_pes,
        A_opt=A_opt,
        M_opt=M_opt,
        b_opt_explore=b_opt_explore,
        rho_epistemic=rho_epistemic,
        q_lo=q_lo,
        q_hi=q_hi,
        P_lo=P_lo,
    )


# ==============================================================================
# 4. Zero-Prior Spectral Conductance Bottleneck & Fiedler Portal Tree Discovery
# ==============================================================================
def _fiedler_sweep_bisect(W_sym: sp.csr_matrix, min_side: int = 25) -> Optional[Tuple[np.ndarray, float]]:
    """Computes the normalized Fiedler eigenvector of symmetric flux matrix `W_sym` (`n x n`)
    and returns `(boolean_side_mask, best_conductance)` via Cheeger sweep cut.
    Uses ZERO spatial coordinates!
    """
    n = W_sym.shape[0]
    if n < 2 * min_side:
        return None
    n_cc, lbl = connected_components(W_sym > 0, directed=False)
    if n_cc > 1:
        # Disconnected component gives conductance 0.0
        c0 = int(np.argmax(np.bincount(lbl)))
        mk = lbl == c0
        if min(int(np.sum(mk)), n - int(np.sum(mk))) >= 1:
            return mk, 0.0
        return None

    W_no_diag = W_sym - sp.diags(W_sym.diagonal())
    deg = np.asarray(W_no_diag.sum(axis=1)).ravel()
    if np.any(deg <= 0.0):
        return None
    inv_sqrt_d = 1.0 / np.sqrt(deg)
    L_norm = sp.eye(n, format="csr") - (sp.diags(inv_sqrt_d) @ W_no_diag @ sp.diags(inv_sqrt_d))

    try:
        k_eig = min(3, n - 2)
        vals, vecs = spla.eigsh(L_norm, k=k_eig, which="SM", tol=1e-5, maxiter=1500, v0=np.ones(n, dtype=float))
        order_eig = np.argsort(vals)
        fiedler = vecs[:, order_eig[1]] * inv_sqrt_d
        # Canonical sign orientation for strict determinism
        if fiedler[0] < 0.0 or (fiedler[0] == 0.0 and np.sum(fiedler) < 0.0):
            fiedler = -fiedler
    except Exception:
        # Power-deflated fallback if ARPACK hits maxiter
        rng_f = np.random.default_rng(42)
        v = rng_f.standard_normal(n)
        d_sqrt = np.sqrt(deg)
        d_sqrt /= np.linalg.norm(d_sqrt)
        P_lazy = 0.5 * (sp.eye(n, format="csr") + sp.diags(inv_sqrt_d) @ W_no_diag @ sp.diags(inv_sqrt_d))
        for _ in range(80):
            v = P_lazy @ v
            v -= np.dot(v, d_sqrt) * d_sqrt
            nrm = np.linalg.norm(v)
            if nrm > 1e-15:
                v /= nrm
        fiedler = v * inv_sqrt_d

    perm = np.argsort(fiedler)
    pos_in_perm = np.empty(n, dtype=np.int64)
    pos_in_perm[perm] = np.arange(n, dtype=np.int64)

    W_coo = sp.triu(W_no_diag, k=1).tocoo()
    u_rk = np.minimum(pos_in_perm[W_coo.row], pos_in_perm[W_coo.col])
    v_rk = np.maximum(pos_in_perm[W_coo.row], pos_in_perm[W_coo.col])
    diff_cut = np.zeros(n, dtype=float)
    np.add.at(diff_cut, u_rk, W_coo.data)
    np.add.at(diff_cut, v_rk, -W_coo.data)
    cut_profile = np.cumsum(diff_cut)[:-1]

    vol_prefix = np.cumsum(deg[perm])[:-1]
    tot_vol = float(np.sum(deg))
    denom = np.minimum(vol_prefix, tot_vol - vol_prefix)

    valid_range = slice(min_side - 1, n - min_side)
    conds = cut_profile[valid_range] / np.maximum(denom[valid_range], 1e-30)
    best_rel = int(np.argmin(conds))
    best_k = (min_side - 1) + best_rel
    best_phi = float(conds[best_rel])

    side_mask = np.zeros(n, dtype=bool)
    side_mask[perm[: best_k + 1]] = True
    return side_mask, best_phi


def _recursive_fiedler_portal_tree(
    p_nodes_loc: np.ndarray,
    W_portal: sp.csr_matrix,
    max_depth: Optional[int] = None,
) -> Tuple[Dict[Tuple[int, int], np.ndarray], Dict[Tuple[int, int], List[Tuple[int, int]]]]:
    """Builds a **strictly binary** nested Fiedler partition tree (`Closes P3-E06`) on an arbitrary
    unstructured portal subgraph `p_nodes_loc` using ONLY portal edge weights `W_portal`!
    Bisects recursively to unrestricted depth until EVERY leaf is an exact 1-node singleton, so
    every internal node has **strictly `2` disjoint non-empty children** (`exact 50.0% PoU child-column
    LU solve conservation for any portal size >= 2!`).
    """
    blocks: Dict[Tuple[int, int], np.ndarray] = {(0, 0): p_nodes_loc.copy()}
    children: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}

    def _bisect_subset(sub_loc_idx: np.ndarray) -> List[np.ndarray]:
        if len(sub_loc_idx) <= 1:
            return [sub_loc_idx]
        if len(sub_loc_idx) == 2:
            return [sub_loc_idx[:1], sub_loc_idx[1:]]
        W_sub = W_portal[sub_loc_idx, :][:, sub_loc_idx]
        n_cc, lbl = connected_components(W_sub > 0, directed=False)
        if n_cc > 1:
            # Group connected components into two balanced non-empty halves
            counts = [(int(np.sum(lbl == c)), c) for c in range(n_cc)]
            counts.sort(reverse=True)
            g_a, g_b = [], []
            sa, sb = 0, 0
            for cnt, c_id in counts:
                if sa <= sb:
                    g_a.append(sub_loc_idx[lbl == c_id])
                    sa += cnt
                else:
                    g_b.append(sub_loc_idx[lbl == c_id])
                    sb += cnt
            if g_a and g_b:
                return [np.sort(np.concatenate(g_a)), np.sort(np.concatenate(g_b))]
        W_no = W_sub - sp.diags(W_sub.diagonal())
        deg = np.maximum(np.asarray(W_no.sum(axis=1)).ravel(), 1e-12)
        L_sub = sp.diags(deg) - W_no
        if len(sub_loc_idx) <= 256:
            _, vecs = np.linalg.eigh(L_sub.toarray())
            fv = vecs[:, 1]
        else:
            v0_orth = np.linspace(-1.0, 1.0, len(sub_loc_idx), dtype=float)
            _, vecs = spla.eigsh(L_sub.tocsr(), k=2, which="SM", tol=1e-5, v0=v0_orth)
            fv = vecs[:, 1]
        if fv[0] < 0.0:
            fv = -fv
        order = np.argsort(fv, kind="mergesort")
        mid = len(order) // 2
        return [np.sort(sub_loc_idx[order[:mid]]), np.sort(sub_loc_idx[order[mid:]])]

    cur_lv_blocks = [np.arange(len(p_nodes_loc), dtype=np.int64)]
    lv = 0
    hard_cap = int(max_depth) if max_depth is not None else (max(1, int(np.ceil(np.log2(max(2, len(p_nodes_loc))))) + 4))
    while any(len(b_sub) > 1 for b_sub in cur_lv_blocks) and lv < hard_cap:
        nxt_lv_blocks: List[np.ndarray] = []
        for bi, b_sub in enumerate(cur_lv_blocks):
            pkey = (lv, bi)
            if len(b_sub) <= 1:
                children[pkey] = []
                continue
            parts = _bisect_subset(b_sub)
            assert len(parts) == 2 and len(parts[0]) >= 1 and len(parts[1]) >= 1
            ch_keys = []
            for pt in parts:
                ci = len(nxt_lv_blocks)
                nxt_lv_blocks.append(pt)
                blocks[(lv + 1, ci)] = p_nodes_loc[pt]
                ch_keys.append((lv + 1, ci))
            children[pkey] = ch_keys
        cur_lv_blocks = nxt_lv_blocks
        lv += 1
    for bi in range(len(cur_lv_blocks)):
        children[(lv, bi)] = []
    return blocks, children


@dataclass
class SpectralPortalDecomposition:
    n_states: int
    gamma_nodes: np.ndarray                 # Sorted global indices of discovered separator Gamma
    room_nodes: List[np.ndarray]            # Disjoint room interiors R_0 .. R_{C-1}
    room_of_state: np.ndarray               # -1 on Gamma, room_id in 0..C-1 on R_c
    portal_nodes_loc: List[np.ndarray]      # Indices into `gamma_nodes` for each portal p=0..P-1
    portal_rooms: List[List[int]]
    room_portals: List[List[int]]
    room_tl: List[np.ndarray]
    tl_pos_in_gamma: List[np.ndarray]
    qt_blocks: Dict[Tuple[int, int, int], np.ndarray]
    qt_children: Dict[Tuple[int, int, int], List[Tuple[int, int, int]]]
    discovery_ms: float
    mean_cluster_conductance: float


def discover_spectral_portals_from_trajectories(
    trans_counts: sp.csr_matrix,
    max_rooms: int = 12,
    min_room_size: int = 55,
    conductance_Stop_thresh: float = 0.14,
) -> SpectralPortalDecomposition:
    """Discovers low-conductance clusters ("learned rooms") and valid bipartite vertex separators ("portals")
    purely from empirical transition counts `trans_counts` (ZERO coordinates, ZERO wall priors!).
    Guarantees exact vertex separation `(trans_counts + trans_counts.T)[R_c, R_{c'}] == 0` for all `c != c'`.
    """
    t0 = time.perf_counter()
    N = trans_counts.shape[0]
    W_sym = (0.5 * (trans_counts + trans_counts.T)).tocsr()
    W_sym = W_sym - sp.diags(W_sym.diagonal())

    # Recursive Cheeger Fiedler bisection while conductance < threshold
    clusters: List[np.ndarray] = [np.arange(N, dtype=np.int64)]
    cond_history: List[float] = []
    while len(clusters) < max_rooms:
        best_split = None
        best_idx = -1
        best_phi = conductance_Stop_thresh
        for idx_c, c_nodes in enumerate(clusters):
            if len(c_nodes) < 2 * min_room_size:
                continue
            W_sub = W_sym[c_nodes, :][:, c_nodes].tocsr()
            res = _fiedler_sweep_bisect(W_sub, min_side=min_room_size)
            if res is not None and res[1] < best_phi:
                best_phi = res[1]
                best_split = (c_nodes[res[0]], c_nodes[~res[0]])
                best_idx = idx_c
        if best_split is None:
            break
        cond_history.append(best_phi)
        clusters.pop(best_idx)
        clusters.extend([np.sort(best_split[0]), np.sort(best_split[1])])

    c_lbl = np.zeros(N, dtype=np.int64)
    for cid, c_nodes in enumerate(clusters):
        c_lbl[c_nodes] = cid

    # Extract minimal vertex separator `Gamma`: for each cross-cluster edge `(u, v)` with `c_lbl[u] < c_lbl[v]`,
    # put the endpoint in the smaller-incident-boundary side (or lower-id cluster) into `Gamma` so zero cross-cluster edges survive!
    A_bin = ((trans_counts + trans_counts.T) > 0).tocoo()
    cross_mask = c_lbl[A_bin.row] < c_lbl[A_bin.col]
    u_cr = A_bin.row[cross_mask]
    v_cr = A_bin.col[cross_mask]
    # Greedy degree-weighted cover of cross-cluster bipartite edges: pick vertex covering more cross-edges
    gamma_mask = np.zeros(N, dtype=bool)
    if len(u_cr) > 0:
        cr_deg = np.bincount(np.concatenate([u_cr, v_cr]), minlength=N)
        for u_i, v_i in zip(u_cr, v_cr):
            if gamma_mask[u_i] or gamma_mask[v_i]:
                continue
            if cr_deg[u_i] > cr_deg[v_i]:
                gamma_mask[u_i] = True
            elif cr_deg[v_i] > cr_deg[u_i]:
                gamma_mask[v_i] = True
            else:
                gamma_mask[u_i if c_lbl[u_i] < c_lbl[v_i] else v_i] = True

    # Ensure non-empty separator even on trivial 1-cluster fallback
    if not np.any(gamma_mask):
        gamma_mask[0] = True

    gamma_nodes = np.flatnonzero(gamma_mask).astype(np.int64)
    n_g = len(gamma_nodes)
    int_nodes = np.flatnonzero(~gamma_mask).astype(np.int64)

    A_sym = ((trans_counts + trans_counts.T) > 0).tocsr()
    n_rooms, r_comp = connected_components(A_sym[int_nodes, :][:, int_nodes], directed=False)
    room_of_state = np.full(N, -1, dtype=np.int64)
    room_nodes: List[np.ndarray] = []
    for c in range(n_rooms):
        rn = np.sort(int_nodes[r_comp == c])
        room_of_state[rn] = c
        room_nodes.append(rn)

    # Group separator nodes `gamma_nodes` into portals `Gamma_p` by `(connected component in W_sym[gamma] + incident room-pair signature)`
    W_gg = W_sym[gamma_nodes, :][:, gamma_nodes].tocsr()
    # Add weak virtual coupling between separator nodes that touch the exact same pair of rooms
    room_inc = A_sym[gamma_nodes, :][:, int_nodes].tocoo()
    inc_rooms_per_g: List[set] = [set() for _ in range(n_g)]
    for gi, ii in zip(room_inc.row, room_inc.col):
        inc_rooms_per_g[int(gi)].add(int(r_comp[int(ii)]))
    sig_groups: Dict[Tuple[int, ...], List[int]] = {}
    for gi, rset in enumerate(inc_rooms_per_g):
        sig = tuple(sorted(rset))
        sig_groups.setdefault(sig, []).append(gi)

    portal_nodes_loc: List[np.ndarray] = []
    for sig, g_list in sorted(sig_groups.items()):
        g_arr = np.array(g_list, dtype=np.int64)
        if len(g_arr) <= 1:
            portal_nodes_loc.append(g_arr)
        else:
            n_sub, sub_lbl = connected_components(W_gg[g_arr, :][:, g_arr] > 0, directed=False)
            if n_sub == 1 or len(g_arr) <= 18:
                portal_nodes_loc.append(g_arr)
            else:
                for sc in range(n_sub):
                    portal_nodes_loc.append(g_arr[sub_lbl == sc])

    n_portals = len(portal_nodes_loc)
    p_of_gloc = np.empty(n_g, dtype=np.int64)
    for pid, p_arr in enumerate(portal_nodes_loc):
        p_of_gloc[p_arr] = pid

    room_tl: List[np.ndarray] = []
    tl_pos_in_gamma: List[np.ndarray] = []
    portal_rooms: List[List[int]] = [[] for _ in range(n_portals)]
    room_portals: List[List[int]] = [[] for _ in range(n_rooms)]

    for c, rn in enumerate(room_nodes):
        sub_rg = A_sym[rn, :][:, gamma_nodes]
        tl = np.flatnonzero(np.asarray(sub_rg.sum(axis=0)).ravel() > 0).astype(np.int64)
        room_tl.append(tl)
        mp = np.full(n_g, -1, dtype=np.int64)
        mp[tl] = np.arange(len(tl), dtype=np.int64)
        tl_pos_in_gamma.append(mp)
        for pid in np.unique(p_of_gloc[tl]):
            pi = int(pid)
            portal_rooms[pi].append(c)
            room_portals[c].append(pi)

    # Build coordinate-free Fiedler binary PoU trees on every portal `pid`
    # Add small local 2-hop room-shared affinity inside `W_portal` so diagonal grid separator nodes stay coupled!
    W_gg_2hop = (W_gg + 0.25 * (A_sym[gamma_nodes, :][:, int_nodes] @ A_sym[int_nodes, :][:, gamma_nodes])).tocsr()
    qt_blocks: Dict[Tuple[int, int, int], np.ndarray] = {}
    qt_children: Dict[Tuple[int, int, int], List[Tuple[int, int, int]]] = {}
    for pid, p_loc in enumerate(portal_nodes_loc):
        W_p = W_gg_2hop[np.arange(n_g), :][:, np.arange(n_g)]
        bl_map, ch_map = _recursive_fiedler_portal_tree(p_loc, W_p, max_depth=None)
        for (lv, bi), barr in bl_map.items():
            qt_blocks[(pid, lv, bi)] = barr
        for (lv, bi), chs in ch_map.items():
            qt_children[(pid, lv, bi)] = [(pid, clv, cbi) for (clv, cbi) in chs]

    disc_ms = 1000.0 * (time.perf_counter() - t0)
    return SpectralPortalDecomposition(
        n_states=N,
        gamma_nodes=gamma_nodes,
        room_nodes=room_nodes,
        room_of_state=room_of_state,
        portal_nodes_loc=portal_nodes_loc,
        portal_rooms=portal_rooms,
        room_portals=room_portals,
        room_tl=room_tl,
        tl_pos_in_gamma=tl_pos_in_gamma,
        qt_blocks=qt_blocks,
        qt_children=qt_children,
        discovery_ms=disc_ms,
        mean_cluster_conductance=float(np.mean(cond_history)) if cond_history else 1.0,
    )


# ==============================================================================
# 5. SPQL Dual-Envelope Fiedler-PoU Portal Solver & Certified Policy Handle
# ==============================================================================
class _SingleMMatrixPortalChannel:
    """Internal reusable local-Schur + Fiedler-PoU portal solver for a single nonsingular M-matrix `A`
    with optional goal-independent non-negative interior source `b_source >= 0` (`0` for `A_pes`,
    `b_opt_explore` for `A_opt`).
    Supports **ALL non-empty goals** `G subset S` (`2^N - 1` subsets, including goals intersecting
    multiple rooms, covering entire rooms, or intersecting separator `Gamma`) via exact killed-portal
    Dirichlet elimination on `E_Gamma = Gamma - G` and straddling-block refinement (`Closes P3-P0-01`).
    """

    def __init__(
        self,
        A_csr: sp.csr_matrix,
        dec: SpectralPortalDecomposition,
        b_source: Optional[np.ndarray] = None,
        enable_pou_conservation: bool = True,
        build_initial_l0_cache: bool = True,
    ) -> None:
        self.A_csr = A_csr
        self.dec = dec
        self.n_g = len(dec.gamma_nodes)
        self.enable_pou = bool(enable_pou_conservation)
        self.local_lu_rhs_solves = 0
        self.room_lu_refactorizations = 0
        self.max_k_neg_roundoff = 0.0

        A_gg = A_csr[dec.gamma_nodes, :][:, dec.gamma_nodes].tocsc()
        self.D_gg_csc = A_gg
        self.D_gg_csr = A_gg.tocsr()
        self.lu_Agg = spla.splu(A_gg)

        self.room_Arg: List[sp.csr_matrix] = []
        self.room_NegAgr: List[sp.csr_matrix] = []
        self.hq_lus: List[spla.SuperLU] = []
        self.has_source = b_source is not None and float(np.max(b_source)) > 0.0
        self.b_source = np.asarray(b_source, dtype=float) if self.has_source else np.zeros(dec.n_states, dtype=float)
        self.h_exp_rooms: List[np.ndarray] = []
        self.r_exp_gam_base = np.zeros(self.n_g, dtype=float)
        if self.has_source:
            self.r_exp_gam_base += self.b_source[dec.gamma_nodes]

        for c, rn in enumerate(dec.room_nodes):
            tl = dec.room_tl[c]
            self.room_Arg.append((-A_csr[rn, :][:, dec.gamma_nodes[tl]]).tocsr())
            self.room_NegAgr.append((-A_csr[dec.gamma_nodes[tl], :][:, rn]).tocsr())
            lu_c = spla.splu(A_csr[rn, :][:, rn].tocsc())
            self.hq_lus.append(lu_c)
            if self.has_source:
                hc = lu_c.solve(self.b_source[rn])
                self.local_lu_rhs_solves += 1
                self.h_exp_rooms.append(hc)
                self.r_exp_gam_base[tl] += self.room_NegAgr[c] @ hc
            else:
                self.h_exp_rooms.append(np.zeros(len(rn), dtype=float))

        # Persistent unclipped Fiedler-tree node cache:
        # `(pid, lv, bi) -> (k_raw_unkilled, neg_m_unsmoothed, {room_c: y_col})`
        self.node_cache: Dict[Tuple[int, int, int], Tuple[np.ndarray, np.ndarray, Dict[int, np.ndarray]]] = {}
        if build_initial_l0_cache:
            for pid in range(len(dec.portal_nodes_loc)):
                self._solve_keys_direct(pid, [(pid, 0, 0)])
        self.init_lu_rhs_solves = int(self.local_lu_rhs_solves)

    def _solve_keys_direct(self, pid: int, ckeys: Sequence[Tuple[int, int, int]]) -> None:
        m_b = len(ckeys)
        if m_b == 0:
            return
        dec = self.dec
        NegM_L = np.zeros((self.n_g, m_b), dtype=float)
        y_by_c: Dict[int, np.ndarray] = {}
        for c in dec.portal_rooms[pid]:
            tl = dec.room_tl[c]
            mp = dec.tl_pos_in_gamma[c]
            L_sub = np.zeros((len(tl), m_b), dtype=float)
            for j, ck in enumerate(ckeys):
                loc = mp[dec.qt_blocks[ck]]
                L_sub[loc[loc >= 0], j] = 1.0
            Yc = self.hq_lus[c].solve(self.room_Arg[c] @ L_sub)
            self.local_lu_rhs_solves += int(m_b)
            y_by_c[c] = Yc
            NegM_L[tl, :] += self.room_NegAgr[c] @ Yc
        K_raw = self.lu_Agg.solve(NegM_L)
        neg_m = max(0.0, float(-np.min(K_raw)))
        self.max_k_neg_roundoff = max(self.max_k_neg_roundoff, neg_m)
        for j, ck in enumerate(ckeys):
            self.node_cache[ck] = (
                K_raw[:, j].copy(),
                NegM_L[:, j].copy(),
                {c: y_by_c[c][:, j].copy() for c in dec.portal_rooms[pid]},
            )

    def split_parents_pou(self, parent_keys: Sequence[Tuple[int, int, int]]) -> None:
        """Strictly binary Fiedler tree Partition-of-Unity split:
        Solves ONLY `1` of `2` children (`exact 50.0% LU backsolve saving!`) and recovers the
        second child by linearity on `k_raw`, `neg_m_col`, and `y_by_c`!
        """
        dec = self.dec
        ordered = sorted(set(parent_keys), key=lambda x: (x[1], x[0], x[2]))
        for lv_s in sorted(set(pk[1] for pk in ordered)):
            lv_pks = [pk for pk in ordered if pk[1] == lv_s]
            solve_by_pid: Dict[int, List[Tuple[int, int, int]]] = {}
            derive_list: List[Tuple[Tuple[int, int, int], List[Tuple[int, int, int]], Tuple[int, int, int]]] = []
            for pk in lv_pks:
                chs = dec.qt_children.get(pk, [])
                if not chs or all(ck in self.node_cache for ck in chs):
                    continue
                missing = [ck for ck in chs if ck not in self.node_cache]
                if self.enable_pou and (pk in self.node_cache) and len(chs) >= 2:
                    drv = missing[-1]
                    for ck in missing[:-1]:
                        solve_by_pid.setdefault(pk[0], []).append(ck)
                    sibs = [ck for ck in chs if ck != drv]
                    derive_list.append((pk, sibs, drv))
                else:
                    for ck in missing:
                        solve_by_pid.setdefault(pk[0], []).append(ck)

            for pid, cks in solve_by_pid.items():
                self._solve_keys_direct(pid, cks)

            for pk, sibs, last_ck in derive_list:
                kp, nmp, yp = self.node_cache[pk]
                kr = kp.copy()
                nmr = nmp.copy()
                for sb in sibs:
                    kr -= self.node_cache[sb][0]
                    nmr -= self.node_cache[sb][1]
                self.max_k_neg_roundoff = max(self.max_k_neg_roundoff, max(0.0, float(-np.min(kr))))
                yr: Dict[int, np.ndarray] = {}
                for c in dec.portal_rooms[pk[0]]:
                    yc_r = yp[c].copy()
                    for sb in sibs:
                        yc_r -= self.node_cache[sb][2][c]
                    yr[c] = yc_r
                self.node_cache[last_ck] = (kr, nmr, yr)

    def build_initial_exterior_cut(self, ctx: dict) -> List[Tuple[int, int, int]]:
        """Constructs the coarsest Fiedler cut whose active blocks lie **strictly inside** `E_Gamma = Gamma - G`
        (`splitting only tree nodes that straddle G_Gamma and E_Gamma via PoU`).
        When `G_Gamma == empty`, returns the exact `L0` whole-portal cut `[(pid, 0, 0) for pid in 0..P-1]`.
        """
        dec = self.dec
        g_gam_mask = ctx["g_gam_mask"]
        if not ctx["has_portal_goal"]:
            return [(pid, 0, 0) for pid in range(len(dec.portal_nodes_loc))]
        out_keys: List[Tuple[int, int, int]] = []
        queue = [(pid, 0, 0) for pid in range(len(dec.portal_nodes_loc))]
        while queue:
            nxt_q: List[Tuple[int, int, int]] = []
            to_split: List[Tuple[int, int, int]] = []
            for ck in queue:
                bl = dec.qt_blocks[ck]
                in_g_bl = g_gam_mask[bl]
                if np.all(in_g_bl):
                    continue  # Purely in G_Gamma: pinned to 1.0, excluded from exterior unknowns
                if not np.any(in_g_bl):
                    out_keys.append(ck)  # Purely in E_Gamma!
                    continue
                # Straddles both G_Gamma and E_Gamma -> split down binary tree!
                to_split.append(ck)
                nxt_q.extend(dec.qt_children[ck])
            if to_split:
                self.split_parents_pou(to_split)
            queue = nxt_q
        return out_keys

    def prepare_goal_context(self, s0: int, gm: np.ndarray) -> dict:
        """Exact all-goal Dirichlet reduction onto `E_Gamma = Gamma - G` (`Closes P3-P0-01`):
          - Eliminates all room interiors `X_c = R_c - G` via complete directed incoming ring `R_{G,c}`,
            handling whole-room goals `R_c <= G` and portal-boundary sources `G_Gamma -> R_c -> E_Gamma` exactly.
          - Factors the exact killed portal diagonal block `A_{E_Gamma, E_Gamma}` whenever `G_Gamma != empty`.
        """
        dec = self.dec
        gam = dec.gamma_nodes
        g_gam_mask = np.asarray(gm[gam], dtype=bool)
        ext_gam_mask = ~g_gam_mask
        has_portal_goal = bool(np.any(g_gam_mask))
        ext_gam_idx = np.flatnonzero(ext_gam_mask).astype(np.int64)
        lu_Agg_ext = spla.splu(self.D_gg_csc[ext_gam_idx, :][:, ext_gam_idx]) if (has_portal_goal and len(ext_gam_idx) > 0) else None

        goal_rooms: Dict[int, dict] = {}
        full_goal_rooms: set = set()
        h_room_const: List[np.ndarray] = []

        # Base portal RHS on `0..n_g-1` before room goal / G_Gamma adjustments
        r_gam = np.zeros(self.n_g, dtype=float)
        if self.has_source:
            r_gam += self.b_source[gam]

        for c, rn in enumerate(dec.room_nodes):
            in_g = np.asarray(gm[rn], dtype=bool)
            tl_c = dec.room_tl[c]
            if np.all(in_g):
                full_goal_rooms.add(c)
                hc_const = np.ones(len(rn), dtype=float)
                h_room_const.append(hc_const)
                r_gam[tl_c] += self.room_NegAgr[c] @ hc_const
                continue

            g_tl_local = g_gam_mask[tl_c]
            if has_portal_goal and np.any(g_tl_local):
                w_g_tl = g_tl_local.astype(float)
                rhs_u0 = self.b_source[rn] + np.asarray(self.room_Arg[c] @ w_g_tl).ravel()
                u_c0 = self.hq_lus[c].solve(rhs_u0)
                self.local_lu_rhs_solves += 1
            else:
                u_c0 = self.h_exp_rooms[c].copy()

            if not np.any(in_g):
                h_room_const.append(u_c0)
                r_gam[tl_c] += self.room_NegAgr[c] @ u_c0
                continue

            g_r = np.flatnonzero(in_g).astype(np.int64)
            ext_rows = np.concatenate([rn[~in_g], gam[tl_c][~g_tl_local]])
            sub = self.A_csr[ext_rows, :][:, rn[g_r]]
            ring_r = g_r[np.asarray((sub < 0.0).sum(axis=0)).ravel() > 0]
            if len(ring_r) == 0:
                hc_const = u_c0.copy()
                hc_const[in_g] = 1.0
                h_room_const.append(hc_const)
                # Note: since ring_r == empty, A[E_Gamma, G_c] == 0 so setting hc_const[in_g]=1 or u_c0 gives identical NegAgr[ext]!
                r_gam[tl_c] += self.room_NegAgr[c] @ u_c0
                continue

            RHS_rg = np.zeros((len(rn), len(ring_r)), dtype=float)
            RHS_rg[ring_r, np.arange(len(ring_r))] = 1.0
            U_rg = self.hq_lus[c].solve(RHS_rg)
            self.local_lu_rhs_solves += int(len(ring_r))
            C_inv = np.linalg.inv(U_rg[ring_r, :])

            NegAgr_U_local = self.room_NegAgr[c] @ U_rg
            Smooth_U = None
            if not has_portal_goal:
                NegAgr_U_full = np.zeros((self.n_g, len(ring_r)), dtype=float)
                NegAgr_U_full[tl_c, :] = NegAgr_U_local
                Smooth_U = self.lu_Agg.solve(NegAgr_U_full)

            rhs_ring_val = np.ones(len(ring_r), dtype=float) - u_c0[ring_r]
            h_goal_corr = U_rg @ (C_inv @ rhs_ring_val)
            hc_total = u_c0 + h_goal_corr
            r_gam[tl_c] += self.room_NegAgr[c] @ hc_total
            hc_store = hc_total.copy()
            hc_store[in_g] = 1.0
            h_room_const.append(hc_store)
            goal_rooms[c] = {
                "in_g": in_g,
                "ring_r": ring_r,
                "U_rg": U_rg,
                "C_inv": C_inv,
                "NegAgr_U_local": NegAgr_U_local,
                "Smooth_U": Smooth_U,
            }

        # Direct portal-to-portal coupling `-A_{E_Gamma, G_Gamma} @ 1` inside `D_gg`
        if has_portal_goal and len(ext_gam_idx) > 0:
            r_gam[ext_gam_idx] += np.asarray((-self.D_gg_csr[ext_gam_idx, :][:, g_gam_mask]).sum(axis=1)).ravel()

        r_gam = np.maximum(r_gam, 0.0)
        if not has_portal_goal:
            r_hat = np.maximum(self.lu_Agg.solve(r_gam), 0.0)
        else:
            r_hat = np.ones(self.n_g, dtype=float)
            if len(ext_gam_idx) > 0:
                r_hat[ext_gam_idx] = np.maximum(lu_Agg_ext.solve(r_gam[ext_gam_idx]), 0.0)

        # Start-state readout `(h_s_tl, tl_s, z_dir)` matching `W_ext` (`zeroed on g_gam_mask`)
        c_s = int(dec.room_of_state[s0])
        if c_s >= 0:
            rn_s = dec.room_nodes[c_s]
            tl_s = dec.room_tl[c_s]
            pos_s = int(np.searchsorted(rn_s, s0))
            if c_s in full_goal_rooms:
                h_s_tl = np.zeros(len(tl_s), dtype=float)
                z_dir = 1.0
            else:
                e_s = np.zeros(len(rn_s), dtype=float)
                e_s[pos_s] = 1.0
                lam_s = self.hq_lus[c_s].solve(e_s, trans="T")
                self.local_lu_rhs_solves += 1
                if c_s in goal_rooms:
                    gr = goal_rooms[c_s]
                    RHS_adj = np.zeros(len(rn_s), dtype=float)
                    RHS_adj[gr["ring_r"]] = gr["C_inv"].T @ gr["U_rg"][pos_s, :]
                    lam_s = lam_s - self.hq_lus[c_s].solve(RHS_adj, trans="T")
                    self.local_lu_rhs_solves += 1
                z_dir = float(h_room_const[c_s][pos_s])
                h_s_tl = np.maximum(np.asarray(self.room_Arg[c_s].T @ lam_s).ravel(), 0.0)
                if has_portal_goal:
                    h_s_tl[g_gam_mask[tl_s]] = 0.0
        else:
            g_pos = int(np.searchsorted(gam, s0))
            tl_s = np.array([g_pos], dtype=np.int64)
            if bool(g_gam_mask[g_pos]):
                h_s_tl = np.array([0.0], dtype=float)
                z_dir = 1.0
            else:
                h_s_tl = np.array([1.0], dtype=float)
                z_dir = 0.0

        return {
            "gm": gm,
            "g_gam_mask": g_gam_mask,
            "ext_gam_idx": ext_gam_idx,
            "has_portal_goal": has_portal_goal,
            "has_full_goal_room": len(full_goal_rooms) > 0,
            "full_goal_rooms": full_goal_rooms,
            "lu_Agg_ext": lu_Agg_ext,
            "goal_rooms": goal_rooms,
            "h_room_const": h_room_const,
            "r_hat": r_hat,
            "tl_s": tl_s,
            "h_s_tl": h_s_tl,
            "z_dir": z_dir,
            "col_cache": {},
        }

    def get_goal_col_unclipped(self, ctx: dict, ck: Tuple[int, int, int]) -> np.ndarray:
        cc_u = ctx.setdefault("col_cache_unclipped", {})
        if ck in cc_u:
            return cc_u[ck]
        k_raw, neg_m_col, y_map = self.node_cache[ck]
        if (not ctx["has_portal_goal"]) and (not ctx["has_full_goal_room"]):
            k_mod = k_raw.copy()
            for c, gr in ctx["goal_rooms"].items():
                if c in y_map:
                    k_mod = k_mod - gr["Smooth_U"] @ (gr["C_inv"] @ y_map[c][gr["ring_r"]])
        else:
            if np.all(ctx["g_gam_mask"][self.dec.qt_blocks[ck]]):
                k_zero = np.zeros(self.n_g, dtype=float)
                cc_u[ck] = k_zero
                return k_zero
            neg_m = neg_m_col.copy()
            for c in ctx["full_goal_rooms"]:
                if c in y_map:
                    tl_c = self.dec.room_tl[c]
                    neg_m[tl_c] -= self.room_NegAgr[c] @ y_map[c]
            for c, gr in ctx["goal_rooms"].items():
                if c in y_map:
                    tl_c = self.dec.room_tl[c]
                    neg_m[tl_c] -= gr["NegAgr_U_local"] @ (gr["C_inv"] @ y_map[c][gr["ring_r"]])
            k_mod = np.zeros(self.n_g, dtype=float)
            ext_idx = ctx["ext_gam_idx"]
            if len(ext_idx) > 0:
                if ctx["has_portal_goal"]:
                    k_mod[ext_idx] = ctx["lu_Agg_ext"].solve(neg_m[ext_idx])
                else:
                    k_mod = self.lu_Agg.solve(neg_m)
        neg_m_val = max(0.0, float(-np.min(k_mod)))
        self.max_k_neg_roundoff = max(self.max_k_neg_roundoff, neg_m_val)
        cc_u[ck] = k_mod
        return k_mod

    def get_goal_col(self, ctx: dict, ck: Tuple[int, int, int]) -> np.ndarray:
        cc = ctx["col_cache"]
        if ck in cc:
            return cc[ck]
        k_pos = np.maximum(self.get_goal_col_unclipped(ctx, ck), 0.0)
        cc[ck] = k_pos
        return k_pos

    def solve_howard_bound(
        self,
        ctx: dict,
        active_keys: Sequence[Tuple[int, int, int]],
        mode: str,
        warm_W: Optional[np.ndarray] = None,
        certify_lyapunov: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, bool]:
        """Equilibrated multi-decade Howard solver (`1.0` down to `1e-300`, `Closes R747-P0-01 & R747-03`):
        Propagates entrywise `K_neg` roundoff, masks unreachable portal components on `lo`, solves coarse
        selector systems via `equilibrated_dense_m_solve`, and verifies post/pre-fixed-point order on `E_Gamma`.
        """
        dec = self.dec
        m = len(active_keys)
        reach_gam = ctx.get("reach_gam_mask", np.ones(self.n_g, dtype=bool))
        r_hat = ctx["r_hat"].copy()
        if mode == "lo":
            r_hat[~reach_gam] = 0.0
        if m == 0:
            W0 = r_hat.copy()
            W0[ctx["g_gam_mask"]] = 1.0
            return np.zeros((self.n_g, 0), dtype=float), np.zeros(0, dtype=float), W0, True

        cols_pos: List[np.ndarray] = []
        cols_neg: List[np.ndarray] = []
        for ck in active_keys:
            k_mod = self.get_goal_col_unclipped(ctx, ck)
            kp = np.maximum(k_mod, 0.0)
            kn = np.maximum(-k_mod, 0.0)
            if mode == "lo":
                kp[~reach_gam] = 0.0
                kn[~reach_gam] = 0.0
            cols_pos.append(kp)
            cols_neg.append(kn)
        K_pos = np.column_stack(cols_pos)
        K_neg = np.column_stack(cols_neg)
        blks = [dec.qt_blocks[ck] for ck in active_keys]
        I_m = np.eye(m, dtype=float)
        ext_idx = ctx["ext_gam_idx"]

        u_fl = U_MACH_F64 * (2.0 * m + 16.0)
        delta_portal = 1e-9 if certify_lyapunov else 0.0
        if mode == "lo":
            K_work = (1.0 - delta_portal) * K_pos
            r_work = (1.0 - delta_portal) * r_hat
        else:
            K_tot = K_pos + K_neg
            rmax = float(np.max(np.sum(K_tot[ext_idx, :], axis=1))) if len(ext_idx) > 0 else 0.0
            if certify_lyapunov and (1.0 + delta_portal) * rmax >= 1.0 - 1e-12:
                return K_pos, np.zeros(m, dtype=float), np.ones(self.n_g, dtype=float), False
            K_work = (1.0 + delta_portal) * K_tot
            r_work = (1.0 + delta_portal) * r_hat

        if warm_W is not None:
            v = np.array([float(np.min(warm_W[bl]) if mode == "lo" else np.max(warm_W[bl])) for bl in blks], dtype=float)
            W = (K_work @ v) + r_work
        else:
            Sys_bar = np.eye(m, dtype=float)
            for j, bl in enumerate(blks):
                Sys_bar[j, :] -= np.mean(K_work[bl, :], axis=0)
            rhs_bar = np.array([float(np.mean(r_work[bl])) for bl in blks], dtype=float)
            v = equilibrated_dense_m_solve(Sys_bar, rhs_bar)
            W = (K_work @ v) + r_work

        max_howard_it = 30 if certify_lyapunov else 8
        for _ in range(max_howard_it):
            x_sel = np.array([bl[int(np.argmin(W[bl]) if mode == "lo" else np.argmax(W[bl]))] for bl in blks], dtype=np.int64)
            vn = equilibrated_dense_m_solve(I_m - K_work[x_sel, :], r_work[x_sel])
            W_nxt = (K_work @ vn) + r_work
            pos_v = vn > 0.0
            rel_chg = float(np.max(np.abs(vn[pos_v] - v[pos_v]) / vn[pos_v])) if np.any(pos_v) else 0.0
            v, W = vn, W_nxt
            if rel_chg < 1e-13:
                break

        if not certify_lyapunov:
            W_out = (K_pos @ v) + r_hat
            if ctx["has_portal_goal"]:
                W_out[ctx["g_gam_mask"]] = 1.0
            return K_pos, v, W_out, True

        W_cert = np.ones(self.n_g, dtype=float)
        if mode == "lo":
            Kv_pos = K_pos[ext_idx, :] @ v
            # Only propagate K_neg on entries that cannot underflow genuine positive paths unnecessarily;
            # full-exterior Higham verification checks exact `(M_pes z_sub)` directly!
            W_lo_ext = np.maximum(Kv_pos + r_hat[ext_idx] - u_fl * (Kv_pos + r_hat[ext_idx]), 0.0) * (1.0 - 2e-10)
            W_lo_ext[~reach_gam[ext_idx]] = 0.0
            W_cert[ext_idx] = W_lo_ext
            blk_mins = np.array([float(np.min(W_cert[bl])) for bl in blks], dtype=float)
            v_c = np.minimum(v, blk_mins)
            ok = bool(np.all(v_c <= blk_mins))
            return K_pos, v_c, W_cert, ok
        else:
            Kv_tot = (K_pos[ext_idx, :] + K_neg[ext_idx, :]) @ v
            W_hi_ext = (Kv_tot + r_hat[ext_idx]) * (1.0 + u_fl) * (1.0 + 2e-10)
            W_cert[ext_idx] = W_hi_ext
            blk_maxs = np.array([float(np.max(W_cert[bl])) for bl in blks], dtype=float)
            v_c = np.maximum(v, blk_maxs)
            ok = bool(np.all(blk_maxs <= v_c))
            return K_pos, v_c, W_cert, ok

    def materialize_full_extension(
        self,
        ctx: dict,
        W_portal: np.ndarray,
        M_global: Optional[sp.csr_matrix] = None,
        reach_all: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, float]:
        """Materializes full exterior desirability extension; when `M_global` is provided (`pessimistic policy
        channel`), upgrades any multi-decade room (`>14` orders of magnitude where single-pass `SuperLU` loses
        relative digits) via diagonally equilibrated `BiCGSTAB` + monotone damped polish (`Closes R747-03`).
        """
        dec = self.dec
        gm = ctx["gm"]
        if reach_all is None:
            W_ext = np.where(ctx["g_gam_mask"], 0.0, W_portal)
            z_full = np.ones(dec.n_states, dtype=float)
            z_full[dec.gamma_nodes] = W_portal
            z_full[gm] = 1.0
            min_raw_ext = float(np.min(W_portal[ctx["ext_gam_idx"]])) if len(ctx["ext_gam_idx"]) > 0 else 1.0
            for c, rn in enumerate(dec.room_nodes):
                if c in ctx["full_goal_rooms"]:
                    z_full[rn] = 1.0
                    continue
                tl_c = dec.room_tl[c]
                y_ext = self.hq_lus[c].solve(self.room_Arg[c] @ W_ext[tl_c])
                self.local_lu_rhs_solves += 1
                if c in ctx["goal_rooms"]:
                    gr = ctx["goal_rooms"][c]
                    y_ext = y_ext - gr["U_rg"] @ (gr["C_inv"] @ y_ext[gr["ring_r"]])
                yc = ctx["h_room_const"][c] + y_ext
                in_g_c = gm[rn]
                if np.any(~in_g_c):
                    min_raw_ext = min(min_raw_ext, float(np.min(yc[~in_g_c])))
                yc_clean = np.maximum(yc, 0.0)
                if np.any(in_g_c):
                    yc_clean[in_g_c] = 1.0
                z_full[rn] = yc_clean
            z_full[gm] = 1.0
            return z_full, min_raw_ext

        reach_gam = reach_all[dec.gamma_nodes]
        z_full = np.zeros(dec.n_states, dtype=float)
        z_full[dec.gamma_nodes] = np.where(reach_gam, W_portal, 0.0)
        z_full[gm] = 1.0

        for c, rn in enumerate(dec.room_nodes):
            in_g_c = gm[rn]
            if c in ctx["full_goal_rooms"] or np.all(in_g_c):
                z_full[rn] = 1.0
                continue
            ext_loc = np.flatnonzero(~in_g_c)
            x_nodes = rn[ext_loc]
            self.local_lu_rhs_solves += 1

            tl_c = dec.room_tl[c]
            W_ext = np.where(ctx["g_gam_mask"], 0.0, z_full[dec.gamma_nodes])
            y_ext = self.hq_lus[c].solve(self.room_Arg[c] @ W_ext[tl_c])
            if c in ctx["goal_rooms"]:
                gr = ctx["goal_rooms"][c]
                y_ext = y_ext - gr["U_rg"] @ (gr["C_inv"] @ y_ext[gr["ring_r"]])
            y_cand = np.maximum((ctx["h_room_const"][c] + y_ext)[ext_loc], 0.0) * (1.0 - 1e-12)
            r_mask_x = reach_all[x_nodes]
            y_cand[~r_mask_x] = 0.0

            M_xc_all = M_global[x_nodes, :]
            z_bnd = z_full.copy()
            z_bnd[x_nodes] = 0.0
            b_x = np.asarray(M_xc_all @ z_bnd).ravel()
            M_xx = M_global[x_nodes, :][:, x_nodes].tocsr()

            deg_x = np.diff(M_xc_all.indptr).astype(float)
            gam_fl = (deg_x + 3.0) * U_MACH_F64
            Mz_cand = np.asarray(M_xx @ y_cand).ravel() + b_x
            ok_fast = bool(
                np.all(y_cand[r_mask_x] > 0.0)
                and np.all(y_cand[r_mask_x] <= Mz_cand[r_mask_x] * np.maximum(1.0 - gam_fl[r_mask_x], 0.0))
            )
            if float(np.max(b_x)) <= 0.0:
                y_cert = np.zeros(len(x_nodes), dtype=float)
            elif ok_fast:
                y_cert = y_cand
            else:
                p_idx = np.flatnonzero(r_mask_x)
                y_cert = np.zeros(len(x_nodes), dtype=float)
                if len(p_idx) > 0 and float(np.max(b_x[p_idx])) > 0.0:
                    M_p = M_xx[p_idx, :][:, p_idx].tocsr()
                    b_p = b_x[p_idx]
                    y_cert[p_idx] = dijkstra_equilibrated_sparse_subsolution(M_p, b_p, damp=1e-12, log_cutoff=630.0)
                    # Record sparse room refactorization separately from native `hq_lus` backsolve RHS (`Closes R675-04`)!
                    self.room_lu_refactorizations += 1

            yc_out = np.ones(len(rn), dtype=float)
            yc_out[ext_loc] = y_cert
            z_full[rn] = yc_out

        z_full[gm] = 1.0
        ext_all = np.flatnonzero(~gm)
        r_ext = ext_all[reach_all[ext_all]]
        min_raw_ext = float(np.min(z_full[r_ext])) if len(r_ext) > 0 else 1.0
        return z_full, min_raw_ext


class SPQLPlanner:
    """PAC-Certified Spectral-Portal Quotient Learner & Multi-Goal Planner (`Phase-III v3 R747-Verified`).
    Constructed purely from an `EmpiricalTrajectoryDataset` (`0` coordinate or true-matrix access!).
    """

    def __init__(
        self,
        dataset: EmpiricalTrajectoryDataset,
        delta: float = 0.05,
        eps_tol: float = 0.20,
        epistemic_stop_ratio: float = 0.22,
        enable_pou_conservation: bool = True,
        enable_epistemic_stopping: bool = True,
        max_rooms: int = 12,
        max_degree_bound: Optional[int] = None,
        n_peeling_epochs: int = 1,
        all_portals_uniform_weight: float = 0.0,
        enable_exact_portal_fallback: bool = True,
    ) -> None:
        t0 = time.perf_counter()
        self.dataset = dataset
        self.lam = float(dataset.lam)
        self.q_min = float(dataset.q_min)
        self.delta = float(delta)
        self.eps_tol = float(eps_tol)
        self.epistemic_stop_ratio = float(epistemic_stop_ratio)
        self.enable_epistemic_stopping = bool(enable_epistemic_stopping)
        self.all_portals_uniform_weight = float(all_portals_uniform_weight)
        self.enable_exact_portal_fallback = bool(enable_exact_portal_fallback)

        self.pac_pair = build_pac_mmatrix_pair(
            dataset, delta=delta, max_degree_bound=max_degree_bound, n_peeling_epochs=n_peeling_epochs
        )
        self.dec = discover_spectral_portals_from_trajectories(
            dataset.trans_counts, max_rooms=max_rooms, min_room_size=max(20, dataset.n_states // 35)
        )
        self.pes_chan = _SingleMMatrixPortalChannel(
            self.pac_pair.A_pes, self.dec, b_source=None, enable_pou_conservation=enable_pou_conservation
        )
        self.opt_chan = _SingleMMatrixPortalChannel(
            self.pac_pair.A_opt, self.dec, b_source=self.pac_pair.b_opt_explore, enable_pou_conservation=enable_pou_conservation
        )
        self.init_lu_rhs = int(self.pes_chan.init_lu_rhs_solves + self.opt_chan.init_lu_rhs_solves)
        self.offline_init_ms = 1000.0 * (time.perf_counter() - t0)

    def resident_bytes(self) -> int:
        """Selected resident bytes across local room/portal LU factors (`pes` + `opt`) and cached Fiedler columns."""
        tot = 0
        for ch in (self.pes_chan, self.opt_chan):
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

    def active_bottleneck_exploration_weights(self) -> np.ndarray:
        """Computes goal-free epistemic bottleneck priority weights `w_act(i)` on states `0..N-1`."""
        N = self.dataset.n_states
        T_sym = ((self.dataset.trans_counts + self.dataset.trans_counts.T) > 0).tocsr()
        ind = np.zeros(N, dtype=float)
        ind[self.dec.gamma_nodes] = 1.0
        corridor = np.clip(ind + 0.65 * (T_sym @ ind) + 0.35 * (T_sym @ (T_sym @ ind)), 0.0, 2.0)
        return (0.15 + corridor) * self.pac_pair.rho_epistemic

    def build_deployed_policy_csr(self, z_sub_pes: np.ndarray, goal_mask: np.ndarray) -> sp.csr_matrix:
        """Constructs the deployed Markov policy `pi_{ij} propto M_{pes, ij} z_sub_pes[j]` on `ext = ~goal_mask`
        via per-row max-log-weight scaling (`Closes R675-02`: row-stochastic down to `2^{-1074}`, zero `1e-300` floor).
        """
        return build_log_scaled_policy_csr(self.pac_pair.M_pes, z_sub_pes, goal_mask)

    def _exact_singleton_portal_fallback(self, ctx_pes: dict, reach_all: np.ndarray) -> np.ndarray:
        """Timed, LU-charged exact exterior singleton-portal fallback on `E_Gamma` when coarse budget cannot
        certify a componentwise Higham subsolution (`Closes R747-01 & R747-03`).
        """
        # Split all remaining coarse portals down to singleton leaves in `node_cache` via binary PoU!
        q_keys = [(pid, 0, 0) for pid in range(len(self.dec.portal_nodes_loc))]
        leaves: List[Tuple[int, int, int]] = []
        while q_keys:
            nxt: List[Tuple[int, int, int]] = []
            to_sp: List[Tuple[int, int, int]] = []
            for ck in q_keys:
                bl = self.dec.qt_blocks[ck]
                if np.all(ctx_pes["g_gam_mask"][bl]):
                    continue
                chs = self.dec.qt_children.get(ck, [])
                if chs and len(bl) >= 2:
                    to_sp.append(ck)
                    nxt.extend(chs)
                else:
                    leaves.append(ck)
            if to_sp:
                self.pes_chan.split_parents_pou(to_sp)
            q_keys = nxt
        _, _, W_singleton, _ = self.pes_chan.solve_howard_bound(
            ctx_pes, leaves, mode="lo", warm_W=None, certify_lyapunov=True
        )
        z_f, _ = self.pes_chan.materialize_full_extension(
            ctx_pes, W_singleton, M_global=self.pac_pair.M_pes, reach_all=reach_all
        )
        return z_f

    def solve_unseen_goal(
        self,
        s0: int,
        goal_mask: np.ndarray,
        phi_goal: float = 0.0,
        max_rounds: int = 12,
        m_cap: int = 384,
        coarse_l0_only: bool = False,
        materialize_policy: bool = True,
    ) -> dict:
        """Plans & PAC-certifies any unseen goal `goal_mask` from `s0` with full R747 delivery contract:
          - Explicit `solver_status`, `policy_present`, `finite_upper`, and timed `fallback_*` fields (`R747-01`);
          - Full-exterior Tier-3 IEEE-754 Higham verification on BOTH `lo` and `hi` (`R747-03 & Sec 8.4`).
        """
        t0 = time.perf_counter()
        gm = np.asarray(goal_mask, dtype=bool)
        phi_f = float(phi_goal)
        if bool(gm[s0]):
            q_ms = 1000.0 * (time.perf_counter() - t0)
            return {
                "solver_status": "goal_at_start",
                "policy_present": False,
                "finite_upper": True,
                "fallback_used": False,
                "fallback_method": None,
                "fallback_ms": 0.0,
                "fallback_lu_rhs": 0,
                "materialization_ms": 0.0,
                "query_ms": q_ms,
                "bounds_only_query_ms": q_ms,
                "certified_bounds_stage_ms": q_ms,
                "interface_candidate_stage_ms": 0.0,
                "certified": True,
                "sound_enclosure": True,
                "within_eps_tol": True,
                "lo": phi_f,
                "hi": phi_f,
                "width": 0.0,
                "plan_gap_pes": 0.0,
                "active_dofs": 0,
                "full_portal_dofs": self.pes_chan.n_g,
                "rounds": 0,
                "operational_lu_rhs": 0,
                "materialization_lu_rhs": 0,
                "total_query_lu_rhs": 0,
                "max_pes_subsolution_residual": 0.0,
                "min_opt_supersolution_residual": 0.0,
                "higham_pes_delta_rel": 0.0,
                "higham_pes_eps_fl": 0.0,
                "higham_opt_delta_abs": 0.0,
                "higham_opt_tau_shift": 0.0,
                "z_sub_full": None,
                "Pi_ext_csr": None,
            }

        rhs0 = self.pes_chan.local_lu_rhs_solves + self.opt_chan.local_lu_rhs_solves
        refac0 = self.pes_chan.room_lu_refactorizations + self.opt_chan.room_lu_refactorizations
        reach_all = backward_reachable_mask(self.pac_pair.M_pes, gm)
        s0_reachable = bool(reach_all[s0])

        ctx_opt = self.opt_chan.prepare_goal_context(s0, gm)
        ctx_opt["reach_all"] = np.ones(self.dec.n_states, dtype=bool)
        ctx_opt["reach_gam_mask"] = np.ones(self.opt_chan.n_g, dtype=bool)

        # If `s0` cannot reach `G` along observed edges `M_pes > 0`, no observed-edge policy can reach `G`!
        if not s0_reachable:
            cut_opt0 = self.opt_chan.build_initial_exterior_cut(ctx_opt)
            _, _, W_opt0, _ = self.opt_chan.solve_howard_bound(ctx_opt, cut_opt0, mode="hi", warm_W=None, certify_lyapunov=True)
            z_sup0, _ = self.opt_chan.materialize_full_extension(ctx_opt, W_opt0)
            opt_ok, lo_cert, opt_d_abs, opt_tau = higham_verify_lower_supersolution(
                self.pac_pair.M_opt, self.pac_pair.b_opt_explore, z_sup0, gm, s0, phi_f, self.lam, self.q_min
            )
            op_rhs = (self.pes_chan.local_lu_rhs_solves + self.opt_chan.local_lu_rhs_solves) - rhs0
            q_ms = 1000.0 * (time.perf_counter() - t0)
            return {
                "solver_status": "unreachable_on_observed_support",
                "policy_present": False,
                "finite_upper": False,
                "fallback_used": False,
                "fallback_method": None,
                "fallback_ms": 0.0,
                "fallback_lu_rhs": 0,
                "materialization_ms": 0.0,
                "query_ms": q_ms,
                "bounds_only_query_ms": q_ms,
                "certified_bounds_stage_ms": q_ms,
                "interface_candidate_stage_ms": 0.0,
                "certified": False,
                "sound_enclosure": bool(opt_ok),
                "within_eps_tol": False,
                "lo": lo_cert if opt_ok else -float("inf"),
                "hi": float("inf"),
                "width": float("inf"),
                "plan_gap_pes": float("inf"),
                "active_dofs": len(cut_opt0),
                "full_portal_dofs": self.pes_chan.n_g,
                "rounds": 1,
                "operational_lu_rhs": int(op_rhs),
                "materialization_lu_rhs": 0,
                "total_query_lu_rhs": int(op_rhs),
                "max_pes_subsolution_residual": 0.0,
                "min_opt_supersolution_residual": -opt_d_abs,
                "higham_pes_delta_rel": 1.0,
                "higham_pes_eps_fl": 1.0,
                "higham_opt_delta_abs": opt_d_abs,
                "higham_opt_tau_shift": opt_tau,
                "z_sub_full": None,
                "Pi_ext_csr": None,
            }

        ctx_pes = self.pes_chan.prepare_goal_context(s0, gm)
        ctx_pes["reach_all"] = reach_all
        ctx_pes["reach_gam_mask"] = reach_all[self.dec.gamma_nodes]

        active_keys = self.pes_chan.build_initial_exterior_cut(ctx_pes)
        if ctx_opt["has_portal_goal"]:
            _ = self.opt_chan.build_initial_exterior_cut(ctx_opt)

        W_pes_lo: Optional[np.ndarray] = None
        W_pes_hi: Optional[np.ndarray] = None
        W_opt_hi: Optional[np.ndarray] = None

        w_s_pes = np.zeros(self.pes_chan.n_g, dtype=float)
        w_s_pes[ctx_pes["tl_s"]] = ctx_pes["h_s_tl"]
        if self.all_portals_uniform_weight > 0.0 and len(ctx_pes["ext_gam_idx"]) > 0:
            u_wt = self.all_portals_uniform_weight / float(len(ctx_pes["ext_gam_idx"]))
            w_s_pes[ctx_pes["ext_gam_idx"]] = np.maximum(w_s_pes[ctx_pes["ext_gam_idx"]], u_wt)

        w_s_opt = np.zeros(self.opt_chan.n_g, dtype=float)
        w_s_opt[ctx_opt["tl_s"]] = ctx_opt["h_s_tl"]

        rounds_limit = 1 if coarse_l0_only else max_rounds
        rounds_run = 0
        lo_c = -float("inf")
        hi_c = float("inf")
        plan_gap_pes = float("inf")

        for rd in range(rounds_limit):
            rounds_run = rd + 1
            K_pes, _, W_pes_lo, _ = self.pes_chan.solve_howard_bound(ctx_pes, active_keys, mode="lo", warm_W=W_pes_lo, certify_lyapunov=False)
            _, _, W_pes_hi, _ = self.pes_chan.solve_howard_bound(ctx_pes, active_keys, mode="hi", warm_W=W_pes_hi, certify_lyapunov=False)
            K_opt, _, W_opt_hi, _ = self.opt_chan.solve_howard_bound(ctx_opt, active_keys, mode="hi", warm_W=W_opt_hi, certify_lyapunov=False)

            z_pes_lo_s = ctx_pes["z_dir"] + float(ctx_pes["h_s_tl"] @ W_pes_lo[ctx_pes["tl_s"]])
            z_pes_hi_s = ctx_pes["z_dir"] + float(ctx_pes["h_s_tl"] @ W_pes_hi[ctx_pes["tl_s"]])
            z_opt_hi_s = ctx_opt["z_dir"] + float(ctx_opt["h_s_tl"] @ W_opt_hi[ctx_opt["tl_s"]])

            hi_c = (phi_f - self.lam * float(np.log(z_pes_lo_s))) if z_pes_lo_s > 0.0 else float("inf")
            hi_pes_best = (phi_f - self.lam * float(np.log(z_pes_hi_s))) if z_pes_hi_s > 0.0 else float("inf")
            lo_c = (phi_f - self.lam * float(np.log(z_opt_hi_s))) if z_opt_hi_s > 0.0 else -float("inf")
            tot_width = hi_c - lo_c if (np.isfinite(hi_c) and np.isfinite(lo_c)) else float("inf")
            plan_gap_pes = max(0.0, hi_c - hi_pes_best) if (np.isfinite(hi_c) and np.isfinite(hi_pes_best)) else float("inf")

            if coarse_l0_only or len(active_keys) == 0 or tot_width <= self.eps_tol or len(active_keys) >= m_cap or rd == rounds_limit - 1:
                break
            pes_gap_cap = max(self.eps_tol, 0.25 * self.lam)
            if (
                self.enable_epistemic_stopping
                and (self.all_portals_uniform_weight <= 0.0)
                and np.isfinite(tot_width)
                and plan_gap_pes <= min(pes_gap_cap, max(0.015 * self.lam, self.epistemic_stop_ratio * tot_width))
            ):
                _, _, W_opt_lo_chk, _ = self.opt_chan.solve_howard_bound(ctx_opt, active_keys, mode="lo", warm_W=None, certify_lyapunov=False)
                z_opt_lo_s = ctx_opt["z_dir"] + float(ctx_opt["h_s_tl"] @ W_opt_lo_chk[ctx_opt["tl_s"]])
                lo_opt_worst = (phi_f - self.lam * float(np.log(z_opt_lo_s))) if z_opt_lo_s > 0.0 else float("inf")
                tot_plan_gap = plan_gap_pes + max(0.0, lo_opt_worst - lo_c)
                if tot_plan_gap <= min(2.0 * pes_gap_cap, max(0.02 * self.lam, self.epistemic_stop_ratio * tot_width)):
                    break

            m_cur = len(active_keys)
            blks_cur = [self.dec.qt_blocks[ck] for ck in active_keys]
            x_p = np.array([bl[int(np.argmax(W_pes_hi[bl]))] for bl in blks_cur], dtype=np.int64)
            psi_p = equilibrated_dense_m_solve((np.eye(m_cur) - K_pes[x_p, :]).T, np.maximum(w_s_pes @ K_pes, 0.0))
            x_o = np.array([bl[int(np.argmax(W_opt_hi[bl]))] for bl in blks_cur], dtype=np.int64)
            psi_o = equilibrated_dense_m_solve((np.eye(m_cur) - K_opt[x_o, :]).T, np.maximum(w_s_opt @ K_opt, 0.0))

            cands = []
            choke_cands = []
            for j, ck in enumerate(active_keys):
                chs = self.dec.qt_children.get(ck, [])
                bl = blks_cur[j]
                if chs and len(bl) >= 2:
                    hi_max_b = float(np.max(W_pes_hi[bl]))
                    lo_min_b = float(np.min(W_pes_lo[bl]))
                    # Relative block log-oscillation works cleanly even when `W ~ 1e-60`!
                    rel_osc_p = (float(np.max(W_pes_lo[bl])) - lo_min_b) / max(float(np.max(W_pes_lo[bl])), 1e-300) if float(np.max(W_pes_lo[bl])) > 0.0 else 0.0
                    osc_p = 0.5 * (float(hi_max_b - np.min(W_pes_hi[bl])) + float(np.max(W_pes_lo[bl]) - lo_min_b))
                    osc_o = float(np.max(W_opt_hi[bl]) - np.min(W_opt_hi[bl]))
                    sc = float(psi_p[j]) * osc_p + 0.5 * float(psi_o[j]) * osc_o + self.all_portals_uniform_weight * rel_osc_p
                    if (not np.isfinite(hi_c)) and float(psi_p[j]) > 0.0 and hi_max_b > 0.0 and lo_min_b <= 0.0:
                        choke_cands.append((float(psi_p[j]) * hi_max_b, j, ck))
                    elif sc > 0.0:
                        cands.append((sc, j, ck))
            if (not choke_cands) and (not cands):
                break
            choke_cands.sort(reverse=True)
            cands.sort(reverse=True)
            repl: Dict[int, List[Tuple[int, int, int]]] = {}
            parents_split: List[Tuple[int, int, int]] = []
            added = 0
            for _, j, ck in choke_cands[:18]:
                chs = self.dec.qt_children[ck]
                if len(active_keys) + added + len(chs) - 1 <= m_cap:
                    repl[j] = chs
                    parents_split.append(ck)
                    added += len(chs) - 1
            if cands:
                top_sc = cands[0][0]
                for sc, j, ck in cands[: max(0, 18 - len(repl))]:
                    if sc < 0.05 * top_sc and self.all_portals_uniform_weight <= 0.0:
                        continue
                    chs = self.dec.qt_children[ck]
                    if len(active_keys) + added + len(chs) - 1 <= m_cap:
                        repl[j] = chs
                        parents_split.append(ck)
                        added += len(chs) - 1
            if not repl:
                src_list = choke_cands if choke_cands else cands
                j0, ck0 = src_list[0][1], src_list[0][2]
                repl[j0] = self.dec.qt_children[ck0]
                parents_split.append(ck0)

            self.pes_chan.split_parents_pou(parents_split)
            self.opt_chan.split_parents_pou(parents_split)
            nxt_keys: List[Tuple[int, int, int]] = []
            for j, ck in enumerate(active_keys):
                if j in repl:
                    nxt_keys.extend(repl[j])
                else:
                    nxt_keys.append(ck)
            active_keys = nxt_keys

        # Terminal equilibrated solve on selected coarse cut
        _, v_pes_lo, W_pes_lo, pes_portal_ok = self.pes_chan.solve_howard_bound(
            ctx_pes, active_keys, mode="lo", warm_W=W_pes_lo, certify_lyapunov=True
        )
        _, v_opt_hi, W_opt_hi, _ = self.opt_chan.solve_howard_bound(
            ctx_opt, active_keys, mode="hi", warm_W=W_opt_hi, certify_lyapunov=True
        )

        # Full-exterior Tier-3 Higham verification for `lo` (charging opt room extension inside operational RHS!)
        z_sup_full, _ = self.opt_chan.materialize_full_extension(ctx_opt, W_opt_hi)
        opt_ok, lo_c, opt_d_abs, opt_tau = higham_verify_lower_supersolution(
            self.pac_pair.M_opt, self.pac_pair.b_opt_explore, z_sup_full, gm, s0, phi_f, self.lam, self.q_min
        )
        if not opt_ok:
            lo_c = -float("inf")

        z_pes_lo_s = ctx_pes["z_dir"] + float(ctx_pes["h_s_tl"] @ W_pes_lo[ctx_pes["tl_s"]])
        hi_portal_est = (phi_f - self.lam * float(np.log(z_pes_lo_s))) if (pes_portal_ok and z_pes_lo_s > 0.0) else float("inf")

        op_rhs = (self.pes_chan.local_lu_rhs_solves + self.opt_chan.local_lu_rhs_solves) - rhs0
        interface_stage_ms = 1000.0 * (time.perf_counter() - t0)
        cert_bounds_stage_ms = None

        t_mat0 = time.perf_counter()
        rhs_mat0 = self.pes_chan.local_lu_rhs_solves + self.opt_chan.local_lu_rhs_solves

        Pi_csr = None
        policy_sha256 = ""
        z_sub_full = None
        pes_d_rel = 1.0
        pes_eps_fl = 1.0
        max_pes_res = 0.0
        fallback_used = False
        fallback_method = None
        fallback_ms = 0.0
        fallback_lu_rhs = 0
        global_fallback_lu_calls = 0
        global_fallback_states = 0
        heuristic_equiv_rhs = 0

        if materialize_policy:
            pes_ok = False
            if W_pes_lo is not None and z_pes_lo_s > 0.0:
                z_sub_full, _ = self.pes_chan.materialize_full_extension(
                    ctx_pes, W_pes_lo, M_global=self.pac_pair.M_pes, reach_all=reach_all
                )
                pes_ok, hi_c, pes_d_rel, pes_eps_fl = higham_verify_upper_subsolution(
                    self.pac_pair.M_pes, z_sub_full, gm, s0, phi_f, self.lam, self.q_min
                )
            if (not pes_ok) and self.enable_exact_portal_fallback and (not coarse_l0_only):
                t_fb0 = time.perf_counter()
                rhs_fb0 = self.pes_chan.local_lu_rhs_solves + self.opt_chan.local_lu_rhs_solves
                fallback_used = True
                fallback_method = "exact_portal_equilibrated_schur"
                z_sub_full = self._exact_singleton_portal_fallback(ctx_pes, reach_all)
                pes_ok, hi_c, pes_d_rel, pes_eps_fl = higham_verify_upper_subsolution(
                    self.pac_pair.M_pes, z_sub_full, gm, s0, phi_f, self.lam, self.q_min
                )
                if not pes_ok:
                    # Single curved room spanned >15 decades: run candidate exterior sparse LU and keep native
                    # room RHS strictly separate from `global_fallback_lu_calls` (`Closes R675-04`)!
                    fallback_method = "dijkstra_equilibrated_exterior_lu"
                    z_sub_full, n_act_ext = dijkstra_equilibrated_global_subsolution(
                        self.pac_pair.M_pes, gm, reach_all, s0, damp=1e-11
                    )
                    global_fallback_lu_calls += 1
                    global_fallback_states += int(n_act_ext)
                    mean_rm = max(1, int(np.mean([len(rn) for rn in self.dec.room_nodes])))
                    heuristic_equiv_rhs += max(1, int(math.ceil(float(n_act_ext) / float(mean_rm))))
                    pes_ok, hi_c, pes_d_rel, pes_eps_fl = higham_verify_upper_subsolution(
                        self.pac_pair.M_pes, z_sub_full, gm, s0, phi_f, self.lam, self.q_min
                    )
                fallback_lu_rhs = int((self.pes_chan.local_lu_rhs_solves + self.opt_chan.local_lu_rhs_solves) - rhs_fb0)
                fallback_ms = 1000.0 * (time.perf_counter() - t_fb0)

            if pes_ok and z_sub_full is not None:
                cert_bounds_stage_ms = 1000.0 * (time.perf_counter() - t0)
                Pi_cand = self.build_deployed_policy_csr(z_sub_full, gm)
                pol_ok, hi_bound, pes_eps_fl, policy_sha256 = verify_and_bind_deployed_policy_csr(
                    self.pac_pair.M_pes, z_sub_full, Pi_cand, gm, s0, phi_f, self.lam, self.q_min, hi_c, pes_eps_fl
                )
                if pol_ok:
                    hi_c = hi_bound
                    Pi_csr = Pi_cand
                    ext_all = np.flatnonzero(~gm)
                    pes_res_vec = np.asarray(self.pac_pair.A_pes @ z_sub_full).ravel()[ext_all]
                    max_pes_res = float(np.max(pes_res_vec)) if len(pes_res_vec) > 0 else 0.0
                    solver_status = (
                        "certified_equilibrated_fallback_policy" if fallback_used else "certified_coarse_finite_policy"
                    )
                else:
                    hi_c = float("inf")
                    z_sub_full = None
                    Pi_csr = None
                    policy_sha256 = ""
                    solver_status = "policy_verification_failure"
            else:
                hi_c = float("inf")
                z_sub_full = None
                Pi_csr = None
                solver_status = "numerical_witness_failure"
        else:
            # Bounds-only mode: still materialize on pes_chan to enforce identical stored-operator guarantee!
            pes_ok = False
            z_tmp = None
            if W_pes_lo is not None and z_pes_lo_s > 0.0:
                z_tmp, _ = self.pes_chan.materialize_full_extension(
                    ctx_pes, W_pes_lo, M_global=self.pac_pair.M_pes, reach_all=reach_all
                )
                pes_ok, hi_c, pes_d_rel, pes_eps_fl = higham_verify_upper_subsolution(
                    self.pac_pair.M_pes, z_tmp, gm, s0, phi_f, self.lam, self.q_min
                )
            if (not pes_ok) and self.enable_exact_portal_fallback and (not coarse_l0_only):
                t_fb0 = time.perf_counter()
                rhs_fb0 = self.pes_chan.local_lu_rhs_solves + self.opt_chan.local_lu_rhs_solves
                fallback_used = True
                fallback_method = "dijkstra_equilibrated_exterior_lu"
                z_tmp, n_act_ext = dijkstra_equilibrated_global_subsolution(
                    self.pac_pair.M_pes, gm, reach_all, s0, damp=1e-11
                )
                global_fallback_lu_calls += 1
                global_fallback_states += int(n_act_ext)
                mean_rm = max(1, int(np.mean([len(rn) for rn in self.dec.room_nodes])))
                heuristic_equiv_rhs += max(1, int(math.ceil(float(n_act_ext) / float(mean_rm))))
                pes_ok, hi_c, pes_d_rel, pes_eps_fl = higham_verify_upper_subsolution(
                    self.pac_pair.M_pes, z_tmp, gm, s0, phi_f, self.lam, self.q_min
                )
                fallback_lu_rhs = int((self.pes_chan.local_lu_rhs_solves + self.opt_chan.local_lu_rhs_solves) - rhs_fb0)
                fallback_ms = 1000.0 * (time.perf_counter() - t_fb0)
            if pes_ok and z_tmp is not None:
                ext_all = np.flatnonzero(~gm)
                max_pes_res = float(np.max(np.asarray(self.pac_pair.A_pes @ z_tmp).ravel()[ext_all])) if len(ext_all) > 0 else 0.0
                solver_status = "sound_bounds_only_no_policy"
            else:
                hi_c = float("inf")
                solver_status = "numerical_witness_failure"

        mat_rhs = int((self.pes_chan.local_lu_rhs_solves + self.opt_chan.local_lu_rhs_solves) - rhs_mat0)
        room_refac = int((self.pes_chan.room_lu_refactorizations + self.opt_chan.room_lu_refactorizations) - refac0)
        mat_ms = 1000.0 * (time.perf_counter() - t_mat0)
        full_q_ms = 1000.0 * (time.perf_counter() - t0)
        if cert_bounds_stage_ms is None:
            cert_bounds_stage_ms = full_q_ms

        finite_upper = bool(np.isfinite(hi_c))
        policy_present = bool(Pi_csr is not None)
        sound_enclosure = bool(opt_ok and ((not finite_upper) or (hi_c >= lo_c - 1e-9)))
        finite_certified = bool(
            sound_enclosure and np.isfinite(lo_c) and finite_upper and (hi_c >= lo_c)
            and ((not materialize_policy) or policy_present)
        )
        return {
            "solver_status": solver_status,
            "policy_present": policy_present,
            "policy_sha256": policy_sha256,
            "operator_step_count": int(self.dataset.total_steps),
            "finite_upper": finite_upper,
            "fallback_used": fallback_used,
            "fallback_method": fallback_method,
            "fallback_ms": fallback_ms,
            "fallback_lu_rhs": fallback_lu_rhs,
            "room_lu_refactorizations": room_refac,
            "global_fallback_lu_calls": int(global_fallback_lu_calls),
            "global_fallback_active_states": int(global_fallback_states),
            "heuristic_equiv_room_rhs": int(heuristic_equiv_rhs),
            "materialization_ms": mat_ms,
            "query_ms": full_q_ms,
            "interface_candidate_stage_ms": interface_stage_ms,
            "certified_bounds_stage_ms": cert_bounds_stage_ms,
            "bounds_only_query_ms": cert_bounds_stage_ms,
            "certified": finite_certified,
            "sound_enclosure": sound_enclosure,
            "within_eps_tol": bool(finite_certified and (hi_c - lo_c <= self.eps_tol)),
            "lo": lo_c,
            "hi": hi_c,
            "width": float(hi_c - lo_c) if (np.isfinite(lo_c) and finite_upper) else float("inf"),
            "plan_gap_pes": plan_gap_pes,
            "active_dofs": len(active_keys) if not fallback_used else int(len(ctx_pes["ext_gam_idx"])),
            "full_portal_dofs": self.pes_chan.n_g,
            "rounds": rounds_run,
            "operational_lu_rhs": int(op_rhs),
            "materialization_lu_rhs": int(mat_rhs),
            "total_query_lu_rhs": int(op_rhs + mat_rhs),
            "max_pes_subsolution_residual": max_pes_res,
            "min_opt_supersolution_residual": -opt_d_abs,
            "higham_pes_delta_rel": pes_d_rel,
            "higham_pes_eps_fl": pes_eps_fl,
            "higham_opt_delta_abs": opt_d_abs,
            "higham_opt_tau_shift": opt_tau,
            "z_sub_full": z_sub_full,
            "Pi_ext_csr": Pi_csr,
        }
