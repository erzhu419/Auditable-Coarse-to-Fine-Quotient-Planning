"""V156 mixed-family evaluation of an anonymous structural-margin guard."""

from __future__ import annotations

import copy
import hashlib
from types import FunctionType

from acfqp import anonymous_relational_factor_bank_acquisition_v148 as legacy_acquisition
from acfqp import construction_k7_domain_registry_extension_v156 as domains
from acfqp import cross_domain_relational_factor_bank_campaign_core_v149 as v149
from acfqp.certified_memoized_planner_sequence_v154 import run_certified_memoized_planner_sequence_v154
from acfqp.generic_quaternary_relation_workflow_adapter_v153 import (
    FAMILY as POSITIVE_FAMILY,
    build_quaternary_relation_workflow_adapter_v153,
)
from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    FAMILY as FALLBACK_FAMILY,
    build_relation_fanout_routing_adapter_v154,
    relation_fanout_routing_config_v154,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.relation_coverage_cross_structure_campaign_core_v154 import build_nonrelational_ood_control_v154
from acfqp.structural_margin_guarded_acquisition_operator_v156 import acquire_matched_structural_margin_guarded_arms_v156
from acfqp.structural_margin_query_guard_receipt_v156 import (
    EXPECTED_CANONICAL_BYTE_COUNT as GUARD_RECEIPT_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as GUARD_RECEIPT_SHA256,
    GUARD_RECEIPT_ID,
)


TARGET_FAMILIES = (POSITIVE_FAMILY, FALLBACK_FAMILY)
_BUILDERS = {
    POSITIVE_FAMILY: build_quaternary_relation_workflow_adapter_v153,
    FALLBACK_FAMILY: build_relation_fanout_routing_adapter_v154,
}


def structural_margin_campaign_config_v156():
    config = relation_fanout_routing_config_v154()
    config["families"][POSITIVE_FAMILY] = {"stage_count": 5, "maximum_acquisition_labels": 1_536}
    config["families"][FALLBACK_FAMILY]["maximum_acquisition_labels"] = 1_536
    return config


def _clone(function, namespace):
    clone = FunctionType(function.__code__, namespace, name=function.__name__, argdefs=function.__defaults__, closure=function.__closure__)
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def _verify_guard(raw: bytes):
    document = loads_canonical_json(raw)
    if (
        canonical_json_bytes(document) != raw
        or len(raw) != GUARD_RECEIPT_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != GUARD_RECEIPT_SHA256
        or document.get("guard_receipt_id") != GUARD_RECEIPT_ID
        or document.get("guard_frozen_before_v156_target_outcomes") is not True
        or document.get("selection_rule", {}).get("exact_signature_registry_consulted") is not False
    ):
        raise ValueError("V156 guard receipt changed")
    return document


_OCCURRENCE_GLOBALS = dict(v149.__dict__)
_OCCURRENCE_GLOBALS.update(
    _BUILDERS=_BUILDERS,
    acquire_matched_anonymous_relational_factor_bank_arms_v148=acquire_matched_structural_margin_guarded_arms_v156,
    run_certificate_local_relational_overlay_sequence_v144r1=run_certified_memoized_planner_sequence_v154,
)
_BASE_OCCURRENCE = _clone(v149.build_cross_domain_relational_factor_bank_occurrence_v149, _OCCURRENCE_GLOBALS)


