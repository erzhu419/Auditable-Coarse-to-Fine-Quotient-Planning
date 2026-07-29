from __future__ import annotations

from dataclasses import fields
from fractions import Fraction
import hashlib
from types import SimpleNamespace
from typing import Any

import pytest

from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import verified_source_acquisition_archive_v2 as archive
from acfqp import (
    verified_source_acquisition_archive_independent_verifier_v2
    as archive_independent,
)
from acfqp import v072_registered_adaptive_quotient_runtime_v1 as adaptive
from acfqp import (
    v072_registered_adaptive_quotient_runtime_independent_verifier_v1
    as adaptive_independent,
)
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_registered_cold_h2_orchestrator_v1 as cold
from acfqp import v072_independent_exact_ground_evaluator_v1 as evaluator
from acfqp import (
    v072_registered_campaign_reconciliation_independent_verifier_v1
    as independent,
)
from acfqp import v072_registered_campaign_reconciliation_v1 as reconciliation
from acfqp import v072_registered_matched_direct_runtime_v1 as direct
from acfqp import v072_registered_operational_terminal_authority_v1 as terminal
from acfqp import v072_source_reconstruction_recipe_v1 as source_recipe
from acfqp import v072_verified_source_archive_component_v1 as component
from tests.test_verified_source_acquisition_archive_independent_verifier_v2 import (
    miniature_source_archive,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _unsafe_exact(cls: type[Any], **values: Any) -> Any:
    result = object.__new__(cls)
    field_names = {
        item.name for item in fields(cls)
    } if hasattr(cls, "__dataclass_fields__") else set()
    for name in field_names | set(values):
        object.__setattr__(result, name, values.get(name))
    return result


def _unsafe_clone(value: Any, **changes: Any) -> Any:
    result = object.__new__(type(value))
    for item in fields(value):
        object.__setattr__(
            result,
            item.name,
            changes.get(item.name, getattr(value, item.name)),
        )
    return result


@pytest.fixture
def source_replay(miniature_source_archive):
    campaign, verification, claimed_archive = miniature_source_archive
    # The miniature archive fixture is an archive-transform fixture.  Add the
    # exact physical raw-ID accounting consumed by reconciliation.
    all_ids: set[str] = set()
    for context_index, result in enumerate(campaign.context_results):
        ids = tuple(
            sorted(
                _id(f"source-raw:{context_index}:{index}")
                for index in range(3)
            )
        )
        object.__setattr__(
            result,
            "accounting",
            SimpleNamespace(physical_unique_observation_ids=ids),
        )
        all_ids.update(ids)
    object.__setattr__(
        campaign,
        "physical_unique_observer_draws",
        len(all_ids),
    )
    object.__setattr__(
        campaign,
        "counters",
        SimpleNamespace(physical_unique_observer_draws=len(all_ids)),
    )
    production = archive.verify_verified_source_acquisition_archive_v2(
        source_campaign=campaign,
        source_verification=verification,
        claimed=claimed_archive,
    )
    independent_attestation = (
        archive_independent.verify_source_acquisition_archive_independently_v2(
            source_campaign=campaign,
            source_verification=verification,
            claimed=claimed_archive,
        )
    )
    bound = component.bind_v072_verified_source_archive_component_v1(
        archive=claimed_archive,
        production_verification=production,
        independent_attestation=independent_attestation,
    )
    return source_recipe.SourceReconstructionReplayV1(
        _id("source-recipe"),
        campaign,
        verification,
        claimed_archive,
        production,
        independent_attestation,
        bound,
    )


def _authority_and_plan(source_replay):
    chain_id = _id("chain")
    anchor_id = _id("anchor")
    manifest_id = _id("manifest")
    final_id = _id("final-preregistration")
    manifest = SimpleNamespace(
        global_bindings={
            "source_reconstruction_recipe_id": source_replay.recipe_id,
            "source_archive_id": source_replay.archive.archive_id,
            "source_archive_verification_attestation_id": (
                source_replay.independent_attestation.verification_id
            ),
        }
    )
    chain = _unsafe_exact(
        consumer.RegisteredCampaignAuthorityChainV1,
        manifest=manifest,
        final_preregistration=SimpleNamespace(),
        remote_main_anchor=SimpleNamespace(anchor_id=anchor_id),
        remote_main_anchor_attestation=SimpleNamespace(),
        repository_root="/registered/repository",
        _chain_id=chain_id,
    )
    plan = consumer.RegisteredCampaignExecutionPlanV1(
        chain_id,
        tuple(
            consumer.RegisteredOccurrenceExecutionPlanV1(chain_id, template)
            for template in consumer.registered_occurrence_templates_v1()
        ),
    )
    return chain, plan, (source_replay.recipe_id, manifest_id, final_id, anchor_id, _id("anchor-attestation"))


def _adaptive_route(
    *,
    chain_id: str,
    anchor_id: str,
    plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
) -> tuple[
    adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1,
    adaptive_independent.RegisteredAdaptiveRuntimeIndependentVerificationV1,
]:
    ordinal = plan.template.occurrence_ordinal
    acquisition = _unsafe_exact(
        __import__(
            "acfqp.v072_registered_target_confidence_accumulator_v1",
            fromlist=["RegisteredTargetRowAcquisitionV1"],
        ).RegisteredTargetRowAcquisitionV1,
        _acquisition_id=_id(f"adaptive-acquisition:{ordinal}"),
        transcript=SimpleNamespace(entries=tuple(range(10 + ordinal))),
    )
    work = _unsafe_exact(
        adaptive.RegisteredAdaptiveOccurrenceWorkV1,
        _work_id=_id(f"adaptive-work:{ordinal}"),
        producer_draw_calls=10 + ordinal,
        unique_online_sample_evidence_draws=10 + ordinal,
        replay_draw_calls=20 + ordinal,
        total_observer_draw_calls=30 + 2 * ordinal,
    )
    model = SimpleNamespace(model_id=_id(f"adaptive-model:{ordinal}"))
    epoch = _unsafe_exact(
        cold.RegisteredColdH2ModelEpochV1,
        _epoch_id=_id(f"adaptive-epoch:{ordinal}"),
        acquisitions=(acquisition,),
        model_pair=SimpleNamespace(quotient_planner_model=model),
    )
    execution = _unsafe_exact(
        adaptive.RegisteredAdaptiveOccurrenceResultV1,
        authority_chain_id=chain_id,
        anchor_id=anchor_id,
        occurrence_plan=plan,
        context=context,
        epochs=(epoch,),
        status=adaptive.RegisteredAdaptiveOccurrenceStatusV1.NO_SOUND_COVER,
        work=work,
        _result_id=_id(f"adaptive-execution:{ordinal}"),
        _certificate_id=None,
    )
    verification = _unsafe_exact(
        adaptive_independent.RegisteredAdaptiveRuntimeIndependentVerificationV1,
        _verification_id=_id(f"adaptive-verification:{ordinal}"),
    )
    result = _unsafe_exact(
        adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1,
        execution=execution,
        independent_verification=verification,
        _verified_result_id=_id(f"adaptive-verified-result:{ordinal}"),
    )
    return result, verification


def _direct_route(
    *,
    chain_id: str,
    anchor_id: str,
    final_id: str,
    plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
) -> tuple[
    direct.RegisteredMatchedDirectOccurrenceResultV1,
    direct.RegisteredMatchedDirectOccurrenceIndependentVerificationV1,
]:
    ordinal = plan.template.occurrence_ordinal
    canonical_direct_plan = direct.RegisteredMatchedDirectOccurrencePlanV1(
        anchor_id,
        context.context_id,
        context.context_key,
        plan.template.context_ordinal,
        plan.template.arm_ordinal,
        ordinal,
    )
    checkpoint = SimpleNamespace(
        checkpoint_id=_id(f"direct-checkpoint:{ordinal}"),
        work=SimpleNamespace(work_id=_id(f"direct-work:{ordinal}")),
        direct_snapshot=SimpleNamespace(
            planner_model=SimpleNamespace(
                model_id=_id(f"direct-model:{ordinal}")
            )
        ),
    )
    result = _unsafe_exact(
        direct.RegisteredMatchedDirectOccurrenceResultV1,
        authority_chain_id=chain_id,
        anchor_id=anchor_id,
        final_preregistration_id=final_id,
        occurrence_plan_id=canonical_direct_plan.plan_id,
        context_id=context.context_id,
        checkpoint_records=(
            SimpleNamespace(inventory_checkpoint=checkpoint),
        ),
        terminal_class=(
            direct.RegisteredMatchedDirectTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE
        ),
        terminal_code=(
            direct.RegisteredMatchedDirectTerminalCodeV1
            .DIRECT_CHECKPOINT_CAP_EXHAUSTED_NONCERTIFICATE
        ),
        acquisition_sample_total=100 + ordinal,
        deterministic_verifier_replay_total=200 + ordinal,
        crn_draw_discount=0,
        _result_id=_id(f"direct-result:{ordinal}"),
    )
    verification = _unsafe_exact(
        direct.RegisteredMatchedDirectOccurrenceIndependentVerificationV1,
        _verification_id=_id(f"direct-verification:{ordinal}"),
    )
    return result, verification


@pytest.fixture
def mechanics_bundle(
    source_replay,
    monkeypatch: pytest.MonkeyPatch,
):
    chain, plan, chain_ids = _authority_and_plan(source_replay)
    source_id, manifest_id, final_id, anchor_id, attestation_id = chain_ids
    del source_id, attestation_id
    adaptive_verifications: dict[str, Any] = {}
    direct_verifications: dict[str, Any] = {}
    contexts = {
        item.context_id: item
        for item in prereg.registered_heldout_public_contexts_v2()
    }
    canonical_direct_plans = {
        occurrence.template.context_id:
            direct.RegisteredMatchedDirectOccurrencePlanV1(
                anchor_id,
                contexts[occurrence.template.context_id].context_id,
                contexts[occurrence.template.context_id].context_key,
                occurrence.template.context_ordinal,
                occurrence.template.arm_ordinal,
                occurrence.template.occurrence_ordinal,
            )
        for occurrence in plan.occurrences
        if (
            occurrence.template.route_kind
            is consumer.RegisteredRouteKindV1.MATCHED_DIRECT_GROUND
        )
    }
    routes = []
    for occurrence in plan.occurrences:
        context = contexts[occurrence.template.context_id]
        if (
            occurrence.template.route_kind
            is consumer.RegisteredRouteKindV1.ADAPTIVE_QUOTIENT
        ):
            result, verification = _adaptive_route(
                chain_id=chain.chain_id,
                anchor_id=anchor_id,
                plan=occurrence,
                context=context,
            )
            adaptive_verifications[result.execution.result_id] = verification
        else:
            result, verification = _direct_route(
                chain_id=chain.chain_id,
                anchor_id=anchor_id,
                final_id=final_id,
                plan=occurrence,
                context=context,
            )
            direct_verifications[result.result_id] = verification
        routes.append(result)

    monkeypatch.setattr(
        consumer,
        "verify_registered_campaign_authority_chain_v1",
        lambda value: (
            source_replay.recipe_id,
            manifest_id,
            final_id,
            anchor_id,
            _id("anchor-attestation"),
        )
        if value is chain
        else (_ for _ in ()).throw(ValueError("foreign chain")),
    )
    monkeypatch.setattr(
        adaptive_independent,
        "verify_registered_adaptive_runtime_independently_v1",
        lambda **kwargs: adaptive_verifications[
            kwargs["claimed"].result_id
        ],
    )
    monkeypatch.setattr(
        direct,
        "verify_registered_matched_direct_occurrence_result_v1",
        lambda value: direct_verifications[value.result_id],
    )
    monkeypatch.setattr(
        direct,
        "registered_matched_direct_occurrence_plan_v1",
        lambda *, anchor, context: canonical_direct_plans[context.context_id],
    )
    return chain, plan, tuple(routes), source_replay


def _reconcile(mechanics_bundle):
    chain, plan, routes, source_replay = mechanics_bundle
    return reconciliation.reconcile_registered_v072_campaign_v1(
        authority_chain=chain,
        execution_plan=plan,
        route_results=routes,
        operational_terminal_authorities=(None,) * 15,
        exact_evaluations=(None,) * 15,
        source_reconstruction_replay=source_replay,
    )


def _certified_first_occurrence(
    mechanics_bundle,
) -> tuple[
    tuple[Any, ...],
    tuple[Any | None, ...],
    tuple[Any | None, ...],
]:
    chain, plan, routes, _source_replay = mechanics_bundle
    first_plan = plan.occurrences[0]
    first_route = routes[0]
    assert type(first_route) is adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1
    certified_execution = _unsafe_clone(
        first_route.execution,
        status=adaptive.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED,
        _certificate_id=_id("adaptive-certificate:0"),
    )
    certified_route = _unsafe_clone(
        first_route,
        execution=certified_execution,
    )
    occurrence = evaluator.RegisteredOccurrenceIdentityV1(
        chain.remote_main_anchor.anchor_id,
        first_plan.template.context_id,
        first_plan.template.context_key,
        first_plan.template.arm,
        first_plan.template.context_ordinal,
        first_plan.template.arm_ordinal,
        first_plan.template.occurrence_ordinal,
    )
    root_decision = SimpleNamespace(
        decision_id=_id("certified-root-decision:0"),
        to_document=lambda: {
            "decision_id": _id("certified-root-decision:0")
        },
    )
    modeled_support = SimpleNamespace(
        authority_id=_id("certified-modeled-support:0"),
        global_other_handler_id=_id("certified-other-handler:0"),
        to_document=lambda: {
            "authority_id": _id("certified-modeled-support:0")
        },
    )
    selected_policy = _unsafe_exact(
        evaluator.RegisteredOperationalSelectedPolicyV1,
        _operational_capability=None,
        occurrence=occurrence,
        route_kind="ADAPTIVE_QUOTIENT",
        operational_policy_source_artifact_id=certified_execution.result_id,
        independent_runtime_verification_id=(
            first_route.independent_verification.verification_id
        ),
        root_decision=root_decision,
        child_decisions=(),
        modeled_support_authority=modeled_support,
    )
    operational_terminal = _unsafe_exact(
        evaluator.RegisteredOccurrenceOperationalTerminalV1,
        _operational_capability=None,
        occurrence=occurrence,
        operational_result_artifact_id=certified_execution.result_id,
        selected_policy_id=selected_policy.selected_policy_id,
        terminal_code="CONDITIONAL_PLAN_CERTIFICATE",
    )
    bundle = evaluator.RegisteredOperationalTerminalPolicyBundleV1(
        _id("terminal-mint-authority:0"),
        operational_terminal,
        selected_policy,
    )
    authority = _unsafe_exact(
        terminal.RegisteredOperationalTerminalAuthorityResultV1,
        verified_runtime_adapter_id=_id("runtime-adapter:0"),
        mint_authority_id=bundle.mint_authority_id,
        evaluator_bundle=bundle,
        access_audit=SimpleNamespace(
            audit_id=_id("access-audit:0"),
            to_document=lambda: {
                "audit_id": _id("access-audit:0")
            },
        ),
        _authority_result_id=_id("terminal-authority-result:0"),
    )
    selected_witness = _unsafe_exact(
        evaluator.RegisteredFixedKappaPolicyWitnessV1,
        occurrence_id=occurrence.occurrence_id,
        context_id=occurrence.context_id,
        route_kind="ADAPTIVE_QUOTIENT",
        root_decision=root_decision,
        child_decisions=(),
        expected_reward=Fraction(1),
        failure_probability=Fraction(0),
        environment_failure_probability=Fraction(0),
        policy_abort_failure_probability=Fraction(0),
        policy_abort_branches=(),
        exact_branch_partitions=(),
        modeled_policy_support_authority_id=(
            modeled_support.authority_id
        ),
        global_other_handler_id=modeled_support.global_other_handler_id,
        query_binding_id=_id("certified-query-binding:0"),
        operational_audit_id=_id("certified-operational-audit:0"),
        operational_root_reward_lower=Fraction(1),
        operational_unrestricted_reward_upper=Fraction(1),
        operational_root_failure_upper=Fraction(0),
        operational_normalized_regret_upper=Fraction(0),
        exact_normalized_regret=Fraction(0),
        reward_containment_pass=True,
        failure_containment_pass=True,
        normalized_regret_containment_pass=True,
        operational_envelope_containment_pass=True,
    )
    work = evaluator.RegisteredExactGroundEvaluationWorkV1(
        evaluation_exact_atom_api_calls=1,
        exact_rows_reconstructed=1,
        exact_atoms_reconstructed=1,
        dp_candidate_extensions=1,
        dp_dominance_comparisons=0,
        dp_frontier_points_retained=1,
        selected_policy_assignments_checked=1,
    )
    evaluation = _unsafe_exact(
        evaluator.RegisteredIndependentExactGroundEvaluationResultV1,
        anchor_id=occurrence.anchor_id,
        occurrence=occurrence,
        operational_terminal_id=operational_terminal.terminal_id,
        operational_selected_policy_id=selected_policy.selected_policy_id,
        status=(
            evaluator.RegisteredExactGroundEvaluationStatusV1
            .CERTIFICATE_METRICS_PASS
        ),
        rows=(
            SimpleNamespace(
                row_id=_id("exact-row:0"),
                to_document=lambda: {
                    "row_id": _id("exact-row:0")
                },
            ),
        ),
        optimal_policy=SimpleNamespace(
            policy_witness_id=_id("optimal-policy:0"),
            to_document=lambda: {
                "policy_witness_id": _id("optimal-policy:0")
            },
        ),
        selected_policy=selected_witness,
        optimal_expected_reward=Fraction(1),
        optimal_failure_probability=Fraction(0),
        selected_expected_reward=Fraction(1),
        selected_failure_probability=Fraction(0),
        regret=Fraction(0),
        normalized_regret=Fraction(0),
        risk_pass=True,
        regret_pass=True,
        certificate_metrics_pass=True,
        work=work,
        execution_lane=evaluator.EVALUATION_LANE,
        operational_work_included=False,
    )
    return (
        (certified_route, *routes[1:]),
        (authority,) + (None,) * 14,
        (evaluation,) + (None,) * 14,
    )


def test_complete_noncertificate_campaign_reconciles_and_replays(
    mechanics_bundle,
) -> None:
    chain, plan, _routes, source_replay = mechanics_bundle
    result = _reconcile(mechanics_bundle)
    assert len(result.occurrences) == 15
    assert result.campaign_totals.plan_certificate_count == 0
    assert result.campaign_totals.noncertificate_count == 15
    assert result.logical_occurrence_denominator == 15
    assert result.source_offline.online_draws_charged == 0
    assert result.source_offline.unique_physical_raw_draws == 9
    assert result.campaign_totals.crn_discount_draws == 0
    assert result.campaign_totals.online_acquisition_draws == sum(
        item.work.online_acquisition_draws for item in result.occurrences
    )
    assert result.campaign_totals.target_replay_draws == sum(
        item.work.target_replay_draws for item in result.occurrences
    )
    verification = (
        independent
        .verify_registered_v072_campaign_reconciliation_independently_v1(
            authority_chain=chain,
            execution_plan=plan,
            source_reconstruction_replay=source_replay,
            claimed=result,
        )
    )
    assert verification.reconciliation_id == result.reconciliation_id
    assert verification.logical_occurrence_denominator == 15


def test_reconciliation_rejects_unknown_route_kind_without_defaulting_direct(
    mechanics_bundle,
) -> None:
    chain, plan, routes, _source_replay = mechanics_bundle
    valid_plan = plan.occurrences[0]
    forged_template = _unsafe_clone(
        valid_plan.template,
        route_kind=object(),
    )
    forged_plan = _unsafe_clone(
        valid_plan,
        template=forged_template,
    )
    context = next(
        item
        for item in prereg.registered_heldout_public_contexts_v2()
        if item.context_id == valid_plan.template.context_id
    )

    with pytest.raises(
        reconciliation.V072RegisteredCampaignReconciliationViolation,
        match="unknown route kind",
    ):
        reconciliation._reconcile_route_occurrence_v1(
            authority_chain=chain,
            anchor_id=chain.remote_main_anchor.anchor_id,
            final_preregistration_id=_id("route-dispatch-final-prereg"),
            plan=forged_plan,
            context=context,
            route_result=routes[0],
            operational_terminal_authority=None,
            exact_evaluation=None,
        )


def test_certified_occurrence_is_registration_disjoint_and_replays(
    mechanics_bundle,
    monkeypatch,
) -> None:
    chain, plan, _routes, source_replay = mechanics_bundle
    routes, authorities, evaluations = _certified_first_occurrence(
        mechanics_bundle
    )
    asserted_authority = authorities[0]
    asserted_evaluation = evaluations[0]
    assert asserted_authority is not None
    assert asserted_evaluation is not None
    monkeypatch.setattr(
        terminal,
        "derive_registered_operational_terminal_authority_v1",
        lambda **_kwargs: asserted_authority,
    )
    monkeypatch.setattr(
        evaluator,
        "evaluate_registered_independent_exact_ground_v2",
        lambda **_kwargs: asserted_evaluation,
    )
    result = reconciliation.reconcile_registered_v072_campaign_v1(
        authority_chain=chain,
        execution_plan=plan,
        route_results=routes,
        operational_terminal_authorities=authorities,
        exact_evaluations=evaluations,
        source_reconstruction_replay=source_replay,
    )
    first = result.occurrences[0]
    assert first.terminal_code == "CONDITIONAL_PLAN_CERTIFICATE"
    assert result.campaign_totals.plan_certificate_count == 1
    assert result.campaign_totals.noncertificate_count == 14
    verification = (
        independent
        .verify_registered_v072_campaign_reconciliation_independently_v1(
            authority_chain=chain,
            execution_plan=plan,
            source_reconstruction_replay=source_replay,
            claimed=result,
        )
    )
    assert verification.reconciliation_id == result.reconciliation_id

    tampered_authority_replay = _unsafe_clone(
        asserted_authority,
        _authority_result_id=_id("tampered-authority-replay"),
    )
    monkeypatch.setattr(
        terminal,
        "derive_registered_operational_terminal_authority_v1",
        lambda **_kwargs: tampered_authority_replay,
    )
    with pytest.raises(
        independent.IndependentRegisteredCampaignReconciliationFailure,
        match="operational terminal authority",
    ):
        independent.verify_registered_v072_campaign_reconciliation_independently_v1(
            authority_chain=chain,
            execution_plan=plan,
            source_reconstruction_replay=source_replay,
            claimed=result,
        )
    monkeypatch.setattr(
        terminal,
        "derive_registered_operational_terminal_authority_v1",
        lambda **_kwargs: asserted_authority,
    )

    tampered_replay = _unsafe_clone(
        asserted_evaluation,
        selected_expected_reward=Fraction(2),
    )
    monkeypatch.setattr(
        evaluator,
        "evaluate_registered_independent_exact_ground_v2",
        lambda **_kwargs: tampered_replay,
    )
    with pytest.raises(
        independent.IndependentRegisteredCampaignReconciliationFailure,
        match="exact rows, atoms, branch partition",
    ):
        independent.verify_registered_v072_campaign_reconciliation_independently_v1(
            authority_chain=chain,
            execution_plan=plan,
            source_reconstruction_replay=source_replay,
            claimed=result,
        )
    monkeypatch.setattr(
        evaluator,
        "evaluate_registered_independent_exact_ground_v2",
        lambda **_kwargs: asserted_evaluation,
    )

    authority = authorities[0]
    assert authority is not None
    policy = authority.evaluator_bundle.selected_policy
    transplanted_policy = _unsafe_clone(
        policy,
        independent_runtime_verification_id=_id("foreign-runtime-verification"),
    )
    transplanted_bundle = _unsafe_clone(
        authority.evaluator_bundle,
        selected_policy=transplanted_policy,
    )
    transplanted_authority = _unsafe_clone(
        authority,
        evaluator_bundle=transplanted_bundle,
    )
    with pytest.raises(
        reconciliation.V072RegisteredCampaignReconciliationViolation,
        match="identity or exact metrics",
    ):
        reconciliation.reconcile_registered_v072_campaign_v1(
            authority_chain=chain,
            execution_plan=plan,
            route_results=routes,
            operational_terminal_authorities=(
                (transplanted_authority,) + authorities[1:]
            ),
            exact_evaluations=evaluations,
            source_reconstruction_replay=source_replay,
        )

    first_evaluation = evaluations[0]
    assert first_evaluation is not None
    transplanted_evaluation = _unsafe_clone(
        first_evaluation,
        operational_selected_policy_id=_id("foreign-selected-policy"),
    )
    with pytest.raises(
        reconciliation.V072RegisteredCampaignReconciliationViolation,
        match="identity or exact metrics",
    ):
        reconciliation.reconcile_registered_v072_campaign_v1(
            authority_chain=chain,
            execution_plan=plan,
            route_results=routes,
            operational_terminal_authorities=authorities,
            exact_evaluations=(
                (transplanted_evaluation,) + evaluations[1:]
            ),
            source_reconstruction_replay=source_replay,
        )


def test_direct_native_plan_domain_is_distinct_and_transplant_rejected(
    mechanics_bundle,
) -> None:
    chain, plan, routes, source_replay = mechanics_bundle
    index = 4
    occurrence_plan = plan.occurrences[index]
    route = routes[index]
    assert type(route) is direct.RegisteredMatchedDirectOccurrenceResultV1
    context = prereg.registered_heldout_public_contexts_v2()[0]
    canonical_direct_plan = direct.RegisteredMatchedDirectOccurrencePlanV1(
        chain.remote_main_anchor.anchor_id,
        context.context_id,
        context.context_key,
        occurrence_plan.template.context_ordinal,
        occurrence_plan.template.arm_ordinal,
        occurrence_plan.template.occurrence_ordinal,
    )
    assert route.occurrence_plan_id == canonical_direct_plan.plan_id
    assert route.occurrence_plan_id != occurrence_plan.occurrence_id

    transplanted_route = _unsafe_clone(
        route,
        occurrence_plan_id=occurrence_plan.occurrence_id,
    )
    transplanted_routes = (
        *routes[:index],
        transplanted_route,
        *routes[index + 1:],
    )
    with pytest.raises(
        reconciliation.V072RegisteredCampaignReconciliationViolation,
        match="reused or transplanted",
    ):
        reconciliation.reconcile_registered_v072_campaign_v1(
            authority_chain=chain,
            execution_plan=plan,
            route_results=transplanted_routes,
            operational_terminal_authorities=(None,) * 15,
            exact_evaluations=(None,) * 15,
            source_reconstruction_replay=source_replay,
        )

    baseline = _reconcile(mechanics_bundle)
    transplanted_occurrence = _unsafe_clone(
        baseline.occurrences[index],
        route_result=transplanted_route,
    )
    forged = _unsafe_clone(
        baseline,
        occurrences=(
            *baseline.occurrences[:index],
            transplanted_occurrence,
            *baseline.occurrences[index + 1:],
        ),
    )
    with pytest.raises(
        independent.IndependentRegisteredCampaignReconciliationFailure,
        match="reused or transplanted",
    ):
        independent.verify_registered_v072_campaign_reconciliation_independently_v1(
            authority_chain=chain,
            execution_plan=plan,
            source_reconstruction_replay=source_replay,
            claimed=forged,
        )


@pytest.mark.parametrize(
    "mutation",
    ("missing", "reordered", "duplicated"),
)
def test_input_occurrence_omission_reorder_and_reuse_fail(
    mechanics_bundle,
    mutation: str,
) -> None:
    chain, plan, routes, source_replay = mechanics_bundle
    changed = {
        "missing": routes[:-1],
        "reordered": (routes[1], routes[0], *routes[2:]),
        "duplicated": (routes[0], routes[0], *routes[2:]),
    }[mutation]
    with pytest.raises(
        reconciliation.V072RegisteredCampaignReconciliationViolation,
    ):
        reconciliation.reconcile_registered_v072_campaign_v1(
            authority_chain=chain,
            execution_plan=plan,
            route_results=changed,
            operational_terminal_authorities=(None,) * 15,
            exact_evaluations=(None,) * 15,
            source_reconstruction_replay=source_replay,
        )


def test_noncertificate_cannot_receive_plan_only_artifacts(
    mechanics_bundle,
) -> None:
    chain, plan, routes, source_replay = mechanics_bundle
    with pytest.raises(
        reconciliation.V072RegisteredCampaignReconciliationViolation,
        match="plan-only",
    ):
        reconciliation.reconcile_registered_v072_campaign_v1(
            authority_chain=chain,
            execution_plan=plan,
            route_results=routes,
            operational_terminal_authorities=(object(),) + (None,) * 14,
            exact_evaluations=(None,) * 15,
            source_reconstruction_replay=source_replay,
        )


def test_crn_discount_and_source_online_mixing_are_rejected(
    mechanics_bundle,
) -> None:
    chain, plan, _routes, source_replay = mechanics_bundle
    baseline = _reconcile(mechanics_bundle)
    first = baseline.occurrences[0]
    forged_work = _unsafe_clone(
        first.work,
        online_acquisition_draws=(
            first.work.online_acquisition_draws
            + first.work.target_replay_draws
        ),
        target_replay_draws=0,
    )
    forged_first = _unsafe_clone(first, work=forged_work)
    forged = _unsafe_clone(
        baseline,
        occurrences=(forged_first, *baseline.occurrences[1:]),
    )
    with pytest.raises(
        independent.IndependentRegisteredCampaignReconciliationFailure,
        match="work differs",
    ):
        independent.verify_registered_v072_campaign_reconciliation_independently_v1(
            authority_chain=chain,
            execution_plan=plan,
            source_reconstruction_replay=source_replay,
            claimed=forged,
        )

    forged_source = _unsafe_clone(
        baseline.source_offline,
        online_draws_charged=baseline.source_offline.unique_physical_raw_draws,
    )
    forged = _unsafe_clone(baseline, source_offline=forged_source)
    with pytest.raises(
        independent.IndependentRegisteredCampaignReconciliationFailure,
        match="source offline union",
    ):
        independent.verify_registered_v072_campaign_reconciliation_independently_v1(
            authority_chain=chain,
            execution_plan=plan,
            source_reconstruction_replay=source_replay,
            claimed=forged,
        )


def test_model_terminal_and_deleted_noncertificate_attacks_fail(
    mechanics_bundle,
) -> None:
    chain, plan, _routes, source_replay = mechanics_bundle
    baseline = _reconcile(mechanics_bundle)
    first = baseline.occurrences[0]
    forged_first = _unsafe_clone(
        first,
        final_planner_model_id=_id("foreign-model"),
    )
    forged = _unsafe_clone(
        baseline,
        occurrences=(forged_first, *baseline.occurrences[1:]),
    )
    with pytest.raises(
        independent.IndependentRegisteredCampaignReconciliationFailure,
        match="model identity",
    ):
        independent.verify_registered_v072_campaign_reconciliation_independently_v1(
            authority_chain=chain,
            execution_plan=plan,
            source_reconstruction_replay=source_replay,
            claimed=forged,
        )

    forged_first = _unsafe_clone(
        first,
        terminal_code="TWO_ROUND_CAP_EXHAUSTED_NONCERTIFICATE",
    )
    forged = _unsafe_clone(
        baseline,
        occurrences=(forged_first, *baseline.occurrences[1:]),
    )
    with pytest.raises(
        independent.IndependentRegisteredCampaignReconciliationFailure,
        match="terminal or model",
    ):
        independent.verify_registered_v072_campaign_reconciliation_independently_v1(
            authority_chain=chain,
            execution_plan=plan,
            source_reconstruction_replay=source_replay,
            claimed=forged,
        )

    forged = _unsafe_clone(
        baseline,
        occurrences=baseline.occurrences[:-1],
    )
    with pytest.raises(
        independent.IndependentRegisteredCampaignReconciliationFailure,
        match="all 15",
    ):
        independent.verify_registered_v072_campaign_reconciliation_independently_v1(
            authority_chain=chain,
            execution_plan=plan,
            source_reconstruction_replay=source_replay,
            claimed=forged,
        )
