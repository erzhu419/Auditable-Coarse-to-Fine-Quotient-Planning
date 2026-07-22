"""V0-048 preregistered promotion and held-out reuse regressions."""

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.cross_query_promotion_v1 as promotion_module
import acfqp.multistep_query_refinement_v1 as multistep_module
from acfqp.cross_query_promotion_v1 import (
    CrossQueryPromotionInvariantViolation,
    CrossQueryPromotionResultV1,
    SUCCESS_STATUS,
    evaluate_cold_heldout_acquisition_v1,
    preregister_lmb_cross_query_reuse_v1,
    run_lmb_cross_query_promotion_v1,
    run_preregistered_heldout_query_v1,
    verify_lmb_cross_query_promotion_v1,
)
from acfqp.multistep_query_refinement_v1 import (
    canonical_lmb_query_kernel_v1,
    run_lmb_h2_multistep_query_refinement_v1,
)
from acfqp.observation_partial_rapm_v1 import (
    ObservationPartialRAPMInvariantViolation,
    PreregisteredReusablePartialRAPMV4,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    synthesize_observed_lmb_partial_rapm_v1,
)
from acfqp.partial_model_planner_v1 import (
    PartialModelPlannerSelectionMode,
    propose_partial_model_plan_from_observed_synthesis_v2,
)
from acfqp.partial_sound_audit_v1 import (
    InitialStateMassV1,
    PartialAuditOutcome,
    PartialSoundAuditInvariantViolation,
    _audit_verified_partial_model_v1,
    audit_partial_fixed_plan_from_observed_synthesis_v2,
)
from tests.test_observation_partial_rapm_v1 import (
    observation_contract as observation_contract_fixture,
)
from tests.test_partial_sound_audit_v1 import _thresholds


@pytest.fixture(scope="module")
def cross_query_contract():
    source = observation_contract_fixture.__wrapped__()
    synthesis = synthesize_observed_lmb_partial_rapm_v1(
        source["log"], source["profile"], source["authority"]
    )
    base_model = synthesis.partial_build_result.model
    source_initial_state_id = source["observed_by_ground"][source["extra"]].state_id
    source_thresholds = _thresholds(
        base_model,
        source_initial_state_id,
        horizon=2,
    )
    source_proposal = propose_partial_model_plan_from_observed_synthesis_v2(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        source_thresholds,
    )
    assert source_proposal.selected_plan is not None
    source_failed_audit = audit_partial_fixed_plan_from_observed_synthesis_v2(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        source_thresholds,
        source_proposal.selected_plan,
    )
    assert (
        source_failed_audit.audit_result.outcome
        is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    )

    # The target is frozen before any V0-047 result or kernel is supplied.
    protocol = preregister_lmb_cross_query_reuse_v1(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        source_thresholds,
    )
    kernel = canonical_lmb_query_kernel_v1()
    source_result = run_lmb_h2_multistep_query_refinement_v1(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        source_thresholds,
        source_proposal,
        source_failed_audit,
        kernel,
    )
    result = run_lmb_cross_query_promotion_v1(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        source_thresholds,
        source_proposal,
        source_failed_audit,
        protocol,
        source_result,
        kernel,
    )
    return {
        **source,
        "synthesis": synthesis,
        "base_model": base_model,
        "source_thresholds": source_thresholds,
        "source_proposal": source_proposal,
        "source_failed_audit": source_failed_audit,
        "protocol": protocol,
        "kernel": kernel,
        "source_result": source_result,
        "result": result,
    }


