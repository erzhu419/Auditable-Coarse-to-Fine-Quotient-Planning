"""Freeze the preregistered V182r1 non-halting confirmation failure."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v182r1 as domains
from acfqp import construction_k7_open_world_machine_execution_preregistration_v182r1 as preregistration
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_FAILURE_ID = (
    "efa82614489dbe9b05ccd25a6d44022a96219df5b0ca5f8a139ec54e4bb805be"
)
EXPECTED_FAILURE_BYTE_COUNT = 586
EXPECTED_FAILURE_SHA256 = (
    "4089aad4c6689fda243ae03e00c27aba4bf0081b2e4d51177d5555077e336ddd"
)
EXPECTED_PROGRESS_IDS = (
    "a76fb88a2cb62e0465190b1598521e5d279b2285d489145724a4835ce7ed3bfb",
    "6ba47949d996b71fbc02ceabc02c52df83d25e35bb4c264eb3f7c486b6801982",
    "0e2936019fc2705815f92952a9a33a788bfd25b48b34a08013330031072f1884",
)
EXPECTED_PROGRESS_SHA256 = (
    "8dc316f2393cf104fd9f23e4d3cfe4ba1968ece4a102e50265157b6f0a90b9fe",
    "09ba869d94e334cdd9f17bb3f72ba3e3dd33198c7be130f701957263bc7f4502",
    "a71026446f946a15a75d6900f7a7fbcb10d8d19d52f8e60bcbccac5ccd4b2586",
)


def verify_open_world_machine_failure_v182r1(
    failure_bytes: bytes,
    progress_bytes: tuple[bytes, ...],
) -> dict[str, Any]:
    document = loads_canonical_json(failure_bytes)
    if type(document) is not dict:
        raise ValueError("V182r1 failure is not one object")
    payload = dict(document)
    failure_id = payload.pop("failure_id", None)
    if not (
        canonical_json_bytes(document) == failure_bytes
        and len(failure_bytes) == EXPECTED_FAILURE_BYTE_COUNT
        and hashlib.sha256(failure_bytes).hexdigest() == EXPECTED_FAILURE_SHA256
        and failure_id == EXPECTED_FAILURE_ID
        and failure_id
        == domains.extension_content_id_v182r1(
            domains.CONSTRUCTION_K7_FAILURE_V182R1_DOMAIN,
            payload,
        )
        and document["execution_preregistration_id"]
        == preregistration.EXPECTED_PREREGISTRATION_ID
        and document["failure_type"] == "OpenWorldMachineCompiledModelV182Error"
        and document["failure_message"]
        == "compiled V182 program did not halt within its frozen budget"
        and document["progress_checkpoint_count"] == 3
        and document["same_identity_rerun_forbidden"] is True
        and document["scientific_success_claimed"] is False
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_execution_allowed"] is False
    ):
        raise ValueError("V182r1 failure identity or semantics changed")
    if len(progress_bytes) != 3:
        raise ValueError("V182r1 retained progress denominator changed")
    previous = None
    for sequence, (raw, expected_id, expected_sha) in enumerate(
        zip(
            progress_bytes,
            EXPECTED_PROGRESS_IDS,
            EXPECTED_PROGRESS_SHA256,
            strict=True,
        )
    ):
        checkpoint = loads_canonical_json(raw)
        if type(checkpoint) is not dict:
            raise ValueError("V182r1 progress checkpoint is not an object")
        checkpoint_payload = dict(checkpoint)
        checkpoint_id = checkpoint_payload.pop("progress_checkpoint_id", None)
        if not (
            canonical_json_bytes(checkpoint) == raw
            and hashlib.sha256(raw).hexdigest() == expected_sha
            and checkpoint_id == expected_id
            and checkpoint_id
            == domains.extension_content_id_v182r1(
                domains.CONSTRUCTION_K7_PROGRESS_CHECKPOINT_V182R1_DOMAIN,
                checkpoint_payload,
            )
            and checkpoint["sequence"] == sequence
            and checkpoint["previous_checkpoint_id"] == previous
            and checkpoint["execution_preregistration_id"]
            == preregistration.EXPECTED_PREREGISTRATION_ID
            and checkpoint["official_execution_allowed"] is False
        ):
            raise ValueError("V182r1 retained progress chain changed")
        previous = checkpoint_id
    return {
        "failure_id": failure_id,
        "progress_checkpoint_ids": list(EXPECTED_PROGRESS_IDS),
        "failure_preserved": True,
        "same_identity_rerun_forbidden": True,
        "scientific_success_claimed": False,
    }


def verify_retained_open_world_machine_failure_v182r1(root: Path) -> dict[str, Any]:
    return verify_open_world_machine_failure_v182r1(
        (root / "FAILURE.json").read_bytes(),
        tuple(path.read_bytes() for path in sorted((root / "progress").glob("*.json"))),
    )


__all__ = (
    "EXPECTED_FAILURE_ID",
    "verify_open_world_machine_failure_v182r1",
    "verify_retained_open_world_machine_failure_v182r1",
)
