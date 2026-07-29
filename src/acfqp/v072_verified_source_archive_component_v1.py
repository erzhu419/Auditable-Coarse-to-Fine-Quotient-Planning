"""Strict typed binding for the verified V0-072 source archive.

The component is deliberately a consumer of already-frozen evidence.  It
accepts exactly the production archive, its production replay verification,
and the separately implemented independent archive-transform attestation.
It does not accept a source campaign, rerun either verifier, open an observer,
or expose any target-observation entry point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import verified_source_acquisition_archive_v2 as archive_v2
from acfqp import (
    verified_source_acquisition_archive_independent_verifier_v2
    as independent_v2,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_verified_source_archive_component_v1"

DOMAIN_TAG = "acfqp:v072-verified-source-archive-component:v1"
ARCHIVE_DOCUMENT_DIGEST_TAG = (
    b"acfqp:v072-independent-archive-document:v2\x00"
)


class V072VerifiedSourceArchiveComponentInvariantViolation(ValueError):
    """The archive and its two verification authorities do not coincide."""


def _content_id(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        DOMAIN_TAG.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072VerifiedSourceArchiveComponentInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _archive_document_digest(
    value: archive_v2.VerifiedSourceAcquisitionArchiveV2,
) -> str:
    return hashlib.sha256(
        ARCHIVE_DOCUMENT_DIGEST_TAG
        + canonical_json_bytes(value.to_document())
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class V072VerifiedSourceArchiveComponentV1:
    """One exact archive bound to both production and independent replay."""

    archive: archive_v2.VerifiedSourceAcquisitionArchiveV2
    production_verification: (
        archive_v2.VerifiedSourceAcquisitionArchiveVerificationV2
    )
    independent_attestation: (
        independent_v2.IndependentSourceAcquisitionArchiveVerificationV2
    )
    _component_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.archive)
            is not archive_v2.VerifiedSourceAcquisitionArchiveV2
            or type(self.production_verification)
            is not (
                archive_v2.VerifiedSourceAcquisitionArchiveVerificationV2
            )
            or type(self.independent_attestation)
            is not (
                independent_v2
                .IndependentSourceAcquisitionArchiveVerificationV2
            )
        ):
            raise V072VerifiedSourceArchiveComponentInvariantViolation(
                "source component requires the three exact V2 artifact types"
            )

        source = self.archive
        production = self.production_verification
        independent = self.independent_attestation
        archive_id = _cid(source.archive_id, "source archive")
        production_id = _cid(
            production.verification_id,
            "production archive verification",
        )
        independent_id = _cid(
            independent.verification_id,
            "independent archive-transform verification",
        )
        expected_pair_count = len(source.adjacent_pairs)
        expected_trial_count = len(source.trials)
        expected_feature_count = len(source.consensus)

        if (
            production.archive_id != archive_id
            or production.replayed_archive_id != archive_id
            or independent.archive_id != archive_id
            or independent.independently_recomputed_archive_id != archive_id
            or production.source_campaign_id != source.source_campaign_id
            or independent.source_campaign_id != source.source_campaign_id
            or production.source_campaign_verification_id
            != source.source_campaign_verification_id
            or independent.source_campaign_verification_id
            != source.source_campaign_verification_id
            or production.registered_adjacent_pair_count
            != expected_pair_count
            or independent.registered_adjacent_pair_count
            != expected_pair_count
            or production.trial_count != expected_trial_count
            or independent.trial_count != expected_trial_count
            or production.feature_count != expected_feature_count
            or independent.feature_count != expected_feature_count
            or independent.archive_document_digest
            != _archive_document_digest(source)
            or source.source_campaign_same_implementation_verified is not True
            or source.independent_fraction_recurrence_verified is not True
            or source.independent_source_campaign_verifier_claimed is not False
            or source.source_frozen is not True
            or source.proposal_only is not True
            or source.may_certify is not False
            or production.same_implementation_archive_replay is not True
            or production.independent_fraction_recurrence_verified is not True
            or production.independent_source_campaign_verifier_claimed
            is not False
            or production.valid is not True
            or independent.independent_archive_transform_verified is not True
            or (
                independent
                .source_campaign_same_implementation_verification_consumed
                is not True
            )
            or independent.independent_source_campaign_verifier_claimed
            is not False
            or independent.source_campaign_verification_boundary
            != independent_v2.SOURCE_CAMPAIGN_VERIFICATION_BOUNDARY
            or independent.valid is not True
        ):
            raise V072VerifiedSourceArchiveComponentInvariantViolation(
                "archive, production replay, and independent transform "
                "attestation do not bind the same exact source evidence"
            )

        # Force all three complete content trees to be canonicalizable before
        # the compact component identity is frozen.
        canonical_json_bytes(source.to_document())
        canonical_json_bytes(production.to_document())
        canonical_json_bytes(independent.to_document())
        object.__setattr__(
            self,
            "_component_id",
            _content_id(
                self._payload(
                    archive_id=archive_id,
                    production_id=production_id,
                    independent_id=independent_id,
                )
            ),
        )

    def _payload(
        self,
        *,
        archive_id: str | None = None,
        production_id: str | None = None,
        independent_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_verified_source_archive_component.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "archive_id": self.archive.archive_id
            if archive_id is None
            else archive_id,
            "production_verification_id": (
                self.production_verification.verification_id
                if production_id is None
                else production_id
            ),
            "independent_archive_transform_attestation_id": (
                self.independent_attestation.verification_id
                if independent_id is None
                else independent_id
            ),
            "source_campaign_id": self.archive.source_campaign_id,
            "source_campaign_verification_id": (
                self.archive.source_campaign_verification_id
            ),
            "source_family_id": self.archive.source_family_id,
            "source_training_split_id": (
                self.archive.source_training_split_id
            ),
            "feature_schema_id": archive_v2.FEATURE_SCHEMA_ID,
            "registered_adjacent_pair_count": len(
                self.archive.adjacent_pairs
            ),
            "trial_count": len(self.archive.trials),
            "feature_count": len(self.archive.consensus),
            "independent_archive_transform_verified": True,
            "independent_source_campaign_verifier_claimed": False,
            "source_frozen": True,
            "proposal_only": True,
            "may_certify": False,
            "source_campaign_input_accepted": False,
            "target_observation_input_accepted": False,
            "environment_law_queries": 0,
            "outcome_enumeration_calls": 0,
            "new_draw_calls": 0,
        }

    @property
    def component_id(self) -> str:
        return self._component_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "archive": self.archive.to_document(),
            "production_verification": (
                self.production_verification.to_document()
            ),
            "independent_attestation": (
                self.independent_attestation.to_document()
            ),
            "component_id": self.component_id,
        }


def bind_v072_verified_source_archive_component_v1(
    *,
    archive: archive_v2.VerifiedSourceAcquisitionArchiveV2,
    production_verification: (
        archive_v2.VerifiedSourceAcquisitionArchiveVerificationV2
    ),
    independent_attestation: (
        independent_v2.IndependentSourceAcquisitionArchiveVerificationV2
    ),
) -> V072VerifiedSourceArchiveComponentV1:
    """Bind three already-frozen artifacts without rerunning acquisition."""

    return V072VerifiedSourceArchiveComponentV1(
        archive,
        production_verification,
        independent_attestation,
    )


__all__ = [
    "ARCHIVE_DOCUMENT_DIGEST_TAG",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V072VerifiedSourceArchiveComponentInvariantViolation",
    "V072VerifiedSourceArchiveComponentV1",
    "bind_v072_verified_source_archive_component_v1",
]
