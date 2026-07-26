"""V0-054B registered action-local H2 semantic-switch regressions."""

from __future__ import annotations

import copy
from dataclasses import replace
from fractions import Fraction

import pytest

import acfqp.h2_action_indexed_proof_dag_v1 as dag_module
import acfqp.h2_action_local_semantic_switch_v1 as switch_module
from acfqp.domains.matching_buffer import (
    LMBKernel,
    generate_solvable_lmb,
)


InvariantViolation = switch_module.ActionLocalSemanticSwitchInvariantViolation
DagInvariantViolation = dag_module.ActionIndexedProofInvariantViolation
Action = dag_module.CandidateAction
Address = dag_module.ProofAddress
GroundRowName = dag_module.GroundRowName
GroundRowStatus = dag_module.GroundRowStatus
ResolutionOutcome = dag_module.ProofResolutionOutcome

EXPECTED_AFFECTED = (
    Address.ROW_M,
    Address.Q_M,
    Address.U1,
    Address.U0,
    Address.PLAN_M,
    Address.REGRET_N,
    Address.REGRET_M,
    Address.RISK_M,
    Address.COVERAGE_M,
    Address.SELECTION,
)
EXPECTED_UNAFFECTED = (
    Address.ROW_S,
    Address.ROW_N1,
    Address.ROW_N2,
    Address.ROW_N3,
    Address.Q_N,
    Address.PLAN_N,
    Address.RISK_N,
    Address.COVERAGE_N,
)


@pytest.fixture(scope="module")
def switch_result():
    return switch_module.run_registered_h2_action_local_semantic_switch_v1()


def _fresh_owner_and_authority(result):
    owner = switch_module._ActionLocalRuntimeOwnerV1()
    owner.install()
    frontier = result.challenger_frontier
    authority = owner.mint_authority(
        result.fixture.fixture_id,
        result.query.query_id,
        result.necessity_proof.proof_id,
        result.first_model.model_id,
        frontier.target_state_id,
        frontier.target_action_id,
        frontier.target_ground_row_id,
    )
    return owner, authority


def test_seed4_generator_matches_literal_and_first_epoch_never_steps(
    monkeypatch,
) -> None:
    generated, evidence = generate_solvable_lmb(
        tile_count=6,
        type_count=2,
        capacity=3,
        max_layers=4,
        seed=4,
    )
    literal = switch_module._literal_kernel_v1()
    assert evidence.seed == 4
    assert evidence.target_sequence == (4, 2, 5, 0, 1, 3)
    assert evidence.verified is True
    assert generated == literal
    assert (
        literal.tile_types,
        literal.blockers,
        literal.type_count,
        literal.capacity,
        literal.max_layers,
    ) == (
        switch_module.TILE_TYPES,
        switch_module.BLOCKERS,
        switch_module.TYPE_COUNT,
        switch_module.CAPACITY,
        switch_module.MAX_LAYERS,
    )

    def forbidden_step(*_args, **_kwargs):
        raise AssertionError("first model construction called LMBKernel.step")

    monkeypatch.setattr(LMBKernel, "step", forbidden_step)
    fixture = switch_module.registered_action_local_fixture_v1()
    query = dag_module.registered_action_indexed_h2_query_v1()
    offline_rows = switch_module._offline_registered_rows_v1(fixture)
    first_model = switch_module.ActionLocalModelEpochV1(
        1,
        fixture.fixture_id,
        query.query_id,
        None,
        dag_module.registered_first_action_indexed_h2_model_v1(),
        offline_rows,
        (switch_module.EXPECTED_GROUND_ROW_IDS[GroundRowName.M],),
    )
    execution = dag_module.execute_action_indexed_epoch_v1(
        first_model.dag_model,
        query,
        dag_module.ActionIndexedProofRuntimeV1(),
    )
    assert len(first_model.observed_rows) == 4
    assert len(first_model.missing_ground_row_ids) == 1
    assert execution.ground_transition_calls == 0
    assert execution.kernel_imported is False


