"""Producer for the preregistered corrected V72r1 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_successor_version_space_preregistration_v72r1 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
    verify_role_free_relational_template_library_v70,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.successor_version_space_campaign_core_v72r1 import (
    build_successor_version_space_campaign_document_v72r1,
)


CAMPAIGN_ID = "2d570b3853f574083cb7e93e2f0ca026a985ca6cd5b2b12475eb4ebc5ead1e80"
EXPECTED_CANONICAL_BYTE_COUNT = 4_445_009
EXPECTED_CANONICAL_SHA256 = "d4dace957a9173220373022310e1b86b9c3ec609df36eaf8765fbc2c95a4f68b"


class ConstructionK7SuccessorVersionSpaceCampaignV72R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SuccessorVersionSpaceCampaignV72R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SuccessorVersionSpaceCampaignV72R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v72r1(
                pre.domains.CONSTRUCTION_K7_SUCCESSOR_VERSION_SPACE_CAMPAIGN_V72R1_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V72r1 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: SuccessorVersionSpaceCampaignV72R1 | None = None


def run_successor_version_space_campaign_v72r1(
) -> SuccessorVersionSpaceCampaignV72R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_successor_version_space_preregistration_v72r1(
        pre.freeze_successor_version_space_preregistration_v72r1()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V72r1 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    if (
        residual_artifact.library_artifact_id != pre.V62_LIBRARY_ID
        or template_artifact.library_artifact_id
        != pre.TEMPLATE_LIBRARY_ARTIFACT_ID
    ):
        _fail("V72r1 frozen library predecessor changed")
    template_document = template_artifact.to_document()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_successor_version_space_campaign_document_v72r1(
        pre.campaign_config_v72r1(),
        preregistration.preregistration_id,
        pre.V71_CAMPAIGN_ID,
        pre.V71_VERIFICATION_ID,
        template_artifact.library_artifact_id,
        factor_library,
        residual_artifact.to_document()["compiled_library"],
        template_document["compiled_template_library"],
        template_document["offline_template_source_ground_support_labels"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V72r1 campaign changed")
    _CACHE = SuccessorVersionSpaceCampaignV72R1(_ISSUER, raw, identity)
    return _CACHE


def verify_successor_version_space_campaign_v72r1(
    value: Any,
) -> SuccessorVersionSpaceCampaignV72R1:
    if type(value) is not SuccessorVersionSpaceCampaignV72R1:
        _fail("V72r1 campaign rejects foreign values")
    value.__post_init__()
    expected = run_successor_version_space_campaign_v72r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V72r1 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_successor_version_space_campaign_v72r1",
    "verify_successor_version_space_campaign_v72r1",
)
