from __future__ import annotations

import hashlib
from pathlib import Path

from acfqp.accounting_v1 import RouteKindEnum
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp import construction_k7_standard_2048_accounted_artifacts_v12 as artifacts
from acfqp import construction_k7_standard_2048_accounted_preregistration_v12 as pre
from acfqp import (
    construction_k7_standard_2048_accounted_independent_verifier_v12 as independent,
)
from acfqp import construction_k7_standard_2048_instrumented_runtime_v12 as runtime
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp.phase3e_ids import canonical_json_bytes, content_id


def _subject(label: str) -> str:
    return content_id(pre.FUTURE_DOMAINS["decision"], {"test_subject": label})


def test_operational_segment_closes_eight_role_output_fixed_point(
    tmp_path: Path,
) -> None:
    draft = runtime.smoke_first_registered_decision_v12()
    subject = _subject("operational-failed-certificate-prefix")
    output = tmp_path / "segment"
    result = artifacts.materialize_operational_segment_v12(
        subject_id=subject,
        segment_role="FAILED_ABSTRACT_CERTIFICATE_COMMON_PREFIX",
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        base_values=draft.common_counter_values,
        business_document={
            "certificate": dict(draft.certificate),
            "route": draft.route,
        },
        trace_document=draft.to_document(),
        terminal_document={
            "terminal_scope": "NONTERMINAL_ROUTE_SEGMENT",
            "terminal_class": "SEGMENT_CLOSURE_NONTERMINAL",
            "terminal_code": "ABSTRACT_CERTIFICATE_FAILED_FALLBACK_PENDING",
        },
        output_directory=output,
        output_key="episode-0000/decision-0000/common",
        allocation_profile="PER_DECISION_OUTPUT_ONLY_GLOBAL_PEAKS_ELSEWHERE",
    )
    assert result.fixed_point.output_bytes == sum(
        row[1] for row in result.output_commit.role_rows
    )
    assert tuple(row[0] for row in result.output_commit.role_rows) == (
        fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
    )
    assert len(tuple(output.iterdir())) == 8
    for role, byte_count, digest in result.output_commit.role_rows:
        raw = (output / f"{role}.json").read_bytes()
        assert len(raw) == byte_count
        assert hashlib.sha256(raw).hexdigest() == digest
    vector = result.accounting_chain.work_vector
    assert vector.value("io.output_bytes") == result.fixed_point.output_bytes
    assert vector.value("io.mounted_bytes_peak") >= result.fixed_point.output_bytes
    recorder = {
        row.path: row.recorder_id for row in vector.records
    }
    assert all(
        recorder[path] == result.measurement.measurement_id
        for path in artifacts.SHARED_PATHS
    )


def test_evaluation_output_is_typed_and_never_gets_comparison_vector(
    tmp_path: Path,
) -> None:
    counters = runtime.NativeCounterSetV12()
    counters.add("evaluation.exact_states_expanded", 3)
    counters.add("evaluation.exact_actions_evaluated", 7)
    counters.add("evaluation.exact_ground_steps", 7)
    counters.add("evaluation.exact_outcome_rows", 19)
    counters.add("evaluation.exact_bellman_backups", 7)
    counters.add("evaluation.exact_subproof_cache_lookups", 13)
    counters.add("evaluation.exact_subproof_cache_hits", 5)
    counters.add("evaluation.exact_subproof_cache_misses", 8)
    counters.add("evaluation.hash_invocations", 1)
    counters.add("evaluation.semantic_integrity_checks", 1)
    counters.add("evaluation.semantic_protocol_checks", 1)
    subject = _subject("evaluation-only")
    output = tmp_path / "evaluation"
    result = artifacts.materialize_evaluation_v12(
        subject_id=subject,
        transport_document={
            "schema": "test.evaluation.transport",
            "subject_id": subject,
        },
        exact_document={"selected_action": "LEFT", "exact": True},
        forced_document=None,
        base_values=counters.freeze(),
        transport_output_bytes=113,
        working_bytes_peak=4096,
        output_directory=output,
        output_key="episode-0000/decision-0001/evaluation",
    )
    assert result.work_vector.value("evaluation.io_output_bytes") == (
        113 + len(result.canonical_bytes)
    )
    assert result.work_vector.value("evaluation.io_mounted_bytes_peak") >= len(
        result.canonical_bytes
    )
    assert result.work_vector.value("evaluation.memory_working_bytes_peak") == 4096
    assert all(
        result.work_vector.value(path) == 0
        for path in (
            "io.output_bytes",
            "fallback.ground_steps",
            "target.execution_ground_steps",
        )
    )
    raw = (output / "EVALUATION_WORK_VECTOR.json").read_bytes()
    assert raw == result.canonical_bytes
    assert result.to_document()["comparison_vector_issued"] is False


