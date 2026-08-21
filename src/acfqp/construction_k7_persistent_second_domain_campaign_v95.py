"""Producer for the preregistered V95 persistent second-domain campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_second_domain_preregistration_v95 as pre
from acfqp.construction_k7_action_applicability_model_v87 import (
    MODEL_ARTIFACT_ID as APPLICABILITY_MODEL_ARTIFACT_ID,
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    MODEL_ARTIFACT_ID as PROJECTED_MODEL_ARTIFACT_ID,
    load_projected_model_artifact_v86,
)
from acfqp.construction_k7_total_label_meta_prior_campaign_v94 import (
    CAMPAIGN_ID as V94_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V94_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V94_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_total_label_meta_prior_independent_verifier_v94 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V94_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V94_VERIFICATION_SHA256,
    VERIFICATION_ID as V94_VERIFICATION_ID,
)
from acfqp.persistent_second_domain_campaign_core_v95 import (
    build_persistent_second_domain_campaign_document_v95,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7PersistentSecondDomainCampaignV95Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PersistentSecondDomainCampaignV95Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PersistentSecondDomainCampaignV95:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "campaign_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v95(
                pre.domains.CONSTRUCTION_K7_PERSISTENT_SECOND_DOMAIN_CAMPAIGN_V95_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V95 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: PersistentSecondDomainCampaignV95 | None = None


def run_persistent_second_domain_campaign_v95(
    v94_campaign_raw: bytes,
    v94_verification_raw: bytes,
) -> PersistentSecondDomainCampaignV95:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V95 campaign exists; same identity will not be rerun")
    inputs = (
        (
            v94_campaign_raw,
            V94_CAMPAIGN_BYTE_COUNT,
            V94_CAMPAIGN_SHA256,
        ),
        (
            v94_verification_raw,
            V94_VERIFICATION_BYTE_COUNT,
            V94_VERIFICATION_SHA256,
        ),
    )
    if any(
        type(raw) is not bytes
        or len(raw) != count
        or hashlib.sha256(raw).hexdigest() != digest
        for raw, count, digest in inputs
    ):
        _fail("V95 frozen predecessor bytes changed")
    v94_campaign = loads_canonical_json(v94_campaign_raw)
    v94_verification = loads_canonical_json(v94_verification_raw)
    if (
        type(v94_campaign) is not dict
        or type(v94_verification) is not dict
        or v94_campaign.get("campaign_id") != V94_CAMPAIGN_ID
        or v94_campaign.get("registered_gate", {}).get("passed") is not True
        or v94_verification.get("verification_id") != V94_VERIFICATION_ID
        or v94_verification.get("campaign_id") != V94_CAMPAIGN_ID
    ):
        _fail("V95 predecessor identity or successful Gate changed")
    preregistration = pre.verify_persistent_second_domain_preregistration_v95(
        pre.freeze_persistent_second_domain_preregistration_v95()
    )
    projected = load_projected_model_artifact_v86()
    applicability = load_action_applicability_model_v87()
    if (
        projected.get("model_artifact_id") != PROJECTED_MODEL_ARTIFACT_ID
        or applicability.get("model_artifact_id")
        != APPLICABILITY_MODEL_ARTIFACT_ID
    ):
        _fail("V95 frozen source-model artifact changed")
    document = build_persistent_second_domain_campaign_document_v95(
        pre.campaign_config_v95(),
        preregistration_id=preregistration.preregistration_id,
        v94_campaign_id=v94_campaign["campaign_id"],
        v94_verification_id=v94_verification["verification_id"],
        projected_model_artifact_id=projected["model_artifact_id"],
        applicability_model_artifact_id=applicability["model_artifact_id"],
        model=projected["projected_disagreement_successor_model"],
        applicability=applicability["action_applicability_program"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V95 campaign changed")
    _CACHE = PersistentSecondDomainCampaignV95(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_persistent_second_domain_campaign_v95")
