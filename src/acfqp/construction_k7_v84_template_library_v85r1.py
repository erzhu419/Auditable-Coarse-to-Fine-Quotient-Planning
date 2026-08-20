"""Read the self-contained V84-derived template library used by V85r1."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v85r1 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


LIBRARY_ARTIFACT_ID = "9e55eb31f49aedce8c611fd37d66f87f42643f385bf9d6f6e98e0856b1ef7520"
EXPECTED_CANONICAL_BYTE_COUNT = 49_262
EXPECTED_CANONICAL_SHA256 = "433e4fe332da6629532e6b84a46e9cfafee2c2378de414cc2c6af3d881133706"
V84_CAMPAIGN_ID = "1828a9c92459da992f2e691b5a8f935005d4da5981070728f4c5d9a0a4e9db28"
V84_CAMPAIGN_SHA256 = "66bf9d5e1252c527cb4e4208b5590b6047a121921552f66442a6248ed7745c13"
ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "artifacts/world_model/v85r1_v84_balanced_template_library.json"
)


class ConstructionK7V84TemplateLibraryV85R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7V84TemplateLibraryV85R1Error(message)


def load_v84_template_library_v85r1() -> dict[str, Any]:
    raw = ARTIFACT_PATH.read_bytes()
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V85r1 template library is not canonical")
    payload = {
        key: value for key, value in document.items() if key != "library_artifact_id"
    }
    if (
        len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        or document.get("library_artifact_id") != LIBRARY_ARTIFACT_ID
        or domains.extension_content_id_v85r1(
            domains.CONSTRUCTION_K7_V84_TEMPLATE_LIBRARY_V85R1_DOMAIN, payload
        )
        != LIBRARY_ARTIFACT_ID
        or document.get("v84_campaign_id") != V84_CAMPAIGN_ID
        or document.get("v84_campaign_sha256") != V84_CAMPAIGN_SHA256
        or document.get("source_program_count") != 6
        or document.get("derived_only_from_frozen_v84_source_programs") is not True
        or document.get("future_target_prediction_authority_present") is not False
        or document.get("abstract_plan_safety_authority_present") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V85r1 template library identity or claim boundary changed")
    library = document.get("compiled_template_library")
    if (
        type(library) is not dict
        or library.get("schema") != "acfqp.generic_role_free_relational_template_library.v33"
        or library.get("role_free_template_count") != 63
        or type(library.get("role_free_templates")) is not list
        or len(library["role_free_templates"]) != 63
    ):
        _fail("V85r1 compiled template inventory changed")
    return document


__all__ = (
    "LIBRARY_ARTIFACT_ID",
    "load_v84_template_library_v85r1",
)
