from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_registered_adaptive_quotient_runtime_v1 as runtime
from acfqp import (
    v072_registered_adaptive_quotient_runtime_independent_verifier_v1
    as independent,
)
from acfqp import (
    v072_registered_incremental_epoch_independent_verifier_v1
    as incremental_independent,
)
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import (
    v072_registered_target_confidence_accumulator_v1 as accumulator,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


ROWS = tuple(_id(f"synthetic-adaptive-row-{index}") for index in range(6))


def _proposal(
    *,
    arm: str = "SOURCE_CONSENSUS_PRIOR",
    ordering_basis_id: str | None = None,
) -> runtime.RegistrationDisjointAdaptiveProposalOrderV1:
    basis = {
        "SOURCE_CONSENSUS_PRIOR": (
            runtime.RegistrationDisjointAdaptiveProposalBasisV1
            .SOURCE_ARCHIVE
        ),
        "NO_PRIOR": (
            runtime.RegistrationDisjointAdaptiveProposalBasisV1.NO_PRIOR
        ),
        "WRONG_CONSENSUS_PRIOR": (
            runtime.RegistrationDisjointAdaptiveProposalBasisV1
            .WRONG_SOURCE_ARCHIVE
        ),
        "OOD_ABSTENTION": (
            runtime.RegistrationDisjointAdaptiveProposalBasisV1
            .OOD_TYPED_ABSTENTION
        ),
    }[arm]
    if ordering_basis_id is None and arm != "NO_PRIOR":
        ordering_basis_id = _id(f"synthetic-order-basis-{arm}")
    return runtime.RegistrationDisjointAdaptiveProposalOrderV1(
        arm,
        basis,
        ordering_basis_id,
        ROWS,
    )


def _cold() -> tuple[
    runtime.RegistrationDisjointAdaptiveAcquisitionV1, ...
]:
    return tuple(
        runtime.RegistrationDisjointAdaptiveAcquisitionV1(
            0,
            row,
            runtime.RegistrationDisjointAcquisitionPurposeV1.COLD_INITIAL,
        )
        for row in ROWS[:2]
    )


def _cold_epoch(
    cold: tuple[runtime.RegistrationDisjointAdaptiveAcquisitionV1, ...],
) -> runtime.RegistrationDisjointAdaptiveModelEpochV1:
    ids = tuple(sorted(item.acquisition_id for item in cold))
    return runtime.RegistrationDisjointAdaptiveModelEpochV1(
        0,
        None,
        None,
        ids,
        ids,
    )


def _extend(
    *,
    epoch: runtime.RegistrationDisjointAdaptiveModelEpochV1,
    audit: runtime.RegistrationDisjointAdaptiveAuditV1,
    round_index: int,
    row: str,
    previous_frontier: (
        runtime.RegistrationDisjointAdaptiveFrontierV1 | None
    ) = None,
    purpose: runtime.RegistrationDisjointAcquisitionPurposeV1 = (
        runtime.RegistrationDisjointAcquisitionPurposeV1.NEW_CHILD
    ),
    parent: (
        runtime.RegistrationDisjointAdaptiveAcquisitionV1 | None
    ) = None,
) -> tuple[
    runtime.RegistrationDisjointAdaptiveLocalRoundV1,
    runtime.RegistrationDisjointAdaptiveModelEpochV1,
    runtime.RegistrationDisjointAdaptiveAcquisitionV1,
]:
    frontier = runtime.RegistrationDisjointAdaptiveFrontierV1(
        round_index,
        epoch.epoch_id,
        audit.audit_id,
        (
            None
            if previous_frontier is None
            else previous_frontier.frontier_id
        ),
        epoch.cumulative_acquisition_ids,
        (row,),
        (_id(f"synthetic-proof-obligation-{round_index}"),),
    )
    acquisition = runtime.RegistrationDisjointAdaptiveAcquisitionV1(
        round_index,
        row,
        purpose,
        frontier.frontier_id,
        None if parent is None else parent.acquisition_id,
    )
    local_round = runtime.RegistrationDisjointAdaptiveLocalRoundV1(
        frontier,
        (acquisition,),
    )
    new_ids = (acquisition.acquisition_id,)
    next_epoch = runtime.RegistrationDisjointAdaptiveModelEpochV1(
        round_index,
        epoch.epoch_id,
        frontier.frontier_id,
        tuple(sorted((*epoch.cumulative_acquisition_ids, *new_ids))),
        new_ids,
    )
    return local_round, next_epoch, acquisition


def _run(
    statuses: tuple[
        runtime.RegistrationDisjointAdaptiveAuditStatusV1, ...
    ],
    *,
    proposal: (
        runtime.RegistrationDisjointAdaptiveProposalOrderV1 | None
    ) = None,
) -> runtime.RegistrationDisjointAdaptiveRunV1:
    if not 1 <= len(statuses) <= 3:
        raise AssertionError("test helper supports cold plus two rounds")
    proposal = _proposal() if proposal is None else proposal
    cold = _cold()
    epoch = _cold_epoch(cold)
    epochs = [epoch]
    audit = runtime.RegistrationDisjointAdaptiveAuditV1(
        epoch.epoch_id,
        0,
        statuses[0],
    )
    audits = [audit]
    rounds: list[runtime.RegistrationDisjointAdaptiveLocalRoundV1] = []
    previous_frontier = None
    for round_index, status in enumerate(statuses[1:], start=1):
        local_round, epoch, _acquisition = _extend(
            epoch=epoch,
            audit=audit,
            round_index=round_index,
            row=ROWS[round_index + 1],
            previous_frontier=previous_frontier,
        )
        rounds.append(local_round)
        previous_frontier = local_round.frontier
        epochs.append(epoch)
        audit = runtime.RegistrationDisjointAdaptiveAuditV1(
            epoch.epoch_id,
            round_index,
            status,
        )
        audits.append(audit)
    return runtime.run_registration_disjoint_adaptive_state_machine_core_v1(
        proposal_order=proposal,
        cold_acquisitions=cold,
        local_rounds=tuple(rounds),
        epochs=tuple(epochs),
        audits=tuple(audits),
    )


def test_production_entry_accepts_no_injected_evidence_or_decision() -> None:
    signature = inspect.signature(
        runtime.run_registered_adaptive_quotient_occurrence_v1
    )
    assert tuple(signature.parameters) == (
        "authority_chain",
        "anchor",
        "occurrence_plan",
        "context",
    )
    assert all(
        item.kind is inspect.Parameter.KEYWORD_ONLY
        for item in signature.parameters.values()
    )
    assert {
        "callback",
        "observations",
        "transcript",
        "law",
        "seed",
        "probabilities",
        "counts",
        "status",
        "terminal",
        "planner_result",
    }.isdisjoint(signature.parameters)
    verification_signature = inspect.signature(
        runtime.verify_registered_adaptive_quotient_occurrence_result_v1
    )
    assert tuple(verification_signature.parameters) == (
        "authority_chain",
        "anchor",
        "occurrence_plan",
        "context",
        "claimed",
    )
    assert all(
        item.kind is inspect.Parameter.KEYWORD_ONLY
        for item in verification_signature.parameters.values()
    )


def test_dependency_protocol_binds_actual_apis_and_exact_blockers() -> None:
    dependency = runtime.inspect_registered_adaptive_dependency_protocol_v1()
    assert dependency.blockers == (
        runtime.EVALUATOR_TERMINAL_MINT_BLOCKER,
    )
    assert runtime.INCREMENTAL_MODEL_EPOCH_BLOCKER is None
    assert runtime.EVALUATOR_TERMINAL_MINT_BLOCKER == (
        "REGISTERED_FIXED_CONCRETIZER_"
        "OPERATIONAL_POLICY_SCHEMA_NOT_INTEGRATED"
    )
    assert dependency.authority_chain_verifier_entrypoint.endswith(
        "verify_registered_campaign_authority_chain_v1"
    )
    assert dependency.cold_model_epoch_type.endswith(
        "RegisteredColdH2ModelEpochV1"
    )
    assert dependency.cold_model_epoch_entrypoint.endswith(
        "build_registered_cold_h2_model_epoch_v1"
    )
    assert dependency.target_accumulator_type.endswith(
        "RegisteredTargetRowAcquisitionV1"
    )
    assert dependency.target_accumulator_entrypoint.endswith(
        "acquire_registered_target_row_v1"
    )
    assert tuple(
        inspect.signature(
            accumulator.acquire_registered_target_row_v1
        ).parameters
    ) == (
        "authority_chain",
        "anchor",
        "context",
        "catalogue",
        "action",
        "arm",
        "purpose",
        "checkpoint",
        "frontier",
        "parent",
    )
    assert dependency.target_confidence_replay_entrypoint.endswith(
        "verify_registered_target_confidence_independently_v1"
    )
    assert dependency.cold_model_builder_entrypoint.endswith(
        "build_registered_target_cold_h2_models_v1"
    )
    assert dependency.frontier_selector_type.endswith(
        "RegisteredSelectorClosureV1"
    )
    assert dependency.frontier_selector_entrypoint.endswith(
        "prepare_registered_acquisition_frontier_v1"
    )
    assert dependency.frontier_selector_verifier_entrypoint.endswith(
        "verify_registered_selector_independently_v1"
    )
    assert dependency.incremental_model_epoch_type.endswith(
        "RegisteredIncrementalH2ModelEpochV1"
    )
    assert dependency.incremental_model_epoch_entrypoint.endswith(
        "materialize_registered_incremental_h2_model_epoch_v1"
    )
    assert dependency.incremental_model_epoch_verifier_type.endswith(
        "RegisteredIncrementalEpochIndependentAttestationV1"
    )
    assert dependency.incremental_model_epoch_verifier_entrypoint.endswith(
        "verify_registered_incremental_h2_model_epoch_independently_v1"
    )
    assert dependency.quotient_planner_entrypoint.endswith(
        "solve_and_verify_v072_exact_lazy_h2_v1"
    )
    assert dependency.proof_verifier_entrypoint.endswith(
        "verify_exact_lazy_h2_solve_result_v1"
    )
    assert dependency.evaluator_terminal_factory_entrypoint.endswith(
        "derive_registered_operational_terminal_authority_v1"
    )
    assert dependency.dependencies_available is True
    document = dependency.to_document()
    assert document["adaptive_planning_dependencies_available"] is True
    assert document["operational_terminal_adapter_available"] is False
    assert document["caller_callback_allowed"] is False
    assert document["caller_observations_allowed"] is False
    assert (
        document[
            "source_quantities_allowed_in_confidence_model_certificate"
        ]
        is False
    )


def test_public_identity_validator_accepts_only_four_adaptive_arms() -> None:
    context = prereg.registered_heldout_public_contexts_v2()[0]
    templates = tuple(
        item
        for item in consumer.registered_occurrence_templates_v1()
        if item.context_id == context.context_id
    )
    plans = tuple(
        consumer.RegisteredOccurrenceExecutionPlanV1(
            _id("synthetic-nonauthorizing-chain"),
            template,
        )
        for template in templates
    )
    accepted = tuple(
        runtime.validate_registered_adaptive_occurrence_identity_v1(
            occurrence_plan=plan,
            context=context,
        ).template.arm
        for plan in plans[:-1]
    )
    assert accepted == runtime.ADAPTIVE_ARMS
    with pytest.raises(
        runtime.V072RegisteredAdaptiveRuntimeInvariantViolation,
        match="four registered adaptive arms",
    ):
        runtime.validate_registered_adaptive_occurrence_identity_v1(
            occurrence_plan=plans[-1],
            context=context,
        )


@pytest.mark.parametrize("arm", runtime.ADAPTIVE_ARMS)
def test_every_adaptive_arm_is_proposal_only(arm: str) -> None:
    proposal = _proposal(
        arm=arm,
        ordering_basis_id=(
            None if arm == "NO_PRIOR" else _id(f"proposal-basis-{arm}")
        ),
    )
    document = proposal.to_document()
    assert document["ordering_only"] is True
    assert document["enters_confidence"] is False
    assert document["enters_model_identity"] is False
    assert document["enters_certificate_identity"] is False


def test_invalid_anchor_or_identity_fails_before_observer_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*_args: object, **_kwargs: object) -> None:
        calls.append("TARGET_ACCESS")
        raise AssertionError("pre-anchor target access occurred")

    for module, name in (
        (observer, "_environment_law"),
        (observer, "open_heldout_target_transition_stream_v2"),
        (observer, "evaluation_only_exact_atoms_v2"),
        (observer.AnchorGatedHeldoutTransitionStreamV2, "draw"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    for nonanchor in (None, object()):
        with pytest.raises(runtime.RegisteredAdaptiveRuntimeLockedV1) as error:
            runtime.run_registered_adaptive_quotient_occurrence_v1(
                authority_chain=object(),  # type: ignore[arg-type]
                anchor=nonanchor,  # type: ignore[arg-type]
                occurrence_plan=object(),  # type: ignore[arg-type]
                context=object(),  # type: ignore[arg-type]
            )
        assert error.value.access_audit == runtime.ZERO_ACCESS_AUDIT
        assert (
            error.value.access_audit.observer_or_target_access_started
            is False
        )
    assert calls == []


def test_independent_preflight_is_target_free_and_exactly_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*_args: object, **_kwargs: object) -> None:
        calls.append("TARGET_ACCESS")
        raise AssertionError("independent preflight opened the target")

    for module, name in (
        (observer, "_environment_law"),
        (observer, "open_heldout_target_transition_stream_v2"),
        (observer, "evaluation_only_exact_atoms_v2"),
        (observer.AnchorGatedHeldoutTransitionStreamV2, "draw"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    with pytest.raises(
        independent.RegisteredAdaptiveRuntimeIndependentGateLockedV1
    ) as error:
        independent.verify_registered_adaptive_runtime_independently_v1(
            authority_chain=object(),  # type: ignore[arg-type]
            anchor=object(),  # type: ignore[arg-type]
            occurrence_plan=object(),  # type: ignore[arg-type]
            context=object(),  # type: ignore[arg-type]
            claimed=object(),  # type: ignore[arg-type]
        )
    assert error.value.observer_stream_opens == 0
    assert error.value.observer_draw_calls == 0
    assert calls == []


def test_fixed_concretizer_exports_distinct_support_and_exact_weights() -> None:
    action_ids = tuple(
        sorted((_id("fixed-kappa-action-a"), _id("fixed-kappa-action-b")))
    )
    decision = runtime.RegisteredAdaptiveConcretizerDecisionV1(
        _id("fixed-kappa-model"),
        _id("fixed-kappa-ground-state"),
        _id("fixed-kappa-public-state"),
        (1, 2, 0),
        1,
        _id("fixed-kappa-coordinate"),
        _id("fixed-kappa-abstract-action"),
        _id("fixed-kappa-entry"),
        action_ids,
        (
            _id("fixed-kappa-semantic-action-a"),
            _id("fixed-kappa-semantic-action-b"),
        ),
        ((0, 1, 0), (1, 2, 1)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    document = decision.to_document()
    assert decision.singleton is False
    assert len(set(document["ground_action_ids"])) == 2
    assert document["uniform_weights"] == [
        {"numerator": 1, "denominator": 2},
        {"numerator": 1, "denominator": 2},
    ]
    assert document["fixed_concretizer"] is True
    assert document["source_quantities_used"] is False
    assert "selected_ground_action" not in document
    assert not hasattr(decision, "selected_ground_action")
    with pytest.raises(
        runtime.V072RegisteredAdaptiveRuntimeInvariantViolation,
        match="concretizer support is malformed",
    ):
        replace(
            decision,
            uniform_weights=(Fraction(1, 2), Fraction(1, 3)),
        )


def test_fixed_concretizer_gap_does_not_reclassify_certificate_status() -> None:
    assert (
        runtime.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED.value
        == "CERTIFIED"
    )
    assert (
        runtime.RegisteredAdaptiveGroundAdapterStatusV1
        .FIXED_CONCRETIZER_OPERATIONAL_POLICY_SCHEMA_NOT_INTEGRATED.value
        == runtime.EVALUATOR_TERMINAL_MINT_BLOCKER
    )
    assert runtime.EVALUATOR_TERMINAL_MINT_BLOCKER not in {
        item.value for item in runtime.RegisteredAdaptiveOccurrenceStatusV1
    }


def test_result_verification_and_attestation_cannot_be_publicly_minted() -> None:
    with pytest.raises(
        runtime.V072RegisteredAdaptiveRuntimeInvariantViolation,
        match="occurrence result is malformed",
    ):
        runtime.RegisteredAdaptiveOccurrenceResultV1(
            object(),
            _id("private-result-chain"),
            _id("private-result-anchor"),
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            (),
            (),
            (),
            runtime.RegisteredAdaptiveOccurrenceStatusV1.NO_SOUND_COVER,
            (),
            (),
            (
                runtime.RegisteredAdaptiveGroundAdapterStatusV1
                .NOT_APPLICABLE_NONCERTIFICATE
            ),
            object(),  # type: ignore[arg-type]
        )
    with pytest.raises(
        runtime.V072RegisteredAdaptiveRuntimeInvariantViolation,
        match="not independently minted",
    ):
        runtime.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1(
            object(),
            object(),  # type: ignore[arg-type]
            object(),
        )
    with pytest.raises(
        independent.V072RegisteredAdaptiveRuntimeIndependentVerificationFailure,
        match="not privately replayed",
    ):
        independent.RegisteredAdaptiveRuntimeIndependentVerificationV1(
            object(),
            _id("private-verification-chain"),
            _id("private-verification-anchor"),
            _id("private-verification-occurrence"),
            _id("private-verification-context"),
            _id("private-verification-result"),
            None,
            runtime.RegisteredAdaptiveOccurrenceStatusV1.NO_SOUND_COVER,
            (
                runtime.RegisteredAdaptiveGroundAdapterStatusV1
                .NOT_APPLICABLE_NONCERTIFICATE
            ),
            (_id("private-verification-epoch"),),
            (),
            (_id("private-verification-model-replay"),),
            (_id("private-verification-planner"),),
            (),
            (),
            (),
            (),
            _id("private-verification-work"),
        )


def test_independent_source_does_not_reuse_producer_policy_or_target() -> None:
    source = inspect.getsource(independent)
    assert "runtime.derive_registered_adaptive_policy_support_v1" not in source
    assert "open_heldout_target_transition_stream_v2" not in source
    assert "acquire_registered_target_row_v1" not in source


def test_incremental_attestation_lineage_rejects_missing_reordered_stale() -> None:
    epochs = tuple(_id(f"adaptive-attestation-epoch-{index}") for index in range(3))
    acquisitions = tuple(
        sorted(_id(f"adaptive-attestation-acquisition-{index}")
               for index in range(3))
    )
    first = (
        incremental_independent
        .RegistrationDisjointIncrementalEpochVerificationV1(
            epochs[0],
            _id("adaptive-attestation-selector-1"),
            epochs[1],
            1,
            acquisitions[:2],
            acquisitions[:2],
            10,
            10,
        )
    )
    second = (
        incremental_independent
        .RegistrationDisjointIncrementalEpochVerificationV1(
            epochs[1],
            _id("adaptive-attestation-selector-2"),
            epochs[2],
            2,
            acquisitions,
            acquisitions[1:],
            12,
            12,
        )
    )
    assert (
        independent
        .verify_registration_disjoint_incremental_attestation_sequence_v1(
            epoch_ids=epochs,
            attestations=(first, second),
        )
        == (first.verification_id, second.verification_id)
    )
    with pytest.raises(
        independent.V072RegisteredAdaptiveRuntimeIndependentVerificationFailure,
        match="missing or excessive",
    ):
        independent.verify_registration_disjoint_incremental_attestation_sequence_v1(
            epoch_ids=epochs,
            attestations=(first,),
        )
    with pytest.raises(
        independent.V072RegisteredAdaptiveRuntimeIndependentVerificationFailure,
        match="reordered or stale",
    ):
        independent.verify_registration_disjoint_incremental_attestation_sequence_v1(
            epoch_ids=epochs,
            attestations=(second, first),
        )
    stale = replace(second, prior_epoch_id=epochs[0])
    with pytest.raises(
        independent.V072RegisteredAdaptiveRuntimeIndependentVerificationFailure,
        match="reordered or stale",
    ):
        independent.verify_registration_disjoint_incremental_attestation_sequence_v1(
            epoch_ids=epochs,
            attestations=(first, stale),
        )


def test_incremental_independent_replay_is_counted_without_online_draws() -> None:
    work = runtime.RegisteredAdaptiveOccurrenceWorkV1(
        cold_epoch_builds=1,
        incremental_epoch_builds=2,
        incremental_epoch_independent_replay_calls=2,
        acquisition_calls=0,
        confidence_replay_calls=0,
        producer_stream_opens=0,
        producer_draw_calls=0,
        replay_stream_opens=0,
        replay_draw_calls=0,
        unique_online_sample_evidence_draws=0,
        total_observer_draw_calls=0,
        closure_builds=3,
        closure_independent_verifications=3,
        confidence_projection_calls=0,
        model_pair_builds=3,
        model_pair_independent_verifications=3,
        quotient_planner_calls=3,
        planner_proof_verification_calls=3,
        selector_calls=2,
        selector_independent_replay_calls=2,
        branch_nodes=0,
        complete_policies=0,
        root_bound_evaluations=0,
        pruned_branches=0,
        source_ordering_recipe_reads=0,
    )
    assert work.incremental_epoch_independent_replay_calls == 2
    assert work.unique_online_sample_evidence_draws == 0
    assert work.total_observer_draw_calls == 0
    with pytest.raises(
        runtime.V072RegisteredAdaptiveRuntimeInvariantViolation,
        match="does not reconcile",
    ):
        replace(work, incremental_epoch_independent_replay_calls=1)


@pytest.mark.parametrize(
    ("statuses", "terminal", "rounds"),
    (
        (
            (
                runtime.RegistrationDisjointAdaptiveAuditStatusV1
                .CERTIFIED,
            ),
            runtime.RegistrationDisjointAdaptiveTerminalStatusV1.CERTIFIED,
            0,
        ),
        (
            (
                runtime.RegistrationDisjointAdaptiveAuditStatusV1
                .NOT_CERTIFIED,
                runtime.RegistrationDisjointAdaptiveAuditStatusV1
                .CERTIFIED,
            ),
            runtime.RegistrationDisjointAdaptiveTerminalStatusV1.CERTIFIED,
            1,
        ),
        (
            (
                runtime.RegistrationDisjointAdaptiveAuditStatusV1
                .NOT_CERTIFIED,
                runtime.RegistrationDisjointAdaptiveAuditStatusV1
                .NOT_CERTIFIED,
                runtime.RegistrationDisjointAdaptiveAuditStatusV1
                .CERTIFIED,
            ),
            runtime.RegistrationDisjointAdaptiveTerminalStatusV1.CERTIFIED,
            2,
        ),
        (
            (
                runtime.RegistrationDisjointAdaptiveAuditStatusV1
                .NOT_CERTIFIED,
                runtime.RegistrationDisjointAdaptiveAuditStatusV1
                .NOT_CERTIFIED,
                runtime.RegistrationDisjointAdaptiveAuditStatusV1
                .NOT_CERTIFIED,
            ),
            (
                runtime.RegistrationDisjointAdaptiveTerminalStatusV1
                .NOT_CERTIFIED_MAX_ROUNDS
            ),
            2,
        ),
    ),
)
def test_state_machine_cold_round1_round2_and_failure(
    statuses: tuple[runtime.RegistrationDisjointAdaptiveAuditStatusV1, ...],
    terminal: runtime.RegistrationDisjointAdaptiveTerminalStatusV1,
    rounds: int,
) -> None:
    result = _run(statuses)
    assert result.terminal_status is terminal
    assert len(result.local_rounds) == rounds
    assert len(result.epochs) == rounds + 1
    assert result.certificate_id is not None if (
        terminal
        is runtime.RegistrationDisjointAdaptiveTerminalStatusV1.CERTIFIED
    ) else result.certificate_id is None
    assert result.to_document()["registered_target_accesses"] == 0
    assert result.to_document()["production_authority_minted"] is False


def test_exact_draw_and_work_totals_include_independent_replay() -> None:
    result = _run(
        (
            runtime.RegistrationDisjointAdaptiveAuditStatusV1
            .NOT_CERTIFIED,
            runtime.RegistrationDisjointAdaptiveAuditStatusV1
            .NOT_CERTIFIED,
            runtime.RegistrationDisjointAdaptiveAuditStatusV1.CERTIFIED,
        )
    )
    # Two cold rows and two new-child acquisitions.
    expected_producer = (
        2
        * (
            prereg.INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
            + prereg.INITIAL_VALIDATION_DRAWS_PER_PHYSICAL_ROW
        )
        + 2
        * (
            prereg.INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
            + prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
        )
    )
    work = result.work
    assert work.cold_acquisition_count == 2
    assert work.local_acquisition_count == 2
    assert work.independent_replay_draws == expected_producer
    assert work.total_target_draws == 2 * expected_producer
    assert work.confidence_replay_calls == 4
    assert work.confidence_projection_calls == 4
    assert work.cold_closure_builds == 3
    assert work.cold_closure_verifications == 3
    assert work.direct_model_builds == 3
    assert work.quotient_model_builds == 3
    assert work.cold_model_independent_verifications == 3
    assert work.quotient_planner_calls == 3
    assert work.planner_proof_verifications == 3
    assert work.frontier_freezes == 2
    assert work.immutable_epoch_rebuilds == 2
    assert work.operational_terminal_mints == 1
    assert len({item.closure_id for item in result.epochs}) == 3
    assert len({item.model_pair_id for item in result.epochs}) == 3
    assert all(
        item.to_document()["source_quantities_used"] is False
        for item in result.epochs
    )
    assert work.source_quantities_in_confidence == 0
    assert work.source_quantities_in_model == 0
    assert work.source_quantities_in_certificate == 0
    assert work.direct_ground_planner_calls == 0
    assert work.crn_draw_discount == 0


def test_source_identity_changes_only_proposal_provenance() -> None:
    statuses = (
        runtime.RegistrationDisjointAdaptiveAuditStatusV1.CERTIFIED,
    )
    first = _run(
        statuses,
        proposal=_proposal(ordering_basis_id=_id("source-basis-a")),
    )
    second = _run(
        statuses,
        proposal=_proposal(ordering_basis_id=_id("source-basis-b")),
    )
    assert first.proposal_order.proposal_order_id != (
        second.proposal_order.proposal_order_id
    )
    assert first.epochs == second.epochs
    assert first.audits == second.audits
    assert first.certificate_id == second.certificate_id
    assert first.run_id != second.run_id


def test_no_replacement_no_early_stop_and_immutable_epoch() -> None:
    cold = _cold()
    epoch0 = _cold_epoch(cold)
    audit0 = runtime.RegistrationDisjointAdaptiveAuditV1(
        epoch0.epoch_id,
        0,
        runtime.RegistrationDisjointAdaptiveAuditStatusV1.NOT_CERTIFIED,
    )
    with pytest.raises(
        runtime.V072RegisteredAdaptiveRuntimeInvariantViolation,
        match="stopped before both",
    ):
        runtime.run_registration_disjoint_adaptive_state_machine_core_v1(
            proposal_order=_proposal(),
            cold_acquisitions=cold,
            local_rounds=(),
            epochs=(epoch0,),
            audits=(audit0,),
        )

    round1, epoch1, acquisition1 = _extend(
        epoch=epoch0,
        audit=audit0,
        round_index=1,
        row=ROWS[2],
    )
    audit1 = runtime.RegistrationDisjointAdaptiveAuditV1(
        epoch1.epoch_id,
        1,
        runtime.RegistrationDisjointAdaptiveAuditStatusV1.NOT_CERTIFIED,
    )
    reused_frontier = runtime.RegistrationDisjointAdaptiveFrontierV1(
        2,
        epoch1.epoch_id,
        audit1.audit_id,
        round1.frontier.frontier_id,
        epoch1.cumulative_acquisition_ids,
        (ROWS[2],),
        (_id("synthetic-proof-obligation-reuse"),),
    )
    replacement = replace(
        acquisition1,
        round_index=2,
        frontier_id=reused_frontier.frontier_id,
    )
    round2 = runtime.RegistrationDisjointAdaptiveLocalRoundV1(
        reused_frontier,
        (replacement,),
    )
    epoch2 = runtime.RegistrationDisjointAdaptiveModelEpochV1(
        2,
        epoch1.epoch_id,
        reused_frontier.frontier_id,
        tuple(
            sorted(
                (
                    *epoch1.cumulative_acquisition_ids,
                    replacement.acquisition_id,
                )
            )
        ),
        (replacement.acquisition_id,),
    )
    audit2 = runtime.RegistrationDisjointAdaptiveAuditV1(
        epoch2.epoch_id,
        2,
        runtime.RegistrationDisjointAdaptiveAuditStatusV1.CERTIFIED,
    )
    with pytest.raises(
        runtime.V072RegisteredAdaptiveRuntimeInvariantViolation,
        match="replaced|new-child",
    ):
        runtime.run_registration_disjoint_adaptive_state_machine_core_v1(
            proposal_order=_proposal(),
            cold_acquisitions=cold,
            local_rounds=(round1, round2),
            epochs=(epoch0, epoch1, epoch2),
            audits=(audit0, audit1, audit2),
        )

    valid_round2, valid_epoch2, _ = _extend(
        epoch=epoch1,
        audit=audit1,
        round_index=2,
        row=ROWS[3],
        previous_frontier=round1.frontier,
    )
    stale_epoch2 = replace(
        valid_epoch2,
        predecessor_epoch_id=epoch0.epoch_id,
    )
    stale_audit2 = runtime.RegistrationDisjointAdaptiveAuditV1(
        stale_epoch2.epoch_id,
        2,
        runtime.RegistrationDisjointAdaptiveAuditStatusV1.CERTIFIED,
    )
    with pytest.raises(
        runtime.V072RegisteredAdaptiveRuntimeInvariantViolation,
        match="immutable epoch rebuild",
    ):
        runtime.run_registration_disjoint_adaptive_state_machine_core_v1(
            proposal_order=_proposal(),
            cold_acquisitions=cold,
            local_rounds=(round1, valid_round2),
            epochs=(epoch0, epoch1, stale_epoch2),
            audits=(audit0, audit1, stale_audit2),
        )


def test_round_two_requires_fresh_strict_frontier_extension() -> None:
    cold = _cold()
    epoch0 = _cold_epoch(cold)
    audit0 = runtime.RegistrationDisjointAdaptiveAuditV1(
        epoch0.epoch_id,
        0,
        runtime.RegistrationDisjointAdaptiveAuditStatusV1.NOT_CERTIFIED,
    )
    round1, epoch1, _ = _extend(
        epoch=epoch0,
        audit=audit0,
        round_index=1,
        row=ROWS[2],
    )
    audit1 = runtime.RegistrationDisjointAdaptiveAuditV1(
        epoch1.epoch_id,
        1,
        runtime.RegistrationDisjointAdaptiveAuditStatusV1.NOT_CERTIFIED,
    )
    stale_frontier = runtime.RegistrationDisjointAdaptiveFrontierV1(
        2,
        epoch1.epoch_id,
        audit1.audit_id,
        round1.frontier.frontier_id,
        round1.frontier.supporting_acquisition_ids,
        (ROWS[3],),
        (_id("synthetic-proof-obligation-stale-frontier"),),
    )
    acquisition = runtime.RegistrationDisjointAdaptiveAcquisitionV1(
        2,
        ROWS[3],
        runtime.RegistrationDisjointAcquisitionPurposeV1.NEW_CHILD,
        stale_frontier.frontier_id,
    )
    round2 = runtime.RegistrationDisjointAdaptiveLocalRoundV1(
        stale_frontier,
        (acquisition,),
    )
    epoch2 = runtime.RegistrationDisjointAdaptiveModelEpochV1(
        2,
        epoch1.epoch_id,
        stale_frontier.frontier_id,
        tuple(
            sorted(
                (*epoch1.cumulative_acquisition_ids, acquisition.acquisition_id)
            )
        ),
        (acquisition.acquisition_id,),
    )
    audit2 = runtime.RegistrationDisjointAdaptiveAuditV1(
        epoch2.epoch_id,
        2,
        runtime.RegistrationDisjointAdaptiveAuditStatusV1.CERTIFIED,
    )
    with pytest.raises(
        runtime.V072RegisteredAdaptiveRuntimeInvariantViolation,
        match="fresh strict extension",
    ):
        runtime.run_registration_disjoint_adaptive_state_machine_core_v1(
            proposal_order=_proposal(),
            cold_acquisitions=cold,
            local_rounds=(round1, round2),
            epochs=(epoch0, epoch1, epoch2),
            audits=(audit0, audit1, audit2),
        )


def test_terminal_audit_cannot_be_followed_by_more_work() -> None:
    cold = _cold()
    epoch0 = _cold_epoch(cold)
    certified = runtime.RegistrationDisjointAdaptiveAuditV1(
        epoch0.epoch_id,
        0,
        runtime.RegistrationDisjointAdaptiveAuditStatusV1.CERTIFIED,
    )
    round1, epoch1, _ = _extend(
        epoch=epoch0,
        audit=certified,
        round_index=1,
        row=ROWS[2],
    )
    audit1 = runtime.RegistrationDisjointAdaptiveAuditV1(
        epoch1.epoch_id,
        1,
        runtime.RegistrationDisjointAdaptiveAuditStatusV1.CERTIFIED,
    )
    with pytest.raises(
        runtime.V072RegisteredAdaptiveRuntimeInvariantViolation,
        match="frontier|terminal",
    ):
        runtime.run_registration_disjoint_adaptive_state_machine_core_v1(
            proposal_order=_proposal(),
            cold_acquisitions=cold,
            local_rounds=(round1,),
            epochs=(epoch0, epoch1),
            audits=(certified, audit1),
        )
