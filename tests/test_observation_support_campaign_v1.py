from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.observation_support_campaign_v1 as campaign
import acfqp.observation_support_joint_pair_recovery_v1 as joint_pair
import acfqp.observation_support_second_transaction_v1 as second_transaction
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer
import acfqp.verified_source_acquisition_archive_v2 as source_archive
from acfqp import (
    verified_source_acquisition_archive_independent_verifier_v2
    as source_archive_independent,
)


@pytest.fixture(scope="module")
def registered_campaign() -> campaign.ObservationSupportCampaignV1:
    return campaign.run_observation_support_campaign_v1(max_workers=32)


def _by_key(
    result: campaign.ObservationSupportCampaignV1,
) -> dict[str, campaign.ContextCampaignResultV1]:
    return {
        item.context.context_key: item for item in result.context_results
    }


def _nested_pool_sources() -> tuple[str, ...]:
    return (
        inspect.getsource(
            campaign.h2_closure
            .acquire_observation_support_h2_closure_v1
        ),
        inspect.getsource(
            campaign.h2_closure
            .verify_observation_support_h2_closure_v1
        ),
        inspect.getsource(
            campaign.refinement
            .refine_observation_support_coordinates_v1
        ),
        inspect.getsource(
            campaign.expansion
            .authorize_partial_support_expansion_v1
        ),
        inspect.getsource(
            campaign.promoted_consumer
            .consume_partial_support_promoted_row_replacement_v1
        ),
        inspect.getsource(
            second_transaction._eligible_counterfactuals
        ),
        inspect.getsource(
            second_transaction.run_second_support_transaction_v1
        ),
        inspect.getsource(joint_pair._model_only_evidence),
        inspect.getsource(joint_pair.run_joint_pair_support_recovery_v1),
    )


def test_nested_observation_process_pools_force_spawn() -> None:
    assert all(
        'get_context("spawn")' in source
        for source in _nested_pool_sources()
    )


def test_real_registered_campaign_closes_the_construction_gate(
    registered_campaign: campaign.ObservationSupportCampaignV1,
) -> None:
    by_key = _by_key(registered_campaign)
    w5 = by_key["opaque_graph_w5_v0"]
    k6 = by_key["opaque_graph_k6_v0"]
    no_cover = by_key["opaque_graph_k6_minus_edge_v0"]

    assert campaign.CONTRACT_VERSION == "1.32.0"
    assert registered_campaign.construction_gate_passed
    assert not registered_campaign.matched_observation_advantage
    assert (
        w5.direct_result.first_certificate_checkpoint
        == w5.quotient_result.first_certificate_checkpoint
        == 4_096
    )
    assert k6.direct_result.first_certificate_checkpoint == 8_192
    assert k6.quotient_result.first_certificate_checkpoint == 16_384
    assert (
        no_cover.direct_result.closure
        is campaign.RouteClosure.EXACT_FEASIBLE_FALLBACK
    )
    assert (
        no_cover.quotient_result.closure
        is campaign.RouteClosure.EXACT_FEASIBLE_FALLBACK
    )
    assert (
        no_cover.direct_result.exact_fallback.search.root_failure_probability
        == no_cover.quotient_result.exact_fallback.search.root_failure_probability
    )
    assert not no_cover.direct_result.exact_fallback.infeasibility_certified
    assert not no_cover.quotient_result.exact_fallback.infeasibility_certified


def test_real_support_promotion_is_a_charged_failed_transaction(
    registered_campaign: campaign.ObservationSupportCampaignV1,
) -> None:
    k6 = _by_key(registered_campaign)["opaque_graph_k6_v0"]
    promoted_executions = tuple(
        item
        for item in k6.executions
        if item.promoted_consumer_result is not None
    )
    assert len(promoted_executions) == 1
    execution = promoted_executions[0]
    assert execution.checkpoint == 8_192
    promoted = execution.promoted_consumer_result
    assert (
        promoted.audit.status
        is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    )
    assert promoted.counters.incremental_observer_draws == 249_728
    assert promoted.audit.root_failure_upper == Fraction(
        1_321_268_563,
        17_179_869_184,
    )
    assert promoted.audit.normalized_regret_upper == Fraction(
        1_300_423_631,
        38_654_705_664,
    )
    assert promoted.promoted_closure.parent_validation_checkpoint == 8_192
    assert promoted.promoted_closure.promoted_validation_checkpoint == 2_048
    assert promoted.promoted_closure.new_child_validation_checkpoint == 8_192
    assert registered_campaign.support_expansion_executed
    assert not registered_campaign.support_expansion_certified
    assert registered_campaign.counters.promoted_support_epoch_count == 1
    assert registered_campaign.counters.promoted_outcome_count > 0
    assert registered_campaign.counters.promoted_model_build_count == 1
    assert registered_campaign.counters.promoted_replan_audit_count == 1


