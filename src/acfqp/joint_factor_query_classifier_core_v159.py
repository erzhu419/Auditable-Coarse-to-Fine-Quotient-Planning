"""Generic raw-factorization labels and finite V159 query-policy grammar."""

from __future__ import annotations

from typing import Any, Iterable

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp.phase3e_ids import canonical_json_bytes


def anonymous_initial_support_signature_v159(adapter: Any):
    keys = tuple(
        adapter.action_key(action) for action in adapter.actions(adapter.initial())
    )
    return tuple(
        sorted(
            (
                len({adapter.catalogue[key].fields[field] for key in keys}),
                len({action.fields[field] for action in adapter.catalogue}),
            )
            for field in range(len(adapter.catalogue[0].fields))
        )
    )


def factorization_relation_candidates_v159(adapter: Any, observations: Iterable[Any]):
    observations = tuple(observations)
    width = len(adapter.catalogue[0].fields)
    state_width = len(observations[0]["rows"][0].pre)
    candidates = []
    for field in range(width):
        for coordinate in range(state_width):
            relation = {}
            valid = True
            for observation in observations:
                value = adapter.catalogue[observation["action_key"]].fields[field]
                deltas = {
                    row.post[coordinate] - row.pre[coordinate]
                    for row in observation["rows"]
                }
                if (
                    len(deltas) != 1
                    or value in relation
                    and relation[value] != next(iter(deltas))
                ):
                    valid = False
                    break
                relation[value] = next(iter(deltas))
            values = tuple(relation.values())
            catalogue_support = {
                action.fields[field] for action in adapter.catalogue
            }
            if (
                valid
                and len(relation) == len(observations)
                and set(relation) == catalogue_support
                and len(set(values)) == len(values)
                and min(values) > 0
            ):
                document = {
                    "action_field": field,
                    "state_delta_coordinate": coordinate,
                    "relation_rows": [
                        {"action_field_value": key, "state_delta": relation[key]}
                        for key in sorted(relation)
                    ],
                    "catalogue_support_exhausted_by_initial_actions": True,
                    "injective_positive_delta_relation": True,
                }
                rank = (
                    -(max(values) - min(values)),
                    field,
                    coordinate,
                    canonical_json_bytes(document),
                )
                candidates.append((rank, document))
    return tuple(document for _rank, document in sorted(candidates))


def build_initial_factorization_source_observation_v159(adapter: Any):
    initial = adapter.initial()
    observations = []
    rows = []
    transition_index = 0
    for action in adapter.actions(initial):
        key = adapter.action_key(action)
        batch = ground._transition_batch(  # noqa: SLF001
            adapter, initial, key, transition_index
        )
        transition_index += len(batch)
        rows.extend(batch)
        observations.append({"action_key": key, "rows": batch})
    candidates = factorization_relation_candidates_v159(adapter, observations)
    return {
        "schema": "acfqp.initial_factorization_source_observation.v159",
        "family": adapter.family,
        "seed": adapter.seed,
        "anonymous_initial_action_support_signature": [
            list(pair) for pair in anonymous_initial_support_signature_v159(adapter)
        ],
        "raw_initial_transition_rows": [row.to_document() for row in rows],
        "raw_initial_transition_sha256": ground._raw_sha(tuple(rows)),  # noqa: SLF001
        "offline_source_observation_labels": len(observations),
        "raw_transition_count": len(rows),
        "factorization_relation_candidates": list(candidates),
        "factorization_relation_candidate_count": len(candidates),
        "positive_factorization_relation_present": bool(candidates),
        "selected_factorization_relation": candidates[0] if candidates else None,
        "label_derived_from_raw_state_action_successor_differences": True,
        "generation_witness_accessed": False,
        "fresh_v159_target_outcomes_accessed": False,
    }


def evaluate_joint_factor_query_expression_v159(expression, signature):
    def matches(value, comparator, target):
        return value == target if comparator == "EQUAL" else value >= target

    count = sum(
        matches(
            pair[0],
            expression["initial_support_comparator"],
            expression["initial_support_value"],
        )
        and matches(
            pair[1],
            expression["catalogue_support_comparator"],
            expression["catalogue_support_value"],
        )
        for pair in signature
    )
    return count > expression["count_threshold"], count


def synthesize_joint_factor_query_classifier_v159(labelled_signatures):
    labelled = tuple(labelled_signatures)
    candidates = []
    evaluated = 0
    for initial_rank, initial_comparator in enumerate(("EQUAL", "AT_LEAST")):
        for catalogue_rank, catalogue_comparator in enumerate(
            ("EQUAL", "AT_LEAST")
        ):
            for initial_value in range(1, 17):
                for catalogue_value in range(1, 17):
                    for threshold in range(0, 9):
                        expression = {
                            "kind": "COUNT_CONJUNCTIVE_PAIR_PREDICATE_GREATER_THAN",
                            "initial_support_comparator": initial_comparator,
                            "initial_support_value": initial_value,
                            "catalogue_support_comparator": catalogue_comparator,
                            "catalogue_support_value": catalogue_value,
                            "count_threshold": threshold,
                        }
                        evaluated += 1
                        if all(
                            evaluate_joint_factor_query_expression_v159(
                                expression, signature
                            )[0]
                            is label
                            for signature, label in labelled
                        ):
                            mdl = (
                                1,
                                initial_rank,
                                catalogue_rank,
                                initial_value.bit_length(),
                                catalogue_value.bit_length(),
                                threshold.bit_length(),
                                initial_value,
                                catalogue_value,
                                threshold,
                            )
                            candidates.append((mdl, expression))
    if not candidates:
        raise ValueError("V159 typed grammar did not separate factorization labels")
    mdl, expression = min(
        candidates, key=lambda row: (row[0], canonical_json_bytes(row[1]))
    )
    return expression, list(mdl), evaluated, len(candidates)


__all__ = (
    "anonymous_initial_support_signature_v159",
    "build_initial_factorization_source_observation_v159",
    "evaluate_joint_factor_query_expression_v159",
    "factorization_relation_candidates_v159",
    "synthesize_joint_factor_query_classifier_v159",
)
