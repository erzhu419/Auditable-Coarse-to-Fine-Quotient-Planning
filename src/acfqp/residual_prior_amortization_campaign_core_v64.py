"""V64 wrapper around the frozen V63r1 matched acquisition procedure."""

from __future__ import annotations

from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v64 as domains
from acfqp.total_residual_sample_tax_campaign_core_v63r1 import (
    build_total_residual_sample_tax_campaign_document_v63r1,
)


class ResidualPriorAmortizationCampaignCoreV64Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ResidualPriorAmortizationCampaignCoreV64Error(message)


def build_residual_prior_amortization_campaign_document_v64(
    config: Mapping[str, Any],
    preregistration_id: str,
    failed_v63_id: str,
    factor_library: Mapping[str, Any],
    residual_library_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    procedure = build_total_residual_sample_tax_campaign_document_v63r1(
        config,
        preregistration_id,
        failed_v63_id,
        factor_library,
        residual_library_artifact,
    )
    summary = procedure["sample_tax"]
    prior_lifetime = summary["observed_prior_lifetime_labels_including_offline"]
    strict_lifetime = summary["observed_strict_lifetime_labels"]
    if prior_lifetime > strict_lifetime:
        _fail("V64 registered offline-tax amortization Gate failed")
    payload = {
        "schema": "acfqp.residual_prior_amortization_campaign.v64",
        "preregistration_id": preregistration_id,
        "v63r1_procedure_output": procedure,
        "v63r1_frozen_campaign_id": "1e9f4fbdb13e9c7c477ec213fec3d0cda09d4b0af7698d8c7e774ebdbf320db8",
        "v63r1_frozen_verification_id": "9dcfc9aa1e363d13ea6f32f0208048657acd4428e6c65d48a3c434b45e531b2c",
        "target_occurrence_count": summary["target_occurrence_count"],
        "offline_development_labels": summary["offline_development_labels"],
        "prior_target_residual_labels": summary[
            "prior_target_residual_acquisition_labels"
        ],
        "strict_target_residual_labels": summary[
            "strict_target_residual_acquisition_labels"
        ],
        "prior_lifetime_labels_including_offline": prior_lifetime,
        "strict_lifetime_labels": strict_lifetime,
        "observed_lifetime_label_saving": strict_lifetime - prior_lifetime,
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
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v64(
            domains.CONSTRUCTION_K7_RESIDUAL_AMORTIZATION_CAMPAIGN_V64_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_residual_prior_amortization_campaign_document_v64",)