def test_first_epoch_is_exactly_4_1_and_selected_n_fails(
    switch_result,
) -> None:
    result = switch_result
    first = result.first_model
    execution = result.first_execution
    n_audit = execution.audit(Action.N)
    m_audit = execution.audit(Action.M)

    assert tuple(item.name for item in first.observed_rows) == (
        GroundRowName.S,
        GroundRowName.N1,
        GroundRowName.N2,
        GroundRowName.N3,
    )
    assert first.missing_ground_row_ids == (
        switch_module.EXPECTED_GROUND_ROW_IDS[GroundRowName.M],
    )
    assert (first.dag_model.observed_row_count, first.dag_model.missing_row_count) == (
        4,
        1,
    )
    assert first.dag_model.row(GroundRowName.M).status is GroundRowStatus.MISSING_VACUOUS
    assert execution.proposal.selected_action is Action.N
    assert execution.proposal.selected_schedule_code == "A0A0"
    assert (
        n_audit.policy_reward_lower,
        n_audit.unrestricted_reward_upper,
        n_audit.normalized_regret,
        n_audit.coverage_passed,
        n_audit.certified,
    ) == (0, 3, Fraction(3, 4), True, False)
    assert m_audit.coverage_passed is False
    assert m_audit.certified is False


def test_frontiers_are_exact_m_diagnostic_and_support_cannot_authorize(
    switch_result,
) -> None:
    result = switch_result
    support = result.support_frontier
    challenger = result.challenger_frontier
    target = result.fixture.action(GroundRowName.M)

    assert support.selected_action is Action.N
    assert support.target_ground_row_id == target.ground_row_id
    assert target.ground_row_id not in support.supported_ground_row_ids
    assert support.target_is_supported is False
    assert support.authorizing is False
    assert challenger.target_state_id == result.fixture.downstream_state.state_id
    assert challenger.target_action_id == target.action_id
    assert challenger.target_ground_row_id == target.ground_row_id
    assert challenger.remaining_horizon == 1
    assert challenger.circuit_addresses == switch_module.EXPECTED_CHALLENGER_CIRCUIT
    assert challenger.unique_missing_maximizer is True
    assert challenger.authorizing is False

    owner, authority = _fresh_owner_and_authority(result)
    try:
        with pytest.raises(InvariantViolation):
            switch_module.freeze_action_local_evidence_request_v1(
                result.necessity_proof,
                authority,
                support,
            )
        assert owner.gate.ground_transition_calls == 0
    finally:
        owner.close()


def test_request_freezes_before_the_only_ground_step(monkeypatch) -> None:
    events: list[str] = []
    original_freeze = switch_module.freeze_action_local_evidence_request_v1
    original_activate = switch_module._ActionLocalKernelStepGateV1.activate

    def traced_freeze(*args, **kwargs):
        events.append("REQUEST_FROZEN")
        return original_freeze(*args, **kwargs)

    def traced_activate(self, request):
        events.append("GROUND_STEP_AUTHORIZED")
        assert events == ["REQUEST_FROZEN", "GROUND_STEP_AUTHORIZED"]
        return original_activate(self, request)

    monkeypatch.setattr(
        switch_module,
        "freeze_action_local_evidence_request_v1",
        traced_freeze,
    )
    monkeypatch.setattr(
        switch_module._ActionLocalKernelStepGateV1,
        "activate",
        traced_activate,
    )
    result = switch_module.run_registered_h2_action_local_semantic_switch_v1()

    assert events == ["REQUEST_FROZEN", "GROUND_STEP_AUTHORIZED"]
    assert (
        result.access_trace.ground_calls_before_request_freeze,
        result.access_trace.ground_calls_after_request_freeze,
        result.access_trace.total_ground_transition_calls,
    ) == (0, 1, 1)
    assert result.access_trace.requested_ground_row_ids == (
        switch_module.EXPECTED_GROUND_ROW_IDS[GroundRowName.M],
    )
    assert (
        result.access_trace.acquired_ground_row_ids
        == result.access_trace.requested_ground_row_ids
    )


