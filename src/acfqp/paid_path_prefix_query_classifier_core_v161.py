"""Build V161 classifier traces only from already-paid path-first batches."""

from __future__ import annotations

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp.fair_unified_factor_prior_ablation_acquisition_v129r1 import (
    fair_witness_blind_path_first_stream_v129r1,
)
from acfqp.progressive_raw_prefix_query_classifier_core_v160 import (
    anonymous_raw_delta_feature_rows_v160,
    evaluate_progressive_raw_prefix_expression_v160,
    synthesize_progressive_raw_prefix_classifier_v160,
)


SOURCE_PREFIX_OBSERVATION_CAP_V161 = 8


def build_paid_path_prefix_trace_v161(
    adapter, *, maximum_prefix_observations: int = SOURCE_PREFIX_OBSERVATION_CAP_V161
):
    if maximum_prefix_observations <= 0:
        raise ValueError("V161 source prefix cap must be positive")
    observations = []
    rows = []
    prefixes = []
    for index, batch in enumerate(
        fair_witness_blind_path_first_stream_v129r1(adapter), start=1
    ):
        observations.append({"action_key": batch[0].action.key, "rows": batch})
        rows.extend(batch)
        features = anonymous_raw_delta_feature_rows_v160(observations)
        prefixes.append(
            {
                "prefix_observation_count": index,
                "raw_transition_count": len(rows),
                "raw_transition_rows": [row.to_document() for row in rows],
                "raw_transition_sha256": ground._raw_sha(tuple(rows)),  # noqa: SLF001
                "anonymous_raw_delta_feature_rows": [
                    list(feature_row) for feature_row in features
                ],
            }
        )
        if index == maximum_prefix_observations:
            break
    if len(prefixes) != maximum_prefix_observations:
        raise ValueError("V161 source path ended before registered prefix cap")
    return {
        "schema": "acfqp.paid_path_prefix_trace.v161",
        "family": adapter.family,
        "seed": adapter.seed,
        "prefixes": prefixes,
        "offline_source_observation_labels": len(prefixes),
        "path_first_generator_continuation_retained": True,
        "source_prefix_cap_is_not_target_stopping_floor": True,
        "generation_witness_accessed": False,
        "fresh_v161_target_outcomes_accessed": False,
    }


def feature_trace_v161(document):
    return tuple(
        tuple(tuple(row) for row in prefix["anonymous_raw_delta_feature_rows"])
        for prefix in document["prefixes"]
    )


__all__ = (
    "SOURCE_PREFIX_OBSERVATION_CAP_V161",
    "build_paid_path_prefix_trace_v161",
    "evaluate_progressive_raw_prefix_expression_v160",
    "feature_trace_v161",
    "synthesize_progressive_raw_prefix_classifier_v160",
)
