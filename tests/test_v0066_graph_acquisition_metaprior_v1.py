from __future__ import annotations

from collections import Counter
from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.cross_graph_relational_support_v1 as source_graph
import acfqp.proposal_only_metaprior_v1 as meta
import acfqp.sequential_bernoulli_acquisition_v1 as sequential
import acfqp.v0066_graph_acquisition_metaprior_v1 as adapter
import acfqp.variable_order_graph_rapm_v1 as target_graph


@pytest.fixture(scope="module")
def campaign() -> adapter.V0066GraphAcquisitionMetaPriorCampaignV1:
    return adapter.run_v0066_graph_acquisition_metaprior_v1()


@pytest.fixture(scope="module")
def verification(
    campaign: adapter.V0066GraphAcquisitionMetaPriorCampaignV1,
) -> adapter.V0066GraphAcquisitionMetaPriorVerificationV1:
    return adapter.verify_v0066_graph_acquisition_metaprior_v1(
        campaign
    )


def _candidate_by_key(
    campaign: adapter.V0066GraphAcquisitionMetaPriorCampaignV1,
) -> dict[str, meta.ProposalCandidateV1]:
    return {
        item.candidate_key: item
        for item in campaign.candidate_registry.candidates
    }


def test_operator_profiles_are_matched_except_for_stopping_rule(
    campaign: adapter.V0066GraphAcquisitionMetaPriorCampaignV1,
) -> None:
    fixed, adaptive = campaign.operator_semantics
    assert fixed.operator_kind is (
        adapter.GraphAcquisitionOperatorKind.FIXED_FULL_ROW_HOEFFDING
    )
    assert adaptive.operator_kind is (
        adapter.GraphAcquisitionOperatorKind.SEQUENTIAL_VARIANCE_ADAPTIVE_PROOF_FRONTIER
    )
    assert (
        fixed.confidence_alpha
        == adaptive.confidence_alpha
        == target_graph.PER_OBLIGATION_TAIL_UPPER
        == Fraction(1, 250_000)
    )
    assert (
        fixed.target_half_width
        == adaptive.target_half_width
        == target_graph.HOEFFDING_RADIUS
        == Fraction(1, 140)
    )
    assert (
        fixed.maximum_draws_per_row
        == adaptive.maximum_draws_per_row
        == target_graph.SAMPLE_COUNT_PER_ROW
        == 131_072
    )
    assert adaptive.confidence_method_id == sequential.METHOD_ID
    assert adaptive.stopping_rule == "first_sound_plan_certificate_or_cap"
    assert fixed.proposal_may_certify is False
    assert adaptive.proposal_may_certify is False


def test_paired_source_trials_are_real_n4_simulator_evidence(
    campaign: adapter.V0066GraphAcquisitionMetaPriorCampaignV1,
) -> None:
    evidence = campaign.source_evidence
    assert evidence.source_context_count == 3
    assert evidence.source_root_row_count == 40
    assert len(evidence.trials) == 40
    assert evidence.fixed_arm_draws == 5_242_880
    assert evidence.sequential_arm_draws == 208_896
    assert evidence.comparison_accounted_draws == 5_451_776
    assert evidence.physical_common_stream_draws == 5_242_880
    assert evidence.fixed_arm_exact_row_setups == 40
    assert evidence.sequential_arm_exact_row_setups == 40
    assert evidence.source_draw_reduction == Fraction(1_229, 1_280)
    assert evidence.source_scoring_proxy_id == adapter.SOURCE_SCORING_PROXY_ID
    assert (
        evidence.source_scoring_proxy_rule
        == adapter.SOURCE_SCORING_PROXY_RULE
        == "first_failure_event_cs_width_le_2radius"
    )
    assert evidence.source_proxy_ranking_only
    assert not evidence.source_scoring_proxy_may_certify
    assert Counter(
        item.sequential_draw_count for item in evidence.trials
    ) == {
        2_048: 20,
        4_096: 5,
        8_192: 12,
        16_384: 3,
    }
    assert all(item.sequential_certified_width for item in evidence.trials)
    assert all(
        item.source_scoring_proxy_id == adapter.SOURCE_SCORING_PROXY_ID
        and item.source_scoring_proxy_rule
        == adapter.SOURCE_SCORING_PROXY_RULE
        and not item.source_scoring_proxy_may_certify
        for item in evidence.trials
    )
    assert all(
        item.sequential_draw_count < item.fixed_draw_count
        for item in evidence.trials
    )
    assert all(
        item.random_word_count
        == item.fixed_draw_count + item.rejection_count
        for item in evidence.trials
    )
    assert not evidence.source_probability_values_used_for_score
    assert not evidence.full_multinomial_row_reconstruction_compared
    assert not evidence.end_to_end_planning_work_compared
    assert not evidence.unconditional_iid_claimed
    assert evidence.target_draws == evidence.target_rows == 0
    assert evidence.target_labels == 0


