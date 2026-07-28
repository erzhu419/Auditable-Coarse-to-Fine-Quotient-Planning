from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.relational_support_synthesis_v1 as rel


@pytest.fixture(scope="module")
def campaign() -> rel.RelationalSupportCampaignV1:
    return rel.run_relational_support_campaign_v1()


def test_preregistration_freezes_disjoint_structural_family() -> None:
    preregistration = rel.preregister_relational_support_family_v1()

    assert len(preregistration.source_contexts) == 3
    assert len(preregistration.target_contexts) == 3
    assert len(preregistration.occurrences) == 6
    assert {
        item.structural_id for item in preregistration.source_contexts
    }.isdisjoint(
        {item.structural_id for item in preregistration.target_contexts}
    )
    assert all(
        item.held_out_from_source for item in preregistration.occurrences
    )
    assert preregistration.official_execution_allowed is False


def test_source_only_closure_selects_relational_coordinates() -> None:
    preregistration = rel.preregister_relational_support_family_v1()
    source_log = rel.acquire_source_relational_observations_v1(
        preregistration.source_contexts
    )
    proposal = rel.synthesize_relational_coordinate_support_v1(source_log)
    selected = next(
        item
        for item in proposal.candidate_trace.candidates
        if item.candidate_id == proposal.candidate_trace.selected_candidate_id
    )

    assert len(source_log.rows) == 144
    assert source_log.query_inputs_used == 0
    assert source_log.target_inputs_used == 0
    assert [item.cumulative_semantic_count for item in proposal.program_registry.summaries] == [
        7,
        19,
        56,
    ]
    assert len(proposal.program_registry.programs) == 56
    assert proposal.candidate_trace.required_candidate_count == 432
    assert proposal.candidate_trace.evaluated_candidate_count == 432
    assert sum(item.admissible for item in proposal.candidate_trace.candidates) == 13
    assert selected.abstract_row_count == 6
    assert proposal.state_program.operation == "cardinality_actions"
    assert proposal.state_program.arguments[0].operation == "legal_actions"
    assert proposal.action_program.operation == "cardinality_cells"
    adjacency = proposal.action_program.arguments[0]
    assert adjacency.operation == "adjacent_filter"
    assert tuple(item.operation for item in adjacency.arguments) == (
        "survivor_cell",
        "occupied_cells",
    )
    assert len(proposal.support_templates) == 6
    assert tuple(
        (
            item.remaining_horizon,
            item.state_coordinate_value[1],
            item.action_coordinate_value[1],
        )
        for item in proposal.proposed_decisions
    ) == ((1, 2, 1), (1, 4, 1), (2, 2, 2))
    assert proposal.target_inputs_used == 0
    assert proposal.query_inputs_used == 0
    assert proposal.target_certificate_authority is False
    assert (
        proposal.concretizer_kind
        == "uniform_over_distinct_matching_ground_actions_v1"
    )
    assert proposal.abstract_selector_randomized is False


def test_producer_api_has_no_target_query_kernel_or_frontier_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preregistration = rel.preregister_relational_support_family_v1()
    source_log = rel.acquire_source_relational_observations_v1(
        preregistration.source_contexts
    )
    signature = inspect.signature(rel.synthesize_relational_coordinate_support_v1)
    assert tuple(signature.parameters) == ("source_log",)

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("source-only producer reached a ground kernel")

    monkeypatch.setattr(rel.G2048Kernel, "step", forbidden)
    monkeypatch.setattr(rel.G2048Kernel, "actions", forbidden)
    proposal = rel.synthesize_relational_coordinate_support_v1(source_log)
    assert proposal.target_inputs_used == 0

    module_source = inspect.getsource(rel)
    for forbidden_token in (
        "D4_ELEMENTS",
        "canonicalize_d4",
        "G2048RelativeSurvivorAdapter",
        "ADAPTIVE_ROW_KEYS",
        '"ROOT_',
        '"CHAIN_',
    ):
        assert forbidden_token not in module_source