def test_golden_outcome_step_fake_is_rejected_before_gate_install(
    switch_result,
    monkeypatch,
) -> None:
    kernel = switch_module._literal_kernel_v1()
    state = switch_module.LMBState(
        48,
        (0, 2),
        switch_module.LMBStatus.ACTIVE,
    )
    action = switch_module.LMBAction(0)
    golden_outcomes = switch_module._CANONICAL_LMB_STEP(
        kernel,
        state,
        action,
    )
    fake_calls = 0

    def golden_fake_step(_kernel, _state, _action):
        nonlocal fake_calls
        fake_calls += 1
        return golden_outcomes

    with monkeypatch.context() as patch:
        patch.setattr(LMBKernel, "step", golden_fake_step)
        with pytest.raises(InvariantViolation):
            switch_module.run_registered_h2_action_local_semantic_switch_v1()
        assert fake_calls == 0
        assert LMBKernel.step is golden_fake_step

    canonical = switch_module.run_registered_h2_action_local_semantic_switch_v1()
    assert canonical.result_id == switch_result.result_id
    assert canonical.to_document() == switch_result.to_document()


def test_gate_execute_fake_cannot_forge_ground_call_provenance(
    switch_result,
    monkeypatch,
) -> None:
    kernel = switch_module._literal_kernel_v1()
    state = switch_module.LMBState(
        48,
        (0, 2),
        switch_module.LMBStatus.ACTIVE,
    )
    action = switch_module.LMBAction(0)
    golden_outcomes = switch_module._CANONICAL_LMB_STEP(
        kernel,
        state,
        action,
    )
    fake_calls = 0
    fake_gate = None

    def golden_fake_execute(self, _request, _kernel, _state, _action):
        nonlocal fake_calls, fake_gate
        fake_calls += 1
        fake_gate = self
        self._ground_transition_calls += 1
        return golden_outcomes

    with monkeypatch.context() as patch:
        patch.setattr(
            switch_module._ActionLocalKernelStepGateV1,
            "execute",
            golden_fake_execute,
        )
        with pytest.raises(InvariantViolation):
            switch_module.run_registered_h2_action_local_semantic_switch_v1()
        assert fake_calls == 0
        assert fake_gate is None
        assert LMBKernel.step is switch_module._CANONICAL_LMB_STEP

    canonical = switch_module.run_registered_h2_action_local_semantic_switch_v1()
    assert (
        canonical.access_trace.ground_calls_before_request_freeze,
        canonical.access_trace.ground_calls_after_request_freeze,
        canonical.access_trace.total_ground_transition_calls,
        canonical.evidence_bundle.receipt.call_sequence,
    ) == (0, 1, 1, 1)
    assert canonical.result_id == switch_result.result_id
    assert canonical.to_document() == switch_result.to_document()


def test_kernel_step_gate_rejects_reentrant_and_concurrent_install() -> None:
    first = switch_module._ActionLocalRuntimeOwnerV1()
    second = switch_module._ActionLocalRuntimeOwnerV1()
    first.install()
    try:
        with pytest.raises(InvariantViolation):
            first.install()
        with pytest.raises(InvariantViolation):
            second.install()
        assert LMBKernel.step is not switch_module._CANONICAL_LMB_STEP
        assert first.gate.ground_transition_calls == 0
        assert second.gate.ground_transition_calls == 0
    finally:
        first.close()

    assert LMBKernel.step is switch_module._CANONICAL_LMB_STEP
    second.install()
    try:
        assert LMBKernel.step is not switch_module._CANONICAL_LMB_STEP
        assert second.gate.ground_transition_calls == 0
    finally:
        second.close()
    assert LMBKernel.step is switch_module._CANONICAL_LMB_STEP


