from __future__ import annotations

import hashlib

from acfqp import construction_k7_generic_bytecode_failure_v47 as failure


def test_v47_failure_is_frozen_and_forbids_same_identity_reuse() -> None:
    frozen = failure.freeze_generic_bytecode_failure_v47()
    assert frozen.failure_id == failure.FAILURE_ID
    assert len(frozen.canonical_bytes) == failure.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == failure.EXPECTED_CANONICAL_SHA256
    assert failure.verify_generic_bytecode_failure_v47(frozen) is frozen
    document = frozen.to_document()
    assert document["registered_workload_access"]["same_id_rerun_forbidden"] is True
    assert document["campaign_artifact_issued"] is False
    assert document["sample_tax_result_issued"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_v47_failure_requires_adapter_independent_successor() -> None:
    document = failure.freeze_generic_bytecode_failure_v47().to_document()
    observed = document["first_contract_failure"]
    assert observed["missing_compiled_binding"] == "OPAQUE_RESOURCE_STATE_COLUMN"
    assert observed["missing_public_operation"] == "ANONYMOUS_VM_SUCCESSOR_EXECUTION"
    assert "USE_FRESH_SOURCE_AND_TARGET_IDENTITIES" in document["required_successor_actions"]