def test_target_recovery_is_two_round_target_only_context_build_and_reuse(
    campaign: rel.RelationalSupportCampaignV1,
) -> None:
    for result in campaign.target_results:
        assert result.first_audit.outcome is rel.TargetAuditOutcome.FAILED_MISSING_SUPPORT
        assert len(result.first_audit.missing_support_ids) == 1
        assert result.first_evidence.ground_transition_row_count == 8
        assert result.second_audit.outcome is rel.TargetAuditOutcome.FAILED_MISSING_SUPPORT
        assert len(result.second_audit.missing_support_ids) == 2
        assert result.second_evidence.ground_transition_row_count == 16
        assert result.final_audit.outcome is rel.TargetAuditOutcome.CERTIFIED
        assert result.final_audit.failure_upper < Fraction(1, 20)
        assert result.final_audit.normalized_regret_upper == 0
        assert result.final_model.source_dynamics_imported is False
        assert result.final_model.exact_dynamics_claimed is False
        assert result.context_build_ground_rows == 24
        assert result.occurrence_new_ground_rows == (0, 0)
        assert all(
            item.model_id == result.final_model.model_id
            and item.outcome is rel.TargetAuditOutcome.CERTIFIED
            for item in result.occurrence_audits
        )
        assert len({item.audit_id for item in result.occurrence_audits}) == 2
        assert tuple(
            item.occurrence_id for item in result.occurrence_audits
        ) == tuple(item.occurrence_id for item in result.direct_controls)
        assert all(
            item.family_confidence_lower == Fraction(239, 250)
            for item in result.occurrence_audits
        )


def test_statistical_work_and_claim_boundary_are_exact(
    campaign: rel.RelationalSupportCampaignV1,
) -> None:
    assert campaign.source_ground_row_count == 144
    assert campaign.target_ground_row_count == 72
    assert campaign.target_generative_sample_count == 72 * 16_384
    assert campaign.wrong_ground_row_count == 16
    assert campaign.wrong_generative_sample_count == 16 * 16_384
    assert campaign.statistical_coordinate_obligations == 176
    assert campaign.family_tail_upper == Fraction(11, 250)
    assert campaign.family_confidence_lower == Fraction(239, 250)
    assert campaign.calibration.exponent == Fraction(2048, 225)
    assert campaign.calibration.taylor_lower > 8000
    assert campaign.automatic_coordinate_selection_claimed is True
    assert campaign.automatic_anonymous_support_proposal_claimed is True
    assert campaign.known_group_prior_used is False
    assert campaign.named_frontier_used is False
    assert campaign.target_only_certificate_claimed is True
    assert campaign.registered_symbolic_outcome_support_used is True
    assert campaign.unknown_outcome_support_claimed is False
    assert campaign.post_context_build_query_reuse_claimed is True
    assert campaign.sequential_occurrence_acquisition_claimed is False
    assert campaign.cross_structural_rapm_reuse_claimed is False
    assert campaign.primitive_invention_claimed is False
    assert campaign.broad_generalization_claimed is False
    assert campaign.sample_efficiency_claimed is False
    assert campaign.same_implementation_semantic_replay_claimed is True
    assert campaign.independent_algorithm_verification_claimed is False
    assert campaign.official_execution_allowed is False
    assert campaign.official_scalar_cost is None
    assert campaign.official_N_break_even is None


def test_cold_direct_controls_match_exact_ground_truth(
    campaign: rel.RelationalSupportCampaignV1,
) -> None:
    assert campaign.cold_direct_exact_ground_row_count == 108
    for result in campaign.target_results:
        expected_risk = (
            2
            * result.context.low_rank_probability
            * (1 - result.context.low_rank_probability)
        )
        expected_reward = (
            Fraction(
                2 ** (result.context.low_rank + 1),
                2 ** (rel.RANK_CAP + 1),
            )
            + Fraction(
                2 ** (result.context.low_rank + 2),
                2 ** (rel.RANK_CAP + 1),
            )
        ) / rel.NORMALIZER
        assert len(result.direct_controls) == 2
        assert all(
            item.reachable_state_action_row_count == 18
            and item.composed_candidate_count == 22
            and item.selected_failure_probability == expected_risk
            and item.selected_normalized_reward == expected_reward
            and item.feasible
            and item.model_reuse_count == 0
            for item in result.direct_controls
        )


