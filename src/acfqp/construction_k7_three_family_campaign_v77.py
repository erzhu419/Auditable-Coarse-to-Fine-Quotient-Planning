"""Producer for the preregistered fail-closed V77 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp import construction_k7_three_family_preregistration_v77 as pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
    verify_role_free_relational_template_library_v70,
)
from acfqp.fail_closed_three_family_campaign_core_v77 import (
    build_fail_closed_three_family_campaign_document_v77,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "5dadee6779c1d18779f41f90aa360816def2333c3f07983b95d1da2d1c28558c"
EXPECTED_CANONICAL_BYTE_COUNT = 3_286_606
EXPECTED_CANONICAL_SHA256 = "044a8a669fd8680e835efc58b5e31ba59c5c15c617cca8b9632fdb93fa2490dc"


class ConstructionK7ThreeFamilyCampaignV77Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ThreeFamilyCampaignV77Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ThreeFamilyCampaignV77:
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
            or pre.domains.extension_content_id_v77(
                pre.domains.CONSTRUCTION_K7_THREE_FAMILY_CAMPAIGN_V77_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V77 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ThreeFamilyCampaignV77 | None = None


def run_three_family_campaign_v77() -> ThreeFamilyCampaignV77:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_three_family_preregistration_v77(
        pre.freeze_three_family_preregistration_v77()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V77 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    if template_artifact.library_artifact_id != pre.TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V77 template library changed")
    template_document = template_artifact.to_document()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_fail_closed_three_family_campaign_document_v77(
        pre.campaign_config_v77(),
        preregistration.preregistration_id,
        pre.V76_FAILURE_ID,
        pre.V75R5_CAMPAIGN_ID,
        pre.V75R5_VERIFICATION_ID,
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
        _fail("frozen V77 campaign changed")
    _CACHE = ThreeFamilyCampaignV77(_ISSUER, raw, identity)
    return _CACHE


def verify_three_family_campaign_v77(value: Any) -> ThreeFamilyCampaignV77:
    if type(value) is not ThreeFamilyCampaignV77:
        _fail("V77 campaign rejects foreign values")
    value.__post_init__()
    expected = run_three_family_campaign_v77()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V77 campaign differs from frozen output")
    return value


__all__ = ("CAMPAIGN_ID", "run_three_family_campaign_v77", "verify_three_family_campaign_v77")