def build_structural_margin_guarded_occurrence_v156(config, *, family, seed, episode_indices, bank_raw, verification_raw, guard_receipt_raw):
    guard = _verify_guard(guard_receipt_raw)
    execution_config = copy.deepcopy(config)
    execution_config["_v156_guard_receipt_hex"] = guard_receipt_raw.hex()
    base = _BASE_OCCURRENCE(
        execution_config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
    )
    adapter = _BUILDERS[family](seed, execution_config)
    legacy = legacy_acquisition.acquire_matched_anonymous_relational_factor_bank_arms_v148(adapter, bank_raw, verification_raw, execution_config)
    prior = base["anonymous_relational_factor_prior_acquisition"]
    strict = base["strict_no_prior_acquisition"]
    legacy_prior = legacy["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"]
    guard_reduction = legacy_prior["ground_support_labels"] - prior["ground_support_labels"]
    factor_reduction = strict["ground_support_labels"] - prior["ground_support_labels"]
    ood = build_nonrelational_ood_control_v154(execution_config, seed=seed + 4_000_000)
    sequences = (base["anonymous_relational_factor_prior_owned_sequence"], base["strict_no_prior_owned_sequence"])
    expected_relation_decision = family == POSITIVE_FAMILY
    exact_fallback = (
        prior["guard_decision"] == "PATH_FIRST_SAFE_FALLBACK"
        and prior["source_v148_acquisition_id"] == legacy_prior["acquisition_id"]
        and prior["ground_support_labels"] == legacy_prior["ground_support_labels"]
        and prior["raw_transition_sha256"] == legacy_prior["raw_transition_sha256"]
    )
    accounting = {
        **base["accounting"],
        "legacy_path_first_prior_acquisition_labels": legacy_prior["ground_support_labels"],
        "labels_avoided_by_structural_margin_guard_vs_legacy_prior": guard_reduction,
        "labels_avoided_by_factor_prior_within_margin_guarded_operator": factor_reduction,
        "nonrelational_ood_compatibility_observation_labels": ood["observation_batch_count"],
    }
    gate = {
        **base["registered_gate"],
        "guard_receipt_frozen_before_target_outcomes": guard["guard_frozen_before_v156_target_outcomes"],
        "exact_signature_registry_not_consulted": prior["exact_signature_registry_consulted"] is False,
        "anonymous_margin_decision_matches_registered_family_cohort": (prior["guard_decision"] == "RELATION_COVERAGE") is expected_relation_decision,
        "positive_margin_relation_coverage_noninferior": guard_reduction >= 0 if expected_relation_decision else True,
        "fallback_margin_selected_exact_path_first": exact_fallback if not expected_relation_decision else True,
        "guard_introduced_no_sample_regression": guard_reduction >= 0,
        "factor_prior_noninferior_within_same_guarded_policy": factor_reduction >= 0,
        "relation_template_selected_in_prior_arm": prior["relational_artifact_expression_selected_count"] > 0,
        "same_relation_available_in_strict_pool": strict["relational_artifact_expression_selected_count"] > 0,
        "v115_memoized_plan_receipt_consumed_both_arms": all(sequence["v115_memoized_compiled_program_plan_receipts_consumed"] for sequence in sequences),
        "nonrelational_ood_rejected_before_bank_access": ood["operator_transfer_rejected_before_bank_access"] and ood["factor_bank_bytes_supplied_to_ood_control"] is False,
        "v154_failed_identity_preserved": guard["v154_failed_identity_preserved"],
    }
    gate["passed"] = all(gate.values())
    legacy_summary = {
        "acquisition_id": legacy_prior["acquisition_id"],
        "ground_support_labels": legacy_prior["ground_support_labels"],
        "first_accepting_observation_label": legacy_prior["first_accepting_observation_label"],
        "raw_transition_sha256": legacy_prior["raw_transition_sha256"],
        "relational_artifact_expression_selected_count": legacy_prior["relational_artifact_expression_selected_count"],
    }
    payload = {
        **{key: value for key, value in base.items() if key != "occurrence_id"},
        "schema": "acfqp.structural_margin_guarded_occurrence.v156",
        "guard_receipt_id": guard["guard_receipt_id"],
        "legacy_path_first_prior_acquisition_summary": legacy_summary,
        "nonrelational_ood_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "guard_sample_reduction_vs_legacy_prior": guard_reduction,
        "factor_prior_sample_reduction_within_guarded_operator": factor_reduction,
        "registered_source_label": "POSITIVE_RELATION_COVERAGE" if expected_relation_decision else "FAILED_RELATION_COVERAGE_SAFE_FALLBACK",
        "sample_tax_guard_claim_scope": "ONLY_THE_PREREGISTERED_V156_TWO_FAMILY_MARGIN_COHORT",
        "guard_is_planning_or_certificate_authority": False,
        "v153_v154_v155_evidence_preserved": True,
    }
    return {**payload, "occurrence_id": domains.extension_content_id_v156(domains.CONSTRUCTION_K7_OCCURRENCE_V156_DOMAIN, payload)}


def _target(args):
    config = args[0]
    return build_structural_margin_guarded_occurrence_v156(
        config,
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        guard_receipt_raw=bytes.fromhex(config["_v156_guard_receipt_hex"]),
    )


_CAMPAIGN_GLOBALS = dict(v149.__dict__)
_CAMPAIGN_GLOBALS.update(TARGET_FAMILIES=TARGET_FAMILIES, _target=_target)
_BASE_CAMPAIGN = _clone(v149.build_cross_domain_relational_factor_bank_campaign_document_v149, _CAMPAIGN_GLOBALS)