def test_target_is_preregistered_and_source_runner_is_target_blind(
    cross_query_contract,
) -> None:
    contract = cross_query_contract
    protocol = contract["protocol"]
    assert tuple(
        inspect.signature(preregister_lmb_cross_query_reuse_v1).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "source_thresholds",
    )
    assert tuple(
        inspect.signature(run_lmb_h2_multistep_query_refinement_v1).parameters
    ) == protocol.source_runner_parameter_names
    assert "target" not in " ".join(protocol.source_runner_parameter_names)
    assert "protocol" not in protocol.source_runner_parameter_names
    assert protocol.source_query_target_input_count == 0
    assert protocol.target_query.initial_state.state_id not in {
        item.state_id for item in contract["log"].states
    }
    assert (
        protocol.target_query.initial_state.state_id
        != protocol.source_initial_state_id
    )
    result = contract["result"]
    assert protocol.target_query.query_id == (
        "d651857a01ffd07170e4325e816b3acf79c7117cb140e23f6baad18e99621669"
    )
    assert protocol.protocol_id == (
        "fb072250b7c99374439f9d84989a044a75cd6b61e364586812f516604b2cf0f4"
    )
    assert result.promotion_build.eligibility_proof.proof_id == (
        "b3c68790c55ef7aa48b3a9a020b24f7083a6db06367b65095cbf607e64a01172"
    )
    assert result.promotion_build.model.model_id == (
        "85315d41c9540decac2b8a089fecb75fb979ab0569a084b08539ca29b5b66cdd"
    )
    assert result.promotion_build.result_id == (
        "a824f85817827a533c7f9afe3e05a73a7490aa91f63cac541cf51e890efb0500"
    )
    assert result.threshold_binding.binding_id == (
        "1fdc52f557f0a77805f7f0965e18a7b64221c85d632b7686389040a6722705dc"
    )
    assert result.plan_proposal.result_id == (
        "7fc5db36d3dc16d2f2930c82fe4560e69b1a3419f536567e8e6c20c844eaf309"
    )
    assert result.plan_audit.result_id == (
        "9efdbe1667879c24ab5b20d72ff8b33fd372c632b8b1f45c591617e71f8e5572"
    )
    assert result.cold_acquisition_trace.trace_id == (
        "443d7c4e4f6a751a5092f60afdd0e6d82ecbacd3f038c8fa27ca0c9a28458fb7"
    )
    assert result.telemetry.telemetry_id == (
        "384ab0c12872ba34f8183e1787cc566e6782cdf45369f0d7b99a08c32328caa8"
    )
    assert result.result_id == (
        "464a0b4b51d36c0fe251ec04b68c75f1b308958fa2eb721ccddd955629330993"
    )


def test_complete_source_model_is_promoted_without_mutating_base(
    cross_query_contract,
) -> None:
    contract = cross_query_contract
    result = contract["result"]
    promotion = result.promotion_build
    model = promotion.model
    assert type(model) is PreregisteredReusablePartialRAPMV4
    assert promotion.complete_model_promoted is True
    assert promotion.target_filtered_promotion is False
    assert promotion.eligibility_proof.target_filtered_row_count == 0
    assert len(promotion.eligibility_proof.complete_promoted_ground_row_ids) == 20
    assert len(promotion.eligibility_proof.source_exact_evidence_ids) == 13
    assert len(promotion.eligibility_proof.target_ground_row_ids) == 3
    assert model.coverage.observed_ground_row_ids == (
        promotion.eligibility_proof.complete_promoted_ground_row_ids
    )
    assert model.coverage.missing_ground_row_ids == ()
    assert model.query_neutral is True
    assert model.acquisition_query_neutral_attested is False
    assert model.promotion_scope_query_neutral_attested is True
    assert model.promotion_authorized is True
    assert model.unrestricted_reuse_claimed is False
    assert model.transition_closure_claimed is False
    assert model.exact_quotient_claimed is False
    assert promotion.base_model_mutated is False
    assert contract["base_model"].to_document() == (
        contract["synthesis"].partial_build_result.model.to_document()
    )


def test_held_out_consumer_has_no_kernel_and_certifies_model_only(
    cross_query_contract,
) -> None:
    result = cross_query_contract["result"]
    assert tuple(
        inspect.signature(run_preregistered_heldout_query_v1).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "promotion",
    )
    proposal = result.plan_proposal
    audit = result.plan_audit
    bounds = audit.audit_result.robust_bounds
    assert proposal.selection_mode is (
        PartialModelPlannerSelectionMode.INTERNAL_V0043_AUDIT_PASS_REWARD_MAX
    )
    assert proposal.candidate_count == proposal.fixed_plan_audit_count == 2
    assert proposal.exact_kernel_calls_during_planning == 0
    assert proposal.direct_ground_optimizer_calls == 0
    assert audit.audit_result.outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
    assert (bounds.policy_reward_lower, bounds.policy_reward_upper) == (1, 1)
    assert bounds.unrestricted_reward_upper == 1
    assert (bounds.policy_failure_lower, bounds.policy_failure_upper) == (0, 0)
    assert bounds.normalized_distribution_regret == 0
    assert bounds.external_coverage_certified is True
    assert audit.exact_kernel_calls_during_audit == 0
    assert audit.direct_ground_optimizer_calls == 0


def test_matched_cold_trace_is_evaluation_only_and_exact(
    cross_query_contract,
) -> None:
    trace = cross_query_contract["result"].cold_acquisition_trace
    assert trace.direct_catalogue_calls == 1
    assert trace.exact_transition_calls == 3
    assert trace.step_internal_legality_checks == 3
    assert trace.ground_search_calls == 0
    assert trace.direct_ground_optimizer_calls == 0
    assert trace.evaluation_lane_only is True
    assert trace.end_to_end_cold_planner_claimed is False
    assert len(trace.catalogue.actions) == 3
    assert len(trace.outcomes) == 3
    assert sum(item.failure for item in trace.outcomes) == 2
    assert sum(
        value
        for item in trace.outcomes
        for name, value in item.reward_features
        if name == "match"
    ) == 1


