"""Load the source-frozen V56 model consumed by the V86 target Gate."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v86 as domains
from acfqp.generic_projected_disagreement_model_compiler_v56 import (
    verify_projected_disagreement_model_v56,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


MODEL_ARTIFACT_ID = "c069fb2a39fee3b9dc7dc847fef15369cf8d65c5d6322bbaae1bbceb924a476e"
EXPECTED_CANONICAL_BYTE_COUNT = 136_251
EXPECTED_CANONICAL_SHA256 = "30c5b8775ae05039a971c20c52450efb29fcc8b57d81a38f70c9567fd9ef2bec"
MODEL_ID = "401693d9b6f3a50ec3581f0878181955cc804324cad003e23635b6af2e9bb1db"
ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "artifacts/world_model/v86_projected_disagreement_model.json"
)


class ConstructionK7ProjectedModelArtifactV86Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProjectedModelArtifactV86Error(message)


def load_projected_model_artifact_v86() -> dict[str, Any]:
    raw = ARTIFACT_PATH.read_bytes()
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V86 model artifact is not canonical")
    payload = {
        key: value for key, value in document.items() if key != "model_artifact_id"
    }
    model = document.get("projected_disagreement_successor_model")
    if (
        len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        or document.get("model_artifact_id") != MODEL_ARTIFACT_ID
        or domains.extension_content_id_v86(
            domains.CONSTRUCTION_K7_PROJECTED_MODEL_ARTIFACT_V86_DOMAIN, payload
        )
        != MODEL_ARTIFACT_ID
        or document.get("projected_disagreement_successor_model_id") != MODEL_ID
        or document.get("model_frozen_before_any_v86_target_outcome") is not True
        or document.get("target_outcomes_used_to_select_or_refit_model") is not False
        or document.get("abstract_plan_safety_authority_present") is not False
        or document.get("complete_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
    ):
        _fail("V86 model artifact identity or claim boundary changed")
    verified = verify_projected_disagreement_model_v56(model)
    if verified.get("projected_disagreement_successor_model_id") != MODEL_ID:
        _fail("V86 embedded model changed")
    return document


__all__ = ("MODEL_ARTIFACT_ID", "MODEL_ID", "load_projected_model_artifact_v86")
