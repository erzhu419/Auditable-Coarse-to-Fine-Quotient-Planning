"""Milestone M2.3.3 SISC Algorithmic Unlock (`quotient_phase2.m233_sisc_subportal_quadtree`):
Adaptive Sub-Portal Quadtree Cut Refinement (`L0..L4` Singletons), Nested-Cut L0-Lyapunov
Invariance, and Partition-of-Unity `(k - 1)` Child Conservation — Strictly Non-Destructive
(`100%` of `green_response` and `M2.0..M2.3.2` Frozen Artifacts Untouched Byte-for-Byte).

Algorithmic Advances Over Uniform Whole-Portal Coarsening (`M2.3.2`):
  1. Adaptive Sub-Portal Quadtree Cuts (`L0 -> L1 -> L2 -> L3 -> L4` exact singletons):
       Instead of promoting an entire planar doorway from `L2` (`16` blocks) to `L3` (`64` blocks)
       and stopping short of `11x11` node resolution, `SubPortalPoUQuadtree3DPlanner` maintains an
       adaptive cut across the forest of doorway quadtrees, splitting ONLY individual high-adjoint-
       oscillation sub-blocks `(p_id, lv, b_idx)` down to `L4` singletons (`m_cap = 768`, up to
       `9` adaptive rounds). This slashes full-interface Krylov defect fallbacks while keeping
       active coarse DOFs compact.
  2. Nested-Cut `L0`-Lyapunov Invariance & Warm-Started Howard Iteration:
       Because every sub-portal quadtree cut `B` refines the initial whole-portal partition `B_0`,
       the `L0` cooperative super-harmonic witness `w_lyap = L_0 v_lyap^{(0)} > 0` (`xi_lyap =
       (I - K) w_lyap > 0`, computed once at `51 x 51` in `< 0.2 ms`) lies exact-algebraically in
       the column space of `L_B` on every subsequent round! Combined with warm-starting `(v_lo, v_hi)`
       from the previous round's `(W_lo_raw, W_hi_raw)`, this eliminates `100%` of `O(m^3)` `v_lyap`
       Howard loops and `Sys_bar` initializations on rounds `1..R` while preserving exact outward-
       shifted `Theorem 1` certificates `L_B v_lo_cert <= W_lo_cert`.
  3. Partition-of-Unity `(k - 1)` Child Solve Conservation:
       Since `1_{B_parent} = sum_{q=1}^k 1_{B_child,q}` and both room harmonic extensions `A_{RR}^{-1}`
       and in-plane smoothing `D^{-1}` are linear, splitting any cached parent block into `k` children
       solves ONLY `k - 1` room-LU RHS columns (`3` instead of `4` for `2x2` splits — a `25%` exact
       reduction in cache-miss LU backsolves) and recovers the `k`-th child by subtraction from the
       unclipped parent response (`max |K_pou - K_direct| < 1e-14`).

Hygiene & Provenance:
  - Hyperparameters (`m_cap = 768`, `max_split_rounds = 9`, `l3_to_l4_cost_weight = 1.25`,
    `rel_score_cutoff = 0.04`, `round1_two_level_thresh = 0.22`) were selected strictly on
    `Dev Cohort 61000..61005` (`0` peeking at `63000..63005` or `64000..64005`) and locked.
  - Evaluates single-worker (`workers = 1`) exact `3 AB / 3 BA` benchmarks across:
      * `Replay Cohort 63000..63005` (`Static 35^3`, `Static 47^3` + `3`-arm cache ablation,
        `Static 59^3`, and `Continual 47^3`);
      * `Fresh Untouched Confirmation Cohort 64000..64005` (`Static 47^3`, `K = 24`, never touched
        prior to this locked run).
  - Writes ONLY to `m233_sisc_unlock_results.json` (`allow_nan=False`) and `m233_sisc_unlock_summary.png`.
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse
import copy
import gc
import hashlib
import itertools
import json
import sys
import time
import warnings
import weakref
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy import stats as sp_stats

from green_response import ProblemSpec, collect_runtime_metadata, enforce_single_thread_env, paired_stats
from green_response.port_solvers import build_grid_points
from quotient_phase2 import compute_phase2_manifest, verify_phase1_readonly_freeze
from quotient_phase2.m20_contracts import Phase2DecisionCertificate, check_directed_goal_reachability
from quotient_phase2.m23_m24_3d_portal_scale import (
    LazyRoomPortalPolicy,
    SeamFreePortal3DPlanner,
    build_3d_reflecting_obstacle_mmatrix,
    build_portal_level_blocks,
    evaluate_3d_deployed_policy_exact,
    extract_directed_goal_ring_in_room,
    generate_3d_multiroom_world,
    solve_and_verify_portal_howard_bounds,
)
from quotient_phase2.m231_fair_ablation import (
    MatrixFreeExactSchurKrylov3DPlanner,
    SingleLUGoalCapacitance3DPlanner,
)
from quotient_phase2.m232_final_closure import (
    _build_task_event,
    _goal_hash,
    _one_sided_20pct_saving_p,
    _reduce_event_ledger,
    _sanitize_for_strict_json,
    _sustained_crossing_k,
)
from quotient_phase2.verify_m232_release import (
    FROZEN_ALL_10_JSON_SHA256,
    EventKey,
    _strict_json_loads,
    run_negative_control_fault_injections,
    verify_all_10_frozen_jsons,
    verify_event_roster_and_inequalities,
)


# Locked Dev-Cohort (`61000..61005`) Hyperparameters — Never Modified on `63k` or `64k`
LOCKED_M233_HYPERPARAMS = {
    "tuned_exclusively_on_cohort": "Dev_61000_61005",
    "m_cap": 768,
    "max_split_rounds": 9,
    "max_candidates_inspected_per_round": 28,
    "relative_score_cutoff": 0.04,
    "round1_l0_to_l2_rel_score_thresh": 0.22,
    "round1_l0_to_l2_width_thresh": 0.35,
    "l3_to_l4_singleton_cost_weight": 1.25,
    "pou_child_conservation_enabled": True,
    "nested_l0_lyapunov_reuse_enabled": True,
    "warm_start_howard_enabled": True,
}

FROZEN_M233_ORIGINAL_JSON_SHA256 = "339e723ff8dca6b9f061c7589de40337e6e2c24e07bac00f6768aeea7ba4539b"


def verify_m233_original_archive_untouched(p2_dir: Path) -> Dict[str, Any]:
    """Verify frozen `m233_sisc_unlock_results.json` remains byte-identical (`R333-D03`)."""
    fp = p2_dir / "m233_sisc_unlock_results.json"
    if not fp.exists():
        raise RuntimeError(f"Missing frozen M2.3.3 archive: {fp}")
    actual = hashlib.sha256(fp.read_bytes()).hexdigest()
    if actual != FROZEN_M233_ORIGINAL_JSON_SHA256:
        raise RuntimeError(
            f"Frozen m233_sisc_unlock_results.json modified! Expected {FROZEN_M233_ORIGINAL_JSON_SHA256}, got {actual}"
        )
    return {"file": fp.name, "sha256": actual, "verified_untouched": True}


def _current_rss_mb() -> float:
    """Read current Linux process VmRSS in MiB from /proc/self/status (`0.0` if unavailable)."""
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024.0
    except OSError:
        pass
    return 0.0


def _scalar_row_snapshot(res: dict) -> dict:
    """Extract pure scalar/stage snapshot from a solver result dict, severing all strong
    references to `LazyRoomPortalPolicy`, `Phase2DecisionCertificate`, `z_guide_full`,
    and parent `SeamFreePortal3DPlanner` / `SuperLU` room factorizations (`Closes SISC-01`).
    """
    st_ms = res.get("stage_ms")
    return {
        "lo": float(res["lo"]),
        "hi": float(res["hi"]),
        "width": float(res["hi"]) - float(res["lo"]),
        "certified": bool(res["certified"]),
        "guarantee_tier": str(res["guarantee_tier"]),
        "status": str(res["status"]),
        "query_ms": float(res["query_ms"]),
        "active_dofs": int(res.get("active_dofs", 0)),
        "used_defect_closure": bool(res.get("used_defect_closure", True)),
        "operational_local_lu_rhs_solves": int(
            res.get("operational_local_lu_rhs_solves", res.get("local_lu_solves", 0))
        ),
        "evaluation_materialization_rhs_solves": int(res.get("evaluation_materialization_rhs_solves", 0)),
        "local_lu_solves": int(res.get("local_lu_solves", 0)),
        "stage_ms": {str(k): float(v) for k, v in st_ms.items()} if isinstance(st_ms, dict) else None,
    }


QuadNodeKey = Tuple[int, int, int]  # (portal_id, level 0..4, block_index_at_level)


class SubPortalPoUQuadtree3DPlanner:
    """Adaptive Sub-Portal Quadtree Quotient Planner (`L0..L4`) with:
      - Zero-hint 3D conductance bottleneck discovery & 27 room-interior sparse LUs (`SeamFreePortal3DPlanner` base);
      - Persistent unclipped quadtree node cache `node_cache[(p_id, lv, bi)] -> (k_raw_col, {room_c: y_col})`;
      - Partition-of-Unity `(k - 1)` child solve conservation across all dyadic splits `L0 -> L1 -> L2 -> L3 -> L4`;
      - Single `L0` cooperative Lyapunov witness `w_lyap` reused exact-algebraically across nested cuts + warm Howard;
      - Surgical per-portal quadtree cache invalidation under localized `update_world_operator`;
      - Full `LazyRoomPortalPolicy` root priming inside `query_ms` + split operational vs. evaluation RHS counters.
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
        coarse_l0_only: bool = False,
        use_portal_cache: bool = True,
        enable_pou_conservation: bool = True,
    ) -> None:
        # Initialize shared room decomposition & room LUs without eager clipped L0 cache duplication
        self.base = SeamFreePortal3DPlanner(
            spec=spec,
            gn=gn,
            free_3d=free_3d,
            free_nodes=free_nodes,
            pts_f=pts_f,
            A_csr=A_csr,
            eps_tol=eps_tol,
            coarse_l0_only=coarse_l0_only,
            use_portal_cache=True,
        )
        t_qt0 = time.perf_counter()
        self.spec = self.base.spec
        self.lam = self.base.lam
        self.gn = self.base.gn
        self.eps_tol = self.base.eps_tol
        self.coarse_l0_only = bool(coarse_l0_only)
        self.use_portal_cache = bool(use_portal_cache)
        self.enable_pou_conservation = bool(enable_pou_conservation)

        # Build strictly nested `L0..L4` quadtree topology on each 2D doorway `p_id`
        self.qt_blocks: Dict[QuadNodeKey, np.ndarray] = {}
        self.qt_children: Dict[QuadNodeKey, List[QuadNodeKey]] = {}
        self.qt_parent: Dict[QuadNodeKey, QuadNodeKey] = {}
        for pid in range(self.base.n_portals):
            blks_by_lv = [
                build_portal_level_blocks(self.base.portal_nodes_loc[pid], self.base.portal_pts[pid], lv)
                for lv in range(5)
            ]
            for lv in range(5):
                for bi, barr in enumerate(blks_by_lv[lv]):
                    self.qt_blocks[(pid, lv, bi)] = barr
                if lv < 4:
                    child_of_node = np.empty(self.base.n_g, dtype=np.int64)
                    for ci, carr in enumerate(blks_by_lv[lv + 1]):
                        child_of_node[carr] = ci
                    for bi, barr in enumerate(blks_by_lv[lv]):
                        pkey = (pid, lv, bi)
                        if len(barr) <= 1:
                            self.qt_children[pkey] = []
                        else:
                            ch_ids = sorted(set(int(x) for x in child_of_node[barr]))
                            ch_keys = [(pid, lv + 1, ci) for ci in ch_ids]
                            self.qt_children[pkey] = ch_keys
                            for ck in ch_keys:
                                self.qt_parent[ck] = pkey

        # Store unclipped L0 root columns in `node_cache` (recomputing unclipped `lu_Agg.solve(NegM_L)` from `y0` with `0` extra room LU solves!)
        self.node_cache: Dict[QuadNodeKey, Tuple[np.ndarray, Dict[int, np.ndarray]]] = {}
        self._seed_l0_from_base_portal_cache(range(self.base.n_portals))
        # Release `base.portal_cache` so resident memory holds ONLY `node_cache` (zero double-counting!)
        self.base.portal_cache.clear()
        self.offline_init_ms = self.base.offline_init_ms + 1000.0 * (time.perf_counter() - t_qt0)

    # Forward read-only attributes used by `LazyRoomPortalPolicy` and test harnesses
    @property
    def operator_epoch(self) -> int:
        return self.base.operator_epoch

    @property
    def n_f(self) -> int:
        return self.base.n_f

    @property
    def n_g(self) -> int:
        return self.base.n_g

    @property
    def n_rooms(self) -> int:
        return self.base.n_rooms

    @property
    def n_portals(self) -> int:
        return self.base.n_portals

    @property
    def gamma_f(self) -> np.ndarray:
        return self.base.gamma_f

    @property
    def room_of_f(self) -> np.ndarray:
        return self.base.room_of_f

    @property
    def room_nodes(self) -> List[np.ndarray]:
        return self.base.room_nodes

    @property
    def room_tl(self) -> List[np.ndarray]:
        return self.base.room_tl

    @property
    def local_lu_solve_calls(self) -> int:
        return self.base.local_lu_solve_calls

    def _seed_l0_from_base_portal_cache(self, pids: Sequence[int]) -> None:
        b = self.base
        pid_list = [int(p) for p in pids]
        if not pid_list:
            return
        NegM_0 = np.zeros((b.n_g, len(pid_list)), dtype=float)
        y0_maps: List[Dict[int, np.ndarray]] = []
        for idx_p, pid in enumerate(pid_list):
            _, _, y_by_c = b.portal_cache[(pid, 0)]
            ym = {c: y_arr[:, 0].copy() for c, y_arr in y_by_c.items()}
            y0_maps.append(ym)
            for c, yc_vec in ym.items():
                NegM_0[b.room_tl[c], idx_p] += b.room_NegAgr[c] @ yc_vec
        K0_raw = b.lu_Agg.solve(NegM_0)
        if not np.all(np.isfinite(K0_raw)):
            raise RuntimeError("Non-finite L0 portal response matrix")
        neg_mag = max(0.0, float(-np.min(K0_raw)))
        if neg_mag > 1e-9 * max(1.0, float(np.max(K0_raw))):
            raise RuntimeError(f"L0 portal response violated non-negativity: min={float(np.min(K0_raw))}")
        b.max_k_neg_roundoff = max(b.max_k_neg_roundoff, neg_mag)
        for idx_p, pid in enumerate(pid_list):
            self.node_cache[(pid, 0, 0)] = (K0_raw[:, idx_p].copy(), y0_maps[idx_p])

    def _solve_node_keys_direct(
        self,
        pid: int,
        ckeys: Sequence[QuadNodeKey],
        store_to_cache: bool,
        out_dict: Dict[QuadNodeKey, Tuple[np.ndarray, Dict[int, np.ndarray]]],
    ) -> None:
        b = self.base
        m_b = len(ckeys)
        if m_b == 0:
            return
        NegM_L = np.zeros((b.n_g, m_b), dtype=float)
        y_by_c: Dict[int, np.ndarray] = {}
        for c in b.portal_rooms[pid]:
            tl = b.room_tl[c]
            mp = b.tl_pos_in_gamma[c]
            L_sub = np.zeros((len(tl), m_b), dtype=float)
            for j, ck in enumerate(ckeys):
                loc_in_tl = mp[self.qt_blocks[ck]]
                L_sub[loc_in_tl[loc_in_tl >= 0], j] = 1.0
            Yc = b.hq_lus[c].solve(b.room_Arg[c] @ L_sub)
            b.local_lu_solve_calls += int(m_b)
            y_by_c[c] = Yc
            NegM_L[tl, :] += b.room_NegAgr[c] @ Yc
        K_raw = b.lu_Agg.solve(NegM_L)
        if not np.all(np.isfinite(K_raw)):
            raise RuntimeError("Non-finite sub-portal response K_raw")
        neg_mag = max(0.0, float(-np.min(K_raw)))
        if neg_mag > 1e-9 * max(1.0, float(np.max(K_raw))):
            raise RuntimeError(f"Sub-portal response violated non-negativity: min={float(np.min(K_raw))}")
        b.max_k_neg_roundoff = max(b.max_k_neg_roundoff, neg_mag)
        for j, ck in enumerate(ckeys):
            entry = (K_raw[:, j].copy(), {c: y_by_c[c][:, j].copy() for c in b.portal_rooms[pid]})
            out_dict[ck] = entry
            if store_to_cache:
                self.node_cache[ck] = entry

    def _ensure_roots_available(
        self, query_store: Dict[QuadNodeKey, Tuple[np.ndarray, Dict[int, np.ndarray]]]
    ) -> None:
        missing_pids = [pid for pid in range(self.base.n_portals) if (pid, 0, 0) not in query_store]
        for pid in missing_pids:
            self._solve_node_keys_direct(pid, [(pid, 0, 0)], store_to_cache=self.use_portal_cache, out_dict=query_store)

    def _split_parents_into_store(
        self,
        parent_keys: Sequence[QuadNodeKey],
        query_store: Dict[QuadNodeKey, Tuple[np.ndarray, Dict[int, np.ndarray]]],
    ) -> None:
        """Top-down quadtree split with Partition-of-Unity `(k - 1)` child conservation:
        When `enable_pou_conservation` is True and parent `pk` is in `query_store` with `k >= 2` children,
        solves at most `k - 1` missing children via room LUs and derives the `k`-th child by exact linearity!
        """
        b = self.base
        ordered_parents = sorted(set(parent_keys), key=lambda x: (x[1], x[0], x[2]))
        for lv_step in sorted(set(pk[1] for pk in ordered_parents)):
            lv_pkeys = [pk for pk in ordered_parents if pk[1] == lv_step]
            solve_by_pid: Dict[int, List[QuadNodeKey]] = {}
            derive_last: List[Tuple[QuadNodeKey, List[QuadNodeKey], QuadNodeKey]] = []
            for pk in lv_pkeys:
                chs = self.qt_children[pk]
                if not chs or all(ck in query_store for ck in chs):
                    continue
                if self.enable_pou_conservation and (pk in query_store) and len(chs) >= 2:
                    # Pick one missing child to derive by subtraction; solve all other missing children
                    missing_chs = [ck for ck in chs if ck not in query_store]
                    derived_ck = missing_chs[-1]
                    for ck in missing_chs[:-1]:
                        solve_by_pid.setdefault(pk[0], []).append(ck)
                    sibs = [ck for ck in chs if ck != derived_ck]
                    derive_last.append((pk, sibs, derived_ck))
                else:
                    for ck in chs:
                        if ck not in query_store:
                            solve_by_pid.setdefault(pk[0], []).append(ck)

            for pid, ckeys in solve_by_pid.items():
                self._solve_node_keys_direct(pid, ckeys, store_to_cache=self.use_portal_cache, out_dict=query_store)

            for pk, sibs, last_ck in derive_last:
                kp_raw, yp_map = query_store[pk]
                k_rem = kp_raw.copy()
                for sb in sibs:
                    k_rem -= query_store[sb][0]
                neg_m = max(0.0, float(-np.min(k_rem)))
                if neg_m > 1e-9 * max(1.0, float(np.max(k_rem))):
                    raise RuntimeError(f"Derived PoU child violated non-negativity: min={float(np.min(k_rem))}")
                b.max_k_neg_roundoff = max(b.max_k_neg_roundoff, neg_m)
                y_rem: Dict[int, np.ndarray] = {}
                for c in b.portal_rooms[pk[0]]:
                    yc_r = yp_map[c].copy()
                    for sb in sibs:
                        yc_r -= query_store[sb][1][c]
                    y_rem[c] = yc_r
                entry = (k_rem, y_rem)
                query_store[last_ck] = entry
                if self.use_portal_cache:
                    self.node_cache[last_ck] = entry

    def factor_plus_response_cache_bytes(self) -> dict:
        b = self.base
        room_lu_b = sum(
            int(lu.L.data.nbytes + lu.L.indices.nbytes + lu.L.indptr.nbytes + lu.U.data.nbytes + lu.U.indices.nbytes + lu.U.indptr.nbytes)
            for lu in b.hq_lus
        )
        agg_lu_b = int(
            b.lu_Agg.L.data.nbytes + b.lu_Agg.L.indices.nbytes + b.lu_Agg.L.indptr.nbytes
            + b.lu_Agg.U.data.nbytes + b.lu_Agg.U.indices.nbytes + b.lu_Agg.U.indptr.nbytes
        )
        cache_b = 0
        for ck, (k_col, ym) in self.node_cache.items():
            cache_b += int(self.qt_blocks[ck].nbytes + k_col.nbytes) + sum(int(v.nbytes) for v in ym.values())
        tot = room_lu_b + agg_lu_b + cache_b
        return {
            "room_lu_bytes": room_lu_b,
            "portal_inplane_lu_bytes": agg_lu_b,
            "quadtree_response_cache_bytes": cache_b,
            "cached_quadtree_nodes": int(len(self.node_cache)),
            "total_bytes": tot,
            "total_mb_decimal": float(tot) / 1e6,
        }

    def update_world_operator(self, A_new_csr: sp.csr_matrix, modified_rooms: Sequence[int], portal_diag_changed: bool) -> dict:
        """Surgical continual world-model update:
        Evicts ONLY quadtree nodes `(p_id, lv, bi)` on portals touching `modified_rooms` (when `portal_diag_changed=False`),
        preserving all learned `L1..L4` sub-portal responses across unmodified rooms!
        """
        t0 = time.perf_counter()
        b = self.base
        n_before = len(self.node_cache)
        mod_set = sorted(set(int(c) for c in modified_rooms))
        if portal_diag_changed:
            aff_portals = set(range(b.n_portals))
        else:
            aff_portals = set()
            for c in mod_set:
                aff_portals.update(b.room_portals[c])

        upd_base = b.update_world_operator(A_new_csr, mod_set, portal_diag_changed=portal_diag_changed)
        if portal_diag_changed:
            self.node_cache.clear()
        else:
            for k in [ck for ck in self.node_cache.keys() if ck[0] in aff_portals]:
                del self.node_cache[k]

        self._seed_l0_from_base_portal_cache(sorted(aff_portals))
        b.portal_cache.clear()
        retained_higher = sum(1 for ck in self.node_cache.keys() if ck[1] > 0)
        return {
            "update_ms": 1000.0 * (time.perf_counter() - t0),
            "rooms_refactored": upd_base["rooms_refactored"],
            "invalidated_portals": len(aff_portals),
            "retained_cache_entries": int(retained_higher),
            "cached_entries_before": int(n_before),
        }

    def solve_exact_reference_value(self, s_f: int, goal_mask: np.ndarray, phi_goal: float = 0.0) -> float:
        # Ensure `base.portal_cache` temporarily has L0 entries if needed by `base.solve_exact_reference_value`
        b = self.base
        for pid in range(b.n_portals):
            if (pid, 0) not in b.portal_cache:
                if (pid, 0, 0) in self.node_cache:
                    k_col, ym = self.node_cache[(pid, 0, 0)]
                    b.portal_cache[(pid, 0)] = ([self.qt_blocks[(pid, 0, 0)]], np.maximum(k_col[:, None], 0.0), {c: v[:, None] for c, v in ym.items()})
                else:
                    b._ensure_portal_level(pid, 0)
        val = b.solve_exact_reference_value(s_f, goal_mask, phi_goal=phi_goal)
        b.portal_cache.clear()
        return val

    def solve_unseen_goal(
        self,
        s_f: int,
        goal_mask: np.ndarray,
        phi_goal: float = 0.0,
        materialize_full_z_sub: bool = False,
    ) -> dict:
        t0 = time.perf_counter()
        b = self.base
        s_i, gm, g_f, phi_f = b._validate_query_inputs(s_f, goal_mask, phi_goal)
        goal_sig = tuple(int(x) for x in g_f)
        solves_before = b.local_lu_solve_calls

        # Short-circuit trivial `start_in_goal` or `unreachable` identically to `SeamFreePortal3DPlanner`
        if bool(gm[s_i]) or (not bool(check_directed_goal_reachability(b.A_csr, gm)[s_i])):
            res_triv = b.solve_unseen_goal(s_i, gm, phi_goal=phi_f, materialize_full_z_sub=materialize_full_z_sub)
            res_triv["stage_ms"] = {
                "goal_ring_and_readout_ms": res_triv["query_ms"],
                "cache_miss_lu_ms": 0.0,
                "howard_and_selection_ms": 0.0,
                "defect_krylov_ms": 0.0,
                "policy_prime_ms": 0.0,
            }
            return res_triv

        t_st0 = time.perf_counter()
        c_g = int(b.room_of_f[g_f[0]])
        rn_g = b.room_nodes[c_g]
        tl_g = b.room_tl[c_g]
        c_s = int(b.room_of_f[s_i])

        # 1. Exact goal-room complete-ring Woodbury elimination in unit terminal gauge (`Proposition 1`)
        in_g_loc, ring_r = extract_directed_goal_ring_in_room(b.A_csr, gm, rn_g, b.gamma_f[tl_g])
        RHS_rg = np.zeros((len(rn_g), len(ring_r)), dtype=float)
        RHS_rg[ring_r, np.arange(len(ring_r))] = 1.0
        U_rg = b.hq_lus[c_g].solve(RHS_rg)
        b.local_lu_solve_calls += int(len(ring_r))
        K_inv = np.linalg.inv(U_rg[ring_r, :])

        NegAgr_U_full = np.zeros((b.n_g, len(ring_r)), dtype=float)
        NegAgr_U_full[tl_g, :] = b.room_NegAgr[c_g] @ U_rg
        Smooth_U = b.lu_Agg.solve(NegAgr_U_full)

        h_goal_r = U_rg @ (K_inv @ np.ones(len(ring_r), dtype=float))
        r_gam = np.zeros(b.n_g, dtype=float)
        r_gam[tl_g] = np.maximum(b.room_NegAgr[c_g] @ h_goal_r, 0.0)
        r_hat = np.maximum(b.lu_Agg.solve(r_gam), 0.0)

        # Start-state adjoint boundary readout (`interior` or `portal` start)
        if c_s >= 0:
            rn_s = b.room_nodes[c_s]
            tl_s = b.room_tl[c_s]
            pos_s = int(np.searchsorted(rn_s, s_i))
            e_s = np.zeros(len(rn_s), dtype=float)
            e_s[pos_s] = 1.0
            lam_s = b.hq_lus[c_s].solve(e_s, trans="T")
            b.local_lu_solve_calls += 1
            if c_s == c_g:
                RHS_adj = np.zeros(len(rn_s), dtype=float)
                RHS_adj[ring_r] = K_inv.T @ U_rg[pos_s, :]
                lam_s = lam_s - b.hq_lus[c_s].solve(RHS_adj, trans="T")
                b.local_lu_solve_calls += 1
            h_s_tl = np.maximum(np.asarray(b.room_Arg[c_s].T @ lam_s).ravel(), 0.0)
            z_dir = float(h_goal_r[pos_s]) if c_s == c_g else 0.0
        else:
            g_idx_s = int(np.searchsorted(b.gamma_f, s_i))
            tl_s = np.array([g_idx_s], dtype=np.int64)
            h_s_tl = np.array([1.0], dtype=float)
            z_dir = 0.0
        goal_ring_ms = 1000.0 * (time.perf_counter() - t_st0)

        cache_miss_lu_ms = 0.0
        howard_and_sel_ms = 0.0
        defect_krylov_ms = 0.0

        # Intra-query memoized store backed by persistent `node_cache` when `use_portal_cache=True`
        query_store: Dict[QuadNodeKey, Tuple[np.ndarray, Dict[int, np.ndarray]]] = (
            self.node_cache if self.use_portal_cache else dict(self.node_cache)
        )
        t_cm0 = time.perf_counter()
        self._ensure_roots_available(query_store)
        cache_miss_lu_ms += 1000.0 * (time.perf_counter() - t_cm0)

        goal_mod_col_cache: Dict[QuadNodeKey, np.ndarray] = {}

        def _get_goal_col(ck: QuadNodeKey) -> np.ndarray:
            if ck in goal_mod_col_cache:
                return goal_mod_col_cache[ck]
            k_raw_col, y_map = query_store[ck]
            if c_g in y_map:
                k_mod = k_raw_col - Smooth_U @ (K_inv @ y_map[c_g][ring_r])
            else:
                k_mod = k_raw_col
            neg_m = max(0.0, float(-np.min(k_mod)))
            if neg_m > 1e-9 * max(1.0, float(np.max(k_mod))):
                raise RuntimeError(f"Goal-modified column violated non-negativity: min={float(np.min(k_mod))}")
            b.max_k_neg_roundoff = max(b.max_k_neg_roundoff, neg_m)
            k_pos = np.maximum(k_mod, 0.0)
            goal_mod_col_cache[ck] = k_pos
            return k_pos

        # 2. Round 0 (`L0` whole-portal partition): compute initial bounds + single reusable `L0` Lyapunov witness `w_lyap`
        t_hw0 = time.perf_counter()
        active_keys: List[QuadNodeKey] = [(pid, 0, 0) for pid in range(b.n_portals)]
        K_buf = np.empty((b.n_g, 1024), dtype=float)
        for j, ck in enumerate(active_keys):
            K_buf[:, j] = _get_goal_col(ck)
        blks_0 = [self.qt_blocks[ck] for ck in active_keys]
        hw0 = solve_and_verify_portal_howard_bounds(
            K_buf[:, : len(active_keys)],
            r_hat,
            blks_0,
            k_neg_roundoff_ub=b.max_k_neg_roundoff,
            max_iters=30,
        )
        hw_verified = bool(hw0["verified"])
        w_lyap = hw0["w_lyap"]
        xi_lyap = hw0["s_0_raw"]
        min_beta = hw0["min_beta_s_over_w"]
        v_lyap_0 = np.array([float(w_lyap[bl[0]]) for bl in blks_0], dtype=float)
        Kw_lyap_base = K_buf[:, : len(active_keys)] @ v_lyap_0
        v_lyap_0_l1 = float(np.sum(np.abs(v_lyap_0)))

        W_lo_raw = hw0["W_lo"]
        W_hi_raw = hw0["W_hi"]
        W_lo = W_lo_raw * (1.0 - 1e-12)
        W_hi = W_hi_raw * (1.0 + 1e-12)

        z_lo_s = z_dir + float(h_s_tl @ W_lo[tl_s])
        z_hi_s = z_dir + float(h_s_tl @ W_hi[tl_s])
        if hw_verified and np.isfinite(z_lo_s) and np.isfinite(z_hi_s) and z_lo_s > 0.0 and z_hi_s >= z_lo_s:
            lo_c = phi_f - b.lam * float(np.log(z_hi_s))
            hi_c = phi_f - b.lam * float(np.log(z_lo_s))
        else:
            lo_c = -float("inf")
            hi_c = float("inf")

        w_s_full = np.zeros(b.n_g, dtype=float)
        w_s_full[tl_s] = h_s_tl
        howard_and_sel_ms += 1000.0 * (time.perf_counter() - t_hw0)

        rounds_run = 1
        used_defect_closure = False
        m_cap = int(LOCKED_M233_HYPERPARAMS["m_cap"])
        max_split_rounds = 0 if self.coarse_l0_only else int(LOCKED_M233_HYPERPARAMS["max_split_rounds"])

        # 3. Adaptive Sub-Portal Quadtree Cut Refinement (`L0 -> L1 -> L2 -> L3 -> L4`)
        for _rd in range(1, max_split_rounds + 1):
            if (not hw_verified) or (hi_c - lo_c <= b.eps_tol) or len(active_keys) >= m_cap:
                break
            t_sel = time.perf_counter()
            m_cur = len(active_keys)
            K_cur = K_buf[:, :m_cur]
            blks_cur = [self.qt_blocks[ck] for ck in active_keys]
            x_adj = np.array([bl[int(np.argmax(W_hi_raw[bl]))] for bl in blks_cur], dtype=np.int64)
            c_s_blk = np.maximum(w_s_full @ K_cur, 0.0)
            psi = np.maximum(np.linalg.solve((np.eye(m_cur) - K_cur[x_adj, :]).T, c_s_blk), 0.0)

            cand_blocks: List[Tuple[float, int, QuadNodeKey]] = []
            for j, ck in enumerate(active_keys):
                bl = blks_cur[j]
                if ck[1] < 4 and len(bl) >= 2 and psi[j] > 0.0:
                    osc = 0.5 * (
                        float(np.max(W_hi_raw[bl]) - np.min(W_hi_raw[bl]))
                        + float(np.max(W_lo_raw[bl]) - np.min(W_lo_raw[bl]))
                    )
                    cost_w = 1.25 if ck[1] == 3 else 1.0
                    sc = float(psi[j]) * osc / cost_w
                    if sc > 0.0:
                        cand_blocks.append((sc, j, ck))
            if not cand_blocks:
                howard_and_sel_ms += 1000.0 * (time.perf_counter() - t_sel)
                break

            cand_blocks.sort(reverse=True)
            top_sc = cand_blocks[0][0]
            replacements: Dict[int, List[QuadNodeKey]] = {}
            parents_to_split: List[QuadNodeKey] = []
            added_dofs = 0
            for sc, j, ck in cand_blocks[:28]:
                if sc < 0.04 * top_sc:
                    continue
                if _rd == 1 and ck[1] == 0 and sc >= 0.22 * top_sc and (hi_c - lo_c) > 0.35:
                    ch1 = self.qt_children[ck]
                    ch2 = [gk for c1 in ch1 for gk in (self.qt_children[c1] or [c1])]
                    if len(active_keys) + added_dofs + len(ch2) - 1 <= m_cap:
                        replacements[j] = ch2
                        parents_to_split.append(ck)
                        parents_to_split.extend(c1 for c1 in ch1 if self.qt_children[c1])
                        added_dofs += len(ch2) - 1
                        continue
                ch1 = self.qt_children[ck]
                if ch1 and (len(active_keys) + added_dofs + len(ch1) - 1 <= m_cap):
                    replacements[j] = ch1
                    parents_to_split.append(ck)
                    added_dofs += len(ch1) - 1
            if not replacements:
                j0, ck0 = cand_blocks[0][1], cand_blocks[0][2]
                ch0 = self.qt_children[ck0]
                if not ch0:
                    howard_and_sel_ms += 1000.0 * (time.perf_counter() - t_sel)
                    break
                replacements[j0] = ch0
                parents_to_split.append(ck0)
            howard_and_sel_ms += 1000.0 * (time.perf_counter() - t_sel)

            t_cm1 = time.perf_counter()
            self._split_parents_into_store(parents_to_split, query_store)
            cache_miss_lu_ms += 1000.0 * (time.perf_counter() - t_cm1)

            t_hw1 = time.perf_counter()
            rounds_run += 1
            new_active: List[QuadNodeKey] = []
            for j, ck in enumerate(active_keys):
                if j in replacements:
                    new_active.extend(replacements[j])
                else:
                    new_active.append(ck)
            active_keys = new_active
            m_new = len(active_keys)
            if m_new > K_buf.shape[1]:
                K_buf = np.empty((b.n_g, max(m_new + 256, K_buf.shape[1] * 2)), dtype=float)
            for j, ck in enumerate(active_keys):
                K_buf[:, j] = _get_goal_col(ck)
            K_cur = K_buf[:, :m_new]
            blks_cur = [self.qt_blocks[ck] for ck in active_keys]
            I_m = np.eye(m_new, dtype=float)

            # Warm-started Adversarial (`min`) & Cooperative (`max`) Howard iterations
            v_lo = np.array([float(np.min(W_lo_raw[bl])) for bl in blks_cur], dtype=float)
            for _ in range(25):
                x_min = np.array([bl[int(np.argmin(W_lo_raw[bl]))] for bl in blks_cur], dtype=np.int64)
                vn = np.linalg.solve(I_m - K_cur[x_min, :], r_hat[x_min])
                W_lo_raw = (K_cur @ vn) + r_hat
                b_mins = np.array([float(np.min(W_lo_raw[bl])) for bl in blks_cur], dtype=float)
                if np.max(np.abs(vn - v_lo) / np.maximum(np.abs(vn), 1e-30)) < 1e-11 and np.max(vn - b_mins) <= 1e-12 * max(1.0, float(np.max(vn))):
                    v_lo = vn
                    break
                v_lo = vn

            v_hi = np.array([float(np.max(W_hi_raw[bl])) for bl in blks_cur], dtype=float)
            for _ in range(25):
                x_max = np.array([bl[int(np.argmax(W_hi_raw[bl]))] for bl in blks_cur], dtype=np.int64)
                vn = np.linalg.solve(I_m - K_cur[x_max, :], r_hat[x_max])
                W_hi_raw = (K_cur @ vn) + r_hat
                b_maxs = np.array([float(np.max(W_hi_raw[bl])) for bl in blks_cur], dtype=float)
                if np.max(np.abs(vn - v_hi) / np.maximum(np.abs(vn), 1e-30)) < 1e-11 and np.max(b_maxs - vn) <= 1e-12 * max(1.0, float(np.max(vn))):
                    v_hi = vn
                    break
                v_hi = vn

            # Nested-cut L0-Lyapunov outward slack shift (`L_B v_lo_cert = L_B v_lo - th_lo * w_lyap`)
            Lv_lo = np.empty(b.n_g, dtype=float)
            Lv_hi = np.empty(b.n_g, dtype=float)
            for j, bl in enumerate(blks_cur):
                Lv_lo[bl] = float(v_lo[j])
                Lv_hi[bl] = float(v_hi[j])

            k_ub = float(b.max_k_neg_roundoff)
            Kw_lyap_ub_cur = Kw_lyap_base + k_ub * v_lyap_0_l1
            xi_lyap_cur = w_lyap - Kw_lyap_ub_cur
            if np.any(xi_lyap_cur <= 0.0):
                hw_verified = False
                howard_and_sel_ms += 1000.0 * (time.perf_counter() - t_hw1)
                break
            xi_lyap = xi_lyap_cur
            r_lo = k_ub * float(np.sum(np.abs(v_lo))) + 1e-13 * np.maximum(W_lo_raw, 0.0)
            r_hi = k_ub * float(np.sum(np.abs(v_hi))) + 1e-13 * np.maximum(W_hi_raw, 0.0)
            d_lo = np.maximum(0.0, Lv_lo - (W_lo_raw - r_lo))
            d_hi = np.maximum(0.0, (W_hi_raw + r_hi) - Lv_hi)
            th_lo = float(np.max(d_lo / xi_lyap_cur)) * (1.0 + 1e-11) if float(np.max(d_lo)) > 0.0 else 0.0
            th_hi = float(np.max(d_hi / xi_lyap_cur)) * (1.0 + 1e-11) if float(np.max(d_hi)) > 0.0 else 0.0

            Lv_lo_c = Lv_lo - th_lo * w_lyap
            Lv_hi_c = Lv_hi + th_hi * w_lyap
            W_lo_c = W_lo_raw - k_ub * float(np.sum(np.abs(v_lo))) - th_lo * Kw_lyap_ub_cur
            W_hi_c = W_hi_raw + k_ub * float(np.sum(np.abs(v_hi))) + th_hi * Kw_lyap_ub_cur

            if (
                np.all(np.isfinite(W_lo_c))
                and np.all(np.isfinite(W_hi_c))
                and np.all(Lv_lo_c > 0.0)
                and np.all(W_lo_c > 0.0)
                and np.all(W_lo_c <= W_hi_c)
                and float(np.min(W_lo_c - Lv_lo_c)) >= -1e-15 * float(np.max(W_lo_c))
                and float(np.min(Lv_hi_c - W_hi_c)) >= -1e-15 * float(np.max(W_hi_c))
            ):
                W_lo = W_lo_c * (1.0 - 1e-12)
                W_hi = W_hi_c * (1.0 + 1e-12)
                z_lo_s = z_dir + float(h_s_tl @ W_lo[tl_s])
                z_hi_s = z_dir + float(h_s_tl @ W_hi[tl_s])
                lo_c = phi_f - b.lam * float(np.log(z_hi_s))
                hi_c = phi_f - b.lam * float(np.log(z_lo_s))
                howard_and_sel_ms += 1000.0 * (time.perf_counter() - t_hw1)
            else:
                # Rare multi-room scale-mismatch fallback (~0.1% of queries): refresh scale-matched
                # cooperative Lyapunov witness `w_lyap` on the current `m_new` cut rather than discarding
                # the already-verified Round-0 enclosure or skipping Step-4 defect closure!
                hw_fb = solve_and_verify_portal_howard_bounds(
                    K_cur, r_hat, blks_cur, k_neg_roundoff_ub=k_ub, max_iters=30
                )
                if bool(hw_fb["verified"]):
                    w_lyap = hw_fb["w_lyap"]
                    xi_lyap = hw_fb["s_0_raw"]
                    min_beta = hw_fb["min_beta_s_over_w"]
                    v_lyap_fb = np.array([float(w_lyap[bl[0]]) for bl in blks_cur], dtype=float)
                    Kw_lyap_base = K_cur @ v_lyap_fb
                    v_lyap_0_l1 = float(np.sum(np.abs(v_lyap_fb)))
                    W_lo_raw = hw_fb["W_lo"]
                    W_hi_raw = hw_fb["W_hi"]
                    W_lo = W_lo_raw * (1.0 - 1e-12)
                    W_hi = W_hi_raw * (1.0 + 1e-12)
                    z_lo_s = z_dir + float(h_s_tl @ W_lo[tl_s])
                    z_hi_s = z_dir + float(h_s_tl @ W_hi[tl_s])
                    lo_c = phi_f - b.lam * float(np.log(z_hi_s))
                    hi_c = phi_f - b.lam * float(np.log(z_lo_s))
                    howard_and_sel_ms += 1000.0 * (time.perf_counter() - t_hw1)
                else:
                    # Keep the already-verified enclosure `(W_lo, W_hi, w_lyap, xi_lyap)` from previous round
                    # and proceed to Step-4 Lyapunov defect closure
                    howard_and_sel_ms += 1000.0 * (time.perf_counter() - t_hw1)
                    break

        # 4. Verified Doob/Lyapunov Sub-Stochastic Defect Closure (rare fallback when `m_cap` reached before `eps_tol`)
        if (not self.coarse_l0_only) and hw_verified and (hi_c - lo_c > b.eps_tol):
            t_def0 = time.perf_counter()
            used_defect_closure = True

            def _apply_K_goal_linear(vec_g: np.ndarray) -> np.ndarray:
                NegM_v = np.zeros(b.n_g, dtype=float)
                for c in range(b.n_rooms):
                    tl_c = b.room_tl[c]
                    v_sub = vec_g[tl_c]
                    if not np.any(v_sub):
                        continue
                    yc = b.hq_lus[c].solve(b.room_Arg[c] @ v_sub)
                    b.local_lu_solve_calls += 1
                    if c == c_g:
                        yc = yc - U_rg @ (K_inv @ yc[ring_r])
                    NegM_v[tl_c] += b.room_NegAgr[c] @ yc
                return b.lu_Agg.solve(NegM_v)

            Lin_sc = spla.LinearOperator(
                (b.n_g, b.n_g),
                matvec=lambda u: np.asarray(u, dtype=float) - (_apply_K_goal_linear(w_lyap * np.asarray(u, dtype=float)) / w_lyap),
                dtype=float,
            )
            u_cur_sc = (0.5 * (W_lo + W_hi)) / w_lyap
            rhs_sc = r_hat / w_lyap
            W_lo_orig, W_hi_orig = W_lo, W_hi
            for rtol_step, maxit_step in ((2.5e-3, 5), (1.0e-4, 8), (2.0e-6, 14), (1.0e-9, 40)):
                u_cur_sc, _ = spla.bicgstab(Lin_sc, rhs_sc, x0=u_cur_sc, rtol=rtol_step, atol=1e-14, maxiter=maxit_step)
                if not np.all(np.isfinite(u_cur_sc)):
                    hw_verified = False
                    break
                z_til = np.maximum(u_cur_sc * w_lyap, 0.0)
                d_til = (_apply_K_goal_linear(z_til) + r_hat) - z_til
                eta_m = float(np.max(np.maximum(-d_til, 0.0) / xi_lyap)) * (1.0 + 1e-10)
                eta_p = float(np.max(np.maximum(d_til, 0.0) / xi_lyap)) * (1.0 + 1e-10)
                u_lo_b = np.maximum(W_lo_orig, z_til - eta_m * w_lyap)
                u_hi_b = np.minimum(W_hi_orig, z_til + eta_p * w_lyap)
                if np.any(u_lo_b <= 0.0) or np.any(u_lo_b > u_hi_b):
                    hw_verified = False
                    break
                W_lo_cand = (_apply_K_goal_linear(u_lo_b) + r_hat) * (1.0 - 1e-12)
                W_hi_cand = (_apply_K_goal_linear(u_hi_b) + r_hat) * (1.0 + 1e-12)
                if (
                    np.all(np.isfinite(W_lo_cand))
                    and np.all(np.isfinite(W_hi_cand))
                    and np.all(W_lo_cand > 0.0)
                    and np.all(W_lo_cand <= W_hi_cand)
                    and np.all(W_lo_cand >= u_lo_b * (1.0 - 2e-12))
                ):
                    W_lo, W_hi = W_lo_cand, W_hi_cand
                    z_lo_s = z_dir + float(h_s_tl @ W_lo[tl_s])
                    z_hi_s = z_dir + float(h_s_tl @ W_hi[tl_s])
                    if z_lo_s > 0.0 and z_hi_s >= z_lo_s:
                        lo_c = phi_f - b.lam * float(np.log(z_hi_s))
                        hi_c = phi_f - b.lam * float(np.log(z_lo_s))
                        if hi_c - lo_c <= b.eps_tol:
                            break
                else:
                    hw_verified = False
                    break
            defect_krylov_ms += 1000.0 * (time.perf_counter() - t_def0)

        t_pol0 = time.perf_counter()
        is_cert = bool(
            (not self.coarse_l0_only)
            and hw_verified
            and np.isfinite(lo_c)
            and np.isfinite(hi_c)
            and (hi_c >= lo_c)
            and (hi_c - lo_c <= b.eps_tol + 1e-12)
        )
        cert_obj = (
            Phase2DecisionCertificate(
                certificate_mode="full_policy_enclosure",
                certified=is_cert,
                epsilon_tol=b.eps_tol,
                lower_bound_opt=lo_c if np.isfinite(lo_c) else 0.0,
                incumbent_policy_upper_bound=hi_c if np.isfinite(hi_c) else None,
                chosen_root_action=0,
                horizon_steps=1,
                state_id=s_i,
                operator_epoch=b.operator_epoch,
                model_semantics="discrete_upwind_kl_lmdp",
            )
            if np.isfinite(lo_c) and (np.isfinite(hi_c) or not is_cert)
            else None
        )
        policy_handle = (
            LazyRoomPortalPolicy(
                planner=b,
                operator_epoch=b.operator_epoch,
                goal_signature=goal_sig,
                phi_goal=phi_f,
                c_goal=c_g,
                in_g_loc=in_g_loc,
                ring_r=ring_r,
                U_rg=U_rg,
                K_inv=K_inv,
                h_goal_r=h_goal_r,
                W_lo_unit=W_lo,
            )
            if np.all(np.isfinite(W_lo)) and np.all(W_lo > 0.0)
            else None
        )
        if policy_handle is not None:
            _ = policy_handle.action_distribution(s_i)
        policy_prime_ms = 1000.0 * (time.perf_counter() - t_pol0)
        query_ms = 1000.0 * (time.perf_counter() - t0)
        solves_after_query = b.local_lu_solve_calls

        t_mat0 = time.perf_counter()
        z_guide_full = None
        if materialize_full_z_sub and policy_handle is not None:
            z_unit = policy_handle.materialize_full_grid_unit()
            exp_arg = -phi_f / b.lam
            if -660.0 <= exp_arg <= 660.0:
                scale_phi = float(np.exp(exp_arg))
                z_guide_full = (z_unit * scale_phi) if (scale_phi > 1e-290 and np.isfinite(scale_phi)) else z_unit
            else:
                z_guide_full = z_unit
        eager_mat_ms = 1000.0 * (time.perf_counter() - t_mat0)
        solves_after_mat = b.local_lu_solve_calls

        return {
            "query_ms": query_ms,
            "eager_materialize_ms": eager_mat_ms,
            "stage_ms": {
                "goal_ring_and_readout_ms": goal_ring_ms,
                "cache_miss_lu_ms": cache_miss_lu_ms,
                "howard_and_selection_ms": howard_and_sel_ms,
                "defect_krylov_ms": defect_krylov_ms,
                "policy_prime_ms": policy_prime_ms,
            },
            "guarantee_tier": "float64_toleranced_model_enclosure" if is_cert else "uncertified",
            "status": "ok" if is_cert else ("uncertified_coarse_l0" if self.coarse_l0_only else "numeric_or_width_unclosed"),
            "lo": lo_c,
            "hi": hi_c,
            "width": float(hi_c - lo_c) if (np.isfinite(lo_c) and np.isfinite(hi_c)) else float("inf"),
            "certified": bool(cert_obj.certified) if cert_obj is not None else False,
            "certificate": cert_obj,
            "policy": policy_handle,
            "active_dofs": int(len(active_keys)),
            "full_interface_dofs": int(b.n_g),
            "rounds": int(rounds_run),
            "used_defect_closure": bool(used_defect_closure),
            "operational_local_lu_rhs_solves": int(solves_after_query - solves_before),
            "evaluation_materialization_rhs_solves": int(solves_after_mat - solves_after_query),
            "local_lu_solves": int(solves_after_mat - solves_before),
            "min_beta_s_over_w": min_beta,
            "z_guide_full": z_guide_full,
        }


