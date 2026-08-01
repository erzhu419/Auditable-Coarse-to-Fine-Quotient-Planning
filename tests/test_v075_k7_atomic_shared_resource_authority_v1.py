from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from acfqp.accounting_v1 import ReducerEnum
from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime
from acfqp import v075_k7_atomic_shared_resource_authority_v1 as authority
from acfqp import v075_k7_parent_atomic_executor_v1 as parent
from tests.test_v075_k7_atomic_pidfd_runtime_v1 import _successor_request
from tests.test_v075_k7_parent_atomic_executor_v1 import _prepare, _runtime_result


def _parent_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    request, spec, bootstrap = _prepare(tmp_path)
    bootstrap.close()
    child_raw = canonical_json_bytes({"schema": "acfqp.test_child_frame.v1"})
    child_document = {
        "atomic_child_business_frame_id": "1" * 64,
        "child_business_bundle_id": "2" * 64,
    }
    monkeypatch.setattr(parent, "_portable_replay", lambda _request: object())
    monkeypatch.setattr(
        parent.child_v1,
        "verify_v075_k7_atomic_child_business_frame_bytes_v1",
        lambda **_kwargs: dict(child_document),
    )
    observed = _runtime_result(child_raw)
    suffix_raw, two_frame = parent._solve_two_frame_fixed_point(  # noqa: SLF001
        child_raw=child_raw,
        request=request,
        spec=spec,
        child_document=child_document,
        runtime_result=observed,
    )
    result = parent.V075K7ParentAtomicExecutionResultV1(
        parent._RESULT_ISSUER,  # noqa: SLF001
        request,
        spec,
        observed,
        child_raw,
        suffix_raw,
        two_frame,
    )
    return request, result


@pytest.fixture(scope="module")
def authentic_result(tmp_path_factory: pytest.TempPathFactory):
    patcher = pytest.MonkeyPatch()
    try:
        yield _parent_result(tmp_path_factory.mktemp("atomic-shared"), patcher)
    finally:
        patcher.undo()


def test_production_registry_keeps_both_observations_attempt_scope_incomplete(
    authentic_result,
) -> None:
    request, result = authentic_result
    verified = authority.verify_v075_k7_atomic_shared_resource_evidence_v1(
        request=request,
        parent_result=result,
    )
    document = verified.to_document()
    registry = verified.registry.to_document()

    assert document["exact_connected_paths"] == []
    assert document["child_runtime_window_scope_incomplete_paths"] == [
        "memory.working_bytes_peak"
    ]
    assert document["runtime_local_scope_incomplete_paths"] == [
        "process.launches"
    ]
    assert len(document["not_connected_paths"]) == 7
    assert len(registry["rows"]) == 9
    assert [row.path for row in verified.resolutions] == [
        "memory.working_bytes_peak",
        "process.launches",
    ]
    memory, process = verified.resolutions
    assert memory.value == result.runtime_result.memory_peak_bytes
    assert memory.to_document()["reducer"] == ReducerEnum.MAX.value
    assert memory.to_document()["connection_status"] == (
        "VERIFIED_CHILD_RUNTIME_WINDOW_SCOPE_INCOMPLETE"
    )
    assert memory.to_document()["attempt_scope_complete"] is False
    assert memory.to_document()["eligible_as_shared_resource_resolution"] is False
    assert process.value == 1
    assert process.to_document()["reducer"] == ReducerEnum.SUM.value
    assert process.to_document()["attempt_scope_complete"] is False
    assert process.to_document()["eligible_as_shared_resource_resolution"] is False
    assert document["counter_records_issued"] is False
    assert document["official_execution_allowed"] is False


def test_frozen_registry_is_canonical_and_new_issuance_rejects_stale_request(
    authentic_result,
) -> None:
    request, result = authentic_result
    registry = authority.freeze_v075_k7_production_shared_resource_registry_v1(
        request=request,
        spec=result.spec,
    )
    frozen_id = registry.registry_id
    original_nonce = request.request_nonce
    object.__setattr__(request, "request_nonce", "f" * 64)
    try:
        # The already issued artifact is one complete canonical snapshot.
        assert registry.registry_id == frozen_id
        with pytest.raises(
            authority.V075K7AtomicSharedResourceAuthorityV1Error
        ):
            authority.freeze_v075_k7_production_shared_resource_registry_v1(
                request=request,
                spec=result.spec,
            )
    finally:
        object.__setattr__(request, "request_nonce", original_nonce)
    assert request.request_id == request._request_id  # noqa: SLF001


def test_runtime_evidence_order_and_identity_crossing_fail_closed(
    authentic_result,
) -> None:
    request, result = authentic_result
    evidence = result.runtime_result.supervisor_resource_evidence
    assert [
        row["role"] for row in evidence.to_document()["lifecycle_sequence"]
    ] == [
        "PROCESS_LAUNCH",
        "OUTPUT_EOF",
        "PROCESS_REAP",
        "CGROUP_EMPTY",
        "DESCENDANT_SCAN",
        "FINAL_MEMORY_PEAK",
        "MEMORY_CONTROLS_VERIFIED",
    ]

    with pytest.raises(runtime.V075K7AtomicPidfdRuntimeV1Error):
        replace(
            evidence,
            _issuer=runtime._SUPERVISOR_EVIDENCE_ISSUER,  # noqa: SLF001
            output_eof_sequence=evidence.process_reap_sequence,
        )
    crossed = _successor_request("shared-resource-crossed-request")
    with pytest.raises(authority.V075K7AtomicSharedResourceAuthorityV1Error):
        authority.verify_v075_k7_atomic_shared_resource_evidence_v1(
            request=crossed,
            parent_result=result,
        )


def test_numeric_rows_and_source_registry_cannot_be_caller_minted(
    authentic_result,
) -> None:
    request, result = authentic_result
    registry = authority.freeze_v075_k7_production_shared_resource_registry_v1(
        request=request,
        spec=result.spec,
    )
    with pytest.raises(authority.V075K7AtomicSharedResourceAuthorityV1Error):
        authority.V075K7VerifiedSharedResourceResolutionV1(
            authority._RESOLUTION_ISSUER,  # noqa: SLF001
            registry,
            result,
            authority.MEMORY_PATH,
            result.runtime_result.memory_peak_bytes + 1,
        )
    with pytest.raises(authority.V075K7AtomicSharedResourceAuthorityV1Error):
        replace(
            registry,
            _issuer=authority._REGISTRY_ISSUER,  # noqa: SLF001
            runtime_source_sha256="0" * 64,
        )
    with pytest.raises(authority.V075K7AtomicSharedResourceAuthorityV1Error):
        authority.V075K7ProductionSharedResourceRegistryV1(
            object(),
            registry.request,
            registry.spec,
            registry.identity_derivation,
            registry.identity_verification,
            registry.runtime_source_sha256,
            registry.runtime_source_byte_count,
        )
