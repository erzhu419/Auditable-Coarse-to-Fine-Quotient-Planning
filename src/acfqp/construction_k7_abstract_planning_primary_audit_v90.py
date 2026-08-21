"""Producer and loader for the registered V90 deterministic audit artifact."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp.abstract_planning_primary_audit_core_v90 import (
    build_abstract_planning_primary_audit_document_v90,
)
from acfqp import construction_k7_abstract_planning_primary_preregistration_v90 as pre
from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


AUDIT_ID = "1470de5895af6fb5215bfc34c29aa14f14f49af375ba003665ebc008d555e503"
EXPECTED_CANONICAL_BYTE_COUNT = 113_015
EXPECTED_CANONICAL_SHA256 = "3607bba575cc24ab41e52181a57a84911a1de85460505102aeb4266c52341d05"
ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / ".tmp/exact-freeze/v89_permutation_matched_sample_tax_campaign.json"
ARTIFACT_PATH = ROOT / "artifacts/world_model/v90_abstract_planning_primary_audit.json"


class ConstructionK7AbstractPlanningPrimaryAuditV90Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractPlanningPrimaryAuditV90Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AbstractPlanningPrimaryAuditV90:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    audit_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "audit_id"}
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("audit_id") != self.audit_id
            or pre.domains.extension_content_id_v90(
                pre.domains.CONSTRUCTION_K7_ABSTRACT_PRIMARY_AUDIT_V90_DOMAIN,
                payload,
            )
            != self.audit_id
        ):
            _fail("V90 audit bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def _build(raw: bytes) -> bytes:
    if (
        len(raw) != pre.V89_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != pre.V89_CAMPAIGN_SHA256
    ):
        _fail("V90 frozen V89 input bytes changed")
    campaign = loads_canonical_json(raw)
    if type(campaign) is not dict or campaign.get("campaign_id") != pre.V89_CAMPAIGN_ID:
        _fail("V90 frozen V89 input identity changed")
    registration = pre.freeze_abstract_planning_primary_preregistration_v90()
    projected = load_projected_model_artifact_v86()
    applicability = load_action_applicability_model_v87()
    document = build_abstract_planning_primary_audit_document_v90(
        campaign,
        registration.preregistration_id,
        pre.V89_VERIFICATION_ID,
        projected["projected_disagreement_successor_model"],
        applicability["action_applicability_program"],
        maximum_abstract_depth=12,
        maximum_abstract_support_branch_evaluations=1_000_000,
        abstract_support_feasible_beam_width=32,
    )
    return canonical_json_bytes(document)


def run_abstract_planning_primary_audit_v90() -> AbstractPlanningPrimaryAuditV90:
    raw = _build(INPUT_PATH.read_bytes())
    document = loads_canonical_json(raw)
    identity = document["audit_id"]
    if AUDIT_ID != "0" * 64 and (
        identity != AUDIT_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V90 audit changed")
    return AbstractPlanningPrimaryAuditV90(_ISSUER, raw, identity)


def load_abstract_planning_primary_audit_v90() -> AbstractPlanningPrimaryAuditV90:
    raw = ARTIFACT_PATH.read_bytes()
    if (
        AUDIT_ID == "0" * 64
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V90 artifact bytes changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or document.get("audit_id") != AUDIT_ID:
        _fail("V90 artifact identity changed")
    return AbstractPlanningPrimaryAuditV90(_ISSUER, raw, AUDIT_ID)


__all__ = (
    "AUDIT_ID",
    "load_abstract_planning_primary_audit_v90",
    "run_abstract_planning_primary_audit_v90",
)