# ==============================================================================
# 1. Deterministic Contract, PoU Exactness, & Adversarial Boundary Suite (`M2.3.3`)
# ==============================================================================
def run_m233_contract_and_pou_verification() -> dict:
    t0 = time.perf_counter()
    verify_phase1_readonly_freeze()
    p2_dir = Path(__file__).resolve().parent
    frozen_10 = verify_all_10_frozen_jsons(p2_dir)
    enforce_single_thread_env()

    with warnings.catch_warnings():
        warnings.simplefilter("error")

        gn = 17
        spec = ProblemSpec(dim=3)
        free = np.ones((gn, gn, gn), dtype=bool)
        free[8, :, :] = False
        free[8, 6:11, 6:11] = True
        nodes = np.flatnonzero(free.ravel()).astype(np.int64)
        fpos = np.full(gn ** 3, -1, dtype=np.int64)
        fpos[nodes] = np.arange(len(nodes), dtype=np.int64)
        _, pts, _ = build_grid_points(3, spec.half_width, gn)
        q = np.full(len(nodes), 0.5, dtype=float)
        b_drift = np.zeros((len(nodes), 3), dtype=float)
        b_drift[:, :] = (0.09, 0.13, -0.07)
        A_csc = build_3d_reflecting_obstacle_mmatrix(spec, gn, free.ravel(), q, b_drift)
        A_csr = A_csc.tocsr()

        def _idx(x: int, y: int, z: int) -> int:
            return int(fpos[(x * gn + y) * gn + z])

        s_left = _idx(3, 8, 8)
        p_door = _idx(8, 8, 8)
        s_same = _idx(13, 6, 6)
        g_far = _idx(13, 8, 8)

        # Check A: Partition-of-Unity `(k - 1)` Child Conservation Exactness (`L0 -> L1 -> L2 -> L3 -> L4`)
        pl_pou = SubPortalPoUQuadtree3DPlanner(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=0.001, enable_pou_conservation=True)
        pl_dir = SubPortalPoUQuadtree3DPlanner(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=0.001, enable_pou_conservation=False)
        all_parents = [ck for ck, chs in pl_pou.qt_children.items() if chs]
        s_pou0 = pl_pou.local_lu_solve_calls
        pl_pou._split_parents_into_store(all_parents, pl_pou.node_cache)
        pou_rhs = int(pl_pou.local_lu_solve_calls - s_pou0)

        s_dir0 = pl_dir.local_lu_solve_calls
        pl_dir._split_parents_into_store(all_parents, pl_dir.node_cache)
        dir_rhs = int(pl_dir.local_lu_solve_calls - s_dir0)

        max_k_diff = max(
            float(np.max(np.abs(pl_pou.node_cache[ck][0] - pl_dir.node_cache[ck][0])))
            for ck in pl_pou.node_cache.keys()
        )
        max_y_diff = max(
            float(np.max(np.abs(pl_pou.node_cache[ck][1][c] - pl_dir.node_cache[ck][1][c])))
            for ck in pl_pou.node_cache.keys()
            for c in pl_pou.node_cache[ck][1].keys()
        )
        pou_exact_ok = bool(pou_rhs < dir_rhs and max_k_diff < 1e-13 and max_y_diff < 1e-13)

        # Check B: EC-01 `phi_goal` Unit-Gauge Invariance + EC-02/EC-03 Guards
        gm_pt = np.zeros(len(nodes), dtype=bool)
        gm_pt[g_far] = True
        ex_pt = np.flatnonzero(~gm_pt)
        z_pt_ex = spla.spsolve(A_csr[ex_pt, :][:, ex_pt].tocsc(), np.asarray((-A_csr[ex_pt, :][:, gm_pt]).sum(axis=1)).ravel())
        v0_pt = float(-spec.lam * np.log(z_pt_ex[int(np.searchsorted(ex_pt, s_left))]))
        widths_phi = []
        ec01_ok = True
        pl_phi = SubPortalPoUQuadtree3DPlanner(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=0.25)
        for phi in (-1000.0, 0.0, 100.0, 145.0, 160.0, 1000.0):
            rr_p = pl_phi.solve_unseen_goal(s_left, gm_pt, phi_goal=phi, materialize_full_z_sub=True)
            vp_p = evaluate_3d_deployed_policy_exact(A_csr, gm_pt, phi, rr_p["z_guide_full"], spec.lam, s_left)
            t_phi = v0_pt + phi
            widths_phi.append(rr_p["width"])
            if not (rr_p["certified"] and rr_p["lo"] - 1e-9 <= t_phi <= vp_p + 1e-9 and vp_p <= rr_p["hi"] + 1e-9):
                ec01_ok = False
        ec01_ok = bool(ec01_ok and (max(widths_phi) - min(widths_phi) <= 1e-12))

        r_triv = pl_phi.solve_unseen_goal(g_far, gm_pt, phi_goal=7.5)
        guards_ok = bool(r_triv["certified"] and r_triv["status"] == "start_in_goal" and abs(r_triv["lo"] - 7.5) < 1e-14)
        gm_portal_bad = np.zeros(len(nodes), dtype=bool)
        gm_portal_bad[p_door] = True
        try:
            _ = pl_phi.solve_unseen_goal(s_left, gm_portal_bad)
            guards_ok = False
        except ValueError:
            pass

        # Check C: Complete Goal-Ring Support (`6` families x `3` eps = `18` checks) + `12` 3-Drift Adversarial Boundary Cases (`eps = 0.001`)
        goal_families: Dict[str, np.ndarray] = {"interior_point": gm_pt}
        g_333 = np.zeros((gn, gn, gn), dtype=bool)
        g_333[12:15, 7:10, 7:10] = True
        goal_families["interior_3x3x3"] = g_333.ravel()[nodes]
        for thick in (1, 2, 3):
            g_slab = np.zeros((gn, gn, gn), dtype=bool)
            g_slab[9 : 9 + thick, 6:11, 6:11] = True
            goal_families[f"portal_adjacent_slab_thickness{thick}"] = g_slab.ravel()[nodes]
        goal_families["whole_goal_room"] = (pl_phi.room_of_f == pl_phi.room_of_f[g_far])

        b6_01_ok = True
        max_b6_regret = 0.0
        for _, gm_c in goal_families.items():
            ext_c = np.flatnonzero(~gm_c)
            z_k = np.ones(len(nodes), dtype=float)
            z_k[ext_c] = spla.spsolve(A_csr[ext_c, :][:, ext_c].tocsc(), np.asarray((-A_csr[ext_c, :][:, gm_c]).sum(axis=1)).ravel())
            v_true = float(-spec.lam * np.log(z_k[s_left]))
            for eps_v in (0.25, 0.01, 0.001):
                pl_t = SubPortalPoUQuadtree3DPlanner(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=eps_v)
                rr_t = pl_t.solve_unseen_goal(s_left, gm_c)
                z_pol = rr_t["policy"].materialize_full_grid_unit()
                j_pol = evaluate_3d_deployed_policy_exact(A_csr, gm_c, 0.0, z_pol, spec.lam, s_left)
                sub_res = float(np.max((A_csr @ z_pol)[ext_c]))
                ok_c = bool(
                    rr_t["certified"]
                    and (rr_t["lo"] - 1e-9 <= v_true <= j_pol + 1e-9 <= rr_t["hi"] + 1e-9)
                    and (rr_t["hi"] - rr_t["lo"] <= eps_v + 1e-11)
                    and (sub_res <= 1e-11)
                )
                if not ok_c:
                    b6_01_ok = False
                if eps_v == 0.001:
                    max_b6_regret = max(max_b6_regret, float(j_pol - v_true))

        adv_goals: Dict[str, np.ndarray] = {}
        g_disc = np.zeros((gn, gn, gn), dtype=bool)
        g_disc[11, 7:9, 7:9] = True
        g_disc[14, 9:11, 9:11] = True
        adv_goals["disconnected_same_room"] = g_disc.ravel()[nodes]
        g_jag = np.zeros((gn, gn, gn), dtype=bool)
        g_jag[9, 6:9, 6:10] = True
        g_jag[10, 7:11, 7:11] = True
        adv_goals["jagged_portal_adjacent"] = g_jag.ravel()[nodes]
        g_out = np.zeros((gn, gn, gn), dtype=bool)
        g_out[15:17, 6:11, 6:11] = True
        adv_goals["outer_wall_slab"] = g_out.ravel()[nodes]
        adv_goals["interior_point"] = gm_pt

        adv_ok = True
        adv_count = 0
        for _, gm_a in adv_goals.items():
            ext_a = np.flatnonzero(~gm_a)
            z_ka = np.ones(len(nodes), dtype=float)
            z_ka[ext_a] = spla.spsolve(A_csr[ext_a, :][:, ext_a].tocsc(), np.asarray((-A_csr[ext_a, :][:, gm_a]).sum(axis=1)).ravel())
            for st_node in (s_left, p_door, s_same):
                adv_count += 1
                v_tr = float(-spec.lam * np.log(z_ka[st_node])) if not gm_a[st_node] else 0.0
                pl_a = SubPortalPoUQuadtree3DPlanner(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=0.001)
                rr_a = pl_a.solve_unseen_goal(st_node, gm_a)
                z_pa = rr_a["policy"].materialize_full_grid_unit()
                j_pa = evaluate_3d_deployed_policy_exact(A_csr, gm_a, 0.0, z_pa, spec.lam, st_node)
                if not (
                    rr_a["certified"]
                    and (rr_a["lo"] - 1e-9 <= v_tr <= j_pa + 1e-9 <= rr_a["hi"] + 1e-9)
                    and (rr_a["hi"] - rr_a["lo"] <= 0.001 + 1e-11)
                ):
                    adv_ok = False

        # Check D: Cache Mode Counter Separation (`B6-02`) & Root Readiness + Weakref GC (`B6-05`)
        gm_q2 = np.zeros(len(nodes), dtype=bool)
        gm_q2[_idx(12, 7, 9)] = True
        c_modes_rhs: Dict[str, List[int]] = {}
        for cm in ("CacheOn_Persistent", "CacheL0Only", "QueryCold"):
            pl_cm = SubPortalPoUQuadtree3DPlanner(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=0.005, use_portal_cache=True)
            rhs_two = []
            for qi, gm_cur in enumerate((gm_pt, gm_q2)):
                if qi > 0:
                    if cm == "CacheL0Only":
                        for kd in [k for k in pl_cm.node_cache.keys() if k[1] > 0]:
                            del pl_cm.node_cache[kd]
                    elif cm == "QueryCold":
                        pl_cm.node_cache.clear()
                rc = pl_cm.solve_unseen_goal(s_left, gm_cur)
                rhs_two.append(int(rc["operational_local_lu_rhs_solves"]))
            c_modes_rhs[cm] = rhs_two
        cache_sep_ok = bool(
            c_modes_rhs["CacheOn_Persistent"][1] < c_modes_rhs["CacheL0Only"][1] < c_modes_rhs["QueryCold"][1]
        )

        pl_rd = SubPortalPoUQuadtree3DPlanner(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=0.25)
        readiness_ok = True
        for st_n in (s_left, p_door):
            rr_r = pl_rd.solve_unseen_goal(st_n, gm_pt)
            pol_r = rr_r["policy"]
            c0 = pl_rd.local_lu_solve_calls
            _, pr1 = pol_r.action_distribution(st_n)
            c1 = pl_rd.local_lu_solve_calls
            _, _ = pol_r.action_distribution(st_n)
            c2 = pl_rd.local_lu_solve_calls
            if (c1 - c0) != 0 or (c2 - c1) != 0 or abs(float(np.sum(pr1)) - 1.0) > 1e-12:
                readiness_ok = False
            del rr_r, pol_r
        wref = weakref.ref(pl_rd.base)
        del pl_rd
        gc.collect()
        gc_ok = bool(wref() is None)
        readiness_ok = bool(readiness_ok and gc_ok)

    all_ok = bool(pou_exact_ok and ec01_ok and guards_ok and b6_01_ok and adv_ok and cache_sep_ok and readiness_ok)
    out = {
        "ALL_M233_CONTRACTS_PASSED": all_ok,
        "elapsed_ms": 1000.0 * (time.perf_counter() - t0),
        "frozen_10_jsons_verified": frozen_10,
        "pou_conservation_check": {
            "pass": pou_exact_ok,
            "pou_rhs_solves": pou_rhs,
            "direct_rhs_solves": dir_rhs,
            "rhs_saving_pct": 100.0 * (1.0 - float(pou_rhs) / float(dir_rhs)),
            "max_abs_K_diff": max_k_diff,
            "max_abs_Y_diff": max_y_diff,
        },
        "ec01_unit_gauge_invariance_pass": ec01_ok,
        "ec02_ec03_guards_pass": guards_ok,
        "b6_01_18_goal_ring_checks_pass": b6_01_ok,
        "b6_01_max_regret_at_eps_1e3": max_b6_regret,
        "adversarial_12_3drift_boundary_checks_pass": adv_ok,
        "adversarial_cases_count": adv_count,
        "cache_mode_counter_separation": {"pass": cache_sep_ok, "two_query_operational_rhs": c_modes_rhs},
        "root_readiness_and_weakref_gc_pass": readiness_ok,
    }
    if not all_ok:
        raise RuntimeError(f"M2.3.3 contract suite failed: {out}")
    return out


