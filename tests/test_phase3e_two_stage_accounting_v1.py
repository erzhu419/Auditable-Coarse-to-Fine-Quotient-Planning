from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib

import pytest

from acfqp.accounting_v1 import (
    LaneEnum,
    NONKERNEL_COMPUTE_EVENTS,
    PEAK_MOUNTED_BYTES,
    CounterRecordV1,
    RouteKindEnum,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualWorkScope,
    official_actual_projection_profile_v1,
)
from acfqp.native_recorder_v1 import NativeCounterRecorderV1, RecordedWorkV1
from acfqp.phase3e_ids import (
    ACCOUNTING_CORE_SEAL_DOMAIN,
    CONTINUATION_WORK_VECTOR_AUTHORITY_DOMAIN,
    NONSEMANTIC_VERIFICATION_ATTESTATION_DOMAIN,
    PHASE3E_DOMAIN_TAG_REGISTRY,
    TWO_STAGE_WORK_AGGREGATE_DOMAIN,
    VERIFICATION_CHARGE_ENTRY_DOMAIN,
    VERIFICATION_CHARGE_MANIFEST_DOMAIN,
    VERIFICATION_CHARGE_PLAN_DOMAIN,
    VERIFICATION_CHARGE_RECEIPT_DOMAIN,
    content_id,
)
from acfqp.phase3e_two_stage_accounting_v1 import (
    AccountingCoreStage,
    ExecutionVectorIntegrityEvidenceV1,
    FrozenNonsemanticVerificationObligationV1,
    NonsemanticVerificationAttestationV1,
    NonsemanticVerificationChargeEntryV1,
    NonsemanticVerificationCheckKind,
    NativeAggregationEvidenceV1,
    SealedAccountingCoreV1,
    TwoStageAccountingClosureV1,
    TwoStageAccountingV1Error,
    TwoStageWorkAggregateV1,
    VerificationChargeEntryV1,
    VerificationChargeManifestV1,
    VerificationChargeObligationV1,
    VerificationChargePlanV1,
    VerificationChargeReceiptV1,
    attest_nonsemantic_verification_v1,
    derive_two_stage_accounting_v1,
    seal_accounting_core_v1,
    verify_two_stage_accounting_v1,
    _route_kind_for_selection_v1,
)
from acfqp.routing_v1 import (
    RouteDecisionContextV1,
    RouteSelection,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationResultV1,
    semantic_verifier_spec_v1,
    verify_actual_projection_semantics_v1,
    verify_work_vector_semantics_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.mark.parametrize(
    ("selection", "expected"),
    (
        (RouteSelection.LOCAL, RouteKindEnum.LOCAL_ATTEMPT),
        (RouteSelection.FALLBACK, RouteKindEnum.DIRECT_FALLBACK),
    ),
)
def test_route_selection_maps_to_exact_accounting_route_kind(
    selection: RouteSelection,
    expected: RouteKindEnum,
) -> None:
    assert _route_kind_for_selection_v1(selection) is expected


def _context(label: str) -> RouteDecisionContextV1:
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    return RouteDecisionContextV1(
        _id(f"preregistration-{label}"),
        _id(f"protocol-{label}"),
        comparison.comparison_profile_id,
        registry.registry_id,
        _id(f"structural-{label}"),
        _id(f"query-{label}"),
        _id(f"plan-{label}"),
        _id(f"threshold-{label}"),
        _id(f"epoch-{label}"),
        _id(f"occurrence-{label}"),
        _id(f"attempt-{label}"),
    )


def _record(role: SemanticRole, *, value: int, recorder: str) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    return CounterRecordV1.observe(
        registry,
        semantic_verifier_spec_v1(role).verification_counter_path,
        value,
        recorder_id=recorder,
    )


@dataclass(frozen=True)
class _World:
    context: RouteDecisionContextV1
    binding: AttestationContextV1
    core_work: RecordedWorkV1
    core: SealedAccountingCoreV1
    plan: VerificationChargePlanV1
    results: tuple[SemanticVerificationResultV1, ...]
    closure: TwoStageAccountingClosureV1


def _world(
    label: str = "base",
    *,
    decision_ref: str | TypedNotApplicable | None = None,
) -> _World:
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, comparison)
    context = _context(label)
    decision_id = (
        _id(f"decision-{label}") if decision_ref is None else decision_ref
    )
    binding = AttestationContextV1(
        context,
        decision_id,
        TypedNotApplicable("common-prefix has no local transaction"),
        5,
    )
    recorder = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=comparison,
        recorder_id=f"common-prefix-core-{label}",
    )
    recorder.add("common.abstract_bellman_backups", 3)
    recorder.add("common.protocol_checks", 2)
    recorder.observe_peak("io.mounted_bytes_peak", 64)
    core_work = recorder.seal()
    core = seal_accounting_core_v1(
        recorded_work=core_work,
        binding=binding,
        core_stage=AccountingCoreStage.COMMON_PREFIX,
        registry=registry,
        comparison_profile=comparison,
        actual_profile=actual,
    )

    work_binding = replace(binding, verified_at_protocol_step=11)
    projection_binding = replace(binding, verified_at_protocol_step=12)
    work_result = verify_work_vector_semantics_v1(
        core_work.work_vector,
        binding=work_binding,
        verification_work_record=_record(
            SemanticRole.WORK_VECTOR,
            value=1,
            recorder=f"work-vector-charge-{label}",
        ),
        registry=registry,
    )
    projection_result = verify_actual_projection_semantics_v1(
        vector=core_work.work_vector,
        claimed_comparison=core_work.comparison_vector,
        projection_proof=core_work.actual_projection_proof,
        binding=projection_binding,
        verification_work_record=_record(
            SemanticRole.ACTUAL_PROJECTION,
            value=2,
            recorder=f"actual-projection-charge-{label}",
        ),
        registry=registry,
    )
    results = (work_result, projection_result)
    plan = VerificationChargePlanV1.for_core(
        core,
        plan_frozen_at_protocol_step=10,
        obligations=(
            VerificationChargeObligationV1.for_role(
                ordinal=0,
                artifact_id=core_work.work_vector.work_vector_id,
                role=SemanticRole.WORK_VECTOR,
                expected_result="VALID",
                verified_at_protocol_step=11,
                verification_work_record=work_result.verification_work_record,
            ),
            VerificationChargeObligationV1.for_role(
                ordinal=1,
                artifact_id=core_work.comparison_vector.comparison_vector_id,
                role=SemanticRole.ACTUAL_PROJECTION,
                expected_result="VALID",
                verified_at_protocol_step=12,
                verification_work_record=(
                    projection_result.verification_work_record
                ),
            ),
        ),
    )
    closure = derive_two_stage_accounting_v1(
        core=core,
        core_work=core_work,
        plan=plan,
        semantic_results=results,
        route_context=context,
        registry=registry,
        comparison_profile=comparison,
        actual_profile=actual,
    )
    return _World(context, binding, core_work, core, plan, results, closure)


