"""Generic raw-delta feature rows and progressive V160 query classifier."""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp.phase3e_ids import canonical_json_bytes


ANONYMOUS_RAW_DELTA_FEATURE_WIDTH_V160 = 10


def anonymous_raw_delta_feature_rows_v160(observations: Iterable[Any]):
    """Return unnamed integer vectors derived uniformly from raw transition deltas."""

    observations = tuple(observations)
    if not observations or not observations[0]["rows"]:
        raise ValueError("V160 raw-prefix observations are empty")
    state_width = len(observations[0]["rows"][0].pre)
    feature_rows = []
    for coordinate in range(state_width):
        supports = tuple(
            tuple(
                sorted(
                    {
                        row.post[coordinate] - row.pre[coordinate]
                        for row in observation["rows"]
                    }
                )
            )
            for observation in observations
        )
        deterministic = tuple(
            support[0] for support in supports if len(support) == 1
        )
        feature_rows.append(
            (
                len(observations),
                sum(len(support) > 1 for support in supports),
                sum(len(support) == 1 for support in supports),
                len(set(supports)),
                len(set(deterministic)),
                sum(all(delta > 0 for delta in support) for support in supports),
                sum(0 in support for support in supports),
                max(len(support) for support in supports),
                sum(len(support) for support in supports),
                int(
                    any(
                        any(delta != 0 for delta in support)
                        for support in supports
                    )
                ),
            )
        )
    return tuple(feature_rows)


def build_progressive_raw_prefix_trace_v160(adapter: Any):
    """Acquire a witness-blind legal-action prefix and retain only raw evidence."""

    initial = adapter.initial()
    actions = tuple(adapter.actions(initial))
    observations = []
    rows = []
    prefixes = []
    transition_index = 0
    for action in actions:
        key = adapter.action_key(action)
        batch = ground._transition_batch(  # noqa: SLF001
            adapter, initial, key, transition_index
        )
        transition_index += len(batch)
        observations.append({"action_key": key, "rows": batch})
        rows.extend(batch)
        features = anonymous_raw_delta_feature_rows_v160(observations)
        prefixes.append(
            {
                "prefix_observation_count": len(observations),
                "raw_transition_count": len(rows),
                "raw_transition_rows": [row.to_document() for row in rows],
                "raw_transition_sha256": ground._raw_sha(tuple(rows)),  # noqa: SLF001
                "anonymous_raw_delta_feature_rows": [
                    list(feature_row) for feature_row in features
                ],
                "anonymous_raw_delta_feature_width": ANONYMOUS_RAW_DELTA_FEATURE_WIDTH_V160,
            }
        )
    return {
        "schema": "acfqp.progressive_raw_prefix_trace.v160",
        "family": adapter.family,
        "seed": adapter.seed,
        "action_ordering_policy": "ADAPTER_LEGAL_ACTION_ENUMERATION_NO_OUTCOME_WITNESS",
        "prefixes": prefixes,
        "offline_source_observation_labels": len(observations),
        "raw_transition_count": len(rows),
        "full_initial_action_frontier_required_for_decision": False,
        "generation_witness_accessed": False,
        "fresh_v160_target_outcomes_accessed": False,
    }


def _relation_matches(comparator: str, left: int, right: int) -> bool:
    if comparator == "EQUAL":
        return left == right
    if comparator == "NOT_EQUAL":
        return left != right
    raise ValueError("unknown V160 feature relation comparator")


def _literal_matches(comparator: str, value: int, target: int) -> bool:
    if comparator == "EQUAL":
        return value == target
    if comparator == "AT_LEAST":
        return value >= target
    raise ValueError("unknown V160 feature literal comparator")


