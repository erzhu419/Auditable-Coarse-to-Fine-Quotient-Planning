from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

import acfqp.cross_geometry_rapm_v1 as rapm
import acfqp.cross_graph_relational_support_v1 as foundation
import acfqp.relational_graph_core_v1 as graph_core


@pytest.fixture(scope="module")
def campaign() -> rapm.CrossGeometryCampaignV1:
    return rapm.run_cross_geometry_campaign_v1()


def test_calibration_is_preregistered_and_exact() -> None:
    calibration = rapm.cross_geometry_calibration_v1()
    assert calibration.sample_count_per_ground_row == 65_536
    assert calibration.radius == Fraction(1, 110)
    assert calibration.exponent == Fraction(65_536, 6_050)
    assert calibration.taylor_degree == 19
    assert calibration.taylor_lower > 50_000
    assert calibration.per_atom_tail_upper == Fraction(1, 25_000)
    assert calibration.preregistered_atom_obligations == 912
    assert calibration.family_tail_upper == Fraction(114, 3_125)
    assert calibration.family_confidence_lower == Fraction(3_011, 3_125)
    assert calibration.family_confidence_lower > Fraction(19, 20)


def test_source_only_proposal_is_cross_geometry_and_nonauthoritative(
    campaign: rapm.CrossGeometryCampaignV1,
) -> None:
    assert campaign.source_ground_rows == 120
    assert campaign.source_bundle.row_counts_by_context == tuple(
        (context.context_id, count)
        for context, count in zip(
            campaign.family.source_contexts,
            (36, 36, 48),
        )
    )
    assert (
        campaign.proposal.state_program.rendered
        == "cardinality_actions(legal_actions)"
    )
    assert (
        campaign.proposal.action_program.rendered
        == "cardinality_cells("
        "adjacent_filter(survivor_cell,occupied_cells))"
    )
    assert campaign.proposal.source_dynamics_included is False
    assert campaign.proposal.source_decisions_included is False
    assert campaign.proposal.target_identity_included is False
    assert campaign.proposal.query_identity_included is False
    assert graph_core.verify_relational_graph_proposal_v1(
        campaign.source_bundle.observation_log,
        campaign.proposal,
    )


def test_target_construction_is_two_round_target_only(
    campaign: rapm.CrossGeometryCampaignV1,
) -> None:
    assert campaign.target_ground_rows == 180
    assert campaign.target_generative_samples == 180 * 65_536
    expected = {
        "c4": (16, 32, 48),
        "diamond": (20, 40, 60),
        "k4": (24, 48, 72),
    }
    for result in campaign.target_results:
        first, second, total = expected[result.context.graph_key]
        assert (
            result.first_audit.outcome
            is rapm.TargetAuditOutcome.FAILED_MISSING_SUPPORT
        )
        assert (
            result.second_audit.outcome
            is rapm.TargetAuditOutcome.FAILED_MISSING_SUPPORT
        )
        assert result.first_evidence.ground_row_count == first
        assert result.second_evidence.ground_row_count == second
        assert result.context_build_ground_rows == total
        assert result.final_model.source_dynamics_imported is False
        assert result.final_model.exact_probabilities_used is False
        assert result.final_audit.target_transition_calls == 0
        assert result.final_audit.source_dynamics_used is False


def test_base_replans_on_k4_and_fails_closed_on_diamond_before_refinement(
    campaign: rapm.CrossGeometryCampaignV1,
) -> None:
    c4, diamond, k4 = campaign.target_results
    assert (
        c4.base_final_audit.outcome
        is rapm.TargetAuditOutcome.CERTIFIED
    )
    assert (
        diamond.base_final_audit.outcome
        is rapm.TargetAuditOutcome.FAILED_RISK_OR_REGRET
    )
    assert diamond.base_final_audit.failure_upper > Fraction(1, 2)
    assert (
        k4.base_final_audit.outcome
        is rapm.TargetAuditOutcome.CERTIFIED
    )
    assert {
        item.action_coordinate
        for item in k4.final_audit.decisions
    } == {(("INTEGER", 2),)}
    assert {
        item.state_coordinate
        for item in k4.final_audit.decisions
    } == {
        (("INTEGER", 2),),
        (("INTEGER", 6),),
    }
    assert campaign.legacy_control.abstract_certificate_count == 1
    assert campaign.legacy_control.rejected_context_count == 2
    assert campaign.legacy_control.false_certificate_count == 0


