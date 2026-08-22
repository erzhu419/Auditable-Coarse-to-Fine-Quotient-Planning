"""V153 acquisition-operator evaluation with abstract planning and certification."""

from __future__ import annotations

import copy
import hashlib
from types import FunctionType

from acfqp import anonymous_relational_factor_bank_acquisition_v148 as v148_acquisition
from acfqp import construction_k7_domain_registry_extension_v153 as domains
from acfqp import cross_domain_relational_factor_bank_campaign_core_v149 as v149
from acfqp.certified_planner_abstention_sequence_v150 import run_certified_planner_abstention_sequence_v150
from acfqp.generic_quaternary_relation_workflow_adapter_v153 import FAMILY, build_quaternary_relation_workflow_adapter_v153
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.relation_coverage_acquisition_operator_v153 import acquire_matched_relation_coverage_arms_v153
from acfqp.relation_coverage_operator_receipt_v153 import EXPECTED_CANONICAL_BYTE_COUNT as RECEIPT_BYTE_COUNT, EXPECTED_CANONICAL_SHA256 as RECEIPT_SHA256, OPERATOR_RECEIPT_ID


TARGET_FAMILIES = (FAMILY,)


def _clone(function, namespace):
    clone = FunctionType(function.__code__, namespace, name=function.__name__, argdefs=function.__defaults__, closure=function.__closure__)
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def _verify_receipt(raw: bytes):
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw or len(raw) != RECEIPT_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != RECEIPT_SHA256 or document.get("operator_receipt_id") != OPERATOR_RECEIPT_ID or document.get("operator_extracted_before_v153_outcomes") is not True or document.get("operator", {}).get("future_target_outcomes_accessed") is not False:
        raise ValueError("V153 operator receipt changed")
    return document


_OCCURRENCE_GLOBALS = dict(v149.__dict__)
_OCCURRENCE_GLOBALS.update(
    _BUILDERS={FAMILY: build_quaternary_relation_workflow_adapter_v153},
    acquire_matched_anonymous_relational_factor_bank_arms_v148=acquire_matched_relation_coverage_arms_v153,
    run_certificate_local_relational_overlay_sequence_v144r1=run_certified_planner_abstention_sequence_v150,
)
_BASE_OCCURRENCE = _clone(v149.build_cross_domain_relational_factor_bank_occurrence_v149, _OCCURRENCE_GLOBALS)


def build_relation_coverage_planning_occurrence_v153(config, *, family, seed, episode_indices, bank_raw, verification_raw, operator_receipt_raw):
    receipt = _verify_receipt(operator_receipt_raw)
    base = _BASE_OCCURRENCE(config, family=family, seed=seed, episode_indices=episode_indices, bank_raw=bank_raw, verification_raw=verification_raw)
    adapter = build_quaternary_relation_workflow_adapter_v153(seed, config)
    legacy = v148_acquisition.acquire_matched_anonymous_relational_factor_bank_arms_v148(adapter, bank_raw, verification_raw, config)
    prior = base["anonymous_relational_factor_prior_acquisition"]
    strict = base["strict_no_prior_acquisition"]
    legacy_prior = legacy["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"]
    operator_reduction = legacy_prior["ground_support_labels"] - prior["ground_support_labels"]
    prior_reduction = strict["ground_support_labels"] - prior["ground_support_labels"]
    accounting = {
        **base["accounting"],
        "legacy_path_first_prior_acquisition_labels": legacy_prior["ground_support_labels"],
        "labels_avoided_by_relation_coverage_operator_vs_legacy_prior": operator_reduction,
        "labels_avoided_by_factor_prior_within_same_adaptive_operator": prior_reduction,
    }
    gate = {
        **base["registered_gate"],
        "operator_receipt_frozen_before_target_outcomes": receipt["operator_extracted_before_v153_outcomes"],
        "adaptive_operator_reduces_labels_vs_legacy_path_first_prior": operator_reduction > 0,
        "factor_prior_reduces_labels_within_same_adaptive_operator": prior_reduction > 0,
        "adaptive_operator_reaches_accepting_observation_before_legacy": prior["first_accepting_observation_label"] < legacy_prior["first_accepting_observation_label"],
        "four_key_relation_instantiated_and_selected": prior["relational_artifact_expression_selected_count"] > 0,
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
        "schema": "acfqp.relation_coverage_planning_occurrence.v153",
        "operator_receipt_id": receipt["operator_receipt_id"],
        "legacy_path_first_prior_acquisition_summary": legacy_summary,
        "accounting": accounting,
        "registered_gate": gate,
        "operator_sample_reduction_vs_legacy_prior": operator_reduction,
        "factor_prior_sample_reduction_within_adaptive_operator": prior_reduction,
        "sample_tax_operator_claim_scope": "ONLY_THE_PREREGISTERED_RELATION_KEYED_WORKFLOW_FAMILY",
        "operator_is_planning_or_certificate_authority": False,
        "v151_v152_evidence_preserved": True,
    }
    return {**payload, "occurrence_id": domains.extension_content_id_v153(domains.CONSTRUCTION_K7_OCCURRENCE_V153_DOMAIN, payload)}


