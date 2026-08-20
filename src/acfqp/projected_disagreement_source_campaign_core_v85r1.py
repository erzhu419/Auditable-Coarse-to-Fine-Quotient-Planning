"""Self-contained V85r1 successor around the frozen V85 acquisition core."""

from __future__ import annotations

from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v85r1 as domains
from acfqp.projected_disagreement_source_campaign_core_v85 import (
    build_projected_disagreement_source_campaign_document_v85,
)


class ProjectedDisagreementSourceCampaignCoreV85R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ProjectedDisagreementSourceCampaignCoreV85R1Error(message)


def build_projected_disagreement_source_campaign_document_v85r1(
    config: Mapping[str, Any],
    preregistration_id: str,
    v84_failed_campaign_id: str,
    v85_pre_outcome_failure_id: str,
    self_contained_template_library_id: str,
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    template_library: Mapping[str, Any],
    offline_template_source_labels: int,
) -> dict[str, Any]:
    inherited = build_projected_disagreement_source_campaign_document_v85(
        config,
        preregistration_id,
        v84_failed_campaign_id,
        factor_library,
        residual_library,
        template_library,
        offline_template_source_labels,
    )
    inherited.pop("campaign_id")
    if (
        inherited.get("schema") != "acfqp.projected_disagreement_source_campaign.v85"
        or inherited.get("preregistration_id") != preregistration_id
        or inherited.get("v84_failed_campaign_id") != v84_failed_campaign_id
        or inherited.get("target_execution_performed") is not False
        or inherited.get("official_execution_allowed") is not False
    ):
        _fail("V85r1 inherited source campaign boundary changed")
    payload = {
        **inherited,
        "schema": "acfqp.projected_disagreement_source_campaign.v85r1",
        "v85_pre_outcome_failure_id": v85_pre_outcome_failure_id,
        "self_contained_template_library_id": self_contained_template_library_id,
        "v85_member_content_domain_reused_without_v85_outcome_reuse": True,
        "fresh_v85r1_member_outcomes_only": True,
        "predecessor_producer_dereference_used": False,
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v85r1(
            domains.CONSTRUCTION_K7_PROJECTED_DISAGREEMENT_CAMPAIGN_V85R1_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_projected_disagreement_source_campaign_document_v85r1",)