def test_source_prior_is_nonneutral_and_ranks_sequential_first(
    campaign: adapter.V0066GraphAcquisitionMetaPriorCampaignV1,
) -> None:
    candidates = _candidate_by_key(campaign)
    adaptive = candidates[
        adapter.GraphAcquisitionOperatorKind.SEQUENTIAL_VARIANCE_ADAPTIVE_PROOF_FRONTIER.value
    ]
    fixed = candidates[
        adapter.GraphAcquisitionOperatorKind.FIXED_FULL_ROW_HOEFFDING.value
    ]
    assert campaign.source_prior.ranked_candidate_ids == (
        adaptive.candidate_id,
        fixed.candidate_id,
    )
    assert tuple(
        (item.mean_rank, item.worst_rank, item.rank_span)
        for item in campaign.source_prior.scores
    ) == (
        (Fraction(1), Fraction(1), Fraction(0)),
        (Fraction(2), Fraction(2), Fraction(0)),
    )
    by_context: dict[str, dict[str, meta.SourceProposalObservationV1]] = {}
    for item in campaign.source_observation_log.observations:
        by_context.setdefault(item.source_context_id, {})[
            item.candidate_id
        ] = item
    assert len(by_context) == 3
    assert all(
        rows[adaptive.candidate_id].proposal_score > 0
        and rows[fixed.candidate_id].proposal_score == 0
        and rows[adaptive.candidate_id].generative_draw_count
        < rows[fixed.candidate_id].generative_draw_count
        and rows[adaptive.candidate_id].source_scoring_proxy_id
        == adapter.SOURCE_SCORING_PROXY_ID
        and rows[fixed.candidate_id].source_scoring_proxy_id
        == adapter.SOURCE_SCORING_PROXY_ID
        and not rows[adaptive.candidate_id].source_scoring_proxy_may_certify
        and not rows[fixed.candidate_id].source_scoring_proxy_may_certify
        for rows in by_context.values()
    )


def test_offline_source_and_online_target_work_are_not_conflated(
    campaign: adapter.V0066GraphAcquisitionMetaPriorCampaignV1,
) -> None:
    offline = campaign.source_observation_log.offline_accounting
    assert offline.lane == "OFFLINE_SOURCE"
    assert offline.source_context_count == 3
    assert offline.candidate_observation_count == 6
    assert offline.logged_observation_count == 80
    assert offline.generative_draw_count == 5_451_776
    assert offline.environment_interaction_count == 0
    assert offline.exact_kernel_call_count == 80
    for item in campaign.target_proposals:
        online = item.applicability.online_accounting
        assert online.lane == "ONLINE_TARGET_APPLICABILITY"
        assert online.structural_observation_count == 3
        assert online.generative_draw_count == 0
        assert online.environment_interaction_count == 0
        assert online.exact_kernel_call_count == 0
        assert online.dynamics_outcome_count == 0
        assert online.reward_label_count == 0
        assert online.certificate_label_count == 0
    document = campaign.to_document()
    assert "total_observations" not in document
    assert "official_scalar_cost" not in document


def test_w5_k6_and_k6_minus_use_only_preacquisition_identities(
    campaign: adapter.V0066GraphAcquisitionMetaPriorCampaignV1,
) -> None:
    contexts = {
        item.context_key: item
        for item in target_graph.registered_variable_order_contexts_v1()
    }
    assert tuple(item.context_key for item in campaign.target_proposals) == (
        "variable_target_w5_v0",
        "variable_target_k6_v0",
        "variable_negative_k6_minus_edge_v0",
    )
    assert len(
        {
            item.applicability.applicability_id
            for item in campaign.target_proposals
        }
    ) == 3
    assert len(
        {
            item.frontier_snapshot_id
            for item in campaign.target_proposals
        }
    ) == 3
    for item in campaign.target_proposals:
        context = contexts[item.context_key]
        assert item.context_id == context.context_id
        assert item.sampling_context_id == context.sampling_context_id
        assert item.query_id == target_graph._registered_query_id(
            context,
            1,
        )
        assert item.applicability.structural_observation_ids
        assert item.target_kernel_calls == 0
        assert item.target_dynamics_rows == 0
        assert item.target_outcome_labels == 0
        assert item.target_reward_labels == 0
        assert item.target_certificate_labels == 0


