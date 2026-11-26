"""Milestone M2.1 (`quotient_phase2.m21_qgap_collar_ablation`):
Controlled 2x2 Feasibility Ablation Under Identical Full-Policy Quality (`eps_tol = 0.25`):
  Factor A: Killed-Domain Local Collar Remainder Lifting (`False` vs `True`, full exterior feedback)
  Factor B: Operator-Verified Bilinear Primal-Dual (DWR) Enclosure (`Hf` & `H1`) + Same-State Pruning (`False` vs `True`)

Evaluates:
  - Part M2.1-A: Unseen-target source-support obstruction resolution (`2D 51^2` & `3D 21^3`, `strict_unclipped`,
    verifying `0%` `H < 0` and `0%` `Z > 1` on principal killed-collar lifts across `hops = 2, 3, 4`).
  - Part M2.1-B: Continual evolving-world full-lifecycle & test-marginal wall-clock ablation across:
      1. `Exp 5B` Parity Dev Cohort (`30300..30311`, `12` maps, `2D 51^2` & `3D 21^3`, `GP` & `Param` streams);
      2. Untouched Confirmation + 3D Scale-Rung Cohort (`40300..40307`, `8` fresh maps, `3D 21^3` & `3D 27^3`
         [`9,261` -> `19,683` nodes], `GP` & `Param` streams, plus standalone single-worker 3D `splu` scaling
         ladder `21^3 -> 25^3 -> 27^3 -> 31^3` up to `29,791` nodes).

Imports `green_response` strictly read-only (`package_py_sha256 == "271ac8df..."` verified at startup).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "1")

import gc
import json
import sys
import time
import warnings
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from sklearn.exceptions import ConvergenceWarning

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
    observe_world_at_points,
    paired_stats,
    run_map_parallel,
    sample_noisy_probes,
)
from green_response.exp5_response_subspace_diagnostic import (
    _eval_killed_macro_bellman_from_tables,
    _precompute_killed_epoch_tables,
    _sample_nonoverlapping_balls,
)
from green_response.macro_planning import _build_macro_eval_layout

from quotient_phase2 import compute_phase2_manifest, verify_phase1_readonly_freeze
from quotient_phase2.m20_contracts import (
    Phase2DecisionCertificate,
    bound_normalized_continuation_dwr,
)


def _extract_full_grid_collar_indices(
    A0_csr: sp.csr_matrix,
    mask_b: np.ndarray,
    ring_b: np.ndarray,
    hops: int = 2,
) -> np.ndarray:
    """Extracts `k`-hop exterior collar node indices (in full-grid coordinates `0..N-1`, strictly outside `mask_b`)."""
    if hops <= 0 or len(ring_b) == 0:
        return np.zeros(0, dtype=np.int64)
    n_grid = A0_csr.shape[0]
    ext_mask = ~mask_b
    adj = (np.abs(A0_csr) + np.abs(A0_csr.T)) > 0
    seed = np.zeros(n_grid, dtype=float)
    seed[ring_b] = 1.0
    cur = ((adj @ seed) > 0.0) & ext_mask
    for _ in range(max(0, hops - 1)):
        nxt = ((adj @ cur.astype(float)) > 0.0) & ext_mask
        cur = cur | nxt
    return np.flatnonzero(cur).astype(np.int64)


class KilledCollarDWRPlanner:
    """Continual fixed-portal macro-planner implementing the 2x2 `M2.1` ablation under `full_policy_enclosure`:
      - `use_collar_lift`: Local principal M-matrix collar correction + exact full-exterior residual (`P2A-01, 02`);
      - `use_bilinear_dwr`: Operator-verified Bilinear Primal-Dual DWR (`Hf` & `H1`) + same-state Q-pruning (`P2A-03..05`).
    Avoids CSR submatrix slicing on `I_b = ~mask_b` by exploiting exact graph-separator zeros on `mask_b \\ ring_b`.
    """

    def __init__(
        self,
        spec: ProblemSpec,
        grid_n: int,
        q_fn0: Callable[[np.ndarray], np.ndarray],
        b_fn0: Optional[Callable[[np.ndarray], np.ndarray]],
        waypoints: Sequence[GoalBall],
        use_collar_lift: bool,
        use_bilinear_dwr: bool,
        collar_hops: int = 2,
    ) -> None:
        self.use_collar_lift = bool(use_collar_lift)
        self.use_bilinear_dwr = bool(use_bilinear_dwr)
        self.collar_hops = int(collar_hops)

        self.pl = SchurPortPlanner(
            spec, grid_n, q_fn0, b_fn0, waypoints, initial_sectors_per_wp="EXACT", lazy_init=True
        )
        self.mt = MacroTourPlanner(self.pl)
        self.n_grid = len(self.pl.pts)
        self.n_wps = len(waypoints)

        # Static geometry & collar topology (computed once from stencil graph)
        A0_csr = self.pl.A0.tocsr()
        self.ext_idx: Dict[int, np.ndarray] = {}
        self.ext_pos_of_full: Dict[int, np.ndarray] = {}
        self.collar_full_idx: Dict[int, np.ndarray] = {}
        all_rings = []
        for j in range(self.n_wps):
            mk = self.pl.wp_masks[j]
            rg = self.pl.wp_rings[j]
            ext = np.flatnonzero(~mk).astype(np.int64)
            pos_map = np.full(self.n_grid, -1, dtype=np.int64)
            pos_map[ext] = np.arange(len(ext), dtype=np.int64)
            self.ext_idx[j] = ext
            self.ext_pos_of_full[j] = pos_map
            self.collar_full_idx[j] = _extract_full_grid_collar_indices(A0_csr, mk, rg, hops=self.collar_hops)
            all_rings.append(rg)

        self.unique_ring_nodes = np.unique(np.concatenate(all_rings)) if all_rings else np.zeros(0, dtype=np.int64)

        # Reference anchor cache (populated at end of calibration from existing `pl.lu0`)
        self.lu_ref: Optional[spla.SuperLU] = None
        self.H_full_ref: Dict[int, np.ndarray] = {}  # shape `(N, m_b)` with `I` on `ring_b`, `0` on strict interior
        self.phi_node_ref: Dict[int, np.ndarray] = {}  # `nid -> A_ref^{-T} e_nid` (`shape (N,)`)
        self.Phi_ring_ref: Dict[int, np.ndarray] = {}  # `b -> (N, m_b)`
        self.Phi_ring_inv_ref: Dict[int, np.ndarray] = {}  # `b -> inv(Phi_ring_ref[b][ring_b, :])`

        # Per-epoch state & Disaggregated Timing / Work Counters
        self.A_cur_csr: sp.csr_matrix = A0_csr
        self.inv_inf_ub_cur: float = float(spec.lam / max(float(np.min(self.pl.q_base)), 1e-12))
        self.ep_dwr_ops: Dict[int, dict] = {}
        self.ep_eval_row_map: Dict[int, np.ndarray] = {}  # `b -> pos in dwr_op['H_corr'] for full node id`
        self.ep_eval_nodes_tuple: Dict[int, Tuple[int, ...]] = {}
        self.ep_wp_is_exact: Dict[int, bool] = {}

        self.ref_cache_build_ms = 0.0
        self.collar_lift_ms = 0.0
        self.dwr_witness_and_audit_ms = 0.0
        self.dp_ms = 0.0
        self.fallback_exact_ms = 0.0
        self.n_collar_solves = 0
        self.n_transpose_start_backsolves = 0

    def freeze_reference_anchor_from_current_epoch(self) -> None:
        """Caches reference killed hitting kernels `H_b^{(ref)}` (and transpose ring bank ONLY if `use_bilinear_dwr`)
        using the single `lu_cur = self.pl._ensure_current_lu()` at the end of calibration.
        100% charged inside operational planner lifecycle time!
        """
        t0 = time.perf_counter()
        lu_cur = self.pl._ensure_current_lu()
        self.lu_ref = lu_cur

        # Forward ring columns (reusing any already in `self.pl._node_col_cache`!)
        U_all_rings = self.pl._get_node_cols(self.unique_ring_nodes)
        ring_col_pos = {int(nid): idx for idx, nid in enumerate(self.unique_ring_nodes)}

        for b in range(self.n_wps):
            rg = self.pl.wp_rings[b]
            ext = self.ext_idx[b]
            cols = [ring_col_pos[int(nid)] for nid in rg]
            U_b = U_all_rings[:, cols]
            H_ext = U_b[ext, :] @ np.linalg.inv(U_b[rg, :])
            H_full = np.zeros((self.n_grid, len(rg)), dtype=float)
            H_full[ext, :] = H_ext
            H_full[rg, np.arange(len(rg))] = 1.0
            self.H_full_ref[b] = H_full

        if self.use_bilinear_dwr and len(self.unique_ring_nodes) > 0:
            RHS_tr = np.zeros((self.n_grid, len(self.unique_ring_nodes)), dtype=float)
            RHS_tr[self.unique_ring_nodes, np.arange(len(self.unique_ring_nodes))] = 1.0
            Phi_all = lu_cur.solve(RHS_tr, trans="T")
            self.pl.total_lu_backsolves += len(self.unique_ring_nodes)
            for idx, nid in enumerate(self.unique_ring_nodes):
                self.phi_node_ref[int(nid)] = Phi_all[:, idx]
            for b in range(self.n_wps):
                rg = self.pl.wp_rings[b]
                Phi_b = np.column_stack([self.phi_node_ref[int(nid)] for nid in rg])
                self.Phi_ring_ref[b] = Phi_b
                self.Phi_ring_inv_ref[b] = np.linalg.inv(Phi_b[rg, :])

        self.ref_cache_build_ms += 1000.0 * (time.perf_counter() - t0)

    def begin_test_epoch(
        self,
        new_q_fn: Callable[[np.ndarray], np.ndarray],
        new_b_fn: Optional[Callable[[np.ndarray], np.ndarray]],
        epoch_tasks: Sequence[Tuple[np.ndarray, Tuple[int, ...]]],
    ) -> None:
        """Assembles `A_cur` WITHOUT `splu(A_cur)` and prepares lifted/DWR operators for `epoch_tasks`."""
        q_new = self.pl.spec.q0 + np.asarray(new_q_fn(self.pl.pts), dtype=float)
        q_min = float(np.min(q_new))
        if not np.all(np.isfinite(q_new)) or q_min <= 0.0:
            raise ValueError(f"Non-positive q_new min={q_min}")
        b_new = None if new_b_fn is None else np.asarray(new_b_fn(self.pl.pts), dtype=float)
        A_new, _ = build_upwind_mmatrix_desirability_operator(self.pl.spec, self.pl.grid_n, q_new, b_new)

        self.pl.operator_epoch += 1
        self.pl.q_base = q_new
        self.pl.b_grid = b_new
        self.pl.A0 = A_new
        self.pl._lu_is_current = False
        self.pl._wp_ring_op_cache.clear()
        self.pl._adhoc_cache.clear()
        self.pl._node_col_cache.clear()
        self.pl._wp_tree.clear()
        self.pl._wp_tree_col_epoch.clear()
        self.pl._wp_verified_epoch.clear()
        self.pl._wp_col_err_bounds.clear()
        for j in range(self.n_wps):
            self.pl.wp_levels[j] = "NONE"

        self.A_cur_csr = A_new.tocsr()
        self.inv_inf_ub_cur = float(self.pl.spec.lam / q_min)
        self.ep_dwr_ops = {
            j: {
                "H_corr": np.zeros((0, len(self.pl.wp_rings[j])), dtype=float),
                "alpha_row": np.zeros(0, dtype=float),
                "r_col_inf": np.zeros(len(self.pl.wp_rings[j]), dtype=float),
                "rho_1": 0.0,
                "z_lo_ext": np.zeros(0, dtype=float),
                "z_hi_ext": np.zeros(0, dtype=float),
            }
            for j in range(self.n_wps)
        }
        self.ep_eval_row_map = {j: np.full(self.n_grid, -1, dtype=np.int64) for j in range(self.n_wps)}
        self.ep_eval_nodes_tuple = {j: () for j in range(self.n_wps)}
        self.ep_wp_is_exact = {j: False for j in range(self.n_wps)}

        # Map tasks to start nodes & collect required exterior evaluation rows per waypoint `b`
        task_s_nodes: List[int] = []
        wp_req_nodes: Dict[int, set] = {}
        for s_xy, sub_ids in epoch_tasks:
            s_arr = np.asarray(s_xy, dtype=float)
            s_node = int(np.argmin(np.sum((self.pl.pts - s_arr[None, :]) ** 2, axis=1)))
            task_s_nodes.append(s_node)
            ev_nodes = [s_node]
            for a in sub_ids:
                ev_nodes.extend(int(x) for x in self.pl.wp_rings[a])
            for b in sub_ids:
                s_set = wp_req_nodes.setdefault(b, set())
                mk_b = self.pl.wp_masks[b]
                for nid in ev_nodes:
                    if not mk_b[nid]:
                        s_set.add(nid)

        if self.use_bilinear_dwr and self.lu_ref is not None:
            t_w0 = time.perf_counter()
            missing_starts = sorted({nid for nid in task_s_nodes if nid not in self.phi_node_ref})
            if missing_starts:
                RHS_s = np.zeros((self.n_grid, len(missing_starts)), dtype=float)
                RHS_s[missing_starts, np.arange(len(missing_starts))] = 1.0
                Phi_s = self.lu_ref.solve(RHS_s, trans="T")
                self.pl.total_lu_backsolves += len(missing_starts)
                self.n_transpose_start_backsolves += len(missing_starts)
                for idx, nid in enumerate(missing_starts):
                    self.phi_node_ref[nid] = Phi_s[:, idx]
            self.dwr_witness_and_audit_ms += 1000.0 * (time.perf_counter() - t_w0)

        for b, req_set in wp_req_nodes.items():
            req_full = np.array(sorted(req_set), dtype=np.int64)
            ext = self.ext_idx[b]
            H_full_work = self.H_full_ref[b]

            if self.use_collar_lift:
                t_l0 = time.perf_counter()
                c_full = self.collar_full_idx[b]
                if len(c_full) > 0:
                    H_full_work = H_full_work.copy()
                    # Local collar residual `R_c = -(A_cur @ H_full)[c_full, :]` (exact via separator!)
                    R_c = -(self.A_cur_csr[c_full, :] @ H_full_work)
                    A_cc = self.A_cur_csr[c_full, :][:, c_full].tocsc()
                    dH_c = spla.splu(A_cc).solve(R_c)
                    H_full_work[c_full, :] += dH_c
                    self.n_collar_solves += 1
                self.collar_lift_ms += 1000.0 * (time.perf_counter() - t_l0)

            t_a0 = time.perf_counter()
            # Full-exterior residual `R_ext = -(A_cur @ H_full_work)[ext, :]` (0 CSR submatrix slicing!)
            R_ext = -(self.A_cur_csr @ H_full_work)[ext, :]
            r_col_inf = np.max(np.abs(R_ext), axis=0)
            rho_1 = float(np.max(np.abs(np.sum(R_ext, axis=1)))) if R_ext.size > 0 else 0.0

            row_lookup = np.full(self.n_grid, -1, dtype=np.int64)
            row_lookup[req_full] = np.arange(len(req_full), dtype=np.int64)
            self.ep_eval_row_map[b] = row_lookup
            self.ep_eval_nodes_tuple[b] = tuple(int(x) for x in req_full)

            if len(req_full) == 0:
                self.ep_dwr_ops[b] = {
                    "H_corr": np.zeros((0, len(self.pl.wp_rings[b]))),
                    "alpha_row": np.zeros(0),
                    "r_col_inf": r_col_inf,
                    "rho_1": rho_1,
                    "z_lo_ext": np.zeros(0),
                    "z_hi_ext": np.zeros(0),
                }
            elif not self.use_bilinear_dwr:
                H_corr = H_full_work[req_full, :].copy()
                alpha_row = np.full(len(req_full), self.inv_inf_ub_cur, dtype=float)
                z_corr = np.sum(H_corr, axis=1)
                d_z = alpha_row * rho_1
                pad_z = 1e-13 * (1.0 + np.abs(z_corr) + d_z)
                self.ep_dwr_ops[b] = {
                    "H_corr": H_corr,
                    "alpha_row": alpha_row,
                    "r_col_inf": r_col_inf,
                    "rho_1": rho_1,
                    "z_lo_ext": z_corr - d_z - pad_z,
                    "z_hi_ext": np.minimum(1.0, z_corr + d_z + pad_z),
                }
            else:
                rg = self.pl.wp_rings[b]
                Phi_req = np.column_stack([self.phi_node_ref[int(nid)] for nid in req_full])
                coeff = self.Phi_ring_inv_ref[b] @ Phi_req[rg, :]
                Psi_full = Phi_req - (self.Phi_ring_ref[b] @ coeff)
                Psi_full[self.pl.wp_masks[b], :] = 0.0
                Psi_ext = Psi_full[ext, :]

                AT_Psi_ext = (self.pl.A0.T @ Psi_full)[ext, :]
                req_ext_pos = self.ext_pos_of_full[b][req_full]
                Delta_adj = -AT_Psi_ext
                Delta_adj[req_ext_pos, np.arange(len(req_full))] += 1.0
                delta_l1 = np.sum(np.abs(Delta_adj), axis=0)
                alpha_row = self.inv_inf_ub_cur * delta_l1
                H_corr = H_full_work[req_full, :] + (Psi_ext.T @ R_ext)

                z_corr = np.sum(H_corr, axis=1)
                d_z = alpha_row * rho_1
                pad_z = 1e-13 * (1.0 + np.abs(z_corr) + d_z)
                self.ep_dwr_ops[b] = {
                    "H_corr": H_corr,
                    "alpha_row": alpha_row,
                    "r_col_inf": r_col_inf,
                    "rho_1": rho_1,
                    "z_lo_ext": z_corr - d_z - pad_z,
                    "z_hi_ext": np.minimum(1.0, z_corr + d_z + pad_z),
                }
            self.dwr_witness_and_audit_ms += 1000.0 * (time.perf_counter() - t_a0)

    def _upgrade_waypoint_to_current_exact(self, b: int, req_full_nodes: np.ndarray) -> None:
        """Upgrades waypoint `b` to exact current-epoch operator (`R_ext == 0, alpha == 0`) on `req_full_nodes`,
        paying `splu(A_cur)` automatically on the first exact fallback of the epoch and atomically extending
        cached rows (`0` extra LU/backsolve) whenever unannounced online queries request new exterior rows (`v10 C01`).
        """
        req_sorted = np.unique(np.asarray(req_full_nodes, dtype=np.int64))
        req_tup = tuple(int(x) for x in req_sorted)
        if self.ep_wp_is_exact.get(b, False) and self.ep_eval_nodes_tuple.get(b) == req_tup:
            return
        t_f0 = time.perf_counter()
        self.pl.ensure_wp_level(b, "EXACT")
        _, U_b = self.pl._wp_tree[b]["EXACT"]
        rg = self.pl.wp_rings[b]
        if len(req_sorted) == 0:
            H_req = np.zeros((0, len(rg)), dtype=float)
        else:
            H_req = U_b[req_sorted, :] @ np.linalg.inv(U_b[rg, :])
        z_ex = np.sum(H_req, axis=1)
        pad_z = 1e-13 * (1.0 + np.abs(z_ex))
        new_op = {
            "H_corr": H_req,
            "alpha_row": np.zeros(len(req_sorted), dtype=float),
            "r_col_inf": np.zeros(len(rg), dtype=float),
            "rho_1": 0.0,
            "z_lo_ext": z_ex - pad_z,
            "z_hi_ext": np.minimum(1.0, z_ex + pad_z),
        }
        row_lookup = np.full(self.n_grid, -1, dtype=np.int64)
        row_lookup[req_sorted] = np.arange(len(req_sorted), dtype=np.int64)
        # Atomic swap only after `new_op` and `row_lookup` are completely built (`v10 C01` invariant):
        self.ep_dwr_ops[b] = new_op
        self.ep_eval_row_map[b] = row_lookup
        self.ep_eval_nodes_tuple[b] = req_tup
        self.ep_wp_is_exact[b] = True
        self.fallback_exact_ms += 1000.0 * (time.perf_counter() - t_f0)

    def _slice_task_dwr_op(self, b: int, task_ext_full_nodes: np.ndarray) -> dict:
        req_task = np.asarray(task_ext_full_nodes, dtype=np.int64)
        if b not in self.ep_eval_row_map:
            cur_nodes = np.zeros(0, dtype=np.int64)
            need_extend = len(req_task) > 0
        else:
            row_map = self.ep_eval_row_map[b]
            idx = row_map[req_task]
            need_extend = bool(np.any(idx < 0))
            if need_extend:
                cur_nodes = np.flatnonzero(row_map >= 0)
        if need_extend:
            merged = np.unique(np.concatenate([cur_nodes, req_task]))
            self._upgrade_waypoint_to_current_exact(b, merged)
        op = self.ep_dwr_ops[b]
        idx = self.ep_eval_row_map[b][req_task]
        if np.any(idx < 0) or (len(idx) > 0 and int(np.max(idx)) >= op["H_corr"].shape[0]):
            raise RuntimeError(f"Inconsistent ep_eval_row_map / ep_dwr_ops state for waypoint {b}")
        return {
            "H_corr": op["H_corr"][idx, :],
            "alpha_row": op["alpha_row"][idx],
            "r_col_inf": op["r_col_inf"],
            "rho_1": op["rho_1"],
            "z_lo_ext": op["z_lo_ext"][idx],
            "z_hi_ext": op["z_hi_ext"][idx],
        }

    def plan_certified_full_policy_task(
        self,
        start_point: Sequence[float],
        target_wp_ids: Sequence[int],
        epsilon_tol: float = 0.25,
    ) -> dict:
        """Plans under the strict `full_policy_enclosure` (`U^mu(s0) - min_a L_a^*(s0) <= epsilon_tol`) contract."""
        s_arr = np.asarray(start_point, dtype=float)
        t_list = list(target_wp_ids)
        m = len(t_list)
        s_node = int(np.argmin(np.sum((self.pl.pts - s_arr[None, :]) ** 2, axis=1)))
        eval_nodes, offsets, in_ball = _build_macro_eval_layout(self.pl, s_node, t_list)
        n_ev = len(eval_nodes)
        n_masks = 1 << m
        full_mk = n_masks - 1
        lam = self.pl.spec.lam
        phis = np.array([float(self.pl.waypoints[b].phi) for b in t_list], dtype=float)

        phi_mask_sum = np.zeros(n_masks, dtype=float)
        masks_by_pop: List[List[int]] = [[] for _ in range(m + 1)]
        for i in range(m):
            phi_mask_sum[1 << i] = phis[i]
        for mk in range(1, n_masks):
            pc = mk.bit_count()
            masks_by_pop[pc].append(mk)
            if pc >= 2:
                lsb = mk & -mk
                phi_mask_sum[mk] = phi_mask_sum[lsb] + phi_mask_sum[mk ^ lsb]

        ext_rows_local: Dict[int, np.ndarray] = {}
        ext_nodes_full: Dict[int, np.ndarray] = {}
        for b in t_list:
            loc_ext = np.flatnonzero(~in_ball[b])
            ext_rows_local[b] = loc_ext
            ext_nodes_full[b] = eval_nodes[loc_ext]

        # Pre-DP check when `use_bilinear_dwr == False` (Primal Uniform baseline requires all-row `z_lo > 0`)
        refinements: List[Tuple[int, str]] = []
        if not self.use_bilinear_dwr:
            for b in t_list:
                if not self.ep_wp_is_exact.get(b, False):
                    op_b = self._slice_task_dwr_op(b, ext_nodes_full[b])
                    if np.any(op_b["z_lo_ext"] <= 1e-15):
                        cur_nodes = np.flatnonzero(self.ep_eval_row_map[b] >= 0)
                        self._upgrade_waypoint_to_current_exact(b, cur_nodes)
                        refinements.append((int(b), "REFRESH_EXACT_POS"))

        for _round in range(m + 1):
            t_d0 = time.perf_counter()
            F0_lo = np.zeros((n_ev, n_masks), dtype=float)
            F0_hi = np.zeros((n_ev, n_masks), dtype=float)
            act_idx = np.zeros((n_ev, n_masks), dtype=np.int32)
            wp_slack_score = {b: 0.0 for b in t_list}
            dp_valid = True

            task_ops = {b: self._slice_task_dwr_op(b, ext_nodes_full[b]) for b in t_list}

            # Base `k = 1`
            for i, b in enumerate(t_list):
                mk = 1 << i
                op_b = task_ops[b]
                z_lo = op_b["z_lo_ext"]
                z_hi = op_b["z_hi_ext"]
                if np.any(~np.isfinite(z_hi)) or np.any(z_hi <= 1e-285):
                    dp_valid = False
                    break
                c0_lo_ext = -lam * np.log(z_hi)
                pos_ok = z_lo > 1e-15
                if (not self.use_bilinear_dwr) and (not np.all(pos_ok)):
                    dp_valid = False
                    break
                c0_hi_ext = np.where(pos_ok, -lam * np.log(np.where(pos_ok, z_lo, 1.0)), np.inf)

                col_lo = np.zeros(n_ev, dtype=float)
                col_hi = np.zeros(n_ev, dtype=float)
                col_lo[ext_rows_local[b]] = c0_lo_ext
                col_hi[ext_rows_local[b]] = c0_hi_ext
                F0_lo[:, mk] = col_lo
                F0_hi[:, mk] = col_hi
                act_idx[:, mk] = i
                if not self.ep_wp_is_exact.get(b, False):
                    fin_w = np.where(np.isfinite(c0_hi_ext), c0_hi_ext - c0_lo_ext, 50.0)
                    wp_slack_score[b] = max(wp_slack_score[b], float(np.max(fin_w)) if len(fin_w) else 0.0)

            if dp_valid:
                for k in range(2, m + 1):
                    mk_list = masks_by_pop[k]
                    pos_in_k = {mk: idx for idx, mk in enumerate(mk_list)}
                    k_len = len(mk_list)
                    best_lo = np.full((n_ev, k_len), np.inf, dtype=float)
                    best_hi = np.full((n_ev, k_len), np.inf, dtype=float)
                    best_act = np.zeros((n_ev, k_len), dtype=np.int32)
                    q_lo_by_i: Dict[int, np.ndarray] = {}
                    q_hi_by_i: Dict[int, np.ndarray] = {}
                    cols_by_i: Dict[int, List[int]] = {}

                    for i, b in enumerate(t_list):
                        bit_i = 1 << i
                        pairs = [(pos_in_k[mk], mk ^ bit_i) for mk in mk_list if (mk & bit_i)]
                        if not pairs:
                            continue
                        col_locs = [p[0] for p in pairs]
                        rem_masks = [p[1] for p in pairs]
                        cols_by_i[i] = col_locs

                        W_lo_rem = F0_lo[:, rem_masks]
                        W_hi_rem = F0_hi[:, rem_masks]
                        sl_b = offsets[b]
                        ql_ext, qh_ext, ok_b = bound_normalized_continuation_dwr(
                            task_ops[b],
                            W_lo_rem[sl_b, :],
                            W_hi_rem[sl_b, :],
                            lam=lam,
                            allow_extended_inf_upper=self.use_bilinear_dwr,
                        )
                        if not ok_b:
                            dp_valid = False
                            break

                        ql_full = W_lo_rem.copy()
                        qh_full = W_hi_rem.copy()
                        ql_full[ext_rows_local[b], :] = ql_ext
                        qh_full[ext_rows_local[b], :] = qh_ext
                        q_lo_by_i[i] = ql_full
                        q_hi_by_i[i] = qh_full

                        cur_lo = best_lo[:, col_locs]
                        better_lo = ql_full < cur_lo
                        best_lo[:, col_locs] = np.where(better_lo, ql_full, cur_lo)

                        cur_hi = best_hi[:, col_locs]
                        # Tie-break safely even when all actions have `+inf` upper bound
                        better_hi = (qh_full < cur_hi) | (np.isinf(cur_hi) & np.isinf(qh_full) & (ql_full < cur_lo))
                        best_hi[:, col_locs] = np.where(better_hi, qh_full, cur_hi)
                        best_act[:, col_locs] = np.where(better_hi, i, best_act[:, col_locs])

                    if not dp_valid:
                        break

                    # Same-state dominated-branch aware attribution:
                    # Only score uncertainty on branches `i` that are NOT strictly dominated (`Q_lo_i < best_hi`)!
                    for i, b in enumerate(t_list):
                        if self.ep_wp_is_exact.get(b, False) or i not in cols_by_i:
                            continue
                        col_locs = cols_by_i[i]
                        ql_i = q_lo_by_i[i]
                        qh_i = q_hi_by_i[i]
                        inc_hi = best_hi[:, col_locs]
                        undominated = ql_i <= inc_hi + 1e-12
                        if np.any(undominated):
                            w_undom = np.where(np.isfinite(qh_i), qh_i - ql_i, 50.0)
                            # Weight root row 4x higher when `k == m` so root-relevant bottlenecks refine first
                            if k == m:
                                root_sc = float(np.max(w_undom[0, undominated[0, :]])) if np.any(undominated[0, :]) else 0.0
                                wp_slack_score[b] = max(wp_slack_score[b], 4.0 * root_sc + 0.25 * float(np.mean(w_undom[undominated])))
                            else:
                                wp_slack_score[b] = max(wp_slack_score[b], float(np.mean(w_undom[undominated])))

                    mk_arr = np.asarray(mk_list, dtype=np.int64)
                    F0_lo[:, mk_arr] = best_lo
                    F0_hi[:, mk_arr] = best_hi
                    act_idx[:, mk_arr] = best_act

            self.dp_ms += 1000.0 * (time.perf_counter() - t_d0)

            if dp_valid:
                lo_0 = float(F0_lo[0, full_mk] + phi_mask_sum[full_mk])
                hi_0 = float(F0_hi[0, full_mk] + phi_mask_sum[full_mk])
                if np.isfinite(lo_0) and np.isfinite(hi_0) and (hi_0 - lo_0 <= epsilon_tol):
                    # Populate actual per-action root Q-intervals (`v10 C04`) and validate `full_policy_enclosure`:
                    if m == 1:
                        root_q_bounds = {0: (lo_0, hi_0)}
                    else:
                        phi_tot = float(phi_mask_sum[full_mk])
                        root_q_bounds = {
                            i: (float(q_lo_by_i[i][0, 0] + phi_tot), float(q_hi_by_i[i][0, 0] + phi_tot))
                            for i in range(m)
                        }
                    cert_obj = Phase2DecisionCertificate(
                        certificate_mode="full_policy_enclosure",
                        certified=True,
                        epsilon_tol=epsilon_tol,
                        lower_bound_opt=lo_0,
                        incumbent_policy_upper_bound=hi_0,
                        root_action_q_bounds=root_q_bounds,
                        chosen_root_action=int(act_idx[0, full_mk]),
                        horizon_steps=m,
                    )
                    return {
                        "status": "epsilon_certified",
                        "certified": True,
                        "certificate_mode": cert_obj.certificate_mode,
                        "macro_value_bounds": [lo_0, hi_0],
                        "root_action_q_bounds": root_q_bounds,
                        "guaranteed_suboptimality_upper_bound": cert_obj.guaranteed_full_horizon_regret_bound,
                        "policy_action_idx": act_idx,
                        "refinement_steps": refinements,
                        "used_terminal_exact_dp": False,
                    }

            # Otherwise upgrade the single highest-impact non-exact waypoint in `t_list`
            non_exact = [b for b in t_list if not self.ep_wp_is_exact.get(b, False)]
            if not non_exact:
                break
            b_pick = max(non_exact, key=lambda x: wp_slack_score.get(x, 0.0))
            cur_nodes = np.flatnonzero(self.ep_eval_row_map[b_pick] >= 0)
            self._upgrade_waypoint_to_current_exact(b_pick, cur_nodes)
            refinements.append((int(b_pick), "REFRESH_EXACT_GAP"))

        # Terminal operational same-cache `plan_exact_subset_dp` closure (`A1` parity, charged inside fallback timer!)
        t_fb0 = time.perf_counter()
        res_ex = self.mt.plan_exact_subset_dp(s_arr, t_list)
        self.fallback_exact_ms += 1000.0 * (time.perf_counter() - t_fb0)
        res_ex["refinement_steps"] = refinements + [("ALL", "TERMINAL_SAME_CACHE_EXACT_DP")]
        res_ex["used_terminal_exact_dp"] = True
        return res_ex


# ==============================================================================
# Part M2.1-A: Unseen-Target Support Obstruction & Collar-Lift Diagnostic
# ==============================================================================
def _m21a_unseen_worker(args: Tuple[int, int, str]) -> dict:
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    enforce_single_thread_env(force=True)
    dim, ms, dim_lbl = args
    gn = 51 if dim == 2 else 21
    r_wp = 0.24 if dim == 2 else 0.34
    world = generate_benchmark_map(ms, dim=dim, regime="competing_corridor", with_drift=True)
    rng = np.random.default_rng(ms + 811 * dim)
    km = KrigingWorldModel(
        *sample_noisy_probes(world, n_probes=40 if dim == 2 else 56, seed=ms + 31 * dim, include_drift=True)
    )

    train_wps = _sample_nonoverlapping_balls(rng, 10, dim, r_wp, 1.18)
    unseen_wps = _sample_nonoverlapping_balls(rng, 6, dim, r_wp, 1.18, avoid=train_wps)
    pl_ref = SchurPortPlanner(world.spec, gn, km.predict_q, km.predict_b, unseen_wps, initial_sectors_per_wp="EXACT", lazy_init=True)
    A_csr = pl_ref.A0.tocsr()
    n_grid = len(pl_ref.pts)

    # Check historical fixed-source span obstruction `(A V)|_{Gamma_new} == 0`
    pl_tr = SchurPortPlanner(world.spec, gn, km.predict_q, km.predict_b, train_wps, initial_sectors_per_wp="EXACT", lazy_init=False)
    V_hist = np.hstack([pl_tr._wp_tree[j]["EXACT"][1] for j in range(len(train_wps))])
    AV_hist = A_csr @ V_hist
    hist_unseen_res = []
    for j in range(len(unseen_wps)):
        rg_u = pl_ref.wp_rings[j]
        # Any linear combination `V_hist @ c` has `(A V_hist c)[rg_u] == 0` because `rg_u` is disjoint from `train_wps`!
        max_av_on_new = float(np.max(np.abs(AV_hist[rg_u, :])))
        hist_unseen_res.append(1.0 - max_av_on_new)

    # Test principal killed-collar lifts across `hops = 2, 3, 4` (`H_base = 0`, ZERO historical oracle on unseen ring!)
    hop_stats = {}
    for hp in (2, 3, 4):
        neg_entries = 0
        z_gt1_rows = 0
        tot_rows = 0
        res_norms = []
        collar_sizes = []
        lift_ms_tot = 0.0
        for j in range(len(unseen_wps)):
            mk_u = pl_ref.wp_masks[j]
            rg_u = pl_ref.wp_rings[j]
            ext_u = np.flatnonzero(~mk_u)
            c_full = _extract_full_grid_collar_indices(A_csr, mk_u, rg_u, hops=hp)
            collar_sizes.append(int(len(c_full)))

            t_l0 = time.perf_counter()
            H_full = np.zeros((n_grid, len(rg_u)), dtype=float)
            H_full[rg_u, np.arange(len(rg_u))] = 1.0
            R_c = -(A_csr[c_full, :] @ H_full)
            A_cc = A_csr[c_full, :][:, c_full].tocsc()
            H_c = spla.splu(A_cc).solve(R_c)
            H_full[c_full, :] = H_c
            R_ext = -(A_csr @ H_full)[ext_u, :]
            lift_ms_tot += 1000.0 * (time.perf_counter() - t_l0)

            H_ext = H_full[ext_u, :]
            neg_entries += int(np.sum(H_ext < -1e-12))
            z_ext = np.sum(H_ext, axis=1)
            z_gt1_rows += int(np.sum(z_ext > 1.0 + 1e-12))
            tot_rows += len(ext_u)
            res_norms.append(float(np.max(np.abs(np.sum(R_ext, axis=1)))))

        hop_stats[f"hops_{hp}"] = {
            "mean_collar_nodes": float(np.mean(collar_sizes)),
            "collar_fraction_of_grid": float(np.mean(collar_sizes) / n_grid),
            "neg_H_entries": int(neg_entries),
            "Z_gt1_rows": int(z_gt1_rows),
            "strict_submarkov_valid": bool(neg_entries == 0 and z_gt1_rows == 0),
            "mean_rim_row_sum_residual_linf": float(np.mean(res_norms)),
            "total_collar_lift_ms_for_6_unseen": float(lift_ms_tot),
        }

    return {
        "dim_label": dim_lbl,
        "map_seed": ms,
        "n_unseen": len(unseen_wps),
        "historical_span_min_unseen_source_residual_linf": float(np.min(hist_unseen_res)),
        "collar_hop_diagnostics": hop_stats,
    }


# ==============================================================================
# Part M2.1-B: Continual Evolving-World 2x2 Factorial + 3D `31^3` Scale Rung
# ==============================================================================
ARMS_M21B = (
    "ExactRing-Rebuild",
    "Structure-Memory-Fresh-Exact",
    "F00_NoLift_PrimalUniform",
    "F10_CollarLift_PrimalUniform",
    "F01_NoLift_BilinearDWR",
    "F11_CollarLift_BilinearDWR",
)


def _build_ground_truth_epoch_tables_fast(
    pl_ref: SchurPortPlanner,
    needed_wps: Sequence[int],
    spotcheck_direct_killed_lu: bool = False,
) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
    """Computes exact killed-domain `(V_full, P_full)` tables for all `needed_wps` from a single `splu(A_ref)`
    via exact graph-separator elimination (`H_ext = U_ext @ inv(U_ring)`), optionally asserting machine-precision
    agreement (`<= 1e-11`) against per-waypoint killed `splu(A_{II})` (`_precompute_killed_epoch_tables`).
    """
    if not needed_wps:
        return {}
    lu_ep = pl_ref._ensure_current_lu()
    n_grid = len(pl_ref.pts)
    lam = pl_ref.spec.lam
    u_rings = np.unique(np.concatenate([pl_ref.wp_rings[dst] for dst in needed_wps]))
    RHS = np.zeros((n_grid, len(u_rings)), dtype=float)
    RHS[u_rings, np.arange(len(u_rings))] = 1.0
    U_all = lu_ep.solve(RHS)
    col_pos = {int(nid): idx for idx, nid in enumerate(u_rings)}

    out_vp: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
    for dst in needed_wps:
        mask_b = pl_ref.wp_masks[dst]
        ring_b = pl_ref.wp_rings[dst]
        ext_idx = np.flatnonzero(~mask_b)
        cols = [col_pos[int(nid)] for nid in ring_b]
        U_b = U_all[:, cols]
        H_ext = U_b[ext_idx, :] @ np.linalg.inv(U_b[ring_b, :])
        phi_b = float(pl_ref.waypoints[dst].phi)
        z_ext = np.sum(H_ext, axis=1)
        V_full = np.full(n_grid, phi_b, dtype=float)
        V_full[ext_idx] = phi_b - lam * np.log(z_ext)
        P_full = np.zeros((n_grid, len(ring_b)), dtype=float)
        P_full[ext_idx, :] = H_ext / z_ext[:, None]
        P_full[ring_b, np.arange(len(ring_b))] = 1.0
        out_vp[dst] = (V_full, P_full)

    if spotcheck_direct_killed_lu:
        first_dst = needed_wps[0]
        dir_vp = _precompute_killed_epoch_tables(pl_ref, [first_dst])
        v_err = float(np.max(np.abs(out_vp[first_dst][0] - dir_vp[first_dst][0])))
        p_err = float(np.max(np.abs(out_vp[first_dst][1] - dir_vp[first_dst][1])))
        if v_err > 1e-10 or p_err > 1e-11:
            raise AssertionError(f"Separator vs direct killed LU mismatch: v_err={v_err}, p_err={p_err}")
    # Release heavy 3D `SuperLU` factor immediately (`_eval_killed_macro_bellman_from_tables` only needs geometry)!
    pl_ref.lu0 = None
    pl_ref._lu_is_current = False
    return out_vp


def _run_m21b_stream_all_arms(
    spec: ProblemSpec,
    gn: int,
    catalog_wps: List[GoalBall],
    world_ops_sequence: List[Tuple[Callable, Callable]],
    tasks_by_epoch: List[List[Tuple[np.ndarray, Tuple[int, ...]]]],
    n_calib_epochs: int,
    collar_hops: int = 2,
    spotcheck_gt: bool = False,
) -> Dict[str, dict]:
    n_epochs = len(world_ops_sequence)

    # Precompute independent killed-operator exact Bellman tables OUTSIDE method timers!
    ref_tables: Dict[int, Tuple[SchurPortPlanner, Dict[int, Tuple[np.ndarray, np.ndarray]]]] = {}
    for ep in range(n_calib_epochs, n_epochs):
        qf, bf = world_ops_sequence[ep]
        pl_ref = SchurPortPlanner(spec, gn, qf, bf, catalog_wps, initial_sectors_per_wp="L1", lazy_init=True)
        needed_ep = sorted({w for _, sub in tasks_by_epoch[ep] for w in sub})
        ref_tables[ep] = (
            pl_ref,
            _build_ground_truth_epoch_tables_fast(
                pl_ref, needed_ep, spotcheck_direct_killed_lu=(spotcheck_gt and ep == n_calib_epochs)
            ),
        )

    out_arms: Dict[str, dict] = {}
    qf0, bf0 = world_ops_sequence[0]

    for arm in ARMS_M21B:
        t_from_zero = 0.0
        t_test_marginal = 0.0
        lus_in_test = 0
        bs_in_test = 0
        tasks_with_new_bs = 0
        tasks_with_refresh = 0
        tasks_with_terminal_fb = 0
        pending_audits = []

        if arm in ("ExactRing-Rebuild", "Structure-Memory-Fresh-Exact"):
            init_lv = "EXACT" if arm == "ExactRing-Rebuild" else "L1"
            t0 = time.perf_counter()
            pl = SchurPortPlanner(spec, gn, qf0, bf0, catalog_wps, initial_sectors_per_wp=init_lv, lazy_init=True)
            t_from_zero += 1000.0 * (time.perf_counter() - t0)

            for ep in range(n_epochs):
                qf, bf = world_ops_sequence[ep]
                lu_b0 = pl.lu_factorizations
                bs_ep0 = pl.total_lu_backsolves
                t_ep0 = time.perf_counter()
                if ep > 0:
                    mode_u = "scratch_rebuild" if arm == "ExactRing-Rebuild" else "structure_only_fresh_exact"
                    pl.update_world_with_residual_audit(qf, bf, mode=mode_u)
                mt = MacroTourPlanner(pl)
                ep_recs = []
                for s_xy, sub_ids in tasks_by_epoch[ep]:
                    bs_t0 = pl.total_lu_backsolves
                    if arm == "ExactRing-Rebuild":
                        res = mt.plan_exact_subset_dp(s_xy, sub_ids)
                    else:
                        res = mt.plan_subset_macro_policy(s_xy, sub_ids, epsilon_tol=0.25, max_refine_steps=12, use_incremental_dp=True)
                        if res.get("status") == "unresolved":
                            res = mt.plan_exact_subset_dp(s_xy, sub_ids)
                            if ep >= n_calib_epochs:
                                tasks_with_terminal_fb += 1
                    if ep >= n_calib_epochs:
                        if pl.total_lu_backsolves > bs_t0:
                            tasks_with_new_bs += 1
                        ep_recs.append((ep, s_xy, sub_ids, res))

                dt_ep = 1000.0 * (time.perf_counter() - t_ep0)
                t_from_zero += dt_ep
                if ep >= n_calib_epochs:
                    t_test_marginal += dt_ep
                    lus_in_test += int(pl.lu_factorizations - lu_b0)
                    bs_in_test += int(pl.total_lu_backsolves - bs_ep0)
                    pending_audits.extend(ep_recs)

            total_lus = int(pl.lu_factorizations)
            total_bs = int(pl.total_lu_backsolves)
            stage_ms = {
                "ref_cache_build_ms": 0.0,
                "collar_lift_ms": 0.0,
                "dwr_witness_and_audit_ms": 0.0,
                "dp_ms": 0.0,
                "fallback_exact_ms": 0.0,
            }
        else:
            use_lift = arm in ("F10_CollarLift_PrimalUniform", "F11_CollarLift_BilinearDWR")
            use_dwr = arm in ("F01_NoLift_BilinearDWR", "F11_CollarLift_BilinearDWR")
            t0 = time.perf_counter()
            kd_pl = KilledCollarDWRPlanner(
                spec, gn, qf0, bf0, catalog_wps,
                use_collar_lift=use_lift, use_bilinear_dwr=use_dwr, collar_hops=collar_hops,
            )
            t_from_zero += 1000.0 * (time.perf_counter() - t0)

            for ep in range(n_epochs):
                qf, bf = world_ops_sequence[ep]
                lu_b0 = kd_pl.pl.lu_factorizations
                bs_ep0 = kd_pl.pl.total_lu_backsolves
                t_ep0 = time.perf_counter()

                if ep < n_calib_epochs:
                    if ep > 0:
                        kd_pl.pl.update_world_with_residual_audit(qf, bf, mode="scratch_rebuild")
                    for s_xy, sub_ids in tasks_by_epoch[ep]:
                        kd_pl.mt.plan_exact_subset_dp(s_xy, sub_ids)
                    if ep == n_calib_epochs - 1:
                        kd_pl.freeze_reference_anchor_from_current_epoch()
                else:
                    kd_pl.begin_test_epoch(qf, bf, tasks_by_epoch[ep])
                    ep_recs = []
                    for s_xy, sub_ids in tasks_by_epoch[ep]:
                        bs_t0 = kd_pl.pl.total_lu_backsolves
                        res = kd_pl.plan_certified_full_policy_task(s_xy, sub_ids, epsilon_tol=0.25)
                        if kd_pl.pl.total_lu_backsolves > bs_t0:
                            tasks_with_new_bs += 1
                        refs = res.get("refinement_steps", []) or []
                        if any(str(lbl).startswith("REFRESH_") for _, lbl in refs):
                            tasks_with_refresh += 1
                        if bool(res.get("used_terminal_exact_dp", False)):
                            tasks_with_terminal_fb += 1
                        ep_recs.append((ep, s_xy, sub_ids, res))

                dt_ep = 1000.0 * (time.perf_counter() - t_ep0)
                t_from_zero += dt_ep
                if ep >= n_calib_epochs:
                    t_test_marginal += dt_ep
                    lus_in_test += int(kd_pl.pl.lu_factorizations - lu_b0)
                    bs_in_test += int(kd_pl.pl.total_lu_backsolves - bs_ep0)
                    pending_audits.extend(ep_recs)

            total_lus = int(kd_pl.pl.lu_factorizations)
            total_bs = int(kd_pl.pl.total_lu_backsolves)
            stage_ms = {
                "ref_cache_build_ms": kd_pl.ref_cache_build_ms,
                "collar_lift_ms": kd_pl.collar_lift_ms,
                "dwr_witness_and_audit_ms": kd_pl.dwr_witness_and_audit_ms,
                "dp_ms": kd_pl.dp_ms,
                "fallback_exact_ms": kd_pl.fallback_exact_ms,
            }

        # Independent ground-truth killed-operator Bellman audit OUTSIDE method timers!
        n_test = 0
        n_cert = 0
        viols = 0
        regrets = []
        widths = []
        for ep, s_xy, sub_ids, res_rec in pending_audits:
            n_test += 1
            if bool(res_rec.get("certified")):
                n_cert += 1
            bounds_c = res_rec.get("macro_value_bounds")
            pol_idx = res_rec.get("policy_action_idx")
            if bounds_c is None or pol_idx is None:
                viols += 1
                continue
            lo_c, hi_c = float(bounds_c[0]), float(bounds_c[1])
            widths.append(hi_c - lo_c)
            pl_r, kvp = ref_tables[ep]
            opt_c, pol_c = _eval_killed_macro_bellman_from_tables(pl_r, kvp, s_xy, sub_ids, pol_idx)
            if not ((lo_c - 1e-9 <= opt_c <= hi_c + 1e-9) and (opt_c - 1e-9 <= pol_c <= hi_c + 1e-9)):
                viols += 1
            regrets.append(float(max(0.0, pol_c - opt_c)))

        out_arms[arm] = {
            "from_zero_lifecycle_ms": t_from_zero,
            "test_epochs_marginal_ms": t_test_marginal,
            "stage_breakdown_ms": stage_ms,
            "total_lu_factorizations": total_lus,
            "test_epochs_lu_factorizations": lus_in_test,
            "total_lu_backsolves": total_bs,
            "test_epochs_lu_backsolves": bs_in_test,
            "tasks_with_new_backsolves": int(tasks_with_new_bs),
            "tasks_with_refresh": int(tasks_with_refresh),
            "tasks_with_terminal_exact_fallback": int(tasks_with_terminal_fb),
            "n_test_tasks": int(n_test),
            "n_certified": int(n_cert),
            "bound_violations": int(viols),
            "mean_certified_width": float(np.mean(widths)) if widths else 0.0,
            "mean_exact_bellman_regret": float(np.mean(regrets)) if regrets else 0.0,
            "max_exact_bellman_regret": float(np.max(regrets)) if regrets else 0.0,
        }
        gc.collect()

    return out_arms


def _build_gp_and_param_streams(ms: int, dim: int) -> Tuple[ProblemSpec, List[GoalBall], Tuple, Tuple]:
    r_wp = 0.25 if dim == 2 else 0.34
    world = generate_benchmark_map(ms, dim=dim, regime="narrow_barrier", with_drift=True)
    rng = np.random.default_rng(ms + 505 * dim)
    catalog_wps = _sample_nonoverlapping_balls(rng, 10, dim, r_wp, 1.18)

    # 1. Realistic unstructured `+12`-probe online GP refits (`ep=0` calib + `5` test updates)
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
    for _ in range(6):
        ep_t = []
        for _ in range(6):
            sub = tuple(sorted(rng.choice(len(catalog_wps), size=4, replace=False).tolist()))
            s_xy = rng.uniform(-1.18, 1.18, size=dim)
            ep_t.append((s_xy, sub))
        tasks_gp.append(ep_t)

    # 2. Low-dimensional parametric hazard modulation stream (`3` calib epochs -> `5` test epochs)
    km_base = KrigingWorldModel(*sample_noisy_probes(world, n_probes=44 if dim == 2 else 60, seed=ms + 99 * dim, include_drift=True))
    c_mod1 = np.zeros(dim, dtype=float); c_mod1[0] = -0.35
    c_mod2 = np.zeros(dim, dtype=float); c_mod2[0] = 0.35
    param_amps = [
        (0.00, 0.00),
        (0.06, 0.00),
        (0.00, 0.06),
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
    for _ in range(len(param_amps)):
        ep_t = []
        for _ in range(6):
            sub = tuple(sorted(rng.choice(len(catalog_wps), size=4, replace=False).tolist()))
            s_xy = rng.uniform(-1.18, 1.18, size=dim)
            ep_t.append((s_xy, sub))
        tasks_param.append(ep_t)

    return world.spec, catalog_wps, (gp_ops_seq, tasks_gp, 1), (param_ops_seq, tasks_param, 3)


def _m21b_dev_parity_worker(ms: int) -> dict:
    """Runs `Exp 5B` parity dev cohort (`30300..30311`) on `2D 51^2` and `3D 21^3`."""
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    enforce_single_thread_env(force=True)
    out = {}
    for dim, gn, lbl in ((2, 51, "2D-51sq"), (3, 21, "3D-21cubed")):
        spec, wps, gp_pack, par_pack = _build_gp_and_param_streams(ms, dim)
        out[f"{lbl}_RealisticGPStream"] = _run_m21b_stream_all_arms(
            spec, gn, wps, gp_pack[0], gp_pack[1], n_calib_epochs=gp_pack[2], collar_hops=2, spotcheck_gt=(ms == 30300)
        )
        out[f"{lbl}_LowDimParametricStream"] = _run_m21b_stream_all_arms(
            spec, gn, wps, par_pack[0], par_pack[1], n_calib_epochs=par_pack[2], collar_hops=2
        )
    return {"map_seed": ms, "streams": out}


def _m21b_confirm_3d_scale_worker(ms: int) -> dict:
    """Runs fresh confirmation + 3D scale-rung cohort (`40300..40307`) on `3D 21^3` and `3D 27^3` (`N=19,683`)."""
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    enforce_single_thread_env(force=True)
    spec, wps, gp_pack, par_pack = _build_gp_and_param_streams(ms, dim=3)
    out = {}
    for gn, lbl in ((21, "3D-21cubed_FreshConfirm"), (27, "3D-27cubed_FreshConfirm")):
        hops_use = 2
        out[f"{lbl}_RealisticGPStream"] = _run_m21b_stream_all_arms(
            spec, gn, wps, gp_pack[0], gp_pack[1], n_calib_epochs=gp_pack[2], collar_hops=hops_use
        )
        out[f"{lbl}_LowDimParametricStream"] = _run_m21b_stream_all_arms(
            spec, gn, wps, par_pack[0], par_pack[1], n_calib_epochs=par_pack[2], collar_hops=hops_use
        )
        gc.collect()
    return {"map_seed": ms, "streams": out}


def _summarize_m21b_cohort(rows: List[dict]) -> dict:
    stream_keys = list(rows[0]["streams"].keys())
    summary = {}
    for sk in stream_keys:
        ex_fz = np.array([r["streams"][sk]["ExactRing-Rebuild"]["from_zero_lifecycle_ms"] for r in rows])
        st_fz = np.array([r["streams"][sk]["Structure-Memory-Fresh-Exact"]["from_zero_lifecycle_ms"] for r in rows])
        ex_mg = np.array([r["streams"][sk]["ExactRing-Rebuild"]["test_epochs_marginal_ms"] for r in rows])
        st_mg = np.array([r["streams"][sk]["Structure-Memory-Fresh-Exact"]["test_epochs_marginal_ms"] for r in rows])
        best_cl_fz_name = "ExactRing-Rebuild" if np.mean(ex_fz) <= np.mean(st_fz) else "Structure-Memory-Fresh-Exact"
        best_cl_mg_name = "ExactRing-Rebuild" if np.mean(ex_mg) <= np.mean(st_mg) else "Structure-Memory-Fresh-Exact"
        best_cl_fz_vec = ex_fz if best_cl_fz_name == "ExactRing-Rebuild" else st_fz
        best_cl_mg_vec = ex_mg if best_cl_mg_name == "ExactRing-Rebuild" else st_mg

        arms_dict = {}
        for arm in ARMS_M21B:
            fz = np.array([r["streams"][sk][arm]["from_zero_lifecycle_ms"] for r in rows])
            mg = np.array([r["streams"][sk][arm]["test_epochs_marginal_ms"] for r in rows])
            n_tot = sum(r["streams"][sk][arm]["n_test_tasks"] for r in rows)
            n_cert = sum(r["streams"][sk][arm]["n_certified"] for r in rows)
            n_viols = sum(r["streams"][sk][arm]["bound_violations"] for r in rows)

            st_keys = ("ref_cache_build_ms", "collar_lift_ms", "dwr_witness_and_audit_ms", "dp_ms", "fallback_exact_ms")
            stage_mean = {
                k: float(np.mean([r["streams"][sk][arm]["stage_breakdown_ms"][k] for r in rows])) for k in st_keys
            }

            arms_dict[arm] = {
                "mean_from_zero_lifecycle_ms": float(np.mean(fz)),
                "mean_test_epochs_marginal_ms": float(np.mean(mg)),
                "stage_breakdown_mean_ms": stage_mean,
                "mean_total_lu_factorizations": float(np.mean([r["streams"][sk][arm]["total_lu_factorizations"] for r in rows])),
                "mean_test_epochs_lu_factorizations": float(np.mean([r["streams"][sk][arm]["test_epochs_lu_factorizations"] for r in rows])),
                "mean_test_epochs_lu_backsolves": float(np.mean([r["streams"][sk][arm]["test_epochs_lu_backsolves"] for r in rows])),
                "total_tasks_with_new_backsolves": int(sum(r["streams"][sk][arm]["tasks_with_new_backsolves"] for r in rows)),
                "total_tasks_with_refresh": int(sum(r["streams"][sk][arm]["tasks_with_refresh"] for r in rows)),
                "total_tasks_with_terminal_exact_fallback": int(sum(r["streams"][sk][arm]["tasks_with_terminal_exact_fallback"] for r in rows)),
                "total_test_tasks": int(n_tot),
                "total_certified_tasks": int(n_cert),
                "complete_certification_rate": float(n_cert / max(n_tot, 1)),
                "total_bound_violations": int(n_viols),
                "mean_certified_width": float(np.mean([r["streams"][sk][arm]["mean_certified_width"] for r in rows])),
                "mean_exact_bellman_regret": float(np.mean([r["streams"][sk][arm]["mean_exact_bellman_regret"] for r in rows])),
                "max_exact_bellman_regret": float(np.max([r["streams"][sk][arm]["max_exact_bellman_regret"] for r in rows])),
                "rel_savings_from_zero_vs_best_classical_pct": float(100.0 * (1.0 - np.mean(fz) / np.mean(best_cl_fz_vec))),
                "rel_savings_test_marginal_vs_best_classical_pct": float(100.0 * (1.0 - np.mean(mg) / np.mean(best_cl_mg_vec))),
                "speedup_from_zero_vs_best_classical_x": float(np.mean(best_cl_fz_vec) / max(float(np.mean(fz)), 1e-12)),
                "speedup_test_marginal_vs_best_classical_x": float(np.mean(best_cl_mg_vec) / max(float(np.mean(mg)), 1e-12)),
                "paired_from_zero_minus_best_classical": paired_stats(fz - best_cl_fz_vec),
                "paired_test_marginal_minus_best_classical": paired_stats(mg - best_cl_mg_vec),
            }

        # Explicit 2x2 factorial main effects & interaction on test-epoch marginal ms (`F00, F10, F01, F11`)
        v00 = np.array([r["streams"][sk]["F00_NoLift_PrimalUniform"]["test_epochs_marginal_ms"] for r in rows])
        v10 = np.array([r["streams"][sk]["F10_CollarLift_PrimalUniform"]["test_epochs_marginal_ms"] for r in rows])
        v01 = np.array([r["streams"][sk]["F01_NoLift_BilinearDWR"]["test_epochs_marginal_ms"] for r in rows])
        v11 = np.array([r["streams"][sk]["F11_CollarLift_BilinearDWR"]["test_epochs_marginal_ms"] for r in rows])
        main_lift = 0.5 * ((v10 - v00) + (v11 - v01))
        main_dwr = 0.5 * ((v01 - v00) + (v11 - v10))
        inter_2x2 = (v11 - v01) - (v10 - v00)

        summary[sk] = {
            "n_maps": len(rows),
            "best_classical_from_zero_arm": best_cl_fz_name,
            "best_classical_test_marginal_arm": best_cl_mg_name,
            "arms": arms_dict,
            "factorial_2x2_test_marginal_ms_effects": {
                "main_effect_collar_lift_ms": paired_stats(main_lift),
                "main_effect_bilinear_dwr_ms": paired_stats(main_dwr),
                "interaction_lift_x_dwr_ms": paired_stats(inter_2x2),
            },
        }
    return summary


def plot_m21_summary(res: dict, out_png: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14.2, 9.6), dpi=160)

    # Panel A: M2.1-A Unseen-target collar-lift rim residual decay (`0%` Z>1 & `0%` H<0 strict sub-Markov)
    ax = axes[0, 0]
    a_sum = res["part_m21a_unseen_collar_lift"]["summary_by_dim"]
    hops = [2, 3, 4]
    for dlbl, marker, col in [("2D-51sq", "o", "#1f77b4"), ("3D-21cubed", "s", "#d62728")]:
        ys = [a_sum[dlbl]["by_hops"][f"hops_{h}"]["mean_rim_row_sum_residual_linf"] for h in hops]
        ax.plot(hops, ys, marker=marker, lw=2.2, color=col, label=f"{dlbl} Killed-Collar Lift (0% Z>1, 0% H<0)")
    ax.axhline(1.0, ls="--", lw=1.6, color="#444444", label="Historical Global Span Obstruction (>= 1.0)")
    ax.set_yscale("log")
    ax.set_xticks(hops)
    ax.set_xlabel("Killed-Domain Principal Collar Hops k")
    ax.set_ylabel("Mean Unseen-Target Rim Residual ||R 1||_inf")
    ax.set_title("A. M2.1-A: Unseen-Target Source Singularity Removal")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8.5, loc="best")

    # Panel B: Dev Cohort (`3D-21cubed` GP vs Param) 2x2 Test-Epoch Marginal Wall-Clock ms
    ax = axes[0, 1]
    dev_s = res["part_m21b_dev_parity_12maps"]["summary"]
    arms_plot = [
        ("ExactRing-Rebuild", "ExactRing"),
        ("Structure-Memory-Fresh-Exact", "StructMem"),
        ("F00_NoLift_PrimalUniform", "F00\nPrimal"),
        ("F10_CollarLift_PrimalUniform", "F10\n+Lift"),
        ("F01_NoLift_BilinearDWR", "F01\n+DWR"),
        ("F11_CollarLift_BilinearDWR", "F11\nLift+DWR"),
    ]
    x = np.arange(len(arms_plot))
    w = 0.36
    gp_21 = [dev_s["3D-21cubed_RealisticGPStream"]["arms"][k]["mean_test_epochs_marginal_ms"] for k, _ in arms_plot]
    pa_21 = [dev_s["3D-21cubed_LowDimParametricStream"]["arms"][k]["mean_test_epochs_marginal_ms"] for k, _ in arms_plot]
    ax.bar(x - w / 2, gp_21, width=w, color="#2b5c8f", label="3D 21^3 Realistic GP Stream")
    ax.bar(x + w / 2, pa_21, width=w, color="#e07b39", label="3D 21^3 Parametric Stream")
    ax.set_xticks(x)
    ax.set_xticklabels([lbl for _, lbl in arms_plot], fontsize=8.5)
    ax.set_ylabel("Mean Test-Epochs Marginal Time (ms / map)")
    ax.set_title("B. Dev 12-Map (Exp 5B Parity, eps=0.25 Full-Policy, 0 Viols)")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8.5)

    # Panel C: Fresh Confirmation Scale Crossover (`2D 51^2` -> `3D 21^3` -> `3D 27^3`) From-Zero Lifecycle ms
    ax = axes[1, 0]
    cf_s = res["part_m21b_fresh_confirm_3d_scale_8maps"]["summary"]
    regimes_c = [
        ("2D 51^2\nGP (Dev)", dev_s["2D-51sq_RealisticGPStream"]),
        ("2D 51^2\nParam (Dev)", dev_s["2D-51sq_LowDimParametricStream"]),
        ("3D 21^3\nGP (Conf)", cf_s["3D-21cubed_FreshConfirm_RealisticGPStream"]),
        ("3D 21^3\nParam (Conf)", cf_s["3D-21cubed_FreshConfirm_LowDimParametricStream"]),
        ("3D 27^3\nGP (Conf)", cf_s["3D-27cubed_FreshConfirm_RealisticGPStream"]),
        ("3D 27^3\nParam (Conf)", cf_s["3D-27cubed_FreshConfirm_LowDimParametricStream"]),
    ]
    xc = np.arange(len(regimes_c))
    wc = 0.26
    best_cl_vals = [
        min(d["arms"]["ExactRing-Rebuild"]["mean_from_zero_lifecycle_ms"],
            d["arms"]["Structure-Memory-Fresh-Exact"]["mean_from_zero_lifecycle_ms"])
        for _, d in regimes_c
    ]
    f01_vals = [d["arms"]["F01_NoLift_BilinearDWR"]["mean_from_zero_lifecycle_ms"] for _, d in regimes_c]
    f11_vals = [d["arms"]["F11_CollarLift_BilinearDWR"]["mean_from_zero_lifecycle_ms"] for _, d in regimes_c]
    ax.bar(xc - wc, best_cl_vals, width=wc, color="#555555", label="Best Classical (ExactRing / StructMem)")
    ax.bar(xc, f01_vals, width=wc, color="#4daf4a", label="F01: Bilinear DWR + Q-Prune")
    ax.bar(xc + wc, f11_vals, width=wc, color="#984ea3", label="F11: CollarLift + Bilinear DWR")
    ax.set_yscale("log")
    ax.set_xticks(xc)
    ax.set_xticklabels([lbl for lbl, _ in regimes_c], fontsize=8.0)
    ax.set_ylabel("From-Zero Full Planner Lifecycle (ms, log scale)")
    ax.set_title("C. Full-Lifecycle Crossover Across Grid Scale (All Costs Charged)")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8.0)

    # Panel D: Test-Epoch LU Factorizations (`5.0` full vs DWR selective refactorization)
    ax = axes[1, 1]
    lu_cl = [
        d["arms"][d["best_classical_from_zero_arm"]]["mean_test_epochs_lu_factorizations"] for _, d in regimes_c
    ]
    lu_f00 = [d["arms"]["F00_NoLift_PrimalUniform"]["mean_test_epochs_lu_factorizations"] for _, d in regimes_c]
    lu_f01 = [d["arms"]["F01_NoLift_BilinearDWR"]["mean_test_epochs_lu_factorizations"] for _, d in regimes_c]
    lu_f11 = [d["arms"]["F11_CollarLift_BilinearDWR"]["mean_test_epochs_lu_factorizations"] for _, d in regimes_c]
    wd = 0.20
    ax.bar(xc - 1.5 * wd, lu_cl, width=wd, color="#555555", label="Best Classical")
    ax.bar(xc - 0.5 * wd, lu_f00, width=wd, color="#d95f02", label="F00 Primal Uniform")
    ax.bar(xc + 0.5 * wd, lu_f01, width=wd, color="#4daf4a", label="F01 Bilinear DWR")
    ax.bar(xc + 1.5 * wd, lu_f11, width=wd, color="#984ea3", label="F11 CollarLift + DWR")
    ax.set_xticks(xc)
    ax.set_xticklabels([lbl for lbl, _ in regimes_c], fontsize=8.0)
    ax.set_ylim(0, 5.6)
    ax.set_ylabel("Mean Test-Epoch Global LU Factorizations (of 5)")
    ax.set_title("D. Global Test-Epoch LU Refactorizations Avoided")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8.0)

    fig.suptitle(
        "Phase-II M2.1 Feasibility Ablation: Killed-Collar Lift x Verified Bilinear DWR (Full-Policy eps=0.25, 100% Certified, 0 Viols)",
        fontsize=11.5, fontweight="bold", y=0.99,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    fig.savefig(out_png)
    plt.close(fig)


def run_m21_ablation_suite(max_workers: int = 8) -> dict:
    verify_phase1_readonly_freeze()
    enforce_single_thread_env(force=True)
    t_start = time.perf_counter()

    # 1. Part M2.1-A (`8` 2D maps + `8` 3D maps)
    tasks_a = [(2, 40100 + i, "2D-51sq") for i in range(8)] + [(3, 40200 + i, "3D-21cubed") for i in range(8)]
    rows_a = run_map_parallel(_m21a_unseen_worker, tasks_a, max_workers=max_workers)
    sum_a = {}
    for dlbl in ("2D-51sq", "3D-21cubed"):
        sub = [r for r in rows_a if r["dim_label"] == dlbl]
        by_hops = {}
        for hp in (2, 3, 4):
            hk = f"hops_{hp}"
            by_hops[hk] = {
                "mean_collar_nodes": float(np.mean([r["collar_hop_diagnostics"][hk]["mean_collar_nodes"] for r in sub])),
                "collar_fraction_of_grid": float(np.mean([r["collar_hop_diagnostics"][hk]["collar_fraction_of_grid"] for r in sub])),
                "total_neg_H_entries": int(sum(r["collar_hop_diagnostics"][hk]["neg_H_entries"] for r in sub)),
                "total_Z_gt1_rows": int(sum(r["collar_hop_diagnostics"][hk]["Z_gt1_rows"] for r in sub)),
                "all_strict_submarkov_valid": bool(all(r["collar_hop_diagnostics"][hk]["strict_submarkov_valid"] for r in sub)),
                "mean_rim_row_sum_residual_linf": float(np.mean([r["collar_hop_diagnostics"][hk]["mean_rim_row_sum_residual_linf"] for r in sub])),
                "mean_collar_lift_ms_for_6_unseen": float(np.mean([r["collar_hop_diagnostics"][hk]["total_collar_lift_ms_for_6_unseen"] for r in sub])),
            }
        sum_a[dlbl] = {
            "n_maps": len(sub),
            "historical_span_min_unseen_source_residual_linf": float(min(r["historical_span_min_unseen_source_residual_linf"] for r in sub)),
            "by_hops": by_hops,
        }

    # 2. Part M2.1-B Dev Cohort (`30300..30311`, 12 maps, `Exp 5B` parity)
    dev_seeds = list(range(30300, 30312))
    rows_dev = run_map_parallel(_m21b_dev_parity_worker, dev_seeds, max_workers=max_workers)
    sum_dev = _summarize_m21b_cohort(rows_dev)

    # 3. Part M2.1-B Fresh Confirmation + 3D Scale Rung (`40300..40307`, 8 untouched maps, `3D 21^3` & `3D 27^3`)
    conf_seeds = list(range(40300, 40308))
    rows_conf = run_map_parallel(_m21b_confirm_3d_scale_worker, conf_seeds, max_workers=max_workers)
    sum_conf = _summarize_m21b_cohort(rows_conf)

    # 4. Standalone single-worker 3D `splu` fill-in & factorization scaling ladder (`21^3 -> 25^3 -> 27^3 -> 31^3`)
    spec_prof = generate_benchmark_map(40300, dim=3).spec
    splu_ladder = {}
    for gn_p in (21, 25, 27, 31):
        n_p = gn_p ** 3
        A_p, _ = build_upwind_mmatrix_desirability_operator(
            spec_prof, gn_p, np.full(n_p, 0.10, dtype=float), np.full((n_p, 3), 0.20, dtype=float)
        )
        t_p0 = time.perf_counter()
        lu_p = spla.splu(A_p)
        dt_p = 1000.0 * (time.perf_counter() - t_p0)
        nnz_lu = int(lu_p.L.nnz + lu_p.U.nnz)
        est_mb = float(nnz_lu * 12.0 / (1024.0 ** 2))
        del lu_p, A_p
        gc.collect()
        splu_ladder[f"3D_{gn_p}cubed"] = {
            "grid_n": gn_p,
            "n_dof": n_p,
            "single_splu_ms": dt_p,
            "lu_nnz": nnz_lu,
            "estimated_factor_MiB": est_mb,
        }

    # Verify global zero violations & 100% complete certification across ALL cohorts & arms
    total_viols = 0
    total_tasks_checked = 0
    total_certified = 0
    for s_block in (sum_dev, sum_conf):
        for sk, sd in s_block.items():
            for arm_d in sd["arms"].values():
                total_viols += arm_d["total_bound_violations"]
                total_tasks_checked += arm_d["total_test_tasks"]
                total_certified += arm_d["total_certified_tasks"]

    elapsed_s = time.perf_counter() - t_start
    return {
        "milestone": "M2.1_Controlled_2x2_CollarLift_x_BilinearDWR_Feasibility_Ablation",
        "quality_contract": {
            "certificate_mode": "full_policy_enclosure",
            "epsilon_tol": 0.25,
            "complete_certification_via_operational_exact_fallback": True,
            "total_test_tasks_across_all_arms_and_cohorts": int(total_tasks_checked),
            "total_certified_tasks": int(total_certified),
            "total_bound_violations": int(total_viols),
        },
        "runtime_metadata": collect_runtime_metadata(max_workers=max_workers),
        "phase2_manifest": compute_phase2_manifest(),
        "wall_clock_suite_seconds": float(elapsed_s),
        "part_m21a_unseen_collar_lift": {
            "summary_by_dim": sum_a,
            "per_map_records": rows_a,
        },
        "part_m21b_dev_parity_12maps": {
            "seeds": dev_seeds,
            "summary": sum_dev,
            "per_map_records": rows_dev,
        },
        "part_m21b_fresh_confirm_3d_scale_8maps": {
            "seeds": conf_seeds,
            "summary": sum_conf,
            "per_map_records": rows_conf,
        },
        "part_m21c_3d_splu_scaling_ladder": splu_ladder,
    }


def main() -> None:
    pkg_dir = Path(__file__).resolve().parent
    res = run_m21_ablation_suite(max_workers=8)
    out_json = pkg_dir / "m21_ablation_results.json"
    out_png = pkg_dir / "m21_ablation_summary.png"
    out_json.write_text(json.dumps(res, indent=2), encoding="utf-8")
    plot_m21_summary(res, out_png)
    qc = res["quality_contract"]
    print(
        f"[M2.1] DONE in {res['wall_clock_suite_seconds']:.1f}s | "
        f"certified={qc['total_certified_tasks']}/{qc['total_test_tasks_across_all_arms_and_cohorts']} | "
        f"bound_violations={qc['total_bound_violations']} | "
        f"frozen_phase1_intact={res['phase2_manifest']['frozen_phase1_verified_intact']}"
    )
    if qc["total_bound_violations"] != 0 or qc["total_certified_tasks"] != qc["total_test_tasks_across_all_arms_and_cohorts"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
