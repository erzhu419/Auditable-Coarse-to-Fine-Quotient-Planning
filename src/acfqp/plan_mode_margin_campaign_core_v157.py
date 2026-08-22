"""Fresh successor to V156 with a domain-applicable plan receipt Gate."""

from __future__ import annotations

import copy
import hashlib
from types import FunctionType

from acfqp import construction_k7_domain_registry_extension_v157 as domains
from acfqp import cross_domain_relational_factor_bank_campaign_core_v149 as v149
from acfqp.applicable_plan_mode_sequence_v157 import annotate_applicable_plan_mode_sequence_v157
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.plan_mode_correction_receipt_v157 import (
    CORRECTION_RECEIPT_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as CORRECTION_RECEIPT_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as CORRECTION_RECEIPT_SHA256,
)
from acfqp.structural_margin_guarded_campaign_core_v156 import (
    FALLBACK_FAMILY,
    POSITIVE_FAMILY,
    build_structural_margin_guarded_occurrence_v156,
    structural_margin_campaign_config_v156,
)
from acfqp.structural_margin_query_guard_receipt_v156 import GUARD_RECEIPT_ID


TARGET_FAMILIES = (POSITIVE_FAMILY, FALLBACK_FAMILY)


def _clone(function, namespace):
    clone = FunctionType(function.__code__, namespace, name=function.__name__, argdefs=function.__defaults__, closure=function.__closure__)
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def _verify_correction(raw: bytes):
    document = loads_canonical_json(raw)
    if (
        canonical_json_bytes(document) != raw
        or len(raw) != CORRECTION_RECEIPT_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CORRECTION_RECEIPT_SHA256
        or document.get("correction_receipt_id") != CORRECTION_RECEIPT_ID
        or document.get("fresh_v157_target_outcomes_accessed") is not False
    ):
        raise ValueError("V157 correction receipt changed")
    return document


def build_plan_mode_margin_occurrence_v157(config, *, family, seed, episode_indices, bank_raw, verification_raw, guard_receipt_raw, correction_receipt_raw):
    correction = _verify_correction(correction_receipt_raw)
    base = build_structural_margin_guarded_occurrence_v156(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        guard_receipt_raw=guard_receipt_raw,
    )
    prior_sequence = annotate_applicable_plan_mode_sequence_v157(base["anonymous_relational_factor_prior_owned_sequence"])
    strict_sequence = annotate_applicable_plan_mode_sequence_v157(base["strict_no_prior_owned_sequence"])
    sequences = (prior_sequence, strict_sequence)
    expected_mode = "DIRECT_GENERIC_FACTOR_PROGRAM" if family == POSITIVE_FAMILY else "V115_MEMOIZED_COMPILED_PROGRAM"
    gate = {
        **{key: value for key, value in base["registered_gate"].items() if key not in {"passed", "v115_memoized_plan_receipt_consumed_both_arms"}},
        "correction_receipt_frozen_before_target_outcomes": correction["fresh_v157_target_outcomes_accessed"] is False,
        "applicable_plan_receipt_path_exercised_both_arms": all(sequence["exactly_one_registered_plan_mode_exercised"] for sequence in sequences),
        "registered_family_plan_mode_observed_both_arms": all(sequence["applicable_plan_receipt_mode"] == expected_mode for sequence in sequences),
        "every_emitted_v115_plan_revalidated_before_v109_receipt": all(sequence["every_emitted_v115_plan_revalidated_before_v109_execution_receipt"] for sequence in sequences),
        "direct_generic_plan_path_covered_by_v109_receipts": all(sequence["direct_generic_plan_path_covered_by_actual_v109_receipts"] for sequence in sequences),
        "all_executed_actions_have_v109_receipts": all(sequence["all_executed_actions_have_v109_receipts"] for sequence in sequences),
        "v156_failed_identity_preserved": correction["v156_failed_identity_preserved"],
    }
    gate["passed"] = all(gate.values())
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key
            not in {
                "schema",
                "occurrence_id",
                "anonymous_relational_factor_prior_owned_sequence",
                "strict_no_prior_owned_sequence",
                "registered_gate",
            }
        },
        "schema": "acfqp.plan_mode_margin_occurrence.v157",
        "correction_receipt_id": correction["correction_receipt_id"],
        "anonymous_relational_factor_prior_owned_sequence": prior_sequence,
        "strict_no_prior_owned_sequence": strict_sequence,
        "registered_gate": gate,
        "applicable_plan_receipt_mode": expected_mode,
        "v156_failure_preserved_not_reclassified": True,
        "sample_tax_guard_claim_scope": "ONLY_THE_PREREGISTERED_V157_TWO_FAMILY_PLAN_MODE_COHORT",
        "guard_is_planning_or_certificate_authority": False,
    }
    return {**payload, "occurrence_id": domains.extension_content_id_v157(domains.CONSTRUCTION_K7_OCCURRENCE_V157_DOMAIN, payload)}


