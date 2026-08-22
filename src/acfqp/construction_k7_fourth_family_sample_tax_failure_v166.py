"""Immutable typed failure for the one-shot V166 formal attempt."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import NoReturn

from acfqp import construction_k7_domain_registry_extension_v167 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PREREGISTRATION_ID = (
    "043a502c5f6f7da983ce1859edace7a74aca28645b688362bcdb2760620337c8"
)
PREREGISTRATION_BYTE_COUNT = 4_681
PREREGISTRATION_SHA256 = (
    "7ef9a7141c6b181d5cbc14a6174a5d273b04f8260a586d3c9e63f35728d3da6e"
)
FAILURE_ID = "2d299454ac4aaa7d0517875f568b90a782d79c1c4aa6881b5d0e18ab48d15911"
EXPECTED_CANONICAL_BYTE_COUNT = 1_800
EXPECTED_CANONICAL_SHA256 = (
    "22333a80c08c1915da8659b25651ee8b49850a7fea132d0acb6df0540dabc51c"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]


class ConstructionK7FourthFamilySampleTaxFailureV166Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FourthFamilySampleTaxFailureV166Error(message)


def freeze_fourth_family_sample_tax_failure_v166(preregistration_raw: bytes) -> bytes:
    registration = loads_canonical_json(preregistration_raw)
    if not (
        canonical_json_bytes(registration) == preregistration_raw
        and len(preregistration_raw) == PREREGISTRATION_BYTE_COUNT
        and hashlib.sha256(preregistration_raw).hexdigest()
        == PREREGISTRATION_SHA256
        and registration["preregistration_id"] == PREREGISTRATION_ID
    ):
        _fail("V166 frozen preregistration changed")
    payload = {
        "schema": "acfqp.fourth_family_sample_tax_failure.v166",
        "failed_preregistration_id": PREREGISTRATION_ID,
        "failed_campaign_id": None,
        "attempt_terminal_state": "FROZEN_PROTOCOL_FAILURE",
        "target_execution_started": True,
        "primary_exception_type": "ValueError",
        "primary_exception_message": "V157 expected exactly one applicable plan mode",
        "primary_failure_stage": "WORKER_OCCURRENCE_PLAN_MODE_ANNOTATION",
        "primary_failure_frames": [
            {
                "relative_path": "src/acfqp/applicable_plan_mode_sequence_v157.py",
                "function": "annotate_applicable_plan_mode_sequence_v157",
                "source_line": 31,
            },
            {
                "relative_path": "src/acfqp/progressive_raw_prefix_campaign_core_v160.py",
                "function": "build_progressive_raw_prefix_occurrence_v160",
                "source_line": 88,
            },
            {
                "relative_path": "src/acfqp/fourth_family_sample_tax_transfer_campaign_core_v166.py",
                "function": "build_fourth_family_sample_tax_occurrence_v166",
                "source_line": 104,
            },
        ],
        "frozen_worker_count": registration["target_worker_count"],
        "failed_occurrence_identity": {
            "kind": "NOT_RETAINED_BY_PROCESS_POOL_EXCEPTION",
            "family": None,
            "seed": None,
            "occurrence_id": None,
        },
        "durable_partial_occurrence_artifact_count": 0,
        "in_memory_success_prefix_recoverable": False,
        "partial_target_outcomes_may_have_been_accessed": True,
        "registered_gate_evaluated": False,
        "same_identity_rerun_forbidden": True,
        "failed_result_not_reclassified_as_success": True,
        "fresh_successor_identity_required": True,
        "query_or_factor_sample_tax_result_claimed": False,
        "fourth_family_transfer_claimed": False,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "failure_id": domains.extension_content_id_v167(
            domains.CONSTRUCTION_K7_V166_FAILURE_V167_DOMAIN, payload
        ),
    }
    raw = canonical_json_bytes(document)
    if FAILURE_ID != "0" * 64 and not (
        document["failure_id"] == FAILURE_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V166 frozen failure changed")
    return raw


__all__ = (
    "FAILURE_ID",
    "freeze_fourth_family_sample_tax_failure_v166",
)