def _reverify_with_binding(
    world: _World,
    *,
    decision_point_id: str | TypedNotApplicable | None = None,
    transaction_id: str | TypedNotApplicable | None = None,
) -> tuple[SemanticVerificationResultV1, ...]:
    registry = official_counter_registry_v1()
    work_binding = replace(
        world.results[0].binding,
        decision_point_id=(
            world.results[0].binding.decision_point_id
            if decision_point_id is None
            else decision_point_id
        ),
        transaction_id=(
            world.results[0].binding.transaction_id
            if transaction_id is None
            else transaction_id
        ),
    )
    projection_binding = replace(
        world.results[1].binding,
        decision_point_id=(
            world.results[1].binding.decision_point_id
            if decision_point_id is None
            else decision_point_id
        ),
        transaction_id=(
            world.results[1].binding.transaction_id
            if transaction_id is None
            else transaction_id
        ),
    )
    return (
        verify_work_vector_semantics_v1(
            world.core_work.work_vector,
            binding=work_binding,
            verification_work_record=world.results[0].verification_work_record,
            registry=registry,
        ),
        verify_actual_projection_semantics_v1(
            vector=world.core_work.work_vector,
            claimed_comparison=world.core_work.comparison_vector,
            projection_proof=world.core_work.actual_projection_proof,
            binding=projection_binding,
            verification_work_record=world.results[1].verification_work_record,
            registry=registry,
        ),
    )


