"""Use a paid-prefix relation witness before any V162 positive switch."""

from __future__ import annotations

from types import FunctionType

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp import anonymous_relational_factor_bank_acquisition_v148 as v148
from acfqp import construction_k7_domain_registry_extension_v162 as domains
from acfqp.construction_k7_paid_path_prefix_classifier_receipt_freeze_v161 import (
    CLASSIFIER_RECEIPT_ID,
    verify_frozen_paid_path_prefix_classifier_receipt_v161,
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


def _contextual_path_first_stream(adapter):
    seen = set()
    transition_index = 0

    def visit(state):
        nonlocal transition_index
        if state in seen:
            return
        seen.add(state)
        for action in adapter.actions(state):
            key = adapter.action_key(action)
            batch = ground._transition_batch(  # noqa: SLF001
                adapter, state, key, transition_index
            )
            transition_index += len(batch)
            successors = tuple(
                outcome.next_state
                for outcome in adapter.kernel.step(state, action)
                if adapter.active(outcome.next_state)
            )
            yield {
                "state": state,
                "action": action,
                "action_key": key,
                "batch": batch,
                "successors": successors,
            }
            for successor in successors:
                yield from visit(successor)

    yield from visit(adapter.initial())


def _paid_prefix_relation_candidates(adapter, contexts):
    width = len(adapter.catalogue[0].fields)
    state_width = len(contexts[0]["batch"][0].pre)
    candidates = []
    for field in range(width):
        support = {action.fields[field] for action in adapter.catalogue}
        for coordinate in range(state_width):
            relation = {}
            valid = True
            for context in contexts:
                value = adapter.catalogue[context["action_key"]].fields[field]
                deltas = {
                    row.post[coordinate] - row.pre[coordinate]
                    for row in context["batch"]
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
            if (
                valid
                and set(relation) == support
                and len(set(values)) == len(values)
                and min(values) > 0
            ):
                document = {
                    "action_field": field,
                    "state_delta_coordinate": coordinate,
                    "relation_rows": [
                        {"action_field_value": value, "state_delta": relation[value]}
                        for value in sorted(relation)
                    ],
                    "paid_path_prefix_exhausted_anonymous_relation_support": True,
                    "injective_positive_delta_relation": True,
                }
                candidates.append(
                    (
                        -(max(values) - min(values)),
                        field,
                        coordinate,
                        ground.canonical_json_bytes(document),
                        document,
                        relation,
                    )
                )
    return tuple(sorted(candidates, key=lambda candidate: candidate[:4]))


def prepare_certified_paid_path_switch_v162(adapter, expression):
    generator = _contextual_path_first_stream(adapter)
    horizon = expression["stable_prefix_observation_count"]
    contexts = []
    observations = []
    rows = []
    decisions = []
    for index in range(1, horizon + 1):
        try:
            context = next(generator)
        except StopIteration as error:
            raise ValueError("V162 path ended before learned horizon") from error
        contexts.append(context)
        observations.append(
            {"action_key": context["action_key"], "rows": context["batch"]}
        )
        rows.extend(context["batch"])
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
    classifier_decision = decisions[-1]["decision"]
    candidates = _paid_prefix_relation_candidates(adapter, contexts)
    certified_switch = classifier_decision == "RELATION_COVERAGE" and bool(candidates)
    return {
        "path_generator": generator,
        "contexts": tuple(contexts),
        "prefix_rows": tuple(rows),
        "decision_trace": decisions,
        "classifier_decision": classifier_decision,
        "relation_candidates": candidates,
        "certified_positive_switch": certified_switch,
        "query_policy_decision": (
            "CERTIFIED_RELATION_COVERAGE"
            if certified_switch
            else "EXACT_PATH_FIRST_SAFE_FALLBACK"
        ),
    }


def certified_paid_path_switch_stream_v162(adapter, prepared):
    for context in prepared["contexts"]:
        yield context["batch"]
    if not prepared["certified_positive_switch"]:
        for context in prepared["path_generator"]:
            yield context["batch"]
        return
    _span, field, _coordinate, _encoded, _document, relation = prepared[
        "relation_candidates"
    ][0]
    transition_index = len(prepared["prefix_rows"])
    queried = {
        (context["state"], context["action_key"])
        for context in prepared["contexts"]
    }
    best = max(
        prepared["contexts"],
        key=lambda context: (
            relation[adapter.catalogue[context["action_key"]].fields[field]],
            -context["action_key"],
        ),
    )
    active = best["successors"]
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
        if (current, key) not in queried:
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

    yield from visit(adapter.initial())


def acquire_matched_certified_paid_path_switch_arms_v162(
    adapter, bank_raw, verification_raw, classifier_receipt_raw, config
):
    classifier = verify_frozen_paid_path_prefix_classifier_receipt_v161(
        classifier_receipt_raw
    )
    prepared = prepare_certified_paid_path_switch_v162(
        adapter, classifier["selected_expression"]
    )
    run_globals = dict(v148.__dict__)

    def stream(_current_adapter):
        yield from certified_paid_path_switch_stream_v162(_current_adapter, prepared)

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
            "schema": "acfqp.certified_paid_path_switch_acquisition_arm.v162",
            "source_v148_acquisition_id": source["acquisition_id"],
            "paid_path_prefix_classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
            "selected_classifier_expression": classifier["selected_expression"],
            "classifier_decision_trace": prepared["decision_trace"],
            "classifier_decision": prepared["classifier_decision"],
            "query_policy_decision": prepared["query_policy_decision"],
            "paid_prefix_relation_candidates": [
                candidate[4] for candidate in prepared["relation_candidates"]
            ],
            "paid_prefix_relation_candidate_count": len(
                prepared["relation_candidates"]
            ),
            "certified_positive_switch": prepared["certified_positive_switch"],
            "unwitnessed_positive_classifier_decision_falls_back_exactly": prepared[
                "classifier_decision"
            ]
            == "RELATION_COVERAGE"
            and not prepared["certified_positive_switch"],
            "classifier_prefix_observation_labels": len(prepared["contexts"]),
            "classifier_prefix_labels_are_included_in_ground_support_labels": True,
            "additional_classifier_only_target_labels": 0,
            "classifier_prefix_raw_transition_count": len(prepared["prefix_rows"]),
            "classifier_prefix_raw_transition_sha256": ground._raw_sha(  # noqa: SLF001
                prepared["prefix_rows"]
            ),
            "fallback_resumed_same_path_first_generator_object": not prepared[
                "certified_positive_switch"
            ],
            "positive_only_switch_to_relation_coverage": prepared[
                "certified_positive_switch"
            ],
            "no_named_initial_or_catalogue_support_primitive": True,
            "full_initial_action_frontier_required_for_decision": False,
            "exact_signature_registry_consulted": False,
            "classifier_accessed_only_its_paid_target_raw_prefix": True,
            "classifier_changes_query_order_not_hypothesis_pool_or_stop_rule": True,
            "classifier_is_model_planning_or_certificate_authority": False,
            "v160_and_v161_failures_preserved_not_reclassified": True,
        }
        wrapped[name] = {
            **arm,
            "document": {
                **payload,
                "acquisition_id": domains.extension_content_id_v162(
                    domains.CONSTRUCTION_K7_ACQUISITION_V162_DOMAIN, payload
                ),
            },
        }
    return wrapped


__all__ = (
    "acquire_matched_certified_paid_path_switch_arms_v162",
    "certified_paid_path_switch_stream_v162",
    "prepare_certified_paid_path_switch_v162",
)
