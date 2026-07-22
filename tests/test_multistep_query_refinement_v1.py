"""V0-047 multi-step query-local model-evolution regressions."""

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.multistep_query_refinement_v1 as multistep_module

from acfqp.observation_partial_rapm_v1 import (
    AmbiguityRowStatus,
    PlanningKind,
    QueryScopedPartialRAPMV3,
    SuccessorKind,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    synthesize_observed_lmb_partial_rapm_v1,
)
from acfqp.partial_model_planner_v1 import (
    PartialModelPlannerSelectionMode,
    propose_partial_model_plan_from_observed_synthesis_v2,
)
from acfqp.partial_sound_audit_v1 import (
    FailedProofReason,
    PartialAuditOutcome,
    audit_partial_fixed_plan_from_observed_synthesis_v2,
)
from acfqp.multistep_query_refinement_v1 import (
    MultiStepEvidencePhase,
    MultiStepQueryRefinementResultV1,
    MultiStepRefinementInvariantViolation,
    SUCCESS_STATUS,
    canonical_lmb_query_kernel_v1,
    run_lmb_h2_multistep_query_refinement_v1,
    verify_lmb_h2_multistep_query_refinement_v1,
)
from tests.test_observation_partial_rapm_v1 import (
    observation_contract as observation_contract_fixture,
)
from tests.test_partial_sound_audit_v1 import _thresholds


@pytest.fixture(scope="module")
def multistep_contract():
    source = observation_contract_fixture.__wrapped__()
    synthesis = synthesize_observed_lmb_partial_rapm_v1(
        source["log"], source["profile"], source["authority"]
    )
    base_model = synthesis.partial_build_result.model
    initial_state_id = source["observed_by_ground"][source["extra"]].state_id
    thresholds = _thresholds(base_model, initial_state_id, horizon=2)
    base_proposal = propose_partial_model_plan_from_observed_synthesis_v2(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        thresholds,
    )
    assert base_proposal.selected_plan is not None
    failed_audit = audit_partial_fixed_plan_from_observed_synthesis_v2(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        thresholds,
        base_proposal.selected_plan,
    )
    assert failed_audit.audit_result.outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    base_document = base_model.to_document()
    kernel = canonical_lmb_query_kernel_v1()
    result = run_lmb_h2_multistep_query_refinement_v1(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        thresholds,
        base_proposal,
        failed_audit,
        kernel,
    )
    return {
        **source,
        "synthesis": synthesis,
        "base_model": base_model,
        "base_document": base_document,
        "thresholds": thresholds,
        "base_proposal": base_proposal,
        "failed_audit": failed_audit,
        "kernel": kernel,
        "result": result,
    }


def test_public_runner_has_no_caller_selected_row_state_or_cap_scope() -> None:
    assert tuple(
        inspect.signature(run_lmb_h2_multistep_query_refinement_v1).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "thresholds",
        "base_plan_proposal",
        "failed_audit",
        "kernel",
    )
    assert tuple(
        inspect.signature(verify_lmb_h2_multistep_query_refinement_v1).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "thresholds",
        "base_plan_proposal",
        "failed_audit",
        "kernel",
        "claimed_result",
    )


