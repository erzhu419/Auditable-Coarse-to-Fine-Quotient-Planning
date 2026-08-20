"""Frozen typed V76 source-stage failure before target execution."""

from __future__ import annotations

import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v76f as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PREREGISTRATION_ID = "30169836395c025b2c86223f7c0a0716677a1076a333c2a4f475ffcf9fffde2b"
FAILURE_ID = "87d538791718b5cb95a1e97e944a3fe066d4061f4e8bfd10a7cf85aba97c4fa7"
EXPECTED_CANONICAL_BYTE_COUNT = 1_344
EXPECTED_CANONICAL_SHA256 = "1d6be261fc514b70946e142b077a3ab659e70db3581405b6227726bc8c79d1ee"


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.three_family_source_abstention_failure.v76",
        "preregistration_id": PREREGISTRATION_ID,
        "campaign_issued": False,
        "campaign_id": None,
        "failure_phase": "THREE_FAMILY_SOURCE_PROCESS_POOL",
        "failure_class": "REGISTERED_SOURCE_OCCURRENCE_HAS_NO_REUSABLE_MODEL",
        "exception_type": "TypeError",
        "exception_message": "'NoneType' object is not subscriptable",
        "exception_source": {
            "relative_path": "src/acfqp/structural_rank_transfer_campaign_core_v75r4.py",
            "function": "_source",
            "operation": "model['source_layout']",
        },
        "failed_family": "BALANCED_BATCH_REFINEMENT",
        "failed_source_seed": 751_102,
        "root_cause": (
            "PREDECESSOR_SOURCE_ACQUISITION_ABSTAINED_AND_NO_REUSABLE_MODEL_WAS_AVAILABLE"
        ),
        "target_execution_started": False,
        "partial_target_outcomes_recovered_or_claimed": False,
        "registered_gate_evaluated": False,
        "same_identity_rerun_allowed": False,
        "corrective_successor_requires_fresh_target_identities": True,
        "corrective_successor_must_retain_source_abstention": True,
        "scientific_success_claimed": False,
        "producer_free_verification_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "status": "PREREGISTERED_SOURCE_FAILURE_PRESERVED_NO_CAMPAIGN",
    }
    return {
        **payload,
        "failure_id": domains.extension_content_id_v76f(payload),
    }


def freeze_three_family_failure_v76() -> bytes:
    raw = canonical_json_bytes(_document())
    document = loads_canonical_json(raw)
    if FAILURE_ID != "0" * 64 and (
        document["failure_id"] != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("frozen V76 failure changed")
    return raw


__all__ = ("FAILURE_ID", "freeze_three_family_failure_v76")
