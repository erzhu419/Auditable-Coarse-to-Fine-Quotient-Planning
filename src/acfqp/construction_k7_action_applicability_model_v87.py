"""Load the frozen, source-only V87 action-applicability model artifact."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v87 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MODEL_ARTIFACT_ID = "07ee765058797bc083db3180bb26952a79a224f8e8aef2f8f284237f87137f77"
EXPECTED_CANONICAL_BYTE_COUNT = 2_978
EXPECTED_CANONICAL_SHA256 = "b564c19963692a593f38c8b64520643b71d28fb2c274d998fcd439553d1f7fd4"
SOURCE_CAMPAIGN_ID = "da749b6ad8996aba86896476fd7293540cca77cd1b4db7145b9bf4fe2759ec70"
SOURCE_MODEL_ID = "401693d9b6f3a50ec3581f0878181955cc804324cad003e23635b6af2e9bb1db"
ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "artifacts/world_model/v87_action_applicability_model.json"
)
_PROGRAM_DOMAIN = b"acfqp:generic-action-applicability-program:v58\x00"


class ConstructionK7ActionApplicabilityModelV87Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ActionApplicabilityModelV87Error(message)


def load_action_applicability_model_v87() -> dict[str, Any]:
    raw = ARTIFACT_PATH.read_bytes()
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V87 applicability artifact is not canonical")
    payload = {
        key: value for key, value in document.items() if key != "model_artifact_id"
    }
    program = document.get("action_applicability_program")
    program_payload = (
        {
            key: value
            for key, value in program.items()
            if key != "action_applicability_program_id"
        }
        if type(program) is dict
        else {}
    )
    relation = program.get("selected_program") if type(program) is dict else None
    if (
        len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        or document.get("model_artifact_id") != MODEL_ARTIFACT_ID
        or domains.extension_content_id_v87(
            domains.CONSTRUCTION_K7_ACTION_APPLICABILITY_MODEL_V87_DOMAIN,
            payload,
        )
        != MODEL_ARTIFACT_ID
        or document.get("v85r1_campaign_id") != SOURCE_CAMPAIGN_ID
        or document.get("source_model_id") != SOURCE_MODEL_ID
        or document.get("target_outcome_input_present") is not False
        or document.get("applicability_used_as_safety_authority") is not False
        or document.get("complete_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or type(program) is not dict
        or program.get("schema")
        != "acfqp.generic_action_applicability_program.v58"
        or program.get("source_campaign_id") != SOURCE_CAMPAIGN_ID
        or program.get("source_model_id") != SOURCE_MODEL_ID
        or program.get("training_exact") is not True
        or program.get("heldout_exact") is not True
        or program.get("training_exact_candidate_count") != 1
        or program.get("future_target_outcome_input_present") is not False
        or program.get("applicability_program_safety_authority_present") is not False
        or program.get("complete_world_model_claimed") is not False
        or program.get("action_applicability_program_id")
        != hashlib.sha256(
            _PROGRAM_DOMAIN + canonical_json_bytes(program_payload)
        ).hexdigest()
        or relation
        != {
            "schema": "acfqp.generic_action_applicability_relation.v58",
            "opcode": "EQ",
            "state_column": 4,
            "action_field": 4,
            "result_type": "BOOL",
            "semantic_names_used": False,
        }
    ):
        _fail("V87 applicability artifact identity or claim boundary changed")
    return document


__all__ = (
    "MODEL_ARTIFACT_ID",
    "load_action_applicability_model_v87",
)
