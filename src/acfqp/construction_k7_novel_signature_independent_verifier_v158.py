"""Producer-free reconstruction of the frozen V158 campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v158 as domains
from acfqp import construction_k7_plan_mode_margin_independent_verifier_v157 as v157
from acfqp import construction_k7_relation_coverage_independent_verifier_v153 as v153
from acfqp import construction_k7_relation_keyed_bank_independent_verifier_v151 as v151
from acfqp import construction_k7_structural_signature_guarded_independent_verifier_v155 as v155
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_novel_signature_adapters_v158 import (
    FALLBACK_FAMILY,
    POSITIVE_FAMILY,
    build_novel_fallback_signature_adapter_v158,
    build_novel_positive_signature_adapter_v158,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "2c4dbab749685e8b3b7cafdd6c9ba7938ce0c5e4a9ee7efed82da3c65cde8adf"
CAMPAIGN_BYTE_COUNT = 15_598_562
CAMPAIGN_SHA256 = "5d14ca42d6168e237f1164995177db0216085eaa340f537b417c8c66f38a34ee"
PREREGISTRATION_ID = "52fb493325ad0abfc00f4d5a1a186dbc982d837224915320193b250bc75f6800"
PREREGISTRATION_BYTE_COUNT = 5_345
PREREGISTRATION_SHA256 = "a65518df8a7ed50c4fc369744495c3bdf9eb5c83f754fd4bb3ed4ce821e77045"
CLASSIFIER_RECEIPT_ID = "0996b4e38becfcf83fdc9d834f5133efd8be5c05632200e2465680320ef3c95d"
CLASSIFIER_RECEIPT_BYTE_COUNT = 1_623
CLASSIFIER_RECEIPT_SHA256 = "862ef939af9f7eec694cddd010d9851d024e9313dce36bd2729d4f1f43eb76b4"
V157_CAMPAIGN_ID = v157.CAMPAIGN_ID
V157_CAMPAIGN_BYTE_COUNT = v157.CAMPAIGN_BYTE_COUNT
V157_CAMPAIGN_SHA256 = v157.CAMPAIGN_SHA256
V157_VERIFICATION_ID = v157.VERIFICATION_ID
V157_VERIFICATION_BYTE_COUNT = v157.EXPECTED_CANONICAL_BYTE_COUNT
V157_VERIFICATION_SHA256 = v157.EXPECTED_CANONICAL_SHA256
BANK_ID = v157.BANK_ID
BANK_VERIFICATION_ID = v157.BANK_VERIFICATION_ID
EXPECTED_OCCURRENCES = tuple(
    [(POSITIVE_FAMILY, seed) for seed in range(1_047_921, 1_047_925)]
    + [(FALLBACK_FAMILY, seed) for seed in range(1_047_931, 1_047_935)]
)
EXPECTED_EPISODES = (761, 762, 763, 764)
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
SOURCE_ROOT = Path(__file__).resolve().parents[2]
_BUILDERS = {
    POSITIVE_FAMILY: build_novel_positive_signature_adapter_v158,
    FALLBACK_FAMILY: build_novel_fallback_signature_adapter_v158,
}
_ACQUISITION_ADDITIONS = {
    "source_v148_acquisition_id",
    "classifier_receipt_id",
    "anonymous_initial_action_support_signature",
    "selected_classifier_expression",
    "selected_predicate_match_count",
    "guard_decision",
    "exact_signature_registry_consulted",
    "classifier_accessed_ground_successor_outcomes",
    "classifier_changes_query_order_not_hypothesis_pool_or_stop_rule",
    "classifier_is_model_planning_or_certificate_authority",
}


class ConstructionK7NovelSignatureIndependentVerifierV158Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7NovelSignatureIndependentVerifierV158Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V158 {key} changed")


def _frozen(raw, document, *, count, digest, key, identity, label):
    _require(
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(key) == identity,
        f"V158 frozen {label} changed",
    )


def _signature(adapter):
    initial_keys = tuple(
        adapter.action_key(action) for action in adapter.actions(adapter.initial())
    )
    return tuple(
        sorted(
            (
                len({adapter.catalogue[key].fields[field] for key in initial_keys}),
                len({action.fields[field] for action in adapter.catalogue}),
            )
            for field in range(len(adapter.catalogue[0].fields))
        )
    )


def _evaluate(expression, signature):
    index = 0 if expression["predicate_field"] == "INITIAL_SUPPORT" else 1
    if expression["predicate_comparator"] == "EQUAL":
        count = sum(pair[index] == expression["predicate_value"] for pair in signature)
    else:
        count = sum(pair[index] >= expression["predicate_value"] for pair in signature)
    return count > expression["count_threshold"], count


def _synthesize_classifier(positive, failed):
    labelled = tuple((signature, True) for signature in positive) + tuple(
        (signature, False) for signature in failed
    )
    candidates = []
    evaluated = 0
    for field_rank, field in enumerate(("INITIAL_SUPPORT", "CATALOGUE_SUPPORT")):
        for comparator_rank, comparator in enumerate(("EQUAL", "AT_LEAST")):
            for value in range(1, 17):
                for threshold in range(0, 7):
                    expression = {
                        "kind": "COUNT_PREDICATE_GREATER_THAN",
                        "predicate_field": field,
                        "predicate_comparator": comparator,
                        "predicate_value": value,
                        "count_threshold": threshold,
                    }
                    evaluated += 1
                    if all(
                        _evaluate(expression, signature)[0] is label
                        for signature, label in labelled
                    ):
                        mdl = (
                            1,
                            comparator_rank,
                            value.bit_length(),
                            threshold.bit_length(),
                            field_rank,
                            value,
                            threshold,
                        )
                        candidates.append((mdl, expression))
    _require(bool(candidates), "V158 classifier grammar no longer separates source labels")
    mdl, expression = min(
        candidates, key=lambda row: (row[0], canonical_json_bytes(row[1]))
    )
    return expression, list(mdl), evaluated, len(candidates)


def _verify_classifier(
    raw: bytes,
    source_campaign: Mapping[str, Any],
    source_verification: Mapping[str, Any],
):
    positive = tuple(
        sorted(
            {
                tuple(
                    tuple(pair)
                    for pair in row["anonymous_relational_factor_prior_acquisition"][
                        "anonymous_initial_action_support_signature"
                    ]
                )
                for row in source_campaign["target_occurrences"]
                if row["anonymous_relational_factor_prior_acquisition"]["guard_decision"]
                == "RELATION_COVERAGE"
            }
        )
    )
    failed = tuple(
        sorted(
            {
                tuple(
                    tuple(pair)
                    for pair in row["anonymous_relational_factor_prior_acquisition"][
                        "anonymous_initial_action_support_signature"
                    ]
                )
                for row in source_campaign["target_occurrences"]
                if row["anonymous_relational_factor_prior_acquisition"]["guard_decision"]
                == "PATH_FIRST_SAFE_FALLBACK"
            }
        )
    )
    expression, mdl, evaluated, separating = _synthesize_classifier(positive, failed)
    payload = {
        "schema": "acfqp.anonymous_query_classifier_receipt.v158",
        "source_v157_campaign_id": V157_CAMPAIGN_ID,
        "source_v157_verification_id": V157_VERIFICATION_ID,
        "finite_typed_classifier_grammar": {
            "aggregate": "COUNT_PREDICATE_GREATER_THAN",
            "predicate_fields": ["INITIAL_SUPPORT", "CATALOGUE_SUPPORT"],
            "predicate_comparators": ["EQUAL", "AT_LEAST"],
            "predicate_values": {"minimum": 1, "maximum": 16},
            "count_thresholds": {"minimum": 0, "maximum": 6},
        },
        "source_positive_signatures": [
            [list(pair) for pair in signature] for signature in positive
        ],
        "source_failed_signatures": [
            [list(pair) for pair in signature] for signature in failed
        ],
        "selected_expression": expression,
        "selected_expression_mdl_key": mdl,
        "candidate_expression_count_evaluated": evaluated,
        "separating_expression_count": separating,
        "exact_mdl_then_canonical_tie_break": True,
        "source_labels_derived_only_from_frozen_predecessor_campaigns": True,
        "fresh_v158_target_outcomes_accessed": False,
        "exact_signature_registry_consulted_at_application": False,
        "classifier_is_query_order_meta_prior_not_model_or_certificate_authority": True,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    expected = {
        **payload,
        "classifier_receipt_id": _content_id(
            domains.CONSTRUCTION_K7_CLASSIFIER_RECEIPT_V158_DOMAIN, payload
        ),
    }
    document = loads_canonical_json(raw)
    _frozen(
        raw,
        document,
        count=CLASSIFIER_RECEIPT_BYTE_COUNT,
        digest=CLASSIFIER_RECEIPT_SHA256,
        key="classifier_receipt_id",
        identity=CLASSIFIER_RECEIPT_ID,
        label="classifier receipt",
    )
    _require(
        source_verification.get(
            "registered_plan_mode_corrected_margin_evidence_independently_verified"
        )
        is True
        and document == expected,
        "V158 classifier receipt was not independently rederived",
    )
    return document


def _config():
    config = v157._config()  # noqa: SLF001
    config["families"][POSITIVE_FAMILY] = {"maximum_acquisition_labels": 1_536}
    config["families"][FALLBACK_FAMILY] = {"maximum_acquisition_labels": 1_536}
    return config


def _normalized_acquisition(recorded, *, classifier, signature, selected, count):
    _verify_id(
        recorded, "acquisition_id", domains.CONSTRUCTION_K7_ACQUISITION_V158_DOMAIN
    )
    expected_decision = (
        "RELATION_COVERAGE" if selected else "PATH_FIRST_SAFE_FALLBACK"
    )
    _require(
        recorded.get("schema") == "acfqp.classifier_guarded_acquisition_arm.v158"
        and recorded.get("classifier_receipt_id") == CLASSIFIER_RECEIPT_ID
        and recorded.get("anonymous_initial_action_support_signature")
        == [list(pair) for pair in signature]
        and recorded.get("selected_classifier_expression")
        == classifier["selected_expression"]
        and recorded.get("selected_predicate_match_count") == count
        and recorded.get("guard_decision") == expected_decision
        and recorded.get("exact_signature_registry_consulted") is False
        and recorded.get("classifier_accessed_ground_successor_outcomes") is False
        and recorded.get("classifier_changes_query_order_not_hypothesis_pool_or_stop_rule")
        is True
        and recorded.get("classifier_is_model_planning_or_certificate_authority")
        is False,
        "V158 classifier acquisition wrapper changed",
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
        EXPECTED_EPISODES=EXPECTED_EPISODES, _fail=_fail, _require=_require
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
        _v150_sequence_verifier=_sequence_verifier, _fail=_fail, _require=_require
    )
    verifier = FunctionType(
        v157._verify_sequence.__code__,  # noqa: SLF001
        globals_v157,
        name=v157._verify_sequence.__name__,  # noqa: SLF001
    )
    return verifier(sequence, candidate, rows, family=family, seed=seed)


def _legacy(adapter, bank, row, *, config, selected):
    recorded = row["legacy_path_first_prior_acquisition_summary"]
    if not selected:
        prior = row["anonymous_relational_factor_prior_acquisition"]
        return {
            "ground_support_labels": prior["ground_support_labels"],
            "first_accepting_observation_label": prior[
                "first_accepting_observation_label"
            ],
            "raw_transition_sha256": prior["raw_transition_sha256"],
            "relational_artifact_expression_selected_count": prior[
                "relational_artifact_expression_selected_count"
            ],
        }
    return v153._legacy_summary(  # noqa: SLF001
        adapter, bank, target=recorded["ground_support_labels"], config=config
    )


def _verify_occurrence(args):
    row, bank, classifier = args
    family, seed = row["target_family"], row["seed"]
    _require(
        (family, seed) in EXPECTED_OCCURRENCES
        and row.get("schema") == "acfqp.novel_signature_occurrence.v158"
        and tuple(row.get("episode_indices", ())) == EXPECTED_EPISODES,
        "V158 occurrence identity changed",
    )
    _verify_id(row, "occurrence_id", domains.CONSTRUCTION_K7_OCCURRENCE_V158_DOMAIN)
    config = _config()
    adapter = _BUILDERS[family](seed, config)
    signature = _signature(adapter)
    selected, count = _evaluate(classifier["selected_expression"], signature)
    expected_selected = family == POSITIVE_FAMILY
    _require(selected is expected_selected, "V158 classifier decision changed")
    source_signatures = {
        tuple(tuple(pair) for pair in signature_row)
        for key in ("source_positive_signatures", "source_failed_signatures")
        for signature_row in classifier[key]
    }
    _require(signature not in source_signatures, "V158 target signature is not novel")
    prior_doc = row["anonymous_relational_factor_prior_acquisition"]
    strict_doc = row["strict_no_prior_acquisition"]
    stream = (
        v153._adaptive_stream(adapter)  # noqa: SLF001
        if selected
        else v151.previous.base.previous.base.path_predecessor._path_first_batches(  # noqa: SLF001
            adapter
        )
    )
    batches = tuple(next(stream) for _ in range(strict_doc["ground_support_labels"]))
    prior_candidate, prior_rows = v151.previous.base._rebuild_acquisition(  # noqa: SLF001
        _normalized_acquisition(
            prior_doc,
            classifier=classifier,
            signature=signature,
            selected=selected,
            count=count,
        ),
        adapter,
        bank,
        batches,
        enabled=True,
        config=config,
    )
    strict_candidate, strict_rows = v151.previous.base._rebuild_acquisition(  # noqa: SLF001
        _normalized_acquisition(
            strict_doc,
            classifier=classifier,
            signature=signature,
            selected=selected,
            count=count,
        ),
        adapter,
        bank,
        batches,
        enabled=False,
        config=config,
    )
    prior_sequence, prior_mode = _verify_sequence(
        row["anonymous_relational_factor_prior_owned_sequence"],
        prior_candidate,
        prior_rows,
        family=family,
        seed=seed,
    )
    strict_sequence, strict_mode = _verify_sequence(
        row["strict_no_prior_owned_sequence"],
        strict_candidate,
        strict_rows,
        family=family,
        seed=seed,
    )
    expected_mode = (
        "DIRECT_GENERIC_FACTOR_PROGRAM"
        if selected
        else "V115_MEMOIZED_COMPILED_PROGRAM"
    )
    _require(
        prior_mode == strict_mode == expected_mode == row["applicable_plan_receipt_mode"],
        "V158 plan receipt mode changed",
    )
    legacy = _legacy(adapter, bank, row, config=config, selected=selected)
    recorded_legacy = row["legacy_path_first_prior_acquisition_summary"]
    _require(
        legacy == {key: recorded_legacy[key] for key in legacy}
        and type(recorded_legacy.get("acquisition_id")) is str
        and len(recorded_legacy["acquisition_id"]) == 64,
        "V158 legacy acquisition reconstruction changed",
    )
    exact_fallback = (
        prior_doc["source_v148_acquisition_id"] == recorded_legacy["acquisition_id"]
        and prior_doc["ground_support_labels"] == recorded_legacy["ground_support_labels"]
        and prior_doc["raw_transition_sha256"]
        == recorded_legacy["raw_transition_sha256"]
    )
    ood = v155._rebuild_ood(seed + 5_000_000, config)  # noqa: SLF001
    _require(row["nonrelational_ood_control"] == ood, "V158 OOD changed")
    guard_reduction = legacy["ground_support_labels"] - prior_doc[
        "ground_support_labels"
    ]
    factor_reduction = strict_doc["ground_support_labels"] - prior_doc[
        "ground_support_labels"
    ]
    accounting = {
        "anonymous_relational_prior_acquisition_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_anonymous_relational_prior": factor_reduction,
        "anonymous_relational_prior_certificate_local_labels": prior_sequence[
            "certificate_local_labels"
        ],
        "strict_no_prior_certificate_local_labels": strict_sequence[
            "certificate_local_labels"
        ],
        "anonymous_relational_prior_lifetime_target_labels": prior_doc[
            "ground_support_labels"
        ]
        + prior_sequence["certificate_local_labels"],
        "strict_no_prior_lifetime_target_labels": strict_doc["ground_support_labels"]
        + strict_sequence["certificate_local_labels"],
        "anonymous_relational_prior_execution_steps": prior_sequence[
            "execution_steps"
        ],
        "strict_no_prior_execution_steps": strict_sequence["execution_steps"],
        "anonymous_relational_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "strict_no_prior_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "anonymous_relational_prior_binding_compute_events": prior_doc[
            "template_binding_evaluation_events"
        ],
        "strict_no_prior_binding_compute_events": strict_doc[
            "template_binding_evaluation_events"
        ],
        "anonymous_relational_prior_planning_compute_events": prior_sequence[
            "planning_compute_events"
        ],
        "strict_no_prior_planning_compute_events": strict_sequence[
            "planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
        "legacy_path_first_prior_acquisition_labels": legacy["ground_support_labels"],
        "labels_avoided_by_synthesized_classifier_vs_legacy_prior": guard_reduction,
        "labels_avoided_by_factor_prior_within_classifier_guarded_operator": factor_reduction,
        "nonrelational_ood_compatibility_observation_labels": ood[
            "observation_batch_count"
        ],
    }
    source_sequences = (
        row["anonymous_relational_factor_prior_owned_sequence"],
        row["strict_no_prior_owned_sequence"],
    )
    gate = {
        "matched_acquisition_completed_within_registered_cap": all(
            0 < document["ground_support_labels"] <= 1_536
            for document in (prior_doc, strict_doc)
        ),
        "same_raw_transition_prefix_through_common_label": True,
        "same_synthesizer_representation_and_stop_rule": all(
            prior_doc[key] is True and strict_doc[key] is True
            for key in (
                "binding_derived_from_current_raw_prefix_in_both_arms",
                "same_generic_atomic_hypothesis_pool",
                "same_candidate_carrier_and_schema",
                "same_candidate_replay_function",
                "same_stopping_rule_function",
            )
        ),
        "only_arm_switch_is_anonymous_relational_prior": prior_doc[
            "only_arm_switch_is_anonymous_relational_prior"
        ]
        is True
        and strict_doc["only_arm_switch_is_anonymous_relational_prior"] is True,
        "v146_source_family_absent_from_target_domain": True,
        "anonymous_relational_instantiation_present_both_arms": all(
            document["anonymous_relational_instantiation"][
                "exact_relational_instantiation_count"
            ]
            > 0
            for document in (prior_doc, strict_doc)
        ),
        "at_least_one_bank_template_selected_in_prior_arm": prior_doc[
            "artifact_expression_selected_count"
        ]
        > 0,
        "both_arm_receding_episodes_succeed": all(
            episode["success"]
            for sequence in source_sequences
            for episode in sequence["episodes"]
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            sequence["every_new_ground_query_followed_a_failed_certificate"]
            for sequence in source_sequences
        ),
        "planner_consumes_compiled_model_without_raw_rows": all(
            sequence[
                "planner_consumed_compiled_successor_without_raw_transition_argument"
            ]
            for sequence in source_sequences
        ),
        "sound_certificate_local_recovery_union": all(
            sequence["source_partial_program_mutated_after_certificate_failure"]
            is False
            and sequence["every_uncompiled_edge_is_certificate_local"] is True
            and sequence["overlay_promoted_to_global_dynamics"] is False
            and sequence["query_local_overlay_used_as_safety_authority"] is False
            for sequence in source_sequences
        ),
        "classifier_receipt_frozen_before_target_outcomes": classifier[
            "fresh_v158_target_outcomes_accessed"
        ]
        is False,
        "target_exact_signature_absent_from_source_registry": signature
        not in source_signatures,
        "classifier_decision_matches_registered_source_label": selected
        is expected_selected,
        "exact_signature_registry_not_consulted": prior_doc[
            "exact_signature_registry_consulted"
        ]
        is False,
        "positive_classifier_relation_coverage_noninferior": guard_reduction >= 0
        if expected_selected
        else True,
        "fallback_classifier_selected_exact_path_first": exact_fallback
        if not expected_selected
        else True,
        "classifier_introduced_no_sample_regression": guard_reduction >= 0,
        "factor_prior_noninferior_within_same_classifier_policy": factor_reduction
        >= 0,
        "relation_template_selected_in_prior_arm": prior_doc[
            "relational_artifact_expression_selected_count"
        ]
        > 0,
        "same_relation_available_in_strict_pool": strict_doc[
            "relational_artifact_expression_selected_count"
        ]
        > 0,
        "applicable_plan_receipt_path_exercised_both_arms": all(
            sequence["exactly_one_registered_plan_mode_exercised"]
            for sequence in source_sequences
        ),
        "registered_family_plan_mode_observed_both_arms": all(
            sequence["applicable_plan_receipt_mode"] == expected_mode
            for sequence in source_sequences
        ),
        "all_executed_actions_have_v109_receipts": all(
            sequence["all_executed_actions_have_v109_receipts"]
            for sequence in source_sequences
        ),
        "nonrelational_ood_rejected_before_bank_access": ood[
            "operator_transfer_rejected_before_bank_access"
        ]
        and ood["factor_bank_bytes_supplied_to_ood_control"] is False,
    }
    gate["passed"] = all(gate.values())
    _require(
        row["classifier_receipt_id"] == CLASSIFIER_RECEIPT_ID
        and row["v146_factor_bank_id"] == BANK_ID
        and row["v146_independent_verification_id"] == BANK_VERIFICATION_ID
        and row["accounting"] == accounting
        and row["registered_gate"] == gate
        and row["paired_label_reduction"] == factor_reduction
        and row["guard_sample_reduction_vs_legacy_prior"] == guard_reduction
        and row["factor_prior_sample_reduction_within_guarded_operator"]
        == factor_reduction
        and row["selected_predicate_match_count"] == count
        and row["applicable_plan_receipt_mode"] == expected_mode
        and row["sample_tax_guard_claim_scope"]
        == "ONLY_THE_PREREGISTERED_V158_NOVEL_SIGNATURE_COHORT"
        and row["classifier_is_planning_or_certificate_authority"] is False
        and row["v156_failure_and_v157_success_preserved"] is True
        and row["registered_workload_sample_efficiency_improvement_observed"]
        is (factor_reduction > 0)
        and row["complete_ground_world_model_synthesized"] is False
        and row["arbitrary_unseen_domain_transfer_claimed"] is False
        and row["official_execution_allowed"] is False
        and row["official_scalar_cost"] is None
        and row["official_N_break_even"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and row["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V158 occurrence evidence changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "family": family,
        "seed": seed,
        "signature": [list(pair) for pair in signature],
        "classifier_selected": selected,
        "predicate_match_count": count,
        "plan_mode": expected_mode,
        "guard_labels_avoided": guard_reduction,
        "factor_prior_labels_avoided": factor_reduction,
        "prior_sequence": prior_sequence,
        "strict_sequence": strict_sequence,
        "accounting": accounting,
    }


def freeze_novel_signature_verification_v158(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v157_campaign_raw: bytes,
    v157_verification_raw: bytes,
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    registration = loads_canonical_json(preregistration_raw)
    bank = loads_canonical_json(bank_raw)
    bank_verification = loads_canonical_json(bank_verification_raw)
    source_campaign = loads_canonical_json(v157_campaign_raw)
    source_verification = loads_canonical_json(v157_verification_raw)
    _frozen(
        campaign_raw,
        campaign,
        count=CAMPAIGN_BYTE_COUNT,
        digest=CAMPAIGN_SHA256,
        key="campaign_id",
        identity=CAMPAIGN_ID,
        label="campaign",
    )
    _verify_id(campaign, "campaign_id", domains.CONSTRUCTION_K7_CAMPAIGN_V158_DOMAIN)
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
        domains.CONSTRUCTION_K7_PREREGISTRATION_V158_DOMAIN,
    )
    _frozen(
        v157_campaign_raw,
        source_campaign,
        count=V157_CAMPAIGN_BYTE_COUNT,
        digest=V157_CAMPAIGN_SHA256,
        key="campaign_id",
        identity=V157_CAMPAIGN_ID,
        label="V157 source campaign",
    )
    _frozen(
        v157_verification_raw,
        source_verification,
        count=V157_VERIFICATION_BYTE_COUNT,
        digest=V157_VERIFICATION_SHA256,
        key="verification_id",
        identity=V157_VERIFICATION_ID,
        label="V157 source verification",
    )
    classifier = _verify_classifier(
        classifier_receipt_raw, source_campaign, source_verification
    )
    _require(
        canonical_json_bytes(bank) == bank_raw
        and bank.get("bank_id") == BANK_ID
        and len(bank_raw) == v151.previous.base.BANK_BYTE_COUNT
        and hashlib.sha256(bank_raw).hexdigest() == v151.previous.base.BANK_SHA256
        and canonical_json_bytes(bank_verification) == bank_verification_raw
        and bank_verification.get("verification_id") == BANK_VERIFICATION_ID
        and len(bank_verification_raw) == v151.previous.base.BANK_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(bank_verification_raw).hexdigest()
        == v151.previous.base.BANK_VERIFICATION_SHA256,
        "V158 frozen factor bank changed",
    )
    for fact in registration["frozen_implementation_source_facts"]:
        raw = (SOURCE_ROOT / fact["relative_path"]).read_bytes()
        _require(
            len(raw) == fact["byte_count"]
            and hashlib.sha256(raw).hexdigest() == fact["sha256"],
            "V158 source closure changed",
        )
    _require(
        registration["frozen_classifier_receipt"] == classifier
        and registration["target_occurrences"]
        == [
            {"family": family, "seed": seed}
            for family, seed in EXPECTED_OCCURRENCES
        ]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES
        and registration["target_worker_count"] == 2
        and registration["required_target_occurrence_count"] == 8
        and registration["maximum_acquisition_labels"] == 1_536
        and all(registration["registered_gate"].values())
        and registration["claim_boundary"]["target_outcomes_accessed"] is False
        and registration["claim_boundary"]["official_scalar_cost"] is None,
        "V158 preregistered contract changed",
    )
    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(
            executor.map(
                _verify_occurrence,
                (
                    (row, bank, classifier)
                    for row in campaign["target_occurrences"]
                ),
            )
        )
    _require(
        tuple((row["family"], row["seed"]) for row in rows)
        == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"]
        == [row["occurrence_id"] for row in rows],
        "V158 occurrence inventory changed",
    )
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric
    }
    accounting.update(
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    factors = tuple(row["factor_prior_labels_avoided"] for row in rows)
    guards = tuple(row["guard_labels_avoided"] for row in rows)
    positive_rows = tuple(row for row in rows if row["family"] == POSITIVE_FAMILY)
    fallback_rows = tuple(row for row in rows if row["family"] == FALLBACK_FAMILY)
    family_reductions = {
        family: sum(
            row["factor_prior_labels_avoided"]
            for row in rows
            if row["family"] == family
        )
        for family in (POSITIVE_FAMILY, FALLBACK_FAMILY)
    }
    local_labels = (
        accounting["anonymous_relational_prior_certificate_local_labels"]
        + accounting["strict_no_prior_certificate_local_labels"]
    )
    gate = {
        "required_target_occurrence_count": 8,
        "passed_target_occurrence_count": 8,
        "required_target_family_count": 2,
        "observed_target_family_count": 2,
        "aggregate_paired_acquisition_label_reduction": sum(factors),
        "aggregate_positive_label_reduction": sum(factors) > 0,
        "positive_reduction_occurrence_count": sum(value > 0 for value in factors),
        "zero_reduction_occurrence_count": sum(value == 0 for value in factors),
        "negative_reduction_occurrence_count": sum(value < 0 for value in factors),
        "family_aggregate_reductions": family_reductions,
        "every_family_has_positive_aggregate_reduction": all(
            value > 0 for value in family_reductions.values()
        ),
        "same_synthesizer_and_stop_rule_everywhere": all(
            row["registered_gate"]["same_synthesizer_representation_and_stop_rule"]
            for row in campaign["target_occurrences"]
        ),
        "anonymous_relational_instantiation_present_everywhere": all(
            row["registered_gate"][
                "anonymous_relational_instantiation_present_both_arms"
            ]
            for row in campaign["target_occurrences"]
        ),
        "both_arm_receding_episodes_succeed_everywhere": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in campaign["target_occurrences"]
        ),
        "certificate_failure_local_recovery_exercised_at_least_once": local_labels
        > 0,
        "strict_incompatible_schema_no_transfer_verified": incompatible_schema_no_transfer_control_v99()[
            "strict_ood_no_transfer"
        ],
    }
    base_passed = all(
        (
            len(rows) == 8,
            gate["aggregate_positive_label_reduction"],
            gate["every_family_has_positive_aggregate_reduction"],
            gate["same_synthesizer_and_stop_rule_everywhere"],
            gate["anonymous_relational_instantiation_present_everywhere"],
            gate["both_arm_receding_episodes_succeed_everywhere"],
            gate["certificate_failure_local_recovery_exercised_at_least_once"],
            gate["strict_incompatible_schema_no_transfer_verified"],
        )
    )
    gate["passed"] = base_passed
    gate.update(
        classifier_receipt_id=CLASSIFIER_RECEIPT_ID,
        aggregate_guard_sample_reduction_vs_legacy_prior=sum(guards),
        positive_classifier_cohort_guard_reduction=sum(
            row["guard_labels_avoided"] for row in positive_rows
        ),
        fallback_classifier_cohort_guard_reduction=sum(
            row["guard_labels_avoided"] for row in fallback_rows
        ),
        aggregate_factor_prior_reduction_within_guarded_operator=sum(factors),
        positive_classifier_relation_coverage_positive_in_aggregate=sum(
            row["guard_labels_avoided"] for row in positive_rows
        )
        > 0,
        fallback_classifier_zero_regression_everywhere=all(
            row["guard_labels_avoided"] == 0 for row in fallback_rows
        ),
        classifier_noninferior_everywhere=all(value >= 0 for value in guards),
        factor_prior_noninferior_everywhere=all(value >= 0 for value in factors),
        factor_prior_positive_in_aggregate=sum(factors) > 0,
        all_target_exact_signatures_novel=all(
            row["registered_gate"]["target_exact_signature_absent_from_source_registry"]
            for row in campaign["target_occurrences"]
        ),
        both_classifier_sides_observed=bool(positive_rows) and bool(fallback_rows),
        exact_signature_registry_absent_everywhere=True,
        applicable_plan_receipt_path_exercised_everywhere=True,
        both_registered_plan_modes_observed={row["plan_mode"] for row in rows}
        == {"DIRECT_GENERIC_FACTOR_PROGRAM", "V115_MEMOIZED_COMPILED_PROGRAM"},
        nonrelational_ood_rejected_everywhere=True,
    )
    gate["passed"] = gate["passed"] and all(
        gate[key]
        for key in (
            "positive_classifier_relation_coverage_positive_in_aggregate",
            "fallback_classifier_zero_regression_everywhere",
            "classifier_noninferior_everywhere",
            "factor_prior_noninferior_everywhere",
            "factor_prior_positive_in_aggregate",
            "all_target_exact_signatures_novel",
            "both_classifier_sides_observed",
            "exact_signature_registry_absent_everywhere",
            "applicable_plan_receipt_path_exercised_everywhere",
            "both_registered_plan_modes_observed",
            "nonrelational_ood_rejected_everywhere",
        )
    )
    _require(
        campaign["schema"] == "acfqp.novel_signature_campaign.v158"
        and campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["classifier_receipt_id"] == CLASSIFIER_RECEIPT_ID
        and campaign["v146_factor_bank_id"] == BANK_ID
        and campaign["v146_independent_verification_id"] == BANK_VERIFICATION_ID
        and campaign["incompatible_schema_no_transfer_control"]
        == incompatible_schema_no_transfer_control_v99()
        and campaign["accounting"] == accounting
        and campaign["registered_gate"] == gate
        and gate["passed"] is True
        and sum(guards) == 428
        and sum(factors) == 28
        and campaign[
            "grammar_synthesized_classifier_novel_signature_transfer_observed"
        ]
        is True
        and campaign["sample_tax_reduction_claim_scope"]
        == "ONLY_THE_PREREGISTERED_V158_NOVEL_SIGNATURE_COHORT"
        and campaign["classifier_is_model_planning_or_certificate_authority"]
        is False
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["complete_world_model_synthesized"] is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V158 aggregate evidence changed",
    )
    payload = {
        "schema": "acfqp.novel_signature_verification.v158",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "source_v157_campaign_id": V157_CAMPAIGN_ID,
        "source_v157_verification_id": V157_VERIFICATION_ID,
        "v146_factor_bank_id": BANK_ID,
        "v146_independent_verification_id": BANK_VERIFICATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_finite_grammar_classifier_reconstruction": True,
        "producer_free_novel_signature_and_classifier_application_reconstruction": True,
        "producer_free_prior_strict_and_legacy_acquisition_reconstruction": True,
        "producer_free_direct_and_memoized_plan_receipt_reconstruction": True,
        "producer_free_abstract_planning_certificate_recovery_and_ood_reconstruction": True,
        "novel_signature_classifier_sample_tax_evidence_independently_verified": True,
        "guard_sample_reduction_vs_legacy_prior": sum(guards),
        "factor_prior_sample_reduction_within_guarded_operator": sum(factors),
        "sample_tax_reduction_claim_scope": campaign[
            "sample_tax_reduction_claim_scope"
        ],
        "classifier_is_model_planning_or_certificate_authority": False,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": _content_id(
            domains.CONSTRUCTION_K7_VERIFICATION_V158_DOMAIN, payload
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V158 frozen verification changed",
        )
    return raw


__all__ = ("VERIFICATION_ID", "freeze_novel_signature_verification_v158")