def test_warm_and_cold_work_lanes_are_not_conflated(
    cross_query_contract,
) -> None:
    result = cross_query_contract["result"]
    telemetry = result.telemetry
    assert result.status == SUCCESS_STATUS
    assert result.held_out_reuse_certified is True
    assert telemetry.source_refinement_transition_calls == 13
    assert telemetry.source_refinement_direct_catalogue_calls == 3
    assert telemetry.promotion_replay_transition_calls == 13
    assert telemetry.promotion_replay_direct_catalogue_calls == 3
    assert telemetry.warm_target_transition_calls == 0
    assert telemetry.warm_target_direct_catalogue_calls == 0
    assert telemetry.cold_evaluation_transition_calls == 3
    assert telemetry.cold_evaluation_direct_catalogue_calls == 1
    assert telemetry.source_cost_amortization_included is False
    assert telemetry.sample_efficiency_claimed is False
    assert telemetry.official_scalar_cost is None
    assert telemetry.official_n_break_even is None
    assert telemetry.sample_efficiency_gate_status == "NOT_RUN"


def test_scope_and_promotion_escalation_fail_closed(cross_query_contract) -> None:
    result = cross_query_contract["result"]
    model = result.promotion_build.model
    with pytest.raises(CrossQueryPromotionInvariantViolation):
        replace(
            result.promotion_build.eligibility_proof,
            target_filtered_row_count=3,
        )
    with pytest.raises(ObservationPartialRAPMInvariantViolation):
        replace(model, unrestricted_reuse_claimed=True)
    with pytest.raises(ObservationPartialRAPMInvariantViolation):
        replace(model, acquisition_query_neutral_attested=True)
    with pytest.raises(ObservationPartialRAPMInvariantViolation):
        replace(model, promotion_authorized=False)
    outside_scope_thresholds = replace(
        result.threshold_binding.thresholds,
        initial_state_distribution=(
            InitialStateMassV1(
                result.promotion_build.protocol.source_initial_state_id,
                Fraction(1),
            ),
        ),
    )
    with pytest.raises(PartialSoundAuditInvariantViolation):
        _audit_verified_partial_model_v1(
            model,
            cross_query_contract["log"],
            cross_query_contract["profile"],
            cross_query_contract["authority"],
            outside_scope_thresholds,
            result.plan_proposal.selected_plan,
        )


def test_cold_path_has_one_direct_and_three_internal_catalogue_calls(
    cross_query_contract,
    monkeypatch,
) -> None:
    contract = cross_query_contract
    authority = promotion_module.canonical_lmb_query_kernel_authority_v1()
    original_actions = type(contract["kernel"]).actions
    original_step = type(contract["kernel"]).step
    original_digest = multistep_module._kernel_source_digest()
    calls = {"direct": 0, "step_internal": 0, "unexpected": 0}

    def wrapped_actions(self, state):
        caller = inspect.currentframe().f_back.f_code
        if caller is promotion_module.evaluate_cold_heldout_acquisition_v1.__code__:
            calls["direct"] += 1
        elif caller is original_step.__code__:
            calls["step_internal"] += 1
        else:
            calls["unexpected"] += 1
        return original_actions(self, state)

    monkeypatch.setattr(
        promotion_module,
        "canonical_lmb_query_kernel_authority_v1",
        lambda: authority,
    )
    monkeypatch.setattr(
        multistep_module,
        "_kernel_source_digest",
        lambda: original_digest,
    )
    monkeypatch.setattr(type(contract["kernel"]), "actions", wrapped_actions)
    replay = evaluate_cold_heldout_acquisition_v1(
        contract["log"],
        contract["result"].promotion_build,
        contract["source_result"],
        contract["kernel"],
    )
    assert replay.to_document() == (
        contract["result"].cold_acquisition_trace.to_document()
    )
    assert calls == {"direct": 1, "step_internal": 3, "unexpected": 0}


def test_independent_full_replay_is_byte_identical(cross_query_contract) -> None:
    contract = cross_query_contract
    result = contract["result"]
    assert type(result) is CrossQueryPromotionResultV1
    verified = verify_lmb_cross_query_promotion_v1(
        contract["log"],
        contract["profile"],
        contract["authority"],
        contract["synthesis"],
        contract["source_thresholds"],
        contract["source_proposal"],
        contract["source_failed_audit"],
        contract["protocol"],
        contract["source_result"],
        contract["kernel"],
        result,
    )
    assert verified.to_document() == result.to_document()
