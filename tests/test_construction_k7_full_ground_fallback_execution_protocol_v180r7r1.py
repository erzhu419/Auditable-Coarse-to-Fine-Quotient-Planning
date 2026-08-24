from __future__ import annotations

import hashlib

import pytest

from acfqp import (
    construction_k7_all_path_production_execution_protocol_v180r3
    as predecessor,
)
from acfqp import construction_k7_domain_registry_extension_v180r7r1p as domains
from acfqp import (
    construction_k7_full_ground_fallback_execution_protocol_v180r7r1
    as protocol,
)
from acfqp import (
    construction_k7_full_ground_fallback_production_terminal_finalizer_v180r7r1
    as finalizer,
)
from acfqp.phase3e_ids import canonical_json_bytes


@pytest.fixture(scope="module")
def frozen_protocol() -> protocol.FullGroundFallbackExecutionProtocolV180r7r1:
    return protocol.freeze_full_ground_fallback_execution_protocol_v180r7r1()


def test_v180r7r1_protocol_has_one_exact_fresh_slot(
    frozen_protocol: protocol.FullGroundFallbackExecutionProtocolV180r7r1,
) -> None:
    document = frozen_protocol.to_document()
    slot = document["production_execution_slot"]
    assert set(slot) == {
        "production_execution_slot_id",
        "predecessor_occurrence_slot_id",
        "execution_nonce",
        "terminal_code",
        "logical_occurrence_id",
        "query_ordinal",
        "preserved_v180r7_failure_id",
        "source_closure_repair_id",
        "materialization_manifest_id",
    }
    slot_payload = dict(slot)
    slot_id = slot_payload.pop("production_execution_slot_id")
    assert slot_id == domains.extension_content_id_v180r7r1p(
        domains.CONSTRUCTION_K7_FALLBACK_PRODUCTION_EXECUTION_SLOT_V180R7R1P_DOMAIN,
        slot_payload,
    )
    consumed = [
        row
        for row in predecessor.freeze_all_path_production_execution_protocol_v180r3()
        .to_document()["production_execution_slots"]
        if row["terminal_code"] == "FULL_GROUND_FALLBACK"
    ][0]
    assert slot["predecessor_occurrence_slot_id"] == consumed[
        "production_execution_slot_id"
    ]
    assert slot_id != consumed["production_execution_slot_id"]
    assert slot["execution_nonce"] != consumed["execution_nonce"]
    assert slot["logical_occurrence_id"] == (
        "293485bc465428ff5b3f923b6d261153a272d30253644076f7dbf19c39cfc3aa"
    )
    assert slot["query_ordinal"] == 7
    assert slot["preserved_v180r7_failure_id"] == (
        "bd6e022804f5be7dc7ae22e781ce121fe462277858b058bacf8f201f5b234f79"
    )
    assert slot["source_closure_repair_id"] == (
        "feb8f6034ef1da9050242fe4e112edb285b77bd63a87642196f8fbc7995544c8"
    )
    assert slot["materialization_manifest_id"] == (
        "1480c3e0a5bcfe7e88f9cbd6a346efd500c17a1826ca656aa527567a0c8ae7f3"
    )


def test_v180r7r1_protocol_identity_and_claim_locks_are_frozen(
    frozen_protocol: protocol.FullGroundFallbackExecutionProtocolV180r7r1,
) -> None:
    document = frozen_protocol.to_document()
    payload = dict(document)
    identity = payload.pop("fallback_execution_protocol_id")
    assert identity == protocol.EXPECTED_PROTOCOL_ID
    assert identity == domains.extension_content_id_v180r7r1p(
        domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_PROTOCOL_V180R7R1P_DOMAIN,
        payload,
    )
    assert len(frozen_protocol.canonical_bytes) == 2_699
    assert hashlib.sha256(frozen_protocol.canonical_bytes).hexdigest() == (
        "b3c9d354d42f6e951883ba61ea893eac476b964fc752adf83383add60a46eada"
    )
    assert canonical_json_bytes(document) == frozen_protocol.canonical_bytes
    assert document["consumed_v180r3_slot_reused"] is False
    assert document["consumed_v180r7_authorization_reused"] is False
    assert document["one_isolated_worker_no_concurrent_campaign"] is True
    assert document[
        "concurrent_workspace_mutation_during_one_shot_occurrence_out_of_scope"
    ] is True
    assert document["production_outcome_accessed"] is False
    assert document["fresh_production_occurrence_count"] == 0
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert document["BREAK_EVEN_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False


def test_real_finalizer_slot_adapter_accepts_frozen_protocol(
    frozen_protocol: protocol.FullGroundFallbackExecutionProtocolV180r7r1,
) -> None:
    adapted = finalizer._slot()
    assert adapted.execution_protocol_id == frozen_protocol.protocol_id
    assert dict(adapted.slot) == frozen_protocol.to_document()[
        "production_execution_slot"
    ]