def _verify(world: _World) -> VerificationChargeReceiptV1:
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, comparison)
    return verify_two_stage_accounting_v1(
        world.closure,
        core_work=world.core_work,
        semantic_results=world.results,
        route_context=world.context,
        registry=registry,
        comparison_profile=comparison,
        actual_profile=actual,
    )


def test_sealed_core_suffix_and_reducer_aggregate_are_exact() -> None:
    world = _world()
    receipt = _verify(world)
    suffix = world.closure.verification_suffix.comparison_vector
    core = world.core_work.comparison_vector
    aggregate = world.closure.aggregate_work.comparison_vector

    assert suffix.value(NONKERNEL_COMPUTE_EVENTS) == 3
    assert aggregate.value(NONKERNEL_COMPUTE_EVENTS) == (
        core.value(NONKERNEL_COMPUTE_EVENTS) + 3
    )
    assert core.value(PEAK_MOUNTED_BYTES) == 64
    assert suffix.value(PEAK_MOUNTED_BYTES) == 0
    assert aggregate.value(PEAK_MOUNTED_BYTES) == 64
    assert receipt.destination_suffix_work_vector_id == (
        world.closure.verification_suffix.work_vector.work_vector_id
    )
    assert receipt.destination_aggregate_work_vector_id == (
        world.closure.aggregate_work.work_vector.work_vector_id
    )
    assert world.closure.manifest.source_counter_record_ids == tuple(
        row.verification_work_record.record_id for row in world.results
    )
    assert world.closure.manifest.semantic_attestation_ids == tuple(
        row.attestation.verification_attestation_id for row in world.results
    )


@pytest.mark.parametrize(
    ("ref_field", "world"),
    (
        (
            "decision_point_id",
            _world(
                "decision-typed-null-substitution",
                decision_ref=TypedNotApplicable("no decision for frozen core"),
            ),
        ),
        ("transaction_id", _world("transaction-typed-null-substitution")),
    ),
)
def test_charge_plan_rejects_typed_null_reason_substitution(
    ref_field: str,
    world: _World,
) -> None:
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, comparison)
    changed = TypedNotApplicable(f"substituted {ref_field} reason")
    kwargs = {ref_field: changed}
    substituted_results = _reverify_with_binding(world, **kwargs)

    with pytest.raises(
        TwoStageAccountingV1Error,
        match="reused across accounting contexts",
    ):
        derive_two_stage_accounting_v1(
            core=world.core,
            core_work=world.core_work,
            plan=world.plan,
            semantic_results=substituted_results,
            route_context=world.context,
            registry=registry,
            comparison_profile=comparison,
            actual_profile=actual,
        )


