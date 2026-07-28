from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

import acfqp.cross_domain_lmb_rapm_v1 as lmb
from acfqp.portable_relational_skeleton_v1 import (
    evaluate_portable_action_program_v1,
    evaluate_portable_state_program_v1,
)
from acfqp.variable_order_graph_rapm_v1 import (
    portable_graph_source_skeleton_v1,
)


@pytest.fixture(scope="module")
def skeleton():
    return portable_graph_source_skeleton_v1()


@pytest.fixture(scope="module")
def campaign(skeleton):
    return lmb.run_cross_domain_lmb_campaign_v1(skeleton)


def test_graph_source_skeleton_is_consumed_without_rewriting(skeleton) -> None:
    assert (
        skeleton.skeleton_id
        == "77a9666172fb5cebf30820b12075fef92e190f3ccda6cdf44e4c902c7dc73322"
    )
    assert skeleton.state_program.rendered == "cardinality_actions(legal_actions)"
    assert (
        skeleton.action_program.rendered
        == "cardinality_resources(linked_filter(action_anchor,active_resources))"
    )
    signature = inspect.signature(lmb.run_cross_domain_lmb_campaign_v1)
    assert tuple(signature.parameters) == ("skeleton", "use_cache")
    source = inspect.getsource(lmb)
    assert "observed_program_closure_synthesis_v1" not in source
    assert "synthesize_observed_lmb" not in source


def test_query_neutral_bridge_automatically_binds_relation_slot(skeleton) -> None:
    bridge = lmb.query_neutral_lmb_bridge_log_v1()
    binding = lmb.bind_lmb_relational_slot_v1(skeleton, bridge)
    assert len(bridge.rows) == 7
    assert bridge.query_inputs_used == 0
    assert bridge.heldout_target_inputs_used == 0
    assert binding.selected_binding_key == "same_type_buffer_tokens"
    assert binding.complete_binding_search
    assert binding.query_inputs_used == 0
    assert binding.heldout_target_inputs_used == 0
    assert binding.target_transition_inputs_used == 0
    summaries = {
        item.binding_key: (
            item.observed_alias_conflict_count,
            item.abstract_support_count,
            item.observed_values,
        )
        for item in binding.candidates
    }
    assert summaries["same_type_buffer_tokens"] == (0, 6, (0, 1, 2))
    assert summaries["all_buffer_tokens"][0] > 0
    assert summaries["different_type_buffer_tokens"][0] > 0
    assert not binding.automatic_ontology_alignment_claimed
    portable_shape_source = inspect.getsource(lmb._portable_shape)
    assert "(2, 4, 6)" not in portable_shape_source
    assert "(1, 2)" not in portable_shape_source
    assert "source_action_values" not in inspect.getsource(
        lmb.bind_lmb_relational_slot_v1
    )