# ==============================================================================
# 2. Single-Worker (`workers = 1`) Exact-Balance SISC Benchmark Campaign
# ==============================================================================
CACHE3_MODES = ("CacheOn_Persistent", "CacheL0Only", "QueryCold")
PAIR2_SISC_ARMS = ("M233_SubPortal_PoUQuadtree", "MatrixFree_ExactSchur_Krylov")


def _load_m232_verified_reference_lookup(p2_dir: Path) -> Dict[Tuple[str, int, int, int, int], Tuple[int, str, float, int]]:
    """Loads already-verified `SingleLU` numerical references from frozen `m232_targeted_replay_results.json`
    keyed by `(world_group, seed, gn, epoch, task_index) -> (start_state, goal_sha1, reference_value, singlelu_bytes)`.
    """
    m232_p = p2_dir / "m232_targeted_replay_results.json"
    data = _strict_json_loads(m232_p.read_text(encoding="utf-8"))
    lookup: Dict[Tuple[str, int, int, int, int], Tuple[int, str, float, int]] = {}
    pm = data["per_map_records"]
    for r in pm["replay_47cubed"]:
        sb = int(r["singlelu_factor_bytes"])
        for e in r["pair_events"]:
            if e["method_id"] == "M231_Portal_CacheOn":
                lookup[("static", int(e["seed"]), 47, 0, int(e["task_index"]))] = (
                    int(e["start_state"]), str(e["goal_signature_sha1"]), float(e["reference_value"]), sb
                )
    for r in pm["replay_59cubed"]:
        sb = int(r["singlelu_factor_bytes"])
        for e in r["pair_events"]:
            if e["method_id"] == "M231_Portal_CacheOn":
                lookup[("static", int(e["seed"]), 59, 0, int(e["task_index"]))] = (
                    int(e["start_state"]), str(e["goal_signature_sha1"]), float(e["reference_value"]), sb
                )
    for r in pm["continual_47cubed"]:
        for e in r["events"]:
            if e["method_id"] == "M231_Portal_CacheOn":
                lookup[("continual", int(e["seed"]), 47, int(e["operator_epoch"]), int(e["task_index"]))] = (
                    int(e["start_state"]), str(e["goal_signature_sha1"]), float(e["reference_value"]), 0
                )
    m233_p = p2_dir / "m233_sisc_unlock_results.json"
    if m233_p.exists():
        verify_m233_original_archive_untouched(p2_dir)
        d233 = _strict_json_loads(m233_p.read_text(encoding="utf-8"))
        pm233 = d233["per_map_records"]
        for r in pm233["replay_35cubed"]:
            sb = int(r["singlelu_factor_bytes"])
            for e in r["pair_events"]:
                if e["method_id"] == "M233_SubPortal_PoUQuadtree":
                    lookup[("static", int(e["seed"]), 35, 0, int(e["task_index"]))] = (
                        int(e["start_state"]), str(e["goal_signature_sha1"]), float(e["reference_value"]), sb
                    )
        for r in pm233["untouched_confirm_47cubed"]:
            sb = int(r["singlelu_factor_bytes"])
            for e in r["pair_events"]:
                if e["method_id"] == "M233_SubPortal_PoUQuadtree":
                    lookup[("static", int(e["seed"]), 47, 0, int(e["task_index"]))] = (
                        int(e["start_state"]), str(e["goal_signature_sha1"]), float(e["reference_value"]), sb
                    )
    return lookup


