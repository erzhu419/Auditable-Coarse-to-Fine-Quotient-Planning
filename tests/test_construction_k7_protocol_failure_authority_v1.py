from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
from typing import Any

import pytest

from acfqp import construction_k7_protocol_failure_authority_v1 as protocol
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.access_protocol_v1 import (
    AccessOperation,
    AccessProtocolViolation,
    AccessRouteScope,
    AccessViolationReason,
    replay_access_protocol,
)
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.phase3e_ids import (
    ACCESS_EVENT_LOG_DOMAIN,
    COMPARISON_VECTOR_DOMAIN,
    COUNTER_RECORD_DOMAIN,
    FORBIDDEN_ACCESS_VIOLATION_DOMAIN,
    WORK_VECTOR_DOMAIN,
    canonical_json_bytes,
    content_id,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def anchors() -> tuple[str, str, str]:
    return (
        _id("protocol-route-attempt"),
        _id("protocol-decision-point"),
        _id("protocol-frozen-rapm"),
    )


@pytest.fixture(scope="module")
def bundle(anchors):
    attempt, point, rapm = anchors
    return protocol.issue_canonical_k7_protocol_failure_bundle_v1(
        route_attempt_id=attempt,
        decision_point_id=point,
        frozen_rapm_id=rapm,
    )


def _resign_complete_document(document: dict[str, Any]) -> bytes:
    """Re-sign every affected identity in the portable bundle.

    This helper deliberately has no semantic knowledge: it demonstrates that
    a valid hash chain is insufficient when event or accounting semantics are
    changed.
    """

    result = deepcopy(document)
    log = result["access_event_log"]
    log_payload = dict(log)
    log_payload.pop("access_event_log_id", None)
    log["access_event_log_id"] = content_id(ACCESS_EVENT_LOG_DOMAIN, log_payload)

    violation = result["forbidden_access_violation"]
    violation["access_event_log_id"] = log["access_event_log_id"]
    violation_payload = dict(violation)
    violation_payload.pop("forbidden_access_violation_id", None)
    violation["forbidden_access_violation_id"] = content_id(
        FORBIDDEN_ACCESS_VIOLATION_DOMAIN, violation_payload
    )

    record_ids: list[str] = []
    for row in result["counter_records"]:
        row["recorder_id"] = protocol._record_id_for(  # noqa: SLF001
            log_id=log["access_event_log_id"],
            violation_id=violation["forbidden_access_violation_id"],
            path=row["path"],
            value=row["value"],
        )
        record_payload = dict(row)
        record_payload.pop("counter_record_id", None)
        row["counter_record_id"] = content_id(
            COUNTER_RECORD_DOMAIN, record_payload
        )
        record_ids.append(row["counter_record_id"])
    result["counter_record_ids"] = record_ids

    work = result["last_valid_prefix_work_vector"]
    work["counter_record_ids"] = record_ids
    work["records"] = deepcopy(result["counter_records"])
    work_payload = {
        key: work[key]
        for key in (
            "schema",
            "counter_registry_id",
            "subject_id",
            "route_kind",
            "counter_record_ids",
        )
    }
    work["work_vector_id"] = content_id(WORK_VECTOR_DOMAIN, work_payload)

    comparison = result["last_valid_prefix_comparison_vector"]
    comparison["work_vector_id"] = work["work_vector_id"]
    comparison_payload = dict(comparison)
    comparison_payload.pop("comparison_vector_id", None)
    comparison["comparison_vector_id"] = content_id(
        COMPARISON_VECTOR_DOMAIN, comparison_payload
    )

    terminal = result["protocol_failure_terminal_authority"]
    terminal["access_event_log_id"] = log["access_event_log_id"]
    terminal["forbidden_access_violation_id"] = violation[
        "forbidden_access_violation_id"
    ]
    terminal["work_vector_id"] = work["work_vector_id"]
    terminal["comparison_vector_id"] = comparison["comparison_vector_id"]
    terminal["counter_record_ids"] = record_ids
    terminal_payload = dict(terminal)
    terminal_payload.pop("protocol_failure_terminal_authority_id", None)
    terminal["protocol_failure_terminal_authority_id"] = protocol._local_id(  # noqa: SLF001
        protocol.PROTOCOL_FAILURE_TERMINAL_AUTHORITY_V1_DOMAIN,
        terminal_payload,
    )

    outer_payload = dict(result)
    outer_payload.pop("protocol_failure_bundle_id", None)
    result["protocol_failure_bundle_id"] = protocol._local_id(  # noqa: SLF001
        protocol.PROTOCOL_FAILURE_BUNDLE_V1_DOMAIN,
        outer_payload,
    )
    return canonical_json_bytes(result)


def _verify(raw: bytes, anchors):
    attempt, point, rapm = anchors
    return protocol.verify_k7_protocol_failure_bundle_bytes_v1(
        raw=raw,
        expected_route_attempt_id=attempt,
        expected_decision_point_id=point,
        expected_frozen_rapm_id=rapm,
    )


def test_real_site_blocker_prevents_a_fabricated_production_claim(bundle) -> None:
    blocker = bundle.blocker
    row = blocker.to_document()
    assert blocker.blocker_code == protocol.BLOCKER_CODE
    assert row["production_runner_module"] == "acfqp.phase3e_runner_v1"
    assert row["protocol_record_symbol"] == "FailClosedAccessController.record"
    assert row["production_predecision_violation_observed"] is False
    assert row["canonical_negative_control_registered"] is True
    assert row["canonical_negative_control_is_production_event"] is False
    assert row["genuine_execution_claimed"] is False


def test_negative_control_uses_exact_shared_profile_and_first_violation(bundle) -> None:
    events = bundle.access_log.events
    assert bundle.access_log.is_frozen is False
    assert len(events) == 2
    assert events[0].operation is AccessOperation.READ_FROZEN_RAPM
    assert events[0].route_scope is AccessRouteScope.COMMON
    assert events[1].operation is AccessOperation.KERNEL_STEP
    assert events[1].route_scope is AccessRouteScope.LOCAL
    with pytest.raises(AccessProtocolViolation) as caught:
        replay_access_protocol(bundle.access_log, bundle.profile)
    assert caught.value.violation == bundle.violation
    assert bundle.violation.reason is (
        AccessViolationReason.PRESELECTION_FORBIDDEN_ACCESS
    )
    assert bundle.violation.offending_sequence_number == 2


def test_last_valid_prefix_is_complete_and_rejected_kernel_never_executes(
    bundle,
) -> None:
    registry = registry_v6.official_counter_registry_v6()
    assert len(bundle.records) == protocol.EXPECTED_COUNTER_RECORD_COUNT == 202
    assert tuple(row.path for row in bundle.records) == registry.required_paths
    assert all(row.observed is True for row in bundle.records)
    assert len({row.record_id for row in bundle.records}) == 202
    assert bundle.work_vector.route_kind is RouteKindEnum.ABSTRACT_FAILED_PREFIX
    values = bundle.work_vector.values
    assert values["route.attempts"] == 1
    assert values["route.successes"] == 0
    assert values["route.failures"] == 1
    assert values["common.protocol_checks"] == 3
    assert values["common.integrity_checks"] == 3
    assert values["common.hash_invocations"] == 3
    assert values["local.materialization_ground_steps"] == 0
    assert values["fallback.ground_steps"] == 0
    assert values["process.launches"] == 0
    assert all(
        values[path] == 0
        for path in values
        if path.startswith(("local.", "fallback.", "rebuild."))
    )


def test_exact_eight_axis_projection_retains_all_work_through_detection(
    bundle,
) -> None:
    profile_bytes = canonical_json_bytes(bundle.profile.to_dict())
    log_bytes = canonical_json_bytes(bundle.access_log.to_dict())
    violation_bytes = canonical_json_bytes(bundle.violation.to_dict())
    assert dict(bundle.comparison_vector.values) == {
        "kernel_transition_calls": 0,
        "nonkernel_compute_events": 9,
        "output_bytes": len(log_bytes) + len(violation_bytes),
        "peak_mounted_bytes": 0,
        "peak_working_bytes": 0,
        "process_launches": 0,
        "read_bytes": len(profile_bytes) + len(log_bytes),
        "staged_bytes": 0,
    }


def test_terminal_is_exactly_protocol_not_integrity_cap_or_infeasibility(
    bundle,
) -> None:
    terminal = bundle.terminal.to_document()
    assert (
        terminal["terminal_scope"],
        terminal["terminal_class"],
        terminal["terminal_code"],
    ) == (
        "ROUTE_ATTEMPT",
        "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "PROTOCOL_FAILURE",
    )
    assert terminal["integrity_failure"] is False
    assert terminal["cap_exhaustion"] is False
    assert terminal["terminal_is_infeasibility_certificate"] is False
    assert terminal["plan_certificate"] is False
    assert terminal["logical_occurrence_closed"] is False
    assert terminal["production_violation_claimed"] is False


def test_independent_bytes_verifier_reconstructs_exact_artifacts(bundle, anchors) -> None:
    verified = _verify(bundle.canonical_bytes, anchors)
    assert verified.bundle_id == bundle.bundle_id
    assert verified.work_vector_id == bundle.work_vector.work_vector_id
    assert verified.comparison_vector_id == (
        bundle.comparison_vector.comparison_vector_id
    )
    assert verified.terminal_authority_id == bundle.terminal.terminal_id
    assert verified.verified_work_vector == bundle.work_vector
    assert verified.verified_comparison_vector == bundle.comparison_vector
    assert verified.to_document()["producer_invoked"] is False


def test_independent_verifier_does_not_call_producer(
    monkeypatch: pytest.MonkeyPatch,
    bundle,
    anchors,
) -> None:
    monkeypatch.setattr(
        protocol,
        "issue_canonical_k7_protocol_failure_bundle_v1",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("producer called")),
    )
    assert _verify(bundle.canonical_bytes, anchors).bundle_id == bundle.bundle_id
    source = inspect.getsource(protocol.verify_k7_protocol_failure_bundle_bytes_v1)
    assert "issue_canonical_k7_protocol_failure_bundle_v1(" not in source


