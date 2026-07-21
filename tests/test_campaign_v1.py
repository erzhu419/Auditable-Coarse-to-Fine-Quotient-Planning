from __future__ import annotations

import copy
import hashlib
from dataclasses import replace

import pytest

from acfqp.access_protocol_v1 import (
    AccessOperation,
    AccessProtocolViolation,
    AccessRouteScope,
    FailClosedAccessController,
)
from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    RouteKindEnum,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.campaign_v1 import (
    CERTIFICATE_COVERAGE_FAIL,
    CampaignClosureSummaryV1,
    CampaignOccurrenceClosureV1,
    CampaignV1Error,
    LogicalOccurrenceV1,
    RebuildEventV1,
    RebuildPolicyV1,
    RouteAttemptV1,
)
from acfqp.routing_v1 import (
    RouteDecisionContextV1,
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    semantic_verifier_spec_v1,
    verify_forbidden_access_violation_semantics_v1,
    verify_terminal_classification_semantics_v1,
    verify_work_vector_semantics_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _record(
    role: SemanticRole,
    lane: LaneEnum = LaneEnum.OPERATIONAL,
) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    spec = semantic_verifier_spec_v1(role)
    return CounterRecordV1.observe(
        registry,
        spec.counter_path_for_lane(lane),
        1,
        recorder_id=f"campaign-{role.value.lower()}-verifier-v1",
    )


def _occurrence(
    index: int,
    policy: RebuildPolicyV1,
    *,
    suffix: str,
    workload_spec_id: str,
) -> LogicalOccurrenceV1:
    return LogicalOccurrenceV1(
        workload_spec_id,
        _id("protocol"),
        index,
        _id(f"structural-{suffix}"),
        _id(f"query-{suffix}"),
        _id(f"plan-{suffix}"),
        _id("threshold"),
        _id(f"epoch-{suffix}-1"),
        policy.rebuild_policy_id,
    )


def _protocol_terminal_result(
    occurrence: LogicalOccurrenceV1,
    attempt: RouteAttemptV1,
    *,
    suffix: str,
    protocol_id: str | None = None,
):
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    context = RouteDecisionContextV1(
        _id(f"preregister-{suffix}"),
        occurrence.protocol_id if protocol_id is None else protocol_id,
        comparison.comparison_profile_id,
        registry.registry_id,
        occurrence.structural_id,
        occurrence.query_id,
        occurrence.selected_plan_id,
        occurrence.threshold_profile_id,
        attempt.build_epoch_id,
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
    )
    point = _id(f"point-{suffix}")
    binding = AttestationContextV1(
        context,
        point,
        TypedNotApplicable("preselection failure has no transaction"),
        1,
    )
    controller = FailClosedAccessController(attempt.route_attempt_id, point)
    with pytest.raises(AccessProtocolViolation) as caught:
        controller.record(AccessOperation.KERNEL_STEP, AccessRouteScope.LOCAL)
    protocol = verify_forbidden_access_violation_semantics_v1(
        caught.value.violation,
        access_log=controller.snapshot(),
        profile=controller.profile,
        binding=binding,
        verification_work_record=_record(SemanticRole.PROTOCOL_ACCESS),
    )
    values = {path: 0 for path in registry.required_paths}
    work = registry.materialize(
        subject_id=attempt.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        records=explicit_records_v1(
            registry, values, recorder_id="campaign-native-recorder-v1"
        ),
    )
    work_result = verify_work_vector_semantics_v1(
        work,
        binding=binding,
        verification_work_record=_record(SemanticRole.WORK_VECTOR),
    )
    evidence = tuple(
        sorted(
            (
                protocol.attestation.verification_attestation_id,
                work_result.attestation.verification_attestation_id,
            )
        )
    )
    terminal = TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
        TerminalCode.PROTOCOL_FAILURE,
        context.route_decision_context_id,
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
        point,
        TypedNotApplicable("preselection failure has no transaction"),
        work.work_vector_id,
        evidence,
    )
    terminal_binding = AttestationContextV1(
        context,
        point,
        TypedNotApplicable("preselection failure has no transaction"),
        1,
        LaneEnum.EVALUATION,
    )
    result = verify_terminal_classification_semantics_v1(
        terminal,
        evidence_results=(work_result, protocol),
        binding=terminal_binding,
        verification_work_record=_record(
            SemanticRole.TERMINAL_CLASSIFICATION,
            LaneEnum.EVALUATION,
        ),
    )
    return terminal, result


