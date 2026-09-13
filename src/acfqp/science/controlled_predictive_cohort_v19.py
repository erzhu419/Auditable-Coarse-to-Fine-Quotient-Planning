"""Frozen local snapshot decomposition of retained V18 first divergences."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR

V18_ROSTER = "controlled_predictive_cohort_roster_v18.json"
V18_DIVERGENCES = "controlled_predictive_first_divergences_v18.json"
METHODS = ("BASE", "CACHED")
PHASES = ("BEFORE_LAST_BATCH", "AFTER_LAST_BATCH")


def build_cohort_roster_v19(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    source = json.loads((directory / V18_DIVERGENCES).read_text(encoding="utf-8"))
    previous = json.loads((directory / V18_ROSTER).read_text(encoding="utf-8"))
    case_records = {row["case"]["name"]: row for row in previous["cases"]}
    contexts, exclusions = [], []
    for witness_index, witness in enumerate(source["witnesses"]):
        identity = {"case_name": witness["case"], "sample_seed": witness["seed"],
                    "query_name": witness["query"], "group": witness["group"],
                    "source_witness_index": witness_index}
        if not witness["divergences"]:
            exclusions.append(identity | {"reason": "NO_FIRST_ACTION_DIVERGENCE", "source_witness": witness})
            continue
        direction = "regression" if witness["cached_minus_base_value"] < 0 else "improvement"
        for divergence_index, divergence in enumerate(witness["divergences"]):
            contexts.append(identity | {"context_index": len(contexts),
                "source_divergence_index": divergence_index, "direction": direction,
                "case": case_records[witness["case"]]["case"],
                "query": previous["queries"][witness["query"]],
                "history": divergence["history"], "history_edges": divergence["history_edges"],
                "target_key": divergence["key"], "compared_actions": divergence["compared_selected_actions"],
                "divergence": divergence})
    selected_cases = list(dict.fromkeys(row["case_name"] for row in contexts))
    selected_seeds = sorted({row["sample_seed"] for row in contexts})
    warm_runs = sorted({(row["case_name"], row["sample_seed"]) for row in contexts})
    snapshots = [{"context_index": row["context_index"], "method": method, "phase": phase}
                 for row in contexts for method in METHODS for phase in PHASES]
    return {
        "schema": "controlled_predictive_cohort_roster_v19",
        "status": "REGISTERED_BEFORE_V19_SNAPSHOT_CONSTRUCTION_AND_LOCAL_TRUTH_EVALUATION",
        "snapshot_construction_or_local_truth_evaluated": False,
        "input_divergences": V18_DIVERGENCES, "input_roster": V18_ROSTER,
        "input_histories": "controlled_predictive_score_cache_v18.json.gz",
        "source_witness_count": len(source["witnesses"]), "source_witnesses": source["witnesses"],
        "source_group_context_counts": source["group_context_counts"],
        "source_retained_count_checks": source["retained_count_checks"],
        "source_unavailable": source["unavailable"],
        "contexts": contexts, "context_count": len(contexts),
        "direction_counts": dict(Counter(row["direction"] for row in contexts)),
        "excluded_contexts": exclusions, "excluded_context_count": len(exclusions),
        "selection_rule": "Include every first-action divergence already recorded in the original ten V18 witnesses; retain witnesses without a divergence as explicit exclusions. Fix regression/improvement groups from retained V18 root-value differences before computing any local decomposition.",
        "cases": [case_records[name] for name in selected_cases], "case_count": len(selected_cases),
        "queries": previous["queries"], "initial_query_order": previous["initial_query_order"],
        "query_roles": previous["query_roles"], "sample_seeds": previous["sample_seeds"],
        "selected_sample_seeds": selected_seeds,
        "historical_exposure": previous["historical_exposure"],
        "historical_primary_case_splits": previous["historical_primary_case_splits"],
        "methods": list(METHODS),
        "method_implementations": {"BASE": "Unchanged V14 MassBoundPlannerState",
            "CACHED": "Unchanged V18 CachedGapPlannerState with the original V17 STOP executor semantics"},
        "phases": list(PHASES), "snapshot_manifest": snapshots, "snapshot_count": len(snapshots),
        "snapshot_rule": "Replay each retained history independently to the selected decision; retain a complete planner snapshot immediately before and immediately after that method's final acquisition batch at the decision. Keep both LEFT and RIGHT action values and the snapshot's frozen continuation policies.",
        "snapshot_then_truth_order": "Freeze all24 declared snapshots and their empirical policies before any local true transition, optimum or counterfactual continuation evaluation.",
        "warm_replay": {
            "planner": "Unchanged V14 MASS_BOUND32 with all original ten warm queries and query order",
            "case_seed_runs": [{"case_name": name, "sample_seed": seed} for name, seed in warm_runs],
            "trajectory_count": len(warm_runs), "batch_cap_per_trajectory": 32,
            "samples_per_batch": 256, "total_replayed_batches": 32 * len(warm_runs),
            "physical_regenerated_draws": 32 * len(warm_runs) * 256,
            "stream": previous["row_stream"],
            "new_independent_draws": 0,
            "scope": "Regenerate exactly the two retained batch-zero warm prefixes once each; share their immutable results across snapshot reconstruction. Count their actual generation cost, even though these replay draws do not provide new independent evidence.",
        },
        "suffix_replay": {"source": "Retained V18 requested and observed batches along each fixed history",
            "new_provider_calls": 0, "new_physical_draws": 0,
            "scope": "Read retained observed batch aggregates and pool the original integer counts; do not request replacement, additional or independent suffix samples. Account for reconstruction and snapshot cloning work."},
        "decomposition": {
            "actions": ["LEFT", "RIGHT"], "remaining_horizon": 2,
            "identity": "Qhat(a)-Qstar(a) = (E_Phat-E_P)[r+Vstar] + E_Phat[Vhat-Vstar]",
            "transition_component": "(E_Phat-E_P)[r+Vstar]",
            "continuation_estimation_component": "E_Phat[Vhat-Vtrue_pi_snapshot]",
            "continuation_policy_component": "E_Phat[Vtrue_pi_snapshot-Vstar]",
            "policy_scope": "Freeze the continuation chosen by that snapshot and action before evaluating its true value. Do not mix later adaptive policy improvements into a frozen snapshot's decomposition.",
            "oracle_scope": "Local exact transitions and optimal values are evaluator-only labels after snapshot freezing; they are not returned as new planning observations.",
        },
        "all_source_witnesses_retained": True,
        "source_fits": 0, "source_setup_seconds": 0.0,
        "u006_assurance_started": False, "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Posthoc local diagnostic on previously exposed retained failures and improvements. These six contexts and24 snapshots are not an independent cohort, new sample experiment, scientific Gate or causal proof from resampling intervention.",
    }


def freeze_cohort_roster_v19(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v19(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
