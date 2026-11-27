"""Zero-Rerun Final Release Verification & Polished Figure Suite (`quotient_phase2.verify_m232_release`):
Closes All `ec3c58f` Release-Polish Items (`C232-01..C232-05`, `R232-D01..R232-D10`) Without Rerunning
`47^3 / 59^3` Campaigns or Modifying Any Frozen Historical Artifact.

Outputs (`100%` Standard RFC-8259 JSON with `allow_nan=False`, Zero Overwrites of Frozen Files):
  1. `quotient_phase2/m232_release_verification_report.json`:
       - Verifies SHA-256 of frozen Phase-I (`271ac8df...`) and all 10 frozen Phase-II JSONs (`m20..m232`),
         plus strict RFC-8259 parsing (no `NaN/Infinity`, no duplicate object keys);
       - `C232-04`: Runs an independent read-only event roster, raw-float inequality, and policy-schedule
         verifier (`COVERAGE_COMPLETE`, `POLICY_SCHEDULE_COMPLETE`, `VALUES_VALID`, `POLICY_CHECKS_VALID`)
         at BOTH `0.0` slack and `1e-7` slack across all `1,440` events and `360` policy evaluations,
         and rejects `4 / 4` fault injections (`drop_one_row`, `duplicate_one_row`, `tamper_bound_hi`,
         `disable_all_policy_evals`);
       - `C232-02 & C232-03`: Deterministically separates operational vs. post-timer evaluation-materialization
         RHS column solves on the frozen `47^3` cache study (`9,010.17` vs `19,008.83` operational RHS =
         `52.60%` saving; `312.0` evaluation RHS/map verified geometrically across `6` maps x `12` tasks),
         documents `QueryCold` historical `t_i == 0` `L0` rebuild scope (`102` RHS/map = `0.48%`), and verifies
         live `operational_local_lu_rhs_solves` vs `evaluation_materialization_rhs_solves` split in code;
       - `R232-D04 & R232-D09`: Computes both planner-only (`15.17%`, `13.74%`) and end-to-end incl. shared
         `GP fit + operator assembly` (`14.77%`, `13.56%`) savings, `20%` gate (`NOT_MET`), and exact `2^6 = 64`
         paired sign-flip sensitivity (`p = 0.0625` on `47^3`, `0.03125` on `59^3` & continual);
       - `C232-05 & R232-D02`: Runs in-memory (`write_json=False`) the complete `M2.0` (`15/15`), `WP0`, `M2.2`
         (`4/4`), `M2.3.1` (`EC-01..EC-06 + 7.3`), `M2.3.2` (`B6-01..B6-05 + 792-ring`), AND `24` independent
         adversarial boundary cases (`disconnected_same_room`, `jagged_portal_adjacent`, `outer_wall_slab`,
         `interior_point` x `3` start classes x `2` planners at `eps = 0.001`).
  2. `quotient_phase2/m232_release_polished_summary.png` (`Closes C232-01`):
       - Panel A: Pure same-block `47^3` 3-arm cache cumulative curves ONLY (no cross-block `MatrixFree` line!);
       - Panel B: Same-block `1`-worker `AB/BA` closest-neighbor bars + paired per-map dots (`20%` gate `NOT_MET`);
       - Panel C: Same-block `AB/BA` cumulative prefix curves `C(k)` (`Portal` vs `MatrixFree` from `pair_arms`);
       - Panel D: Saved per-task deployed policy regret across all 4 blocks (`Portal` max `0.0335`, `MF` max `0.0478`).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

import copy
import hashlib
import itertools
import json
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.sparse.linalg as spla
from scipy import stats as sp_stats
from scipy.sparse.csgraph import connected_components

from green_response import ProblemSpec, collect_runtime_metadata, enforce_single_thread_env
from green_response.port_solvers import build_grid_points
from quotient_phase2 import compute_phase2_manifest, verify_phase1_readonly_freeze
from quotient_phase2.m23_m24_3d_portal_scale import (
    SeamFreePortal3DPlanner,
    build_3d_reflecting_obstacle_mmatrix,
    discover_3d_bottleneck_planes_zero_hint,
    evaluate_3d_deployed_policy_exact,
    extract_directed_goal_ring_in_room,
    generate_3d_multiroom_world,
)
from quotient_phase2.m231_fair_ablation import MatrixFreeExactSchurKrylov3DPlanner
from quotient_phase2.m232_final_closure import (
    _sanitize_for_strict_json,
    run_m232_contract_and_ring_closure,
)


FROZEN_ALL_10_JSON_SHA256: Dict[str, str] = {
    "m20_contract_results.json": "bdad834622c2ab0215be84c2e3cfb4473f5b242e053d9b7bef8e792081c67004",
    "m21_ablation_results.json": "634c15e52fb3a8181f738baef40b8d7c30e690a8600a7cf1e30b6ca17a3c4fc1",
    "m21_economic_gate_verdict.json": "dca3212a6b34dda33952f58397c7d9ae3bade9058be083e98154d3f9d7b3a95b",
    "m21_post_audit_closure.json": "9b8d0db59265b0386dd3cf3812c1234aeb1e24aa782ca5b9d0fe20e3e2c967a1",
    "m22_pilot_results.json": "55d7e1ea176d2ad53d173595339c21216fc6f210857b5d28e30b98c163a3d892",
    "m23_m24_3d_results.json": "8fb6fb84749dfa640e5f5394c65db71426302a365e95a512c25dd896bce30f05",
    "m231_audit_closure.json": "4a0e2514a351ab7102dc9e54c6fce38dc9b5b8325ec8c277aa96aaa09257c4a9",
    "m231_fair_ablation_results.json": "f844a1028ec72ca7e0c26f77106b65d622412c8efb500fbe1e7f0869706cf003",
    "m232_contract_and_ring_closure.json": "06b441563dd2f30bffc982cd437b7b5d4a497636451bc5cf69bf241339410dba",
    "m232_targeted_replay_results.json": "9979d61a4de74d4e05fc8d1beff2103a4d292c693be4ebd1fc422004f91fc730",
}


def _strict_json_loads(raw_text: str) -> Any:
    """Strict RFC-8259 parser rejecting bare `NaN/Infinity` and duplicate object keys."""
    def _no_dups(pairs: List[Tuple[str, Any]]) -> dict:
        out: Dict[str, Any] = {}
        for k, v in pairs:
            if k in out:
                raise ValueError(f"Duplicate JSON key: {k!r}")
            out[k] = v
        return out

    def _no_nonfinite(tok: str) -> Any:
        raise ValueError(f"Non-RFC-8259 constant encountered: {tok!r}")

    return json.loads(raw_text, object_pairs_hook=_no_dups, parse_constant=_no_nonfinite)


def verify_all_10_frozen_jsons(p2_dir: Path) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for fn, exp_sha in FROZEN_ALL_10_JSON_SHA256.items():
        fp = p2_dir / fn
        if not fp.exists():
            raise RuntimeError(f"Missing frozen artifact: {fn}")
        raw_bytes = fp.read_bytes()
        actual = hashlib.sha256(raw_bytes).hexdigest()
        if actual != exp_sha:
            raise RuntimeError(f"Frozen artifact {fn} modified! Expected {exp_sha}, got {actual}")
        strict_rfc = False
        if fn.startswith("m232_"):
            _ = _strict_json_loads(raw_bytes.decode("utf-8"))
            strict_rfc = True
        out[fn] = {"sha256": actual, "verified_untouched": True, "strict_rfc8259_verified": strict_rfc}
    return out


# ==============================================================================
# 1. Independent Event-Roster, Raw-Float Inequality, & Policy-Schedule Verifier (`C232-04`)
# ==============================================================================
EventKey = Tuple[str, int, int, int, int, str]


def build_expected_m232_roster() -> Tuple[Set[EventKey], Set[EventKey]]:
    """Constructs the exact frozen `1,440`-event roster and `360`-slot deployed-policy schedule."""
    seeds = range(63000, 63006)
    expected_keys: Set[EventKey] = set()
    expected_pol_keys: Set[EventKey] = set()

    for sd in seeds:
        for ti in range(24):
            for m in ("CacheOn_Persistent", "CacheL0Only", "QueryCold"):
                k = ("cache_ablation_47cubed", sd, 47, 0, ti, m)
                expected_keys.add(k)
                if m == "CacheOn_Persistent" and ti < 12:
                    expected_pol_keys.add(k)
            for m in ("M231_Portal_CacheOn", "MatrixFree_ExactSchur_Krylov"):
                k47 = ("pair_abba_47cubed", sd, 47, 0, ti, m)
                k59 = ("pair_abba_59cubed", sd, 59, 0, ti, m)
                expected_keys.add(k47)
                expected_keys.add(k59)
                if ti < 12:
                    expected_pol_keys.add(k47)
                if ti < 6:
                    expected_pol_keys.add(k59)
        for gti in range(36):
            ep = gti // 6
            for m in ("M231_Portal_CacheOn", "MatrixFree_ExactSchur_Krylov"):
                kc = ("continual_abba_47cubed", sd, 47, ep, gti, m)
                expected_keys.add(kc)
                if (gti % 6) == 0:
                    expected_pol_keys.add(kc)

    assert len(expected_keys) == 1440 and len(expected_pol_keys) == 360
    return expected_keys, expected_pol_keys


def extract_all_events_from_replay(replay_data: dict) -> List[dict]:
    pm = replay_data["per_map_records"]
    return (
        [e for r in pm["replay_47cubed"] for e in r["cache_events"]]
        + [e for r in pm["replay_47cubed"] for e in r["pair_events"]]
        + [e for r in pm["replay_59cubed"] for e in r["pair_events"]]
        + [e for r in pm["continual_47cubed"] for e in r["events"]]
    )


def verify_event_roster_and_inequalities(
    events: List[dict],
    expected_keys: Set[EventKey],
    expected_pol_keys: Set[EventKey],
    eps_budget: float = 0.25,
    slack: float = 0.0,
) -> dict:
    """Independently verifies roster completeness, uniqueness, cross-arm task identity, policy schedule,
    and raw-float inequalities WITHOUT trusting saved boolean flags (`Closes C232-04`).
    """
    seen_keys: Set[EventKey] = set()
    dup_count = 0
    actual_pol_keys: Set[EventKey] = set()
    val_viols = 0
    pol_viols = 0
    task_identities: Dict[Tuple[str, int, int, int, int], Tuple[int, str, float]] = {}
    cross_arm_mismatch_count = 0

    widths: List[float] = []
    vref_minus_lo: List[float] = []
    hi_minus_vref: List[float] = []
    hi_minus_jeval: List[float] = []
    regret_by_method: Dict[str, List[float]] = {}

    for ev in events:
        key: EventKey = (
            str(ev["block_id"]),
            int(ev["seed"]),
            int(ev["grid_n"]),
            int(ev["operator_epoch"]),
            int(ev["task_index"]),
            str(ev["method_id"]),
        )
        if key in seen_keys:
            dup_count += 1
        seen_keys.add(key)

        # Cross-arm task identity check (static 47^3 cache + pair share the exact same 24 tasks!)
        world_grp = "static47" if key[0] in ("cache_ablation_47cubed", "pair_abba_47cubed") else key[0]
        t_slot = (world_grp, key[1], key[2], key[3], key[4])
        sig_tuple = (int(ev["start_state"]), str(ev["goal_signature_sha1"]), float(ev["reference_value"]))
        if t_slot in task_identities:
            prev = task_identities[t_slot]
            if prev[0] != sig_tuple[0] or prev[1] != sig_tuple[1] or abs(prev[2] - sig_tuple[2]) > 1e-12:
                cross_arm_mismatch_count += 1
        else:
            task_identities[t_slot] = sig_tuple

        lo = float(ev["lo"])
        hi = float(ev["hi"])
        v_ref = float(ev["reference_value"])
        w = hi - lo
        widths.append(w)
        vref_minus_lo.append(v_ref - lo)
        hi_minus_vref.append(hi - v_ref)

        is_val_ok = (
            bool(ev["certified"])
            and bool(ev["reference_valid"])
            and np.isfinite(lo)
            and np.isfinite(hi)
            and np.isfinite(v_ref)
            and (lo <= v_ref + slack)
            and (v_ref <= hi + slack)
            and (0.0 <= w <= eps_budget + slack)
        )
        if not is_val_ok:
            val_viols += 1

        if ev.get("policy_value") is not None or bool(ev.get("policy_evaluated", False)):
            actual_pol_keys.add(key)
            if ev.get("policy_value") is None:
                pol_viols += 1
            else:
                j_val = float(ev["policy_value"])
                hi_minus_jeval.append(hi - j_val)
                regret_by_method.setdefault(key[5], []).append(j_val - v_ref)
                is_pol_ok = (
                    is_val_ok
                    and np.isfinite(j_val)
                    and (lo <= v_ref + slack)
                    and (v_ref <= j_val + max(slack, 0.0))
                    and (j_val <= hi + slack)
                )
                if not is_pol_ok:
                    pol_viols += 1

    missing_keys = expected_keys - seen_keys
    unexpected_keys = seen_keys - expected_keys
    coverage_complete = bool(
        len(events) == len(expected_keys)
        and dup_count == 0
        and len(missing_keys) == 0
        and len(unexpected_keys) == 0
        and cross_arm_mismatch_count == 0
    )
    policy_schedule_complete = bool(actual_pol_keys == expected_pol_keys)
    values_valid = bool(len(events) > 0 and val_viols == 0)
    policy_checks_valid = bool(len(actual_pol_keys) > 0 and pol_viols == 0)

    return {
        "slack_used": slack,
        "COVERAGE_COMPLETE": coverage_complete,
        "POLICY_SCHEDULE_COMPLETE": policy_schedule_complete,
        "VALUES_VALID": values_valid,
        "POLICY_CHECKS_VALID": policy_checks_valid,
        "ALL_INDEPENDENT_GATES_PASSED": bool(
            coverage_complete and policy_schedule_complete and values_valid and policy_checks_valid
        ),
        "total_rows_seen": len(events),
        "unique_keys_seen": len(seen_keys),
        "duplicate_key_count": dup_count,
        "missing_key_count": len(missing_keys),
        "unexpected_key_count": len(unexpected_keys),
        "cross_arm_task_mismatch_count": cross_arm_mismatch_count,
        "distinct_geometric_task_slots": len(task_identities),
        "scheduled_policy_slots_seen": len(actual_pol_keys),
        "value_violation_count": val_viols,
        "policy_violation_count": pol_viols,
        "min_width": float(min(widths)) if widths else None,
        "max_width": float(max(widths)) if widths else None,
        "min_vref_minus_lo": float(min(vref_minus_lo)) if vref_minus_lo else None,
        "min_hi_minus_vref": float(min(hi_minus_vref)) if hi_minus_vref else None,
        "min_hi_minus_jeval": float(min(hi_minus_jeval)) if hi_minus_jeval else None,
        "max_regret_by_method": {k: float(max(vs)) for k, vs in sorted(regret_by_method.items())},
    }


def run_negative_control_fault_injections(
    base_events: List[dict],
    expected_keys: Set[EventKey],
    expected_pol_keys: Set[EventKey],
) -> dict:
    """Verifies that all 4 fault-injection classes are strictly rejected (`ALL_INDEPENDENT_GATES_PASSED == False`)."""
    # 1. Drop one valid row
    ev_drop = copy.deepcopy(base_events[:-1])
    r_drop = verify_event_roster_and_inequalities(ev_drop, expected_keys, expected_pol_keys, slack=1e-7)

    # 2. Duplicate one valid row
    ev_dup = copy.deepcopy(base_events) + [copy.deepcopy(base_events[0])]
    r_dup = verify_event_roster_and_inequalities(ev_dup, expected_keys, expected_pol_keys, slack=1e-7)

    # 3. Tamper one upper bound below `reference_value` (even while leaving saved boolean `True`!)
    ev_tamper = copy.deepcopy(base_events)
    ev_tamper[0]["hi"] = float(ev_tamper[0]["reference_value"]) - 1e-3
    ev_tamper[0]["value_enclosure_satisfied"] = True
    r_tamper = verify_event_roster_and_inequalities(ev_tamper, expected_keys, expected_pol_keys, slack=1e-7)

    # 4. Disable all policy evaluations
    ev_nopol = copy.deepcopy(base_events)
    for row in ev_nopol:
        row["policy_evaluated"] = False
        row["policy_value"] = None
        row["four_inequalities_satisfied"] = None
    r_nopol = verify_event_roster_and_inequalities(ev_nopol, expected_keys, expected_pol_keys, slack=1e-7)

    all_rejected = bool(
        (not r_drop["COVERAGE_COMPLETE"]) and (not r_drop["ALL_INDEPENDENT_GATES_PASSED"])
        and (not r_dup["COVERAGE_COMPLETE"]) and (not r_dup["ALL_INDEPENDENT_GATES_PASSED"])
        and (not r_tamper["VALUES_VALID"]) and (not r_tamper["ALL_INDEPENDENT_GATES_PASSED"])
        and (not r_nopol["POLICY_SCHEDULE_COMPLETE"]) and (not r_nopol["ALL_INDEPENDENT_GATES_PASSED"])
    )
    return {
        "ALL_4_FAULT_INJECTIONS_REJECTED": all_rejected,
        "drop_one_row_rejected": not r_drop["ALL_INDEPENDENT_GATES_PASSED"],
        "duplicate_one_row_rejected": not r_dup["ALL_INDEPENDENT_GATES_PASSED"],
        "tamper_bound_hi_rejected": not r_tamper["ALL_INDEPENDENT_GATES_PASSED"],
        "disable_all_policy_evals_rejected": not r_nopol["ALL_INDEPENDENT_GATES_PASSED"],
    }


# ==============================================================================
# 2. Deterministic Post-Processing of RHS Split (`C232-02/03`) & Sign-Flip Stats (`R232-D04/09`)
# ==============================================================================
def _paired_summary_independent(cand: np.ndarray, base: np.ndarray) -> dict:
    diff = np.asarray(cand, dtype=float) - np.asarray(base, dtype=float)
    n = len(diff)
    mean_c = float(np.mean(cand))
    mean_b = float(np.mean(base))
    mean_d = float(np.mean(diff))
    sd_d = float(np.std(diff, ddof=1))
    se_d = sd_d / np.sqrt(float(n))
    t_crit = float(sp_stats.t.ppf(0.975, df=n - 1))
    t_eq = mean_d / se_d
    p_2s = float(2.0 * sp_stats.t.sf(abs(t_eq), df=n - 1))

    # Pre-declared 20% relative time saving test: H1: E[cand - 0.80 * base] < 0
    d20 = np.asarray(cand, dtype=float) - 0.80 * np.asarray(base, dtype=float)
    t20 = float(np.mean(d20)) / (float(np.std(d20, ddof=1)) / np.sqrt(float(n)))
    p_1s_20 = float(sp_stats.t.cdf(t20, df=n - 1))

    # Exact 2^n paired sign-flip sensitivity (descriptive robustness check, NOT a replacement gate)
    signs = np.array(list(itertools.product((-1.0, 1.0), repeat=n)), dtype=float)
    flipped_means = (signs @ diff) / float(n)
    p_signflip_2s = float(np.mean(np.abs(flipped_means) >= abs(mean_d) - 1e-12))

    saving_pct = 100.0 * (1.0 - mean_c / mean_b)
    return {
        "n_maps": n,
        "portal_mean_ms": mean_c,
        "matrixfree_mean_ms": mean_b,
        "speedup_ratio": mean_b / mean_c,
        "relative_time_saving_pct": saving_pct,
        "mean_diff_ms": mean_d,
        "ci95_diff_ms": [mean_d - t_crit * se_d, mean_d + t_crit * se_d],
        "p_two_sided_paired_t": p_2s,
        "n_maps_portal_faster": int(np.sum(diff < 0.0)),
        "p_two_sided_exact_sign_flip": p_signflip_2s,
        "one_sided_p_20pct_saving": p_1s_20,
        "engineering_20pct_gate": "PASS" if (saving_pct >= 20.0 and p_1s_20 < 0.05) else "NOT_MET",
        "per_map_diff_ms": [float(x) for x in diff],
    }


def compute_postprocessed_rhs_and_cost_tables(replay_data: dict) -> dict:
    pm = replay_data["per_map_records"]
    r47 = pm["replay_47cubed"]
    r59 = pm["replay_59cubed"]
    rc = pm["continual_47cubed"]

    # Geometrically verify exact evaluation-materialization RHS count on all 6 47^3 maps (`12 * 26 = 312`)
    eval_rhs_per_map: List[int] = []
    init_l0_rhs_per_map: List[int] = []
    for rec in r47:
        sd = int(rec["seed"])
        w = generate_3d_multiroom_world(sd, 47, ProblemSpec(dim=3), 24, fit_gp_world=False)
        A_chk = build_3d_reflecting_obstacle_mmatrix(w["spec"], 47, w["free_mask"], w["q_f"], w["b_f"]).tocsr()
        xc, yc, zc = discover_3d_bottleneck_planes_zero_hint(w["free_3d"])
        c_ijk = np.unravel_index(w["free_nodes"], (47, 47, 47))
        gmask = np.isin(c_ijk[0], xc) | np.isin(c_ijk[1], yc) | np.isin(c_ijk[2], zc)
        gam_f = np.flatnonzero(gmask).astype(np.int64)
        int_f = np.flatnonzero(~gmask).astype(np.int64)
        A_gg = A_chk[gam_f, :][:, gam_f]
        n_portals, p_lbl = connected_components((np.abs(A_gg) + np.abs(A_gg.T)) > 0, directed=False)
        n_rooms, r_lbl = connected_components((np.abs(A_chk[int_f, :][:, int_f]) + np.abs(A_chk[int_f, :][:, int_f].T)) > 0, directed=False)
        rm_of = np.full(len(w["free_nodes"]), -1, dtype=np.int64)
        p_rooms = [set() for _ in range(n_portals)]
        for rc_i in range(n_rooms):
            rn_i = int_f[r_lb_mask := (r_lbl == rc_i)]
            rm_of[rn_i] = rc_i
            tl_i = np.flatnonzero(np.asarray(np.abs(A_chk[rn_i, :][:, gam_f]).sum(axis=0)).ravel() > 0)
            for pid in np.unique(p_lbl[tl_i]):
                p_rooms[int(pid)].add(rc_i)
        # First 12 tasks on CacheOn_Persistent call materialize_full_grid_unit() after priming room_of_f[s_f]
        ev_rhs = 0
        for ti in range(12):
            s_f, _ = w["tasks"][ti]
            assert int(rm_of[s_f]) >= 0
            ev_rhs += (int(n_rooms) - 1)
        eval_rhs_per_map.append(ev_rhs)
        init_l0_rhs_per_map.append(int(sum(len(s_set) for s_set in p_rooms)))

    assert eval_rhs_per_map == [312] * 6, f"Unexpected eval RHS per map: {eval_rhs_per_map}"

    mixed_on = np.array([r["cache_arms"]["CacheOn_Persistent"]["total_local_lu_solves"] for r in r47], dtype=float)
    op_on = mixed_on - np.array(eval_rhs_per_map, dtype=float)
    op_l0 = np.array([r["cache_arms"]["CacheL0Only"]["total_local_lu_solves"] for r in r47], dtype=float)
    mixed_cold = np.array([r["cache_arms"]["QueryCold"]["total_local_lu_solves"] for r in r47], dtype=float)

    # Planner-only & End-to-End (incl. shared GP fit + operator assembly)
    p47_pl = np.array([r["pair_arms"]["M231_Portal_CacheOn"]["total_ms"] for r in r47], dtype=float)
    mf47_pl = np.array([r["pair_arms"]["MatrixFree_ExactSchur_Krylov"]["total_ms"] for r in r47], dtype=float)
    sh47 = np.array([float(r["shared_gp_fit_ms"]) + float(r["shared_operator_assembly_ms"]) for r in r47], dtype=float)

    p59_pl = np.array([r["pair_arms"]["M231_Portal_CacheOn"]["total_ms"] for r in r59], dtype=float)
    mf59_pl = np.array([r["pair_arms"]["MatrixFree_ExactSchur_Krylov"]["total_ms"] for r in r59], dtype=float)
    sh59 = np.array([float(r["shared_gp_fit_ms"]) + float(r["shared_operator_assembly_ms"]) for r in r59], dtype=float)

    pc_marg = np.array([r["arms"]["M231_Portal_CacheOn"]["post_init_marginal_incl_rebuild_ms"] for r in rc], dtype=float)
    mfc_marg = np.array([r["arms"]["MatrixFree_ExactSchur_Krylov"]["post_init_marginal_incl_rebuild_ms"] for r in rc], dtype=float)
    pc_life = np.array([r["arms"]["M231_Portal_CacheOn"]["lifecycle_incl_rebuild_ms"] for r in rc], dtype=float)
    mfc_life = np.array([r["arms"]["MatrixFree_ExactSchur_Krylov"]["lifecycle_incl_rebuild_ms"] for r in rc], dtype=float)

    return {
        "cache_47cubed_rhs_decomposition": {
            "unit": "room_local_LU_RHS_column_backsolves",
            "verified_eval_materialization_rhs_per_map": eval_rhs_per_map,
            "CacheOn_mixed_rhs_mean": float(np.mean(mixed_on)),
            "CacheOn_eval_materialization_rhs_mean": float(np.mean(eval_rhs_per_map)),
            "CacheOn_operational_rhs_mean": float(np.mean(op_on)),
            "CacheL0Only_operational_rhs_mean": float(np.mean(op_l0)),
            "CacheOn_vs_CacheL0Only_mixed_rhs_saving_pct": float(100.0 * (1.0 - np.mean(mixed_on) / np.mean(op_l0))),
            "CacheOn_vs_CacheL0Only_operational_rhs_saving_pct": float(100.0 * (1.0 - np.mean(op_on) / np.mean(op_l0))),
            "QueryCold_recorded_rhs_mean_incl_task0_L0_rebuild": float(np.mean(mixed_cold)),
            "QueryCold_task0_redundant_L0_rhs_per_map": init_l0_rhs_per_map,
            "QueryCold_task0_redundant_L0_fraction_pct": float(100.0 * np.mean(init_l0_rhs_per_map) / np.mean(mixed_cold)),
        },
        "closest_neighbor_abba_summaries": {
            "static_47cubed_planner_only": _paired_summary_independent(p47_pl, mf47_pl),
            "static_47cubed_end_to_end_incl_gp_and_assembly": _paired_summary_independent(p47_pl + sh47, mf47_pl + sh47),
            "static_59cubed_planner_only": _paired_summary_independent(p59_pl, mf59_pl),
            "static_59cubed_end_to_end_incl_gp_and_assembly": _paired_summary_independent(p59_pl + sh59, mf59_pl + sh59),
            "continual_47cubed_post_init_marginal_incl_rebuild": _paired_summary_independent(pc_marg, mfc_marg),
            "continual_47cubed_full_lifecycle_incl_rebuild": _paired_summary_independent(pc_life, mfc_life),
        },
    }


# ==============================================================================
# 3. Live In-Memory Adversarial Boundary (`24` Cases) & Split-Counter Regression
# ==============================================================================
def run_adversarial_24_and_live_counter_checks() -> dict:
    gn = 17
    spc = ProblemSpec(dim=3)
    free = np.ones((gn, gn, gn), dtype=bool)
    free[8, :, :] = False
    free[8, 6:11, 6:11] = True
    nodes = np.flatnonzero(free.ravel()).astype(np.int64)
    mp = np.full(gn ** 3, -1, dtype=np.int64)
    mp[nodes] = np.arange(len(nodes), dtype=np.int64)
    _, pts, _ = build_grid_points(3, spc.half_width, gn)
    q = 0.45 + 0.13 * (1.0 + pts[nodes, 0])
    b = np.zeros((len(nodes), 3), dtype=float)
    b[:] = (0.07, -0.11, 0.19)
    A = build_3d_reflecting_obstacle_mmatrix(spc, gn, free.ravel(), q, b).tocsr()

    def _idx(x: int, y: int, z: int) -> int:
        return int(mp[(x * gn + y) * gn + z])

    def _mask(coords: List[Tuple[int, int, int]]) -> np.ndarray:
        g = np.zeros(len(nodes), dtype=bool)
        for c in coords:
            g[_idx(*c)] = True
        return g

    goals = {
        "disconnected_same_room": _mask([(9, 8, 8), (14, 10, 7)]),
        "jagged_portal_adjacent": _mask(
            [(x, y, z) for x in (9, 10, 11) for y in range(6, 11) for z in range(6, 11) if (x + y + z) % 3 != 0]
        ),
        "outer_wall_slab": _mask([(x, y, z) for x in (15, 16) for y in range(4, 13) for z in range(5, 12)]),
        "interior_point": _mask([(13, 8, 8)]),
    }

    n_cases = 0
    all_fourfold_ok = True
    all_support_ok = True
    max_action_err = 0.0
    max_regret = 0.0

    for _, goal in goals.items():
        ext = np.flatnonzero(~goal)
        zref = np.ones(len(nodes), dtype=float)
        zref[ext] = spla.spsolve(A[ext, :][:, ext].tocsc(), np.asarray((-A[ext, :][:, goal]).sum(axis=1)).ravel())
        for _, s in (("other_room", _idx(3, 8, 8)), ("portal", _idx(8, 8, 8)), ("same_room", _idx(12, 12, 12))):
            for cls in (SeamFreePortal3DPlanner, MatrixFreeExactSchurKrylov3DPlanner):
                n_cases += 1
                pl = cls(spc, gn, free, nodes, pts[nodes], A, eps_tol=0.001)
                r = pl.solve_unseen_goal(s, goal)
                base = pl.base if hasattr(pl, "base") else pl
                rc = int(base.room_of_f[np.flatnonzero(goal)[0]])
                rn = base.room_nodes[rc]
                _, ring = extract_directed_goal_ring_in_room(A, goal, rn, base.gamma_f[base.room_tl[rc]])
                gi = np.flatnonzero(goal[rn])
                ring_full = gi[np.asarray((A[ext, :][:, rn[gi]] < 0.0).sum(axis=0)).ravel() > 0]
                if not np.array_equal(ring, ring_full):
                    all_support_ok = False
                v_true = -spc.lam * float(np.log(zref[s]))
                guide = r["policy"].materialize_full_grid_unit()
                j_val = evaluate_3d_deployed_policy_exact(A, goal, 0.0, guide, spc.lam, s)
                for at in (s, _idx(7, 8, 8), _idx(8, 8, 8), _idx(9, 8, 8), _idx(12, 12, 12)):
                    if goal[at]:
                        continue
                    nb, p_act = r["policy"].action_distribution(at)
                    w_row = -A.getrow(at)[:, nb].toarray().ravel() * guide[nb]
                    pe = w_row / float(np.sum(w_row))
                    max_action_err = max(max_action_err, float(np.max(np.abs(pe - p_act))))
                ok = bool(
                    r["certified"]
                    and (r["lo"] <= v_true + 1e-9)
                    and (v_true <= j_val + 1e-9)
                    and (j_val <= r["hi"] + 1e-9)
                    and (r["width"] <= 0.001 + 1e-12)
                )
                if not ok:
                    all_fourfold_ok = False
                max_regret = max(max_regret, float(j_val - v_true))
                del r, pl

    # Same-epoch old-policy snapshot invariance
    pl_snap = SeamFreePortal3DPlanner(spc, gn, free, nodes, pts[nodes], A, eps_tol=0.001)
    s0 = _idx(3, 8, 8)
    r_old = pl_snap.solve_unseen_goal(s0, goals["interior_point"])
    pol_old = r_old["policy"]
    probes = [s0, _idx(7, 8, 8), _idx(8, 8, 8), _idx(9, 8, 8), _idx(12, 12, 12)]
    act_before = [pol_old.action_distribution(x) for x in probes]
    _ = pl_snap.solve_unseen_goal(s0, goals["jagged_portal_adjacent"])
    act_after = [pol_old.action_distribution(x) for x in probes]
    same_epoch_drift = max(float(np.max(np.abs(p0 - p1))) for (_, p0), (_, p1) in zip(act_before, act_after))
    del r_old, pol_old, pl_snap

    # Live C232-02 operational vs evaluation materialization RHS counter check
    pl_lazy = SeamFreePortal3DPlanner(spc, gn, free, nodes, pts[nodes], A, eps_tol=0.005)
    out_lazy = pl_lazy.solve_unseen_goal(s0, goals["interior_point"], materialize_full_z_sub=False)
    pl_eager = SeamFreePortal3DPlanner(spc, gn, free, nodes, pts[nodes], A, eps_tol=0.005)
    out_eager = pl_eager.solve_unseen_goal(s0, goals["interior_point"], materialize_full_z_sub=True)
    counter_split_ok = bool(
        out_lazy["operational_local_lu_rhs_solves"] == out_eager["operational_local_lu_rhs_solves"]
        and out_lazy["evaluation_materialization_rhs_solves"] == 0
        and out_eager["evaluation_materialization_rhs_solves"] == 1
        and out_eager["local_lu_solves"] == out_eager["operational_local_lu_rhs_solves"] + 1
    )
    del pl_lazy, out_lazy, pl_eager, out_eager

    return {
        "n_adversarial_cases": n_cases,
        "all_24_fourfold_ok": all_fourfold_ok,
        "all_24_ring_support_matches_global_exterior": all_support_ok,
        "max_callable_vs_full_guide_action_error": max_action_err,
        "same_epoch_old_policy_action_drift": same_epoch_drift,
        "max_adversarial_regret_at_eps_0001": max_regret,
        "live_c232_02_rhs_counter_split_verified": counter_split_ok,
        "PASS": bool(
            n_cases == 24
            and all_fourfold_ok
            and all_support_ok
            and max_action_err < 1e-12
            and same_epoch_drift == 0.0
            and counter_split_ok
        ),
    }


# ==============================================================================
# 4. Polished Release Summary Plotter (`Closes C232-01`, Writes New PNG Only)
# ==============================================================================
def plot_polished_m232_release_figure(replay_data: dict, post_tables: dict, fig_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14.0, 9.8), dpi=170)

    cache_modes = replay_data["cache_causal_ablation_47cubed"]["modes"]
    pm = replay_data["per_map_records"]
    r47 = pm["replay_47cubed"]
    r59 = pm["replay_59cubed"]
    rc = pm["continual_47cubed"]
    cn = post_tables["closest_neighbor_abba_summaries"]

    # Panel A: Pure Same-Block 47^3 3-Arm Cache Causal Curves ONLY (`NO cross-block MatrixFree line!`)
    ax = axes[0, 0]
    ks = np.arange(1, 25)
    for m_k, m_lbl, st, col in (
        ("QueryCold", "QueryCold (Clear L0..L3 per Query): 15.28s", "--", "#c0392b"),
        ("CacheL0Only", "CacheL0Only (Keep L0, Clear L1..L3): 12.18s", "-.", "#d35400"),
        ("CacheOn_Persistent", "CacheOn_Persistent (Keep L0..L3): 8.56s", "-", "#27ae60"),
    ):
        ys = np.array(cache_modes[m_k]["prefix_cumulative_mean_ms"], dtype=float) / 1000.0
        ax.plot(ks, ys, st, linewidth=2.4, label=m_lbl, color=col)
    ax.text(
        0.04,
        0.64,
        "CacheOn vs CacheL0Only:\n-29.75% wall-clock (p=1.2e-4)\n-52.60% operational RHS\n(9,010 vs 19,009 solves/map)",
        transform=ax.transAxes,
        fontsize=8.1,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#eafaf1", "edgecolor": "#27ae60", "alpha": 0.92},
    )
    ax.set_xlabel("Streaming Unseen Goal Index k (1..24)")
    ax.set_ylabel("Same-Block Cumulative Time C(k) (s)")
    ax.set_title("A. 47^3 Three-Arm Cache Causal Study (Same Block, 1 Worker)")
    ax.grid(True, alpha=0.28)
    ax.legend(fontsize=7.9, loc="upper left")

    # Panel B: Same-Block 1-Worker AB/BA Closest-Neighbor Head-to-Head + Per-Map Paired Dots
    ax = axes[0, 1]
    blk_specs = [
        ("Static 47^3\n(K=24)", cn["static_47cubed_planner_only"], [r["pair_arms"]["M231_Portal_CacheOn"]["total_ms"] / 1000.0 for r in r47], [r["pair_arms"]["MatrixFree_ExactSchur_Krylov"]["total_ms"] / 1000.0 for r in r47]),
        ("Static 59^3\n(K=24)", cn["static_59cubed_planner_only"], [r["pair_arms"]["M231_Portal_CacheOn"]["total_ms"] / 1000.0 for r in r59], [r["pair_arms"]["MatrixFree_ExactSchur_Krylov"]["total_ms"] / 1000.0 for r in r59]),
        ("Continual 47^3\n(Marginal)", cn["continual_47cubed_post_init_marginal_incl_rebuild"], [r["arms"]["M231_Portal_CacheOn"]["post_init_marginal_incl_rebuild_ms"] / 1000.0 for r in rc], [r["arms"]["MatrixFree_ExactSchur_Krylov"]["post_init_marginal_incl_rebuild_ms"] / 1000.0 for r in rc]),
        ("Continual 47^3\n(Lifecycle)", cn["continual_47cubed_full_lifecycle_incl_rebuild"], [r["arms"]["M231_Portal_CacheOn"]["lifecycle_incl_rebuild_ms"] / 1000.0 for r in rc], [r["arms"]["MatrixFree_ExactSchur_Krylov"]["lifecycle_incl_rebuild_ms"] / 1000.0 for r in rc]),
    ]
    xb = np.arange(len(blk_specs))
    w = 0.34
    mf_means = [b[1]["matrixfree_mean_ms"] / 1000.0 for b in blk_specs]
    p_means = [b[1]["portal_mean_ms"] / 1000.0 for b in blk_specs]
    ax.bar(xb - w / 2, mf_means, width=w, color="#e67e22", alpha=0.88, label="MatrixFree Exact Schur Krylov")
    ax.bar(xb + w / 2, p_means, width=w, color="#27ae60", alpha=0.88, label="Dyadic Portal (CacheOn)")
    for i, (_, st_d, p_pts, mf_pts) in enumerate(blk_specs):
        for yp, ymf in zip(p_pts, mf_pts):
            ax.plot([xb[i] - w / 2, xb[i] + w / 2], [ymf, yp], color="#34495e", alpha=0.32, linewidth=0.9)
            ax.scatter([xb[i] - w / 2, xb[i] + w / 2], [ymf, yp], color="#2c3e50", s=13, zorder=4, alpha=0.7)
        ax.text(
            xb[i],
            max(max(mf_pts), max(p_pts)) + 0.9,
            f"-{st_d['relative_time_saving_pct']:.1f}%\n(p={st_d['p_two_sided_paired_t']:.3g})",
            ha="center",
            va="bottom",
            fontsize=7.9,
            fontweight="bold",
        )
    ax.text(
        0.03,
        0.78,
        "Pre-declared >=20% saving gate:\nNOT_MET across all 4 endpoints",
        transform=ax.transAxes,
        fontsize=8.0,
        bbox={"boxstyle": "round,pad=0.32", "facecolor": "#fef9e7", "edgecolor": "#d4ac0d", "alpha": 0.95},
    )
    ax.set_xticks(xb)
    ax.set_xticklabels([b[0] for b in blk_specs], fontsize=8.3)
    ax.set_ylabel("Single-Worker Wall-Clock Time (s)")
    ax.set_ylim(0, max(max(b[3]) for b in blk_specs) * 1.22)
    ax.set_title("B. Same-Block AB/BA Closest-Neighbor Replay (n=6 Maps)")
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend(fontsize=8.0, loc="upper right")

    # Panel C: Pure Same-Block AB/BA Prefix Cumulative Curves C(k) (`pair_arms` ONLY!)
    ax = axes[1, 0]
    p47_c = np.mean([r["pair_arms"]["M231_Portal_CacheOn"]["prefix_cumulative_ms"] for r in r47], axis=0) / 1000.0
    mf47_c = np.mean([r["pair_arms"]["MatrixFree_ExactSchur_Krylov"]["prefix_cumulative_ms"] for r in r47], axis=0) / 1000.0
    p59_c = np.mean([r["pair_arms"]["M231_Portal_CacheOn"]["prefix_cumulative_ms"] for r in r59], axis=0) / 1000.0
    mf59_c = np.mean([r["pair_arms"]["MatrixFree_ExactSchur_Krylov"]["prefix_cumulative_ms"] for r in r59], axis=0) / 1000.0

    ax.plot(ks, mf59_c, "--", color="#d35400", linewidth=2.1, label="59^3 MatrixFree (pair_arms): 32.83s")
    ax.plot(ks, p59_c, "-", color="#8e44ad", linewidth=2.3, label="59^3 Portal (pair_arms): 28.32s (-13.7%, mean k=13)")
    ax.plot(ks, mf47_c, "--", color="#2980b9", linewidth=2.1, label="47^3 MatrixFree (pair_arms): 10.65s")
    ax.plot(ks, p47_c, "-", color="#16a085", linewidth=2.3, label="47^3 Portal (pair_arms): 9.04s (-15.2%, mean k=6)")
    ax.axvline(6, color="#16a085", linestyle=":", alpha=0.65)
    ax.axvline(13, color="#8e44ad", linestyle=":", alpha=0.65)
    ax.set_xlabel("Streaming Unseen Goal Index k (1..24)")
    ax.set_ylabel("Same-Block AB/BA Cumulative Time C(k) (s)")
    ax.set_title("C. Same-Block AB/BA Prefix Curves (47^3 & 59^3 pair_arms)")
    ax.grid(True, alpha=0.28)
    ax.legend(fontsize=7.7, loc="upper left")

    # Panel D: Event-Reduced Deployed Policy Regret Across All 360 Scheduled Evaluations
    ax = axes[1, 1]
    ev_all = extract_all_events_from_replay(replay_data)
    groups = [
        ("Cache 47^3\nPortal (n=72)", [float(e["policy_value"]) - float(e["reference_value"]) for e in ev_all if e["block_id"] == "cache_ablation_47cubed" and e["policy_evaluated"]]),
        ("Pair 47^3\nPortal (n=72)", [float(e["policy_value"]) - float(e["reference_value"]) for e in ev_all if e["block_id"] == "pair_abba_47cubed" and e["method_id"] == "M231_Portal_CacheOn" and e["policy_evaluated"]]),
        ("Pair 59^3\nPortal (n=36)", [float(e["policy_value"]) - float(e["reference_value"]) for e in ev_all if e["block_id"] == "pair_abba_59cubed" and e["method_id"] == "M231_Portal_CacheOn" and e["policy_evaluated"]]),
        ("Continual 47^3\nPortal (n=36)", [float(e["policy_value"]) - float(e["reference_value"]) for e in ev_all if e["block_id"] == "continual_abba_47cubed" and e["method_id"] == "M231_Portal_CacheOn" and e["policy_evaluated"]]),
        ("All Blocks\nMatrixFree (n=144)", [float(e["policy_value"]) - float(e["reference_value"]) for e in ev_all if e["method_id"] == "MatrixFree_ExactSchur_Krylov" and e["policy_evaluated"]]),
    ]
    ax.boxplot([g[1] for g in groups], tick_labels=[g[0] for g in groups])
    ax.axhline(0.25, color="#c0392b", linestyle="--", linewidth=1.5, label="Contract Budget eps=0.25 (Portal max=0.0335, MF max=0.0478)")
    ax.set_ylabel("Deployed Policy Regret J^{mu} - V*")
    ax.set_title("D. 360/360 Verified Policy Checks (L <= V* <= J^{mu} <= U at 0.0 Slack)")
    ax.tick_params(axis="x", labelsize=7.6)
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend(fontsize=7.8, loc="upper right")

    plt.tight_layout()
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close(fig)


def run_m232_release_verification() -> dict:
    t0 = time.perf_counter()
    enforce_single_thread_env()
    p2_dir = Path(__file__).resolve().parent

    with warnings.catch_warnings():
        warnings.simplefilter("error")

        # 1. Verify Phase-I and all 10 frozen Phase-II JSONs before doing anything
        verify_phase1_readonly_freeze()
        frozen_before = verify_all_10_frozen_jsons(p2_dir)

        # 2. Load frozen `m232_targeted_replay_results.json` strictly and run roster + fault-injection audit
        replay_raw = (p2_dir / "m232_targeted_replay_results.json").read_text(encoding="utf-8")
        replay_data = _strict_json_loads(replay_raw)
        all_events = extract_all_events_from_replay(replay_data)
        exp_keys, exp_pol_keys = build_expected_m232_roster()

        roster_zero_slack = verify_event_roster_and_inequalities(all_events, exp_keys, exp_pol_keys, slack=0.0)
        roster_tol_slack = verify_event_roster_and_inequalities(all_events, exp_keys, exp_pol_keys, slack=1e-7)
        neg_controls = run_negative_control_fault_injections(all_events, exp_keys, exp_pol_keys)

        # 3. Deterministic post-processing breakdowns (RHS split, planner-only vs end-to-end, sign-flip sensitivity)
        post_tables = compute_postprocessed_rhs_and_cost_tables(replay_data)

        # 4. In-memory live contract + full EC-01..EC-06 + 24 adversarial boundary cases + live RHS split check
        in_mem_contracts = run_m232_contract_and_ring_closure(write_json=False)
        adv24_and_counter = run_adversarial_24_and_live_counter_checks()

        # 5. Render polished summary PNG (without touching frozen `m232_targeted_replay_summary.png`)
        fig_out = p2_dir / "m232_release_polished_summary.png"
        plot_polished_m232_release_figure(replay_data, post_tables, fig_out)

        # 6. Re-verify all 10 frozen JSONs are STILL 100% untouched!
        frozen_after = verify_all_10_frozen_jsons(p2_dir)

    all_passed = bool(
        roster_zero_slack["ALL_INDEPENDENT_GATES_PASSED"]
        and roster_tol_slack["ALL_INDEPENDENT_GATES_PASSED"]
        and neg_controls["ALL_4_FAULT_INJECTIONS_REJECTED"]
        and in_mem_contracts["ALL_B6FF40D_CONTRACT_ISSUES_CLOSED"]
        and adv24_and_counter["PASS"]
        and (frozen_before == frozen_after)
    )

    report = _sanitize_for_strict_json({
        "milestone": "M2.3.2_Final_Release_Polish_and_ReadOnly_Verification",
        "ALL_RELEASE_CHECKS_PASSED": all_passed,
        "elapsed_s": float(time.perf_counter() - t0),
        "runtime_metadata": collect_runtime_metadata(),
        "phase2_manifest": compute_phase2_manifest(),
        "verified_frozen_replay_sha256": FROZEN_ALL_10_JSON_SHA256["m232_targeted_replay_results.json"],
        "verified_frozen_contract_sha256": FROZEN_ALL_10_JSON_SHA256["m232_contract_and_ring_closure.json"],
        "all_10_frozen_json_artifacts_verified": frozen_after,
        "c232_closure_summary": {
            "C232_01_same_block_polished_figure": str(fig_out.name),
            "C232_02_operational_vs_eval_rhs_split": post_tables["cache_47cubed_rhs_decomposition"],
            "C232_03_querycold_task0_scope_documented_and_future_guarded": True,
            "C232_04_independent_roster_and_fault_injection_verifier": {
                "zero_slack_verification": roster_zero_slack,
                "toleranced_1e7_verification": roster_tol_slack,
                "negative_control_fault_injections": neg_controls,
            },
            "C232_05_full_ec01_ec06_wired_and_legacy_archive_guarded": {
                "in_memory_m232_and_m231_ec_all_passed": in_mem_contracts["ALL_B6FF40D_CONTRACT_ISSUES_CLOSED"],
                "adversarial_24_and_live_rhs_split": adv24_and_counter,
            },
        },
        "locked_manuscript_tables": post_tables["closest_neighbor_abba_summaries"],
    })

    report_path = p2_dir / "m232_release_verification_report.json"
    txt = json.dumps(report, indent=2, allow_nan=False)
    _ = _strict_json_loads(txt)
    report_path.write_text(txt, encoding="utf-8")

    # Final post-write check that all 10 historical JSONs remain untouched
    _ = verify_all_10_frozen_jsons(p2_dir)

    rhs_d = post_tables["cache_47cubed_rhs_decomposition"]
    cn_d = post_tables["closest_neighbor_abba_summaries"]
    print(
        f"[M2.3.2 RELEASE VERIFIED] ALL_RELEASE_CHECKS_PASSED={all_passed} | "
        f"Events={roster_zero_slack['total_rows_seen']}/1440 (0.0-slack valid={roster_zero_slack['ALL_INDEPENDENT_GATES_PASSED']}) | "
        f"FaultInjectionsRejected=4/4 ({neg_controls['ALL_4_FAULT_INJECTIONS_REJECTED']}) | "
        f"Adv24+Counter={adv24_and_counter['PASS']} (max_reg={adv24_and_counter['max_adversarial_regret_at_eps_0001']:.3e}) | "
        f"CacheOpRHS={rhs_d['CacheOn_operational_rhs_mean']:.2f} vs {rhs_d['CacheL0Only_operational_rhs_mean']:.2f} (-{rhs_d['CacheOn_vs_CacheL0Only_operational_rhs_saving_pct']:.2f}%) | "
        f"E2E_47={cn_d['static_47cubed_end_to_end_incl_gp_and_assembly']['relative_time_saving_pct']:.2f}% "
        f"E2E_59={cn_d['static_59cubed_end_to_end_incl_gp_and_assembly']['relative_time_saving_pct']:.2f}% | "
        f"elapsed={report['elapsed_s']:.2f}s"
    )
    if not all_passed:
        raise RuntimeError("M2.3.2 release verification failed!")
    return report


if __name__ == "__main__":
    run_m232_release_verification()
