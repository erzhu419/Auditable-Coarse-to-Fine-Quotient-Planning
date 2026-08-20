"""Frozen role-free terminal-template library extracted from V69 evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v70 as domains
from acfqp.construction_k7_source_complete_relational_campaign_v69 import (
    CAMPAIGN_ID as V69_CAMPAIGN_ID,
    run_source_complete_relational_campaign_v69,
    verify_source_complete_relational_campaign_v69,
)
from acfqp.generic_role_free_relational_template_v33 import (
    compile_role_free_relational_template_library_v33,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


LIBRARY_ARTIFACT_ID = "8657115a19bace2861b3a14ff780a2708b6e76101a2b7468e52e5285a113b2a9"
EXPECTED_CANONICAL_BYTE_COUNT = 85_517
EXPECTED_CANONICAL_SHA256 = "afa701e1d1bcf9b1128ee767202fcf75ef0a2d76e8b0646162735e16f3ff8aab"
V69_VERIFICATION_ID = "3c67ad21d01897448aa5a60c7fe4d802f2b1f477761451dc801e1b270c31d3ed"
IMPLEMENTATION_COMMIT = "7ed54bc"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATH = "src/acfqp/generic_role_free_relational_template_v33.py"


class ConstructionK7RoleFreeRelationalTemplateLibraryV70Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RoleFreeRelationalTemplateLibraryV70Error(message)


def _document() -> dict[str, Any]:
    campaign = verify_source_complete_relational_campaign_v69(
        run_source_complete_relational_campaign_v69()
    ).to_document()
    if campaign["campaign_id"] != V69_CAMPAIGN_ID:
        _fail("V70 V69 campaign predecessor changed")
    source_programs = tuple(
        row["prior_episode"]["predecessor_v30_episode"][
            "final_relational_terminal_program"
        ]
        for row in campaign["occurrences"]
    )
    library = compile_role_free_relational_template_library_v33(source_programs)
    source_raw = (SOURCE_ROOT / BOUND_SOURCE_PATH).read_bytes()
    prior_source_rows = sum(
        len(row["prior_episode"]["terminal_program_source_evidence"]["raw_transition_rows"])
        for row in campaign["occurrences"]
    )
    source_labels = (
        campaign["accounting"]["common_partial_acquisition_labels"]
        + campaign["accounting"]["prior_certificate_local_labels"]
    )
    payload = {
        "schema": "acfqp.role_free_relational_template_library.v70",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "v69_campaign_id": V69_CAMPAIGN_ID,
        "v69_verification_id": V69_VERIFICATION_ID,
        "source_occurrence_ids": [row["occurrence_id"] for row in campaign["occurrences"]],
        "source_terminal_program_ids": [
            row["terminal_program_id"] for row in source_programs
        ],
        "compiled_template_library": library,
        "offline_template_source_ground_support_labels": source_labels,
        "offline_template_source_raw_transition_rows": prior_source_rows,
        "offline_residual_library_labels_not_included": 204,
        "source_closure": {
            "relative_path": BOUND_SOURCE_PATH,
            "byte_count": len(source_raw),
            "sha256": hashlib.sha256(source_raw).hexdigest(),
        },
        "raw_column_numbers_retained": False,
        "source_status_tokens_retained": False,
        "domain_or_state_role_names_present": False,
        "future_target_prediction_authority_present": False,
        "abstract_plan_safety_authority_present": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "library_artifact_id": domains.extension_content_id_v70(
            domains.CONSTRUCTION_K7_ROLE_FREE_RELATIONAL_LIBRARY_V70_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RoleFreeRelationalTemplateLibraryV70:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    library_artifact_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "library_artifact_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("library_artifact_id") != self.library_artifact_id
            or domains.extension_content_id_v70(
                domains.CONSTRUCTION_K7_ROLE_FREE_RELATIONAL_LIBRARY_V70_DOMAIN,
                payload,
            )
            != self.library_artifact_id
        ):
            _fail("V70 template library bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: RoleFreeRelationalTemplateLibraryV70 | None = None


def freeze_role_free_relational_template_library_v70() -> RoleFreeRelationalTemplateLibraryV70:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["library_artifact_id"]
    if LIBRARY_ARTIFACT_ID != "0" * 64 and (
        identity != LIBRARY_ARTIFACT_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V70 template library changed")
    _CACHE = RoleFreeRelationalTemplateLibraryV70(_ISSUER, raw, identity)
    return _CACHE


def verify_role_free_relational_template_library_v70(
    value: Any,
) -> RoleFreeRelationalTemplateLibraryV70:
    if type(value) is not RoleFreeRelationalTemplateLibraryV70:
        _fail("V70 template library rejects foreign values")
    value.__post_init__()
    expected = freeze_role_free_relational_template_library_v70()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V70 template library differs from frozen output")
    return value


__all__ = (
    "LIBRARY_ARTIFACT_ID",
    "freeze_role_free_relational_template_library_v70",
    "verify_role_free_relational_template_library_v70",
)
