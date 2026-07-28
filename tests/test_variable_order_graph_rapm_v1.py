from dataclasses import fields, replace
from fractions import Fraction

import pytest

import acfqp.variable_order_graph_rapm_v1 as graph


@pytest.fixture(scope="session")
def campaign() -> graph.VariableOrderGraphCampaignV1:
    return graph.run_variable_order_graph_campaign_v1()


def test_registered_vertex_counts_are_strictly_disjoint() -> None:
    family = graph.registered_variable_order_family_v1()
    assert family.source_vertex_counts == (4,)
    assert family.target_vertex_counts == (5, 6)
    assert not set(family.source_vertex_counts) & set(
        family.target_vertex_counts
    )
    context_fields = {item.name for item in fields(graph.VariableOrderGraphContextV1)}
    assert "selected_root_action" not in context_fields
    assert "role" not in context_fields


def test_source_skeleton_is_data_only_and_portable(
    campaign: graph.VariableOrderGraphCampaignV1,
) -> None:
    assert len(campaign.source_log.rows) == 120
    assert (
        campaign.source_skeleton.state_program.rendered
        == "cardinality_actions(legal_actions)"
    )
    assert (
        campaign.source_skeleton.action_program.rendered
        == "cardinality_resources(linked_filter(action_anchor,active_resources))"
    )
    assert campaign.source_metrics.ground_state_count == 51
    assert campaign.source_metrics.abstract_state_count == 4
    assert campaign.source_metrics.ground_row_count == 120
    assert campaign.source_metrics.abstract_support_count == 7
    skeleton_fields = {
        item.name for item in fields(type(campaign.source_skeleton))
    }
    assert skeleton_fields == {
        "role_schema_id",
        "source_observation_log_id",
        "state_program",
        "action_program",
        "support_schema",
    }