def test_failed_diamond_certificate_selects_only_source_frozen_programs(
    campaign: rapm.CrossGeometryCampaignV1,
) -> None:
    diamond = campaign.target_results[1]
    assert diamond.final_profile.refinement_index == 1
    assert diamond.refinement_trace is not None
    assert len(diamond.refinement_trace.candidates) == 4
    assert (
        diamond.final_profile.state_programs[-1].rendered
        == "rank_degree_signature"
    )
    assert (
        diamond.final_profile.action_programs[-1].rendered
        == "cardinality_cells("
        "adjacent_filter(survivor_cell,all_cells))"
    )
    assert (
        diamond.refinement_trace.target_program_generation_count == 0
    )
    assert (
        diamond.refinement_trace.target_primitive_generation_count == 0
    )
    assert (
        diamond.final_audit.outcome
        is rapm.TargetAuditOutcome.CERTIFIED
    )
    assert diamond.final_audit.failure_upper < Fraction(1, 20)
    assert diamond.final_audit.normalized_regret_upper == 0


def test_all_heldout_targets_certify_and_match_cold_ground(
    campaign: rapm.CrossGeometryCampaignV1,
) -> None:
    expected_bounds = {
        "c4": Fraction(230_656_215, 5_905_580_032),
        "diamond": Fraction(516_701_257, 10_737_418_240),
        "k4": Fraction(839_745_981, 21_474_836_480),
    }
    for result in campaign.target_results:
        assert (
            result.final_audit.outcome
            is rapm.TargetAuditOutcome.CERTIFIED
        )
        assert (
            result.final_audit.failure_upper
            == expected_bounds[result.context.graph_key]
        )
        assert result.final_audit.failure_upper < Fraction(1, 20)
        assert result.final_audit.normalized_regret_upper == 0
        assert all(
            item.selected_failure_probability == Fraction(99, 5_000)
            and item.feasible
            and item.model_reuse_count == 0
            for item in result.direct_controls
        )


def test_two_occurrences_reuse_only_their_context_local_model(
    campaign: rapm.CrossGeometryCampaignV1,
) -> None:
    assert campaign.occurrence_count == 6
    for result in campaign.target_results:
        assert len(result.occurrences) == 2
        assert len({item.occurrence_id for item in result.occurrences}) == 2
        assert len({item.audit_id for item in result.occurrence_audits}) == 2
        assert all(
            item.model_id == result.final_model.model_id
            and item.profile_id == result.final_profile.profile_id
            and item.outcome is rapm.TargetAuditOutcome.CERTIFIED
            for item in result.occurrence_audits
        )
        assert result._payload()["occurrence_new_ground_rows"] == [0, 0]
    assert len(
        {
            item.final_model.model_id
            for item in campaign.target_results
        }
    ) == 3


def test_no_transfer_and_ood_controls_fall_back_without_false_certificate(
    campaign: rapm.CrossGeometryCampaignV1,
) -> None:
    assert len(campaign.no_transfer_controls) == 3
    assert all(
        item.source_proposal_available is False
        and item.target_transition_driven_abstraction_search_allowed is False
        and item.abstract_certificate_count == 0
        and item.direct_fallback_failure_probability == Fraction(99, 5_000)
        and item.same_result_as_registered_cold_control
        for item in campaign.no_transfer_controls
    )
    ood = campaign.semantic_ood_control
    assert ood.ground_row_count == 48
    assert ood.generative_sample_count == 48 * 65_536
    assert ood.registered_mechanism_verification_passed is False
    assert ood.model_construction_allowed is False
    assert ood.abstract_certificate_count == 0
    assert ood.fallback_required
    assert ood.false_certificate_count == 0
    assert ood.unregistered_topology_rejected_pre_ground
    assert ood.unregistered_topology_ground_access_count == 0


