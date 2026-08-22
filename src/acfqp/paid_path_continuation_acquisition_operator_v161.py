"""V161 exact fallback continuation with positive-only query-policy switching."""

from __future__ import annotations

from types import FunctionType

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp import anonymous_relational_factor_bank_acquisition_v148 as v148
from acfqp import construction_k7_domain_registry_extension_v161 as domains
from acfqp.construction_k7_paid_path_prefix_classifier_receipt_freeze_v161 import (
    CLASSIFIER_RECEIPT_ID,
    verify_frozen_paid_path_prefix_classifier_receipt_v161,
)
from acfqp.fair_unified_factor_prior_ablation_acquisition_v129r1 import (
    fair_witness_blind_path_first_stream_v129r1,
)
from acfqp.progressive_raw_prefix_acquisition_operator_v160 import (
    _relation_from_observations,
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


def prepare_paid_path_prefix_query_v161(adapter, expression):
    generator = fair_witness_blind_path_first_stream_v129r1(adapter)
    horizon = expression["stable_prefix_observation_count"]
    observations = []
    batches = []
    rows = []
    decisions = []
    for index in range(1, horizon + 1):
        try:
            batch = next(generator)
        except StopIteration as error:
            raise ValueError("V161 path ended before learned horizon") from error
        observations.append({"action_key": batch[0].action.key, "rows": batch})
        batches.append(batch)
        rows.extend(batch)
        features = anonymous_raw_delta_feature_rows_v160(observations)
        decision, count = evaluate_progressive_raw_prefix_expression_v160(
            expression, features, prefix_observation_count=index
        )
        decisions.append(
            {
                "prefix_observation_count": index,
                "anonymous_raw_delta_feature_rows": [list(row) for row in features],
                "decision": decision,
                "selected_predicate_match_count": count,
            }
        )
    decision = decisions[-1]["decision"]
    if decision == "CONTINUE":
        raise ValueError("V161 learned horizon emitted no terminal query decision")
    return {
        "path_generator": generator,
        "prefix_batches": tuple(batches),
        "prefix_rows": tuple(rows),
        "decision_trace": decisions,
        "query_policy_decision": decision,
    }


def paid_path_continuation_stream_v161(adapter, prepared):
    for batch in prepared["prefix_batches"]:
        yield batch
    if prepared["query_policy_decision"] == "PATH_FIRST_SAFE_FALLBACK":
        yield from prepared["path_generator"]
        return

    initial = adapter.initial()
    initial_encoded = adapter.encode(initial)
    transition_index = len(prepared["prefix_rows"])
    queried = {
        (batch[0].pre, batch[0].action.key) for batch in prepared["prefix_batches"]
    }
    initial_actions = {
        adapter.action_key(action): action for action in adapter.actions(initial)
    }
    observations = []
    for batch in prepared["prefix_batches"]:
        key = batch[0].action.key
        if batch[0].pre == initial_encoded and key in initial_actions:
            observations.append(
                {
                    "action_key": key,
                    "rows": batch,
                    "successors": tuple(
                        outcome.next_state
                        for outcome in adapter.kernel.step(
                            initial, initial_actions[key]
                        )
                    ),
                }
            )
    observed_initial_keys = {row["action_key"] for row in observations}
    for key, action in initial_actions.items():
        if key in observed_initial_keys:
            continue
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
        queried.add((initial_encoded, key))
        yield batch
    field, _coordinate, relation = _relation_from_observations(
        adapter, observations
    )
    best = max(
        observations,
        key=lambda item: (
            relation[adapter.catalogue[item["action_key"]].fields[field]],
            -item["action_key"],
        ),
    )
    active = tuple(state for state in best["successors"] if adapter.active(state))
    current = min(active, key=adapter.encode) if active else None
    while current is not None and adapter.active(current):
        actions = tuple(adapter.actions(current))
        known = tuple(
            action
            for action in actions
            if adapter.catalogue[adapter.action_key(action)].fields[field] in relation
        )
        if not known:
            break
        action = max(
            known,
            key=lambda row: (
                relation[adapter.catalogue[adapter.action_key(row)].fields[field]],
                -adapter.action_key(row),
            ),
        )
        key = adapter.action_key(action)
        encoded = adapter.encode(current)
        if (encoded, key) not in queried:
            batch = ground._transition_batch(  # noqa: SLF001
                adapter, current, key, transition_index
            )
            transition_index += len(batch)
            queried.add((encoded, key))
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
        encoded = adapter.encode(state)
        for action in adapter.actions(state):
            key = adapter.action_key(action)
            if (encoded, key) not in queried:
                batch = ground._transition_batch(  # noqa: SLF001
                    adapter, state, key, transition_index
                )
                transition_index += len(batch)
                queried.add((encoded, key))
                yield batch
            for outcome in adapter.kernel.step(state, action):
                if adapter.active(outcome.next_state):
                    yield from visit(outcome.next_state)

    yield from visit(initial)


def acquire_matched_paid_path_continuation_arms_v161(
    adapter, bank_raw, verification_raw, classifier_receipt_raw, config
):
    classifier = verify_frozen_paid_path_prefix_classifier_receipt_v161(
        classifier_receipt_raw
    )
    expression = classifier["selected_expression"]
    prepared = prepare_paid_path_prefix_query_v161(adapter, expression)
    run_globals = dict(v148.__dict__)

    def stream(_current_adapter):
        yield from paid_path_continuation_stream_v161(_current_adapter, prepared)

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
            "schema": "acfqp.paid_path_continuation_acquisition_arm.v161",
            "source_v148_acquisition_id": source["acquisition_id"],
            "paid_path_prefix_classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
            "selected_classifier_expression": expression,
            "classifier_decision_trace": prepared["decision_trace"],
            "query_policy_decision": prepared["query_policy_decision"],
            "classifier_path_prefix_labels": len(prepared["prefix_batches"]),
            "classifier_prefix_labels_are_exact_path_first_acquisition_labels": True,
            "additional_classifier_only_target_labels": 0,
            "classifier_prefix_raw_transition_count": len(prepared["prefix_rows"]),
            "classifier_prefix_raw_transition_sha256": ground._raw_sha(  # noqa: SLF001
                prepared["prefix_rows"]
            ),
            "fallback_resumed_same_path_first_generator_object": prepared[
                "query_policy_decision"
            ]
            == "PATH_FIRST_SAFE_FALLBACK",
            "positive_only_switch_to_relation_coverage": prepared[
                "query_policy_decision"
            ]
            == "RELATION_COVERAGE",
            "exact_signature_registry_consulted": False,
            "classifier_accessed_only_its_paid_target_raw_prefix": True,
            "classifier_changes_query_order_not_hypothesis_pool_or_stop_rule": True,
            "classifier_is_model_planning_or_certificate_authority": False,
            "v160_failure_preserved_not_reclassified": True,
        }
        wrapped[name] = {
            **arm,
            "document": {
                **payload,
                "acquisition_id": domains.extension_content_id_v161(
                    domains.CONSTRUCTION_K7_ACQUISITION_V161_DOMAIN, payload
                ),
            },
        }
    return wrapped


__all__ = (
    "acquire_matched_paid_path_continuation_arms_v161",
    "paid_path_continuation_stream_v161",
    "prepare_paid_path_prefix_query_v161",
)
