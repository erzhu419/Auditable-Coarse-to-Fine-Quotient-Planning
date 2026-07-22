"""V0-049 held-out family, matched cold baseline, and amortization regressions."""

from dataclasses import replace
from fractions import Fraction
import inspect
import sys

import pytest

import acfqp.heldout_family_amortization_v1 as family_module
from acfqp.heldout_family_amortization_v1 import (
    ComponentwiseRelation,
    FAMILY_TARGET_STATES,
    HeldOutFamilyInvariantViolation,
    OCCURRENCE_QUERY_INDICES,
    preregister_lmb_heldout_family_v1,
    run_cold_direct_h1_baseline_v1,
    run_lmb_heldout_family_amortization_v1,
    run_preregistered_heldout_family_occurrence_v1,
    verify_lmb_heldout_family_amortization_v1,
)
from acfqp.multistep_query_refinement_v1 import (
    canonical_lmb_query_kernel_v1,
    run_lmb_h2_multistep_query_refinement_v1,
)
from acfqp.observation_partial_rapm_v1 import (
    ObservationPartialRAPMInvariantViolation,
    PreregisteredReusablePartialRAPMV5,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    synthesize_observed_lmb_partial_rapm_v1,
)
from acfqp.partial_model_planner_v1 import (
    propose_partial_model_plan_from_observed_synthesis_v2,
)
from acfqp.partial_sound_audit_v1 import (
    FrozenPartialAuditThresholdsV1,
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
def family_contract():
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

    # All targets and the workload order are frozen before source acquisition.
    protocol = preregister_lmb_heldout_family_v1(
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
    base_before = base_model.to_document()
    result = run_lmb_heldout_family_amortization_v1(
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
    assert base_model.to_document() == base_before
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


def test_family_is_preregistered_and_source_and_cold_apis_are_blind(
    family_contract,
) -> None:
    contract = family_contract
    protocol = contract["protocol"]
    assert tuple(inspect.signature(preregister_lmb_heldout_family_v1).parameters) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "source_thresholds",
    )
    assert tuple(
        inspect.signature(run_lmb_h2_multistep_query_refinement_v1).parameters
    ) == protocol.source_runner_parameter_names
    assert protocol.source_query_target_input_count == 0
    assert tuple(
        inspect.signature(run_cold_direct_h1_baseline_v1).parameters
    ) == ("observation_log", "query", "occurrence", "kernel")
    assert "promotion" not in inspect.signature(run_cold_direct_h1_baseline_v1).parameters
    assert "source_result" not in inspect.signature(run_cold_direct_h1_baseline_v1).parameters
    assert "kernel" not in inspect.signature(
        run_preregistered_heldout_family_occurrence_v1
    ).parameters
    assert tuple(item.query_index for item in protocol.target_queries) == (1, 2, 3)
    assert tuple(
        item.initial_state.to_document() for item in protocol.target_queries
    ) == tuple(family_module._state_observation(item).to_document() for item in FAMILY_TARGET_STATES)
    assert tuple(
        next(
            query.query_index
            for query in protocol.target_queries
            if query.query_id == occurrence.query_id
        )
        for occurrence in protocol.logical_occurrences
    ) == OCCURRENCE_QUERY_INDICES
    assert not {
        item.initial_state.state_id for item in protocol.target_queries
    } & {item.state_id for item in contract["log"].states}


def test_complete_model_is_promoted_into_separate_three_state_v5_scope(
    family_contract,
) -> None:
    contract = family_contract
    promotion = contract["result"].promotion_build
    model = promotion.model
    assert type(model) is PreregisteredReusablePartialRAPMV5
    assert len(promotion.eligibility_proof.complete_promoted_ground_row_ids) == 20
    assert len(promotion.eligibility_proof.source_exact_evidence_ids) == 13
    assert len(promotion.eligibility_proof.target_coverages) == 3
    assert sum(
        len(item.ground_row_ids)
        for item in promotion.eligibility_proof.target_coverages
    ) == 9
    assert promotion.eligibility_proof.target_filtered_row_count == 0
    assert model.coverage.missing_ground_row_ids == ()
    assert model.authorized_initial_state_ids == tuple(
        sorted(item.initial_state.state_id for item in contract["protocol"].target_queries)
    )
    assert model.parent_scoped_model.to_document() == (
        promotion.parent_promotion.model.to_document()
    )
    assert model.query_neutral is True
    assert model.acquisition_query_neutral_attested is False
    assert model.promotion_scope_query_neutral_attested is True
    assert model.unrestricted_reuse_claimed is False
    assert model.transition_closure_claimed is False
    assert model.exact_quotient_claimed is False


def test_ten_warm_certificates_match_complete_cold_direct_plans(
    family_contract,
) -> None:
    result = family_contract["result"]
    assert len(result.matched_occurrences) == 10
    for matched in result.matched_occurrences:
        bounds = matched.warm_audit.audit_result.robust_bounds
        assert matched.warm_audit.audit_result.outcome is PartialAuditOutcome.CERTIFIED_FIXED_PLAN
        assert (
            bounds.policy_reward_lower,
            bounds.policy_reward_upper,
            bounds.policy_failure_upper,
            bounds.normalized_distribution_regret,
        ) == (Fraction(1), Fraction(1), Fraction(0), Fraction(0))
        assert matched.warm_work.exact_transition_calls == 0
        assert matched.warm_work.direct_catalogue_calls == 0
        assert matched.warm_work.model_plan_candidates == 2
        assert matched.warm_work.model_fixed_plan_audits == 3
        assert matched.cold_direct.optimal_reward == 1
        assert matched.cold_direct.failure_probability == 0
        assert matched.cold_direct.normalized_regret == 0
        assert matched.cold_direct.exact_transition_calls == 3
        assert matched.cold_direct.direct_catalogue_calls == 1
        assert matched.cold_direct.step_internal_legality_checks == 3
        assert matched.cold_direct.ground_action_candidates == 3
        assert matched.cold_direct.direct_ground_optimizer_calls == 1
        assert matched.cold_direct.promotion_input_count == 0
        assert matched.cold_direct.source_result_input_count == 0
        assert len(matched.matching_source_evidence_ids) == 3


def test_prefix_curve_and_lane_accounting_are_exact_and_non_scalar(
    family_contract,
) -> None:
    result = family_contract["result"]
    source_relations = tuple(item.source_inclusive_relation for item in result.prefixes)
    verification_relations = tuple(
        item.verification_inclusive_relation for item in result.prefixes
    )
    assert source_relations == (
        ComponentwiseRelation.COLD_STRICT_COMPONENTWISE,
        ComponentwiseRelation.COLD_STRICT_COMPONENTWISE,
        ComponentwiseRelation.COLD_STRICT_COMPONENTWISE,
        ComponentwiseRelation.INCOMPARABLE,
        ComponentwiseRelation.WARM_STRICT_COMPONENTWISE,
        ComponentwiseRelation.WARM_STRICT_COMPONENTWISE,
        ComponentwiseRelation.WARM_STRICT_COMPONENTWISE,
        ComponentwiseRelation.WARM_STRICT_COMPONENTWISE,
        ComponentwiseRelation.WARM_STRICT_COMPONENTWISE,
        ComponentwiseRelation.WARM_STRICT_COMPONENTWISE,
    )
    assert verification_relations == (
        *(ComponentwiseRelation.COLD_STRICT_COMPONENTWISE for _ in range(6)),
        ComponentwiseRelation.INCOMPARABLE,
        ComponentwiseRelation.INCOMPARABLE,
        ComponentwiseRelation.WARM_STRICT_COMPONENTWISE,
        ComponentwiseRelation.WARM_STRICT_COMPONENTWISE,
    )
    final = result.prefixes[-1]
    assert (
        final.source_inclusive_warm_transition_calls,
        final.source_inclusive_warm_catalogue_calls,
        final.verification_inclusive_warm_transition_calls,
        final.verification_inclusive_warm_catalogue_calls,
        final.cold_transition_calls,
        final.cold_catalogue_calls,
    ) == (13, 3, 26, 6, 30, 10)
    assert (
        result.source_work.exact_transition_calls,
        result.source_work.direct_catalogue_calls,
    ) == (
        family_contract["source_result"].telemetry.cumulative_exact_kernel_queries,
        family_contract["source_result"].telemetry.boundary_action_catalogue_queries,
    )
    replay_proof = result.promotion_build.parent_promotion.eligibility_proof
    assert (
        result.promotion_replay_work.exact_transition_calls,
        result.promotion_replay_work.direct_catalogue_calls,
    ) == (
        replay_proof.independent_replay_transition_calls,
        replay_proof.independent_replay_direct_catalogue_calls,
    )
    assert result.telemetry.source_transition_calls == (
        result.source_work.exact_transition_calls
    )
    assert all(item.official_scalar_cost is None for item in result.prefixes)
    assert all(item.official_N_break_even is None for item in result.prefixes)
    telemetry = result.telemetry
    assert telemetry.first_source_inclusive_warm_dominance_prefix == 5
    assert telemetry.first_verification_inclusive_warm_dominance_prefix == 9
    assert telemetry.source_cost_amortization_included is True
    assert telemetry.cold_end_to_end_planner_claimed is True
    assert telemetry.sample_efficiency_claimed is False
    assert telemetry.exact_kernel_calls_are_samples is False
    assert telemetry.tax_operator_selected is False
    assert telemetry.dominant_tax_axis is None
    assert telemetry.sample_efficiency_gate_status == "NOT_RUN"


def test_cold_direct_method_access_is_one_catalogue_plus_three_steps(
    family_contract,
) -> None:
    contract = family_contract
    query = contract["protocol"].target_queries[1]
    occurrence = contract["protocol"].logical_occurrences[1]
    action_calls = 0
    step_calls = 0
    actions_code = type(contract["kernel"]).actions.__code__
    step_code = type(contract["kernel"]).step.__code__

    def profile_calls(frame, event, arg):
        del arg
        if event != "call":
            return
        nonlocal action_calls
        nonlocal step_calls
        if frame.f_code is actions_code:
            action_calls += 1
        elif frame.f_code is step_code:
            step_calls += 1

    sys.setprofile(profile_calls)
    try:
        cold = run_cold_direct_h1_baseline_v1(
            contract["log"], query, occurrence, contract["kernel"]
        )
    finally:
        sys.setprofile(None)
    assert cold.direct_catalogue_calls == 1
    assert cold.exact_transition_calls == 3
    assert step_calls == 3
    # One explicit catalogue plus one internal legality check per step.
    assert action_calls == 4


def test_scope_claim_and_accounting_escalations_fail_closed(
    family_contract,
) -> None:
    contract = family_contract
    result = contract["result"]
    model = result.promotion_build.model
    with pytest.raises(ObservationPartialRAPMInvariantViolation):
        replace(
            model,
            authorized_initial_state_ids=tuple(
                sorted((*model.authorized_initial_state_ids, contract["protocol"].singleton_protocol.source_initial_state_id))
            ),
        )
    with pytest.raises(ObservationPartialRAPMInvariantViolation):
        replace(model, acquisition_query_neutral_attested=True)
    with pytest.raises(HeldOutFamilyInvariantViolation):
        replace(result.telemetry, sample_efficiency_claimed=True)
    with pytest.raises(HeldOutFamilyInvariantViolation):
        replace(result.telemetry, official_N_break_even=5)
    with pytest.raises(HeldOutFamilyInvariantViolation):
        replace(
            result.prefixes[3],
            source_inclusive_relation=ComponentwiseRelation.WARM_STRICT_COMPONENTWISE,
        )
    with pytest.raises(HeldOutFamilyInvariantViolation):
        replace(result.matched_occurrences[0].cold_direct, promotion_input_count=1)

    first = result.matched_occurrences[0]
    out_of_scope = FrozenPartialAuditThresholdsV1(
        model.model_id,
        1,
        (
            InitialStateMassV1(
                contract["protocol"].singleton_protocol.source_initial_state_id,
                Fraction(1),
            ),
        ),
        first.threshold_binding.thresholds.reward_weights,
        Fraction(0),
        Fraction(0),
        first.threshold_binding.thresholds.return_bound_proof,
    )
    with pytest.raises(PartialSoundAuditInvariantViolation):
        _audit_verified_partial_model_v1(
            model,
            contract["log"],
            contract["profile"],
            contract["authority"],
            out_of_scope,
            replace(
                first.warm_plan.selected_plan,
                partial_model_id=model.model_id,
            ),
        )


def test_canonical_family_identities_are_frozen(family_contract) -> None:
    result = family_contract["result"]
    # Values are frozen after the first clean semantic replay.
    assert result.promotion_build.protocol.protocol_id == (
        "96589cb7d925ca856e2c83ab8dfb3beb859225bde2cbe2311caf06e5111b8e58"
    )
    assert result.promotion_build.eligibility_proof.proof_id == (
        "45cbb9b7f99ca88905876d11c2e1b600fc10d0d75c496cf5a2104a25f48398ab"
    )
    assert result.promotion_build.model.model_id == (
        "d60d051e9422a40f3088875fa6a47e34f153dae4967dfcff5faf9547837a5b12"
    )
    assert result.promotion_build.result_id == (
        "93522fbcd24003d5ca9d2554a0a9c38eaf3d50f501211a394a475f96d057f4d7"
    )
    assert result.telemetry.telemetry_id == (
        "3df1ce57d3f7f1cee83da42cf422552c452498b1cd02ea904842c251cd0ec0cc"
    )
    assert result.prefixes[-1].prefix_id == (
        "28a8cbeac22b1c3116af2c00cd7996b7517e0e88959d313165dc7780edd4192e"
    )
    assert result.result_id == (
        "0445866669fdc2863856daf6986e855de71ba751e3b1f37b747b5490bf2880ba"
    )


def test_full_independent_family_replay_is_byte_identical(family_contract) -> None:
    contract = family_contract
    verified = verify_lmb_heldout_family_amortization_v1(
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
        contract["result"],
    )
    assert verified.to_document() == contract["result"].to_document()