def _target(args):
    config = args[0]
    return build_plan_mode_margin_occurrence_v157(
        config,
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        guard_receipt_raw=bytes.fromhex(config["_v156_guard_receipt_hex"]),
        correction_receipt_raw=bytes.fromhex(config["_v157_correction_receipt_hex"]),
    )


_CAMPAIGN_GLOBALS = dict(v149.__dict__)
_CAMPAIGN_GLOBALS.update(TARGET_FAMILIES=TARGET_FAMILIES, _target=_target)
_BASE_CAMPAIGN = _clone(v149.build_cross_domain_relational_factor_bank_campaign_document_v149, _CAMPAIGN_GLOBALS)


def build_plan_mode_margin_campaign_document_v157(config, *, preregistration_id, bank_raw, verification_raw, guard_receipt_raw, correction_receipt_raw):
    correction = _verify_correction(correction_receipt_raw)
    execution_config = copy.deepcopy(config)
    execution_config["_v156_guard_receipt_hex"] = guard_receipt_raw.hex()
    execution_config["_v157_correction_receipt_hex"] = correction_receipt_raw.hex()
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
        "guard_receipt_id": GUARD_RECEIPT_ID,
        "correction_receipt_id": correction["correction_receipt_id"],
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
        "applicable_plan_receipt_path_exercised_everywhere": all(row["registered_gate"]["applicable_plan_receipt_path_exercised_both_arms"] for row in base["target_occurrences"]),
        "both_registered_plan_modes_observed": modes == {"DIRECT_GENERIC_FACTOR_PROGRAM", "V115_MEMOIZED_COMPILED_PROGRAM"},
        "nonrelational_ood_rejected_everywhere": all(row["registered_gate"]["nonrelational_ood_rejected_before_bank_access"] for row in base["target_occurrences"]),
        "v156_failed_identity_preserved": True,
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
        and gate["applicable_plan_receipt_path_exercised_everywhere"]
        and gate["both_registered_plan_modes_observed"]
        and gate["nonrelational_ood_rejected_everywhere"]
    )
    payload = {
        **{key: value for key, value in base.items() if key != "campaign_id"},
        "schema": "acfqp.plan_mode_margin_campaign.v157",
        "guard_receipt_id": GUARD_RECEIPT_ID,
        "correction_receipt_id": correction["correction_receipt_id"],
        "registered_gate": gate,
        "plan_mode_corrected_structural_margin_evidence_observed": gate["passed"],
        "v156_failure_preserved_not_reclassified": True,
        "sample_tax_reduction_claim_scope": "ONLY_THE_PREREGISTERED_V157_TWO_FAMILY_PLAN_MODE_COHORT",
        "guard_is_model_planning_or_certificate_authority": False,
        "complete_world_model_synthesized": False,
    }
    return {**payload, "campaign_id": domains.extension_content_id_v157(domains.CONSTRUCTION_K7_CAMPAIGN_V157_DOMAIN, payload)}


__all__ = (
    "FALLBACK_FAMILY",
    "POSITIVE_FAMILY",
    "TARGET_FAMILIES",
    "build_plan_mode_margin_campaign_document_v157",
    "build_plan_mode_margin_occurrence_v157",
    "structural_margin_campaign_config_v156",
)
