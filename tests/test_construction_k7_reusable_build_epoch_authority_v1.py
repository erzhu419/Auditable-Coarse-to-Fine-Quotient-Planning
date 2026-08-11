from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_reusable_build_epoch_authority_v1 as subject
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_k7_causal_promotion_accounted_executor_v1 as executor_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_REUSABLE_MODEL_OPERATIONAL_TRACE_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:k7-reusable-query-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def test_domains_and_claims_remain_bounded() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert subject.EXPECTED_REQUIRED_BUILD_EPOCH_PATH_COUNT == 100


@pytest.fixture(scope="module")
def real_build_epoch(tmp_path_factory: pytest.TempPathFactory):
    if os.environ.get("ACFQP_RUN_REAL_K7_REUSABLE_BUILD_EPOCH") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_REUSABLE_BUILD_EPOCH=1")
    retained = os.environ.get("ACFQP_REUSABLE_BUILD_EPOCH_TRACE")
    if retained:
        trace_raw = Path(retained).read_bytes()
        envelope = subject.replay_reusable_build_epoch_source_v1(trace_raw)
        trace = loads_canonical_json(trace_raw)
        model_raw = canonical_json_bytes(trace["root_numerical_model"])
        return trace_raw, model_raw, envelope
    root = tmp_path_factory.mktemp("k7-reusable-build-epoch")
    preparation = executor_v1.prepare_v075_k7_causal_promotion_accounted_runtime_v1(
        repository_root=REPOSITORY_ROOT,
        runtime_cas_root=root / "runtime-cas",
    )
    execution = executor_v1.execute_v075_k7_causal_promotion_with_model_export_v2(
        preparation,
        trace_output_path=root / "trace.json",
        construction_fixture_marker="real-reusable-build-epoch",
        timeout_seconds=3_600,
    )
    envelope = subject.issue_reusable_build_epoch_authority_v1(execution)
    assert execution.root_model_bytes is not None
    return execution.trace_raw, execution.root_model_bytes, envelope


def test_real_same_run_model_and_one_hundred_build_paths(real_build_epoch) -> None:
    trace_raw, model_raw, envelope = real_build_epoch

    replayed = planning_v2.replay_v075_numerical_model_bytes_v2(
        model_raw
    )
    assert replayed.model_id == envelope.root_model_id
    assert len(envelope.resolutions) == 100
    assert len(envelope.counter_records) == 100
    assert sum(len(row.ordered_source_record_ids) for row in envelope.resolutions) == 1_200
    assert envelope.values["acquisition.initial_engine_ground_draws"] > 0
    assert envelope.values["build.initial_model_rows_built"] > 0

    document = envelope.to_document()
    assert document["same_run_model_and_native_work_bound"] is True
    assert document["construction_work_zeroed_for_reuse"] is False
    assert document["query_segment_work_included"] is False
    assert document["warm_query_executed"] is False
    assert document["plan_certificate_issued"] is False
    assert document["official_execution_allowed"] is False


def test_real_build_epoch_bytes_replay_and_model_tamper_rejection(
    real_build_epoch,
) -> None:
    trace_raw, _model_raw, envelope = real_build_epoch
    replayed = subject.verify_reusable_build_epoch_authority_bytes_v1(
        source_trace_bytes=trace_raw,
        envelope_bytes=canonical_json_bytes(envelope.to_document()),
    )
    assert replayed.envelope_id == envelope.envelope_id

    changed = loads_canonical_json(trace_raw)
    changed["root_numerical_model"]["threshold_profile_id"] = "0" * 64
    payload = copy.deepcopy(changed)
    payload.pop("operational_trace_id")
    changed["operational_trace_id"] = content_id(
        V075_K7_REUSABLE_MODEL_OPERATIONAL_TRACE_V1_DOMAIN,
        payload,
    )
    with pytest.raises(subject.ConstructionK7ReusableBuildEpochAuthorityV1Error):
        subject.verify_reusable_build_epoch_authority_bytes_v1(
            source_trace_bytes=canonical_json_bytes(changed),
            envelope_bytes=canonical_json_bytes(envelope.to_document()),
        )


def test_real_two_fresh_queries_reuse_one_model_and_expose_frontier(
    real_build_epoch,
) -> None:
    trace_raw, _model_raw, envelope = real_build_epoch
    envelope_bytes = canonical_json_bytes(envelope.to_document())
    first_spec = query_v1.freeze_reusable_abstract_query_spec_v1(
        build_epoch=envelope,
        logical_occurrence_id=_id("fresh-query-1"),
        query_ordinal=0,
    )
    second_spec = query_v1.freeze_reusable_abstract_query_spec_v1(
        build_epoch=envelope,
        logical_occurrence_id=_id("fresh-query-2"),
        query_ordinal=1,
    )
    first = query_v1.run_reusable_abstract_query_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        query=first_spec,
    )
    second = query_v1.run_reusable_abstract_query_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        query=second_spec,
    )

    assert first.query.query_id != second.query.query_id
    assert first.result_id != second.result_id
    assert first.numerical_proof.proof_id == second.numerical_proof.proof_id
    assert first.numerical_proof.model.model_id == envelope.root_model_id
    assert first.numerical_proof.outcome is planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
    assert first.numerical_proof.failed_frontier is not None
    assert first.to_document()["certificate_failed_frontier_present"] is True
    assert first.to_document()["local_ground_recovery_authorized_here"] is False
    assert first.to_document()["ground_recovery_executed_here"] is False
    assert first.to_document()["model_construction_repeated"] is False

    replayed = query_v1.verify_reusable_abstract_query_result_bytes_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        result_bytes=canonical_json_bytes(first.to_document()),
    )
    assert replayed.result_id == first.result_id
