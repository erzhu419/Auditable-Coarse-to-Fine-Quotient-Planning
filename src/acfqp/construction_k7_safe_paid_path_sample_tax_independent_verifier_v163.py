"""Producer-free reconstruction of the frozen V163 campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp import construction_k7_domain_registry_extension_v162 as domains_v162
from acfqp import construction_k7_domain_registry_extension_v163 as domains
from acfqp import construction_k7_plan_mode_margin_independent_verifier_v157 as v157
from acfqp import construction_k7_relation_keyed_bank_independent_verifier_v151 as v151
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.anonymous_relational_factor_bank_acquisition_v148 import (
    acquire_matched_anonymous_relational_factor_bank_arms_v148,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY as MODULAR_FAMILY,
    build_modular_routing_adapter_v128,
    modular_routing_config_v128,
)
from acfqp.generic_novel_signature_adapters_v158 import (
    FALLBACK_FAMILY,
    POSITIVE_FAMILY,
    build_novel_fallback_signature_adapter_v158,
    build_novel_positive_signature_adapter_v158,
)
from acfqp.novel_signature_campaign_core_v158 import (
    novel_signature_campaign_config_v158,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.progressive_raw_prefix_query_classifier_core_v160 import (
    anonymous_raw_delta_feature_rows_v160,
    evaluate_progressive_raw_prefix_expression_v160,
)


CAMPAIGN_ID = "193323db43d5524e5bebe3a1713e946ab7dbb77cf79307c957a13cded0d9c219"
CAMPAIGN_BYTE_COUNT = 31_528_790
CAMPAIGN_SHA256 = "9dab876ef04bd5b48698fdb9295aaf6efe1f6e3a51bd945fe84e449367aaa433"
PREREGISTRATION_ID = (
    "214233cd0d3af6c319fc872a03813890e1920d4e6e3049158c25caf2454ce9fe"
)
PREREGISTRATION_BYTE_COUNT = 389_728
PREREGISTRATION_SHA256 = (
    "0f328858df6f19a90cd15ec3c1ab95744e99112d505a8b9f97ccfab64ffd2d56"
)
CLASSIFIER_RECEIPT_ID = (
    "893a5b0597fe2c9d0544defcf3655ce6e186950e7c1342a7a7502de0d4f1378d"
)
CLASSIFIER_BYTE_COUNT = 383_778
CLASSIFIER_SHA256 = (
    "ac6ae1dfe458cd4d818f4acb3c9ba77f829787ee1f57c8fdcd8e379c118267df"
)
V162_FAILED_CAMPAIGN_ID = (
    "84250a94f22de611e57987c88bedbf5d44cc2bfa8f92cdec942ef625daa6b69a"
)
V162_FAILURE_BYTE_COUNT = 2_561
V162_FAILURE_SHA256 = (
    "3f69c16b089ce2bb95a458b1e046dd19c3d262b953397bd79d8579e1f9f96c7a"
)
V160_FAILED_CAMPAIGN_ID = (
    "38cbf013db9ceb15605807f5aa83564f7b89fc559d793dcfd7a049d7095771c6"
)
V160_FAILURE_SHA256 = (
    "1d554b56462031920d3573ed1969997eedd8955426bfd024f8355bfab362d3ab"
)
V161_FAILED_PREREGISTRATION_ID = (
    "84bfbf8e9be7de54d0ac95516e5adf18cd5cf7ea08ddb8c22881795c234ee13e"
)
V161_FAILURE_SHA256 = (
    "2a6658caac00c9c4257311e6a1bcc9667afadc13339d36aff4d84d6ea7293cab"
)
EXPECTED_OCCURRENCES = (
    *((POSITIVE_FAMILY, seed) for seed in range(1_048_501, 1_048_505)),
    *((FALLBACK_FAMILY, seed) for seed in range(1_048_511, 1_048_513)),
    *((MODULAR_FAMILY, seed) for seed in range(1_048_521, 1_048_523)),
)
EXPECTED_EPISODES = (901, 902, 903, 904)
VERIFICATION_ID = (
    "5e856f8cab34726906f3e93924ea099d2027ee39aca0708efc5ebabec437975b"
)
EXPECTED_CANONICAL_BYTE_COUNT = 28_544
EXPECTED_CANONICAL_SHA256 = (
    "bd98840ef1a21d3897195e86093b0ed727acbb606dc544cd10df343d7dda002f"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
_BUILDERS = {
    POSITIVE_FAMILY: build_novel_positive_signature_adapter_v158,
    FALLBACK_FAMILY: build_novel_fallback_signature_adapter_v158,
    MODULAR_FAMILY: build_modular_routing_adapter_v128,
}
_ACQUISITION_ADDITIONS = {
    "source_v148_acquisition_id",
    "paid_path_prefix_classifier_receipt_id",
    "selected_classifier_expression",
    "classifier_decision_trace",
    "classifier_decision",
    "query_policy_decision",
    "paid_prefix_relation_candidates",
    "paid_prefix_relation_candidate_count",
    "certified_positive_switch",
    "unwitnessed_positive_classifier_decision_falls_back_exactly",
    "classifier_prefix_observation_labels",
    "classifier_prefix_labels_are_included_in_ground_support_labels",
    "additional_classifier_only_target_labels",
    "classifier_prefix_raw_transition_count",
    "classifier_prefix_raw_transition_sha256",
    "fallback_resumed_same_path_first_generator_object",
    "positive_only_switch_to_relation_coverage",
    "no_named_initial_or_catalogue_support_primitive",
    "full_initial_action_frontier_required_for_decision",
    "exact_signature_registry_consulted",
    "classifier_accessed_only_its_paid_target_raw_prefix",
    "classifier_changes_query_order_not_hypothesis_pool_or_stop_rule",
    "classifier_is_model_planning_or_certificate_authority",
    "v160_and_v161_failures_preserved_not_reclassified",
}


class ConstructionK7SafePaidPathSampleTaxIndependentVerifierV163Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SafePaidPathSampleTaxIndependentVerifierV163Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    _require(
        document.get(key)
        == _content_id(
            domain, {name: value for name, value in document.items() if name != key}
        ),
        f"V163 {key} changed",
    )


def _frozen(raw, document, *, count, digest, key, identity, label):
    _require(
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(key) == identity,
        f"V163 frozen {label} changed",
    )


def _config():
    config = novel_signature_campaign_config_v158()
    modular = modular_routing_config_v128()
    config["families"][MODULAR_FAMILY] = copy.deepcopy(
        modular["families"][MODULAR_FAMILY]
    )
    config["families"][POSITIVE_FAMILY]["maximum_acquisition_labels"] = 1_536
    config["families"][FALLBACK_FAMILY]["maximum_acquisition_labels"] = 1_536
    config["families"][MODULAR_FAMILY]["maximum_acquisition_labels"] = 2_048
    return config


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


def _relation_candidates(adapter, contexts):
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
                if len(deltas) != 1 or (
                    value in relation and relation[value] != next(iter(deltas))
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
                        {
                            "action_field_value": value,
                            "state_delta": relation[value],
                        }
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
                        canonical_json_bytes(document),
                        document,
                        relation,
                    )
                )
    return tuple(sorted(candidates, key=lambda candidate: candidate[:4]))


def _prepare(adapter, expression):
    generator = _contextual_path_first_stream(adapter)
    contexts = []
    observations = []
    rows = []
    decisions = []
    for index in range(1, expression["stable_prefix_observation_count"] + 1):
        context = next(generator)
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
    candidates = _relation_candidates(adapter, contexts)
    certified = classifier_decision == "RELATION_COVERAGE" and bool(candidates)
    return {
        "path_generator": generator,
        "contexts": tuple(contexts),
        "prefix_rows": tuple(rows),
        "decision_trace": decisions,
        "classifier_decision": classifier_decision,
        "relation_candidates": candidates,
        "certified_positive_switch": certified,
        "query_policy_decision": (
            "RELATION_COVERAGE" if certified else "PATH_FIRST_SAFE_FALLBACK"
        ),
    }


def _query_stream(adapter, prepared):
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


def _normalized_acquisition(recorded, prepared, classifier):
    _verify_id(
        recorded,
        "acquisition_id",
        domains_v162.CONSTRUCTION_K7_ACQUISITION_V162_DOMAIN,
    )
    expected = {
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
        "unwitnessed_positive_classifier_decision_falls_back_exactly": (
            prepared["classifier_decision"] == "RELATION_COVERAGE"
            and not prepared["certified_positive_switch"]
        ),
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
    _require(
        recorded.get("schema")
        == "acfqp.certified_paid_path_switch_acquisition_arm.v162"
        and all(recorded.get(key) == value for key, value in expected.items())
        and type(recorded.get("source_v148_acquisition_id")) is str
        and len(recorded["source_v148_acquisition_id"]) == 64,
        "V163 independently reconstructed query wrapper changed",
    )
    normalized = {
        key: copy.deepcopy(value)
        for key, value in recorded.items()
        if key not in _ACQUISITION_ADDITIONS and key != "acquisition_id"
    }
    normalized["schema"] = "acfqp.anonymous_relational_factor_bank_acquisition_arm.v148"
    normalized["acquisition_id"] = recorded["source_v148_acquisition_id"]
    return normalized


def _sequence_verifier(family):
    globals_v150 = dict(v157.__dict__)
    globals_v150.update(
        EXPECTED_EPISODES=EXPECTED_EPISODES,
        _fail=_fail,
        _require=_require,
    )
    factory = FunctionType(
        v157._v150_sequence_verifier.__code__,  # noqa: SLF001
        globals_v150,
        name=v157._v150_sequence_verifier.__name__,  # noqa: SLF001
    )
    return factory(family)


def _verify_sequence(sequence, candidate, rows, *, family, seed):
    globals_v157 = dict(v157.__dict__)
    globals_v157.update(
        _v150_sequence_verifier=_sequence_verifier,
        _fail=_fail,
        _require=_require,
    )
    verifier = FunctionType(
        v157._verify_sequence.__code__,  # noqa: SLF001
        globals_v157,
        name=v157._verify_sequence.__name__,  # noqa: SLF001
    )
    return verifier(sequence, candidate, rows, family=family, seed=seed)


def _verify_occurrence(args):
    row, bank, bank_raw, bank_verification_raw, classifier = args
    family, seed = row["target_family"], row["seed"]
    _require(
        (family, seed) in EXPECTED_OCCURRENCES
        and row.get("schema") == "acfqp.safe_paid_path_sample_tax_occurrence.v163"
        and tuple(row.get("episode_indices", ())) == EXPECTED_EPISODES,
        "V163 occurrence identity changed",
    )
    _verify_id(row, "occurrence_id", domains.CONSTRUCTION_K7_OCCURRENCE_V163_DOMAIN)
    config = _config()
    adapter = _BUILDERS[family](seed, config)
    prepared = _prepare(adapter, classifier["selected_expression"])
    prior_doc = row["progressive_prior_acquisition"]
    strict_doc = row["progressive_strict_acquisition"]
    maximum = max(
        prior_doc["ground_support_labels"], strict_doc["ground_support_labels"]
    )
    stream = _query_stream(adapter, prepared)
    batches = tuple(next(stream) for _ in range(maximum))
    prior_candidate, prior_rows = v151.previous.base._rebuild_acquisition(  # noqa: SLF001
        _normalized_acquisition(prior_doc, prepared, classifier),
        adapter,
        bank,
        batches,
        enabled=True,
        config=config,
    )
    strict_candidate, strict_rows = v151.previous.base._rebuild_acquisition(  # noqa: SLF001
        _normalized_acquisition(strict_doc, prepared, classifier),
        adapter,
        bank,
        batches,
        enabled=False,
        config=config,
    )
    prior_sequence, prior_mode = _verify_sequence(
        row["progressive_prior_sequence"],
        prior_candidate,
        prior_rows,
        family=family,
        seed=seed,
    )
    strict_sequence, strict_mode = _verify_sequence(
        row["progressive_strict_sequence"],
        strict_candidate,
        strict_rows,
        family=family,
        seed=seed,
    )
    _require(prior_mode == strict_mode, "V163 plan modes disagreed")
    legacy = acquire_matched_anonymous_relational_factor_bank_arms_v148(
        adapter, bank_raw, bank_verification_raw, config
    )["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"]
    legacy_summary = {
        key: legacy[key]
        for key in (
            "acquisition_id",
            "ground_support_labels",
            "raw_transition_sha256",
            "first_accepting_observation_label",
        )
    }
    guard_reduction = (
        legacy["ground_support_labels"] - prior_doc["ground_support_labels"]
    )
    factor_reduction = (
        strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    )
    accounting = {
        "progressive_prior_acquisition_labels": prior_doc["ground_support_labels"],
        "progressive_strict_acquisition_labels": strict_doc["ground_support_labels"],
        "legacy_path_first_prior_acquisition_labels": legacy[
            "ground_support_labels"
        ],
        "classifier_prefix_labels_included_in_acquisition": prior_doc[
            "classifier_prefix_observation_labels"
        ],
        "additional_classifier_only_target_labels": 0,
        "labels_avoided_by_progressive_query_policy_vs_legacy_path_first": guard_reduction,
        "labels_avoided_by_factor_prior_within_progressive_policy": factor_reduction,
        "progressive_prior_certificate_local_labels": prior_sequence[
            "certificate_local_labels"
        ],
        "progressive_strict_certificate_local_labels": strict_sequence[
            "certificate_local_labels"
        ],
        "progressive_prior_execution_steps": prior_sequence["execution_steps"],
        "progressive_strict_execution_steps": strict_sequence["execution_steps"],
        "progressive_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "progressive_strict_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "classifier_derivation_compute_events": classifier[
            "classifier_derivation_compute_events"
        ],
        "progressive_prior_planning_compute_events": prior_sequence[
            "planning_compute_events"
        ],
        "progressive_strict_planning_compute_events": strict_sequence[
            "planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    certified = prepared["certified_positive_switch"]
    fallback = not certified
    exact_fallback = (
        prior_doc["source_v148_acquisition_id"] == legacy["acquisition_id"]
        and prior_doc["ground_support_labels"] == legacy["ground_support_labels"]
        and prior_doc["raw_transition_sha256"] == legacy["raw_transition_sha256"]
    )
    source_sequences = (
        row["progressive_prior_sequence"],
        row["progressive_strict_sequence"],
    )
    plan_modes = {prior_mode, strict_mode}
    gate = {
        "fresh_target_identity": True,
        "classifier_receipt_frozen_before_target_outcomes": classifier[
            "fresh_v161_target_outcomes_accessed"
        ]
        is False,
        "no_named_initial_or_catalogue_support_primitive": all(
            document["no_named_initial_or_catalogue_support_primitive"] is True
            for document in (prior_doc, strict_doc)
        ),
        "decision_before_full_initial_action_frontier": all(
            document["full_initial_action_frontier_required_for_decision"] is False
            for document in (prior_doc, strict_doc)
        ),
        "classifier_uses_only_paid_target_raw_prefix": all(
            document["classifier_accessed_only_its_paid_target_raw_prefix"] is True
            and document[
                "classifier_prefix_labels_are_included_in_ground_support_labels"
            ]
            is True
            for document in (prior_doc, strict_doc)
        ),
        "query_policy_noninferior_to_legacy_path_first": guard_reduction >= 0,
        "exact_fallback_has_zero_regression": (
            guard_reduction == 0 and exact_fallback if fallback else True
        ),
        "factor_prior_noninferior_within_same_progressive_policy": factor_reduction
        >= 0,
        "matched_acquisition_completed_within_cap": all(
            0
            < document["ground_support_labels"]
            <= config["families"][family]["maximum_acquisition_labels"]
            for document in (prior_doc, strict_doc)
        ),
        "both_arms_use_same_synthesizer_and_stop_rule": all(
            prior_doc[key] is True and strict_doc[key] is True
            for key in (
                "same_generic_atomic_hypothesis_pool",
                "same_candidate_carrier_and_schema",
                "same_candidate_replay_function",
                "same_stopping_rule_function",
            )
        ),
        "both_arm_receding_episodes_succeed": all(
            episode["success"]
            for sequence in source_sequences
            for episode in sequence["episodes"]
        ),
        "planner_consumes_compiled_model_without_raw_rows": all(
            sequence[
                "planner_consumed_compiled_successor_without_raw_transition_argument"
            ]
            for sequence in source_sequences
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            sequence["every_new_ground_query_followed_a_failed_certificate"]
            for sequence in source_sequences
        ),
        "query_local_overlay_not_promoted_to_global_dynamics": all(
            sequence["source_partial_program_mutated_after_certificate_failure"]
            is False
            and sequence["overlay_promoted_to_global_dynamics"] is False
            and sequence["query_local_overlay_used_as_safety_authority"] is False
            for sequence in source_sequences
        ),
        "applicable_plan_receipt_mode_agrees_between_arms": len(plan_modes) == 1,
        "all_executed_actions_have_v109_receipts": all(
            sequence["all_executed_actions_have_v109_receipts"]
            for sequence in source_sequences
        ),
        "exact_signature_registry_not_consulted": all(
            document["exact_signature_registry_consulted"] is False
            for document in (prior_doc, strict_doc)
        ),
        "raw_prefix_query_decision_matches_witnessed_state": (
            prior_doc["query_policy_decision"]
            == strict_doc["query_policy_decision"]
            == ("RELATION_COVERAGE" if certified else "PATH_FIRST_SAFE_FALLBACK")
        ),
        "certified_switch_requires_classifier_and_paid_relation_witness": (
            not certified
            or all(
                document["classifier_decision"] == "RELATION_COVERAGE"
                and document["paid_prefix_relation_candidate_count"] > 0
                for document in (prior_doc, strict_doc)
            )
        ),
        "unwitnessed_classifier_positive_falls_back_exactly": all(
            not (
                document["classifier_decision"] == "RELATION_COVERAGE"
                and not document["certified_positive_switch"]
            )
            or document[
                "unwitnessed_positive_classifier_decision_falls_back_exactly"
            ]
            for document in (prior_doc, strict_doc)
        ),
        "fallback_resumed_same_generator_object_both_arms": (
            all(
                document["fallback_resumed_same_path_first_generator_object"]
                is True
                for document in (prior_doc, strict_doc)
            )
            if fallback
            else True
        ),
        "no_additional_classifier_only_target_labels": all(
            document["additional_classifier_only_target_labels"] == 0
            for document in (prior_doc, strict_doc)
        ),
        "v160_and_v161_failures_preserved": True,
        "query_policy_noninferior_to_exact_path_first": guard_reduction >= 0,
        "certified_switch_is_noninferior_when_exercised": (
            guard_reduction >= 0 if certified else True
        ),
        "strict_query_policy_reduction_not_required_after_v162_counterexample": True,
        "factor_prior_sample_reduction_measured_separately": factor_reduction >= 0,
        "v162_failed_identity_preserved": True,
    }
    gate["passed"] = all(value for value in gate.values() if type(value) is bool)
    payload = {
        "schema": "acfqp.safe_paid_path_sample_tax_occurrence.v163",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(EXPECTED_EPISODES),
        "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "v146_factor_bank_id": prior_doc["v146_factor_bank_id"],
        "v146_independent_verification_id": prior_doc[
            "v146_independent_verification_id"
        ],
        "progressive_prior_acquisition": prior_doc,
        "progressive_strict_acquisition": strict_doc,
        "progressive_prior_sequence": row["progressive_prior_sequence"],
        "progressive_strict_sequence": row["progressive_strict_sequence"],
        "legacy_path_first_prior_summary": legacy_summary,
        "applicable_plan_receipt_mode": next(iter(plan_modes)),
        "accounting": accounting,
        "registered_gate": gate,
        "query_policy_sample_reduction_vs_legacy_path_first": guard_reduction,
        "factor_prior_sample_reduction_within_progressive_policy": factor_reduction,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V163_THREE_FAMILY_COHORT",
        "query_policy_classifier_is_model_planning_or_certificate_authority": False,
        "complete_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "failed_v160_campaign_id": V160_FAILED_CAMPAIGN_ID,
        "failed_v160_record_sha256": V160_FAILURE_SHA256,
        "failed_v161_preregistration_id": V161_FAILED_PREREGISTRATION_ID,
        "failed_v161_record_sha256": V161_FAILURE_SHA256,
        "certified_positive_switch": certified,
        "exact_path_first_fallback": fallback,
        "v160_and_v161_failures_preserved_not_reclassified": True,
        "failed_v162_campaign_id": V162_FAILED_CAMPAIGN_ID,
        "failed_v162_record_sha256": V162_FAILURE_SHA256,
        "v162_failure_preserved_not_reclassified": True,
        "query_policy_strict_sample_reduction_claimed": False,
    }
    expected = {
        **payload,
        "occurrence_id": _content_id(
            domains.CONSTRUCTION_K7_OCCURRENCE_V163_DOMAIN, payload
        ),
    }
    _require(row == expected, "V163 occurrence evidence changed")
    return {
        "occurrence_id": row["occurrence_id"],
        "family": family,
        "seed": seed,
        "classifier_decision": prepared["classifier_decision"],
        "certified_positive_switch": certified,
        "paid_relation_candidate_count": len(prepared["relation_candidates"]),
        "query_policy_labels_avoided": guard_reduction,
        "factor_prior_labels_avoided": factor_reduction,
        "prior_sequence": prior_sequence,
        "strict_sequence": strict_sequence,
        "accounting": accounting,
        "registered_gate": gate,
    }


def freeze_safe_paid_path_sample_tax_verification_v163(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v162_failure_raw: bytes,
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    registration = loads_canonical_json(preregistration_raw)
    classifier = loads_canonical_json(classifier_receipt_raw)
    bank = loads_canonical_json(bank_raw)
    bank_verification = loads_canonical_json(bank_verification_raw)
    failure = loads_canonical_json(v162_failure_raw)
    _frozen(
        campaign_raw,
        campaign,
        count=CAMPAIGN_BYTE_COUNT,
        digest=CAMPAIGN_SHA256,
        key="campaign_id",
        identity=CAMPAIGN_ID,
        label="campaign",
    )
    _verify_id(campaign, "campaign_id", domains.CONSTRUCTION_K7_CAMPAIGN_V163_DOMAIN)
    _frozen(
        preregistration_raw,
        registration,
        count=PREREGISTRATION_BYTE_COUNT,
        digest=PREREGISTRATION_SHA256,
        key="preregistration_id",
        identity=PREREGISTRATION_ID,
        label="preregistration",
    )
    _verify_id(
        registration,
        "preregistration_id",
        domains.CONSTRUCTION_K7_TARGET_PREREGISTRATION_V163_DOMAIN,
    )
    _frozen(
        classifier_receipt_raw,
        classifier,
        count=CLASSIFIER_BYTE_COUNT,
        digest=CLASSIFIER_SHA256,
        key="classifier_receipt_id",
        identity=CLASSIFIER_RECEIPT_ID,
        label="classifier receipt",
    )
    _require(
        classifier["fresh_v161_target_outcomes_accessed"] is False
        and classifier["fresh_v161_target_labels"] == 0
        and classifier["offline_source_observation_labels"] == 96
        and classifier[
            "query_policy_classifier_is_model_planning_or_certificate_authority"
        ]
        is False,
        "V163 classifier claim boundary changed",
    )
    _require(
        canonical_json_bytes(failure) == v162_failure_raw
        and len(v162_failure_raw) == V162_FAILURE_BYTE_COUNT
        and hashlib.sha256(v162_failure_raw).hexdigest() == V162_FAILURE_SHA256
        and failure["failed_campaign_id"] == V162_FAILED_CAMPAIGN_ID
        and failure["failed_result_not_reclassified_as_success"] is True
        and failure["same_identity_rerun_forbidden"] is True,
        "V163 preserved V162 failure changed",
    )
    _require(
        canonical_json_bytes(bank) == bank_raw
        and bank.get("bank_id") == v151.BANK_ID
        and len(bank_raw) == v151.previous.base.BANK_BYTE_COUNT
        and hashlib.sha256(bank_raw).hexdigest() == v151.previous.base.BANK_SHA256
        and canonical_json_bytes(bank_verification) == bank_verification_raw
        and bank_verification.get("verification_id") == v151.BANK_VERIFICATION_ID
        and len(bank_verification_raw)
        == v151.previous.base.BANK_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(bank_verification_raw).hexdigest()
        == v151.previous.base.BANK_VERIFICATION_SHA256,
        "V163 frozen factor bank changed",
    )
    for fact in registration["frozen_implementation_source_facts"]:
        raw = (SOURCE_ROOT / fact["relative_path"]).read_bytes()
        _require(
            len(raw) == fact["byte_count"]
            and hashlib.sha256(raw).hexdigest() == fact["sha256"],
            "V163 source closure changed",
        )
    _require(
        registration["frozen_classifier_receipt"] == classifier
        and registration["frozen_v162_failure"]["document"] == failure
        and registration["target_occurrences"]
        == [
            {"family": family, "seed": seed}
            for family, seed in EXPECTED_OCCURRENCES
        ]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES
        and registration["target_worker_count"] == 2
        and registration["required_target_occurrence_count"] == 8
        and all(registration["registered_gate"].values())
        and registration["claim_boundary"]["target_outcomes_accessed"] is False
        and registration["claim_boundary"][
            "strict_query_policy_sample_reduction_claimed"
        ]
        is False,
        "V163 preregistered contract changed",
    )
    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(
            executor.map(
                _verify_occurrence,
                (
                    (
                        row,
                        bank,
                        bank_raw,
                        bank_verification_raw,
                        classifier,
                    )
                    for row in campaign["target_occurrences"]
                ),
            )
        )
    _require(
        tuple((row["family"], row["seed"]) for row in rows)
        == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"]
        == [row["occurrence_id"] for row in rows],
        "V163 occurrence inventory changed",
    )
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric
    }
    guards = tuple(row["query_policy_labels_avoided"] for row in rows)
    factors = tuple(row["factor_prior_labels_avoided"] for row in rows)
    accounting.update(
        offline_source_observation_labels=96,
        target_classifier_path_prefix_labels=sum(
            row["accounting"]["classifier_prefix_labels_included_in_acquisition"]
            for row in rows
        ),
        additional_classifier_only_target_labels=0,
        total_query_policy_labels_avoided_vs_exact_path_first=sum(guards),
        total_factor_prior_labels_avoided_within_same_query_policy=sum(factors),
        source_and_target_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    certified_rows = [row for row in rows if row["certified_positive_switch"]]
    fallback_rows = [row for row in rows if not row["certified_positive_switch"]]
    gate = {
        "required_target_occurrence_count": 8,
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "all_three_registered_families_present": {
            row["family"] for row in rows
        }
        == {POSITIVE_FAMILY, FALLBACK_FAMILY, MODULAR_FAMILY},
        "at_least_one_certified_switch_exercised": bool(certified_rows),
        "query_policy_noninferior_everywhere": all(value >= 0 for value in guards),
        "every_certified_switch_noninferior": all(
            row["query_policy_labels_avoided"] >= 0 for row in certified_rows
        ),
        "every_exact_fallback_is_zero_regression": all(
            row["query_policy_labels_avoided"] == 0
            and row["registered_gate"]["exact_fallback_has_zero_regression"]
            for row in fallback_rows
        ),
        "factor_prior_noninferior_everywhere": all(value >= 0 for value in factors),
        "factor_prior_strictly_reduces_sample_tax_in_aggregate": sum(factors) > 0,
        "sample_tax_axes_remain_separate": accounting[
            "source_and_target_labels_execution_steps_derivation_and_planning_compute_separate"
        ],
        "no_additional_classifier_only_target_labels": accounting[
            "additional_classifier_only_target_labels"
        ]
        == 0,
        "both_arm_receding_plans_succeed_everywhere": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in rows
        ),
        "certificate_failure_local_recovery_exercised": sum(
            row["accounting"]["progressive_prior_certificate_local_labels"]
            + row["accounting"]["progressive_strict_certificate_local_labels"]
            for row in rows
        )
        > 0,
        "all_executed_actions_have_v109_receipts": all(
            row["registered_gate"]["all_executed_actions_have_v109_receipts"]
            for row in rows
        ),
        "strict_incompatible_schema_no_transfer_verified": incompatible_schema_no_transfer_control_v99()[
            "strict_ood_no_transfer"
        ],
        "v162_failed_identity_preserved_everywhere": True,
        "strict_query_policy_reduction_not_claimed": True,
    }
    gate["passed"] = (
        len(rows) == 8
        and gate["passed_target_occurrence_count"] == 8
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.safe_paid_path_sample_tax_campaign.v163",
        "preregistration_id": PREREGISTRATION_ID,
        "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "failed_v162_campaign_id": V162_FAILED_CAMPAIGN_ID,
        "failed_v162_record_sha256": V162_FAILURE_SHA256,
        "target_occurrences": campaign["target_occurrences"],
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": incompatible_schema_no_transfer_control_v99(),
        "accounting": accounting,
        "registered_gate": gate,
        "safe_query_and_factor_prior_sample_tax_reduction_verified": gate["passed"],
        "v162_failure_preserved_not_reclassified": True,
        "query_policy_strict_sample_reduction_claimed": False,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V163_THREE_FAMILY_COHORT",
        "query_policy_classifier_is_model_planning_or_certificate_authority": False,
        "complete_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    expected_campaign = {
        **payload,
        "campaign_id": _content_id(
            domains.CONSTRUCTION_K7_CAMPAIGN_V163_DOMAIN, payload
        ),
    }
    _require(campaign == expected_campaign, "V163 aggregate campaign changed")
    verification_payload = {
        "schema": "acfqp.safe_paid_path_sample_tax_verification.v163",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "preserved_v162_failed_campaign_id": V162_FAILED_CAMPAIGN_ID,
        "preserved_v162_failure_sha256": V162_FAILURE_SHA256,
        "v146_factor_bank_id": v151.BANK_ID,
        "v146_independent_verification_id": v151.BANK_VERIFICATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_paid_prefix_classifier_and_relation_witness_reconstruction": True,
        "producer_free_prior_strict_and_exact_path_acquisition_reconstruction": True,
        "producer_free_receding_abstract_planning_and_v109_receipt_reconstruction": True,
        "producer_free_certificate_failure_local_recovery_reconstruction": True,
        "safe_query_and_factor_prior_sample_tax_evidence_independently_verified": True,
        "query_policy_labels_avoided_vs_exact_path_first": sum(guards),
        "factor_prior_labels_avoided_within_same_query_policy": sum(factors),
        "sample_tax_claim_scope": campaign["sample_tax_claim_scope"],
        "query_policy_strict_sample_reduction_claimed": False,
        "query_policy_classifier_is_model_planning_or_certificate_authority": False,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **verification_payload,
        "verification_id": _content_id(
            domains.CONSTRUCTION_K7_VERIFICATION_V163_DOMAIN,
            verification_payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V163 frozen verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_safe_paid_path_sample_tax_verification_v163",
)