def test_route_execution_core_closes_into_postfreeze_verification_aggregate() -> None:
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, comparison)
    context = _context("fallback-route")
    binding = AttestationContextV1(
        context,
        _id("fallback-decision"),
        TypedNotApplicable("direct fallback has no local transaction"),
        6,
    )
    recorder = NativeCounterRecorderV1(
        subject_id=context.route_attempt_id,
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=comparison,
        recorder_id="direct-fallback-core-test-v1",
    )
    recorder.add("fallback.ground_steps", 7)
    recorder.add("fallback.outcome_rows", 9)
    recorder.record_route_completion(success=True)
    core_work = recorder.seal()
    core = seal_accounting_core_v1(
        recorded_work=core_work,
        binding=binding,
        core_stage=AccountingCoreStage.ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=comparison,
        actual_profile=actual,
    )
    result_binding = replace(binding, verified_at_protocol_step=21)
    result = verify_work_vector_semantics_v1(
        core_work.work_vector,
        binding=result_binding,
        verification_work_record=_record(
            SemanticRole.WORK_VECTOR,
            value=1,
            recorder="fallback-work-vector-charge-v1",
        ),
        registry=registry,
    )
    plan = VerificationChargePlanV1.for_core(
        core,
        plan_frozen_at_protocol_step=20,
        obligations=(
            VerificationChargeObligationV1.for_role(
                ordinal=0,
                artifact_id=core_work.work_vector.work_vector_id,
                role=SemanticRole.WORK_VECTOR,
                expected_result="VALID",
                verified_at_protocol_step=21,
                verification_work_record=result.verification_work_record,
            ),
        ),
    )
    closure = derive_two_stage_accounting_v1(
        core=core,
        core_work=core_work,
        plan=plan,
        semantic_results=(result,),
        route_context=context,
        registry=registry,
        comparison_profile=comparison,
        actual_profile=actual,
    )
    assert closure.verification_suffix.actual_projection_proof.work_scope is (
        ActualWorkScope.MARGINAL_ROUTE_VERIFICATION
    )
    assert closure.aggregate_work.actual_projection_proof.work_scope is (
        ActualWorkScope.MARGINAL_ROUTE_AGGREGATE
    )
    assert closure.aggregate_work.work_vector.value("fallback.ground_steps") == 7
    assert closure.aggregate_work.work_vector.value("common.integrity_checks") == 1


def test_all_portable_artifacts_round_trip_and_reject_extra_fields() -> None:
    world = _world("roundtrip")
    closure = world.closure
    assert SealedAccountingCoreV1.from_dict(closure.core.to_dict()) == closure.core
    assert VerificationChargePlanV1.from_dict(closure.plan.to_dict()) == closure.plan
    for entry in closure.manifest.entries:
        assert VerificationChargeEntryV1.from_dict(entry.to_dict()) == entry
    assert TwoStageWorkAggregateV1.from_dict(closure.aggregate.to_dict()) == closure.aggregate
    assert VerificationChargeManifestV1.from_dict(closure.manifest.to_dict()) == closure.manifest
    assert VerificationChargeReceiptV1.from_dict(closure.receipt.to_dict()) == closure.receipt

    document = closure.manifest.to_dict()
    document["undeclared"] = 1
    with pytest.raises(TwoStageAccountingV1Error, match="field set"):
        VerificationChargeManifestV1.from_dict(document)


def test_padding_manifest_is_rejected_even_when_resigned() -> None:
    world = _world("padding")
    original = world.closure.manifest
    extra = VerificationChargeEntryV1(
        2,
        _id("padded-artifact"),
        SemanticRole.WORK_VECTOR.value,
        _id("padded-record"),
        _id("padded-attestation"),
    )
    padded_manifest = replace(original, entries=original.entries + (extra,))
    padded_receipt = replace(
        world.closure.receipt,
        verification_charge_manifest_id=padded_manifest.verification_charge_manifest_id,
        replayed_source_counter_record_ids=padded_manifest.source_counter_record_ids,
        replayed_semantic_attestation_ids=padded_manifest.semantic_attestation_ids,
    )
    forged = replace(
        world.closure,
        manifest=padded_manifest,
        receipt=padded_receipt,
    )
    attacked = replace(world, closure=forged)
    with pytest.raises(TwoStageAccountingV1Error, match="differs from exact replay"):
        _verify(attacked)


def test_source_record_substitution_is_rejected_even_when_resigned() -> None:
    world = _world("substitution")
    original = world.closure.manifest
    substituted_entry = replace(
        original.entries[0], source_counter_record_id=_id("substituted-record")
    )
    substituted_manifest = replace(
        original,
        entries=(substituted_entry,) + original.entries[1:],
    )
    substituted_receipt = replace(
        world.closure.receipt,
        verification_charge_manifest_id=substituted_manifest.verification_charge_manifest_id,
        replayed_source_counter_record_ids=substituted_manifest.source_counter_record_ids,
    )
    forged = replace(
        world.closure,
        manifest=substituted_manifest,
        receipt=substituted_receipt,
    )
    attacked = replace(world, closure=forged)
    with pytest.raises(TwoStageAccountingV1Error, match="differs from exact replay"):
        _verify(attacked)


