from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_integrity_failure_authority_v1 as integrity
from acfqp.accounting_v1 import (
    CounterRecordV1,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.phase3e_ids import canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def context() -> integrity.K7IntegrityAttemptContextV1:
    return integrity.K7IntegrityAttemptContextV1(
        structural_id=_id("integrity-structural"),
        query_id=_id("integrity-query"),
        selected_plan_id=_id("integrity-plan"),
        threshold_profile_id=_id("integrity-threshold"),
        build_epoch_id=_id("integrity-build-epoch"),
        logical_occurrence_id=_id("integrity-logical-occurrence"),
        route_attempt_id=_id("integrity-route-attempt"),
        decision_point_id=_id("integrity-decision-point"),
        transaction_id=_id("integrity-transaction"),
    )


@pytest.fixture(scope="module")
def expected_bytes() -> bytes:
    return canonical_json_bytes(
        {
            "schema": "acfqp.test_frozen_model.v1",
            "model_epoch": 7,
            "payload": [1, 2, 3],
        }
    )


@pytest.fixture(scope="module")
def expected_identity(expected_bytes: bytes) -> integrity.K7ExpectedArtifactIdentityV1:
    return integrity.freeze_k7_expected_artifact_identity_v1(
        artifact_role="FROZEN_RAPM",
        artifact_schema="acfqp.test_frozen_model.v1",
        content_domain="acfqp:test-frozen-model:v1",
        source_locator_id=_id("frozen-model-source-locator"),
        expected_bytes=expected_bytes,
    )


def _event(
    context: integrity.K7IntegrityAttemptContextV1,
    *,
    sequence_number: int = 1,
    phase: integrity.IntegrityFailureCutoffV1 = (
        integrity.IntegrityFailureCutoffV1.MIDROUTE_EXECUTION
    ),
    deltas: tuple[tuple[str, int], ...] = (
        ("common.abstract_bellman_backups", 7),
        ("io.staged_bytes", 11),
        ("local.causal_candidate_evaluations", 2),
        ("local.materialization_ground_steps", 3),
        ("process.launches", 1),
        ("solver.attempts", 1),
    ),
) -> integrity.K7IntegrityAccessEventV1:
    return integrity.K7IntegrityAccessEventV1(
        context_id=context.context_id,
        sequence_number=sequence_number,
        phase=phase,
        event_kind="TRUSTED_PREFIX_COUNTER_CHECKPOINT",
        evidence_ref_id=_id(f"prefix-evidence-{sequence_number}-{phase.value}"),
        counter_deltas=tuple(
            integrity.K7IntegrityCounterDeltaV1(path, value)
            for path, value in sorted(deltas)
        ),
    )


@pytest.fixture(scope="module")
def integrity_case(context, expected_identity):
    # Deliberately noncanonical and different-length bytes exercise every
    # identity check while remaining preserved verbatim in the portable proof.
    offending_bytes = b'{"model_epoch":8, "schema":"forged"}\n'
    event = _event(context)
    bundle = integrity.issue_k7_integrity_failure_bundle_v1(
        context=context,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        cutoff=integrity.IntegrityFailureCutoffV1.MIDROUTE_EXECUTION,
        prefix_events=(event,),
        expected_identity=expected_identity,
        offending_bytes=offending_bytes,
    )
    return offending_bytes, event, bundle


def _resign_outer(document: dict[str, Any]) -> bytes:
    result = deepcopy(document)
    payload = dict(result)
    payload.pop("integrity_failure_bundle_id", None)
    result["integrity_failure_bundle_id"] = integrity._local_id(  # noqa: SLF001
        integrity.INTEGRITY_FAILURE_BUNDLE_V1_DOMAIN,
        payload,
    )
    return canonical_json_bytes(result)


def _project_v6(work: WorkVectorV1):
    registry = registry_v6.official_counter_registry_v6()
    profile = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(registry, profile)
    axes = {axis.name: 0 for axis in profile.axes}
    for term in actual.terms:
        contribution = work.values[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            axes[term.target_axis] += contribution
        else:
            axes[term.target_axis] = max(axes[term.target_axis], contribution)
    from acfqp.accounting_v1 import ComparisonVectorV1

    return ComparisonVectorV1(
        profile.comparison_profile_id,
        work.work_vector_id,
        work.subject_id,
        work.route_kind,
        tuple(sorted(axes.items())),
    )


def test_identity_mismatch_uses_expected_anchor_and_exact_observed_bytes(
    context,
    expected_identity,
    integrity_case,
) -> None:
    offending_bytes, _event_row, bundle = integrity_case
    receipt = bundle.read_receipt

    assert receipt.context_id == context.context_id
    assert receipt.expected_identity_id == expected_identity.identity_id
    assert receipt.expected_artifact_id == expected_identity.expected_artifact_id
    assert receipt.expected_sha256 == expected_identity.expected_sha256
    assert receipt.expected_byte_count == expected_identity.expected_byte_count
    assert receipt.observed_artifact_id == integrity._raw_domain_id(  # noqa: SLF001
        expected_identity.content_domain,
        offending_bytes,
    )
    assert receipt.observed_sha256 == hashlib.sha256(offending_bytes).hexdigest()
    assert receipt.observed_byte_count == len(offending_bytes)
    assert receipt.violation_reasons == (
        integrity.IntegrityViolationReasonV1.NONCANONICAL_BYTES,
        integrity.IntegrityViolationReasonV1.CONTENT_ID_MISMATCH,
        integrity.IntegrityViolationReasonV1.SHA256_MISMATCH,
        integrity.IntegrityViolationReasonV1.BYTE_COUNT_MISMATCH,
    )
    assert bundle.offending_bytes == offending_bytes


def test_last_valid_prefix_is_complete_202_record_work_and_eight_axis_projection(
    integrity_case,
) -> None:
    offending_bytes, _event_row, bundle = integrity_case
    registry = registry_v6.official_counter_registry_v6()
    records = bundle.records

    assert len(records) == integrity.EXPECTED_COUNTER_RECORD_COUNT == 202
    assert tuple(row.path for row in records) == registry.required_paths
    assert all(row.observed is True for row in records)
    assert len({row.record_id for row in records}) == 202
    assert "integrity.bytes_hashed" not in {row.path for row in records}
    assert bundle.work_vector.records == records
    assert bundle.work_vector.route_kind is RouteKindEnum.LOCAL_ATTEMPT
    assert _project_v6(bundle.work_vector) == bundle.comparison_vector
    assert len(bundle.comparison_vector.values) == 8
    axes = dict(bundle.comparison_vector.values)
    assert axes == {
        "kernel_transition_calls": 3,
        "nonkernel_compute_events": 12,
        "output_bytes": 0,
        "peak_mounted_bytes": 0,
        "peak_working_bytes": 0,
        "process_launches": 1,
        "read_bytes": len(offending_bytes),
        "staged_bytes": 11,
    }
    values = bundle.work_vector.values
    assert values["route.attempts"] == 1
    assert values["route.successes"] == 0
    assert values["route.failures"] == 1
    assert values["solver.attempts"] == 1
    assert values["solver.successes"] == 0
    assert values["solver.failures"] == 1
    assert values["process.launches"] == 1
    assert values["process.exit_successes"] == 0
    assert values["process.exit_failures"] == 1
    assert values["common.integrity_checks"] == 1
    assert values["common.protocol_checks"] == 1
    assert values["common.hash_invocations"] == 1
    assert values["io.read_bytes"] == len(offending_bytes)


def test_native_zero_partition_is_explicit_and_complete(integrity_case) -> None:
    _offending_bytes, _event_row, bundle = integrity_case
    attestation = bundle.prefix_completeness
    zero_records = tuple(row for row in bundle.records if row.value == 0)
    nonzero_records = tuple(row for row in bundle.records if row.value != 0)

    assert attestation.counter_record_ids == tuple(
        row.record_id for row in bundle.records
    )
    assert attestation.native_zero_paths == tuple(row.path for row in zero_records)
    assert attestation.native_zero_recorder_ids == tuple(
        row.recorder_id for row in zero_records
    )
    assert attestation.nonzero_paths == tuple(row.path for row in nonzero_records)
    assert len(zero_records) + len(nonzero_records) == 202
    assert attestation.prior_prefix_event_count == 1


def test_terminal_is_only_route_attempt_integrity_noncertificate(integrity_case) -> None:
    _offending_bytes, _event_row, bundle = integrity_case
    document = bundle.to_document()
    terminal = bundle.terminal_authority.to_document()

    for row in (document, terminal):
        assert row["terminal_scope"] == "ROUTE_ATTEMPT"
        assert row["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
        assert row["terminal_code"] == "INTEGRITY_FAILURE"
        assert row["specific_cause"] == "ARTIFACT_IDENTITY_MISMATCH"
        assert row["protocol_failure"] is False
        assert row["plan_certificate"] is False
        assert row["infeasibility_certificate"] is False
        assert row["logical_occurrence_closed"] is False
        assert row["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    assert document["workload_economics_gate_status"] == (
        "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )


def test_independent_byte_verifier_replays_without_calling_producer(
    monkeypatch,
    context,
    expected_identity,
    integrity_case,
) -> None:
    _offending_bytes, _event_row, bundle = integrity_case

    def forbidden_producer(**_kwargs):
        raise AssertionError("producer was invoked by independent verifier")

    monkeypatch.setattr(
        integrity,
        "issue_k7_integrity_failure_bundle_v1",
        forbidden_producer,
    )
    verification = integrity.verify_k7_integrity_failure_bundle_bytes_v1(
        raw=bundle.canonical_bytes,
        expected_identity_id=expected_identity.identity_id,
        expected_context_id=context.context_id,
    )

    assert verification.bundle_id == bundle.bundle_id
    assert verification.bundle_sha256 == hashlib.sha256(
        bundle.canonical_bytes
    ).hexdigest()
    assert verification.bundle_byte_count == len(bundle.canonical_bytes)
    assert verification.verified_work_vector == bundle.work_vector
    assert verification.verified_comparison_vector == bundle.comparison_vector
    assert verification.to_document()["producer_invoked"] is False
    assert verification.to_document()["verification_lane"] == "evaluation"


@pytest.mark.parametrize(
    "route_kind",
    [
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        RouteKindEnum.LOCAL_ATTEMPT,
        RouteKindEnum.DIRECT_FALLBACK,
    ],
)
def test_empty_last_valid_prefix_is_still_complete_for_noncertificate_routes(
    context,
    expected_identity,
    route_kind: RouteKindEnum,
) -> None:
    bundle = integrity.issue_k7_integrity_failure_bundle_v1(
        context=context,
        route_kind=route_kind,
        cutoff=integrity.IntegrityFailureCutoffV1.EARLY_INPUT_READ,
        prefix_events=(),
        expected_identity=expected_identity,
        offending_bytes=b"not-json",
    )
    assert len(bundle.records) == 202
    assert bundle.work_vector.route_kind is route_kind
    assert bundle.work_vector.value("route.attempts") == 1
    assert bundle.work_vector.value("route.failures") == 1
    assert bundle.terminal_authority.terminal_id


def test_abstract_certificate_route_cannot_end_as_integrity_certificate(
    context,
    expected_identity,
) -> None:
    with pytest.raises(
        integrity.ConstructionK7IntegrityFailureAuthorityV1Error,
        match="cannot use an abstract-certificate route kind",
    ):
        integrity.issue_k7_integrity_failure_bundle_v1(
            context=context,
            route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            cutoff=integrity.IntegrityFailureCutoffV1.EARLY_INPUT_READ,
            prefix_events=(),
            expected_identity=expected_identity,
            offending_bytes=b"not-json",
        )


def test_matching_bytes_cannot_be_relabelled_as_integrity_failure(
    context,
    expected_identity,
    expected_bytes,
) -> None:
    with pytest.raises(
        integrity.ConstructionK7IntegrityFailureAuthorityV1Error,
        match="no integrity failure exists",
    ):
        integrity.issue_k7_integrity_failure_bundle_v1(
            context=context,
            route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
            cutoff=integrity.IntegrityFailureCutoffV1.EARLY_INPUT_READ,
            prefix_events=(),
            expected_identity=expected_identity,
            offending_bytes=expected_bytes,
        )


@pytest.mark.parametrize(
    ("events", "cutoff", "message"),
    [
        ("gapped", integrity.IntegrityFailureCutoffV1.MIDROUTE_EXECUTION, "not contiguous"),
        ("post_cutoff", integrity.IntegrityFailureCutoffV1.PRELAUNCH_FREEZE, "post-cutoff"),
        ("unknown_path", integrity.IntegrityFailureCutoffV1.MIDROUTE_EXECUTION, "unknown or optional"),
        ("wrong_family", integrity.IntegrityFailureCutoffV1.MIDROUTE_EXECUTION, "route-family exclusivity"),
        ("bad_reconciliation", integrity.IntegrityFailureCutoffV1.MIDROUTE_EXECUTION, "more solver outcomes"),
    ],
)
def test_protocol_violations_are_rejected_not_relabelled_as_integrity(
    context,
    expected_identity,
    events: str,
    cutoff: integrity.IntegrityFailureCutoffV1,
    message: str,
) -> None:
    if events == "gapped":
        rows = (_event(context, sequence_number=2),)
    elif events == "post_cutoff":
        rows = (_event(context),)
    elif events == "unknown_path":
        rows = (_event(context, deltas=(("integrity.bytes_hashed", 1),)),)
    elif events == "wrong_family":
        rows = (_event(context, deltas=(("fallback.ground_steps", 1),)),)
    else:
        rows = (
            _event(
                context,
                deltas=(("solver.attempts", 1), ("solver.successes", 2)),
            ),
        )
    with pytest.raises(
        integrity.ConstructionK7IntegrityFailureAuthorityV1Error,
        match=message,
    ):
        integrity.issue_k7_integrity_failure_bundle_v1(
            context=context,
            route_kind=RouteKindEnum.LOCAL_ATTEMPT,
            cutoff=cutoff,
            prefix_events=rows,
            expected_identity=expected_identity,
            offending_bytes=b"not-json",
        )


def test_noncanonical_outer_bytes_and_id_only_bundle_fail_closed(
    context,
    expected_identity,
    integrity_case,
) -> None:
    _offending_bytes, _event_row, bundle = integrity_case
    with pytest.raises(
        integrity.ConstructionK7IntegrityFailureAuthorityV1Error,
        match="noncanonical",
    ):
        integrity.verify_k7_integrity_failure_bundle_bytes_v1(
            raw=bundle.canonical_bytes + b" ",
            expected_identity_id=expected_identity.identity_id,
            expected_context_id=context.context_id,
        )
    with pytest.raises(
        integrity.ConstructionK7IntegrityFailureAuthorityV1Error,
        match="field set changed",
    ):
        integrity.verify_k7_integrity_failure_bundle_bytes_v1(
            raw=canonical_json_bytes(
                {"integrity_failure_bundle_id": bundle.bundle_id}
            ),
            expected_identity_id=expected_identity.identity_id,
            expected_context_id=context.context_id,
        )


def test_fully_resigned_anchor_transplant_is_rejected(
    context,
    expected_bytes,
    expected_identity,
) -> None:
    replacement_identity = integrity.freeze_k7_expected_artifact_identity_v1(
        artifact_role="FROZEN_RAPM",
        artifact_schema="acfqp.test_frozen_model.v1",
        content_domain="acfqp:test-frozen-model:v1",
        source_locator_id=_id("attacker-controlled-source"),
        expected_bytes=expected_bytes,
    )
    forged = integrity.issue_k7_integrity_failure_bundle_v1(
        context=context,
        route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        cutoff=integrity.IntegrityFailureCutoffV1.EARLY_INPUT_READ,
        prefix_events=(),
        expected_identity=replacement_identity,
        offending_bytes=b"attacker-bytes",
    )
    assert replacement_identity.identity_id != expected_identity.identity_id
    with pytest.raises(
        integrity.ConstructionK7IntegrityFailureAuthorityV1Error,
        match="transplanted away from an external anchor",
    ):
        integrity.verify_k7_integrity_failure_bundle_bytes_v1(
            raw=forged.canonical_bytes,
            expected_identity_id=expected_identity.identity_id,
            expected_context_id=context.context_id,
        )


def test_fully_resigned_protocol_terminal_relabel_is_rejected(
    context,
    expected_identity,
    integrity_case,
) -> None:
    _offending_bytes, _event_row, bundle = integrity_case
    document = bundle.to_document()
    terminal = document["integrity_failure_terminal_authority"]
    terminal["terminal_code"] = "PROTOCOL_FAILURE"
    terminal["protocol_failure"] = True
    terminal_payload = dict(terminal)
    terminal_payload.pop("integrity_failure_terminal_authority_id")
    terminal["integrity_failure_terminal_authority_id"] = integrity._local_id(  # noqa: SLF001
        integrity.INTEGRITY_TERMINAL_AUTHORITY_V1_DOMAIN,
        terminal_payload,
    )

    with pytest.raises(
        integrity.ConstructionK7IntegrityFailureAuthorityV1Error,
        match="terminal class, identity, or lock changed",
    ):
        integrity.verify_k7_integrity_failure_bundle_bytes_v1(
            raw=_resign_outer(document),
            expected_identity_id=expected_identity.identity_id,
            expected_context_id=context.context_id,
        )


def test_fully_resigned_work_counter_attack_fails_independent_replay(
    context,
    expected_identity,
    integrity_case,
) -> None:
    _offending_bytes, _event_row, bundle = integrity_case
    document = bundle.to_document()
    registry = registry_v6.official_counter_registry_v6()

    record_documents = deepcopy(document["counter_records"])
    target_index = next(
        index
        for index, row in enumerate(record_documents)
        if row["path"] == "io.read_bytes"
    )
    old = CounterRecordV1.from_dict(record_documents[target_index])
    forged_value = old.value + 1
    forged_record = CounterRecordV1(
        old.counter_registry_id,
        old.path,
        forged_value,
        True,
        integrity._record_id_for(  # noqa: SLF001
            context_id=context.context_id,
            access_sequence_id=bundle.access_sequence.sequence_id,
            path=old.path,
            value=forged_value,
        ),
        old.semantics_id,
        old.owner,
        old.unit,
        old.lane,
        old.scope,
        old.reducer,
    )
    record_documents[target_index] = forged_record.to_dict()
    records = tuple(CounterRecordV1.from_dict(row) for row in record_documents)
    forged_work = WorkVectorV1(
        registry.registry_id,
        context.route_attempt_id,
        RouteKindEnum.LOCAL_ATTEMPT,
        records,
    )
    forged_comparison = _project_v6(forged_work)

    document["counter_records"] = [row.to_dict() for row in records]
    document["counter_record_ids"] = [row.record_id for row in records]
    document["last_valid_prefix_work_vector"] = forged_work.to_dict()
    document["last_valid_prefix_comparison_vector"] = forged_comparison.to_dict()
    completeness = document["integrity_prefix_completeness"]
    completeness["work_vector_id"] = forged_work.work_vector_id
    completeness["comparison_vector_id"] = forged_comparison.comparison_vector_id
    completeness["counter_record_ids"] = [row.record_id for row in records]
    completeness_payload = dict(completeness)
    completeness_payload.pop("integrity_prefix_completeness_id")
    completeness["integrity_prefix_completeness_id"] = integrity._local_id(  # noqa: SLF001
        integrity.INTEGRITY_PREFIX_COMPLETENESS_V1_DOMAIN,
        completeness_payload,
    )
    terminal = document["integrity_failure_terminal_authority"]
    terminal["work_vector_id"] = forged_work.work_vector_id
    terminal["comparison_vector_id"] = forged_comparison.comparison_vector_id
    terminal["counter_record_ids"] = [row.record_id for row in records]
    terminal["prefix_completeness_id"] = completeness[
        "integrity_prefix_completeness_id"
    ]
    terminal_payload = dict(terminal)
    terminal_payload.pop("integrity_failure_terminal_authority_id")
    terminal["integrity_failure_terminal_authority_id"] = integrity._local_id(  # noqa: SLF001
        integrity.INTEGRITY_TERMINAL_AUTHORITY_V1_DOMAIN,
        terminal_payload,
    )

    with pytest.raises(
        integrity.ConstructionK7IntegrityFailureAuthorityV1Error,
        match="CounterRecords are incomplete or changed",
    ):
        integrity.verify_k7_integrity_failure_bundle_bytes_v1(
            raw=_resign_outer(document),
            expected_identity_id=expected_identity.identity_id,
            expected_context_id=context.context_id,
        )


def test_caller_cannot_mint_expected_identity_or_terminal(
    context,
    expected_identity,
    integrity_case,
) -> None:
    with pytest.raises(
        integrity.ConstructionK7IntegrityFailureAuthorityV1Error,
        match="caller-minted",
    ):
        integrity.K7ExpectedArtifactIdentityV1(
            object(),
            expected_identity.artifact_role,
            expected_identity.artifact_schema,
            expected_identity.content_domain,
            expected_identity.source_locator_id,
            expected_identity.expected_artifact_id,
            expected_identity.expected_sha256,
            expected_identity.expected_byte_count,
        )

    _offending_bytes, _event_row, bundle = integrity_case
    authority = bundle.terminal_authority
    with pytest.raises(
        integrity.ConstructionK7IntegrityFailureAuthorityV1Error,
        match="caller-minted",
    ):
        integrity.K7IntegrityFailureTerminalAuthorityV1(
            object(),
            context,
            authority.route_kind,
            authority.cutoff,
            authority.expected_identity_id,
            authority.read_receipt_id,
            authority.access_sequence_id,
            authority.prefix_completeness_id,
            authority.work_vector_id,
            authority.comparison_vector_id,
            authority.counter_record_ids,
            authority.violation_reasons,
        )