def test_manifest_is_mechanically_all_considered_and_deduplicated(
    registered_campaign: campaign.ObservationSupportCampaignV1,
) -> None:
    expected_logical = 0
    expected_unique: set[tuple[str, str, str, str]] = set()
    for context_result in registered_campaign.context_results:
        for execution in context_result.executions:
            base_multiplier = int(execution.direct_considered) + int(
                execution.quotient_considered
            )
            if execution.quotient_refinement is not None:
                base_multiplier += len(
                    execution.quotient_refinement.candidate_traces
                )
            if execution.support_expansion_authorization is not None:
                base_multiplier += len(
                    execution.support_expansion_authorization
                    .candidate_evidence
                )
            expected_logical += (
                base_multiplier * len(execution.closure.all_rows)
            )
            for row in execution.closure.all_rows:
                expected_unique.add(
                    (
                        row.binding.context_id,
                        row.binding.row_id,
                        row.support_epoch.support_epoch_id,
                        row.confidence_authority.authority_id,
                    )
                )
            if execution.promoted_consumer_result is not None:
                rows = (
                    execution.promoted_consumer_result
                    .promoted_closure.all_rows
                )
                expected_logical += len(rows)
                for row in rows:
                    expected_unique.add(
                        (
                            row.binding.context_id,
                            row.binding.row_id,
                            row.support_epoch.support_epoch_id,
                            row.confidence_authority.authority_id,
                        )
                    )
    manifest = registered_campaign.family_manifest
    assert len(manifest.considerations) == expected_logical
    assert manifest.unique_row_epoch_count == len(expected_unique)
    assert (
        registered_campaign.family_authority.realized_unique_row_epoch_count
        == len(expected_unique)
    )


def test_incremental_accounting_uses_raw_id_union_not_prefix_sum(
    registered_campaign: campaign.ObservationSupportCampaignV1,
) -> None:
    k6 = _by_key(registered_campaign)["opaque_graph_k6_v0"]
    assert (
        k6.accounting.direct_unique_observer_draws
        < k6.accounting.quotient_unique_observer_draws
    )
    assert (
        k6.accounting.direct_unique_observer_draws
        < k6.accounting.direct_rebuild_observer_draws
    )
    assert (
        k6.accounting.quotient_unique_observer_draws
        < k6.accounting.quotient_rebuild_observer_draws
    )
    assert (
        registered_campaign.counters.physical_unique_random_word_calls
        == (
            registered_campaign.counters.physical_unique_observer_draws
            + registered_campaign.counters.physical_unique_rejections
        )
    )
    document = registered_campaign.to_document()
    assert (
        document["matched_observation_advantage_metric"]
        == "UNIQUE_RAW_OBSERVATION_PREFIX_CALLS_ONLY"
    )