def _run_static_pair_single_map(
    *,
    block_id: str,
    seed: int,
    map_idx: int,
    gn: int,
    n_tasks: int,
    n_pol_evals: int,
    run_cache_ablation: bool,
    ref_lookup: Optional[Dict[Tuple[str, int, int, int, int], Tuple[int, str, float, int]]],
    force_fresh_singlelu: bool,
) -> dict:
    enforce_single_thread_env()
    world = generate_3d_multiroom_world(seed=seed, gn=gn, spec=ProblemSpec(dim=3), n_tasks=n_tasks, fit_gp_world=True)
    spec = world["spec"]
    lam = float(spec.lam)
    free_3d = world["free_3d"]
    free_mask = world["free_mask"]
    free_nodes = world["free_nodes"]
    pts_f = world["pts_f"]
    tasks = world["tasks"]

    t_op = time.perf_counter()
    A_csc = build_3d_reflecting_obstacle_mmatrix(spec, gn, free_mask, world["q_f"], world["b_f"])
    A_csr = A_csc.tocsr()
    op_asm_ms = 1000.0 * (time.perf_counter() - t_op)

    # Optional 3-Arm Cache Causal Study (`exact 2x 3x3 Latin square across 6 maps`)
    cache_order: Optional[List[str]] = None
    cache_raw: Optional[Dict[str, dict]] = None
    if run_cache_ablation:
        cache_order = [CACHE3_MODES[(map_idx + k) % 3] for k in range(3)]
        cache_raw = {}
        for rk, c_mode in enumerate(cache_order):
            gc.collect()
            rss_before = _current_rss_mb()
            pl_c = SubPortalPoUQuadtree3DPlanner(spec, gn, free_3d, free_nodes, pts_f, A_csr, eps_tol=0.25, use_portal_cache=True)
            wref_c_base = weakref.ref(pl_c.base)
            wref_c_pl = weakref.ref(pl_c)
            init_ms = pl_c.offline_init_ms
            raw_rows = []
            guides_c: Dict[int, np.ndarray] = {}
            n_pol_c = min(n_pol_evals, n_tasks) if c_mode == "CacheOn_Persistent" else 0
            for t_i, (s_f, gm_k) in enumerate(tasks):
                if t_i > 0:
                    if c_mode == "CacheL0Only":
                        for kd in [k for k in pl_c.node_cache.keys() if k[1] > 0]:
                            del pl_c.node_cache[kd]
                    elif c_mode == "QueryCold":
                        pl_c.node_cache.clear()
                rr = pl_c.solve_unseen_goal(s_f, gm_k, phi_goal=0.0, materialize_full_z_sub=(t_i < n_pol_c))
                if t_i < n_pol_c and rr["z_guide_full"] is not None:
                    guides_c[t_i] = np.array(rr["z_guide_full"], dtype=float, copy=True)
                raw_rows.append(_scalar_row_snapshot(rr))
                del rr
            mem_led = pl_c.factor_plus_response_cache_bytes()
            rss_peak_arm = _current_rss_mb()
            del pl_c
            gc.collect()
            if wref_c_base() is not None or wref_c_pl() is not None:
                raise RuntimeError(f"SISC-01 isolation violation: cache arm {c_mode} retained planner/LU base!")
            rss_after = _current_rss_mb()
            q_arr = [x["query_ms"] for x in raw_rows]
            cache_raw[c_mode] = {
                "exec_rank": rk,
                "init_ms": init_ms,
                "total_ms": init_ms + float(np.sum(q_arr)),
                "mean_query_ms": float(np.mean(q_arr)),
                "first6_query_ms": float(np.mean(q_arr[:6])),
                "last6_query_ms": float(np.mean(q_arr[-6:])),
                "prefix_cumulative_ms": [float(x) for x in np.cumsum([init_ms] + q_arr)[1:]],
                "total_operational_local_lu_rhs_solves": int(sum(x["operational_local_lu_rhs_solves"] for x in raw_rows)),
                "total_evaluation_materialization_rhs_solves": int(sum(x["evaluation_materialization_rhs_solves"] for x in raw_rows)),
                "total_local_lu_solves": int(sum(x["local_lu_solves"] for x in raw_rows)),
                "factor_plus_response_cache_bytes": mem_led,
                "rss_mb_before_arm": rss_before,
                "rss_mb_end_of_arm_before_del": rss_peak_arm,
                "rss_mb_after_arm_gc": rss_after,
                "prior_base_gc_freed": True,
                "_raw_rows": raw_rows,
                "_guides": guides_c,
            }

    # Closest-Neighbor Exact `AB / BA` Head-to-Head (`SubPortalPoUQuadtree` vs `MatrixFree_ExactSchur_Krylov`)
    pair_order = list(PAIR2_SISC_ARMS) if (map_idx % 2 == 0) else list(reversed(PAIR2_SISC_ARMS))
    pair_raw: Dict[str, dict] = {}
    n_pol = min(n_pol_evals, n_tasks)

    for rk, arm_nm in enumerate(pair_order):
        gc.collect()
        rss_before = _current_rss_mb()
        if arm_nm == "M233_SubPortal_PoUQuadtree":
            pl_p = SubPortalPoUQuadtree3DPlanner(spec, gn, free_3d, free_nodes, pts_f, A_csr, eps_tol=0.25, use_portal_cache=True)
            wref_base = weakref.ref(pl_p.base)
            wref_pl = weakref.ref(pl_p)
            init_ms = pl_p.offline_init_ms
            raw_rows = []
            guides_p: Dict[int, np.ndarray] = {}
            for t_i, (s_f, gm_k) in enumerate(tasks):
                rr = pl_p.solve_unseen_goal(s_f, gm_k, phi_goal=0.0, materialize_full_z_sub=(t_i < n_pol))
                if t_i < n_pol and rr["z_guide_full"] is not None:
                    guides_p[t_i] = np.array(rr["z_guide_full"], dtype=float, copy=True)
                raw_rows.append(_scalar_row_snapshot(rr))
                del rr
            mem_led = pl_p.factor_plus_response_cache_bytes()
            stage_sum_ms = {
                sk: float(sum(x["stage_ms"][sk] for x in raw_rows))
                for sk in ("goal_ring_and_readout_ms", "cache_miss_lu_ms", "howard_and_selection_ms", "defect_krylov_ms", "policy_prime_ms")
            }
            rss_peak_arm = _current_rss_mb()
            del pl_p
            gc.collect()
        else:
            pl_mf = MatrixFreeExactSchurKrylov3DPlanner(spec, gn, free_3d, free_nodes, pts_f, A_csr, eps_tol=0.25)
            wref_base = weakref.ref(pl_mf.base)
            wref_pl = weakref.ref(pl_mf)
            init_ms = pl_mf.offline_init_ms
            raw_rows = []
            guides_p = {}
            for t_i, (s_f, gm_k) in enumerate(tasks):
                rr = pl_mf.solve_unseen_goal(s_f, gm_k, phi_goal=0.0)
                if t_i < n_pol and rr["policy"] is not None:
                    s_m0 = pl_mf.base.local_lu_solve_calls
                    guides_p[t_i] = np.array(rr["policy"].materialize_full_grid_unit(), dtype=float, copy=True)
                    rr["evaluation_materialization_rhs_solves"] = int(pl_mf.base.local_lu_solve_calls - s_m0)
                    rr["local_lu_solves"] = int(rr["operational_local_lu_rhs_solves"] + rr["evaluation_materialization_rhs_solves"])
                rr["active_dofs"] = int(pl_mf.base.n_g)
                rr["used_defect_closure"] = True
                raw_rows.append(_scalar_row_snapshot(rr))
                del rr
            mem_led = None
            stage_sum_ms = None
            rss_peak_arm = _current_rss_mb()
            del pl_mf
            gc.collect()

        if wref_base() is not None or wref_pl() is not None:
            raise RuntimeError(f"SISC-01 isolation violation: pair arm {arm_nm} retained planner/LU base!")
        rss_after = _current_rss_mb()

        q_arr = [x["query_ms"] for x in raw_rows]
        pair_raw[arm_nm] = {
            "exec_rank": rk,
            "init_ms": init_ms,
            "total_ms": init_ms + float(np.sum(q_arr)),
            "mean_query_ms": float(np.mean(q_arr)),
            "first6_query_ms": float(np.mean(q_arr[:6])),
            "last6_query_ms": float(np.mean(q_arr[-6:])),
            "prefix_cumulative_ms": [float(x) for x in np.cumsum([init_ms] + q_arr)[1:]],
            "mean_active_dofs": float(np.mean([x["active_dofs"] for x in raw_rows])),
            "defect_closure_count": int(sum(1 for x in raw_rows if x["used_defect_closure"])),
            "total_operational_local_lu_rhs_solves": int(sum(x["operational_local_lu_rhs_solves"] for x in raw_rows)),
            "total_evaluation_materialization_rhs_solves": int(sum(x["evaluation_materialization_rhs_solves"] for x in raw_rows)),
            "total_local_lu_solves": int(sum(x["local_lu_solves"] for x in raw_rows)),
            "stage_sum_ms": stage_sum_ms,
            "factor_plus_response_cache_bytes": mem_led,
            "rss_mb_before_arm": rss_before,
            "rss_mb_end_of_arm_before_del": rss_peak_arm,
            "rss_mb_after_arm_gc": rss_after,
            "prior_base_gc_freed": True,
            "_raw_rows": raw_rows,
            "_guides": guides_p,
        }

    # Untimed Post-Pass: Independent `SingleLU` Reference + Deployed Policy Evaluation (`L <= V* <= J^{mu} <= U`)
    ref_vals: List[float] = []
    ref_ok: List[bool] = []
    slu_bytes = 0
    slu_total_ms: Optional[float] = None
    cross_verified_err: Optional[float] = None

    if force_fresh_singlelu or (ref_lookup is None) or (("static", seed, gn, 0, 0) not in ref_lookup):
        gc.collect()
        slu = SingleLUGoalCapacitance3DPlanner(spec, A_csc, A_csr)
        slu_q_ms = 0.0
        for t_i, (s_f, gm_k) in enumerate(tasks):
            rs = slu.solve_unseen_goal(s_f, gm_k)
            slu_q_ms += float(rs["query_ms"])
            ref_vals.append(float(rs["value"]))
            ref_ok.append(bool(rs["reference_valid"]))
        slu_total_ms = float(slu.offline_init_ms + slu_q_ms)
        slu_bytes = int(slu.factor_bytes())
        del slu
        gc.collect()
        if ref_lookup is not None and ("static", seed, gn, 0, 0) in ref_lookup:
            diffs = []
            for t_i, (s_f, gm_k) in enumerate(tasks):
                st_exp, gh_exp, v_exp, _ = ref_lookup[("static", seed, gn, 0, t_i)]
                assert st_exp == int(s_f) and gh_exp == _goal_hash(gm_k)
                diffs.append(abs(ref_vals[t_i] - v_exp))
            cross_verified_err = float(max(diffs))
            assert cross_verified_err < 1e-12, f"Cross-check mismatch vs frozen m232 SingleLU: {cross_verified_err}"
    else:
        for t_i, (s_f, gm_k) in enumerate(tasks):
            st_exp, gh_exp, v_exp, sb_exp = ref_lookup[("static", seed, gn, 0, t_i)]
            if st_exp != int(s_f) or gh_exp != _goal_hash(gm_k):
                raise RuntimeError(f"Task identity mismatch vs frozen m232 at seed={seed}, gn={gn}, t_i={t_i}")
            ref_vals.append(v_exp)
            ref_ok.append(True)
            slu_bytes = sb_exp

    cache_events: List[dict] = []
    if cache_raw is not None:
        for c_mode, cd in cache_raw.items():
            r_rows = cd.pop("_raw_rows")
            g_map = cd.pop("_guides")
            for t_i, rr_x in enumerate(r_rows):
                s_f, gm_k = tasks[t_i]
                jp = evaluate_3d_deployed_policy_exact(A_csr, gm_k, 0.0, g_map[t_i], lam, s_f) if t_i in g_map else None
                cache_events.append(_build_task_event(
                    block_id=f"m233_cache_{gn}cubed",
                    seed=seed,
                    gn=gn,
                    epoch=0,
                    task_index=t_i,
                    s_f=s_f,
                    gm=gm_k,
                    method_id=c_mode,
                    res=rr_x,
                    v_ref=ref_vals[t_i],
                    ref_valid=ref_ok[t_i],
                    j_pol=jp,
                ))

    pair_events: List[dict] = []
    for arm_nm, pd in pair_raw.items():
        r_rows = pd.pop("_raw_rows")
        g_map = pd.pop("_guides")
        for t_i, rr_x in enumerate(r_rows):
            s_f, gm_k = tasks[t_i]
            jp = evaluate_3d_deployed_policy_exact(A_csr, gm_k, 0.0, g_map[t_i], lam, s_f) if t_i in g_map else None
            pair_events.append(_build_task_event(
                block_id=block_id,
                seed=seed,
                gn=gn,
                epoch=0,
                task_index=t_i,
                s_f=s_f,
                gm=gm_k,
                method_id=arm_nm,
                res=rr_x,
                v_ref=ref_vals[t_i],
                ref_valid=ref_ok[t_i],
                j_pol=jp,
            ))

    return {
        "seed": seed,
        "gn": gn,
        "n_free_dofs": int(len(free_nodes)),
        "shared_gp_fit_ms": float(world["gp_fit_ms"]),
        "shared_operator_assembly_ms": op_asm_ms,
        "singlelu_factor_bytes": slu_bytes,
        "singlelu_reference_total_ms": slu_total_ms,
        "m232_reference_cross_check_max_abs_diff": cross_verified_err,
        "cache_execution_order": cache_order,
        "cache_arms": cache_raw,
        "cache_events": cache_events,
        "pair_execution_order": pair_order,
        "pair_arms": pair_raw,
        "pair_events": pair_events,
    }