@pytest.mark.parametrize("anchor_index", range(3))
def test_external_identity_transplant_is_rejected(bundle, anchors, anchor_index) -> None:
    changed = list(anchors)
    changed[anchor_index] = _id(f"wrong-anchor-{anchor_index}")
    with pytest.raises(protocol.ConstructionK7ProtocolFailureAuthorityV1Error):
        _verify(bundle.canonical_bytes, tuple(changed))


def test_noncanonical_bundle_bytes_are_rejected(bundle, anchors) -> None:
    with pytest.raises(protocol.ConstructionK7ProtocolFailureAuthorityV1Error):
        _verify(bundle.canonical_bytes + b"\n", anchors)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("terminal_code", "INTEGRITY_FAILURE"),
        ("integrity_failure", True),
        ("cap_exhaustion", True),
        ("terminal_is_infeasibility_certificate", True),
        ("plan_certificate", True),
        ("production_violation_claimed", True),
        ("official_execution_allowed", True),
    ),
)
def test_fully_resigned_terminal_relabels_fail_closed(
    bundle,
    anchors,
    field,
    value,
) -> None:
    document = bundle.to_document()
    document[field] = value
    raw = _resign_complete_document(document)
    with pytest.raises(protocol.ConstructionK7ProtocolFailureAuthorityV1Error):
        _verify(raw, anchors)


