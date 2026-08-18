"""Producer-free verification of V64 observed residual-prior amortization."""

from __future__ import annotations

import hashlib
import math
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v63r1 as procedure_domains
from acfqp import construction_k7_domain_registry_extension_v64 as domains
from acfqp.construction_k7_total_residual_sample_tax_independent_verifier_v63r1 import (
    reconstruct_total_residual_occurrences_v63r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


VERIFICATION_ID = "fe6b372c86255a7150b5321a394203607e78e1f333d238786a85f6e3b344a2bf"
EXPECTED_CANONICAL_BYTE_COUNT = 714
EXPECTED_CANONICAL_SHA256 = "cfb08891a206fe63340c36d6e4723666b1b3a059d53e122cade9f4bbe25616aa"
_PREREGISTRATION_ID = "00ce3d9d8979bb94c42378eb6acf0fbec0238f6eb34868cd3d7bc0df2dcd329c"
_FAILED_V63_ID = "716b0fba8968318c284a0840e2f109c861f819d5c52a177fdd41efee88c2fae0"
_V62_LIBRARY_ID = "26e5e031eb6b57e73253bc85bc3d0c372f6444248ad0c4e3343a01f43353b3d0"
_V63R1_CAMPAIGN_ID = "1e9f4fbdb13e9c7c477ec213fec3d0cda09d4b0af7698d8c7e774ebdbf320db8"
_V63R1_VERIFICATION_ID = "9dcfc9aa1e363d13ea6f32f0208048657acd4428e6c65d48a3c434b45e531b2c"


class ConstructionK7ResidualAmortizationIndependentVerifierV64Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ResidualAmortizationIndependentVerifierV64Error(message)


def _id(domain: str, document: dict[str, Any], key: str, function: Any) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if function(domain, payload) != document.get(key):
        _fail(f"V64 {key} changed")


def _verify_procedure(document: dict[str, Any]) -> dict[str, Any]:
    _id(
        procedure_domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_CAMPAIGN_V63R1_DOMAIN,
        document,
        "campaign_id",
        procedure_domains.extension_content_id_v63r1,
    )
    if (
        document.get("preregistration_id") != _PREREGISTRATION_ID
        or document.get("failed_v63_registered_failure_id") != _FAILED_V63_ID
        or document.get("v62_library_artifact_id") != _V62_LIBRARY_ID
    ):
        _fail("V64 embedded procedure predecessor changed")
    occurrences = document.get("occurrences")
    if type(occurrences) is not list or len(occurrences) != 72:
        _fail("V64 embedded procedure occurrence count changed")
    facts = reconstruct_total_residual_occurrences_v63r1(occurrences)
    prior = facts["prior_labels"]
    strict = facts["strict_labels"]
    reduction = strict - prior
    if reduction <= 0:
        _fail("V64 embedded target label reduction changed")
    offline = 204
    summary_payload = {
        "schema": "acfqp.total_residual_factor_sample_tax_summary.v63r1",
        "offline_development_labels": offline,
        "target_occurrence_count": facts["occurrence_count"],
        "prior_target_residual_acquisition_labels": prior,
        "strict_target_residual_acquisition_labels": strict,
        "target_residual_label_reduction": reduction,
        "observed_prior_lifetime_labels_including_offline": offline + prior,
        "observed_strict_lifetime_labels": strict,
        "offline_tax_amortized_within_registered_occurrences": offline + prior
        <= strict,
        "diagnostic_projected_break_even_occurrence_count": math.ceil(
            offline * facts["occurrence_count"] / reduction
        ),
        "diagnostic_projection_is_not_official_economics": True,
        "prior_proposal_count": facts["prior_proposal_count"],
        "strict_proposal_count": facts["strict_proposal_count"],
        "family_projections": facts["family_projections"],
        "only_switched_variable": "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH",
        "same_synthesizer_stop_confidence_and_totalization_rule": True,
        "official_break_even_claimed": False,
    }
    expected_summary = {
        **summary_payload,
        "sample_tax_id": procedure_domains.extension_content_id_v63r1(
            procedure_domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_SUMMARY_V63R1_DOMAIN,
            summary_payload,
        ),
    }
    if document.get("sample_tax") != expected_summary:
        _fail("V64 embedded sample-tax summary changed")
    expected_accounting = {
        "offline_development_labels": offline,
        "common_partial_acquisition_target_labels": facts[
            "common_partial_acquisition_labels"
        ],
        "prior_residual_acquisition_target_labels": prior,
        "strict_residual_acquisition_target_labels": strict,
        "full_safety_local_ground_support_labels": facts[
            "full_safety_local_labels"
        ],
        "execution_steps": facts["execution_steps"],
        "abstract_planning_compute_events": facts[
            "abstract_planning_compute_events"
        ],
        "all_axes_separate": True,
    }
    if document.get("accounting") != expected_accounting:
        _fail("V64 embedded accounting changed")
    locks = {
        "all_registered_occurrences_retained_including_abstentions": True,
        "fresh_held_out_outcome_execution_performed": True,
        "producer_free_verification_present": False,
        "all_ground_queries_followed_failed_certificates": True,
        "statistical_residual_proposal_used_as_safety_authority": False,
        "complete_residual_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    if any(document.get(key) != value for key, value in locks.items()):
        _fail("V64 embedded claim locks changed")
    return facts


def verify_residual_amortization_campaign_bytes_v64(raw: bytes) -> bytes:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V64 campaign bytes are not canonical")
    _id(
        domains.CONSTRUCTION_K7_RESIDUAL_AMORTIZATION_CAMPAIGN_V64_DOMAIN,
        document,
        "campaign_id",
        domains.extension_content_id_v64,
    )
    if document.get("preregistration_id") != _PREREGISTRATION_ID:
        _fail("V64 preregistration join changed")
    procedure = document.get("v63r1_procedure_output")
    if type(procedure) is not dict:
        _fail("V64 embedded procedure changed")
    facts = _verify_procedure(procedure)
    prior = facts["prior_labels"]
    strict = facts["strict_labels"]
    expected = {
        "v63r1_frozen_campaign_id": _V63R1_CAMPAIGN_ID,
        "v63r1_frozen_verification_id": _V63R1_VERIFICATION_ID,
        "target_occurrence_count": 72,
        "offline_development_labels": 204,
        "prior_target_residual_labels": prior,
        "strict_target_residual_labels": strict,
        "prior_lifetime_labels_including_offline": 204 + prior,
        "strict_lifetime_labels": strict,
        "observed_lifetime_label_saving": strict - (204 + prior),
        "offline_tax_amortized_on_fresh_registered_occurrences": True,
        "all_occurrences_retained": True,
        "same_v63r1_matched_procedure_reused_without_rule_change": True,
        "sample_labels_execution_steps_and_compute_axes_separate": True,
        "producer_free_verification_present": False,
        "statistical_residual_proposal_used_as_safety_authority": False,
        "complete_residual_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    if any(document.get(key) != value for key, value in expected.items()):
        _fail("V64 top-level amortization facts changed")
    if expected["observed_lifetime_label_saving"] < 0:
        _fail("V64 offline tax was not actually amortized")
    payload = {
        "schema": "acfqp.residual_prior_amortization_verification.v64",
        "campaign_id": document["campaign_id"],
        "occurrence_count": facts["occurrence_count"],
        "offline_development_labels": 204,
        "prior_target_residual_labels": prior,
        "strict_target_residual_labels": strict,
        "target_label_reduction_before_offline_tax": strict - prior,
        "observed_lifetime_label_saving_after_offline_tax": strict - (204 + prior),
        "prior_proposal_count": facts["prior_proposal_count"],
        "strict_proposal_count": facts["strict_proposal_count"],
        "all_occurrence_acquisitions_reconstructed": True,
        "producer_imported": False,
        "campaign_core_imported": False,
        "official_execution_allowed": False,
        "status": "PRODUCER_FREE_RESIDUAL_PRIOR_AMORTIZATION_VERIFIED",
    }
    verification = {
        **payload,
        "verification_id": domains.extension_content_id_v64(
            domains.CONSTRUCTION_K7_RESIDUAL_AMORTIZATION_VERIFICATION_V64_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V64 verification changed")
    return result


__all__ = ("verify_residual_amortization_campaign_bytes_v64",)