def test_duplicate_counter_or_attestation_ids_are_rejected() -> None:
    world = _world("duplicates")
    first, second = world.closure.manifest.entries
    with pytest.raises(TwoStageAccountingV1Error, match="repeats a source CounterRecord"):
        replace(
            world.closure.manifest,
            entries=(first, replace(second, source_counter_record_id=first.source_counter_record_id)),
        )
    with pytest.raises(TwoStageAccountingV1Error, match="repeats a semantic attestation"):
        replace(
            world.closure.manifest,
            entries=(first, replace(second, semantic_attestation_id=first.semantic_attestation_id)),
        )


def test_cross_context_semantic_results_cannot_be_reused() -> None:
    source = _world("source-context")
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, comparison)
    target_context = replace(
        source.context,
        query_id=_id("different-query-same-native-work"),
    )
    target_binding = AttestationContextV1(
        target_context,
        source.binding.decision_point_id,
        source.binding.transaction_id,
        source.binding.verified_at_protocol_step,
    )
    target_core = seal_accounting_core_v1(
        recorded_work=source.core_work,
        binding=target_binding,
        core_stage=AccountingCoreStage.COMMON_PREFIX,
        registry=registry,
        comparison_profile=comparison,
        actual_profile=actual,
    )
    target_plan = VerificationChargePlanV1.for_core(
        target_core,
        plan_frozen_at_protocol_step=10,
        obligations=source.plan.obligations,
    )
    with pytest.raises(TwoStageAccountingV1Error, match="reused across accounting contexts"):
        derive_two_stage_accounting_v1(
            core=target_core,
            core_work=source.core_work,
            plan=target_plan,
            semantic_results=source.results,
            route_context=target_context,
            registry=registry,
            comparison_profile=comparison,
            actual_profile=actual,
        )


def test_omission_and_plan_staleness_fail_closed() -> None:
    world = _world("omission")
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, comparison)
    with pytest.raises(TwoStageAccountingV1Error, match="exactly cover"):
        derive_two_stage_accounting_v1(
            core=world.core,
            core_work=world.core_work,
            plan=world.plan,
            semantic_results=world.results[:1],
            route_context=world.context,
            registry=registry,
            comparison_profile=comparison,
            actual_profile=actual,
        )
    stale = replace(world.plan, accounting_core_seal_id=_id("stale-core"))
    with pytest.raises(TwoStageAccountingV1Error, match="stale for the sealed core"):
        derive_two_stage_accounting_v1(
            core=world.core,
            core_work=world.core_work,
            plan=stale,
            semantic_results=world.results,
            route_context=world.context,
            registry=registry,
            comparison_profile=comparison,
            actual_profile=actual,
        )


def test_charge_plan_must_precede_every_verification_step() -> None:
    world = _world("sequence")
    obligations = list(world.plan.obligations)
    obligations[0] = replace(obligations[0], verified_at_protocol_step=10)
    with pytest.raises(TwoStageAccountingV1Error, match="strictly after"):
        VerificationChargePlanV1.for_core(
            world.core,
            plan_frozen_at_protocol_step=10,
            obligations=obligations,
        )