def _raw_terminal(
    occurrence: LogicalOccurrenceV1,
    attempt: RouteAttemptV1,
    code: TerminalCode,
) -> TerminalArtifactV1:
    class_by_code = {
        TerminalCode.ABSTRACT_CERTIFIED: TerminalClass.PLAN_CERTIFICATE,
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: (
            TerminalClass.INFEASIBILITY_CERTIFICATE
        ),
        TerminalCode.REBUILD_REQUIRED: (
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
        ),
    }
    return TerminalArtifactV1(
        "ROUTE_ATTEMPT",
        class_by_code[code],
        code,
        _id("raw-route-context"),
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
        TypedNotApplicable("raw"),
        TypedNotApplicable("raw"),
        _id("raw-work"),
        (_id("raw-attestation"),),
    )


def test_raw_hash_only_plan_and_infeasibility_cannot_enter_campaign_close() -> None:
    policy = RebuildPolicyV1()
    occurrence = _occurrence(
        1, policy, suffix="raw", workload_spec_id=_id("raw-workload")
    )
    attempt = RouteAttemptV1.initial(occurrence)
    for code in (
        TerminalCode.ABSTRACT_CERTIFIED,
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE,
    ):
        raw = _raw_terminal(occurrence, attempt, code)
        with pytest.raises(
            CampaignV1Error, match="verified TERMINAL_CLASSIFICATION"
        ):
            CampaignOccurrenceClosureV1.close(
                occurrence,
                policy,
                (attempt,),
                (raw,),  # type: ignore[arg-type] - attack input
                ((raw.actual_work_vector_id,),),
                _id(f"raw-sum-{code.value}"),
            )


def test_verified_protocol_terminal_closes_and_summary_uses_occurrence_denominator() -> None:
    workload = _id("verified-workload")
    policy = RebuildPolicyV1()
    occurrence = _occurrence(1, policy, suffix="verified", workload_spec_id=workload)
    attempt = RouteAttemptV1.initial(occurrence)
    terminal, result = _protocol_terminal_result(
        occurrence, attempt, suffix="verified"
    )
    closure = CampaignOccurrenceClosureV1.close(
        occurrence,
        policy,
        (attempt,),
        (result,),
        ((terminal.actual_work_vector_id,),),
        _id("verified-occurrence-sum"),
    )
    summary = CampaignClosureSummaryV1.summarize(
        workload, (occurrence,), (closure,), (result,)
    )
    assert summary.closure_denominator == 1
    assert summary.total_route_attempt_count == 1
    assert summary.noncertificate_count == 1
    assert summary.plan_certificate_count == 0
    assert summary.infeasibility_certificate_count == 0
    assert summary.official_run_valid is False
    assert summary.certificate_coverage_gate == CERTIFICATE_COVERAGE_FAIL
    assert summary.official_execution_allowed is False


def test_summary_rejects_missing_or_other_terminal_authority() -> None:
    workload = _id("summary-authority-workload")
    policy = RebuildPolicyV1()
    occurrence = _occurrence(1, policy, suffix="first", workload_spec_id=workload)
    attempt = RouteAttemptV1.initial(occurrence)
    terminal, result = _protocol_terminal_result(occurrence, attempt, suffix="first")
    closure = CampaignOccurrenceClosureV1.close(
        occurrence,
        policy,
        (attempt,),
        (result,),
        ((terminal.actual_work_vector_id,),),
        _id("first-sum"),
    )
    with pytest.raises(CampaignV1Error, match="one closure and one verified"):
        CampaignClosureSummaryV1.summarize(
            workload, (occurrence,), (closure,), ()
        )

    other = _occurrence(2, policy, suffix="other", workload_spec_id=workload)
    other_attempt = RouteAttemptV1.initial(other)
    _, other_result = _protocol_terminal_result(
        other, other_attempt, suffix="other"
    )
    with pytest.raises(CampaignV1Error, match="does not match"):
        CampaignClosureSummaryV1.summarize(
            workload, (occurrence,), (closure,), (other_result,)
        )


def test_campaign_rejects_semantic_terminal_from_another_protocol_context() -> None:
    workload = _id("protocol-context-workload")
    policy = RebuildPolicyV1()
    occurrence = _occurrence(
        1, policy, suffix="protocol-context", workload_spec_id=workload
    )
    attempt = RouteAttemptV1.initial(occurrence)
    terminal, result = _protocol_terminal_result(
        occurrence,
        attempt,
        suffix="protocol-context",
        protocol_id=_id("foreign-protocol"),
    )
    with pytest.raises(CampaignV1Error, match="another occurrence, query, attempt"):
        CampaignOccurrenceClosureV1.close(
            occurrence,
            policy,
            (attempt,),
            (result,),
            ((terminal.actual_work_vector_id,),),
            _id("foreign-protocol-sum"),
        )


