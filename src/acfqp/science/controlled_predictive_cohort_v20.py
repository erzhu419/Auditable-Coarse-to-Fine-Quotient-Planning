"""Frozen variance-based allocation on the complete exposed V18 cohort."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR, V7Case

V18_ROSTER = "controlled_predictive_cohort_roster_v18.json"
V19_ROSTER = "controlled_predictive_cohort_roster_v19.json"
METHODS = ("full_state_empirical", "exact_empirical_quotient", "online_mass_bound",
           "online_cached_balanced_gap_stop", "online_variance_gap_stop")
ONLINE_METHODS = METHODS[2:]
CANDIDATE_METHODS = METHODS[3:]


def _source(reports_dir: str | Path | None):
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    return directory, json.loads((directory / V18_ROSTER).read_text(encoding="utf-8"))


def cases_v20(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    _, roster = _source(reports_dir)
    return tuple(V7Case(**(row["case"] | {"board": tuple(row["case"]["board"])})) for row in roster["cases"])


def build_cohort_roster_v20(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    directory, roster = _source(reports_dir)
    witnesses = json.loads((directory / V19_ROSTER).read_text(encoding="utf-8"))["source_witnesses"]
    roster.pop("v18_target_acquisition_execution_or_outcomes_evaluated")
    for key in ("legacy_v15_comparison", "legacy_v17_comparison", "current_cached_comparison"):
        roster.pop(key)
    cached_rule = roster["acquisition_methods"]["online_cached_balanced_gap_stop"]
    cached_stopping = roster["candidate_stopping"]["online_cached_balanced_gap_stop"]
    roster.update(
        schema="controlled_predictive_cohort_roster_v20",
        status="REGISTERED_BEFORE_V20_TARGET_ACQUISITION_EXECUTION_AND_OUTCOMES",
        v20_target_acquisition_execution_or_outcomes_evaluated=False,
        input_roster=V18_ROSTER,
        methods=list(METHODS), online_methods=list(ONLINE_METHODS), candidate_methods=list(CANDIDATE_METHODS),
        gap_methods=list(CANDIDATE_METHODS),
        query_execution_count_scope="Each of five methods uses all16 original cases x3 seeds x10 queries; three ONLINE methods produce1440 adaptive history trees.",
        split_label_scope="Original PRIMARY splits, families and mass groups remain historical development metadata; no source representation is fitted in V20.",
        scope="Previously exposed development inputs only. V20 changes repeated-observation allocation while retaining V18 cached stopping, structural acquisition, execution and the original scientific FAIL. All480 contexts and all ten diagnostic witnesses remain included.",
    )
    roster["acquisition_methods"] = {
        "online_mass_bound": roster["acquisition_methods"]["online_mass_bound"],
        "online_cached_balanced_gap_stop": cached_rule,
        "online_variance_gap_stop": {"label": "VARIANCE", "repeat_observations": True,
            "rule": "Run unchanged V18 gap stopping and V14 structural select_row first. With no structural frontier, prioritize known positive-range rows by frozen empirical variance reduction in the incumbent-minus-challenger action difference; otherwise fall back to original BALANCED selection."},
    }
    roster["candidate_stopping"] = {method: list(cached_stopping) for method in CANDIDATE_METHODS}
    warm = roster["warm_preparation"]
    warm["shared_by_methods"] = list(ONLINE_METHODS)
    warm["integer_count_conversions"] = {
        "cached_gap": {"planner": "Unchanged V18 CachedGapPlannerState", "shared_by_methods": [CANDIDATE_METHODS[0]]},
        "variance": {"planner": "VarianceGapPlannerState", "shared_by_methods": [CANDIDATE_METHODS[1]]},
        "physical_conversions_per_case_seed": 2,
        "attribution": "Each candidate bears the full paid common warm and its own independent planner conversion. Perform each conversion once per case/seed physically. Divide setup by ten only for declared batch attribution; BASE pays no conversion. Charge all scoring, copying, cache maintenance, updates and fallbacks.",
    }
    roster["cached_allocation"] = roster.pop("gap_allocation")
    roster["cached_allocation"]["recomputation"] = "CACHED uses unchanged V18 gap caches and upper-score reuse for original BALANCED selection."
    roster["gap_score"]["recomputation"] = "Both candidates use the unchanged V18 incremental gap cache and original V17 STOP executor semantics. Variance allocation does not change gap assessments or stopping thresholds."
    roster["score_cache"]["comparison"] = "Preserve V18 cached gap calculation and diagnostics. Only the unchanged CACHED control must reproduce old full histories; VARIANCE acquisition histories may change."
    roster["variance_allocation"] = {
        "incumbent": "Current empirical lower-bound maximizing action, with original alphabetical ties.",
        "challenger": "Original gap upper-maximizing other legal action, with original ties.",
        "continuation_policy": "Use the same current empirical lower-bound continuation policy for both first-action paths.",
        "net_coefficient": "c = empirical_reach_incumbent - empirical_reach_challenger; accumulate all paths to a shared observed row before squaring.",
        "return": "Y = query.reward_weight * reward + cache.lower[successor]",
        "sample_count": "n = 256 * row_batch_count",
        "sample_variance": "s2 = n/(n-1) * sum(p * (Y - sum(p*Y))**2)",
        "score": "c**2 * s2 * (1/n - 1/(n+256))",
        "eligibility": "Known rows with positive original physical range; stop traversal at unknown rows and leave them to unchanged structural bounds/acquisition.",
        "ties": "Maximum score, then fewer accumulated batches, then original row key/action order.",
        "fallback": "Use unchanged BALANCED selection when there is no challenger or no positive variance-reduction score. Zero empirical variance and net cancellation do not add a stopping condition.",
        "computation": "Recompute the variance allocation from the current model at each request; charge propagation, row/successor reads, variance calculation and fallback. No added allocation-score cache.",
        "scope": "First-order allocation proxy under a frozen empirical continuation policy; no confidence interval, oracle correction, unfavorable-batch removal or new stopping threshold.",
    }
    roster["history_evaluation"].update(
        execution_tree_count=1440,
        execution_order="Rotate the three ONLINE methods by(case_index + seed_index + query_index) modulo3.",
        physical_cost="Count common warm acquisition once, two independent candidate conversions once each, every post-warm batch request across every method/query/history, and one shared full-row benchmark acquisition. Sibling-history cloning is physical audit work.",
    )
    roster["history_policy_examples"] = [example | {"method": "online_variance_gap_stop"}
        for example in roster["history_policy_examples"]]
    roster["legacy_v14_comparison"]["scope"] = roster["legacy_v14_comparison"]["scope"].replace("V18", "V20")
    roster["legacy_v18_comparison"] = {
        "input_result": "controlled_predictive_score_cache_v18.json.gz",
        "method": "online_cached_balanced_gap_stop", "query_tree_count": 480,
        "trace_ignored_fields": [],
        "scope": "After every current history freezes, compare newly paid CACHED full traces and root metrics exactly to retained V18. Historical results are validation only; candidate VARIANCE traces may differ.",
    }
    roster["source_witnesses"] = witnesses
    roster["witness_comparison"] = {
        "source_roster": V19_ROSTER, "source_witness_count": 10, "included_count": 10, "included_all": True,
        "source_group_counts": {"two_cached_regressions_versus_base": 2, "original_eight_base_worse_than_full": 8},
        "v19_divergence_contexts": 6, "v19_no_divergence_contexts": 4,
        "selection": "Keep all ten original identities and groups fixed before V20 results, including the four without V19 first-action divergences. All are part of the full480-context comparison; do not restrict execution or conclusions to the six decomposed contexts.",
    }
    return roster


def freeze_cohort_roster_v20(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v20(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
