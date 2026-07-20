from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib

import pytest

from acfqp.accounting_v1 import (
    CounterRecordV1,
    RouteKindEnum,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
import acfqp.phase3e_local_semantics_v1 as local_semantics
from acfqp.phase3e_local_semantics_v1 import (
    FrozenThresholdProfileV1,
    LocalSolverOutcome,
    LocalTransactionResultV1,
    Phase3ELocalSemanticV1Error,
    PostAuditCertificateV1,
    PostAuditOutcome,
    TrustedLocalExecutionV1,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    TransactionV1,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationV1Error,
    semantic_verifier_spec_v1,
    verify_local_transaction_result_semantics_v1,
    verify_post_audit_semantics_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _record(role: SemanticRole) -> CounterRecordV1:
    registry = official_counter_registry_v1()
    return CounterRecordV1.observe(
        registry,
        semantic_verifier_spec_v1(role).verification_counter_path,
        1,
        recorder_id=f"phase3e-{role.value.lower()}-authority-test-v1",
    )


def _world(*, post_outcome: PostAuditOutcome = PostAuditOutcome.FAILED):
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    cap = RouteCapProfileV1()
    query_id = _id("query")
    threshold = FrozenThresholdProfileV1(
        query_id, Fraction(1, 20), Fraction(1, 20)
    )
    context = RouteDecisionContextV1(
        _id("pre"),
        _id("protocol"),
        comparison.comparison_profile_id,
        registry.registry_id,
        _id("structural"),
        query_id,
        _id("stitched-selected-plan"),
        threshold.threshold_profile_id,
        _id("epoch"),
        _id("occurrence"),
        _id("attempt"),
    )
    point = DecisionPointV1(
        context.route_decision_context_id,
        1,
        _id("frontier"),
        _id("causal"),
        _id("common-prefix-work"),
    )
    transaction = TransactionV1(
        context.logical_occurrence_id,
        context.route_attempt_id,
        point.decision_point_id,
        1,
        point.frontier_snapshot_id,
        cap.route_cap_profile_id,
    )
    values = {path: 0 for path in registry.required_paths}
    values.update(
        {
            "local.materialization_ground_steps": 1,
            "local.materialization_outcome_rows": 4,
            "local.solver_subset_evaluations": 1,
            "local.solver_policy_assignments": 2,
            "local.postaudit_ground_steps": 1,
            "local.postaudit_outcome_rows": 4,
            "route.attempts": 1,
            "route.successes": 1 if post_outcome is PostAuditOutcome.CERTIFIED else 0,
            "route.failures": 0 if post_outcome is PostAuditOutcome.CERTIFIED else 1,
            "solver.attempts": 1,
            "solver.successes": 1,
            "process.launches": 1,
            "process.exit_successes": 1,
        }
    )
    vector = registry.materialize(
        subject_id=transaction.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        records=explicit_records_v1(
            registry,
            values,
            recorder_id="phase3e-local-authority-native-test-v1",
        ),
    )
    local = LocalTransactionResultV1(
        context.route_decision_context_id,
        point.decision_point_id,
        transaction.transaction_id,
        context.route_attempt_id,
        context.query_id,
        context.selected_plan_id,
        cap.route_cap_profile_id,
        _id("selected-local-upper"),
        vector.work_vector_id,
        _id("capability-binding"),
        _id("worker-result-binding"),
        _id("runtime-attestation-binding"),
        _id("overlay-binding"),
        _id("new-stitched-plan-binding"),
        LocalSolverOutcome.CANDIDATE_FOUND,
        True,
        None,
    )
    if post_outcome is PostAuditOutcome.CERTIFIED:
        reward, failure, regret = Fraction(3, 64), Fraction(1, 100), Fraction(0)
    else:
        reward, failure, regret = Fraction(0), Fraction(1, 10), Fraction(1, 10)
    post = PostAuditCertificateV1(
        context.route_decision_context_id,
        point.decision_point_id,
        transaction.transaction_id,
        context.route_attempt_id,
        context.query_id,
        context.selected_plan_id,
        context.threshold_profile_id,
        local.local_transaction_result_id,
        vector.work_vector_id,
        local.candidate_overlay_binding_id,
        local.stitched_plan_binding_id,
        _id(f"audit-issue-set-{post_outcome.value}"),
        post_outcome,
        reward,
        failure,
        regret,
        1,
        4,
    )
    execution = local_semantics._seal_trusted_execution_v1(
        local_result=local,
        post_audit=post,
        work_vector=vector,
        threshold_profile=threshold,
    )
    binding = AttestationContextV1(
        context, point.decision_point_id, transaction.transaction_id, 20
    )
    return (
        registry,
        cap,
        context,
        point,
        transaction,
        vector,
        threshold,
        local,
        post,
        execution,
        binding,
    )


@pytest.mark.parametrize("outcome", (PostAuditOutcome.CERTIFIED, PostAuditOutcome.FAILED))
def test_local_and_postaudit_artifacts_strict_roundtrip(outcome: PostAuditOutcome) -> None:
    *_, local, post, _execution, _binding = _world(post_outcome=outcome)
    threshold = _world(post_outcome=outcome)[6]
    assert FrozenThresholdProfileV1.from_dict(threshold.to_dict()) == threshold
    assert LocalTransactionResultV1.from_dict(local.to_dict()) == local
    assert PostAuditCertificateV1.from_dict(post.to_dict()) == post


def test_trusted_runtime_yields_local_and_failed_postaudit_authority() -> None:
    registry, cap, context, point, transaction, vector, _threshold, local, post, execution, binding = _world()
    local_result = verify_local_transaction_result_semantics_v1(
        execution,
        context=context,
        decision_point=point,
        transaction=transaction,
        cap_profile=cap,
        binding=binding,
        verification_work_record=_record(SemanticRole.LOCAL_SOLVER_RESULT),
        registry=registry,
    )
    assert local_result.outcome == "CANDIDATE_FOUND"
    assert local_result.attestation.artifact_id == local.local_transaction_result_id

    post_result = verify_post_audit_semantics_v1(
        execution,
        local_solver_result=local_result,
        context=context,
        decision_point=point,
        transaction=transaction,
        cap_profile=cap,
        binding=binding,
        verification_work_record=_record(SemanticRole.POST_AUDIT),
        registry=registry,
    )
    assert post_result.outcome == "FAILED"
    assert post_result.artifact == post
    assert post_result.binding.transaction_id == transaction.transaction_id
    assert post_result.attestation.artifact_id == post.post_audit_certificate_id


def test_raw_reserialised_artifacts_never_mint_authority() -> None:
    registry, cap, context, point, transaction, _vector, _threshold, local, post, _execution, binding = _world()
    with pytest.raises(SemanticVerificationV1Error, match="opaque trusted runtime"):
        verify_local_transaction_result_semantics_v1(
            local,
            context=context,
            decision_point=point,
            transaction=transaction,
            cap_profile=cap,
            binding=binding,
            verification_work_record=_record(SemanticRole.LOCAL_SOLVER_RESULT),
            registry=registry,
        )
    with pytest.raises(SemanticVerificationV1Error, match="opaque trusted runtime"):
        verify_post_audit_semantics_v1(
            post,
            local_solver_result=object(),
            context=context,
            decision_point=point,
            transaction=transaction,
            cap_profile=cap,
            binding=binding,
            verification_work_record=_record(SemanticRole.POST_AUDIT),
            registry=registry,
        )


def test_replace_and_rehash_cannot_reuse_runtime_provenance() -> None:
    registry, cap, context, point, transaction, vector, threshold, local, post, execution, binding = _world()
    changed = replace(local, selected_upper_id=_id("attacker-new-upper"))
    attacked = TrustedLocalExecutionV1(
        changed,
        replace(post, local_transaction_result_id=changed.local_transaction_result_id),
        vector,
        threshold,
        execution.local_provenance,
        execution.postaudit_provenance,
    )
    with pytest.raises(SemanticVerificationV1Error, match="trusted provenance"):
        verify_local_transaction_result_semantics_v1(
            attacked,
            context=context,
            decision_point=point,
            transaction=transaction,
            cap_profile=cap,
            binding=binding,
            verification_work_record=_record(SemanticRole.LOCAL_SOLVER_RESULT),
            registry=registry,
        )


def test_context_or_transaction_substitution_is_rejected() -> None:
    registry, cap, context, point, transaction, _vector, _threshold, _local, _post, execution, _binding = _world()
    foreign_context = replace(context, selected_plan_id=_id("foreign-plan"))
    foreign_binding = AttestationContextV1(
        foreign_context, point.decision_point_id, transaction.transaction_id, 20
    )
    with pytest.raises(SemanticVerificationV1Error, match="another context"):
        verify_local_transaction_result_semantics_v1(
            execution,
            context=foreign_context,
            decision_point=point,
            transaction=transaction,
            cap_profile=cap,
            binding=foreign_binding,
            verification_work_record=_record(SemanticRole.LOCAL_SOLVER_RESULT),
            registry=registry,
        )


def test_trusted_postaudit_requires_candidate_and_exact_overlay_stitch_chain() -> None:
    registry, cap, context, point, transaction, vector, threshold, local, post, _execution, binding = _world()
    del registry, cap, context, point, transaction, binding

    no_candidate = replace(
        local,
        candidate_overlay_binding_id=TypedNotApplicable("no candidate overlay"),
        stitched_plan_binding_id=TypedNotApplicable("no stitched plan"),
        outcome=LocalSolverOutcome.NO_FEASIBLE_ASSIGNMENT,
    )
    no_candidate_post = replace(
        post,
        local_transaction_result_id=no_candidate.local_transaction_result_id,
    )
    with pytest.raises(Phase3ELocalSemanticV1Error, match="CANDIDATE_FOUND"):
        local_semantics._seal_trusted_execution_v1(
            local_result=no_candidate,
            post_audit=no_candidate_post,
            work_vector=vector,
            threshold_profile=threshold,
        )

    with pytest.raises(Phase3ELocalSemanticV1Error, match="execution chain"):
        local_semantics._seal_trusted_execution_v1(
            local_result=local,
            post_audit=replace(post, overlay_binding_id=_id("foreign-overlay")),
            work_vector=vector,
            threshold_profile=threshold,
        )
    with pytest.raises(Phase3ELocalSemanticV1Error, match="execution chain"):
        local_semantics._seal_trusted_execution_v1(
            local_result=local,
            post_audit=replace(
                post, stitched_plan_binding_id=_id("foreign-stitched-plan")
            ),
            work_vector=vector,
            threshold_profile=threshold,
        )


def test_postaudit_cannot_self_select_or_relabel_frozen_tolerance() -> None:
    registry, cap, context, point, transaction, vector, threshold, local, post, _execution, binding = _world()

    # The raw transport can carry a claim, but the trusted execution boundary
    # recomputes it from a separately supplied frozen threshold profile.
    with pytest.raises(Phase3ELocalSemanticV1Error, match="frozen threshold"):
        local_semantics._seal_trusted_execution_v1(
            local_result=local,
            post_audit=replace(post, outcome=PostAuditOutcome.CERTIFIED),
            work_vector=vector,
            threshold_profile=threshold,
        )

    permissive = FrozenThresholdProfileV1(
        context.query_id, Fraction(1), Fraction(1)
    )
    permissive_post = replace(
        post,
        threshold_profile_id=permissive.threshold_profile_id,
        outcome=PostAuditOutcome.CERTIFIED,
    )
    permissive_execution = local_semantics._seal_trusted_execution_v1(
        local_result=local,
        post_audit=permissive_post,
        work_vector=vector,
        threshold_profile=permissive,
    )
    with pytest.raises(SemanticVerificationV1Error, match="frozen threshold"):
        verify_local_transaction_result_semantics_v1(
            permissive_execution,
            context=context,
            decision_point=point,
            transaction=transaction,
            cap_profile=cap,
            binding=binding,
            verification_work_record=_record(SemanticRole.LOCAL_SOLVER_RESULT),
            registry=registry,
        )


def test_cap_exhausted_shape_cannot_be_relabeled_infeasible() -> None:
    *_, local, _post, _execution, _binding = _world()
    cap_result = replace(
        local,
        candidate_overlay_binding_id=TypedNotApplicable("cap produced no candidate"),
        stitched_plan_binding_id=TypedNotApplicable("cap produced no stitched plan"),
        outcome=LocalSolverOutcome.SEARCH_CAP_EXHAUSTED,
        search_complete=False,
        cap_reason="max_policy_assignments",
    )
    assert cap_result.outcome is LocalSolverOutcome.SEARCH_CAP_EXHAUSTED
    assert "INFEASIBLE" not in cap_result.outcome.value
    with pytest.raises(Phase3ELocalSemanticV1Error):
        replace(cap_result, outcome=LocalSolverOutcome.NO_FEASIBLE_ASSIGNMENT)


def test_cap_exhausted_authority_requires_native_saturation_and_rejection() -> None:
    registry, cap, context, point, transaction, vector, _threshold, local, _post, _execution, binding = _world()
    values = dict(vector.values)
    values["local.solver_policy_assignments"] = dict(cap.limits)["max_policy_assignments"]
    values["control.cap_rejections"] = 1
    values["solver.successes"] = 0
    values["solver.failures"] = 1
    exhausted_vector = registry.materialize(
        subject_id=transaction.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        records=explicit_records_v1(
            registry, values, recorder_id="phase3e-local-cap-exhausted-v1"
        ),
    )
    exhausted = replace(
        local,
        work_vector_id=exhausted_vector.work_vector_id,
        candidate_overlay_binding_id=TypedNotApplicable("cap produced no candidate"),
        stitched_plan_binding_id=TypedNotApplicable("cap produced no stitched plan"),
        outcome=LocalSolverOutcome.SEARCH_CAP_EXHAUSTED,
        search_complete=False,
        cap_reason="max_policy_assignments",
    )
    execution = local_semantics._seal_trusted_execution_v1(
        local_result=exhausted,
        post_audit=None,
        work_vector=exhausted_vector,
    )
    result = verify_local_transaction_result_semantics_v1(
        execution,
        context=context,
        decision_point=point,
        transaction=transaction,
        cap_profile=cap,
        binding=binding,
        verification_work_record=_record(SemanticRole.LOCAL_SOLVER_RESULT),
        registry=registry,
    )
    assert result.outcome == "SEARCH_CAP_EXHAUSTED"

    unsaturated_values = dict(values)
    unsaturated_values["local.solver_policy_assignments"] -= 1
    unsaturated_vector = registry.materialize(
        subject_id=transaction.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        records=explicit_records_v1(
            registry, unsaturated_values, recorder_id="phase3e-false-cap-claim-v1"
        ),
    )
    false_claim = replace(exhausted, work_vector_id=unsaturated_vector.work_vector_id)
    attacked = local_semantics._seal_trusted_execution_v1(
        local_result=false_claim,
        post_audit=None,
        work_vector=unsaturated_vector,
    )
    with pytest.raises(SemanticVerificationV1Error, match="cap-saturation"):
        verify_local_transaction_result_semantics_v1(
            attacked,
            context=context,
            decision_point=point,
            transaction=transaction,
            cap_profile=cap,
            binding=binding,
            verification_work_record=_record(SemanticRole.LOCAL_SOLVER_RESULT),
            registry=registry,
        )


def test_local_counter_over_cap_is_rejected_even_with_a_matching_test_seal() -> None:
    registry, cap, context, point, transaction, vector, threshold, local, post, _execution, binding = _world()
    values = dict(vector.values)
    values["local.solver_policy_assignments"] = dict(cap.limits)["max_policy_assignments"] + 1
    attacked_vector = registry.materialize(
        subject_id=transaction.transaction_id,
        route_kind=RouteKindEnum.LOCAL_ATTEMPT,
        records=explicit_records_v1(
            registry, values, recorder_id="phase3e-over-cap-attack-v1"
        ),
    )
    attacked_local = replace(local, work_vector_id=attacked_vector.work_vector_id)
    attacked_post = replace(
        post,
        local_transaction_result_id=attacked_local.local_transaction_result_id,
        work_vector_id=attacked_vector.work_vector_id,
    )
    attacked = local_semantics._seal_trusted_execution_v1(
        local_result=attacked_local,
        post_audit=attacked_post,
        work_vector=attacked_vector,
        threshold_profile=threshold,
    )
    with pytest.raises(SemanticVerificationV1Error, match="exceeds the frozen"):
        verify_local_transaction_result_semantics_v1(
            attacked,
            context=context,
            decision_point=point,
            transaction=transaction,
            cap_profile=cap,
            binding=binding,
            verification_work_record=_record(SemanticRole.LOCAL_SOLVER_RESULT),
            registry=registry,
        )


def test_postaudit_counter_and_route_completion_mismatches_are_rejected() -> None:
    registry, cap, context, point, transaction, vector, threshold, local, post, execution, binding = _world()
    local_result = verify_local_transaction_result_semantics_v1(
        execution,
        context=context,
        decision_point=point,
        transaction=transaction,
        cap_profile=cap,
        binding=binding,
        verification_work_record=_record(SemanticRole.LOCAL_SOLVER_RESULT),
        registry=registry,
    )
    mismatched_post = replace(post, postaudit_positive_outcomes=3)
    attacked = local_semantics._seal_trusted_execution_v1(
        local_result=local,
        post_audit=mismatched_post,
        work_vector=vector,
        threshold_profile=threshold,
    )
    with pytest.raises(SemanticVerificationV1Error, match="counters differ"):
        verify_post_audit_semantics_v1(
            attacked,
            local_solver_result=local_result,
            context=context,
            decision_point=point,
            transaction=transaction,
            cap_profile=cap,
            binding=binding,
            verification_work_record=_record(SemanticRole.POST_AUDIT),
            registry=registry,
        )

    certified_post = replace(
        post,
        outcome=PostAuditOutcome.CERTIFIED,
        lifted_failure_upper=Fraction(1, 100),
        regret_upper=Fraction(0),
    )
    attacked_route = local_semantics._seal_trusted_execution_v1(
        local_result=local,
        post_audit=certified_post,
        work_vector=vector,
        threshold_profile=threshold,
    )
    with pytest.raises(SemanticVerificationV1Error, match="route completion"):
        verify_post_audit_semantics_v1(
            attacked_route,
            local_solver_result=local_result,
            context=context,
            decision_point=point,
            transaction=transaction,
            cap_profile=cap,
            binding=binding,
            verification_work_record=_record(SemanticRole.POST_AUDIT),
            registry=registry,
        )