def test_wrong_proposal_fails_before_fallback_without_false_certificate(
    campaign: rel.RelationalSupportCampaignV1,
) -> None:
    wrong = campaign.wrong_control
    assert wrong.final_audit.outcome is rel.TargetAuditOutcome.FAILED_RISK
    assert wrong.final_audit.failure_upper == 1
    assert wrong.acquired_ground_row_count == 16
    assert wrong.false_certificate_count == 0
    assert wrong.fallback_required is True


def test_unregistered_support_and_ood_structure_fail_closed(
    campaign: rel.RelationalSupportCampaignV1,
) -> None:
    result = campaign.target_results[0]
    context = result.context
    kernel = rel._kernel_for_context(context)
    initial = rel._initial_target_catalogues(context, kernel)
    decisions = rel._decision_lookup(campaign.proposal)
    root_key = next(key for key in decisions if key[0] == rel.HORIZON)
    decisions[root_key] = ("INTEGER", 99)
    audit = rel.audit_relational_partial_model_v1(
        campaign.preregistration,
        campaign.proposal,
        context,
        result.final_model,
        campaign.calibration,
        initial,
        decision_override=decisions,
    )
    assert audit.outcome is rel.TargetAuditOutcome.FAILED_UNREGISTERED_SUPPORT

    with pytest.raises(rel.RelationalSupportInvariantViolation):
        rel.RelationalStructuralContextV1(
            "unregistered_geometry",
            rel.ContextSplit.TARGET,
            4,
            Fraction(999, 1000),
            ((0, 1), (1, 2), (2, 3)),
        )


def test_authorization_rejects_stale_or_nonfailed_proof(
    campaign: rel.RelationalSupportCampaignV1,
) -> None:
    result = campaign.target_results[0]
    with pytest.raises(rel.RelationalSupportInvariantViolation):
        rel.authorize_failed_relational_support_v1(
            campaign.preregistration,
            campaign.proposal,
            result.context,
            result.final_model,
            result.final_audit,
            3,
        )
    with pytest.raises(rel.RelationalSupportInvariantViolation):
        rel.authorize_failed_relational_support_v1(
            campaign.preregistration,
            campaign.proposal,
            result.context,
            result.intermediate_model,
            result.first_audit,
            2,
        )


def test_source_log_requires_complete_two_step_action_closure(
    campaign: rel.RelationalSupportCampaignV1,
) -> None:
    with pytest.raises(rel.RelationalSupportInvariantViolation):
        replace(campaign.source_log, rows=campaign.source_log.rows[:-1])