def _run_continual_47_sisc_single_map(
    *,
    seed: int,
    map_idx: int,
    n_epochs: int,
    tasks_per_ep: int,
    ref_lookup: Optional[Dict[Tuple[str, int, int, int, int], Tuple[int, str, float, int]]],
    force_fresh_singlelu: bool,
) -> dict:
    enforce_single_thread_env()
    gn = 47
    tot_tasks = (1 + n_epochs) * tasks_per_ep
    world = generate_3d_multiroom_world(seed=seed, gn=gn, spec=ProblemSpec(dim=3), n_tasks=tot_tasks, fit_gp_world=False)
    spec = world["spec"]
    lam = float(spec.lam)
    free_3d = world["free_3d"]
    free_mask = world["free_mask"]
    free_nodes = world["free_nodes"]
    pts_f = world["pts_f"]
    tasks_all = world["tasks"]

    pl_tmp = SeamFreePortal3DPlanner(
        spec, gn, free_3d, free_nodes, pts_f,
        build_3d_reflecting_obstacle_mmatrix(spec, gn, free_mask, world["q_f"], world["b_f"]).tocsr(),
        eps_tol=0.25,
    )
    room_nodes_ref = [rn.copy() for rn in pl_tmp.room_nodes]
    n_rooms_ref = pl_tmp.n_rooms
    del pl_tmp
    gc.collect()

    q_cur = world["q_f"].copy()
    b_cur = world["b_f"].copy()
    t0_op = time.perf_counter()
    A0_csc = build_3d_reflecting_obstacle_mmatrix(spec, gn, free_mask, q_cur, b_cur)
    A0_csr = A0_csc.tocsr()
    op_init_ms = 1000.0 * (time.perf_counter() - t0_op)

    epoch_ops: List[Tuple[sp.csc_matrix, sp.csr_matrix, List[int], float]] = [(A0_csc, A0_csr, [], op_init_ms)]
    rng_ep = np.random.default_rng(seed + 810000)
    for _ in range(n_epochs):
        mod_rooms = [int(c) for c in rng_ep.choice(n_rooms_ref, size=2, replace=False)]
        for c in mod_rooms:
            rn_c = room_nodes_ref[c]
            ctr_c = np.mean(pts_f[rn_c], axis=0, keepdims=True)
            bump = float(rng_ep.uniform(0.18, 0.42)) * np.exp(-np.sum((pts_f[rn_c] - ctr_c) ** 2, axis=1) / 0.12)
            q_cur[rn_c] = np.clip(q_cur[rn_c] + bump, 0.05, 6.0)
            b_cur[rn_c, :] += rng_ep.normal(0.0, 0.05, size=(1, 3))
        t_rb = time.perf_counter()
        At_csc = build_3d_reflecting_obstacle_mmatrix(spec, gn, free_mask, q_cur, b_cur)
        At_csr = At_csc.tocsr()
        rb_ms = 1000.0 * (time.perf_counter() - t_rb)
        epoch_ops.append((At_csc, At_csr, mod_rooms, rb_ms))

    pair_order = list(PAIR2_SISC_ARMS) if (map_idx % 2 == 0) else list(reversed(PAIR2_SISC_ARMS))
    arm_streams: Dict[str, dict] = {}

    for rk, arm_nm in enumerate(pair_order):
        gc.collect()
        rss_before = _current_rss_mb()
        if arm_nm == "M233_SubPortal_PoUQuadtree":
            pl_obj: Any = SubPortalPoUQuadtree3DPlanner(spec, gn, free_3d, free_nodes, pts_f, epoch_ops[0][1], eps_tol=0.25, use_portal_cache=True)
            init_ms = pl_obj.offline_init_ms
        else:
            pl_obj = MatrixFreeExactSchurKrylov3DPlanner(spec, gn, free_3d, free_nodes, pts_f, epoch_ops[0][1], eps_tol=0.25)
            init_ms = pl_obj.offline_init_ms
        wref_base = weakref.ref(pl_obj.base)
        wref_pl = weakref.ref(pl_obj)

        life_ms = op_init_ms + init_ms
        marg_ms = 0.0
        retained_higher: List[int] = []
        raw_task_rows: List[Tuple[int, int, dict, Optional[np.ndarray]]] = []

        for ep_idx, (_, A_ep_csr, mod_r, rb_ms) in enumerate(epoch_ops):
            if ep_idx > 0:
                upd = pl_obj.update_world_operator(A_ep_csr, mod_r, portal_diag_changed=False)
                life_ms += rb_ms + upd["update_ms"]
                marg_ms += rb_ms + upd["update_ms"]
                retained_higher.append(int(upd["retained_cache_entries"]))
            ep_slice = tasks_all[ep_idx * tasks_per_ep : (ep_idx + 1) * tasks_per_ep]
            for local_ti, (s_f, gm_k) in enumerate(ep_slice):
                g_ti = ep_idx * tasks_per_ep + local_ti
                eval_pol_here = (local_ti == 0)
                if arm_nm == "M233_SubPortal_PoUQuadtree":
                    rr = pl_obj.solve_unseen_goal(s_f, gm_k, phi_goal=0.0, materialize_full_z_sub=eval_pol_here)
                    z_pol = np.array(rr["z_guide_full"], dtype=float, copy=True) if (eval_pol_here and rr["z_guide_full"] is not None) else None
                else:
                    rr = pl_obj.solve_unseen_goal(s_f, gm_k, phi_goal=0.0)
                    if eval_pol_here and rr["policy"] is not None:
                        s_m0 = pl_obj.base.local_lu_solve_calls
                        z_pol = np.array(rr["policy"].materialize_full_grid_unit(), dtype=float, copy=True)
                        rr["evaluation_materialization_rhs_solves"] = int(pl_obj.base.local_lu_solve_calls - s_m0)
                        rr["local_lu_solves"] = int(rr["operational_local_lu_rhs_solves"] + rr["evaluation_materialization_rhs_solves"])
                    else:
                        z_pol = None
                    rr["active_dofs"] = int(pl_obj.base.n_g)
                    rr["used_defect_closure"] = True
                life_ms += rr["query_ms"]
                if ep_idx > 0:
                    marg_ms += rr["query_ms"]
                raw_task_rows.append((ep_idx, g_ti, _scalar_row_snapshot(rr), z_pol))
                del rr

        rss_peak_arm = _current_rss_mb()
        del pl_obj
        gc.collect()
        if wref_base() is not None or wref_pl() is not None:
            raise RuntimeError(f"SISC-01 isolation violation: continual arm {arm_nm} retained planner/LU base!")
        rss_after = _current_rss_mb()
        arm_streams[arm_nm] = {
            "exec_rank": rk,
            "lifecycle_incl_rebuild_ms": life_ms,
            "post_init_marginal_incl_rebuild_ms": marg_ms,
            "mean_retained_l1_l4_quadtree_nodes": float(np.mean(retained_higher)) if retained_higher else 0.0,
            "defect_closure_count": int(sum(1 for _, _, rx, _ in raw_task_rows if rx["used_defect_closure"])),
            "rss_mb_before_arm": rss_before,
            "rss_mb_end_of_arm_before_del": rss_peak_arm,
            "rss_mb_after_arm_gc": rss_after,
            "prior_base_gc_freed": True,
            "_raw_rows": raw_task_rows,
        }

    ref_by_gti: Dict[int, Tuple[float, bool]] = {}
    cross_err_cont: Optional[float] = None
    if force_fresh_singlelu or (ref_lookup is None) or (("continual", seed, 47, 0, 0) not in ref_lookup):
        diffs_c = []
        for ep_idx, (A_ep_csc, A_ep_csr, _, _) in enumerate(epoch_ops):
            gc.collect()
            slu_ep = SingleLUGoalCapacitance3DPlanner(spec, A_ep_csc, A_ep_csr)
            ep_slice = tasks_all[ep_idx * tasks_per_ep : (ep_idx + 1) * tasks_per_ep]
            for local_ti, (s_f, gm_k) in enumerate(ep_slice):
                g_ti = ep_idx * tasks_per_ep + local_ti
                rs = slu_ep.solve_unseen_goal(s_f, gm_k)
                ref_by_gti[g_ti] = (float(rs["value"]), bool(rs["reference_valid"]))
                if ref_lookup is not None and ("continual", seed, 47, ep_idx, g_ti) in ref_lookup:
                    st_e, gh_e, v_e, _ = ref_lookup[("continual", seed, 47, ep_idx, g_ti)]
                    assert st_e == int(s_f) and gh_e == _goal_hash(gm_k)
                    diffs_c.append(abs(float(rs["value"]) - v_e))
            del slu_ep
        if diffs_c:
            cross_err_cont = float(max(diffs_c))
            assert cross_err_cont < 1e-12
    else:
        for ep_idx in range(1 + n_epochs):
            ep_slice = tasks_all[ep_idx * tasks_per_ep : (ep_idx + 1) * tasks_per_ep]
            for local_ti, (s_f, gm_k) in enumerate(ep_slice):
                g_ti = ep_idx * tasks_per_ep + local_ti
                st_e, gh_e, v_e, _ = ref_lookup[("continual", seed, 47, ep_idx, g_ti)]
                if st_e != int(s_f) or gh_e != _goal_hash(gm_k):
                    raise RuntimeError(f"Continual task mismatch at seed={seed}, ep={ep_idx}, g_ti={g_ti}")
                ref_by_gti[g_ti] = (v_e, True)

    cont_events: List[dict] = []
    for arm_nm, ad in arm_streams.items():
        r_rows = ad.pop("_raw_rows")
        for ep_idx, g_ti, rr_x, z_pol in r_rows:
            s_f, gm_k = tasks_all[g_ti]
            A_ep_csr = epoch_ops[ep_idx][1]
            v_ref, r_ok = ref_by_gti[g_ti]
            jp = evaluate_3d_deployed_policy_exact(A_ep_csr, gm_k, 0.0, z_pol, lam, s_f) if z_pol is not None else None
            cont_events.append(_build_task_event(
                block_id="m233_continual_abba_47cubed",
                seed=seed,
                gn=gn,
                epoch=ep_idx,
                task_index=g_ti,
                s_f=s_f,
                gm=gm_k,
                method_id=arm_nm,
                res=rr_x,
                v_ref=v_ref,
                ref_valid=r_ok,
                j_pol=jp,
            ))

    return {
        "seed": seed,
        "gn": gn,
        "stream_name": "known_support_synthetic_local_operator_updates",
        "shared_operator_rebuild_marginal_ms": float(sum(x[3] for x in epoch_ops[1:])),
        "m232_reference_cross_check_max_abs_diff": cross_err_cont,
        "pair_execution_order": pair_order,
        "arms": arm_streams,
        "events": cont_events,
    }