def test_verification_sources_cannot_reuse_sealed_core_counter_records() -> None:
    world = _world("core-suffix-disjoint")
    core_record_id = world.core.core_counter_record_ids[0]
    reused_semantic = replace(
        world.plan.obligations[0],
        source_counter_record_id=core_record_id,
    )
    with pytest.raises(TwoStageAccountingV1Error, match="sealed-core CounterRecord"):
        VerificationChargePlanV1.for_core(
            world.core,
            plan_frozen_at_protocol_step=10,
            obligations=(reused_semantic, *world.plan.obligations[1:]),
        )

    reused_nonsemantic = FrozenNonsemanticVerificationObligationV1(
        len(world.plan.obligations),
        NonsemanticVerificationCheckKind.NATIVE_AGGREGATION,
        core_record_id,
        "common.protocol_checks",
        13,
    )
    with pytest.raises(TwoStageAccountingV1Error, match="sealed-core CounterRecord"):
        VerificationChargePlanV1.for_core(
            world.core,
            plan_frozen_at_protocol_step=10,
            obligations=world.plan.obligations,
            nonsemantic_obligations=(reused_nonsemantic,),
        )

    # Direct dataclass construction cannot bypass the replay-side guard.
    bypass = replace(
        world.plan,
        obligations=(reused_semantic, *world.plan.obligations[1:]),
    )
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, comparison)
    with pytest.raises(TwoStageAccountingV1Error, match="sealed-core CounterRecord"):
        derive_two_stage_accounting_v1(
            core=world.core,
            core_work=world.core_work,
            plan=bypass,
            semantic_results=world.results,
            route_context=world.context,
            registry=registry,
            comparison_profile=comparison,
            actual_profile=actual,
        )


def test_evaluation_lane_cannot_leak_into_operational_suffix() -> None:
    world = _world("evaluation-lane")
    obligation = world.plan.obligations[0]
    spec = semantic_verifier_spec_v1(SemanticRole.WORK_VECTOR)
    with pytest.raises(TwoStageAccountingV1Error, match="rejects evaluation-lane"):
        replace(
            obligation,
            verification_lane=LaneEnum.EVALUATION,
            verification_counter_path=spec.evaluation_verification_counter_path,
        )


def test_new_domain_tags_are_registered_unique_and_cross_role_separated() -> None:
    expected = {
        "accounting_core_seal": ACCOUNTING_CORE_SEAL_DOMAIN,
        "verification_charge_plan": VERIFICATION_CHARGE_PLAN_DOMAIN,
        "verification_charge_entry": VERIFICATION_CHARGE_ENTRY_DOMAIN,
        "two_stage_work_aggregate": TWO_STAGE_WORK_AGGREGATE_DOMAIN,
        "verification_charge_manifest": VERIFICATION_CHARGE_MANIFEST_DOMAIN,
        "verification_charge_receipt": VERIFICATION_CHARGE_RECEIPT_DOMAIN,
        "nonsemantic_verification_attestation": (
            NONSEMANTIC_VERIFICATION_ATTESTATION_DOMAIN
        ),
        "continuation_work_vector_authority": (
            CONTINUATION_WORK_VECTOR_AUTHORITY_DOMAIN
        ),
    }
    for key, domain in expected.items():
        assert PHASE3E_DOMAIN_TAG_REGISTRY[key] == domain
    assert len(set(expected.values())) == len(expected)
    payload = {"same": "payload"}
    assert len({content_id(domain, payload) for domain in expected.values()}) == len(expected)


def _world_with_prepaid_nonsemantic_check(
    label: str,
) -> tuple[_World, CounterRecordV1]:
    base = _world(label)
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, comparison)
    record = CounterRecordV1.observe(
        registry,
        "common.protocol_checks",
        1,
        recorder_id=f"prepaid-protocol-check-{label}",
    )
    obligation = FrozenNonsemanticVerificationObligationV1(
        len(base.plan.obligations),
        NonsemanticVerificationCheckKind.NATIVE_AGGREGATION,
        record.record_id,
        record.path,
        13,
    )
    plan = VerificationChargePlanV1.for_core(
        base.core,
        plan_frozen_at_protocol_step=10,
        obligations=base.plan.obligations,
        nonsemantic_obligations=(obligation,),
    )

    def evidence_after_aggregation(_aggregate, _suffix, _aggregate_work):
        return (NativeAggregationEvidenceV1(),)

    closure = derive_two_stage_accounting_v1(
        core=base.core,
        core_work=base.core_work,
        plan=plan,
        semantic_results=base.results,
        nonsemantic_records=(record,),
        nonsemantic_evidence_factory=evidence_after_aggregation,
        route_context=base.context,
        registry=registry,
        comparison_profile=comparison,
        actual_profile=actual,
    )
    return replace(base, plan=plan, closure=closure), record