def test_target_acquisition_uses_generative_atom_api_not_exact_step(
    campaign: rel.RelationalSupportCampaignV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = campaign.target_results[0]
    kernel = rel._kernel_for_context(result.context)
    initial = rel._initial_target_catalogues(result.context, kernel)

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("target acquisition called exact kernel.step")

    monkeypatch.setattr(rel.RankRelativeAcquisitionKernelV1, "step", forbidden)
    replayed = rel.acquire_authorized_target_rows_v1(
        campaign.preregistration,
        campaign.proposal,
        result.context,
        result.first_authorization,
        kernel,
        initial,
    )
    assert replayed.to_document() == result.first_evidence.to_document()
    assert all(
        row.exact_probabilities_absent
        and row.structural_outcome_support_known
        and not row.unknown_outcome_support_claimed
        and row.probability_estimates_from_draws_only
        for row in replayed.sampled_rows
    )


def test_semantic_evidence_attestation_is_required_by_model_builder(
    campaign: rel.RelationalSupportCampaignV1,
) -> None:
    result = campaign.target_results[0]
    original = result.first_evidence
    row = original.sampled_rows[0]
    replacement_character = (
        "1" if row.outcome_nibbles_hex[0] != "1" else "0"
    )
    tampered_row = replace(
        row,
        outcome_nibbles_hex=(
            replacement_character + row.outcome_nibbles_hex[1:]
        ),
    )
    tampered = replace(
        original,
        sampled_rows=tuple(
            sorted(
                (tampered_row,) + original.sampled_rows[1:],
                key=lambda item: item.sampled_row_id,
            )
        ),
    )
    with pytest.raises(rel.RelationalSupportInvariantViolation):
        rel.build_relational_partial_model_v1(
            campaign.preregistration,
            campaign.proposal,
            result.context,
            (tampered,),
            (result.first_evidence_verification,),
        )
    kernel = rel._kernel_for_context(result.context)
    with pytest.raises(rel.RelationalSupportInvariantViolation):
        rel.verify_target_relational_evidence_v1(
            campaign.preregistration,
            campaign.proposal,
            result.context,
            result.initial_model,
            result.first_audit,
            result.first_authorization,
            tampered,
            kernel,
            rel._initial_target_catalogues(result.context, kernel),
        )


def test_fixed_uniform_concretizer_covers_all_distinct_matching_actions(
    campaign: rel.RelationalSupportCampaignV1,
) -> None:
    result = campaign.target_results[0]
    catalogues = rel.successor_catalogues_from_evidence_v1(
        result.first_evidence
    )
    multiplicities = [
        len(
            rel._selected_ground_actions(
                campaign.proposal,
                state,
                catalogue,
            )
        )
        for state, catalogue in catalogues
    ]
    assert multiplicities.count(1) == 8
    assert multiplicities.count(2) == 4
    assert (
        campaign.proposal.concretizer_kind
        == "uniform_over_distinct_matching_ground_actions_v1"
    )


def test_interval_rows_reject_duplicates_and_non_decreasing_horizon(
    campaign: rel.RelationalSupportCampaignV1,
) -> None:
    observed = next(
        row
        for row in campaign.target_results[0].final_model.rows
        if row.evidence == "TARGET_RAW_STATISTICAL"
    )
    duplicate = (observed.intervals[0], observed.intervals[0])
    with pytest.raises(rel.RelationalSupportInvariantViolation):
        replace(observed, intervals=duplicate)

    if observed.support_template.remaining_horizon == 1:
        cycle_destination = (
            "ACTIVE",
            1,
            observed.support_template.state_coordinate_value,
        )
    else:
        cycle_destination = (
            "ACTIVE",
            2,
            observed.support_template.state_coordinate_value,
        )
    cycle = rel.TargetSupportIntervalV1(
        cycle_destination,
        Fraction(0),
        Fraction(1),
    )
    with pytest.raises(rel.RelationalSupportInvariantViolation):
        replace(observed, intervals=(cycle,))


def test_implementation_and_kernel_authorities_are_frozen() -> None:
    assert (
        rel._observed_implementation_sha256_v1()
        == rel.IMPLEMENTATION_SHA256
    )
    assert (
        rel._observed_kernel_implementation_sha256_v1()
        == rel.KERNEL_IMPLEMENTATION_SHA256
    )


def test_raw_draw_tamper_and_chain_splice_are_rejected(
    campaign: rel.RelationalSupportCampaignV1,
) -> None:
    original_result = campaign.target_results[0]
    original_evidence = original_result.first_evidence
    original_row = original_evidence.sampled_rows[0]
    replacement_character = (
        "1" if original_row.outcome_nibbles_hex[0] != "1" else "0"
    )
    tampered_row = replace(
        original_row,
        outcome_nibbles_hex=(
            replacement_character + original_row.outcome_nibbles_hex[1:]
        ),
    )
    tampered_evidence = replace(
        original_evidence,
        sampled_rows=tuple(
            sorted(
                (tampered_row,) + original_evidence.sampled_rows[1:],
                key=lambda item: item.sampled_row_id,
            )
        ),
    )
    with pytest.raises(rel.RelationalSupportInvariantViolation):
        replace(
            original_result,
            first_evidence=tampered_evidence,
        )


def test_same_implementation_verifier_replays_complete_campaign(
    campaign: rel.RelationalSupportCampaignV1,
) -> None:
    verification = rel.verify_relational_support_campaign_v1(campaign)
    assert verification.replayed_source_row_count == 144
    assert verification.replayed_target_ground_row_count == 88
    assert verification.replayed_target_sample_count == 88 * 16_384
    assert verification.replayed_direct_ground_row_count == 108
    assert verification.exact_comparator_count == 6
    assert verification.proposal_byte_identical
    assert verification.target_results_byte_identical
    assert verification.wrong_control_byte_identical
    assert verification.raw_draws_replayed
    assert verification.claim_boundary_valid
    assert verification.independent_algorithm_verification is False
    assert (
        verification.verifier_kind
        == "same_implementation_full_semantic_replay_v1"
    )
