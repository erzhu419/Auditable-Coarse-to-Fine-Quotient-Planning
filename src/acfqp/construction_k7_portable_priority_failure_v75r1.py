"""Frozen typed execution failure for V75r1 before campaign issuance."""

from __future__ import annotations

import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v75r1 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PREREGISTRATION_ID = "b36ec9a233328d4493386d9bfa3e362886397bc11c07a64104490b7db9ab4acd"
FAILURE_ID = "1024e36371f1cf3eada5ed3fab62e8910e1eb820041f2d6a79729c9835864078"
EXPECTED_CANONICAL_BYTE_COUNT = 1_390
EXPECTED_CANONICAL_SHA256 = "c7a1788da99f587de35bba2422263e1dd71d76c8ff98b66c2219254b5f8002ae"


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.portable_priority_failure.v75r1",
        "preregistration_id": PREREGISTRATION_ID,
        "campaign_issued": False,
        "campaign_id": None,
        "failure_phase": "FRESH_TARGET_PROCESS_POOL_EXECUTION",
        "failure_class": "ADAPTER_FLAT_ACTION_RECEIPT_TYPE_MISMATCH",
        "exception_type": "AttributeError",
        "exception_message": (
            "'CoupledExchangeAction' object has no attribute 'key'"
        ),
        "exception_source": {
            "relative_path": "src/acfqp/generic_portable_certificate_query_priority_v44.py",
            "function": "run_portable_priority_certificate_episode_v44.query",
            "operation": "FlatRawTransitionV4(selected_action=adapter.action(key))",
        },
        "root_cause": (
            "REAL_DOMAIN_ADAPTER_ACTION_RETURNS_DOMAIN_ACTION_WHILE_RECEIPT_REQUIRES_FLAT_RAW_ACTION"
        ),
        "source_stage_completed_before_failure": True,
        "partial_target_outcomes_recovered_or_claimed": False,
        "registered_gate_evaluated": False,
        "scientific_success_or_reduction_claimed": False,
        "same_identity_rerun_allowed": False,
        "corrective_successor_requires_fresh_target_identities": True,
        "failure_preserved_before_corrective_successor": True,
        "producer_free_verification_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "status": "PREREGISTERED_EXECUTION_FAILURE_PRESERVED_NO_CAMPAIGN",
    }
    return {
        **payload,
        "failure_id": domains.extension_content_id_v75r1(
            domains.CONSTRUCTION_K7_PORTABLE_PRIORITY_FAILURE_V75R1_DOMAIN,
            payload,
        ),
    }


def freeze_portable_priority_failure_v75r1() -> bytes:
    raw = canonical_json_bytes(_document())
    document = loads_canonical_json(raw)
    if FAILURE_ID != "0" * 64 and (
        document["failure_id"] != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("frozen V75r1 failure changed")
    return raw


__all__ = ("FAILURE_ID", "freeze_portable_priority_failure_v75r1")