def test_preexecution_invalidation_is_derived_and_authorized_before_final_epoch(
    monkeypatch,
) -> None:
    events: list[str] = []
    original_execute = switch_module.execute_action_indexed_epoch_v1
    original_derive_pre = (
        switch_module.derive_action_indexed_preexecution_invalidation_v1
    )
    original_authorize = switch_module.authorize_action_indexed_final_epoch_v1
    original_derive_post = (
        switch_module.derive_action_indexed_delta_and_invalidation_v1
    )

    def traced_execute(model, query, runtime):
        if model.epoch is dag_module.ModelEpoch.FIRST_4_OBSERVED_1_MISSING:
            events.append("FIRST_EXECUTION_ENTERED")
        else:
            events.append("FINAL_EXECUTION_ENTERED")
        return original_execute(model, query, runtime)

    def traced_derive_pre(*args, **kwargs):
        derived = original_derive_pre(*args, **kwargs)
        events.append("PREEXECUTION_INVALIDATION_DERIVED")
        return derived

    def traced_authorize(*args, **kwargs):
        authorized = original_authorize(*args, **kwargs)
        events.append("PREEXECUTION_INVALIDATION_AUTHORIZED")
        return authorized

    def traced_derive_post(*args, **kwargs):
        verified = original_derive_post(*args, **kwargs)
        events.append("POSTEXECUTION_INVALIDATION_VERIFIED")
        return verified

    monkeypatch.setattr(
        switch_module,
        "execute_action_indexed_epoch_v1",
        traced_execute,
    )
    monkeypatch.setattr(
        switch_module,
        "derive_action_indexed_preexecution_invalidation_v1",
        traced_derive_pre,
    )
    monkeypatch.setattr(
        switch_module,
        "authorize_action_indexed_final_epoch_v1",
        traced_authorize,
    )
    monkeypatch.setattr(
        switch_module,
        "derive_action_indexed_delta_and_invalidation_v1",
        traced_derive_post,
    )

    result = switch_module.run_registered_h2_action_local_semantic_switch_v1()

    assert events == [
        "FIRST_EXECUTION_ENTERED",
        "PREEXECUTION_INVALIDATION_DERIVED",
        "PREEXECUTION_INVALIDATION_AUTHORIZED",
        "FINAL_EXECUTION_ENTERED",
        "POSTEXECUTION_INVALIDATION_VERIFIED",
    ]
    assert (
        result.final_execution.preexecution_invalidation_id
        == result.preexecution_invalidation.plan_id
    )
    assert (
        result.invalidation.preexecution_invalidation_id
        == result.preexecution_invalidation.plan_id
    )


def test_final_epoch_cannot_execute_before_preinvalidation_authority() -> None:
    query = dag_module.registered_action_indexed_h2_query_v1()
    first_model = dag_module.registered_first_action_indexed_h2_model_v1()
    final_model = dag_module.registered_final_action_indexed_h2_model_v1()
    runtime = dag_module.ActionIndexedProofRuntimeV1()
    first_execution = dag_module.execute_action_indexed_epoch_v1(
        first_model,
        query,
        runtime,
    )

    with pytest.raises(DagInvariantViolation):
        dag_module.execute_action_indexed_epoch_v1(
            final_model,
            query,
            runtime,
        )

    _delta, preexecution = (
        dag_module.derive_action_indexed_preexecution_invalidation_v1(
            first_model,
            final_model,
            first_execution,
        )
    )
    dag_module.authorize_action_indexed_final_epoch_v1(
        runtime,
        preexecution,
    )
    final_execution = dag_module.execute_action_indexed_epoch_v1(
        final_model,
        query,
        runtime,
    )
    assert final_execution.preexecution_invalidation_id == preexecution.plan_id


