"""Producer for the preregistered V75r4 structural-rank campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp import construction_k7_structural_rank_preregistration_v75r4 as pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
    verify_role_free_relational_template_library_v70,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.structural_rank_transfer_campaign_core_v75r4 import (
    build_structural_rank_transfer_campaign_document_v75r4,
)


CAMPAIGN_ID = "cc3ad3f14573acecea2a6001f0f7f706a3fbb585385f7aa873c5bdb0b3dfcb96"
EXPECTED_CANONICAL_BYTE_COUNT = 2_132_765
EXPECTED_CANONICAL_SHA256 = "5ee5438496f0bdc808576423e1363f377b18ff14c5b9c513d61670b98286a99d"


class ConstructionK7StructuralRankCampaignV75R4Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StructuralRankCampaignV75R4Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StructuralRankCampaignV75R4:
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
            or pre.domains.extension_content_id_v75r4(
                pre.domains.CONSTRUCTION_K7_STRUCTURAL_RANK_CAMPAIGN_V75R4_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V75r4 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: StructuralRankCampaignV75R4 | None = None


def run_structural_rank_campaign_v75r4() -> StructuralRankCampaignV75R4:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_structural_rank_preregistration_v75r4(
        pre.freeze_structural_rank_preregistration_v75r4()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V75r4 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    if template_artifact.library_artifact_id != pre.TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V75r4 frozen terminal-template library changed")
    template_document = template_artifact.to_document()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_structural_rank_transfer_campaign_document_v75r4(
        pre.campaign_config_v75r4(),
        preregistration.preregistration_id,
        (
            pre.V75_FAILURE_ID,
            pre.V75R1_FAILURE_ID,
            pre.V75R2_FAILURE_ID,
            pre.V75R3_CAMPAIGN_ID,
        ),
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
        _fail("frozen V75r4 campaign changed")
    _CACHE = StructuralRankCampaignV75R4(_ISSUER, raw, identity)
    return _CACHE


def verify_structural_rank_campaign_v75r4(
    value: Any,
) -> StructuralRankCampaignV75R4:
    if type(value) is not StructuralRankCampaignV75R4:
        _fail("V75r4 campaign rejects foreign values")
    value.__post_init__()
    expected = run_structural_rank_campaign_v75r4()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V75r4 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_structural_rank_campaign_v75r4",
    "verify_structural_rank_campaign_v75r4",
)