def test_fully_resigned_allowed_sequence_cannot_retain_protocol_terminal(
    bundle,
    anchors,
) -> None:
    document = bundle.to_document()
    event = document["access_event_log"]["events"][1]
    event["operation"] = "READ_FROZEN_BUILD_EPOCH"
    event["route_scope"] = "COMMON"
    event["artifact_id"] = _id("frozen-build-epoch")
    raw = _resign_complete_document(document)
    with pytest.raises(
        protocol.ConstructionK7ProtocolFailureAuthorityV1Error,
        match="canonical K7 predecision violation fixture changed",
    ):
        _verify(raw, anchors)


def test_fully_resigned_sequence_gap_is_invalid_not_a_protocol_terminal(
    bundle,
    anchors,
) -> None:
    document = bundle.to_document()
    document["access_event_log"]["events"][1]["sequence_number"] = 3
    raw = _resign_complete_document(document)
    with pytest.raises(
        protocol.ConstructionK7ProtocolFailureAuthorityV1Error,
        match="sequence, or violation bytes are invalid",
    ):
        _verify(raw, anchors)


def test_fully_resigned_counter_inflation_differs_from_exact_replay(
    bundle,
    anchors,
) -> None:
    document = bundle.to_document()
    target = next(
        row
        for row in document["counter_records"]
        if row["path"] == "common.protocol_checks"
    )
    target["value"] += 1
    raw = _resign_complete_document(document)
    with pytest.raises(
        protocol.ConstructionK7ProtocolFailureAuthorityV1Error,
        match="complete last-valid protocol prefix differs",
    ):
        _verify(raw, anchors)


def test_unknown_or_missing_counter_cannot_be_inferred_as_native_zero(
    bundle,
    anchors,
) -> None:
    document = bundle.to_document()
    document["counter_records"].pop()
    raw = _resign_complete_document(document)
    with pytest.raises(protocol.ConstructionK7ProtocolFailureAuthorityV1Error):
        _verify(raw, anchors)


def test_outer_hash_chain_without_semantic_replay_is_insufficient(
    bundle,
    anchors,
) -> None:
    document = bundle.to_document()
    document["forbidden_access_violation"]["reason"] = (
        "PRESELECTION_ROUTE_SCOPE_VIOLATION"
    )
    raw = _resign_complete_document(document)
    with pytest.raises(
        protocol.ConstructionK7ProtocolFailureAuthorityV1Error,
        match="claimed violation differs",
    ):
        _verify(raw, anchors)