def test_authority_is_single_use_and_rejects_foreign_types_and_copies(
    switch_result,
) -> None:
    result = switch_result
    assert not hasattr(switch_module, "_AUTHORITY_MINT")

    owner, authority = _fresh_owner_and_authority(result)
    try:
        request = switch_module.freeze_action_local_evidence_request_v1(
            result.necessity_proof,
            authority,
            result.challenger_frontier,
        )
        receipt = authority.acquire(request, switch_module._literal_kernel_v1())
        assert receipt.request_id == request.request_id
        assert receipt.call_sequence == 1
        assert owner.gate.ground_transition_calls == 1
        with pytest.raises(InvariantViolation):
            authority.acquire(request, switch_module._literal_kernel_v1())
        assert owner.gate.ground_transition_calls == 1
    finally:
        owner.close()

    with pytest.raises(InvariantViolation):
        switch_module.ActionLocalGroundTransitionAuthorityV1(
            result.fixture.fixture_id,
            result.query.query_id,
            result.necessity_proof.proof_id,
            result.first_model.model_id,
            result.challenger_frontier.target_state_id,
            result.challenger_frontier.target_action_id,
            result.challenger_frontier.target_ground_row_id,
            _owner=object(),
        )

    for copier in (copy.copy, copy.deepcopy):
        owner, source = _fresh_owner_and_authority(result)
        try:
            with pytest.raises(InvariantViolation):
                copier(source)
            assert owner.gate.ground_transition_calls == 0
        finally:
            owner.close()

    class CopiedRequest(switch_module.ActionLocalEvidenceRequestV1):
        pass

    owner, source = _fresh_owner_and_authority(result)
    try:
        canonical = switch_module.freeze_action_local_evidence_request_v1(
            result.necessity_proof,
            source,
            result.challenger_frontier,
        )
        copied_request = CopiedRequest(
            canonical.proof_id,
            canonical.authority_id,
            canonical.first_model_id,
            canonical.query_id,
            canonical.state_id,
            canonical.action_id,
            canonical.ground_row_id,
            canonical.max_ground_transition_calls,
        )
        with pytest.raises(InvariantViolation):
            source.acquire(copied_request, switch_module._literal_kernel_v1())
        assert owner.gate.ground_transition_calls == 0
    finally:
        owner.close()


def test_forged_authority_and_early_step_gate_fail_without_ground_call(
    switch_result,
) -> None:
    result = switch_result
    frontier = result.challenger_frontier
    owner, authority = _fresh_owner_and_authority(result)
    try:
        forged = switch_module.ActionLocalGroundTransitionAuthorityV1(
            result.fixture.fixture_id,
            result.query.query_id,
            result.necessity_proof.proof_id,
            result.first_model.model_id,
            frontier.target_state_id,
            frontier.target_action_id,
            frontier.target_ground_row_id,
            _owner=owner,
        )
        with pytest.raises(InvariantViolation):
            switch_module.freeze_action_local_evidence_request_v1(
                result.necessity_proof,
                forged,
                frontier,
            )
        assert owner.gate.ground_transition_calls == 0

        request = switch_module.freeze_action_local_evidence_request_v1(
            result.necessity_proof,
            authority,
            frontier,
        )
        kernel = switch_module._literal_kernel_v1()
        with pytest.raises(InvariantViolation):
            kernel.step(
                switch_module.LMBState(
                    48,
                    (0, 2),
                    switch_module.LMBStatus.ACTIVE,
                ),
                switch_module.LMBAction(0),
            )
        assert owner.gate.ground_transition_calls == 0

        receipt = authority.acquire(request, kernel)
        assert receipt.ground_row_id == frontier.target_ground_row_id
        assert owner.gate.ground_transition_calls == 1
    finally:
        owner.close()


def test_final_epoch_is_exactly_5_0_and_switch_is_strict(
    switch_result,
) -> None:
    result = switch_result
    final = result.final_model
    execution = result.final_execution
    witness = result.policy_switch
    m_audit = execution.audit(Action.M)

    assert tuple(item.name for item in final.observed_rows) == tuple(GroundRowName)
    assert final.missing_ground_row_ids == ()
    assert (final.dag_model.observed_row_count, final.dag_model.missing_row_count) == (
        5,
        0,
    )
    assert final.dag_model.row(GroundRowName.M).status is GroundRowStatus.OBSERVED
    assert execution.proposal.selected_action is Action.M
    assert execution.proposal.selected_schedule_code == "A0A1"
    assert (
        m_audit.policy_reward_lower,
        m_audit.unrestricted_reward_upper,
        m_audit.normalized_regret,
        m_audit.coverage_passed,
        m_audit.certified,
    ) == (1, 1, 0, True, True)
    assert (
        witness.first_action,
        witness.final_action,
        witness.first_schedule_code,
        witness.final_schedule_code,
        witness.first_reachable_value,
        witness.final_reachable_value,
        witness.value_improvement,
        witness.tie_break_only,
    ) == (Action.N, Action.M, "A0A0", "A0A1", 0, 1, 1, False)


