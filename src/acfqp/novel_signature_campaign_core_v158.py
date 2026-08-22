"""V158 fresh exact-signature transfer of a synthesized query classifier."""

from __future__ import annotations

import copy
import hashlib
from types import FunctionType

from acfqp import anonymous_relational_factor_bank_acquisition_v148 as legacy_acquisition
from acfqp import construction_k7_domain_registry_extension_v158 as domains
from acfqp import cross_domain_relational_factor_bank_campaign_core_v149 as v149
from acfqp.anonymous_query_classifier_receipt_v158 import (
    CLASSIFIER_RECEIPT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as CLASSIFIER_RECEIPT_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as CLASSIFIER_RECEIPT_SHA256,
    SOURCE_FAILED_SIGNATURES,
    SOURCE_POSITIVE_SIGNATURES,
    evaluate_classifier_expression_v158,
)
from acfqp.applicable_plan_mode_sequence_v157 import annotate_applicable_plan_mode_sequence_v157
from acfqp.certified_memoized_planner_sequence_v154 import run_certified_memoized_planner_sequence_v154
from acfqp.classifier_guarded_acquisition_operator_v158 import acquire_matched_classifier_guarded_arms_v158
from acfqp.generic_novel_signature_adapters_v158 import (
    FALLBACK_FAMILY,
    POSITIVE_FAMILY,
    build_novel_fallback_signature_adapter_v158,
    build_novel_positive_signature_adapter_v158,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.relation_coverage_cross_structure_campaign_core_v154 import build_nonrelational_ood_control_v154
from acfqp.structural_margin_guarded_acquisition_operator_v156 import anonymous_initial_action_support_signature_v156
from acfqp.structural_margin_guarded_campaign_core_v156 import structural_margin_campaign_config_v156


TARGET_FAMILIES = (POSITIVE_FAMILY, FALLBACK_FAMILY)
_BUILDERS = {POSITIVE_FAMILY: build_novel_positive_signature_adapter_v158, FALLBACK_FAMILY: build_novel_fallback_signature_adapter_v158}


def novel_signature_campaign_config_v158():
    config = structural_margin_campaign_config_v156()
    config["families"][POSITIVE_FAMILY] = {"maximum_acquisition_labels": 1_536}
    config["families"][FALLBACK_FAMILY] = {"maximum_acquisition_labels": 1_536}
    return config


def _clone(function, namespace):
    clone = FunctionType(function.__code__, namespace, name=function.__name__, argdefs=function.__defaults__, closure=function.__closure__)
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def _verify_classifier(raw: bytes):
    document = loads_canonical_json(raw)
    if (
        canonical_json_bytes(document) != raw or len(raw) != CLASSIFIER_RECEIPT_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != CLASSIFIER_RECEIPT_SHA256
        or document.get("classifier_receipt_id") != CLASSIFIER_RECEIPT_ID or document.get("fresh_v158_target_outcomes_accessed") is not False
    ):
        raise ValueError("V158 classifier receipt changed")
    return document


_OCCURRENCE_GLOBALS = dict(v149.__dict__)
_OCCURRENCE_GLOBALS.update(
    _BUILDERS=_BUILDERS,
    acquire_matched_anonymous_relational_factor_bank_arms_v148=acquire_matched_classifier_guarded_arms_v158,
    run_certificate_local_relational_overlay_sequence_v144r1=run_certified_memoized_planner_sequence_v154,
)
_BASE_OCCURRENCE = _clone(v149.build_cross_domain_relational_factor_bank_occurrence_v149, _OCCURRENCE_GLOBALS)


def build_novel_signature_occurrence_v158(config, *, family, seed, episode_indices, bank_raw, verification_raw, classifier_receipt_raw):
    classifier = _verify_classifier(classifier_receipt_raw)
    execution_config = copy.deepcopy(config)
    execution_config["_v158_classifier_receipt_hex"] = classifier_receipt_raw.hex()
    base = _BASE_OCCURRENCE(execution_config, family=family, seed=seed, episode_indices=episode_indices, bank_raw=bank_raw, verification_raw=verification_raw)
    adapter = _BUILDERS[family](seed, execution_config)
    signature = anonymous_initial_action_support_signature_v156(adapter)
    source_signatures = set(SOURCE_POSITIVE_SIGNATURES + SOURCE_FAILED_SIGNATURES)
    if signature in source_signatures:
        raise ValueError("V158 target exact signature was not fresh")
    selected, predicate_count = evaluate_classifier_expression_v158(classifier["selected_expression"], signature)
    legacy = legacy_acquisition.acquire_matched_anonymous_relational_factor_bank_arms_v148(adapter, bank_raw, verification_raw, execution_config)
    prior = base["anonymous_relational_factor_prior_acquisition"]
    strict = base["strict_no_prior_acquisition"]
    legacy_prior = legacy["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"]
    guard_reduction = legacy_prior["ground_support_labels"] - prior["ground_support_labels"]
    factor_reduction = strict["ground_support_labels"] - prior["ground_support_labels"]
    ood = build_nonrelational_ood_control_v154(execution_config, seed=seed + 5_000_000)
    prior_sequence = annotate_applicable_plan_mode_sequence_v157(base["anonymous_relational_factor_prior_owned_sequence"])
    strict_sequence = annotate_applicable_plan_mode_sequence_v157(base["strict_no_prior_owned_sequence"])
    sequences = (prior_sequence, strict_sequence)
    expected_selected = family == POSITIVE_FAMILY
    expected_mode = "DIRECT_GENERIC_FACTOR_PROGRAM" if expected_selected else "V115_MEMOIZED_COMPILED_PROGRAM"
    exact_fallback = (
        prior["source_v148_acquisition_id"] == legacy_prior["acquisition_id"] and prior["ground_support_labels"] == legacy_prior["ground_support_labels"] and prior["raw_transition_sha256"] == legacy_prior["raw_transition_sha256"]
    )
    accounting = {
        **base["accounting"],
        "legacy_path_first_prior_acquisition_labels": legacy_prior["ground_support_labels"],
        "labels_avoided_by_synthesized_classifier_vs_legacy_prior": guard_reduction,
        "labels_avoided_by_factor_prior_within_classifier_guarded_operator": factor_reduction,
        "nonrelational_ood_compatibility_observation_labels": ood["observation_batch_count"],
    }
    gate = {
        **base["registered_gate"],
        "classifier_receipt_frozen_before_target_outcomes": classifier["fresh_v158_target_outcomes_accessed"] is False,
        "target_exact_signature_absent_from_source_registry": signature not in source_signatures,
        "classifier_decision_matches_registered_source_label": selected is expected_selected,
        "exact_signature_registry_not_consulted": prior["exact_signature_registry_consulted"] is False,
        "positive_classifier_relation_coverage_noninferior": guard_reduction >= 0 if expected_selected else True,
        "fallback_classifier_selected_exact_path_first": exact_fallback if not expected_selected else True,
        "classifier_introduced_no_sample_regression": guard_reduction >= 0,
        "factor_prior_noninferior_within_same_classifier_policy": factor_reduction >= 0,
        "relation_template_selected_in_prior_arm": prior["relational_artifact_expression_selected_count"] > 0,
        "same_relation_available_in_strict_pool": strict["relational_artifact_expression_selected_count"] > 0,
        "applicable_plan_receipt_path_exercised_both_arms": all(sequence["exactly_one_registered_plan_mode_exercised"] for sequence in sequences),
        "registered_family_plan_mode_observed_both_arms": all(sequence["applicable_plan_receipt_mode"] == expected_mode for sequence in sequences),
        "all_executed_actions_have_v109_receipts": all(sequence["all_executed_actions_have_v109_receipts"] for sequence in sequences),
        "nonrelational_ood_rejected_before_bank_access": ood["operator_transfer_rejected_before_bank_access"] and ood["factor_bank_bytes_supplied_to_ood_control"] is False,
    }
    gate["passed"] = all(gate.values())
    legacy_summary = {key: legacy_prior[key] for key in ("acquisition_id", "ground_support_labels", "first_accepting_observation_label", "raw_transition_sha256", "relational_artifact_expression_selected_count")}
    payload = {
        **{key: value for key, value in base.items() if key not in {"occurrence_id", "anonymous_relational_factor_prior_owned_sequence", "strict_no_prior_owned_sequence", "registered_gate"}},
        "schema": "acfqp.novel_signature_occurrence.v158",
        "classifier_receipt_id": classifier["classifier_receipt_id"],
        "anonymous_relational_factor_prior_owned_sequence": prior_sequence,
        "strict_no_prior_owned_sequence": strict_sequence,
        "legacy_path_first_prior_acquisition_summary": legacy_summary,
        "nonrelational_ood_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "selected_predicate_match_count": predicate_count,
        "guard_sample_reduction_vs_legacy_prior": guard_reduction,
        "factor_prior_sample_reduction_within_guarded_operator": factor_reduction,
        "applicable_plan_receipt_mode": expected_mode,
        "sample_tax_guard_claim_scope": "ONLY_THE_PREREGISTERED_V158_NOVEL_SIGNATURE_COHORT",
        "classifier_is_planning_or_certificate_authority": False,
        "v156_failure_and_v157_success_preserved": True,
    }
    return {**payload, "occurrence_id": domains.extension_content_id_v158(domains.CONSTRUCTION_K7_OCCURRENCE_V158_DOMAIN, payload)}


def _target(args):
    config = args[0]
    return build_novel_signature_occurrence_v158(config, family=args[1], seed=args[2], episode_indices=args[3], bank_raw=args[4], verification_raw=args[5], classifier_receipt_raw=bytes.fromhex(config["_v158_classifier_receipt_hex"]))


_CAMPAIGN_GLOBALS = dict(v149.__dict__)
_CAMPAIGN_GLOBALS.update(TARGET_FAMILIES=TARGET_FAMILIES, _target=_target)
_BASE_CAMPAIGN = _clone(v149.build_cross_domain_relational_factor_bank_campaign_document_v149, _CAMPAIGN_GLOBALS)


def build_novel_signature_campaign_document_v158(config, *, preregistration_id, bank_raw, verification_raw, classifier_receipt_raw):
    classifier = _verify_classifier(classifier_receipt_raw)
    execution_config = copy.deepcopy(config)
    execution_config["_v158_classifier_receipt_hex"] = classifier_receipt_raw.hex()
    base = _BASE_CAMPAIGN(execution_config, preregistration_id=preregistration_id, bank_raw=bank_raw, verification_raw=verification_raw)
    positive_rows = [row for row in base["target_occurrences"] if row["target_family"] == POSITIVE_FAMILY]
    fallback_rows = [row for row in base["target_occurrences"] if row["target_family"] == FALLBACK_FAMILY]
    guard_reduction = sum(row["guard_sample_reduction_vs_legacy_prior"] for row in base["target_occurrences"])
    factor_reduction = sum(row["factor_prior_sample_reduction_within_guarded_operator"] for row in base["target_occurrences"])
    positive_reduction = sum(row["guard_sample_reduction_vs_legacy_prior"] for row in positive_rows)
    fallback_reduction = sum(row["guard_sample_reduction_vs_legacy_prior"] for row in fallback_rows)
    modes = {row["applicable_plan_receipt_mode"] for row in base["target_occurrences"]}
    gate = {
        **base["registered_gate"],
        "classifier_receipt_id": classifier["classifier_receipt_id"],
        "aggregate_guard_sample_reduction_vs_legacy_prior": guard_reduction,
        "positive_classifier_cohort_guard_reduction": positive_reduction,
        "fallback_classifier_cohort_guard_reduction": fallback_reduction,
        "aggregate_factor_prior_reduction_within_guarded_operator": factor_reduction,
        "positive_classifier_relation_coverage_positive_in_aggregate": positive_reduction > 0,
        "fallback_classifier_zero_regression_everywhere": all(row["guard_sample_reduction_vs_legacy_prior"] == 0 for row in fallback_rows),
        "classifier_noninferior_everywhere": all(row["guard_sample_reduction_vs_legacy_prior"] >= 0 for row in base["target_occurrences"]),
        "factor_prior_noninferior_everywhere": all(row["factor_prior_sample_reduction_within_guarded_operator"] >= 0 for row in base["target_occurrences"]),
        "factor_prior_positive_in_aggregate": factor_reduction > 0,
        "all_target_exact_signatures_novel": all(row["registered_gate"]["target_exact_signature_absent_from_source_registry"] for row in base["target_occurrences"]),
        "both_classifier_sides_observed": bool(positive_rows) and bool(fallback_rows),
        "exact_signature_registry_absent_everywhere": all(row["registered_gate"]["exact_signature_registry_not_consulted"] for row in base["target_occurrences"]),
        "applicable_plan_receipt_path_exercised_everywhere": all(row["registered_gate"]["applicable_plan_receipt_path_exercised_both_arms"] for row in base["target_occurrences"]),
        "both_registered_plan_modes_observed": modes == {"DIRECT_GENERIC_FACTOR_PROGRAM", "V115_MEMOIZED_COMPILED_PROGRAM"},
        "nonrelational_ood_rejected_everywhere": all(row["registered_gate"]["nonrelational_ood_rejected_before_bank_access"] for row in base["target_occurrences"]),
    }
    gate["passed"] = base["registered_gate"]["passed"] and all(gate[key] for key in ("positive_classifier_relation_coverage_positive_in_aggregate", "fallback_classifier_zero_regression_everywhere", "classifier_noninferior_everywhere", "factor_prior_noninferior_everywhere", "factor_prior_positive_in_aggregate", "all_target_exact_signatures_novel", "both_classifier_sides_observed", "exact_signature_registry_absent_everywhere", "applicable_plan_receipt_path_exercised_everywhere", "both_registered_plan_modes_observed", "nonrelational_ood_rejected_everywhere"))
    payload = {
        **{key: value for key, value in base.items() if key != "campaign_id"},
        "schema": "acfqp.novel_signature_campaign.v158",
        "classifier_receipt_id": classifier["classifier_receipt_id"],
        "registered_gate": gate,
        "grammar_synthesized_classifier_novel_signature_transfer_observed": gate["passed"],
        "sample_tax_reduction_claim_scope": "ONLY_THE_PREREGISTERED_V158_NOVEL_SIGNATURE_COHORT",
        "classifier_is_model_planning_or_certificate_authority": False,
        "complete_world_model_synthesized": False,
    }
    return {**payload, "campaign_id": domains.extension_content_id_v158(domains.CONSTRUCTION_K7_CAMPAIGN_V158_DOMAIN, payload)}


__all__ = ("FALLBACK_FAMILY", "POSITIVE_FAMILY", "build_novel_signature_campaign_document_v158", "build_novel_signature_occurrence_v158", "novel_signature_campaign_config_v158")