def test_terminal_claims_and_exact_lanes_remain_scoped(
    registered_campaign: campaign.ObservationSupportCampaignV1,
) -> None:
    assert all(
        item.conditional_statistical_scope
        == observer.STATISTICAL_CLAIM_SCOPE
        and item.randomness_implementation
        == observer.REGISTERED_RANDOMNESS_IMPLEMENTATION
        and not item.exact_iid_implementation_claimed
        and not item.formal_exact_iid_plan_certificate
        for item in registered_campaign.terminal_envelopes
    )
    for result in registered_campaign.context_results:
        assert result.other_escape_handler.failure_value == 1
        assert not result.other_escape_handler.requires_ground_action
        assert all(
            execution.bridge.other_escape_handler.handler_id
            == result.other_escape_handler.handler_id
            for execution in result.executions
        )
        for route in (result.direct_result, result.quotient_result):
            freeze = route.operational_freeze
            assert freeze.planning_trace_prefix_id
            if route.exact_lift is not None:
                assert not route.exact_lift.may_influence_operational_certificate
            if route.exact_fallback is not None:
                assert (
                    route.exact_fallback.logical_lane
                    == "FALLBACK_EXACT"
                )
    assert not registered_campaign.official_execution_allowed
    assert registered_campaign.official_scalar_cost is None
    assert registered_campaign.official_N_break_even is None
    assert registered_campaign.WORKLOAD_ECONOMICS_GATE_NOT_RUN
    assert registered_campaign.COUNTER_COMPLETENESS_GATE_NOT_RUN
    operational_source = inspect.getsource(
        campaign._context_operational_trace_id
    )
    assert "exact_lift" not in operational_source
    assert "exact_fallback" not in operational_source
    assert "context_result_id" not in operational_source
    assert all(
        'get_context("spawn")' in source
        for source in _nested_pool_sources()
    )