def test_raw_rebuild_terminal_cannot_authorize_retry_or_rebuild_event() -> None:
    policy = RebuildPolicyV1.allowing_one(_id("recipe"))
    occurrence = _occurrence(
        1, policy, suffix="retry", workload_spec_id=_id("retry-workload")
    )
    first = RouteAttemptV1.initial(occurrence)
    raw = _raw_terminal(occurrence, first, TerminalCode.REBUILD_REQUIRED)
    with pytest.raises(CampaignV1Error, match="verified REBUILD_REQUIRED"):
        RouteAttemptV1.retry(
            occurrence,
            policy,
            first,
            raw,  # type: ignore[arg-type] - transport attack
            _id("retry-epoch-2"),
        )
    second_candidate = RouteAttemptV1(
        occurrence.logical_occurrence_id,
        2,
        _id("retry-epoch-2"),
        first.route_attempt_id,
    )
    with pytest.raises(CampaignV1Error, match="verified TERMINAL_CLASSIFICATION"):
        RebuildEventV1.authorize(
            occurrence,
            policy,
            first,
            raw,  # type: ignore[arg-type] - transport attack
            second_candidate,
            _id("rebuild-work"),
        )
    with pytest.raises(CampaignV1Error, match="verified TERMINAL_CLASSIFICATION"):
        CampaignOccurrenceClosureV1.close(
            occurrence,
            policy,
            (first,),
            (raw,),  # type: ignore[arg-type]
            ((raw.actual_work_vector_id,),),
            _id("retry-raw-sum"),
        )


def test_verified_campaign_artifacts_roundtrip_and_hash_tamper_reject() -> None:
    workload = _id("roundtrip-workload")
    policy = RebuildPolicyV1()
    occurrence = _occurrence(1, policy, suffix="roundtrip", workload_spec_id=workload)
    attempt = RouteAttemptV1.initial(occurrence)
    terminal, result = _protocol_terminal_result(
        occurrence, attempt, suffix="roundtrip"
    )
    closure = CampaignOccurrenceClosureV1.close(
        occurrence,
        policy,
        (attempt,),
        (result,),
        ((terminal.actual_work_vector_id,),),
        _id("roundtrip-sum"),
    )
    summary = CampaignClosureSummaryV1.summarize(
        workload, (occurrence,), (closure,), (result,)
    )
    for artifact, loader, id_field in (
        (policy, RebuildPolicyV1.from_dict, "rebuild_policy_id"),
        (occurrence, LogicalOccurrenceV1.from_dict, "logical_occurrence_id"),
        (attempt, RouteAttemptV1.from_dict, "route_attempt_id"),
        (
            closure,
            lambda document: CampaignOccurrenceClosureV1.from_dict(
                document,
                occurrence=occurrence,
                policy=policy,
                attempts=(attempt,),
                terminal_results=(result,),
                attempt_work_vector_ids=((terminal.actual_work_vector_id,),),
                rebuild_events=(),
            ),
            "campaign_occurrence_closure_id",
        ),
        (
            summary,
            lambda document: CampaignClosureSummaryV1.from_dict(
                document,
                occurrences=(occurrence,),
                closures=(closure,),
                final_terminal_results=(result,),
            ),
            "campaign_summary_id",
        ),
    ):
        document = artifact.to_dict()
        assert loader(copy.deepcopy(document)).to_dict() == document
        tampered = copy.deepcopy(document)
        tampered[id_field] = "0" * 64
        with pytest.raises(CampaignV1Error, match="content ID mismatch"):
            loader(tampered)

    with pytest.raises(CampaignV1Error, match="requires semantic replay inputs"):
        CampaignOccurrenceClosureV1.from_dict(closure.to_dict())
    with pytest.raises(CampaignV1Error, match="requires occurrence, closure"):
        CampaignClosureSummaryV1.from_dict(summary.to_dict())
    with pytest.raises(CampaignV1Error, match="requires semantic terminal replay"):
        replace(closure, _authority=None)
    with pytest.raises(CampaignV1Error, match="authoritative closure replay"):
        replace(summary, _authority=None)