def test_evaluation_artifact_is_independently_reconstructed_from_transport(
    tmp_path: Path,
) -> None:
    counters = runtime.NativeCounterSetV12()
    counters.add("evaluation.exact_states_expanded", 2)
    counters.add("evaluation.exact_actions_evaluated", 5)
    counters.add("evaluation.exact_ground_steps", 5)
    counters.add("evaluation.exact_outcome_rows", 11)
    counters.add("evaluation.exact_bellman_backups", 5)
    counters.add("evaluation.hash_invocations")
    worker_values = dict(counters.freeze())
    subject = _subject("independent-evaluation-replay")
    exact = {"selected_action": "LEFT", "exact": True}
    transport_payload = {
        "schema": "acfqp.standard_2048_accounted_evaluation_transport.v12",
        "schema_version": pre.SCHEMA_VERSION,
        "accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "episode_index": 0,
        "decision_index": 0,
        "state_before_decision": {"test_state": True},
        "selected_action": "LEFT",
        "exact_plan": exact,
        "forced_selected_action_exact_evaluation": None,
        "selected_action_exact_value_and_loss_equivalent": True,
        "selected_action_label_identical": True,
        "evaluation_counter_values": worker_values,
        "operational_route_work_present": False,
    }
    transport = {
        **transport_payload,
        "accounted_counter_bundle_id": content_id(
            pre.FUTURE_DOMAINS["counter_bundle"], transport_payload
        ),
    }
    parent_values = dict(worker_values)
    parent_values["evaluation.hash_invocations"] += 1
    parent_values["evaluation.semantic_integrity_checks"] += 1
    parent_values["evaluation.semantic_protocol_checks"] += 1
    parent_values["evaluation.io_read_bytes"] = len(canonical_json_bytes(transport))
    result = artifacts.materialize_evaluation_v12(
        subject_id=subject,
        transport_document=transport,
        exact_document=exact,
        forced_document=None,
        base_values=parent_values,
        transport_output_bytes=len(canonical_json_bytes(transport)),
        working_bytes_peak=pre.EPISODE_WORKER_WORKING_BYTES_PEAK_UPPER,
        output_directory=tmp_path / "evaluation",
        output_key="evaluation",
    )
    full = result.to_document()
    summary = {
        "accounted_counter_bundle_id": full["accounted_counter_bundle_id"],
        "work_vector_id": result.work_vector.work_vector_id,
        "accounting_measurement_id": result.measurement[
            "accounting_measurement_id"
        ],
        "output_commit_id": result.output_commit.output_commit_id,
        "output_key": "evaluation",
        "evaluation.io.output_bytes": result.work_vector.value(
            "evaluation.io_output_bytes"
        ),
        "comparison_vector_issued": False,
    }
    seen: set[Path] = set()
    replayed = independent._verify_evaluation_bundle(
        root=tmp_path,
        summary=summary,
        seen=seen,
        expected_subject_id=subject,
        expected_transport_id=transport["accounted_counter_bundle_id"],
        expected_episode_index=0,
        expected_decision_index=0,
        expected_state={"test_state": True},
        expected_action="LEFT",
    )
    assert replayed == result.work_vector
    assert seen == {(tmp_path / "evaluation" / "EVALUATION_WORK_VECTOR.json").resolve()}
