from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile

import pytest

from acfqp import construction_k7_query_bound_recovery_overlay_v1 as overlay_v1
from acfqp import construction_k7_query_bound_recovery_request_v1 as request_v1
from acfqp import construction_k7_query_bound_supervised_executor_v1 as subject
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:query-bound-supervisor-test:v1\x00" + label.encode()
    ).hexdigest()


def test_public_surface_and_shared_path_boundary_are_frozen() -> None:
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundSupervisedExecutorV1Error",
        "DEFAULT_TIMEOUT_SECONDS",
        "EXPECTED_CHILD_INTEGRITY_OBLIGATIONS",
        "EXPECTED_CHILD_PROTOCOL_OBLIGATIONS",
        "INPUT_ROLES",
        "PARENT_INTEGRITY_OBLIGATIONS",
        "PARENT_PROTOCOL_OBLIGATIONS",
        "PRE_OUTPUT_SHARED_PATHS",
        "QueryBoundPreOutputMeasurementV1",
        "QueryBoundRuntimePreparationV1",
        "SupervisedQueryBoundExecutionV1",
        "execute_query_bound_accounted_v1",
        "prepare_query_bound_accounted_runtime_v1",
        "require_supervised_query_bound_execution_v1",
    }
    assert subject.PRE_OUTPUT_SHARED_PATHS == (
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
        "io.mounted_bytes_peak",
        "io.read_bytes",
        "io.staged_bytes",
        "memory.working_bytes_peak",
        "process.launches",
    )
    assert {
        subject.PREPARATION_DOMAIN,
        subject.REQUEST_DOMAIN,
        subject.TRACE_DOMAIN,
        subject.MEASUREMENT_DOMAIN,
    } <= PHASE3E_DOMAIN_TAGS


def test_runtime_preparation_is_recursive_and_content_addressed() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-qb-runtime-cas-", dir="/tmp") as root:
        prepared = subject.prepare_query_bound_accounted_runtime_v1(
            repository_root=Path(__file__).parents[1],
            runtime_cas_root=root,
        )
        assert prepared.manifest.file_count > 100
        assert prepared.manifest.total_bytes > 1_000_000
        assert set(subject.PRIMARY_RUNTIME_ROOT_MODULES) <= set(
            prepared.source_closure.root_modules
        )
        assert sum(
            row.startswith(subject.RUNTIME_DYNAMIC_ROOT_PREFIX)
            for row in prepared.source_closure.root_modules
        ) > 100
        assert prepared.to_document()["official_execution_allowed"] is False
        assert len(prepared.preparation_id) == 64


def test_supervised_execution_is_not_caller_mintable() -> None:
    with pytest.raises(subject.ConstructionK7QueryBoundSupervisedExecutorV1Error):
        subject.require_supervised_query_bound_execution_v1(object())  # type: ignore[arg-type]


@pytest.fixture(scope="module")
def real_supervised_execution():
    if os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_SUPERVISOR") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_QUERY_BOUND_SUPERVISOR=1")
    retained = os.environ.get("ACFQP_CAUSAL_RECOVERY_TRACE")
    if not retained:
        pytest.fail("ACFQP_CAUSAL_RECOVERY_TRACE must name the retained real trace")
    repository_root = Path(__file__).parents[1]
    trace_raw = Path(retained).read_bytes()
    envelope = build_v1.replay_reusable_build_epoch_source_v1(trace_raw)
    envelope_bytes = canonical_json_bytes(envelope.to_document())
    query = query_v1.freeze_reusable_abstract_query_spec_v1(
        build_epoch=envelope,
        logical_occurrence_id=_id("fresh-supervised-query"),
        query_ordinal=0,
    )
    root = query_v1.run_reusable_abstract_query_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        query=query,
    )
    root_bytes = canonical_json_bytes(root.to_document())
    overlay = overlay_v1.apply_query_bound_cached_recovery_overlay_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_bytes,
    )
    overlay_bytes = canonical_json_bytes(overlay.to_document())
    request = request_v1.prepare_query_bound_recovery_request_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_bytes,
        overlay_bytes=overlay_bytes,
    )
    with tempfile.TemporaryDirectory(prefix="acfqp-qb-supervisor-", dir="/tmp") as temporary:
        temporary_root = Path(temporary)
        preparation = subject.prepare_query_bound_accounted_runtime_v1(
            repository_root=repository_root,
            runtime_cas_root=temporary_root / "cas",
        )
        result = subject.execute_query_bound_accounted_v1(
            preparation,
            source_trace_bytes=trace_raw,
            build_epoch_envelope_bytes=envelope_bytes,
            root_query_result_bytes=root_bytes,
            overlay_bytes=overlay_bytes,
            request_bytes=canonical_json_bytes(request.to_document()),
            trace_output_path=temporary_root / "operational-trace.json",
        )
        yield result


def test_real_supervisor_materializes_all_preoutput_shared_evidence(
    real_supervised_execution,
) -> None:
    result = subject.require_supervised_query_bound_execution_v1(
        real_supervised_execution
    )
    measurement = result.measurement
    fixed = dict(measurement.fixed_values)
    assert set(fixed) == set(subject.PRE_OUTPUT_SHARED_PATHS) - {
        "io.mounted_bytes_peak"
    }
    assert all(value > 0 for value in fixed.values())
    assert fixed["process.launches"] == 1
    assert measurement.input_file_count == 5
    assert measurement.input_total_bytes > 0
    assert measurement.pre_output_mounted_bytes_peak > 0
    assert measurement.mounted_bytes_peak(0) == measurement.pre_output_mounted_bytes_peak
    assert len(result.recorded_stages) == 5
    assert sum(len(row.work_vector.records) for row in result.recorded_stages) == 1_010
    assert result.science_summary["terminal_class"] == "PLAN_CERTIFICATE"
    assert result.science_summary["terminal_code"] == "FULL_GROUND_FALLBACK"
    document = result.to_document()
    assert document["eight_pre_output_shared_paths_owner_correct"] is True
    assert document["io_output_bytes_pending_fixed_point_and_commit"] is True
    assert document["occurrence_work_vector_issued"] is False
    assert document["official_execution_allowed"] is False
