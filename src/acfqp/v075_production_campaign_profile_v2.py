"""Target-free scheduling profile for the V0-075 production campaign.

This leaf deliberately has no dependency on the manifest, pre-open,
observer, occurrence, total-lift, or campaign-runner implementations.  It
freezes only the public execution shape that must be known before any of
those downstream authorities exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.45.0"
PROFILE_KEY = "v075_production_campaign_profile_v2"

REGISTERED_OCCURRENCE_COUNT = 15
REGISTERED_MAX_WORKERS = 15
MAX_PROFILE_BYTES = 16 * 1024

TARGET_EXECUTION_OPENED = False
OFFICIAL_EXECUTION_ALLOWED = False

DOMAIN_TAGS = {
    "profile": "acfqp:v075-production-campaign-runner-profile:v2",
}


class V075ProductionCampaignProfileV2InvariantViolation(ValueError):
    """The immutable scheduling profile was forged, changed, or mistyped."""


def _fail(message: str) -> None:
    raise V075ProductionCampaignProfileV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ProductionCampaignProfileV2InvariantViolation(
            str(error)
        ) from error


_PROFILE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionCampaignProfileV2:
    """Exact fifteen-occurrence scheduling contract, not an execution grant."""

    _issuer: object = field(repr=False, compare=False)
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _PROFILE_ISSUER
            or REGISTERED_OCCURRENCE_COUNT != 15
            or REGISTERED_MAX_WORKERS != REGISTERED_OCCURRENCE_COUNT
        ):
            _fail("production campaign profile is caller-minted or changed")
        object.__setattr__(
            self,
            "_profile_id",
            _hash("profile", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_campaign_runner_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_count": REGISTERED_OCCURRENCE_COUNT,
            "max_workers": REGISTERED_MAX_WORKERS,
            "executor": "THREAD_POOL_OVER_ISOLATED_OCCURRENCE_IPC",
            "parallelism_axis": "LOGICAL_OCCURRENCE_ONLY",
            "one_fresh_ipc_child_per_occurrence": True,
            "intra_occurrence_parallelism_allowed": False,
            "result_order": "IMMUTABLE_SCIENTIFIC_ORDER",
            "scientific_ordinals": list(
                range(REGISTERED_OCCURRENCE_COUNT)
            ),
            "transport_ordinals": list(
                range(1, REGISTERED_OCCURRENCE_COUNT + 1)
            ),
            "per_occurrence_algorithm_changed": False,
            "accuracy_reduction_allowed": False,
            "statistical_threshold_reduction_allowed": False,
            "draw_cap_reduction_allowed": False,
            "evidence_omission_allowed": False,
            "final_preregistration_binding_required": True,
            "target_execution_opened": False,
            "target_accessed": False,
            "official_execution_allowed": False,
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


def freeze_v075_production_campaign_profile_v2(
) -> V075ProductionCampaignProfileV2:
    """Return the sole registered V2 scheduling profile."""

    return V075ProductionCampaignProfileV2(_PROFILE_ISSUER)


def verify_v075_production_campaign_profile_bytes_v2(
    raw: bytes,
) -> V075ProductionCampaignProfileV2:
    """Recompute and byte-compare the exact profile without caller inputs."""

    if type(raw) is not bytes or not raw or len(raw) > MAX_PROFILE_BYTES:
        _fail("production campaign profile bytes are absent or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075ProductionCampaignProfileV2InvariantViolation(
            "production campaign profile is not canonical JSON"
        ) from error
    expected = freeze_v075_production_campaign_profile_v2()
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != raw
        or document != expected.to_document()
        or raw != expected.canonical_bytes
    ):
        _fail("production campaign profile differs from exact V2 replay")
    return expected


__all__ = [
    "DOMAIN_TAGS",
    "MAX_PROFILE_BYTES",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_MAX_WORKERS",
    "REGISTERED_OCCURRENCE_COUNT",
    "SCHEMA_VERSION",
    "TARGET_EXECUTION_OPENED",
    "V075ProductionCampaignProfileV2",
    "V075ProductionCampaignProfileV2InvariantViolation",
    "freeze_v075_production_campaign_profile_v2",
    "verify_v075_production_campaign_profile_bytes_v2",
]