def evaluate_progressive_raw_prefix_expression_v160(
    expression: Any,
    feature_rows: Sequence[Sequence[int]],
    *,
    prefix_observation_count: int,
):
    if prefix_observation_count < expression["stable_prefix_observation_count"]:
        return "CONTINUE", 0
    left = expression["relation"]["left_feature_slot"]
    right = expression["relation"]["right_feature_slot"]
    literal = expression["literal"]["feature_slot"]
    count = sum(
        _relation_matches(
            expression["relation"]["comparator"], row[left], row[right]
        )
        and _literal_matches(
            expression["literal"]["comparator"],
            row[literal],
            expression["literal"]["value"],
        )
        for row in feature_rows
    )
    decision = (
        "RELATION_COVERAGE"
        if count > expression["count_threshold"]
        else "PATH_FIRST_SAFE_FALLBACK"
    )
    return decision, count


def synthesize_progressive_raw_prefix_classifier_v160(labelled_traces):
    """Select the shortest stable generic relation program by exact MDL."""

    labelled = tuple(labelled_traces)
    if not labelled:
        raise ValueError("V160 labelled traces are empty")
    width = len(labelled[0][0][0])
    if width != ANONYMOUS_RAW_DELTA_FEATURE_WIDTH_V160:
        raise ValueError("V160 anonymous feature width changed")
    maximum_stable_horizon = min(len(trace) for trace, _label in labelled)
    literal_values = tuple(
        sorted(
            {
                value
                for trace, _label in labelled
                for feature_rows in trace
                for row in feature_rows
                for value in row
            }
        )
    )
    maximum_row_count = max(
        len(feature_rows)
        for trace, _label in labelled
        for feature_rows in trace
    )
    candidates = []
    evaluated = 0
    for horizon in range(1, maximum_stable_horizon + 1):
        for relation_rank, relation_comparator in enumerate(
            ("EQUAL", "NOT_EQUAL")
        ):
            for left in range(width):
                for right in range(left + 1, width):
                    for literal_rank, literal_comparator in enumerate(
                        ("EQUAL", "AT_LEAST")
                    ):
                        for literal in range(width):
                            for value in literal_values:
                                counts = []
                                labels = []
                                for trace, label in labelled:
                                    for feature_rows in trace[horizon - 1 :]:
                                        counts.append(
                                            sum(
                                                _relation_matches(
                                                    relation_comparator,
                                                    row[left],
                                                    row[right],
                                                )
                                                and _literal_matches(
                                                    literal_comparator,
                                                    row[literal],
                                                    value,
                                                )
                                                for row in feature_rows
                                            )
                                        )
                                        labels.append(label)
                                for threshold in range(maximum_row_count + 1):
                                    evaluated += 1
                                    if all(
                                        (count > threshold) is label
                                        for count, label in zip(counts, labels)
                                    ):
                                        expression = {
                                            "kind": "COUNT_ANONYMOUS_RAW_DELTA_ROWS_WITH_RELATION_AND_LITERAL_GREATER_THAN",
                                            "stable_prefix_observation_count": horizon,
                                            "relation": {
                                                "left_feature_slot": left,
                                                "comparator": relation_comparator,
                                                "right_feature_slot": right,
                                            },
                                            "literal": {
                                                "feature_slot": literal,
                                                "comparator": literal_comparator,
                                                "value": value,
                                            },
                                            "count_threshold": threshold,
                                        }
                                        mdl = (
                                            horizon.bit_length(),
                                            relation_rank,
                                            literal_rank,
                                            abs(right - left).bit_length(),
                                            value.bit_length(),
                                            threshold.bit_length(),
                                            horizon,
                                            left,
                                            right,
                                            literal,
                                            value,
                                            threshold,
                                        )
                                        candidates.append((mdl, expression))
    if not candidates:
        raise ValueError("V160 generic raw-prefix grammar did not separate labels")
    mdl, expression = min(
        candidates, key=lambda row: (row[0], canonical_json_bytes(row[1]))
    )
    return expression, list(mdl), evaluated, len(candidates)


__all__ = (
    "ANONYMOUS_RAW_DELTA_FEATURE_WIDTH_V160",
    "anonymous_raw_delta_feature_rows_v160",
    "build_progressive_raw_prefix_trace_v160",
    "evaluate_progressive_raw_prefix_expression_v160",
    "synthesize_progressive_raw_prefix_classifier_v160",
)