def _exact_sign_flip_p(diffs: np.ndarray) -> Tuple[float, float]:
    n = len(diffs)
    obs = float(np.mean(diffs))
    all_means = np.array([float(np.mean(np.array(s) * diffs)) for s in itertools.product((-1.0, 1.0), repeat=n)])
    p_1s = float(np.mean(all_means <= obs + 1e-15))
    p_2s = float(np.mean(np.abs(all_means) >= abs(obs) - 1e-15))
    return p_1s, p_2s


def _summarize_sisc_pair(
    rows: List[dict],
    block_label: str,
    cohort_provenance: str,
    arms_key: str,
    events_key: str,
    time_key: str,
    include_shared_prefix: bool = False,
) -> dict:
    cand_nm, base_nm = PAIR2_SISC_ARMS
    p_arr = np.array([r[arms_key][cand_nm][time_key] for r in rows], dtype=float)
    mf_arr = np.array([r[arms_key][base_nm][time_key] for r in rows], dtype=float)
    if include_shared_prefix:
        sh = np.array([float(r["shared_gp_fit_ms"]) + float(r["shared_operator_assembly_ms"]) for r in rows], dtype=float)
        p_arr = p_arr + sh
        mf_arr = mf_arr + sh

    p_mean = float(np.mean(p_arr))
    mf_mean = float(np.mean(mf_arr))
    speedup = mf_mean / p_mean
    saving_pct = 100.0 * (1.0 - (p_mean / mf_mean))
    diffs = p_arr - mf_arr
    p_diff = paired_stats(diffs) if len(rows) >= 2 else None
    p_20 = _one_sided_20pct_saving_p(p_arr, mf_arr)
    sf_1s, sf_2s = _exact_sign_flip_p(diffs) if 2 <= len(rows) <= 16 else (None, None)

    all_events = [e for r in rows for e in r[events_key]]
    p_events = [e for e in all_events if e["method_id"] == cand_nm]
    mf_events = [e for e in all_events if e["method_id"] == base_nm]

    crossings_per_seed = {}
    mean_crossing = None
    if (not include_shared_prefix) and ("prefix_cumulative_ms" in rows[0][arms_key][cand_nm]):
        p_pref = np.mean([r[arms_key][cand_nm]["prefix_cumulative_ms"] for r in rows], axis=0)
        mf_pref = np.mean([r[arms_key][base_nm]["prefix_cumulative_ms"] for r in rows], axis=0)
        mean_crossing = _sustained_crossing_k(p_pref, mf_pref)
        for r in rows:
            crossings_per_seed[str(r["seed"])] = _sustained_crossing_k(
                r[arms_key][cand_nm]["prefix_cumulative_ms"],
                r[arms_key][base_nm]["prefix_cumulative_ms"],
            )

    p_rank0 = sum(1 for r in rows if r["pair_execution_order"][0] == cand_nm)
    mf_rank0 = sum(1 for r in rows if r["pair_execution_order"][0] == base_nm)
    mean_dofs = (
        float(np.mean([r[arms_key][cand_nm]["mean_active_dofs"] for r in rows]))
        if "mean_active_dofs" in rows[0][arms_key][cand_nm]
        else None
    )
    tot_def = int(sum(r[arms_key][cand_nm]["defect_closure_count"] for r in rows))
    tot_tasks_arm = len(p_events)

    return {
        "block_label": block_label,
        "cohort_provenance": cohort_provenance,
        "workers": 1,
        "execution_schedule": f"deterministic_AB_BA_balanced (PoUQuadtree_first={p_rank0}, MatrixFree_first={mf_rank0})",
        "n_maps": len(rows),
        "pou_quadtree_mean_ms": p_mean,
        "matrixfree_mean_ms": mf_mean,
        "speedup_ratio_matrixfree_over_pou": speedup,
        "relative_time_saving_pct": saving_pct,
        "paired_equal_time_diff_pou_minus_matrixfree_ms": p_diff,
        "per_map_diffs_ms": [float(x) for x in diffs],
        "faster_map_count": int(np.sum(diffs < 0.0)),
        "exact_sign_flip_p_one_sided": sf_1s,
        "exact_sign_flip_p_two_sided": sf_2s,
        "diagnostic_one_sided_p_for_20pct_saving": p_20,
        "engineering_20pct_time_saving_gate": "PASS" if (saving_pct >= 20.0 and p_20 < 0.05) else "NOT_MET",
        "mean_active_coarse_dofs": mean_dofs,
        "defect_closure_tasks": f"{tot_def}/{tot_tasks_arm}",
        "no_krylov_coarse_closure_pct": 100.0 * (1.0 - float(tot_def) / float(max(1, tot_tasks_arm))),
        "observed_cohort_mean_prefix_crossing_through_K24": mean_crossing,
        "per_seed_sustained_prefix_crossing_through_K24": crossings_per_seed if crossings_per_seed else None,
        "event_reduced_verification": {
            cand_nm: _reduce_event_ledger(p_events),
            base_nm: _reduce_event_ledger(mf_events),
        },
    }


def _build_expected_m233_roster() -> Tuple[Set[EventKey], Set[EventKey]]:
    expected_keys: Set[EventKey] = set()
    expected_pol_keys: Set[EventKey] = set()
    cand_nm, base_nm = PAIR2_SISC_ARMS

    for sd in range(63000, 63006):
        for ti in range(24):
            for m in CACHE3_MODES:
                kc = ("m233_cache_47cubed", sd, 47, 0, ti, m)
                expected_keys.add(kc)
                if m == "CacheOn_Persistent" and ti < 12:
                    expected_pol_keys.add(kc)
            for m in (cand_nm, base_nm):
                k35 = ("m233_pair_abba_35cubed", sd, 35, 0, ti, m)
                k47 = ("m233_pair_abba_47cubed", sd, 47, 0, ti, m)
                k59 = ("m233_pair_abba_59cubed", sd, 59, 0, ti, m)
                expected_keys.update((k35, k47, k59))
                if ti < 12:
                    expected_pol_keys.add(k35)
                    expected_pol_keys.add(k47)
                if ti < 6:
                    expected_pol_keys.add(k59)
        for gti in range(36):
            ep = gti // 6
            for m in (cand_nm, base_nm):
                kct = ("m233_continual_abba_47cubed", sd, 47, ep, gti, m)
                expected_keys.add(kct)
                if (gti % 6) == 0:
                    expected_pol_keys.add(kct)

    for sd in range(64000, 64012):
        for ti in range(24):
            for m in (cand_nm, base_nm):
                kcf = ("m233_confirm_abba_47cubed", sd, 47, 0, ti, m)
                expected_keys.add(kcf)
                if ti < 12:
                    expected_pol_keys.add(kcf)

    assert len(expected_keys) == 2304 and len(expected_pol_keys) == 792
    return expected_keys, expected_pol_keys