def test_prepaid_nonsemantic_check_closes_without_self_reference() -> None:
    world, record = _world_with_prepaid_nonsemantic_check("nonsemantic")
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, comparison)
    receipt = verify_two_stage_accounting_v1(
        world.closure,
        core_work=world.core_work,
        semantic_results=world.results,
        nonsemantic_records=(record,),
        route_context=world.context,
        registry=registry,
        comparison_profile=comparison,
        actual_profile=actual,
    )

    assert world.closure.verification_suffix.work_vector.value(
        "common.protocol_checks"
    ) >= record.value
    assert world.closure.manifest.source_counter_record_ids[-1] == record.record_id
    assert len(world.closure.nonsemantic_attestations) == 1
    attestation = world.closure.nonsemantic_attestations[0]
    assert attestation.nonsemantic_verification_attestation_id not in (
        world.closure.manifest.source_counter_record_ids
    )
    assert world.closure.aggregate.two_stage_work_aggregate_id in (
        attestation.verified_evidence_ids
    )
    assert receipt.replayed_nonsemantic_attestation_ids == (
        attestation.nonsemantic_verification_attestation_id,
    )
    assert (
        NonsemanticVerificationAttestationV1.from_dict(attestation.to_dict())
        == attestation
    )
    entry = world.closure.manifest.nonsemantic_entries[0]
    assert NonsemanticVerificationChargeEntryV1.from_dict(entry.to_dict()) == entry


def test_nonsemantic_omission_and_source_substitution_fail_closed() -> None:
    world, record = _world_with_prepaid_nonsemantic_check("nonsemantic-attacks")
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, comparison)
    kwargs = dict(
        core=world.core,
        core_work=world.core_work,
        plan=world.plan,
        semantic_results=world.results,
        route_context=world.context,
        registry=registry,
        comparison_profile=comparison,
        actual_profile=actual,
    )
    with pytest.raises(TwoStageAccountingV1Error, match="exactly cover"):
        derive_two_stage_accounting_v1(**kwargs)

    substituted = CounterRecordV1.observe(
        registry,
        record.path,
        record.value,
        recorder_id="substituted-prepaid-protocol-check",
    )
    with pytest.raises(TwoStageAccountingV1Error, match="omitted or substituted"):
        derive_two_stage_accounting_v1(
            **kwargs,
            nonsemantic_records=(substituted,),
            nonsemantic_evidence_factory=lambda *_: (),
        )


def test_nonsemantic_attestation_rejects_fabricated_or_wrong_kind_evidence() -> None:
    world, record = _world_with_prepaid_nonsemantic_check("nonsemantic-stale")
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, comparison)
    obligation = world.plan.nonsemantic_obligations[0]
    with pytest.raises(TwoStageAccountingV1Error, match="typed aggregation"):
        attest_nonsemantic_verification_v1(
            core=world.core,
            core_work=world.core_work,
            plan=world.plan,
            obligation=obligation,
            evidence=ExecutionVectorIntegrityEvidenceV1(world.core_work),
            aggregate=world.closure.aggregate,
            suffix=world.closure.verification_suffix,
            aggregate_work=world.closure.aggregate_work,
            route_context=world.context,
            registry=registry,
            comparison_profile=comparison,
            actual_profile=actual,
        )

    fabricated = replace(
        world.closure.nonsemantic_attestations[0],
        verified_evidence_ids=(_id("fabricated-substitution"),),
    )
    with pytest.raises(TwoStageAccountingV1Error, match="differs from exact replay"):
        verify_two_stage_accounting_v1(
            replace(
                world.closure,
                nonsemantic_attestations=(fabricated,),
            ),
            core_work=world.core_work,
            semantic_results=world.results,
            nonsemantic_records=(record,),
            route_context=world.context,
            registry=registry,
            comparison_profile=comparison,
            actual_profile=actual,
        )