def test_action_indexed_dag_work_invalidation_and_roots_are_exact(
    switch_result,
) -> None:
    result = switch_result
    first = result.first_execution
    final = result.final_execution
    preexecution = result.preexecution_invalidation
    invalidation = result.invalidation

    assert (
        first.work.lower_computed,
        first.work.lower_reused,
        first.work.fresh_root_computed,
        first.work.total_computed,
    ) == (18, 0, 3, 21)
    assert (
        final.work.lower_computed,
        final.work.lower_reused,
        final.work.fresh_root_computed,
        final.work.total_computed,
    ) == (10, 8, 3, 13)
    assert len(first.resolutions) == len(final.resolutions) == 18
    assert all(
        item.outcome is ResolutionOutcome.COMPUTED for item in first.resolutions
    )
    final_computed = tuple(
        item.address
        for item in final.resolutions
        if item.outcome is ResolutionOutcome.COMPUTED
    )
    final_reused = tuple(
        item.address
        for item in final.resolutions
        if item.outcome is ResolutionOutcome.REUSED
    )
    assert (
        preexecution.delta_id
        == result.overlay_build.action_indexed_delta.delta_id
    )
    assert preexecution.first_model_id == result.first_model.dag_model.model_id
    assert preexecution.final_model_id == result.final_model.dag_model.model_id
    assert preexecution.first_execution_id == first.execution_id
    assert preexecution.direct_changed_addresses == (Address.ROW_M,)
    assert preexecution.affected_addresses == EXPECTED_AFFECTED
    assert preexecution.unaffected_addresses == EXPECTED_UNAFFECTED
    assert final.preexecution_invalidation_id == preexecution.plan_id
    assert invalidation.preexecution_invalidation_id == preexecution.plan_id
    assert invalidation.direct_changed_addresses == (Address.ROW_M,)
    assert invalidation.affected_addresses == EXPECTED_AFFECTED
    assert invalidation.unaffected_addresses == EXPECTED_UNAFFECTED
    assert invalidation.recomputed_addresses == EXPECTED_AFFECTED
    assert invalidation.reused_addresses == EXPECTED_UNAFFECTED
    assert invalidation.closure_edges == preexecution.closure_edges
    assert final_computed == EXPECTED_AFFECTED
    assert final_reused == EXPECTED_UNAFFECTED

    first_roots = (*first.candidate_roots, first.selected_root)
    final_roots = (*final.candidate_roots, final.selected_root)
    assert len(first_roots) == len(final_roots) == 3
    assert not ({item.root_id for item in first_roots} & {item.root_id for item in final_roots})
    assert first.selected_root.root_id not in {
        item.root_id for item in first.candidate_roots
    }
    assert final.selected_root.root_id not in {
        item.root_id for item in final.candidate_roots
    }


def test_overlay_appends_only_m_and_preserves_every_base_row(
    switch_result,
) -> None:
    result = switch_result
    overlay = result.overlay_build
    delta = overlay.action_indexed_delta

    assert overlay.added_ground_row_ids == (
        switch_module.EXPECTED_GROUND_ROW_IDS[GroundRowName.M],
    )
    assert overlay.removed_ground_row_ids == ()
    assert overlay.changed_ground_row_ids == ()
    assert overlay.immutable_append_only is True
    assert delta.changed_row_names == (GroundRowName.M,)
    assert delta.unchanged_row_names == (
        GroundRowName.S,
        GroundRowName.N1,
        GroundRowName.N2,
        GroundRowName.N3,
    )
    assert (
        delta.first_observed_count,
        delta.first_missing_count,
        delta.final_observed_count,
        delta.final_missing_count,
    ) == (4, 1, 5, 0)
    assert tuple(
        item.to_document() for item in result.final_model.observed_rows[:-1]
    ) == tuple(item.to_document() for item in result.first_model.observed_rows)
    assert result.final_model.observed_rows[-1].name is GroundRowName.M


