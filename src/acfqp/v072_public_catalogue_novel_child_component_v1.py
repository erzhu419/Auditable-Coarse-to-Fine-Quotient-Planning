"""Typed V0-072 binding for public novel-child cardinality evidence.

This component consumes only an already-frozen public cardinality authority
and its separately implemented independent attestation.  It cannot open a
target observer, enumerate outcomes, inspect an environment law, or accept a
caller-provided row mapping/count.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import public_novel_child_cardinality_authority_v2 as authority_v2
from acfqp import (
    public_novel_child_cardinality_independent_verifier_v2
    as independent_v2,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_public_catalogue_novel_child_component_v1"
DOMAIN_TAG = "acfqp:v072-public-catalogue-novel-child-component:v1"


class V072PublicCatalogueNovelChildComponentInvariantViolation(ValueError):
    """The cardinality authority and independent attestation diverge."""


def _content_id(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        DOMAIN_TAG.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072PublicCatalogueNovelChildComponentInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class V072PublicCatalogueNovelChildComponentV1:
    """One public full-row-list authority plus independent replay proof."""

    cardinality_authority: (
        authority_v2.PublicNovelChildCardinalityAuthorityV2
    )
    independent_attestation: (
        independent_v2.IndependentNovelChildCardinalityAttestationV2
    )
    _component_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.cardinality_authority)
            is not authority_v2.PublicNovelChildCardinalityAuthorityV2
            or type(self.independent_attestation)
            is not (
                independent_v2
                .IndependentNovelChildCardinalityAttestationV2
            )
        ):
            raise V072PublicCatalogueNovelChildComponentInvariantViolation(
                "novel-child component requires the two exact V2 artifacts"
            )
        claimed = self.cardinality_authority
        evidence = claimed.cardinality_evidence
        attestation = self.independent_attestation
        authority_id = _cid(
            claimed.authority_id,
            "public cardinality authority",
        )
        attestation_id = _cid(
            attestation.attestation_id,
            "independent cardinality attestation",
        )
        _cid(evidence.evidence_id, "public cardinality evidence")
        if (
            attestation.authority_id != authority_id
            or attestation.parent_artifact_id
            != evidence.parent_artifact_id
            or attestation.closure_id != evidence.current_closure_id
            or attestation.selector_counterfactual_id
            != claimed.selector_counterfactual_id
            or attestation.context_id != evidence.context_id
            or attestation.round_index != evidence.round_index
            or attestation.exact_new_child_row_count
            != evidence.new_child_row_count
            or attestation.exact_cumulative_child_row_count
            != evidence.cumulative_child_row_count
            or attestation.exact_round_draw_upper
            != evidence.exact_round_draw_upper
            or attestation.exact_cumulative_draw_upper
            != evidence.cumulative_draw_upper
            or attestation.verification_result != "VALID"
            or evidence.new_child_row_count != len(
                evidence.rows_to_acquire
            )
            or evidence.cumulative_child_row_count
            != len(evidence.cumulative_rows)
            or evidence.environment_law_queries != 0
            or evidence.outcome_enumeration_calls != 0
            or evidence.new_draw_calls != 0
        ):
            raise V072PublicCatalogueNovelChildComponentInvariantViolation(
                "public cardinality authority and independent replay do not "
                "bind the same parent, closure, rows, and exact draw bounds"
            )
        canonical_json_bytes(claimed.to_document())
        canonical_json_bytes(attestation.to_document())
        object.__setattr__(
            self,
            "_component_id",
            _content_id(
                self._payload(
                    authority_id=authority_id,
                    attestation_id=attestation_id,
                )
            ),
        )

    def _payload(
        self,
        *,
        authority_id: str | None = None,
        attestation_id: str | None = None,
    ) -> dict[str, Any]:
        claimed = self.cardinality_authority
        evidence = claimed.cardinality_evidence
        return {
            "schema": (
                "acfqp.v072_public_catalogue_novel_child_component.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "cardinality_authority_id": (
                claimed.authority_id
                if authority_id is None
                else authority_id
            ),
            "cardinality_evidence_id": evidence.evidence_id,
            "independent_attestation_id": (
                self.independent_attestation.attestation_id
                if attestation_id is None
                else attestation_id
            ),
            "logical_occurrence_id": evidence.logical_occurrence_id,
            "context_id": evidence.context_id,
            "arm": evidence.arm,
            "model_id": evidence.model_id,
            "audit_id": evidence.audit_id,
            "frontier_id": evidence.frontier_id,
            "threshold_profile_id": evidence.threshold_profile_id,
            "parent_artifact_id": evidence.parent_artifact_id,
            "parent_row_binding_id": evidence.parent_row_binding_id,
            "parent_support_epoch_id": evidence.parent_support_epoch_id,
            "current_closure_id": evidence.current_closure_id,
            "selector_counterfactual_id": (
                claimed.selector_counterfactual_id
            ),
            "round_index": evidence.round_index,
            "new_child_row_count": evidence.new_child_row_count,
            "cumulative_child_row_count": (
                evidence.cumulative_child_row_count
            ),
            "exact_round_draw_upper": evidence.exact_round_draw_upper,
            "exact_cumulative_draw_upper": (
                evidence.cumulative_draw_upper
            ),
            "full_public_catalogue_row_list_bound": True,
            "independently_replayed": True,
            "caller_supplied_mapping": False,
            "caller_supplied_count": False,
            "observer_input_accepted": False,
            "environment_law_input_accepted": False,
            "outcome_input_accepted": False,
            "environment_law_queries": 0,
            "outcome_enumeration_calls": 0,
            "new_draw_calls": 0,
        }

    @property
    def component_id(self) -> str:
        return self._component_id

    @property
    def rows_to_acquire(
        self,
    ) -> tuple[authority_v2.PublicH1PhysicalRowV2, ...]:
        return self.cardinality_authority.rows_to_acquire

    @property
    def cumulative_rows(
        self,
    ) -> tuple[authority_v2.PublicH1PhysicalRowV2, ...]:
        return self.cardinality_authority.cumulative_rows

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "cardinality_authority": (
                self.cardinality_authority.to_document()
            ),
            "independent_attestation": (
                self.independent_attestation.to_document()
            ),
            "component_id": self.component_id,
        }


def bind_v072_public_catalogue_novel_child_component_v1(
    *,
    cardinality_authority: (
        authority_v2.PublicNovelChildCardinalityAuthorityV2
    ),
    independent_attestation: (
        independent_v2.IndependentNovelChildCardinalityAttestationV2
    ),
) -> V072PublicCatalogueNovelChildComponentV1:
    """Bind preverified public row evidence without opening its sources."""

    return V072PublicCatalogueNovelChildComponentV1(
        cardinality_authority,
        independent_attestation,
    )


__all__ = [
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V072PublicCatalogueNovelChildComponentInvariantViolation",
    "V072PublicCatalogueNovelChildComponentV1",
    "bind_v072_public_catalogue_novel_child_component_v1",
]