def test_only_three_direct_boundary_catalogue_requests_are_made(
    multistep_contract,
    monkeypatch,
) -> None:
    kernel = multistep_contract["kernel"]
    kernel_type = type(kernel)
    original_actions = kernel_type.actions
    original_step = kernel_type.step
    original_digest = multistep_module._kernel_source_digest()
    original_authority = multistep_module.canonical_lmb_query_kernel_authority_v1()
    direct_catalogue_calls = 0
    step_internal_legality_checks = 0
    unexpected_action_calls = 0

    def count_actions(self, state):
        nonlocal direct_catalogue_calls
        nonlocal step_internal_legality_checks
        nonlocal unexpected_action_calls
        frame = inspect.currentframe()
        assert frame is not None and frame.f_back is not None
        caller_code = frame.f_back.f_code
        del frame
        if caller_code is multistep_module._expand_boundary.__code__:
            direct_catalogue_calls += 1
        elif caller_code is original_step.__code__:
            step_internal_legality_checks += 1
        else:
            unexpected_action_calls += 1
        return original_actions(self, state)

    monkeypatch.setattr(kernel_type, "actions", count_actions)
    monkeypatch.setattr(
        multistep_module, "_kernel_source_digest", lambda: original_digest
    )
    monkeypatch.setattr(
        multistep_module,
        "canonical_lmb_query_kernel_authority_v1",
        lambda: original_authority,
    )
    result = multistep_contract["result"]
    bundle_one = multistep_module._acquire(
        1,
        result.round_one_request,
        multistep_contract["log"],
        None,
        kernel,
    )
    boundary = multistep_module._expand_boundary(
        multistep_contract["log"],
        multistep_contract["synthesis"],
        result.round_one_request,
        bundle_one,
        kernel,
    )
    bundle_two = multistep_module._acquire(
        2,
        result.round_two_request,
        multistep_contract["log"],
        boundary,
        kernel,
    )
    assert direct_catalogue_calls == 3
    assert step_internal_legality_checks == 13
    assert unexpected_action_calls == 0
    assert bundle_one.to_document() == result.round_one_bundle.to_document()
    assert boundary.to_document() == result.boundary_expansion.to_document()
    assert bundle_two.to_document() == result.round_two_bundle.to_document()
    assert boundary.action_catalogue_query_count == 3


def test_round_one_resolves_exactly_four_rows_and_registers_three_boundaries(
    multistep_contract,
) -> None:
    result = multistep_contract["result"]
    request = result.round_one_request
    bundle = result.round_one_bundle
    boundary = result.boundary_expansion
    base_frontier = multistep_contract[
        "failed_audit"
    ].audit_result.failed_proof_frontier
    assert base_frontier is not None

    assert request.round_index == 1
    assert request.phase is MultiStepEvidencePhase.INITIAL_FRONTIER_ROWS
    assert request.frontier_id == base_frontier.frontier_id
    assert request.maximum_exact_kernel_queries == 4
    assert request.selected_plan_risk_row_count == 4
    assert request.unrestricted_value_challenger_row_count == 0
    assert request.request_preparation_kernel_calls == 0
    assert request.request_preparation_ground_search_calls == 0
    assert request.global_minimum_claimed is False
    assert all(item.concretizer_probability == Fraction(1, 4) for item in request.row_proofs)
    assert all(item.row_exposure_upper == Fraction(1, 4) for item in request.row_proofs)

    assert bundle.exact_kernel_query_count == 4
    assert bundle.extra_ground_row_access_count == 0
    assert sum(
        item.successor.kind is SuccessorKind.REGISTERED_STATE
        for item in bundle.evidence
    ) == 1
    assert sum(
        item.successor.kind is SuccessorKind.EXTERNAL_STATE
        for item in bundle.evidence
    ) == 3
    assert boundary.action_catalogue_query_count == 3
    assert boundary.exact_transition_query_count == 0
    assert boundary.ground_search_call_count == 0
    assert len(boundary.catalogues) == 3
    assert len(boundary.registered_boundary_state_ids) == 3
    assert len(boundary.registered_boundary_ground_row_ids) == 9
    assert all(len(item.actions) == 3 for item in boundary.catalogues)
    assert request.request_id == (
        "8deedc2abc78cb4b91d866f2e77e311a8ed1f0336db8e41fc8b20fa330714636"
    )
    assert boundary.expansion_id == (
        "6b9770c03a9473c5ecf47437d9fe82eaf550524576a03932572ae47a78ae1ddf"
    )