def _target(args):
    config = args[0]
    return build_relation_coverage_planning_occurrence_v153(
        config,
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        operator_receipt_raw=bytes.fromhex(config["_v153_operator_receipt_hex"]),
    )


_CAMPAIGN_GLOBALS = dict(v149.__dict__)
_CAMPAIGN_GLOBALS.update(TARGET_FAMILIES=TARGET_FAMILIES, _target=_target)
_BASE_CAMPAIGN = _clone(v149.build_cross_domain_relational_factor_bank_campaign_document_v149, _CAMPAIGN_GLOBALS)


def build_relation_coverage_planning_campaign_document_v153(config, *, preregistration_id, bank_raw, verification_raw, operator_receipt_raw):
    receipt = _verify_receipt(operator_receipt_raw)
    execution_config = copy.deepcopy(config)
    execution_config["_v153_operator_receipt_hex"] = operator_receipt_raw.hex()
    base = _BASE_CAMPAIGN(execution_config, preregistration_id=preregistration_id, bank_raw=bank_raw, verification_raw=verification_raw)
    operator_reduction = sum(row["operator_sample_reduction_vs_legacy_prior"] for row in base["target_occurrences"])
    prior_reduction = sum(row["factor_prior_sample_reduction_within_adaptive_operator"] for row in base["target_occurrences"])
    gate = {
        **base["registered_gate"],
        "operator_receipt_id": receipt["operator_receipt_id"],
        "aggregate_operator_sample_reduction_vs_legacy_prior": operator_reduction,
        "aggregate_factor_prior_reduction_within_adaptive_operator": prior_reduction,
        "operator_positive_everywhere": all(row["operator_sample_reduction_vs_legacy_prior"] > 0 for row in base["target_occurrences"]),
        "factor_prior_positive_within_operator_everywhere": all(row["factor_prior_sample_reduction_within_adaptive_operator"] > 0 for row in base["target_occurrences"]),
    }
    gate["passed"] = base["registered_gate"]["passed"] and gate["operator_positive_everywhere"] and gate["factor_prior_positive_within_operator_everywhere"]
    payload = {
        **{key: value for key, value in base.items() if key != "campaign_id"},
        "schema": "acfqp.relation_coverage_planning_campaign.v153",
        "operator_receipt_id": receipt["operator_receipt_id"],
        "registered_gate": gate,
        "sample_tax_reduction_operator_observed": gate["passed"],
        "sample_tax_reduction_claim_scope": "ONLY_THE_PREREGISTERED_V153_QUATERNARY_RELATION_COHORT",
        "operator_is_model_planning_or_certificate_authority": False,
        "complete_world_model_synthesized": False,
    }
    return {**payload, "campaign_id": domains.extension_content_id_v153(domains.CONSTRUCTION_K7_CAMPAIGN_V153_DOMAIN, payload)}


__all__ = ("build_relation_coverage_planning_campaign_document_v153", "build_relation_coverage_planning_occurrence_v153")
