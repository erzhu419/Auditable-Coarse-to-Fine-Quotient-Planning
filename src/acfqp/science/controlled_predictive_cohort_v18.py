"""Frozen V18 scoring-cache comparison preserving complete V17 STOP histories."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR, V7Case

V17_ROSTER = "controlled_predictive_cohort_roster_v17.json"
METHODS = ("full_state_empirical", "exact_empirical_quotient", "online_mass_bound",
           "online_balanced_resampling", "online_balanced_gap_stop", "online_cached_balanced_gap_stop")
ONLINE_METHODS = METHODS[2:]
CANDIDATE_METHODS = METHODS[3:]
GAP_METHODS = METHODS[4:]


def _source(reports_dir: str | Path | None) -> dict:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    return json.loads((directory / V17_ROSTER).read_text(encoding="utf-8"))


def cases_v18(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    return tuple(V7Case(**(row["case"] | {"board": tuple(row["case"]["board"])}))
                 for row in _source(reports_dir)["cases"])


def build_cohort_roster_v18(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    roster = _source(reports_dir)
    roster.pop("v17_target_acquisition_execution_or_outcomes_evaluated")
    roster.pop("current_continue_comparison")
    roster.update(
        schema="controlled_predictive_cohort_roster_v18",
        status="REGISTERED_BEFORE_V18_TARGET_ACQUISITION_EXECUTION_AND_OUTCOMES",
        v18_target_acquisition_execution_or_outcomes_evaluated=False,
        input_roster=V17_ROSTER,
        methods=list(METHODS), online_methods=list(ONLINE_METHODS), candidate_methods=list(CANDIDATE_METHODS),
        gap_methods=list(GAP_METHODS),
        split_label_scope="Original PRIMARY splits, families and mass groups remain historical development metadata; no source representation is fitted in V18.",
        scope="Previously exposed development inputs only. V18 measures scoring computation and cache costs while requiring exact complete V17 STOP histories. Original inputs, query weights, sampling, stopping, action selection and the scientific FAIL remain unchanged.",
    )
    warm = roster["warm_preparation"]
    warm["shared_by_methods"] = list(ONLINE_METHODS)
    conversions = warm["integer_count_conversions"]
    conversions["gap"]["shared_by_methods"] = ["online_balanced_gap_stop"]
    conversions["cached_gap"] = {"planner": "CachedGapPlannerState", "shared_by_methods": ["online_cached_balanced_gap_stop"]}
    conversions["physical_conversions_per_case_seed"] = 3
    conversions["attribution"] = "Each method bears the full paid common warm cost and its own planner-type conversion. Perform balanced, original gap and cached gap conversions separately once per case/seed, charging each physically. Divide setup by ten only for declared batch attribution; BASE pays no conversion. All cache initialization, update and copy work is paid."
    roster["candidate_stopping"].pop("online_balanced_gap_continue")
    roster["candidate_stopping"]["online_cached_balanced_gap_stop"] = list(roster["candidate_stopping"]["online_balanced_gap_stop"])
    roster["acquisition_methods"].pop("online_balanced_gap_continue")
    roster["acquisition_methods"]["online_cached_balanced_gap_stop"] = (
        roster["acquisition_methods"]["online_balanced_gap_stop"] | {"label": "CACHED_BALANCED_STOP"})
    roster["gap_score"]["recomputation"] = "Original STOP fully recomputes V16 scoring. Cached STOP initializes each query cache once, then recomputes changed states and observed ancestors; mathematical operations and deterministic order remain unchanged."
    roster["gap_allocation"]["recomputation"] = "Both STOP methods call the unchanged V17 executor and V15 balanced selection. Original STOP recomputes its scores; cached STOP reuses the identical maintained gap upper scores for balanced selection. Both retain full gap assessments and charge score traversal, cache updates and copies."
    roster["score_cache"] = {
        "queries": "History-local per-query gap scoring caches; do not share mutable caches across sibling histories or methods.",
        "invalidation": "After a first or repeated row batch, mark the changed row state, newly observed successors and observed ancestors dirty for every initialized query cache. Recompute in increasing remaining horizon and original deterministic state/action order.",
        "balanced_score_reuse": "The gap upper recurrence equals the V15 BALANCED upper scoring recurrence. Return its maintained upper values, action values, policy and radius for unchanged balanced reach/selection.",
        "diagnostics": "Keep every original gap assessment and candidate-path diagnostic; no early exit, approximation, arithmetic reassociation, pruning or changed tie-breaking.",
        "clone": "Copy score maps and dirty sets with each planner history clone; include query-entry copying in deployment and sibling copying in physical audit.",
        "comparison": "Require complete cached/original STOP trace and root metrics equality, with no fields excluded. Measure costs and work counters separately.",
    }
    roster["history_evaluation"]["physical_cost"] = "Count common warm acquisition once, three independent planner conversions once each, every post-warm batch request across every method/query/history, and one shared full-row benchmark acquisition. Sibling-history cloning is physical audit work."
    roster["history_policy_examples"] = [example | {"method": "online_cached_balanced_gap_stop"}
        for example in roster["history_policy_examples"]]
    for key in ("legacy_v14_comparison", "legacy_v15_comparison"):
        roster[key]["scope"] = roster[key]["scope"].replace("V17", "V18")
    roster["legacy_v17_comparison"] = {
        "input_result": "controlled_predictive_balanced_stop_v17.json.gz",
        "method": "online_balanced_gap_stop", "query_tree_count": 480,
        "scope": "After all current trees freeze, compare newly paid original STOP complete traces and root metrics exactly to retained V17 STOP. No trace fields are excluded; historical results are validation only.",
    }
    roster["current_cached_comparison"] = {
        "candidate": "online_cached_balanced_gap_stop", "comparator": "online_balanced_gap_stop",
        "query_tree_count": 480, "compared_fields": ["trace", "root_metrics"], "trace_ignored_fields": [],
        "scope": "After all current trees freeze, require exact full observation, diagnostic, action and child-history equality. Costs and work counters remain separate outcomes.",
    }
    return roster


def freeze_cohort_roster_v18(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v18(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
