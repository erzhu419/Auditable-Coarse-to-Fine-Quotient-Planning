"""Outcome-free protocol for one fresh V180r7r1 fallback occurrence."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from typing import Any

from acfqp import (
    construction_k7_all_path_production_execution_protocol_v180r3
    as predecessor_protocol,
)
from acfqp import construction_k7_domain_registry_extension_v180r7r1p as domains
from acfqp import (
    construction_k7_full_ground_fallback_execution_failure_freeze_v180r7
    as predecessor_failure,
)
from acfqp import (
    construction_k7_full_ground_fallback_materialized_source_evidence_freeze_v180r7r1
    as materialization,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_PROTOCOL_ID = (
    "0d037ddaa78b4f6fceca4409db55eeb0acb93d8c1d64953430debd108ef31889"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_699
EXPECTED_CANONICAL_SHA256 = (
    "b3c9d354d42f6e951883ba61ea893eac476b964fc752adf83383add60a46eada"
)

PREDECESSOR_PROTOCOL_ID = (
    "ea8aa0a457d09b7056f19f73ca606262fb806f445d0c868708b617244d396e01"
)
PREDECESSOR_FULL_GROUND_FALLBACK_SLOT_ID = (
    "7003f77883606c1416537ad568f8e9d27178b68d79765456816c854b347de63e"
)
PRESERVED_V180R7_AUTHORIZATION_ID = (
    "445851c4b3ceb25be1858e0c4c07e436631486efe12853db8fef4fdf9c5573e9"
)
PRESERVED_V180R7_FAILURE_ID = (
    "bd6e022804f5be7dc7ae22e781ce121fe462277858b058bacf8f201f5b234f79"
)
SOURCE_CLOSURE_REPAIR_ID = (
    "feb8f6034ef1da9050242fe4e112edb285b77bd63a87642196f8fbc7995544c8"
)
MATERIALIZATION_MANIFEST_ID = (
    "1480c3e0a5bcfe7e88f9cbd6a346efd500c17a1826ca656aa527567a0c8ae7f3"
)
MATERIALIZED_SOURCE_TREE_ID = (
    "5cc30a0a9eea4caa239953af930c8382d3194b2f2ad82847eb9c0ba79b7a2993"
)
SOURCE_CLOSURE_ID = (
    "ac3f10ef4eea5c0ecc740d9cecc1991e851a65af198e6696f32bde1965feeb4b"
)
LOGICAL_OCCURRENCE_ID = (
    "293485bc465428ff5b3f923b6d261153a272d30253644076f7dbf19c39cfc3aa"
)
QUERY_ORDINAL = 7
TERMINAL_CODE = "FULL_GROUND_FALLBACK"
EXECUTION_NONCE = hashlib.sha256(
    b"acfqp:v180r7r1:fresh-full-ground-fallback-execution-nonce\x00"
    + MATERIALIZATION_MANIFEST_ID.encode("ascii")
).hexdigest()
EXPECTED_PRODUCTION_EXECUTION_SLOT_ID = (
    "6c344549d8e179b64f53856500bcfba8d31777a6ee652f3a9cebf73951bf35a8"
)

_SLOT_FIELDS = {
    "execution_nonce",
    "logical_occurrence_id",
    "materialization_manifest_id",
    "predecessor_occurrence_slot_id",
    "preserved_v180r7_failure_id",
    "production_execution_slot_id",
    "query_ordinal",
    "source_closure_repair_id",
    "terminal_code",
}


class FullGroundFallbackExecutionProtocolV180r7r1Error(ValueError):
    """The consumed slot or frozen construction lineage changed."""


def _fail(message: str) -> None:
    raise FullGroundFallbackExecutionProtocolV180r7r1Error(message)


def build_full_ground_fallback_execution_protocol_v180r7r1() -> dict[str, Any]:
    consumed = (
        predecessor_protocol.freeze_all_path_production_execution_protocol_v180r3()
    )
    consumed_document = consumed.to_document()
    consumed_slots = [
        row
        for row in consumed_document["production_execution_slots"]
        if row["terminal_code"] == TERMINAL_CODE
    ]
    failed = (
        predecessor_failure.load_frozen_full_ground_fallback_execution_failure_v180r7()
    )
    failure_document = failed.to_document()
    staged = (
        materialization.load_frozen_full_ground_fallback_materialized_source_v180r7r1()
    )
    staged_document = staged.to_document()
    if not (
        consumed.production_execution_protocol_id == PREDECESSOR_PROTOCOL_ID
        and len(consumed_slots) == 1
        and consumed_slots[0]["production_execution_slot_id"]
        == PREDECESSOR_FULL_GROUND_FALLBACK_SLOT_ID
        and consumed_slots[0]["execution_nonce"] != EXECUTION_NONCE
        and failed.failure_id == PRESERVED_V180R7_FAILURE_ID
        and failure_document["fallback_execution_authorization_id"]
        == PRESERVED_V180R7_AUTHORIZATION_ID
        and failure_document["same_authorization_rerun_forbidden"] is True
        and failure_document["success_claimed"] is False
        and staged.materialization_manifest_id == MATERIALIZATION_MANIFEST_ID
        and staged.materialized_source_tree_id == MATERIALIZED_SOURCE_TREE_ID
        and staged.source_closure_id == SOURCE_CLOSURE_ID
        and staged_document["source_closure_repair_id"]
        == SOURCE_CLOSURE_REPAIR_ID
        and staged_document["scientific_occurrence_executed"] is False
        and staged_document["production_outcome_accessed"] is False
    ):
        _fail("consumed failure or materialized-source lineage changed")

    slot_payload = {
        "predecessor_occurrence_slot_id": (
            PREDECESSOR_FULL_GROUND_FALLBACK_SLOT_ID
        ),
        "execution_nonce": EXECUTION_NONCE,
        "terminal_code": TERMINAL_CODE,
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "query_ordinal": QUERY_ORDINAL,
        "preserved_v180r7_failure_id": PRESERVED_V180R7_FAILURE_ID,
        "source_closure_repair_id": SOURCE_CLOSURE_REPAIR_ID,
        "materialization_manifest_id": MATERIALIZATION_MANIFEST_ID,
    }
    slot = {
        **slot_payload,
        "production_execution_slot_id": domains.extension_content_id_v180r7r1p(
            domains.CONSTRUCTION_K7_FALLBACK_PRODUCTION_EXECUTION_SLOT_V180R7R1P_DOMAIN,
            slot_payload,
        ),
    }
    if set(slot) != _SLOT_FIELDS:
        raise AssertionError("V180r7r1 execution slot field set changed")
    if slot["production_execution_slot_id"] != EXPECTED_PRODUCTION_EXECUTION_SLOT_ID:
        _fail("V180r7r1 frozen execution slot identity changed")
    payload = {
        "schema": "acfqp.full_ground_fallback_execution_protocol.v180r7r1",
        "predecessor_production_execution_protocol_id": PREDECESSOR_PROTOCOL_ID,
        "preserved_v180r7_authorization_id": PRESERVED_V180R7_AUTHORIZATION_ID,
        "preserved_v180r7_failure_id": PRESERVED_V180R7_FAILURE_ID,
        "source_closure_repair_id": SOURCE_CLOSURE_REPAIR_ID,
        "materialization_manifest_id": MATERIALIZATION_MANIFEST_ID,
        "materialized_source_tree_id": MATERIALIZED_SOURCE_TREE_ID,
        "unchanged_v2_source_closure_id": SOURCE_CLOSURE_ID,
        "production_execution_slot": slot,
        "singular_fresh_slot_count": 1,
        "consumed_v180r3_slot_reused": False,
        "consumed_v180r7_authorization_reused": False,
        "same_failed_identity_rerun_forbidden": True,
        "fresh_process_or_occurrence_boundary_required": True,
        "one_isolated_worker_no_concurrent_campaign": True,
        "concurrent_workspace_mutation_during_one_shot_occurrence_out_of_scope": (
            True
        ),
        "counter_record_work_vector_comparison_vector_required": True,
        "registered_record_to_record_v6_to_v9_lift_required": True,
        "historical_summary_to_counter_translation_forbidden": True,
        "materialized_construction_work_is_separate_from_route_vectors": True,
        "output_fixed_point_required": True,
        "producer_free_replay_required": True,
        "protocol_frozen_before_any_v180r7r1_outcome": True,
        "production_outcome_accessed": False,
        "fresh_production_occurrence_count": 0,
        "partial_campaign_cannot_unlock_any_gate": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "construction_only": True,
    }
    return {
        **payload,
        "fallback_execution_protocol_id": domains.extension_content_id_v180r7r1p(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_PROTOCOL_V180R7R1P_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FullGroundFallbackExecutionProtocolV180r7r1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    protocol_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        if not (
            self._issuer is _ISSUER
            and type(document) is dict
            and canonical_json_bytes(document) == self.canonical_bytes
            and document.get("fallback_execution_protocol_id")
            == self.protocol_id
        ):
            _fail("V180r7r1 execution protocol is foreign or noncanonical")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


@lru_cache(maxsize=1)
def freeze_full_ground_fallback_execution_protocol_v180r7r1(
) -> FullGroundFallbackExecutionProtocolV180r7r1:
    document = build_full_ground_fallback_execution_protocol_v180r7r1()
    raw = canonical_json_bytes(document)
    if EXPECTED_PROTOCOL_ID != "0" * 64 and not (
        document["fallback_execution_protocol_id"] == EXPECTED_PROTOCOL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V180r7r1 frozen execution protocol identity changed")
    return FullGroundFallbackExecutionProtocolV180r7r1(
        _ISSUER,
        raw,
        document["fallback_execution_protocol_id"],
    )


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_PROTOCOL_ID",
    "EXPECTED_PRODUCTION_EXECUTION_SLOT_ID",
    "FullGroundFallbackExecutionProtocolV180r7r1",
    "FullGroundFallbackExecutionProtocolV180r7r1Error",
    "build_full_ground_fallback_execution_protocol_v180r7r1",
    "freeze_full_ground_fallback_execution_protocol_v180r7r1",
)