def test_each_target_receives_only_a_proposal_not_a_certificate(
    campaign: adapter.V0066GraphAcquisitionMetaPriorCampaignV1,
) -> None:
    candidates = _candidate_by_key(campaign)
    adaptive_id = candidates[
        adapter.GraphAcquisitionOperatorKind.SEQUENTIAL_VARIANCE_ADAPTIVE_PROOF_FRONTIER.value
    ].candidate_id
    for item in campaign.target_proposals:
        proposal = item.proposal
        assert proposal.status is meta.ProposalStatus.PROPOSAL_READY
        assert proposal.selected_candidate_ids == (adaptive_id,)
        assert proposal.proposal_only
        assert not proposal.may_certify
        assert not proposal.may_narrow_target_envelopes
        assert proposal.target_local_acquisition_required
        assert proposal.target_local_certificate_required
        assert proposal.certificate_authority == "NONE"
        assert not proposal.sample_efficiency_claimed
    assert campaign.source_only_nonneutral_proxy_ranking
    assert not campaign.end_to_end_operator_ranking_claimed
    assert not campaign.target_sample_efficiency_claimed
    assert not campaign.broad_sample_efficiency_claimed
    assert not campaign.plan_certificate_claimed
    assert not campaign.official_execution_allowed


def test_target_proposal_builder_does_not_call_source_or_target_kernel(
    monkeypatch: pytest.MonkeyPatch,
    campaign: adapter.V0066GraphAcquisitionMetaPriorCampaignV1,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("target proposal construction accessed a kernel")

    monkeypatch.setattr(
        source_graph.GraphMergeKernelV1,
        "__init__",
        forbidden,
    )
    monkeypatch.setattr(
        target_graph.RelationalGraphMergeKernelV2,
        "__init__",
        forbidden,
    )
    replay = adapter.build_graph_target_acquisition_proposals_v1(
        campaign.source_log,
        campaign.source_skeleton,
        campaign.candidate_registry,
        campaign.transfer_envelope,
        campaign.source_prior,
    )
    assert tuple(item.target_proposal_id for item in replay) == tuple(
        item.target_proposal_id for item in campaign.target_proposals
    )


def test_source_scoring_function_never_reads_probability_values() -> None:
    source = inspect.getsource(adapter._run_paired_source_row_trial)
    assert ".probability" not in source
    assert "target_graph.RelationalGraphMergeKernelV2" not in source
    assert "failure_by_atom" in source
    assert adapter.SOURCE_CLAIM_SCOPE == (
        "DESCRIPTIVE_REGISTERED_SOURCE_CONTEXTS_AND_PAIRED_SEEDS_ONLY"
    )


def test_identity_and_claim_tampering_fail_closed(
    campaign: adapter.V0066GraphAcquisitionMetaPriorCampaignV1,
) -> None:
    with pytest.raises(
        adapter.V0066GraphAcquisitionMetaPriorInvariantViolation
    ):
        replace(campaign, target_sample_efficiency_claimed=True)
    with pytest.raises(
        adapter.V0066GraphAcquisitionMetaPriorInvariantViolation
    ):
        replace(
            campaign.target_proposals[0],
            target_dynamics_rows=1,
        )
    stale = replace(
        campaign.target_proposals[0].applicability,
        frontier_snapshot_id=campaign.target_proposals[1].frontier_snapshot_id,
    )
    stale_result = meta.rank_target_proposals_v1(
        campaign.candidate_registry,
        campaign.transfer_envelope,
        campaign.source_prior,
        stale,
        campaign.target_proposals[0].request,
    )
    assert stale_result.status is (
        meta.ProposalStatus.IDENTITY_MISMATCH_REFUSED
    )
    assert stale_result.selected_candidate_ids == ()


def test_full_verifier_replays_source_trials_and_not_a_certificate(
    campaign: adapter.V0066GraphAcquisitionMetaPriorCampaignV1,
    verification: adapter.V0066GraphAcquisitionMetaPriorVerificationV1,
) -> None:
    assert verification.campaign_id == campaign.campaign_id
    assert (
        verification.source_evidence_id
        == campaign.source_evidence.evidence_id
    )
    assert verification.source_prior_id == campaign.source_prior.prior_id
    assert verification.paired_source_streams_replayed == 40
    assert verification.source_draw_accounting_reconciled
    assert verification.nonneutral_source_proxy_ordering_replayed
    assert verification.source_proxy_noncertification_verified
    assert verification.zero_target_dynamics_verified
    assert verification.proposal_only_authority_verified
    assert not verification.certificate_verified
