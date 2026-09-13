"""Frozen V17 balanced allocation with the unchanged V16 local gap stop."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR, V7Case

V16_ROSTER = "controlled_predictive_cohort_roster_v16.json"
METHODS = ("full_state_empirical", "exact_empirical_quotient", "online_mass_bound",
           "online_balanced_resampling", "online_balanced_gap_continue", "online_balanced_gap_stop")
ONLINE_METHODS = METHODS[2:]
CANDIDATE_METHODS = METHODS[3:]
GAP_METHODS = METHODS[4:]


def _source(reports_dir: str | Path | None) -> dict:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    return json.loads((directory / V16_ROSTER).read_text(encoding="utf-8"))


def cases_v17(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    return tuple(V7Case(**(row["case"] | {"board": tuple(row["case"]["board"])}))
                 for row in _source(reports_dir)["cases"])


def build_cohort_roster_v17(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    roster = _source(reports_dir)
    roster.pop("v16_target_acquisition_execution_or_outcomes_evaluated")
    roster.update(
        schema="controlled_predictive_cohort_roster_v17",
        status="REGISTERED_BEFORE_V17_TARGET_ACQUISITION_EXECUTION_AND_OUTCOMES",
        v17_target_acquisition_execution_or_outcomes_evaluated=False,
        input_roster=V16_ROSTER,
        methods=list(METHODS), online_methods=list(ONLINE_METHODS), candidate_methods=list(CANDIDATE_METHODS),
        gap_methods=list(GAP_METHODS),
        split_label_scope="Original PRIMARY splits, families and mass groups remain historical development metadata; no source representation is fitted in V17.",
        scope="Previously exposed development inputs only. V17 isolates the unchanged V16 local gap stop with V15 balanced allocation, retaining all original inputs, physical bounds, indexed streams and the original scientific FAIL.",
    )
    warm = roster["warm_preparation"]
    warm["shared_by_methods"] = list(ONLINE_METHODS)
    warm["integer_count_conversions"]["gap"]["shared_by_methods"] = list(GAP_METHODS)
    for previous, method, label in zip(("online_gap_continue", "online_gap_stop"), GAP_METHODS,
                                       ("BALANCED_CONTINUE", "BALANCED_STOP")):
        roster["candidate_stopping"][method] = roster["candidate_stopping"].pop(previous)
        roster["acquisition_methods"].pop(previous)
        roster["acquisition_methods"][method] = {
            "label": label, "repeat_observations": True,
            "rule": "Before each batch compute the unchanged V16 action gap; " + (
                "stop this decision when separated. " if method == "online_balanced_gap_stop"
                else "record separation and continue. ")
                + "Otherwise use unchanged V14 structural select_row if available, then unchanged V15 BALANCED score-policy candidates and fewest prior batches with key/action ties.",
        }
    roster["gap_allocation"] = {
        "rule": "Use the unchanged V15 BALANCED allocation and resampling score in balanced_resampling_score; V16 incumbent/challenger paths do not choose acquisition rows.",
        "structural_priority": "If STOP has not stopped the current decision, unchanged V14 select_row takes precedence. With no structural frontier, use the V15 score-policy reachable known positive-radius rows.",
        "selection": "Fewest accumulated row batches, then key/action ties. Each first or repeated acquisition costs one256-draw batch.",
        "recomputation": "Recompute the V16 gap assessment before every acquisition decision and V15 BALANCED acquisition scores when needed. All calculation work is charged; no score caching optimization.",
        "no_eligible_row": "A distinct local stopping reason; not interpreted as action separation.",
        "stop_scope": "BALANCED_STOP ends acquisition only at the current ACTIVE state. The next observed child receives a fresh gap check and quota.",
    }
    roster["history_policy_examples"] = [example | {"method": "online_balanced_gap_stop"}
        for example in roster["history_policy_examples"]]
    for key in ("legacy_v14_comparison", "legacy_v15_comparison"):
        roster[key]["scope"] = roster[key]["scope"].replace("V16", "V17")
    roster["current_continue_comparison"] = {
        "candidate": "online_balanced_gap_continue", "comparator": "online_balanced_resampling",
        "query_tree_count": 480,
        "compared_fields": ["projected_trace", "root_metrics"],
        "trace_ignored_fields": ["gap_assessments", "decision_kind"],
        "scope": "After all current trees freeze, compare complete retained observations and decisions exactly after removing gap-only diagnostics and method labels. CONTINUE must reproduce BALANCED acquisition and policy semantics while paying the added gap computation cost.",
    }
    return roster


def freeze_cohort_roster_v17(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v17(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
