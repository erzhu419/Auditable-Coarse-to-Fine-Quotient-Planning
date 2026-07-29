from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

import acfqp.observation_support_graph_model_v1 as graph_model
import acfqp.observation_support_h2_closure_v1 as h2_closure
import acfqp.observation_support_promoted_h2_consumer_v1 as first_consumer
import acfqp.observation_support_second_transaction_v1 as second
import acfqp.partial_support_expansion_authority_v1 as expansion
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer


@dataclass(frozen=True)
class _Built:
    context: observer.PublicGraphContextV1
    closure: h2_closure.ObservationSupportH2ClosureV1
    bridge: graph_model.ObservationSupportGraphModelBridgeV1
    base_audit: robust.RobustPlanAuditV1
    threshold: robust.RobustThresholdProfileV1
    transaction1: (
        first_consumer.ObservationSupportPromotedH2ConsumerV1
    )
    run: second.SecondSupportTransactionRunV1
    probe: second.K6TwoDistinctRowProbeV0


@pytest.fixture(scope="module")
def built() -> _Built:
    context = observer.public_context_by_key_v1("opaque_graph_k6_v0")
    closure = h2_closure.acquire_observation_support_h2_closure_v1(
        context,
        8192,
        max_workers=32,
    )
    bridge = graph_model.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=closure.root_catalogue,
        catalogues=(closure.root_catalogue, *closure.child_catalogues),
        partial_rows=closure.all_rows,
    )
    threshold = robust.RobustThresholdProfileV1(
        context.context_id,
        context.risk_tolerance,
        bridge.reward_ceiling,
    )
    base_audit = robust.solve_quotient_robust_h2_v1(
        bridge.quotient_model,
        threshold,
    )
    authorization1 = expansion.authorize_partial_support_expansion_v1(
        bridge=bridge,
        audit=base_audit,
        threshold=threshold,
        partial_rows=closure.all_rows,
        checkpoint_draw_count=2048,
    )
    replacement1 = expansion.promote_authorized_partial_support_row_v1(
        bridge=bridge,
        audit=base_audit,
        threshold=threshold,
        partial_rows=closure.all_rows,
        authorization=authorization1,
    )
    transaction1 = (
        first_consumer.consume_partial_support_promoted_row_replacement_v1(
            context=context,
            parent_closure=closure,
            parent_bridge=bridge,
            parent_audit=base_audit,
            threshold=threshold,
            replacement=replacement1,
            new_child_validation_checkpoint=8192,
            max_workers=32,
        )
    )
    run = second.run_second_support_transaction_v1(
        context=context,
        base_closure=closure,
        base_bridge=bridge,
        base_audit=base_audit,
        threshold=threshold,
        transaction1=transaction1,
        max_workers=32,
    )
    probe = second.freeze_k6_two_distinct_row_probe_v0(
        context=context,
        base_closure=closure,
        transaction1=transaction1,
        second_run=run,
    )
    return _Built(
        context,
        closure,
        bridge,
        base_audit,
        threshold,
        transaction1,
        run,
        probe,
    )


@pytest.fixture(scope="module")
def probe(built: _Built) -> second.K6TwoDistinctRowProbeV0:
    return built.probe


def test_bounded_k6_probe_finds_no_sound_different_row_cover(
    probe: second.K6TwoDistinctRowProbeV0,
) -> None:
    run = probe.second_run

    assert (
        run.outcome
        is second.SecondTransactionOutcome.NO_SOUND_DIFFERENT_ROW_COVER
    )
    assert len(run.candidate_evidence) == 49
    assert all(
        item.status is expansion.RowCounterfactualStatus.STILL_FAILED
        for item in run.candidate_evidence
    )
    assert sum(
        item.changes_failed_to_certified
        for item in run.candidate_evidence
    ) == 0
    assert run.authorization is None
    assert run.replacement is None
    assert run.closure is None
    assert run.bridge is None
    assert run.audit is None


def test_candidates_are_recomputed_on_mixed_model_without_row_reuse(
    probe: second.K6TwoDistinctRowProbeV0,
) -> None:
    run = probe.second_run
    context = run.context

    assert all(
        item.parent_model_id == context.transaction1_model_id
        and item.parent_audit_id == context.transaction1_audit_id
        and item.threshold_profile_id == context.threshold_profile_id
        for item in run.candidate_evidence
    )
    candidate_partial_ids = {
        item.partial_row_id for item in run.candidate_evidence
    }
    assert context.transaction1_parent_partial_row_id not in (
        candidate_partial_ids
    )
    assert context.transaction1_promoted_partial_row_id not in (
        candidate_partial_ids
    )
    assert len(candidate_partial_ids) == len(run.candidate_evidence)


def test_no_cover_charges_no_new_observations_and_closes_budget(
    probe: second.K6TwoDistinctRowProbeV0,
) -> None:
    run = probe.second_run
    counters = run.counters

    assert counters.eligible_counterfactual_row_count == 49
    assert counters.causal_counterfactual_row_count == 0
    assert counters.incremental_observer_draws == 0
    assert counters.incremental_random_word_calls == 0
    assert counters.incremental_rejections == 0
    assert counters.cap_rejections == 0
    assert counters.global_16384_checkpoint_accesses == 0
    assert run.third_transaction_allowed is False
    assert probe.third_transaction_allowed is False
    assert probe.base_checkpoint == 8192
    assert probe.max_global_checkpoint == 8192
    assert probe.global_16384_checkpoint_accesses == 0


