"""Experiment 5 (`green_response` — `v6` Stage 2 / `C2-10` Falsifiable Diagnostic, 8-Core Parallel):
Cross-Task & Cross-World Response-Space Compressibility, Action-Ranking Preservation, & Net-Benefit Gate.

Answers GPT6's bounded Stage-2 research question BEFORE building any permanent `ResponseMemory` machinery:
  > Under identical GP world models, physical observations, and task information, can low-rank response
  > representations learned from past solves reduce cumulative compute on future tasks at bounded decision
  > loss — AFTER charging basis construction, discrete M-matrix residual verification, positivity guards
  > (`Z_hat - eta > 0`), and automatic `ExactRing` fallback?

Sub-experiments:
  5A. Fixed-World Compressibility, Unseen-Target PDE Source-Support Obstruction, & Reciprocal Portal SVD
      (`16` Maps: `8` Narrow-Barrier `30100..30107` + `8` Competing-Corridor `30200..30207`, `2D 51^2` + `3D 21^3`):
        - Separates seen-catalog new subsets (already solved in ~2 ms by `ExactRing` column cache) from
          genuinely unseen target locations (`Gamma_new` disjoint from historical `Gamma_train`).
        - Verifies the elliptic PDE source-support obstruction: projecting an unseen target onto interior-harmonic
          historical target columns yields `||E_{Gamma_new} - A_theta U_hat||_inf == 1.0` (`0%` certification).
        - Evaluates `Standard-POD-SVD` vs `Task-Weighted-Portal-SVD` (`r in {2, 4, 8, 16, 32, 64}`) on singular
          value decay, root Q-error, top-1 action agreement (overall & near-tie `gap < 0.25`), exact induced
          Bellman policy regret, and net cumulative wall-clock vs `SingleLU-ExactRing`.

  5B. Continual Evolving-World Petrov-Galerkin Reduced Basis + Certified M-Matrix Fallback (`12` Maps `30300..30311`,
      `2D 51^2` & `3D 21^3`, `K = 8` `m = 5` Tours/Epoch):
        - Compares `ExactRing-Rebuild`, `Structure-Memory-Fresh-Exact`, `Residual-Audited-Rank0`,
          `POD-Galerkin-Certified`, and `TaskWeighted-Galerkin-Certified` (all using strict `Z_stored - eta > 0`
          positivity and 4-way Subset-DP `eps_tol = 0.25` certification with automatic `ExactRing` fallback,
          charging 100% of SVD + Galerkin + sparse `A_theta @ U_hat` residual check + fallback from zero!) across:
            (i) Realistic unstructured `+12`-probe online GP refits (`6` epochs: `1` init + `5` updates);
            (ii) Structured low-dimensional parametric world modulations (`4` calibration epochs -> `6` test epochs).

  5C. Pre-Declared Go / No-Go Gate (`>= 20%` net from-zero wall-clock savings at `0` bound violations).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from green_response import (
    GoalBall,
    KrigingWorldModel,
    MacroTourPlanner,
    ProblemSpec,
    SchurPortPlanner,
    build_upwind_mmatrix_desirability_operator,
    collect_runtime_metadata,
    enforce_single_thread_env,
    generate_benchmark_map,
    independent_exact_macro_bellman_reference,
    observe_world_at_points,
    paired_stats,
    run_map_parallel,
    sample_noisy_probes,
)


# ==============================================================================
# Exp 5A: Fixed-World Spectral Decay, Action Ranking, & Source-Support Obstruction
# ==============================================================================
def _sample_nonoverlapping_balls(
    rng: np.random.Generator, n_balls: int, dim: int, r_wp: float, box_lim: float, avoid: Sequence[GoalBall] = ()
) -> List[GoalBall]:
    out: List[GoalBall] = []
    all_existing = list(avoid)
    for _ in range(n_balls):
        for _att in range(500):
            pt = rng.uniform(-box_lim, box_lim, size=dim)
            if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.08 * r_wp for w in all_existing):
                gb = GoalBall(tuple(pt.tolist()), phi=0.0, radius=r_wp)
                out.append(gb)
                all_existing.append(gb)
                break
    return out


def _eval_lowrank_portal_macro_dp(
    pl_full: SchurPortPlanner,
    start_node: int,
    unseen_wp_ids: Sequence[int],
    G_portal_approx: np.ndarray,
    portal_row_of_node: Dict[int, int],
) -> Tuple[np.ndarray, int]:
    """Evaluates approximate Subset-DP root Q-values and chosen root action using a rank-`r`
    approximation `G_portal_approx` (`shape = (n_portals, n_grid)`) to the exact evaluation-portal
    adjoint Green rows `(A_0^{-1})[portal_nodes, :]`.
    """
    lam = pl_full.spec.lam
    t_canon = sorted(int(w) for w in unseen_wp_ids)
    m = len(t_canon)
    eval_nodes = [start_node]
    offsets: Dict[int, slice] = {}
    for b in t_canon:
        rb = pl_full.wp_rings[b]
        offsets[b] = slice(len(eval_nodes), len(eval_nodes) + len(rb))
        eval_nodes.extend(int(x) for x in rb)
    eval_arr = np.asarray(eval_nodes, dtype=np.int64)
    p_rows = np.asarray([portal_row_of_node[int(nd)] for nd in eval_arr], dtype=np.int64)

    c0_leg: Dict[int, np.ndarray] = {}
    P_leg: Dict[int, np.ndarray] = {}
    in_ball: Dict[int, np.ndarray] = {}

    for b in t_canon:
        ring_b = pl_full.wp_rings[b]
        ring_p_rows = np.asarray([portal_row_of_node[int(nd)] for nd in ring_b], dtype=np.int64)
        U_ring_sub = G_portal_approx[np.ix_(ring_p_rows, ring_b)]
        U_eval_sub = G_portal_approx[np.ix_(p_rows, ring_b)]
        # Regularized inverse in case severe rank truncation makes `U_ring_sub` ill-conditioned
        pinv_b = np.linalg.pinv(U_ring_sub, rcond=1e-10)
        he_b = U_eval_sub @ pinv_b
        he_pos = np.maximum(he_b, 1e-15)
        zb_raw = np.maximum(np.sum(he_pos, axis=1), 1e-15)
        ib = pl_full.wp_masks[b][eval_arr]
        in_ball[b] = ib
        zb_s = np.where(ib, 1.0, zb_raw)
        c0_leg[b] = np.where(ib, 0.0, -lam * np.log(zb_s))
        P_leg[b] = he_pos / np.sum(he_pos, axis=1, keepdims=True)

    n_ev = len(eval_arr)
    n_masks = 1 << m
    F_hat = np.zeros((n_ev, n_masks), dtype=float)
    for i, b in enumerate(t_canon):
        F_hat[:, 1 << i] = c0_leg[b]

    for k in range(2, m + 1):
        for mk in range(1, n_masks):
            if mk.bit_count() != k:
                continue
            best_v = np.full(n_ev, np.inf, dtype=float)
            for i, b in enumerate(t_canon):
                if not (mk & (1 << i)):
                    continue
                rem = mk ^ (1 << i)
                cont = P_leg[b] @ F_hat[offsets[b], rem]
                if np.any(in_ball[b]):
                    cont = np.where(in_ball[b], F_hat[:, rem], cont)
                best_v = np.minimum(best_v, c0_leg[b] + cont)
            F_hat[:, mk] = best_v

    full_mk = n_masks - 1
    Q_hat = np.zeros(m, dtype=float)
    for i, b in enumerate(t_canon):
        rem = full_mk ^ (1 << i)
        Q_hat[i] = float(F_hat[0, rem]) if in_ball[b][0] else float(c0_leg[b][0] + P_leg[b][0, :] @ F_hat[offsets[b], rem])
    return Q_hat, int(np.argmin(Q_hat))


def _exp5a_fixed_world_worker(args: Tuple[int, int, str]) -> dict:
    idx_m, ms, regime_name = args
    rng = np.random.default_rng(ms + 303)
    world2 = generate_benchmark_map(ms, dim=2, regime=regime_name, with_drift=True)
    km2 = KrigingWorldModel(*sample_noisy_probes(world2, n_probes=56, seed=ms + 11, include_drift=True))
    gn2 = 51
    r_wp2 = 0.22

    # 16 historical training balls + 8 strictly disjoint unseen target balls
    train_wps = _sample_nonoverlapping_balls(rng, 16, 2, r_wp2, 1.24)
    unseen_wps = _sample_nonoverlapping_balls(rng, 8, 2, r_wp2, 1.24, avoid=train_wps)
    all_wps = train_wps + unseen_wps
    n_tr = len(train_wps)
    unseen_ids = list(range(n_tr, len(all_wps)))

    pl = SchurPortPlanner(world2.spec, gn2, km2.predict_q, km2.predict_b, all_wps, initial_sectors_per_wp="EXACT", lazy_init=True)
    lu0 = pl._ensure_current_lu()
    A_csr = pl.A0.tocsr()
    inv_norm_ub = float(pl.spec.lam / max(float(np.min(pl.q_base)), 1e-12))

    # Build historical Green column matrix `Y_hist` from `train_wps` (`L8` + `EXACT` columns)
    hist_cols = []
    train_ring_union = set()
    for j in range(n_tr):
        _, U_j = pl.ensure_wp_level(j, "EXACT")
        hist_cols.append(U_j)
        train_ring_union.update(int(x) for x in pl.wp_rings[j])
    Y_hist = np.hstack(hist_cols)  # (N_grid, M_hist_cols)

    # 1. Verify PDE source-support obstruction on genuinely disjoint unseen targets (`Gamma_new \cap Gamma_train == empty`)
    U_svd_full, s_vals_hist, _ = np.linalg.svd(Y_hist, full_matrices=False)
    V_hist_64 = U_svd_full[:, : min(64, U_svd_full.shape[1])]
    AV_hist_64 = A_csr @ V_hist_64
    GtG_64 = AV_hist_64.T @ AV_hist_64 + 1e-14 * np.eye(AV_hist_64.shape[1])

    disjoint_unseen_count = 0
    naive_unseen_res_linf = []
    naive_unseen_certified = 0
    for uid in unseen_ids:
        ring_u = pl.wp_rings[uid]
        if any(int(nd) in train_ring_union for nd in ring_u):
            continue
        disjoint_unseen_count += 1
        B_u = np.zeros((len(pl.pts), 1), dtype=float)
        B_u[ring_u, 0] = 1.0  # L1 aggregate ring source on unseen target
        c_ls = np.linalg.solve(GtG_64, AV_hist_64.T @ B_u)
        U_hat_u = np.maximum(V_hist_64 @ c_ls, 0.0)
        res_inf = float(np.max(np.abs(B_u - (A_csr @ U_hat_u))))
        err_ub = inv_norm_ub * res_inf
        min_diag = float(np.min(U_hat_u[ring_u, 0]))
        naive_unseen_res_linf.append(res_inf)
        if err_ub < 0.45 * min_diag:
            naive_unseen_certified += 1

    # 2. Sample 12 unseen-target `m = 4` tour tasks + 12 seen-catalog `m = 4` tour tasks
    start_pts = []
    unseen_tasks = []
    seen_tasks = []
    for _ in range(12):
        sub_u = tuple(sorted(rng.choice(unseen_ids, size=4, replace=False).tolist()))
        sub_s = tuple(sorted(rng.choice(n_tr, size=4, replace=False).tolist()))
        s_pt = rng.uniform(-1.20, 1.20, size=2)
        for _att in range(120):
            cand = rng.uniform(-1.20, 1.20, size=2)
            if all(np.linalg.norm(cand - np.asarray(all_wps[w].center)) > r_wp2 + 0.14 for w in sub_u + sub_s):
                s_pt = cand
                break
        s_nd = int(np.argmin(np.sum((pl.pts - s_pt[None, :]) ** 2, axis=1)))
        start_pts.append((s_pt, s_nd))
        unseen_tasks.append((s_pt, s_nd, sub_u))
        seen_tasks.append((s_pt, s_nd, sub_s))

    # Measure `ExactRing` cached seen-catalog query time vs fresh unseen-target `ExactRing` solve time
    pl_seen_bench = SchurPortPlanner(world2.spec, gn2, km2.predict_q, km2.predict_b, train_wps, initial_sectors_per_wp="EXACT", lazy_init=False)
    mt_seen = MacroTourPlanner(pl_seen_bench)
    t_s0 = time.perf_counter()
    for s_pt, _, sub_s in seen_tasks:
        mt_seen.plan_exact_subset_dp(s_pt, sub_s)
    seen_cached_12tasks_ms = 1000.0 * (time.perf_counter() - t_s0)

    pl_unseen_exact = SchurPortPlanner(world2.spec, gn2, km2.predict_q, km2.predict_b, unseen_wps, initial_sectors_per_wp="EXACT", lazy_init=True)
    mt_unseen_exact = MacroTourPlanner(pl_unseen_exact)
    t_u0 = time.perf_counter()
    exact_unseen_refs = []
    for s_pt, s_nd, sub_u in unseen_tasks:
        loc_ids = tuple(w - n_tr for w in sub_u)
        res_ex = mt_unseen_exact.plan_exact_subset_dp(s_pt, loc_ids)
        sens_ex = mt_unseen_exact.compute_exact_macro_q_sensitivities(s_pt, loc_ids, max_alt_branches=0, include_drift_grad=False)
        exact_unseen_refs.append((res_ex, sens_ex))
    # Pure `plan_exact_subset_dp` time on unseen stream (re-measured cleanly without sensitivity call)
    pl_unseen_timed = SchurPortPlanner(world2.spec, gn2, km2.predict_q, km2.predict_b, unseen_wps, initial_sectors_per_wp="EXACT", lazy_init=True)
    mt_unseen_timed = MacroTourPlanner(pl_unseen_timed)
    t_ut0 = time.perf_counter()
    for s_pt, _, sub_u in unseen_tasks:
        mt_unseen_timed.plan_exact_subset_dp(s_pt, tuple(w - n_tr for w in sub_u))
    exact_unseen_from_zero_12tasks_ms = 1000.0 * (time.perf_counter() - t_ut0)

    # 3. Reciprocal Evaluation-Portal Green Operator `G_portal = (A_0^{-1})[portal_nodes, :]` SVD vs Task-Weighted SVD
    portal_nodes_sorted = sorted(
        {s_nd for _, s_nd in start_pts}.union(*(set(int(x) for x in pl.wp_rings[u]) for u in unseen_ids))
    )
    portal_row_of = {nd: i for i, nd in enumerate(portal_nodes_sorted)}
    t_pbuild0 = time.perf_counter()
    E_portal = np.zeros((len(pl.pts), len(portal_nodes_sorted)), dtype=float)
    for col_i, nd in enumerate(portal_nodes_sorted):
        E_portal[nd, col_i] = 1.0
    G_portal_exact = lu0.solve(E_portal, trans="T").T  # shape = (n_portals, N_grid)
    portal_build_ms = 1000.0 * (time.perf_counter() - t_pbuild0)

    # Standard unweighted SVD vs Task-Weighted SVD (higher row weight on start depots & high-sensitivity ring nodes)
    Up_std, sp_vals, Vtp_std = np.linalg.svd(G_portal_exact, full_matrices=False)
    row_weights = np.ones(len(portal_nodes_sorted), dtype=float)
    start_node_set = {s_nd for _, s_nd in start_pts}
    for i_p, nd in enumerate(portal_nodes_sorted):
        if nd in start_node_set:
            row_weights[i_p] = 4.0
    W_sqrt = np.sqrt(row_weights)
    Up_tw, _, Vtp_tw = np.linalg.svd(G_portal_exact * W_sqrt[:, None], full_matrices=False)

    energy_cum = np.cumsum(sp_vals ** 2) / max(float(np.sum(sp_vals ** 2)), 1e-30)
    ranks_90_99_999 = {
        "r_90pct": int(np.searchsorted(energy_cum, 0.90) + 1),
        "r_99pct": int(np.searchsorted(energy_cum, 0.99) + 1),
        "r_99_9pct": int(np.searchsorted(energy_cum, 0.999) + 1),
        "n_portals_full_rank": len(portal_nodes_sorted),
    }

    ranks_eval = (4, 8, 16, 32, 64)
    rank_curves: Dict[str, dict] = {"Standard_POD_SVD": {}, "TaskWeighted_SVD": {}}
    for basis_kind, U_b, Vt_b, inv_w in [
        ("Standard_POD_SVD", Up_std, Vtp_std, np.ones_like(W_sqrt)),
        ("TaskWeighted_SVD", Up_tw, Vtp_tw, 1.0 / W_sqrt),
    ]:
        for r_k in ranks_eval:
            r_eff = min(r_k, len(sp_vals))
            G_r = ((U_b[:, :r_eff] * sp_vals[:r_eff][None, :] if basis_kind == "Standard_POD_SVD" else (U_b[:, :r_eff] * inv_w[:, None]) @ ((U_b[:, :r_eff].T * W_sqrt[None, :]) @ G_portal_exact))
                   if basis_kind == "TaskWeighted_SVD" else (U_b[:, :r_eff] * sp_vals[:r_eff][None, :]) @ Vt_b[:r_eff, :])
            q_max_errs = []
            top1_agree = []
            neartie_agree = []
            induced_regrets = []
            for idx_t, (s_pt, s_nd, sub_u) in enumerate(unseen_tasks):
                _, sens_ex = exact_unseen_refs[idx_t]
                Q_true = np.asarray(sens_ex["Q_root_canonical"], dtype=float)
                Q_hat, act_hat_pos = _eval_lowrank_portal_macro_dp(pl, s_nd, sub_u, G_r, portal_row_of)
                q_max_errs.append(float(np.max(np.abs(Q_hat - Q_true))))
                agree = int(act_hat_pos == int(np.argmin(Q_true)))
                top1_agree.append(agree)
                if float(sens_ex["action_gap"]) < 0.25:
                    neartie_agree.append(agree)
                induced_regrets.append(float(max(0.0, Q_true[act_hat_pos] - np.min(Q_true))))
            rank_curves[basis_kind][f"r_{r_k}"] = {
                "mean_root_Q_linf_err": float(np.mean(q_max_errs)),
                "top1_action_agreement_rate": float(np.mean(top1_agree)),
                "neartie_top1_agreement_rate": float(np.mean(neartie_agree)) if neartie_agree else None,
                "mean_induced_root_bellman_regret": float(np.mean(induced_regrets)),
                "max_induced_root_bellman_regret": float(np.max(induced_regrets)),
            }

    return {
        "map_seed": ms,
        "regime": regime_name,
        "disjoint_unseen_targets_tested": disjoint_unseen_count,
        "naive_interior_pod_unseen_min_residual_linf": float(np.min(naive_unseen_res_linf)) if naive_unseen_res_linf else 1.0,
        "naive_interior_pod_unseen_certified_rate": float(naive_unseen_certified / max(disjoint_unseen_count, 1)),
        "seen_catalog_exactring_cached_12tasks_ms": seen_cached_12tasks_ms,
        "unseen_targets_exactring_from_zero_12tasks_ms": exact_unseen_from_zero_12tasks_ms,
        "portal_green_bank_offline_build_ms": portal_build_ms,
        "portal_spectral_ranks": ranks_90_99_999,
        "rank_curves": rank_curves,
    }


# ==============================================================================
# Exp 5B: Continual Evolving-World Petrov-Galerkin Subspace + Certified Fallback
# ==============================================================================
def _assemble_new_operator_lazy_no_lu(pl: SchurPortPlanner, new_q_fn, new_b_fn) -> None:
    """Updates `pl`'s discrete M-matrix operator `(q_base, b_grid, A0, operator_epoch)` WITHOUT calling `splu` upfront,
    so certified reduced-basis approximations that satisfy `eps_tol` truly avoid `splu` factorization!
    """
    q_new = pl.spec.q0 + np.asarray(new_q_fn(pl.pts), dtype=float)
    q_min = float(np.min(q_new))
    if not np.all(np.isfinite(q_new)) or q_min <= 0.0:
        raise ValueError(f"Non-positive q_new min={q_min}")
    b_new = None if new_b_fn is None else np.asarray(new_b_fn(pl.pts), dtype=float)
    A_new, _ = build_upwind_mmatrix_desirability_operator(pl.spec, pl.grid_n, q_new, b_new)
    pl.operator_epoch += 1
    pl.q_base = q_new
    pl.b_grid = b_new
    pl.A0 = A_new
    pl._lu_is_current = False
    pl._wp_ring_op_cache.clear()
    pl._adhoc_cache.clear()
    pl._node_col_cache.clear()
    pl._wp_tree.clear()
    pl._wp_tree_col_epoch.clear()
    pl._wp_verified_epoch.clear()
    pl._wp_col_err_bounds.clear()
    for j in range(len(pl.waypoints)):
        pl.wp_levels[j] = "NONE"


def _try_petrov_galerkin_waypoint_inject(
    pl: SchurPortPlanner,
    wp_id: int,
    snap_cols_exact: List[np.ndarray],
    max_rank: int,
    mode_pg: str = "pod_svd_l2",
) -> dict:
    """Attempts to certify an `"EXACT"` ring response `U_stored` for `wp_id` under `pl.A0` WITHOUT `splu`:
      - `mode_pg == "pod_svd_l2"`: Pooled unweighted POD/SVD basis `V_r` + least-squares `min_C ||E - A_0 V_r C||_F`;
      - `mode_pg == "colwise_irls_linf"`: Per-ring-node historical subspace (`K_snap <= 4` per ring column,
        preserving exact node-localized singular peaks!) + 1-step `L_inf`-targeted IRLS Petrov-Galerkin projection;
      - Evaluates exact M-matrix residual bound `err_ub = (lam / q_min) * ||E - A_0 U_stored||_inf` on the actual
        stored nonnegative matrix `U_stored`, enforces `U_stored - err_ub > 0` (`err_ub < 0.42 * diag`), and feeds
        certified column bounds into `MacroTourPlanner`'s 4-way Subset-DP certificate with automatic `ExactRing` fallback!
    """
    t0 = time.perf_counter()
    if not snap_cols_exact:
        return {"accepted_pre_dp": False, "ms": 0.0, "max_err_ub": float("inf")}
    ring_b = pl.wp_rings[wp_id]
    m_b = len(ring_b)
    n_grid = len(pl.pts)
    A_csr = pl.A0.tocsr()
    q_min = float(np.min(pl.q_base))
    inv_norm_ub = float(pl.spec.lam / max(q_min, 1e-12))

    if mode_pg == "pod_svd_l2":
        S_mat = np.hstack(snap_cols_exact)
        U_s, s_v, _ = np.linalg.svd(S_mat, full_matrices=False)
        r_use = min(max_rank, int(np.sum(s_v > 1e-12 * s_v[0])) if len(s_v) else 0)
        if r_use == 0:
            return {"accepted_pre_dp": False, "ms": 1000.0 * (time.perf_counter() - t0), "max_err_ub": float("inf")}
        V_r = U_s[:, :r_use]
        M = A_csr @ V_r
        GtG = M.T @ M + 1e-13 * np.eye(r_use)
        C_opt = np.linalg.solve(GtG, M[ring_b, :].T)
        U_raw = V_r @ C_opt
        if np.min(U_raw) >= 0.0:
            U_stored = U_raw
            AU_stored = M @ C_opt
        else:
            U_stored = np.maximum(U_raw, 0.0)
            AU_stored = A_csr @ U_stored
    else:
        k_sn = len(snap_cols_exact)
        S_stack = np.stack(snap_cols_exact, axis=1)  # (N_grid, K_snap, m_b)
        S_flat = S_stack.reshape(n_grid, k_sn * m_b)
        AS_flat = A_csr @ S_flat
        AS = AS_flat.reshape(n_grid, k_sn, m_b)
        eye_k = 1e-13 * np.eye(k_sn)[None, :, :]
        G0 = np.einsum("nkm,nlm->mkl", AS, AS) + eye_k
        rhs0 = AS[ring_b, :, np.arange(m_b)]  # (m_b, K_snap)
        alpha0 = np.linalg.solve(G0, rhs0[:, :, None])[:, :, 0]  # (m_b, K_snap)
        AU0 = np.einsum("nkm,mk->nm", AS, alpha0)
        R0 = -AU0
        R0[ring_b, np.arange(m_b)] += 1.0
        r_scale = np.maximum(np.max(np.abs(R0), axis=0, keepdims=True), 1e-12)
        w_irls = 1.0 + 12.0 * ((np.abs(R0) / r_scale) ** 2)
        AS_w = AS * w_irls[:, None, :]
        G1 = np.einsum("nkm,nlm->mkl", AS_w, AS) + eye_k
        rhs1 = AS_w[ring_b, :, np.arange(m_b)]
        alpha1 = np.linalg.solve(G1, rhs1[:, :, None])[:, :, 0]
        U_raw = np.einsum("nkm,mk->nm", S_stack, alpha1)
        if np.min(U_raw) >= 0.0:
            U_stored = U_raw
            AU_stored = np.einsum("nkm,mk->nm", AS, alpha1)
        else:
            U_stored = np.maximum(U_raw, 0.0)
            AU_stored = A_csr @ U_stored

    R_mat = -AU_stored
    R_mat[ring_b, np.arange(m_b)] += 1.0
    col_res_inf = np.max(np.abs(R_mat), axis=0)
    err_ub = inv_norm_ub * col_res_inf
    diag_vals = U_stored[ring_b, np.arange(m_b)]

    if np.any(diag_vals <= 1e-14) or np.any(err_ub >= 0.42 * diag_vals) or float(np.sum(err_ub)) > 0.35 * float(np.sum(diag_vals)):
        return {
            "accepted_pre_dp": False,
            "ms": 1000.0 * (time.perf_counter() - t0),
            "max_err_ub": float(np.max(err_ub)),
        }

    parts_ex = pl._wp_partitions[wp_id]["EXACT"]
    tree = pl._wp_tree.setdefault(wp_id, {})
    tree.clear()
    tree["EXACT"] = (parts_ex, U_stored)
    pl._wp_col_err_bounds[(wp_id, "EXACT")] = err_ub
    pl._wp_verified_epoch[(wp_id, "EXACT")] = pl.operator_epoch
    pl._wp_tree_col_epoch.pop((wp_id, "EXACT"), None)
    pl._wp_ring_op_cache.pop((wp_id, "EXACT"), None)
    pl.wp_levels[wp_id] = "EXACT"
    return {
        "accepted_pre_dp": True,
        "ms": 1000.0 * (time.perf_counter() - t0),
        "max_err_ub": float(np.max(err_ub)),
    }


def _precompute_killed_epoch_tables(
    pl_ref: SchurPortPlanner, needed_wps: Sequence[int]
) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
    """Precomputes independent killed-operator exact `(V_full, P_full)` on `Omega \\ Gamma_dst`
    once per `(epoch, dst)` across all 5 methods (never touching `pl._wp_tree` or `bound_harmonic_batch`).
    """
    A_csr = pl_ref.A0.tocsr()
    N = len(pl_ref.pts)
    lam = pl_ref.spec.lam
    out_vp: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
    for dst in needed_wps:
        mask_b = pl_ref.wp_masks[dst]
        ring_b = pl_ref.wp_rings[dst]
        ext_idx = np.flatnonzero(~mask_b)
        lu_ee = spla.splu(A_csr[ext_idx, :][:, ext_idx].tocsc())
        RHS = -(A_csr[ext_idx, :][:, ring_b].toarray())
        H_ext = lu_ee.solve(RHS)
        phi_b = float(pl_ref.waypoints[dst].phi)
        Z_bar_ext = H_ext @ np.ones(len(ring_b), dtype=float)
        V_full = np.full(N, phi_b, dtype=float)
        V_full[ext_idx] = phi_b - lam * np.log(Z_bar_ext)
        P_full = np.zeros((N, len(ring_b)), dtype=float)
        P_full[ext_idx, :] = H_ext / Z_bar_ext[:, None]
        for k_r, nid in enumerate(ring_b):
            P_full[int(nid), k_r] = 1.0
        out_vp[int(dst)] = (V_full, P_full)
    return out_vp


def _eval_killed_macro_bellman_from_tables(
    pl_ref: SchurPortPlanner,
    killed_vp: Dict[int, Tuple[np.ndarray, np.ndarray]],
    start_xy: Sequence[float],
    target_ids: Sequence[int],
    policy_action_idx: np.ndarray,
) -> Tuple[float, float]:
    """Exact `O(m^2 2^m)` Subset Macro-Bellman verifier matching `independent_exact_macro_bellman_reference`
    identically while reusing precomputed killed-operator `(V_full, P_full)` across methods.
    """
    s_node = int(np.argmin(np.sum((pl_ref.pts - np.asarray(start_xy, dtype=float)[None, :]) ** 2, axis=1)))
    t_list = list(target_ids)
    m = len(t_list)
    eval_list = [s_node]
    offsets: Dict[int, slice] = {}
    for a in t_list:
        ra = pl_ref.wp_rings[a]
        offsets[a] = slice(len(eval_list), len(eval_list) + len(ra))
        eval_list.extend(int(x) for x in ra)
    eval_nodes = np.asarray(eval_list, dtype=np.int64)
    in_ball = {b: pl_ref.wp_masks[b][eval_nodes] for b in t_list}
    exact_val = {b: killed_vp[b][0][eval_nodes] for b in t_list}
    P_ring = {b: killed_vp[b][1][eval_nodes, :] for b in t_list}

    n_ev = len(eval_nodes)
    n_masks = 1 << m
    F_opt = np.zeros((n_ev, n_masks), dtype=float)
    J_pol = np.zeros((n_ev, n_masks), dtype=float)
    for i, b in enumerate(t_list):
        mk = 1 << i
        F_opt[:, mk] = exact_val[b]
        J_pol[:, mk] = exact_val[b]

    masks_by_pop: List[List[int]] = [[] for _ in range(m + 1)]
    for mk in range(1, n_masks):
        masks_by_pop[mk.bit_count()].append(mk)

    for k in range(2, m + 1):
        for mk in masks_by_pop[k]:
            best_v = np.full(n_ev, np.inf, dtype=float)
            q_choices: Dict[int, np.ndarray] = {}
            for i in range(m):
                if not (mk & (1 << i)):
                    continue
                b = t_list[i]
                rem = mk ^ (1 << i)
                f_rem = F_opt[:, rem]
                cont_opt = np.where(in_ball[b], f_rem, P_ring[b] @ f_rem[offsets[b]])
                best_v = np.minimum(best_v, exact_val[b] + cont_opt)
                j_rem = J_pol[:, rem]
                cont_pol = np.where(in_ball[b], j_rem, P_ring[b] @ j_rem[offsets[b]])
                q_choices[i] = exact_val[b] + cont_pol
            F_opt[:, mk] = best_v
            act_col = policy_action_idx[:, mk]
            out_col = np.full(n_ev, np.nan, dtype=float)
            for i, qv in q_choices.items():
                sel = act_col == i
                if np.any(sel):
                    out_col[sel] = qv[sel]
            J_pol[:, mk] = out_col

    full_mk = n_masks - 1
    return float(F_opt[0, full_mk]), float(J_pol[0, full_mk])


def _run_evolving_world_stream_on_map(
    spec: ProblemSpec,
    gn: int,
    catalog_wps: List[GoalBall],
    world_ops_sequence: List[Tuple[callable, callable]],
    tasks_by_epoch: List[List[Tuple[np.ndarray, Tuple[int, ...]]]],
    n_calib_epochs: int,
    max_pg_rank: int = 16,
    spotcheck_direct_ref: bool = False,
) -> Dict[str, dict]:
    """Runs all 5 competing continual response-reuse methods across `world_ops_sequence` (`T` epochs),
    verifying 0 bound violations against independent killed-operator Subset Macro-Bellman ground truth
    STRICTLY OUTSIDE the per-method runtime timers!
    """
    methods = (
        "ExactRing-Rebuild",
        "Structure-Memory-Fresh-Exact",
        "Residual-Audited-Rank0",
        "POD-Galerkin-Certified",
        "TaskWeighted-Galerkin-Certified",
    )
    n_wps = len(catalog_wps)
    n_epochs = len(world_ops_sequence)

    # Precompute independent killed-operator exact waypoint tables (`Omega \ Gamma_dst`) for test epochs
    ref_tables: Dict[int, Tuple[SchurPortPlanner, Dict[int, Tuple[np.ndarray, np.ndarray]]]] = {}
    for ep in range(n_calib_epochs, n_epochs):
        qf, bf = world_ops_sequence[ep]
        pl_ref = SchurPortPlanner(spec, gn, qf, bf, catalog_wps, initial_sectors_per_wp="L1", lazy_init=True)
        needed_ep = sorted({w for _, sub in tasks_by_epoch[ep] for w in sub})
        ref_tables[ep] = (pl_ref, _precompute_killed_epoch_tables(pl_ref, needed_ep))

    did_spotcheck = False
    out_m: Dict[str, dict] = {}
    for m in methods:
        qf0, bf0 = world_ops_sequence[0]
        init_lv = "EXACT" if m in ("ExactRing-Rebuild", "POD-Galerkin-Certified", "TaskWeighted-Galerkin-Certified") else "L1"
        t_from_zero = 0.0
        t_test_epochs = 0.0
        svd_pg_audit_ms = 0.0
        lus_in_test = 0
        pg_wps_certified = 0
        pg_wps_attempted = 0
        fallback_exact_refreshes = 0
        viols = 0
        certs = 0
        regrets = []
        pending_audits = []

        t0 = time.perf_counter()
        pl = SchurPortPlanner(spec, gn, qf0, bf0, catalog_wps, initial_sectors_per_wp=init_lv, lazy_init=True)
        t_from_zero += 1000.0 * (time.perf_counter() - t0)

        snap_bank: Dict[int, List[np.ndarray]] = {j: [] for j in range(n_wps)}

        for ep in range(n_epochs):
            qf, bf = world_ops_sequence[ep]
            lu_before_ep = pl.lu_factorizations
            t_ep0 = time.perf_counter()
            if ep > 0:
                if m in ("ExactRing-Rebuild",):
                    pl.update_world_with_residual_audit(qf, bf, mode="scratch_rebuild")
                elif m == "Structure-Memory-Fresh-Exact":
                    pl.update_world_with_residual_audit(qf, bf, mode="structure_only_fresh_exact")
                elif m == "Residual-Audited-Rank0":
                    pl.update_world_with_residual_audit(qf, bf, mode="selective_residual")
                else:
                    # Petrov-Galerkin methods: assemble new operator WITHOUT factorizing `splu` upfront!
                    _assemble_new_operator_lazy_no_lu(pl, qf, bf)
                    needed_wps = sorted({w for _, sub in tasks_by_epoch[ep] for w in sub})
                    mpg = "colwise_irls_linf" if m == "TaskWeighted-Galerkin-Certified" else "pod_svd_l2"
                    for w_id in needed_wps:
                        if snap_bank[w_id]:
                            pg_wps_attempted += 1
                            pg_inf = _try_petrov_galerkin_waypoint_inject(pl, w_id, snap_bank[w_id], max_rank=max_pg_rank, mode_pg=mpg)
                            svd_pg_audit_ms += pg_inf["ms"]
                            if pg_inf["accepted_pre_dp"]:
                                pg_wps_certified += 1

            mt = MacroTourPlanner(pl)
            ep_records = []
            for s_xy, sub_ids in tasks_by_epoch[ep]:
                if m == "ExactRing-Rebuild":
                    res = mt.plan_exact_subset_dp(s_xy, sub_ids)
                elif m in ("POD-Galerkin-Certified", "TaskWeighted-Galerkin-Certified") and ep < n_calib_epochs:
                    res = mt.plan_exact_subset_dp(s_xy, sub_ids)
                else:
                    bs_b = pl.total_lu_backsolves
                    res = mt.plan_subset_macro_policy(s_xy, sub_ids, epsilon_tol=0.25, max_refine_steps=12, use_incremental_dp=True)
                    if m in ("POD-Galerkin-Certified", "TaskWeighted-Galerkin-Certified") and pl.total_lu_backsolves > bs_b:
                        fallback_exact_refreshes += 1
                if ep >= n_calib_epochs:
                    ep_records.append((ep, s_xy, sub_ids, res["macro_value_bounds"], res["policy_action_idx"], bool(res["certified"])))

            # Harvest current-epoch exact columns into `snap_bank` for Petrov-Galerkin methods (charged inside timer!)
            if m in ("POD-Galerkin-Certified", "TaskWeighted-Galerkin-Certified"):
                for w_id in range(n_wps):
                    if pl._is_level_exact_in_current_epoch(w_id, "EXACT"):
                        _, U_ex = pl._wp_tree[w_id]["EXACT"]
                        snap_bank[w_id].append(U_ex.copy())
                        if len(snap_bank[w_id]) > 4:
                            snap_bank[w_id].pop(0)

            dt_ep = 1000.0 * (time.perf_counter() - t_ep0)
            t_from_zero += dt_ep
            if ep >= n_calib_epochs:
                t_test_epochs += dt_ep
                lus_in_test += int(pl.lu_factorizations - lu_before_ep)
                pending_audits.extend(ep_records)

        # Ground-truth audit check strictly OUTSIDE planner runtime timers!
        for ep, s_xy, sub_ids, bounds_c, pol_idx, is_cert in pending_audits:
            certs += int(is_cert)
            pl_r, kvp = ref_tables[ep]
            opt_c, pol_c = _eval_killed_macro_bellman_from_tables(pl_r, kvp, s_xy, sub_ids, pol_idx)
            if spotcheck_direct_ref and not did_spotcheck:
                ref_dir = independent_exact_macro_bellman_reference(pl_r, s_xy, sub_ids, policy_action_idx=pol_idx)
                assert abs(opt_c - ref_dir["optimal_adaptive_macro_cost"]) <= 1e-13
                assert abs(pol_c - ref_dir["evaluated_policy_exact_macro_cost"]) <= 1e-13
                did_spotcheck = True
            lo_c, hi_c = bounds_c
            if not ((lo_c - 1e-9 <= opt_c <= hi_c + 1e-9) and (opt_c - 1e-9 <= pol_c <= hi_c + 1e-9)):
                viols += 1
            regrets.append(float(max(0.0, pol_c - opt_c)))

        lu_total = int(pl.lu_factorizations)
        bs_total = int(pl.total_lu_backsolves)
        out_m[m] = {
            "from_zero_cumulative_ms": t_from_zero,
            "test_epochs_marginal_ms": t_test_epochs,
            "svd_plus_pg_plus_residual_audit_ms": svd_pg_audit_ms,
            "total_lu_factorizations": lu_total,
            "test_epochs_lu_factorizations": lus_in_test,
            "total_lu_backsolves": bs_total,
            "pg_waypoints_certified_without_lu": pg_wps_certified,
            "pg_waypoints_attempted": pg_wps_attempted,
            "fallback_exact_task_triggers": fallback_exact_refreshes,
            "certified_test_tasks": certs,
            "bound_violations": viols,
            "mean_exact_bellman_regret": float(np.mean(regrets)) if regrets else 0.0,
        }
    return out_m


def _exp5b_continual_subspace_worker(args: Tuple[int, int]) -> dict:
    idx_m, ms = args
    out_regimes = {}

    for dim, gn, r_wp, dim_lbl in [(2, 51, 0.25, "2D-51sq"), (3, 21, 0.34, "3D-21cubed")]:
        world = generate_benchmark_map(ms, dim=dim, regime="narrow_barrier", with_drift=True)
        rng = np.random.default_rng(ms + 505 * dim)
        catalog_wps = _sample_nonoverlapping_balls(rng, 10, dim, r_wp, 1.18)

        # Stream 1: Realistic unstructured `+12`-probe online GP refits (`6` epochs: `ep=0` calib + `5` test updates)
        X_cur, q_cur, b_cur = sample_noisy_probes(world, n_probes=32 if dim == 2 else 48, seed=ms + 17 * dim, include_drift=True)
        gp_ops_seq = []
        for ep in range(6):
            km_ep = KrigingWorldModel(X_cur.copy(), q_cur.copy(), b_cur.copy())
            gp_ops_seq.append((km_ep.predict_q, km_ep.predict_b))
            if ep < 5:
                X_add = rng.uniform(-1.35, 1.35, size=(12, dim))
                obs_rng = np.random.default_rng(np.random.SeedSequence([ms, dim, ep, 7701]))
                Xa, qa, ba = observe_world_at_points(world, X_add, obs_rng, include_drift=True)
                X_cur = np.vstack([X_cur, Xa])
                q_cur = np.concatenate([q_cur, qa])
                b_cur = np.vstack([b_cur, ba])

        tasks_gp = []
        for ep in range(6):
            ep_t = []
            for _ in range(6):
                sub = tuple(sorted(rng.choice(len(catalog_wps), size=4, replace=False).tolist()))
                s_xy = rng.uniform(-1.18, 1.18, size=dim)
                ep_t.append((s_xy, sub))
            tasks_gp.append(ep_t)

        res_gp_stream = _run_evolving_world_stream_on_map(
            world.spec, gn, catalog_wps, gp_ops_seq, tasks_gp, n_calib_epochs=1, max_pg_rank=24, spotcheck_direct_ref=(idx_m == 0)
        )

        # Stream 2: Low-dimensional parametric hazard/wind modulation family (`3` calibration epochs -> `5` test epochs)
        km_base = KrigingWorldModel(*sample_noisy_probes(world, n_probes=44 if dim == 2 else 60, seed=ms + 99 * dim, include_drift=True))
        c_mod1 = np.zeros(dim, dtype=float); c_mod1[0] = -0.35
        c_mod2 = np.zeros(dim, dtype=float); c_mod2[0] = 0.35
        param_amps = [
            (0.00, 0.00),
            (0.06, 0.00),
            (0.00, 0.06),
            # 5 test epochs interpolating inside/near the 2-parameter hazard manifold (`|\Delta q| ~ 0.04..0.06`)
            (0.03, 0.03),
            (0.045, 0.015),
            (0.015, 0.045),
            (0.05, 0.02),
            (0.025, 0.05),
        ]
        param_ops_seq = []
        for a1, a2 in param_amps:
            def _qf(X, _a1=a1, _a2=a2, _km=km_base, _c1=c_mod1, _c2=c_mod2):
                d1 = np.sum((X - _c1[None, :]) ** 2, axis=1)
                d2 = np.sum((X - _c2[None, :]) ** 2, axis=1)
                return _km.predict_q(X) + _a1 * np.exp(-d1 / 0.30) + _a2 * np.exp(-d2 / 0.30)
            param_ops_seq.append((_qf, km_base.predict_b))

        tasks_param = []
        for ep in range(len(param_amps)):
            ep_t = []
            for _ in range(6):
                sub = tuple(sorted(rng.choice(len(catalog_wps), size=4, replace=False).tolist()))
                s_xy = rng.uniform(-1.18, 1.18, size=dim)
                ep_t.append((s_xy, sub))
            tasks_param.append(ep_t)

        res_param_stream = _run_evolving_world_stream_on_map(
            world.spec, gn, catalog_wps, param_ops_seq, tasks_param, n_calib_epochs=3, max_pg_rank=28
        )

        out_regimes[f"{dim_lbl}_RealisticGPStream"] = res_gp_stream
        out_regimes[f"{dim_lbl}_LowDimParametricStream"] = res_param_stream

    return {"map_seed": ms, "streams": out_regimes}


def run_exp5_diagnostic_suite(max_workers: int = 8) -> dict:
    # 5A: 8 Standard + 8 Competing-Corridor maps
    tasks_5a = [(i, 30100 + i, "narrow_barrier") for i in range(8)] + [
        (8 + i, 30200 + i, "competing_corridor") for i in range(8)
    ]
    rows_5a = run_map_parallel(_exp5a_fixed_world_worker, tasks_5a, max_workers=max_workers)

    def _sum_5a(sub_rows: List[dict]) -> dict:
        ranks_eval = (4, 8, 16, 32, 64)
        rc_out = {}
        for bk in ("Standard_POD_SVD", "TaskWeighted_SVD"):
            rc_out[bk] = {}
            for rk in ranks_eval:
                ks = f"r_{rk}"
                nt_vals = [
                    r["rank_curves"][bk][ks]["neartie_top1_agreement_rate"]
                    for r in sub_rows
                    if r["rank_curves"][bk][ks]["neartie_top1_agreement_rate"] is not None
                ]
                rc_out[bk][ks] = {
                    "mean_root_Q_linf_err": float(np.mean([r["rank_curves"][bk][ks]["mean_root_Q_linf_err"] for r in sub_rows])),
                    "top1_action_agreement_rate": float(np.mean([r["rank_curves"][bk][ks]["top1_action_agreement_rate"] for r in sub_rows])),
                    "neartie_top1_agreement_rate": float(np.mean(nt_vals)) if nt_vals else None,
                    "mean_induced_root_bellman_regret": float(np.mean([r["rank_curves"][bk][ks]["mean_induced_root_bellman_regret"] for r in sub_rows])),
                }
        return {
            "n_maps": len(sub_rows),
            "naive_interior_pod_unseen_min_residual_linf": float(min(r["naive_interior_pod_unseen_min_residual_linf"] for r in sub_rows)),
            "naive_interior_pod_unseen_certified_rate": float(np.mean([r["naive_interior_pod_unseen_certified_rate"] for r in sub_rows])),
            "mean_seen_catalog_exactring_cached_12tasks_ms": float(np.mean([r["seen_catalog_exactring_cached_12tasks_ms"] for r in sub_rows])),
            "mean_unseen_targets_exactring_from_zero_12tasks_ms": float(np.mean([r["unseen_targets_exactring_from_zero_12tasks_ms"] for r in sub_rows])),
            "mean_portal_green_bank_offline_build_ms": float(np.mean([r["portal_green_bank_offline_build_ms"] for r in sub_rows])),
            "mean_rank_90pct_energy": float(np.mean([r["portal_spectral_ranks"]["r_90pct"] for r in sub_rows])),
            "mean_rank_99pct_energy": float(np.mean([r["portal_spectral_ranks"]["r_99pct"] for r in sub_rows])),
            "mean_rank_99_9pct_energy": float(np.mean([r["portal_spectral_ranks"]["r_99_9pct"] for r in sub_rows])),
            "mean_portals_full_rank": float(np.mean([r["portal_spectral_ranks"]["n_portals_full_rank"] for r in sub_rows])),
            "rank_curves": rc_out,
        }

    sum_5a = {
        "standard_narrow_barrier_8maps": _sum_5a([r for r in rows_5a if r["regime"] == "narrow_barrier"]),
        "competing_corridor_8maps": _sum_5a([r for r in rows_5a if r["regime"] == "competing_corridor"]),
        "pooled_16maps": _sum_5a(rows_5a),
        "per_map_records": rows_5a,
    }

    # 5B: 12 maps continual evolving-world streams (`2D 51^2` & `3D 21^3`, Realistic GP vs Low-Dim Parametric)
    seeds_5b = list(range(30300, 30312))
    rows_5b = run_map_parallel(_exp5b_continual_subspace_worker, [(i, s) for i, s in enumerate(seeds_5b)], max_workers=max_workers)
    methods_5b = (
        "ExactRing-Rebuild",
        "Structure-Memory-Fresh-Exact",
        "Residual-Audited-Rank0",
        "POD-Galerkin-Certified",
        "TaskWeighted-Galerkin-Certified",
    )
    streams_out = {}
    for sk in rows_5b[0]["streams"].keys():
        ex_fz = np.array([r["streams"][sk]["ExactRing-Rebuild"]["from_zero_cumulative_ms"] for r in rows_5b])
        st_fz = np.array([r["streams"][sk]["Structure-Memory-Fresh-Exact"]["from_zero_cumulative_ms"] for r in rows_5b])
        ex_mg = np.array([r["streams"][sk]["ExactRing-Rebuild"]["test_epochs_marginal_ms"] for r in rows_5b])
        st_mg = np.array([r["streams"][sk]["Structure-Memory-Fresh-Exact"]["test_epochs_marginal_ms"] for r in rows_5b])
        m_dict = {}
        for m in methods_5b:
            m_fz = np.array([r["streams"][sk][m]["from_zero_cumulative_ms"] for r in rows_5b])
            m_mg = np.array([r["streams"][sk][m]["test_epochs_marginal_ms"] for r in rows_5b])
            att_tot = sum(r["streams"][sk][m]["pg_waypoints_attempted"] for r in rows_5b)
            cert_tot = sum(r["streams"][sk][m]["pg_waypoints_certified_without_lu"] for r in rows_5b)
            m_dict[m] = {
                "mean_from_zero_cumulative_ms": float(np.mean(m_fz)),
                "mean_test_epochs_marginal_ms": float(np.mean(m_mg)),
                "mean_svd_pg_audit_overhead_ms": float(np.mean([r["streams"][sk][m]["svd_plus_pg_plus_residual_audit_ms"] for r in rows_5b])),
                "mean_total_lu_factorizations": float(np.mean([r["streams"][sk][m]["total_lu_factorizations"] for r in rows_5b])),
                "mean_test_epochs_lu_factorizations": float(np.mean([r["streams"][sk][m]["test_epochs_lu_factorizations"] for r in rows_5b])),
                "mean_total_lu_backsolves": float(np.mean([r["streams"][sk][m]["total_lu_backsolves"] for r in rows_5b])),
                "pg_pre_dp_certification_rate": float(cert_tot / max(att_tot, 1)) if att_tot > 0 else 0.0,
                "mean_fallback_triggers": float(np.mean([r["streams"][sk][m]["fallback_exact_task_triggers"] for r in rows_5b])),
                "total_bound_violations": int(sum(r["streams"][sk][m]["bound_violations"] for r in rows_5b)),
                "mean_exact_bellman_regret": float(np.mean([r["streams"][sk][m]["mean_exact_bellman_regret"] for r in rows_5b])),
                "rel_savings_from_zero_vs_ExactRing_pct": float(100.0 * (1.0 - np.mean(m_fz) / np.mean(ex_fz))),
                "rel_savings_test_marginal_vs_best_classical_pct": float(
                    100.0 * (1.0 - np.mean(m_mg) / min(float(np.mean(ex_mg)), float(np.mean(st_mg))))
                ),
                "paired_from_zero_minus_ExactRing": paired_stats(m_fz - ex_fz),
                "paired_test_marginal_minus_ExactRing": paired_stats(m_mg - ex_mg),
                "paired_test_marginal_minus_StructureMemory": paired_stats(m_mg - st_mg),
            }
        streams_out[sk] = m_dict

    # 5C: Pre-declared Go / No-Go Gate (`>= 20%` net from-zero savings over best classical baseline at `0` violations)
    gate_eval = {}
    for sk, md in streams_out.items():
        best_pg = min(
            ("POD-Galerkin-Certified", "TaskWeighted-Galerkin-Certified"),
            key=lambda k: md[k]["mean_from_zero_cumulative_ms"],
        )
        best_cl = min(
            ("ExactRing-Rebuild", "Structure-Memory-Fresh-Exact", "Residual-Audited-Rank0"),
            key=lambda k: md[k]["mean_from_zero_cumulative_ms"],
        )
        sav_fz_pct = 100.0 * (1.0 - md[best_pg]["mean_from_zero_cumulative_ms"] / md[best_cl]["mean_from_zero_cumulative_ms"])
        sav_mg_pct = md[best_pg]["rel_savings_test_marginal_vs_best_classical_pct"]
        viols_pg = md[best_pg]["total_bound_violations"]
        gate_eval[sk] = {
            "best_subspace_method": best_pg,
            "best_classical_baseline_from_zero": best_cl,
            "net_from_zero_savings_vs_best_classical_pct": float(sav_fz_pct),
            "post_calib_test_marginal_savings_vs_best_classical_pct": float(sav_mg_pct),
            "bound_violations": int(viols_pg),
            "passes_20pct_from_zero_go_gate": bool(viols_pg == 0 and sav_fz_pct >= 20.0),
            "passes_20pct_post_calibration_marginal_gate": bool(viols_pg == 0 and sav_mg_pct >= 20.0),
        }

    return {
        "exp5a_fixed_world_compressibility_and_obstruction": sum_5a,
        "exp5b_continual_petrov_galerkin_streams_12maps": {
            "seeds": seeds_5b,
            "streams": streams_out,
            "per_map_records": rows_5b,
        },
        "exp5c_predeclared_20pct_go_nogo_gate": gate_eval,
    }


def plot_exp5(res: dict, out_png: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(16.4, 10.2))
    s5a = res["exp5a_fixed_world_compressibility_and_obstruction"]["pooled_16maps"]
    ranks = [4, 8, 16, 32, 64]

    # Panel A: Unseen-Target Induced Root Bellman Regret vs Rank `r` (`Standard POD` vs `Task-Weighted SVD`)
    ax = axes[0, 0]
    y_pod = [max(s5a["rank_curves"]["Standard_POD_SVD"][f"r_{r}"]["mean_induced_root_bellman_regret"], 1e-6) for r in ranks]
    y_tw = [max(s5a["rank_curves"]["TaskWeighted_SVD"][f"r_{r}"]["mean_induced_root_bellman_regret"], 1e-6) for r in ranks]
    ax.plot(ranks, y_pod, "o--", color="#d62728", lw=2.0, label="Standard Unweighted POD/SVD")
    ax.plot(ranks, y_tw, "s-", color="#2ca02c", lw=2.2, label="Task-Weighted Portal SVD")
    ax.set_yscale("log")
    ax.set_xticks(ranks)
    ax.set_xlabel("Subspace Rank r (Full Portal Rank ≈ 225)")
    ax.set_ylabel("Mean Induced Root Bellman Regret (max(·, 1e-6), log)")
    ax.set_title(
        f"A. Fixed-World Unseen-Target Regret vs Rank (16 Maps)\n"
        f"(Naive Interior-POD Unseen Residual = {s5a['naive_interior_pod_unseen_min_residual_linf']:.2f}, Cert = 0%)",
        fontsize=9.3,
    )
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8.0)

    # Panel B: Top-1 Action Agreement (Overall vs Near-Tie `gap < 0.25`)
    ax = axes[0, 1]
    ag_pod = [100.0 * s5a["rank_curves"]["Standard_POD_SVD"][f"r_{r}"]["top1_action_agreement_rate"] for r in ranks]
    ag_tw = [100.0 * s5a["rank_curves"]["TaskWeighted_SVD"][f"r_{r}"]["top1_action_agreement_rate"] for r in ranks]
    nt_pod = [100.0 * (s5a["rank_curves"]["Standard_POD_SVD"][f"r_{r}"]["neartie_top1_agreement_rate"] or 0.0) for r in ranks]
    nt_tw = [100.0 * (s5a["rank_curves"]["TaskWeighted_SVD"][f"r_{r}"]["neartie_top1_agreement_rate"] or 0.0) for r in ranks]
    ax.plot(ranks, ag_pod, "o--", color="#d62728", lw=1.8, label="Standard POD (All Tasks)")
    ax.plot(ranks, ag_tw, "s-", color="#2ca02c", lw=2.1, label="Task-Weighted SVD (All Tasks)")
    ax.plot(ranks, nt_pod, "^:", color="#ff7f0e", lw=1.7, label="Standard POD (Near-Tie gap<.25)")
    ax.plot(ranks, nt_tw, "D-.", color="#1f77b4", lw=1.9, label="Task-Weighted SVD (Near-Tie gap<.25)")
    ax.set_xticks(ranks)
    ax.set_ylim(10, 102)
    ax.set_xlabel("Subspace Rank r")
    ax.set_ylabel("Root Optimal Action Agreement (%)")
    ax.set_title(
        f"B. Action-Ranking Preservation vs Rank (99% Energy Rank ≈ {s5a['mean_rank_99pct_energy']:.0f})\n"
        f"(ExactRing Seen-Cache: {s5a['mean_seen_catalog_exactring_cached_12tasks_ms']:.1f} ms vs Unseen: {s5a['mean_unseen_targets_exactring_from_zero_12tasks_ms']:.1f} ms)",
        fontsize=9.3,
    )
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.6, loc="upper left")

    # Panel C: Continual Evolving-World From-Zero Cumulative Compute (`12` Maps, Realistic GP vs Parametric)
    ax = axes[1, 0]
    st_b = res["exp5b_continual_petrov_galerkin_streams_12maps"]["streams"]
    s_keys = [
        "2D-51sq_RealisticGPStream",
        "2D-51sq_LowDimParametricStream",
        "3D-21cubed_RealisticGPStream",
        "3D-21cubed_LowDimParametricStream",
    ]
    s_lbls = ["2D Realistic\n+12 GP Stream", "2D Low-Dim\nParametric", "3D Realistic\n+12 GP Stream", "3D Low-Dim\nParametric"]
    x = np.arange(len(s_keys))
    w = 0.16
    for off, mk, lbl, col in [
        (-2 * w, "ExactRing-Rebuild", "ExactRing Rebuild", "#333333"),
        (-1 * w, "Structure-Memory-Fresh-Exact", "Structure-Memory", "#ff7f0e"),
        (0 * w, "Residual-Audited-Rank0", "Residual-Rank0", "#9467bd"),
        (1 * w, "POD-Galerkin-Certified", "POD-Galerkin + Cert", "#1f77b4"),
        (2 * w, "TaskWeighted-Galerkin-Certified", "TaskWt-Galerkin + Cert", "#2ca02c"),
    ]:
        ys = [st_b[sk][mk]["mean_from_zero_cumulative_ms"] for sk in s_keys]
        ax.bar(x + off, ys, width=w, color=col, label=lbl)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(s_lbls, fontsize=8.0)
    ax.set_ylabel("From-Zero Cumulative Compute (ms, log)")
    ax.set_title("C. Continual World-Stream Total Cost Incl. SVD + Audit + Fallback (0 Viols)", fontsize=9.3)
    ax.grid(True, axis="y", which="both", alpha=0.3)
    ax.legend(fontsize=7.2, loc="upper left")

    # Panel D: Pre-DP Petrov-Galerkin Certification Rate & Post-Calib Marginal Time in 3D
    ax = axes[1, 1]
    s_3d = ["3D-21cubed_RealisticGPStream", "3D-21cubed_LowDimParametricStream"]
    x3 = np.arange(len(s_3d))
    w3 = 0.16
    max_y3 = max(
        st_b[sk][mk]["mean_test_epochs_marginal_ms"]
        for sk in s_3d
        for mk in ("ExactRing-Rebuild", "Structure-Memory-Fresh-Exact", "Residual-Audited-Rank0", "POD-Galerkin-Certified", "TaskWeighted-Galerkin-Certified")
    )
    for off, mk, lbl, col in [
        (-2 * w3, "ExactRing-Rebuild", "ExactRing", "#333333"),
        (-1 * w3, "Structure-Memory-Fresh-Exact", "Structure-Memory", "#ff7f0e"),
        (0 * w3, "Residual-Audited-Rank0", "Residual-Rank0", "#9467bd"),
        (1 * w3, "POD-Galerkin-Certified", "POD-Galerkin", "#1f77b4"),
        (2 * w3, "TaskWeighted-Galerkin-Certified", "TaskWt-Galerkin", "#2ca02c"),
    ]:
        ys = [st_b[sk][mk]["mean_test_epochs_marginal_ms"] for sk in s_3d]
        bars = ax.bar(x3 + off, ys, width=w3, color=col, label=lbl)
        if "Galerkin" in mk:
            for b, sk in zip(bars, s_3d):
                cr = 100.0 * st_b[sk][mk]["pg_pre_dp_certification_rate"]
                ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.015 * max_y3, f"{cr:.0f}%\ncert", ha="center", va="bottom", fontsize=7.0)
    ax.set_ylim(0.0, 1.32 * max_y3)
    ax.set_xticks(x3)
    ax.set_xticklabels(["3D 21³ Realistic +12 GP Updates\n(Unstructured Innovations)", "3D 21³ Low-Dim Parametric\n(2-Mode Hazard Manifold)"], fontsize=8.3)
    ax.set_ylabel("Post-Calibration Test-Stream Marginal Compute (ms)")
    ax.set_title("D. 3D Test-Stream Marginal Compute & Pre-DP Subspace Cert Rate", fontsize=9.3)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=7.3, loc="upper left", ncol=2)

    plt.tight_layout()
    plt.savefig(out_png, dpi=175)
    plt.close(fig)


def main() -> None:
    enforce_single_thread_env()
    n_workers = 8
    out_dir = Path(__file__).resolve().parent
    t0 = time.perf_counter()
    print(f"=== Running Exp 5 Falsifiable Response-Subspace Diagnostic ({n_workers} Workers) ===", flush=True)
    res = run_exp5_diagnostic_suite(max_workers=n_workers)
    meta = collect_runtime_metadata(max_workers=n_workers)
    payload = {
        "metadata": meta,
        "source_manifest": meta["source_manifest"],
        "block_provenance": "fresh_computed_in_current_run",
        **res,
    }
    (out_dir / "exp5_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plot_exp5(res, out_dir / "exp5_response_subspace.png")
    print(f"Saved exp5_results.json and exp5_response_subspace.png in {time.perf_counter()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
