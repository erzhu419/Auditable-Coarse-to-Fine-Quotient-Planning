"""Frozen V16 action-gap allocation and stopping comparison on V15 inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR, V7Case

V15_ROSTER = "controlled_predictive_cohort_roster_v15.json"
METHODS = ("full_state_empirical", "exact_empirical_quotient", "online_mass_bound",
           "online_balanced_resampling", "online_gap_continue", "online_gap_stop")
ONLINE_METHODS = METHODS[2:]
CANDIDATE_METHODS = METHODS[3:]
GAP_METHODS = METHODS[4:]


def _source(reports_dir: str | Path | None) -> dict:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    return json.loads((directory / V15_ROSTER).read_text(encoding="utf-8"))


def cases_v16(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    return tuple(V7Case(**(record["case"] | {"board": tuple(record["case"]["board"])}))
                 for record in _source(reports_dir)["cases"])


def build_cohort_roster_v16(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    roster = _source(reports_dir)
    roster.pop("v15_target_acquisition_execution_or_outcomes_evaluated")
    balanced_score = roster.pop("resampling_score")
    roster.update(
        schema="controlled_predictive_cohort_roster_v16",
        status="REGISTERED_BEFORE_V16_TARGET_ACQUISITION_EXECUTION_AND_OUTCOMES",
        v16_target_acquisition_execution_or_outcomes_evaluated=False,
        input_roster=V15_ROSTER,
        methods=list(METHODS), online_methods=list(ONLINE_METHODS), candidate_methods=list(CANDIDATE_METHODS),
        query_execution_count_scope="Each of six methods uses the original 16 cases x 3 seeds x 10 queries; four ONLINE methods produce1920 adaptive history trees.",
        split_label_scope="Original PRIMARY splits, families and mass groups are historical development metadata; no source representation is fitted in V16.",
        balanced_resampling_score=balanced_score,
        candidate_stopping={
            "online_balanced_resampling": ["total_batch_cap", "current_decision_quota", "terminal_state", "no_eligible_row"],
            "online_gap_continue": ["total_batch_cap", "current_decision_quota", "terminal_state", "no_eligible_row"],
            "online_gap_stop": ["total_batch_cap", "current_decision_quota", "terminal_state", "heuristic_action_separation", "no_eligible_row"],
        },
        gap_methods=list(GAP_METHODS),
        scope="Previously exposed development inputs only. V16 compares action-gap sampling allocation with and without local heuristic stopping; original scientific FAIL, cases, queries, structural mass bounds and indexed sample streams remain frozen.",
    )
    warm = roster["warm_preparation"]
    warm["shared_by_methods"] = list(ONLINE_METHODS)
    warm.pop("integer_count_conversion")
    warm["integer_count_conversions"] = {
        "balanced": {"planner": "Unchanged V15 ResamplingPlannerState", "shared_by_methods": ["online_balanced_resampling"]},
        "gap": {"planner": "GapPlannerState", "shared_by_methods": list(GAP_METHODS)},
        "physical_conversions_per_case_seed": 2,
        "conversion": "Each conversion clones the paid32-cap warm model and reconstructs integer counts; each observed row initially has one256-draw batch.",
        "attribution": "Each candidate bears the complete common warm cost plus its own planner-type conversion. Charge each conversion once physically; divide setup by ten only for declared batch attribution. BASE pays no conversion.",
    }
    roster["acquisition_methods"].pop("online_directed_resampling")
    for method, label in zip(GAP_METHODS, ("GAP_CONTINUE", "GAP_STOP")):
        roster["acquisition_methods"][method] = {
            "label": label, "repeat_observations": True,
            "rule": "Before each batch compute the current action gap; " + (
                "stop this decision when separated. " if method == "online_gap_stop" else "record separation and continue. ")
                + "Otherwise use unchanged V14 structural select_row if available; with no structural frontier, acquire the maximal combined incumbent/challenger path contribution, then key/action ties.",
        }
    roster["gap_score"] = {
        "terminal": "Original terminal query value for both Vminus and Vplus.",
        "unknown_action": "Original V14 physical mass-bound Qlower and Qupper.",
        "known_action_minus": "sum(p * (reward_weight * reward + successor_Vminus)) - radius",
        "known_action_plus": "sum(p * (reward_weight * reward + successor_Vplus)) + radius",
        "radius": "(V14 physical Qupper - V14 physical Qlower) / sqrt(256 * row_batch_count)",
        "state_minus_and_plus": "Separately maximize legal action Qminus and Qplus; alphabetical ties.",
        "clipping": False, "statistical_confidence_interval": False,
        "recomputation": "Full recomputation at each acquisition decision, charged to that method.",
        "incumbent": "Current original empirical maximal-QL action with alphabetical ties.",
        "challenger": "Among other legal actions, maximal heuristic Qplus with alphabetical ties.",
        "separated": "There is only one legal action, or incumbent Qminus >= challenger Qplus.",
        "scope": "Heuristic intervals and separation do not provide statistical confidence or a policy-optimality guarantee.",
    }
    roster["gap_allocation"] = {
        "paths": "Fix the incumbent as first action and follow maximal-Qminus successors; fix the challenger as first action and follow maximal-Qplus successors. Propagate empirical reach through known rows only.",
        "eligibility": "Positive empirical reach and positive radius for known rows, or positive physical width for unknown rows. Known zero-radius rows still propagate reach. With only one legal action, CONTINUE retains the incumbent path without a challenger.",
        "known_row_contribution": "Sum empirical reach times radius across the two paths.",
        "unknown_frontier_contribution": "Sum empirical reach times physical completion width across the two paths; do not traverse unknown transitions.",
        "selection": "Maximum accumulated contribution, then key/action ties; acquire one256-draw batch, including for an already observed row.",
        "structural_priority": "If STOP has not stopped this decision, original V14 select_row takes precedence over the gap-path candidate choice.",
        "no_eligible_row": "A distinct local stopping reason; not interpreted as action separation.",
        "stop_scope": "GAP_STOP separation ends acquisition only at the current ACTIVE state; the next observed child receives a fresh gap check and quota.",
    }
    roster["history_evaluation"].update(
        execution_tree_count=roster["query_execution_context_count"] * len(ONLINE_METHODS),
        execution_order="Rotate the four ONLINE methods by(case_index + seed_index + query_index) modulo4.",
        physical_cost="Count shared warm acquisition once, separate balanced and gap conversions once each, every post-warm batch call across all counterfactual histories, and one shared full-row benchmark acquisition. Sibling-history cloning is audit work.",
        labels="Freeze all method/query execution trees before computing true optimal labels.",
    )
    roster["history_policy_examples"] = [example | {"method": "online_gap_stop"}
        for example in roster["history_policy_examples"]]
    roster["legacy_v14_comparison"]["scope"] = (
        "After all V16 trees freeze, compare the newly paid BASE48 warm prefixes and480 full ONLINE trees to retained V14 results. Compare trace and outcome semantics, not time.")
    roster["legacy_v15_comparison"] = {
        "input_result": "controlled_predictive_resampling_v15.json.gz",
        "method": "online_balanced_resampling", "query_tree_count": 480,
        "scope": "After all V16 trees freeze, read retained V15 BALANCED trees and require exact trace/root outcome reproduction. V16 pays its own batches and conversion; historical data is validation only.",
    }
    return roster


def freeze_cohort_roster_v16(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v16(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
