from __future__ import annotations

import hashlib
from pathlib import Path

from acfqp import construction_k7_all_path_formalization_contract_v180 as subject
from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp.routing_v1 import TerminalCode


def test_v180_contract_is_outcome_free_and_binds_v179() -> None:
    result = subject.freeze_all_path_formalization_contract_v180()
    document = result.to_document()
    assert document["predecessor"]["registered_finite_central_objective_completed"]
    assert document["predecessor"]["v179_bytes_or_claims_mutated"] is False
    assert document["claim_locks"]["v180_terminal_outcomes_accessed"] is False
    assert document["terminal_coverage_contract"]["terminal_codes"] == [
        code.value for code in TerminalCode
    ]


def test_v180_contract_freezes_v9_full_vector_and_economics_order() -> None:
    document = subject.freeze_all_path_formalization_contract_v180().to_document()
    authorities = document["accounting_authorities"]
    assert authorities["registered_leaf_count"] == registry_v9.EXPECTED_V9_LEAF_COUNT
    assert authorities["required_leaf_count_per_vector"] == (
        registry_v9.EXPECTED_V9_REQUIRED_LEAF_COUNT
    )
    assert authorities["nine_shared_resource_receipts_required_per_execution_window"]
    assert authorities["output_bytes_exact_fixed_point_required"]
    assert document["economics_protocol"]["primary_authority"] == (
        "EXACT_WEIGHT_AGNOSTIC_WORK_VECTOR"
    )
    assert document["economics_protocol"][
        "official_scalar_calibration_present_in_this_contract"
    ] is False
    assert document["gate_order"][1] == "COUNTER_COMPLETENESS_GATE"


def test_v180_contract_keeps_all_result_gates_locked() -> None:
    locks = subject.freeze_all_path_formalization_contract_v180().to_document()[
        "claim_locks"
    ]
    assert locks["all_path_native_accounting_complete"] is False
    assert locks["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert locks["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert locks["official_scalar_cost"] is None
    assert locks["official_N_break_even"] is None
    assert locks["official_execution_allowed"] is False


def test_v180_contract_frozen_identity_when_registered() -> None:
    result = subject.freeze_all_path_formalization_contract_v180()
    if subject.EXPECTED_CONTRACT_ID == "0" * 64:
        return
    assert result.formalization_contract_id == subject.EXPECTED_CONTRACT_ID
    assert len(result.canonical_bytes) == subject.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(result.canonical_bytes).hexdigest() == (
        subject.EXPECTED_CANONICAL_SHA256
    )
    frozen = (
        Path(__file__).resolve().parents[1]
        / ".tmp/exact-freeze/v180_all_path_formalization_contract.json"
    ).read_bytes()
    assert frozen == result.canonical_bytes