def test_first_overlay_reuses_the_discovered_coordinate_and_moves_frontier_to_t1(
    multistep_contract,
) -> None:
    contract = multistep_contract
    result = contract["result"]
    build = result.first_overlay_build
    model = build.model
    audit = result.first_plan_audit.audit_result
    frontier = audit.failed_proof_frontier

    assert contract["base_model"].to_document() == contract["base_document"]
    assert type(model) is QueryScopedPartialRAPMV3
    assert model.overlay_version == 1
    assert model.previous_model_id == contract["base_model"].model_id
    assert model.query_neutral is False
    assert model.transition_closure_claimed is False
    assert model.promotion_authorized is False
    assert len(model.coverage.observed_ground_row_ids) == 11
    assert len(model.coverage.missing_ground_row_ids) == 9
    reused_cell = next(
        item
        for item in model.cells
        if item.planning_kind is PlanningKind.ACTIVE
        and item.coordinate_values == (3,)
    )
    assert len(reused_cell.member_state_ids) == 4
    labels = {
        item.label_values
        for item in model.semantic_actions
        if item.cell_id == reused_cell.cell_id
    }
    assert labels == {(False,), (True,)}
    assert result.first_plan_proposal.candidate_count == 4
    assert result.first_plan_proposal.fixed_plan_audit_count == 4
    assert result.first_plan_proposal.exact_kernel_calls_during_planning == 0
    assert (
        result.first_plan_proposal.semantic_tie_break_rule
        == "NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1"
    )
    assert result.first_plan_proposal.selected_semantic_tie_break_key == (
        0, 1, 0, 1, 0, 1, 0, 1
    )
    assert audit.outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    assert frontier is not None
    assert frontier.earliest_time_index == 1
    assert frontier.remaining_horizon == 1
    assert frontier.reason is FailedProofReason.UNRESOLVED_POLICY_PATH_DISTINCTION
    assert frontier.external_coverage_failed is False
    assert build.model.model_id == (
        "e3d550b7d46b516bd443881e14ade00b8a1cc673f141039d09dc585fa2b28fba"
    )


def test_round_two_is_the_complete_nine_row_value_risk_scope(
    multistep_contract,
) -> None:
    result = multistep_contract["result"]
    request = result.round_two_request
    bundle = result.round_two_bundle
    boundary = result.boundary_expansion

    assert request.round_index == 2
    assert request.phase is MultiStepEvidencePhase.DOWNSTREAM_VALUE_RISK_ROWS
    assert request.requested_ground_row_ids == (
        boundary.registered_boundary_ground_row_ids
    )
    assert request.maximum_exact_kernel_queries == 9
    assert request.selected_plan_risk_row_count == 3
    assert request.unrestricted_value_challenger_row_count == 9
    assert sum(item.selected_plan_support for item in request.row_proofs) == 3
    assert sum(item.required_for_risk for item in request.row_proofs) == 3
    assert sum(item.required_for_value for item in request.row_proofs) == 9
    assert all(item.current_model_missing for item in request.row_proofs)
    assert bundle.exact_kernel_query_count == 9
    assert bundle.extra_ground_row_access_count == 0
    assert sum(item.failure for item in bundle.evidence) == 6
    assert sum(not item.failure for item in bundle.evidence) == 3
    assert sum(
        dict(item.reward_features).get("match", Fraction(0)) == 1
        for item in bundle.evidence
    ) == 3
    assert request.request_id == (
        "dc79dda993650f03b335217fbdf98cc10449bb79f7374d0440258996b84b1ccf"
    )