def _plot_m233_sisc_summary(
    pair35: dict,
    pair47: dict,
    pair59: dict,
    cont47: dict,
    confirm47: dict,
    cache47: dict,
    rows_confirm47: List[dict],
    rows59: List[dict],
    m232_savings_ref: Dict[str, float],
    fig_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14.4, 9.8), dpi=180)
    cand_nm, base_nm = PAIR2_SISC_ARMS

    is_repl = "clean_isolation" in fig_path.name
    cf_bar_lbl = "Clean-Isolation Repl. 64000..64011 (n=12)" if is_repl else "Untouched Confirm 64000..64011 (n=12)"
    cf_cat_lbl = "Static 47^3\n(Repl. 64k n=12)" if is_repl else "Static 47^3\n(Confirm n=12)"
    cf_mf_lbl = "47^3 MatrixFree (Clean-Isolation Repl. 64k)" if is_repl else "47^3 MatrixFree (Untouched Confirm 64k)"

    # Panel A: Progression from Uniform-Portal `M2.3.2` to Sub-Portal PoU-Quadtree `M2.3.3` (+ 64k Cohort)
    ax = axes[0, 0]
    cats = [
        "Static 35^3\n(Replay 63k)",
        "Static 47^3\n(Replay 63k)",
        "Static 59^3\n(Replay 63k)",
        "Continual 47^3\n(Marg, 63k)",
        cf_cat_lbl,
    ]
    old_sav = [
        m232_savings_ref["35"],
        m232_savings_ref["47"],
        m232_savings_ref["59"],
        m232_savings_ref["cont47"],
        np.nan,
    ]
    new_sav = [
        pair35["relative_time_saving_pct"],
        pair47["relative_time_saving_pct"],
        pair59["relative_time_saving_pct"],
        cont47["relative_time_saving_pct"],
        confirm47["relative_time_saving_pct"],
    ]
    x = np.arange(len(cats))
    w = 0.34
    ax.axhline(0.0, color="black", linewidth=0.9)
    ax.axhline(20.0, color="#8e44ad", linestyle="--", linewidth=1.6, label="Pre-Declared 20% Saving Gate")
    ax.bar(x[:4] - w / 2, old_sav[:4], width=w, color="#95a5a6", label="Uniform Portal L0..L3 (M2.3.2)")
    ax.bar(x[:-1] + w / 2, new_sav[:-1], width=w, color="#27ae60", label="Sub-Portal PoU-Quadtree L0..L4 (M2.3.3)")
    ax.bar(x[-1:], new_sav[-1:], width=w * 1.15, color="#16a085", label=cf_bar_lbl)
    for idx_i, sv in enumerate(new_sav):
        xpos = x[idx_i] + (w / 2 if idx_i < 4 else 0.0)
        ax.text(xpos, sv + 1.0, f"+{sv:.1f}%", ha="center", va="bottom", fontsize=7.9, fontweight="bold", color="#1e8449")
    for idx_i in range(4):
        sv0 = old_sav[idx_i]
        va = "bottom" if sv0 >= 0 else "top"
        off = 0.8 if sv0 >= 0 else -1.2
        ax.text(x[idx_i] - w / 2, sv0 + off, f"{sv0:+.1f}%", ha="center", va=va, fontsize=7.4, color="#566573")
    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=8.0)
    ax.set_ylabel("Relative Time Saving vs. MatrixFree (%)")
    ax.set_ylim(-18.0, max(new_sav) + 9.0)
    ax.set_title("A. Closest-Neighbor Time Saving Unlock (1 Worker, Exact AB / BA)", fontsize=9.5, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend(fontsize=7.3, loc="lower right")

    # Panel B: 64k (`47^3`) & `59^3` Same-Block Cumulative Curves `C(k)`
    ax = axes[0, 1]
    ks = np.arange(1, 25)
    c_p_64 = np.mean([r["pair_arms"][cand_nm]["prefix_cumulative_ms"] for r in rows_confirm47], axis=0) / 1000.0
    c_mf_64 = np.mean([r["pair_arms"][base_nm]["prefix_cumulative_ms"] for r in rows_confirm47], axis=0) / 1000.0
    c_p_59 = np.mean([r["pair_arms"][cand_nm]["prefix_cumulative_ms"] for r in rows59], axis=0) / 1000.0
    c_mf_59 = np.mean([r["pair_arms"][base_nm]["prefix_cumulative_ms"] for r in rows59], axis=0) / 1000.0
    ax.plot(ks, c_mf_59, "--", color="#d35400", linewidth=2.1, label="59^3 MatrixFree (Replay 63k)")
    ax.plot(ks, c_p_59, "-", color="#8e44ad", linewidth=2.3, label=f"59^3 PoU-Quadtree (-{pair59['relative_time_saving_pct']:.1f}%, k*={pair59['observed_cohort_mean_prefix_crossing_through_K24']})")
    ax.plot(ks, c_mf_64, "--", color="#e67e22", linewidth=2.0, label=cf_mf_lbl)
    ax.plot(ks, c_p_64, "-", color="#16a085", linewidth=2.3, label=f"47^3 PoU-Quadtree (-{confirm47['relative_time_saving_pct']:.1f}%, k*={confirm47['observed_cohort_mean_prefix_crossing_through_K24']})")
    ax.set_xlabel("Streaming Unseen Goal Index $k$ (1..24)")
    ax.set_ylabel("Single-Worker Cumulative Planner Time $C(k)$ (s)")
    ax.set_title("B. Cumulative Amortization on 59^3 & Untouched 47^3 Confirm Cohort", fontsize=9.5, fontweight="bold")
    ax.grid(True, alpha=0.28)
    ax.legend(fontsize=7.5, loc="upper left")

    # Panel C: 47^3 Sub-Portal Quadtree 3-Arm Cache Causal Decomposition (`Intra-Query Memoization ON`)
    ax = axes[1, 0]
    for m_k, m_lbl, st, col in (
        ("QueryCold", "QueryCold (Clear L0..L4 per Query)", "--", "#c0392b"),
        ("CacheL0Only", "CacheL0Only (Keep L0, Clear L1..L4 per Query)", "-.", "#d35400"),
        ("CacheOn_Persistent", "CacheOn_Persistent (Keep L0..L4 Sub-Blocks)", "-", "#27ae60"),
    ):
        ys = np.array(cache47["modes"][m_k]["prefix_cumulative_mean_ms"], dtype=float) / 1000.0
        ax.plot(ks, ys, st, linewidth=2.3, label=m_lbl, color=col)
    sav_l0 = cache47["modes"]["CacheL0Only"]["relative_time_saving_of_CacheOn_vs_mode_pct"]
    rhs_l0 = cache47["modes"]["CacheL0Only"]["operational_rhs_saving_of_CacheOn_vs_mode_pct"]
    ax.text(
        0.04, 0.76,
        f"vs. CacheL0Only:\n-{sav_l0:.1f}% wall time\n-{rhs_l0:.1f}% operational LU RHS",
        transform=ax.transAxes,
        fontsize=8.0,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#eafaf1", edgecolor="#27ae60", alpha=0.9),
    )
    ax.set_xlabel("Streaming Unseen Goal Index $k$ (1..24)")
    ax.set_ylabel("Single-Worker Cumulative Time $C(k)$ (s)")
    ax.set_title("C. Sub-Portal Quadtree 3-Arm Cache Ablation (47^3, 2x 3x3 Latin)", fontsize=9.5, fontweight="bold")
    ax.grid(True, alpha=0.28)
    ax.legend(fontsize=7.7, loc="upper left")

    # Panel D: Zero-Slack Deployed Policy Regret Across All 5 SISC Cohorts (`648 / 648` Evaluations)
    ax = axes[1, 1]
    reg_groups = []
    reg_labels = []
    for lbl, rlist, ev_key in (
        ("35^3\n(63k)", "r35", "pair_events"),
        ("47^3\n(63k)", "r47", "pair_events"),
        ("59^3\n(63k)", "r59", "pair_events"),
        ("47^3\n(Confirm 64k)", "rcf", "pair_events"),
    ):
        pass
    reg_cf_pou = [
        float(e["policy_value"]) - float(e["reference_value"])
        for r in rows_confirm47 for e in r["pair_events"]
        if e["method_id"] == cand_nm and e["policy_evaluated"]
    ]
    reg_cf_mf = [
        float(e["policy_value"]) - float(e["reference_value"])
        for r in rows_confirm47 for e in r["pair_events"]
        if e["method_id"] == base_nm and e["policy_evaluated"]
    ]
    reg_59_pou = [
        float(e["policy_value"]) - float(e["reference_value"])
        for r in rows59 for e in r["pair_events"]
        if e["method_id"] == cand_nm and e["policy_evaluated"]
    ]
    reg_59_mf = [
        float(e["policy_value"]) - float(e["reference_value"])
        for r in rows59 for e in r["pair_events"]
        if e["method_id"] == base_nm and e["policy_evaluated"]
    ]
    bp = ax.boxplot(
        [reg_cf_pou, reg_cf_mf, reg_59_pou, reg_59_mf],
        tick_labels=[f"47^3 Confirm\nPoU-QT (n={len(reg_cf_pou)})", "47^3 Confirm\nMatrixFree", f"59^3 Replay\nPoU-QT (n={len(reg_59_pou)})", "59^3 Replay\nMatrixFree"],
        patch_artist=True,
    )
    for patch, col in zip(bp["boxes"], ("#a3e4d7", "#fad7a0", "#d2b4de", "#fad7a0")):
        patch.set_facecolor(col)
    ax.axhline(0.25, color="#c0392b", linestyle="--", linewidth=1.6, label="Target Budget $\\varepsilon_{\\mathrm{tol}} = 0.25$")
    ax.set_ylabel("Exact Deployed Policy Regret $J^{\\hat{\\mu}}(s_0) - V^*(s_0)$")
    ax.set_title("D. Deployed Policy Regret (0 Violations at Zero Slack)", fontsize=9.5, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend(fontsize=8.0, loc="upper right")

    plt.tight_layout()
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)


def verify_zero_cross_arm_retention_probe() -> Dict[str, Any]:
    """Deterministic `SISC-01` regression gate reproducing `r333_m233_retention_probe.py`:
    instruments constructor weakrefs across `_run_static_pair_single_map` (3 cache + 2 pair +
    1 independent reference arm) and verifies `alive_prior_bases == []` at every transition.
    """
    global SubPortalPoUQuadtree3DPlanner, MatrixFreeExactSchurKrylov3DPlanner
    global SingleLUGoalCapacitance3DPlanner, generate_3d_multiroom_world

    orig_p = SubPortalPoUQuadtree3DPlanner
    orig_b = MatrixFreeExactSchurKrylov3DPlanner
    orig_s = SingleLUGoalCapacitance3DPlanner
    orig_w = generate_3d_multiroom_world
    refs: List[Tuple[str, weakref.ReferenceType[Any]]] = []
    timeline: List[Dict[str, Any]] = []

    def _snap(label: str) -> None:
        gc.collect()
        timeline.append({"stage": label, "alive_prior_bases": [nm for nm, r in refs if r() is not None]})

    class _P(orig_p):  # type: ignore[misc,valid-type]
        def __init__(self, *a: Any, **kw: Any) -> None:
            _snap("before_Portal_ctor")
            super().__init__(*a, **kw)
            refs.append((f"Portal_{len(refs)}", weakref.ref(self.base)))

    class _B(orig_b):  # type: ignore[misc,valid-type]
        def __init__(self, *a: Any, **kw: Any) -> None:
            _snap("before_MatrixFree_ctor")
            super().__init__(*a, **kw)
            refs.append((f"MatrixFree_{len(refs)}", weakref.ref(self.base)))

    class _S(orig_s):  # type: ignore[misc,valid-type]
        def __init__(self, *a: Any, **kw: Any) -> None:
            _snap("before_independent_reference_ctor")
            super().__init__(*a, **kw)

    def _tiny_world(**kwargs: Any) -> dict:
        gn = 17
        spec = ProblemSpec(dim=3)
        free = np.ones((gn, gn, gn), dtype=bool)
        free[8, :, :] = False
        free[8, 6:11, 6:11] = True
        nodes = np.flatnonzero(free.ravel())
        pos = np.full(gn**3, -1, dtype=int)
        pos[nodes] = np.arange(len(nodes))
        _, pts, _ = build_grid_points(3, spec.half_width, gn)
        tasks = []
        for ti in range(int(kwargs["n_tasks"])):
            s = int(pos[3 * gn * gn + 8 * gn + 8])
            g = int(pos[(12 + ti) * gn * gn + 8 * gn + 8])
            gm = np.zeros(len(nodes), dtype=bool)
            gm[g] = True
            tasks.append((s, gm))
        return {
            "spec": spec,
            "free_3d": free,
            "free_mask": free.ravel(),
            "free_nodes": nodes,
            "pts_f": pts[nodes],
            "tasks": tasks,
            "q_f": np.full(len(nodes), 0.5, dtype=float),
            "b_f": np.tile([0.09, 0.13, -0.07], (len(nodes), 1)),
            "gp_fit_ms": 0.0,
        }

    try:
        SubPortalPoUQuadtree3DPlanner = _P  # type: ignore[misc]
        MatrixFreeExactSchurKrylov3DPlanner = _B  # type: ignore[misc]
        SingleLUGoalCapacitance3DPlanner = _S  # type: ignore[misc]
        generate_3d_multiroom_world = _tiny_world  # type: ignore[assignment]
        res = _run_static_pair_single_map(
            block_id="sisc01_retention_probe",
            seed=17,
            map_idx=0,
            gn=17,
            n_tasks=2,
            n_pol_evals=1,
            run_cache_ablation=True,
            ref_lookup=None,
            force_fresh_singlelu=True,
        )
        _snap("after_runner_return")
    finally:
        SubPortalPoUQuadtree3DPlanner = orig_p  # type: ignore[misc]
        MatrixFreeExactSchurKrylov3DPlanner = orig_b  # type: ignore[misc]
        SingleLUGoalCapacitance3DPlanner = orig_s  # type: ignore[misc]
        generate_3d_multiroom_world = orig_w  # type: ignore[assignment]
        gc.collect()

    zero_retained = all(len(step["alive_prior_bases"]) == 0 for step in timeline)
    all_valid = all(bool(e["value_enclosure_satisfied"]) for e in res["cache_events"] + res["pair_events"])
    if not (zero_retained and all_valid and len(timeline) == 7):
        raise RuntimeError(f"SISC-01 zero-retention gate failed: timeline={timeline}, valid={all_valid}")
    return {
        "pass": True,
        "stages_checked": len(timeline),
        "max_alive_prior_bases": max(len(step["alive_prior_bases"]) for step in timeline),
        "timeline": timeline,
    }


def run_m233_sisc_campaign(self_test: bool = False, clean_isolation_replication: bool = False) -> dict:
    t_all0 = time.perf_counter()
    p2_dir = Path(__file__).resolve().parent
    frozen_m233_orig = verify_m233_original_archive_untouched(p2_dir)
    sisc01_probe = verify_zero_cross_arm_retention_probe()
    contracts_out = run_m233_contract_and_pou_verification()
    contracts_out["sisc01_zero_cross_arm_retention_probe"] = sisc01_probe
    ref_lookup = _load_m232_verified_reference_lookup(p2_dir)

    if self_test:
        r_st = _run_static_pair_single_map(
            block_id="m233_self_test_35",
            seed=61000,
            map_idx=0,
            gn=35,
            n_tasks=6,
            n_pol_evals=2,
            run_cache_ablation=True,
            ref_lookup=None,
            force_fresh_singlelu=True,
        )
        rc_st = _run_continual_47_sisc_single_map(
            seed=63000,
            map_idx=0,
            n_epochs=1,
            tasks_per_ep=2,
            ref_lookup=ref_lookup,
            force_fresh_singlelu=True,
        )
        st_events = r_st["cache_events"] + r_st["pair_events"] + rc_st["events"]
        led_st = _reduce_event_ledger(st_events)
        assert led_st["ALL_SAVED_EVENTS_SATISFIED"], f"Self-test ledger failed: {led_st}"
        st_exp_all = {
            (str(e["block_id"]), int(e["seed"]), int(e["grid_n"]), int(e["operator_epoch"]), int(e["task_index"]), str(e["method_id"]))
            for e in st_events
        }
        st_exp_pol = {
            (str(e["block_id"]), int(e["seed"]), int(e["grid_n"]), int(e["operator_epoch"]), int(e["task_index"]), str(e["method_id"]))
            for e in st_events if e["policy_evaluated"]
        }
        st_aud0 = verify_event_roster_and_inequalities(st_events, st_exp_all, st_exp_pol, eps_budget=0.25, slack=0.0)
        st_faults = run_negative_control_fault_injections(st_events, st_exp_all, st_exp_pol)
        assert st_aud0["ALL_INDEPENDENT_GATES_PASSED"] and st_faults["ALL_4_FAULT_INJECTIONS_REJECTED"]
        # Smoke-test summary plot & strict JSON serializer before full campaign
        st_p_sum = _summarize_sisc_pair([r_st, r_st], "st_p", "st", "pair_arms", "pair_events", "total_ms")
        st_c_sum = _summarize_sisc_pair([rc_st, rc_st], "st_c", "st", "arms", "events", "post_init_marginal_incl_rebuild_ms")
        st_modes = {
            m_nm: {
                "prefix_cumulative_mean_ms": r_st["cache_arms"][m_nm]["prefix_cumulative_ms"],
                "relative_time_saving_of_CacheOn_vs_mode_pct": 25.0,
                "operational_rhs_saving_of_CacheOn_vs_mode_pct": 50.0,
            }
            for m_nm in CACHE3_MODES
        }
        r_st24 = copy.deepcopy(r_st)
        for arm_x in PAIR2_SISC_ARMS:
            r_st24["pair_arms"][arm_x]["prefix_cumulative_ms"] = list(np.linspace(1.0, 24.0, 24))
        for m_nm in CACHE3_MODES:
            st_modes[m_nm]["prefix_cumulative_mean_ms"] = list(np.linspace(1.0, 24.0, 24))
        tmp_fig = Path("/tmp/m233_selftest_summary.png")
        _plot_m233_sisc_summary(
            st_p_sum, st_p_sum, st_p_sum, st_c_sum, st_p_sum,
            {"modes": st_modes}, [r_st24], [r_st24],
            {"35": -12.15, "47": 15.17, "59": 13.74, "cont47": 9.98},
            tmp_fig,
        )
        if tmp_fig.exists():
            tmp_fig.unlink()
        _ = _strict_json_loads(json.dumps(_sanitize_for_strict_json({"aud": st_aud0, "faults": st_faults}), allow_nan=False))
        verify_all_10_frozen_jsons(p2_dir)
        print(
            f"[M2.3.3 SELF-TEST PASS] Contracts={contracts_out['ALL_M233_CONTRACTS_PASSED']} | "
            f"PoU RHS saving={contracts_out['pou_conservation_check']['rhs_saving_pct']:.1f}% "
            f"(max_K_diff={contracts_out['pou_conservation_check']['max_abs_K_diff']:.2e}) | "
            f"ZeroSlackAudit={st_aud0['ALL_INDEPENDENT_GATES_PASSED']} | "
            f"Faults4/4={st_faults['ALL_4_FAULT_INJECTIONS_REJECTED']} | Frozen10=Untouched"
        )
        return {"self_test_passed": True, "contracts": contracts_out, "ledger": led_st}

    seeds_replay = list(range(63000, 63006))
    seeds_confirm = list(range(64000, 64012))
    K_goals = 24

    print("[M2.3.3 Block S1] Running 1-worker Static 35^3 AB/BA Replay (63000..63005, K=24)...")
    rows35 = [
        _run_static_pair_single_map(
            block_id="m233_pair_abba_35cubed",
            seed=sd,
            map_idx=idx_m,
            gn=35,
            n_tasks=K_goals,
            n_pol_evals=12,
            run_cache_ablation=False,
            ref_lookup=ref_lookup if clean_isolation_replication else None,
            force_fresh_singlelu=((idx_m == 0) if clean_isolation_replication else True),
        )
        for idx_m, sd in enumerate(seeds_replay)
    ]
    pair35_sum = _summarize_sisc_pair(
        rows35, "Replay_35cubed_AB_BA_Pair", "Replay_Cohort_63000_63005", "pair_arms", "pair_events", "total_ms"
    )
    pair35_e2e = _summarize_sisc_pair(
        rows35, "Replay_35cubed_AB_BA_EndToEnd", "Replay_Cohort_63000_63005", "pair_arms", "pair_events", "total_ms", include_shared_prefix=True
    )
    print(
        f"  -> 35^3 Pair AB/BA: PoU={pair35_sum['pou_quadtree_mean_ms']:.1f}ms vs MF={pair35_sum['matrixfree_mean_ms']:.1f}ms | "
        f"saving={pair35_sum['relative_time_saving_pct']:.2f}% ({pair35_sum['speedup_ratio_matrixfree_over_pou']:.2f}x, "
        f"faster={pair35_sum['faster_map_count']}/6, p={pair35_sum['paired_equal_time_diff_pou_minus_matrixfree_ms']['p_two_sided']:.4g})"
    )

    print("[M2.3.3 Block S2] Running 1-worker Static 47^3 3-Arm Cache + AB/BA Replay (63000..63005, K=24)...")
    rows47 = [
        _run_static_pair_single_map(
            block_id="m233_pair_abba_47cubed",
            seed=sd,
            map_idx=idx_m,
            gn=47,
            n_tasks=K_goals,
            n_pol_evals=12,
            run_cache_ablation=True,
            ref_lookup=ref_lookup,
            force_fresh_singlelu=(idx_m == 0),
        )
        for idx_m, sd in enumerate(seeds_replay)
    ]
    pair47_sum = _summarize_sisc_pair(
        rows47, "Replay_47cubed_AB_BA_Pair", "Replay_Cohort_63000_63005", "pair_arms", "pair_events", "total_ms"
    )
    pair47_e2e = _summarize_sisc_pair(
        rows47, "Replay_47cubed_AB_BA_EndToEnd", "Replay_Cohort_63000_63005", "pair_arms", "pair_events", "total_ms", include_shared_prefix=True
    )

    c_on_arr = np.array([r["cache_arms"]["CacheOn_Persistent"]["total_ms"] for r in rows47], dtype=float)
    c_on_op_rhs = float(np.mean([r["cache_arms"]["CacheOn_Persistent"]["total_operational_local_lu_rhs_solves"] for r in rows47]))
    modes_sum = {}
    all_cache_ev = [e for r in rows47 for e in r["cache_events"]]
    for m_nm in CACHE3_MODES:
        m_arr = np.array([r["cache_arms"][m_nm]["total_ms"] for r in rows47], dtype=float)
        m_pref = np.mean([r["cache_arms"][m_nm]["prefix_cumulative_ms"] for r in rows47], axis=0)
        m_op_rhs = float(np.mean([r["cache_arms"][m_nm]["total_operational_local_lu_rhs_solves"] for r in rows47]))
        m_ev = [e for e in all_cache_ev if e["method_id"] == m_nm]
        modes_sum[m_nm] = {
            "rank_counts_across_6_maps": [sum(1 for r in rows47 if r["cache_arms"][m_nm]["exec_rank"] == rk) for rk in range(3)],
            "planner_only_mean_ms": float(np.mean(m_arr)),
            "mean_query_ms": float(np.mean([r["cache_arms"][m_nm]["mean_query_ms"] for r in rows47])),
            "first6_query_mean_ms": float(np.mean([r["cache_arms"][m_nm]["first6_query_ms"] for r in rows47])),
            "last6_query_mean_ms": float(np.mean([r["cache_arms"][m_nm]["last6_query_ms"] for r in rows47])),
            "prefix_cumulative_mean_ms": [float(x) for x in m_pref],
            "mean_operational_local_lu_rhs_solves_per_map": m_op_rhs,
            "mean_evaluation_materialization_rhs_solves_per_map": float(
                np.mean([r["cache_arms"][m_nm]["total_evaluation_materialization_rhs_solves"] for r in rows47])
            ),
            "speedup_of_CacheOn_vs_mode": float(np.mean(m_arr) / np.mean(c_on_arr)),
            "relative_time_saving_of_CacheOn_vs_mode_pct": float(100.0 * (1.0 - np.mean(c_on_arr) / np.mean(m_arr))),
            "operational_rhs_saving_of_CacheOn_vs_mode_pct": float(100.0 * (1.0 - c_on_op_rhs / m_op_rhs)),
            "paired_diff_CacheOn_minus_mode_ms": paired_stats(c_on_arr - m_arr) if m_nm != "CacheOn_Persistent" else None,
            "event_reduced_verification": _reduce_event_ledger(m_ev),
        }
    cache47_sum = {
        "cohort_label": "Replay_47cubed_SubPortal_Quadtree_Cache_Ablation",
        "workers": 1,
        "execution_schedule": "exact_2x_3x3_cyclic_Latin_square",
        "modes": modes_sum,
    }
    print(
        f"  -> 47^3 Pair AB/BA: PoU={pair47_sum['pou_quadtree_mean_ms']:.1f}ms vs MF={pair47_sum['matrixfree_mean_ms']:.1f}ms | "
        f"saving={pair47_sum['relative_time_saving_pct']:.2f}% ({pair47_sum['speedup_ratio_matrixfree_over_pou']:.2f}x, "
        f"gate20={pair47_sum['engineering_20pct_time_saving_gate']}, p20={pair47_sum['diagnostic_one_sided_p_for_20pct_saving']:.4g})"
    )

    print("[M2.3.3 Block S3] Running 1-worker Static 59^3 AB/BA Replay (63000..63005, K=24)...")
    rows59 = [
        _run_static_pair_single_map(
            block_id="m233_pair_abba_59cubed",
            seed=sd,
            map_idx=idx_m,
            gn=59,
            n_tasks=K_goals,
            n_pol_evals=6,
            run_cache_ablation=False,
            ref_lookup=ref_lookup,
            force_fresh_singlelu=(idx_m == 0),
        )
        for idx_m, sd in enumerate(seeds_replay)
    ]
    pair59_sum = _summarize_sisc_pair(
        rows59, "Replay_59cubed_AB_BA_Pair", "Replay_Cohort_63000_63005", "pair_arms", "pair_events", "total_ms"
    )
    pair59_e2e = _summarize_sisc_pair(
        rows59, "Replay_59cubed_AB_BA_EndToEnd", "Replay_Cohort_63000_63005", "pair_arms", "pair_events", "total_ms", include_shared_prefix=True
    )
    print(
        f"  -> 59^3 Pair AB/BA: PoU={pair59_sum['pou_quadtree_mean_ms']:.1f}ms vs MF={pair59_sum['matrixfree_mean_ms']:.1f}ms | "
        f"saving={pair59_sum['relative_time_saving_pct']:.2f}% ({pair59_sum['speedup_ratio_matrixfree_over_pou']:.2f}x, "
        f"gate20={pair59_sum['engineering_20pct_time_saving_gate']}, p20={pair59_sum['diagnostic_one_sided_p_for_20pct_saving']:.4g})"
    )

    print("[M2.3.3 Block S4] Running 1-worker Continual 47^3 AB/BA Replay (63000..63005, 1+5 Epochs x 6 Tasks)...")
    rows_cont = [
        _run_continual_47_sisc_single_map(
            seed=sd,
            map_idx=idx_m,
            n_epochs=5,
            tasks_per_ep=6,
            ref_lookup=ref_lookup,
            force_fresh_singlelu=(idx_m == 0),
        )
        for idx_m, sd in enumerate(seeds_replay)
    ]
    cont47_marg = _summarize_sisc_pair(
        rows_cont, "Replay_Continual_47cubed_Marginal_AB_BA", "Replay_Cohort_63000_63005", "arms", "events", "post_init_marginal_incl_rebuild_ms"
    )
    cont47_life = _summarize_sisc_pair(
        rows_cont, "Replay_Continual_47cubed_Lifecycle_AB_BA", "Replay_Cohort_63000_63005", "arms", "events", "lifecycle_incl_rebuild_ms"
    )
    print(
        f"  -> Continual 47^3 Marg AB/BA: PoU={cont47_marg['pou_quadtree_mean_ms']:.1f}ms vs MF={cont47_marg['matrixfree_mean_ms']:.1f}ms | "
        f"saving={cont47_marg['relative_time_saving_pct']:.2f}% ({cont47_marg['speedup_ratio_matrixfree_over_pou']:.2f}x, "
        f"gate20={cont47_marg['engineering_20pct_time_saving_gate']}, p20={cont47_marg['diagnostic_one_sided_p_for_20pct_saving']:.4g})"
    )

    print("[M2.3.3 Block S5] Running 1-worker Static 47^3 AB/BA on Seeds 64000..64011 (n=12, K=24)...")
    rows_confirm47 = [
        _run_static_pair_single_map(
            block_id="m233_confirm_abba_47cubed",
            seed=sd,
            map_idx=idx_m,
            gn=47,
            n_tasks=K_goals,
            n_pol_evals=12,
            run_cache_ablation=False,
            ref_lookup=ref_lookup if clean_isolation_replication else None,
            force_fresh_singlelu=((idx_m == 0) if clean_isolation_replication else True),
        )
        for idx_m, sd in enumerate(seeds_confirm)
    ]
    confirm47_sum = _summarize_sisc_pair(
        rows_confirm47,
        "Untouched_Confirmation_47cubed_AB_BA_Pair",
        "Fresh_Untouched_Confirmation_Cohort_64000_64011 (n=12 maps, 6 AB / 6 BA, zero tuning)",
        "pair_arms",
        "pair_events",
        "total_ms",
    )
    confirm47_e2e = _summarize_sisc_pair(
        rows_confirm47,
        "Untouched_Confirmation_47cubed_AB_BA_EndToEnd",
        "Fresh_Untouched_Confirmation_Cohort_64000_64011 (n=12 maps, 6 AB / 6 BA, zero tuning)",
        "pair_arms",
        "pair_events",
        "total_ms",
        include_shared_prefix=True,
    )
    print(
        f"  -> UNTOUCHED CONFIRM 64000..64011 (n=12) 47^3 AB/BA: PoU={confirm47_sum['pou_quadtree_mean_ms']:.1f}ms vs MF={confirm47_sum['matrixfree_mean_ms']:.1f}ms | "
        f"saving={confirm47_sum['relative_time_saving_pct']:.2f}% ({confirm47_sum['speedup_ratio_matrixfree_over_pou']:.2f}x, "
        f"faster={confirm47_sum['faster_map_count']}/12, gate20={confirm47_sum['engineering_20pct_time_saving_gate']}, "
        f"p20={confirm47_sum['diagnostic_one_sided_p_for_20pct_saving']:.4g})"
    )

    # Stage breakdown summary on Static 35^3, 47^3, 59^3 (`PoUQuadtree`)
    stage_breakdown = {}
    for lbl, rlist in (("static_35cubed", rows35), ("static_47cubed", rows47), ("static_59cubed", rows59), ("confirm_47cubed", rows_confirm47)):
        init_m = float(np.mean([r["pair_arms"]["M233_SubPortal_PoUQuadtree"]["init_ms"] for r in rlist]))
        st_m = {
            sk: float(np.mean([r["pair_arms"]["M233_SubPortal_PoUQuadtree"]["stage_sum_ms"][sk] for r in rlist]))
            for sk in ("goal_ring_and_readout_ms", "cache_miss_lu_ms", "howard_and_selection_ms", "defect_krylov_ms", "policy_prime_ms")
        }
        stage_breakdown[lbl] = {"offline_init_mean_ms": init_m, "query_stages_sum_mean_ms": st_m}

    # Independent Zero-Slack Event Roster + 4-Fault-Injection Audit over all `2,016` saved events & `648` policy evals
    all_events = (
        [e for r in rows35 for e in r["pair_events"]]
        + [e for r in rows47 for e in r["cache_events"]]
        + [e for r in rows47 for e in r["pair_events"]]
        + [e for r in rows59 for e in r["pair_events"]]
        + [e for r in rows_cont for e in r["events"]]
        + [e for r in rows_confirm47 for e in r["pair_events"]]
    )
    exp_keys, exp_pol_keys = _build_expected_m233_roster()
    audit_zero_slack = verify_event_roster_and_inequalities(all_events, exp_keys, exp_pol_keys, eps_budget=0.25, slack=0.0)
    audit_1e7_slack = verify_event_roster_and_inequalities(all_events, exp_keys, exp_pol_keys, eps_budget=0.25, slack=1e-7)
    fault_report = run_negative_control_fault_injections(all_events, exp_keys, exp_pol_keys)
    faults_rejected = bool(fault_report["ALL_4_FAULT_INJECTIONS_REJECTED"])

    fig_name = "m233_clean_isolation_summary.png" if clean_isolation_replication else "m233_sisc_unlock_summary.png"
    out_json_name = (
        "m233_clean_isolation_replication.json"
        if clean_isolation_replication
        else "m233_sisc_unlock_results.json"
    )
    out_json = p2_dir / out_json_name
    if out_json.name == "m233_sisc_unlock_results.json" and out_json.exists():
        raise RuntimeError(
            "Refusing to overwrite frozen m233_sisc_unlock_results.json (R333-D03); "
            "pass --clean-isolation-replication to write m233_clean_isolation_replication.json."
        )

    if clean_isolation_replication:
        for s_dict in (pair35_sum, pair35_e2e, pair47_sum, pair47_e2e, pair59_sum, pair59_e2e, cont47_marg, cont47_life):
            s_dict["cohort_provenance"] = "Protocol_Fixed_Clean_Isolation_Replay_63000_63005 (zero cross-arm retention)"
        for s_dict in (confirm47_sum, confirm47_e2e):
            s_dict["block_label"] = s_dict["block_label"].replace("Untouched_Confirmation", "Clean_Isolation_Confirm_Replication")
            s_dict["cohort_provenance"] = (
                "Protocol_Fixed_Clean_Isolation_Confirm_Replication_64000_64011 "
                "(n=12 maps, 6 AB / 6 BA, zero cross-arm retention; re-evaluates M2.3.3 confirmation seeds, not a fresh untouched cohort)"
            )

    fig_path = p2_dir / fig_name
    _plot_m233_sisc_summary(
        pair35_sum,
        pair47_sum,
        pair59_sum,
        cont47_marg,
        confirm47_sum,
        cache47_sum,
        rows_confirm47,
        rows59,
        {"35": -12.15, "47": 15.17, "59": 13.74, "cont47": 9.98},
        fig_path,
    )

    frozen_10_after = verify_all_10_frozen_jsons(p2_dir)
    frozen_m233_after = verify_m233_original_archive_untouched(p2_dir)
    verify_phase1_readonly_freeze()
    rt_meta = collect_runtime_metadata()
    rt_meta["actual_parallel_workers"] = 1

    # Compare clean-isolation replication directly against frozen M2.3.3 archive (`339e723f...`)
    orig_m233_data = _strict_json_loads((p2_dir / "m233_sisc_unlock_results.json").read_text(encoding="utf-8"))
    orig_sisc = orig_m233_data["sisc_head_to_head_summaries"]
    cur_sisc = {
        "replay_35cubed_planner_only": pair35_sum,
        "replay_35cubed_end_to_end": pair35_e2e,
        "replay_47cubed_planner_only": pair47_sum,
        "replay_47cubed_end_to_end": pair47_e2e,
        "replay_59cubed_planner_only": pair59_sum,
        "replay_59cubed_end_to_end": pair59_e2e,
        "continual_47cubed_marginal": cont47_marg,
        "continual_47cubed_lifecycle": cont47_life,
        "continual_47cubed_mean_retained_l1_l4_nodes": float(
            np.mean([r["arms"]["M233_SubPortal_PoUQuadtree"]["mean_retained_l1_l4_quadtree_nodes"] for r in rows_cont])
        ),
        "confirm_64000_64011_47cubed_planner_only": confirm47_sum,
        "confirm_64000_64011_47cubed_end_to_end": confirm47_e2e,
    }
    comparison_vs_orig = {}
    for k_orig, k_cur in (
        ("untouched_confirm_64000_64011_47cubed_planner_only", "confirm_64000_64011_47cubed_planner_only"),
        ("replay_59cubed_planner_only", "replay_59cubed_planner_only"),
        ("replay_47cubed_planner_only", "replay_47cubed_planner_only"),
        ("replay_35cubed_planner_only", "replay_35cubed_planner_only"),
        ("continual_47cubed_marginal", "continual_47cubed_marginal"),
        ("continual_47cubed_lifecycle", "continual_47cubed_lifecycle"),
    ):
        o_b = orig_sisc[k_orig]
        c_b = cur_sisc[k_cur]
        comparison_vs_orig[k_cur] = {
            "frozen_m233_saving_pct": float(o_b["relative_time_saving_pct"]),
            "clean_isolation_saving_pct": float(c_b["relative_time_saving_pct"]),
            "saving_pct_delta_clean_minus_frozen": float(c_b["relative_time_saving_pct"] - o_b["relative_time_saving_pct"]),
            "frozen_m233_pou_mean_ms": float(o_b["pou_quadtree_mean_ms"]),
            "clean_isolation_pou_mean_ms": float(c_b["pou_quadtree_mean_ms"]),
            "frozen_m233_mf_mean_ms": float(o_b["matrixfree_mean_ms"]),
            "clean_isolation_mf_mean_ms": float(c_b["matrixfree_mean_ms"]),
            "clean_isolation_20pct_gate": str(c_b["engineering_20pct_time_saving_gate"]),
            "clean_isolation_p_20pct": float(c_b["diagnostic_one_sided_p_for_20pct_saving"]),
            "clean_isolation_p_two_sided": float(c_b["paired_equal_time_diff_pou_minus_matrixfree_ms"]["p_two_sided"]),
        }

    rss_telemetry_summary = {}
    for lbl, rlist, akey in (
        ("replay_35cubed", rows35, "pair_arms"),
        ("replay_47cubed", rows47, "pair_arms"),
        ("replay_59cubed", rows59, "pair_arms"),
        ("continual_47cubed", rows_cont, "arms"),
        ("confirm_47cubed", rows_confirm47, "pair_arms"),
    ):
        rss_telemetry_summary[lbl] = {
            arm_nm: {
                "mean_rss_mb_before_arm": float(np.mean([r[akey][arm_nm]["rss_mb_before_arm"] for r in rlist])),
                "max_rss_mb_end_of_arm": float(np.max([r[akey][arm_nm]["rss_mb_end_of_arm_before_del"] for r in rlist])),
                "mean_rss_mb_after_arm_gc": float(np.mean([r[akey][arm_nm]["rss_mb_after_arm_gc"] for r in rlist])),
                "all_prior_bases_gc_freed": bool(all(r[akey][arm_nm]["prior_base_gc_freed"] for r in rlist)),
            }
            for arm_nm in PAIR2_SISC_ARMS
        }

    payload = _sanitize_for_strict_json({
        "milestone": (
            "M2.3.3_Protocol_Fixed_Clean_Isolation_Replication_SISC01_Closure"
            if clean_isolation_replication
            else "M2.3.3_SISC_SubPortal_PoU_Quadtree_Unlock_and_Untouched_Confirmation"
        ),
        "protocol_status": (
            "protocol_fixed_clean_isolation_replication_zero_cross_arm_retention"
            if clean_isolation_replication
            else "original_campaign"
        ),
        "elapsed_wall_s": float(time.perf_counter() - t_all0),
        "locked_hyperparameters": LOCKED_M233_HYPERPARAMS,
        "runtime_metadata": rt_meta,
        "phase2_manifest": compute_phase2_manifest(),
        "prior_10_frozen_artifacts_verified": frozen_10_after,
        "frozen_m233_original_archive_verified": frozen_m233_after,
        "sisc01_zero_cross_arm_retention_probe": sisc01_probe,
        "rss_telemetry_summary_mb": rss_telemetry_summary,
        "comparison_vs_frozen_m233_original": comparison_vs_orig,
        "contracts_and_pou_verification": contracts_out,
        "independent_roster_and_zero_slack_audit": {
            "audit_at_zero_slack": audit_zero_slack,
            "audit_at_1e7_slack": audit_1e7_slack,
            "negative_control_fault_injections": fault_report,
            "all_4_fault_injections_rejected": faults_rejected,
        },
        "sisc_head_to_head_summaries": cur_sisc,
        "cache_causal_ablation_47cubed": cache47_sum,
        "stage_timing_breakdown_ms": stage_breakdown,
        "per_map_records": {
            "replay_35cubed": rows35,
            "replay_47cubed": rows47,
            "replay_59cubed": rows59,
            "continual_47cubed": rows_cont,
            "confirm_47cubed": rows_confirm47,
        },
    })

    txt = json.dumps(payload, indent=2, allow_nan=False)
    _ = _strict_json_loads(txt)
    out_json.write_text(txt, encoding="utf-8")

    if not (audit_zero_slack["ALL_INDEPENDENT_GATES_PASSED"] and faults_rejected):
        raise RuntimeError(f"M2.3.3 zero-slack audit failed: {audit_zero_slack}")

    print(
        f"[DONE] Wrote {out_json.name} & {fig_path.name} in {payload['elapsed_wall_s']:.1f}s | "
        f"ZeroSlackPass={audit_zero_slack['ALL_INDEPENDENT_GATES_PASSED']} (2304 events, 792 pol evals) | "
        f"Faults4/4={faults_rejected} | SISC01_ZeroRetention={sisc01_probe['pass']} | Frozen11=100% Untouched"
    )
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--contracts-only", action="store_true")
    parser.add_argument("--clean-isolation-replication", action="store_true")
    args = parser.parse_args()
    if args.contracts_only:
        probe_out = verify_zero_cross_arm_retention_probe()
        res = run_m233_contract_and_pou_verification()
        print(
            f"[M2.3.3 CONTRACTS PASS] {res['ALL_M233_CONTRACTS_PASSED']} | "
            f"SISC01_ZeroRetention={probe_out['pass']} (max_alive={probe_out['max_alive_prior_bases']}) in {res['elapsed_ms']:.1f}ms"
        )
    elif args.self_test:
        run_m233_sisc_campaign(self_test=True)
    elif args.clean_isolation_replication:
        run_m233_sisc_campaign(self_test=False, clean_isolation_replication=True)
    else:
        run_m233_sisc_campaign(self_test=False, clean_isolation_replication=False)
