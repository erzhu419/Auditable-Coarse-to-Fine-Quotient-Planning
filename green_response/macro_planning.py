"""Scalable Certified Multi-Waypoint Planning inside the Green Response Space (`green_response.macro_planning`):

Audit Closures & Upgrades (`85e2323` Post-Audit):
1. Gauge-Normalized Terminal-Cost Shift Invariance (`Bug 2.2`):
   Normalizes boundary desirability to `g_b = 1` (`Z_bar_b = H_b 1`, `c0_b = -lam * log(Z_bar_b)`,
   `P_b f = H_b f / Z_bar_b`) and factors deterministic subset terminal-cost sums `Phi(S) = sum_{b in S} phi_b`
   cleanly out of backward interval DP, preserving bit-identical interval widths, policies, and refinement
   trajectories across arbitrary `phi_b in [-500, +500]` without desirability underflow!
2. Fail-Closed Outward Interval Arithmetic & Zero-Budget Guard (`Bugs 2.3 & 2.4`):
   Removes all midpoint-repair blocks; checks `step_i >= max_refine_steps` BEFORE any refinement;
   returns typed `IntervalCertificate` dicts with nullable `policy_action_idx` / `bounds` on `numeric_invalid`.
3. Matched-Policy-Class Operational Exact-Ring Baselines (`Stage B1`):
   `plan_exact_subset_dp` (`Full-ExactRing + identical O(m^2 2^m) Subset-DP`) and `plan_exact_fixed_tour`
   (`Cached-ExactRing + Fixed-Tour Suffix Evaluation`), sharing identical `splu(A_0)` caching and policy classes.
4. Decision-Guided Dual-Occupancy × Cost-Normalized Refinement (`Stage C`):
   Propagates incumbent (`mu_hat`) and contender (`mu_check`) forward state-subset occupancies in `< 2 ms`,
   refining only waypoints whose port uncertainty contributes to the root decision gap per new LU backsolve!
"""
from __future__ import annotations

import itertools
import math
import time
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import scipy.sparse.linalg as spla

from .core import IntervalCertificate
from .port_solvers import LEVEL_RANK, SchurPortPlanner, next_finer_level


def _build_macro_eval_layout(
    pl: SchurPortPlanner, s_node: int, t_list: Sequence[int]
) -> Tuple[np.ndarray, Dict[int, slice], Dict[int, np.ndarray]]:
    eval_chunks = [np.array([s_node], dtype=np.int64)] + [pl.wp_rings[a] for a in t_list]
    eval_nodes = np.concatenate(eval_chunks)
    offsets: Dict[int, slice] = {}
    in_ball_eval: Dict[int, np.ndarray] = {}
    cur_off = 1
    for a in t_list:
        offsets[a] = slice(cur_off, cur_off + len(pl.wp_rings[a]))
        cur_off += len(pl.wp_rings[a])
    for b in t_list:
        in_ball_eval[b] = pl.wp_masks[b][eval_nodes]
    return eval_nodes, offsets, in_ball_eval


def independent_exact_ball_operators(
    pl: SchurPortPlanner, s_node: int, target_ids: Sequence[int]
) -> Tuple[np.ndarray, Dict[int, slice], Dict[int, np.ndarray], Dict[int, np.ndarray], float]:
    """Independent sparse-LU reference on `Omega \\ Gamma_b` (NEVER touching `pl._wp_tree` or
    `pl.bound_harmonic_batch`!) with exact `t = 0` ball absorption and gauge-normalized `Z_bar = H_b 1`
    so arbitrary finite `phi_b` never underflows!
    """
    t_list = list(target_ids)
    eval_nodes, offsets, _ = _build_macro_eval_layout(pl, s_node, t_list)
    A_csr = pl.A0.tocsr()
    N = len(pl.pts)
    lam = pl.spec.lam

    exact_val: Dict[int, np.ndarray] = {}
    P_ring: Dict[int, np.ndarray] = {}
    min_H_entry = np.inf

    for dst in t_list:
        mask_b = pl.wp_masks[dst]
        ring_b = pl.wp_rings[dst]
        ext_idx = np.flatnonzero(~mask_b)
        A_ee = A_csr[ext_idx, :][:, ext_idx].tocsc()
        lu_ee = spla.splu(A_ee)
        RHS = -(A_csr[ext_idx, :][:, ring_b].toarray())
        H_ext = lu_ee.solve(RHS)

        min_H_entry = min(min_H_entry, float(np.min(H_ext)))
        phi_b = float(pl.waypoints[dst].phi)
        Z_bar_ext = H_ext @ np.ones(len(ring_b), dtype=float)
        V_full = np.full(N, phi_b, dtype=float)
        V_full[ext_idx] = phi_b - lam * np.log(Z_bar_ext)

        P_full = np.zeros((N, len(ring_b)), dtype=float)
        P_full[ext_idx, :] = H_ext / Z_bar_ext[:, None]
        for k_r, nid in enumerate(ring_b):
            P_full[int(nid), k_r] = 1.0

        exact_val[dst] = V_full[eval_nodes]
        P_ring[dst] = P_full[eval_nodes, :]

    return eval_nodes, offsets, exact_val, P_ring, min_H_entry


def independent_exact_ball_tour_scores(
    pl: SchurPortPlanner, start_xy: Sequence[float], target_ids: Sequence[int]
) -> Tuple[Dict[Tuple[int, ...], float], float]:
    """Independent exact discrete ball-stopping tour scores for all `m!` permutations."""
    s_node = int(np.argmin(np.sum((pl.pts - np.asarray(start_xy, dtype=float)[None, :]) ** 2, axis=1)))
    t_list = list(target_ids)
    m = len(t_list)
    eval_nodes, offsets, exact_val, P_ring, min_H = independent_exact_ball_operators(pl, s_node, t_list)
    in_ball = {b: pl.wp_masks[b][eval_nodes] for b in t_list}

    W_suf: Dict[Tuple[int, ...], np.ndarray] = {(b,): exact_val[b].copy() for b in t_list}
    for L_s in range(2, m + 1):
        first_only = (L_s == m)
        for b in t_list:
            others = [x for x in t_list if x != b]
            sl_b = offsets[b]
            ib_b = in_ball[b]
            Pb = P_ring[b][0:1, :] if first_only else P_ring[b]
            vb = exact_val[b][0:1] if first_only else exact_val[b]
            for rest in itertools.permutations(others, L_s - 1):
                w_r = W_suf[rest]
                cont_ext = Pb @ w_r[sl_b]
                if first_only:
                    val_out = np.where(ib_b[0:1], vb + w_r[0:1], vb + cont_ext)
                else:
                    val_out = np.where(ib_b, vb + w_r, vb + cont_ext)
                W_suf[(b, *rest)] = val_out

    scores = {perm: float(W_suf[perm][0]) for perm in itertools.permutations(t_list, m)}
    return scores, min_H


def independent_exact_macro_bellman_reference(
    pl: SchurPortPlanner,
    start_xy: Sequence[float],
    target_ids: Sequence[int],
    policy_action_idx: Optional[np.ndarray] = None,
) -> dict:
    """Independent exact `O(m^2 2^m)` Subset Macro-Bellman reference on `Omega \\ Gamma_b`:
    Computes exact optimal adaptive macro value `F*(x_0, T)` AND (if `policy_action_idx` of shape
    `(N_eval, 2^m)` is supplied) exact policy value `J^{pi_hat}(x_0, T)` across ALL row x mask states!
    """
    s_node = int(np.argmin(np.sum((pl.pts - np.asarray(start_xy, dtype=float)[None, :]) ** 2, axis=1)))
    t_list = list(target_ids)
    m = len(t_list)
    eval_nodes, offsets, exact_val, P_ring, _ = independent_exact_ball_operators(pl, s_node, t_list)
    in_ball = {b: pl.wp_masks[b][eval_nodes] for b in t_list}

    n_ev = len(eval_nodes)
    n_masks = 1 << m
    F_opt = np.zeros((n_ev, n_masks), dtype=float)
    J_pol = np.zeros((n_ev, n_masks), dtype=float) if policy_action_idx is not None else None

    for i, b in enumerate(t_list):
        mk = 1 << i
        F_opt[:, mk] = exact_val[b]
        if J_pol is not None:
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
                qb_opt = exact_val[b] + cont_opt
                best_v = np.minimum(best_v, qb_opt)

                if J_pol is not None:
                    j_rem = J_pol[:, rem]
                    cont_pol = np.where(in_ball[b], j_rem, P_ring[b] @ j_rem[offsets[b]])
                    q_choices[i] = exact_val[b] + cont_pol
            F_opt[:, mk] = best_v
            if J_pol is not None:
                act_col = policy_action_idx[:, mk]
                out_col = np.full(n_ev, np.nan, dtype=float)
                for i, qv in q_choices.items():
                    sel = act_col == i
                    if np.any(sel):
                        out_col[sel] = qv[sel]
                J_pol[:, mk] = out_col

    full_mk = n_masks - 1
    return {
        "optimal_adaptive_macro_cost": float(F_opt[0, full_mk]),
        "evaluated_policy_exact_macro_cost": None if J_pol is None else float(J_pol[0, full_mk]),
        "F_opt_table": F_opt,
        "J_pol_table": J_pol,
    }


