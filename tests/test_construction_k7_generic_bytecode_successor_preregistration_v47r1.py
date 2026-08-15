from __future__ import annotations

import hashlib

from acfqp import construction_k7_generic_bytecode_failure_v47 as failure
from acfqp import construction_k7_generic_bytecode_successor_preregistration_v47r1 as pre


def test_v47r1_is_fresh_frozen_and_outcome_free() -> None:
    frozen = pre.freeze_generic_bytecode_successor_preregistration_v47r1()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    document = frozen.to_document()
    assert document["frozen_failed_predecessor"]["failure_id"] == failure.FAILURE_ID
    assert document["frozen_failed_predecessor"]["failed_identity_reused"] is False
    assert document["fresh_workloads"]["all_seed_identities_fresh_after_v47_failure"] is True
    assert document["outcome_fields_present"] is False
    assert document["fresh_outcome_execution_performed"] is False


def test_v47r1_closes_target_register_and_executor_contract() -> None:
    document = pre.freeze_generic_bytecode_successor_preregistration_v47r1().to_document()
    engine = document["generic_engine"]
    assert engine["complete_target_state_register_binding_required"] is True
    assert engine["public_anonymous_vm_executor_required"] is True
    assert engine["domain_named_primitive_count"] == 0
    assert engine["lmb_named_primitive_count"] == 0
    assert document["protocol"]["planner_consumes_compiled_world_model_only"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_v47r1_source_closure_is_exact() -> None:
    document = pre.freeze_generic_bytecode_successor_preregistration_v47r1().to_document()
    for fact in document["source_closure"]["source_facts"]:
        raw = (pre.SOURCE_ROOT / fact["relative_path"]).read_bytes()
        assert len(raw) == fact["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == fact["sha256"]
