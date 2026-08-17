"""Additive V50r1 campaign core with one source-closed dependency correction.

The failed V50 core remains byte-for-byte frozen.  Its orchestration code is
reused without mutation by constructing a private function with a copied
global namespace in which the sole V5 synthesizer dependency is replaced by
the additive V6 safe-terminal synthesizer.  No caller callback is accepted.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping, NoReturn

from acfqp import layout_factorized_campaign_core_v50 as predecessor
from acfqp.generic_layout_factorized_world_model_v6 import (
    synthesize_layout_factorized_world_model_v6,
)
from acfqp.phase3e_ids import content_id


PREDECESSOR_CORE_BYTE_COUNT = 43_506
PREDECESSOR_CORE_SHA256 = (
    "36b8b4dba0c8a83a6020c84cf7a4167c190f8db4eccc37c59cfabf00c2b9c7d8"
)
V50_FAILURE_ID = "603e1e69ed5e4093675435ffda6aa1de82118d93b44232a9cfc0454a00424581"


class LayoutFactorizedCampaignCoreV50R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise LayoutFactorizedCampaignCoreV50R1Error(message)


_FROZEN_PREDECESSOR_BUILDER = predecessor.build_layout_factorized_campaign_document_v50
_FROZEN_V6_SYNTHESIZER = synthesize_layout_factorized_world_model_v6


def _verify_predecessor_core_source() -> None:
    path = Path(predecessor.__file__)
    raw = path.read_bytes()
    if (
        len(raw) != PREDECESSOR_CORE_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != PREDECESSOR_CORE_SHA256
    ):
        _fail("V50r1 frozen predecessor orchestration source changed")
    if predecessor.build_layout_factorized_campaign_document_v50 is not _FROZEN_PREDECESSOR_BUILDER:
        _fail("V50r1 predecessor builder callable identity changed")
    if synthesize_layout_factorized_world_model_v6 is not _FROZEN_V6_SYNTHESIZER:
        _fail("V50r1 safe synthesizer callable identity changed")


def build_layout_factorized_campaign_document_v50r1(
    config: Mapping[str, Any], preregistration_id: str
) -> dict[str, Any]:
    _verify_predecessor_core_source()
    rebound_globals = dict(_FROZEN_PREDECESSOR_BUILDER.__globals__)
    if rebound_globals.get("synthesize_layout_factorized_world_model_v5") is None:
        _fail("V50r1 predecessor dependency slot changed")
    rebound_globals["synthesize_layout_factorized_world_model_v5"] = (
        _FROZEN_V6_SYNTHESIZER
    )
    private_builder = FunctionType(
        _FROZEN_PREDECESSOR_BUILDER.__code__,
        rebound_globals,
        "_source_closed_v50r1_builder",
        _FROZEN_PREDECESSOR_BUILDER.__defaults__,
        _FROZEN_PREDECESSOR_BUILDER.__closure__,
    )
    predecessor_document = private_builder(config, preregistration_id)
    models = predecessor_document["world_models"]
    if not all(
        model.get("terminal_next_status_column_candidates_excluded") is True
        and model.get("terminal_self_next_dependency_count") == 0
        and model["compiled_program"].get(
            "terminal_next_status_column_candidates_excluded"
        )
        is True
        and model["compiled_program"].get("terminal_self_next_dependency_count")
        == 0
        for model in models.values()
    ):
        _fail("V50r1 safe-terminal correction was not present in both models")
    payload = {
        **{
            key: value
            for key, value in predecessor_document.items()
            if key != "campaign_id"
        },
        "schema": "acfqp.layout_factorized_campaign.v50r1",
        "frozen_failed_predecessor_id": V50_FAILURE_ID,
        "successor_correction": {
            "predecessor_orchestration_code_reused_without_mutation": True,
            "private_copied_global_namespace_used": True,
            "rebound_dependency_count": 1,
            "rebound_from": "synthesize_layout_factorized_world_model_v5",
            "rebound_to": "synthesize_layout_factorized_world_model_v6",
            "caller_supplied_callback_present": False,
            "terminal_next_status_column_candidates_excluded": True,
            "terminal_self_next_dependency_count": 0,
        },
    }
    return {
        **payload,
        "campaign_id": content_id(config["domains"]["campaign"], payload),
    }


__all__ = (
    "LayoutFactorizedCampaignCoreV50R1Error",
    "PREDECESSOR_CORE_BYTE_COUNT",
    "PREDECESSOR_CORE_SHA256",
    "V50_FAILURE_ID",
    "build_layout_factorized_campaign_document_v50r1",
)