def test_frontier_request_receipt_and_access_trace_tampering_fails_closed(
    switch_result,
) -> None:
    result = switch_result
    n_action = result.fixture.action(GroundRowName.N1)

    with pytest.raises(InvariantViolation):
        replace(result.challenger_frontier, target_action_id=n_action.action_id)
    with pytest.raises(InvariantViolation):
        replace(result.challenger_frontier, remaining_horizon=2)
    with pytest.raises(InvariantViolation):
        replace(result.support_frontier, authorizing=True)
    with pytest.raises(InvariantViolation):
        replace(result.request, action_id=n_action.action_id)
    with pytest.raises(InvariantViolation):
        replace(result.request, max_ground_transition_calls=2)
    with pytest.raises(InvariantViolation):
        replace(result.evidence_bundle.receipt, reward=Fraction(0))
    with pytest.raises(InvariantViolation):
        replace(result.evidence_bundle.receipt, call_sequence=2)
    with pytest.raises(InvariantViolation):
        replace(result.access_trace, ground_calls_before_request_freeze=1)


def test_overlay_invalidation_and_policy_tampering_fails_closed(
    switch_result,
) -> None:
    result = switch_result

    with pytest.raises(InvariantViolation):
        replace(
            result.overlay_build,
            added_ground_row_ids=(
                switch_module.EXPECTED_GROUND_ROW_IDS[GroundRowName.N1],
            ),
        )
    with pytest.raises(InvariantViolation):
        replace(
            result.overlay_build,
            removed_ground_row_ids=(
                switch_module.EXPECTED_GROUND_ROW_IDS[GroundRowName.S],
            ),
        )
    with pytest.raises(DagInvariantViolation):
        replace(
            result.preexecution_invalidation,
            affected_addresses=(
                result.preexecution_invalidation.affected_addresses[:-1]
            ),
        )
    with pytest.raises(DagInvariantViolation):
        replace(
            result.invalidation,
            affected_addresses=result.invalidation.affected_addresses[:-1],
        )
    with pytest.raises(DagInvariantViolation):
        replace(
            result.invalidation,
            reused_addresses=(*result.invalidation.reused_addresses, Address.ROW_M),
        )
    with pytest.raises(InvariantViolation):
        replace(result.policy_switch, value_improvement=Fraction(0))
    with pytest.raises(InvariantViolation):
        replace(result.policy_switch, tie_break_only=True)


def test_final_epoch_rejects_fully_resigned_row_m_observation_downgrade(
    switch_result,
) -> None:
    """A valid hash chain cannot replace semantic proof replay.

    The attacker changes only the final ROW_M observation flag, then rebuilds
    every content-addressed object whose identity depends on that leaf while
    retaining the old (now false) derived proof results.  The execution
    constructor must independently reject this semantically inconsistent DAG.
    """

    execution = switch_result.final_execution
    resigned_nodes = {}
    for original in execution.nodes:
        if original.address is Address.ROW_M:
            result_fields = tuple(
                replace(field, boolean_value=False)
                if field.name == "all_rows_observed"
                else field
                for field in original.result_fields
            )
            node = replace(original, result_fields=result_fields)
        elif original.address in EXPECTED_AFFECTED:
            node = replace(
                original,
                ordered_parent_node_ids=tuple(
                    resigned_nodes[parent].node_id
                    for parent in dag_module.EXPECTED_PARENT_ADDRESSES[
                        original.address
                    ]
                ),
            )
        else:
            node = original
        resigned_nodes[original.address] = node

    ordered_nodes = tuple(
        resigned_nodes[address] for address in dag_module.ADDRESS_ORDER
    )
    ordered_node_ids = tuple(node.node_id for node in ordered_nodes)
    resigned_resolutions = tuple(
        replace(
            resolution,
            node_key_id=resigned_nodes[resolution.address].node_key_id,
            node_id=resigned_nodes[resolution.address].node_id,
        )
        if resolution.address in EXPECTED_AFFECTED
        else resolution
        for resolution in execution.resolutions
    )
    resigned_audits = tuple(
        replace(audit, ordered_lower_node_ids=ordered_node_ids)
        for audit in execution.candidate_audits
    )
    resigned_candidate_roots = tuple(
        replace(
            root,
            candidate_audit_id=audit.audit_id,
            ordered_lower_node_ids=ordered_node_ids,
        )
        for root, audit in zip(execution.candidate_roots, resigned_audits)
    )
    resigned_proposal = replace(
        execution.proposal,
        selection_node_id=resigned_nodes[Address.SELECTION].node_id,
        candidate_audit_ids=tuple(
            audit.audit_id for audit in resigned_audits
        ),
        candidate_root_ids=tuple(
            root.root_id for root in resigned_candidate_roots
        ),
    )
    selected_audit = resigned_audits[
        0 if resigned_proposal.selected_action is Action.N else 1
    ]
    resigned_selected_root = replace(
        execution.selected_root,
        candidate_audit_id=selected_audit.audit_id,
        ordered_lower_node_ids=ordered_node_ids,
        proposal_id=resigned_proposal.proposal_id,
    )

    assert resigned_nodes[Address.ROW_M].boolean("all_rows_observed") is False
    assert resigned_nodes[Address.COVERAGE_M].boolean("passes") is True
    assert resigned_proposal.selected_action is Action.M
    with pytest.raises(DagInvariantViolation):
        replace(
            execution,
            resolutions=resigned_resolutions,
            nodes=ordered_nodes,
            candidate_audits=resigned_audits,
            candidate_roots=resigned_candidate_roots,
            proposal=resigned_proposal,
            selected_root=resigned_selected_root,
        )