def test_campaign_identity_is_parallelism_invariant(
    registered_campaign: campaign.ObservationSupportCampaignV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    by_context_id = {
        item.context.context_id: item
        for item in registered_campaign.context_results
    }
    monkeypatch.setattr(
        campaign,
        "run_observation_support_context_v1",
        lambda context, *, max_workers: by_context_id[context.context_id],
    )
    serial_schedule = campaign.run_observation_support_campaign_v1(
        max_workers=1
    )
    parallel_schedule = campaign.run_observation_support_campaign_v1(
        max_workers=32
    )
    assert serial_schedule.campaign_id == registered_campaign.campaign_id
    assert parallel_schedule.campaign_id == registered_campaign.campaign_id
    assert serial_schedule == parallel_schedule == registered_campaign


def test_gate_and_manifest_attacks_fail_closed(
    registered_campaign: campaign.ObservationSupportCampaignV1,
) -> None:
    with pytest.raises(campaign.ObservationSupportCampaignInvariantViolation):
        replace(registered_campaign, construction_gate_passed=False)
    with pytest.raises(campaign.ObservationSupportCampaignInvariantViolation):
        replace(registered_campaign, matched_observation_advantage=True)
    with pytest.raises(campaign.ObservationSupportCampaignInvariantViolation):
        replace(
            registered_campaign,
            counters=replace(
                registered_campaign.counters,
                promoted_support_epoch_count=0,
            ),
        )
    with pytest.raises(campaign.ObservationSupportCampaignInvariantViolation):
        replace(
            registered_campaign.terminal_envelopes[0],
            exact_iid_implementation_claimed=True,
        )
    with pytest.raises(campaign.ObservationSupportCampaignInvariantViolation):
        replace(
            registered_campaign.context_results[0],
            other_escape_handler=(
                registered_campaign.context_results[1]
                .other_escape_handler
            ),
        )
    with pytest.raises(campaign.ObservationSupportCampaignInvariantViolation):
        replace(
            registered_campaign.context_results[0]
            .direct_result.exact_access_order,
            sequence=(
                "EXACT_AUTHORITY_ACCESS",
                "OPERATIONAL_ROUTE_FREEZE",
            ),
        )
    with pytest.raises(campaign.ObservationSupportCampaignInvariantViolation):
        replace(
            registered_campaign.context_results[0].direct_result,
            operational_freeze=replace(
                registered_campaign.context_results[0]
                .direct_result.operational_freeze,
                planning_trace_prefix_id=(
                    registered_campaign.context_results[0]
                    .direct_result.operational_freeze.audit_id
                ),
            ),
        )
    exact_route = next(
        route
        for result in registered_campaign.context_results
        for route in (result.direct_result, result.quotient_result)
        if route.exact_lift is not None
    )
    foreign_freeze = next(
        route.operational_freeze
        for result in registered_campaign.context_results
        for route in (result.direct_result, result.quotient_result)
        if route.operational_freeze.freeze_id
        != exact_route.operational_freeze.freeze_id
    )
    with pytest.raises(campaign.ObservationSupportCampaignInvariantViolation):
        replace(
            exact_route,
            exact_lift=replace(
                exact_route.exact_lift,
                prerequisite_operational_freeze_id=foreign_freeze.freeze_id,
            ),
        )


def test_full_campaign_verifier_replays_every_family_row_and_roles(
    registered_campaign: campaign.ObservationSupportCampaignV1,
) -> None:
    verification = campaign.verify_observation_support_campaign_v1(
        registered_campaign,
        max_workers=32,
    )
    archive = (
        source_archive.freeze_verified_source_acquisition_archive_v2(
            source_campaign=registered_campaign,
            source_verification=verification,
        )
    )
    archive_verification = (
        source_archive.verify_verified_source_acquisition_archive_v2(
            source_campaign=registered_campaign,
            source_verification=verification,
            claimed=archive,
        )
    )
    independent_archive_verification = (
        source_archive_independent
        .verify_source_acquisition_archive_independently_v2(
            source_campaign=registered_campaign,
            source_verification=verification,
            claimed=archive,
        )
    )
    assert archive_verification.valid
    assert independent_archive_verification.independent_archive_transform_verified
    assert (
        independent_archive_verification
        .independent_source_campaign_verifier_claimed
        is False
    )
    assert len(archive.adjacent_pairs) == 7
    assert {
        (
            item.source_context_key,
            item.before_checkpoint,
            item.after_checkpoint,
        )
        for item in archive.adjacent_pairs
    } == {
        (context_key, before, after)
        for context_key, pairs in (
            source_archive.REGISTERED_ADJACENT_PAIRS.items()
        )
        for before, after in pairs
    }
    archive_document = archive.to_document()
    assert archive_document["caller_supplied_gain_or_score"] is False
    assert archive_document["promoted_mixed_epoch_source_excluded"]
    assert archive_document["target_identity_fields_absent"]
    assert archive.proposal_only and not archive.may_certify
    assert archive.independent_fraction_recurrence_verified
    assert not archive.independent_source_campaign_verifier_claimed
    assert not archive_verification.independent_source_campaign_verifier_claimed
    assert all(
        item.portable_feature.ids_stripped
        and item.portable_feature.exact_probabilities_absent
        and item.local_snapshot.portable_feature_key
        == item.portable_feature.feature_key
        for item in archive.trials
    )
    family_row_ids = {
        item.row.partial_row_id
        for item in registered_campaign.family_authority.unique_evidences
    }
    assert set(verification.replayed_row_ids) == family_row_ids
    assert verification.role_manifest.complete_same_implementation_bundle
    roles = {
        item.artifact_role for item in verification.role_manifest.bindings
    }
    assert "OBSERVATION_ONLY_H2_CLOSURE" in roles
    assert "RAW_PARTIAL_SUPPORT_ROW_REPLAY" in roles
    assert "PROMOTED_MIXED_EPOCH_CLOSURE_REPLAN" in roles
    assert "PRE_EXACT_OPERATIONAL_ROUTE_FREEZE" in roles
    assert "COMPLETE_SEARCH_POSTHOC_CAP_EXACT_FALLBACK" in roles
    assert "STANDALONE_EXACT_LIFT_EVALUATION" in roles
    first = verification.role_manifest.bindings[0]
    duplicate_role = campaign.VerifiedArtifactRoleBindingV1(
        "INCOMPATIBLE_ROLE_ATTACK",
        first.artifact_id,
        first.semantic_verification_id,
    )
    with pytest.raises(campaign.ObservationSupportCampaignInvariantViolation):
        campaign.DurableVerifiedRoleManifestV1(
            verification.role_manifest.campaign_id,
            tuple(
                sorted(
                    (*verification.role_manifest.bindings, duplicate_role),
                    key=lambda item: item.binding_id,
                )
            ),
        )
    omitted_raw = next(
        item
        for item in verification.role_manifest.bindings
        if item.artifact_role == "RAW_PARTIAL_SUPPORT_ROW_REPLAY"
    )
    with pytest.raises(campaign.ObservationSupportCampaignInvariantViolation):
        campaign.ObservationSupportCampaignVerificationV1(
            verification.campaign_id,
            verification.replayed_campaign_id,
            verification.replayed_row_ids,
            verification.replayed_row_verification_ids,
            verification.family_verification_id,
            campaign.DurableVerifiedRoleManifestV1(
                verification.role_manifest.campaign_id,
                tuple(
                    item
                    for item in verification.role_manifest.bindings
                    if item != omitted_raw
                ),
            ),
        )