def test_vertex_permutation_is_relationally_equivariant(
    campaign: rapm.CrossGeometryCampaignV1,
) -> None:
    control = campaign.permutation_control
    assert control.permutation == (2, 0, 3, 1)
    assert control.state_program_ids_equal
    assert control.action_program_ids_equal
    assert control.support_multiset_equal
    assert control.mapped_certificate_value_equal
    assert control.graph_identity_feature_used is False


def test_pre_authorization_and_cross_structural_transplants_fail_closed(
    campaign: rapm.CrossGeometryCampaignV1,
) -> None:
    c4, diamond, _ = campaign.target_results
    with pytest.raises(rapm.CrossGeometryInvariantViolation):
        rapm.acquire_authorized_target_evidence_v1(
            c4.context,
            c4.base_profile,
            diamond.first_authorization,
            foundation.target_root_catalogues_v1(c4.context),
        )
    with pytest.raises(rapm.CrossGeometryInvariantViolation):
        rapm.build_target_statistical_rapm_v1(
            diamond.context,
            campaign.proposal,
            diamond.base_profile,
            (c4.first_evidence,),
            (c4.first_verification,),
        )
    foreign_model = replace(
        c4.final_model,
        context_id=diamond.context.context_id,
    )
    with pytest.raises(rapm.CrossGeometryInvariantViolation):
        rapm.audit_target_rapm_v1(
            diamond.context,
            c4.final_profile,
            foreign_model,
            foundation.target_root_catalogues_v1(diamond.context),
        )


def test_raw_draw_tamper_is_rejected_by_semantic_replay(
    campaign: rapm.CrossGeometryCampaignV1,
) -> None:
    c4 = campaign.target_results[0]
    original = c4.first_evidence.sampled_rows[0]
    replacement = "0" if original.draws_hex[0] != "0" else "1"
    tampered_row = replace(
        original,
        draws_hex=replacement + original.draws_hex[1:],
    )
    tampered_evidence = replace(
        c4.first_evidence,
        sampled_rows=tuple(
            sorted(
                (tampered_row,) + c4.first_evidence.sampled_rows[1:],
                key=lambda item: item.sampled_row_id,
            )
        ),
    )
    with pytest.raises(
        rapm.CrossGeometryInvariantViolation,
        match="raw-draw semantic replay",
    ):
        rapm.verify_target_evidence_v1(
            c4.context,
            c4.base_profile,
            c4.first_authorization,
            foundation.target_root_catalogues_v1(c4.context),
            tampered_evidence,
        )


def test_campaign_and_same_implementation_verifier_are_frozen(
    campaign: rapm.CrossGeometryCampaignV1,
) -> None:
    assert (
        campaign.campaign_id
        == "2399c56dd7378429cc08dabb52d7bb76c61bc26f7541dccb535badfe193a7d7a"
    )
    verification = rapm.verify_cross_geometry_campaign_v1(campaign)
    assert verification.source_proposal_replayed
    assert verification.model_epochs_replayed == 6
    assert verification.occurrence_audits_replayed == 6
    assert verification.evidence_verification_attestations_checked == 6
    assert verification.cold_controls_checked == 6
    assert verification.controls_checked == 6
    assert verification.raw_draws_operationally_replayed
    assert verification.independent_algorithm_verification is False
    assert (
        verification.verification_id
        == "ea29a7e0c885166c1b321df24a53edc37975fe680f9bc97f4fa38288830ea329"
    )
    document = campaign.to_document()
    assert document["broad_graph_generalization_claimed"] is False
    assert document["second_domain_claimed"] is False
    assert document["sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