def test_verifier_bypasses_public_runner(
    switch_result,
    monkeypatch,
) -> None:
    def public_runner_must_not_be_called():
        raise AssertionError("verifier called the public production runner")

    monkeypatch.setattr(
        switch_module,
        "run_registered_h2_action_local_semantic_switch_v1",
        public_runner_must_not_be_called,
    )
    report = switch_module.verify_registered_h2_action_local_semantic_switch_v1(
        switch_result
    )
    assert report.claimed_result_id == switch_result.result_id
    assert report.replayed_result_id == switch_result.result_id
    assert report.exact_document_match is True
    assert report.independent_algorithm is False
    assert report.evaluation_lane_only is True
    assert report.included_in_operational_work is False
    assert (
        report.report_id
        == switch_module.EXPECTED_CANONICAL_IDS["verification"]
    )


def test_two_runs_are_content_identical_and_claim_locks_remain_closed(
    switch_result,
) -> None:
    assert (
        switch_module.require_action_local_semantic_switch_result_v1(
            switch_result
        )
        is switch_result
    )
    repeated = switch_module.run_registered_h2_action_local_semantic_switch_v1()
    assert repeated.result_id == switch_result.result_id
    assert repeated.to_document() == switch_result.to_document()
    assert switch_module._canonical_result_ids(switch_result) == {
        key: value
        for key, value in switch_module.EXPECTED_CANONICAL_IDS.items()
        if key != "verification"
    }

    locks = switch_result.claim_locks
    assert locks.registered_h2_action_local_switch_claimed is True
    assert locks.unrestricted_challenger_frontier_claimed is True
    assert locks.exact_one_row_overlay_claimed is True
    assert locks.action_indexed_invalidation_claimed is True
    assert locks.strict_policy_switch_claimed is True
    assert locks.generic_action_local_minimality_claimed is False
    assert locks.generic_h_gt_1_completeness_claimed is False
    assert locks.durable_persistence_claimed is False
    assert locks.cross_query_reuse_claimed is False
    assert locks.automatic_coordinate_invention_claimed is False
    assert locks.partial_dynamics_claimed is False
    assert locks.learned_dynamics_claimed is False
    assert locks.sample_efficiency_claimed is False
    assert locks.byte_savings_claimed is False
    assert locks.cpu_savings_claimed is False
    assert locks.wall_clock_savings_claimed is False
    assert locks.total_work_savings_claimed is False
    assert locks.official_execution_allowed is False
    assert locks.official_scalar_cost is None
    assert locks.official_N_break_even is None
    assert locks.workload_economics_gate == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert locks.counter_completeness_gate == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    with pytest.raises(InvariantViolation):
        replace(locks, sample_efficiency_claimed=True)
    with pytest.raises(InvariantViolation):
        replace(locks, official_execution_allowed=True)
