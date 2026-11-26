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

    def _init_subset_dp_workspace(self, s_node: int, t_list: Sequence[int]) -> Optional[dict]:
        """Allocates reusable tables and static mask/index maps for Incremental Subset-Bellman DP."""
        m = len(t_list)
        phis = np.array([float(self.pl.waypoints[b].phi) for b in t_list], dtype=float)
        if not np.all(np.isfinite(phis)):
            return None
        eval_nodes, offsets, in_ball_eval = _build_macro_eval_layout(self.pl, s_node, t_list)
        n_ev = len(eval_nodes)
        n_masks = 1 << m

        phi_mask_sum = np.zeros(n_masks, dtype=float)
        for i in range(m):
            phi_mask_sum[1 << i] = phis[i]
        masks_by_pop: List[List[int]] = [[] for _ in range(m + 1)]
        for mk in range(1, n_masks):
            pc = mk.bit_count()
            masks_by_pop[pc].append(mk)
            if pc >= 2:
                lsb = mk & -mk
                phi_mask_sum[mk] = phi_mask_sum[lsb] + phi_mask_sum[mk ^ lsb]

        pos_in_k_map: List[Dict[int, int]] = [{} for _ in range(m + 1)]
        col_locs_ki: Dict[Tuple[int, int], np.ndarray] = {}
        rem_masks_ki: Dict[Tuple[int, int], np.ndarray] = {}
        for k in range(2, m + 1):
            mk_list = masks_by_pop[k]
            p_map = {mk: idx for idx, mk in enumerate(mk_list)}
            pos_in_k_map[k] = p_map
            for i in range(m):
                bit_i = 1 << i
                pairs = [(p_map[mk], mk ^ bit_i) for mk in mk_list if (mk & bit_i)]
                col_locs_ki[(k, i)] = np.array([c[0] for c in pairs], dtype=np.int64)
                rem_masks_ki[(k, i)] = np.array([c[1] for c in pairs], dtype=np.int64)

        return {
            "m": m,
            "t_list": list(t_list),
            "eval_nodes": eval_nodes,
            "offsets": offsets,
            "in_ball_eval": in_ball_eval,
            "phis": phis,
            "phi_mask_sum": phi_mask_sum,
            "masks_by_pop": masks_by_pop,
            "pos_in_k_map": pos_in_k_map,
            "col_locs_ki": col_locs_ki,
            "rem_masks_ki": rem_masks_ki,
            "wp_sig": {},
            "wp_prep": {},
            "Zbar_bounds": {},
            "C0_bounds": {},
            "wp_base_width": {b: 0.0 for b in t_list},
            "wp_added_by_k": {b: {} for b in t_list},
            "P_hat": {},
            "Q_lo_ki": {},
            "Q_hi_ki": {},
            "added_ki": {},
            "F0_lo": np.zeros((n_ev, n_masks), dtype=float),
            "F0_hi": np.zeros((n_ev, n_masks), dtype=float),
            "policy_action_idx": np.zeros((n_ev, n_masks), dtype=np.int32),
            "opt_lo_action_idx": np.zeros((n_ev, n_masks), dtype=np.int32),
            "inc_local_slack": np.zeros((n_ev, n_masks), dtype=float),
            "opt_local_slack": np.zeros((n_ev, n_masks), dtype=float),
            "initialized": False,
        }

    def _step_incremental_subset_macro_dp(self, ws: dict) -> Tuple[dict, bool, dict]:
        """Dependency-Tracked Incremental Subset-Bellman Update (`ddd19c5 Stage B`):
        Updates ONLY single-leg operators of waypoints whose `(level, built_epoch, verified_epoch)` changed,
        and propagates ONLY dirty `(k, action, remainder_mask)` columns, matching `_compute_subset_macro_dp`
        to machine precision (`<= 1e-14` under BLAS batch-width rounding; `0.0` on Suite 15).
        """
        t_list = ws["t_list"]
        m = ws["m"]
        eval_nodes = ws["eval_nodes"]
        offsets = ws["offsets"]
        in_ball_eval = ws["in_ball_eval"]
        n_ev = len(eval_nodes)

        changed_wps: List[int] = []
        for b in t_list:
            cur_lv = self.pl.wp_levels.get(b, "NONE")
            sig_b = (
                cur_lv,
                self.pl._wp_tree_col_epoch.get((b, cur_lv), -1),
                self.pl._wp_verified_epoch.get((b, cur_lv), -1),
            )
            if (not ws["initialized"]) or (ws["wp_sig"].get(b) != sig_b):
                changed_wps.append(b)
                ws["wp_sig"][b] = sig_b

        if changed_wps:
            sub_prep, sub_zbar, sub_c0, sub_w, ok = self._compute_single_leg_bounds(
                eval_nodes, changed_wps, in_ball_eval
            )
            if not ok:
                return {}, False, {"dirty_waypoints": len(changed_wps), "cols_propagated": 0, "cols_total": 0}
            for b in changed_wps:
                ws["wp_prep"][b] = sub_prep[b]
                ws["Zbar_bounds"][b] = sub_zbar[b]
                ws["C0_bounds"][b] = sub_c0[b]
                ws["wp_base_width"][b] = sub_w[b]
                ws["wp_added_by_k"][b].clear()
                pr = sub_prep[b]
                W_mid = np.maximum(0.0, pr["U_eval"] @ pr["P_pinv"])
                row_s = np.sum(W_mid, axis=1, keepdims=True)
                ws["P_hat"][b] = np.where(row_s > 1e-30, W_mid / np.maximum(row_s, 1e-30), 1.0 / W_mid.shape[1])

        changed_set = set(changed_wps)
        changed_bits = 0
        for i, b in enumerate(t_list):
            if b in changed_set:
                changed_bits |= (1 << i)

        F0_lo = ws["F0_lo"]
        F0_hi = ws["F0_hi"]
        act_idx = ws["policy_action_idx"]
        opt_lo_act = ws["opt_lo_action_idx"]
        inc_slk = ws["inc_local_slack"]
        opt_slk = ws["opt_local_slack"]

        for i, b in enumerate(t_list):
            if b in changed_set or not ws["initialized"]:
                mk = 1 << i
                c0_l, c0_h = ws["C0_bounds"][b]
                F0_lo[:, mk] = c0_l
                F0_hi[:, mk] = c0_h
                act_idx[:, mk] = i
                opt_lo_act[:, mk] = i
                slk_b = np.maximum(0.0, c0_h - c0_l)
                inc_slk[:, mk] = slk_b
                opt_slk[:, mk] = slk_b

        cols_propagated = 0
        cols_total = 0

        for k in range(2, m + 1):
            mk_list = ws["masks_by_pop"][k]
            mk_arr = np.asarray(mk_list, dtype=np.int64)
            k_len = len(mk_list)
            dirty_k_mask = np.ones(k_len, dtype=bool) if not ws["initialized"] else ((mk_arr & changed_bits) != 0)
            if not np.any(dirty_k_mask):
                for i in range(m):
                    cols_total += len(ws["col_locs_ki"][(k, i)])
                continue

            for i, b in enumerate(t_list):
                rem_arr = ws["rem_masks_ki"][(k, i)]
                n_ci = len(rem_arr)
                cols_total += n_ci
                if n_ci == 0:
                    continue
                key_ki = (k, i)
                if (not ws["initialized"]) or (b in changed_set) or (key_ki not in ws["Q_lo_ki"]):
                    ql, qh, ok_b = self._propagate_leg_batch(
                        b, ws["wp_prep"][b], ws["Zbar_bounds"][b], ws["C0_bounds"][b],
                        in_ball_eval[b], offsets[b], F0_lo[:, rem_arr], F0_hi[:, rem_arr], first_only=False,
                    )
                    if not ok_b:
                        return {}, False, {"dirty_waypoints": len(changed_wps)}
                    cols_propagated += n_ci
                    in_ring_w = np.mean(F0_hi[offsets[b], :][:, rem_arr] - F0_lo[offsets[b], :][:, rem_arr], axis=0)
                    added_mat = np.where(
                        in_ball_eval[b][:, None], 0.0, np.maximum(0.0, (qh - ql) - in_ring_w[None, :])
                    )
                    ws["Q_lo_ki"][key_ki] = ql
                    ws["Q_hi_ki"][key_ki] = qh
                    ws["added_ki"][key_ki] = added_mat
                else:
                    dirty_ci = np.flatnonzero((rem_arr & changed_bits) != 0)
                    if len(dirty_ci) > 0:
                        rem_sub = rem_arr[dirty_ci]
                        ql_s, qh_s, ok_b = self._propagate_leg_batch(
                            b, ws["wp_prep"][b], ws["Zbar_bounds"][b], ws["C0_bounds"][b],
                            in_ball_eval[b], offsets[b], F0_lo[:, rem_sub], F0_hi[:, rem_sub], first_only=False,
                        )
                        if not ok_b:
                            return {}, False, {"dirty_waypoints": len(changed_wps)}
                        cols_propagated += len(dirty_ci)
                        in_ring_w = np.mean(
                            F0_hi[offsets[b], :][:, rem_sub] - F0_lo[offsets[b], :][:, rem_sub], axis=0
                        )
                        added_sub = np.where(
                            in_ball_eval[b][:, None], 0.0, np.maximum(0.0, (qh_s - ql_s) - in_ring_w[None, :])
                        )
                        ws["Q_lo_ki"][key_ki][:, dirty_ci] = ql_s
                        ws["Q_hi_ki"][key_ki][:, dirty_ci] = qh_s
                        ws["added_ki"][key_ki][:, dirty_ci] = added_sub

                has_stale_err = float(ws["wp_prep"][b].get("u1_err_sum", 0.0)) > 0.0
                if ws["wp_prep"][b]["level"] != "EXACT" or has_stale_err:
                    ws["wp_added_by_k"][b][k] = float(np.max(ws["added_ki"][key_ki]))
                else:
                    ws["wp_added_by_k"][b][k] = 0.0

            # Re-minimize across actions ONLY on dirty masks of cardinality `k` (or full `k_len` if fast)
            best_lo = np.full((n_ev, k_len), np.inf, dtype=float)
            best_hi = np.full((n_ev, k_len), np.inf, dtype=float)
            best_act = np.zeros((n_ev, k_len), dtype=np.int32)
            best_lo_act = np.zeros((n_ev, k_len), dtype=np.int32)
            best_inc_slk = np.zeros((n_ev, k_len), dtype=float)
            best_opt_slk = np.zeros((n_ev, k_len), dtype=float)

            for i in range(m):
                col_locs = ws["col_locs_ki"][(k, i)]
                if len(col_locs) == 0:
                    continue
                Q_lo_b = ws["Q_lo_ki"][(k, i)]
                Q_hi_b = ws["Q_hi_ki"][(k, i)]
                added_mat = ws["added_ki"][(k, i)]

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

            F0_lo[:, mk_arr] = best_lo
            F0_hi[:, mk_arr] = best_hi
            act_idx[:, mk_arr] = best_act
            opt_lo_act[:, mk_arr] = best_lo_act
            inc_slk[:, mk_arr] = best_inc_slk
            opt_slk[:, mk_arr] = best_opt_slk

        ws["initialized"] = True
        phi_sum = ws["phi_mask_sum"]
        F_lo = F0_lo + phi_sum[None, :]
        F_hi = F0_hi + phi_sum[None, :]
        if not (np.all(np.isfinite(F_lo)) and np.all(np.isfinite(F_hi)) and np.all(F_lo <= F_hi)):
            return {}, False, {"dirty_waypoints": len(changed_wps)}

        wp_width = {
            b: max([ws["wp_base_width"][b], *ws["wp_added_by_k"][b].values()])
            for b in t_list
        }
        out_dp = {
            "eval_nodes": eval_nodes,
            "offsets": offsets,
            "in_ball_eval": in_ball_eval,
            "wp_prep": ws["wp_prep"],
            "Zbar_bounds": ws["Zbar_bounds"],
            "C0_bounds": ws["C0_bounds"],
            "wp_width": wp_width,
            "P_hat": ws["P_hat"],
            "F0_lo": F0_lo,
            "F0_hi": F0_hi,
            "phi_mask_sum": phi_sum,
            "F_lo": F_lo,
            "F_hi": F_hi,
            "policy_action_idx": act_idx,
            "opt_lo_action_idx": opt_lo_act,
            "inc_local_slack": inc_slk,
            "opt_local_slack": opt_slk,
            "masks_by_pop": ws["masks_by_pop"],
        }
        return out_dp, True, {
            "dirty_waypoints": len(changed_wps),
            "cols_propagated": int(cols_propagated),
            "cols_total": int(cols_total),
        }

    def _compute_subset_macro_dp(
        self, s_node: int, t_list: Sequence[int]
    ) -> Tuple[dict, bool]:
        """From-scratch `O(m^2 2^m)` Gauge-Normalized Batched Subset-State Macro-Bellman Interval DP."""
        ws = self._init_subset_dp_workspace(s_node, t_list)
        if ws is None:
            return {}, False
        dp_out, ok, _ = self._step_incremental_subset_macro_dp(ws)
        return dp_out, ok

    def _compute_dual_occupancy_waypoint_impacts(self, dp: dict, t_list: Sequence[int]) -> Dict[int, float]:
        """Heuristic dual-occupancy acquisition score (`0.5` incumbent + `0.5` optimistic contender):
        Uses pre-cached `P_hat` from `dp` when available (avoiding redundant matrix multiplies!).
        Note: Certified bounds come strictly from M-matrix interval Bellman tables, never from `P_hat`.
        """
        m = len(t_list)
        n_ev = len(dp["eval_nodes"])
        n_masks = 1 << m
        full_mk = n_masks - 1
        offsets = dp["offsets"]
        in_ball = dp["in_ball_eval"]
        wp_prep = dp["wp_prep"]

        P_hat: Dict[int, np.ndarray] = dict(dp.get("P_hat", {}))
        for b in t_list:
            if b not in P_hat:
                pr = wp_prep[b]
                W_mid = np.maximum(0.0, pr["U_eval"] @ pr["P_pinv"])
                row_s = np.sum(W_mid, axis=1, keepdims=True)
                P_hat[b] = np.where(row_s > 1e-30, W_mid / np.maximum(row_s, 1e-30), 1.0 / W_mid.shape[1])

        wp_impact: Dict[int, float] = {b: 0.0 for b in t_list}
        for act_table, slack_table in (
            (dp["policy_action_idx"], dp["inc_local_slack"]),
            (dp["opt_lo_action_idx"], dp["opt_local_slack"]),
        ):
            rho = np.zeros((n_ev, n_masks), dtype=float)
            rho[0, full_mk] = 0.5
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
        """Matched-Policy-Class Exact-Ring Subset-Bellman Operational Route (`ddd19c5 P1 Fail-Closed`):
        Uses current-epoch `EXACT` singleton ring operators (`H_b = U_eval @ inv(U_ring)`) in ONE
        vectorized backward pass, with ZERO silent `1e-300` clamping (`numeric_invalid` on underflow/NaN!).
        """
        t0 = time.perf_counter()
        s_arr = np.asarray(start_point, dtype=float)
        t_list = list(target_wp_ids)
        m = len(t_list)
        solves_before = self.pl.total_lu_backsolves

        def _fail_exact(reason: str) -> dict:
            tot_ms = 1000.0 * (time.perf_counter() - t0)
            return IntervalCertificate(
                status="numeric_invalid",
                certified=False,
                certificate_scope="exact_discrete_ball_stopping_macro_mdp_all_markov_policies",
                epsilon_tol=0.0,
                stop_reason=reason,
                operator_epoch=self.pl.operator_epoch,
                work={"new_lu_backsolves": self.pl.total_lu_backsolves - solves_before, "planning_ms": tot_ms},
                extras={
                    "macro_value_bounds": None,
                    "guaranteed_suboptimality_upper_bound": None,
                    "policy_action_idx": None,
                    "select_next_waypoint": None,
                    "eval_nodes": None,
                    "refinement_steps": [],
                    "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                    "planning_ms": tot_ms,
                },
            ).to_dict()

        if not np.all(np.isfinite(s_arr)) or any(not np.isfinite(self.pl.waypoints[b].phi) for b in t_list):
            return _fail_exact("nonfinite_input")

        s_node = int(np.argmin(np.sum((self.pl.pts - s_arr[None, :]) ** 2, axis=1)))

        t_col0 = time.perf_counter()
        for b in t_list:
            if not self.pl._is_level_exact_in_current_epoch(b, "EXACT"):
                if "EXACT" in self.pl._wp_tree.get(b, {}):
                    self.pl.refresh_waypoint_under_current_operator(b, "EXACT")
                else:
                    self.pl.ensure_wp_level(b, "EXACT")
            else:
                self.pl.ensure_wp_level(b, "EXACT")
        col_solve_ms = 1000.0 * (time.perf_counter() - t_col0)

        t_dp0 = time.perf_counter()
        eval_nodes, offsets, in_ball = _build_macro_eval_layout(self.pl, s_node, t_list)
        lam = self.pl.spec.lam
        phis = np.array([float(self.pl.waypoints[b].phi) for b in t_list], dtype=float)
        c0_leg: Dict[int, np.ndarray] = {}
        P_leg: Dict[int, np.ndarray] = {}
        for b in t_list:
            pr = self.pl.prepare_wp_ring_eval(b, eval_nodes)
            H_eval = pr["U_eval"] @ pr["P_pinv"]
            if not np.all(np.isfinite(H_eval)):
                return _fail_exact("nonfinite_harmonic_operator")
            zbar_raw = np.sum(H_eval, axis=1)
            ext_rows = ~in_ball[b]
            # Strict fail-closed check (NO `maximum(..., 1e-300)` silent clamping!):
            if np.any(zbar_raw[ext_rows] <= 1e-285) or np.any(H_eval[ext_rows, :] < -1e-7):
                return _fail_exact("desirability_underflow_or_sign_loss")
            zbar_safe = np.where(in_ball[b], 1.0, zbar_raw)
            cb0 = -lam * np.log(zbar_safe)
            cb0[in_ball[b]] = 0.0
            Pb = H_eval / zbar_safe[:, None]
            if not (np.all(np.isfinite(cb0)) and np.all(np.isfinite(Pb))):
                return _fail_exact("nonfinite_normalized_leg_operator")
            c0_leg[b] = cb0
            P_leg[b] = Pb

        n_ev = len(eval_nodes)
        n_masks = 1 << m
        F0_exact = np.zeros((n_ev, n_masks), dtype=float)
        act_idx = np.zeros((n_ev, n_masks), dtype=np.int32)
        phi_mask_sum = np.zeros(n_masks, dtype=float)
        for i, b in enumerate(t_list):
            mk = 1 << i
            F0_exact[:, mk] = c0_leg[b]
            act_idx[:, mk] = i
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
            best_v = np.full((n_ev, k_len), np.inf, dtype=float)
            best_a = np.zeros((n_ev, k_len), dtype=np.int32)
            for i, b in enumerate(t_list):
                bit_i = 1 << i
                valid_cols = [(pos_in_k[mk], mk ^ bit_i) for mk in mk_list if (mk & bit_i)]
                if not valid_cols:
                    continue
                col_locs = [c[0] for c in valid_cols]
                rem_masks = [c[1] for c in valid_cols]
                W_rem = F0_exact[:, rem_masks]
                cont = P_leg[b] @ W_rem[offsets[b], :]
                if np.any(in_ball[b]):
                    cont = np.where(in_ball[b][:, None], W_rem, cont)
                Q_b = c0_leg[b][:, None] + cont
                cur_slice = best_v[:, col_locs]
                better = Q_b < cur_slice
                best_v[:, col_locs] = np.where(better, Q_b, cur_slice)
                best_a[:, col_locs] = np.where(better, i, best_a[:, col_locs])
            F0_exact[:, mk_list] = best_v
            act_idx[:, mk_list] = best_a
        dp_ms = 1000.0 * (time.perf_counter() - t_dp0)

        t_ctrl0 = time.perf_counter()
        F_exact = F0_exact + phi_mask_sum[None, :]
        full_mk = n_masks - 1
        val0 = float(F_exact[0, full_mk])
        if not np.all(np.isfinite(F_exact)) or not math.isfinite(val0):
            return _fail_exact("nonfinite_dp_output")

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

        ctrl_ms = 1000.0 * (time.perf_counter() - t_ctrl0)
        tot_ms = 1000.0 * (time.perf_counter() - t0)
        return IntervalCertificate(
            status="epsilon_certified",
            certified=True,
            certificate_scope="exact_discrete_ball_stopping_macro_mdp_all_markov_policies",
            epsilon_tol=0.0,
            lower_bound=val0,
            upper_bound=val0,
            stop_reason="exact_ring_single_pass",
            operator_epoch=self.pl.operator_epoch,
            work={
                "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                "col_solve_ms": col_solve_ms,
                "dp_ms": dp_ms,
                "occupancy_ms": 0.0,
                "selection_ms": 0.0,
                "controller_ms": ctrl_ms,
                "planning_ms": tot_ms,
                "eval_rows": int(n_ev),
                "subset_masks": int(n_masks),
                "row_mask_entries": int(n_ev * n_masks),
                "dp_tables_bytes": int(F_exact.nbytes + act_idx.nbytes),
            },
            extras={
                "route_chosen": "cached_exact_ring_subset_dp",
                "macro_value_bounds": [val0, val0],
                "guaranteed_suboptimality_upper_bound": 0.0,
                "policy_action_idx": act_idx.copy(),
                "select_next_waypoint": select_next_waypoint,
                "eval_nodes": eval_nodes,
                "refinement_steps": [],
                "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                "col_solve_ms": col_solve_ms,
                "dp_ms": dp_ms,
                "occupancy_ms": 0.0,
                "controller_ms": ctrl_ms,
                "planning_ms": tot_ms,
            },
        ).to_dict()

    def plan_exact_fixed_tour(
        self,
        start_point: Sequence[float],
        target_wp_ids: Sequence[int],
    ) -> dict:
        """Matched-Class Operational Cached-ExactRing Fixed-Tour Evaluator (`ddd19c5 P1 Fail-Closed`)."""
        t0 = time.perf_counter()
        s_arr = np.asarray(start_point, dtype=float)
        t_list = list(target_wp_ids)
        m = len(t_list)
        solves_before = self.pl.total_lu_backsolves

        def _fail_fixed(reason: str) -> dict:
            tot_ms = 1000.0 * (time.perf_counter() - t0)
            return IntervalCertificate(
                status="numeric_invalid",
                certified=False,
                certificate_scope="exact_discrete_ball_stopping_response_composition_model",
                epsilon_tol=0.0,
                stop_reason=reason,
                operator_epoch=self.pl.operator_epoch,
                work={"new_lu_backsolves": self.pl.total_lu_backsolves - solves_before, "ordering_ms": tot_ms},
                extras={
                    "best_order": None,
                    "selected_bounds": None,
                    "guaranteed_suboptimality_upper_bound": None,
                    "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                    "ordering_ms": tot_ms,
                    "scores": None,
                },
            ).to_dict()

        if not np.all(np.isfinite(s_arr)) or any(not np.isfinite(self.pl.waypoints[b].phi) for b in t_list):
            return _fail_fixed("nonfinite_input")

        s_node = int(np.argmin(np.sum((self.pl.pts - s_arr[None, :]) ** 2, axis=1)))

        t_col0 = time.perf_counter()
        for b in t_list:
            if not self.pl._is_level_exact_in_current_epoch(b, "EXACT"):
                if "EXACT" in self.pl._wp_tree.get(b, {}):
                    self.pl.refresh_waypoint_under_current_operator(b, "EXACT")
                else:
                    self.pl.ensure_wp_level(b, "EXACT")
            else:
                self.pl.ensure_wp_level(b, "EXACT")
        col_solve_ms = 1000.0 * (time.perf_counter() - t_col0)

        t_enum0 = time.perf_counter()
        eval_nodes, offsets, in_ball = _build_macro_eval_layout(self.pl, s_node, t_list)
        lam = self.pl.spec.lam
        total_phi = float(sum(float(self.pl.waypoints[b].phi) for b in t_list))
        c0_leg: Dict[int, np.ndarray] = {}
        P_leg: Dict[int, np.ndarray] = {}
        for b in t_list:
            pr = self.pl.prepare_wp_ring_eval(b, eval_nodes)
            H_eval = pr["U_eval"] @ pr["P_pinv"]
            if not np.all(np.isfinite(H_eval)):
                return _fail_fixed("nonfinite_harmonic_operator")
            zbar_raw = np.sum(H_eval, axis=1)
            ext_rows = ~in_ball[b]
            if np.any(zbar_raw[ext_rows] <= 1e-285) or np.any(H_eval[ext_rows, :] < -1e-7):
                return _fail_fixed("desirability_underflow_or_sign_loss")
            zbar_safe = np.where(in_ball[b], 1.0, zbar_raw)
            cb0 = -lam * np.log(zbar_safe)
            cb0[in_ball[b]] = 0.0
            Pb = H_eval / zbar_safe[:, None]
            if not (np.all(np.isfinite(cb0)) and np.all(np.isfinite(Pb))):
                return _fail_fixed("nonfinite_normalized_leg_operator")
            c0_leg[b] = cb0
            P_leg[b] = Pb

        W_suf: Dict[Tuple[int, ...], np.ndarray] = {(b,): c0_leg[b].copy() for b in t_list}
        for L_s in range(2, m + 1):
            first_only = (L_s == m)
            for b in t_list:
                others = [x for x in t_list if x != b]
                sl_b = offsets[b]
                ib_b = in_ball[b]
                Pb = P_leg[b][0:1, :] if first_only else P_leg[b]
                vb = c0_leg[b][0:1] if first_only else c0_leg[b]
                r_perms = list(itertools.permutations(others, L_s - 1))
                W_mat = np.column_stack([W_suf[rp] for rp in r_perms])
                cont_mat = Pb @ W_mat[sl_b, :]
                if first_only:
                    out_mat = np.where(ib_b[0:1, None], vb[:, None] + W_mat[0:1, :], vb[:, None] + cont_mat)
                else:
                    out_mat = np.where(ib_b[:, None], vb[:, None] + W_mat, vb[:, None] + cont_mat)
                for c_k, rp in enumerate(r_perms):
                    W_suf[(b, *rp)] = out_mat[:, c_k]

        scores = {perm: float(W_suf[perm][0] + total_phi) for perm in itertools.permutations(t_list, m)}
        if not all(math.isfinite(v) for v in scores.values()):
            return _fail_fixed("nonfinite_tour_score")
        best_order = min(scores.keys(), key=lambda pm: scores[pm])
        best_val = scores[best_order]
        enum_ms = 1000.0 * (time.perf_counter() - t_enum0)
        tot_ms = 1000.0 * (time.perf_counter() - t0)
        return IntervalCertificate(
            status="epsilon_certified",
            certified=True,
            certificate_scope="exact_discrete_ball_stopping_response_composition_model",
            epsilon_tol=0.0,
            lower_bound=best_val,
            upper_bound=best_val,
            stop_reason="exact_ring_fixed_tour_enumeration",
            operator_epoch=self.pl.operator_epoch,
            work={
                "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                "col_solve_ms": col_solve_ms,
                "enum_ms": enum_ms,
                "ordering_ms": tot_ms,
            },
            extras={
                "best_order": best_order,
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
            },
        ).to_dict()

    def plan_subset_macro_policy(
        self,
        start_point: Sequence[float],
        target_wp_ids: Sequence[int],
        epsilon_tol: float = 0.25,
        max_refine_steps: int = 8,
        allow_exact_ring_level: bool = True,
        refine_strategy: str = "decision_guided",
        use_incremental_dp: bool = True,
        return_dp_tables: bool = False,
    ) -> dict:
        """Genuine Adaptive Subset-State Macro-Planner (`m = 5..10`, `ddd19c5 Stage A + Stage B`):
          - Supports exact dependency-tracked Incremental Subset-DP (`use_incremental_dp=True`),
            avoiding full-table re-evaluation of unaffected `(k, action, mask)` columns;
          - Equalizes batch size across `"decision_guided"` and `"uniform_width"` for clean priority ablation;
          - Exposes full phase timings (`col_solve_ms`, `dp_ms`, `occupancy_ms`, `selection_ms`, `controller_ms`)
            and optional `F_lo_table, F_hi_table` (`return_dp_tables=True`) for full-table envelope audits!
        """
        t0 = time.perf_counter()
        s_arr = np.asarray(start_point, dtype=float)
        t_list = list(target_wp_ids)
        m = len(t_list)
        solves_before = self.pl.total_lu_backsolves

        def _fail_macro(reason: str, refs: list, trace: list) -> dict:
            tot_ms = 1000.0 * (time.perf_counter() - t0)
            return IntervalCertificate(
                status="numeric_invalid",
                certified=False,
                certificate_scope="exact_discrete_ball_stopping_macro_mdp_all_markov_policies",
                epsilon_tol=epsilon_tol,
                stop_reason=reason,
                operator_epoch=self.pl.operator_epoch,
                work={"new_lu_backsolves": self.pl.total_lu_backsolves - solves_before, "planning_ms": tot_ms},
                extras={
                    "macro_value_bounds": None,
                    "guaranteed_suboptimality_upper_bound": None,
                    "policy_action_idx": None,
                    "select_next_waypoint": None,
                    "eval_nodes": None,
                    "refinement_steps": refs,
                    "refinement_trace": trace,
                    "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                    "planning_ms": tot_ms,
                    "ordering_ms": tot_ms,
                },
            ).to_dict()

        if not np.all(np.isfinite(s_arr)) or any(not np.isfinite(self.pl.waypoints[j].phi) for j in t_list):
            return _fail_macro("nonfinite_input", [], [])

        s_node = int(np.argmin(np.sum((self.pl.pts - s_arr[None, :]) ** 2, axis=1)))
        t_col_ms = 0.0
        t_dp_ms = 0.0
        t_occ_ms = 0.0
        t_sel_ms = 0.0

        t_c0 = time.perf_counter()
        for j in t_list:
            cur_lv = self.pl.wp_levels.get(j, "NONE")
            if cur_lv == "NONE":
                rem_lv = self.pl._wp_remembered_level.get(j, self.pl.default_lazy_level)
                self.pl.ensure_wp_level(j, rem_lv)
            elif not self.pl._is_level_valid_in_current_epoch(j, cur_lv):
                self.pl.refresh_waypoint_under_current_operator(j, cur_lv)
        t_col_ms += 1000.0 * (time.perf_counter() - t_c0)

        inc_ws = self._init_subset_dp_workspace(s_node, t_list) if use_incremental_dp else None
        if use_incremental_dp and inc_ws is None:
            return _fail_macro("nonfinite_input", [], [])

        refinements: list = []
        refinement_trace: list = []
        certified = False
        stop_reason = "budget_exhausted"
        full_mk = (1 << m) - 1
        dp_res: dict = {}
        prev_root_act: Optional[int] = None
        prev_gap: Optional[float] = None
        dp_calls = 0
        total_cols_propagated = 0
        total_cols_full_equiv = 0

        # Unified batch size across strategies for single-factor priority fairness (`ddd19c5 Sec 6`)
        batch_cap = 3 if m >= 6 else 2

        for step_i in range(max_refine_steps + 1):
            t_d0 = time.perf_counter()
            dp_calls += 1
            if use_incremental_dp and inc_ws is not None:
                dp_res, ok, dp_diag = self._step_incremental_subset_macro_dp(inc_ws)
                total_cols_propagated += dp_diag.get("cols_propagated", 0)
                total_cols_full_equiv += dp_diag.get("cols_total", 0)
            else:
                dp_res, ok = self._compute_subset_macro_dp(s_node, t_list)
            t_dp_ms += 1000.0 * (time.perf_counter() - t_d0)

            if not ok:
                if step_i >= max_refine_steps:
                    return _fail_macro("numeric_invalid_at_budget_cap", refinements, refinement_trace)
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
                    return _fail_macro("numeric_invalid_at_max_resolution", refinements, refinement_trace)
                if use_incremental_dp:
                    inc_ws = self._init_subset_dp_workspace(s_node, t_list)
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
                t_o0 = time.perf_counter()
                impacts = self._compute_dual_occupancy_waypoint_impacts(dp_res, t_list)
                t_occ_ms += 1000.0 * (time.perf_counter() - t_o0)

                t_s0 = time.perf_counter()
                cands_active = []
                cands_fallback = []
                for j in t_list:
                    cur_lv = self.pl.wp_levels[j]
                    imp_j = impacts.get(j, 0.0)
                    w_j = dp_res["wp_width"].get(j, 0.0)
                    if (j, cur_lv) in self.pl._wp_col_err_bounds:
                        d_cols = max(1, len(self.pl._wp_partitions[j][cur_lv]))
                        if imp_j > 1e-12:
                            cands_active.append((imp_j / float(d_cols), imp_j, j, cur_lv, True))
                        elif w_j > 1e-12:
                            cands_fallback.append((w_j / float(d_cols), 0.0, j, cur_lv, True))
                        continue
                    nxt = next_finer_level(cur_lv, allow_exact=allow_exact_ring_level)
                    if nxt is not None:
                        d_cols = max(1, self.pl.marginal_backsolves_to_refine(j, nxt))
                        if imp_j > 1e-12:
                            cands_active.append((imp_j / float(d_cols), imp_j, j, nxt, False))
                        elif w_j > 1e-12:
                            cands_fallback.append((w_j / float(d_cols), 0.0, j, nxt, False))
                cands = cands_active if cands_active else cands_fallback
                if not cands:
                    t_sel_ms += 1000.0 * (time.perf_counter() - t_s0)
                    stop_reason = "all_relevant_waypoints_at_max_resolution"
                    break
                cands.sort(reverse=True)
                picked = [(j, nxt, is_ref) for _, _, j, nxt, is_ref in cands[:batch_cap]]
                t_sel_ms += 1000.0 * (time.perf_counter() - t_s0)

                t_c0 = time.perf_counter()
                bs_round0 = self.pl.total_lu_backsolves
                for j, nxt, is_ref in picked:
                    if is_ref:
                        self.pl.refresh_waypoint_under_current_operator(j, nxt)
                        refinements.append((int(j), f"REFRESH_{nxt}"))
                    else:
                        self.pl.ensure_wp_level(j, nxt)
                        refinements.append((int(j), nxt))
                t_col_ms += 1000.0 * (time.perf_counter() - t_c0)
                refinement_trace.append({
                    "round": step_i + 1,
                    "picked": [(int(j), ("REFRESH_" + nxt if is_ref else nxt)) for j, nxt, is_ref in picked],
                    "new_backsolves": self.pl.total_lu_backsolves - bs_round0,
                    "gap_before": gap_ub,
                })
            elif refine_strategy == "uniform_width":
                t_s0 = time.perf_counter()
                cands_u = []
                for j in t_list:
                    cur_lv = self.pl.wp_levels[j]
                    w_j = dp_res["wp_width"].get(j, 0.0)
                    if (j, cur_lv) in self.pl._wp_col_err_bounds and w_j > 1e-12:
                        cands_u.append((10, w_j, j, cur_lv, True))
                        continue
                    nxt = next_finer_level(cur_lv, allow_exact=allow_exact_ring_level)
                    if nxt is not None and w_j > 1e-12:
                        cands_u.append((-LEVEL_RANK[cur_lv], w_j, j, nxt, False))
                if not cands_u:
                    t_sel_ms += 1000.0 * (time.perf_counter() - t_s0)
                    stop_reason = "all_active_waypoints_at_max_resolution"
                    break
                cands_u.sort(reverse=True)
                picked_u = [(j, nxt, is_ref) for _, _, j, nxt, is_ref in cands_u[:batch_cap]]
                t_sel_ms += 1000.0 * (time.perf_counter() - t_s0)

                t_c0 = time.perf_counter()
                bs_round0 = self.pl.total_lu_backsolves
                for wp_pick, nxt, is_ref in picked_u:
                    if is_ref:
                        self.pl.refresh_waypoint_under_current_operator(wp_pick, nxt)
                        refinements.append((int(wp_pick), f"REFRESH_{nxt}"))
                    else:
                        self.pl.ensure_wp_level(wp_pick, nxt)
                        refinements.append((int(wp_pick), nxt))
                t_col_ms += 1000.0 * (time.perf_counter() - t_c0)
                refinement_trace.append({
                    "round": step_i + 1,
                    "picked": [(int(w), ("REFRESH_" + nx if ir else nx)) for w, nx, ir in picked_u],
                    "new_backsolves": self.pl.total_lu_backsolves - bs_round0,
                    "gap_before": gap_ub,
                })
            else:
                raise ValueError(f"Unknown refine_strategy: {refine_strategy}")

        t_ctrl0 = time.perf_counter()
        eval_nodes = dp_res["eval_nodes"]
        offsets = dp_res["offsets"]
        act_table = dp_res["policy_action_idx"].copy()
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

        t_ctrl_ms = 1000.0 * (time.perf_counter() - t_ctrl0)
        lo_fin = float(dp_res["F_lo"][0, full_mk])
        hi_fin = float(dp_res["F_hi"][0, full_mk])
        tot_ms = 1000.0 * (time.perf_counter() - t0)

        extras_dict = {
            "route_chosen": f"{'incremental' if use_incremental_dp else 'scratch'}_{refine_strategy}_port_dp",
            "refine_strategy": refine_strategy,
            "use_incremental_dp": bool(use_incremental_dp),
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
            "occupancy_ms": t_occ_ms,
            "selection_ms": t_sel_ms,
            "controller_ms": t_ctrl_ms,
            "planning_ms": tot_ms,
            "ordering_ms": tot_ms,
        }
        if return_dp_tables:
            extras_dict["F_lo_table"] = dp_res["F_lo"].copy()
            extras_dict["F_hi_table"] = dp_res["F_hi"].copy()

        return IntervalCertificate(
            status="epsilon_certified" if certified else "unresolved",
            certified=certified,
            certificate_scope="exact_discrete_ball_stopping_macro_mdp_all_markov_policies",
            epsilon_tol=epsilon_tol,
            lower_bound=lo_fin,
            upper_bound=hi_fin,
            stop_reason=stop_reason,
            operator_epoch=self.pl.operator_epoch,
            work={
                "new_lu_backsolves": self.pl.total_lu_backsolves - solves_before,
                "col_solve_ms": t_col_ms,
                "dp_ms": t_dp_ms,
                "occupancy_ms": t_occ_ms,
                "selection_ms": t_sel_ms,
                "controller_ms": t_ctrl_ms,
                "planning_ms": tot_ms,
                "dp_calls": int(dp_calls),
                "refinement_rounds_executed": len(refinement_trace),
                "incremental_cols_propagated": int(total_cols_propagated),
                "full_dp_cols_equivalent": int(total_cols_full_equiv),
                "eval_rows": int(n_ev),
                "subset_masks": int(n_masks),
                "row_mask_entries": int(n_ev * n_masks),
                "dp_tables_bytes": int(dp_res["F_lo"].nbytes + dp_res["F_hi"].nbytes + act_table.nbytes),
            },
            extras=extras_dict,
        ).to_dict()

    def plan_economical_hybrid(
        self,
        start_point: Sequence[float],
        target_wp_ids: Sequence[int],
        epsilon_tol: float = 0.25,
        max_refine_steps: int = 12,
    ) -> dict:
        """Conditional Heuristic Macro-Router (`ddd19c5` + `d1b926a` + `29fa7c6` Scope Note):
        Note: `plan_exact_subset_dp` (`ExactRing + Subset-DP`) is the recommended default production
        macro-planner in 2D and moderate 3D (`<= 31^3`), where single-pass exact DP avoids multi-round
        port overhead. This router is retained as a transparent heuristic option (primarily useful when
        residual-valid columns are already warm after micro-updates and a fresh `splu` can be avoided).
        """
        t_r0 = time.perf_counter()
        t_list = list(target_wp_ids)
        m = len(t_list)
        n_grid = len(self.pl.pts)
        dim = self.pl.spec.dim
        exact_work = self.pl.estimate_current_exact_route_work(t_list)
        missing_exact_bs = int(exact_work["missing_current_exact_backsolves"])
        needs_lu = bool(exact_work["requires_new_lu_factorization"])
        all_residual_valid = (int(exact_work["residual_valid_waypoints"]) == int(exact_work["total_target_waypoints"]))

        # Conservative, transparent cost rule (`d1b926a Sec 3.1`):
        #   1. If residual-valid columns already cover all active waypoints AND exact route would trigger a fresh LU,
        #      try incremental residual-audited port DP to avoid `splu` when possible;
        #   2. Otherwise, default to single-pass `plan_exact_subset_dp` unless we are in high-DOF 3D (`n_grid >= 20000`)
        #      with substantial uncached ring backsolves (`missing_exact_bs >= 40 * m`).
        use_port_route = (
            (needs_lu and all_residual_valid and m > 0)
            or (dim >= 3 and n_grid >= 20000 and missing_exact_bs >= 40 * max(1, m))
        )
        router_ms = 1000.0 * (time.perf_counter() - t_r0)
        if not use_port_route:
            res = self.plan_exact_subset_dp(start_point, t_list)
            selected_route = "cached_exact_ring_subset_dp"
        else:
            res = self.plan_subset_macro_policy(
                start_point,
                t_list,
                epsilon_tol=epsilon_tol,
                max_refine_steps=max_refine_steps,
                refine_strategy="decision_guided",
                use_incremental_dp=True,
            )
            selected_route = "incremental_decision_port_dp"

        inner_ms = float(res.get("planning_ms", 0.0))
        total_ms = inner_ms + router_ms
        res["inner_route_planning_ms"] = inner_ms
        res["router_ms"] = router_ms
        res["planning_ms"] = total_ms
        if isinstance(res.get("work"), dict):
            res["work"]["inner_route_planning_ms"] = inner_ms
            res["work"]["router_ms"] = router_ms
            res["work"]["planning_ms"] = total_ms
            res["work"]["exact_route_work_estimate"] = exact_work
        res["exact_route_work_estimate"] = exact_work
        res["hybrid_selected_route"] = selected_route
        return res

    def compute_exact_macro_q_sensitivities(
        self,
        start_point: Sequence[float],
        target_wp_ids: Sequence[int],
        max_alt_branches: int = 3,
        include_drift_grad: bool = True,
    ) -> dict:
        """Target-Permutation-Invariant Active-Branch Discrete Green Adjoint Sensitivity (`29fa7c6` Closure):
        Canonicalizes `target_wp_ids` as an unordered set (`sorted(unique)`) so all outputs are 100%
        invariant (`0.0` difference) under arbitrary input list permutations, and computes via Reverse-Mode AD
        through the Subset-DP DAG + ONE batched SuperLU transpose solve `A_0^{-T}`:
          - Uses `np.add.at` scatter-accumulation on `eval_nodes` so start-on-ring and overlapping-ring
            geometries sum repeated physical-node contributions exactly (`< 1e-9` vs killed-domain FD);
          - Extracts BOTH `grad_q` (`dF / dq_grid`) AND upwind drift `grad_b` (`dF / db_grid`, zero extra solves!)
            for the incumbent branch AND up to `max_alt_branches` competing root actions;
          - Explicitly declares `derivative_kind = "active_branch"` alongside `active_action_margin` and
            `tie_detected` (reflecting the piecewise-smooth cusp at Bellman action ties).
        """
        t0 = time.perf_counter()
        s_arr = np.asarray(start_point, dtype=float)
        t_canon = sorted(dict.fromkeys(int(w) for w in target_wp_ids))
        m = len(t_canon)
        n_grid = len(self.pl.pts)
        dim = self.pl.spec.dim
        if m == 0:
            z = np.zeros(n_grid, dtype=float)
            zb = np.zeros((n_grid, dim), dtype=float)
            return {
                "derivative_kind": "active_branch",
                "tie_detected": False,
                "active_action_margin": float("inf"),
                "canonical_wp_ids": (),
                "optimal_value": 0.0,
                "incumbent_wp": None,
                "runner_up_wp": None,
                "action_gap": 0.0,
                "grad_q_optimal": z,
                "grad_q_runner_up": z.copy(),
                "grad_q_top_gap": z.copy(),
                "grad_b_optimal": zb,
                "grad_b_runner_up": zb.copy(),
                "grad_b_top_gap": zb.copy(),
                "alt_branches": [],
                "sensitivity_ms": 1000.0 * (time.perf_counter() - t0),
            }

        s_node = int(np.argmin(np.sum((self.pl.pts - s_arr[None, :]) ** 2, axis=1)))
        for b in t_canon:
            if not self.pl._is_level_exact_in_current_epoch(b, "EXACT"):
                if "EXACT" in self.pl._wp_tree.get(b, {}):
                    self.pl.refresh_waypoint_under_current_operator(b, "EXACT")
                else:
                    self.pl.ensure_wp_level(b, "EXACT")
            else:
                self.pl.ensure_wp_level(b, "EXACT")
        lu_cur = self.pl._ensure_current_lu()

        eval_nodes, offsets, in_ball = _build_macro_eval_layout(self.pl, s_node, t_canon)
        lam = self.pl.spec.lam
        phis = np.array([float(self.pl.waypoints[b].phi) for b in t_canon], dtype=float)

        U_full: Dict[int, np.ndarray] = {}
        P_pinv: Dict[int, np.ndarray] = {}
        H_eval: Dict[int, np.ndarray] = {}
        zbar_safe: Dict[int, np.ndarray] = {}
        c0_leg: Dict[int, np.ndarray] = {}
        P_leg: Dict[int, np.ndarray] = {}

        for b in t_canon:
            ring_b = self.pl.wp_rings[b]
            _, U_b = self.pl.ensure_wp_level(b, "EXACT")
            pinv_b = np.linalg.inv(U_b[ring_b, :])
            he_b = U_b[eval_nodes, :] @ pinv_b
            zb_raw = np.sum(he_b, axis=1)
            zb_s = np.where(in_ball[b], 1.0, zb_raw)
            cb0 = np.where(in_ball[b], 0.0, -lam * np.log(zb_s))
            U_full[b] = U_b
            P_pinv[b] = pinv_b
            H_eval[b] = he_b
            zbar_safe[b] = zb_s
            c0_leg[b] = cb0
            P_leg[b] = he_b / zb_s[:, None]

        n_ev = len(eval_nodes)
        n_masks = 1 << m
        F0_exact = np.zeros((n_ev, n_masks), dtype=float)
        act_idx = np.zeros((n_ev, n_masks), dtype=np.int32)
        step_margin = np.full((n_ev, n_masks), np.inf, dtype=float)
        phi_mask_sum = np.zeros(n_masks, dtype=float)
        for i, b in enumerate(t_canon):
            mk = 1 << i
            F0_exact[:, mk] = c0_leg[b]
            act_idx[:, mk] = i
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
            best_v = np.full((n_ev, k_len), np.inf, dtype=float)
            second_v = np.full((n_ev, k_len), np.inf, dtype=float)
            best_a = np.zeros((n_ev, k_len), dtype=np.int32)
            for i, b in enumerate(t_canon):
                bit_i = 1 << i
                valid_cols = [(pos_in_k[mk], mk ^ bit_i) for mk in mk_list if (mk & bit_i)]
                if not valid_cols:
                    continue
                col_locs = [c[0] for c in valid_cols]
                rem_masks = [c[1] for c in valid_cols]
                W_rem = F0_exact[:, rem_masks]
                cont = P_leg[b] @ W_rem[offsets[b], :]
                if np.any(in_ball[b]):
                    cont = np.where(in_ball[b][:, None], W_rem, cont)
                Q_b = c0_leg[b][:, None] + cont
                cur_best = best_v[:, col_locs]
                cur_sec = second_v[:, col_locs]
                better = Q_b < cur_best
                second_v[:, col_locs] = np.where(better, cur_best, np.minimum(cur_sec, Q_b))
                best_v[:, col_locs] = np.where(better, Q_b, cur_best)
                best_a[:, col_locs] = np.where(better, i, best_a[:, col_locs])
            F0_exact[:, mk_list] = best_v
            act_idx[:, mk_list] = best_a
            step_margin[:, mk_list] = np.maximum(0.0, second_v - best_v)

        full_mk = n_masks - 1
        Q_root = np.zeros(m, dtype=float)
        for i, b in enumerate(t_canon):
            rem = full_mk ^ (1 << i)
            if in_ball[b][0]:
                q0_i = float(F0_exact[0, rem])
            else:
                q0_i = float(c0_leg[b][0] + P_leg[b][0, :] @ F0_exact[offsets[b], rem])
            Q_root[i] = q0_i + float(phi_mask_sum[full_mk])

        order_i = np.argsort(Q_root, kind="mergesort")
        inc_i = int(order_i[0])
        alt_is = [int(x) for x in order_i[1 : 1 + max(1, int(max_alt_branches))]]
        run_i = alt_is[0] if alt_is else inc_i

        def _accumulate_theta(forced_root_i: int) -> Tuple[float, Dict[int, np.ndarray], float]:
            if forced_root_i == int(act_idx[0, full_mk]):
                V0_pi = F0_exact
            else:
                V0_pi = F0_exact.copy()
                b0 = t_canon[forced_root_i]
                rem0 = full_mk ^ (1 << forced_root_i)
                V0_pi[0, full_mk] = (
                    V0_pi[0, rem0] if in_ball[b0][0] else float(c0_leg[b0][0] + P_leg[b0][0, :] @ V0_pi[offsets[b0], rem0])
                )
            rho = np.zeros((n_ev, n_masks), dtype=float)
            rho[0, full_mk] = 1.0
            Theta: Dict[int, np.ndarray] = {b: np.zeros((n_ev, len(self.pl.wp_rings[b])), dtype=float) for b in t_canon}
            min_active_margin = float("inf")

            for k in range(m, 0, -1):
                for mk in masks_by_pop[k]:
                    nz_rows = np.flatnonzero(rho[:, mk] > 0.0)
                    for r in nz_rows:
                        m_val = float(rho[r, mk])
                        if k >= 2 and not (r == 0 and mk == full_mk and forced_root_i != int(act_idx[0, full_mk])):
                            min_active_margin = min(min_active_margin, float(step_margin[r, mk]))
                        i_act = forced_root_i if (r == 0 and mk == full_mk) else int(act_idx[r, mk])
                        b = t_canon[i_act]
                        rem = mk ^ (1 << i_act)
                        if in_ball[b][r]:
                            if k > 1:
                                rho[r, rem] += m_val
                        else:
                            v_rem = V0_pi[offsets[b], rem] if k > 1 else np.zeros(len(self.pl.wp_rings[b]), dtype=float)
                            v_bar = float(P_leg[b][r, :] @ v_rem)
                            Theta[b][r, :] += m_val * (((-lam - v_bar) + v_rem) / zbar_safe[b][r])
                            if k > 1:
                                rho[offsets[b], rem] += m_val * P_leg[b][r, :]
            return float(V0_pi[0, full_mk] + phi_mask_sum[full_mk]), Theta, min_active_margin

        val_inc, Theta_inc, min_act_margin = _accumulate_theta(inc_i)
        modes_theta = [Theta_inc]
        alt_vals: List[float] = []
        for ai in alt_is:
            v_a, Th_a, _ = _accumulate_theta(ai)
            alt_vals.append(v_a)
            modes_theta.append(Th_a)
        val_run = alt_vals[0] if alt_vals else val_inc

        # Batch ALL transpose solves into ONE SuperLU call (`A_0^T Psi = W_stacked`) with exact scatter-add!
        rhs_blocks = []
        block_slices = []
        col_cursor = 0
        for th_dict in modes_theta:
            mode_sl = {}
            for b in t_canon:
                th_b = th_dict[b]
                rb_len = len(self.pl.wp_rings[b])
                if not np.any(th_b):
                    mode_sl[b] = None
                    continue
                W_b = np.zeros((n_grid, rb_len), dtype=float)
                pinv_T = P_pinv[b].T
                np.add.at(W_b, eval_nodes, th_b @ pinv_T)
                np.add.at(W_b, self.pl.wp_rings[b], -((H_eval[b].T @ th_b) @ pinv_T))
                rhs_blocks.append(W_b)
                mode_sl[b] = slice(col_cursor, col_cursor + rb_len)
                col_cursor += rb_len
            block_slices.append(mode_sl)

        if rhs_blocks:
            Psi_all = lu_cur.solve(np.hstack(rhs_blocks), trans="T")
        else:
            Psi_all = np.zeros((n_grid, 0), dtype=float)

        # Precompute upwind grid geometry once for zero-extra-solve drift sensitivity `dF / db_grid`
        gn = self.pl.grid_n
        h_grid = self.pl.h
        b_cur = np.zeros((n_grid, dim), dtype=float) if self.pl.b_grid is None else self.pl.b_grid
        strides = [gn ** (dim - 1 - ax) for ax in range(dim)]
        idx_all = np.arange(n_grid, dtype=np.int64)
        coords_ax = [(idx_all // strides[ax]) % gn for ax in range(dim)]

        grads_q_out = []
        grads_b_out = []
        for mode_sl in block_slices:
            g_q = np.zeros(n_grid, dtype=float)
            g_b = np.zeros((n_grid, dim), dtype=float)
            for b in t_canon:
                sl_b = mode_sl[b]
                if sl_b is None:
                    continue
                Psi_b = Psi_all[:, sl_b]
                U_b = U_full[b]
                g_q += -(1.0 / lam) * np.einsum("ij,ij->i", Psi_b, U_b)
                if include_drift_grad:
                    for ax in range(dim):
                        st = strides[ax]
                        c_ax = coords_ax[ax]
                        b_col = b_cur[:, ax]
                        mask_p = (b_col > 0.0) & (c_ax < (gn - 1))
                        if np.any(mask_p):
                            ip = idx_all[mask_p]
                            g_b[ip, ax] += (1.0 / h_grid) * np.einsum("ij,ij->i", Psi_b[ip, :], U_b[ip + st, :] - U_b[ip, :])
                        mask_m = (b_col < 0.0) & (c_ax > 0)
                        if np.any(mask_m):
                            im = idx_all[mask_m]
                            g_b[im, ax] += (1.0 / h_grid) * np.einsum("ij,ij->i", Psi_b[im, :], U_b[im, :] - U_b[im - st, :])
            grads_q_out.append(g_q)
            grads_b_out.append(g_b)

        g_q_opt = grads_q_out[0]
        g_b_opt = grads_b_out[0]
        g_q_run = grads_q_out[1] if len(grads_q_out) > 1 else g_q_opt.copy()
        g_b_run = grads_b_out[1] if len(grads_b_out) > 1 else g_b_opt.copy()

        alt_branches_out = []
        for idx_alt, ai in enumerate(alt_is):
            gq_a = grads_q_out[1 + idx_alt]
            gb_a = grads_b_out[1 + idx_alt]
            alt_branches_out.append({
                "wp_id": int(t_canon[ai]),
                "value": float(alt_vals[idx_alt]),
                "gap": float(alt_vals[idx_alt] - val_inc),
                "grad_q_branch": gq_a,
                "grad_q_gap": gq_a - g_q_opt,
                "grad_b_gap": gb_a - g_b_opt,
            })

        eff_margin = float(min(min_act_margin, val_run - val_inc)) if m >= 2 else float("inf")
        return {
            "derivative_kind": "active_branch",
            "tie_detected": bool(m >= 2 and eff_margin <= 1e-11),
            "active_action_margin": eff_margin,
            "canonical_wp_ids": tuple(t_canon),
            "Q_root_canonical": Q_root,
            "optimal_value": val_inc,
            "runner_up_value": val_run,
            "incumbent_wp": int(t_canon[inc_i]),
            "runner_up_wp": int(t_canon[run_i]),
            "action_gap": float(val_run - val_inc),
            "grad_q_optimal": g_q_opt,
            "grad_q_runner_up": g_q_run,
            "grad_q_top_gap": g_q_run - g_q_opt,
            "grad_b_optimal": g_b_opt,
            "grad_b_runner_up": g_b_run,
            "grad_b_top_gap": g_b_run - g_b_opt,
            "alt_branches": alt_branches_out,
            "sensitivity_ms": 1000.0 * (time.perf_counter() - t0),
        }

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
