from __future__ import annotations

import copy
from dataclasses import replace
from fractions import Fraction

import pytest

import acfqp.cross_domain_lmb_rapm_v1 as lmb
import acfqp.variable_cardinality_multidomain_campaign_v1 as multi
import acfqp.variable_order_graph_rapm_v1 as graph


@pytest.fixture(scope="module")
def campaign() -> multi.VariableCardinalityMultidomainCampaignV1:
    return multi.run_variable_cardinality_multidomain_campaign_v1()


@pytest.fixture(scope="module")
def verification(
    campaign: multi.VariableCardinalityMultidomainCampaignV1,
) -> multi.VariableCardinalityMultidomainVerificationV1:
    return multi.verify_variable_cardinality_multidomain_campaign_v1(
        campaign
    )


def test_profile_uses_one_independently_verified_source_chain(
    campaign: multi.VariableCardinalityMultidomainCampaignV1,
) -> None:
    assert (
        multi.PROFILE_KEY
        == "variable_cardinality_two_domain_relational_rapm_v0"
    )
    assert (
        campaign.source_log.observation_log_id
        == campaign.graph_campaign.source_log.observation_log_id
        == campaign.independent_source_verification.source_observation_log_id
    )
    assert (
        campaign.source_skeleton.skeleton_id
        == campaign.graph_campaign.source_skeleton.skeleton_id
        == campaign.lmb_campaign.skeleton_id
        == campaign.independent_source_verification.skeleton_id
        == "77a9666172fb5cebf30820b12075fef92e190f3ccda6cdf44e4c902c7dc73322"
    )
    assert campaign.independent_source_verification.independent_implementation
    assert not campaign.independent_source_verification.producer_imported
    assert (
        campaign.graph_campaign.campaign_id
        == "8e839923dd2d965f6180fbff8abaebfbd6c5e9d6546cb60cb12666182bf7a77a"
    )
    assert (
        campaign.graph_verification.verification_id
        == "ad4a502c71eb1c3f3a55c1a1c468be06b529d2e1ba0cc62cbd149ba9dbae3bd1"
    )
    assert (
        campaign.lmb_campaign.campaign_id
        == "baa37d57d60fb67c513e5655734e98d211e82ef278c1c0347bed864cf8a9f1d6"
    )


def test_exact_program_ids_are_shared_but_target_identities_are_not(
    campaign: multi.VariableCardinalityMultidomainCampaignV1,
) -> None:
    isolation = campaign.isolation
    assert (
        isolation.state_program_id
        == campaign.source_skeleton.state_program.program_id
    )
    assert (
        isolation.action_program_id
        == campaign.source_skeleton.action_program.program_id
    )
    assert isolation.same_state_program_id
    assert isolation.same_action_program_id
    pairs = (
        (isolation.graph_context_ids, isolation.lmb_context_ids),
        (isolation.graph_evidence_ids, isolation.lmb_evidence_ids),
        (isolation.graph_model_ids, isolation.lmb_model_ids),
        (isolation.graph_binding_ids, isolation.lmb_binding_ids),
        (isolation.graph_dynamics_ids, isolation.lmb_dynamics_ids),
    )
    assert all(not (set(left) & set(right)) for left, right in pairs)
    assert isolation.context_identities_isolated
    assert isolation.evidence_identities_isolated
    assert isolation.model_identities_isolated
    assert isolation.binding_identities_isolated
    assert isolation.dynamics_identities_isolated


def test_conditional_union_bound_does_not_assume_cross_arm_independence(
    campaign: multi.VariableCardinalityMultidomainCampaignV1,
) -> None:
    calibration = campaign.union_calibration
    assert calibration.graph_family_tail_upper == Fraction(287, 250_000)
    assert calibration.lmb_family_tail_upper == Fraction(2, 125)
    assert calibration.union_tail_upper == Fraction(4_287, 250_000)
    assert calibration.union_confidence_lower == Fraction(245_713, 250_000)
    assert calibration.union_confidence_lower > Fraction(19, 20)
    assert (
        calibration.union_bound_kind
        == "boole_union_bound_without_cross_arm_independence_v1"
    )
    assert not calibration.cross_arm_independence_required
    assert not calibration.unconditional_iid_claimed
    assert campaign.graph_campaign.calibration.unconditional_iid_claim is False
    assert campaign.lmb_campaign.calibration.unconditional_iid_claimed is False


def test_graph_and_lmb_metrics_are_kept_in_native_units(
    campaign: multi.VariableCardinalityMultidomainCampaignV1,
) -> None:
    assert campaign.graph_target_context_count == 3
    assert campaign.lmb_target_context_count == 3
    assert tuple(
        item.evidence.ground_row_count
        for item in campaign.graph_campaign.results
    ) == (22, 60, 60)
    assert tuple(
        item.evidence.generative_draw_count
        for item in campaign.graph_campaign.results
    ) == (2_883_584, 7_864_320, 7_864_320)
    assert campaign.graph_sparse_ground_rows == 142
    assert campaign.graph_generative_draws == 18_612_224
    assert campaign.graph_sparse_complete_closure_calls == 0
    assert campaign.graph_fallback_exact_ground_rows == 60
    assert campaign.lmb_operational_support_count == 6
    assert campaign.lmb_operational_draws == 98_304
    assert campaign.lmb_operational_exact_ground_rows == 0
    assert campaign.lmb_standalone_cold_ground_rows == 13