def build_structural_margin_guarded_campaign_document_v156(config, *, preregistration_id, bank_raw, verification_raw, guard_receipt_raw):
    guard = _verify_guard(guard_receipt_raw)
    execution_config = copy.deepcopy(config)
    execution_config["_v156_guard_receipt_hex"] = guard_receipt_raw.hex()
    base = _BASE_CAMPAIGN(execution_config, preregistration_id=preregistration_id, bank_raw=bank_raw, verification_raw=verification_raw)
    positive_rows = [row for row in base["target_occurrences"] if row["target_family"] == POSITIVE_FAMILY]
    fallback_rows = [row for row in base["target_occurrences"] if row["target_family"] == FALLBACK_FAMILY]
    guard_reduction = sum(row["guard_sample_reduction_vs_legacy_prior"] for row in base["target_occurrences"])
    factor_reduction = sum(row["factor_prior_sample_reduction_within_guarded_operator"] for row in base["target_occurrences"])
    positive_reduction = sum(row["guard_sample_reduction_vs_legacy_prior"] for row in positive_rows)
    fallback_reduction = sum(row["guard_sample_reduction_vs_legacy_prior"] for row in fallback_rows)
    gate = {
        **base["registered_gate"],
        "guard_receipt_id": guard["guard_receipt_id"],
        "aggregate_guard_sample_reduction_vs_legacy_prior": guard_reduction,
        "positive_margin_cohort_guard_reduction": positive_reduction,
        "fallback_margin_cohort_guard_reduction": fallback_reduction,
        "aggregate_factor_prior_reduction_within_guarded_operator": factor_reduction,
        "positive_margin_relation_coverage_positive_in_aggregate": positive_reduction > 0,
        "fallback_margin_zero_regression_everywhere": all(row["guard_sample_reduction_vs_legacy_prior"] == 0 for row in fallback_rows),
        "guard_noninferior_everywhere": all(row["guard_sample_reduction_vs_legacy_prior"] >= 0 for row in base["target_occurrences"]),
        "factor_prior_noninferior_everywhere": all(row["factor_prior_sample_reduction_within_guarded_operator"] >= 0 for row in base["target_occurrences"]),
        "factor_prior_positive_in_aggregate": factor_reduction > 0,
        "both_margin_sides_observed": bool(positive_rows) and bool(fallback_rows),
        "exact_signature_registry_absent_everywhere": all(row["registered_gate"]["exact_signature_registry_not_consulted"] for row in base["target_occurrences"]),
        "memoized_plan_receipt_consumed_everywhere": all(row["registered_gate"]["v115_memoized_plan_receipt_consumed_both_arms"] for row in base["target_occurrences"]),
        "nonrelational_ood_rejected_everywhere": all(row["registered_gate"]["nonrelational_ood_rejected_before_bank_access"] for row in base["target_occurrences"]),
        "v154_failed_identity_preserved": True,
    }
    gate["passed"] = (
        base["registered_gate"]["passed"]
        and gate["positive_margin_relation_coverage_positive_in_aggregate"]
        and gate["fallback_margin_zero_regression_everywhere"]
        and gate["guard_noninferior_everywhere"]
        and gate["factor_prior_noninferior_everywhere"]
        and gate["factor_prior_positive_in_aggregate"]
        and gate["both_margin_sides_observed"]
        and gate["exact_signature_registry_absent_everywhere"]
        and gate["memoized_plan_receipt_consumed_everywhere"]
        and gate["nonrelational_ood_rejected_everywhere"]
    )
    payload = {
        **{key: value for key, value in base.items() if key != "campaign_id"},
        "schema": "acfqp.structural_margin_guarded_campaign.v156",
        "guard_receipt_id": guard["guard_receipt_id"],
        "registered_gate": gate,
        "structural_margin_guard_cross_family_nonregression_and_gain_observed": gate["passed"],
        "sample_tax_reduction_claim_scope": "ONLY_THE_PREREGISTERED_V156_TWO_FAMILY_MARGIN_COHORT",
        "guard_is_model_planning_or_certificate_authority": False,
        "complete_world_model_synthesized": False,
    }
    return {**payload, "campaign_id": domains.extension_content_id_v156(domains.CONSTRUCTION_K7_CAMPAIGN_V156_DOMAIN, payload)}


__all__ = (
    "FALLBACK_FAMILY",
    "POSITIVE_FAMILY",
    "TARGET_FAMILIES",
    "build_structural_margin_guarded_campaign_document_v156",
    "build_structural_margin_guarded_occurrence_v156",
    "structural_margin_campaign_config_v156",
)
