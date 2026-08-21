"""Frozen typed record for the preregistered V91r1 source-member failure."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v91r1 as domains
from acfqp.construction_k7_occurrence_balanced_source_preregistration_v91r1 import (
    PREREGISTRATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


FAILURE_ID = (
    "6c076b761b7b2b9e68a0ac49a7f7b8ae1accb43e2b140486b1c268eb23b179c6"
)
EXPECTED_CANONICAL_BYTE_COUNT = 1_416
EXPECTED_CANONICAL_SHA256 = (
    "044b3dca2d35570d72cbd90795f01289845bb7e8ba973a9dbf0ec34a07ef6b39"
)


class ConstructionK7OccurrenceBalancedSourceFailureV91R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OccurrenceBalancedSourceFailureV91R1Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.occurrence_balanced_source_failure.v91r1",
        "preregistration_id": PREREGISTRATION_ID,
        "failure_stage": "SOURCE_MEMBER_COMMON_PARTIAL_ACQUISITION",
        "failed_source_family": "COUPLED_EXCHANGE",
        "failed_source_seed": 931101,
        "source_member_results_returned_to_parent": 0,
        "other_registered_source_seed_terminal_state": "NOT_OBSERVED_BY_PARENT",
        "exception_module": (
            "acfqp.true_bit_symmetric_three_domain_campaign_core_v59"
        ),
        "exception_type": "TrueBitSymmetricThreeDomainCampaignCoreV59Error",
        "exception_message": (
            "V59 true-bit acquisition did not close before its cap for "
            "COUPLED_EXCHANGE seed 931101; pending=['STRICT_NO_PRIOR']"
        ),
        "failed_before_reference_alignment": True,
        "failed_before_occurrence_balanced_query_scheduling": True,
        "failed_before_model_compilation": True,
        "failed_before_target_execution": True,
        "registered_campaign_document_produced": False,
        "same_preregistered_identity_will_not_be_rerun": True,
        "partial_worker_artifacts_available_to_parent": False,
        "typed_result": "SOURCE_MEMBER_CAP_FAILURE_NONCERTIFICATE",
        "fresh_target_outcome_count": 0,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "failure_id": domains.extension_content_id_v91r1(
            domains.CONSTRUCTION_K7_OCCURRENCE_BALANCED_SOURCE_CAMPAIGN_V91R1_DOMAIN,
            payload,
        ),
    }


def freeze_occurrence_balanced_source_failure_v91r1() -> bytes:
    document = _document()
    raw = canonical_json_bytes(document)
    if FAILURE_ID != "0" * 64 and (
        document["failure_id"] != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V91r1 failure changed")
    return raw


def verify_occurrence_balanced_source_failure_bytes_v91r1(raw: bytes) -> dict[str, Any]:
    expected = freeze_occurrence_balanced_source_failure_v91r1()
    if type(raw) is not bytes or raw != expected:
        _fail("V91r1 failure bytes changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V91r1 failure canonical bytes changed")
    return document


__all__ = (
    "FAILURE_ID",
    "freeze_occurrence_balanced_source_failure_v91r1",
    "verify_occurrence_balanced_source_failure_bytes_v91r1",
)