def test_final_partial_overlay_certifies_h2_without_ground_optimization(
    multistep_contract,
) -> None:
    result = multistep_contract["result"]
    final_build = result.final_overlay_build
    model = final_build.model
    proposal = result.final_plan_proposal
    audit = result.final_plan_audit.audit_result
    telemetry = result.telemetry

    assert type(result) is MultiStepQueryRefinementResultV1
    assert result.status == SUCCESS_STATUS
    assert result.promotion_disposition == "RETAIN_QUERY_LOCAL_OVERLAY_ONLY"
    assert result.reusable_base_mutated is False
    assert result.general_causal_minimality_claimed is False
    assert result.sample_saving_claimed is False
    assert model.overlay_version == 2
    assert model.previous_model_id == result.first_overlay_build.model.model_id
    assert len(model.coverage.observed_ground_row_ids) == 20
    assert len(model.coverage.missing_ground_row_ids) == 0
    assert model.transition_closure_claimed is False
    assert proposal.candidate_count == proposal.fixed_plan_audit_count == 4
    assert (
        proposal.selection_mode
        is PartialModelPlannerSelectionMode.INTERNAL_V0043_AUDIT_PASS_REWARD_MAX
    )
    reused_cell = next(
        item
        for item in model.cells
        if item.planning_kind is PlanningKind.ACTIVE
        and item.coordinate_values == (3,)
    )
    selected_stage_one = {
        item.cell_id: item.semantic_action_id
        for item in proposal.selected_plan.stages[1].assignments
    }
    selected_action = next(
        item
        for item in model.semantic_actions
        if item.semantic_action_id == selected_stage_one[reused_cell.cell_id]
    )
    assert selected_action.label_values == (False,)
    assert audit.outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
    assert audit.certificate is not None
    assert audit.failed_proof_frontier is None
    assert audit.robust_bounds.policy_reward_lower == 1
    assert audit.robust_bounds.policy_reward_upper == 1
    assert audit.robust_bounds.policy_failure_lower == 0
    assert audit.robust_bounds.policy_failure_upper == 0
    assert audit.robust_bounds.normalized_distribution_regret == 0
    assert (
        telemetry.round_one_exact_kernel_queries,
        telemetry.boundary_action_catalogue_queries,
        telemetry.round_two_exact_kernel_queries,
        telemetry.cumulative_exact_kernel_queries,
        telemetry.replanning_pass_count,
        telemetry.total_candidate_plan_audits,
        telemetry.reused_existing_coordinate_signature_count,
    ) == (4, 3, 9, 13, 2, 8, 1)
    assert telemetry.exact_kernel_calls_during_planning_and_audit == 0
    assert telemetry.direct_ground_optimization_calls == 0
    assert telemetry.sample_efficiency_claimed is False
    assert model.model_id == (
        "a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315"
    )
    assert result.final_plan_audit.result_id == (
        "81f379b9485d1da2aaf56fd20ff75d5c45c8ac4b870cc6e52b795ef6896e9529"
    )
    assert telemetry.telemetry_id == (
        "bd65b6748493283b3d6f8b6b6345354dc44df01cdad92e3fc1d053f9f13cea03"
    )
    assert result.result_id == (
        "9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42"
    )


def test_multistep_chain_rejects_scope_omission_and_claim_escalation(
    multistep_contract,
) -> None:
    result = multistep_contract["result"]
    request = result.round_two_request
    with pytest.raises(MultiStepRefinementInvariantViolation):
        replace(
            request,
            requested_ground_row_ids=request.requested_ground_row_ids[:-1],
        )
    with pytest.raises(ValueError):
        replace(result.final_overlay_build.model, promotion_authorized=True)
    with pytest.raises(MultiStepRefinementInvariantViolation):
        replace(
            result.round_one_request.row_proofs[0],
            required_for_risk=False,
            required_for_value=False,
        )


def test_independent_verifier_replays_the_complete_two_round_chain(
    multistep_contract,
) -> None:
    contract = multistep_contract
    verified = verify_lmb_h2_multistep_query_refinement_v1(
        contract["log"],
        contract["profile"],
        contract["authority"],
        contract["synthesis"],
        contract["thresholds"],
        contract["base_proposal"],
        contract["failed_audit"],
        contract["kernel"],
        contract["result"],
    )
    assert verified.to_document() == contract["result"].to_document()