def test_exact_rejection_mapper_has_no_modulo_tail_bias() -> None:
    modulus = 300
    limit = (1 << 64) - ((1 << 64) % modulus)
    quotient, remainder = divmod(1 << 64, modulus)
    assert limit == quotient * modulus
    assert (1 << 64) - limit == remainder
    assert 0 < remainder < modulus
    assert graph.exact_rejection_ordinal_v1(3, limit) is None
    assert graph.exact_rejection_ordinal_v1(3, (1 << 64) - 1) is None
    for token in range(modulus):
        expected = 2 * (token // 100) + (0 if token % 100 < 99 else 1)
        assert graph.exact_rejection_ordinal_v1(3, token) == expected
        assert (
            graph.exact_rejection_ordinal_v1(
                3,
                token + (quotient - 1) * modulus,
            )
            == expected
        )
    with pytest.raises(graph.VariableOrderGraphInvariantViolation):
        graph.exact_rejection_ordinal_v1(5, 0)


def test_raw_trace_and_rejection_trace_replay_fail_closed(
    campaign: graph.VariableOrderGraphCampaignV1,
) -> None:
    result = campaign.results[0]
    row = result.evidence.root_rows[0]
    assert graph.verify_packed_variable_graph_row_v1(result.context, row)
    changed = bytes([row.packed_ordinals[0] ^ 1]) + row.packed_ordinals[1:]
    forged = replace(row, packed_ordinals=changed)
    with pytest.raises(graph.VariableOrderGraphInvariantViolation):
        graph.verify_packed_variable_graph_row_v1(result.context, forged)
    changed_rejections = (
        bytes([row.packed_rejection_flags[0] ^ 1])
        + row.packed_rejection_flags[1:]
    )
    forged_rejections = replace(
        row,
        packed_rejection_flags=changed_rejections,
    )
    with pytest.raises(graph.VariableOrderGraphInvariantViolation):
        graph.verify_packed_variable_graph_row_v1(
            result.context,
            forged_rejections,
        )


def test_operational_rows_expose_support_not_exact_probability(
    campaign: graph.VariableOrderGraphCampaignV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = campaign.results[0]
    descriptor_fields = {
        item.name for item in fields(graph.ObservedVariableGraphAtomV1)
    }
    assert "probability" not in descriptor_fields
    assert result.evidence.exact_local_support_row_count == 22
    assert result.final_model.exact_local_support_rows_used == 22

    def forbidden_atoms(*args: object, **kwargs: object) -> object:
        raise AssertionError("builder attempted a second kernel support read")

    monkeypatch.setattr(graph.RelationalGraphMergeKernelV2, "atoms", forbidden_atoms)
    rebuilt = graph.build_partial_statistical_rapm_v1(
        result.context,
        campaign.source_skeleton,
        result.final_profile,
        result.evidence,
        result.verification,
    )
    assert rebuilt.model_id == result.final_model.model_id


def test_root_cone_is_authorized_after_both_root_rows(
    campaign: graph.VariableOrderGraphCampaignV1,
) -> None:
    expected_actions = {
        "variable_target_w5_v0": ((0, 1, 1),),
        "variable_target_k6_v0": ((0, 1, 0), (0, 1, 1)),
        "variable_negative_k6_minus_edge_v0": ((2, 3, 2), (2, 3, 3)),
    }
    for result in campaign.results:
        authorization = result.evidence.authorization
        assert authorization.authorization_sequence == 3
        assert authorization.root_row_ids == tuple(
            sorted(item.row_id for item in result.evidence.root_rows)
        )
        assert (
            authorization.selected_ground_actions
            == expected_actions[result.context.context_key]
        )
        assert result.evidence.access_log.events[1].kind is graph.AccessKind.ROOT_ROWS
        assert result.evidence.access_log.events[2].sequence == 3


def test_evaluation_role_label_cannot_change_sampled_row(
    campaign: graph.VariableOrderGraphCampaignV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = campaign.results[0]
    row = result.evidence.root_rows[0]
    monkeypatch.setattr(
        graph,
        "registered_graph_target_role_v1",
        lambda context: graph.GraphTargetRole.NO_SOUND_COVER,
    )
    replayed = graph._acquire_row(
        result.context,
        row.catalogue,
        row.action,
    )
    assert replayed.row_id == row.row_id
    assert replayed.packed_ordinals == row.packed_ordinals
    assert (
        replayed.packed_rejection_flags
        == row.packed_rejection_flags
    )


def test_positive_targets_and_no_cover_fallback_goldens(
    campaign: graph.VariableOrderGraphCampaignV1,
) -> None:
    w5, k6, negative = campaign.results
    assert w5.evidence.ground_row_count == 22
    assert k6.evidence.ground_row_count == 60
    assert negative.evidence.ground_row_count == 60
    assert w5.final_audit.outcome is graph.PortableGraphAuditOutcome.CONDITIONALLY_CERTIFIED
    assert k6.final_audit.outcome is graph.PortableGraphAuditOutcome.CONDITIONALLY_CERTIFIED
    assert w5.program_trace is not None
    assert w5.program_trace.candidate_count == 11
    assert (
        w5.program_trace.selected_program_rendered
        == "active_attribute_degree_signature"
    )
    assert k6.program_trace is None
    assert negative.program_trace is not None
    assert negative.program_trace.candidate_count == 9
    assert not negative.program_trace.sound_cover_found
    assert negative.fallback_used
    assert negative.fallback_proof is not None
    assert negative.fallback_proof.exact_failure_probability == Fraction(
        2277,
        16000,
    )
    assert negative.fallback_proof.exact_normalized_reward == Fraction(3, 64)
    assert negative.false_certificate_count == 0


def test_complete_contingent_policy_and_uniform_distinct_concretizer(
    campaign: graph.VariableOrderGraphCampaignV1,
) -> None:
    for result, evaluation in zip(campaign.results, campaign.evaluations):
        audit = result.final_audit
        assert audit.decision_count == len(audit.policy_assignments)
        assert sum(
            item.remaining_horizon == graph.HORIZON
            for item in audit.policy_assignments
        ) == 1
        for assignment in audit.policy_assignments:
            for entry in assignment.concretizer_entries:
                assert entry.distinct_ground_actions == tuple(
                    sorted(set(entry.distinct_ground_actions))
                )
        assert (
            evaluation.lifted_exact_failure_probability
            <= audit.failure_upper
        )
        assert (
            evaluation.lifted_exact_normalized_reward
            >= audit.normalized_reward_lower
        )
        assert evaluation.audit_bounds_cover_exact_lift
        assert evaluation.exact_regret_check_passed


def test_omitted_reachable_continuation_assignment_is_rejected(
    campaign: graph.VariableOrderGraphCampaignV1,
) -> None:
    result = campaign.results[0]
    assignments = list(result.final_audit.policy_assignments)
    removed = next(
        item for item in assignments if item.remaining_horizon == 1
    )
    assignments.remove(removed)
    forged_audit = replace(
        result.final_audit,
        policy_assignments=tuple(assignments),
        decision_count=len(assignments),
    )
    forged_result = replace(result, final_audit=forged_audit)
    with pytest.raises(
        graph.VariableOrderGraphInvariantViolation,
        match="lacks a reachable",
    ):
        graph.evaluate_variable_graph_context_v1(forged_result)


def test_matched_direct_control_and_fallback_work_are_separate(
    campaign: graph.VariableOrderGraphCampaignV1,
) -> None:
    assert [
        item.matched_direct_control.matched_h2_row_count
        for item in campaign.evaluations
    ] == [30, 60, 60]
    assert [
        item.coverage.explicitly_unknown_ground_rows
        for item in campaign.evaluations
    ] == [8, 0, 0]
    assert campaign.sparse_construction_complete_closure_calls == 0
    assert campaign.fallback_exact_ground_rows == 60
    assert campaign.evaluations[0].matched_direct_control.exact_root_failure_probability == Fraction(
        99,
        5000,
    )
    assert campaign.evaluations[1].matched_direct_control.exact_root_failure_probability == Fraction(
        99,
        5000,
    )


def test_operational_runner_never_calls_cold_evaluation(
    campaign: graph.VariableOrderGraphCampaignV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = campaign.results[0]

    def forbidden_cold(*args: object, **kwargs: object) -> object:
        raise AssertionError("operational runner called evaluation-only cold control")

    monkeypatch.setattr(graph, "cold_variable_graph_control_v1", forbidden_cold)
    monkeypatch.setattr(
        graph,
        "acquire_sparse_variable_graph_evidence_v1",
        lambda context, skeleton: expected.evidence,
    )
    monkeypatch.setattr(
        graph,
        "verify_sparse_variable_graph_evidence_v1",
        lambda context, skeleton, evidence: expected.verification,
    )
    replayed = graph.run_variable_graph_context_v1.__wrapped__(
        expected.context,
        campaign.source_skeleton,
    )
    assert replayed.result_id == expected.result_id


def test_calibration_covers_adaptive_aggregate_family(
    campaign: graph.VariableOrderGraphCampaignV1,
) -> None:
    calibration = campaign.calibration
    assert calibration.family_aggregate_obligations == 287
    assert calibration.positive_aggregate_obligations == 167
    assert calibration.hoeffding_exponent == Fraction(16384, 1225)
    assert calibration.exponential_taylor_degree == 16
    assert calibration.exponential_taylor_lower > 500_000
    assert calibration.per_obligation_tail_upper == Fraction(1, 250_000)
    assert calibration.family_tail_upper == Fraction(287, 250_000)
    assert calibration.family_confidence_lower == Fraction(249713, 250000)
    assert calibration.statistical_claim_scope == graph.STATISTICAL_CLAIM_SCOPE
    assert not calibration.unconditional_iid_claim

    result = campaign.results[0]
    forged = replace(
        result.evidence,
        preregistered_aggregate_obligation_count=(
            result.evidence.preregistered_aggregate_obligation_count - 1
        ),
    )
    with pytest.raises(graph.VariableOrderGraphInvariantViolation):
        graph.verify_sparse_variable_graph_evidence_v1(
            result.context,
            campaign.source_skeleton,
            forged,
        )


def test_query_reuse_has_zero_second_occurrence_acquisition(
    campaign: graph.VariableOrderGraphCampaignV1,
) -> None:
    reused = tuple(
        item for item in campaign.query_occurrences if item.identity_bound_reuse
    )
    assert len(reused) == 2
    assert all(item.occurrence_index == 2 for item in reused)
    assert all(item.newly_acquired_ground_rows == 0 for item in reused)
    assert all(item.newly_acquired_draws == 0 for item in reused)
    for result in campaign.results[:2]:
        bound = tuple(
            item
            for item in campaign.query_occurrences
            if item.context_id == result.context.context_id
        )
        assert len({item.query_id for item in bound}) == 2
        assert {item.final_model_id for item in bound} == {
            result.final_model.model_id
        }
        assert {item.final_audit_id for item in bound} == {
            result.final_audit.audit_id
        }


def test_no_transfer_and_vertex_permutation_controls_are_executed(
    campaign: graph.VariableOrderGraphCampaignV1,
) -> None:
    control = campaign.no_transfer_control
    assert control.tested_injections == 3
    assert control.cross_order_evidence_transplant_rejected
    assert control.target_log_as_source_rejected
    assert control.forbidden_source_dynamics_access_rejected
    for permutation in campaign.permutation_controls:
        assert permutation.kernel_equivariance
        assert permutation.state_coordinate_equivariance
        assert permutation.action_coordinate_equivariance
        assert (
            permutation.exact_original_failure_probability
            == permutation.exact_permuted_failure_probability
        )


def test_campaign_semantic_verifier_closes_all_identity_chains(
    campaign: graph.VariableOrderGraphCampaignV1,
) -> None:
    verification = graph.verify_variable_order_graph_campaign_v1(campaign)
    assert verification.campaign_id == campaign.campaign_id
    assert verification.positive_certificate_count == 2
    assert verification.exact_fallback_count == 1
    assert verification.no_transfer_boundary_passed
    assert verification.sparse_access_boundary_passed
    assert verification.verified_no_transfer_control_id == (
        campaign.no_transfer_control.control_id
    )
    assert campaign.status == "CONDITIONAL_CROSS_ORDER_SPARSE_RAPM_CLOSED"