class MacroTourPlanner:
    """Scalable Certified Fixed-Order BnB, Matched Exact-Ring Operational DP, & Decision-Guided
    Adaptive Subset Macro-DP Planner (`green_response`).
    """

    def __init__(self, port_planner: SchurPortPlanner):
        self.pl = port_planner

    def _compute_single_leg_bounds(
        self, eval_nodes: np.ndarray, t_list: Sequence[int], in_ball_eval: Dict[int, np.ndarray]
    ) -> Tuple[Dict[int, dict], Dict[int, Tuple[np.ndarray, np.ndarray]], Dict[int, Tuple[np.ndarray, np.ndarray]], Dict[int, float], bool]:
        """Gauge-normalized single-leg intervals (`Z_bar_b = H_b 1`, `c0_b = -lam * log(Z_bar_b)`):
        100% invariant to `phi_b` shifts and strictly fail-closed (`0` midpoint repairs!).
        """
        lam = self.pl.spec.lam
        wp_prep: Dict[int, dict] = {b: self.pl.prepare_wp_ring_eval(b, eval_nodes) for b in t_list}
        Zbar_bounds: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
        C0_bounds: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
        wp_width: Dict[int, float] = {b: 0.0 for b in t_list}

        for b in t_list:
            phi_b = float(self.pl.waypoints[b].phi)
            if not np.isfinite(phi_b):
                return wp_prep, Zbar_bounds, C0_bounds, wp_width, False

            pr = wp_prep[b]
            ring_b = pr["ring_d"]
            ones_b = np.ones((len(ring_b), 1), dtype=float)
            zbar_lo_m, zbar_hi_m, ok = self.pl.bound_harmonic_batch(pr, ones_b, ones_b, eval_first_only=False)
            if not ok:
                return wp_prep, Zbar_bounds, C0_bounds, wp_width, False

            u1_b = pr["u1_full"]
            u1_ring = u1_b[ring_b]
            u1_err = float(pr.get("u1_err_sum", 0.0))

            zbar_m_lo = zbar_lo_m[:, 0] - 1e-12 * (1.0 + np.abs(zbar_lo_m[:, 0]))
            zbar_m_hi = zbar_hi_m[:, 0] + 1e-12 * (1.0 + np.abs(zbar_hi_m[:, 0]))

            if np.all(u1_ring - u1_err > 1e-14):
                gam_lo = float(np.min(1.0 / (u1_ring + u1_err)))
                gam_hi = float(np.max(1.0 / (u1_ring - u1_err)))
                zbar_pos_lo = gam_lo * np.maximum(0.0, u1_b[eval_nodes] - u1_err) * (1.0 - 1e-12)
                zbar_pos_hi = gam_hi * (u1_b[eval_nodes] + u1_err) * (1.0 + 1e-12)
                zbar_lo_b = np.maximum(zbar_m_lo, zbar_pos_lo)
                zbar_hi_b = np.minimum(zbar_m_hi, zbar_pos_hi)
            else:
                zbar_lo_b = zbar_m_lo
                zbar_hi_b = zbar_m_hi

            ib = in_ball_eval[b]
            if np.any(ib):
                zbar_lo_b[ib] = 1.0
                zbar_hi_b[ib] = 1.0

            # FAIL-CLOSED CHECK (zero midpoint repair!):
            if not (
                np.all(np.isfinite(zbar_lo_b))
                and np.all(np.isfinite(zbar_hi_b))
                and np.all(zbar_lo_b > 0.0)
                and np.all(zbar_lo_b <= zbar_hi_b)
            ):
                return wp_prep, Zbar_bounds, C0_bounds, wp_width, False

            c0_lo = -lam * np.log(zbar_hi_b)
            c0_hi = -lam * np.log(zbar_lo_b)
            if np.any(ib):
                c0_lo[ib] = 0.0
                c0_hi[ib] = 0.0
            Zbar_bounds[b] = (zbar_lo_b, zbar_hi_b)
            C0_bounds[b] = (c0_lo, c0_hi)
            has_stale_err = float(pr.get("u1_err_sum", 0.0)) > 0.0
            if pr["level"] != "EXACT" or has_stale_err:
                wp_width[b] = max(wp_width[b], float(np.max(c0_hi - c0_lo)))

        return wp_prep, Zbar_bounds, C0_bounds, wp_width, True

    def _propagate_leg_batch(
        self,
        b: int,
        wp_prep_b: dict,
        Zbar_b: Tuple[np.ndarray, np.ndarray],
        C0_b: Tuple[np.ndarray, np.ndarray],
        in_ball_b: np.ndarray,
        sl_b: slice,
        W_rem_lo: np.ndarray,
        W_rem_hi: np.ndarray,
        first_only: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray, bool]:
        """Propagates gauge-normalized continuation intervals `[W_rem_lo, W_rem_hi]` backward across
        leg `b` (`P_b f = H_b f / Z_bar_b`) with exact `t = 0` ball absorption and ZERO midpoint repair!
        """
        if not (np.all(np.isfinite(W_rem_lo)) and np.all(np.isfinite(W_rem_hi))) or np.any(W_rem_lo > W_rem_hi):
            return W_rem_lo, W_rem_hi, False

        F_lo_rb = W_rem_lo[sl_b, :]
        F_hi_rb = W_rem_hi[sl_b, :]
        f_min_rb = np.min(F_lo_rb, axis=0) - 1e-12 * (1.0 + np.max(np.abs(F_lo_rb), axis=0))
        f_max_rb = np.max(F_hi_rb, axis=0) + 1e-12 * (1.0 + np.max(np.abs(F_hi_rb), axis=0))
        mu_shift = 0.5 * (f_min_rb + f_max_rb)
        TF_lo = F_lo_rb - mu_shift[None, :]
        TF_hi = F_hi_rb - mu_shift[None, :]

        Num_lo, Num_hi, ok = self.pl.bound_harmonic_batch(wp_prep_b, TF_lo, TF_hi, eval_first_only=first_only)
        if not ok:
            return Num_lo, Num_hi, False

        if first_only:
            z_lo_b = Zbar_b[0][0:1, None]
            z_hi_b = Zbar_b[1][0:1, None]
            c0_lo_b = C0_b[0][0:1, None]
            c0_hi_b = C0_b[1][0:1, None]
            ib_mask = in_ball_b[0:1]
            rem_lo_self = W_rem_lo[0:1, :]
            rem_hi_self = W_rem_hi[0:1, :]
        else:
            z_lo_b = Zbar_b[0][:, None]
            z_hi_b = Zbar_b[1][:, None]
            c0_lo_b = C0_b[0][:, None]
            c0_hi_b = C0_b[1][:, None]
            ib_mask = in_ball_b
            rem_lo_self = W_rem_lo
            rem_hi_self = W_rem_hi

        # Outward rounding BEFORE intersection with maximum-principle `[f_min_rb, f_max_rb]`:
        div_lo = np.where(Num_lo >= 0.0, Num_lo / z_hi_b, Num_lo / z_lo_b)
        div_hi = np.where(Num_hi >= 0.0, Num_hi / z_lo_b, Num_hi / z_hi_b)
        cand_lo = mu_shift[None, :] + div_lo
        cand_hi = mu_shift[None, :] + div_hi
        pad_q = 1e-12 * (1.0 + np.maximum(np.abs(cand_lo), np.abs(cand_hi)))
        Q_lo = np.maximum(f_min_rb[None, :], cand_lo - pad_q)
        Q_hi = np.minimum(f_max_rb[None, :], cand_hi + pad_q)

        if np.any(ib_mask):
            Q_lo = np.where(ib_mask[:, None], rem_lo_self, Q_lo)
            Q_hi = np.where(ib_mask[:, None], rem_hi_self, Q_hi)

        # FAIL-CLOSED CHECK (zero midpoint repair!):
        if not (np.all(np.isfinite(Q_lo)) and np.all(np.isfinite(Q_hi)) and np.all(Q_lo <= Q_hi)):
            return Q_lo, Q_hi, False

        return c0_lo_b + Q_lo, c0_hi_b + Q_hi, True

    def _compute_subset_macro_dp(
        self, s_node: int, t_list: Sequence[int]
    ) -> Tuple[dict, bool]:
        """`O(m^2 2^m)` Gauge-Normalized Batched Subset-State Macro-Bellman Interval DP."""
        m = len(t_list)
        eval_nodes, offsets, in_ball_eval = _build_macro_eval_layout(self.pl, s_node, t_list)
        wp_prep, Zbar_b, C0_b, wp_width, ok = self._compute_single_leg_bounds(eval_nodes, t_list, in_ball_eval)
        if not ok:
            return {}, False

        phis = np.array([float(self.pl.waypoints[b].phi) for b in t_list], dtype=float)
        if not np.all(np.isfinite(phis)):
            return {}, False

        n_ev = len(eval_nodes)
        n_masks = 1 << m
        # `F0_lo, F0_hi` store zero-phi transit bounds; deterministic `phi_mask_sum` is added at the end!
        F0_lo = np.zeros((n_ev, n_masks), dtype=float)
        F0_hi = np.zeros((n_ev, n_masks), dtype=float)
        act_idx = np.zeros((n_ev, n_masks), dtype=np.int32)
        opt_lo_act = np.zeros((n_ev, n_masks), dtype=np.int32)
        inc_local_slack = np.zeros((n_ev, n_masks), dtype=float)
        opt_local_slack = np.zeros((n_ev, n_masks), dtype=float)
        phi_mask_sum = np.zeros(n_masks, dtype=float)

        for i, b in enumerate(t_list):
            mk = 1 << i
            F0_lo[:, mk] = C0_b[b][0]
            F0_hi[:, mk] = C0_b[b][1]
            act_idx[:, mk] = i
            opt_lo_act[:, mk] = i
            slk_b = np.maximum(0.0, C0_b[b][1] - C0_b[b][0])
            inc_local_slack[:, mk] = slk_b
            opt_local_slack[:, mk] = slk_b
            phi_mask_sum[mk] = phis[i]

        masks_by_pop: List[List[int]] = [[] for _ in range(m + 1)]
        for mk in range(1, n_masks):
            pc = mk.bit_count()
            masks_by_pop[pc].append(mk)
            if pc >= 2:
                lsb = mk & -mk
                phi_mask_sum[mk] = phi_mask_sum[lsb] + phi_mask_sum[mk ^ lsb]

        for k in range(2, m + 1):
            mk_list = masks_by_pop[k]
            pos_in_k = {mk: idx for idx, mk in enumerate(mk_list)}
            k_len = len(mk_list)
            best_lo = np.full((n_ev, k_len), np.inf, dtype=float)
            best_hi = np.full((n_ev, k_len), np.inf, dtype=float)
            best_act = np.zeros((n_ev, k_len), dtype=np.int32)
            best_lo_act = np.zeros((n_ev, k_len), dtype=np.int32)
            best_inc_slk = np.zeros((n_ev, k_len), dtype=float)
            best_opt_slk = np.zeros((n_ev, k_len), dtype=float)

            for i, b in enumerate(t_list):
                bit_i = 1 << i
                valid_cols = [(pos_in_k[mk], mk ^ bit_i) for mk in mk_list if (mk & bit_i)]
                if not valid_cols:
                    continue
                col_locs = [c[0] for c in valid_cols]
                rem_masks = [c[1] for c in valid_cols]
                Q_lo_b, Q_hi_b, ok_b = self._propagate_leg_batch(
                    b, wp_prep[b], Zbar_b[b], C0_b[b], in_ball_eval[b], offsets[b],
                    F0_lo[:, rem_masks], F0_hi[:, rem_masks], first_only=False,
                )
                if not ok_b:
                    return {}, False

                in_ring_w = np.mean(F0_hi[offsets[b], :][:, rem_masks] - F0_lo[offsets[b], :][:, rem_masks], axis=0)
                added_mat = np.where(
                    in_ball_eval[b][:, None],
                    0.0,
                    np.maximum(0.0, (Q_hi_b - Q_lo_b) - in_ring_w[None, :]),
                )
                has_stale_err = float(wp_prep[b].get("u1_err_sum", 0.0)) > 0.0
                if wp_prep[b]["level"] != "EXACT" or has_stale_err:
                    wp_width[b] = max(wp_width[b], float(np.max(added_mat)))

                cur_lo_slice = best_lo[:, col_locs]
                cur_hi_slice = best_hi[:, col_locs]
                better_lo = Q_lo_b < cur_lo_slice
                best_lo[:, col_locs] = np.where(better_lo, Q_lo_b, cur_lo_slice)
                best_lo_act[:, col_locs] = np.where(better_lo, i, best_lo_act[:, col_locs])
                best_opt_slk[:, col_locs] = np.where(better_lo, added_mat, best_opt_slk[:, col_locs])

                better_hi = Q_hi_b < cur_hi_slice
                best_hi[:, col_locs] = np.where(better_hi, Q_hi_b, cur_hi_slice)
                best_act[:, col_locs] = np.where(better_hi, i, best_act[:, col_locs])
                best_inc_slk[:, col_locs] = np.where(better_hi, added_mat, best_inc_slk[:, col_locs])

            F0_lo[:, mk_list] = best_lo
            F0_hi[:, mk_list] = best_hi
            act_idx[:, mk_list] = best_act
            opt_lo_act[:, mk_list] = best_lo_act
            inc_local_slack[:, mk_list] = best_inc_slk
            opt_local_slack[:, mk_list] = best_opt_slk

        F_lo = F0_lo + phi_mask_sum[None, :]
        F_hi = F0_hi + phi_mask_sum[None, :]
        if not (np.all(np.isfinite(F_lo)) and np.all(np.isfinite(F_hi)) and np.all(F_lo <= F_hi)):
            return {}, False

        return {
            "eval_nodes": eval_nodes,
            "offsets": offsets,
            "in_ball_eval": in_ball_eval,
            "wp_prep": wp_prep,
            "Zbar_bounds": Zbar_b,
            "C0_bounds": C0_b,
            "wp_width": wp_width,
            "F0_lo": F0_lo,
            "F0_hi": F0_hi,
            "phi_mask_sum": phi_mask_sum,
            "F_lo": F_lo,
            "F_hi": F_hi,
            "policy_action_idx": act_idx,
            "opt_lo_action_idx": opt_lo_act,
            "inc_local_slack": inc_local_slack,
            "opt_local_slack": opt_local_slack,
            "masks_by_pop": masks_by_pop,
        }, True

    def _compute_dual_occupancy_waypoint_impacts(self, dp: dict, t_list: Sequence[int]) -> Dict[int, float]:
        """Propagates forward hitting occupancy from `(row=0, full_mask)` along BOTH the incumbent
        policy `mu_hat` (`policy_action_idx`) and the optimistic contender policy `mu_check`
        (`opt_lo_action_idx`), returning each waypoint `b`'s expected contribution to `F_hi(x_0, T) - F_lo(x_0, T)`!
        """
        m = len(t_list)
        n_ev = len(dp["eval_nodes"])
        n_masks = 1 << m
        full_mk = n_masks - 1
        offsets = dp["offsets"]
        in_ball = dp["in_ball_eval"]
        wp_prep = dp["wp_prep"]

        # Precompute fast nonnegative normalized midpoint hitting matrices `P_hat[b]` (`(n_ev, |R_b|)`)
        P_hat: Dict[int, np.ndarray] = {}
        for b in t_list:
            pr = wp_prep[b]
            W_mid = np.maximum(0.0, pr["U_eval"] @ pr["P_pinv"])
            row_s = np.sum(W_mid, axis=1, keepdims=True)
            W_mid = np.where(row_s > 1e-30, W_mid / np.maximum(row_s, 1e-30), 1.0 / W_mid.shape[1])
            P_hat[b] = W_mid

        wp_impact: Dict[int, float] = {b: 0.0 for b in t_list}
        for act_table, slack_table in (
            (dp["policy_action_idx"], dp["inc_local_slack"]),
            (dp["opt_lo_action_idx"], dp["opt_local_slack"]),
        ):
            rho = np.zeros((n_ev, n_masks), dtype=float)
            rho[0, full_mk] = 0.5  # 0.5 weight on incumbent + 0.5 on optimistic contender
            for k in range(m, 0, -1):
                mk_list = dp["masks_by_pop"][k]
                for mk in mk_list:
                    mass_col = rho[:, mk]
                    if not np.any(mass_col > 1e-12):
                        continue
                    act_col = act_table[:, mk]
                    slk_col = slack_table[:, mk]
                    for i, b in enumerate(t_list):
                        if not (mk & (1 << i)):
                            continue
                        sel = (act_col == i) & (mass_col > 1e-12)
                        if not np.any(sel):
                            continue
                        m_sel = mass_col[sel]
                        wp_impact[b] += float(np.sum(m_sel * slk_col[sel]))
                        if k > 1:
                            rem_mk = mk ^ (1 << i)
                            ib_sel = in_ball[b][sel]
                            if np.any(ib_sel):
                                sel_idx = np.flatnonzero(sel)
                                rho[sel_idx[ib_sel], rem_mk] += m_sel[ib_sel]
                            ext_sel = ~ib_sel
                            if np.any(ext_sel):
                                sel_idx = np.flatnonzero(sel)
                                rho[offsets[b], rem_mk] += m_sel[ext_sel] @ P_hat[b][sel_idx[ext_sel], :]
        return wp_impact

    def plan_exact_subset_dp(
        self,
        start_point: Sequence[float],
        target_wp_ids: Sequence[int],
    ) -> dict:
        """Matched-Policy-Class Exact-Ring Subset-Bellman Baseline (`GPT6 85e2323 Stage B1`):
        Uses `self.pl` cached `EXACT` singleton ring operators (`H_b = U_eval @ inv(U_ring)`) to solve
        the exact same `O(m^2 2^m)` adaptive subset-state MDP in ONE vectorized backward pass without
        interval multi-round overhead or unused port prebuilds!
        """
        t0 = time.perf_counter()
        s_arr = np.asarray(start_point, dtype=float)[None, :]
        s_node = int(np.argmin(np.sum((self.pl.pts - s_arr) ** 2, axis=1)))
        t_list = list(target_wp_ids)
        m = len(t_list)
        solves_before = self.pl.total_lu_backsolves

        t_col0 = time.perf_counter()
        for b in t_list:
            if float(self.pl.get_wp_ring_operator(b).get("u1_err_sum", 0.0)) > 0.0:
                self.pl.refresh_waypoint_under_current_operator(b, "EXACT")
            else:
                self.pl.ensure_wp_level(b, "EXACT")
        col_solve_ms = 1000.0 * (time.perf_counter() - t_col0)

        t_dp0 = time.perf_counter()
        eval_nodes, offsets, in_ball = _build_macro_eval_layout(self.pl, s_node, t_list)
        lam = self.pl.spec.lam
        c_leg: Dict[int, np.ndarray] = {}
        P_leg: Dict[int, np.ndarray] = {}
        for b in t_list:
            pr = self.pl.prepare_wp_ring_eval(b, eval_nodes)
            H_eval = pr["U_eval"] @ pr["P_pinv"]
            zbar = np.maximum(np.sum(H_eval, axis=1), 1e-300)
            phi_b = float(self.pl.waypoints[b].phi)
            cb = phi_b - lam * np.log(zbar)
            cb[in_ball[b]] = phi_b
            c_leg[b] = cb
            P_leg[b] = H_eval / zbar[:, None]

        n_ev = len(eval_nodes)
        n_masks = 1 << m
        F_exact = np.zeros((n_ev, n_masks), dtype=float)
        act_idx = np.zeros((n_ev, n_masks), dtype=np.int32)
        for i, b in enumerate(t_list):
            mk = 1 << i
            F_exact[:, mk] = c_leg[b]
            act_idx[:, mk] = i

        masks_by_pop: List[List[int]] = [[] for _ in range(m + 1)]
        for mk in range(1, n_masks):
            masks_by_pop[mk.bit_count()].append(mk)

        for k in range(2, m + 1):
            mk_list = masks_by_pop[k]
            pos_in_k = {mk: idx for idx, mk in enumerate(mk_list)}
            k_len = len(mk_list)
            best_v = np.full((n_ev, k_len), np.inf, dtype=float)
            best_a = np.zeros((n_ev, k_len), dtype=np.int32)
            for i, b in enumerate(t_list):
                bit_i = 1 << i
                valid_cols = [(pos_in_k[mk], mk ^ bit_i) for mk in mk_list if (mk & bit_i)]
                if not valid_cols:
                    continue
                col_locs = [c[0] for c in valid_cols]
                rem_masks = [c[1] for c in valid_cols]
                W_rem = F_exact[:, rem_masks]
                cont = P_leg[b] @ W_rem[offsets[b], :]
                if np.any(in_ball[b]):
                    cont = np.where(in_ball[b][:, None], W_rem, cont)
                Q_b = c_leg[b][:, None] + cont
                cur_slice = best_v[:, col_locs]
                better = Q_b < cur_slice
                best_v[:, col_locs] = np.where(better, Q_b, cur_slice)
                best_a[:, col_locs] = np.where(better, i, best_a[:, col_locs])
            F_exact[:, mk_list] = best_v
            act_idx[:, mk_list] = best_a
        dp_ms = 1000.0 * (time.perf_counter() - t_dp0)

        def select_next_waypoint(cur_xy: np.ndarray, prev_wp: Optional[int], rem_wp_ids: Sequence[int]) -> int:
            rem_set = set(rem_wp_ids)
            mk = 0
            for idx_i, wid in enumerate(t_list):
                if wid in rem_set:
                    mk |= (1 << idx_i)
            if prev_wp is not None and prev_wp in offsets:
                ring_p = self.pl.wp_rings[prev_wp]
                loc_k = int(np.argmin(np.sum((self.pl.pts[ring_p] - np.asarray(cur_xy)[None, :]) ** 2, axis=1)))
                row_idx = offsets[prev_wp].start + loc_k
            else:
                row_idx = 0
            return t_list[int(act_idx[row_idx, mk])]

        full_mk = n_masks - 1
        val0 = float(F_exact[0, full_mk])
        tot_ms = 1000.0 * (time.perf_counter() - t0)
        return IntervalCertificate(
            status="epsilon_certified",
            certified=True,
            certificate_scope="exact_discrete_ball_stopping_macro_mdp_all_markov_policies",
            epsilon_tol=0.0,
            lower_bound=val0,
            upper_bound=val0,
            stop_reason="exact_ring_single_pass",
            work={
                "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                "col_solve_ms": col_solve_ms,
                "dp_ms": dp_ms,
                "planning_ms": tot_ms,
                "eval_rows": int(n_ev),
                "subset_masks": int(n_masks),
                "row_mask_entries": int(n_ev * n_masks),
                "dp_tables_bytes": int(F_exact.nbytes + act_idx.nbytes),
            },
            extras={
                "macro_value_bounds": [val0, val0],
                "guaranteed_suboptimality_upper_bound": 0.0,
                "policy_action_idx": act_idx,
                "select_next_waypoint": select_next_waypoint,
                "eval_nodes": eval_nodes,
                "refinement_steps": [],
                "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                "col_solve_ms": col_solve_ms,
                "dp_ms": dp_ms,
                "planning_ms": tot_ms,
            },
        ).to_dict()

    def plan_exact_fixed_tour(
        self,
        start_point: Sequence[float],
        target_wp_ids: Sequence[int],
    ) -> dict:
        """Matched-Class Operational Cached-ExactRing Fixed-Tour Evaluator (`GPT6 85e2323 Stage B1`):
        Uses `self.pl` cached `EXACT` ring columns to evaluate all `m!` fixed orders cleanly without
        redundant sparse factorizations or interval-bound overhead.
        """
        t0 = time.perf_counter()
        s_arr = np.asarray(start_point, dtype=float)[None, :]
        s_node = int(np.argmin(np.sum((self.pl.pts - s_arr) ** 2, axis=1)))
        t_list = list(target_wp_ids)
        m = len(t_list)
        solves_before = self.pl.total_lu_backsolves

        t_col0 = time.perf_counter()
        for b in t_list:
            self.pl.ensure_wp_level(b, "EXACT")
        col_solve_ms = 1000.0 * (time.perf_counter() - t_col0)

        t_enum0 = time.perf_counter()
        eval_nodes, offsets, in_ball = _build_macro_eval_layout(self.pl, s_node, t_list)
        lam = self.pl.spec.lam
        c_leg: Dict[int, np.ndarray] = {}
        P_leg: Dict[int, np.ndarray] = {}
        for b in t_list:
            pr = self.pl.prepare_wp_ring_eval(b, eval_nodes)
            H_eval = pr["U_eval"] @ pr["P_pinv"]
            zbar = np.maximum(np.sum(H_eval, axis=1), 1e-300)
            phi_b = float(self.pl.waypoints[b].phi)
            cb = phi_b - lam * np.log(zbar)
            cb[in_ball[b]] = phi_b
            c_leg[b] = cb
            P_leg[b] = H_eval / zbar[:, None]

        W_suf: Dict[Tuple[int, ...], np.ndarray] = {(b,): c_leg[b].copy() for b in t_list}
        for L_s in range(2, m + 1):
            first_only = (L_s == m)
            for b in t_list:
                others = [x for x in t_list if x != b]
                sl_b = offsets[b]
                ib_b = in_ball[b]
                Pb = P_leg[b][0:1, :] if first_only else P_leg[b]
                vb = c_leg[b][0:1] if first_only else c_leg[b]
                for rest in itertools.permutations(others, L_s - 1):
                    r_list = list(itertools.permutations(others, L_s - 1))
                    break
                r_perms = list(itertools.permutations(others, L_s - 1))
                W_mat = np.column_stack([W_suf[rp] for rp in r_perms])
                cont_mat = Pb @ W_mat[sl_b, :]
                if first_only:
                    out_mat = np.where(ib_b[0:1, None], vb[:, None] + W_mat[0:1, :], vb[:, None] + cont_mat)
                else:
                    out_mat = np.where(ib_b[:, None], vb[:, None] + W_mat, vb[:, None] + cont_mat)
                for c_k, rp in enumerate(r_perms):
                    W_suf[(b, *rp)] = out_mat[:, c_k]

        scores = {perm: float(W_suf[perm][0]) for perm in itertools.permutations(t_list, m)}
        best_order = min(scores.keys(), key=lambda pm: scores[pm])
        best_val = scores[best_order]
        enum_ms = 1000.0 * (time.perf_counter() - t_enum0)
        tot_ms = 1000.0 * (time.perf_counter() - t0)
        return {
            "best_order": best_order,
            "status": "epsilon_certified",
            "certified": True,
            "certificate_scope": "exact_discrete_ball_stopping_response_composition_model",
            "selected_bounds": [best_val, best_val],
            "guaranteed_suboptimality_upper_bound": 0.0,
            "total_permutations_in_space": math.factorial(m),
            "unique_leaves_evaluated": math.factorial(m),
            "pruned_permutations_never_expanded": 0,
            "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
            "col_solve_ms": col_solve_ms,
            "enum_ms": enum_ms,
            "ordering_ms": tot_ms,
            "scores": scores,
        }

    def plan_subset_macro_policy(
        self,
        start_point: Sequence[float],
        target_wp_ids: Sequence[int],
        epsilon_tol: float = 0.25,
        max_refine_steps: int = 8,
        allow_exact_ring_level: bool = True,
        refine_strategy: str = "decision_guided",
    ) -> dict:
        """Genuine `O(m^2 2^m)` Adaptive Subset-State Macro-Planner (`m = 5..10`):
        Certifies `F_lo(x_0, T) <= F*(x_0, T) <= J^{mu_hat}(x_0, T) <= F_hi(x_0, T)` with suboptimality
        `<= epsilon_tol` over ALL Markov macro-policies!
        Supports `refine_strategy` in `{"decision_guided", "uniform_width"}`.
        """
        t0 = time.perf_counter()
        s_arr = np.asarray(start_point, dtype=float)
        t_list = list(target_wp_ids)
        m = len(t_list)
        solves_before = self.pl.total_lu_backsolves

        if not np.all(np.isfinite(s_arr)) or any(not np.isfinite(self.pl.waypoints[j].phi) for j in t_list):
            tot_ms = 1000.0 * (time.perf_counter() - t0)
            return IntervalCertificate(
                status="numeric_invalid",
                certified=False,
                certificate_scope="exact_discrete_ball_stopping_macro_mdp_all_markov_policies",
                epsilon_tol=epsilon_tol,
                stop_reason="nonfinite_input",
                work={"new_lu_backsolves": 0, "planning_ms": tot_ms},
                extras={
                    "macro_value_bounds": None,
                    "guaranteed_suboptimality_upper_bound": None,
                    "policy_action_idx": None,
                    "select_next_waypoint": None,
                    "eval_nodes": None,
                    "refinement_steps": [],
                    "new_lu_backsolves": 0,
                    "planning_ms": tot_ms,
                    "ordering_ms": tot_ms,
                },
            ).to_dict()

        s_node = int(np.argmin(np.sum((self.pl.pts - s_arr[None, :]) ** 2, axis=1)))
        t_col_ms = 0.0
        t_dp_ms = 0.0

        t_c0 = time.perf_counter()
        for j in t_list:
            if self.pl.wp_levels.get(j, "NONE") == "NONE":
                self.pl.ensure_wp_level(j, self.pl.default_lazy_level)
        t_col_ms += 1000.0 * (time.perf_counter() - t_c0)

        refinements = []
        refinement_trace = []
        certified = False
        stop_reason = "budget_exhausted"
        full_mk = (1 << m) - 1
        dp_res: dict = {}
        prev_root_act: Optional[int] = None
        prev_gap: Optional[float] = None

        for step_i in range(max_refine_steps + 1):
            t_d0 = time.perf_counter()
            dp_res, ok = self._compute_subset_macro_dp(s_node, t_list)
            t_dp_ms += 1000.0 * (time.perf_counter() - t_d0)

            if not ok:
                # CRITICAL FIX (`Bug 2.3`): Check remaining refinement budget BEFORE refining!
                if step_i >= max_refine_steps:
                    tot_ms = 1000.0 * (time.perf_counter() - t0)
                    return IntervalCertificate(
                        status="numeric_invalid",
                        certified=False,
                        certificate_scope="exact_discrete_ball_stopping_macro_mdp_all_markov_policies",
                        epsilon_tol=epsilon_tol,
                        stop_reason="numeric_invalid_at_budget_cap",
                        work={"new_lu_backsolves": self.pl.total_lu_backsolves - solves_before, "planning_ms": tot_ms},
                        extras={
                            "macro_value_bounds": None,
                            "guaranteed_suboptimality_upper_bound": None,
                            "policy_action_idx": None,
                            "select_next_waypoint": None,
                            "eval_nodes": None,
                            "refinement_steps": refinements,
                            "refinement_trace": refinement_trace,
                            "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                            "planning_ms": tot_ms,
                            "ordering_ms": tot_ms,
                        },
                    ).to_dict()

                progressed = False
                t_c0 = time.perf_counter()
                for j in t_list:
                    cur_lv = self.pl.wp_levels[j]
                    if (j, cur_lv) in self.pl._wp_col_err_bounds:
                        self.pl.refresh_waypoint_under_current_operator(j, cur_lv)
                        refinements.append((int(j), f"REFRESH_{cur_lv}"))
                        progressed = True
                        continue
                    nxt = next_finer_level(cur_lv, allow_exact=allow_exact_ring_level)
                    if nxt is not None:
                        self.pl.ensure_wp_level(j, nxt)
                        refinements.append((int(j), nxt))
                        progressed = True
                t_col_ms += 1000.0 * (time.perf_counter() - t_c0)
                if not progressed:
                    tot_ms = 1000.0 * (time.perf_counter() - t0)
                    return IntervalCertificate(
                        status="numeric_invalid",
                        certified=False,
                        certificate_scope="exact_discrete_ball_stopping_macro_mdp_all_markov_policies",
                        epsilon_tol=epsilon_tol,
                        stop_reason="numeric_invalid_at_max_resolution",
                        work={"new_lu_backsolves": self.pl.total_lu_backsolves - solves_before, "planning_ms": tot_ms},
                        extras={
                            "macro_value_bounds": None,
                            "guaranteed_suboptimality_upper_bound": None,
                            "policy_action_idx": None,
                            "select_next_waypoint": None,
                            "eval_nodes": None,
                            "refinement_steps": refinements,
                            "refinement_trace": refinement_trace,
                            "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                            "planning_ms": tot_ms,
                            "ordering_ms": tot_ms,
                        },
                    ).to_dict()
                continue

            lo_0 = float(dp_res["F_lo"][0, full_mk])
            hi_0 = float(dp_res["F_hi"][0, full_mk])
            gap_ub = hi_0 - lo_0
            cur_root_act = int(dp_res["policy_action_idx"][0, full_mk])
            if prev_gap is not None and refinement_trace:
                refinement_trace[-1]["gap_after"] = gap_ub
                refinement_trace[-1]["gap_reduction"] = float(prev_gap - gap_ub)
                refinement_trace[-1]["root_action_changed"] = bool(cur_root_act != prev_root_act)
            prev_root_act = cur_root_act
            prev_gap = gap_ub

            if gap_ub <= epsilon_tol:
                certified = True
                stop_reason = "certified_within_epsilon"
                break
            if step_i >= max_refine_steps:
                stop_reason = "max_refine_steps_reached"
                break

            if refine_strategy == "decision_guided":
                impacts = self._compute_dual_occupancy_waypoint_impacts(dp_res, t_list)
                cands = []
                for j in t_list:
                    cur_lv = self.pl.wp_levels[j]
                    imp_j = impacts.get(j, 0.0)
                    w_j = dp_res["wp_width"].get(j, 0.0)
                    if (j, cur_lv) in self.pl._wp_col_err_bounds and (imp_j > 1e-12 or w_j > 1e-12):
                        d_cols = max(1, len(self.pl._wp_partitions[j][cur_lv]))
                        score = (imp_j + 1e-4 * w_j) / float(d_cols)
                        cands.append((score, imp_j, j, cur_lv, True, d_cols))
                        continue
                    nxt = next_finer_level(cur_lv, allow_exact=allow_exact_ring_level)
                    if nxt is not None and (imp_j > 1e-12 or w_j > 1e-12):
                        d_cols = max(1, self.pl.marginal_backsolves_to_refine(j, nxt))
                        score = (imp_j + 1e-5 * w_j) / float(d_cols)
                        cands.append((score, imp_j, j, nxt, False, d_cols))
                if not cands:
                    stop_reason = "all_relevant_waypoints_at_max_resolution"
                    break
                cands.sort(reverse=True)
                tot_imp = sum(c[1] for c in cands)
                picked = []
                acc_imp = 0.0
                max_batch = 3 if m >= 6 else 2
                max_exact_in_round = 2 if (m >= 7 and step_i >= 4) else 1
                exact_picked = 0
                for sc, imp_j, j, nxt, is_ref, d_cols in cands:
                    if nxt == "EXACT" and not is_ref and exact_picked >= max_exact_in_round and d_cols > 16:
                        continue
                    picked.append((j, nxt, is_ref, d_cols, imp_j))
                    if nxt == "EXACT" and not is_ref:
                        exact_picked += 1
                    acc_imp += imp_j
                    if len(picked) >= max_batch or (tot_imp > 0.0 and acc_imp >= 0.65 * tot_imp):
                        break
                t_c0 = time.perf_counter()
                bs_round0 = self.pl.total_lu_backsolves
                for j, nxt, is_ref, _, _ in picked:
                    if is_ref:
                        self.pl.refresh_waypoint_under_current_operator(j, nxt)
                        refinements.append((int(j), f"REFRESH_{nxt}"))
                    else:
                        self.pl.ensure_wp_level(j, nxt)
                        refinements.append((int(j), nxt))
                t_col_ms += 1000.0 * (time.perf_counter() - t_c0)
                refinement_trace.append({
                    "round": step_i + 1,
                    "picked": [(int(j), ("REFRESH_" + nxt if is_ref else nxt)) for j, nxt, is_ref, _, _ in picked],
                    "new_backsolves": self.pl.total_lu_backsolves - bs_round0,
                    "gap_before": gap_ub,
                })
            elif refine_strategy == "uniform_width":
                cands_u = []
                for j in t_list:
                    cur_lv = self.pl.wp_levels[j]
                    if (j, cur_lv) in self.pl._wp_col_err_bounds:
                        cands_u.append((10, dp_res["wp_width"].get(j, 0.0), j, cur_lv, True))
                        continue
                    nxt = next_finer_level(cur_lv, allow_exact=allow_exact_ring_level)
                    if nxt is not None:
                        cands_u.append((-LEVEL_RANK[cur_lv], dp_res["wp_width"].get(j, 0.0), j, nxt, False))
                if not cands_u:
                    stop_reason = "all_active_waypoints_at_max_resolution"
                    break
                cands_u.sort(reverse=True)
                n_pick = max(2, (len(cands_u) + 1) // 2) if m >= 6 else (
                    2 if len(cands_u) >= 2 and LEVEL_RANK[self.pl.wp_levels[cands_u[0][2]]] <= LEVEL_RANK["L4"] else 1
                )
                t_c0 = time.perf_counter()
                bs_round0 = self.pl.total_lu_backsolves
                for _, _, wp_pick, nxt, is_ref in cands_u[:n_pick]:
                    if is_ref:
                        self.pl.refresh_waypoint_under_current_operator(wp_pick, nxt)
                        refinements.append((int(wp_pick), f"REFRESH_{nxt}"))
                    else:
                        self.pl.ensure_wp_level(wp_pick, nxt)
                        refinements.append((int(wp_pick), nxt))
                t_col_ms += 1000.0 * (time.perf_counter() - t_c0)
                refinement_trace.append({
                    "round": step_i + 1,
                    "picked": [(int(w), ("REFRESH_" + nx if ir else nx)) for _, _, w, nx, ir in cands_u[:n_pick]],
                    "new_backsolves": self.pl.total_lu_backsolves - bs_round0,
                    "gap_before": gap_ub,
                })
            else:
                raise ValueError(f"Unknown refine_strategy: {refine_strategy}")

        eval_nodes = dp_res["eval_nodes"]
        offsets = dp_res["offsets"]
        act_table = dp_res["policy_action_idx"]
        n_ev = len(eval_nodes)
        n_masks = 1 << m

        def select_next_waypoint(cur_xy: np.ndarray, prev_wp: Optional[int], rem_wp_ids: Sequence[int]) -> int:
            rem_set = set(rem_wp_ids)
            mk = 0
            for idx_i, wid in enumerate(t_list):
                if wid in rem_set:
                    mk |= (1 << idx_i)
            if prev_wp is not None and prev_wp in offsets:
                ring_p = self.pl.wp_rings[prev_wp]
                loc_k = int(np.argmin(np.sum((self.pl.pts[ring_p] - np.asarray(cur_xy)[None, :]) ** 2, axis=1)))
                row_idx = offsets[prev_wp].start + loc_k
            else:
                row_idx = 0
            chosen_i = int(act_table[row_idx, mk])
            return t_list[chosen_i]

        lo_fin = float(dp_res["F_lo"][0, full_mk])
        hi_fin = float(dp_res["F_hi"][0, full_mk])
        tot_ms = 1000.0 * (time.perf_counter() - t0)
        return IntervalCertificate(
            status="epsilon_certified" if certified else "unresolved",
            certified=certified,
            certificate_scope="exact_discrete_ball_stopping_macro_mdp_all_markov_policies",
            epsilon_tol=epsilon_tol,
            lower_bound=lo_fin,
            upper_bound=hi_fin,
            stop_reason=stop_reason,
            work={
                "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                "col_solve_ms": t_col_ms,
                "dp_ms": t_dp_ms,
                "planning_ms": tot_ms,
                "refinement_rounds_executed": len(refinement_trace),
                "eval_rows": int(n_ev),
                "subset_masks": int(n_masks),
                "row_mask_entries": int(n_ev * n_masks),
                "dp_tables_bytes": int(dp_res["F_lo"].nbytes + dp_res["F_hi"].nbytes + act_table.nbytes),
            },
            extras={
                "refine_strategy": refine_strategy,
                "macro_value_bounds": [lo_fin, hi_fin],
                "guaranteed_suboptimality_upper_bound": float(max(0.0, hi_fin - lo_fin)),
                "policy_action_idx": act_table,
                "select_next_waypoint": select_next_waypoint,
                "eval_nodes": eval_nodes,
                "refinement_steps": refinements,
                "refinement_trace": refinement_trace,
                "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                "col_solve_ms": t_col_ms,
                "dp_ms": t_dp_ms,
                "planning_ms": tot_ms,
                "ordering_ms": tot_ms,
            },
        ).to_dict()

    def _eval_prefix_batch_bounds(
        self,
        prefixes: List[Tuple[int, ...]],
        t_list: Sequence[int],
        dp: dict,
    ) -> Tuple[np.ndarray, np.ndarray, bool]:
        """Evaluates provable `[LB(P), UB(P)]` at `s_node` (`row 0`) for prefixes `P` of identical
        length `k` (`1 <= k <= m`) using gauge-normalized `F0_lo, F0_hi` + deterministic `total_phi`!
        """
        m = len(t_list)
        k = len(prefixes[0])
        pos_of = {w: i for i, w in enumerate(t_list)}
        full_mk = (1 << m) - 1
        K_p = len(prefixes)
        total_phi = float(dp["phi_mask_sum"][full_mk])

        wp_prep = dp["wp_prep"]
        Zbar_b = dp["Zbar_bounds"]
        C0_b = dp["C0_bounds"]
        in_ball = dp["in_ball_eval"]
        offsets = dp["offsets"]
        n_ev = len(dp["eval_nodes"])

        if k == m:
            cur_lo = np.column_stack([C0_b[p[-1]][0] for p in prefixes])
            cur_hi = np.column_stack([C0_b[p[-1]][1] for p in prefixes])
            start_pos = k - 2
        else:
            rem_masks = [full_mk ^ sum(1 << pos_of[w] for w in p) for p in prefixes]
            cur_lo = dp["F0_lo"][:, rem_masks]
            cur_hi = dp["F0_hi"][:, rem_masks]
            start_pos = k - 1

        for pos in range(start_pos, -1, -1):
            first_only = (pos == 0)
            out_rows = 1 if first_only else n_ev
            nxt_lo = np.empty((out_rows, K_p), dtype=float)
            nxt_hi = np.empty((out_rows, K_p), dtype=float)

            groups: Dict[int, List[int]] = {}
            for col_i, p in enumerate(prefixes):
                groups.setdefault(p[pos], []).append(col_i)
            for b, cols in groups.items():
                ql, qh, ok = self._propagate_leg_batch(
                    b, wp_prep[b], Zbar_b[b], C0_b[b], in_ball[b], offsets[b],
                    cur_lo[:, cols], cur_hi[:, cols], first_only=first_only,
                )
                if not ok:
                    return nxt_lo, nxt_hi, False
                nxt_lo[:, cols] = ql
                nxt_hi[:, cols] = qh
            cur_lo, cur_hi = nxt_lo, nxt_hi

        return cur_lo[0, :] + total_phi, cur_hi[0, :] + total_phi, True

    def plan_fixed_tour_bnb(
        self,
        start_point: Sequence[float],
        target_wp_ids: Sequence[int],
        epsilon_tol: float = 0.25,
        max_refine_steps: int = 8,
        allow_exact_ring_level: bool = True,
        mode: str = "certified_adaptive",
        return_all_perm_enclosures: bool = False,
    ) -> dict:
        """Scalable Subset-Bellman-Guided Interval Branch-and-Bound Fixed-Order Tour Planner (`m = 5..8`):
          - Computes gauge-normalized `O(m^2 2^m)` Subset Macro-Bellman lower bounds `F_lo(., S_rem)`;
          - Prunes prefix subtrees strictly when `LB(P) > U_incumbent` (exact optimality pruning, never
            dropping the global fixed-order optimum!);
          - Strictly fail-closed on cross-round interval intersections (`0` midpoint repairs!).
        """
        t0 = time.perf_counter()
        s_arr = np.asarray(start_point, dtype=float)
        t_list = list(target_wp_ids)
        m = len(t_list)
        solves_before = self.pl.total_lu_backsolves

        if not np.all(np.isfinite(s_arr)) or any(not np.isfinite(self.pl.waypoints[j].phi) for j in t_list):
            return {
                "best_order": None,
                "status": "numeric_invalid",
                "certified": False,
                "ordering_ms": 1000.0 * (time.perf_counter() - t0),
            }

        s_node = int(np.argmin(np.sum((self.pl.pts - s_arr[None, :]) ** 2, axis=1)))
        for j in t_list:
            if self.pl.wp_levels.get(j, "NONE") == "NONE":
                self.pl.ensure_wp_level(j, self.pl.default_lazy_level)

        if mode == "heuristic_fast":
            dp, ok = self._compute_subset_macro_dp(s_node, t_list)
            if not ok:
                return {"best_order": None, "status": "numeric_invalid", "certified": False, "ordering_ms": 1000.0 * (time.perf_counter() - t0)}
            F0_mid = 0.5 * (dp["F0_lo"] + dp["F0_hi"])
            rem = list(t_list)
            pos_of = {w: i for i, w in enumerate(t_list)}
            cur_dist = np.zeros(len(dp["eval_nodes"]), dtype=float)
            cur_dist[0] = 1.0
            order_greedy: List[int] = []
            for _step in range(m):
                mk = sum(1 << pos_of[w] for w in rem)
                best_w = rem[0]
                best_sc = np.inf
                for w in rem:
                    rem_mk = mk ^ (1 << pos_of[w])
                    if len(rem) == 1:
                        v_mid = 0.5 * (dp["C0_bounds"][w][0] + dp["C0_bounds"][w][1])
                        sc = float(cur_dist @ v_mid)
                    else:
                        ql, qh, _ = self._propagate_leg_batch(
                            w, dp["wp_prep"][w], dp["Zbar_bounds"][w], dp["C0_bounds"][w],
                            dp["in_ball_eval"][w], dp["offsets"][w],
                            F0_mid[:, [rem_mk]], F0_mid[:, [rem_mk]], first_only=False,
                        )
                        sc = float(cur_dist @ (0.5 * (ql[:, 0] + qh[:, 0])))
                    if sc < best_sc:
                        best_sc = sc
                        best_w = w
                order_greedy.append(best_w)
                rem.remove(best_w)
                pr = dp["wp_prep"][best_w]
                ib = dp["in_ball_eval"][best_w]
                nxt_dist = np.zeros_like(cur_dist)
                if np.any(cur_dist[ib] > 0):
                    nxt_dist[ib] += cur_dist[ib]
                ext_m = (~ib) & (cur_dist > 1e-15)
                if np.any(ext_m):
                    W_approx = np.maximum(0.0, pr["U_eval"][ext_m, :] @ pr["P_pinv"])
                    rs = np.maximum(np.sum(W_approx, axis=1, keepdims=True), 1e-30)
                    W_approx /= rs
                    nxt_dist[dp["offsets"][best_w]] += cur_dist[ext_m] @ W_approx
                cur_dist = nxt_dist

            best_perm = tuple(order_greedy)
            lo_a, hi_a, ok_h = self._eval_prefix_batch_bounds([best_perm], t_list, dp)
            if not ok_h:
                return {"best_order": None, "status": "numeric_invalid", "certified": False, "ordering_ms": 1000.0 * (time.perf_counter() - t0)}
            return {
                "best_order": best_perm,
                "status": "heuristic",
                "certified": False,
                "certificate_scope": "none (heuristic macro-midpoint rollout)",
                "epsilon_tol": float(epsilon_tol),
                "selected_bounds": [float(lo_a[0]), float(hi_a[0])],
                "min_rival_lower_bound": None,
                "guaranteed_suboptimality_upper_bound": None,
                "pruned_permutations": max(0, math.factorial(m) - 1),
                "evaluated_full_permutations": 1,
                "refinement_steps": [],
                "stop_reason": "heuristic_no_refinement",
                "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                "ordering_ms": 1000.0 * (time.perf_counter() - t0),
                "perm_enclosures": {best_perm: (float(lo_a[0]), float(hi_a[0]))},
            }

        refinements = []
        certified = False
        stop_reason = "budget_exhausted"
        total_perms = math.factorial(m)

        known_leaf_bounds: Dict[Tuple[int, ...], Tuple[float, float]] = {}
        pruned_prefix_lbs: List[Tuple[Tuple[int, ...], float]] = []
        frontier_prefixes: Optional[List[Tuple[int, ...]]] = None
        active_leaves: List[Tuple[int, ...]] = []
        best_order: Tuple[int, ...] = tuple(t_list)
        lo_sel, hi_sel, min_riv_lo = 0.0, np.inf, 0.0
        total_leaf_evals = 0

        for step_i in range(max_refine_steps + 1):
            dp, ok = self._compute_subset_macro_dp(s_node, t_list)
            if not ok:
                return {
                    "best_order": None,
                    "status": "numeric_invalid",
                    "certified": False,
                    "refinement_steps": refinements,
                    "ordering_ms": 1000.0 * (time.perf_counter() - t0),
                }

            pos_of = {w: i for i, w in enumerate(t_list)}
            rem_s = set(t_list)
            seed_ord: List[int] = []
            cur_row = 0
            for _ in range(m):
                mk = sum(1 << pos_of[w] for w in rem_s)
                pick_i = int(dp["policy_action_idx"][cur_row, mk])
                w_pick = t_list[pick_i]
                seed_ord.append(w_pick)
                rem_s.remove(w_pick)
                cur_row = dp["offsets"][w_pick].start
            seed_perm = tuple(seed_ord)
            if seed_perm not in active_leaves:
                active_leaves.append(seed_perm)

            eval_now = [
                pm for pm in active_leaves
                if (pm not in known_leaf_bounds) or pm == best_order or known_leaf_bounds[pm][0] < hi_sel - epsilon_tol + 1e-12
            ]
            for c_st in range(0, len(eval_now), 512):
                chunk = eval_now[c_st:c_st + 512]
                l_ch, h_ch, ok_c = self._eval_prefix_batch_bounds(chunk, t_list, dp)
                if not ok_c:
                    return {"best_order": None, "status": "numeric_invalid", "certified": False, "ordering_ms": 1000.0 * (time.perf_counter() - t0)}
                total_leaf_evals += len(chunk)
                for pm, lv, hv in zip(chunk, l_ch, h_ch):
                    pad_lv = float(lv) - 1e-12 * (1.0 + abs(float(lv)))
                    pad_hv = float(hv) + 1e-12 * (1.0 + abs(float(hv)))
                    if pm in known_leaf_bounds:
                        old_l, old_h = known_leaf_bounds[pm]
                        nl, nh = max(old_l, pad_lv), min(old_h, pad_hv)
                        # FAIL-CLOSED CHECK (zero midpoint repair!):
                        if nl > nh:
                            return {"best_order": None, "status": "numeric_invalid", "certified": False, "ordering_ms": 1000.0 * (time.perf_counter() - t0)}
                        known_leaf_bounds[pm] = (nl, nh)
                    else:
                        if pad_lv > pad_hv:
                            return {"best_order": None, "status": "numeric_invalid", "certified": False, "ordering_ms": 1000.0 * (time.perf_counter() - t0)}
                        known_leaf_bounds[pm] = (pad_lv, pad_hv)

            best_order = min(known_leaf_bounds.keys(), key=lambda pm: (known_leaf_bounds[pm][1], known_leaf_bounds[pm][0]))
            lo_sel, hi_sel = known_leaf_bounds[best_order]
            u_inc = hi_sel

            can_still_refine = (step_i < max_refine_steps) and any(
                next_finer_level(self.pl.wp_levels[j], allow_exact=allow_exact_ring_level) is not None for j in t_list
            )

            if return_all_perm_enclosures and m <= 5 and frontier_prefixes is None:
                all_p = [pm for pm in itertools.permutations(t_list, m) if pm not in known_leaf_bounds]
                if all_p:
                    p_lo, p_hi, ok_p = self._eval_prefix_batch_bounds(all_p, t_list, dp)
                    if not ok_p:
                        return {"best_order": None, "status": "numeric_invalid", "certified": False, "ordering_ms": 1000.0 * (time.perf_counter() - t0)}
                    total_leaf_evals += len(all_p)
                    for pm, lv, hv in zip(all_p, p_lo, p_hi):
                        known_leaf_bounds[pm] = (float(lv), float(hv))
                    active_leaves.extend(all_p)
                frontier_prefixes = []
            else:
                if frontier_prefixes is None:
                    frontier_prefixes = [(w,) for w in t_list]

                while frontier_prefixes:
                    k_len = len(frontier_prefixes[0])
                    if k_len == m:
                        new_leaves = [pm for pm in frontier_prefixes if pm not in known_leaf_bounds]
                        for c_st in range(0, len(new_leaves), 512):
                            chunk = new_leaves[c_st:c_st + 512]
                            l_ch, h_ch, ok_c = self._eval_prefix_batch_bounds(chunk, t_list, dp)
                            if not ok_c:
                                return {"best_order": None, "status": "numeric_invalid", "certified": False, "ordering_ms": 1000.0 * (time.perf_counter() - t0)}
                            total_leaf_evals += len(chunk)
                            for pm, lv, hv in zip(chunk, l_ch, h_ch):
                                known_leaf_bounds[pm] = (float(lv), float(hv))
                                if float(hv) < u_inc:
                                    u_inc = float(hv)
                        active_leaves.extend(new_leaves)
                        frontier_prefixes = []
                        break

                    surviving_p: List[Tuple[int, ...]] = []
                    for c_st in range(0, len(frontier_prefixes), 512):
                        chunk = frontier_prefixes[c_st:c_st + 512]
                        lb_k, _, ok_k = self._eval_prefix_batch_bounds(chunk, t_list, dp)
                        if not ok_k:
                            return {"best_order": None, "status": "numeric_invalid", "certified": False, "ordering_ms": 1000.0 * (time.perf_counter() - t0)}
                        for pref, l_val in zip(chunk, lb_k):
                            lv = float(l_val)
                            if lv > u_inc and best_order[:k_len] != pref and seed_perm[:k_len] != pref:
                                pruned_prefix_lbs.append((pref, lv))
                            else:
                                surviving_p.append(pref)

                    if not surviving_p:
                        frontier_prefixes = []
                        break

                    est_children = len(surviving_p) * (m - k_len)
                    if can_still_refine and m >= 7 and est_children > 380:
                        frontier_prefixes = surviving_p
                        break

                    next_p: List[Tuple[int, ...]] = []
                    for pref in surviving_p:
                        used = set(pref)
                        for w in t_list:
                            if w not in used:
                                next_p.append((*pref, w))
                    frontier_prefixes = next_p

            best_order = min(known_leaf_bounds.keys(), key=lambda pm: (known_leaf_bounds[pm][1], known_leaf_bounds[pm][0]))
            lo_sel, hi_sel = known_leaf_bounds[best_order]

            active_leaves = [
                pm for pm in active_leaves
                if pm == best_order or known_leaf_bounds[pm][0] < hi_sel - epsilon_tol + 1e-12
            ]

            if not frontier_prefixes:
                min_leaf_riv = min((v[0] for pm, v in known_leaf_bounds.items() if pm != best_order), default=np.inf)
                min_pref_riv = min((lv for _, lv in pruned_prefix_lbs), default=np.inf)
                min_riv_lo = min(min_leaf_riv, min_pref_riv)
                gap_ub = hi_sel - min_riv_lo

                if gap_ub <= epsilon_tol:
                    certified = True
                    stop_reason = "certified_within_epsilon"
                    break
            else:
                min_riv_lo = float(dp["F_lo"][0, (1 << m) - 1])
                gap_ub = hi_sel - min_riv_lo

            if step_i >= max_refine_steps:
                stop_reason = "max_refine_steps_reached"
                break

            impacts = self._compute_dual_occupancy_waypoint_impacts(dp, t_list)
            contested_wps = set(t_list) if frontier_prefixes else set()
            if not contested_wps:
                for pm in active_leaves[:min(len(active_leaves), 16)]:
                    contested_wps.update(pm)
                if not contested_wps:
                    contested_wps = set(t_list)

            cands = []
            for j in contested_wps:
                cur_lv = self.pl.wp_levels[j]
                nxt = next_finer_level(cur_lv, allow_exact=allow_exact_ring_level)
                if nxt is not None:
                    d_cols = max(1, self.pl.marginal_backsolves_to_refine(j, nxt))
                    sc = (impacts.get(j, 0.0) + 1e-4 * dp["wp_width"].get(j, 0.0)) / float(d_cols)
                    cands.append((sc, -LEVEL_RANK[cur_lv], j, nxt))
            if not cands:
                if frontier_prefixes:
                    continue
                stop_reason = "all_active_waypoints_at_max_resolution"
                break

            cands.sort(reverse=True)
            n_pick = max(2, (len(cands) + 1) // 2) if m >= 6 else (
                2 if len(cands) >= 2 and LEVEL_RANK[self.pl.wp_levels[cands[0][2]]] <= LEVEL_RANK["L4"] else 1
            )
            for _, _, wp_pick, nxt in cands[:n_pick]:
                self.pl.ensure_wp_level(wp_pick, nxt)
                refinements.append((int(wp_pick), nxt))

        pruned_count = total_perms - len(known_leaf_bounds)
        return {
            "best_order": best_order,
            "status": "epsilon_certified" if certified else "unresolved",
            "certified": certified,
            "certificate_scope": "exact_discrete_ball_stopping_response_composition_model",
            "epsilon_tol": float(epsilon_tol),
            "selected_bounds": [float(lo_sel), float(hi_sel)],
            "min_rival_lower_bound": float(min_riv_lo),
            "guaranteed_suboptimality_upper_bound": float(max(0.0, hi_sel - min_riv_lo)),
            "total_permutations_in_space": total_perms,
            "unique_leaves_evaluated": len(known_leaf_bounds),
            "pruned_permutations_never_expanded": pruned_count,
            "total_leaf_evaluations_across_rounds": total_leaf_evals,
            "refinement_steps": refinements,
            "stop_reason": stop_reason,
            "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
            "ordering_ms": 1000.0 * (time.perf_counter() - t0),
            "perm_enclosures": known_leaf_bounds,
            "pruned_prefix_lower_bounds": pruned_prefix_lbs,
        }
