"""Producer for the preregistered V89 permutation-matched sample-tax Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_permutation_matched_sample_tax_preregistration_v89 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70
from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.permutation_matched_sample_tax_campaign_core_v89 import (
    build_permutation_matched_sample_tax_campaign_document_v89,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7PermutationMatchedSampleTaxCampaignV89Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PermutationMatchedSampleTaxCampaignV89Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PermutationMatchedSampleTaxCampaignV89:
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
            or pre.domains.extension_content_id_v89(
                pre.domains.CONSTRUCTION_K7_PERMUTATION_MATCHED_CAMPAIGN_V89_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V89 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: PermutationMatchedSampleTaxCampaignV89 | None = None


def run_permutation_matched_sample_tax_campaign_v89(
) -> PermutationMatchedSampleTaxCampaignV89:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_permutation_matched_sample_tax_preregistration_v89(
        pre.freeze_permutation_matched_sample_tax_preregistration_v89()
    )
    if pre._frozen_source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V89 source closure changed")
    projected = load_projected_model_artifact_v86()
    applicability = load_action_applicability_model_v87()
    factor_library = (
        v70.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_permutation_matched_sample_tax_campaign_document_v89(
        pre.campaign_config_v89(),
        preregistration.preregistration_id,
        pre.PROJECTED_MODEL_ARTIFACT_ID,
        pre.APPLICABILITY_MODEL_ARTIFACT_ID,
        projected["projected_disagreement_successor_model"],
        applicability["action_applicability_program"],
        factor_library,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V89 campaign changed")
    _CACHE = PermutationMatchedSampleTaxCampaignV89(_ISSUER, raw, identity)
    return _CACHE


def verify_permutation_matched_sample_tax_campaign_v89(
    value: Any,
) -> PermutationMatchedSampleTaxCampaignV89:
    if type(value) is not PermutationMatchedSampleTaxCampaignV89:
        _fail("V89 campaign rejects foreign values")
    value.__post_init__()
    expected = run_permutation_matched_sample_tax_campaign_v89()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V89 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_permutation_matched_sample_tax_campaign_v89",
    "verify_permutation_matched_sample_tax_campaign_v89",
)