def test_bound_lmb_views_use_the_same_portable_programs(
    skeleton,
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    binding = campaign.binding
    expected = {
        "lmb_cross_domain_seed0_mask7_v0": (
            2,
            ((3, 1), (5, 2)),
        ),
        "lmb_cross_domain_seed1_mask7_v0": (
            3,
            ((3, 1), (4, 2), (5, 1)),
        ),
        "lmb_cross_domain_seed4_mask21_v0": (
            3,
            ((1, 1), (3, 1), (5, 2)),
        ),
    }
    for context in lmb.registered_lmb_target_contexts_v1():
        assert (
            lmb.evaluate_bound_lmb_coordinates_v1(
                skeleton,
                binding,
                context,
                context.root_state,
                2,
            )
            == expected[context.context_key]
        )
        ir = lmb.materialize_lmb_relational_state_v1(
            context,
            context.root_state,
            2,
            binding,
        )
        assert evaluate_portable_state_program_v1(
            skeleton.state_program,
            ir,
        )[1] == expected[context.context_key][0]
        by_tile = {
            int(item.opaque_action_key.removeprefix("tile=")): (
                evaluate_portable_action_program_v1(
                    skeleton.action_program,
                    ir,
                    item,
                )[1]
            )
            for item in ir.legal_actions
        }
        assert tuple(sorted(by_tile.items())) == expected[context.context_key][1]
    # The target exercises multiple previously unseen structural contexts.
    assert {
        item.second_authorization.support.state_coordinate
        for item in campaign.target_results
    } == {1, 2}
    assert {
        item.first_authorization.support.state_coordinate
        for item in campaign.target_results
    } == {2, 3}


def test_each_target_uses_two_certificate_triggered_supports_only(
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    assert campaign.operational_support_count == 6
    assert campaign.operational_target_draw_count == 6 * 16_384
    assert campaign.operational_exact_ground_row_count == 0
    assert campaign.standalone_cold_ground_row_count == 13
    assert campaign.operational_support_count < campaign.standalone_cold_ground_row_count
    for result in campaign.target_results:
        assert result.first_audit.outcome is lmb.LMBAuditOutcome.FAILED_MISSING_ROOT_SUPPORT
        assert result.first_authorization.transaction_index == 1
        assert result.first_authorization.support.remaining_horizon == 2
        assert result.first_authorization.support.action_coordinate == 2
        assert result.intermediate_model.epoch_index == 1
        assert (
            result.second_audit.outcome
            is lmb.LMBAuditOutcome.FAILED_MISSING_CONTINUATION_SUPPORT
        )
        assert result.second_authorization.transaction_index == 2
        assert result.second_authorization.support.remaining_horizon == 1
        assert result.second_authorization.support.action_coordinate == 1
        assert result.final_model.epoch_index == 2
        assert len(result.final_model.rows) == 2
        assert result.final_model.exact_target_rows_enumerated == 0
        assert result.final_model.target_program_generation_count == 0
        assert not result.final_model.source_frozen_refinement_registry_used


def test_counter_traces_replay_fixed_distinct_action_concretizers(
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    for result in campaign.target_results:
        for authorization, trace, verification in (
            (
                result.first_authorization,
                result.first_trace,
                result.first_verification,
            ),
            (
                result.second_authorization,
                result.second_trace,
                result.second_verification,
            ),
        ):
            assert trace.draw_count == 16_384
            assert (
                trace.candidate_block_count
                == trace.draw_count + trace.rejected_block_count
            )
            assert trace.rejection_sampling_exact_uniform
            assert not trace.unconditional_iid_claimed
            assert (
                trace.randomness_assumption_id
                == lmb.lmb_randomness_assumption_v1().assumption_id
            )
            assert trace.exact_ground_rows_enumerated == 0
            assert tuple(tile for tile, _ in trace.action_draw_counts) == (
                authorization.support.ground_action_tiles
            )
            assert sum(count for _, count in trace.action_draw_counts) == 16_384
            assert verification.raw_counter_draws_replayed == 16_384
            assert (
                verification.candidate_counter_blocks_replayed
                == trace.candidate_block_count
            )
            assert (
                verification.rejected_counter_blocks_replayed
                == trace.rejected_block_count
            )
            assert verification.fixed_concretizer_replayed
            assert verification.conditional_random_oracle_assumption_checked
            assert not verification.unconditional_iid_claimed
            assert lmb.verify_lmb_support_trace_v1(
                result.context,
                authorization,
                trace,
            ).verification_id == verification.verification_id


def test_statistical_certificates_and_exact_cold_controls_match(
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    assert campaign.calibration.radius == Fraction(1, 60)
    assert campaign.calibration.exponent == Fraction(2048, 225)
    assert campaign.calibration.taylor_lower > 8_000
    assert campaign.calibration.family_tail_upper == Fraction(2, 125)
    assert campaign.calibration.family_confidence_lower == Fraction(123, 125)
    assert campaign.calibration.family_confidence_lower > Fraction(19, 20)
    assert campaign.calibration.confidence_semantics.startswith(
        "conditional_on_registered_random_oracle"
    )
    assert not campaign.calibration.unconditional_iid_claimed
    assert tuple(
        item.complete_h2_ground_row_count for item in campaign.cold_controls
    ) == (3, 5, 5)
    for result, cold in zip(campaign.target_results, campaign.cold_controls):
        audit = result.final_audit
        assert audit.outcome is lmb.LMBAuditOutcome.CERTIFIED
        assert audit.reward_lower == Fraction(59, 60)
        assert audit.reward_upper == Fraction(61, 60)
        assert audit.failure_upper == Fraction(119, 3600)
        assert audit.failure_upper < Fraction(1, 20)
        assert audit.normalized_regret_upper == Fraction(1, 60)
        assert audit.normalized_regret_upper < Fraction(1, 20)
        assert audit.target_transition_calls == 0
        assert audit.exact_ground_rows_used == 0
        assert audit.statistical_confidence_conditional
        assert not audit.unconditional_iid_claimed
        assert cold.exact_optimal_reward == 1
        assert cold.exact_optimal_failure == 0
        assert cold.selected_root_tile == result.context.selected_root_tile


def test_rejection_sampler_is_exact_for_nondivisor_action_counts() -> None:
    modulus = 1 << 256
    assert lmb._exact_uniform_ordinal(modulus - 1, 3) is None
    assert lmb._exact_uniform_ordinal(modulus - 2, 3) == 2
    assert lmb._exact_uniform_ordinal(0, 3) == 0
    assert lmb._exact_uniform_ordinal(1, 3) == 1
    assert lmb._exact_uniform_ordinal(2, 3) == 2


def test_semantic_policy_is_selected_from_enumerated_catalogues(
    skeleton,
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    for result in campaign.target_results:
        assert result.first_audit.root_action_catalogue == (1, 2)
        assert result.first_audit.selected_root_action_coordinate == 2
        assert result.second_audit.continuation_action_catalogue == (1,)
        assert result.second_audit.selected_continuation_action_coordinate == 1
        replay = lmb.audit_lmb_partial_statistical_rapm_v1(
            skeleton,
            campaign.binding,
            result.context,
            result.intermediate_model,
        )
        assert replay.audit_id == result.second_audit.audit_id
    source = inspect.getsource(lmb.audit_lmb_partial_statistical_rapm_v1)
    assert "_enumerated_semantic_action_catalogue_v1" in source
    assert "_select_semantic_action_v1" in source


def test_statistical_rows_reject_intervals_that_exclude_empirical_value(
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    row = campaign.target_results[0].final_model.rows[0]
    with pytest.raises(
        lmb.CrossDomainLMBInvariantViolation,
        match="statistical model row interval is invalid",
    ):
        replace(row, reward_lower=row.empirical_reward + Fraction(1, 100))
    with pytest.raises(
        lmb.CrossDomainLMBInvariantViolation,
        match="statistical model row interval is invalid",
    ):
        replace(row, failure_upper=row.empirical_failure - Fraction(1, 100))


def test_two_identity_distinct_queries_reuse_each_final_model(
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    assert campaign.occurrence_count == 6
    for result in campaign.target_results:
        assert len({item.query.query_id for item in result.occurrences}) == 2
        assert {item.model_id for item in result.occurrences} == {
            result.final_model.model_id
        }
        assert {item.new_target_draws for item in result.occurrences} == {0}
        assert {
            item.normalized_regret_upper for item in result.occurrences
        } == {Fraction(1, 60)}


def test_no_transfer_wrong_binding_and_ood_controls_fail_closed(
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    assert len(campaign.no_transfer_controls) == 3
    assert all(
        not item.abstract_model_built
        and item.abstract_certificate_count == 0
        and item.direct_reward == 1
        and item.direct_failure == 0
        and not item.target_program_search_performed
        and item.standalone_direct_control_consumed
        for item in campaign.no_transfer_controls
    )
    wrong = campaign.wrong_binding_control
    assert wrong.wrong_binding_key == "all_buffer_tokens"
    assert wrong.observed_alias_conflict_count > 0
    assert wrong.no_sound_abstract_action
    assert wrong.abstract_certificate_count == 0
    assert wrong.bridge_alias_analysis_replayed
    assert tuple(item.ood_mechanism for item in campaign.semantic_ood_controls) == (
        "hidden_selected_tile_failure_v1",
        "match_arity_four_v1",
    )
    assert all(
        item.rejected_before_model
        and item.ground_draws_before_rejection == 0
        and item.abstract_certificate_count == 0
        and item.direct_fallback_required
        and item.control_scope == "semantic_registry_identity_mismatch_only"
        and not item.alternate_mechanism_executed
        for item in campaign.semantic_ood_controls
    )
    with pytest.raises(lmb.CrossDomainLMBInvariantViolation):
        lmb.LMBSemanticsProfileV1(match_arity=4)


def test_tile_and_type_permutation_preserves_semantics(
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    control = campaign.permutation_control
    assert control.tile_permutation == (5, 4, 3, 2, 1, 0)
    assert control.type_permutation == (1, 0)
    assert control.root_support_multiset_preserved
    assert control.continuation_support_multiset_preserved
    assert control.selected_plan_mapped
    assert control.reward_failure_preserved


def test_context_epoch_and_raw_trace_transplants_are_rejected(
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    first, second, _ = campaign.target_results
    with pytest.raises(lmb.CrossDomainLMBInvariantViolation):
        lmb.verify_lmb_support_trace_v1(
            second.context,
            first.first_authorization,
            first.first_trace,
        )
    stale_authorization = replace(
        first.first_authorization,
        model_id=first.intermediate_model.model_id,
    )
    with pytest.raises(lmb.CrossDomainLMBInvariantViolation):
        lmb.verify_lmb_support_trace_v1(
            first.context,
            stale_authorization,
            first.first_trace,
        )
    tampered = replace(
        first.first_trace,
        raw_block_commitment=hashlib.sha256(b"tampered").hexdigest(),
    )
    with pytest.raises(lmb.CrossDomainLMBInvariantViolation):
        lmb.verify_lmb_support_trace_v1(
            first.context,
            first.first_authorization,
            tampered,
        )
    with pytest.raises(lmb.CrossDomainLMBInvariantViolation):
        lmb.overlay_lmb_statistical_row_v1(
            second.initial_model,
            first.final_model.rows[0],
        )


def test_cross_domain_rows_and_duck_types_are_rejected(
    skeleton,
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    class Duck:
        skeleton_id = skeleton.skeleton_id
        state_program = skeleton.state_program
        action_program = skeleton.action_program

    with pytest.raises(lmb.CrossDomainLMBInvariantViolation):
        lmb.bind_lmb_relational_slot_v1(
            Duck(),
            campaign.bridge_log,
        )
    with pytest.raises(lmb.CrossDomainLMBInvariantViolation):
        lmb.overlay_lmb_statistical_row_v1(
            campaign.target_results[0].initial_model,
            object(),  # type: ignore[arg-type]
        )
    assert campaign.transplant_control.cross_domain_row_rejected
    assert campaign.transplant_control.cross_context_evidence_rejected
    assert campaign.transplant_control.stale_epoch_authorization_rejected
    assert campaign.transplant_control.altered_raw_trace_rejected
    assert campaign.transplant_control.unregistered_semantics_rejected


def test_claim_boundary_excludes_parallel_composition_and_sample_saving(
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    assert campaign.status == lmb.SUCCESS_STATUS
    assert campaign.source_graph_skeleton_reused
    assert not campaign.source_dynamics_imported
    assert campaign.target_program_generation_count == 0
    assert campaign.automatic_slot_binding_within_frozen_adapter_claimed
    assert (
        campaign.bridge_supervision_scope
        == "human_frozen_ontology_query_neutral_exact_bridge_v1"
    )
    assert not campaign.automatic_ontology_alignment_claimed
    assert not campaign.sample_efficiency_claimed
    assert campaign.statistical_confidence_conditional
    assert not campaign.unconditional_iid_claimed
    assert not campaign.official_execution_allowed
    assert campaign.official_scalar_cost is None
    assert campaign.official_N_break_even is None
    assert campaign.operational_target_draw_count == 98_304
    assert campaign.standalone_cold_ground_row_count == 13
    assert "cold_exact_lmb_h2_control_v1" not in inspect.getsource(
        lmb.run_lmb_target_context_v1
    )
    assert not hasattr(campaign.target_results[0], "cold_control")


def test_full_campaign_replay_checks_all_raw_draws(
    skeleton,
    campaign: lmb.CrossDomainLMBCampaignV1,
) -> None:
    verification = lmb.verify_cross_domain_lmb_campaign_v1(
        skeleton,
        campaign,
    )
    assert verification.campaign_id == campaign.campaign_id
    assert verification.source_skeleton_identity_checked
    assert verification.bridge_binding_replayed
    assert verification.context_chains_replayed == 3
    assert verification.raw_counter_draws_replayed == 98_304
    assert (
        verification.candidate_counter_blocks_replayed
        == 98_304 + verification.rejected_counter_blocks_replayed
    )
    assert verification.cold_controls_replayed == 3
    assert verification.controls_checked == 8
    assert verification.same_implementation_replay
    assert not verification.independent_algorithm_verification
    assert verification.conditional_random_oracle_assumption_checked
    assert not verification.unconditional_iid_claimed