def test_graph_has_two_conditional_plans_and_one_charged_exact_fallback(
    campaign: multi.VariableCardinalityMultidomainCampaignV1,
) -> None:
    results = campaign.graph_campaign.results
    assert sum(
        item.terminal_outcome
        is graph.VariableGraphTerminalOutcome.CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE
        for item in results
    ) == 2
    fallback = next(item for item in results if item.fallback_used)
    assert (
        fallback.context.context_key
        == "variable_negative_k6_minus_edge_v0"
    )
    assert fallback.fallback_proof is not None
    assert fallback.fallback_proof.exact_failure_probability == Fraction(
        2_277,
        16_000,
    )
    assert fallback.fallback_proof.evaluated_state_action_rows == 60


def test_lmb_reuse_is_only_repeated_occurrence_same_parameters(
    campaign: multi.VariableCardinalityMultidomainCampaignV1,
) -> None:
    assert (
        campaign.lmb_reuse_scope
        == "identity_distinct_repeated_occurrence_same_query_parameters_only"
    )
    assert not campaign.changed_query_reuse_claimed
    assert len(campaign.lmb_campaign.target_results) == 3
    for result in campaign.lmb_campaign.target_results:
        assert len(result.occurrences) == 2
        assert len({item.query.query_id for item in result.occurrences}) == 2
        assert len(
            {
                (
                    item.query.root_state,
                    item.query.horizon,
                    item.query.risk_tolerance,
                    item.query.regret_tolerance,
                    item.query.reward_normalizer,
                )
                for item in result.occurrences
            }
        ) == 1


def test_source_registry_dynamics_and_cross_target_rows_are_zero(
    campaign: multi.VariableCardinalityMultidomainCampaignV1,
) -> None:
    assert campaign.source_registry_rows_imported == 0
    assert campaign.source_dynamics_rows_imported == 0
    assert campaign.cross_target_transition_rows_imported == 0
    assert campaign.isolation.source_registry_rows_imported == 0
    assert campaign.isolation.source_dynamics_rows_imported == 0
    assert campaign.isolation.cross_target_transition_rows_imported == 0
    assert campaign.graph_campaign.source_transition_rows_imported == 0
    assert campaign.lmb_campaign.source_dynamics_imported is False


def test_executed_wrong_arm_transplants_fail_closed(
    campaign: multi.VariableCardinalityMultidomainCampaignV1,
) -> None:
    control = campaign.cross_arm_transplant
    assert control.executed_check_count == 6
    assert control.declared_only_check_count == 0
    assert control.graph_campaign_rejected_by_lmb_verifier
    assert control.lmb_campaign_rejected_by_graph_verifier
    assert control.lmb_evidence_rejected_by_graph_verifier
    assert control.graph_evidence_rejected_by_lmb_verifier
    assert control.graph_model_rejected_by_lmb_overlay
    assert control.graph_source_log_rejected_as_lmb_bridge
    replay = multi.run_variable_cardinality_cross_arm_transplants_v1(
        campaign.graph_campaign,
        campaign.lmb_campaign,
    )
    assert replay.control_id == control.control_id


def test_claim_and_economics_locks_remain_closed(
    campaign: multi.VariableCardinalityMultidomainCampaignV1,
) -> None:
    assert campaign.status == multi.SUCCESS_STATUS
    assert campaign.independent_source_verification_only
    assert campaign.target_same_implementation_verification
    assert not campaign.independent_target_verification_claimed
    assert not campaign.automatic_ontology_alignment_claimed
    assert not campaign.generic_model_selected_planning_claimed
    assert not campaign.unconditional_statistics_claimed
    assert not campaign.observational_ood_generalization_claimed
    assert not campaign.changed_query_reuse_claimed
    assert not campaign.sample_efficiency_claimed
    assert not campaign.official_execution_allowed
    assert campaign.official_scalar_cost is None
    assert campaign.official_N_break_even is None
    assert campaign.workload_economics_gate == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert campaign.counter_completeness_gate == "COUNTER_COMPLETENESS_GATE_NOT_RUN"


def test_claim_lock_and_identity_tampering_fail_before_replay(
    campaign: multi.VariableCardinalityMultidomainCampaignV1,
) -> None:
    with pytest.raises(
        multi.VariableCardinalityMultidomainInvariantViolation
    ):
        replace(campaign, automatic_ontology_alignment_claimed=True)
    with pytest.raises(
        multi.VariableCardinalityMultidomainInvariantViolation
    ):
        replace(
            campaign.isolation,
            lmb_context_ids=campaign.isolation.graph_context_ids,
        )
    tampered = copy.copy(campaign)
    object.__setattr__(tampered, "status", "TAMPERED")
    with pytest.raises(
        multi.VariableCardinalityMultidomainInvariantViolation
    ):
        multi.verify_variable_cardinality_multidomain_campaign_v1(tampered)


def test_full_verifier_reports_independent_source_only(
    campaign: multi.VariableCardinalityMultidomainCampaignV1,
    verification: multi.VariableCardinalityMultidomainVerificationV1,
) -> None:
    assert verification.campaign_id == campaign.campaign_id
    assert verification.independent_source_verified
    assert verification.graph_target_same_implementation_verified
    assert verification.lmb_target_same_implementation_verified
    assert not verification.independent_target_verification_claimed
    assert verification.conditional_union_bound_verified
    assert verification.claim_locks_verified
    assert (
        verification.independent_source_verification_id
        == campaign.independent_source_verification.verification_id
    )
    assert verification.graph_verification_id == (
        campaign.graph_verification.verification_id
    )
    assert verification.lmb_verification_id == (
        campaign.lmb_verification.verification_id
    )
