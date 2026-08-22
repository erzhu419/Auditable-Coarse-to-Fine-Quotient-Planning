"""Apply the V160 raw-prefix classifier as a query-order meta-prior."""

from __future__ import annotations

from types import FunctionType

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp import anonymous_relational_factor_bank_acquisition_v148 as v148
from acfqp import construction_k7_domain_registry_extension_v160 as domains
from acfqp.construction_k7_progressive_raw_prefix_classifier_receipt_freeze_v160 import (
    CLASSIFIER_RECEIPT_ID,
    verify_frozen_progressive_raw_prefix_classifier_receipt_v160,
)
from acfqp.progressive_raw_prefix_query_classifier_core_v160 import (
    anonymous_raw_delta_feature_rows_v160,
    evaluate_progressive_raw_prefix_expression_v160,
)


def _clone(function, namespace):
    clone = FunctionType(
        function.__code__,
        namespace,
        name=function.__name__,
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def prepare_progressive_raw_prefix_query_v160(adapter, expression):
    initial = adapter.initial()
    actions = tuple(adapter.actions(initial))
    horizon = expression["stable_prefix_observation_count"]
    if len(actions) < horizon:
        raise ValueError("V160 target exposes fewer actions than the learned horizon")
    transition_index = 0
    observations = []
    batches = []
    rows = []
    decisions = []
    for action in actions[:horizon]:
        key = adapter.action_key(action)
        batch = ground._transition_batch(  # noqa: SLF001
            adapter, initial, key, transition_index
        )
        transition_index += len(batch)
        observations.append(
            {
                "action_key": key,
                "rows": batch,
                "successors": tuple(
                    outcome.next_state
                    for outcome in adapter.kernel.step(initial, action)
                ),
            }
        )
        batches.append(batch)
        rows.extend(batch)
        feature_rows = anonymous_raw_delta_feature_rows_v160(observations)
        decision, count = evaluate_progressive_raw_prefix_expression_v160(
            expression,
            feature_rows,
            prefix_observation_count=len(observations),
        )
        decisions.append(
            {
                "prefix_observation_count": len(observations),
                "anonymous_raw_delta_feature_rows": [
                    list(row) for row in feature_rows
                ],
                "decision": decision,
                "selected_predicate_match_count": count,
            }
        )
    decision = decisions[-1]["decision"]
    if decision == "CONTINUE":
        raise ValueError("V160 learned horizon did not emit a terminal query decision")
    return {
        "initial_state": initial,
        "initial_actions": actions,
        "observations": observations,
        "prefix_batches": tuple(batches),
        "prefix_rows": tuple(rows),
        "next_transition_index": transition_index,
        "decision_trace": decisions,
        "query_policy_decision": decision,
    }


def _relation_from_observations(adapter, observations):
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
                candidates.append(
                    (
                        -(max(values) - min(values)),
                        field,
                        coordinate,
                        relation,
                    )
                )
    if not candidates:
        raise ValueError("V160 positive query decision exposed no relation")
    _span, field, coordinate, relation = min(candidates)
    return field, coordinate, relation


def progressive_raw_prefix_stream_v160(adapter, prepared):
    initial = prepared["initial_state"]
    transition_index = prepared["next_transition_index"]
    observations = list(prepared["observations"])
    queried = {
        (initial, observation["action_key"]) for observation in observations
    }
    for batch in prepared["prefix_batches"]:
        yield batch

    if prepared["query_policy_decision"] == "RELATION_COVERAGE":
        for action in prepared["initial_actions"][len(observations) :]:
            key = adapter.action_key(action)
            batch = ground._transition_batch(  # noqa: SLF001
                adapter, initial, key, transition_index
            )
            transition_index += len(batch)
            observations.append(
                {
                    "action_key": key,
                    "rows": batch,
                    "successors": tuple(
                        outcome.next_state
                        for outcome in adapter.kernel.step(initial, action)
                    ),
                }
            )
            queried.add((initial, key))
            yield batch
        field, _coordinate, relation = _relation_from_observations(
            adapter, observations
        )
        best = max(
            observations,
            key=lambda item: (
                relation[
                    adapter.catalogue[item["action_key"]].fields[field]
                ],
                -item["action_key"],
            ),
        )
        active = tuple(
            state for state in best["successors"] if adapter.active(state)
        )
        current = min(active, key=adapter.encode) if active else None
        while current is not None and adapter.active(current):
            actions = tuple(adapter.actions(current))
            known = tuple(
                action
                for action in actions
                if adapter.catalogue[adapter.action_key(action)].fields[field]
                in relation
            )
            if not known:
                break
            action = max(
                known,
                key=lambda row: (
                    relation[
                        adapter.catalogue[adapter.action_key(row)].fields[field]
                    ],
                    -adapter.action_key(row),
                ),
            )
            key = adapter.action_key(action)
            batch = ground._transition_batch(  # noqa: SLF001
                adapter, current, key, transition_index
            )
            transition_index += len(batch)
            queried.add((current, key))
            yield batch
            active = tuple(
                outcome.next_state
                for outcome in adapter.kernel.step(current, action)
                if adapter.active(outcome.next_state)
            )
            current = min(active, key=adapter.encode) if active else None

    seen = set()

    def visit(state):
        nonlocal transition_index
        if state in seen:
            return
        seen.add(state)
        for action in adapter.actions(state):
            key = adapter.action_key(action)
            if (state, key) not in queried:
                batch = ground._transition_batch(  # noqa: SLF001
                    adapter, state, key, transition_index
                )
                transition_index += len(batch)
                queried.add((state, key))
                yield batch
            for outcome in adapter.kernel.step(state, action):
                if adapter.active(outcome.next_state):
                    yield from visit(outcome.next_state)

    yield from visit(initial)


def acquire_matched_progressive_raw_prefix_arms_v160(
    adapter, bank_raw, verification_raw, classifier_receipt_raw, config
):
    classifier = verify_frozen_progressive_raw_prefix_classifier_receipt_v160(
        classifier_receipt_raw
    )
    expression = classifier["selected_expression"]
    prepared = prepare_progressive_raw_prefix_query_v160(adapter, expression)
    run_globals = dict(v148.__dict__)

    def stream(_current_adapter):
        yield from progressive_raw_prefix_stream_v160(_current_adapter, prepared)

    run_globals["fair_witness_blind_path_first_stream_v129r1"] = stream
    run = _clone(
        v148.acquire_matched_anonymous_relational_factor_bank_arms_v148,
        run_globals,
    )
    arms = run(adapter, bank_raw, verification_raw, config)
    wrapped = {}
    for name, arm in arms.items():
        source = arm["document"]
        payload = {
            **{
                key: value
                for key, value in source.items()
                if key not in {"schema", "acquisition_id"}
            },
            "schema": "acfqp.progressive_raw_prefix_acquisition_arm.v160",
            "source_v148_acquisition_id": source["acquisition_id"],
            "progressive_raw_prefix_classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
            "selected_classifier_expression": expression,
            "classifier_decision_trace": prepared["decision_trace"],
            "query_policy_decision": prepared["query_policy_decision"],
            "classifier_prefix_observation_labels": len(
                prepared["prefix_batches"]
            ),
            "classifier_prefix_labels_are_included_in_ground_support_labels": True,
            "classifier_prefix_raw_transition_count": len(prepared["prefix_rows"]),
            "classifier_prefix_raw_transition_sha256": ground._raw_sha(  # noqa: SLF001
                prepared["prefix_rows"]
            ),
            "no_named_initial_or_catalogue_support_primitive": True,
            "full_initial_action_frontier_required_for_decision": False,
            "exact_signature_registry_consulted": False,
            "classifier_accessed_only_its_paid_target_raw_prefix": True,
            "classifier_changes_query_order_not_hypothesis_pool_or_stop_rule": True,
            "classifier_is_model_planning_or_certificate_authority": False,
        }
        wrapped[name] = {
            **arm,
            "document": {
                **payload,
                "acquisition_id": domains.extension_content_id_v160(
                    domains.CONSTRUCTION_K7_ACQUISITION_V160_DOMAIN, payload
                ),
            },
        }
    return wrapped


__all__ = (
    "acquire_matched_progressive_raw_prefix_arms_v160",
    "prepare_progressive_raw_prefix_query_v160",
    "progressive_raw_prefix_stream_v160",
)