def test_uncertified_probe_has_typed_null_exact_metrics(
    probe: second.K6TwoDistinctRowProbeV0,
) -> None:
    assert probe.exact_lift is None
    assert probe.exact_failure_probability is None
    assert probe.exact_normalized_regret is None
    document = probe.to_document()
    assert document["exact_lift_evaluation_id"] is None
    assert document["exact_failure_probability"] is None
    assert document["exact_normalized_regret"] is None
    assert document["exact_evaluation_lane_only"] is True


def test_serial_and_parallel_schedules_have_identical_identities(
    built: _Built,
) -> None:
    serial_run = second.run_second_support_transaction_v1(
        context=built.context,
        base_closure=built.closure,
        base_bridge=built.bridge,
        base_audit=built.base_audit,
        threshold=built.threshold,
        transaction1=built.transaction1,
        max_workers=1,
    )
    serial = second.freeze_k6_two_distinct_row_probe_v0(
        context=built.context,
        base_closure=built.closure,
        transaction1=built.transaction1,
        second_run=serial_run,
    )

    assert serial.probe_id == built.probe.probe_id
    assert serial.to_document() == built.probe.to_document()
    assert serial.second_run.run_id == built.run.run_id


def test_negative_run_complete_verifier_replays_full_dependency_chain(
    built: _Built,
) -> None:
    verification = second.verify_second_support_transaction_v1(
        context=built.context,
        base_closure=built.closure,
        base_bridge=built.bridge,
        base_audit=built.base_audit,
        threshold=built.threshold,
        transaction1=built.transaction1,
        claimed=built.run,
        max_workers=32,
    )

    assert verification.valid
    assert verification.claimed_run_id == built.run.run_id
    assert verification.replayed_run_id == built.run.run_id
    assert (
        verification.outcome
        is second.SecondTransactionOutcome.NO_SOUND_DIFFERENT_ROW_COVER
    )
    assert verification.independent_algorithm_implementation is False


def test_no_sound_path_cannot_reach_exact_or_global_16384(
    built: _Built,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_exact(*_args, **_kwargs):
        raise AssertionError("NO_SOUND path reached exact evaluation")

    monkeypatch.setattr(
        observer,
        "evaluation_exact_atoms_v1",
        forbidden_exact,
    )
    monkeypatch.setattr(
        observer,
        "evaluation_exact_ground_search_v1",
        forbidden_exact,
    )
    requested_checkpoints: list[int] = []

    def bounded_closure(
        context: observer.PublicGraphContextV1,
        checkpoint: int,
        *,
        max_workers: int,
    ) -> h2_closure.ObservationSupportH2ClosureV1:
        assert context == built.context
        assert max_workers == 32
        requested_checkpoints.append(checkpoint)
        if checkpoint != 8192:
            raise AssertionError("public probe requested global checkpoint 16384")
        return built.closure

    monkeypatch.setattr(
        h2_closure,
        "acquire_observation_support_h2_closure_v1",
        bounded_closure,
    )
    frozen = second.run_k6_two_distinct_row_probe_v0(max_workers=32)

    assert frozen.exact_lift is None
    assert requested_checkpoints == [8192]
    assert frozen.global_16384_checkpoint_accesses == 0


def test_checkpoint_transaction_and_history_attacks_fail_closed(
    probe: second.K6TwoDistinctRowProbeV0,
) -> None:
    error = second.ObservationSupportSecondTransactionInvariantViolation

    with pytest.raises(error, match="history or checkpoint"):
        replace(probe.second_run.context, transaction_index=3)
    with pytest.raises(error, match="history or checkpoint"):
        replace(
            probe.second_run.context,
            transaction_history_ids=probe.second_run.context
            .transaction_history_ids[:-1],
        )
    with pytest.raises(error, match="bounded K6 probe"):
        replace(probe, max_global_checkpoint=16_384)
    with pytest.raises(error, match="bounded K6 probe"):
        replace(probe, third_transaction_allowed=True)
    with pytest.raises(error, match="registered finite profile"):
        replace(
            second.registered_second_transaction_caps_v1(),
            max_support_transactions=3,
        )


def test_candidate_transplant_attack_fails_closed(
    probe: second.K6TwoDistinctRowProbeV0,
) -> None:
    first = probe.second_run.candidate_evidence[0]
    transplanted = replace(
        first,
        parent_audit_id=probe.second_run.context.base_audit_id,
    )
    candidates = tuple(
        sorted(
            (transplanted, *probe.second_run.candidate_evidence[1:]),
            key=lambda item: item.evidence_id,
        )
    )

    with pytest.raises(
        second.ObservationSupportSecondTransactionInvariantViolation,
        match="schema is invalid",
    ):
        replace(probe.second_run, candidate_evidence=candidates)
